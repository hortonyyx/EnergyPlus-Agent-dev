"""C2 B-M §6: `reading.view_manifest_coverage` gate① check — INVARIANT, always
BLOCK on fail regardless of run_profile (three states x every run_profile)."""

from __future__ import annotations

import pytest

from src.agent.execution.view_manifest import build_view_manifest
from src.validator.checks.schema import Disposition, disposition
from src.validator.checks.view_manifest import CHECK_ID, check_view_manifest_coverage

SM21 = "case_tests/e2e_tests/sm21_anchor"
_ALL_PROFILES = ("exploratory", "dev", "golden", "regression")


def _manifest():
    return build_view_manifest(SM21)


def _blocking(report) -> bool:
    return any(r.check_id == CHECK_ID for r in report.blocking())


@pytest.mark.parametrize("run_profile", _ALL_PROFILES)
def test_manifest_missing_blocks_regardless_of_profile(run_profile):
    rep = check_view_manifest_coverage(None, set(), run_profile=run_profile)
    assert _blocking(rep)


@pytest.mark.parametrize("run_profile", _ALL_PROFILES)
def test_missing_required_view_blocks_regardless_of_profile(run_profile):
    m = _manifest()
    produced = set(m.expected_output_ids()) - {"South_view"}
    rep = check_view_manifest_coverage(m, produced, run_profile=run_profile)
    assert _blocking(rep)
    result = next(r for r in rep.results if r.check_id == CHECK_ID)
    assert "South_view" in result.evidence["missing_expected_output_ids"]


@pytest.mark.parametrize("run_profile", _ALL_PROFILES)
def test_extra_stem_blocks_regardless_of_profile(run_profile):
    m = _manifest()
    produced = set(m.expected_output_ids()) | {"bogus_extra"}
    rep = check_view_manifest_coverage(m, produced, run_profile=run_profile)
    assert _blocking(rep)
    result = next(r for r in rep.results if r.check_id == CHECK_ID)
    assert "bogus_extra" in result.evidence["extra_stems"]


@pytest.mark.parametrize("run_profile", _ALL_PROFILES)
def test_exact_match_passes_regardless_of_profile(run_profile):
    m = _manifest()
    produced = set(m.expected_output_ids())
    rep = check_view_manifest_coverage(m, produced, run_profile=run_profile)
    assert not rep.blocking()
    result = next(r for r in rep.results if r.check_id == CHECK_ID)
    assert disposition(result, run_profile=run_profile) == Disposition.INFO


def test_not_an_evidence_check_id_no_run_profile_carve_out():
    """r1 裁决: unlike EVIDENCE_CHECK_IDS, this check gets no `legacy_migrated`
    flag-instead-of-block softening — every FAIL is BLOCK, full stop."""
    from src.validator.checks.schema import is_evidence_check_id

    assert not is_evidence_check_id(CHECK_ID)
