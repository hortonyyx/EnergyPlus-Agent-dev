"""T-junction interior-edge pairing locks (segment_score T-junction fix, 2026-07-27).

A real building is rarely a conforming mesh: a long corridor wall faces several
rooms of unequal depth and is split into collinear sub-edges on the opposite
side.  These locks pin the exact-coverage pairing contract on both the GT
(answer) and correction (product) sides, including the four "still red" failure
modes (gap / overlap / imprecise endpoint) that separate a legal T-junction from
a real topology break.  The two pre-existing invariant locks live in
``test_c2_b4b_phase_b`` and are intentionally not duplicated here.
"""
from __future__ import annotations

from types import SimpleNamespace

import copy

import pytest

from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.schema import CellV3, CorrectedGeometryV3, FloorV3, FootprintRing
from src.agent.judge.gt import load_gt_document
from src.agent.judge.gt_schema import compute_gt_v3_content_sha256, validate_gt_v3
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError
from src.agent.judge.segment_score import (
    assign_plan_segments, extract_correction_plan_segments, extract_gt_plan_segments, score_plan_segments)


def _gt_floor(fid, footprint, zones):
    ring = SimpleNamespace(exterior=SimpleNamespace(vertices=footprint))
    return SimpleNamespace(id=fid, footprint=ring, boundary_segments=(),
                           zones=[SimpleNamespace(id=zid, polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=poly))) for zid, poly in zones])


def _correction(fid, footprint, cells):
    floor = SimpleNamespace(id=fid, footprint=SimpleNamespace(vertices=footprint),
                            cells=[SimpleNamespace(id=cid, polygon=poly) for cid, poly in cells])
    return SimpleNamespace(floors=[floor])


# One long corridor wall (A) faced by four collinear short walls (B,C,D,E).
# A's single unsplit east edge [0,8] at x=2 is tiled into four sub-intervals.
LONG_FACING_FOUR = {
    "footprint": [(0., 0.), (4., 0.), (4., 8.), (0., 8.)],
    "zones": [("A", [(0., 0.), (2., 0.), (2., 8.), (0., 8.)]),
              ("B", [(2., 0.), (4., 0.), (4., 2.), (2., 2.)]),
              ("C", [(2., 2.), (4., 2.), (4., 4.), (2., 4.)]),
              ("D", [(2., 4.), (4., 4.), (4., 6.), (2., 6.)]),
              ("E", [(2., 6.), (4., 6.), (4., 8.), (2., 8.)])],
}


def test_lock1_t_junction_long_edge_faces_four_short_edges():
    """Lock 1: a long edge facing four collinear short edges is cut into four segments.

    The four rooms B/C/D/E also share conforming horizontal walls with each
    other (B-C, C-D, D-E), so the floor has seven interior segments total --
    four T-junction segments on the corridor wall plus three conforming ones.
    """
    segments = extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", LONG_FACING_FOUR["footprint"], LONG_FACING_FOUR["zones"])]))
    interior = [item for item in segments if not item.exterior]
    corridor = {(item.p1, item.p2): item.zone_ids for item in interior if "A" in item.zone_ids}
    assert corridor[((2., 0.), (2., 2.))] == ("A", "B")
    assert corridor[((2., 2.), (2., 4.))] == ("A", "C")
    assert corridor[((2., 4.), (2., 6.))] == ("A", "D")
    assert corridor[((2., 6.), (2., 8.))] == ("A", "E")
    assert {item.zone_ids for item in interior if "A" not in item.zone_ids} == {("B", "C"), ("C", "D"), ("D", "E")}
    assert len(interior) == 7


def test_lock2_real_sm24_gt_extracts_without_raise_and_matches_hand_computed_count():
    """Lock 2: the real signed-off sm24 GT no longer rejects; segment count is hand-computed.

    Hand computation (zone adjacencies on F1): eleven single-wall adjacencies
    (z0-z1, z0-z4, z0-z5, z1-z2, z1-z5, z2-z3, z2-z5, z3-z5, z3-z7, z5-z7,
    z6-z7) plus the C-shaped corridor wrapping z4 on three walls (z4-z5) and
    meeting z6 on two walls (z5-z6) -> 11 + 3 + 2 = 16 interior segments.
    """
    gt = load_gt_document("sm24_anchor")
    segments = extract_gt_plan_segments(gt)
    interior = [item for item in segments if not item.exterior]
    counts = {}
    for item in interior:
        counts[item.zone_ids] = counts.get(item.zone_ids, 0) + 1
    assert sum(counts.values()) == 16
    assert counts[("z4", "z5")] == 3   # corridor wraps the z4 notch on three walls
    assert counts[("z5", "z6")] == 2   # corridor meets z6 on two walls
    # The previously-unpairable long corridor west wall is now tiled, not rejected.
    corridor_west = [item for item in interior if item.zone_ids in (("z0", "z5"), ("z1", "z5"), ("z2", "z5"))]
    assert {tuple(round(c, 6) for c in item.p1) for item in corridor_west} == {(4.18, 3.44), (4.18, 8.06), (4.18, 13.0)}
    assert len(corridor_west) == 3


