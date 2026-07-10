from __future__ import annotations

import json
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
from src.agent.execution.manifest import RunManifest, hash_file, hash_text


CASE_DIR = Path("case_tests/e2e_tests/sm21_anchor")


def _build(tmp_path: Path):
    return build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "staging")


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
    src = run_dir / "0_reading" / "cv_evidence" / "1f_view" / "prescan"
    src.mkdir(parents=True)
    (src / "candidates.json").write_text("{}", encoding="utf-8")

    manifest = build_isolation_workspace(
        CASE_DIR, run_dir=run_dir, staging_root=tmp_path / "staging"
    )
    staging = manifest.staging_root

    copied = staging / "prescan" / "cv_evidence" / "1f_view" / "prescan" / "candidates.json"
    assert copied.exists()
    kickoff = (staging / "kickoff_prompt.md").read_text(encoding="utf-8")
    assert "prescan/cv_evidence/<image_stem>/prescan/" in kickoff


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


def test_merge_archives_provenance_and_binds_hash(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    output = staging / "out/output.json"
    output.write_text('{"views":[]}', encoding="utf-8")
    run_dir = tmp_path / "case_run"

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)

    assert attempt_dir.name == "001"
    assert (attempt_dir / "isolation_provenance.json").exists()
    assert (attempt_dir / "isolation_archive/MANIFEST.json").exists()
    assert (attempt_dir / "isolation_archive/isolation_settings.json").exists()
    assert (attempt_dir / "isolation_archive/guard.py").exists()
    rec = RunManifest.load(run_dir).accepted("0_reading")
    assert rec is not None
    assert rec.output_hash == hash_text('{"views":[]}')
    assert rec.input_hashes["isolation_provenance"] == hash_file(attempt_dir / "isolation_provenance.json")


def test_merge_retries_next_attempt_without_overwrite(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    output = staging / "out/output.json"
    output.write_text('{"views":[1]}', encoding="utf-8")
    run_dir = tmp_path / "case_run"
    existing = run_dir / "0_reading/attempts/001"
    existing.mkdir(parents=True)
    (existing / "output.json").write_text("existing", encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)

    assert attempt_dir.name == "002"
    assert (existing / "output.json").read_text(encoding="utf-8") == "existing"


def test_feedback_rejects_contamination_tokens():
    with pytest.raises(ValueError):
        check_feedback_text("please compare against gt.json")
