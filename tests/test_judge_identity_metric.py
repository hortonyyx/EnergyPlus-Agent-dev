"""Judge identity + metric locks (W1-W4, 2026-07-27).

Pins the planar scorer's coordinate-identity layer (single-link cluster + guard
band + diameter guard, replacing the 1e-12 quantum grid), the joint-cutpoint
match (replacing one-to-one exhaustive assignment), and the length-denominator
criterion split.  Each lock names the acceptance item (A1..A11 / B) it pins;
the per-lock neuter self-check is in the execution log.
"""
from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.agent.judge.score_policy import c2_v3_score_policy
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError
from src.agent.judge.segment_score import (
    PlanSegment,
    _cluster_axis,
    extract_correction_plan_segments,
    extract_gt_plan_segments,
    match_plan_segments,
    score_plan_segments,
)


def _config():
    return JudgeScoreConfigV1(schema_version="1", plan_axis_alignment_tol_m=.05, plan_position_tol_m=.3,
        plan_extent_tol_m=.3, claim_complete_epsilon_m=.05, opening_match_center_tol_m=.4,
        opening_assignment_tie_epsilon=1e-9, along_claim_tol_m=.4, width_claim_tol_m=.4,
        sill_claim_tol_m=.3, head_claim_tol_m=.3, floor_line_tol_m=.3)


def seg(key, p1, p2, *, floor="F", exterior=True):
    return PlanSegment(key, floor, p1, p2, exterior=exterior)


def _gt_floor(fid, footprint, zones):
    ring = SimpleNamespace(exterior=SimpleNamespace(vertices=footprint))
    return SimpleNamespace(id=fid, footprint=ring, boundary_segments=(),
                           zones=[SimpleNamespace(id=zid, polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=poly)))
                                  for zid, poly in zones])


def _correction(fid, footprint, cells):
    floor = SimpleNamespace(id=fid, footprint=SimpleNamespace(vertices=footprint),
                            cells=[SimpleNamespace(id=cid, polygon=poly) for cid, poly in cells])
    return SimpleNamespace(floors=[floor])


LONG_FACING_FOUR = {
    "footprint": [(0., 0.), (4., 0.), (4., 8.), (0., 8.)],
    "zones": [("A", [(0., 0.), (2., 0.), (2., 8.), (0., 8.)]),
              ("B", [(2., 0.), (4., 0.), (4., 2.), (2., 2.)]),
              ("C", [(2., 2.), (4., 2.), (4., 4.), (2., 4.)]),
              ("D", [(2., 4.), (4., 4.), (4., 6.), (2., 6.)]),
              ("E", [(2., 6.), (4., 6.), (4., 8.), (2., 8.)])],
}


# ---------------------------------------------------------------------------
# W1 identity layer: cluster / guard band / diameter / non-finite (A1/A2/A3/A9)
# ---------------------------------------------------------------------------


def test_a1_identity_merges_one_ulp_binary_spelling():
    # A1 / G-c.1: 8.059999999999999 vs 8.06 (1 ulp at 8) collapse to one atom.
    identity = _cluster_axis([8.059999999999999, 8.06], side="gt", floor_id="F", axis="y",
                             identity_code="score_gt_identity_invalid")
    assert identity.rep[8.059999999999999] == identity.rep[8.06]


def test_a1_identity_merges_fp_sum_spelling():
    # A1 / G-c.2: 0.1+0.2 vs 0.3 collapse to one atom.
    identity = _cluster_axis([0.1 + 0.2, 0.3], side="product", floor_id="F", axis="x",
                             identity_code="score_product_identity_invalid")
    assert identity.rep[0.1 + 0.2] == identity.rep[0.3]


def test_a1_quantum_boundary_pair_not_false_red():
    # A1 / G-c.3 (r2 quantum-boundary pair): two binary64 values 1 ulp apart
    # that straddle a 1e-12 grid boundary.  The old quantum snapped them to
    # different cells (false red); clustering has no cells, so a sub-merge gap
    # merges them.
    half_quantum = 0.5e-12
    below = math.nextafter(half_quantum, -math.inf)
    above = math.nextafter(half_quantum, math.inf)
    assert below != above and abs(above - below) < 1e-12
    # sanity: the retired 1e-12 quantum WOULD have split this pair.
    assert round(below / 1e-12) != round(above / 1e-12)
    identity = _cluster_axis([below, above], side="gt", floor_id="F", axis="x",
                             identity_code="score_gt_identity_invalid")
    assert identity.rep[below] == identity.rep[above]


def test_a2_identity_splits_1e9_gap():
    # A2: a 1e-9 endpoint gap (>> split) stays two distinct atoms.
    identity = _cluster_axis([5.0, 5.0 + 1e-9], side="gt", floor_id="F", axis="x",
                             identity_code="score_gt_identity_invalid")
    assert identity.rep[5.0] != identity.rep[5.0 + 1e-9]


