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

from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.schema import CellV3, CorrectedGeometryV3, FloorV3, FootprintRing
from src.agent.judge.score_policy import c2_v3_score_policy
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError
from src.agent.judge.identity_provenance import (
    AliasCertificate,
    CoordinateOccurrence,
    CoordinateSourceKey,
    SourceTopologyIndex,
)
from src.agent.judge.segment_score import (
    PlanSegment,
    _assert_obs_conservation,
    _assert_target_conservation,
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


def _cluster_values(values, *, side, floor_id, axis):
    """Historical numeric counterexamples on source-bearing alias slots."""
    keys = tuple(
        CoordinateSourceKey(
            side,
            floor_id,
            "historical_lock",
            f"value-{index}",
            "counterexample",
            index,
            None,
            axis,
        )
        for index, _value in enumerate(values)
    )
    occurrences = tuple(
        CoordinateOccurrence.make(key, value, f"historical:{index}")
        for index, (key, value) in enumerate(zip(keys, values, strict=True))
    )
    certificates = {}
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            pair = (left, right) if left <= right else (right, left)
            certificates[pair] = AliasCertificate(
                "profile_axis_constraint",
                left,
                right,
                support_slots=(("historical_counterexample",),),
            )
    topology = SourceTopologyIndex(
        side=side,
        floor_id=floor_id,
        certificates=certificates,
    )
    return (
        _cluster_axis(
            occurrences,
            side=side,
            floor_id=floor_id,
            axis=axis,
            topology=topology,
        ),
        keys,
    )


def _gt_floor(fid, footprint, zones):
    ring = SimpleNamespace(exterior=SimpleNamespace(vertices=footprint))
    return SimpleNamespace(id=fid, footprint=ring, boundary_segments=(),
                           zones=[SimpleNamespace(id=zid, polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=poly)))
                                  for zid, poly in zones])


def _correction(fid, footprint, cells):
    floor = SimpleNamespace(id=fid, footprint=SimpleNamespace(vertices=footprint),
                            cells=[SimpleNamespace(id=cid, polygon=poly) for cid, poly in cells])
    return SimpleNamespace(floors=[floor])


def _typed_correction(cells, footprint_vertices, fid="F"):
    """Build a real CorrectedGeometryV3 so validate_corrected_geometry (the
    production legitimacy authority) can run on the same fixture the judge sees."""
    floor = FloorV3(id=fid, name=fid, z_floor=0.0, ceiling_height=3.0,
                    footprint=FootprintRing(vertices=footprint_vertices), cells=cells)
    xs = [float(v[0]) for v in footprint_vertices]
    ys = [float(v[1]) for v in footprint_vertices]
    return CorrectedGeometryV3(schema_version="3", footprint_x=[min(xs), max(xs)],
                               footprint_y=[min(ys), max(ys)], floors=[floor])


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
    identity, keys = _cluster_values(
        [8.059999999999999, 8.06], side="gt", floor_id="F", axis="y"
    )
    assert identity.rep[keys[0]] == identity.rep[keys[1]]


def test_a1_identity_merges_fp_sum_spelling():
    # A1 / G-c.2: 0.1+0.2 vs 0.3 collapse to one atom.
    identity, keys = _cluster_values(
        [0.1 + 0.2, 0.3], side="product", floor_id="F", axis="x"
    )
    assert identity.rep[keys[0]] == identity.rep[keys[1]]


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
    identity, keys = _cluster_values(
        [below, above], side="gt", floor_id="F", axis="x"
    )
    assert identity.rep[keys[0]] == identity.rep[keys[1]]


def test_a2_identity_splits_1e9_gap():
    # A2: a 1e-9 endpoint gap (>> split) stays two distinct atoms.
    identity, keys = _cluster_values(
        [5.0, 5.0 + 1e-9], side="gt", floor_id="F", axis="x"
    )
    assert identity.rep[keys[0]] != identity.rep[keys[1]]


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


