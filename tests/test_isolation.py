from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.execution.isolation import (
    _assert_source_allowed,
    build_isolation_workspace,
    check_feedback_text,
    merge_isolated_output,
    spawn_command,
)
from src.agent.execution.manifest import (
    RunManifest,
    RunManifestV2,
    StageRecord,
    hash_file,
    hash_text,
    load_run_manifest,
    migrate_run_to_v2,
)
from src.agent.execution.view_manifest import provision_view_manifest


CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")
_REAL_VIEWS_PATH = Path(
    "case_tests/e2e_tests/sm21_anchor/run_2026-06-20_gpt54_reading/0_reading/attempts/002/output.json"
)


def _real_views() -> dict:
    """A real, gate①-clean six-view sm21 aggregate (reused as a fixture, not
    re-derived per test — matches what `_draw_reading`'s flat-flow glob would
    have produced for this run)."""
    return json.loads(_REAL_VIEWS_PATH.read_text(encoding="utf-8"))


def _build(tmp_path: Path):
    """Preview/unbound build (no run_dir) — never merge-eligible."""
    return build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "staging")


def _formal_build(case_dir: Path, run_dir: Path, staging_root: Path):
    """Formal (run-bound) build. `build_isolation_workspace` only *verifies*
    the view manifest (§4.4/§5.2) — it never provisions — so every formal-build
    test provisions first, exactly as an operator/CLI must."""
    provision_view_manifest(case_dir, run_dir)
    return build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=staging_root)


def _case_copy(tmp_path: Path, *, name: str = "sm21_anchor") -> Path:
    """A private copy of sm21_anchor so tamper tests never touch the real
    checked-in fixture (golden byte discipline)."""
    dest = tmp_path / name
    shutil.copytree(CASE_DIR, dest)
    return dest


def _tiny_png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


def _request(staging: Path, payload: dict, name: str = "request.json") -> Path:
    path = staging / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _hook(staging: Path, command: str) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return _hook_payload(staging, payload)


def _hook_payload(staging: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(staging / "guard.py")],
        input=json.dumps(payload),
        text=True,
        cwd=staging,
        capture_output=True,
        check=False,
    )


