"""M4 acceptance: full-case validation baseline + policy paths (build plan §2.1 M4).

sm20_anchor is the positive baseline — every gate ① check over the on-disk case
must pass. Also covers confirmation_policy and the --intake-from downstream_only
scope, and the negative corpus (fixtures) wired through validate_case-style flow.
"""

from __future__ import annotations

from pathlib import Path

from src.agent.execution import (
    GeometryApproval,
    RunPolicy,
    validate_case,
)
from src.agent.execution.policy import ConfirmationPolicy, ValidationScope

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")


def test_sm20_anchor_positive_baseline():
    """Every per-stage gate ① passes on the clean sm20_anchor case."""
    res = validate_case(_ANCHOR)
    assert not res.blocked, res.blocking_summary
    # all the expected stages were validated
    assert "1_correction" in res.reports
    assert "2_modelling" in res.reports
    assert "4_mep" in res.reports
    # every report passes
    for key, rep in res.reports.items():
        assert rep.passed, f"{key} blocked: {[r.message for r in rep.blocking()]}"


def test_sm20_anchor_reports_writable(tmp_path):
    """write_reports emits *_checks.json without raising (smoke)."""
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    res = validate_case(case, write_reports=True)
    assert (case / "1_correction" / "correction_checks.json").exists()
    assert (case / "2_modelling" / "kernel_checks.json").exists()
    assert (case / "4_mep" / "mep_checks.json").exists()
    # A validation SUMMARY under a distinct name — never the M0 audit manifest.
    assert (case / "validation_manifest.json").exists()
    assert not (case / "run_manifest.json").exists()
    assert not res.blocked


def test_geometry_digest_computed():
    res = validate_case(_ANCHOR)
    assert res.geometry_digest is not None
    # unapproved by default
    assert res.geometry_approved is False


def test_confirmation_required_blocks_until_approved(tmp_path):
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    # required + unapproved → blocked even though all checks pass
    res = validate_case(case, policy=RunPolicy(
        confirmation_policy=ConfirmationPolicy.REQUIRED))
    assert res.blocked
    assert any("not approved" in s for s in res.blocking_summary)

    # approve the exact digest → no longer blocked
    GeometryApproval(digest=res.geometry_digest, actor="op").save(case)
    res2 = validate_case(case, policy=RunPolicy(
        confirmation_policy=ConfirmationPolicy.REQUIRED))
    assert not res2.blocked
    assert res2.geometry_approved


def test_optional_policy_never_blocks_on_approval():
    res = validate_case(_ANCHOR, policy=RunPolicy(
        confirmation_policy=ConfirmationPolicy.OPTIONAL))
    assert not res.blocked  # optional never blocks on missing approval


def test_existing_manifest_not_overwritten_by_validate_case(tmp_path):
    """write_reports must not fabricate/overwrite the M0 audit run_manifest.json."""
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    (case / "run_manifest.json").write_text('{"case":"sm20_anchor","stages":{}}')
    validate_case(case, write_reports=True)
    # the real audit manifest is untouched; the summary went elsewhere
    assert (case / "run_manifest.json").read_text().strip() == \
        '{"case":"sm20_anchor","stages":{}}'
    assert (case / "validation_manifest.json").exists()


# --------------------------------------------------------------------------- #
# H1 regression: full-scope blocks on every missing required artifact
# --------------------------------------------------------------------------- #
def test_empty_case_blocks_not_silent_pass(tmp_path):
    case = tmp_path / "empty"
    case.mkdir()
    res = validate_case(case)
    assert res.blocked, "an empty case must NOT pass silently"
    # every required stage flagged missing
    for stage in ("0_reading", "1_correction", "2_modelling", "3_split_pairing",
                  "4_mep", "5_intakeoutput"):
        assert stage in res.reports


def test_missing_single_artifact_blocks(tmp_path):
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    (case / "4_mep" / "mep_output.json").unlink()
    res = validate_case(case)
    assert res.blocked
    assert any("4_mep" in s and "missing" in s for s in res.blocking_summary)


def test_missing_geometry_artifact_no_bogus_digest(tmp_path):
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    (case / "2_modelling" / "building_geometry.json").unlink()
    res = validate_case(case)
    assert res.blocked
    assert res.geometry_digest is None  # no digest from a {} fallback


def test_bad_geometry_specs_blocks_no_digest(tmp_path):
    """Stale/garbage geometry_specs.md must block + no approval digest (re-verify High)."""
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    (case / "3_split_pairing" / "geometry_specs.md").write_text(
        "garbage geometry specs, not the generated surface graph")
    res = validate_case(case)
    assert res.blocked
    assert res.geometry_digest is None  # never bind a digest to unchecked bytes
    assert "3_split_pairing" in res.reports and not res.reports["3_split_pairing"].passed


def test_bad_building_geometry_blocks_no_digest(tmp_path):
    """Stale/garbage building_geometry.json must block + no digest (re-verify High)."""
    import json as _json
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    (case / "2_modelling" / "building_geometry.json").write_text(
        _json.dumps({"zones": ["BogusZone"], "surfaces": [], "windows": []}))
    res = validate_case(case)
    assert res.blocked
    assert res.geometry_digest is None
    assert "kernel.artifact_consistency" in {
        r.check_id for r in res.reports["2_modelling"].blocking()}


# EP run outputs (eplusout.*) are gitignored, so these tests synthesize the .end
# in a tmp copy rather than depending on a live/committed one — hermetic on a
# fresh clone / CI.
_CLEAN_END = "EnergyPlus Completed Successfully-- 6 Warning; 0 Severe Errors; ...\n"


def _anchor_copy_with_ep(tmp_path, end_text: str | None):
    import shutil

    case = tmp_path / "sm20_anchor"
    shutil.copytree(_ANCHOR, case)
    end = case / "EP" / "EP_run" / "eplusout.end"
    end.parent.mkdir(parents=True, exist_ok=True)
    if end_text is None:
        end.unlink(missing_ok=True)
    else:
        end.write_text(end_text)
    return case


def test_require_ep_blocks_when_no_run(tmp_path):
    case = _anchor_copy_with_ep(tmp_path, None)  # no EP run
    res = validate_case(case, policy=RunPolicy(require_ep=True))
    assert res.blocked
    assert any("eplusout.end" in s for s in res.blocking_summary)


def test_require_ep_passes_on_clean_run(tmp_path):
    case = _anchor_copy_with_ep(tmp_path, _CLEAN_END)
    res = validate_case(case, policy=RunPolicy(require_ep=True))
    assert not res.blocked
    assert res.reports["downstream"].passed


def test_anchor_with_clean_ep_run_validates(tmp_path):
    case = _anchor_copy_with_ep(tmp_path, _CLEAN_END)
    res = validate_case(case)  # require_ep defaults False
    assert "downstream" in res.reports and res.reports["downstream"].passed
    assert not res.blocked


def test_downstream_only_scope_skips_geometry():
    """--intake-from: only the supplied IntakeOutput is validated."""
    res = validate_case(_ANCHOR, policy=RunPolicy(
        validation_scope=ValidationScope.DOWNSTREAM_ONLY))
    assert set(res.reports) == {"5_intakeoutput"}
    assert not res.blocked
    assert res.geometry_digest is None  # geometry not validated in this scope