def test_m4_gt_interior_pairing_failure_code_is_gt_side_verbatim():
    # M-4 / §3.3: a GT interior-pairing failure raises the GT-side top-level
    # code verbatim (score_gt_identity_invalid), never the product-side code.
    # r1 left the GT side un-pinned (only ``reason`` was asserted on this path),
    # so swapping extract_gt's identity_code to the product code kept the whole
    # suite green -- the false-lock shape M-4 names (r0's "three tests stay
    # green"复发).  Neuter: swap that code -> this reds.  Product side is pinned
    # by test_a2_product_side_1e9_gap_still_red_code_unchanged above.
    floor = _gt_floor("F", [(0., 0.), (2., 0.), (2., 2.), (0., 2.)],
                      [("A", [(0., 0.), (2., 0.), (2., 1.), (0., 1.)]),
                       ("B", [(2., 0.), (0., 0.), (0., -1.), (2., -1.)])])  # zone B outside footprint
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[floor]))
    assert exc.value.code == "score_gt_identity_invalid"


def test_a3_guard_band_is_loud_reject_with_hex_context():
    # A3: a gap inside [merge, split] is unresolvable ambiguity -> loud reject,
    # neither merged nor split, with hex binary64 recorded for reproducibility.
    gap = 3e-12  # inside (1e-12, 1e-11)
    with pytest.raises(ScoreContractError) as exc:
        _cluster_values(
            [5.0, 5.0 + gap], side="gt", floor_id="F", axis="x"
        )
    assert exc.value.code == "score_identity_guard_band_ambiguity"
    assert exc.value.context["reason"] == "identity_guard_band_ambiguity"
    assert exc.value.context["side"] == "gt"
    assert "gap_hex" in exc.value.context and "lo_hex" in exc.value.context


def test_a9_chain_bridge_over_diameter_rejects():
    # A9: many sub-merge gaps that chain-bridge past the diameter cap -> reject.
    # 13 values each 0.9e-12 apart (< merge, so single-link chains them) span
    # 10.8e-12 > diameter 1e-12 (§2.1: cap <= merge): distinct intents welded.
    vals = [5.0 + i * 0.9e-12 for i in range(13)]
    with pytest.raises(ScoreContractError) as exc:
        _cluster_values(vals, side="gt", floor_id="F", axis="x")
    assert exc.value.code == "score_identity_chain_bridge"
    assert exc.value.context["reason"] == "identity_chain_bridge_over_diameter"
    assert "diameter_hex" in exc.value.context


def test_a9_non_finite_value_rejects():
    # A9: non-finite coordinates are rejected with their hex recorded.
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ScoreContractError) as exc:
            _cluster_values([1.0, bad], side="gt", floor_id="F", axis="x")
        assert exc.value.code == "score_identity_non_finite"
        assert exc.value.context["reason"] == "identity_non_finite_value"


def test_a9_identity_merge_edge_collapse_rejects():
    # A9 / C-1''(4): identity merge must not collapse adjacent polygon vertices
    # into a zero-length edge.  Two near-coincident first vertices (0.5e-12
    # apart, sub-merge) collapse after identity -> the ring rejects.
    floor = _gt_floor("F", [(0., 0.), (1., 0.), (1., 1.), (0., 1.)],
                      [("Z", [(0., 0.), (0.5e-12, 0.), (1., 0.), (1., 1.), (0., 1.)])])
    with pytest.raises(ScoreContractError) as exc:
        extract_gt_plan_segments(SimpleNamespace(floors=[floor]))
    assert exc.value.code == "score_identity_merge_collapse"
    assert exc.value.context["reason"] == "identity_merge_edge_collapse"
    # R-5: the ORIGINAL merged binary64 pair and exact diameter are recorded.
    assert "v1_hex" in exc.value.context and "v2_hex" in exc.value.context
    assert "diameter_hex" in exc.value.context


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
# B-1 dead-frame: one-way support-line registration + conservation (sol fixture)
# ---------------------------------------------------------------------------


