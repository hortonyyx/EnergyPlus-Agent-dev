"""M2a acceptance: 0/1 deterministic checks + real bad fixtures (build plan §2.1)."""

from __future__ import annotations

import json
from pathlib import Path

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
_RESTORE_READINGS = Path("AI_agent/logs/review/2026-06-30_reading_scaffold_restore_validation/readings")


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
    v = ReadingView.model_validate({"image_kind": "plan", "uncaptured": [], "dimensions": []})
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
