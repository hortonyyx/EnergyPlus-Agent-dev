"""M2a acceptance: 0/1 deterministic checks + real bad fixtures (build plan §2.1)."""

from __future__ import annotations

import json
from pathlib import Path

from src.agent.correction.facade import derive_facade_frame
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution import RouteAction, route_stage_failure
from src.agent.reading import ReadingView, load_reading_view
from src.validator.checks.correction import check_correction
from src.validator.checks.reading import check_reading_view
from src.validator.checks.schema import CheckLayer, CheckReport

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN = _ANCHOR / "run_2026-06-15_baseline"
_FIX = Path("tests/fixtures/validation")


def _ids(rep):
    return {r.check_id for r in rep.blocking()}


def _plan_with_room_labels(room_labels):
    return ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}},
            {"id": "S2", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 8], "p2": [10, 8]}},
        ],
        "room_labels": room_labels,
    })


def _provenance_mode(rep):
    result = next(r for r in rep.results if r.check_id == "reading.stroke_provenance_coverage")
    return result.evidence["provenance_mode"]


def _sm21_like_dim_chain():
    return [
        {"id": "D27", "text": "540", "value_m": 0.54, "chain_id": "south", "role": "segment", "order": 1, "axis": "x", "from": [0.00, 0.00], "to": [0.54, 0.00]},
        {"id": "D28", "text": "900", "value_m": 0.90, "chain_id": "south", "role": "segment", "order": 2, "axis": "x", "from": [0.54, 0.00], "to": [1.44, 0.00]},
        {"id": "D29", "text": "2000", "value_m": 2.00, "chain_id": "south", "role": "segment", "order": 3, "axis": "x", "from": [1.44, 0.00], "to": [3.44, 0.00]},
        {"id": "D30", "text": "1200", "value_m": 1.20, "chain_id": "south", "role": "segment", "order": 4, "axis": "x", "from": [3.44, 0.00], "to": [4.64, 0.00]},
    ]


def _rect_plan_with_vertical_wall(x, *, provenance=None, dimension_refs=None):
    wall = {
        "id": "S5",
        "pen": "wall",
        "geometry": {"kind": "line", "p1": [x, 0.0], "p2": [x, 3.0], "thickness_m": None},
    }
    if provenance is not None:
        wall["provenance"] = provenance
    if dimension_refs is not None:
        wall["dimension_refs"] = dimension_refs
    return ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [5, 0], "thickness_m": None}, "provenance": "seen", "confidence": "high"},
            {"id": "S2", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 3], "p2": [5, 3], "thickness_m": None}, "provenance": "seen", "confidence": "high"},
            {"id": "S3", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 3], "thickness_m": None}, "provenance": "seen", "confidence": "high"},
            {"id": "S4", "pen": "wall", "geometry": {"kind": "line", "p1": [5, 0], "p2": [5, 3], "thickness_m": None}, "provenance": "seen", "confidence": "high"},
            wall,
        ],
        "dimensions": _sm21_like_dim_chain(),
    })


# --------------------------------------------------------------------------- #
# reading linter — clean anchor passes, synthetic bad blocks
# --------------------------------------------------------------------------- #
def test_clean_anchor_reading_passes():
    for name in ("1f_view.json", "East_view.json"):
        view = load_reading_view(_RUN / "0_reading" / name)
        rep = check_reading_view(view)
        assert rep.passed, f"{name} blocking: {[r.message for r in rep.blocking()]}"


def test_reading_duplicate_stroke_id_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [5, 0]}},
            {"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 5]}},
        ],
    })
    rep = check_reading_view(v)
    assert "reading.stroke_ids_unique" in _ids(rep)


def test_reading_room_labels_empty_noop():
    v = _plan_with_room_labels([])
    rep = check_reading_view(v)
    assert not any("room_label" in r.check_id for r in rep.results)


def test_reading_room_labels_valid_when_present():
    v = _plan_with_room_labels([
        {
            "id": "RL1",
            "anchor": [2.0, 4.0],
            "role": "meeting room",
            "label_text": "Meeting Room",
            "basis": "label",
        },
        {
            "id": "RL2",
            "anchor": [8.0, 2.0],
            "role": "lobby",
            "label_text": "round table cluster",
            "basis": "furniture",
            "confidence": None,
        },
    ])
    rep = check_reading_view(v)
    assert rep.passed, [r.message for r in rep.blocking()]
    passed = {r.check_id for r in rep.results if r.status.value == "pass"}
    assert {
        "reading.room_label_ids_unique",
        "reading.room_label_roles_valid",
        "reading.room_label_basis_valid",
        "reading.room_label_anchors_in_bounds",
    } <= passed


