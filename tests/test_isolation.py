from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.execution import isolation
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
    prescan_files = {
        "candidates.json",
        "structural_candidates.json",
        "cc_box_candidates.json",
        "tick_candidates.json",
        "combined_overlay.png",
        "all_candidates_overlay.png",
        "cc_box_overlay.png",
        "tick_overlay.png",
    }
    for name in prescan_files:
        (src / name).write_bytes(name.encode("utf-8"))

    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root

    copied_root = staging / "prescan" / "cv_evidence" / "1f_view" / "prescan"
    assert {path.name for path in copied_root.iterdir()} == prescan_files
    for name in prescan_files:
        assert (copied_root / name).read_bytes() == (src / name).read_bytes()
    kickoff = (staging / "kickoff_prompt.md").read_text(encoding="utf-8")
    assert "prescan/cv_evidence/<image_stem>/prescan/" in kickoff
    prescan_line = next(
        line for line in kickoff.splitlines() if line.startswith("Deterministic prescan candidates")
    )
    named_files = set(re.findall(r"`([^`]+\.(?:json|png))`", prescan_line))
    assert named_files, "no prescan artifacts were parsed from the generated kickoff"
    assert named_files == prescan_files
    assert "`combined_overlay.png` (structural-only)" in prescan_line
    assert "`candidates.json` (all candidates)" in prescan_line
    assert "Nothing is dropped" in prescan_line


_KICKOFF_PROBE_FORMS_RE = re.compile(
    r"The normal probe form is `(?P<direct>[^`]+)`; use "
    r"`(?P<batch>[^`]+)` for sweeps \(maximum (?P<limit>\d+) requests, "
    r"all validated before any run\)\. The legacy `(?P<request>[^`]+)` "
    r"form is also available\."
)


def test_build_kickoff_probe_forms_match_live_guard(tmp_path: Path):
    """The command shapes parsed from the generated kickoff are real guard
    inputs, not test-side copies of what the kickoff was meant to say.

    Each parsed template is materialized into a legal command and submitted to
    the staged production guard.  The batch limit is likewise parsed from the
    prose, checked against the live guard constant, and exercised at both sides
    of the boundary so neither the prose parse nor the mechanism check can be
    vacuous.
    """
    staging = _build(tmp_path).staging_root
    kickoff = (staging / "kickoff_prompt.md").read_text(encoding="utf-8")
    match = _KICKOFF_PROBE_FORMS_RE.search(kickoff)
    assert match is not None, "generated kickoff no longer exposes all three probe forms"

    direct = (
        match.group("direct")
        .replace("<tool>", "crop_zoom")
        .replace("<path>", "case_data/1f_view.png")
        .replace("out/<name>", "out/kickoff_direct")
        .replace("[--<key> <value> ...]", "--bbox 0,0,20,20")
    )
    request = match.group("request").replace("<name>", "kickoff_request")
    batch = match.group("batch").replace("<name>", "kickoff_batch")
    assert all("<" not in command and ">" not in command for command in (direct, request, batch))

    request_payload = {
        "tool": "crop_zoom",
        "args": {
            "image": "case_data/1f_view.png",
            "out_dir": "out/kickoff_request",
            "bbox": "0,0,20,20",
        },
    }
    _request(staging, request_payload, name="requests/kickoff_request.json")
    batch_entry = {"id": "probe_001", **request_payload}
    _request(staging, {"requests": [batch_entry]}, name="requests/kickoff_batch.json")

    expected_reasons = {
        direct: "allowed run_cv_probe direct arguments",
        batch: "allowed run_cv_probe batch",
        request: "allowed run_cv_probe request",
    }
    assert len(expected_reasons) == 3, "parsed kickoff forms unexpectedly collapsed together"
    for command, expected_reason in expected_reasons.items():
        proc = _hook(staging, command)
        assert proc.returncode == 0, (command, proc.stdout, proc.stderr)
        log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        assert log["reason"] == expected_reason

    stated_limit = int(match.group("limit"))
    guard_limit = _guard_module().MAX_PROBE_BATCH_SIZE
    assert stated_limit == guard_limit
    at_limit = [{"id": f"probe_{i:03d}", **request_payload} for i in range(stated_limit)]
    _request(staging, {"requests": at_limit}, name="requests/kickoff_batch.json")
    assert _hook(staging, batch).returncode == 0

    over_limit = at_limit + [{"id": "probe_over_limit", **request_payload}]
    _request(staging, {"requests": over_limit}, name="requests/kickoff_batch.json")
    denied = _hook(staging, batch)
    assert denied.returncode == 2, (denied.stdout, denied.stderr)
    assert f"maximum is {stated_limit}" in denied.stderr


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
    directive.write_text(
        "Measure before drawing. Treat the exterior grade line as interior floor ±0.000.\n",
        encoding="utf-8",
    )

    cmd = spawn_command(staging, directive=directive)
    prompt = cmd[2]
    assert prompt.startswith("KICKOFF")
    assert "Per-run directive" in prompt
    assert "Measure before drawing" in prompt
    assert "exterior grade line" in prompt
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

    # P1-1: the same escape spelled as a BARE, extension-less name. Before the
    # shared validator classified path-role parameters by NAME, this value was
    # handed to `_looks_like_path`, which does not recognize `escape` as a path,
    # so it never reached `_path_arg` at all — the R2-1 hole, surviving in the
    # request JSON. Both invocation forms now go through one rule.
    (staging / "escape").symlink_to(outside)
    _request(staging, {"tool": "crop_zoom", "args": {"image": "escape", "out_dir": "out/cv"}}, "bare_request.json")
    proc = _hook(staging, "python tools/run_cv_probe.py --request bare_request.json")
    assert proc.returncode == 2, proc.stdout


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