def test_b1_one_wall_cannot_charge_two_parallel_answer_walls():
    # B-1 (controller dead-frame, acceptance lock 1): the false-green root.  A
    # 4 m product wall at x=1.1 sat within the 0.3 m position tolerance of TWO
    # parallel answer walls (x=1.0 and x=1.2) and used to earn 8/8 -- 8 m of
    # passing on a 4 m wall, with extra = 4-8 = -4 silently swallowed by
    # ``extra > epsilon``.  It must now LOUD-reject: the judge's own position
    # tolerance cannot separate the two answer walls, so per R-4 it says
    # unsupported (score_identity_support_ambiguous), never scores 8 m.
    footprint = [(0., 0.), (2., 0.), (2., 4.), (0., 4.)]
    gt = SimpleNamespace(floors=[_gt_floor("F", footprint, [
        ("L", [(0., 0.), (1., 0.), (1., 4.), (0., 4.)]),
        ("M", [(1., 0.), (1.2, 0.), (1.2, 4.), (1., 4.)]),
        ("R", [(1.2, 0.), (2., 0.), (2., 4.), (1.2, 4.)])])])
    targets = [s for s in extract_gt_plan_segments(gt) if not s.exterior]
    product = [s for s in extract_correction_plan_segments(_correction("F", footprint, [
        ("P1", [(0., 0.), (1.1, 0.), (1.1, 4.), (0., 4.)]),
        ("P2", [(1.1, 0.), (2., 0.), (2., 4.), (1.1, 4.)])])) if not s.exterior]
    with pytest.raises(ScoreContractError) as exc:
        match_plan_segments(targets=targets, observations=product, config=_config())
    assert exc.value.code == "score_identity_support_ambiguous"
    assert exc.value.context["reason"] == "observation_eligible_for_multiple_support_lines"


def test_b1_conservation_over_charge_raises_through_match_path():
    # R2-M1 (replaces the prior direct-helper lock sol flagged): the over-charge
    # gate must fire through the REAL match_plan_segments wiring, not a direct
    # ``_assert_obs_conservation(8.0 > 4.0 + tol)`` call (the r0 false-lock shape:
    # it pinned "8.0 > 4.0 + tol" without exercising registration / cut tiling,
    # so a gate that never ran in production still passed).  Here two answer
    # walls sit on the SAME support line with OVERLAPPING spans -- t1 [0,4] and
    # t2 [1,3] both at x=2 -- so one product wall registers to a SINGLE line (no
    # score_identity_support_ambiguous) yet covers BOTH targets, charging
    # 4 m + 2 m = 6 m on a 4 m wall.  cover (6) > obs length (4) is the double-
    # charge signature and must LOUD-reject.  Neuter: make the gate
    # ``covered > obs_length + 1e9`` (or drop the raise) and this reds -- the
    # wall would otherwise score 6 m passing on a 4 m wall (the false green).
    targets = (seg("t1", (2, 0), (2, 4), exterior=False),   # answer wall [0,4] on x=2
               seg("t2", (2, 1), (2, 3), exterior=False))   # answer wall [1,3] on x=2 (overlaps t1)
    obs = (seg("wall", (2, 0), (2, 4), exterior=False),)    # product wall covers both -> 6 m on a 4 m wall
    with pytest.raises(ScoreContractError) as exc:
        match_plan_segments(targets=targets, observations=obs, config=_config())
    assert exc.value.code == "score_denominator_nonconserving"
    assert exc.value.gate_id == "scoring.denominator_totality"
    assert exc.value.context["reason"] == "observation_cover_exceeds_length"
    assert exc.value.context["obs_length"] == pytest.approx(4.0)
    assert exc.value.context["covered"] == pytest.approx(6.0)
    assert exc.value.context["excess"] == pytest.approx(2.0)


def test_b1_obs_conservation_equality_boundary_does_not_fire():
    # R2-M1: the over-charge gate is STRICT but only fires on a real over-charge,
    # not on geometric equality.  cover == obs length (a single obs exactly
    # spanning its registered target(s)) is the legitimate equality and must not
    # raise -- otherwise every exactly-covered wall would false-red.  This is the
    # direct boundary assertion (the match-path over-charge lock above covers the
    # > side); a tiny FP over (1e-13) still fires because the gate has no window.
    _assert_obs_conservation("obs", obs_length=4.0, covered=4.0)
    _assert_obs_conservation("obs", obs_length=4.0, covered=4.0 - 1e-13)
    with pytest.raises(ScoreContractError):
        _assert_obs_conservation("obs", obs_length=4.0, covered=4.0 + 1e-13)


