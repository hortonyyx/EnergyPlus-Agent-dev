"""M2a acceptance: 0/1 deterministic checks + real bad fixtures (build plan §2.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.correction.facade import derive_facade_frame
from src.agent.correction.schema import CorrectedGeometry
from src.agent.execution import RouteAction, route_stage_failure
from src.agent.judge.gt import load_gt
from src.agent.reading import ReadingView, attach_raw_metadata, load_reading_view
from src.validator.checks.correction import check_correction
from src.validator.checks.reading import check_reading_view
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus, EVIDENCE_CHECK_IDS

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor")
_RUN = _ANCHOR / "run_2026-06-15_baseline"
_FIX = Path("tests/fixtures/validation")
_RESTORE_READINGS = Path("AI_agent/logs/experiments/2026-06-30_reading_scaffold_restore_validation/readings")


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


def _provenance_result(rep):
    return next(r for r in rep.results if r.check_id == "reading.stroke_provenance_coverage")


def _jamb_result(rep):
    return next(r for r in rep.results if r.check_id == "reading.partition_on_window_jamb")


def _result(rep, check_id):
    return next(r for r in rep.results if r.check_id == check_id)


def _load_restore_reading(path: Path) -> ReadingView:
    data = json.loads(path.read_text(encoding="utf-8"))
    for dim in data.get("dimensions", []):
        for key in ("from", "to"):
            if dim.get(key) == [None, None]:
                dim.pop(key)
    return ReadingView.model_validate(data)


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


def _dimensioned_chain_view(*, overall=5.0, segments=None, axis="x"):
    if segments is None:
        segments = [2.0, 3.0]
    dims = [
        {
            "id": "D0",
            "text_verbatim": str(overall),
            "value_m": overall,
            "chain_id": "c",
            "role": "overall",
            "order": 0,
            "axis": axis,
            "from": [0, 0],
            "to": [overall if axis == "x" else 0, overall if axis == "y" else 0],
        }
    ]
    running = 0.0
    for idx, value in enumerate(segments, start=1):
        start = running
        running += value
        dims.append({
            "id": f"D{idx}",
            "text_verbatim": str(value),
            "value_m": value,
            "chain_id": "c",
            "role": "segment",
            "order": idx,
            "axis": axis,
            "from": [start if axis == "x" else 0, start if axis == "y" else 0],
            "to": [running if axis == "x" else 0, running if axis == "y" else 0],
        })
    return ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [],
        "dimensions": dims,
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
    legacy_rep = check_reading_view(legacy)
    assert _provenance_mode(legacy_rep) == "legacy"
    assert _provenance_result(legacy_rep).status.value == "fail"
    assert "reading.stroke_provenance_coverage" in {r.check_id for r in legacy_rep.flagged()}

    partial = _plan_with_room_labels([])
    partial.strokes[0].provenance = "seen"
    partial_rep = check_reading_view(partial)
    assert _provenance_mode(partial_rep) == "partial"
    assert _provenance_result(partial_rep).status.value == "fail"
    assert "reading.stroke_provenance_coverage" in {r.check_id for r in partial_rep.flagged()}

    full = _plan_with_room_labels([])
    for stroke in full.strokes:
        stroke.provenance = "seen"
        stroke.confidence = "high"
    full_rep = check_reading_view(full)
    assert _provenance_mode(full_rep) == "full"
    assert _provenance_result(full_rep).status.value == "pass"


def test_provenance_coverage_blocks_by_profile_but_legacy_migrated_is_grandfathered():
    partial = _plan_with_room_labels([])
    partial.strokes[0].provenance = "seen"

    regression = check_reading_view(partial, run_profile="regression")
    assert "reading.stroke_provenance_coverage" in {r.check_id for r in regression.blocking()}

    grandfathered = check_reading_view(
        partial,
        run_profile="regression",
        view_metadata={"legacy_migrated": True},
    )
    assert "reading.stroke_provenance_coverage" in {r.check_id for r in grandfathered.flagged()}
    assert "reading.stroke_provenance_coverage" not in {r.check_id for r in grandfathered.blocking()}


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


def test_partition_on_window_jamb_flags_advisory_only():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        # a plan run under an acceptance profile must declare its world frame
        # (7.31 plan-frame gate); unrelated to what this test asserts.
        "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [0, 0], "p2": [15, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [0, 8], "p2": [15, 8]}},
            {"id": "S3", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 8]}},
            {"id": "S4", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [15, 0], "p2": [15, 8]}},
            {"id": "W1", "pen": "window", "provenance": "seen", "geometry": {"kind": "line", "p1": [3.4, 0], "p2": [4.6, 0]}},
            {"id": "S5", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [3.39, 0], "p2": [3.39, 8]}},
        ],
        "dimensions": [
            {"id": "D0", "text_verbatim": "15.0", "value_m": 15.0, "chain_id": "south", "role": "overall", "order": 0, "axis": "x", "from": [0, 0], "to": [15, 0]},
            {"id": "D1", "text_verbatim": "3.4", "value_m": 3.4, "chain_id": "south", "role": "segment", "order": 1, "axis": "x", "from": [0, 0], "to": [3.4, 0]},
            {"id": "D2", "text_verbatim": "11.6", "value_m": 11.6, "chain_id": "south", "role": "segment", "order": 2, "axis": "x", "from": [3.4, 0], "to": [15, 0]},
        ],
    })
    rep = check_reading_view(v, run_profile="regression")
    assert rep.passed, [r.message for r in rep.blocking()]
    assert "reading.partition_on_window_jamb" not in EVIDENCE_CHECK_IDS
    assert "reading.partition_on_window_jamb" in {r.check_id for r in rep.flagged()}
    result = _jamb_result(rep)
    offender = result.evidence["offenders"][0]
    assert offender["stroke_id"] == "S5"
    assert offender["window_jambs"][0]["window_id"] == "W1"
    assert offender["matching_dimension_positions"]
    assert offender["joins_walls"]["both_endpoints_join"] is True
    assert result.layer == CheckLayer.CROSS_CHECK


def test_partition_not_on_window_jamb_is_clean():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [0, 0], "p2": [15, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [0, 8], "p2": [15, 8]}},
            {"id": "S3", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 8]}},
            {"id": "S4", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [15, 0], "p2": [15, 8]}},
            {"id": "W1", "pen": "window", "provenance": "seen", "geometry": {"kind": "line", "p1": [3.4, 0], "p2": [4.6, 0]}},
            {"id": "S5", "pen": "wall", "provenance": "seen", "geometry": {"kind": "line", "p1": [5, 0], "p2": [5, 8]}},
        ],
    })
    result = _jamb_result(check_reading_view(v, run_profile="regression"))
    assert result.status.value == "pass"


def test_partition_on_window_jamb_real_restore_reading_r2_flags_four():
    r2 = _load_restore_reading(_RESTORE_READINGS / "sonnet_r2" / "1f_view.json")

    r2_result = _jamb_result(check_reading_view(r2))
    assert r2_result.status.value == "fail"
    offenders = r2_result.evidence["offenders"]
    assert [offender["stroke_id"] for offender in offenders] == ["S9", "S11", "S12", "S14"]
    assert [round(offender["coord_m"], 2) for offender in offenders] == [3.44, 6.3, 8.7, 11.36]
    assert all(offender["matching_dimension_positions"] for offender in offenders)
    assert all(offender["joins_walls"]["both_endpoints_join"] for offender in offenders)


def test_dimension_chain_closure_groups_by_chain_id_and_axis():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "dimensions": [
            {"id": "DX0", "text_verbatim": "5", "value_m": 5, "chain_id": "same", "role": "overall", "order": 0, "axis": "x"},
            {"id": "DX1", "text_verbatim": "2", "value_m": 2, "chain_id": "same", "role": "segment", "order": 1, "axis": "x"},
            {"id": "DX2", "text_verbatim": "3", "value_m": 3, "chain_id": "same", "role": "segment", "order": 2, "axis": "x"},
            {"id": "DY0", "text_verbatim": "7", "value_m": 7, "chain_id": "same", "role": "overall", "order": 0, "axis": "y"},
            {"id": "DY1", "text_verbatim": "4", "value_m": 4, "chain_id": "same", "role": "segment", "order": 1, "axis": "y"},
            {"id": "DY2", "text_verbatim": "3", "value_m": 3, "chain_id": "same", "role": "segment", "order": 2, "axis": "y"},
        ],
    })
    closure = next(r for r in check_reading_view(v).results
                   if r.check_id == "reading.dimension_chain_closure")
    assert closure.status.value == "pass"
    assert closure.evidence["chains_checked"] == 2


def test_incomplete_dimension_chain_is_evidence_debt():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "dimensions": [
            {"id": "D1", "text_verbatim": "2", "value_m": 2, "chain_id": "c", "role": "segment", "order": 1, "axis": "x"},
        ],
    })
    rep = check_reading_view(v)
    assert "reading.dimension_chain_closure" in {r.check_id for r in rep.flagged()}


def test_non_closing_dimension_chain_is_evidence_debt():
    rep = check_reading_view(_dimensioned_chain_view(overall=6.0, segments=[2.0, 3.0]))
    assert "reading.dimension_chain_closure" in {r.check_id for r in rep.flagged()}


def test_dimension_chain_closure_flags_49mm_gap():
    rep = check_reading_view(_dimensioned_chain_view(overall=5.049, segments=[2.0, 3.0]))
    result = next(r for r in rep.results if r.check_id == "reading.dimension_chain_closure")
    assert result.status == CheckStatus.FAIL
    assert result.evidence["mismatches"][0]["overall"] == 5.049


def test_dimensioned_view_with_empty_dimensions_is_evidence_debt():
    v = ReadingView.model_validate({"image_kind": "plan", "uncaptured": [], "dimensions": []})
    rep = check_reading_view(v, dimensioned=True)
    assert "reading.dimensions_present" in {r.check_id for r in rep.flagged()}


def test_dimensioned_new_dimensions_require_p1a_fields():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "dimensions": [{"id": "D1", "text": "5", "value_m": 5}],
    })
    rep = check_reading_view(v, dimensioned=True)
    assert "reading.dimension_p1a_fields" in {r.check_id for r in rep.flagged()}


def test_dimension_derived_refs_are_required_and_resolvable():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "dimension_derived", "dimension_refs": [],
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [1, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "dimension_derived", "dimension_refs": ["missing"],
             "geometry": {"kind": "line", "p1": [0, 1], "p2": [1, 1]}},
        ],
        "dimensions": [{"id": "D1", "text_verbatim": "1", "value_m": 1}],
    })
    rep = check_reading_view(v)
    assert "reading.dimension_derived_refs" in {r.check_id for r in rep.flagged()}

    v.strokes[0].dimension_refs = ["D1"]
    v.strokes[1].dimension_refs = ["D1"]
    rep = check_reading_view(v)
    result = next(r for r in rep.results if r.check_id == "reading.dimension_derived_refs")
    assert result.status.value == "pass"


def test_run_profile_blocks_evidence_debt_only_in_regression():
    v = _dimensioned_chain_view(overall=6.0, segments=[2.0, 3.0])
    exploratory = check_reading_view(v, run_profile="exploratory")
    regression = check_reading_view(v, run_profile="regression")
    assert "reading.dimension_chain_closure" in {r.check_id for r in exploratory.flagged()}
    assert "reading.dimension_chain_closure" in {r.check_id for r in regression.blocking()}


def test_legacy_migrated_evidence_debt_never_blocks():
    # scale_origin is supplied so the only thing this total `not rep.blocking()`
    # assertion can trip on is evidence debt — the 7.31 plan-frame gate has no
    # legacy carve-out by design and is covered by its own tests below.
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [], "dimensions": [],
        "scale_origin": {"world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None},
    })
    rep = check_reading_view(
        v,
        run_profile="regression",
        view_metadata={
            "dimensioned": True,
            "raw_has_dimensions": False,
            "raw_has_uncaptured": False,
            "legacy_migrated": True,
        },
    )
    assert "reading.dimensions_present" in {r.check_id for r in rep.flagged()}
    assert not rep.blocking()


def test_raw_uncaptured_presence_distinguishes_missing_from_explicit_empty():
    missing = ReadingView.model_validate({"image_kind": "plan", "strokes": []})
    attach_raw_metadata(
        missing,
        {"raw_has_dimensions": False, "raw_has_uncaptured": False, "legacy_migrated": False},
    )
    rep = check_reading_view(missing)
    assert "reading.raw_field_presence" in {r.check_id for r in rep.flagged()}

    explicit = ReadingView.model_validate({"image_kind": "plan", "uncaptured": [], "strokes": []})
    attach_raw_metadata(
        explicit,
        {"raw_has_dimensions": False, "raw_has_uncaptured": True, "legacy_migrated": False},
    )
    result = next(r for r in check_reading_view(explicit).results
                  if r.check_id == "reading.raw_field_presence")
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


def test_reading_forbidden_topology_fields_block():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {
                "id": "S1",
                "pen": "wall",
                "parent_wall_id": "W1",
                "rooms": ["R1"],
                "geometry": {
                    "kind": "line",
                    "p1": [0, 0],
                    "p2": [10, 0],
                    "is_exterior": True,
                    "parent_window_ids": ["WIN1"],
                },
            }
        ],
    })
    rep = check_reading_view(v)
    assert "reading.no_topology_fields" in _ids(rep)
    result = next(r for r in rep.results if r.check_id == "reading.no_topology_fields")
    assert result.evidence["offenders"] == [{
        "id": "S1",
        "fields": ["is_exterior", "parent_wall_id", "parent_window_ids", "rooms"],
    }]


def test_reading_missing_geometry_kind_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall", "geometry": {"p1": [0, 0], "p2": [10, 0]}}],
    })
    rep = check_reading_view(v)
    assert "reading.pen_kind_valid" in _ids(rep)
    result = next(r for r in rep.results if r.check_id == "reading.pen_kind_valid")
    assert result.evidence["offenders"] == [{"id": "S1", "kind": None, "reason": "missing geometry kind"}]


def test_reading_degenerate_line_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan", "uncaptured": [],
        "strokes": [{"id": "S1", "pen": "wall", "geometry": {"kind": "line", "p1": [1, 1], "p2": [1, 1]}}],
    })
    assert "reading.nondegenerate_geometry" in _ids(check_reading_view(v))


def test_reading_malformed_polyline_blocks():
    v = ReadingView.model_validate({
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "geometry": {"kind": "polyline", "points": [[0, 0]]}},
            {"id": "S2", "pen": "wall", "geometry": {"kind": "polyline", "points": [[0, 0], ["bad", 1]]}},
        ],
    })
    rep = check_reading_view(v)
    assert "reading.nondegenerate_geometry" in _ids(rep)
    result = next(r for r in rep.results if r.check_id == "reading.nondegenerate_geometry")
    assert [offender["id"] for offender in result.evidence["offenders"]] == ["S1", "S2"]


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
            {"id": "D1", "value_m": 15.0, "chain_id": "w", "role": "overall", "order": 0, "axis": "x"},
            {"id": "D2", "value_m": 3.0, "chain_id": "w", "role": "segment", "order": 1, "axis": "x"},
            {"id": "D3", "value_m": 3.0, "chain_id": "w", "role": "segment", "order": 2, "axis": "x"},
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


def test_correction_residual_soft_checks_are_explicitly_deferred():
    geom = CorrectedGeometry.model_validate({
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [{"id": "A", "x": [0, 10], "y": [0, 8]}]}],
    })
    rep = check_correction(geom)
    deferred = {
        r.check_id: r for r in rep.results
        if r.check_id.startswith("correction.") and r.status == CheckStatus.NOT_APPLICABLE
    }
    for check_id in (
        "correction.facade_area_residuals",
        "correction.wwr_residuals",
        "correction.area_residuals",
        "correction.unsupported_count_by_severity",
    ):
        assert deferred[check_id].layer == CheckLayer.CROSS_CHECK
        assert deferred[check_id].message == "deferred until evidence is richer"


def _facade_window_view(facade: str, span=(3.4, 4.6)) -> ReadingView:
    return ReadingView.model_validate({
        "image_label": f"{facade} elevation",
        "image_kind": "elevation",
        "facade": {
            "view_facade": facade,
            "local_x_positive": "image_left_to_right",
            "mirrored": "false",
            "orientation_evidence": [{"source": "image_name"}],
        },
        "uncaptured": [],
        "strokes": [
            {
                "id": "W_read",
                "pen": "window",
                "provenance": "seen",
                "confidence": "high",
                "geometry": {
                    "kind": "rect",
                    "x_range_m": list(span),
                    "y_range_m": [1.0, 2.0],
                },
            }
        ],
    })


def _geom_with_window(facade="South", span=(3.4, 4.6)) -> CorrectedGeometry:
    return CorrectedGeometry.model_validate({
        "footprint_x": [0, 10],
        "footprint_y": [0, 8],
        "floors": [
            {
                "name": "F1",
                "z_floor": 0,
                "ceiling_height": 3,
                "cells": [{"id": "A", "x": [0, 10], "y": [0, 8]}],
            }
        ],
        "windows": [
            {
                "id": "W_llm",
                "floor": "F1",
                "facade": facade,
                "span": list(span),
                "z": [1.0, 2.0],
                "room": "A",
            }
        ],
    })


def test_facade_frame_cross_check_consistent_synthetic_passes():
    rep = check_correction(
        _geom_with_window("South", (3.4, 4.6)),
        reading_views=[_facade_window_view("South", (3.4, 4.6))],
    )
    result = _result(rep, "correction.facade_frame_cross_check")
    assert result.status == CheckStatus.PASS
    assert result.evidence["matches_checked"] == 1


def test_facade_frame_cross_check_displaced_llm_window_flags_with_evidence():
    rep = check_correction(
        _geom_with_window("South", (4.1, 5.3)),
        reading_views=[_facade_window_view("South", (3.4, 4.6))],
    )
    result = _result(rep, "correction.facade_frame_cross_check")
    assert result.status == CheckStatus.FAIL
    assert result.layer == CheckLayer.CROSS_CHECK
    mismatch = result.evidence["mismatches"][0]
    assert mismatch["reading_local_span"] == [3.4, 4.6]
    assert mismatch["deterministic_world_span"] == [3.4, 4.6]
    assert mismatch["llm_world_span"] == [4.1, 5.3]
    assert mismatch["abs_delta_m"] > result.evidence["tolerance_m"]
    assert result in rep.flagged()
    assert rep.passed


def test_facade_frame_cross_check_without_elevation_data_not_applicable():
    rep = check_correction(_geom_with_window("South", (3.4, 4.6)), reading_views=[])
    result = _result(rep, "correction.facade_frame_cross_check")
    assert result.status == CheckStatus.NOT_APPLICABLE
    assert result.layer == CheckLayer.CROSS_CHECK


def test_facade_frame_cross_check_west_flipped_facade_matches_frame_convention():
    # West uses the E/W flipped sign from derive_facade_frame: local [3.4, 4.6]
    # on an 8m-deep footprint maps to world-y [3.4, 4.6].
    rep = check_correction(
        _geom_with_window("West", (3.4, 4.6)),
        reading_views=[_facade_window_view("West", (3.4, 4.6))],
    )
    result = _result(rep, "correction.facade_frame_cross_check")
    assert result.status == CheckStatus.PASS
    assert result.evidence["matches_checked"] == 1


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


def test_facade_east_west_signs_match_sm21_f2_gt_window_spans():
    gt = load_gt("sm21_anchor")
    fp = gt["footprint"]
    fx, fy = [0.0, fp["W_m"]], [0.0, fp["D_m"]]
    east_opening = next(
        w for w in gt["windows"]
        if w["facade"] == "East" and w["floor"] == "Floor 2"
    )["openings"][0]
    west_opening = next(
        w for w in gt["windows"]
        if w["facade"] == "West" and w["floor"] == "Floor 2"
    )["openings"][0]

    east = derive_facade_frame(view_facade="East", footprint_x=fx, footprint_y=fy)
    east_start = east_opening["x_m"]
    east_end = east_start + east_opening["width_m"]
    assert east.sign == +1
    assert round(east.to_world_along(east_start), 6) == round(east_start, 6)
    assert round(east.to_world_along(east_end), 6) == round(east_end, 6)

    west = derive_facade_frame(view_facade="West", footprint_x=fx, footprint_y=fy)
    west_start = west_opening["x_m"]
    west_end = west_start + west_opening["width_m"]
    assert west.sign == -1
    assert round(west.to_world_along(west_start), 6) == round(west_end, 6)
    assert round(west.to_world_along(west_end), 6) == round(west_start, 6)


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


# --------------------------------------------------------------------------- #
# 7.31 plan-frame gate: a plan gate② cannot score is refused under the
# acceptance profiles and only flagged under the lenient ones.
# --------------------------------------------------------------------------- #

_PLAN_FRAME_CHECK = "reading.plan_scale_origin_usable"
_OMIT = object()
_ALL_PROFILES = ["exploratory", "dev", "golden", "regression"]
_ACCEPTANCE_PROFILES = ["golden", "regression"]
_LENIENT_PROFILES = ["exploratory", "dev"]
_USABLE_ORIGIN = {
    "world_x_m": 1.5,
    "world_y_m": -2.0,
    "world_z_m": None,
    "note": "plan-local (0,0) measured at the SW inner corner",
}


def _clean_plan_payload(scale_origin=_OMIT) -> dict:
    """A plan that passes every other reading check under EVERY run profile, so
    a refusal in these tests can only come from the plan-frame gate."""
    payload = {
        "image_kind": "plan",
        "uncaptured": [],
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 8], "p2": [10, 8]}},
        ],
        "dimensions": [],
    }
    if scale_origin is not _OMIT:
        payload["scale_origin"] = scale_origin
    return payload


def _clean_plan(scale_origin=_OMIT) -> ReadingView:
    return ReadingView.model_validate(_clean_plan_payload(scale_origin))


def test_clean_plan_fixture_is_clean_apart_from_the_plan_frame_gate():
    """Guards the three tests below against the false-lock family where the
    fixture satisfies (or breaks) the assertion for some unrelated reason."""
    for profile in _ALL_PROFILES:
        rep = check_reading_view(_clean_plan(_USABLE_ORIGIN), run_profile=profile)
        assert rep.passed, [(r.check_id, r.message) for r in rep.blocking()]
        assert not rep.flagged(), [r.check_id for r in rep.flagged()]


@pytest.mark.parametrize("run_profile", _ACCEPTANCE_PROFILES)
def test_plan_without_scale_origin_is_refused_under_acceptance_profiles(run_profile):
    rep = check_reading_view(_clean_plan(), run_profile=run_profile)
    assert not rep.passed
    # equality, not membership: the gate is the ONLY reason this run was refused
    assert _ids(rep) == {_PLAN_FRAME_CHECK}
    result = _result(rep, _PLAN_FRAME_CHECK)
    assert result.status is CheckStatus.FAIL
    assert result.evidence["unusable_fields"] == ["world_x_m", "world_y_m"]


@pytest.mark.parametrize("run_profile", _LENIENT_PROFILES)
def test_plan_without_scale_origin_only_warns_under_lenient_profiles(run_profile):
    rep = check_reading_view(_clean_plan(), run_profile=run_profile)
    assert rep.passed
    assert _PLAN_FRAME_CHECK not in _ids(rep)
    assert _PLAN_FRAME_CHECK in {r.check_id for r in rep.flagged()}
    assert _result(rep, _PLAN_FRAME_CHECK).status is CheckStatus.FAIL


@pytest.mark.parametrize("run_profile", _ALL_PROFILES)
def test_plan_with_usable_scale_origin_passes_under_every_profile(run_profile):
    rep = check_reading_view(_clean_plan(_USABLE_ORIGIN), run_profile=run_profile)
    assert rep.passed
    result = _result(rep, _PLAN_FRAME_CHECK)
    assert result.status is CheckStatus.PASS
    assert result.evidence == {"world_x_m": 1.5, "world_y_m": -2.0}


@pytest.mark.parametrize(
    "unusable_origin",
    [
        pytest.param({"world_x_m": None, "world_y_m": 0.0}, id="null_x"),
        pytest.param({"world_x_m": 0.0}, id="y_key_absent"),
        pytest.param({"world_x_m": "0.0", "world_y_m": "0.0"}, id="numeric_strings"),
        pytest.param({"world_x_m": True, "world_y_m": False}, id="booleans"),
        pytest.param({"world_x_m": float("nan"), "world_y_m": 0.0}, id="nan_x"),
        pytest.param({"world_x_m": float("inf"), "world_y_m": 0.0}, id="inf_x"),
        pytest.param({"world_x_m": [0.0], "world_y_m": [0.0]}, id="lists"),
        pytest.param(
            {"note": "plan-local (0,0) measured at the SW inner corner"},
            id="prose_note_only",
        ),
        pytest.param({}, id="empty_object"),
        pytest.param(None, id="explicit_null_object"),
    ],
)
def test_present_but_unusable_scale_origin_is_treated_exactly_like_missing(unusable_origin):
    strict = check_reading_view(_clean_plan(unusable_origin), run_profile="golden")
    assert _ids(strict) == {_PLAN_FRAME_CHECK}

    lenient = check_reading_view(_clean_plan(unusable_origin), run_profile="exploratory")
    assert lenient.passed
    assert _PLAN_FRAME_CHECK in {r.check_id for r in lenient.flagged()}


@pytest.mark.parametrize("run_profile", _ALL_PROFILES)
def test_plan_frame_gate_does_not_reach_non_plan_views(run_profile):
    elevation = ReadingView.model_validate({
        "image_kind": "elevation",
        "uncaptured": [],
        "facade": {"view_facade": "South", "local_x_positive": "image_left_to_right",
                   "mirrored": "false"},
        "strokes": [
            {"id": "S1", "pen": "outline", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}},
        ],
    })
    rep = check_reading_view(elevation, run_profile=run_profile)
    assert _result(rep, _PLAN_FRAME_CHECK).status is CheckStatus.NOT_APPLICABLE
    assert rep.passed


@pytest.mark.parametrize("run_profile", _ACCEPTANCE_PROFILES)
def test_plan_frame_gate_survives_the_aggregating_per_view_prefix(tmp_path, run_profile):
    """The production wiring (`compute_reading_report_from_vector_dir`, the merge
    checker) renames every per-view result to `<stem>.<check_id>`; the policy has
    to still recognise it or the gate silently degrades to a flag."""
    from src.agent.execution.evidence_preflight import compute_reading_report_from_vector_dir

    vector_dir = tmp_path / "0_reading"
    vector_dir.mkdir(parents=True)
    (vector_dir / "1f_view.json").write_text(
        json.dumps(_clean_plan_payload()), encoding="utf-8"
    )

    strict = compute_reading_report_from_vector_dir(vector_dir, run_profile=run_profile)
    assert _ids(strict) == {f"1f_view.{_PLAN_FRAME_CHECK}"}

    lenient = compute_reading_report_from_vector_dir(vector_dir, run_profile="exploratory")
    assert lenient.passed
    assert f"1f_view.{_PLAN_FRAME_CHECK}" in {r.check_id for r in lenient.flagged()}


@pytest.mark.parametrize("run_profile", _ACCEPTANCE_PROFILES)
def test_plan_frame_gate_reaches_the_flow_stage_gate(run_profile):
    """The acceptance-run gate① for 0_reading is `check_reading_stage`
    (scripts/tool_scripts/run_stage.py `_read_reading`). Locking the policy only
    through the per-view entry point would leave that wiring untested."""
    from src.validator.checks.view_manifest import check_reading_stage

    produced = {"1f_view": _clean_plan_payload()}
    prefixed = f"1f_view.{_PLAN_FRAME_CHECK}"

    # manifest=None also raises reading.view_manifest_coverage; assert on the
    # specific check id, never on rep.passed, so that cannot stand in for this.
    strict = check_reading_stage(None, produced, run_profile=run_profile)
    assert prefixed in _ids(strict)

    lenient = check_reading_stage(None, produced, run_profile="exploratory")
    assert prefixed not in _ids(lenient)
    assert prefixed in {r.check_id for r in lenient.flagged()}

    usable = check_reading_stage(
        None, {"1f_view": _clean_plan_payload(_USABLE_ORIGIN)}, run_profile=run_profile
    )
    assert prefixed not in _ids(usable)
    assert _result(usable, prefixed).status is CheckStatus.PASS


_OCR_BOUNDS_CHECK = "reading.ocr_anchors_in_bounds"


@pytest.mark.parametrize("run_profile", _ACCEPTANCE_PROFILES)
def test_ocr_pixel_anchor_out_of_bounds_is_advisory_under_acceptance(run_profile):
    """M-3 (r1 / F-4 ③): an OCR/annotation anchor outside the trusted image bounds
    is SURFACED — the bad-data signal O-4's canvas fix removed (it stopped letting
    OCR anchors blow up the ~3.3e8-px canvas, but that also deleted the only
    signal of a pixel anchor, masking bad data). A pixel anchor like [360,450] on
    a ~10 m plan still FAILS reading.ocr_anchors_in_bounds. Never clamped, never
    silently dropped — only surfaced.

    2026-08-04 r4 (batch C dispatch §1, user-ratified downgrade): this used to
    BLOCK under golden/regression; it no longer does, on ANY profile including
    acceptance — the median/MAD fence behind this check has known false
    negatives/positives on ordinary shapes (see
    src.validator.checks.reading._structural_metric_reference's docstring and
    the two "real shape must not be blocked" locks near the end of this file).
    It is advisory only now: the FAIL fact is still produced, still carries the
    same evidence, and still shows up in ``rep.flagged()`` — it just does not
    stop gate①. The structural fix is R1.5.

    Neuter: reintroduce a BLOCK branch for this check_id in schema.disposition
    (e.g. restore ``_OCR_ANCHOR_BLOCK_PROFILES = {"golden", "regression"}``)
    ⇒ the FAIL blocks again under acceptance ⇒ this lock reds."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["ocr_texts"] = [{"text": "3600", "anchor": [360, 450]}]  # pixel anchor
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile=run_profile)
    result = _result(rep, _OCR_BOUNDS_CHECK)
    assert result.status is CheckStatus.FAIL
    assert result.evidence["offenders"][0]["anchor"] == [360, 450]
    assert "anomalous relative to structural geometry" in result.evidence["offenders"][0]["reason"]
    assert _OCR_BOUNDS_CHECK not in _ids(rep)  # no longer BLOCKS under acceptance
    assert _OCR_BOUNDS_CHECK in {r.check_id for r in rep.flagged()}  # still surfaced
    assert rep.passed  # advisory-only: does not stop gate①


