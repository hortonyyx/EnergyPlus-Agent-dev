"""Windows update/rollback filesystem properties; synthetic validation, no model/network."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which("powershell.exe")
pytestmark = pytest.mark.skipif(SHELL is None, reason="Windows installation tool")


def write_release(root, tag, *, lock="same", files=None):
    payload = {
        "Start.cmd": "echo " + tag,
        "sim_bim.py": tag,
        "uv.lock": lock,
        "pyproject.toml": "locked-project",
        ".python-version": "3.12",
        "src/agent_runtime/agent_versions.json": "{}",
        **(files or {}),
    }
    for name, text in payload.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    manifest = {"schema_version": "sim-bim-release.v1", "source_commit": tag * 40,
                "runtime_version": "runtime-test", "domain_version": "domain-test",
                "files": {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in payload}}
    (root / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


@pytest.fixture
def installation(tmp_path):
    old = tmp_path / "fixed install"
    new = tmp_path / "release"
    write_release(old, "a", files={"skills/retired/guide.md": "old"})
    write_release(new, "b", files={"src/current.py": "new"})
    env = old / ".venv/Scripts/python.exe"
    env.parent.mkdir(parents=True)
    env.write_bytes(b"preserve original environment")
    (old / "my-settings.json").write_text("user-owned", encoding="utf-8")
    return {"install": str(old), "release": str(new), "backup": str(tmp_path / "backup"),
            "work": str(tmp_path / "work")}


def run_action(tmp_path, config, action="update", override="", *, ok=True):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    driver = tmp_path / "driver.ps1"
    driver.write_text("""
$ErrorActionPreference = 'Stop'
. $env:TEST_UPDATE_SCRIPT
$c = Get-Content -LiteralPath $env:TEST_UPDATE_CONFIG -Raw -Encoding UTF8 | ConvertFrom-Json
$InstallRoot=$c.install; $Release=$c.release; $BackupRoot=$c.backup; $WorkRoot=$c.work
$Action=$env:TEST_UPDATE_ACTION
function Verify-Product($Output) { return @{ passed=$true; elapsed_seconds=0; live_model_requests=0 } }
function Sync-Dependencies { Add-Content -LiteralPath (Join-Path $script:Install '.venv/sync.txt') -Value ([IO.File]::ReadAllText((Join-Path $script:Install 'uv.lock'))) }
""" + override + "\nInvoke-ProductUpdate | ConvertTo-Json -Depth 10\n", encoding="utf-8")
    result = subprocess.run([SHELL, "-NoProfile", "-File", str(driver)], cwd=tmp_path,
        env={**os.environ, "TEST_UPDATE_SCRIPT": str(ROOT / "scripts/release/update_product.ps1"),
             "TEST_UPDATE_CONFIG": str(config_path), "TEST_UPDATE_ACTION": action},
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    if ok:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout
    return result


def manifest(root):
    return json.loads((Path(root) / "release-manifest.json").read_bytes())


def assert_payload(root, tag):
    root = Path(root)
    m = manifest(root)
    assert m["source_commit"] == tag * 40
    assert all(hashlib.sha256((root / n).read_bytes()).hexdigest() == h for n, h in m["files"].items())
    assert (root / "my-settings.json").read_text() == "user-owned"
    assert (root / ".venv/Scripts/python.exe").read_bytes() == b"preserve original environment"


def test_update_rollback_and_repeated_update_keep_fixed_directory_and_one_small_backup(tmp_path, installation):
    c = installation
    run_action(tmp_path, c)
    assert_payload(c["install"], "b")
    assert not (Path(c["install"]) / "skills").exists()
    with zipfile.ZipFile(Path(c["backup"]) / "previous.zip") as archive:
        assert ".python-version" in archive.namelist()
        assert not any(n.startswith(".venv/") or n == "my-settings.json" for n in archive.namelist())
    before = (Path(c["backup"]) / "previous.zip").read_bytes()
    run_action(tmp_path, c)  # Same release is a no-op; it must not discard the useful rollback.
    assert (Path(c["backup"]) / "previous.zip").read_bytes() == before
    run_action(tmp_path, c, "rollback")
    assert_payload(c["install"], "a")
    assert not (Path(c["install"]) / "src/current.py").exists()
    run_action(tmp_path, c)
    assert_payload(c["install"], "b")
    assert sorted(p.name for p in Path(c["backup"]).iterdir()) == ["previous.zip", "state.json", "update.lock"]
    assert not list(Path(c["work"]).iterdir())
    assert not (Path(c["install"]) / ".venv/sync.txt").exists()


@pytest.mark.parametrize("damage", ["installed_edit", "release_edit", "unmanaged_collision", "nested_backup", "same_roots"])
def test_preflight_refuses_without_changing_user_or_installed_files(tmp_path, installation, damage):
    c = installation.copy(); installed = Path(c["install"])
    if damage == "installed_edit":
        (installed / "sim_bim.py").write_text("local change")
    elif damage == "release_edit":
        (Path(c["release"]) / "sim_bim.py").write_text("bad download")
    elif damage == "unmanaged_collision":
        (installed / "src/current.py").write_text("user-owned")
    elif damage == "nested_backup":
        c["backup"] = str(installed / "backups")
    else:
        c["work"] = c["backup"]
    before = {p.relative_to(installed).as_posix(): p.read_bytes() for p in installed.rglob("*") if p.is_file()}
    result = run_action(tmp_path, c, ok=False)
    expected = {"installed_edit": "Payload missing or modified", "release_edit": "Payload missing or modified",
                "unmanaged_collision": "Unmanaged file", "nested_backup": "must be separate", "same_roots": "must differ"}
    assert expected[damage] in result.stderr
    assert {p.relative_to(installed).as_posix(): p.read_bytes() for p in installed.rglob("*") if p.is_file()} == before
    assert not list(Path(c["backup"]).glob("*.zip"))


@pytest.mark.parametrize("name", ["../outside", "C:/outside", "src/../../outside", ".venv/stolen", "CON", "src/file:stream", "src/space. "])
def test_manifest_cannot_escape_or_take_ownership_of_environment(tmp_path, installation, name):
    c = installation
    path = Path(c["release"]) / "release-manifest.json"
    m = json.loads(path.read_bytes()); m["files"][name] = "0" * 64
    path.write_text(json.dumps(m))
    result = run_action(tmp_path, c, ok=False)
    assert "Unsafe payload path" in result.stderr
    assert_payload(c["install"], "a")


def test_failed_validation_restores_payload_and_locked_dependencies(tmp_path, installation):
    c = installation
    write_release(Path(c["release"]), "b", lock="new-lock", files={"src/current.py": "new"})
    override = """