def test_b1_per_target_conservation_tiles_target_length():
    # R2-M1 #2: per-target sub-interval conservation.  The cut tiling partitions
    # each target's [t0, t1] into matched / miss / duplicate sub-intervals, so
    # matched + miss + duplicate == target.length must hold.  Verified two ways:
    # (a) end-to-end -- a half-covered 4 m wall gives 2 m matched + 2 m miss, and
    #     the policy invariant passing + failing == wall length holds (the gate
    #     does not false-fire on real input);
    # (b) the gate itself -- a non-tiling account raises.
    # NOTE: the per-target gate is a defensive self-check; the cut loop partitions
    # [t0, t1] exactly by construction, so NO valid match_plan_segments input can
    # trigger it (unlike the obs over-charge gate, which has a real trigger via
    # overlapping same-line targets).  It is therefore locked by a direct helper
    # call -- disclosed here, not disguised as a match-path lock.
    target = seg("wall", (2, 0), (2, 4), exterior=False)
    obs = (seg("half", (2, 0), (2, 2), exterior=False),)
    rows = score_plan_segments(targets=(target,), observations=obs, config=_config())
    policy = c2_v3_score_policy(claim_rows=(), segment_rows=rows)
    wc = next(c for c in policy.criteria if c.criterion_id == "walls_complete")
    assert wc.passing_units == pytest.approx(2.0) and wc.failing_units == pytest.approx(2.0)
    assert wc.passing_units + wc.failing_units == pytest.approx(4.0)
    # the gate: a tiling account (2 + 2 + 0 == 4) passes; a non-tiling one raises.
    _assert_target_conservation("wall", 4.0, matched_cover=2.0, miss_length=2.0, duplicate_length=0.0)
    with pytest.raises(ScoreContractError) as exc:
        _assert_target_conservation("wall", 4.0, matched_cover=2.0, miss_length=1.0, duplicate_length=0.0)
    assert exc.value.code == "score_denominator_nonconserving"
    assert exc.value.context["reason"] == "target_subintervals_do_not_tile"
    assert exc.value.context["target_length"] == pytest.approx(4.0)
    assert exc.value.context["accounted_length"] == pytest.approx(3.0)


def test_b1_well_separated_walls_register_without_over_reject():
    # B-1 acceptance lock 3: when two answer walls are > 2x the position
    # tolerance apart, a product wall near ONE of them registers to that one
    # line and scores normally -- step 1 does not over-reject.  Contrast with
    # the parallel-wall case: there the walls were 0.2 m apart (< 2x tol), here
    # they are 2.0 m apart.
    footprint = [(0., 0.), (4., 0.), (4., 4.), (0., 4.)]
    gt = SimpleNamespace(floors=[_gt_floor("F", footprint, [
        ("A", [(0., 0.), (1., 0.), (1., 4.), (0., 4.)]),
        ("B", [(1., 0.), (3., 0.), (3., 4.), (1., 4.)]),
        ("C", [(3., 0.), (4., 0.), (4., 4.), (3., 4.)])])])
    targets = [s for s in extract_gt_plan_segments(gt) if not s.exterior]
    product = [s for s in extract_correction_plan_segments(_correction("F", footprint, [
        ("P1", [(0., 0.), (1.05, 0.), (1.05, 4.), (0., 4.)]),
        ("P2", [(1.05, 0.), (3.05, 0.), (3.05, 4.), (1.05, 4.)]),
        ("P3", [(3.05, 0.), (4., 0.), (4., 4.), (3.05, 4.)])])) if not s.exterior]
    rows, _ = match_plan_segments(targets=targets, observations=product, config=_config())
    wc = _wall_criterion(rows)
    assert wc.passing_units == pytest.approx(8.0)
    assert wc.failing_units == pytest.approx(0.0)
    assert wc.verdict == "pass"


# ---------------------------------------------------------------------------
# C-1' answer atoms are a pure function of answer bytes (A8)
# ---------------------------------------------------------------------------


