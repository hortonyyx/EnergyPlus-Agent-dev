"""②-1d: pre-projection boundary facts and independent basis reconciliation."""
from __future__ import annotations

from collections import Counter
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
    AsMeasuredWallV1,
)
from src.agent.judge.gt_revisions import AsSignedV1
from src.agent.judge.tarch_converter_schema import (
    ConversionReportV1,
    TarchConversionRequestV1,
)
from tests.answer_compiler_fixtures import synthetic_signed_facts

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


def test_r1_real_sm25_stores_100_projection_free_boundary_edges_in_both_facts_layers():
    measured, _ledger, signed, _request, _report = _real_inputs()
    for document in (measured, signed):
        edges = [edge for view in document.views for edge in view.boundary_edges]
        assert len(edges) == 100
        assert Counter(edge.boundary_condition for edge in edges) == {
            "exterior": 32, "interzone": 68}
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
    _measured, _ledger, signed, _request, report = _real_inputs()
    audit = reconcile_boundary_basis(signed, report)
    assert audit.passed
    assert audit.paired_edges == 100
    assert audit.mismatches == []
    assert audit.structural_failures == []
    assert Counter((row.facts_boundary_condition, row.converter_basis)
                   for row in audit.rows) == {
        ("exterior", "outer_skin"): 32,
        ("interzone", "wall_axis"): 68,
    }


def test_r2_mutating_one_boundary_condition_reddens_only_that_edge():
    _measured, ledger, signed, request, report = _real_inputs()
    raw = signed.model_dump(mode="json")
    target = next(edge for view in raw["views"]
                  for edge in view["boundary_edges"]
                  if edge["boundary_condition"] == "exterior")
    target_id = target["id"]
    target["boundary_condition"] = "interzone"
    perturbed = AsSignedV1.model_validate(raw)

    audit = reconcile_boundary_basis(perturbed, report)
    assert not audit.passed
    assert audit.paired_edges == 100
    assert [row.facts_edge_id for row in audit.mismatches] == [target_id]
    assert audit.structural_failures == []
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
    assert len(audit.pairings) == 25
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