def test_reading_room_labels_invalid_blocks():
    v = _plan_with_room_labels([
        {
            "id": "RL1",
            "anchor": [2.0, 4.0],
            "role": "office",
            "label_text": "Office",
            "basis": "label",
        },
        {
            "id": "RL1",
            "anchor": [12.0, 4.0],
            "role": "banquet",
            "label_text": "Banquet",
            "basis": "prior",
        },
    ])
    blocking = _ids(check_reading_view(v))
    assert {
        "reading.room_label_ids_unique",
        "reading.room_label_roles_valid",
        "reading.room_label_basis_valid",
    } <= blocking
    rep = check_reading_view(v)
    flagged = {r.check_id for r in rep.flagged()}
    assert "reading.room_label_anchors_in_bounds" in flagged
    anchor = next(r for r in rep.results if r.check_id == "reading.room_label_anchors_in_bounds")
    assert anchor.layer == CheckLayer.CROSS_CHECK


def test_reading_provenance_mode_full_partial_legacy():
    legacy = _plan_with_room_labels([])
    assert _provenance_mode(check_reading_view(legacy)) == "legacy"

    partial = _plan_with_room_labels([])
    partial.strokes[0].provenance = "seen"
    assert _provenance_mode(check_reading_view(partial)) == "partial"

    full = _plan_with_room_labels([])
    for stroke in full.strokes:
        stroke.provenance = "seen"
        stroke.confidence = "high"
    assert _provenance_mode(check_reading_view(full)) == "full"


def test_stroke_dimension_consistency_flags_sm21_like_wall_without_blocking():
    v = _rect_plan_with_vertical_wall(3.44)
    rep = check_reading_view(v)
    assert rep.passed, [r.message for r in rep.blocking()]
    flagged = {r.check_id for r in rep.flagged()}
    assert "reading.stroke_dimension_consistency" in flagged
    result = next(r for r in rep.results if r.check_id == "reading.stroke_dimension_consistency")
    offender = result.evidence["offenders"][0]
    assert offender["stroke_id"] == "S5"
    assert offender["axis"] == "x"
    assert offender["coord_m"] == 3.44
    assert "D29" in offender["matching_dimension_ids"]
    assert offender["joins_walls"]["both_endpoints_join"] is True
    assert result.layer == CheckLayer.CROSS_CHECK


def test_stroke_dimension_consistency_ignores_dimension_derived_clean_grid():
    v = _rect_plan_with_vertical_wall(
        3.44, provenance="dimension_derived", dimension_refs=["D27", "D28", "D29"]
    )
    rep = check_reading_view(v)
    assert rep.passed, [r.message for r in rep.blocking()]
    flagged = {r.check_id for r in rep.flagged()}
    assert "reading.stroke_dimension_consistency" not in flagged
    result = next(r for r in rep.results if r.check_id == "reading.stroke_dimension_consistency")
    assert result.status.value == "pass"


def _plan_with_healed_door(*, uncaptured=None, self_check=None):
    data = {
        "image_kind": "plan",
        "strokes": [
            {"id": "S1", "pen": "wall",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0], "thickness_m": None},
             "note": "healed door opening at x≈7.5 (door swing seen); EP wall is continuous"},
            {"id": "S2", "pen": "wall",
             "geometry": {"kind": "line", "p1": [0, 8], "p2": [10, 8], "thickness_m": None}},
        ],
    }
    if uncaptured is not None:
        data["uncaptured"] = uncaptured
    if self_check is not None:
        data["self_check"] = self_check
    return ReadingView.model_validate(data)


def _heal_result(rep):
    return next(r for r in rep.results if r.check_id == "reading.door_heal_traced")


def test_door_heal_without_trace_flags_not_blocks():
    rep = check_reading_view(_plan_with_healed_door(uncaptured=[]))
    assert rep.passed, [r.message for r in rep.blocking()]  # advisory, never blocks
    assert "reading.door_heal_traced" in {r.check_id for r in rep.flagged()}
    res = _heal_result(rep)
    assert res.layer == CheckLayer.CROSS_CHECK
    assert res.evidence["healed_stroke_ids"] == ["S1"]