def test_ocr_pixel_anchor_out_of_bounds_only_flags_under_lenient():
    """M-3 companion: under exploratory/dev the same out-of-bounds OCR anchor only
    FLAGs (surfaced, not blocking). Since 2026-08-04 r4 this is true on every
    profile (see test_ocr_pixel_anchor_out_of_bounds_is_advisory_under_acceptance
    above for the acceptance-profile half) — kept as its own lock so the
    exploratory/dev half stays pinned independently. Neuter: make the OCR check
    INVARIANT (always block) ⇒ rep.passed flips false ⇒ this lock reds."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["ocr_texts"] = [{"text": "3600", "anchor": [360, 450]}]
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="exploratory")
    assert _result(rep, _OCR_BOUNDS_CHECK).status is CheckStatus.FAIL
    assert _OCR_BOUNDS_CHECK not in _ids(rep)  # FLAG, not BLOCK
    assert rep.passed  # flags do not block gate①


def test_ocr_in_bounds_and_margin_tolerated_anchors_pass():
    """M-3 companion: a legitimate in-bounds OCR anchor passes, and an anchor just
    outside the structural extent (within _OCR_ANCHOR_MARGIN_M) is tolerated — a
    label sitting just past a wall is legitimate, so the check does not
    false-positive on normal labels. Neuter: set the margin to 0 (drop the margin
    in the check) ⇒ the margin-tolerated anchor flips to FAIL ⇒ this lock reds."""
    from src.validator.checks.reading import _OCR_ANCHOR_MARGIN_M

    payload = _clean_plan_payload(_USABLE_ORIGIN)
    # structure spans x∈[0,10], y∈[0,8]
    payload["ocr_texts"] = [
        {"text": "room", "anchor": [5, 4]},       # well inside
        {"text": "dim", "anchor": [11.5, 4]},     # 1.5 m past xmax=10, within margin
    ]
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="regression")
    result = _result(rep, _OCR_BOUNDS_CHECK)
    assert result.status is CheckStatus.PASS
    assert _OCR_BOUNDS_CHECK not in _ids(rep)
    assert _OCR_ANCHOR_MARGIN_M >= 1.5  # the tolerated anchor relies on the margin


# --------------------------------------------------------------------------- #
# X-1 (r2 batchC dispatch §1): dimension endpoints in bounds — same shape as
# the OCR-anchor bounds check above, but for `dimensions[].from`/`.to`. N-3's
# adaptive canvas scale stopped the renderer from raising on a pixel-scale
# dimension endpoint (it downscales instead of blowing up); gate① never had a
# bounds check on dimension endpoints in the first place, so that removed the
# last machine-readable signal of this failure mode entirely. Repro payload
# matches the r1 crossreview exactly: a 10x8 m structure with one pixel-scale
# dimension endpoint from=[360,450].
# --------------------------------------------------------------------------- #
_DIM_BOUNDS_CHECK = "reading.dimension_endpoints_in_bounds"


@pytest.mark.parametrize("run_profile", _ACCEPTANCE_PROFILES)
def test_dimension_pixel_endpoint_out_of_bounds_is_advisory_under_acceptance(run_profile):
    """X-1: a dimension endpoint outside the trusted image bounds is SURFACED —
    the exact bad-data shape M-3 already catches for OCR anchors. Before this
    check existed, N-3's adaptive canvas scale silently downscaled a
    pixel-scale dimension endpoint into a legible-looking but wrong PNG instead
    of raising (the old signal), and gate① never flagged it (the new, missing
    signal). A pixel endpoint like [360,450] on a ~10x8 m plan still FAILS
    reading.dimension_endpoints_in_bounds.

    2026-08-04 r4 (batch C dispatch §1, user-ratified downgrade): this used to
    BLOCK under golden/regression; it no longer does, on ANY profile — same
    downgrade, same reasons (known false negatives/positives in the shared
    ``_structural_metric_reference`` fence), as the OCR-anchor companion above.
    Structural fix is R1.5.

    Neuter: reintroduce a BLOCK branch for this check_id in schema.disposition
    (e.g. restore ``_DIMENSION_ENDPOINT_BLOCK_PROFILES = {"golden", "regression"}``)
    ⇒ the FAIL blocks again under acceptance ⇒ this lock reds."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["dimensions"] = [{"id": "D1", "from": [360, 450], "to": [365, 450], "text": "3600"}]
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile=run_profile)
    result = _result(rep, _DIM_BOUNDS_CHECK)
    assert result.status is CheckStatus.FAIL
    assert result.evidence["offenders"][0]["point"] == [360, 450]
    assert result.evidence["offenders"][0]["field"] == "from"
    assert "anomalous relative to structural geometry" in result.evidence["offenders"][0]["reason"]
    assert _DIM_BOUNDS_CHECK not in _ids(rep)  # no longer BLOCKS under acceptance
    assert _DIM_BOUNDS_CHECK in {r.check_id for r in rep.flagged()}  # still surfaced
    assert rep.passed  # advisory-only: does not stop gate①