def test_lock3_coverage_gap_is_still_red():
    """Lock 3 (R-3): a sub-interval with no collinear cover is a topology hole, not a T-junction."""
    footprint = [(0., 0.), (4., 0.), (4., 10.), (0., 10.)]
    zones = [("A", [(0., 0.), (2., 0.), (2., 10.), (0., 10.)]),  # long east edge [0,10] at x=2
             ("B", [(2., 0.), (4., 0.), (4., 5.), (2., 5.)]),    # faces [0,5]
             ("C", [(2., 6.), (4., 6.), (4., 10.), (2., 10.)])]  # faces [6,10] -> gap (5,6)
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)]))
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_lock4_coverage_overlap_is_still_red():
    """Lock 4 (R-3): two zones claiming the same interior edge (over-coverage) is rejected.

    A purely area-overlapping pair would also create uncovered edges (holes), so
    to isolate the over-coverage guard we give two zones the identical interior
    edge: the west wall x=2 [0,4] is traversed by both B and C on the same side,
    so a single sub-interval has two reverse owners.  Because C is a full copy of
    B, the same duplication also lands on the exterior edges (RW-3 guard); either
    guard rejects it, and which one fires first is a traversal-order detail, so
    the lock accepts either reason.  See test_l_e for the pure exterior-only form.
    """
    footprint = [(0., 0.), (4., 0.), (4., 4.), (0., 4.)]
    zones = [("A", [(0., 0.), (2., 0.), (2., 4.), (0., 4.)]),
             ("B", [(2., 0.), (4., 0.), (4., 4.), (2., 4.)]),
             ("C", [(2., 0.), (4., 0.), (4., 4.), (2., 4.)])]  # duplicate of B -> over-coverage
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)]))
    assert exc.value.context["reason"] in ("invalid_interior_edge_pair", "exterior_duplicate_owner")


def test_lock5_imprecise_endpoint_is_still_red():
    """Lock 5 (R-2): a 1mm endpoint mismatch is a gap, proving no tolerance was introduced."""
    footprint = [(0., 0.), (4., 0.), (4., 10.), (0., 10.)]
    zones = [("A", [(0., 0.), (2., 0.), (2., 10.), (0., 10.)]),       # long east edge [0,10] at x=2
             ("B", [(2., 0.), (4., 0.), (4., 5.), (2., 5.)]),         # faces [0,5]
             ("C", [(2., 5.001), (4., 5.001), (4., 10.), (2., 10.)])] # faces [5.001,10] -> 1mm gap (5,5.001)
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)]))
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_lock7_correction_corridor_wall_enters_observation_set():
    """Lock 7: the same T-junction on the correction side feeds the corridor wall into observations.

    This is the false-red fix: previously the silent ``continue`` dropped the
    corridor wall, so it could never match and was scored as a miss.
    """
    geometry = _correction("F1", LONG_FACING_FOUR["footprint"], LONG_FACING_FOUR["zones"])
    segments = extract_correction_plan_segments(geometry)
    interior = [item for item in segments if not item.exterior]
    assert len([item for item in segments if item.exterior]) == 4
    corridor = {item.zone_ids for item in interior if "A" in item.zone_ids}
    assert corridor == {("A", "B"), ("A", "C"), ("A", "D"), ("A", "E")}
    # The long corridor edge is present as four observed sub-segments, not dropped.
    assert all(item.source_ids == ("correction:F1",) for item in interior)
    assert len(interior) == 7


# ---------------------------------------------------------------------------
# r1 rework locks (RW-1 representation identity / RW-2 non-orthogonal seam /
# RW-3 exterior duplicate owner / product-side assignment+score).  Per-lock
# neuter independence is in the execution log r1 section.
# ---------------------------------------------------------------------------


