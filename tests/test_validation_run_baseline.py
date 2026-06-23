"""M4 acceptance: per-run validation baseline + policy paths (build plan §2.1 M4).

sm20_anchor's golden RUN (run_2026-06-15_baseline) is the positive baseline —
every gate ① check over its on-disk products must pass. A case = materials
(case_data); a run = a self-contained <case>/run_<note>/ holding 0_reading + 1..5
+ EP. validate_case takes the RUN dir; the case (testdata) is its parent.
"""

from __future__ import annotations

from pathlib import Path

from src.agent.execution import (
    GeometryApproval,
    RunPolicy,
    run_meta_path,
    validate_case,
)
from src.agent.execution.policy import ConfirmationPolicy, ValidationScope

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN_NAME = "run_2026-06-15_baseline"
_RUN = _ANCHOR / _RUN_NAME


def _copy(tmp_path):
    """Copy the anchor case to tmp; return (case_dir, run_dir)."""
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    return case, case / _RUN_NAME


def test_sm20_anchor_positive_baseline():
    """Every per-stage gate ① passes on the clean sm20_anchor golden run."""
    res = validate_case(_RUN)
    assert not res.blocked, res.blocking_summary
    assert res.case == "sm20_anchor"  # case = parent, not the run folder
    assert "1_correction" in res.reports
    assert "2_modelling" in res.reports
    assert "4_mep" in res.reports
    for key, rep in res.reports.items():
        assert rep.passed, f"{key} blocked: {[r.message for r in rep.blocking()]}"


def test_sm20_anchor_reports_writable(tmp_path):
    _case, run = _copy(tmp_path)
    res = validate_case(run, write_reports=True)
    assert (run / "1_correction" / "correction_checks.json").exists()
    assert (run / "2_modelling" / "kernel_checks.json").exists()
    assert (run / "4_mep" / "mep_checks.json").exists()
    # validation SUMMARY into _run under a distinct name (not the audit manifest)
    assert run_meta_path(run, "validation_manifest.json").exists()
    assert not (run / "validation_manifest.json").exists()
    assert not (run / "run_manifest.json").exists()
    assert not run_meta_path(run, "run_manifest.json").exists()
    assert not res.blocked


def test_geometry_digest_computed():
    res = validate_case(_RUN)
    assert res.geometry_digest is not None
    assert res.geometry_approved is False


def test_confirmation_required_blocks_until_approved(tmp_path):
    _case, run = _copy(tmp_path)
    res = validate_case(run, policy=RunPolicy(
        confirmation_policy=ConfirmationPolicy.REQUIRED))
    assert res.blocked
    assert any("not approved" in s for s in res.blocking_summary)

    # approval is per-run → save into the run dir
    GeometryApproval(digest=res.geometry_digest, actor="op").save(run)
    res2 = validate_case(run, policy=RunPolicy(
        confirmation_policy=ConfirmationPolicy.REQUIRED))
    assert not res2.blocked
    assert res2.geometry_approved


def test_optional_policy_never_blocks_on_approval():
    res = validate_case(_RUN, policy=RunPolicy(
        confirmation_policy=ConfirmationPolicy.OPTIONAL))
    assert not res.blocked


def test_existing_manifest_not_overwritten_by_validate_case(tmp_path):
    _case, run = _copy(tmp_path)
    (run / "run_manifest.json").write_text('{"case":"sm20_anchor","stages":{}}')
    validate_case(run, write_reports=True)
    assert (run / "run_manifest.json").read_text().strip() == \
        '{"case":"sm20_anchor","stages":{}}'
    assert run_meta_path(run, "validation_manifest.json").exists()
    assert not (run / "validation_manifest.json").exists()


# --------------------------------------------------------------------------- #
# H1 regression: full-scope blocks on every missing required artifact
# --------------------------------------------------------------------------- #
def test_empty_run_blocks_not_silent_pass(tmp_path):
    run = tmp_path / "case" / "run_empty"
    run.mkdir(parents=True)
    res = validate_case(run)
    assert res.blocked, "an empty run must NOT pass silently"
    for stage in ("0_reading", "1_correction", "2_modelling", "3_split_pairing",
                  "4_mep", "5_intakeoutput"):
        assert stage in res.reports


def test_missing_single_artifact_blocks(tmp_path):
    _case, run = _copy(tmp_path)
    (run / "4_mep" / "mep_output.json").unlink()
    res = validate_case(run)
    assert res.blocked
    assert any("4_mep" in s and "missing" in s for s in res.blocking_summary)


