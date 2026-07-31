"""Slices 2/3 RED locks for aggregate ReadingView normalization."""

from __future__ import annotations

import copy

from src.agent.judge.score_schema import ElevationScoreViewBindingV1
from tests.test_reading_typed_scoring_slice0 import _real_payload
from tests.test_reading_typed_scoring_slice1 import _trusted_request


def _normalize(payload: dict | None = None, *, bindings=None):
    from src.agent.judge.reading_typed_adapter import normalize_reading_attempt

    raw = _real_payload() if payload is None else payload
    request = _trusted_request(raw)
    return normalize_reading_attempt(
        raw=raw,
        source_output_sha256=request["product_identity"].output_sha256,
        base_manifest=request["base_view_manifest"],
        score_bindings=bindings or request["score_bindings"],
    )


def _applicability(outcome):
    return {
        (item.source_input_id, item.component): item
        for item in outcome.certificate.component_applicability
    }


def _elevation_observations(outcome):
    return tuple(
        item
        for item in outcome.certificate.observations
        if item.kind == "elevation_opening"
    )


def test_real_elevations_use_canonical_ranges_and_ruled_vertical_fallback():
    outcome = _normalize()
    observations = _elevation_observations(outcome)
    applicability = _applicability(outcome)

    assert len(observations) == 6
    assert {
        item.source_input_id for item in observations
    } == {"East_view", "South_view"}
    assert len(outcome.certificate.vertical_datums) == 4
    assert all(
        item.source == "project_convention_2026_07_25"
        and item.z_origin == 0.0
        and item.authority
        == "user_ruling_grade_line_equals_interior_floor_zero"
        for item in outcome.certificate.vertical_datums
    )
    for source, expected_count in (("East_view", 4), ("South_view", 2)):
        for component in ("elevation_opening_xy", "elevation_opening_z"):
            row = applicability[(source, component)]
            assert row.status == "applicable"
            assert row.observation_count == expected_count
    for source in ("North_view", "West_view"):
        for component in ("elevation_opening_xy", "elevation_opening_z"):
            row = applicability[(source, component)]
            assert row.status == "not_applicable"
            assert row.cause_class == "trusted_frame"
            assert row.denominator_disposition == "retain_as_miss"


def test_aligned_elevations_project_exactly_and_raw_ids_are_namespaced():
    payload = _real_payload()
    for source in ("North_view", "West_view"):
        payload["views"][source]["facade"]["local_x_positive"] = (
            "image_left_to_right"
        )
        payload["views"][source]["facade"]["mirrored"] = "false"
    outcome = _normalize(payload)
    observations = _elevation_observations(outcome)

    assert len(observations) == 13
    assert len({item.observation_id for item in observations}) == 13
    repeated_s3 = [
        item for item in observations if item.source_stroke_id == "S3"
    ]
    assert len(repeated_s3) == 4
    assert len({item.observation_id for item in repeated_s3}) == 4

    by_raw = {
        (item.source_input_id, item.source_stroke_id): item
        for item in observations
    }
    east = by_raw[("East_view", "S3")]
    assert (east.world_along_interval.lo, east.world_along_interval.hi) == (
        3.5,
        5.3,
    )
    assert (east.z_interval.lo, east.z_interval.hi) == (2.4, 3.5)
    south = by_raw[("South_view", "S3")]
    assert (south.world_along_interval.lo, south.world_along_interval.hi) == (
        2.04,
        4.54,
    )
    north = by_raw[("North_view", "S3")]
    assert (north.world_along_interval.lo, north.world_along_interval.hi) == (
        5.34,
        9.46,
    )
    west = by_raw[("West_view", "S3")]
    assert (west.world_along_interval.lo, west.world_along_interval.hi) == (
        17.66,
        19.159999999999997,
    )


def test_sm24_frame_disagreement_witness_preserves_raw_declarations():
    outcome = _normalize()
    witnesses = {
        item.source_input_id: item
        for item in outcome.certificate.elevation_frame_disagreements
    }
    assert tuple(sorted(witnesses)) == ("North_view", "West_view")
    for source in ("North_view", "West_view"):
        witness = witnesses[source]
        assert witness.binding_local_x_positive == "image_left_to_right"
        assert witness.product_local_x_positive_raw == "image_right_to_left"
        assert (
            witness.product_local_x_positive_effective
            == "image_right_to_left"
        )
        assert witness.binding_mirrored is False
        assert witness.product_mirrored_raw == "false"
        assert witness.product_mirrored_effective is False
        assert witness.reason == "elevation_local_x_sense_disagreement"