def test_a2_product_side_1e9_gap_still_red_code_unchanged():
    # A2: a 1e-9 gap on the product side stays red, error code verbatim.
    footprint = [(0., 0.), (4., 0.), (4., 10.), (0., 10.)]
    cells = [("A", [(0., 0.), (2., 0.), (2., 10.), (0., 10.)]),
             ("B", [(2., 0.), (4., 0.), (4., 5.), (2., 5.)]),
             ("C", [(2., 5. + 1e-9), (4., 5. + 1e-9), (4., 10.), (2., 10.)])]
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(_correction("F", footprint, cells))
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_a3_guard_band_is_loud_reject_with_hex_context():
    # A3: a gap inside [merge, split] is unresolvable ambiguity -> loud reject,
    # neither merged nor split, with hex binary64 recorded for reproducibility.
    gap = 3e-12  # inside (1e-12, 1e-11)
    with pytest.raises(ScoreContractError) as exc:
        _cluster_axis([5.0, 5.0 + gap], side="gt", floor_id="F", axis="x",
                      identity_code="score_gt_identity_invalid")
    assert exc.value.context["reason"] == "identity_guard_band_ambiguity"
    assert "gap_hex" in exc.value.context and "lo_hex" in exc.value.context


def test_a9_chain_bridge_over_diameter_rejects():
    # A9: many sub-merge gaps that chain-bridge past the diameter cap -> reject.
    # 13 values each 0.9e-12 apart (< merge, so single-link chains them) span
    # 10.8e-12 > diameter 1e-11: distinct intents welded by chaining.
    vals = [5.0 + i * 0.9e-12 for i in range(13)]
    with pytest.raises(ScoreContractError) as exc:
        _cluster_axis(vals, side="gt", floor_id="F", axis="x", identity_code="score_gt_identity_invalid")
    assert exc.value.context["reason"] == "identity_chain_bridge_over_diameter"
    assert "diameter_hex" in exc.value.context


def test_a9_non_finite_value_rejects():
    # A9: non-finite coordinates are rejected with their hex recorded.
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ScoreContractError) as exc:
            _cluster_axis([1.0, bad], side="gt", floor_id="F", axis="x", identity_code="score_gt_identity_invalid")
        assert exc.value.context["reason"] == "identity_non_finite_value"


def test_a9_identity_merge_edge_collapse_rejects():
    # A9 / C-1''(4): identity merge must not collapse adjacent polygon vertices
    # into a zero-length edge.  Two near-coincident first vertices (0.5e-12
    # apart, sub-merge) collapse after identity -> the ring rejects.
    floor = _gt_floor("F", [(0., 0.), (1., 0.), (1., 1.), (0., 1.)],
                      [("Z", [(0., 0.), (0.5e-12, 0.), (1., 0.), (1., 1.), (0., 1.)])])
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[floor]))
    assert exc.value.context["reason"] == "identity_merge_edge_collapse"


# ---------------------------------------------------------------------------
# W3 joint cutpoint + W4 length denominator / criterion split (A4 / W3 exit)
# ---------------------------------------------------------------------------


def _wall_criterion(rows):
    policy = c2_v3_score_policy(claim_rows=(), segment_rows=rows)
    return next(c for c in policy.criteria if c.criterion_id == "walls_complete")


def test_a4_q3_full_wall_miss_scores_zero_over_wall_length():
    # A4 Q3 (1): a fully-missed wall scores 0; failing == wall length.
    target = seg("wall", (2, 0), (2, 4), exterior=False)
    rows = score_plan_segments(targets=(target,), observations=(), config=_config())
    wc = _wall_criterion(rows)
    assert wc.denominator_units == pytest.approx(4.0)
    assert wc.passing_units == pytest.approx(0.0)
    assert wc.failing_units == pytest.approx(4.0)
    assert wc.verdict == "fail"


def test_a4_q3_split_differently_scores_full_not_ambiguous():
    # A4 Q3 (2): a wall drawn correctly but split differently on each side scores
    # 100% -- the corridor case.  GT has two sub-walls [0,2]+[2,4]; the product
    # has one long wall [0,4].  The old exhaustive matcher raised score_match_
    # ambiguous here; the joint cutpoint covers both, no exception.
    targets = (seg("t1", (2, 0), (2, 2), exterior=False), seg("t2", (2, 2), (2, 4), exterior=False))
    obs = (seg("long", (2, 0), (2, 4), exterior=False),)
    rows, _ = match_plan_segments(targets=targets, observations=obs, config=_config())
    wc = _wall_criterion(rows)
    assert wc.passing_units == pytest.approx(4.0)
    assert wc.failing_units == pytest.approx(0.0)
    assert wc.verdict == "pass"