def test_dimension_pixel_endpoint_out_of_bounds_only_flags_under_lenient():
    """X-1 companion: under exploratory/dev the same out-of-bounds dimension
    endpoint only FLAGs (surfaced, not blocking). Since 2026-08-04 r4 this is
    true on every profile (see
    test_dimension_pixel_endpoint_out_of_bounds_is_advisory_under_acceptance
    above for the acceptance-profile half). Neuter: make the check INVARIANT
    (always block) ⇒ rep.passed flips false ⇒ this lock reds."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["dimensions"] = [{"id": "D1", "from": [360, 450], "to": [365, 450], "text": "3600"}]
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="exploratory")
    assert _result(rep, _DIM_BOUNDS_CHECK).status is CheckStatus.FAIL
    assert _DIM_BOUNDS_CHECK not in _ids(rep)  # FLAG, not BLOCK
    assert rep.passed  # flags do not block gate①


def test_dimension_endpoint_in_bounds_and_margin_tolerated_passes():
    """X-1 companion: a legitimate in-bounds dimension endpoint passes, and one
    just outside the structural extent (within _OCR_ANCHOR_MARGIN_M) is
    tolerated — a dimension tick/arrow extending slightly past a wall is
    normal. Also proves dimension endpoints do not inflate their own bounds
    (exclude_dimensions=True in _image_bounds): D1's own far endpoint sits at
    x=11.5 and is STILL judged against the wall-only extent [0,10], not
    against a bound that includes itself."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    # structure (strokes only) spans x∈[0,10], y∈[0,8]
    payload["dimensions"] = [
        {"id": "D1", "from": [5, 4], "to": [8, 4], "text": "300"},        # well inside
        {"id": "D2", "from": [11.5, 4], "to": [11.5, 6], "text": "150"},  # 1.5 m past xmax=10, within margin
    ]
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="regression")
    result = _result(rep, _DIM_BOUNDS_CHECK)
    assert result.status is CheckStatus.PASS
    assert _DIM_BOUNDS_CHECK not in _ids(rep)


