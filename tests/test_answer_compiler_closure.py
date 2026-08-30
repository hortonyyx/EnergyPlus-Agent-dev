"""Each sol-B6 dependency propagation rule has an executable fixture."""
from __future__ import annotations

import src.agent.judge.answer_compiler as ac
from src.agent.judge.answer_compiler import AnswerCompiler, OutputProfile
from src.agent.judge.gt_revisions import AsSignedV1
from tests.answer_compiler_fixtures import (
    bind_signed_to_request,
    replace_signed_view,
    request_with_affine,
    synthetic_signed_facts,
)


def _metric(view, name):
    return next(metric for metric in view.metrics if metric.metric == name)


def _assert_na_zone_has_no_coordinate_payload(zone):
    assert zone.vertices is None
    assert zone.edges == []
    dumped = zone.model_dump(mode="json")
    assert dumped["vertices"] is None and dumped["edges"] == []
    for record in dumped["na"]:
        assert not any(token in key for key in record
                       for token in ("point", "vertex", "span", "const", "interval", "axis"))


def _without_partition(signed: AsSignedV1) -> AsSignedV1:
    view = signed.views[0].model_dump(mode="json")
    view["walls"] = [wall for wall in view["walls"] if wall["id"] != "wall-partition"]
    view["converter_readouts"]["face_lines_not_paired_into_a_wall"] = ["A9", "AA"]
    return replace_signed_view(signed, view)


def test_rule_1_missing_segment_invalidates_incident_ring_and_keeps_denominator():
    _measured, ledger, signed, request = synthetic_signed_facts()
    damaged = _without_partition(signed)
    view = AnswerCompiler(OutputProfile.FORM_A_AXIS).compile(
        damaged, ledger, request).views[0]
    assert view.counts == {
        "declared_zones": 2, "measured_cavities": 1,
        "projected_zones": 0, "na_zones": 2,
        "openings": 0, "na_openings": 0}
    assert all(zone.vertices is None for zone in view.zones)
    assert any(record.reason_code == "unpaired_face_line_intersects_the_zone_component"
               for zone in view.zones for record in zone.na)
    metric = _metric(view, "zone_geometry")
    assert (metric.coverage_expected, metric.coverage_available,
            metric.coverage_na) == (2, 0, 2)


def test_rule_2_uncertain_junction_invalidates_every_incident_segment_and_ring():
    _measured, ledger, signed, request = synthetic_signed_facts()
    view = signed.views[0].model_dump(mode="json")
    # A diagonal footprint edge produces a corner for which the orthogonal
    # support-line intersection invariant has no answer.
    view["footprint"]["rings"][0]["points"] = [
        [0, 0], [100000, 0], [99000, 60000], [0, 60000], [0, 0]]
    # Remove the east strip so the right cavity actually reaches that diagonal
    # boundary; otherwise the strip masks it and the fixture has no stock.
    view["walls"] = [wall for wall in view["walls"] if wall["id"] != "wall-east"]
    view["converter_readouts"]["face_lines_not_paired_into_a_wall"] = ["A7", "A8"]
    damaged = replace_signed_view(signed, view)
    compiled = AnswerCompiler(OutputProfile.FORM_A_AXIS).compile(
        damaged, ledger, request).views[0]
    affected = [zone for zone in compiled.zones
                if any(record.rule == "junction_dependency" for record in zone.na)]
    assert affected
    for zone in affected:
        _assert_na_zone_has_no_coordinate_payload(zone)
        assert any(record.reason_code == "incident_component_invalidated_the_complete_ring"
                   for record in zone.na)


def test_rule_3_bad_view_affine_makes_all_coordinate_metrics_na_without_coordinates():
    _measured, ledger, signed, request = synthetic_signed_facts()
    bad_request = request_with_affine(request, m01=0.25)
    rebound = bind_signed_to_request(signed, bad_request)
    view = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        rebound, ledger, bad_request).views[0]
    assert all(zone.vertices is None for zone in view.zones)
    assert all(zone.clear_span_area_units2 is None for zone in view.zones)
    assert _metric(view, "zone_count").status == "na"
    assert _metric(view, "zone_geometry").status == "na"
    assert _metric(view, "clear_span_area").status == "na"
    assert {record.rule for record in view.na} == {"view_coordinate_source"}


def test_rule_4_ambiguous_opening_is_local_and_does_not_kill_zones_or_outline():
    _measured, ledger, signed, request = synthetic_signed_facts()
    view = signed.views[0].model_dump(mode="json")
    view["openings"] = [{
        "id": "AB", "block_name": "SYNTH-WINDOW", "kind": "window",
        "axis": "x", "along_min": 40000, "along_max": 50000,
        "cross_lo": 0, "cross_hi": 2400, "carrier_wall_ids": [],
        "jamb_handles": [], "classification": "exterior",
    }]
    view["converter_readouts"]["unresolved_opening_carriers"] = [{
        "opening_id": "AB", "reason": "no_wall_with_this_face_pair",
        "candidate_wall_ids": [],
    }]
    damaged = replace_signed_view(signed, view)
    compiled = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        damaged, ledger, request).views[0]
    assert compiled.counts["projected_zones"] == 2
    assert _metric(compiled, "zone_count").status == "available"
    assert _metric(compiled, "zone_geometry").status == "available"
    assert _metric(compiled, "opening_geometry").status == "na"
    assert len(compiled.openings) == 1
    opening = compiled.openings[0]
    assert opening.status == "na" and opening.axis is None
    assert opening.along_interval is None and opening.cross_interval is None
    assert opening.na[0].rule == "opening_local"


def test_rule_5_boundary_unknown_is_profile_sensitive_axis_green_exterior_na(monkeypatch):
    _measured, ledger, signed, request = synthetic_signed_facts()
    original = ac._classify_boundary

    def unknown(*args, **kwargs):
        _condition, evidence = original(*args, **kwargs)
        return "unclaimed_void", {**evidence, "boundary_condition": "unclaimed_void"}

    monkeypatch.setattr(ac, "_classify_boundary", unknown)
    axis = AnswerCompiler(OutputProfile.FORM_A_AXIS).compile(
        signed, ledger, request).views[0]
    exterior = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        signed, ledger, request).views[0]
    assert axis.counts["projected_zones"] == 2
    assert exterior.counts["projected_zones"] == 0
    assert all(zone.vertices is None and zone.edges == [] for zone in exterior.zones)
    assert any(record.rule == "profile_dependency"
               for zone in exterior.zones for record in zone.na)


def test_rule_6_missing_component_is_na_and_never_removed_from_the_score_denominator():
    _measured, ledger, signed, request = synthetic_signed_facts()
    view = AnswerCompiler(OutputProfile.FORM_B_EXTERIOR_SKIN).compile(
        _without_partition(signed), ledger, request).views[0]
    for metric_name in ("zone_geometry", "clear_span_area"):
        metric = _metric(view, metric_name)
        assert metric.coverage_expected == 2
        assert metric.coverage_available + metric.coverage_na == 2
    assert len(view.zones) == 2, "the missing target must remain as an NA slot"
    for zone in view.zones:
        if zone.vertices is None:
            _assert_na_zone_has_no_coordinate_payload(zone)
