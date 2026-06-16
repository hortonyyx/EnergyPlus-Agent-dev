"""M2b acceptance: geometry gate — closure/normals/pairing/coverage (build plan §2.1).

Includes the negative regression: forcing a reciprocal interior-wall pair to
Outdoors must make the coverage-completeness check fail (the hole the per-pair
gate + EP are blind to)."""

from __future__ import annotations

import copy
from pathlib import Path

from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry import build_geometry
from src.validator.checks.kernel import check_kernel
from src.validator.checks.schema import CheckStatus

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")


def _anchor_geom() -> CorrectedGeometry:
    return CorrectedGeometry.model_validate_json(
        (_ANCHOR / "1_correction" / "correction_geometry_snapped.json").read_text()
    )


def _blocking_ids(rep):
    return {r.check_id for r in rep.blocking()}


def test_clean_anchor_kernel_passes():
    bg = build_geometry(_anchor_geom())
    rep = check_kernel(bg)
    assert rep.passed, [r.message for r in rep.blocking()]
    # the rectangular coverage check actually ran (not skipped)
    cov = next(r for r in rep.results if r.check_id == "kernel.coverage_completeness")
    assert cov.status == CheckStatus.PASS


def test_coverage_hole_negative_regression():
    """Force a reciprocal interior-wall pair to Outdoors → coverage must fail."""
    bg = build_geometry(_anchor_geom())
    # find a reciprocal interior wall pair and break BOTH sides to Outdoors
    pair = None
    by_name = {s.name: s for s in bg.surfaces}
    for s in bg.surfaces:
        if s.stype == "Wall" and s.obc == "Surface" and s.obc_obj in by_name:
            pair = (s, by_name[s.obc_obj])
            break
    assert pair is not None, "anchor should have at least one interior wall pair"
    for s in pair:
        s.obc = "Outdoors"
        s.obc_obj = ""
    rep = check_kernel(bg)
    assert "kernel.coverage_completeness" in _blocking_ids(rep)


def test_inward_normal_negative_regression():
    bg = build_geometry(_anchor_geom())
    wall = next(s for s in bg.surfaces if s.stype == "Wall")
    wall.verts = wall.verts[::-1]  # reverse → flip normal inward
    rep = check_kernel(bg)
    assert "kernel.normals" in _blocking_ids(rep)


def test_spec_self_consistency_dangling_obc():
    bg = build_geometry(_anchor_geom())
    s = next(x for x in bg.surfaces if x.obc == "Surface")
    s.obc_obj = "Does_Not_Exist"
    rep = check_kernel(bg)
    assert "kernel.spec_self_consistency" in _blocking_ids(rep)


def test_undefined_zone_blocks():
    """A surface whose zone is not in bg.zones/zone_volumes must block (Codex M2)."""
    bg = build_geometry(_anchor_geom())
    target = bg.surfaces[0].zone
    for s in bg.surfaces:
        if s.zone == target:
            s.zone = "NoSuchZone"  # leave bg.zones / zone_volumes unchanged
    rep = check_kernel(bg)
    blocked = _blocking_ids(rep)
    assert "kernel.spec_self_consistency" in blocked or "kernel.zone_closure" in blocked


def test_pairing_gate_blocks_on_injected_issue():
    bg = build_geometry(_anchor_geom())
    rep = check_kernel(bg, interzone_issues=["injected: wall X has no reciprocal"])
    assert "kernel.pairing_gate" in _blocking_ids(rep)


def test_coverage_not_applicable_under_nonrect_profile():
    bg = build_geometry(_anchor_geom())
    rep = check_kernel(bg, capability_profile="nonrectangular")
    cov = next(r for r in rep.results if r.check_id == "kernel.coverage_completeness")
    assert cov.status == CheckStatus.NOT_APPLICABLE
    # not_applicable must not block (policy ≠ fact)
    assert "kernel.coverage_completeness" not in _blocking_ids(rep)


def test_golden_anchor_object_counts():
    """Golden: stable zone/surface/window counts (build plan §2.1 M2b golden)."""
    bg = build_geometry(_anchor_geom())
    assert len(dict.fromkeys(bg.zones)) == 19
    assert len(bg.surfaces) == 135
    assert len(bg.windows) == 16