def test_door_heal_with_top_level_trace_passes():
    rep = check_reading_view(_plan_with_healed_door(
        uncaptured=["healed door opening at x≈7.5 on S1"]))
    assert "reading.door_heal_traced" not in {r.check_id for r in rep.flagged()}
    assert _heal_result(rep).status.value == "pass"


def test_door_heal_trace_in_nested_self_check_tolerated():
    # carrier alignment (F2): a heal trace nested under the legacy
    # self_check.uncaptured_visual_elements is still pooled and counts.
    rep = check_reading_view(_plan_with_healed_door(
        uncaptured=[],
        self_check={"uncaptured_visual_elements": ["healed door at x≈7.5"]}))
    assert "reading.door_heal_traced" not in {r.check_id for r in rep.flagged()}
    assert _heal_result(rep).status.value == "pass"


def test_no_heal_clean_plan_door_heal_not_applicable():
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}}],
    })
    rep = check_reading_view(v)
    assert "reading.door_heal_traced" not in {r.check_id for r in rep.flagged()}
    assert _heal_result(rep).status.value == "not_applicable"


def test_reading_illegal_pen_for_plan_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall_fill", "geometry": {"kind": "rect", "x_range_m": [0, 5], "y_range_m": [0, 3]}}],
    })
    rep = check_reading_view(v)
    assert "reading.pen_kind_valid" in _ids(rep)  # wall_fill is elevation-only


def test_reading_degenerate_line_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [1, 1], "p2": [1, 1]}}],
    })
    assert "reading.nondegenerate_geometry" in _ids(check_reading_view(v))


def test_reading_collapsed_axis_rect_blocks():
    """A rect with one collapsed axis (e.g. width 0, height 3) is degenerate (Codex M3)."""
    v = ReadingView.model_validate({
        "image_kind": "elevation", "uncaptured": [],
        "facade": {"view_facade": "South"},
        "strokes": [{"id": "S1", "pen": "wall_fill",
                     "geometry": {"kind": "rect", "x_range_m": [5, 5], "y_range_m": [0, 3]}}],
    })
    assert "reading.nondegenerate_geometry" in _ids(check_reading_view(v))


def test_reading_elevation_missing_facade_blocks():
    v = ReadingView.model_validate({
        "image_kind": "elevation", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall_fill", "geometry": {"kind": "rect", "x_range_m": [0, 8], "y_range_m": [0, 3.6]}}],
    })
    assert "reading.facade_fields" in _ids(check_reading_view(v))


def test_self_consistent_wrong_dimension_passes_linter():
    """The deterministic linter only checks INTERNAL consistency: a chain that
    closes (even if every value is wrong vs the real drawing) must NOT block."""
    v = load_reading_view(_FIX / "self_consistent_wrong_dimension.json")
    rep = check_reading_view(v)
    assert rep.passed, [r.message for r in rep.blocking()]
    # chain closure passed (3+3+3+6 == 15)
    closure = next(r for r in rep.results if r.check_id == "reading.dimension_chain_closure")
    assert closure.status.value == "pass"


def test_broken_dimension_chain_flags_not_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "dimensions": [
            {"id": "D1", "value_m": 15.0, "chain_id": "w", "role": "overall", "order": 0},
            {"id": "D2", "value_m": 3.0, "chain_id": "w", "role": "segment", "order": 1},
            {"id": "D3", "value_m": 3.0, "chain_id": "w", "role": "segment", "order": 2},
        ],
    })
    rep = check_reading_view(v)
    assert rep.passed  # cross_check failure flags, never blocks
    flagged = {r.check_id for r in rep.flagged()}
    assert "reading.dimension_chain_closure" in flagged


# --------------------------------------------------------------------------- #
# correction checks — clean anchor passes; bad fixtures caught
# --------------------------------------------------------------------------- #
def test_clean_anchor_correction_passes():
    geom = CorrectedGeometry.model_validate_json(
        (_RUN / "1_correction" / "correction_geometry_snapped.json").read_text()
    )
    rep = check_correction(geom, expected_zone_total=19)
    assert rep.passed, [r.message for r in rep.blocking()]


