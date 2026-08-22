"""S1 (2026-08-22): multi-plan world-transform exit snap locks.

The converter quantises on its declared native grid BEFORE the per-view world
affine; two plan views that draw the same outline at different sheet positions
therefore evaluate the same mathematical world coordinate through two different
float sums and can differ by pure re-association noise (measured 3.55e-15 m on
sm25).  Multi-floor consumers compare footprints/extents bitwise, so
``gt_extraction._transform`` snaps its world exit onto the signed noise-criterion
grid (1e-9 m, ``tarch_normalize._PAIRING_Z_TOLERANCE_M``) — but only when the
manifest carries more than one plan view: the single-plan path stays
byte-frozen (signed single-floor answers must rebuild identically).

These tests prove their own premise: the neutered run must exhibit the disease
the snap removes, a real 1 mm difference must survive it, and the single-plan
path must not take it at all.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.gt_extraction import (ExtractionError, ExtractionInputs,
                                           _plan_world_snap_grid, _transform,
                                           _WORLD_SNAP_GRID_M, extract_gt_v3)
from src.agent.judge.gt_manifest import load_gt_tooling_config
from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from tests.test_gt_extraction import (_manifest_from_payload, _translated_mm_dxf,
                                      _translated_mm_manifest)

RING = [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (2.0, 1.0), (2.0, 3.0), (0.0, 3.0)]


def _tooling():
    return load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml",
                                  REPO_ROOT / "src/configs/correction.yaml")


def _extract(tmp_path, manifest):
    return extract_gt_v3(ExtractionInputs(tmp_path / "translated-mm.dxf", manifest, _tooling(),
                                          compute_gt_implementation_hashes(REPO_ROOT)))


def _family_extents(doc, family):
    extents = {}
    for floor in doc.floors:
        segments = [s for s in floor.boundary_segments if s.facade_family == family]
        extents[floor.id] = (min(s.world_along_interval.lo for s in segments),
                             max(s.world_along_interval.hi for s in segments))
    return extents


def test_translated_two_floor_plans_carry_bit_identical_world_geometry(tmp_path):
    """Lock 1: same outline on two sheet positions -> identical fingerprint/extent."""
    path = tmp_path / "translated-mm.dxf"
    _translated_mm_dxf(path, RING)
    doc = _extract(tmp_path, _translated_mm_manifest(path, RING))
    fingerprints = {floor.id: floor.footprint_fingerprint for floor in doc.floors}
    rings = {floor.id: floor.footprint.exterior.vertices for floor in doc.floors}
    assert len(fingerprints) == 2 and len(set(fingerprints.values())) == 1
    assert rings["F1"] == rings["F2"]
    for family in ("North", "South", "East", "West"):
        extents = _family_extents(doc, family)
        assert extents["F1"] == extents["F2"], family


def test_neuter_unwires_the_snap_and_restores_the_disease(tmp_path, monkeypatch):
    """Premise self-proof: without the snap this fixture really does go noisy."""
    monkeypatch.setenv("GT_NEUTER_WORLD_SNAP", "1")
    path = tmp_path / "translated-mm.dxf"
    _translated_mm_dxf(path, RING)
    doc = _extract(tmp_path, _translated_mm_manifest(path, RING))
    fingerprints = {floor.id: floor.footprint_fingerprint for floor in doc.floors}
    assert len(set(fingerprints.values())) == 2, "neutered fixture must exhibit the disease"
    disagreeing = [family for family in ("North", "South", "East", "West")
                   if _family_extents(doc, family)["F1"] != _family_extents(doc, family)["F2"]]
    assert disagreeing, "neutered fixture must disagree on at least one facade extent"


def test_single_plan_manifest_takes_no_snap(tmp_path):
    """T1 guard: the frozen single-plan path must not take the snap at all."""
    path = tmp_path / "translated-mm.dxf"
    _translated_mm_dxf(path, RING)
    manifest = _translated_mm_manifest(path, RING)
    both = _plan_world_snap_grid(manifest)
    assert both == _WORLD_SNAP_GRID_M
    single = _manifest_from_payload({**manifest.model_dump(mode="python"),
                                     "views": [v for v in manifest.model_dump(mode="python")["views"]
                                               if v.get("floor_id") == "F1"],
                                     "floors": [f for f in manifest.model_dump(mode="python")["floors"]
                                                if f["id"] == "F1"]})
    assert _plan_world_snap_grid(single) is None
    assert _plan_world_snap_grid(None) is None


def test_snap_grid_reuses_the_signed_noise_criterion():
    """The snap value is not a new number: it is the signed pairing tolerance."""
    assert _WORLD_SNAP_GRID_M == tn._PAIRING_Z_TOLERANCE_M == 1e-9


class _Affine:
    def __init__(self, m00, m01, m02, m10, m11, m12):
        self.m00, self.m01, self.m02 = m00, m01, m02
        self.m10, self.m11, self.m12 = m10, m11, m12


class _View:
    def __init__(self, affine):
        self.world_from_source_m = affine


# The sm25 sheet offsets: two affines mapping the same native corner (F1
# -25469.0 mm <-> F2 29511.8 mm, shared y 42213.6) to the same world point.
F1_VIEW = _View(_Affine(0.001, 0.0, 30.469, 0.0, 0.001, -28.213600000000003))
F2_VIEW = _View(_Affine(0.001, 0.0, -24.511800000000004, 0.0, 0.001, -28.213600000000003))


def test_transform_collapses_noise_but_keeps_a_real_1mm_difference():
    """Lock 4 (unit): noise collapses bitwise; a real 1 mm offset survives."""
    a = _transform((-25469.0, 42213.6), F1_VIEW, 1.0, _WORLD_SNAP_GRID_M)
    b = _transform((29511.8, 42213.6), F2_VIEW, 1.0, _WORLD_SNAP_GRID_M)
    assert a == b == (5.0, 14.0)
    shifted = _View(_Affine(0.001, 0.0, -24.511800000000004 + 0.001, 0.0, 0.001,
                            -28.213600000000003))
    c = _transform((29511.8, 42213.6), shifted, 1.0, _WORLD_SNAP_GRID_M)
    assert c != a
    assert abs((c[0] - a[0]) - 0.001) < 1e-12 and c[1] == a[1]


def test_real_cross_floor_offset_fails_closed_at_extraction(tmp_path):
    """Lock 4 (extraction): a >tolerance offset must trip the existing ring gate."""
    path = tmp_path / "translated-mm.dxf"
    _translated_mm_dxf(path, RING)
    manifest = _translated_mm_manifest(path, RING)
    raw = manifest.model_dump(mode="python")
    for view in raw["views"]:
        if view.get("id") == "plan-F2":
            view["world_from_source_m"]["m02"] += 0.002
    shifted = _manifest_from_payload(raw)
    with pytest.raises(ExtractionError, match="dxf_profile_floor_footprint_mismatch"):
        _extract(tmp_path, shifted)