function Verify-Product($Output) {
    if (([IO.File]::ReadAllText((Join-Path $script:Install 'sim_bim.py'))) -eq 'b') { throw 'injected validation failure' }
    return @{passed=$true;elapsed_seconds=0;live_model_requests=0}
}
"""
    result = run_action(tmp_path, c, override=override, ok=False)
    assert "previous version was restored" in result.stderr
    assert_payload(c["install"], "a")
    assert (Path(c["install"]) / ".venv/sync.txt").read_text().splitlines() == ["new-lock", "same"]
    assert json.loads((Path(c["backup"]) / "state.json").read_bytes())["status"] == "recovered"
    assert not list(Path(c["work"]).iterdir())


def test_interrupted_update_requires_and_supports_explicit_recovery(tmp_path, installation):
    c = installation
    run_action(tmp_path, c, override="function Verify-Product($Output) { exit 91 }", ok=False)
    assert_payload(c["install"], "b")
    result = run_action(tmp_path, c, ok=False)
    assert "Interrupted update" in result.stderr
    # Simulate an interrupted atomic-copy temporary file; no unmanaged file is touched.
    (Path(c["install"]) / "sim_bim.py.sim-bim-update.tmp").write_text("partial copy")
    run_action(tmp_path, c, "rollback")
    assert_payload(c["install"], "a")
    assert not (Path(c["install"]) / "sim_bim.py.sim-bim-update.tmp").exists()
    assert not list(Path(c["work"]).iterdir())


def test_recovery_preserves_edits_made_after_interruption(tmp_path, installation):
    c = installation
    run_action(tmp_path, c, override="function Verify-Product($Output) { exit 91 }", ok=False)
    (Path(c["install"]) / "sim_bim.py").write_text("user changed it after crash")
    run_action(tmp_path, c, "rollback", ok=False)
    assert (Path(c["install"]) / "sim_bim.py").read_text() == "user changed it after crash"


def test_recovery_rejects_modified_backup(tmp_path, installation):
    c = installation
    run_action(tmp_path, c, override="function Verify-Product($Output) { exit 91 }", ok=False)
    with zipfile.ZipFile(Path(c["backup"]) / "previous.zip", "a") as archive:
        archive.writestr("../escape.txt", "no")
    run_action(tmp_path, c, "rollback", ok=False)
    assert not (tmp_path / "escape.txt").exists()
    assert_payload(c["install"], "b")


def test_concurrent_maintenance_is_rejected_before_any_payload_change(tmp_path, installation):
    c = installation
    override = """
New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$held = [IO.File]::Open((Join-Path $BackupRoot 'update.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
"""
    result = run_action(tmp_path, c, override=override, ok=False)
    assert "update.lock" in result.stderr
    assert_payload(c["install"], "a")
    assert not (Path(c["backup"]) / "previous.zip").exists()


def test_busy_product_is_not_updated_or_terminated(tmp_path, installation):
    c = installation
    override = """
function Get-CimInstance {
    return [pscustomobject]@{ ProcessId=999999; Name='python.exe'; ExecutablePath=(Join-Path $script:Install '.venv/Scripts/python.exe'); CommandLine='product run' }
}
"""
    result = run_action(tmp_path, c, override=override, ok=False)
    assert "Product is running" in result.stderr
    assert_payload(c["install"], "a")
    assert not (Path(c["backup"]) / "previous.zip").exists()


def test_interruption_between_backup_record_and_promotion_is_recoverable(tmp_path, installation):
    c = installation
    override = """
$originalWriter = ${function:Write-Record}
function Write-Record($Path, $Value) {
    & $originalWriter $Path $Value
    if ($Value.status -eq 'pending') { exit 92 }
}
"""
    run_action(tmp_path, c, override=override, ok=False)
    assert_payload(c["install"], "a")
    assert (Path(c["backup"]) / "previous.zip.tmp").exists()
    run_action(tmp_path, c, "rollback")
    assert_payload(c["install"], "a")
    assert not (Path(c["backup"]) / "previous.zip.tmp").exists()
    assert not list(Path(c["work"]).iterdir())