# --------------------------------------------------------------------------- #
# B-1 (r3 batchC dispatch §1 BLOCKER): the r2 X-2 mechanism above (a "trusted"
# bound resolved from the case_data source image's real PIXEL size) was
# dimensionally wrong — reading coordinates are METRES, and a real case_data
# image is 790-3000 px wide/tall, so the exact repro payload [360, 450] sailed
# straight through the regression gate on every real image; the r2 tests only
# ever exercised it against a synthetic 2x2 px fixture that artificially
# guaranteed the bad value was "out of pixel bounds". See sol's 2026-08-04
# batch C r2 review §2 for the full repro and
# src.validator.checks.reading._structural_metric_reference for the
# dimensionally-safe (route (b), internal unit-anomaly, no external root)
# replacement. This section proves it at REAL case_data pixel scale
# (790-1111 px, matching sm24_anchor's own 1f_view.png dimensions) through the
# real production entry point (check_reading_stage + a real case_dir +
# manifest) — not the old 2x2 px fixture the retired mechanism depended on to
# look like it worked.
# --------------------------------------------------------------------------- #
def _write_realscale_case(root: Path, *, image_size=(790, 1111)) -> Path:
    """A minimal synthetic case at a REAL case_data pixel scale (default
    matches sm24_anchor/case_data/1f_view.png's actual 790x1111 px) — enough
    for build_view_manifest to succeed. Unlike the retired 2x2 px fixture,
    this size is exactly the shape of image that let [360, 450] sail through
    the old px-as-metre mechanism (360 < 790, 450 < 1111 — comfortably
    "in pixel bounds"), so it is the correct regression fixture for B-1: the
    NEW mechanism must still block the payload even though the image is
    plenty big enough in pixels to have swallowed it under the old one."""
    from PIL import Image

    case_data = root / "case_data"
    case_data.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", image_size, color=(200, 200, 200)).save(case_data / "1f_view.png")
    testdata = {
        "TestName": "b1-lock",
        "Floor plans": [
            {"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 1, "dimensioned": False},
        ],
    }
    (case_data / "testdata_prompt.json").write_text(json.dumps(testdata), encoding="utf-8")
    return root


def test_b1_pixel_anchor_is_still_surfaced_on_a_real_case_data_scale_image(tmp_path):
    """B-1 (r3 batchC dispatch §1 BLOCKER), r4-downgraded: the decisive
    regression for the original BLOCKER. A real (790x1111 px — sm24_anchor's
    own 1f_view.png size) case_data image is wired through the REAL production
    entry point (check_reading_stage + build_view_manifest), and the exact
    repro payload [360, 450] on a ~10x8 m plan still FAILS+FLAGS under the
    regression profile.

    Under the retired r2 mechanism this would PASS (360 < 790, 450 < 1111 are
    both comfortably inside the image's real pixel bounds) — that IS the B-1
    bug, and this is the fixture that exposes it (the retired suite's 2x2 px
    fixture could not, by construction: sol 2026-08-04 review §2).

    2026-08-04 r4: this no longer BLOCKS (the median/MAD fence has its own
    known false-negative/false-positive failure modes — see
    ``_structural_metric_reference``'s docstring — so it was downgraded to
    advisory on every profile). The point of THIS lock is narrower than
    before: the FAIL fact + evidence are still produced end-to-end through the
    real entry point, not silently dropped, even though it no longer stops
    gate①.

    Neuter: reintroduce any form of "compare a metre reading coordinate
    against the source image's real pixel width/height" (e.g. resurrect
    resolve_view_pixel_bounds and feed its result back into
    _ocr_anchors_in_bounds) ⇒ the FAIL fact itself disappears/changes shape ⇒
    this lock reds. (BLOCK-vs-FLAG for this shape is covered separately by
    test_ocr_pixel_anchor_out_of_bounds_is_advisory_under_acceptance /
    test_dimension_pixel_endpoint_out_of_bounds_is_advisory_under_acceptance.)"""
    from src.agent.execution.view_manifest import build_view_manifest
    from src.validator.checks.view_manifest import check_reading_stage

    case_dir = _write_realscale_case(tmp_path / "case")
    manifest = build_view_manifest(case_dir)

    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["ocr_texts"] = [{"text": "3600", "anchor": [360, 450]}]  # pixel anchor
    payload["dimensions"] = [{"id": "D1", "from": [360, 450], "to": [365, 450], "text": "3600"}]

    rep = check_reading_stage(manifest, {"1f_view": payload}, run_profile="regression")
    prefixed_ocr = f"1f_view.{_OCR_BOUNDS_CHECK}"
    prefixed_dim = f"1f_view.{_DIM_BOUNDS_CHECK}"
    flagged_ids = {r.check_id for r in rep.flagged()}
    assert _result(rep, prefixed_ocr).status is CheckStatus.FAIL
    assert prefixed_ocr not in _ids(rep)  # advisory, no longer BLOCKS
    assert prefixed_ocr in flagged_ids  # still surfaced
    assert _result(rep, prefixed_dim).status is CheckStatus.FAIL
    assert prefixed_dim not in _ids(rep)  # advisory, no longer BLOCKS
    assert prefixed_dim in flagged_ids  # still surfaced
    assert rep.passed  # advisory-only: nothing here stops gate①


def test_b1_legitimate_product_on_a_real_case_data_scale_image_is_not_flagged(tmp_path):
    """B-1 companion (r3 batchC dispatch §1 "另配一条合法产物不被误伤的对照锁"):
    the exact same real (790x1111 px) case_data image, but with a legitimate,
    plausible OCR anchor/dimension endpoint (well within the traced plan's own
    metric scale) — proves the new mechanism does not falsely accuse ordinary
    products just because it now ignores the image's pixel size entirely."""
    from src.agent.execution.view_manifest import build_view_manifest
    from src.validator.checks.view_manifest import check_reading_stage

    case_dir = _write_realscale_case(tmp_path / "case")
    manifest = build_view_manifest(case_dir)

    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["ocr_texts"] = [{"text": "room", "anchor": [5.0, 4.0]}]  # well inside the 10x8 m plan
    payload["dimensions"] = [{"id": "D1", "from": [1.0, 0.0], "to": [9.0, 0.0], "text": "800"}]

    rep = check_reading_stage(manifest, {"1f_view": payload}, run_profile="regression")
    prefixed_ocr = f"1f_view.{_OCR_BOUNDS_CHECK}"
    prefixed_dim = f"1f_view.{_DIM_BOUNDS_CHECK}"
    assert _result(rep, prefixed_ocr).status is CheckStatus.PASS
    assert prefixed_ocr not in _ids(rep)
    assert _result(rep, prefixed_dim).status is CheckStatus.PASS
    assert prefixed_dim not in _ids(rep)
    assert rep.passed


def test_b1_large_legitimate_building_is_not_falsely_accused():
    """B-1 companion: the fence scales with the drawing's OWN structural
    extent (median absolute deviation), not a fixed absolute threshold, so a
    genuinely large building's own annotations are never falsely flagged just
    for being numerically big. A 120x90 m structure (an order of magnitude
    bigger than the ~10x8 m plan used elsewhere in this file) with an OCR
    anchor/dimension endpoint at a plausible position near its own edge (135 m,
    95 m — just past the traced outline, the same "label past a wall" shape as
    the small-building margin tests) still passes.

    Contrast with test_b1_unit_anomaly_scales_with_structural_extent below:
    the SAME 120x90 m building rejects an anchor an order of magnitude past
    ITS OWN scale (1200, 900) — proving this is a relative, not an absolute,
    judgment."""
    payload = {
        "image_kind": "plan",
        "uncaptured": [],
        "scale_origin": _USABLE_ORIGIN,
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [120, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 90], "p2": [120, 90]}},
        ],
        "dimensions": [],
        "ocr_texts": [{"text": "room", "anchor": [135.0, 95.0]}],
    }
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="regression")
    result = _result(rep, _OCR_BOUNDS_CHECK)
    assert result.status is CheckStatus.PASS
    assert _OCR_BOUNDS_CHECK not in _ids(rep)


