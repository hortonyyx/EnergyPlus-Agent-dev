from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.execution import isolation, view_manifest
from src.agent.execution.isolation import (
    _assert_source_allowed,
    build_isolation_workspace,
    check_feedback_text,
    merge_isolated_output,
    spawn_command,
    write_feedback,
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
    """Preview/unbound build (no run_dir) — never merge-eligible.

    Pinned to ``guard_profile="strict"``: as of 2026-08-18 the SHIPPING default
    is ``observe`` (CLAUDE.md §0.4#1 — exploratory tier logs and does not
    enforce), but what the guard tests below assert is the strict policy's
    JUDGMENT, which ``observe`` computes identically and then declines to
    enforce. Pinning keeps those assertions about the judgment instead of
    silently becoming assertions about the default. The default itself is
    locked separately (``test_default_guard_profile_is_observe``).
    """
    return build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / "staging", guard_profile="strict"
    )


def _formal_build(case_dir: Path, run_dir: Path, staging_root: Path):
    """Formal (run-bound) build. `build_isolation_workspace` only *verifies*
    the view manifest (§4.4/§5.2) — it never provisions — so every formal-build
    test provisions first, exactly as an operator/CLI must."""
    provision_view_manifest(case_dir, run_dir)
    # Most tests below exercise merge/provenance mechanics, not the human review
    # workflow. Keep those fixtures on the explicit control arm; dedicated pilot
    # review tests build with the production default and verify the state gate.
    return build_isolation_workspace(
        case_dir,
        run_dir=run_dir,
        staging_root=staging_root,
        pilot_review_gate=False,
    )


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


def _access_log(staging: Path) -> Path:
    """F-55: access_log.jsonl no longer lives under staging_root — it was
    relocated to a SIBLING directory (`<staging.name>.audit`) so the reader's
    own OS-level writes cannot reach it (guard.py's `_audit_dir` / isolation
    .py's mirrored rule of the same name). Every existing test that used to
    read `staging / "access_log.jsonl"` directly reads through this helper
    now — the log's CONTENT and the property each test verifies are
    unchanged; only its physical location moved, which is the entire point
    of the fix."""
    return staging.parent / f"{staging.name}.audit" / "access_log.jsonl"


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


