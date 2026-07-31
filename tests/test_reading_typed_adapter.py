"""Slices 2/3 RED locks for aggregate ReadingView normalization."""

from __future__ import annotations

import copy

from src.agent.judge.score_schema import (
    ElevationScoreViewBindingV1,
    PlanScoreViewBindingV1,
)
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


def _plan_observations(outcome, kind: str):
    return tuple(
        item
        for item in outcome.certificate.observations
        if item.kind == kind
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
        17.659999999999997,
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


def test_invalid_vertical_datum_keeps_horizontal_evidence_only():
    payload = _real_payload()
    payload["views"]["East_view"]["scale_origin"]["world_z_m"] = "not-a-number"
    outcome = _normalize(payload)
    applicability = _applicability(outcome)
    xy = applicability[("East_view", "elevation_opening_xy")]
    z = applicability[("East_view", "elevation_opening_z")]
    assert xy.status == "applicable"
    assert xy.observation_count == 4
    assert z.status == "not_applicable"
    assert z.reasons == ("elevation_vertical_datum_unsupported",)
    assert z.cause_class == "product_content"
    assert z.denominator_disposition == "retain_as_miss"
    rows = [
        item
        for item in _elevation_observations(outcome)
        if item.source_input_id == "East_view"
    ]
    assert len(rows) == 4
    assert all(
        item.z_interval is None
        and item.vertical_transform_sha256 is None
        for item in rows
    )
    assert all(
        item.input_id != "East_view"
        for item in outcome.certificate.vertical_datums
    )


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


def test_plan_frame_certificate_and_real_endpoints_are_exact():
    outcome = _normalize()
    assert len(outcome.certificate.plan_frames) == 1
    frame = outcome.certificate.plan_frames[0]
    assert frame.input_id == "1f_view"
    assert frame.floor_id == "F1"
    assert frame.source == "reading_scale_origin_v1"
    assert frame.units == "metre"
    assert frame.local_axes == "drawing_right_up"
    assert frame.affine.model_dump() == {
        "xx": 1.0,
        "xy": 0.0,
        "x0": 0.0,
        "yx": 0.0,
        "yy": 1.0,
        "y0": 0.0,
    }
    assert frame.nonzero_origin is False
    walls = {
        item.source_stroke_id: item
        for item in _plan_observations(outcome, "plan_segment")
    }
    assert len(walls) == 15
    assert (walls["S1"].world_p1.x, walls["S1"].world_p1.y) == (0.0, 20.0)
    assert (walls["S1"].world_p2.x, walls["S1"].world_p2.y) == (10.0, 20.0)
    assert all(item.topology == "unknown" for item in walls.values())


def test_plan_structured_origin_translates_but_note_never_does():
    base = _real_payload()
    translated = copy.deepcopy(base)
    translated["views"]["1f_view"]["scale_origin"]["world_x_m"] = 2.5
    translated["views"]["1f_view"]["scale_origin"]["world_y_m"] = -1.25
    prose = copy.deepcopy(base)
    prose["views"]["1f_view"]["scale_origin"]["note"] = (
        "world_x_m=999; world_y_m=-999; this prose is non-load-bearing"
    )

    base_outcome = _normalize(base)
    translated_outcome = _normalize(translated)
    prose_outcome = _normalize(prose)
    base_s1 = next(
        item
        for item in _plan_observations(base_outcome, "plan_segment")
        if item.source_stroke_id == "S1"
    )
    translated_s1 = next(
        item
        for item in _plan_observations(translated_outcome, "plan_segment")
        if item.source_stroke_id == "S1"
    )
    prose_s1 = next(
        item
        for item in _plan_observations(prose_outcome, "plan_segment")
        if item.source_stroke_id == "S1"
    )
    assert (
        translated_s1.world_p1.x - base_s1.world_p1.x,
        translated_s1.world_p1.y - base_s1.world_p1.y,
    ) == (2.5, -1.25)
    assert prose_s1.world_p1 == base_s1.world_p1
    assert (
        prose_outcome.certificate.plan_frames
        == base_outcome.certificate.plan_frames
    )
    assert (
        prose_outcome.certificate.content_sha256
        != base_outcome.certificate.content_sha256
    )


def test_missing_plan_frame_is_product_na_with_retained_denominator_rights():
    payload = _real_payload()
    del payload["views"]["1f_view"]["scale_origin"]["world_x_m"]
    outcome = _normalize(payload)
    applicability = _applicability(outcome)
    for component in ("plan_segments", "plan_openings"):
        row = applicability[("1f_view", component)]
        assert row.status == "not_applicable"
        assert row.reasons == ("plan_frame_unavailable",)
        assert row.cause_class == "product_content"
        assert row.denominator_disposition == "retain_as_miss"
        assert row.observation_count == 0
    assert not outcome.certificate.plan_frames
    assert not [
        item
        for item in outcome.certificate.observations
        if item.source_input_id == "1f_view"
    ]


def test_plan_polyline_closure_and_rect_wall_are_per_stroke():
    payload = _real_payload()
    plan = payload["views"]["1f_view"]
    plan["strokes"] = [
        {
            "id": "open-poly",
            "pen": "wall",
            "geometry": {
                "kind": "polyline",
                "points": [[0.0, 0.0], [2.0, 0.0], [2.0, 3.0]],
                "closed": False,
            },
        },
        {
            "id": "closed-poly",
            "pen": "wall",
            "geometry": {
                "kind": "polyline",
                "points": [[5.0, 5.0], [6.0, 5.0], [6.0, 6.0]],
                "closed": True,
            },
        },
        {
            "id": "rect-no-centerline",
            "pen": "wall",
            "geometry": {
                "kind": "rect",
                "x_range_m": [7.0, 8.0],
                "y_range_m": [7.0, 8.0],
            },
        },
    ]
    outcome = _normalize(payload)
    walls = _plan_observations(outcome, "plan_segment")
    assert len([item for item in walls if item.source_stroke_id == "open-poly"]) == 2
    assert len(
        [item for item in walls if item.source_stroke_id == "closed-poly"]
    ) == 3
    assert not [
        item for item in walls if item.source_stroke_id == "rect-no-centerline"
    ]
    applicability = _applicability(outcome)[("1f_view", "plan_segments")]
    assert applicability.status == "applicable"
    assert applicability.observation_count == 5
    witnesses = [
        item
        for item in outcome.certificate.unmeasurable_observation_witnesses
        if item.source_input_id == "1f_view"
    ]
    assert len(witnesses) == 1
    assert witnesses[0].source_stroke_id == "rect-no-centerline"
    assert witnesses[0].reason == "plan_wall_rect_has_no_centerline_contract"


def test_supported_empty_plan_walls_are_applicable_zero():
    payload = _real_payload()
    payload["views"]["1f_view"]["strokes"] = []
    outcome = _normalize(payload)
    applicability = _applicability(outcome)
    assert applicability[("1f_view", "plan_segments")].status == "applicable"
    assert applicability[("1f_view", "plan_segments")].observation_count == 0
    assert applicability[("1f_view", "plan_openings")].status == "applicable"
    assert applicability[("1f_view", "plan_openings")].observation_count == 0


def test_malformed_plan_wall_is_component_na_not_empty_success():
    payload = _real_payload()
    payload["views"]["1f_view"]["strokes"][0]["geometry"] = {
        "kind": "line",
        "p1": ["bad", 0.0],
        "p2": [1.0, 0.0],
    }
    outcome = _normalize(payload)
    applicability = _applicability(outcome)
    segments = applicability[("1f_view", "plan_segments")]
    assert segments.status == "not_applicable"
    assert segments.reasons == ("plan_geometry_unsupported",)
    assert segments.cause_class == "product_content"
    assert segments.denominator_disposition == "retain_as_miss"
    assert segments.observation_count == 0
    assert applicability[("1f_view", "plan_openings")].status == "applicable"
    assert any(
        item.source_stroke_id == "S1"
        and item.component == "plan_segments"
        and item.reason == "consumed_geometry_malformed"
        for item in outcome.certificate.unmeasurable_observation_witnesses
    )


def test_plan_window_line_rect_polyline_vertices_are_transformed():
    payload = _real_payload()
    payload["views"]["1f_view"]["scale_origin"]["world_x_m"] = 10.0
    payload["views"]["1f_view"]["scale_origin"]["world_y_m"] = 20.0
    payload["views"]["1f_view"]["strokes"] = [
        {
            "id": "line-window",
            "pen": "window",
            "geometry": {
                "kind": "line",
                "p1": [1.0, 2.0],
                "p2": [3.0, 4.0],
            },
        },
        {
            "id": "rect-window",
            "pen": "window",
            "geometry": {
                "kind": "rect",
                "x_range_m": [5.0, 4.0],
                "y_range_m": [7.0, 6.0],
            },
        },
        {
            "id": "poly-window",
            "pen": "window",
            "geometry": {
                "kind": "polyline",
                "points": [[8.0, 9.0], [10.0, 11.0], [12.0, 9.0]],
                "closed": True,
            },
        },
    ]
    outcome = _normalize(payload)
    rows = {
        item.source_stroke_id: item
        for item in _plan_observations(outcome, "plan_opening")
    }
    assert len(rows["line-window"].world_vertices) == 2
    assert (
        rows["line-window"].world_vertices[0].x,
        rows["line-window"].world_vertices[0].y,
    ) == (11.0, 22.0)
    assert [
        (point.x, point.y) for point in rows["rect-window"].local_vertices
    ] == [(4.0, 6.0), (5.0, 6.0), (5.0, 7.0), (4.0, 7.0)]
    assert len(rows["poly-window"].world_vertices) == 3


def test_adapter_has_no_typed_gt_import():
    from pathlib import Path

    source = Path(
        "src/agent/judge/reading_typed_adapter.py"
    ).read_text(encoding="utf-8")
    assert "src.agent.judge.gt_schema" not in source


def test_multiple_plan_inputs_for_one_floor_are_trusted_filtered():
    payload = _real_payload()
    payload["views"]["1f_view_copy"] = copy.deepcopy(
        payload["views"]["1f_view"]
    )
    request = _trusted_request(payload)
    original_entry = next(
        item
        for item in request["base_view_manifest"].required_entries()
        if item.input_id == "1f_view"
    )
    copied_entry = original_entry.model_copy(
        update={
            "input_id": "1f_view_copy",
            "expected_output_id": "1f_view_copy",
            "source_image": "case_data/1f_view_copy.png",
        }
    )
    manifest = request["base_view_manifest"].model_copy(
        update={
            "entries": sorted(
                (*request["base_view_manifest"].entries, copied_entry),
                key=lambda item: item.input_id,
            )
        }
    )
    original_binding = next(
        item
        for item in request["score_bindings"].bindings
        if isinstance(item, PlanScoreViewBindingV1)
    )
    copied_binding = original_binding.model_copy(
        update={"input_id": "1f_view_copy"}
    )
    bindings = request["score_bindings"].model_copy(
        update={
            "bindings": tuple(
                sorted(
                    (*request["score_bindings"].bindings, copied_binding),
                    key=lambda item: item.input_id,
                )
            )
        }
    )
    from src.agent.judge.reading_typed_adapter import normalize_reading_attempt

    outcome = normalize_reading_attempt(
        raw=payload,
        source_output_sha256="e" * 64,
        base_manifest=manifest,
        score_bindings=bindings,
    )
    applicability = _applicability(outcome)
    for source in ("1f_view", "1f_view_copy"):
        for component in ("plan_segments", "plan_openings"):
            row = applicability[(source, component)]
            assert row.status == "not_applicable"
            assert row.reasons == (
                "multiple_plan_views_per_floor_unsupported",
            )
            assert row.cause_class == "trusted_input"
            assert row.denominator_disposition == "filter"
    assert len(outcome.trusted_capability_dispositions) == 4