def test_b1_unit_anomaly_scales_with_structural_extent():
    """B-1 companion: the SAME 120x90 m building as the test above, but now
    with an anchor at (1200, 900) — exactly 10x its own structural scale, the
    same order-of-magnitude relationship [360, 450] has to the ~10-20 m
    buildings used elsewhere in this file. It is still FAILED (flagged, not
    blocked — 2026-08-04 r4 downgrade), proving the check is a RELATIVE
    (order-of-magnitude-vs-own-geometry) judgment, not an absolute metre
    threshold that would eventually false-positive on any large enough
    legitimate building — this relative property is exactly what does NOT
    hold on the closed-polyline / elongated-building shapes covered by the
    two "real shape must not be blocked" locks near the end of this file,
    which is why the check as a whole is advisory now, not why this
    particular relative-scaling property is wrong."""
    payload = {
        "image_kind": "plan",
        "uncaptured": [],
        "scale_origin": _USABLE_ORIGIN,
        "strokes": [
            {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [120, 0]}},
            {"id": "S2", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 90], "p2": [120, 90]}},
        ],
        "dimensions": [],
        "ocr_texts": [{"text": "bad", "anchor": [1200.0, 900.0]}],
    }
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="regression")
    result = _result(rep, _OCR_BOUNDS_CHECK)
    assert result.status is CheckStatus.FAIL
    assert _OCR_BOUNDS_CHECK not in _ids(rep)  # advisory (r4), not BLOCKED
    assert _OCR_BOUNDS_CHECK in {r.check_id for r in rep.flagged()}