def test_formal_scope_stages_only_declared_images_and_records_out_of_scope_views(tmp_path: Path):
    """W4: scope is fixed before build; missing an in-scope view still blocks."""
    import shutil

    case_dir = tmp_path / "sm24_copy"
    shutil.copytree("case_tests/e2e_tests/sm24_anchor", case_dir)
    run_dir = tmp_path / "scope_run"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text(
        "reading_exam_scope:\n"
        "  input_ids: [1f_view, South_view]\n"
        "  reason: focused reading exam\n",
        encoding="utf-8",
    )
    provision_view_manifest(case_dir, run_dir)

    workspace = build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=tmp_path / "staging")
    staged_images = sorted(path.name for path in (workspace.staging_root / "case_data").glob("*.png"))
    inventory = json.loads((workspace.staging_root / "input_inventory.json").read_text(encoding="utf-8"))
    binding = json.loads((workspace.staging_root / "binding.json").read_text(encoding="utf-8"))

    assert staged_images == ["1f_view.png", "South_view.png"]
    assert [item["input_id"] for item in inventory] == ["1f_view", "South_view"]
    assert binding["reading_exam_scope_input_ids"] == ["1f_view", "South_view"]
    assert binding["reading_exam_scope_sha256"]

    output = workspace.staging_root / "out/output.json"
    output.write_text(json.dumps({"views": {"1f_view": _real_views()["1f_view"]}}), encoding="utf-8")
    attempt_dir = merge_isolated_output(workspace.staging_root, run_dir, output_path=output)
    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))["results"]
    coverage = next(row for row in checks if row["check_id"] == "reading.view_manifest_coverage")
    assert coverage["status"] == "fail"
    assert coverage["evidence"]["missing_expected_output_ids"] == ["South_view"]
    out_of_scope = [row for row in checks if ".out_of_scope." in row["check_id"]]
    assert {row["evidence"]["input_id"] for row in out_of_scope} == {"East_view", "North_view", "West_view"}
    assert all(row["status"] == "not_applicable" for row in out_of_scope)
    assert all(row["evidence"]["source"] == "run_config.yaml:reading_exam_scope" for row in out_of_scope)


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


FEEDBACK_REFUSAL_CASES = (
    ("token", "gt.json", "please compare against gt.json"),
    ("token", "test_baseline", "open test_baseline for the answer"),
    ("token", "case_tests", "inspect case_tests before revising"),
    (
        "token",
        "/workspaces/energyplus-agent-dev",
        "read /workspaces/EnergyPlus-Agent-dev/private-result.json",
    ),
    ("token", "attempts/", "copy the accepted attempts/003/output.json"),
    ("token", "judge.json", "use judge.json as your source"),
    ("token", "judge_rubric.md", "follow judge_rubric.md"),
    ("token", "verdict", "the verdict says this answer is wrong"),
    ("pattern", "grade artifact filename", "compare against grade.png"),
    ("pattern", "grade path segment", "read private/grade/result.txt"),
    ("pattern", "stage grade artifact", "open report/0_reading_grade.png"),
    ("pattern", "grade artifact field", 'the packet says "grade": "result.png"'),
    ("pattern", "grade sidecar field", "copy grade_png_sha256 from the score sidecar"),
    ("pattern", "report grade field", "use the reading_grade report asset"),
)


def test_feedback_allows_architectural_grade_prose():
    check_feedback_text(
        "Treat the exterior grade line as interior floor ±0.000. "
        "Describe below-grade walls and ordinary drawing evidence plainly."
    )


@pytest.mark.parametrize("kind, reason, text", FEEDBACK_REFUSAL_CASES)
def test_feedback_rejects_every_contamination_token(kind: str, reason: str, text: str):
    message = f"feedback contains forbidden {kind}: {reason}"
    with pytest.raises(ValueError, match=re.escape(message)):
        check_feedback_text(text)


@pytest.mark.parametrize("kind, reason, text", FEEDBACK_REFUSAL_CASES)
def test_feedback_refusal_fixtures_are_neuter_clean(
    monkeypatch: pytest.MonkeyPatch, kind: str, reason: str, text: str
):
    """Each refusal fixture passes when only its intended protection is removed."""
    if kind == "token":
        monkeypatch.setattr(
            isolation,
            "FEEDBACK_FORBIDDEN_SUBSTRINGS",
            tuple(token for token in isolation.FEEDBACK_FORBIDDEN_SUBSTRINGS if token != reason),
        )
    else:
        monkeypatch.setattr(
            isolation,
            "FEEDBACK_FORBIDDEN_PATTERNS",
            tuple(
                item for item in isolation.FEEDBACK_FORBIDDEN_PATTERNS if item[0] != reason
            ),
        )
    check_feedback_text(text)


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


_KICKOFF_POINTER_RE = re.compile(r"Canonical worked-example file:\s*`([^`]+)`")


def test_build_kickoff_points_at_staged_worked_example_path(tmp_path: Path):
    """S1 consistency lock (R2-4 rebuild). The previous version asserted
    `str(WORKED_EXAMPLE_STAGED) in kickoff` and stat'd `staging /
    WORKED_EXAMPLE_STAGED` — both against the test's own constant, so pointing
    the kickoff at `<staged>.missing` left it green (the constant is a substring
    of the broken pointer, and the stat never saw the broken pointer at all).

    This version PARSES the path the kickoff actually names out of its syntactic
    slot and stats *that*, so a pointer-only drift is caught."""
    staging = _build(tmp_path).staging_root
    kickoff = (staging / "skills/intake_pipeline/0_reading/session_kickoff.md").read_text(encoding="utf-8")
    assert str(WORKED_EXAMPLE_SOURCE) not in kickoff, "kickoff still names the denied repo path"

    match = _KICKOFF_POINTER_RE.search(kickoff)
    assert match is not None, "kickoff no longer names a canonical worked-example file"
    named = match.group(1)
    # The file the kickoff names must really be there — stat the PARSED path.
    assert (staging / named).is_file(), f"kickoff names {named!r}, which does not exist in staging"
    # ...and it must be the staged copy, byte-identical to the repo source.
    assert (staging / named).read_bytes() == WORKED_EXAMPLE_SOURCE.read_bytes()
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


def _guard_module():
    """Import the very guard.py file that is copied into staging."""
    sys.path.insert(0, str(Path("src/agent/execution/isolation_templates").resolve()))
    try:
        import guard as guard_mod

        return guard_mod
    finally:
        sys.path.pop(0)


