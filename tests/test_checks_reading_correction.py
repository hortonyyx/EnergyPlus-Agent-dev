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
_FIX = Path("tests/fixtures/validation")


def _ids(rep):
    return {r.check_id for r in rep.blocking()}


# --------------------------------------------------------------------------- #
# reading linter — clean anchor passes, synthetic bad blocks
# --------------------------------------------------------------------------- #
def test_clean_anchor_reading_passes():
    for name in ("1f_view.json", "East_view.json"):
        view = load_reading_view(_ANCHOR / "0_reading" / name)
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
        (_ANCHOR / "1_correction" / "correction_geometry_snapped.json").read_text()
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