def test_build_isolation_workspace_copies_whitelist_and_manifest(tmp_path: Path):
    manifest = _build(tmp_path)
    staging = manifest.staging_root

    assert (staging / "case_data" / "1f_view.png").exists()
    assert (staging / "case_data" / "testdata_prompt.json").exists()
    assert (staging / "skills/intake_pipeline/0_reading/session_kickoff.md").exists()
    assert not (staging / "skills/intake_pipeline/0_reading/judge_rubric.md").exists()
    assert (staging / "src/agent/reading/cv_toolbox/__init__.py").exists()
    assert (staging / "tools/cv_probe.py").exists()
    assert (staging / "tools/run_cv_probe.py").exists()
    assert (staging / "out").is_dir()

    data = json.loads((staging / "MANIFEST.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1"
    assert data["merge_eligible"] is False
    assert data["excluded_from_staging"] == []
    assert all(not item["source_path"].startswith("/") for item in data["files"] if not item["source_path"].startswith("<generated>"))
    first_png = next(item for item in data["files"] if item["path"] == "case_data/1f_view.png")
    assert first_png["sha256"] == hash_file(staging / "case_data/1f_view.png")


@pytest.mark.parametrize(
    "path",
    [
        "case_tests/test_baseline/gt/sm21/gt.json",
        "case_tests/e2e_tests/sm21_anchor/run_foo/0_reading/output.json",
        "case_tests/e2e_tests/sm21_anchor/0_reading/attempts/001/output.json",
        "skills/intake_pipeline/0_reading/judge_rubric.md",
        "case_tests/e2e_tests/sm21_anchor/report/verdict.json",
        "case_tests/e2e_tests/sm21_anchor/report/grade.json",
    ],
)
def test_forbidden_source_paths_are_rejected(path: str):
    with pytest.raises(ValueError):
        _assert_source_allowed(Path(path))


def test_run_prescan_source_path_is_allowed():
    _assert_source_allowed(
        Path("case_tests/e2e_tests/sm21_anchor/run_x/0_reading/cv_evidence/1f_view/prescan/candidates.json")
    )
    # Judgment artifacts stay blocked even inside a prescan folder.
    with pytest.raises(ValueError):
        _assert_source_allowed(
            Path("case_tests/e2e_tests/sm21_anchor/run_x/0_reading/cv_evidence/1f_view/prescan/grade.png")
        )
    # Non-prescan run paths stay blocked.
    with pytest.raises(ValueError):
        _assert_source_allowed(
            Path("case_tests/e2e_tests/sm21_anchor/run_x/0_reading/cv_evidence/1f_view/001_crop_zoom.json")
        )


def test_build_copies_run_prescan_and_kickoff_mentions_it(tmp_path: Path):
    run_dir = tmp_path / "run_probe"
    run_dir.mkdir()
    src = run_dir / "0_reading" / "cv_evidence" / "1f_view" / "prescan"
    src.mkdir(parents=True)
    (src / "candidates.json").write_text("{}", encoding="utf-8")

    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root

    copied = staging / "prescan" / "cv_evidence" / "1f_view" / "prescan" / "candidates.json"
    assert copied.exists()
    kickoff = (staging / "kickoff_prompt.md").read_text(encoding="utf-8")
    assert "prescan/cv_evidence/<image_stem>/prescan/" in kickoff


def test_formal_build_requires_view_manifest_already_provisioned(tmp_path: Path):
    """§5.2: `build_isolation_workspace` only *verifies* — it never provisions.
    A run_dir with no view_manifest.json yet must be refused, not silently
    auto-provisioned (that would smuggle a write into a "just build" call)."""
    run_dir = tmp_path / "run_unprovisioned"
    run_dir.mkdir()
    with pytest.raises(ValueError, match="provision"):
        build_isolation_workspace(CASE_DIR, run_dir=run_dir, staging_root=tmp_path / "staging")


def test_formal_build_writes_binding_and_input_inventory(tmp_path: Path):
    run_dir = tmp_path / "run_formal"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root

    assert manifest.merge_eligible is True
    binding = json.loads((staging / "binding.json").read_text(encoding="utf-8"))
    assert binding["merge_eligible"] is True
    assert binding["case_id"] == "sm21_anchor"
    assert set(binding) == {
        "merge_eligible", "run_id", "case_id", "case_dir", "run_dir",
        "view_manifest_sha256", "case_metadata_sha256", "image_sha256",
    }
    run_manifest = load_run_manifest(run_dir)
    assert isinstance(run_manifest, RunManifestV2)
    assert binding["run_id"] == run_manifest.run_id

    inventory = json.loads((staging / "input_inventory.json").read_text(encoding="utf-8"))
    assert len(inventory) == 6
    assert {"input_id", "file", "view_type", "declared_direction_token", "floor_ref", "expected_output_id"} <= set(inventory[0])
    # denominator/completeness content never leaks into the reader-visible projection
    for entry in inventory:
        assert "opening_evidence" not in entry
        assert "negative_evidence_capable_claims" not in entry


def test_spawn_command_appends_directive_and_feedback_pointer(tmp_path: Path):
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "kickoff_prompt.md").write_text("KICKOFF\n", encoding="utf-8")
    directive = tmp_path / "directive.md"
    directive.write_text("Measure before drawing. Calibrate first.\n", encoding="utf-8")

    cmd = spawn_command(staging, directive=directive)
    prompt = cmd[2]
    assert prompt.startswith("KICKOFF")
    assert "Per-run directive" in prompt
    assert "Measure before drawing" in prompt
    assert "feedback.md" not in prompt
    assert (staging / "directive.md").read_text(encoding="utf-8").startswith("Measure before")

    (staging / "feedback.md").write_text("redo", encoding="utf-8")
    prompt2 = spawn_command(staging, directive=directive)[2]
    assert "feedback.md" in prompt2 and "read it FIRST" in prompt2

    bad = tmp_path / "bad_directive.md"
    bad.write_text("compare against gt" + ".json please", encoding="utf-8")
    with pytest.raises(ValueError):
        spawn_command(staging, directive=bad)


def test_staging_run_cv_probe_smoke(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    req = _request(
        staging,
        {
            "tool": "crop_zoom",
            "args": {
                "image": "case_data/1f_view.png",
                "out_dir": "out/cv",
                "bbox": "0,0,20,20",
                "sidecar_name": "001_crop_zoom",
            },
        },
    )
    subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", "--request", str(req)],
        cwd=staging,
        check=True,
    )
    assert (staging / "out/cv/cv_evidence/1f_view/001_crop_zoom.json").exists()


def test_guard_allows_legal_run_cv_probe_and_logs(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {
            "tool": "crop_zoom",
            "args": {
                "image": "case_data/1f_view.png",
                "out_dir": "out/cv",
                "bbox": "0,0,20,20",
                "sidecar_name": "001_crop_zoom",
            },
        },
    )
    proc = _hook(staging, "python tools/run_cv_probe.py --request request.json")
    assert proc.returncode == 0, proc.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow"
    assert log["tool"] == "Bash"
    assert log["normalized_paths"]


def test_guard_ignores_transcript_path_envelope_for_legal_tool_input(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    transcript = "/root/.claude/projects/-tmp-ep-isolation-smoke-sm24/session.jsonl"
    read_payload = {
        "session_id": "s",
        "transcript_path": transcript,
        "cwd": str(staging),
        "permission_mode": "default",
        "tool_name": "Read",
        "tool_input": {"file_path": str(staging / "case_data/1f_view.png")},
    }
    proc = _hook_payload(staging, read_payload)
    assert proc.returncode == 0, proc.stderr

    proc = _hook_payload(
        staging,
        {
            "transcript_path": transcript,
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        },
    )
    assert proc.returncode == 0, proc.stderr

    _request(
        staging,
        {
            "tool": "crop_zoom",
            "args": {
                "image": "case_data/1f_view.png",
                "out_dir": "out/cv",
                "bbox": "0,0,20,20",
                "sidecar_name": "001_crop_zoom",
            },
        },
    )
    proc = _hook_payload(
        staging,
        {
            "transcript_path": transcript,
            "tool_name": "Bash",
            "tool_input": {"command": f"python {staging / 'tools/run_cv_probe.py'} --request request.json"},
        },
    )
    assert proc.returncode == 0, proc.stderr


def test_guard_with_transcript_path_still_denies_illegal_tool_input(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(
        staging,
        {
            "transcript_path": "/root/.claude/projects/-tmp-ep-isolation-smoke-sm24/session.jsonl",
            "tool_name": "Read",
            "tool_input": {"file_path": "/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/x/gt.json"},
        },
    )
    assert proc.returncode == 2
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "deny"
    assert "tool_input_excerpt" in log


@pytest.mark.parametrize(
    "command",
    [
        "python -c 'print(1)'",
        "python tools/run_cv_probe.py --request request.json; ls",
        "cd case_data",
        "env python tools/run_cv_probe.py --request request.json",
        "python tools/run_cv_probe.py --request ../request.json",
        "python tools/run_cv_probe.py --request ~/request.json",
        "python tools/run_cv_probe.py --request /workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/x/gt.json",
    ],
)
def test_guard_rejects_forbidden_bash_shapes(tmp_path: Path, command: str):
    staging = _build(tmp_path).staging_root
    _request(staging, {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": "out/cv", "bbox": "0,0,20,20"}})
    proc = _hook(staging, command)
    assert proc.returncode == 2
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "deny"


def test_guard_rejects_symlink_and_request_paths_outside_staging(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    outside = tmp_path / "outside.png"
    outside.write_bytes((staging / "case_data/1f_view.png").read_bytes())
    (staging / "case_data/escape.png").symlink_to(outside)

    _request(staging, {"tool": "crop_zoom", "args": {"image": "case_data/escape.png", "out_dir": "out/cv", "bbox": "0,0,20,20"}})
    proc = _hook(staging, "python tools/run_cv_probe.py --request request.json")
    assert proc.returncode == 2

    _request(staging, {"tool": "crop_zoom", "args": {"image": str(outside), "out_dir": "out/cv", "bbox": "0,0,20,20"}}, "outside_request.json")
    proc = _hook(staging, "python tools/run_cv_probe.py --request outside_request.json")
    assert proc.returncode == 2


# --------------------------------------------------------------------------- #
# §5.2 merge — the "merge 同门" acceptance path + the eight negative examples
# --------------------------------------------------------------------------- #
def test_merge_accepts_real_matching_views_and_binds_hash(tmp_path: Path):
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    payload = json.dumps({"views": _real_views()})
    output.write_text(payload, encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)

    assert attempt_dir.name == "001"
    assert (attempt_dir / "isolation_provenance.json").exists()
    assert (attempt_dir / "isolation_archive/MANIFEST.json").exists()
    assert (attempt_dir / "isolation_archive/isolation_settings.json").exists()
    assert (attempt_dir / "isolation_archive/guard.py").exists()
    rec = load_run_manifest(run_dir).accepted("0_reading")
    assert rec is not None
    assert rec.output_hash == hash_text(payload)
    assert rec.artifact_contract == "reading_isolated_v2"
    assert rec.artifact_hashes["output"] == rec.output_hash
    assert rec.input_hashes["isolation_provenance"] == hash_file(attempt_dir / "isolation_provenance.json")
    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    # Zero BLOCK-disposition (invariant) fails — this fixture is a real, older
    # reading run predating some provenance/dimension conventions, so a few
    # advisory cross_check fails are expected and don't prevent acceptance.
    assert not any(r["status"] == "fail" and r["layer"] == "invariant" for r in checks["results"])


def test_merge_empty_views_is_filed_but_not_accepted(tmp_path: Path):
    """Negative example #1 (empty views) — and the flagged behavior reversal:
    under the old (pre-B-M) contract this used to be silently ACCEPTED; under
    the trusted-manifest contract a required view with no matching artifact is
    a miss, so it is filed (audit trail preserved) but never promoted to
    accepted, regardless of `accept=True`."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output, accept=True)

    assert attempt_dir.name == "001"
    assert (attempt_dir / "output.json").exists()
    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    assert any(r["check_id"] == "reading.view_manifest_coverage" and r["status"] == "fail" for r in checks["results"])
    assert load_run_manifest(run_dir).accepted("0_reading") is None


def test_merge_retries_next_attempt_without_overwrite(tmp_path: Path):
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")
    existing = run_dir / "0_reading/attempts/001"
    existing.mkdir(parents=True)
    (existing / "output.json").write_text("existing", encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)

    assert attempt_dir.name == "002"
    assert (existing / "output.json").read_text(encoding="utf-8") == "existing"


def test_merge_missing_entry_is_rejected(tmp_path: Path):
    """Negative example #2 (missing entry)."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    views = _real_views()
    del views["South_view"]
    output.write_text(json.dumps({"views": views}), encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)
    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    cov = next(r for r in checks["results"] if r["check_id"] == "reading.view_manifest_coverage")
    assert cov["status"] == "fail"
    assert "South_view" in cov["evidence"]["missing_expected_output_ids"]
    assert load_run_manifest(run_dir).accepted("0_reading") is None


def test_merge_extra_stem_is_rejected(tmp_path: Path):
    """Negative example #3 (extra stem)."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    views = _real_views()
    views["bogus_extra_view"] = views["South_view"]
    output.write_text(json.dumps({"views": views}), encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)
    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    cov = next(r for r in checks["results"] if r["check_id"] == "reading.view_manifest_coverage")
    assert cov["status"] == "fail"
    assert "bogus_extra_view" in cov["evidence"]["extra_stems"]
    assert load_run_manifest(run_dir).accepted("0_reading") is None


def test_merge_tampered_image_is_rejected(tmp_path: Path):
    """Negative example #4 (tampered image, after build before merge)."""
    case_dir = _case_copy(tmp_path)
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(case_dir, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    img = case_dir / "case_data" / "1f_view.png"
    data = bytearray(img.read_bytes())
    data[0] ^= 0xFF
    img.write_bytes(bytes(data))

    with pytest.raises(ValueError, match="drift"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_merge_changed_view_manifest_is_rejected(tmp_path: Path):
    """Negative example #5 (the committed view manifest file itself directly
    edited between build and merge)."""
    case_dir = _case_copy(tmp_path)
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(case_dir, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    vm_path = run_dir / "_run" / "view_manifest.json"
    vm = json.loads(vm_path.read_text(encoding="utf-8"))
    vm["content_sha256"] = "0" * 64  # corrupt the self-identity hash directly
    vm_path.write_text(json.dumps(vm), encoding="utf-8")

    with pytest.raises(ValueError, match="drift"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_merge_unbound_preview_workspace_always_rejected(tmp_path: Path):
    """Negative example #6 (a workspace built with no run_dir is never
    merge-eligible — not even into a real, provisioned run)."""
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    provision_view_manifest(CASE_DIR, run_dir)
    staging = _build(tmp_path).staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="merge-eligible"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_merge_built_for_run_a_rejected_into_run_b(tmp_path: Path):
    """Negative example #7: same case, same images, same view manifest — only
    run_id differs (r3's specific A->B example, not just "different case")."""
    case_dir = _case_copy(tmp_path)
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    run_a.mkdir()
    run_b.mkdir()
    provision_view_manifest(case_dir, run_a)
    provision_view_manifest(case_dir, run_b)
    manifest = _formal_build(case_dir, run_a, tmp_path / "staging")  # already provisioned; re-provision is idempotent
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="bound to"):
        merge_isolated_output(staging, run_b, output_path=output)


def test_merge_target_manifest_replaced_after_build_is_rejected(tmp_path: Path):
    """Negative example #8: the target run's manifest is replaced with a
    different (still-v2) identity after the workspace was built."""
    case_dir = _case_copy(tmp_path)
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(case_dir, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    from src.agent.execution.manifest import ensure_run_manifest_v2
    from src.agent.execution.view_manifest import verify_view_manifest

    (run_dir / "_run" / "run_manifest.json").unlink()
    verification = verify_view_manifest(case_dir, run_dir)
    ensure_run_manifest_v2(run_dir, view_manifest_sha256=verification.on_disk.content_sha256)

    with pytest.raises(ValueError, match="identity has changed"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_merge_refuses_grandfathered_v1_run(tmp_path: Path):
    """§5.1/§9 flagged behavior change: a v1 (grandfathered) run — one whose
    run_manifest.json already persists at manifest_version=1 — is read-only for
    new 0_reading attempts; isolation merge must refuse outright, even with a
    workspace built (and hand-wired) against it."""
    case_dir = _case_copy(tmp_path)
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    provision_view_manifest(case_dir, run_dir)
    manifest = build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=tmp_path / "staging")
    staging = manifest.staging_root

    # Simulate a legacy v1 manifest landing on this (already-verified) run dir —
    # e.g. a stale v1 run reused before its formal v2 identity commit. The
    # accepted pointer's real attempt artifacts exist on disk (M0 discipline —
    # CR-03's migration backfill now hard-requires output.json + checks.json).
    attempt_dir = run_dir / "1_correction" / "attempts" / "001"
    attempt_dir.mkdir(parents=True)
    out_text = json.dumps({"legacy": True})
    (attempt_dir / "output.json").write_text(out_text, encoding="utf-8")
    (attempt_dir / "checks.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    v1 = RunManifest(case=case_dir.name)
    v1.accept(StageRecord(stage="1_correction", accepted_attempt=1, output_hash=hash_text(out_text)))
    v1.save(run_dir)

    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="grandfathered"):
        merge_isolated_output(staging, run_dir, output_path=output)

    migrate_run_to_v2(case_dir, run_dir)
    # Post-migration the SAME staging workspace's binding.json run_id predates
    # the migration's freshly generated run_id, so identity re-check (by
    # design — migration always mints a new run_id, §5.1) still refuses; the
    # operator must re-build the isolation workspace against the migrated run.
    with pytest.raises(ValueError, match="identity has changed"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_excluded_input_never_copied_into_staging(tmp_path: Path):
    """Reader-visibility negative example: an image the view manifest
    classifies `excluded_input` never becomes reader-visible — not copied into
    `case_data/`, absent from `input_inventory.json`, logged instead in
    `excluded_from_staging`."""
    case_dir = tmp_path / "synth_case"
    (case_dir / "case_data").mkdir(parents=True)
    (case_dir / "case_data" / "1f_view.png").write_bytes(_tiny_png_bytes())
    (case_dir / "case_data" / "detail_x.png").write_bytes(_tiny_png_bytes())
    (case_dir / "case_data" / "testdata_prompt.json").write_text(
        json.dumps(
            {
                "TestName": "synth_case",
                "Floor plans": [
                    {"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 1}
                ],
                "views": {"detail_x": {"excluded_reason": "non_drawing_asset"}},
            }
        ),
        encoding="utf-8",
    )

    manifest = build_isolation_workspace(case_dir, staging_root=tmp_path / "staging")
    staging = manifest.staging_root

    assert (staging / "case_data" / "1f_view.png").exists()
    assert not (staging / "case_data" / "detail_x.png").exists()
    assert manifest.excluded_from_staging == [
        {"input_id": "detail_x", "source_image": "case_data/detail_x.png", "excluded_reason": "non_drawing_asset"}
    ]
    inventory = json.loads((staging / "input_inventory.json").read_text(encoding="utf-8"))
    assert {e["input_id"] for e in inventory} == {"1f_view"}


def test_feedback_rejects_contamination_tokens():
    with pytest.raises(ValueError):
        check_feedback_text("please compare against gt.json")


# --------------------------------------------------------------------------- #
# F-2 / S1 — worked-example staged at a non-denied path, in MANIFEST, and the
# kickoff pointer agrees with the actual staged file
# --------------------------------------------------------------------------- #
WORKED_EXAMPLE_SOURCE = Path("case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json")
WORKED_EXAMPLE_STAGED = Path("reference/worked_example_plan.json")


def test_build_stages_worked_example_byte_identical_and_in_manifest(tmp_path: Path):
    """S1 positive lock: the kickoff's worked-example is staged at a non-denied
    path, byte-identical to the repo source, and recorded in MANIFEST (the 07-30
    hand-staged copy was absent from MANIFEST, which broke the merge ledger)."""
    from src.agent.execution.isolation import WORKED_EXAMPLE_STAGED as staged_rel

    staging = _build(tmp_path).staging_root

    staged = staging / WORKED_EXAMPLE_STAGED
    assert staged.exists(), "worked-example was not staged"
    assert staged.read_bytes() == WORKED_EXAMPLE_SOURCE.read_bytes(), "staged bytes drifted from source"
    assert staged.read_bytes() == WORKED_EXAMPLE_SOURCE.read_bytes()  # parity with stated rel path
    assert str(staged.relative_to(staging)) == str(staged_rel)

    manifest = json.loads((staging / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = next((e for e in manifest["files"] if e["path"] == str(WORKED_EXAMPLE_STAGED)), None)
    assert entry is not None, "worked-example missing from MANIFEST"
    assert entry["category"] == "reference"
    assert entry["source_path"] == str(WORKED_EXAMPLE_SOURCE)
    assert entry["sha256"] == hash_file(staged)


def test_build_kickoff_points_at_staged_worked_example_path(tmp_path: Path):
    """S1 consistency lock: the worked-example path named in the staged kickoff
    text actually exists in staging — a real stat, not a hardcoded string compare,
    so a 'kickoff says A, file at B' second-order drift cannot pass."""
    staging = _build(tmp_path).staging_root
    kickoff = (staging / "skills/intake_pipeline/0_reading/session_kickoff.md").read_text(encoding="utf-8")
    assert str(WORKED_EXAMPLE_SOURCE) not in kickoff, "kickoff still names the denied repo path"
    assert str(WORKED_EXAMPLE_STAGED) in kickoff
    # Real stat of the path the kickoff actually names:
    assert (staging / WORKED_EXAMPLE_STAGED).exists()
    # The denied repo path the kickoff used to name must NOT be reader-reachable:
    assert not (staging / "case_tests").exists()


def test_worked_example_staged_path_is_not_guard_denied(tmp_path: Path):
    """The staged worked-example path trips no DENY_TOKEN, so a Read of it is
    allowed by the guard (the reader is sent there by the kickoff)."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(
        staging,
        {
            "tool_name": "Read",
            "tool_input": {"file_path": str(staging / WORKED_EXAMPLE_STAGED)},
        },
    )
    assert proc.returncode == 0, proc.stderr


# --------------------------------------------------------------------------- #
# F-4 / K / S2 — guard: tighten write protection (out/ + requests/ only) AND
# relax prose scanning (path-like checks only on path-looking strings). Net
# effect is a stricter guard with better usability. Both halves are required.
# --------------------------------------------------------------------------- #
def test_build_precreates_requests_dir_and_kickoff_mentions_it(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    assert (staging / "requests").is_dir()
    kickoff = (staging / "kickoff_prompt.md").read_text(encoding="utf-8")
    assert "requests/" in kickoff and "out/" in kickoff
    settings = json.loads((staging / "isolation_settings.json").read_text(encoding="utf-8"))
    allow = settings["permissions"]["allow"]
    assert any("requests" in entry and entry.startswith("Write") for entry in allow)


@pytest.mark.parametrize(
    "target",
    [
        "tools/run_cv_probe.py",
        "tools/cv_probe.py",
        "guard.py",
        "isolation_settings.json",
        "MANIFEST.json",
        "binding.json",
        "skills/intake_pipeline/0_reading/guide.md",
        "src/agent/reading/cv_toolbox/tools.py",
        "case_data/1f_view.png",
        "prescan/cv_evidence/1f_view/prescan/candidates.json",
        "reference/worked_example_plan.json",
        "stray_root_file.txt",  # directly at staging root
    ],
)
def test_guard_denies_write_outside_out_or_requests(tmp_path: Path, target: str):
    """S2a negative locks: every sensitive location is denied to write tools."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": target, "content": "# replaced"}},
    )
    assert proc.returncode == 2, (target, proc.stderr)
    assert "out/" in proc.stderr and "requests/" in proc.stderr


def test_guard_denies_overwrite_of_tools_run_cv_probe(tmp_path: Path):
    """S2a / K negative lock: the F-4/K escape — overwriting the one
    Bash-allowlisted executable then running arbitrary code — must be closed.
    (This was `allow` before this batch; the explicit, headline new lock.)"""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": "tools/run_cv_probe.py", "content": "# replaced"}},
    )
    assert proc.returncode == 2
    assert "out/" in proc.stderr and "requests/" in proc.stderr


@pytest.mark.parametrize(
    "target",
    [
        "out/reading_summary.md",
        "out/sub/1f_view.json",
        "requests/probe.json",
        "requests/sub/x.json",
    ],
)
def test_guard_allows_write_under_out_or_requests(tmp_path: Path, target: str):
    """S2a positive: legitimate write targets under out/ or requests/ are allowed."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": target, "content": "ok"}},
    )
    assert proc.returncode == 0, (target, proc.stderr)


def test_guard_allows_reading_summary_with_prose_forbidden_tokens(tmp_path: Path):
    """S2b usability positive (the F-4 fix): a reading summary whose PROSE uses
    '~' (约等号), the domain term 'grade line' (室外地坪线), '..', and a semicolon
    is allowed — these are not paths. Before this batch this was denied 3x."""
    staging = _build(tmp_path).staging_root
    content = "Grade line (室外地坪线) at ~0.000; the .. range and ; semicolons are fine in prose"
    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": "out/reading_summary.md", "content": content}},
    )
    assert proc.returncode == 0, proc.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow"


def test_guard_r1_allows_reading_summary_content_with_slash_and_grade_line(tmp_path: Path):
    """S2b r1 (F-4 fix on realistic content) — controller live-probe case. The
    original S2b `_looks_like_path` judged the WHOLE string, so any content
    containing '/' (a date like 2026/07/31, m/s, N/A) was treated as a path and
    scanned for DENY_TOKENS — the domain term 'grade line' was then denied and
    the required summary could not be written. r1 judges by PARAMETER ROLE: a
    content-role parameter is excluded from the scan entirely. This is lock 1."""
    staging = _build(tmp_path).staging_root
    content = "Windows on 2026/07/31: grade line at z=0, span 1.2 m."
    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": "out/reading_summary.md", "content": content}},
    )
    assert proc.returncode == 0, proc.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow"


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        (
            "write_content",
            {"tool_name": "Write", "tool_input": {"file_path": "out/reading_summary.md",
                "content": "Windows on 2026/07/31: grade line at z=0, span 1.2 m."}},
        ),
        (
            "edit_old_string",
            {"tool_name": "Edit", "tool_input": {"file_path": "out/reading_summary.md",
                "old_string": "ratio 3/4 by the grade line", "new_string": "fixed"}},
        ),
        (
            "edit_new_string",
            {"tool_name": "Edit", "tool_input": {"file_path": "out/reading_summary.md",
                "old_string": "fixed", "new_string": "Windows on 2026/07/31: grade line at z=0"}},
        ),
        (
            "multiedit_edits",
            {"tool_name": "MultiEdit", "tool_input": {"file_path": "out/reading_summary.md",
                "edits": [
                    {"old_string": "grade line at 3/4", "new_string": "Windows on 2026/07/31"},
                    {"old_string": "wind 1.2 m/s", "new_string": "case_tests is just prose here"},
                ]}},
        ),
        (
            "notebookedit_new_source",
            {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "requests/nb.ipynb",
                "cell_id": "c1", "cell_type": "code", "edit_mode": "replace",
                "new_source": "Windows on 2026/07/31: grade line; case_tests mention"}},
        ),
    ],
)
def test_guard_r1_excludes_content_role_params_from_path_scan(tmp_path: Path, label: str, payload: dict):
    """S2b r1 — PARAMETER ROLE lock. Every content-role parameter name
    (content / old_string / new_string / MultiEdit edits[] / NotebookEdit
    new_source) is excluded from the path-token scan entirely. Each payload's
    text body contains both a '/' and a DENY_TOKEN ('grade' / 'case_tests'),
    which the original whole-string `_looks_like_path` would have caught — they
    must now all ALLOW. Proves the exclusion is by key name across tools, not a
    one-off `content` special case."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(staging, payload)
    assert proc.returncode == 0, (label, proc.stderr)
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow", label


def test_guard_r1_denies_write_to_tools_with_innocent_prose_content(tmp_path: Path):
    """S2b r1 — lock 2 (write protection survives the body-scan loosening).
    Loosening the *content* scan must NOT loosen the *write-target* protection.
    A Write to tools/run_cv_probe.py is still DENIED even though its content is
    perfectly innocent prose (no '/', no DENY_TOKEN) — proves we relaxed the body
    scan, not the write protection (S2a `_check_write_target` still governs)."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": "tools/run_cv_probe.py",
            "content": "innocent prose with no forbidden tokens or slashes here"}},
    )
    assert proc.returncode == 2, proc.stderr
    assert "write target must be under out/ or requests/" in proc.stderr


def test_guard_r1_bash_command_with_case_tests_still_denied(tmp_path: Path):
    """S2b r1 — lock 3 (Bash unchanged). The Bash `command` still goes through
    the full strict whole-string check; the content-role relaxation never touches
    the Bash path. A command containing `case_tests` is still DENIED — even an
    otherwise-read-only `ls` is denied because the lexical token check fires
    first on the whole string."""
    staging = _build(tmp_path).staging_root
    proc = _hook(staging, "ls case_tests/x")
    assert proc.returncode == 2, proc.stderr
    assert "forbidden token: case_tests" in proc.stderr


# --------------------------------------------------------------------------- #
# R2-1 — the parameter-role classifier is a TOTAL function. r1 kept
# `_looks_like_path` as a pre-gate for every non-content string, so a bare,
# slash-less, extension-less value slipped past the checks even when its key was
# explicitly `file_path`. Bare `case_tests` regressed DENY -> ALLOW against the
# pre-batch commit; the r1 fixture only ever used `case_tests/x`, so the lock was
# green purely because of the fixture's SHAPE. These locks pin both shapes side
# by side and pin the fail-closed default for unknown keys.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value", ["case_tests", "case_tests/x"])
def test_guard_r2_bare_and_slashed_forbidden_path_both_denied(tmp_path: Path, value: str):
    """R2-1 lock 1: a DENY_TOKEN in a path-role parameter is denied whether or
    not the value happens to contain a '/'. The bare form is the regression the
    controller reproduced (DENY at f98d248 -> ALLOW at r1)."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(staging, {"tool_name": "Read", "tool_input": {"file_path": value}})
    assert proc.returncode == 2, (value, proc.stdout, proc.stderr)
    assert "forbidden token: case_tests" in proc.stderr


@pytest.mark.parametrize("value", ["escape", "./escape"])
def test_guard_r2_bare_extensionless_escaping_symlink_denied(tmp_path: Path, value: str):
    """R2-1 lock 2: a top-level symlink out of staging is denied even when the
    parameter value is bare and extension-less. Under r1 only `./escape` was
    denied (it starts with '.'), so the symlink property depended on string
    surface shape rather than on the parameter being a path."""
    staging = _build(tmp_path).staging_root
    (staging / "escape").symlink_to("/etc/passwd")
    proc = _hook_payload(staging, {"tool_name": "Read", "tool_input": {"file_path": value}})
    assert proc.returncode == 2, (value, proc.stdout, proc.stderr)
    assert "escapes staging" in proc.stderr


@pytest.mark.parametrize(
    ("label", "tool_input"),
    [
        ("unknown_key_bare_deny_token", {"mystery_param": "case_tests"}),
        ("unknown_key_bare_escaping_symlink", {"mystery_param": "escape"}),
        ("unknown_nested_key_bare_deny_token", {"opts": {"deeply": {"nested": "case_tests"}}}),
    ],
)
def test_guard_r2_unknown_key_defaults_to_path_role(tmp_path: Path, label: str, tool_input: dict):
    """R2-1 lock 3: an unknown/unanticipated key is treated as a path role
    (fail-closed default), so a future tool parameter cannot reopen this hole in
    a fourth shape. All three payloads use bare, slash-less values that r1's
    `_looks_like_path` pre-gate would have skipped entirely."""
    staging = _build(tmp_path).staging_root
    (staging / "escape").symlink_to("/etc/passwd")
    proc = _hook_payload(staging, {"tool_name": "Read", "tool_input": tool_input})
    assert proc.returncode == 2, (label, proc.stdout, proc.stderr)


def test_guard_r2_param_role_is_total_over_keys():
    """R2-1 structural lock: `_param_role` is total — exactly two outcomes, and
    every key that is not a declared content-role key (including `None`, the
    key-less leaf) resolves to the checked side. Supplements, does not replace,
    the live locks above."""
    sys.path.insert(0, str(Path("src/agent/execution/isolation_templates").resolve()))
    try:
        import guard as guard_mod  # the very file that is copied into staging
    finally:
        sys.path.pop(0)
    roles = {guard_mod._param_role(k) for k in guard_mod.CONTENT_ROLE_KEYS}
    assert roles == {"content"}
    for key in (*guard_mod.PATH_ROLE_KEYS, None, "", "mystery_param", "edits", "cell_id"):
        assert guard_mod._param_role(key) == "path", key


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("read_gt_json", {"tool_name": "Read", "tool_input": {"file_path": "case_tests/test_baseline/gt/x/gt.json"}}),
        ("read_case_tests", {"tool_name": "Read", "tool_input": {"file_path": "case_tests/e2e_tests/sm21_anchor/case_data/1f_view.png"}}),
        ("abs_outside", {"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}}),
        ("non_allowlisted_cmd", {"tool_name": "Bash", "tool_input": {"command": "rm -rf out"}}),
        ("python_c", {"tool_name": "Bash", "tool_input": {"command": "python -c 'print(1)'"}}),
        ("compound_token", {"tool_name": "Bash", "tool_input": {"command": "ls; whoami"}}),
    ],
)
def test_guard_security_properties_stay_denied(tmp_path: Path, label: str, payload: dict):
    """S2b regression locks: six of the eight required security properties stay
    red->deny through the prose-scan relaxation. (Property 4 symlink escape and
    property 8 request-file forbidden token have dedicated tests below.)"""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(staging, payload)
    assert proc.returncode == 2, (label, proc.stderr)


def test_guard_denies_read_of_symlink_escaping_staging(tmp_path: Path):
    """S2b regression lock (property 4, non-Bash side): a Read of a symlink whose
    target escapes staging is denied even though the path itself looks in-bounds."""
    staging = _build(tmp_path).staging_root
    outside = tmp_path / "outside_secret.png"
    outside.write_bytes((staging / "case_data/1f_view.png").read_bytes())
    (staging / "case_data/escape.png").symlink_to(outside)
    proc = _hook_payload(
        staging,
        {"tool_name": "Read", "tool_input": {"file_path": "case_data/escape.png"}},
    )
    assert proc.returncode == 2


# --------------------------------------------------------------------------- #
# R2-2 — the one helper the guard lets the reader execute writes wherever the
# request's `out_dir` points. Before this item, both the hook and the wrapper
# only required "somewhere inside staging", so `{"out_dir": "tools"}` was allowed
# and the helper really created three files under `tools/**`. Output-role
# parameters must now resolve into the writable root, enforced in BOTH places,
# and the E2E locks below actually run the helper and diff the staging tree.
# --------------------------------------------------------------------------- #
_E2E_WRITABLE_PREFIXES = ("out/", "requests/")
# Explicit, named exemptions — never a silent ignore:
_E2E_EXEMPT_NAMES = ("access_log.jsonl",)  # the guard's own append-only audit log
_E2E_EXEMPT_PARTS = ("__pycache__",)  # interpreter byte-cache of the staged tools


def _staging_snapshot(root: Path) -> dict[str, str]:
    """content hash of every regular file in the staging tree."""
    return {
        p.relative_to(root).as_posix(): hash_file(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and not p.is_symlink()
    }


def _protected_tree_diff(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Files added or rewritten OUTSIDE out/ and requests/, excluding the two
    named exemptions above."""
    changed = []
    for rel, digest in after.items():
        if before.get(rel) == digest:
            continue
        if rel.startswith(_E2E_WRITABLE_PREFIXES):
            continue
        parts = Path(rel).parts
        if parts[-1] in _E2E_EXEMPT_NAMES or any(p in _E2E_EXEMPT_PARTS for p in parts):
            continue
        changed.append(rel)
    return sorted(changed)


def _run_helper(staging: Path, request_rel: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", "--request", request_rel],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "out_dir",
    [
        "tools",  # the reproduced escape: overwrite-adjacent to the one allowlisted exe
        "tools/cv_evidence",
        "requests/evidence",  # requests/ carries the request file, never helper output
        "prescan",
        "reference",
        "case_data",
        ".",  # staging root
    ],
)
def test_guard_denies_request_output_dir_outside_writable_root(tmp_path: Path, out_dir: str):
    """R2-2 hook side: an output-role parameter that resolves anywhere but the
    writable root is refused before the helper is ever started."""
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": out_dir, "bbox": "0,0,20,20"}},
        name="requests/probe.json",
    )
    proc = _hook(staging, "python tools/run_cv_probe.py --request requests/probe.json")
    assert proc.returncode == 2, (out_dir, proc.stdout, proc.stderr)


def test_e2e_request_writing_outside_out_is_refused_and_tree_is_unchanged(tmp_path: Path):
    """R2-2 core lock — real E2E. Uses the exact request the reviewer used to
    land three files under `tools/**`: the hook must refuse it, the wrapper must
    refuse it independently (no guard/wrapper policy gap), and a before/after
    hash diff of the WHOLE staging tree must show zero additions and zero
    rewrites outside out/ and requests/."""
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": "tools", "bbox": "0,0,20,20"}},
        name="requests/write_tools.json",
    )
    before = _staging_snapshot(staging)

    hook = _hook(staging, "python tools/run_cv_probe.py --request requests/write_tools.json")
    assert hook.returncode == 2, hook.stderr
    assert "out/" in hook.stderr

    # Independently of the hook, the wrapper itself must refuse the same request.
    helper = _run_helper(staging, "requests/write_tools.json")
    assert helper.returncode != 0, helper.stdout
    assert "out/" in (helper.stderr + helper.stdout)

    after = _staging_snapshot(staging)
    assert _protected_tree_diff(before, after) == []
    assert not (staging / "tools" / "cv_evidence").exists()


def test_e2e_allowed_request_writes_only_under_out(tmp_path: Path):
    """R2-2 companion lock: the same machinery on a LEGAL request. The hook
    allows it, the helper really runs and really writes, new files appear under
    out/ — which is what proves the tree diff above is not vacuous — and nothing
    outside out/ / requests/ is added or rewritten."""
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": "out/cv", "bbox": "0,0,20,20"}},
        name="requests/probe.json",
    )
    before = _staging_snapshot(staging)

    hook = _hook(staging, "python tools/run_cv_probe.py --request requests/probe.json")
    assert hook.returncode == 0, hook.stderr

    helper = _run_helper(staging, "requests/probe.json")
    assert helper.returncode == 0, helper.stderr

    after = _staging_snapshot(staging)
    produced = sorted(rel for rel in after if rel not in before and rel.startswith("out/"))
    assert produced, "the helper wrote nothing under out/ — the diff would be vacuous"
    assert _protected_tree_diff(before, after) == []


# --------------------------------------------------------------------------- #
# R2-3 — a writable root that is ITSELF a symlink used to reverse-authorize its
# target: `(root/"out").resolve()` yielded `tools`, so `tools/**` became an
# allowed root and `Write out/run_cv_probe.py` was allowed. The roots are now
# pinned to real directories that resolve to themselves.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("root_name", ["out", "requests"])
def test_guard_denies_writes_when_an_allowed_root_is_a_symlink(tmp_path: Path, root_name: str):
    """R2-3 lock: with `<root_name> -> tools` pre-seeded, the supported explicit
    `--staging-root` build still succeeds, but the guard must refuse — writing
    "under out/" would really land in the protected `tools/`."""
    staging_root = tmp_path / "staging"
    staging_root.mkdir()
    (staging_root / "tools").mkdir()
    (staging_root / root_name).symlink_to("tools")

    staging = build_isolation_workspace(CASE_DIR, staging_root=staging_root).staging_root
    assert (staging / root_name).is_symlink(), "fixture precondition: the root stayed a symlink"
    assert (staging / root_name / "run_cv_probe.py").resolve() == (
        staging / "tools" / "run_cv_probe.py"
    ).resolve()

    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": f"{root_name}/run_cv_probe.py", "content": "overwrite"}},
    )
    assert proc.returncode == 2, proc.stdout
    assert "real directory" in proc.stderr

    # fail-closed: while the authorization set is untrustworthy, even a read is refused
    proc = _hook_payload(staging, {"tool_name": "Read", "tool_input": {"file_path": "case_data/1f_view.png"}})
    assert proc.returncode == 2, proc.stdout


def test_guard_denies_writes_when_allowed_root_symlinked_after_build(tmp_path: Path):
    """R2-3 companion: the same refusal when the root is swapped for a symlink
    *after* a normal build, i.e. the check is re-run per decision rather than
    once at build time."""
    staging = _build(tmp_path).staging_root
    shutil.rmtree(staging / "out")
    (staging / "out").symlink_to("tools")

    proc = _hook_payload(
        staging,
        {"tool_name": "Write", "tool_input": {"file_path": "out/run_cv_probe.py", "content": "overwrite"}},
    )
    assert proc.returncode == 2, proc.stdout
    assert "real directory" in proc.stderr


def test_guard_denies_bash_request_file_with_forbidden_token(tmp_path: Path):
    """S2b regression lock (property 8): a CV-probe request JSON whose value
    contains a DENY_TOKEN is denied — `_validate_request_file` keeps the strict
    scan (unchanged by the prose relaxation)."""
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": "out/cv", "bbox": "0,0,20,20", "note": "see grade line"}},
        name="requests/req.json",
    )
    proc = _hook(staging, "python tools/run_cv_probe.py --request requests/req.json")
    assert proc.returncode == 2


# --------------------------------------------------------------------------- #
# F-5 / S4 — merge auto-assembles per-image <expected_output_id>.json files
# (the kickoff tells the reader to write one JSON per drawing; merge used to
# require a single aggregate nobody produced). Pure mechanical搬运; fail-closed
# on missing/extra; the single-aggregate old path still works.
# --------------------------------------------------------------------------- #
def _formal_sm21(tmp_path: Path):
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    return _formal_build(CASE_DIR, run_dir, tmp_path / "staging"), run_dir


def _write_per_image_views(staging: Path, views: dict) -> None:
    for eid, view in views.items():
        (staging / "out" / f"{eid}.json").write_text(json.dumps(view), encoding="utf-8")


def test_merge_assembles_per_image_views_byte_equal_and_accepts(tmp_path: Path):
    """S4 positive lock: with no aggregate, merge assembles the per-image
    <expected_output_id>.json files; each view is json.loads of its source
    (zero content change) and the result is accepted like the old aggregate."""
    manifest, run_dir = _formal_sm21(tmp_path)
    staging = manifest.staging_root
    real = _real_views()
    _write_per_image_views(staging, real)
    assert not (staging / "out" / "output.json").exists()

    attempt_dir = merge_isolated_output(staging, run_dir)  # default output.json absent -> assemble

    assembled = json.loads((attempt_dir / "output.json").read_text(encoding="utf-8"))
    assert set(assembled["views"]) == set(real)
    # zero content change: each assembled view == json.loads of its source file
    for eid, view in real.items():
        source_loaded = json.loads((staging / "out" / f"{eid}.json").read_text(encoding="utf-8"))
        assert assembled["views"][eid] == source_loaded
        assert assembled["views"][eid] == view
    # accepted on the real gate①-clean views
    rec = load_run_manifest(run_dir).accepted("0_reading")
    assert rec is not None
    assert rec.artifact_contract == "reading_isolated_v2"
    assert rec.output_hash == hash_text((attempt_dir / "output.json").read_text(encoding="utf-8"))


def test_merge_per_image_missing_is_rejected(tmp_path: Path):
    """S4 fail-closed: a manifest expected_output_id with no per-image file is a
    loud error (no silent empty-fill, no partial attempt written)."""
    manifest, run_dir = _formal_sm21(tmp_path)
    staging = manifest.staging_root
    real = _real_views()
    ids = sorted(real)
    for eid in ids[:-1]:  # omit exactly one expected id
        (staging / "out" / f"{eid}.json").write_text(json.dumps(real[eid]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        merge_isolated_output(staging, run_dir)
    # no attempt was filed
    assert not (run_dir / "0_reading" / "attempts").exists() or not list((run_dir / "0_reading" / "attempts").iterdir())


def test_merge_per_image_extra_is_rejected(tmp_path: Path):
    """S4 fail-closed: a *_view.json not declared in the manifest is a loud error."""
    manifest, run_dir = _formal_sm21(tmp_path)
    staging = manifest.staging_root
    real = _real_views()
    _write_per_image_views(staging, real)
    (staging / "out" / "rogue_view.json").write_text(json.dumps(real[sorted(real)[0]]), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        merge_isolated_output(staging, run_dir)


def test_merge_single_aggregate_still_accepted_alongside_per_image(tmp_path: Path):
    """S4: the old path is not broken — when a valid aggregate output.json is
    present it is used (per-image files, if any, are ignored, not assembled)."""
    manifest, run_dir = _formal_sm21(tmp_path)
    staging = manifest.staging_root
    real = _real_views()
    payload = json.dumps({"views": real})
    (staging / "out" / "output.json").write_text(payload, encoding="utf-8")
    _write_per_image_views(staging, real)  # also present; aggregate must win

    attempt_dir = merge_isolated_output(staging, run_dir)
    # the attempt's output.json is the aggregate bytes verbatim (not re-dumped)
    assert (attempt_dir / "output.json").read_text(encoding="utf-8") == payload