def test_guard_r2_param_role_is_total_over_keys():
    """R2-1 structural lock: `_param_role` is total — exactly two outcomes, and
    every key that is not a declared free-text key (including `None`, the
    key-less leaf) resolves to the checked side. Supplements, does not replace,
    the live locks above.

    R3-3 NIT-1: the first assertion used to be `{_param_role(k) for k in
    CONTENT_ROLE_KEYS} == {"content"}`, which is true under *any* implementation
    of `_param_role` because the implementation is literally "is the key in that
    tuple" — a tautology. The exempt names are now spelled out as literals, so
    dropping one from the production tuple turns this test red.
    """
    guard_mod = _guard_module()
    for key in (
        "content",
        "old_string",
        "new_string",
        "new_source",
        "activeForm",
        "description",
        "prompt",
        "query",
    ):
        assert guard_mod._param_role(key, "Write") == "content", key
    # tool-scoped: the same name is free text for one tool and a path for another
    assert guard_mod._param_role("pattern", "Grep") == "content"
    assert guard_mod._param_role("pattern", "Glob") == "path"
    assert guard_mod._param_role("pattern", "") == "path"
    # never exempt, whatever else moves
    assert guard_mod._param_role("command", "Bash") == "path"
    assert guard_mod._param_role("file_path", "Write") == "path"
    for key in (*guard_mod.PATH_ROLE_KEYS, None, "", "mystery_param", "edits", "cell_id"):
        assert guard_mod._param_role(key, "Read") == "path", key


# --------------------------------------------------------------------------- #
# R3-1 — the r2 fail-closed default was correct but the exempt table only listed
# Write/Edit text bodies, so the F-4 friction this whole batch exists to remove
# simply MOVED: `TodoWrite {"activeForm": "... grade line ..."}` and
# `Grep {"pattern": "z ~ 0.0"}` were refused with zero safety value. The named
# free-text parameters of the tools the reader can actually reach are now exempt.
# The default itself is untouched — the deny locks below pin that.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("label", "payload"),
    [
        (
            "todowrite_activeform",
            {
                "tool_name": "TodoWrite",
                "tool_input": {
                    "todos": [
                        {
                            # the tokens live ONLY in activeForm, so this case is
                            # red unless `activeForm` itself is exempt
                            "content": "Trace the interior partitions",
                            "status": "in_progress",
                            "activeForm": "Marking the grade line at ~0.000, .. range on North",
                        }
                    ]
                },
            },
        ),
        (
            "grep_regex_pattern",
            {
                "tool_name": "Grep",
                "tool_input": {"pattern": "grade line|wall_..[0-9]|z ~ 0.0", "path": "out"},
            },
        ),
        (
            "bash_style_description_on_non_bash_tool",
            {
                "tool_name": "Glob",
                "tool_input": {"pattern": "out/*.json", "description": "list the ~1.2 m .. sills near the grade line"},
            },
        ),
    ],
)
def test_guard_r3_free_text_params_of_non_write_tools_are_allowed(
    tmp_path: Path, label: str, payload: dict
):
    """R3-1 availability positive. A non-Write/Edit tool carrying `grade line`,
    `..` or `~` in a FREE-TEXT parameter must be ALLOWed — these were ALLOW at r1,
    DENY at r2, and every one of them is a path-free string. Live through the real
    staged guard, decision read back out of the audit log."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(staging, payload)
    assert proc.returncode == 0, (label, proc.stdout, proc.stderr)
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow", label


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        # the fail-closed default for unknown keys (R2-1) must survive R3-1
        (
            "unknown_key_absolute_escape",
            {"tool_name": "TodoWrite", "tool_input": {"scratch_note": "/etc/passwd"}},
        ),
        (
            "unknown_key_deny_token",
            {"tool_name": "Grep", "tool_input": {"pattern": "anything", "context_note": "case_tests"}},
        ),
        (
            "unknown_key_parent_traversal",
            {"tool_name": "Grep", "tool_input": {"pattern": "anything", "extra_root": "../../etc"}},
        ),
        # a path-role parameter is untouched by the free-text exemptions
        (
            "path_key_bare_deny_token",
            {"tool_name": "Read", "tool_input": {"file_path": "case_tests"}},
        ),
        # tool-scoped: `pattern` is free text for Grep only, never for Glob
        (
            "glob_pattern_is_still_a_path",
            {"tool_name": "Glob", "tool_input": {"pattern": "**/gt" + ".json"}},
        ),
    ],
)
def test_guard_r3_default_stays_fail_closed_after_free_text_exemptions(
    tmp_path: Path, label: str, payload: dict
):
    """R3-1 negative locks. Adding named free-text parameters to the exempt table
    must not weaken anything else: an UNKNOWN key carrying an out-of-workspace
    path is still refused (the R2-1 hard requirement), a real path parameter is
    still refused, and `pattern` — free text for Grep — is still a scanned path
    for Glob. Each payload's only offending value sits in the named key."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(staging, payload)
    assert proc.returncode == 2, (label, proc.stdout, proc.stderr)


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
# R3-3 NIT-2 (registered, not changed — the rework order authorized this
# exemption): the match is by PATH PART, so `__pycache__` is exempt at ANY depth,
# including `tools/__pycache__/**`. A change written into a protected directory's
# byte-cache is therefore invisible to this E2E diff. Acceptable because (a) the
# reader cannot author a .pyc — the write gate refuses every target outside
# out//requests/, and (b) `tools/**` is independently protected by that same
# gate, which has its own negative locks.
_E2E_EXEMPT_PARTS = ("__pycache__",)  # interpreter byte-cache of the staged tools


def _staging_snapshot(root: Path) -> dict[str, str]:
    """Type + content/target signature for every entry in the staging tree.

    Directories and symlinks are included, not merely regular files, so the
    R2-2 E2E assertion really diffs the whole tree.
    """
    snapshot = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            snapshot[rel] = f"symlink:{path.readlink()}"
        elif path.is_dir():
            snapshot[rel] = "directory"
        elif path.is_file():
            snapshot[rel] = f"file:{hash_file(path)}"
        else:
            snapshot[rel] = "other"
    return snapshot


