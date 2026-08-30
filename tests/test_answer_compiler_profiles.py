"""②-1c: signed-fixture, real-sm25, profile, and 6a/6b/6c locks."""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Polygon

from src.agent.judge.answer_compiler import (
    AnswerCompiler,
    CompiledZoneEdgeV1,
    OutputProfile,
    _merge_projected_spans,
    _support_vertices,
    read_facts_for_compilation,
)
from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1
from tests.answer_compiler_fixtures import synthetic_signed_facts

REPO = Path(__file__).resolve().parents[1]
SM25_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
SM25_GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"
UNITS = 10_000


def _by_zone(answer):
    return {zone.zone_id: zone for zone in answer.views[0].zones}


def test_1a_fully_signed_synthetic_ledger_reproduces_the_known_target_bit_for_bit():
    measured, ledger, signed, request = synthetic_signed_facts()
    assert all(record.verdict == "drawing_error" and record.action is not None
               for record in ledger.revisions)
    # The signed actions really moved the facts-layer inputs used by the
    # compiler; this is not a known target that happens to equal as_measured.
    before = {face.id: face.const for face in measured.views[0].face_lines}
    after = {face.id: face.const for face in signed.views[0].face_lines}
    assert (before["A9"], before["AA"]) == (49400, 50600)
    assert (after["A9"], after["AA"]) == (49402, 50602)

    form_a = _by_zone(AnswerCompiler(OutputProfile.FORM_A_AXIS).compile(
        signed, ledger, request))
    form_b = _by_zone(AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        signed, ledger, request))
    assert form_a["F1-left"].vertices == [
        [1200, 58800], [50002, 58800], [50002, 1200], [1200, 1200]]
    assert form_a["F1-right"].vertices == [
        [50002, 1200], [50002, 58800], [98800, 58800], [98800, 1200]]
    assert form_b["F1-left"].vertices == [
        [0, 60000], [50002, 60000], [50002, 0], [0, 0]]
    assert form_b["F1-right"].vertices == [
        [50002, 0], [50002, 60000], [100000, 60000], [100000, 0]]


def test_1b_real_sm25_reproduces_every_projectable_form_b_zone_and_names_unsigned_na():
    _measured, ledger, signed = read_facts_for_compilation("sm25-L_anchor")
    request = TarchConversionRequestV1.model_validate_json(
        (SM25_SOURCE / "request_as_measured.json").read_text())
    answer = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        signed, ledger, request)
    assert {record.component_id for record in answer.unresolved_revisions} >= {
        "rev-13ad", "rev-13ae", "rev-13af"}
    assert all(record.reason_code == "revision_has_no_signed_verdict"
               for record in answer.unresolved_revisions)
    assert {view.view_id: view.counts["projected_zones"] for view in answer.views} == {
        "plan-F1": 11, "plan-F2": 14}
    unsigned_na_zones = [
        zone for view in answer.views for zone in view.zones
        if any(record.rule == "unsigned_revision" for record in zone.na)]
    assert unsigned_na_zones, "unsigned revisions must invalidate their incident rings"
    assert all(zone.vertices is None and zone.edges == []
               for zone in unsigned_na_zones)

    gt = json.loads(SM25_GT.read_text())
    gt_floor = {floor["id"]: floor for floor in gt["floors"]}
    checked = 0
    for view in answer.views:
        for zone in view.zones:
            if zone.vertices is None:
                assert zone.edges == []  # zero coordinate leakage from a partial ring
                continue
            polygon = Polygon(zone.vertices)
            representative = polygon.representative_point()
            matches = []
            for expected in gt_floor[view.floor_id]["zones"]:
                expected_polygon = Polygon([
                    (round(x * UNITS), round(y * UNITS))
                    for x, y in expected["polygon"]["exterior"]["vertices"]])
                if expected_polygon.contains(representative):
                    matches.append(expected)
            assert len(matches) == 1
            expected_vertices = {
                (round(x * UNITS), round(y * UNITS))
                for x, y in matches[0]["polygon"]["exterior"]["vertices"]}
            assert set(map(tuple, zone.vertices)) == expected_vertices
            checked += 1
    assert checked == 25