def test_b1_resists_stray_stroke_self_inflation(tmp_path):
    """B-1 companion (carries forward the r1/r2 "stray_long_stroke" exploit,
    the one of the three original inflation tricks that could not be defeated
    just by construction — see _structural_metric_reference's docstring for
    why dropping OCR/dimension/declared-``image_bounds`` fields from the
    reference set defeats the other two by construction alone). A produced
    view adds an extra wall stroke reaching all the way to (400, 500), right
    next to the bad OCR anchor at [360, 450] — under a naive min/max bounding
    box this would widen the "structural extent" enough to swallow the bad
    anchor. The median/MAD-based reference barely moves (worked numerically in
    _structural_metric_reference's docstring: median_x stays 5, MAD_x stays 5,
    with or without the injected stroke) — the bad anchor is still FAILED
    (flagged, not blocked — 2026-08-04 r4 downgrade; see that function's
    docstring for the separate, real false-positive shapes that motivated the
    downgrade — this specific resistance property is unaffected by it).

    Neuter: revert _structural_metric_reference to raw min/max over the same
    point set (drop the median/MAD statistics) ⇒ this lock reds — the injected
    stroke's own endpoint widens the naive bounds enough for [360, 450] to
    pass (status flips to PASS, not just BLOCK-vs-FLAG)."""
    from src.agent.execution.view_manifest import build_view_manifest
    from src.validator.checks.view_manifest import check_reading_stage

    case_dir = _write_realscale_case(tmp_path / "case")
    manifest = build_view_manifest(case_dir)

    base = _clean_plan_payload(_USABLE_ORIGIN)
    payload = {
        **base,
        "ocr_texts": [{"text": "3600", "anchor": [360, 450]}],
        "strokes": base["strokes"] + [
            {"id": "S3", "pen": "wall", "provenance": "seen", "confidence": "high",
             "geometry": {"kind": "line", "p1": [0, 0], "p2": [400, 500]}},
        ],
    }
    rep = check_reading_stage(manifest, {"1f_view": payload}, run_profile="regression")
    prefixed = f"1f_view.{_OCR_BOUNDS_CHECK}"
    result = _result(rep, prefixed)
    assert result.status is CheckStatus.FAIL
    assert prefixed not in _ids(rep)  # advisory (r4), not BLOCKED
    assert prefixed in {r.check_id for r in rep.flagged()}  # despite the injected stroke, still surfaced


def test_b1_declared_image_bounds_and_dimension_endpoints_cannot_inflate_the_reference(tmp_path):
    """B-1 companion (carries forward the other two r1/r2 inflation tricks —
    a declared `image_bounds` extra field, and an extra pixel-scale dimension
    endpoint — both of which are now defeated by construction:
    _structural_metric_reference never reads either field, only strokes).
    2026-08-04 r4: the FAIL is still produced (this construction-level
    resistance is unaffected), it just no longer blocks (advisory only)."""
    from src.agent.execution.view_manifest import build_view_manifest
    from src.validator.checks.view_manifest import check_reading_stage

    case_dir = _write_realscale_case(tmp_path / "case")
    manifest = build_view_manifest(case_dir)

    base = _clean_plan_payload(_USABLE_ORIGIN)
    bad_anchor = {"text": "3600", "anchor": [360, 450]}
    tricks = {
        "extra_pixel_dimension_endpoint": {
            **base,
            "ocr_texts": [bad_anchor],
            "dimensions": [{"id": "D1", "from": [360, 450], "to": [365, 450], "text": "3600"}],
        },
        "declared_image_bounds_extra_field": {
            **base,
            "ocr_texts": [bad_anchor],
            "image_bounds": {"x": [0, 1000], "y": [0, 1000]},
        },
    }
    prefixed = f"1f_view.{_OCR_BOUNDS_CHECK}"
    for label, payload in tricks.items():
        rep = check_reading_stage(manifest, {"1f_view": payload}, run_profile="regression")
        result = _result(rep, prefixed)
        assert result.status is CheckStatus.FAIL, label
        assert prefixed not in _ids(rep), label  # advisory (r4), not BLOCKED
        assert prefixed in {r.check_id for r in rep.flagged()}, label