def test_build_kickoff_names_outputs_by_expected_output_id_not_view_suffix(tmp_path: Path):
    """M-2 / N-2 (r1, F-3): the generated kickoff_prompt.md is the FIRST
    instruction the reader receives (spawn_command feeds it to ``claude -p
    <prompt>``). It must name reading outputs by ``<expected_output_id>`` (from
    input_inventory.json), matching the O-3 unique spec in session_kickoff.md —
    NOT teach the old ``<name>_view.json`` derivation. The old kickoff wrote
    ``<name>_view.json`` even AFTER O-3 deleted that derivation from
    session_kickoff.md, so a reader following the kickoff (not the skill doc)
    appended ``_view`` again and was refused at merge (the O-3 病灶 on the real
    isolated path — the cross-review's F-3 second derivation site).

    Reads the REAL generated kickoff_prompt.md. Neuter: revert the kickoff
    sentence to ``<name>_view.json`` ⇒ ``expected_output_id``/input_inventory
    vanish and ``<name>_view`` reappears ⇒ this lock reds. (The merge-side
    backstop for a reader that still appends ``_view`` is L-50 /
    test_merge_per_image_view_suffix_misapplied_is_rejected.)"""
    manifest = _build(tmp_path)
    kickoff = (manifest.staging_root / "kickoff_prompt.md").read_text(encoding="utf-8")
    assert "expected_output_id" in kickoff
    assert "input_inventory.json" in kickoff
    assert "<name>_view" not in kickoff  # the old derivation rule is gone


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
        log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    # S-2 (G-3): binding now also pins the frozen effective run policy so merge
    # can re-verify it did not drift between build and merge. This is a
    # contract change (not a relaxation): the set is still exact-equal, now over
    # 13 keys rather than 8.
    assert set(binding) == {
        "merge_eligible", "run_id", "case_id", "case_dir", "run_dir",
        "view_manifest_sha256", "case_metadata_sha256", "image_sha256",
        "run_policy_sha256", "run_policy_run_profile",
        "run_policy_capability_profile", "run_policy_legacy_defaulted",
        "pilot_review_gate",
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "deny"
    assert "tool_input_excerpt" in log


@pytest.mark.parametrize(
    "command",
    [
        # 2026-08-16: `python -c 'print(1)'` MOVED OUT of this list — it is now
        # allowed on purpose (A3 removal). See
        # test_guard_allows_reader_authored_computation. Everything left here is
        # denied for a reason that survived that change: shell structure, cwd/env
        # manipulation, or the information boundary itself.
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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

    workspace = build_isolation_workspace(
        case_dir,
        run_dir=run_dir,
        staging_root=tmp_path / "staging",
        pilot_review_gate=False,
    )
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


def test_merge_rejects_reading_exam_scope_changed_since_build(tmp_path: Path):
    """The valid current scope must still match the scope bound at build time."""
    case_dir = _case_copy(tmp_path, name="sm24_copy")
    run_dir = tmp_path / "scope_run"
    run_dir.mkdir()
    config_path = run_dir / "run_config.yaml"
    config_path.write_text(
        "reading_exam_scope:\n"
        "  input_ids: [1f_view, South_view]\n"
        "  reason: focused reading exam\n",
        encoding="utf-8",
    )
    base_manifest = provision_view_manifest(case_dir, run_dir)
    workspace = build_isolation_workspace(case_dir, run_dir=run_dir, staging_root=tmp_path / "staging")
    output = workspace.staging_root / "out/output.json"
    output.write_text(json.dumps({"views": {}}), encoding="utf-8")

    config_path.write_text(
        "reading_exam_scope:\n"
        "  input_ids: [1f_view]\n"
        "  reason: narrowed reading exam\n",
        encoding="utf-8",
    )
    changed_scope = view_manifest._declared_reading_exam_scope(run_dir, base_manifest)
    assert changed_scope is not None
    (run_dir / "_run" / "reading_exam_scope.json").write_text(
        changed_scope.model_dump_json(indent=2), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="reading exam scope changed"):
        merge_isolated_output(workspace.staging_root, run_dir, output_path=output)


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
WORKED_EXAMPLE_SOURCE = Path(isolation.WORKED_EXAMPLE_SOURCE)
WORKED_EXAMPLE_STAGED = Path("reference/worked_example_plan.json")


def _wall_line_fingerprint(path: Path) -> set[tuple[tuple[float, float], tuple[float, float]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    lines = set()
    for stroke in payload["strokes"]:
        geometry = stroke["geometry"]
        if stroke["pen"] != "wall" or geometry["kind"] != "line":
            continue
        p1 = tuple(float(value) for value in geometry["p1"])
        p2 = tuple(float(value) for value in geometry["p2"])
        lines.add(tuple(sorted((p1, p2))))
    return lines


def test_worked_example_is_synthetic_and_not_the_sm21_shaped_case_artifact():
    """Regression lock for the 2026-08-18 benchmark-confound finding.

    The previous ``smalloffice_20`` example was a different case by name but its
    complete Floor-1 wall grid was identical to sm21. A reader was required to
    inspect it before the sm21 exam. Keep examples out of case artifacts and
    ensure the replacement cannot silently drift back to that exact wall prior.
    """
    contaminated = Path("case_tests/e2e_tests/smalloffice_20/0_reading/1f_view.json")

    assert "case_tests" not in WORKED_EXAMPLE_SOURCE.parts
    assert WORKED_EXAMPLE_SOURCE.is_file()
    assert _wall_line_fingerprint(WORKED_EXAMPLE_SOURCE)
    assert _wall_line_fingerprint(WORKED_EXAMPLE_SOURCE) != _wall_line_fingerprint(contaminated)


def test_worked_example_is_schema_valid_and_gate_clean():
    """A format anchor must not teach a shape that the production gate rejects."""
    from src.agent.reading.schema import ReadingView
    from src.validator.checks.reading import check_reading_view

    payload = json.loads(WORKED_EXAMPLE_SOURCE.read_text(encoding="utf-8"))
    report = check_reading_view(
        ReadingView.model_validate(payload),
        run_profile="regression",
        dimensioned_state="declared_true",
    )

    assert report.blocking() == []


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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
        # 2026-08-16: `python -c 'print(1)'` was listed here as security property
        # #5 and is now ALLOWED on purpose. It was never an information-boundary
        # property — running a program reveals nothing by itself — it was a
        # capability lockdown filed under the security heading, which is exactly
        # the conflation the 2026-08-02 ruling names. What the boundary actually
        # needs is that a program cannot REACH the answers, and that is locked by
        # test_guard_information_boundary_survives_a3_removal (including the
        # `-c` form) and test_guard_scans_the_bytes_that_will_run_not_the_command_line.
        ("compound_token", {"tool_name": "Bash", "tool_input": {"command": "ls; whoami"}}),
    ],
)
def test_guard_security_properties_stay_denied(tmp_path: Path, label: str, payload: dict):
    """S2b regression locks: the required security properties stay red->deny
    through the prose-scan relaxation and the 2026-08-16 A3 removal. (Property 4
    symlink escape and property 8 request-file forbidden token have dedicated
    tests below.)"""
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
# F-55 (2026-08-16): access_log.jsonl no longer lives under staging_root (see
# `_access_log`/guard.py's `_audit_dir`), so `_staging_snapshot`'s
# `root.rglob("*")` never sees it any more and this exemption is now
# vestigial — left in place, harmless, rather than pulled mid-fix for a name
# that still describes what it would have exempted.
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


def _assert_probe_artifacts(
    staging: Path, out_dir: str, image_stem: str, sidecar_name: str
) -> None:
    evidence_dir = staging / out_dir / "cv_evidence" / image_stem
    assert (evidence_dir / f"{sidecar_name}.json").exists()
    assert (evidence_dir / f"{sidecar_name}_overlay.png").exists()


def test_px_m_calibrator_path_and_direct_inline_json_reach_real_entrypoint(
    tmp_path: Path,
):
    """F-49 R-1/R-3/R-4: preserve the file-path form, then prove the
    documented one-call inline form passes both the real hook and wrapper and
    creates both evidence artifacts."""
    staging = _build(tmp_path).staging_root
    anchors = [
        {
            "axis": "x",
            "px_a": 100,
            "px_b": 700,
            "value_m": 15.0,
            "dimension_ref": "overall_width",
        }
    ]

    anchors_path = staging / "requests/anchors.json"
    anchors_path.write_text(json.dumps(anchors), encoding="utf-8")
    _request(
        staging,
        {
            "tool": "px_m_calibrator",
            "args": {
                "image": "case_data/1f_view.png",
                "out_dir": "out/f49_path",
                "anchors_json": "requests/anchors.json",
                "sidecar_name": "001_px_m_calibrator",
            },
        },
        name="requests/f49_path.json",
    )
    path_command = (
        "python tools/run_cv_probe.py --request requests/f49_path.json"
    )
    path_hook = _hook(staging, path_command)
    assert path_hook.returncode == 0, (path_hook.stdout, path_hook.stderr)
    path_helper = _run_helper(staging, "requests/f49_path.json")
    assert path_helper.returncode == 0, (path_helper.stdout, path_helper.stderr)
    _assert_probe_artifacts(
        staging, "out/f49_path", "1f_view", "001_px_m_calibrator"
    )

    inline = json.dumps(anchors, separators=(",", ":"))
    direct_command = (
        "python tools/run_cv_probe.py --tool px_m_calibrator "
        "--image case_data/1f_view.png --out-dir out/f49_inline "
        f"--anchors-json '{inline}' --sidecar-name 001_px_m_calibrator"
    )
    direct_hook = _hook(staging, direct_command)
    assert direct_hook.returncode == 0, (direct_hook.stdout, direct_hook.stderr)
    direct_helper = subprocess.run(
        [
            sys.executable,
            "tools/run_cv_probe.py",
            "--tool",
            "px_m_calibrator",
            "--image",
            "case_data/1f_view.png",
            "--out-dir",
            "out/f49_inline",
            "--anchors-json",
            inline,
            "--sidecar-name",
            "001_px_m_calibrator",
        ],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )
    assert direct_helper.returncode == 0, (
        direct_helper.stdout,
        direct_helper.stderr,
    )
    _assert_probe_artifacts(
        staging, "out/f49_inline", "1f_view", "001_px_m_calibrator"
    )


@pytest.mark.parametrize("form", ["request", "batch"])
def test_px_m_calibrator_json_array_reaches_real_entrypoint(
    tmp_path: Path, form: str
):
    """F-49 R-1/R-3/R-4/R-5: the JSON-array shape advertised by both
    request examples must survive the real staged command-line entrypoint."""
    staging = _build(tmp_path).staging_root
    sidecar_name = f"001_f49_{form}"
    request = {
        "tool": "px_m_calibrator",
        "args": {
            "image": "case_data/1f_view.png",
            "out_dir": f"out/f49_{form}",
            "anchors_json": [
                {
                    "axis": "x",
                    "px_a": 100,
                    "px_b": 700,
                    "value_m": 15.0,
                    "dimension_ref": "overall_width",
                }
            ],
            "sidecar_name": sidecar_name,
        },
    }
    if form == "request":
        _request(staging, request, name="requests/f49_request.json")
        command = (
            "python tools/run_cv_probe.py --request requests/f49_request.json"
        )
        run_helper = lambda: _run_helper(staging, "requests/f49_request.json")
    else:
        _batch(staging, [{"id": "calibrate_x", **request}])
        command = "python tools/run_cv_probe.py --batch requests/batch.json"
        run_helper = lambda: _run_helper_batch(staging)

    hook = _hook(staging, command)
    assert hook.returncode == 0, (hook.stdout, hook.stderr)
    helper = run_helper()
    assert helper.returncode == 0, (helper.stdout, helper.stderr)
    _assert_probe_artifacts(
        staging, f"out/f49_{form}", "1f_view", sidecar_name
    )


def test_overlay_logger_direct_inline_json_reaches_real_entrypoint(tmp_path: Path):
    """F-49 premise check: candidates_json is the same JSON-or-path role and
    its documented direct shape must pass the real hook and wrapper."""
    staging = _build(tmp_path).staging_root
    candidates = json.dumps(
        [
            {
                "candidate_id": "wall_1",
                "geometry": {"kind": "line", "axis": "col", "x_px": 100},
                "status": "accepted",
                "reason": "F-49 premise check",
            }
        ],
        separators=(",", ":"),
    )
    command = (
        "python tools/run_cv_probe.py --tool overlay_logger "
        "--image case_data/1f_view.png --out-dir out/f49_overlay "
        f"--candidates-json '{candidates}' --sidecar-name 001_overlay_logger"
    )
    hook = _hook(staging, command)
    assert hook.returncode == 0, (hook.stdout, hook.stderr)
    helper = subprocess.run(
        [
            sys.executable,
            "tools/run_cv_probe.py",
            "--tool",
            "overlay_logger",
            "--image",
            "case_data/1f_view.png",
            "--out-dir",
            "out/f49_overlay",
            "--candidates-json",
            candidates,
            "--sidecar-name",
            "001_overlay_logger",
        ],
        cwd=staging,
        capture_output=True,
        text=True,
        check=False,
    )
    assert helper.returncode == 0, (helper.stdout, helper.stderr)
    _assert_probe_artifacts(
        staging, "out/f49_overlay", "1f_view", "001_overlay_logger"
    )


def test_guard_allows_direct_probe_form_and_logs(tmp_path: Path):
    """P1-1 hook side: the legal direct shape is ALLOWED and its path arguments
    are normalized into the audit log (so the log stays a usable read of what the
    reader actually touched)."""
    staging = _build(tmp_path).staging_root
    proc = _hook(staging, _direct_command())
    assert proc.returncode == 0, proc.stderr
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert log["reason"] in proc.stderr


def test_guard_missing_direct_value_receipt_includes_the_required_pair_syntax(tmp_path: Path):
    staging = _build(tmp_path).staging_root

    proc = _hook(staging, "python tools/run_cv_probe.py --tool crop_zoom --image")

    assert proc.returncode == 2
    assert "write --image <value>" in proc.stderr


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        # 2026-08-16: the safe next step for each of these changed with A3
        # removal, because the reader now HAS a general way out — its own Python.
        # `find` left this list entirely: it is allowlisted now, so there is no
        # denial left to carry advice.
        (
            "python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv | tee out/log",
            "express the pipeline in the Python program instead",
        ),
        (
            "mkdir out/new_probe_dir",
            "run it from Python instead",
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert log["decision"] == "deny", label


_DIRECT_BASH_BOUNDARY_SHAPES = [
        # 2026-08-16 (A3 removal) reshaped this list. Three shapes left it and
        # each departure is deliberate:
        #   `python -c` and reader-authored scripts are the capability this round
        #     restores, so they moved to the positive tests below;
        #   `cat case_data/...` is now an allowlisted read whose path goes through
        #     the same normalization `ls` always used.
        # `tools/cv_probe.py` stays here and is the load-bearing one: the raw CLI
        # must NOT become executable just because scripts did, or the 08-15
        # prescan withdrawal silently reverses.
        ("other_script_direct_form",
         "python tools/cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv"),
        ("other_script_request_form", "python tools/other.py --request requests/probe.json"),
        ("python_alone", "python"),
        ("compound_token_after_direct_form",
         "python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv | tee x"),
        ("redirect_after_direct_form",
         "python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv > out/log"),
        ("script_outside_writable_dirs", "python skills/whatever.py"),
        ("nonexistent_script", "python out/never_written.py"),
        # `-m` names an installed module, so its code never reaches the scan.
        # `pip` would fetch from the network and mutate the environment;
        # `http.server` would open a socket. Neither is caught by scanning a bare
        # module name, and neither is a computation the reader loses: everything
        # importable via -m is importable from -c, where the code IS scanned.
        ("module_form_pip", "python -m pip install requests"),
        ("module_form_server", "python -m http.server"),
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
    log = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
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

    # strict: this asserts the guard's JUDGMENT of a symlinked write root, which
    # the shipping `observe` default computes identically and then declines to
    # enforce (CLAUDE.md §0.4#1). Same reason `_build` is pinned.
    staging = build_isolation_workspace(
        CASE_DIR, staging_root=staging_root, guard_profile="strict"
    ).staging_root
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


def test_merge_per_image_view_suffix_misapplied_is_rejected(tmp_path: Path):
    """L-50 (O-3): a source PNG whose stem already ends in ``_view`` (e.g.
    ``1f_view.png``) has ``expected_output_id`` = the stem itself (identity
    transform, view_manifest §4.2). The OLD kickoff generic rule
    ``<name>_view.json`` invited a reader to append ``_view`` AGAIN, leaving a
    spurious ``1f_view_view.json`` ALONGSIDE the correct ``1f_view.json``.
    Merge must refuse that extra file (``1f_view_view`` is not a manifest
    expected_output_id), never silently keep it as a duplicate. Neuter: drop the
    extra-stem check in ``_load_isolated_views`` (isolation.py:602-607) ⇒ the
    spurious file is no longer refused ⇒ this lock reds. The kickoff now names
    outputs by ``expected_output_id`` from ``input_inventory.json`` (O-3); this
    lock is the merge-side backstop for a reader that still appends ``_view``."""
    manifest, run_dir = _formal_sm21(tmp_path)
    staging = manifest.staging_root
    real = _real_views()
    _write_per_image_views(staging, real)  # all correct <expected_output_id>.json present
    identity_id = "1f_view"
    assert identity_id in real and identity_id.endswith("_view")
    # reader ALSO wrote the old <name>_view.json form for an identity stem
    (staging / "out" / f"{identity_id}_view.json").write_text(
        json.dumps(real[identity_id]), encoding="utf-8"
    )
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


# ---------------------------------------------------------------------------
# 2026-08-16 — A3 removal ("能力封口" withdrawn).
#
# WHAT CHANGED AND WHY IT IS NOT A LOOSENING OF THE ISOLATION:
# The 2026-08-02 ruling (CLAUDE.md §1.5 #7) is that isolation must "严格限制可见
# 信息与写出边界，不限制在合法输入上采用何种计算方法" — and it names shutting
# down general CV programming by command shape as the thing NOT to do. Until this
# batch the guard did exactly that: `python -c` -> DENY, any self-written script
# -> DENY. These tests pin the new split: the reader may run its own code, and
# the boundary that decides what it may SEE moved from "which command was typed"
# to "which bytes are about to run".
#
# Every test here drives the real hook against a real staging workspace, so a
# regression shows up as a behaviour change and not as a diff in a constant.
# ---------------------------------------------------------------------------

_READER_COMPUTATION_ALLOWED = [
    ("dash_c", "python -c 'import numpy; print(numpy.__version__)'"),
    # Division, comparison and `;` are ordinary Python. They are also the shell
    # operators the pre-2026-08-16 substring scan refused ANYWHERE in the command
    # line, which would have made the newly-legal form unusable in practice —
    # the lockdown reappearing through the side door.
    ("division_operator", "python -c 'print(15 / 2)'"),
    ("comparison_operators", "python -c 'print(3 > 2)'"),
    ("statement_separator", "python -c 'import numpy as np; print(np.pi)'"),
    # Reading a file was never a capability worth locking: every path below goes
    # through the same `_path_arg` normalization `ls` already used.
    ("read_own_file", "cat out/measure.py"),
    ("head_own_file", "head out/measure.py"),
]


@pytest.mark.parametrize(
    ("label", "command"), _READER_COMPUTATION_ALLOWED,
    ids=[case[0] for case in _READER_COMPUTATION_ALLOWED],
)
def test_guard_allows_reader_authored_computation(tmp_path: Path, label: str, command: str):
    staging = _build(tmp_path).staging_root
    (staging / "out" / "measure.py").write_text("print(1)\n", encoding="utf-8")
    (staging / "out" / "x.json").write_text("{}", encoding="utf-8")
    proc = _hook(staging, command)
    assert proc.returncode == 0, (label, proc.stderr)


def test_guard_allows_running_a_script_the_reader_wrote(tmp_path: Path):
    """The headline positive: write a measurement program, then run it."""
    staging = _build(tmp_path).staging_root
    (staging / "out" / "measure.py").write_text(
        "import numpy as np\nfrom PIL import Image\n"
        "img = np.array(Image.open('case_data/1f_view.png').convert('L'))\n"
        "print(img.shape)\n",
        encoding="utf-8",
    )
    proc = _hook(staging, "python out/measure.py")
    assert proc.returncode == 0, proc.stderr


def test_guard_scans_the_bytes_that_will_run_not_the_command_line(tmp_path: Path):
    """The load-bearing test of the whole batch.

    `python out/leak.py` carries no forbidden token — the command line is clean
    no matter what the file holds. If the guard kept scanning only the command,
    allowing scripts would have opened the answer directory in one line. So the
    scan follows the bytes.
    """
    staging = _build(tmp_path).staging_root
    gt = "/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/sm21_anchor/gt.json"
    command = "python out/leak.py"

    # Self-check FIRST, and with the same command and the same filename: only the
    # bytes differ between the two halves. Without this half the test would still
    # pass if the deny came from the command line, i.e. it would be testing
    # nothing — the "prove the probe can see its target" discipline.
    (staging / "out" / "leak.py").write_text("print(1)\n", encoding="utf-8")
    assert _hook(staging, command).returncode == 0, "the command itself must be clean"

    (staging / "out" / "leak.py").write_text(f"print(open({gt!r}).read())\n", encoding="utf-8")
    proc = _hook(staging, command)
    assert proc.returncode == 2, proc.stdout
    assert "leak.py" in proc.stderr, proc.stderr


def test_guard_scans_the_whole_import_surface_not_just_the_entry_script(tmp_path: Path):
    """Entry script clean, helper dirty — `import helper` would otherwise be a
    one-line bypass of the file scan."""
    staging = _build(tmp_path).staging_root
    gt = "/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/sm21_anchor/gt.json"
    (staging / "out" / "main.py").write_text("import helper\nprint(helper.PATH)\n", encoding="utf-8")
    (staging / "out" / "helper.py").write_text(f"PATH = {gt!r}\n", encoding="utf-8")
    denied = _hook(staging, "python out/main.py")
    assert denied.returncode == 2, denied.stdout
    assert "helper.py" in denied.stderr, denied.stderr

    # ...and the SAME command is allowed once the dirty file is gone, which is
    # what proves the deny came from the helper and not from `main.py`.
    (staging / "out" / "helper.py").unlink()
    assert _hook(staging, "python out/main.py").returncode == 0


_EXEC_BOUNDARY_DENIED = [
    ("dash_c_reads_answers",
     "python -c 'print(open(\"/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/x/gt.json\").read())'"),
    # `$HOME` reaches outside staging while no forbidden token ever appears in
    # the command — the shell substitutes it after the guard has looked.
    ("shell_expansion", 'python -c "print(open(\'$HOME/x\').read())"'),
    ("command_substitution", "python -c 'print(1)' `ls`"),
    ("pipe_stays_denied", "python out/measure.py | head"),
    ("cat_reaches_answers",
     "cat /workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/x/gt.json"),
]


@pytest.mark.parametrize(
    ("label", "command"), _EXEC_BOUNDARY_DENIED,
    ids=[case[0] for case in _EXEC_BOUNDARY_DENIED],
)
def test_guard_information_boundary_survives_a3_removal(tmp_path: Path, label: str, command: str):
    staging = _build(tmp_path).staging_root
    (staging / "out" / "measure.py").write_text("print(1)\n", encoding="utf-8")
    proc = _hook(staging, command)
    assert proc.returncode == 2, (label, proc.stdout)


@pytest.mark.parametrize(
    ("label", "body", "fragment"),
    [
        ("network_egress", "import urllib.request\n", "network egress"),
        ("raw_socket", "import socket\n", "network egress"),
        ("child_process", "import subprocess\n", "child process"),
    ],
)
def test_guard_refuses_egress_and_indirection_inside_executed_code(
    tmp_path: Path, label: str, body: str, fragment: str
):
    """The two exec-only refusals, and they are NOT capability lockdowns:
    outbound network is named by the 2026-08-02 ruling as something isolation
    must prevent, and a child process computes nothing new — it only moves the
    work out of the guard's view, since only the top-level Bash call is hooked.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(body, encoding="utf-8")
    proc = _hook(staging, "python out/prog.py")
    assert proc.returncode == 2, proc.stdout
    assert fragment in proc.stderr, proc.stderr


def test_guard_does_not_brick_python_over_prose_words_in_code(tmp_path: Path):
    """Regression guard for a trap this design walked into once already.

    'grade' (室外地坪线), 'attempts' and 'verdict' are this project's own
    vocabulary, and the repo already rules them legal in a reader's prose
    (test_guard_allows_reading_summary_with_prose_forbidden_tokens). Scanning
    executed code with the full DENY_TOKENS list would mean one comment disables
    every Python call for the rest of a one-shot session — the lockdown coming
    back as an accident rather than a decision.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(
        "# grade line at 0.000; earlier attempts and the judge verdict are prose\n"
        "print('ok')\n",
        encoding="utf-8",
    )
    assert _hook(staging, "python out/prog.py").returncode == 0


def test_prescan_withdrawal_is_not_reversed_by_the_executable_surface(tmp_path: Path):
    """08-15 D1 withdrew prescan from the reader's option set. Making scripts
    executable must not hand it back through `tools/cv_probe.py`, or this round
    would be changing two variables at once and its result would be unreadable.
    """
    staging = _build(tmp_path).staging_root
    assert (staging / "tools" / "cv_probe.py").exists(), "the CLI is staged; that is the point"
    proc = _hook(
        staging,
        "python tools/cv_probe.py prescan-plan --image case_data/1f_view.png --out-dir out/cv",
    )
    assert proc.returncode == 2, proc.stdout


def test_access_log_records_the_payload_on_allow_too(tmp_path: Path):
    """F-44. The excerpt used to be a deny-only field, so the ALLOWED surface —
    the only one that can carry anything out of the clean room — left nothing
    behind but a hash of the payload. A hash proves two entries are identical; it
    cannot tell an auditor what ran, which is what made "was this reading
    produced without touching the answers?" unanswerable after the fact.
    """
    staging = _build(tmp_path).staging_root
    program = "import numpy as np; print(np.pi)"
    assert _hook(staging, f"python -c '{program}'").returncode == 0

    entry = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert entry["decision"] == "allow"
    assert program in entry["tool_input_excerpt"]
    # The code that ran is hashed, so editing the file afterwards cannot rewrite
    # the record of what was authorized.
    assert entry["executed_code"] == [
        {"path": "-c", "sha256": hashlib.sha256(program.encode("utf-8")).hexdigest()}
    ]


def test_access_log_hashes_every_scanned_script(tmp_path: Path):
    staging = _build(tmp_path).staging_root
    (staging / "out" / "main.py").write_text("import helper\n", encoding="utf-8")
    (staging / "out" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert _hook(staging, "python out/main.py").returncode == 0

    entry = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    recorded = {item["path"]: item["sha256"] for item in entry["executed_code"]}
    assert set(recorded) == {"out/main.py", "out/helper.py"}
    for rel, digest in recorded.items():
        assert digest == hashlib.sha256(
            (staging / rel).read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()


# --- 2026-08-16 cross-family review (sol) BLOCKER + the variant it did not reach ---
# The first version of the exec scan covered `*.py` ONLY. sol reproduced the hole
# end to end; reviewing my own fix surfaced a second shape that needs no `exec` at
# all. Both are ORDINARY Python, not obfuscation, which is why they matter: the
# stated threat model covers a reader taking an easy path, and these were easy.

def test_exec_scan_covers_code_carried_by_a_non_py_file(tmp_path: Path):
    """sol's BLOCKER, verbatim: a clean `.py` execs a `.txt` the scan never read."""
    staging = _build(tmp_path).staging_root
    gt = "/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/sm21_anchor/gt.json"
    (staging / "out" / "payload.txt").write_text(
        f"from pathlib import Path\nprint(Path({gt!r}).exists())\n", encoding="utf-8"
    )
    (staging / "out" / "runner.py").write_text(
        "from pathlib import Path\nexec(Path('out/payload.txt').read_text())\n", encoding="utf-8"
    )
    proc = _hook(staging, "python out/runner.py")
    assert proc.returncode == 2, proc.stdout


def test_exec_scan_covers_a_path_carried_by_a_non_py_file(tmp_path: Path):
    """The variant with no dynamic execution at all: the `.txt` carries the PATH,
    and a completely ordinary program opens it. Denying `exec` alone would not
    have caught this — which is why the FILE SET, not just the mechanism, moved.
    """
    staging = _build(tmp_path).staging_root
    gt = "/workspaces/EnergyPlus-Agent-dev/case_tests/test_baseline/gt/sm21_anchor/gt.json"
    (staging / "out" / "target.txt").write_text(gt + "\n", encoding="utf-8")
    (staging / "out" / "reader.py").write_text(
        "p = open('out/target.txt').read().strip()\nprint(open(p).read())\n", encoding="utf-8"
    )
    proc = _hook(staging, "python out/reader.py")
    assert proc.returncode == 2, proc.stdout


@pytest.mark.parametrize(
    "code",
    ["import importlib", "exec('x=1')", "eval('1+1')", "import pickle", "import runpy"],
)
def test_dynamic_execution_is_refused_by_name(tmp_path: Path, code: str):
    """The mechanism is refused independently of where the bytes live, so the two
    defences do not depend on each other."""
    staging = _build(tmp_path).staging_root
    assert _hook(staging, f"python -c '{code}'").returncode == 2


def test_binary_artifacts_do_not_block_execution(tmp_path: Path):
    """Negative control for the fix: `out/` fills up with crop PNGs and overlays
    during a real run. If widening the scan to every file had made those a hard
    error, the capability this batch restores would be unusable in practice — and
    that failure would only appear after the first CV call, not in any unit test
    that forgets to put a binary there.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "measure.py").write_text("print(1)\n", encoding="utf-8")
    (staging / "out" / "crop.png").write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 400)
    assert _hook(staging, "python out/measure.py").returncode == 0


def test_scanned_non_code_files_are_not_logged_as_executed_code(tmp_path: Path):
    """Widening the scan must not widen the CLAIM: a `.json` that was read as a
    potential carrier did not RUN, and `executed_code` is an execution record.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "measure.py").write_text("print(1)\n", encoding="utf-8")
    (staging / "out" / "1f_view.json").write_text('{"strokes": []}', encoding="utf-8")
    assert _hook(staging, "python out/measure.py").returncode == 0

    entry = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert [item["path"] for item in entry["executed_code"]] == ["out/measure.py"]


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("walk_from_root", "import os\nfor r, d, f in os.walk('/'):\n    print(r)\n    break\n"),
        ("walk_from_root_double_quoted", 'import os\nfor r, d, f in os.walk("/"):\n    print(r)\n    break\n'),
        ("root_via_os_sep", "import os\nfor r, d, f in os.walk(os.sep):\n    print(r)\n    break\n"),
        ("home_directory", "from pathlib import Path\nprint(Path.home())\n"),
        ("expanduser", "import os\nprint(os.path.expanduser('x'))\n"),
        ("environment", "import os\nprint(os.environ)\n"),
    ],
)
def test_paths_obtained_instead_of_written_are_refused(tmp_path: Path, label: str, body: str):
    """A lexical scan can only judge paths that appear AS TEXT, so the way past it
    is to never type one.

    This whole class was missed on the first pass, and the review request shipped
    with the claim that the pure-slash exemption "let no real path through".
    `os.walk('/')` disproved that claim: zero forbidden tokens, whole filesystem.
    The exemption exists for the division operator, and a quoted `'/'` is not
    division — that is the distinction these cases pin.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(body, encoding="utf-8")
    assert _hook(staging, "python out/prog.py").returncode == 2


@pytest.mark.parametrize(
    ("label", "body"),
    [
        ("spaced_division", "px, m = 60.7, 2.0\nprint(px / m)\n"),
        ("relative_join", "import os\nprint(os.path.join('out', 'cv', 'x.json'))\n"),
        ("real_measurement",
         "import numpy as np\nfrom PIL import Image\n"
         "img = np.array(Image.open('case_data/1f_view.png').convert('L'))\nprint(img.shape)\n"),
    ],
)
def test_ordinary_measurement_code_survives_the_path_rules(tmp_path: Path, label: str, body: str):
    """The negative control that keeps the rule above from becoming a lockdown:
    spaced division is why the slash exemption exists at all, and it must still
    work alongside the root-literal denial."""
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(body, encoding="utf-8")
    assert _hook(staging, "python out/prog.py").returncode == 0, body


# ---------------------------------------------------------------------------
# F-60 (2026-08-17) — the traversal/home rules used to be bare substring tests
# (`".." in text` / `"~" in text`) applied to whole FILE BODIES by the exec scan.
# Source files carry prose, and prose contains both characters, so the scan fired
# on English punctuation and on numpy's unary `~`. Found while reviewing an sm21
# pilot: the reader's two real pixel-measurement attempts were refused for
# exactly these two reasons, and the artifact it then produced ("round numbers
# instead of measurements") is indistinguishable from a reader that never tried
# — same family as F-49.
#
# ⛔ The locks below come in PAIRS on purpose. A narrowing like this is only
# correct if the prose stops matching AND every real escape shape still does, so
# each positive lock is paired with the negative it could have broken. A test
# file that only proved "prose is allowed now" would go green on `return True`.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body, shape",
    [
        ('print("Scanning for vertical walls...")\n', "ellipsis in a print string"),
        ("# Find bounds of walls (gray = ~180)\nx = 1\n", "tilde meaning 'approximately'"),
        ("import numpy as np\nmask = np.zeros(3, bool)\ncyan = ~mask\n", "numpy unary NOT"),
        ("import numpy as np\na = np.zeros(3, bool)\nb = ~(a & a)\n", "numpy NOT before a paren"),
        ("x = [[1, 2]]\nimport numpy as np\ny = np.array(x)[..., 0]\n", "numpy Ellipsis index"),
        ("def f():\n    ...\n", "Ellipsis as a statement"),
        ("# z ~ 0.0 within tolerance\nz = 0.0\n", "the free-text example CONTENT_ROLE_KEYS cites"),
    ],
)
def test_guard_f60_allows_prose_punctuation_in_reader_authored_code(
    tmp_path: Path, body: str, shape: str
):
    """F-60 positive half: prose punctuation inside code no longer reads as a path.

    Real entry point — a file written under out/ and executed through the hook,
    not a regex asserted in isolation, because the defect was in what the exec
    scan does to a FILE, and only the file channel can show that.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(body, encoding="utf-8")
    proc = _hook(staging, "python out/prog.py")
    assert proc.returncode == 0, f"{shape} still denied: {proc.stderr}"


@pytest.mark.parametrize(
    "body, shape",
    [
        ('open("../gt.json")\n', "separator-adjacent traversal"),
        ('from pathlib import Path\np = Path("..") / "gt"\n', "'..' standing alone as a path segment"),
        ('open("..\\\\secret")\n', "backslash traversal"),
        ('x = "foo/.."\n', "traversal at the end of a path"),
        ('open("..../../gt")\n', "dot padding does not buy an escape"),
        ('open("~/.ssh/id_rsa")\n', "home path"),
        ('open("~root/answers")\n', "home path with a user name"),
    ],
)
def test_guard_f60_still_denies_every_real_path_shape(tmp_path: Path, body: str, shape: str):
    """F-60 negative half — the half that makes the positive half mean anything.

    Each row is a shape the OLD bare-substring rule caught. If a future edit
    widens the regex back toward "anything containing .. or ~", these stay green;
    if it narrows past correctness, they go red. That asymmetry is the point.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(body, encoding="utf-8")
    proc = _hook(staging, "python out/prog.py")
    assert proc.returncode != 0, f"{shape} was allowed through"


def test_guard_f60_narrowing_did_not_shrink_the_scanned_surface(tmp_path: Path):
    """⭐ The lock that protects the part of the design F-60 must NOT touch.

    `_scan_reader_authored_code` deliberately scans EVERY writable file, not the
    one named on the command line — a 2026-08-16 cross-family review reproduced
    the hole that scanning only the entry script leaves (`out/main.py` stays
    clean and imports `out/helper.py`, which holds the path). The F-60 narrowing
    is about WHICH CHARACTERS count as a path, and must not become an excuse to
    narrow WHICH FILES are read. Here the executed file is spotless and the
    offender is a sibling: it must still be refused.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "main.py").write_text("print('clean')\n", encoding="utf-8")
    (staging / "out" / "helper.py").write_text(
        'ANSWERS = "../../case_tests/test_baseline/gt/sm21_anchor/gt.json"\n', encoding="utf-8"
    )
    proc = _hook(staging, "python out/main.py")
    assert proc.returncode != 0, "a sibling file carrying the answer path was not scanned"
    assert "helper.py" in proc.stderr, proc.stderr


def test_guard_f60_denial_names_the_line_and_the_matched_text(tmp_path: Path):
    """F-53/F-54/F-58 family: a refusal has to be actionable.

    "contains a forbidden token" alone is unactionable precisely BECAUSE the scan
    reads every writable file — the offender is routinely not the file being run,
    so the reader cannot tell what to change. The message must name the file, the
    line number, and the characters that matched.
    """
    staging = _build(tmp_path).staging_root
    (staging / "out" / "prog.py").write_text(
        "# fine\n# also fine\nDATA = open('../gt.json')\n", encoding="utf-8"
    )
    proc = _hook(staging, "python out/prog.py")
    assert proc.returncode != 0
    assert "prog.py" in proc.stderr, proc.stderr
    assert "line 3" in proc.stderr, proc.stderr
    assert "../" in proc.stderr, proc.stderr


def test_guard_f60_regression_case_proves_its_own_premise():
    """⚠️ This repo's rule: a regression case must show the OLD judgement really
    would have failed here, otherwise a green row proves nothing about the bug.

    The old rule was literally `".." in text` / `"~" in text`. Assert both halves
    directly: every prose sample WOULD have been caught by the old test (so the
    positive locks above are not vacuous), and is NOT caught by the new one.
    """
    guard_mod = _guard_module()
    prose = [
        'print("Scanning for vertical walls...")',
        "# Find bounds of walls (gray = ~180)",
        "cyan = ~mask",
        "# z ~ 0.0 within tolerance",
    ]
    for sample in prose:
        assert ".." in sample or "~" in sample, (
            f"{sample!r} would not have tripped the old rule — it is not a "
            "regression case for F-60 at all"
        )
        assert not guard_mod._TRAVERSAL_RE.search(sample), sample
        assert not guard_mod._HOME_RE.search(sample), sample


# ---------------------------------------------------------------------------
# 2026-08-18 · WIRING locks for `reading.calibration_axes_agree`.
#
# The checker itself is unit-tested in test_checks_reading_correction.py. What
# those tests cannot show is that `merge_isolated_output` actually CALLS it —
# and this repo's standing lesson is that a change must be locked at the wiring,
# not only at the mechanism (a perfectly correct checker nobody invokes looks
# exactly like no checker at all in the artifact).
# ---------------------------------------------------------------------------

_CAL_CHECK_ID = "reading.calibration_axes_agree"


def _write_bad_calibration(staging: Path) -> None:
    """A px_m_calibrator sidecar shaped like the real 2026-08-17 legal exit:
    the tool SUCCEEDED (rc=0) and recorded that it disagrees with itself."""
    target = staging / "out" / "cv" / "cv_evidence" / "1f_view" / "002_px_m_calibrator.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "tool": "px_m_calibrator",
                "results": [
                    {
                        "candidate_id": "1f_view:px_m_calibrator:002:scale",
                        "axis_calibration_disagreement": True,
                        "axis_px_per_m": {"x": 60.0666, "y": 87.5},
                        "axis_relative_deviation": 0.3718,
                        "axis_relative_deviation_limit": 0.003,
                        "metric": {"confidence": "low"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_merge_records_calibration_disagreement_in_the_checks_artifact(tmp_path: Path):
    """The wiring lock: a disagreeing calibration in staging must reach checks.json.

    Without this, the 2026-08-17 legal exit leaves the disagreement in two
    sidecar fields with no machine consumer anywhere in the pipeline — which is
    precisely what the 2026-08-18 draw measured going wrong.
    """
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": _real_views()}), encoding="utf-8")
    _write_bad_calibration(staging)

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)

    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    hits = [r for r in checks["results"] if r["check_id"].endswith(_CAL_CHECK_ID)]
    assert hits, "the calibration check never ran — merge is not wired to it"
    assert hits[0]["status"] == "fail", hits[0]
    assert hits[0]["evidence"]["offenders"][0]["axis_relative_deviation"] == 0.3718


def test_merge_records_calibration_agreement_when_the_ruler_is_consistent(tmp_path: Path):
    """The paired positive: the wiring must not be a constant-fail either.

    A lock that only ever proves "fail appears" would stay green if the checker
    were replaced by `add_fail(...)` unconditionally, so the agreeing case has
    to be pinned in the same artifact.
    """
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    manifest = _formal_build(CASE_DIR, run_dir, tmp_path / "staging")
    staging = manifest.staging_root
    output = staging / "out/output.json"
    output.write_text(json.dumps({"views": _real_views()}), encoding="utf-8")
    target = staging / "out" / "cv" / "cv_evidence" / "1f_view" / "001_px_m_calibrator.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "tool": "px_m_calibrator",
                "results": [
                    {
                        "candidate_id": "1f_view:px_m_calibrator:001:scale",
                        "axis_calibration_disagreement": False,
                        "axis_px_per_m": {"x": 60.0, "y": 60.0},
                        "metric": {"confidence": "high"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    attempt_dir = merge_isolated_output(staging, run_dir, output_path=output)

    checks = json.loads((attempt_dir / "checks.json").read_text(encoding="utf-8"))
    hits = [r for r in checks["results"] if r["check_id"].endswith(_CAL_CHECK_ID)]
    assert hits and hits[0]["status"] == "pass", hits


# ---------------------------------------------------------------------------
# 2026-08-18 · PILOT R2 EXTERNAL APPROVAL STATE.
#
# Feedback changes the artifact; it is not approval. The reader must stop after
# applying it, and an operator-owned state transition must bind the exact pilot
# bytes before batch work or merge can proceed.
# ---------------------------------------------------------------------------


def _gated_formal_build(tmp_path: Path) -> tuple[Path, Path]:
    run_dir = tmp_path / "case_run"
    run_dir.mkdir()
    provision_view_manifest(CASE_DIR, run_dir)
    staging = build_isolation_workspace(
        CASE_DIR,
        run_dir=run_dir,
        staging_root=tmp_path / "staging",
        pilot_review_gate=True,
    ).staging_root
    return staging, run_dir


def _write_only_plan_pilot(staging: Path, payload: dict | None = None) -> Path:
    inventory = json.loads((staging / "input_inventory.json").read_text(encoding="utf-8"))
    pilot_id = next(
        item["expected_output_id"] for item in inventory if item["view_type"] == "plan"
    )
    path = staging / "out" / f"{pilot_id}.json"
    path.write_text(json.dumps(payload or {"image_kind": "plan"}), encoding="utf-8")
    return path


def test_default_pilot_review_state_is_waiting_and_outside_reader_surface(tmp_path: Path):
    from src.agent.execution.isolation import pilot_review_state_path

    staging = _build(tmp_path).staging_root
    marker = pilot_review_state_path(staging)
    state = json.loads(marker.read_text(encoding="utf-8"))

    assert state["enabled"] is True
    assert state["phase"] == "awaiting_pilot"
    assert staging not in marker.parents


def test_feedback_requires_second_stop_then_explicit_approval_releases_batch(tmp_path: Path):
    from src.agent.execution.isolation import (
        _record_reader_session_id,
        approve_pilot,
        pilot_review_state_path,
    )

    staging = _build(tmp_path).staging_root
    _record_reader_session_id(staging, json.dumps({"session_id": "sess-review"}))
    pilot = _write_only_plan_pilot(staging)

    write_feedback(staging, "Recheck every measured candidate and revise only the pilot.")
    state = json.loads(pilot_review_state_path(staging).read_text(encoding="utf-8"))
    assert state["phase"] == "feedback_issued"
    assert state["feedback_round"] == 1

    rework_prompt = _spawn_argv(staging, resume=True)[2]
    assert "STOP again" in rework_prompt
    assert "Do not start any remaining image" in rework_prompt

    approve_pilot(staging)
    state = json.loads(pilot_review_state_path(staging).read_text(encoding="utf-8"))
    assert state["phase"] == "approved"
    assert state["approved_pilot_sha256"] == hash_file(pilot)

    approval_prompt = _spawn_argv(staging, resume=True)[2]
    assert "approved" in approval_prompt
    assert "remaining images" in approval_prompt
    assert "feedback.md" not in approval_prompt


def test_pilot_approval_refuses_when_reader_already_started_batch(tmp_path: Path):
    from src.agent.execution.isolation import approve_pilot

    staging = _build(tmp_path).staging_root
    inventory = json.loads((staging / "input_inventory.json").read_text(encoding="utf-8"))
    first_two = [item["expected_output_id"] for item in inventory[:2]]
    for output_id in first_two:
        (staging / "out" / f"{output_id}.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="exactly one completed"):
        approve_pilot(staging)


@pytest.mark.parametrize("name", ["output.json", "reading_summary.md"])
def test_pilot_approval_refuses_premature_aggregate_or_summary(tmp_path: Path, name: str):
    from src.agent.execution.isolation import approve_pilot

    staging = _build(tmp_path).staging_root
    _write_only_plan_pilot(staging)
    (staging / "out" / name).write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="exists before external approval"):
        approve_pilot(staging)


def test_merge_refuses_before_external_pilot_approval(tmp_path: Path):
    staging, run_dir = _gated_formal_build(tmp_path)
    output = staging / "out" / "output.json"
    output.write_text(json.dumps({"views": _real_views()}), encoding="utf-8")

    with pytest.raises(ValueError, match="has not received external approval"):
        merge_isolated_output(staging, run_dir, output_path=output)

    assert not (run_dir / "0_reading" / "attempts").exists()


def test_merge_refuses_if_approved_pilot_bytes_change(tmp_path: Path):
    from src.agent.execution.isolation import approve_pilot

    staging, run_dir = _gated_formal_build(tmp_path)
    pilot = _write_only_plan_pilot(staging, _real_views()["1f_view"])
    approve_pilot(staging)
    output = staging / "out" / "output.json"
    output.write_text(json.dumps({"views": _real_views()}), encoding="utf-8")
    pilot.write_text(json.dumps({"image_kind": "plan", "changed": True}), encoding="utf-8")

    with pytest.raises(ValueError, match="approved pilot changed"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_merge_refuses_if_aggregate_contains_a_different_unapproved_pilot(tmp_path: Path):
    from src.agent.execution.isolation import approve_pilot

    staging, run_dir = _gated_formal_build(tmp_path)
    approved_view = _real_views()["1f_view"]
    _write_only_plan_pilot(staging, approved_view)
    approve_pilot(staging)

    merged_views = json.loads(json.dumps(_real_views()))
    merged_views["1f_view"]["image_label"] = "different unapproved pilot"
    output = staging / "out" / "output.json"
    output.write_text(json.dumps({"views": merged_views}), encoding="utf-8")

    with pytest.raises(ValueError, match="merged payload differs"):
        merge_isolated_output(staging, run_dir, output_path=output)


def test_approved_immutable_pilot_allows_full_merge(tmp_path: Path):
    from src.agent.execution.isolation import approve_pilot

    staging, run_dir = _gated_formal_build(tmp_path)
    pilot = _write_only_plan_pilot(staging, _real_views()["1f_view"])
    approve_pilot(staging)
    output = staging / "out" / "output.json"
    output.write_text(json.dumps({"views": _real_views()}), encoding="utf-8")

    attempt = merge_isolated_output(staging, run_dir, output_path=output)

    assert attempt.is_dir()
    archived = json.loads(
        (attempt / "isolation_archive" / "pilot_review_state.json").read_text(encoding="utf-8")
    )
    assert archived["phase"] == "approved"
    assert archived["approved_pilot_sha256"] == hash_file(pilot)


def test_new_feedback_revokes_a_prior_pilot_approval(tmp_path: Path):
    from src.agent.execution.isolation import approve_pilot, pilot_review_state_path

    staging = _build(tmp_path).staging_root
    _write_only_plan_pilot(staging)
    approve_pilot(staging)
    write_feedback(staging, "One more pilot-only correction is required.")

    state = json.loads(pilot_review_state_path(staging).read_text(encoding="utf-8"))
    assert state["phase"] == "feedback_issued"
    assert state["approved_pilot_path"] is None
    assert state["approved_pilot_sha256"] is None


# ---------------------------------------------------------------------------
# 2026-08-18 · A1 SESSION FORM (`spawn_command(resume=...)`).
#
# The variable: 07-07 ran the pilot review inside ONE conversation (the reviewed
# work was still in context when the review arrived); every run since has
# cold-started each round via `claude -p`. That difference was named as gap #6
# on 2026-07-09 and never isolated — eight draws have attributed "the reader
# does not measure deeply" to prompts, tools and model identity instead.
#
# ⛔ The load-bearing lock here is the FAIL-CLOSED one: if `--resume` could
# silently fall back to a cold start when no session id exists, the experiment
# would report "we tested same-session" while having tested the control.
# ---------------------------------------------------------------------------


def _spawn_argv(staging: Path, **kw) -> list[str]:
    from src.agent.execution.isolation import spawn_command

    return spawn_command(staging, execute=False, **kw)


def test_spawn_defaults_to_cold_start_and_asks_for_the_session_id(tmp_path: Path):
    """Default is unchanged behaviour — plus the one addition that makes A1
    possible at all: the starting round must emit its session id."""
    staging = _build(tmp_path).staging_root
    argv = _spawn_argv(staging)
    assert "-r" not in argv
    assert argv[argv.index("--output-format") + 1] == "json"
    assert "Read skills/intake_pipeline/0_reading/session_kickoff.md" in argv[argv.index("-p") + 1]


def test_spawn_resume_refuses_when_no_session_was_recorded(tmp_path: Path):
    """⭐ Fail-closed, and the reason is experimental integrity, not safety.

    A silent cold-start fallback would make `--resume` a no-op that still LOOKS
    like the treatment arm — the run would be logged as same-session while
    actually being another cold start, and the one variable we are trying to
    isolate would be silently unisolated.
    """
    from src.agent.execution.isolation import spawn_command

    staging = _build(tmp_path).staging_root
    with pytest.raises(ValueError, match="cannot resume"):
        spawn_command(staging, execute=False, resume=True)


def test_spawn_resume_refuses_an_empty_recorded_session_id(tmp_path: Path):
    from src.agent.execution.isolation import session_id_path, spawn_command

    staging = _build(tmp_path).staging_root
    recorded = session_id_path(staging)
    recorded.parent.mkdir(parents=True, exist_ok=True)
    recorded.write_text("   \n", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot resume"):
        spawn_command(staging, execute=False, resume=True)


def test_spawn_resume_passes_the_id_and_does_not_resend_the_kickoff(tmp_path: Path):
    """The resumed turn must be just the review.

    Re-sending the kickoff would both burn the window and change the shape being
    reproduced: in 07-07 the reviewer said the next thing into an ongoing
    conversation, it did not restate the brief.
    """
    from src.agent.execution.isolation import session_id_path

    staging = _build(tmp_path).staging_root
    recorded = session_id_path(staging)
    recorded.parent.mkdir(parents=True, exist_ok=True)
    recorded.write_text("abc-123", encoding="utf-8")
    write_feedback(staging, "rework the pilot")

    argv = _spawn_argv(staging, resume=True)

    assert argv[argv.index("-r") + 1] == "abc-123"
    prompt = argv[argv.index("-p") + 1]
    assert "feedback.md" in prompt
    assert "session_kickoff.md" not in prompt, "the kickoff was re-sent into a resumed session"
    assert "STOP again" in prompt


def test_recorded_session_id_lives_outside_the_reader_writable_surface(tmp_path: Path):
    """F-55's rule applied to session identity: the audited party must not be
    able to forge or erase the record of which session it ran in."""
    from src.agent.execution.isolation import _record_reader_session_id, session_id_path

    staging = _build(tmp_path).staging_root
    _record_reader_session_id(staging, json.dumps({"session_id": "sess-42", "result": "ok"}))
    recorded = session_id_path(staging)
    assert recorded.read_text(encoding="utf-8") == "sess-42"
    assert staging not in recorded.parents, "session id was written inside the reader's workspace"
    assert recorded.parent == staging.parent / f"{staging.name}.audit"


@pytest.mark.parametrize("stdout", ["not json at all", "{}", '{"result": "ok"}'])
def test_unparseable_spawn_output_records_nothing_rather_than_a_bogus_id(tmp_path: Path, stdout: str):
    """A round whose id could not be captured still succeeded; what it loses is
    the ability to resume — and the refusal above makes that loud, not silent."""
    from src.agent.execution.isolation import _record_reader_session_id, session_id_path

    staging = _build(tmp_path).staging_root
    _record_reader_session_id(staging, stdout)
    assert not session_id_path(staging).exists()


# ---------------------------------------------------------------------------
# 2026-08-18 · N3 REPRODUCIBLE READER INVOCATIONS.
#
# A run is not reproducible merely because run_config names a model. These
# locks prove which executable/model/session form actually ran and bind that
# controller-owned ledger into the accepted reading attempt.
# ---------------------------------------------------------------------------


def test_execute_records_exact_reader_invocation_outside_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    from src.agent.execution.isolation import reader_invocations_path

    staging = _build(tmp_path).staging_root

    def fake_run(cmd, **kwargs):
        if cmd[-1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, "2.1.198 (Claude Code)\n", "")
        return subprocess.CompletedProcess(
            cmd, 0, json.dumps({"session_id": "sess-n3", "result": "ok"}), ""
        )

    monkeypatch.setattr(isolation.subprocess, "run", fake_run)
    spawn_command(staging, model="claude-haiku-4-5-20251001", execute=True)
    capsys.readouterr()

    ledger = reader_invocations_path(staging)
    records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    record = records[0]
    assert record["runner_version"] == "2.1.198 (Claude Code)"
    assert record["requested_model"] == "claude-haiku-4-5-20251001"
    assert record["session_form"] == "start"
    assert record["reported_session_id"] == "sess-n3"
    assert record["returncode"] == 0
    assert record["input_hashes"]["manifest_sha256"] == hash_file(
        staging / "MANIFEST.json"
    )
    assert record["argv_redacted"][2].startswith("<prompt sha256=")
    assert "session_kickoff.md" not in record["argv_redacted"][2]
    assert staging not in ledger.parents


def test_single_plan_experiment_fixes_model_and_rejects_model_drift(tmp_path: Path):
    from src.agent.execution.isolation import (
        prepare_single_plan_experiment,
        reading_experiment_spec_path,
    )

    run_dir = tmp_path / "run_single"
    staging = tmp_path / "staging_single"
    prepare_single_plan_experiment(
        CASE_DIR,
        run_dir,
        staging,
        input_id="1f_view",
        model="claude-haiku-4-5-20251001",
    )

    inventory = json.loads((staging / "input_inventory.json").read_text(encoding="utf-8"))
    assert [item["input_id"] for item in inventory] == ["1f_view"]
    spec = json.loads(reading_experiment_spec_path(staging).read_text(encoding="utf-8"))
    assert spec["experiment_kind"] == "single_plan_same_session"
    assert spec["model"] == "claude-haiku-4-5-20251001"
    argv = spawn_command(staging)
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5-20251001"

    with pytest.raises(ValueError, match="model mismatch"):
        spawn_command(staging, model="claude-sonnet-4-6")


def test_controlled_single_plan_merge_requires_and_archives_same_session_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    from src.agent.execution.isolation import (
        approve_pilot,
        prepare_single_plan_experiment,
        reader_invocations_path,
    )

    model = "claude-haiku-4-5-20251001"
    run_dir = tmp_path / "run_single"
    staging = tmp_path / "staging_single"
    prepare_single_plan_experiment(
        CASE_DIR, run_dir, staging, input_id="1f_view", model=model
    )

    actual_turn = 0

    def fake_run(cmd, **kwargs):
        nonlocal actual_turn
        if cmd[-1] == "--version":
            return subprocess.CompletedProcess(cmd, 0, "2.1.198 (Claude Code)\n", "")
        actual_turn += 1
        stdout = json.dumps({"session_id": "sess-one", "result": "pilot"}) if actual_turn == 1 else "revised"
        return subprocess.CompletedProcess(cmd, 0, stdout, "")

    monkeypatch.setattr(isolation.subprocess, "run", fake_run)
    spawn_command(staging, execute=True)
    capsys.readouterr()
    pilot = staging / "out" / "1f_view.json"
    pilot.write_text(json.dumps(_real_views()["1f_view"]), encoding="utf-8")
    write_feedback(staging, "Recheck the measured wall and opening candidates in the pilot only.")
    spawn_command(staging, execute=True, resume=True)
    capsys.readouterr()
    approve_pilot(staging)

    attempt = merge_isolated_output(staging, run_dir)

    records = [
        json.loads(line)
        for line in reader_invocations_path(staging).read_text(encoding="utf-8").splitlines()
    ]
    assert [record["session_form"] for record in records] == ["start", "resume"]
    assert records[1]["session_id"] == records[0]["reported_session_id"] == "sess-one"
    archive = attempt / "isolation_archive"
    assert (archive / "reader_invocations.jsonl").is_file()
    assert (archive / "reading_experiment_spec.json").is_file()
    provenance = json.loads((attempt / "isolation_provenance.json").read_text(encoding="utf-8"))
    assert provenance["reader_invocations_sha256"] == hash_file(
        archive / "reader_invocations.jsonl"
    )
    accepted = load_run_manifest(run_dir).accepted("0_reading")
    assert accepted is not None
    assert accepted.input_hashes["isolation_reader_invocations"]
    assert accepted.input_hashes["isolation_experiment_spec"]


# ---------------------------------------------------------------------------
# 2026-08-18 · GUARD PROFILE — the relaxed control arm.
#
# ⭐ The load-bearing lock in this block is BOUNDARY PARITY. The arm exists to
# weigh guard friction against measurement depth, and its result is only worth
# reading if "the reader never reached the answers" is still true under the
# relaxed policy. If a future edit lets one boundary shape through on `relaxed`,
# every conclusion drawn from that arm becomes unciteable — so the parity test
# is what makes the experiment admissible, not a nicety.
# ---------------------------------------------------------------------------

_BOUNDARY_SHAPES = [
    ("cat ../../case_tests/test_baseline/gt/sm21_anchor/gt.json", "traversal to the answers"),
    ("python -c \"open('gt.json')\"", "answer filename"),
    ("cat /workspaces/EnergyPlus-Agent-dev/x", "repo absolute path"),
    ("cat case_tests/test_baseline/x", "answer directory token"),
    ("python -c \"import os; os.path.expanduser('~')\"", "home obtained, not typed"),
    ("python -c \"exec(open('x').read())\"", "code the guard never sees"),
    ("python -c \"import subprocess\"", "child the guard never sees"),
    ("cat $HOME/x", "shell expansion"),
    ("cat `pwd`/x", "command substitution"),
]

_FRICTION_SHAPES = [
    ("ls out > list.txt", "shell redirect"),
    ("cat out/x | head -3", "pipeline"),
    ("grep -n wall out/1f.json", "command allowlist"),
    ("python -c \"g = 'grade line at z=0'\"", "the word grade (elevation vocabulary)"),
]


def _profile_staging(tmp_path: Path, profile: str) -> Path:
    return build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / f"staging_{profile}",
        pilot_review_gate=False, guard_profile=profile,
    ).staging_root


@pytest.mark.parametrize("command, shape", _BOUNDARY_SHAPES)
def test_relaxed_profile_keeps_every_answer_boundary_shape_denied(
    tmp_path: Path, command: str, shape: str
):
    """⭐ Boundary parity — what makes the control arm admissible.

    The relaxed profile drops friction; if it ever drops boundary, the arm can
    no longer support the sentence "this reading was produced without reaching
    the answers", which is the sentence every draw's credibility rests on.
    """
    for profile in ("strict", "relaxed"):
        staging = _profile_staging(tmp_path, profile)
        proc = _hook(staging, command)
        assert proc.returncode != 0, f"{shape} was ALLOWED under {profile}"


@pytest.mark.parametrize("command, shape", _FRICTION_SHAPES)
def test_relaxed_profile_actually_unlocks_the_measured_friction(
    tmp_path: Path, command: str, shape: str
):
    """The paired positive: each row is friction MEASURED to cost real attempts.

    Without this half the profile could be a no-op and the control arm would
    silently be a second copy of the strict arm — the same "reported the
    treatment, ran the control" failure the --resume refusal guards against.
    """
    strict = _profile_staging(tmp_path, "strict")
    relaxed = _profile_staging(tmp_path, "relaxed")
    assert _hook(strict, command).returncode != 0, f"{shape} was not friction to begin with"
    assert _hook(relaxed, command).returncode == 0, f"{shape} still denied under relaxed"


def test_default_guard_profile_is_observe_and_records_what_it_did_not_enforce(tmp_path: Path):
    """⭐ CLAUDE.md §0.4#1 lock — the ONE guard lock kept under §0.4#4.

    Not a scaffolding-detail lock: it pins the ratified governance decision
    itself. If the default silently reverts to `strict`, the next draw pays
    friction again and the draw gets misattributed — which is exactly the
    failure this batch has already spent eight draws on. Two properties, both
    load-bearing:

    1. the shipped default is `observe` (nobody has to remember a flag), and
    2. a call strict WOULD have denied runs anyway, while the log still carries
       strict's verdict as `shadow_decision` — so the friction measurement is
       collected without any reader paying for it.
    """
    staging = build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / "staging", pilot_review_gate=False
    ).staging_root
    assert (staging.parent / f"{staging.name}.audit" / "guard_profile").read_text(
        encoding="utf-8"
    ).strip() == "observe"

    boundary_shape = 'python -c "open(\'../gt\' + \'.json\')"'
    proc = _hook(staging, boundary_shape)
    assert proc.returncode == 0, f"observe must not enforce, got: {proc.stderr}"

    log = (staging.parent / f"{staging.name}.audit" / "access_log.jsonl").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    entry = json.loads(log[-1])
    assert entry["guard_profile"] == "observe"
    assert entry["decision"] == "allow", "the log must say what happened"
    assert entry["shadow_decision"] == "deny", "…and what strict would have said"
    assert entry["shadow_reason"]


def test_guard_profile_marker_is_outside_the_reader_writable_surface(tmp_path: Path):
    """Same rule as the session id: the audited party must not be able to grant
    itself a weaker policy by writing a file it is allowed to write."""
    staging = _profile_staging(tmp_path, "relaxed")
    marker = staging.parent / f"{staging.name}.audit" / "guard_profile"
    assert marker.read_text(encoding="utf-8") == "relaxed"
    assert staging not in marker.parents


@pytest.mark.parametrize("value", ["", "RELAXED", "relaxed\n\nextra", "strict", "garbage"])
def test_unrecognised_profile_marker_fails_closed_to_strict(tmp_path: Path, value: str):
    """Fail-closed: anything that is not exactly "relaxed" is strict.

    A truncated or corrupted marker must not be able to open the boundary —
    note "relaxed\\n" alone IS accepted (the reader strips), but any other
    content is not.
    """
    staging = _profile_staging(tmp_path, "strict")
    marker = staging.parent / f"{staging.name}.audit" / "guard_profile"
    marker.write_text(value, encoding="utf-8")
    assert _hook(staging, "ls out > x.txt").returncode != 0, f"{value!r} opened the gate"


def test_build_rejects_an_unknown_guard_profile(tmp_path: Path):
    with pytest.raises(ValueError, match="unknown guard profile"):
        build_isolation_workspace(
            CASE_DIR, staging_root=tmp_path / "staging", guard_profile="off"
        )


def test_access_log_stamps_which_profile_judged_each_call(tmp_path: Path):
    """Without this stamp a relaxed log is indistinguishable from a strict one
    after the fact — and comparing the two logs line for line is the entire
    method of the experiment."""
    staging = _profile_staging(tmp_path, "relaxed")
    _hook(staging, "ls out")
    entry = json.loads(_access_log(staging).read_text(encoding="utf-8").splitlines()[-1])
    assert entry["guard_profile"] == "relaxed"


def test_no_pilot_gate_kickoff_states_an_explicit_override(tmp_path: Path):
    """The control-arm kickoff must CONTRADICT the staged skill doc out loud.

    Editing the staged copy of session_kickoff.md instead would make the run
    unauditable against the committed skill, and leaving the contradiction
    silent is the D1 shape this repo has already been bitten by.
    """
    staging = _profile_staging(tmp_path, "strict")
    text = (staging / "kickoff_prompt.md").read_text(encoding="utf-8")
    assert "NO review point" in text
    assert "overriding the pilot-review step" in text
    assert "ONE pilot approval gate" not in text
    gated = build_isolation_workspace(CASE_DIR, staging_root=tmp_path / "gated").staging_root
    assert "ONE pilot approval gate" in (gated / "kickoff_prompt.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# F-61 (2026-08-18) — unlocking `|` moved the friction one layer down instead of
# removing it. The relaxed profile let the pipeline through the STRUCTURE check
# and then handed the whole token list — `|`, `tail`, `-300` included — to the
# per-command checks, so the probe wrapper reported "unknown probe parameter
# --batch" for a call the kickoff itself teaches.
#
# Measured cost: the control-arm reader wrote SEVEN CV request files, hit this on
# its first real measurement call, and did the remaining five images by eye. The
# arm designed to remove this class of friction was voided by a new instance of
# it, authored by the orchestrator.
#
# ⭐ The lesson these locks encode: verifying "what must stay blocked is still
# blocked" is only half a verification. The other half — "what must now work
# actually works, end to end" — is the half that was skipped.
# ---------------------------------------------------------------------------


def _relaxed_staging(tmp_path: Path) -> Path:
    staging = build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / "staging",
        pilot_review_gate=False, guard_profile="relaxed",
    ).staging_root
    # The guard validates a --batch file's CONTENTS, so the fixture has to
    # provide a real one — a missing file would make these locks pass or fail
    # for the wrong reason.
    (staging / "requests").mkdir(exist_ok=True)
    (staging / "requests" / "t.json").write_text(
        json.dumps({"requests": [{"id": "a", "tool": "crop_zoom", "args": {
            "image": "case_data/1f_view.png", "out_dir": "out/cv",
            "bbox": [200, 200, 600, 500], "scale": 2.0}}]}),
        encoding="utf-8",
    )
    return staging


@pytest.mark.parametrize(
    "command, shape",
    [
        ("python tools/run_cv_probe.py --batch requests/t.json", "batch, no pipeline"),
        ("python tools/run_cv_probe.py --batch requests/t.json 2>&1 | tail -300", "batch + 2>&1 + pipe (the exact F-61 repro)"),
        ("python tools/run_cv_probe.py --batch requests/t.json | tail -5", "batch + pipe"),
        ("python tools/run_cv_probe.py --tool crop_zoom --image case_data/1f_view.png --out-dir out/cv | tail -5", "direct form + pipe"),
        ("cat out/x.json | head -3", "read-only pipeline"),
    ],
)
def test_relaxed_profile_lets_a_piped_probe_call_through(tmp_path: Path, command: str, shape: str):
    """The half of the verification that was skipped: the measurement path works.

    Every row is a form the kickoff or cv_toolbox actively teaches. A guard that
    allows the operator but then misreads the command is indistinguishable, from
    the reader's side, from a guard that forbids it.
    """
    staging = _relaxed_staging(tmp_path)
    proc = _hook(staging, command)
    assert proc.returncode == 0, f"{shape} denied: {proc.stderr}"


@pytest.mark.parametrize(
    "command, shape",
    [
        ("ls out | python -c \"exec(open('x').read())\"", "dynamic exec in the SECOND segment"),
        ("ls out | python -c \"import subprocess\"", "child process in the second segment"),
        ("ls out | cat ../../case_tests/test_baseline/gt/sm21_anchor/gt.json", "answers in the second segment"),
        ("ls out > /workspaces/EnergyPlus-Agent-dev/leak.txt", "redirect target outside staging"),
        ("ls out | python -c \"import os; os.path.expanduser('~')\"", "home obtained in the second segment"),
    ],
)
def test_every_pipeline_segment_is_checked_not_just_the_first(
    tmp_path: Path, command: str, shape: str
):
    """⭐ The paired negative, and the reason the fix splits instead of truncating.

    Checking only the head segment would have fixed F-61 in one line AND opened a
    hole: `cat x | python -c '<code>'` would put code past the exec scan — the
    same "code the guard never saw" shape EXEC_DENY_DYNAMIC exists to close. Each
    row here fails if a future edit takes the one-line route.
    """
    staging = _relaxed_staging(tmp_path)
    assert _hook(staging, command).returncode != 0, f"{shape} was allowed through"


def test_strict_profile_pipeline_handling_is_unchanged_by_the_f61_fix(tmp_path: Path):
    """The fix must not leak into strict: there, `|` never reaches segmentation
    because the structure check refuses it first."""
    staging = build_isolation_workspace(
        CASE_DIR, staging_root=tmp_path / "strict", guard_profile="strict",
    ).staging_root
    (staging / "requests").mkdir(exist_ok=True)
    (staging / "requests" / "t.json").write_text('{"requests": []}', encoding="utf-8")
    proc = _hook(staging, "python tools/run_cv_probe.py --batch requests/t.json | tail -5")
    assert proc.returncode != 0
    assert "compound shell token forbidden" in proc.stderr, proc.stderr