def test_a4_q3_half_wall_scores_half():
    # A4 Q3 (3): a wall half-covered scores 2/4.
    target = seg("wall", (2, 0), (2, 4), exterior=False)
    obs = (seg("half", (2, 0), (2, 2), exterior=False),)
    rows = score_plan_segments(targets=(target,), observations=obs, config=_config())
    wc = _wall_criterion(rows)
    assert wc.passing_units == pytest.approx(2.0)
    assert wc.failing_units == pytest.approx(2.0)


def test_a4_failing_equals_wall_length_independent_of_facing_room_count():
    # W4 / R-3: the denominator is wall LENGTH, not facing-interface count.  A
    # 4 m wall fully missed fails by 4.0 m whether it faces one room or many;
    # the old per-interface denominator inflated this up to 3.96x on real sm24.
    target = seg("wall", (2, 0), (2, 4), exterior=False)
    rows = score_plan_segments(targets=(target,), observations=(), config=_config())
    assert _wall_criterion(rows).failing_units == pytest.approx(4.0)
    # conservation invariant survives the length denominator.
    policy = c2_v3_score_policy(claim_rows=(), segment_rows=rows)
    assert all(c.passing_units + c.failing_units == pytest.approx(c.denominator_units)
               for c in policy.criteria if c.eligible)


def test_w4_extra_and_duplicate_walls_split_into_separate_criteria():
    # W4: over-draw (extra) and double-draw (duplicate) are separate accounts
    # from miss; product over-draw never inflates walls_complete's denominator.
    target = seg("wall", (2, 0), (2, 4), exterior=False)
    obs = (seg("ok", (2, 0), (2, 2), exterior=False),       # covers [0,2]
           seg("dup", (2, 0), (2, 2), exterior=False),      # re-covers [0,2] -> duplicate
           seg("extra", (5, 0), (6, 0), exterior=False))    # covers no target -> extra
    rows = score_plan_segments(targets=(target,), observations=obs, config=_config())
    by_id = {c.criterion_id: c for c in c2_v3_score_policy(claim_rows=(), segment_rows=rows).criteria}
    # walls_complete denominator is the answer wall length (4 m), not 4 + extra.
    assert by_id["walls_complete"].denominator_units == pytest.approx(4.0)
    assert by_id["no_extra_walls"].failing_units == pytest.approx(1.0)
    assert by_id["no_duplicate_wall_strokes"].failing_units == pytest.approx(2.0)


def test_w3_score_match_ambiguous_unreachable_on_plan_wall_path():
    # W3 exit: score_match_ambiguous is structurally unreachable on the plan-wall
    # path.  One long corridor wall [0,8] over four GT sub-walls tiles cleanly
    # with no exception and no miss (the corridor false-red root cause).
    targets = [s for s in extract_gt_plan_segments(
        SimpleNamespace(floors=[_gt_floor("F", LONG_FACING_FOUR["footprint"], LONG_FACING_FOUR["zones"])])) if not s.exterior]
    prod_zones = [("A", [(0., 0.), (2., 0.), (2., 8.), (0., 8.)]),
                  ("BCDE", [(2., 0.), (4., 0.), (4., 8.), (2., 8.)])]
    obs = [s for s in extract_correction_plan_segments(_correction("F", LONG_FACING_FOUR["footprint"], prod_zones)) if not s.exterior]
    rows, _ = match_plan_segments(targets=targets, observations=obs, config=_config())
    # the joint cutpoint raises nothing (the old exhaustive matcher raised
    # score_match_ambiguous here); the four GT corridor sub-walls (zone pair
    # includes A) are all covered complete by the one long product wall.  The
    # three cross walls B-C/C-D/D-E legitimately miss -- the single-cell product
    # drew no cross walls -- and that is the correct result, not a false red.
    corridor = [r for r in rows if r.target is not None and "A" in r.target.zone_ids]
    assert len(corridor) >= 4
    assert all(r.status == "complete" for r in corridor)


# ---------------------------------------------------------------------------
# C-1' answer atoms are a pure function of answer bytes (A8)
# ---------------------------------------------------------------------------


def test_a8_answer_denominator_independent_of_product():
    # A8 / C-1': the GT atom set and walls_complete denominator are a pure
    # function of the answer bytes.  Same GT with two different products
    # (one matching, one a single cell with no interior walls) yields the same
    # denominator -- the GT identity pool never mixes with the product pool.
    gt = SimpleNamespace(floors=[_gt_floor("F", LONG_FACING_FOUR["footprint"], LONG_FACING_FOUR["zones"])])
    targets = extract_gt_plan_segments(gt)
    product_match = extract_correction_plan_segments(_correction("F", LONG_FACING_FOUR["footprint"], LONG_FACING_FOUR["zones"]))
    product_single = extract_correction_plan_segments(_correction("F", LONG_FACING_FOUR["footprint"], [("only", LONG_FACING_FOUR["footprint"])]))

    def wall_denominator(product):
        rows, _ = match_plan_segments(targets=targets, observations=product, config=_config())
        return _wall_criterion(rows).denominator_units
    # denominator identical despite radically different products.
    assert wall_denominator(product_match) == pytest.approx(wall_denominator(product_single))
    # GT extraction itself is product-independent (re-extract is byte-identical).
    assert extract_gt_plan_segments(gt) == targets