def test_b1_m2_undecodable_source_image_no_longer_degrades_the_check(tmp_path):
    """M-2 (r3 batchC dispatch §2 MAJOR), closed as a structural consequence of
    the B-1 fix: the retired mechanism resolved trusted PIXEL bounds by
    PIL-decoding the case_data source image per stem, and silently `continue`d
    (dropping that stem's trusted bounds, falling back to the weaker
    product-derivable bounds) when the bytes were not a valid image — even
    though the manifest/hash were perfectly valid (sol 2026-08-04 review
    §2.2, row 3: coverage still PASS, blocking=[], report passed=True).

    The B-1 replacement never opens the image file at all — the reference is
    computed purely from the view's own stroke geometry — so there is no more
    image-decode step on this path to silently fail. This test proves it
    through the real production entry point: the case_data "image" on disk is
    genuinely corrupt (not decodable by PIL), build_view_manifest still
    succeeds (hash/manifest identity does not require decoding), and the bad
    OCR anchor is STILL surfaced (FAIL + flagged) exactly as if the image had
    been valid. 2026-08-04 r4: it no longer BLOCKS (advisory-only downgrade,
    unrelated to M-2) — this lock's own point (the FAIL fact does not
    silently degrade when the image is corrupt) is unaffected by that.

    Neuter: reintroduce any image-decode step into the OCR-anchor/dimension-
    endpoint bounds checks (e.g. resurrect resolve_view_pixel_bounds and make
    a decode failure silently drop to a weaker fallback) ⇒ this lock stays
    green today but would start reproducing M-2's silent-degrade shape again —
    the intended regression signal is the companion real-image lock above
    (test_b1_pixel_anchor_is_still_surfaced_on_a_real_case_data_scale_image)
    flipping if that resurrected mechanism ever became the primary gate
    again; this test pins the specific "image is corrupt" input shape so a
    future patch cannot reintroduce a decode-dependent fallback without this
    test forcing the author to look at it."""
    from src.agent.execution.view_manifest import build_view_manifest
    from src.validator.checks.view_manifest import check_reading_stage

    case_dir = tmp_path / "case"
    case_data = case_dir / "case_data"
    case_data.mkdir(parents=True)
    # Genuinely undecodable bytes at a .png path — hashes fine, PIL cannot open it.
    (case_data / "1f_view.png").write_bytes(b"not a real png file, just garbage bytes")
    testdata = {
        "TestName": "m2-lock",
        "Floor plans": [
            {"floor": 1, "path": "case_data/1f_view.png", "thermal_zones": 1, "dimensioned": False},
        ],
    }
    (case_data / "testdata_prompt.json").write_text(json.dumps(testdata), encoding="utf-8")

    manifest = build_view_manifest(case_dir)  # hashing raw bytes does not require decoding them

    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["ocr_texts"] = [{"text": "3600", "anchor": [360, 450]}]
    rep = check_reading_stage(manifest, {"1f_view": payload}, run_profile="regression")
    prefixed = f"1f_view.{_OCR_BOUNDS_CHECK}"
    result = _result(rep, prefixed)
    assert result.status is CheckStatus.FAIL
    assert prefixed not in _ids(rep)  # advisory (r4), not BLOCKED
    assert prefixed in {r.check_id for r in rep.flagged()}  # still surfaced — coverage also still passes (identity is fine)
    coverage_id = "reading.view_manifest_coverage"
    assert _result(rep, coverage_id).status is CheckStatus.PASS


# --------------------------------------------------------------------------- #
# 2026-08-04 r4 (batch C dispatch §1, user-ratified downgrade): the two real
# shapes that forced the downgrade in the first place. Both are ordinary,
# legitimate architectural drawings — not adversarial/inflation fixtures like
# the B-1 tricks above — and both trip the median/MAD fence in
# _structural_metric_reference because a closed polyline that repeats its
# start point as its last point pulls the median toward that repeated corner
# instead of the shape's centre. This is exactly the false-positive shape
# sol's independent review + the orchestrator's own live testing found; these
# two locks pin "these legitimate artifacts must never be BLOCKED" so nobody
# re-tightens this heuristic back into a hard gate without seeing this file
# first. (They do NOT assert the FAIL disappears — the underlying mis-
# judgment is real and documented; only that it stays advisory.)
# --------------------------------------------------------------------------- #
def test_b1_r4_closed_polyline_10x8_room_with_legitimate_annotation_is_not_blocked():
    """r4 real-shape lock #1: an ordinary 10x8 m room traced as a single closed
    polyline stroke ((0,0)->(10,0)->(10,8)->(0,8)->back to (0,0), the natural
    encoding of "trace the room outline and close it") with one perfectly
    legitimate OCR annotation at (9, 4) — well inside the room, nowhere near
    either wall. The repeated (0,0) start/end point collapses median_x to 0
    (not 5) and MAD_x to 0, fencing the annotation OUTSIDE the tolerated band
    even though it sits squarely inside the room the check is supposed to be
    judging against — the false positive that motivated the r4 downgrade.

    This is the load-bearing assertion of this lock: the legitimate artifact
    is NOT blocked. (Its FAIL status is asserted too, to pin the exact
    mechanism being locked against regressing silently — if a future change
    makes it PASS instead, that's a different, welcome fix and this assertion
    would need loosening then, not before.)

    Neuter: reintroduce a BLOCK branch for reading.ocr_anchors_in_bounds under
    "regression" in schema.disposition ⇒ this exact legitimate 10x8 m room
    payload starts blocking gate① ⇒ this lock reds. That is precisely the
    regression this lock exists to catch."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["strokes"] = [
        {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
         "geometry": {"kind": "polyline",
                      "points": [[0, 0], [10, 0], [10, 8], [0, 8], [0, 0]]}},
    ]
    payload["ocr_texts"] = [{"text": "room", "anchor": [9.0, 4.0]}]  # inside the room
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="regression")
    result = _result(rep, _OCR_BOUNDS_CHECK)
    assert result.status is CheckStatus.FAIL  # the known false positive, pinned
    assert _OCR_BOUNDS_CHECK not in _ids(rep)  # ⭐ must never BLOCK
    assert _OCR_BOUNDS_CHECK in {r.check_id for r in rep.flagged()}  # still surfaced
    assert rep.passed  # ⭐ this legitimate artifact is not refused


def test_b1_r4_elongated_60x4_building_with_legitimate_annotation_is_not_blocked():
    """r4 real-shape lock #2: a 60x4 m elongated building (e.g. a long narrow
    corridor block), also traced as a single closed polyline with a repeated
    start/end point, with one legitimate OCR annotation at (55, 2) — well
    inside the building, near its far (long) end. Same median-collapse
    mechanism as the 10x8 m room above (median_x collapses to 0 instead of
    30), same false positive, same r4 downgrade rationale.

    Neuter: reintroduce a BLOCK branch for reading.ocr_anchors_in_bounds under
    "regression" in schema.disposition ⇒ this exact legitimate 60x4 m building
    payload starts blocking gate① ⇒ this lock reds."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["strokes"] = [
        {"id": "S1", "pen": "wall", "provenance": "seen", "confidence": "high",
         "geometry": {"kind": "polyline",
                      "points": [[0, 0], [60, 0], [60, 4], [0, 4], [0, 0]]}},
    ]
    payload["ocr_texts"] = [{"text": "room", "anchor": [55.0, 2.0]}]  # inside the building
    view = ReadingView.model_validate(payload)
    rep = check_reading_view(view, run_profile="regression")
    result = _result(rep, _OCR_BOUNDS_CHECK)
    assert result.status is CheckStatus.FAIL  # the known false positive, pinned
    assert _OCR_BOUNDS_CHECK not in _ids(rep)  # ⭐ must never BLOCK
    assert _OCR_BOUNDS_CHECK in {r.check_id for r in rep.flagged()}  # still surfaced
    assert rep.passed  # ⭐ this legitimate artifact is not refused


# --- F-33: a malformed dimension endpoint must be an offender, never a crash ---
#
# Found by run_2026-08-15_reading_restart_A1, the first real reading run in
# weeks: the reader wrote North_view D6 as {"from": [8.7, 0.0], "to": [11.36]}
# — one component short. ReadingView loads it fine (the schema types from/to as
# plain list[float]), then _dimensions_wellformed did `d.to[1]` and raised
# IndexError, taking down the whole merge. Same family as F-6 (judge crashed
# instead of reporting "unsupported") and violates "a gate may say fail, it may
# not die".

_AXIS_ENDPOINT_CHECK = "reading.axis_endpoint_consistent"

# The exact shape the reader emitted, kept verbatim so this lock stays tied to
# the real artifact rather than to a hand-invented one.
_A1_MALFORMED_DIMENSION = {
    "id": "D6", "text_verbatim": "2660", "value_m": 2.66,
    "from": [8.7, 0.0], "to": [11.36], "axis": "x",
}


def test_malformed_dimension_endpoint_premise_would_have_crashed_the_old_gate():
    """Self-proving premise (a regression case must show the old judgement
    really fails on this fixture): the pre-fix body is exactly the two lines
    below, and on this payload they raise IndexError. Without this, the lock
    underneath could be green for a reason unrelated to the fix."""
    d = _A1_MALFORMED_DIMENSION
    with pytest.raises(IndexError):
        _ = abs(d["to"][1] - d["from"][1])  # the pre-fix line 789