def test_missing_geometry_artifact_no_bogus_digest(tmp_path):
    _case, run = _copy(tmp_path)
    (run / "2_modelling" / "building_geometry.json").unlink()
    res = validate_case(run)
    assert res.blocked
    assert res.geometry_digest is None


def test_bad_geometry_specs_blocks_no_digest(tmp_path):
    _case, run = _copy(tmp_path)
    (run / "3_split_pairing" / "geometry_specs.md").write_text(
        "garbage geometry specs, not the generated surface graph")
    res = validate_case(run)
    assert res.blocked
    assert res.geometry_digest is None
    assert "3_split_pairing" in res.reports and not res.reports["3_split_pairing"].passed


def test_bad_building_geometry_blocks_no_digest(tmp_path):
    import json as _json

    _case, run = _copy(tmp_path)
    (run / "2_modelling" / "building_geometry.json").write_text(
        _json.dumps({"zones": ["BogusZone"], "surfaces": [], "windows": []}))
    res = validate_case(run)
    assert res.blocked
    assert res.geometry_digest is None
    assert "kernel.artifact_consistency" in {
        r.check_id for r in res.reports["2_modelling"].blocking()}


# EP run outputs (eplusout.*) are gitignored, so these synthesize the .end in a
# tmp copy — hermetic on a fresh clone / CI.
_CLEAN_END = "EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors; ...\n"


def _run_copy_with_ep(tmp_path, end_text: str | None):
    _case, run = _copy(tmp_path)
    end = run / "EP" / "EP_run" / "eplusout.end"
    end.parent.mkdir(parents=True, exist_ok=True)
    if end_text is None:
        end.unlink(missing_ok=True)
    else:
        end.write_text(end_text)
    return run


def test_require_ep_blocks_when_no_run(tmp_path):
    run = _run_copy_with_ep(tmp_path, None)
    res = validate_case(run, policy=RunPolicy(require_ep=True))
    assert res.blocked
    assert any("eplusout.end" in s for s in res.blocking_summary)


def test_require_ep_passes_on_clean_run(tmp_path):
    run = _run_copy_with_ep(tmp_path, _CLEAN_END)
    res = validate_case(run, policy=RunPolicy(require_ep=True))
    assert not res.blocked
    assert res.reports["downstream"].passed


def test_run_with_clean_ep_validates(tmp_path):
    run = _run_copy_with_ep(tmp_path, _CLEAN_END)
    res = validate_case(run)
    assert "downstream" in res.reports and res.reports["downstream"].passed
    assert not res.blocked


def test_downstream_only_scope_skips_geometry():
    res = validate_case(_RUN, policy=RunPolicy(
        validation_scope=ValidationScope.DOWNSTREAM_ONLY))
    assert set(res.reports) == {"5_intakeoutput"}
    assert not res.blocked
    assert res.geometry_digest is None


# --- sm21_anchor: 2-floor golden RUN (run_2026-06-16_opus_e2e) -----------------
# A 2-storey office with a differing F1 (3 N offices + corridor + 3 S) vs F2
# (2 N meeting + corridor + 4 S). Fresh cold-agent reading (no reuse), gate① all
# green, EP 0 severe. Counts are the regression anchor; gt is judge-only.
_ANCHOR_21 = Path("case_tests/e2e_tests/sm21_anchor")
_RUN_21 = _ANCHOR_21 / "run_2026-06-16_opus_e2e"


def test_sm21_anchor_positive_baseline():
    """Every per-stage gate ① passes on the clean sm21_anchor golden run."""
    res = validate_case(_RUN_21, policy=RunPolicy(require_ep=True))
    assert not res.blocked, res.blocking_summary
    assert res.case == "sm21_anchor"
    for key, rep in res.reports.items():
        assert rep.passed, f"{key} blocked: {[r.message for r in rep.blocking()]}"


def test_sm21_anchor_golden_counts():
    """Frozen geometry counts: 14 zones / 100 surfaces / 15 windows (== gt)."""
    import json

    bg = json.loads(
        (_RUN_21 / "2_modelling" / "building_geometry.json").read_text())
    assert len(bg["zones"]) == 14
    assert len(bg["surfaces"]) == 100
    assert len(bg["windows"]) == 15


def test_sm21_anchor_ep_clean():
    """EP completed with zero severe errors."""
    from src.runner.runner import read_ep_end

    end = read_ep_end(_RUN_21 / "EP" / "EP_run")
    assert end is not None and end["completed"] and end["severe"] == 0