# ---------------------------------------------------------------------------
# §5-B product_to_gt multi-cover (B exit 1: per-key contract lock)
# ---------------------------------------------------------------------------


def test_b_observation_map_records_multi_cover_per_key():
    # §5-B exit 1 (per-key contract lock, NOT a weak length-equal assertion): a
    # product wall covering two GT walls maps to BOTH target keys in the
    # observation map.  This multi-cover result is what rebuilds product_to_gt;
    # a one-to-one dict would have silently kept only one and lost the other.
    targets = (seg("t1", (2, 0), (2, 2), exterior=False), seg("t2", (2, 2), (2, 4), exterior=False))
    obs = (seg("long", (2, 0), (2, 4), exterior=False),)
    _, obs_map = match_plan_segments(targets=targets, observations=obs, config=_config())
    assert obs_map["long"] == ("t1", "t2")


# ---------------------------------------------------------------------------
# W5 shared orthogonality module (R-4: production legal / judge NA, zero gt import)
# ---------------------------------------------------------------------------


def test_w5_orthogonality_module_has_zero_judge_import():
    # W5 / invariant #4: the shared orthogonality module must not import the
    # judge (or gt) -- production and gate(1) never pull the judge transitively.
    # AST (not substring) so the rule text mentioning the module name is not a hit.
    source = Path("src/agent/correction/orthogonality.py").read_text(encoding="utf-8")
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    assert not any(name.startswith("src.agent.judge") for name in modules)


def test_w5_classify_edge_orthogonality_three_classes():
    # W5: the shared yardstick classifies the Y-1 near-axis seam as advisory
    # (production admits it; the judge pairs it by exact reverse, never broken).
    from src.agent.correction.orthogonality import classify_edge_orthogonality
    assert classify_edge_orthogonality(1.0, 0.0) == "axis_aligned"
    assert classify_edge_orthogonality(0.0, 1.0) == "axis_aligned"
    assert classify_edge_orthogonality(5e-10, 1.0) == "near_orthogonal_advisory"
    assert classify_edge_orthogonality(1.0, 1.0) == "non_orthogonal"


def test_w5_cell_geometry_uses_shared_epsilon_unchanged():
    # W5: cell_geometry's _EPS is the shared ORTHOGONALITY_EPSILON (1e-9), value
    # unchanged -- only the source is centralized so judge and production agree.
    from src.agent.correction import cell_geometry
    from src.agent.correction.orthogonality import ORTHOGONALITY_EPSILON
    assert cell_geometry._EPS == ORTHOGONALITY_EPSILON == 1e-9


# ---------------------------------------------------------------------------
# §5-B product_to_gt multi-cover, facade path (B exit 2: window-binding fixture)
# ---------------------------------------------------------------------------


def test_b_facade_multi_span_straddle_fails_closed_not_first():
    # §5-B exit 2: a product facade span straddling two GT facade spans has >1
    # candidate and is NOT mapped -- "take first" would silently mis-bind a
    # window to the wrong wall with no test going red.  No mapping makes the
    # window fail closed (unmatched).  A single-contained span maps normally.
    from src.agent.judge.score_service import _resolve_facade_product_to_gt
    gt = SimpleNamespace(floors=[SimpleNamespace(id="F", boundary_segments=[
        SimpleNamespace(id="gt-a", floor_id="F", facade_family="North",
            world_along_interval=SimpleNamespace(lo=0., hi=2.)),
        SimpleNamespace(id="gt-b", floor_id="F", facade_family="North",
            world_along_interval=SimpleNamespace(lo=2., hi=4.)),
    ])])
    straddle = SimpleNamespace(facade_segments=[SimpleNamespace(
        id="prod-long", floor_id="F", facade_family="North",
        world_along_interval=SimpleNamespace(lo=0., hi=4.))])
    # multi-cover: straddles both -> not mapped (never "take first").
    assert _resolve_facade_product_to_gt(geometry=straddle, gt=gt) == {}
    contained = SimpleNamespace(facade_segments=[SimpleNamespace(
        id="prod-a", floor_id="F", facade_family="North",
        world_along_interval=SimpleNamespace(lo=0.5, hi=1.5))])
    # single-contained -> maps to gt-a.
    assert _resolve_facade_product_to_gt(geometry=contained, gt=gt) == {"prod-a": "gt-a"}