def _typed_correction(cells, footprint_vertices):
    floor = FloorV3(id="F1", name="F1", z_floor=0.0, ceiling_height=3.0,
                    footprint=FootprintRing(vertices=footprint_vertices), cells=cells)
    xs = [float(v[0]) for v in footprint_vertices]
    ys = [float(v[1]) for v in footprint_vertices]
    return CorrectedGeometryV3(schema_version="3", footprint_x=[min(xs), max(xs)],
                               footprint_y=[min(ys), max(ys)], floors=[floor])


def _plan_config():
    return JudgeScoreConfigV1(schema_version="1", plan_axis_alignment_tol_m=.05, plan_position_tol_m=.3,
        plan_extent_tol_m=.3, claim_complete_epsilon_m=.05, opening_match_center_tol_m=.4,
        opening_assignment_tie_epsilon=1e-9, along_claim_tol_m=.4, width_claim_tol_m=.4,
        sill_claim_tol_m=.3, head_claim_tol_m=.3, floor_line_tol_m=.3)


def test_l_a_real_sm24_seam_binary_spelling_not_false_red():
    """L-a (RW-1): the same sm24 seam written 8.059999999999999 (z0 top) and 8.06
    (z1 bottom) validates GREEN and extracts GREEN.  Before RW-1 the scorer read
    the binary spelling difference as a topology break (false red); the validator
    was always blind to it because it checks per-zone edge orthogonality, not
    cross-zone seam identity.
    """
    gt = load_gt_document("sm24_anchor")
    variant = copy.deepcopy(gt)
    z1 = next(z for z in variant.floors[0].zones if z.id == "z1")
    rewritten = 0
    for index, vertex in enumerate(z1.polygon.exterior.vertices):
        if float(vertex[1]) == 8.059999999999999:
            z1.polygon.exterior.vertices[index] = [float(vertex[0]), 8.06]
            rewritten += 1
    assert rewritten > 0
    variant.content_sha256 = compute_gt_v3_content_sha256(variant)
    validate_gt_v3(variant, tolerances=variant.generator.tolerances, expected_case="sm24_anchor")
    segments = extract_gt_plan_segments(variant)
    assert len([s for s in segments if not s.exterior]) == 16


def test_l_b_typed_correction_fp_sum_not_false_red():
    """L-b (RW-1): a typed correction whose cell A right edge is x=0.1+0.2 and
    cell B left edge is the literal 0.3 validates GREEN (cell_polygon_contract,
    coverage) and extracts GREEN.  0.1+0.2 == 0.30000000000000004 != 0.3 in
    binary; before RW-1 the scorer split them across two supporting lines.
    """
    a = 0.1 + 0.2
    assert a != 0.3  # the binary spelling difference this lock exists for
    cells = [CellV3(id="A", role="office", x=[0.0, a], y=[0.0, 1.0],
                   polygon=[[0.0, 0.0], [a, 0.0], [a, 1.0], [0.0, 1.0]]),
             CellV3(id="B", role="office", x=[0.3, 1.0], y=[0.0, 1.0],
                   polygon=[[0.3, 0.0], [1.0, 0.0], [1.0, 1.0], [0.3, 1.0]])]
    geom = _typed_correction(cells, [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    assert all(finding.ok for finding in validate_corrected_geometry(geom))
    segments = extract_correction_plan_segments(geom)
    assert len([s for s in segments if not s.exterior]) == 1


def test_l_c_1e9_endpoint_gap_still_red():
    """L-c (RW-1 separation): a 1e-9 endpoint gap is ~1000 coordinate quanta, so
    canonicalization does NOT absorb it -- the seam stays a red topology break.
    Existing locks only covered 1e-3; this pins the 1e-9 boundary so the quantum
    can never be widened into a physical tolerance.
    """
    footprint = [(0., 0.), (4., 0.), (4., 10.), (0., 10.)]
    zones = [("A", [(0., 0.), (2., 0.), (2., 10.), (0., 10.)]),
             ("B", [(2., 0.), (4., 0.), (4., 5.), (2., 5.)]),
             ("C", [(2., 5. + 1e-9), (4., 5. + 1e-9), (4., 10.), (2., 10.)])]
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)]))
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_l_d_one_sided_dangling_edge_still_red():
    """L-d: a long edge whose opposite side only covers part of it (one-sided
    dangling) stays red.  Gap is Lock3, overlap is Lock4; this pins the dangling
    failure mode.  All three ride the same one-sided-interior guard -- see the
    execution-log self-check for the shared-guard disclosure.
    """
    footprint = [(0., 0.), (4., 0.), (4., 10.), (0., 10.)]
    zones = [("A", [(0., 0.), (2., 0.), (2., 10.), (0., 10.)]),  # long east edge [0,10]
             ("B", [(2., 0.), (4., 0.), (4., 5.), (2., 5.)])]     # faces [0,5] only -> [5,10] dangles
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)]))
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_l_e_exterior_only_duplicate_owner_red():
    """L-e (RW-3): two zones that both equal the full footprint cover every
    exterior edge twice in the same direction.  This was silently GREEN (0
    interior) before RW-3; the exterior-only duplicate-owner guard now rejects it.
    The guard catches ONLY this shape -- it is not a general overlap claim
    (area-level zone overlap is the upstream coverage validator's job).
    """
    footprint = [(0., 0.), (4., 0.), (4., 8.), (0., 8.)]
    zones = [("A", list(footprint)), ("B", list(footprint))]
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)]))
    assert exc.value.context["reason"] == "exterior_duplicate_owner"


