"""②-1d: pre-projection boundary facts and independent basis reconciliation."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest
from shapely.geometry import Polygon

import src.agent.judge.answer_compiler as ac
import src.agent.judge.as_measured as am
from src.agent.judge.answer_compiler import (
    AnswerCompiler,
    BoundaryBasisMismatchError,
    BoundaryConditionMismatchError,
    OutputProfile,
    read_facts_for_compilation,
    reconcile_boundary_basis,
)
from src.agent.judge.as_measured import (
    AsMeasuredBoundaryEdgeV1,
    AsMeasuredFaceLineV1,
    AsMeasuredViewV1,
    AsMeasuredWallV1,
    derive_boundary_edges,
)
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import (
    ConversionReportV1,
    TarchConversionRequestV1,
)
from tests.answer_compiler_fixtures import synthetic_signed_facts
# ⭐ A-11 rework-1 root cause B: the deferred-projection adjudication is
# declared ONCE in tests/deferred_projection_ledger.py (F-153 form B = known
# debt, who retires it, and the pinned count) — this file and
# test_f156_ring_from_intersection.py both import it, so they cannot drift.
from tests.deferred_projection_ledger import (
    DEFERRED_PROJECTION_CODES,
    KNOWN_DEFECT_CODES,
    SM25_DEFERRED_CAVITY_COUNT,
)
from tests.deferred_projection_ledger import (
    deferred_cavities as _deferred_cavities,
)
from tests.deferred_projection_ledger import (
    failures_not_from_deferred_cavities as _failures_not_from_deferred_cavities,
)

REPO = Path(__file__).resolve().parents[1]
SM25_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
SM25_REPORT = (
    REPO / "case_tests/test_baseline/gt/sm25-L_anchor/review/conversion_report.json")


def _real_inputs():
    measured, ledger, signed = read_facts_for_compilation("sm25-L_anchor")
    request = TarchConversionRequestV1.model_validate_json(
        (SM25_SOURCE / "request_as_measured.json").read_text())
    report = ConversionReportV1.model_validate_json(SM25_REPORT.read_text())
    return measured, ledger, signed, request, report


def _edge_conditions(answer) -> list[tuple[str, str]]:
    return sorted(
        (edge.component_id, edge.evidence.boundary_condition)
        for view in answer.views for zone in view.zones for edge in zone.edges)


def test_r1_real_sm25_stores_179_projection_free_boundary_edges_in_both_facts_layers():
    """F-156: 100 -> 171.  The two corridor cavities used to yield NO ring at
    all (every one of their wall end caps read as ``owner_count=0``); they now
    carry rings, which is the whole point of the change.  A-11 (2026-09-05,
    1 mm ingest snap): 171 -> 179 -- one as-received-F1 cavity that was a
    ring LOSS closes into a ring (83 -> 91 edges), and its two rooms now
    carry rings of their own.  ⛔ The count is a readout, not the criterion
    -- the criteria are the ring identity checks below and in
    ``tests/test_f156_ring_from_intersection.py``."""
    measured, _ledger, signed, _request, _report = _real_inputs()
    for document in (measured, signed):
        edges = [edge for view in document.views for edge in view.boundary_edges]
        assert len(edges) == 179
        assert Counter(edge.boundary_condition for edge in edges) == {
            "exterior": 46, "interzone": 133}
        assert all(edge.evidence.thickness_units > 0 for edge in edges)
        assert all(edge.evidence.cavity_side_face_line_ids for edge in edges)
        assert all(edge.evidence.far_side_face_line_ids for edge in edges)
        assert all(edge.p1 != edge.p2 for edge in edges)
        # This is the independent column.  No converter projection choice is
        # copied into the first-class boundary records.
        assert all("basis" not in edge.model_dump(mode="json") for edge in edges)


def test_r1_as_signed_refreshes_boundary_evidence_after_authorized_translation():
    measured, _ledger, signed, _request = synthetic_signed_facts()
    before = {edge.id: edge for edge in measured.views[0].boundary_edges}
    after = {edge.id: edge for edge in signed.views[0].boundary_edges}
    moved = [edge_id for edge_id in before
             if before[edge_id].evidence != after[edge_id].evidence]
    assert len(moved) == 2
    assert {(before[edge_id].evidence.raw_face_const,
             after[edge_id].evidence.raw_face_const,
             before[edge_id].evidence.opposite_face_const,
             after[edge_id].evidence.opposite_face_const)
            for edge_id in moved} == {
        (49400, 49402, 50600, 50602),
        (50600, 50602, 49400, 49402),
    }
    assert all(before[edge_id].boundary_condition
               == after[edge_id].boundary_condition == "interzone"
               for edge_id in moved)


def test_r2_real_sm25_pairs_every_edge_and_lists_zero_mismatches():
    """F-156 narrows this: every paired row still agrees, and every converter
    zone is still accounted for, but the audit as a whole no longer passes.

    The two corridor cavities now HAVE rings, so they are compared instead of
    excluded -- and the comparison reports the answer-side
    ``outer_skin``<->``wall_axis`` basis switch that F-157 owns.  ⛔ That is not
    tolerated silently: it is named, with the residual in units².  ⛔ ⭐ What
    this batch does require is the zero-threshold half: NO cavity that is
    genuinely the same room as its zone may show ANY residual.
    """
    _measured, _ledger, signed, _request, report = _real_inputs()
    audit = reconcile_boundary_basis(signed, report)
    assert audit.paired_edges == 108
    assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 29)
    assert audit.mismatches == []
    # ⭐⭐⭐ Zero threshold: every cavity that is NOT reported as a
    # projected-ring difference has a residual of exactly nothing -- there is no
    # "small enough" band anywhere in this assertion.
    # A-11 (1 mm ingest snap): 100 -> 108 paired edges and 2 -> 4 deferred
    # cavities.  The snap closes the old 286.8 m2 endcap-loss cavity into two
    # REAL rooms, whose projected rings then surface the F-153 form B endcap
    # geometry difference for the first time (named ``..._is_not_the_
    # converter_zone`` rows, symdiff 1182000 units2 -- a real geometric
    # difference, ⛔ not representation noise: the reconciliation now compares
    # BOTH sides on the same 1 mm grid, so a 0.1 mm band can no longer hide
    # here).  Plus the two pre-existing ``..._unavailable`` parallel cavities
    # F-157 already owed.
    deferred = _deferred_cavities(audit)
    assert len(deferred) == SM25_DEFERRED_CAVITY_COUNT
    assert _failures_not_from_deferred_cavities(audit) == []
    assert not audit.passed  # F-157 owes two residuals; F-153 form B owes the endcap
    # ⭐ ②-1d rework3: the producer-written endcap loss (F-153 form B) is now
    # fail-loud, ⛔ no longer a silent exclusion.  No exclusion survives on the
    # honest substrate; the endcap surfaces as a NAMED red owned by the F-153
    # form B lock in ``tests/test_o21d_exclusion_gap.py``, ⛔ not asserted here
    # ([[invalidation-blast-radius-must-be-scoped]]).
    assert audit.exclusions == []
    assert Counter((row.facts_boundary_condition, row.converter_basis)
                   for row in audit.rows) == {
        ("exterior", "outer_skin"): 34,
        ("interzone", "wall_axis"): 74,
    }


def test_r2_mutating_one_boundary_condition_reddens_only_that_edge():
    _measured, ledger, signed, request, report = _real_inputs()
    baseline = reconcile_boundary_basis(signed, report)
    # ⭐ The target must be an edge that actually REACHES the per-edge
    # comparison -- ⛔ a cavity whose ring is already reported as not being its
    # zone would swallow the mutation and make this lock pass vacuously.
    paired_cavities = {proof.cavity_id for proof in baseline.pairings}
    raw = signed.model_dump(mode="json")
    target = next(edge for view in raw["views"]
                  for edge in view["boundary_edges"]
                  if (edge["boundary_condition"] == "exterior"
                      and edge["cavity_id"] in paired_cavities))
    target_id = target["id"]
    target["boundary_condition"] = "interzone"
    perturbed = AsSignedV1.model_validate(raw)

    audit = reconcile_boundary_basis(perturbed, report)
    assert not audit.passed
    assert audit.paired_edges == 108
    assert [row.facts_edge_id for row in audit.mismatches] == [target_id]
    # ⭐⭐⭐ The zero-threshold ring gate sees it too: re-projecting that edge on
    # the WRONG basis moves the ring by half a wall thickness, so the mutated
    # cavity joins the named projected-ring differences.  Every OTHER structural
    # failure still comes only from the cavities F-157 already owes.
    mutated_cavity = target["cavity_id"]
    assert any(mutated_cavity in item
               and item.startswith(DEFERRED_PROJECTION_CODES[0])
               for item in audit.structural_failures)
    allowed = {cavity for _view, cavity in _deferred_cavities(baseline)}
    allowed.add(mutated_cavity)
    # ⛔ skip the F-153 form B fail-loud reds (owned by another lock); every
    # OTHER structural failure must come only from F-157's cavities or the
    # mutated one.
    assert all(f"cavity:{item.split(':')[3]}" in allowed
               for item in audit.structural_failures
               if not item.startswith(KNOWN_DEFECT_CODES)), audit.structural_failures
    with pytest.raises(BoundaryBasisMismatchError) as exc_info:
        audit.assert_consistent()
    assert target_id in str(exc_info.value)

    with pytest.raises(BoundaryConditionMismatchError) as exc_info:
        AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
            perturbed, ledger, request)
    assert [row["facts_edge_id"] for row in exc_info.value.mismatches] == [target_id]


def test_r2_pairing_exhausts_both_directions_and_all_rotations_with_hard_limit():
    _measured, _ledger, signed, _request, report = _real_inputs()
    audit = reconcile_boundary_basis(signed, report)
    assert len(audit.pairings) == 27  # A-11: 25 -> 27 (two closed rings)
    for proof in audit.pairings:
        edge_count = len(proof.facts_edge_ids)
        assert len(proof.hypotheses) == edge_count * 2
        assert {(item.direction, item.rotation) for item in proof.hypotheses} == {
            (direction, rotation)
            for direction in ("forward", "reverse")
            for rotation in range(edge_count)}
        assert proof.selected_max_residual_units <= proof.residual_hard_limit_units
        assert proof.all_alternatives_strictly_worse
        assert (proof.alternative_min_residual_units
                > proof.selected_max_residual_units)
        assert proof.geometry_and_ancestry_pairing_identical
        assert (proof.geometric_converter_edge_indices
                == proof.ancestry_converter_edge_indices)


# --------------------------------------------------------------------------
# F-156: the two sm25 corridor cavities now carry rings, and their projected
# rings still differ from their converter zones by the answer-side
# outer_skin<->wall_axis basis switch -- F-157's residual, named on every run.
# These helpers let the OTHER locks keep asserting exact failure lists without
# either restating that residual or being weakened into "contains".
# ⛔ Not a cavity roster: membership is computed from THIS run's own
# projected-ring failures, so it empties out by itself once F-157 lands.
# --------------------------------------------------------------------------
# ⭐ A-11 rework-1 root cause B: every name below now comes from the ONE
# declaration point (``tests/deferred_projection_ledger.py`` — the
# adjudication of F-153 form B as known debt lives THERE, stated once).
# This file previously carried its own copy and drifted out of sync with
# ``test_f156_ring_from_intersection.py``, which is exactly how one substrate
# came to read green here and red there.


def _assert_structural_red(audit, expected_fragment: str) -> None:
    assert not audit.passed
    assert audit.mismatches == []
    assert any(expected_fragment in item for item in audit.structural_failures)
    with pytest.raises(BoundaryBasisMismatchError) as exc_info:
        audit.assert_consistent()
    assert expected_fragment in str(exc_info.value)


def test_rework_e3_deleting_one_complete_facts_ring_reddens_only_that_ring():
    _measured, _ledger, signed, _request, report = _real_inputs()
    baseline = reconcile_boundary_basis(signed, report)
    pairing = next(row for row in baseline.pairings
                   if row.converter_zone_id == "F1-z3")
    removed = set(pairing.facts_edge_ids)
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        view["boundary_edges"] = [
            edge for edge in view["boundary_edges"] if edge["id"] not in removed]

    audit = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)
    assert audit.paired_edges == 104  # A-11: 96 -> 104 (baseline 100 -> 108)
    assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 29)
    assert _failures_not_from_deferred_cavities(audit) == [
        f"facts_boundary_ring_missing:plan-F1:{pairing.cavity_id}:converter=F1-z3"]
    _assert_structural_red(audit, "facts_boundary_ring_missing:plan-F1")


def test_rework_e4_all_boundary_facts_empty_is_never_zero_comparisons_green():
    _measured, _ledger, signed, _request, report = _real_inputs()
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        view["boundary_edges"] = []

    audit = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)
    assert audit.paired_edges == 0
    assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 29)
    assert sum(item.startswith("facts_boundary_edges_empty:")
               for item in audit.structural_failures) == 2
    assert sum(item.startswith("facts_boundary_ring_missing:")
               for item in audit.structural_failures) == 29  # A-11: +2 rings
    assert not any(item.startswith("converter_zone_unclaimed_by_facts:")
                   for item in audit.structural_failures)
    _assert_structural_red(audit, "facts_boundary_edges_empty:plan-F1")


def test_rework_e2c_converter_zone_fifty_metres_outside_all_facts_is_named():
    _measured, _ledger, signed, _request, report = _real_inputs()
    report_raw = report.model_dump(mode="python")
    phantom = deepcopy(next(zone for zone in report_raw["zones"]
                            if zone["zone_id"] == "F1-z3"))
    phantom["zone_id"] = "F1-phantom-50m"
    phantom["name"] = "phantom-50m"
    for edge in phantom["edges"]:
        edge["p1"] = [edge["p1"][0] + 50.0, edge["p1"][1] + 50.0]
        edge["p2"] = [edge["p2"][0] + 50.0, edge["p2"][1] + 50.0]
    phantom["polygon_m"]["exterior"]["vertices"] = [
        [point[0] + 50.0, point[1] + 50.0]
        for point in phantom["polygon_m"]["exterior"]["vertices"]]
    phantom["seed_point_world_m"] = [
        phantom["seed_point_world_m"][0] + 50.0,
        phantom["seed_point_world_m"][1] + 50.0,
    ]
    report_raw["zones"].append(phantom)

    audit = reconcile_boundary_basis(
        signed, ConversionReportV1.model_validate(report_raw))
    assert audit.paired_edges == 108  # A-11: 100 -> 108
    assert (audit.accounted_converter_zones, audit.converter_zones) == (29, 30)
    assert _failures_not_from_deferred_cavities(audit) == [
        "converter_zone_facts_cavity_pairing_not_unique:"
        "plan-F1:F1-phantom-50m:[]",
        "converter_zone_unclaimed_by_facts:F1:F1-phantom-50m",
    ]
    _assert_structural_red(
        audit, "converter_zone_unclaimed_by_facts:F1:F1-phantom-50m")


def test_rework_real_sm25_two_metre_footprint_vertex_spike_reddens_the_lost_view():
    """Acceptance 3: real sm25 geometry, not a hand-cleared edge list."""
    _measured, _ledger, signed, request, report = _real_inputs()
    raw = signed.model_dump(mode="json")
    plan_f1 = next(view for view in raw["views"]
                   if view["view_id"] == "plan-F1")
    exterior = next(ring for ring in plan_f1["footprint"]["rings"]
                    if ring["kind"] == "exterior")
    vertex = exterior["points"].index([50_000, 40_000])
    exterior["points"][vertex] = [50_000, 60_000]  # +20,000 units = +2 m
    for view in raw["views"]:
        measured_view = AsMeasuredViewV1.model_validate(view)
        view["boundary_edges"] = [
            edge.model_dump(mode="json") for edge in derive_boundary_edges(
                measured_view, min_room_area_m2=request.min_room_area_m2)]

    perturbed = AsSignedV1.model_validate(raw)
    assert {view.view_id: len(view.boundary_edges) for view in perturbed.views} == {
        "plan-F1": 0, "plan-F2": 88}
    audit = reconcile_boundary_basis(perturbed, report)
    assert audit.paired_edges == 56
    assert (audit.accounted_converter_zones, audit.converter_zones) == (15, 29)
    assert all("plan-F2" not in item
               for item in _failures_not_from_deferred_cavities(audit))
    _assert_structural_red(
        audit, "facts_boundary_footprint_unusable:plan-F1")


def test_rework_e4_multi_exterior_branch_has_an_explicit_synthetic_lock():
    """The corpus has zero real multi-exterior stock; this fixture is synthetic."""
    _measured, _ledger, signed, request, report = _real_inputs()
    raw = signed.model_dump(mode="json")
    plan_f1 = next(view for view in raw["views"]
                   if view["view_id"] == "plan-F1")
    exterior = deepcopy(next(ring for ring in plan_f1["footprint"]["rings"]
                             if ring["kind"] == "exterior"))
    exterior["polygon_index"] = 1
    exterior["points"] = [[x + 500_000, y] for x, y in exterior["points"]]
    plan_f1["footprint"]["rings"].append(exterior)
    measured_view = AsMeasuredViewV1.model_validate(plan_f1)
    plan_f1["boundary_edges"] = [
        edge.model_dump(mode="json") for edge in derive_boundary_edges(
            measured_view, min_room_area_m2=request.min_room_area_m2)]
    assert plan_f1["boundary_edges"] == []

    audit = reconcile_boundary_basis(AsSignedV1.model_validate(raw), report)
    assert audit.paired_edges == 56
    _assert_structural_red(
        audit, "answer_compiler_requires_one_exterior_ring:plan-F1:2")


def test_r3_synthetic_supply_measures_unclaimed_void_and_unknown():
    """Supply the two real drawing shapes absent from sm25's projected stock.

    ``unclaimed_void`` models a wall facing a sub-threshold service shaft that
    was not admitted to the room-cavity population.  ``unknown`` models an
    axis-aligned room wall facing a diagonal/chamfered footprint edge: the ray
    leaves the footprint, but there is no axis-aligned ring edge to witness.
    """
    lo = AsMeasuredFaceLineV1(
        id="A1", layer="WALL", axis="y", const=100,
        along_min=100, along_max=900)
    hi = AsMeasuredFaceLineV1(
        id="A2", layer="WALL", axis="y", const=200,
        along_min=100, along_max=900)
    wall = AsMeasuredWallV1(
        id="wall", axis="y", face_lo=100, face_hi=200, thickness=100,
        along_min=100, along_max=900,
        face_line_ids_lo=["A1"], face_line_ids_hi=["A2"])
    group = am._BoundaryWallGroup(
        axis="y", face_lo=100, face_hi=200, runs=(wall,), openings=())
    span = am._BoundarySpan(
        axis="y", cavity_const=100, lo=100, hi=900, side=-1,
        p1=(100, 100), p2=(100, 900), group=group,
        boundary_condition="unknown")
    rectangular = Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])
    rectangular_ring = [(
        "footprint:synthetic:ring:0",
        [[0, 0], [1000, 0], [1000, 1000], [0, 1000], [0, 0]])]
    condition, unclaimed_evidence, logical = am._classify_boundary_fact(
        span, 100, 200, rectangular, rectangular_ring,
        Polygon(), [], {})
    assert (condition, logical, unclaimed_evidence.adjacent_cavity_id) == (
        "unclaimed_void", True, None)

    diagonal = Polygon([(0, 0), (1000, 0), (500, 1000)])
    diagonal_ring = [(
        "footprint:synthetic:ring:0",
        [[0, 0], [1000, 0], [500, 1000], [0, 0]])]
    diagonal_group = am._BoundaryWallGroup(
        axis="y", face_lo=700, face_hi=800,
        runs=(AsMeasuredWallV1(
            id="diagonal-wall", axis="y", face_lo=700, face_hi=800,
            thickness=100, along_min=100, along_max=900,
            face_line_ids_lo=["A1"], face_line_ids_hi=["A2"]),),
        openings=())
    diagonal_span = am._BoundarySpan(
        axis="y", cavity_const=700, lo=100, hi=900, side=-1,
        p1=(700, 100), p2=(700, 900), group=diagonal_group,
        boundary_condition="unknown")
    condition, unknown_evidence, logical = am._classify_boundary_fact(
        diagonal_span, 700, 800, diagonal, diagonal_ring,
        Polygon(), [], {})
    assert (condition, logical, unknown_evidence.footprint_edge_id) == (
        "unknown", True, None)

    # Both measurements fit the same first-class schema consumed in production.
    for index, (condition, evidence, span_value, wall_value) in enumerate((
            ("unclaimed_void", unclaimed_evidence, span, wall),
            ("unknown", unknown_evidence, diagonal_span,
             diagonal_group.runs[0]))):
        row = AsMeasuredBoundaryEdgeV1(
            id=f"synthetic-{index}", cavity_id="synthetic-cavity",
            sequence=index, axis=span_value.axis,
            cavity_const=span_value.cavity_const,
            span_lo=span_value.lo, span_hi=span_value.hi,
            side=span_value.side, p1=list(span_value.p1), p2=list(span_value.p2),
            wall_ids=[wall_value.id], face_line_handles=["A1", "A2"],
            boundary_condition=condition, evidence=evidence)
        assert row.boundary_condition == condition


def test_r4_clear_every_converter_judgment_readout_and_renamed_carrier_has_teeth(
        monkeypatch):
    _measured, ledger, signed, request, _report = _real_inputs()
    compiler = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN)
    baseline = compiler.compile(signed, ledger, request).model_dump(mode="json")

    judgment_fields = (
        "diagnostics", "gates", "unresolved_opening_carriers",
        "face_groups_with_a_split_const",
        "jamb_cap_bands_missing_a_face_line", "axis_snapped_lines",
    )

    def cleared(document: AsSignedV1) -> AsSignedV1:
        raw = document.model_dump(mode="json")
        for view in raw["views"]:
            for field in judgment_fields:
                view["converter_readouts"][field] = []
        return AsSignedV1.model_validate(raw)

    without_judgments = cleared(signed)
    assert compiler.compile(
        without_judgments, ledger, request).model_dump(mode="json") == baseline

    raw = signed.model_dump(mode="json")
    raw["views"][0]["converter_readouts"]["diagnostics"].append({
        "code": "synthetic_ignored_metadata", "severity": "INFO",
        "stage": "test", "action_code": "none", "handles": [],
        "points_dxf_mm": [],
        "context": {"classification_hint": "interzone"},
    })
    with_renamed_carrier = AsSignedV1.model_validate(raw)
    assert compiler.compile(
        with_renamed_carrier, ledger, request).model_dump(mode="json") == baseline

    original_lookup = ac._stored_boundary_for_span

    def bad_lookup(view, cavity_id, span, group):
        record = original_lookup(view, cavity_id, span, group)
        hints = [diagnostic.get("context", {}).get("classification_hint")
                 for diagnostic in view.converter_readouts.diagnostics]
        hint = next((value for value in hints if value), None)
        if record is not None and hint is not None:
            return record.model_copy(update={"boundary_condition": hint})
        return record

    monkeypatch.setattr(ac, "_stored_boundary_for_span", bad_lookup)
    # Counterfactual: if the compiler starts consuming this arbitrarily named
    # carrier, the semantic clear-all lock is observably red.
    with pytest.raises(BoundaryConditionMismatchError):
        compiler.compile(with_renamed_carrier, ledger, request)
    compiler.compile(without_judgments, ledger, request)


def test_r5_deleting_boundary_edges_preserves_independent_reclassification():
    _measured, ledger, signed, request, _report = _real_inputs()
    raw = signed.model_dump(mode="json")
    for view in raw["views"]:
        del view["boundary_edges"]
    without_boundary_facts = AsSignedV1.model_validate(raw)

    for profile in OutputProfile:
        compiler = AnswerCompiler(profile)
        stored = compiler.compile(signed, ledger, request)
        recomputed = compiler.compile(without_boundary_facts, ledger, request)
        assert _edge_conditions(stored) == _edge_conditions(recomputed)
        assert [(view.counts, [zone.vertices for zone in view.zones])
                for view in stored.views] == [
                    (view.counts, [zone.vertices for zone in view.zones])
                    for view in recomputed.views]