def test_malformed_dimension_endpoint_is_reported_not_raised():
    """⭐ The lock: gate① reports the malformed endpoint as an offender of
    reading.axis_endpoint_consistent and completes the report.

    Neuter: drop the `len(...) >= 2` guard in _dimensions_wellformed ⇒ this
    test raises IndexError instead of asserting ⇒ red."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["dimensions"] = [_A1_MALFORMED_DIMENSION]

    rep = check_reading_view(ReadingView.model_validate(payload))  # must not raise

    result = _result(rep, _AXIS_ENDPOINT_CHECK)
    assert result.status is CheckStatus.FAIL
    offenders = result.evidence["offenders"]
    assert [o["id"] for o in offenders] == ["D6"]
    assert offenders[0]["reason"] == "malformed endpoints"


def test_wellformed_dimension_endpoints_still_pass():
    """The guard must not turn healthy dimensions into offenders — an
    axis-consistent, two-component dimension stays a pass."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["dimensions"] = [
        {"id": "D1", "text_verbatim": "15000", "value_m": 15.0,
         "from": [0.0, 0.0], "to": [15.0, 0.0], "axis": "x"},
    ]
    rep = check_reading_view(ReadingView.model_validate(payload))
    assert _result(rep, _AXIS_ENDPOINT_CHECK).status is CheckStatus.PASS


def test_absent_dimension_endpoints_stay_skipped():
    """Behaviour preservation: endpoints that are ABSENT were skipped before
    the fix and must still be skipped — the guard targets present-but-malformed
    values only, so old artifacts keep their verdicts."""
    payload = _clean_plan_payload(_USABLE_ORIGIN)
    payload["dimensions"] = [
        {"id": "D1", "text_verbatim": "15000", "value_m": 15.0, "axis": "x"},
    ]
    rep = check_reading_view(ReadingView.model_validate(payload))
    assert _result(rep, _AXIS_ENDPOINT_CHECK).status is CheckStatus.PASS


# ---------------------------------------------------------------------------
# 2026-08-18 · `reading.calibration_axes_agree` — the machine consumer for the
# cross-axis calibration signal.
#
# Motivating measurement (`run_2026-08-17_707mode_H2`, pilot r2): the tool
# reported disagreement=true / 37.18% deviation / confidence=low / an explicit
# "do not trust the blend" warning, and the reader used the blend anyway AND
# told its reviewer the calibration was consistent. Before this check, that
# outcome was invisible to every automated consumer in the repo.
#
# ⛔ Locks come in pairs: "the bad shape trips it" is worthless without "the
# clean shape does not", and both are worthless without "absence is not a pass".
# ---------------------------------------------------------------------------

_CAL_CHECK = "reading.calibration_axes_agree"


def _cal_sidecar(cv_root: Path, name: str, *, disagree: bool, on_metric_only: bool = False) -> Path:
    """Write one px_m_calibrator sidecar shaped like the real tool's output."""
    result = {
        "candidate_id": f"1f_view:px_m_calibrator:{name}:scale",
        "axis_px_per_m": {"x": 60.0666, "y": 87.5} if disagree else {"x": 60.0, "y": 60.0},
        "axis_relative_deviation": 0.3718 if disagree else None,
        "axis_relative_deviation_limit": 0.003,
        "metric": {"confidence": "low" if disagree else "high"},
    }
    flag_home = result["metric"] if on_metric_only else result
    flag_home["axis_calibration_disagreement"] = disagree
    target = cv_root / "cv_evidence" / "1f_view" / f"{name}_px_m_calibrator.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"tool": "px_m_calibrator", "results": [result]}), encoding="utf-8")
    return target


def _cal_report(profile: str = "regression") -> CheckReport:
    return CheckReport(stage="0_reading", capability_profile="orthogonal_polygon", run_profile=profile)


def test_calibration_axes_check_fails_when_the_two_axes_disagree(tmp_path: Path):
    from src.validator.checks.reading import check_calibration_evidence

    _cal_sidecar(tmp_path, "002", disagree=True)
    rep = check_calibration_evidence(_cal_report(), tmp_path)
    result = _result(rep, _CAL_CHECK)
    assert result.status is CheckStatus.FAIL, result.message
    assert result.evidence["offenders"][0]["axis_relative_deviation"] == 0.3718


def test_calibration_axes_check_reads_the_flag_from_metric_too(tmp_path: Path):
    """The tool writes the flag on the result AND mirrors it into `metric`.

    A checker that trusted only one spelling would go silent the day the other
    is the surviving one — and silence here is indistinguishable from agreement,
    which is the exact failure this whole check exists to end.
    """
    from src.validator.checks.reading import check_calibration_evidence

    _cal_sidecar(tmp_path, "002", disagree=True, on_metric_only=True)
    rep = check_calibration_evidence(_cal_report(), tmp_path)
    assert _result(rep, _CAL_CHECK).status is CheckStatus.FAIL


def test_calibration_axes_check_passes_when_the_axes_agree(tmp_path: Path):
    from src.validator.checks.reading import check_calibration_evidence

    _cal_sidecar(tmp_path, "001", disagree=False)
    rep = check_calibration_evidence(_cal_report(), tmp_path)
    assert _result(rep, _CAL_CHECK).status is CheckStatus.PASS


@pytest.mark.parametrize("shape", ["no_directory", "empty_directory"])
def test_calibration_axes_check_never_reports_absence_as_agreement(tmp_path: Path, shape: str):
    """⭐ Absence is NOT a pass.

    "No calibration evidence" conflates "the reader never calibrated" with "the
    directory moved" — and a PASS here would launder both into a clean bill of
    health, which is this repo's recurring `absence conflates causes` trap.
    """
    from src.validator.checks.reading import check_calibration_evidence

    root = tmp_path / "cv"
    if shape == "empty_directory":
        (root / "cv_evidence").mkdir(parents=True)
    rep = check_calibration_evidence(_cal_report(), root)
    result = _result(rep, _CAL_CHECK)
    assert result.status is CheckStatus.NOT_APPLICABLE
    assert result.status is not CheckStatus.PASS
    assert "not" in result.message.lower()


def test_calibration_axes_check_errors_rather_than_passes_on_unreadable_evidence(tmp_path: Path):
    """Fail-closed: unparseable evidence means we do not KNOW the ruler agrees."""
    from src.validator.checks.reading import check_calibration_evidence

    target = tmp_path / "cv_evidence" / "1f_view" / "003_px_m_calibrator.json"
    target.parent.mkdir(parents=True)
    target.write_text("{not json", encoding="utf-8")
    rep = check_calibration_evidence(_cal_report(), tmp_path)
    assert _result(rep, _CAL_CHECK).status is CheckStatus.ERROR


@pytest.mark.parametrize(
    "profile, expected_blocking",
    [("exploratory", 0), ("dev", 0), ("golden", 1), ("regression", 1)],
)
def test_calibration_axes_disagreement_blocks_only_on_acceptance_profiles(
    tmp_path: Path, profile: str, expected_blocking: int
):
    """The profile split is the whole reason diagnostic draws stay runnable.

    Both halves are load-bearing: if it blocked everywhere, exploratory draws
    could not merge and the check would be removed; if it blocked nowhere, an
    acceptance run would still accept geometry built on a ruler that disagrees
    with itself — which is the status quo this replaces.
    """
    from src.validator.checks.reading import check_calibration_evidence

    _cal_sidecar(tmp_path, "002", disagree=True)
    rep = check_calibration_evidence(_cal_report(profile), tmp_path)
    assert len(rep.blocking()) == expected_blocking


def test_calibration_axes_evidence_carries_no_run_specific_absolute_path(tmp_path: Path):
    """⭐ Regression lock for a defect this check introduced and L-11 caught.

    Check FACTS must be comparable across two runs of the same product that
    differ only in policy — L-11 asserts the fact rows are byte-identical. The
    first version of this checker put `str(root)` (an absolute per-run staging
    tmpdir) into evidence, so two identical products produced different rows and
    L-11 went red. Keep the label relative.
    """
    from src.validator.checks.reading import check_calibration_evidence

    rows = []
    for run in ("staging_reg", "staging_exp"):
        root = tmp_path / run / "out" / "cv"
        root.mkdir(parents=True)
        _cal_sidecar(root, "001", disagree=False)
        rep = check_calibration_evidence(_cal_report(), root)
        rows.append(json.dumps(_result(rep, _CAL_CHECK).evidence, sort_keys=True))
    assert rows[0] == rows[1], "evidence differs between two runs of the same product"
    assert str(tmp_path) not in rows[0], "an absolute path leaked into check evidence"


def test_calibration_axes_evidence_has_no_absolute_path_when_directory_is_missing(tmp_path: Path):
    """Same property on the absence branch — that is the one L-11 actually hit."""
    from src.validator.checks.reading import check_calibration_evidence

    rows = []
    for run in ("staging_reg", "staging_exp"):
        rep = check_calibration_evidence(_cal_report(), tmp_path / run / "out" / "cv")
        rows.append(json.dumps(_result(rep, _CAL_CHECK).evidence, sort_keys=True))
    assert rows[0] == rows[1]
    assert str(tmp_path) not in rows[0]