def test_a8_answer_denominator_independent_of_product():
    # A8 / C-1': the walls_complete denominator is a PURE function of the answer
    # bytes -- the GT identity pool never mixes with the product pool.  This lock
    # replaces a false-lock: the prior fixture gave both products the SAME
    # relevant coordinates and compared with pytest.approx, so an illegal GT+
    # product joint pool moved the answer representative by 5e-13 and the test
    # still passed.  Here the two products carry DIFFERENT sub-merge neighbours
    # of the GT x=4 endpoint, so a joint pool would shift the answer's x=4 atom
    # (and hence the wall length / denominator) by a different last-bit amount in
    # each product.  C-1' forbids that: the byte-identical denominator below can
    # only hold if the answer never sees the product's values.
    import struct
    gt_foot = [(0., 0.), (4., 0.), (4., 2.), (0., 2.)]
    gt_zones = [("B", [(0., 0.), (4., 0.), (4., 1.), (0., 1.)]),
                ("T", [(0., 1.), (4., 1.), (4., 2.), (0., 2.)])]
    gt = SimpleNamespace(floors=[_gt_floor("F", gt_foot, gt_zones)])
    targets = extract_gt_plan_segments(gt)

    def product_with_neighbour(delta: float):
        # product footprint and cells pull their right edge to 4-delta, a sub-
        # merge neighbour of the GT x=4 atom.  Cells stay closed (each edge has
        # its reverse pair) so extraction is legal; only the right-wall x moves.
        right = 4. - delta
        foot = [(0., 0.), (right, 0.), (right, 2.), (0., 2.)]
        return extract_correction_plan_segments(_correction("F", foot, [
            ("B", [(0., 0.), (right, 0.), (right, 1.), (0., 1.)]),
            ("T", [(0., 1.), (right, 1.), (right, 2.), (0., 2.)])]))

    def wall_den_bytes(product):
        rows, _ = match_plan_segments(targets=targets, observations=product, config=_config())
        return struct.pack(">d", _wall_criterion(rows).denominator_units)

    # binary64-IDENTICAL across the two products (both 4.0 = 0x4010000000000000).
    # pytest.approx would pass at 4.0 vs 3.9999999999995; byte equality does not.
    assert wall_den_bytes(product_with_neighbour(5e-13)) == wall_den_bytes(product_with_neighbour(9e-13))


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


def test_b_facade_multi_candidate_gt_span_is_not_mapped():
    # R2-M2 neuter ① (the :230 path): a product facade span contained in MORE
    # THAN ONE GT facade span (>1 candidate) is NOT mapped.  This is the >1
    # branch sol r2 said NO fixture reached -- the prior straddle lock above is
    # 0 candidate (相邻 [0,2]/[2,4] 对产品 [0,4] 在"完整包含"定义下谁也不含),
    # so weakening ``len(candidates) == 1`` to ``if candidates`` could not change
    # it.  Here the GT South facade carries TWO spans (multi-span same facade):
    # south-wide [0,4] and south-nested [1,3].  prod-full [0,4] is contained only
    # in south-wide (single candidate -> mapped); prod-inner [1.5,2.5] is
    # contained in BOTH (>1 candidate -> not mapped, never "take first").
    # Neuter: ``len(candidates) == 1`` -> ``if candidates`` maps prod-inner to
    # south-wide too, so the ``== {"prod-full": "south-wide"}`` assertion reds.
    from src.agent.judge.score_service import _resolve_facade_product_to_gt
    gt = SimpleNamespace(floors=[SimpleNamespace(id="F", boundary_segments=[
        SimpleNamespace(id="south-wide", floor_id="F", facade_family="South",
            world_along_interval=SimpleNamespace(lo=0., hi=4.)),
        SimpleNamespace(id="south-nested", floor_id="F", facade_family="South",
            world_along_interval=SimpleNamespace(lo=1., hi=3.)),
    ])])
    geometry = SimpleNamespace(facade_segments=[
        SimpleNamespace(id="prod-full", floor_id="F", facade_family="South",
            world_along_interval=SimpleNamespace(lo=0., hi=4.)),
        SimpleNamespace(id="prod-inner", floor_id="F", facade_family="South",
            world_along_interval=SimpleNamespace(lo=1.5, hi=2.5)),
    ])
    assert _resolve_facade_product_to_gt(geometry=geometry, gt=gt) == {"prod-full": "south-wide"}


def test_b_facade_multi_candidate_window_temporary_binding_fails_closed():
    # R2-M2 neuter ① (the bind path): a window whose span is contained in MORE
    # THAN ONE product facade segment (temporary binding, facade_segment_id is
    # None) fails closed -- it does NOT "take the first" segment.  The other
    # ``len(candidates) == 1`` unique-candidate gate lives here in
    # bind_correction_window_segment; weakening it to ``if candidates`` reds this.
    # (The correction e2e path uses explicit facade_segment_id with
    # allow_temporary_binding=False, so it bypasses this temporary gate; the
    # temporary gate is the reading / direct-resolver path and is real code --
    # exercised by build_correction_window_resolver's default allow_temporary=True.)
    from src.agent.correction.schema import FacadeSegment, WorldInterval
    from src.agent.judge.opening_claim_score import bind_correction_window_segment
    H = "a" * 64
    def facade(id, lo, hi):
        return FacadeSegment(id=id, floor_id="F", facade_family="South", p1=(lo, 0.), p2=(hi, 0.),
            outward_normal=(0, -1), world_along_interval=WorldInterval(lo=lo, hi=hi), depth=0.,
            visible_intervals=[], source_footprint_fingerprint=H)
    window = SimpleNamespace(id="w", floor_id="F", facade="South", span=(1.5, 2.5), facade_segment_id=None)
    # two South segments both fully contain the window span [1.5,2.5] -> >1 candidate -> fail closed.
    with pytest.raises(ScoreContractError) as exc:
        bind_correction_window_segment(window=window, segments=(facade("s-wide", 0., 4.), facade("s-nested", 1., 3.)))
    assert exc.value.code == "score_product_segment_unresolved"
    # control: exactly one containing segment -> temporary_unique_span_binding succeeds.
    bound, mode = bind_correction_window_segment(window=window, segments=(facade("s-only", 0., 4.),))
    assert mode == "temporary_unique_span_binding" and bound.id == "s-only"