def test_6a_axis_profile_deduplicates_a_collapsed_step_and_counterfactual_is_red():
    _measured, ledger, signed, request = synthetic_signed_facts()
    template = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        signed, ledger, request).views[0].zones[0].edges[0]

    def edge(index, axis, support):
        raw = template.model_dump(mode="json")
        raw.update(component_id=f"edge-{index}", axis=axis,
                   support_const=support, span_lo=index * 10,
                   span_hi=(index + 1) * 10)
        return CompiledZoneEdgeV1.model_validate(raw)

    # The third support line repeats x=0.  Intersecting supports without 6a
    # emits two adjacent (0,0) vertices, the degenerate edge that originally
    # made cell_polygon red.
    edges = [edge(0, "y", 0), edge(1, "x", 30000), edge(2, "y", 0),
             edge(3, "x", 0), edge(4, "y", 50000),
             edge(5, "x", 60000)]
    raw_vertices = []
    for index, current in enumerate(edges):
        previous = edges[index - 1]
        raw_vertices.append(
            (previous.support_const, current.support_const)
            if previous.axis == "y"
            else (current.support_const, previous.support_const))
    assert any(left == right for left, right in zip(raw_vertices, raw_vertices[1:])), (
        "counterfactual lost its degenerate edge and can no longer prove 6a")
    vertices, failures = _support_vertices(edges, "fixture-6a")
    assert not failures
    assert not any(left == right for left, right in zip(vertices, vertices[1:]))


def test_6b_one_wall_support_cannot_switch_basis_mid_span():
    _measured, ledger, signed, request = synthetic_signed_facts()
    edge = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        signed, ledger, request).views[0].zones[0].edges[0]
    first = edge.model_copy(update={"component_id": "same-wall-a", "span_lo": 0,
                                    "span_hi": 10})
    second = edge.model_copy(update={"component_id": "same-wall-b", "span_lo": 10,
                                     "span_hi": 20})
    assert len(_merge_projected_spans([first, second])) == 1

    # Counterfactual: choose a role-specific midline for the second half of
    # the same wall.  The 120 mm half-thickness step remains and the support
    # list can no longer be one wall line -- the gate is observably red.
    switched = second.model_copy(update={
        "support_const": second.support_const + edge.evidence.thickness_units // 2,
        "basis": "wall_axis"})
    assert len(_merge_projected_spans([first, switched])) == 2
    assert first.support_const != switched.support_const


def test_6c_vertices_are_support_line_intersections_not_wall_endpoints():
    _measured, ledger, signed, request = synthetic_signed_facts()
    form_b = _by_zone(AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        signed, ledger, request))
    left = form_b["F1-left"]
    partition = next(edge for edge in left.edges if edge.wall_ids == ["wall-partition"])
    assert partition.span_lo == 2400 and partition.span_hi == 57600
    # Its final endpoints come from the adjacent exterior support lines.
    assert [50002, 0] in left.vertices and [50002, 60000] in left.vertices
    assert [50002, 2400] not in left.vertices and [50002, 57600] not in left.vertices


def test_profiles_have_the_three_metamorphic_relations_in_both_directions():
    _measured, ledger, signed, request = synthetic_signed_facts()
    axis_compiler = AnswerCompiler(OutputProfile.FORM_A_AXIS)
    skin_compiler = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN)
    axis = axis_compiler.compile(signed, ledger, request)
    skin = skin_compiler.compile(signed, ledger, request)

    def edges_by_wall(answer):
        return {tuple(edge.wall_ids): edge
                for zone in answer.views[0].zones for edge in zone.edges}

    a_edges, b_edges = edges_by_wall(axis), edges_by_wall(skin)
    assert a_edges[("wall-partition",)].support_const == 50002
    assert b_edges[("wall-partition",)].support_const == 50002
    for wall_id in ("wall-south", "wall-north", "wall-west", "wall-east"):
        a_edge, b_edge = a_edges[(wall_id,)], b_edges[(wall_id,)]
        assert abs(a_edge.support_const - b_edge.support_const) == (
            a_edge.evidence.thickness_units // 2)

    assert axis_compiler.reproject(
        axis, signed, ledger, request,
        to_profile=OutputProfile.FORM_B_EXTERIOR_SKIN).model_dump(mode="json") == (
            skin.model_dump(mode="json"))
    assert skin_compiler.reproject(
        skin, signed, ledger, request,
        to_profile=OutputProfile.FORM_A_AXIS).model_dump(mode="json") == (
            axis.model_dump(mode="json"))


def test_clear_span_is_a_derived_table_not_a_profile():
    _measured, ledger, signed, request = synthetic_signed_facts()
    assert {profile.value for profile in OutputProfile} == {
        "form_a_axis", "form_b_exterior_skin"}
    answer = AnswerCompiler(OutputProfile.FORM_A_AXIS).compile(
        signed, ledger, request)
    table = AnswerCompiler.clear_span_table(answer)
    assert table["profile_kind"] == "derived_clear_span_area"
    assert [row["clear_span_area_m2"] for row in table["views"]["plan-S"]] == [
        25.944, 25.944]