def test_elevation_zero_missing_and_malformed_are_distinct():
    empty = _real_payload()
    empty["views"]["East_view"]["strokes"] = [
        item
        for item in empty["views"]["East_view"]["strokes"]
        if item["pen"] != "window"
    ]
    empty_outcome = _normalize(empty)
    empty_app = _applicability(empty_outcome)
    for component in ("elevation_opening_xy", "elevation_opening_z"):
        assert empty_app[("East_view", component)].status == "applicable"
        assert empty_app[("East_view", component)].observation_count == 0

    missing = _real_payload()
    del missing["views"]["East_view"]
    missing_app = _applicability(_normalize(missing))
    for component in ("elevation_opening_xy", "elevation_opening_z"):
        row = missing_app[("East_view", component)]
        assert row.status == "not_applicable"
        assert row.reasons == ("reading_view_missing",)
        assert row.cause_class == "product_content"
        assert row.denominator_disposition == "retain_as_miss"

    malformed = _real_payload()
    malformed["views"]["East_view"]["strokes"][2]["geometry"] = {}
    malformed_outcome = _normalize(malformed)
    malformed_app = _applicability(malformed_outcome)
    for component in ("elevation_opening_xy", "elevation_opening_z"):
        row = malformed_app[("East_view", component)]
        assert row.status == "not_applicable"
        assert row.reasons == ("elevation_opening_geometry_unsupported",)
        assert row.denominator_disposition == "retain_as_miss"
    assert any(
        item.source_input_id == "East_view"
        and item.source_stroke_id == "S3"
        and item.reason == "consumed_geometry_malformed"
        for item in malformed_outcome.certificate.unmeasurable_observation_witnesses
    )


def test_elevation_line_polyline_and_degenerate_bounds_are_measurable():
    payload = _real_payload()
    payload["views"]["East_view"]["strokes"] = [
        {
            "id": "line-point",
            "pen": "window",
            "geometry": {
                "kind": "line",
                "p1": [1.0, 2.0],
                "p2": [1.0, 2.0],
            },
        },
        {
            "id": "poly",
            "pen": "window",
            "geometry": {
                "kind": "polyline",
                "points": [[4.0, 3.0], [2.0, 1.0], [3.0, 5.0]],
                "closed": False,
            },
        },
    ]
    outcome = _normalize(payload)
    rows = {
        item.source_stroke_id: item
        for item in _elevation_observations(outcome)
        if item.source_input_id == "East_view"
    }
    point = rows["line-point"]
    assert (point.local_x_interval.lo, point.local_x_interval.hi) == (1.0, 1.0)
    assert (point.local_y_interval.lo, point.local_y_interval.hi) == (2.0, 2.0)
    poly = rows["poly"]
    assert (poly.local_x_interval.lo, poly.local_x_interval.hi) == (2.0, 4.0)
    assert (poly.local_y_interval.lo, poly.local_y_interval.hi) == (1.0, 5.0)


def test_declared_vertical_datum_is_distinct_and_shifts_z():
    payload = _real_payload()
    payload["views"]["East_view"]["scale_origin"]["world_z_m"] = 1.25
    outcome = _normalize(payload)
    datum = next(
        item
        for item in outcome.certificate.vertical_datums
        if item.input_id == "East_view"
    )
    assert datum.source == "product_declared"
    assert datum.z_origin == 1.25
    assert datum.authority == "reading_scale_origin_world_z_m"
    row = next(
        item
        for item in _elevation_observations(outcome)
        if item.source_input_id == "East_view"
        and item.source_stroke_id == "S3"
    )
    assert (row.z_interval.lo, row.z_interval.hi) == (3.65, 4.75)


def test_multi_floor_elevation_binding_is_trusted_filtered():
    payload = _real_payload()
    request = _trusted_request(payload)
    bindings = tuple(
        item.model_copy(update={"floor_ids": ("F1", "F2")})
        if isinstance(item, ElevationScoreViewBindingV1)
        and item.input_id == "East_view"
        else item
        for item in request["score_bindings"].bindings
    )
    score_bindings = request["score_bindings"].model_copy(
        update={"bindings": bindings}
    )
    outcome = _normalize(payload, bindings=score_bindings)
    applicability = _applicability(outcome)
    for component in ("elevation_opening_xy", "elevation_opening_z"):
        row = applicability[("East_view", component)]
        assert row.status == "not_applicable"
        assert row.reasons == ("elevation_floor_partition_unresolved",)
        assert row.cause_class == "trusted_input"
        assert row.denominator_disposition == "filter"
    datum = next(
        item
        for item in outcome.certificate.vertical_datums
        if item.input_id == "East_view"
    )
    assert datum.status == "not_applicable"
    assert datum.source == "multi_floor_unavailable"


def test_normalization_is_order_invariant_but_geometry_sensitive():
    payload = _real_payload()
    reversed_payload = copy.deepcopy(payload)
    reversed_payload["views"] = dict(
        reversed(tuple(reversed_payload["views"].items()))
    )
    source_hash = "f" * 64
    request = _trusted_request(payload)
    from src.agent.judge.reading_typed_adapter import normalize_reading_attempt

    first = normalize_reading_attempt(
        raw=payload,
        source_output_sha256=source_hash,
        base_manifest=request["base_view_manifest"],
        score_bindings=request["score_bindings"],
    )
    reordered = normalize_reading_attempt(
        raw=reversed_payload,
        source_output_sha256=source_hash,
        base_manifest=request["base_view_manifest"],
        score_bindings=request["score_bindings"],
    )
    changed = copy.deepcopy(payload)
    changed["views"]["East_view"]["strokes"][2]["geometry"]["x_range_m"][0] += (
        0.25
    )
    changed_outcome = normalize_reading_attempt(
        raw=changed,
        source_output_sha256=source_hash,
        base_manifest=request["base_view_manifest"],
        score_bindings=request["score_bindings"],
    )
    assert first.certificate == reordered.certificate
    assert first.certificate.content_sha256 != (
        changed_outcome.certificate.content_sha256
    )