# ---------------------------------------------------------------------------
# R-4 / W5 wiring: production legality vs judge capability (live counter-example)
# ---------------------------------------------------------------------------
# Two cells share ONE near-vertical interior wall.  Cell A leans it dx_a; cell B
# leans the reverse dx_b.  Production admits any dx <= 1e-9 (edge_is_axis_aligned),
# so validate_corrected_geometry stays five-way GREEN for both spellings.  The
# judge's question is separate: can its exact-reverse path MEASURE this wall?
#   * dx_a == dx_b -> exact reverse pair -> extracts one interior wall, scores.
#   * dx_a != dx_b (5e-10 vs 4e-10) -> not exact reverses -> capability NA
#     (score_unsupported_combination), NEVER score_product_identity_invalid.
# Before this batch the judge convicted the legal geometry with its own exactness
# ceiling (exterior_duplicate_owner on the axis-aligned span the lean perturbed) --
# the same disease in a second face, which is why R-4 routes the whole shape to
# unsupported at the source instead of patching each face.


def _shared_wall_cells(dx_a, dx_b, *, H=1.0):
    return [
        CellV3(id="A", role="office", x=[0.0, 0.5 + dx_a], y=[0.0, H],
               polygon=[[0.0, 0.0], [0.5, 0.0], [0.5 + dx_a, H], [0.0, H]]),
        CellV3(id="B", role="office", x=[0.5, 1.0], y=[0.0, H],
               polygon=[[0.5, 0.0], [1.0, 0.0], [1.0, H], [0.5 + dx_b, H]]),
    ]