def test_y1_nonorthogonal_exact_reverse_paired_not_false_red():
    """Y-1 (RW-2): two cells sharing a near-orthogonal exact-reverse edge
    (dx=5e-10, dy=1) pair cleanly.  cell_geometry admits dx<1e-9 as orthogonal, so
    a legal correction can carry such a seam; the scorer must not reinterpret it
    as a topology break.  The exact-reverse fallback is the general-segment seam
    (invariant #6): C2 enables orthogonal T-junction tiling today, and a future
    non-orthogonal profile extends here without rewriting the API.
    """
    p, q = (0.5, 0.0), (0.5 + 5e-10, 1.0)
    cells = [("A", [(0.0, 0.0), (0.5, 0.0), q, (0.0, 1.0)]),
             ("B", [q, (0.5, 0.0), (1.0, 0.0), (1.0, 1.0)])]
    segments = extract_correction_plan_segments(
        _correction("F1", [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], cells))
    interior = [s for s in segments if not s.exterior]
    assert len(interior) == 1
    assert set(interior[0].zone_ids) == {"A", "B"}


def test_l_f_legal_t_junction_full_assignment_and_score():
    """L-f: a legal T-junction flows all the way through assignment and score --
    0 unmatched on either side and every segment complete -- not merely 'enters
    the observation set' (the prior Lock7 bar).
    """
    footprint = LONG_FACING_FOUR["footprint"]
    zones = LONG_FACING_FOUR["zones"]
    targets = [s for s in extract_gt_plan_segments(SimpleNamespace(floors=[_gt_floor("F1", footprint, zones)])) if not s.exterior]
    observations = [s for s in extract_correction_plan_segments(_correction("F1", footprint, zones)) if not s.exterior]
    assert len(targets) == 7 and len(observations) == 7
    config = _plan_config()
    assignment = assign_plan_segments(targets=targets, observations=observations, config=config)
    assert assignment.unmatched_targets == ()
    assert assignment.unmatched_observations == ()
    scores = score_plan_segments(targets=targets, observations=observations, config=config)
    assert all(score.status == "complete" for score in scores)


def test_l_f_product_failure_semantics():
    """L-f: illegal corrections fail loudly with the product identity error (not a
    silent observation drop), and a binary-spelling correction does NOT false-red.
    """
    gap_zones = [("A", [(0., 0.), (2., 0.), (2., 10.), (0., 10.)]),
                 ("B", [(2., 0.), (4., 0.), (4., 5.), (2., 5.)]),
                 ("C", [(2., 6.), (4., 6.), (4., 10.), (2., 10.)])]
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(
            _correction("F1", [(0., 0.), (4., 0.), (4., 10.), (0., 10.)], gap_zones))
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"

    # binary spelling of the same seam is not a topology break: must not raise
    a = 0.1 + 0.2
    fp_cells = [("A", [(0.0, 0.0), (a, 0.0), (a, 1.0), (0.0, 1.0)]),
                ("B", [(0.3, 0.0), (1.0, 0.0), (1.0, 1.0), (0.3, 1.0)])]
    extract_correction_plan_segments(
        _correction("F1", [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], fp_cells))