def test_bad_2f_corridor_split_tripwire_and_audit():
    geom = CorrectedGeometry.model_validate(
        json.loads((_FIX / "bad_2f_corridor_split.json").read_text())
    )
    # testdata says 3 zones on 2f (N corridor S); the over-split has 6 cells.
    rep = check_correction(geom, expected_zone_total=3, relied_on_testdata=True)
    flagged = {r.check_id for r in rep.flagged()}
    assert "correction.zone_count_tripwire" in flagged
    # relied_on_testdata but no audit entry → audit completeness blocks.
    assert "correction.audit_completeness" in _ids(rep)


def test_wrong_facade_window_flagged():
    geom = CorrectedGeometry.model_validate(
        json.loads((_FIX / "wrong_facade_window.json").read_text())
    )
    rep = check_correction(geom)
    assert "correction.window_on_wall" in {r.check_id for r in rep.flagged()}


def test_coverage_hole_blocks():
    geom = CorrectedGeometry.model_validate({
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "A", "x": [0, 5], "y": [0, 4]},  # leaves a hole
        ]}],
    })
    rep = check_correction(geom)
    assert "correction.coverage" in _ids(rep)


def test_zstack_gap_blocks():
    geom = CorrectedGeometry.model_validate({
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [
            {"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [{"id": "A", "x": [0, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 5, "ceiling_height": 3, "cells": [{"id": "B", "x": [0, 10], "y": [0, 8]}]},
        ],
    })
    assert "correction.zstack_continuity" in _ids(check_correction(geom))


def test_audit_completeness_passes_when_sourced():
    geom = CorrectedGeometry.model_validate({
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [{"id": "A", "x": [0, 10], "y": [0, 8]}]}],
        "corrections": [{"source": "testdata", "reason": "snapped to 50mm grid"}],
    })
    rep = check_correction(geom, relied_on_testdata=True)
    assert rep.passed, [r.message for r in rep.blocking()]


# --------------------------------------------------------------------------- #
# facade image-local → world translation
# --------------------------------------------------------------------------- #
def test_facade_frames_standard_convention():
    fx, fy = [0.0, 15.0], [0.0, 8.0]
    south = derive_facade_frame(view_facade="South", footprint_x=fx, footprint_y=fy)
    assert south.world_axis == "x" and south.sign == +1 and south.base_world == 0.0
    assert south.to_world_along(0.0) == 0.0 and south.to_world_along(15.0) == 15.0

    north = derive_facade_frame(view_facade="North", footprint_x=fx, footprint_y=fy)
    assert north.world_axis == "x" and north.sign == -1 and north.base_world == 8.0
    # north image-left (local 0) maps to the east end (x=15)
    assert north.to_world_along(0.0) == 15.0 and north.to_world_along(15.0) == 0.0

    east = derive_facade_frame(view_facade="East", footprint_x=fx, footprint_y=fy)
    assert east.world_axis == "y" and east.base_world == 15.0


def test_facade_mirrored_flips_sign():
    fx, fy = [0.0, 15.0], [0.0, 8.0]
    base = derive_facade_frame(view_facade="South", footprint_x=fx, footprint_y=fy, mirrored="false")
    mir = derive_facade_frame(view_facade="South", footprint_x=fx, footprint_y=fy, mirrored="true")
    assert base.sign == -mir.sign


# --------------------------------------------------------------------------- #
# failure classification routing (§0.3)
# --------------------------------------------------------------------------- #
def test_manual_stage_failure_routes_human_redraw():
    rep = CheckReport(stage="0_reading")
    rep.add_fail("reading.stroke_ids_unique", CheckLayer.INVARIANT, "dup")
    assert route_stage_failure("0_reading", rep) == RouteAction.HUMAN_REDRAW_REQUIRED


def test_stochastic_stage_failure_routes_blind_resample():
    rep = CheckReport(stage="1_correction")
    rep.add_fail("correction.coverage", CheckLayer.INVARIANT, "hole")
    assert route_stage_failure("1_correction", rep) == RouteAction.BLIND_RESAMPLE


def test_deterministic_stage_failure_routes_fail_closed():
    rep = CheckReport(stage="2_modelling")
    rep.add_fail("kernel.zone_closed", CheckLayer.INVARIANT, "missing face")
    assert route_stage_failure("2_modelling", rep) == RouteAction.FAIL_CLOSED


def test_clean_report_routes_proceed():
    rep = CheckReport(stage="1_correction")
    rep.add_pass("correction.coverage", CheckLayer.INVARIANT)
    assert route_stage_failure("1_correction", rep) == RouteAction.PROCEED