def test_r4_live_counterexample_is_unsupported_not_identity_invalid():
    # R-4 acceptance lock 1 (controller: "currently red -> green"): sol's live
    # counter-example.  Production is five-way GREEN; the judge resolves the
    # un-measurable near-orthogonal wall as capability NA, never as a topology
    # break.  This is the whole point of the batch.
    geom = _typed_correction(_shared_wall_cells(5e-10, 4e-10),
                             [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    assert all(finding.ok for finding in validate_corrected_geometry(geom))
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(geom)
    assert exc.value.code == "score_unsupported_combination"
    assert exc.value.context["reason"] == "near_orthogonal_advisory_unpaired"


def test_r4_control_exact_reverse_advisory_pairs_and_scores():
    # R-4 acceptance lock 2 (control): with both lean spellings equal (exact
    # reverse), the advisory wall pairs cleanly, extracts one interior wall, and
    # scores end-to-end -- proving the advisory path did not slap every legal
    # near-axis shape with NA.  A GT mirror (exact x=0.5 wall) is covered within
    # the judge tolerance, so the shared wall scores complete.
    H = 1.0
    geom = _typed_correction(_shared_wall_cells(5e-10, 5e-10),
                             [[0.0, 0.0], [1.0, 0.0], [1.0, H], [0.0, H]])
    assert all(finding.ok for finding in validate_corrected_geometry(geom))
    obs = [s for s in extract_correction_plan_segments(geom) if not s.exterior]
    assert len(obs) == 1
    gt = SimpleNamespace(floors=[_gt_floor("F", [[0.0, 0.0], [1.0, 0.0], [1.0, H], [0.0, H]],
        [("A", [[0.0, 0.0], [0.5, 0.0], [0.5, H], [0.0, H]]),
         ("B", [[0.5, 0.0], [1.0, 0.0], [1.0, H], [0.5, H]])])])
    targets = [s for s in extract_gt_plan_segments(gt) if not s.exterior]
    rows, _ = match_plan_segments(targets=targets, observations=obs, config=_config())
    assert _wall_criterion(rows).passing_units == pytest.approx(H)


def test_r4_non_orthogonal_edge_still_identity_invalid_verbatim():
    # R-4 acceptance lock 3: a genuinely non-orthogonal edge (both dx, dy > 1e-9)
    # is a real topology break and stays identity_invalid VERBATIM (general-seam
    # path, unchanged).  cell A leans dx=0.5, cell B leans dx=0.6 -- not exact
    # reverses, so the general seam cannot pair them.  Counterpart to advisory:
    # advisory = production admitted -> judge NA; non-orthogonal = production
    # rejects -> judge broken.  (Production rejection is pinned by
    # test_invalid_polygons_raise[not orthogonal] via cell_polygon.)
    footprint = [(0., 0.), (4., 0.), (4., 4.), (0., 4.)]
    cells = [("A", [(0., 0.), (2., 0.), (2.5, 4.), (0., 4.)]),
             ("B", [(2., 0.), (4., 0.), (4., 4.), (2.6, 4.)])]
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(_correction("F", footprint, cells))
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_r4_advisory_hit_is_recorded_at_runtime(caplog):
    # R-4 step 3 (runtime artifact): a paired near-orthogonal advisory edge is
    # recorded so a real run can answer "did this fire, how many" -- the signal
    # the later flip-to-blocking counts.  The control shape pairs cleanly and the
    # structured advisory log fires exactly once for the one shared wall.
    import logging
    geom = _typed_correction(_shared_wall_cells(5e-10, 5e-10),
                             [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    with caplog.at_level(logging.INFO, logger="src.agent.judge.segment_score"):
        extract_correction_plan_segments(geom)
    hits = [r for r in caplog.records if getattr(r, "event", None) == "near_orthogonal_advisory_hit"]
    assert len(hits) == 1
    assert hits[0].floor_id == "F"


# ---------------------------------------------------------------------------
# R2-B1: mixed-defect priority -- a real seam may never be masked by capability
# NA (collect-then-arbitrate, NOT a re-ordering of the buckets).
# ---------------------------------------------------------------------------
# sol's live counter-example (footprint [0,4]x[0,10], three cells).  Cell A's
# right edge is either EXACT or a near-vertical advisory (dx=5e-10); cells B/C
# carry a 1e-9 seam (the real topology break).  r2 ran advisory-first and the
# resulting capability NA hid the seam -- a true red washed into NA (the second
# false-green of the batch).  The fix is structural (collect diagnostics, then
# arbitrate), not a bucket swap: tile-first re-raises a DERIVATIVE
# exterior_duplicate_owner the advisory lean perturbed onto a neighbour span.


def test_r2b1_true_gap_only_is_identity_red_code_verbatim():
    # R2-B1 acceptance lock 1: a real 1e-9 seam (B/C) with NO advisory edge is
    # identity red, code verbatim.  A's right edge is EXACT here.  Production is
    # five-way GREEN, so the red is not an echo of an upstream rejection.
    geom = _typed_correction([
        CellV3(id="A", role="office", x=[0., 2.], y=[0., 10.],
               polygon=[[0., 0.], [2., 0.], [2., 10.], [0., 10.]]),
        CellV3(id="B", role="office", x=[2., 4.], y=[0., 5.],
               polygon=[[2., 0.], [4., 0.], [4., 5.], [2., 5.]]),
        CellV3(id="C", role="office", x=[2., 4.], y=[5. + 1e-9, 10.],
               polygon=[[2., 5. + 1e-9], [4., 5. + 1e-9], [4., 10.], [2., 10.]]),
    ], [[0., 0.], [4., 0.], [4., 10.], [0., 10.]])
    assert all(finding.ok for finding in validate_corrected_geometry(geom))
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(geom)
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.gate_id == "scoring.input_identity"
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_r2b1_true_gap_plus_advisory_stays_identity_red_not_na():
    # R2-B1 acceptance lock 2 (the r2 false-green root): the SAME 1e-9 seam with
    # an UNPAIRED advisory edge added (A's right edge leans dx=5e-10) must STILL
    # end identity red -- the advisory's capability NA may never mask the real
    # seam.  r2 ran advisory-first and the NA hid this seam (whole round NA, no
    # score).  Production is five-way GREEN.
    geom = _typed_correction([
        CellV3(id="A", role="office", x=[0., 2. + 5e-10], y=[0., 10.],
               polygon=[[0., 0.], [2., 0.], [2. + 5e-10, 10.], [0., 10.]]),
        CellV3(id="B", role="office", x=[2., 4.], y=[0., 5.],
               polygon=[[2., 0.], [4., 0.], [4., 5.], [2., 5.]]),
        CellV3(id="C", role="office", x=[2., 4.], y=[5. + 1e-9, 10.],
               polygon=[[2., 5. + 1e-9], [4., 5. + 1e-9], [4., 10.], [2., 10.]]),
    ], [[0., 0.], [4., 0.], [4., 10.], [0., 10.]])
    assert all(finding.ok for finding in validate_corrected_geometry(geom))
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(geom)
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.gate_id == "scoring.input_identity"
    # the root-cause real-break reason wins (invalid_interior_edge_pair), NOT
    # the derivative exterior_duplicate_owner the advisory lean perturbed onto
    # the neighbour top span (§1.2 step 3 -- closest-to-root within identity).
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_r2b1_advisory_only_no_real_break_is_capability_na():
    # R2-B1 acceptance lock 3 (no over-reject): a single unpaired advisory edge
    # with NO real seam must still resolve as capability NA -- the priority rule
    # must not slap every legal advisory shape with identity red.  Cell A alone
    # has one near-vertical advisory right edge (no facing pair) and no other
    # interior edge, so the only diagnostic is the capability NA.
    geom = _typed_correction([
        CellV3(id="A", role="office", x=[0., 2. + 5e-10], y=[0., 10.],
               polygon=[[0., 0.], [2., 0.], [2. + 5e-10, 10.], [0., 10.]]),
    ], [[0., 0.], [4., 0.], [4., 10.], [0., 10.]])
    with pytest.raises(ScoreContractError) as exc:
        extract_correction_plan_segments(geom)
    assert exc.value.code == "score_unsupported_combination"
    assert exc.value.gate_id == "scoring.capability"
    assert exc.value.context["reason"] == "near_orthogonal_advisory_unpaired"


def test_r2b1_arbitrator_real_break_outranks_capability_na():
    # R2-B1 acceptance lock 4 (the priority rule is real, not dead code): given
    # BOTH a real-break identity diagnostic and a capability NA on the same
    # floor, the arbitrator raises the identity code -- the seam may never be
    # masked.  Neuter: flip the arbitrator to capability-first (the r2 disease)
    # and this lock goes red (it would raise score_unsupported_combination).
    from src.agent.judge.segment_score import _arbitrate_pairing_diagnostics, _PairDiagnostic
    diagnostics = [
        _PairDiagnostic(category="capability", code="score_unsupported_combination",
            gate_id="scoring.capability",
            context={"reason": "near_orthogonal_advisory_unpaired", "floor_id": "F"}),
        _PairDiagnostic(category="identity", code="score_product_identity_invalid",
            gate_id="scoring.input_identity",
            context={"reason": "invalid_interior_edge_pair", "floor_id": "F"}),
    ]
    with pytest.raises(ScoreContractError) as exc:
        _arbitrate_pairing_diagnostics(diagnostics, identity_code="score_product_identity_invalid")
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.gate_id == "scoring.input_identity"
    assert exc.value.context["reason"] == "invalid_interior_edge_pair"


def test_r2b1_unpaired_advisory_edge_is_recorded_at_runtime(caplog):
    # R2-B1 / §1.3: an UNPAIRED advisory edge (the one that resolves as NA) is
    # recorded in the runtime artifact too, not only paired hits -- r2's paired-
    # hit-only log was blind to exactly the edges that trigger NA, which are the
    # ones R-4's later flip-to-blocking most needs to count.
    import logging
    geom = _typed_correction([
        CellV3(id="A", role="office", x=[0., 2. + 5e-10], y=[0., 10.],
               polygon=[[0., 0.], [2., 0.], [2. + 5e-10, 10.], [0., 10.]]),
    ], [[0., 0.], [4., 0.], [4., 10.], [0., 10.]])
    with caplog.at_level(logging.INFO, logger="src.agent.judge.segment_score"):
        with pytest.raises(ScoreContractError):
            extract_correction_plan_segments(geom)
    unpaired = [r for r in caplog.records if getattr(r, "event", None) == "near_orthogonal_advisory_unpaired"]
    assert len(unpaired) == 1
    assert unpaired[0].unpaired is True
    assert unpaired[0].floor_id == "F"