def _protected_tree_diff(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Entries added, removed, or rewritten outside the writable roots.

    The two exemption collections above are the complete named allowlist; no
    path is silently skipped.
    """
    changed = []
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) == after.get(rel):
            continue
        if rel.startswith(_E2E_WRITABLE_PREFIXES):
            continue
        parts = Path(rel).parts
        if parts[-1] in _E2E_EXEMPT_NAMES or any(p in _E2E_EXEMPT_PARTS for p in parts):
            continue
        if rel not in before:
            change = "added"
        elif rel not in after:
            change = "removed"
        else:
            change = "rewritten"
        changed.append(f"{change}:{rel}")
    return changed


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


def test_wrapper_independently_refuses_outside_output_and_tree_is_unchanged(tmp_path: Path):
    """R2-2 wrapper lock. Invoke the helper without the hook and prove its
    independent output-root policy refuses the exact `out_dir="tools"` escape
    without changing the protected tree."""
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": "tools", "bbox": "0,0,20,20"}},
        name="requests/write_tools.json",
    )
    before = _staging_snapshot(staging)

    helper = _run_helper(staging, "requests/write_tools.json")
    after = _staging_snapshot(staging)
    assert _protected_tree_diff(before, after) == []
    assert not (staging / "tools" / "cv_evidence").exists()
    assert helper.returncode != 0, helper.stdout
    assert "out/" in (helper.stderr + helper.stdout)


def test_wrapper_refuses_when_the_writable_root_is_a_symlink(tmp_path: Path):
    """R3-2 lock: the wrapper and the guard now SHARE one writable-root rule.

    Pre-seed `out -> tools`, then bypass the hook entirely and drive the helper
    directly — the exact shape that used to slip past the wrapper's private
    `(root/name).resolve(strict=False)` and really wrote six entries under
    `tools/**` while the hook was refusing the same call. The wrapper must now
    refuse with the guard's own reason and leave the protected tree untouched.
    """
    staging_root = tmp_path / "staging"
    staging_root.mkdir()
    (staging_root / "tools").mkdir()
    (staging_root / "out").symlink_to("tools")

    staging = build_isolation_workspace(CASE_DIR, staging_root=staging_root).staging_root
    assert (staging / "out").is_symlink(), "fixture precondition: the root stayed a symlink"
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": "out/cv", "bbox": "0,0,20,20"}},
        name="requests/probe.json",
    )
    before = _staging_snapshot(staging)

    helper = _run_helper(staging, "requests/probe.json")
    after = _staging_snapshot(staging)

    # The tree assertion goes FIRST so a regression reports what really landed:
    # `out` is a symlink, so anything written "under out/" shows up as tools/**.
    assert _protected_tree_diff(before, after) == []
    assert not (staging / "tools" / "cv").exists()
    assert helper.returncode != 0, helper.stdout
    assert "real directory" in (helper.stderr + helper.stdout), helper.stderr


@pytest.mark.parametrize(
    ("label", "out_dir", "hook_should_allow"),
    [
        ("outside_tools", "tools", False),
        ("outside_reference", "reference", False),
        ("inside_out", "out/cv", True),
    ],
)
def test_e2e_hook_then_helper_changes_only_writable_tree(
    tmp_path: Path, label: str, out_dir: str, hook_should_allow: bool
):
    """R2-2 core E2E lock.

    Build a real staging workspace, run the real hook, execute the real helper
    exactly when the hook allows the shape, then diff every staging entry. The
    legal shape proves the helper branch and tree diff are non-vacuous; the two
    outside shapes pin the refusal boundary.
    """
    staging = _build(tmp_path).staging_root
    _request(
        staging,
        {"tool": "crop_zoom", "args": {"image": "case_data/1f_view.png", "out_dir": out_dir, "bbox": "0,0,20,20"}},
        name="requests/probe.json",
    )
    before = _staging_snapshot(staging)

    hook = _hook(staging, "python tools/run_cv_probe.py --request requests/probe.json")
    helper = _run_helper(staging, "requests/probe.json") if hook.returncode == 0 else None

    after = _staging_snapshot(staging)
    assert _protected_tree_diff(before, after) == [], label

    if hook_should_allow:
        assert hook.returncode == 0, (label, hook.stdout, hook.stderr)
        assert helper is not None and helper.returncode == 0, (
            label,
            None if helper is None else helper.stdout,
            None if helper is None else helper.stderr,
        )
        produced = sorted(
            rel
            for rel in after
            if rel not in before and rel.startswith("out/") and after[rel].startswith("file:")
        )
        assert produced, "the helper wrote no files under out/ — the E2E diff would be vacuous"
    else:
        assert hook.returncode == 2, (label, hook.stdout, hook.stderr)
        assert "out/" in hook.stderr
        assert helper is None, "the helper must run only for hook-allowed shapes"


# --------------------------------------------------------------------------- #
# P1-1/P1-2 — the DIRECT one-call probe form.
#
# The guard used to require a probe command to be exactly four tokens
# (`python tools/run_cv_probe.py --request <json>`), so every measurement cost
# two tool calls: Write the request JSON, then Bash it. The 07-30 run paid that
# 2x tax on the one action the reading methodology depends on — probe calls fell
# 19 -> 8. The token count is now a STRICT ARGUMENT PARSER instead: paired
# `--key value` only, keys from an enumerated allowlist, every value through the
# same `_validate_probe_params` the request path uses.
# --------------------------------------------------------------------------- #
# `--sidecar-name 042_crop_zoom` is deliberately a name the tool's own
# auto-numbering can never produce (it starts at 001). A neuter that silently
# drops one direct-form argument on the way to cv_probe therefore CHANGES the
# landing path instead of coincidentally reproducing it — with `001_crop_zoom`
# here, dropping `--sidecar-name` was invisible and every lock below stayed
# green. Every other argument in this string is load-bearing on its own:
# cv_probe declares `--image`/`--out-dir` required and errors without `--bbox`.
_DIRECT_SIDECAR_NAME = "042_crop_zoom"
_DIRECT_SIDECAR_REL = f"out/cv/cv_evidence/1f_view/{_DIRECT_SIDECAR_NAME}.json"
_DIRECT_PROBE_ARGS = (
    "--tool crop_zoom --image case_data/1f_view.png --out-dir out/cv "
    f"--bbox 0,0,20,20 --sidecar-name {_DIRECT_SIDECAR_NAME}"
)


def _direct_command(args: str = _DIRECT_PROBE_ARGS) -> str:
    return f"python tools/run_cv_probe.py {args}"


def _run_helper_direct(staging: Path, args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", *args.split()],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )


def _batch(staging: Path, entries: list[dict], name: str = "requests/batch.json") -> Path:
    return _request(staging, {"requests": entries}, name=name)


def _batch_entry(
    request_id: str,
    *,
    tool: str = "crop_zoom",
    out_dir: str = "out/cv",
    **args,
) -> dict:
    return {
        "id": request_id,
        "tool": tool,
        "args": {
            "image": "case_data/1f_view.png",
            "out_dir": out_dir,
            **args,
        },
    }


def _run_helper_batch(
    staging: Path, batch_rel: str = "requests/batch.json"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", "--batch", batch_rel],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )


def test_staging_run_cv_probe_direct_form_smoke(tmp_path: Path):
    """P1-2 wrapper side: one call, no request file anywhere, real sidecar under
    `out/`."""
    staging = _build(tmp_path).staging_root
    helper = _run_helper_direct(staging, _DIRECT_PROBE_ARGS)
    assert helper.returncode == 0, helper.stderr
    assert (staging / _DIRECT_SIDECAR_REL).exists()
    assert not list((staging / "requests").glob("*.json")), (
        "the direct form must need no request file at all — that second call is "
        "the whole cost this item removes"
    )


def test_guard_allows_direct_probe_form_and_logs(tmp_path: Path):
    """P1-1 hook side: the legal direct shape is ALLOWED and its path arguments
    are normalized into the audit log (so the log stays a usable read of what the
    reader actually touched)."""
    staging = _build(tmp_path).staging_root
    proc = _hook(staging, _direct_command())
    assert proc.returncode == 0, proc.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow"
    assert log["reason"] == "allowed run_cv_probe direct arguments"
    assert any(path.endswith("case_data/1f_view.png") for path in log["normalized_paths"])
    assert any(path.endswith("out/cv") for path in log["normalized_paths"])


def test_probe_help_is_allowlisted_and_documents_all_three_forms(tmp_path: Path):
    """A rejected exploratory `--help` must become a no-write, copyable repair.

    This locks the exact guard exception as well as the staged wrapper's complete
    direct/request/batch guidance; a partial argparse help text is insufficient.
    """
    staging = _build(tmp_path).staging_root

    hook = _hook(staging, "python tools/run_cv_probe.py --help")
    helper = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", "--help"],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )

    assert hook.returncode == 0, hook.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow"
    assert log["reason"] == "allowed run_cv_probe help"
    assert helper.returncode == 0, helper.stderr
    assert "Usage:" in helper.stdout
    assert "--tool px_m_calibrator" in helper.stdout
    assert "--request requests/calibrate.json" in helper.stdout
    assert "--batch requests/sweep.json" in helper.stdout


@pytest.mark.parametrize(
    ("label", "command", "expected"),
    [
        (
            "bare_tool_name",
            "python tools/run_cv_probe.py px_m_calibrator --image case_data/1f_view.png --out-dir out/cv",
            "did you mean --tool px_m_calibrator?",
        ),
        (
            "batch_wrong_envelope",
            "python tools/run_cv_probe.py --batch requests/wrong_envelope.json",
            'use: {"requests":[{"id":"calibrate_x","tool":"px_m_calibrator"',
        ),
        (
            "batch_wrong_entry",
            "python tools/run_cv_probe.py --batch requests/wrong_entry.json",
            'use: {"id":"calibrate_x","tool":"px_m_calibrator","args":',
        ),
    ],
)
def test_guard_probe_shape_receipts_include_a_minimal_correct_repair(
    tmp_path: Path, label: str, command: str, expected: str
):
    """W3: real failed shapes carry the next valid form in the denial itself."""
    staging = _build(tmp_path).staging_root
    if label == "batch_wrong_envelope":
        _request(staging, {"wrong": []}, name="requests/wrong_envelope.json")
    elif label == "batch_wrong_entry":
        _request(
            staging,
            {"requests": [{"tool": "crop_zoom", "args": {}}]},
            name="requests/wrong_entry.json",
        )

    proc = _hook(staging, command)

    assert proc.returncode == 2, proc.stdout
    assert expected in proc.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["reason"] in proc.stderr


def test_guard_missing_direct_value_receipt_includes_the_required_pair_syntax(tmp_path: Path):
    staging = _build(tmp_path).staging_root

    proc = _hook(staging, "python tools/run_cv_probe.py --tool crop_zoom --image")

    assert proc.returncode == 2
    assert "write --image <value>" in proc.stderr


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv | tee out/log",
            "remove the pipe and rerun the same python tools/run_cv_probe.py command directly",
        ),
        (
            "mkdir out/new_probe_dir",
            "out/ and requests/ are already provisioned",
        ),
        (
            "find case_data -type f",
            "use ls case_data to list the copied input images",
        ),
    ],
)
def test_guard_real_shell_denials_include_an_isolation_safe_next_step(
    tmp_path: Path, command: str, expected: str
):
    """W3 locks the three real non-probe denial receipts without allowing Bash."""
    staging = _build(tmp_path).staging_root

    proc = _hook(staging, command)

    assert proc.returncode == 2
    assert expected in proc.stderr
    if command.startswith("find "):
        assert _hook(staging, "ls case_data").returncode == 0


@pytest.mark.parametrize(
    "args",
    [
        "px_m_calibrator --image case_data/1f_view.png --out-dir out/cv",
        "--tool crop_zoom --image",
    ],
)
def test_wrapper_direct_shape_receipts_match_the_guard_repairs(tmp_path: Path, args: str):
    """The executable has the same actionable errors if the hook is bypassed."""
    staging = _build(tmp_path).staging_root

    helper = _run_helper_direct(staging, args)

    assert helper.returncode != 0
    if args.startswith("px_m_calibrator"):
        assert "did you mean --tool px_m_calibrator?" in (helper.stderr + helper.stdout)
    else:
        assert "write --image <value>" in (helper.stderr + helper.stdout)


def test_direct_and_request_forms_produce_identical_output(tmp_path: Path):
    """P1-3: the old `--request` form is unchanged, and the new form is the same
    probe — not a second, differently-behaving entry point. Same tool, same
    arguments, byte-identical sidecar."""
    staging = _build(tmp_path).staging_root
    sidecar = staging / _DIRECT_SIDECAR_REL

    _request(
        staging,
        {
            "tool": "crop_zoom",
            "args": {
                "image": "case_data/1f_view.png",
                "out_dir": "out/cv",
                "bbox": "0,0,20,20",
                "sidecar_name": _DIRECT_SIDECAR_NAME,
            },
        },
        name="requests/probe.json",
    )
    assert _hook(staging, "python tools/run_cv_probe.py --request requests/probe.json").returncode == 0
    assert _run_helper(staging, "requests/probe.json").returncode == 0
    via_request = sidecar.read_bytes()

    shutil.rmtree(staging / "out/cv")
    assert _hook(staging, _direct_command()).returncode == 0
    assert _run_helper_direct(staging, _DIRECT_PROBE_ARGS).returncode == 0

    assert sidecar.read_bytes() == via_request


_DIRECT_DENY_SHAPES = [
        # output-role parameter outside the writable root — the R2-2 rule, reached
        # through the new form, via the SHARED implementation
        ("out_dir_tools", "--tool crop_zoom --image case_data/1f_view.png --out-dir tools"),
        ("out_dir_underscore_spelling", "--tool crop_zoom --image case_data/1f_view.png --out_dir tools"),
        ("out_dir_reference", "--tool crop_zoom --image case_data/1f_view.png --out-dir reference"),
        # path-role parameter escaping staging, INCLUDING the bare extension-less
        # symlink that no string-shape test recognizes as a path
        ("image_bare_escaping_symlink", "--tool crop_zoom --image escape --out-dir out/cv"),
        ("image_slashed_escaping_symlink", "--tool crop_zoom --image case_data/escape.png --out-dir out/cv"),
        ("image_absolute_outside", "--tool crop_zoom --image /etc/passwd --out-dir out/cv"),
        ("candidates_json_bare_escaping_symlink",
         "--tool overlay_logger --image case_data/1f_view.png --candidates-json escape --out-dir out/cv"),
        # parser shape rules
        ("unknown_key", "--tool crop_zoom --image case_data/1f_view.png --out-dir out/cv --nope 1"),
        ("bare_positional", "--tool crop_zoom --image case_data/1f_view.png stray.json"),
        ("repeated_key", "--tool crop_zoom --tool wall_line_profiler --image case_data/1f_view.png"),
        ("missing_value_at_end", "--tool crop_zoom --image"),
        # The value slot holds another `--key`. Note the EVEN token count: with
        # `--out-dir out/cv` appended, neutering the "next token is a key" half of
        # the check merely shifts the pairing and `out/cv` lands as a bare
        # positional, so the call is still refused — by a different rule. The
        # shape below leaves nothing over, so it is the only one that really pins
        # this half.
        ("missing_value_taken_from_next_key", "--tool crop_zoom --image --out-dir"),
        ("missing_value_shifts_the_pairing", "--tool crop_zoom --image --out-dir out/cv"),
        ("missing_tool", "--image case_data/1f_view.png --out-dir out/cv"),
        ("missing_image", "--tool crop_zoom --out-dir out/cv"),
        ("no_arguments_at_all", ""),
        # the lexical scan still runs on every value, in every role
        ("deny_token_in_free_text_value", "--tool crop_zoom --image case_data/1f_view.png --label gt.json"),
        ("parent_traversal_in_out_dir", "--tool crop_zoom --image case_data/1f_view.png --out-dir out/../tools"),
        # `--request` may not be smuggled in as a direct parameter
        ("request_key_in_direct_form", "--tool crop_zoom --request requests/probe.json"),
]


@pytest.mark.parametrize(
    ("label", "args"),
    _DIRECT_DENY_SHAPES,
    ids=[case[0] for case in _DIRECT_DENY_SHAPES],
)
def test_guard_denies_illegal_direct_probe_shapes(tmp_path: Path, label: str, args: str):
    """P1-3 negative locks for the direct form. Fail-closed on every axis: role
    violations, escaping paths, unknown keys and every ambiguous argument shape.
    """
    staging = _build(tmp_path).staging_root
    (staging / "escape").symlink_to("/etc/passwd")
    (staging / "case_data" / "escape.png").symlink_to("/etc/passwd")
    proc = _hook(staging, _direct_command(args))
    assert proc.returncode == 2, (label, proc.stdout, proc.stderr)
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "deny", label


_DIRECT_BASH_BOUNDARY_SHAPES = [
        ("other_script_direct_form",
         "python tools/cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv"),
        ("other_script_request_form", "python tools/other.py --request requests/probe.json"),
        ("python_dash_c", "python -c 'print(1)'"),
        ("python_alone", "python"),
        ("compound_token_after_direct_form",
         "python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv | tee x"),
        ("redirect_after_direct_form",
         "python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv > out/log"),
        ("not_allowlisted_command", "cat case_data/1f_view.png"),
]


@pytest.mark.parametrize(
    ("label", "command"),
    _DIRECT_BASH_BOUNDARY_SHAPES,
    ids=[case[0] for case in _DIRECT_BASH_BOUNDARY_SHAPES],
)
def test_guard_direct_form_does_not_loosen_bash_boundary(tmp_path: Path, label: str, command: str):
    """P1-3: replacing the token-count rule must not let anything else through.
    argv[1] identity, `python -c`, the compound-token scan and the command
    allowlist all still apply, and are now denied on their own merits rather than
    incidentally by a length check."""
    staging = _build(tmp_path).staging_root
    proc = _hook(staging, command)
    assert proc.returncode == 2, (label, proc.stdout, proc.stderr)


def test_direct_param_allowlist_matches_cv_probe_options(tmp_path: Path):
    """P1-1 anti-drift lock: the allowlist must be the real enumeration of
    cv_probe's options, not a guess and not a stale copy.

    Read straight out of `scripts/tool_scripts/cv_probe.py` — the file staged as
    `tools/cv_probe.py` — so adding an option there without deciding whether the
    isolated reader may pass it turns this red instead of silently shipping a key
    the guard refuses (or, worse, a stale list nobody rechecks).
    """
    guard_mod = _guard_module()
    source = Path("scripts/tool_scripts/cv_probe.py").read_text(encoding="utf-8")
    declared = {
        name.replace("-", "_")
        for name in re.findall(r'add_argument\(\s*"--([a-z0-9-]+)"', source)
    }
    assert declared, "fixture precondition: options were parsed out of cv_probe.py"
    # `tool` is the subparser selector (the request JSON's top-level "tool"), so
    # it is the one key with no add_argument line.
    assert set(guard_mod.PROBE_DIRECT_PARAM_KEYS) == declared | {"tool"}
    # Roles are a subset of the allowlist, by name, and out_dir is not both.
    assert set(guard_mod.PROBE_PATH_ROLE_KEYS) < set(guard_mod.PROBE_DIRECT_PARAM_KEYS)
    assert set(guard_mod.REQUEST_OUTPUT_ROLE_KEYS) < set(guard_mod.PROBE_DIRECT_PARAM_KEYS)
    assert not set(guard_mod.PROBE_PATH_ROLE_KEYS) & set(guard_mod.REQUEST_OUTPUT_ROLE_KEYS)


@pytest.mark.parametrize(
    ("label", "out_dir", "hook_should_allow"),
    [
        ("outside_tools", "tools", False),
        ("outside_reference", "reference", False),
        ("inside_out", "out/cv", True),
    ],
)
def test_e2e_direct_form_hook_then_helper_changes_only_writable_tree(
    tmp_path: Path, label: str, out_dir: str, hook_should_allow: bool
):
    """P1-3 E2E lock for the direct form, same discipline as the request-form
    one: real hook, real helper (only when the hook allows), whole-tree diff.
    The legal shape additionally asserts the helper really produced files, so the
    diff cannot pass by being vacuous.
    """
    staging = _build(tmp_path).staging_root
    args = f"--tool crop_zoom --image case_data/1f_view.png --out-dir {out_dir} --bbox 0,0,20,20"
    before = _staging_snapshot(staging)

    hook = _hook(staging, _direct_command(args))
    helper = _run_helper_direct(staging, args) if hook.returncode == 0 else None

    after = _staging_snapshot(staging)
    assert _protected_tree_diff(before, after) == [], label

    if hook_should_allow:
        assert hook.returncode == 0, (label, hook.stdout, hook.stderr)
        assert helper is not None and helper.returncode == 0, (
            label,
            None if helper is None else helper.stderr,
        )
        produced = sorted(
            rel
            for rel in after
            if rel not in before and rel.startswith("out/") and after[rel].startswith("file:")
        )
        assert produced, "the helper wrote no files under out/ — the E2E diff would be vacuous"
    else:
        assert hook.returncode == 2, (label, hook.stdout, hook.stderr)
        assert "out/" in hook.stderr
        assert helper is None, "the helper must run only for hook-allowed shapes"


def test_wrapper_direct_form_independently_refuses_outside_output(tmp_path: Path):
    """P1-2: the wrapper is an independent defence for the direct form too —
    bypass the hook entirely and it still refuses `--out-dir tools`, leaving the
    protected tree untouched."""
    staging = _build(tmp_path).staging_root
    before = _staging_snapshot(staging)

    helper = _run_helper_direct(
        staging, "--tool crop_zoom --image case_data/1f_view.png --out-dir tools --bbox 0,0,20,20"
    )
    after = _staging_snapshot(staging)

    assert _protected_tree_diff(before, after) == []
    assert not (staging / "tools" / "cv_evidence").exists()
    assert helper.returncode != 0, helper.stdout
    assert "out/" in (helper.stderr + helper.stdout)


# --------------------------------------------------------------------------- #
# L1 — bounded batch probing.  A normal ~20-probe measurement sweep now pays
# one Write + one Bash round trip, while every inner request still passes the
# exact validator used by the legacy single-request form before anything runs.
# --------------------------------------------------------------------------- #
def test_guard_allows_bounded_probe_batch_and_logs_every_request_path(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    _batch(
        staging,
        [
            _batch_entry("crop_nw", bbox="0,0,20,20", sidecar_name="041_crop_zoom"),
            _batch_entry(
                "vertical_bands",
                tool="wall_line_profiler",
                axis="col",
                sidecar_name="043_wall_cols",
            ),
        ],
    )

    proc = _hook(staging, "python tools/run_cv_probe.py --batch requests/batch.json")

    assert proc.returncode == 0, proc.stderr
    log = json.loads((staging / "access_log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "allow"
    assert log["reason"] == "allowed run_cv_probe batch"
    assert any(path.endswith("requests/batch.json") for path in log["normalized_paths"])
    assert any(path.endswith("case_data/1f_view.png") for path in log["normalized_paths"])
    assert any(path.endswith("out/cv") for path in log["normalized_paths"])


def test_probe_batch_returns_one_document_with_stable_ids_and_own_sidecars(tmp_path: Path):
    """The Bash result is the one-read aggregate, while the ordinary per-probe
    append-only evidence files remain the audit source of truth."""
    staging = _build(tmp_path).staging_root
    _batch(
        staging,
        [
            _batch_entry("crop_nw", bbox="0,0,20,20", sidecar_name="041_crop_zoom"),
            _batch_entry(
                "vertical_bands",
                tool="wall_line_profiler",
                axis="col",
                sidecar_name="043_wall_cols",
            ),
        ],
    )

    helper = _run_helper_batch(staging)

    assert helper.returncode == 0, helper.stderr
    aggregate = json.loads(helper.stdout)
    assert aggregate["batch_schema"] == "1"
    assert aggregate["request_count"] == 2
    assert [item["id"] for item in aggregate["results"]] == [
        "crop_nw",
        "vertical_bands",
    ]
    assert [item["tool"] for item in aggregate["results"]] == [
        "crop_zoom",
        "wall_line_profiler",
    ]
    for item in aggregate["results"]:
        sidecar = staging / item["sidecar"]
        assert sidecar.is_file(), item
        assert item["result"] == json.loads(sidecar.read_text(encoding="utf-8"))
    assert len(list((staging / "out/cv/cv_evidence/1f_view").glob("*.json"))) == 2


def test_probe_batch_sidecars_are_byte_identical_to_legacy_single_requests(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    entries = [
        _batch_entry("crop_nw", bbox="0,0,20,20", sidecar_name="041_crop_zoom"),
        _batch_entry(
            "vertical_bands",
            tool="wall_line_profiler",
            axis="col",
            sidecar_name="043_wall_cols",
        ),
    ]
    _batch(staging, entries)
    assert _run_helper_batch(staging).returncode == 0
    sidecar_dir = staging / "out/cv/cv_evidence/1f_view"
    batch_bytes = {
        path.name: path.read_bytes() for path in sorted(sidecar_dir.glob("*.json"))
    }

    shutil.rmtree(staging / "out/cv")
    for index, entry in enumerate(entries):
        _request(
            staging,
            {"tool": entry["tool"], "args": entry["args"]},
            name=f"requests/single_{index}.json",
        )
        single = _run_helper(staging, f"requests/single_{index}.json")
        assert single.returncode == 0, single.stderr

    single_bytes = {
        path.name: path.read_bytes() for path in sorted(sidecar_dir.glob("*.json"))
    }
    assert single_bytes == batch_bytes


@pytest.mark.parametrize(
    ("label", "bad_entry"),
    [
        ("lexical", _batch_entry("bad", bbox="0,0,20,20", label="gt" + ".json")),
        ("output_role", _batch_entry("bad", out_dir="tools", bbox="0,0,20,20")),
        (
            "path_role_bare_symlink",
            {
                "id": "bad",
                "tool": "crop_zoom",
                "args": {"image": "escape", "out_dir": "out/cv", "bbox": "0,0,20,20"},
            },
        ),
    ],
)
def test_guard_refuses_whole_batch_when_any_request_fails_single_request_validator(
    tmp_path: Path, label: str, bad_entry: dict
):
    staging = _build(tmp_path).staging_root
    (staging / "escape").symlink_to("/etc/passwd")
    _batch(
        staging,
        [
            _batch_entry("good_first", bbox="0,0,20,20", sidecar_name="040_crop_zoom"),
            bad_entry,
        ],
    )
    before = _staging_snapshot(staging)

    hook = _hook(staging, "python tools/run_cv_probe.py --batch requests/batch.json")

    after = _staging_snapshot(staging)
    assert hook.returncode == 2, (label, hook.stdout, hook.stderr)
    assert _protected_tree_diff(before, after) == []
    assert not list((staging / "out").rglob("*.json")), label


@pytest.mark.parametrize(
    ("label", "bad_entry"),
    [
        ("outside_output", _batch_entry("bad", out_dir="tools", bbox="0,0,20,20")),
        ("tool_specific_unknown_option", _batch_entry("bad", bbox="0,0,20,20", nope="1")),
        ("tool_specific_missing_bbox", _batch_entry("bad")),
    ],
)
def test_wrapper_preflights_entire_batch_before_first_probe_executes(
    tmp_path: Path, label: str, bad_entry: dict
):
    """Bypass the hook: both wrapper path validation and cv_probe argparse
    validation happen for request 2 before valid request 1 may write."""
    staging = _build(tmp_path).staging_root
    _batch(
        staging,
        [
            _batch_entry("good_first", bbox="0,0,20,20", sidecar_name="040_crop_zoom"),
            bad_entry,
        ],
    )
    before = _staging_snapshot(staging)

    helper = _run_helper_batch(staging)

    after = _staging_snapshot(staging)
    assert helper.returncode != 0, (label, helper.stdout, helper.stderr)
    assert _protected_tree_diff(before, after) == []
    assert not list((staging / "out").rglob("*.json")), label


def test_guard_enforces_finite_probe_batch_bound(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    maximum = _guard_module().MAX_PROBE_BATCH_SIZE
    assert 20 <= maximum <= 64, "bound must cover a real sweep without becoming unbounded"
    entries = [
        _batch_entry(f"probe_{index:02d}", bbox="0,0,20,20")
        for index in range(maximum + 1)
    ]
    _batch(staging, entries)

    proc = _hook(staging, "python tools/run_cv_probe.py --batch requests/batch.json")

    assert proc.returncode == 2, proc.stderr
    assert f"maximum is {maximum}" in proc.stderr


def test_wrapper_independently_enforces_shared_probe_batch_bound(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    maximum = _guard_module().MAX_PROBE_BATCH_SIZE
    _batch(
        staging,
        [
            _batch_entry(f"probe_{index:02d}", bbox="0,0,20,20")
            for index in range(maximum + 1)
        ],
    )

    helper = _run_helper_batch(staging)

    assert helper.returncode != 0
    assert f"maximum is {maximum}" in (helper.stdout + helper.stderr)
    assert not list((staging / "out").rglob("*.json"))


@pytest.mark.parametrize(
    "entries",
    [
        [],
        [
            _batch_entry("duplicate", bbox="0,0,20,20"),
            _batch_entry("duplicate", bbox="20,0,40,20"),
        ],
        [_batch_entry("contains space", bbox="0,0,20,20")],
    ],
    ids=["empty", "duplicate_ids", "invalid_id"],
)
def test_guard_rejects_ambiguous_probe_batch_envelopes(
    tmp_path: Path, entries: list[dict]
):
    staging = _build(tmp_path).staging_root
    _batch(staging, entries)

    proc = _hook(staging, "python tools/run_cv_probe.py --batch requests/batch.json")

    assert proc.returncode == 2, proc.stderr


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


@pytest.mark.parametrize(
    ("label", "tool_input"),
    [
        (
            "decoy_file_path_masks_notebook_path",
            {"file_path": "out/decoy.txt", "notebook_path": "tools/protected.ipynb", "new_source": "x"},
        ),
        (
            "decoy_notebook_path_masks_file_path",
            {"notebook_path": "out/decoy.ipynb", "file_path": "tools/protected.py", "content": "x"},
        ),
        (
            "both_targets_legal_still_ambiguous",
            {"file_path": "out/a.txt", "notebook_path": "out/b.ipynb", "new_source": "x"},
        ),
    ],
)
def test_guard_denies_ambiguous_multiple_write_targets(tmp_path: Path, label: str, tool_input: dict):
    """R2-5 (sol MINOR-1): `_write_target` used to take the first key in
    WRITE_TARGET_KEYS order, so an innocuous `file_path` masked the real
    `notebook_path` and the write was allowed. Two target keys in one call is
    ambiguous about where the write lands and is now refused outright — including
    when both would individually be legal, so the rule is about the ambiguity,
    not about the destination."""
    staging = _build(tmp_path).staging_root
    proc = _hook_payload(staging, {"tool_name": "NotebookEdit", "tool_input": tool_input})
    assert proc.returncode == 2, (label, proc.stdout, proc.stderr)
    assert "ambiguous write target" in proc.stderr


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


@pytest.mark.parametrize(
    ("aggregate_text", "error"),
    [
        ("{this is not valid JSON", "aggregate output.json is not valid JSON"),
        (json.dumps({"views": []}), "aggregate output.json must be shaped"),
    ],
    ids=["invalid_json", "wrong_shape"],
)
def test_merge_existing_corrupt_aggregate_is_rejected_instead_of_assembled(
    tmp_path: Path, aggregate_text: str, error: str
):
    """R2-6: only an absent aggregate activates per-image assembly.

    A present but corrupt aggregate retains the old fail-loud contract even when
    every per-image file is complete; corruption must never be reinterpreted as
    absence.
    """
    manifest, run_dir = _formal_sm21(tmp_path)
    staging = manifest.staging_root
    _write_per_image_views(staging, _real_views())
    (staging / "out" / "output.json").write_text(aggregate_text, encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        merge_isolated_output(staging, run_dir)
    assert not (run_dir / "0_reading" / "attempts").exists() or not list(
        (run_dir / "0_reading" / "attempts").iterdir()
    )
