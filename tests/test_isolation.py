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
