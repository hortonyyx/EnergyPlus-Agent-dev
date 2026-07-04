from __future__ import annotations

import copy
import json
from pathlib import Path

from src.agent.judge.correction_score import score_correction_geometry
from src.agent.judge.elevation_score import score_reading_elevation_views
from src.agent.judge.gt import load_gt
from src.agent.judge.score_policy import elevation_windows_placed_criterion


_SM21_RUN = Path("case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e")


def _tiny_gt() -> dict:
    return {
        "case": "tiny",
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "zones": [{"id": "A", "role": "office", "rect_m": [0, 0, 10, 4]}],
            }
        ],
        "windows": [
            {
                "facade": "South",
                "floor": "Floor 1",
                "sill_m": 1.0,
                "head_m": 2.0,
                "openings": [
                    {"x_m": 1.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0},
                    {"x_m": 4.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0},
                    {"x_m": 7.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0},
                ],
            }
        ],
    }


def _stacked_gt() -> dict:
    gt = _tiny_gt()
    gt["floors"].append(
        {
            "name": "Floor 2",
            "z_floor": 3.0,
            "ceiling_height": 3.0,
            "zones": [{"id": "B", "role": "office", "rect_m": [0, 0, 10, 4]}],
        }
    )
    return gt


def _elevation_view(facade: str, strokes: list[dict]) -> dict:
    return {
        "image_kind": "elevation",
        "facade": {"view_facade": facade, "local_x_positive": "image_left_to_right"},
        "strokes": strokes,
        "uncaptured": [],
    }


def _win(sid: str, span: tuple[float, float], z: tuple[float, float]) -> dict:
    return {
        "id": sid,
        "pen": "window",
        "geometry": {"kind": "rect", "x_range_m": list(span), "y_range_m": list(z)},
    }


def test_sm21_per_opening_z_is_authoritative_south_f1_s7_hit():
    gt = load_gt("sm21_anchor")
    output = json.loads((_SM21_RUN / "0_reading/attempts/001/output.json").read_text())

    result = score_reading_elevation_views(output, gt)
    sf1 = result.scores["South"]["Floor 1"]
    s7 = next(m for m in sf1.matches if m.source_id == "S7")

    assert s7.status == "complete"
    assert s7.truth is not None and s7.truth.z == (1.5, 2.1)
    assert s7.deltas["sill_m"] == 0.0
    assert result.summary()["complete_total"] == 15


def test_overlap_ratio_matching_semantics_do_not_double_count_rejected_pairs():
    gt = _tiny_gt()
    output = {
        "South_view": _elevation_view(
            "South",
                [_win("hit", (1.0, 2.0), (1.0, 2.0)), _win("extra", (9.0, 9.5), (1.0, 2.0))],
            )
        }

    result = score_reading_elevation_views(output, gt)
    sf1 = result.scores["South"]["Floor 1"]
    statuses = [m.status for m in sf1.matches]

    assert statuses == ["complete", "miss", "miss"]
    assert [e.status for e in sf1.extras] == ["extra"]
    assert result.summary()["matched_total"] == 1
    assert result.summary()["complete_total"] == 1
    assert result.summary()["miss_total"] == 2
    assert result.summary()["extra_total"] == 1


def test_elevation_window_overlap_080_is_within_tol():
    gt = _tiny_gt()
    gt["windows"][0]["openings"] = [gt["windows"][0]["openings"][0]]
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("partial", (1.2, 2.2), (1.0, 2.0))])},
        gt,
    )

    match = result.scores["South"]["Floor 1"].matches[0]

    assert match.status == "within_tol"
    assert match.source_id == "partial"
    assert match.overlap_ratio == 0.8
    assert match.deltas["along_center_m"] == 0.2


def test_elevation_window_overlap_060_is_miss_plus_extra():
    gt = _tiny_gt()
    gt["windows"][0]["openings"] = [gt["windows"][0]["openings"][0]]
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("partial", (1.4, 2.4), (1.0, 2.0))])},
        gt,
    )

    score = result.scores["South"]["Floor 1"]

    assert score.matches[0].status == "miss"
    assert score.matches[0].overlap_ratio is None
    assert [e.status for e in score.extras] == ["extra"]


def test_elevation_window_overlap_097_is_complete():
    gt = _tiny_gt()
    gt["windows"][0]["openings"] = [gt["windows"][0]["openings"][0]]
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("nearly_exact", (1.03, 2.03), (1.0, 2.0))])},
        gt,
    )

    match = result.scores["South"]["Floor 1"].matches[0]

    assert match.status == "complete"
    assert match.overlap_ratio == 0.97


def test_zero_2d_overlap_wrong_floor_same_along_is_miss_plus_extra_not_drift():
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("wrong_floor", (1.0, 2.0), (4.0, 5.0))])},
        _stacked_gt(),
    )

    f1 = result.scores["South"]["Floor 1"]
    f2 = result.scores["South"]["Floor 2"]

    assert f1.matches[0].status == "miss"
    assert f1.matches[0].overlap_ratio is None
    assert [e.status for e in f2.extras] == ["extra"]
    assert result.summary()["z_drift_total"] == 0
    assert result.summary()["miss_total"] == 3
    assert result.summary()["extra_total"] == 1


def test_width_delta_is_reported_evidence_only_after_overlap_association():
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("wide", (0.75, 2.25), (1.0, 2.0))])},
        _tiny_gt(),
    )

    match = result.scores["South"]["Floor 1"].matches[0]

    assert match.status == "miss"
    assert [e.status for e in result.scores["South"]["Floor 1"].extras] == ["extra"]


def test_slightly_wide_elevation_window_is_within_tol_not_complete():
    gt = _tiny_gt()
    gt["windows"][0]["openings"] = [gt["windows"][0]["openings"][0]]
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("wide", (0.875, 2.125), (1.0, 2.0))])},
        gt,
    )

    match = result.scores["South"]["Floor 1"].matches[0]

    assert match.status == "within_tol"
    assert match.overlap_ratio == 0.8
    assert match.gt_coverage == 1.0
    assert match.product_coverage == 0.8
    assert match.deltas["width_m"] == 0.25


def test_east_stacked_windows_are_disambiguated_by_z_not_along_only():
    gt = load_gt("sm21_anchor")
    output = json.loads((_SM21_RUN / "0_reading/attempts/001/output.json").read_text())

    result = score_reading_elevation_views(output, gt)

    f1 = result.scores["East"]["Floor 1"].matches[0]
    f2 = result.scores["East"]["Floor 2"].matches[0]
    assert f1.source_id == "S4"
    assert f1.truth is not None and f1.truth.z == (1.0, 2.8)
    assert f2.source_id == "S3"
    assert f2.truth is not None and f2.truth.z == (4.0, 5.8)


def test_orientation_interval_reflection_per_facade_and_ambiguous():
    gt = {
        "case": "orient",
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {
                "name": "Floor 1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "zones": [{"id": "A", "role": "office", "rect_m": [0, 0, 10, 4]}],
            }
        ],
        "windows": [
            {
                "facade": "South",
                "floor": "Floor 1",
                "openings": [{"x_m": 2.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0}],
            },
            {
                "facade": "North",
                "floor": "Floor 1",
                "openings": [
                    {"x_m": 2.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0},
                    {"x_m": 7.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0},
                ],
            },
        ],
    }
    output = {
        "South_view": _elevation_view("South", [_win("mirrored", (7.0, 8.0), (1.0, 2.0))]),
        "North_view": _elevation_view(
            "North",
            [_win("left", (2.0, 3.0), (1.0, 2.0)), _win("right", (7.0, 8.0), (1.0, 2.0))],
        ),
    }

    result = score_reading_elevation_views(output, gt)

    assert result.orientation_by_facade["South"] == "flipped"
    south_match = result.scores["South"]["Floor 1"].matches[0]
    assert south_match.status == "complete"
    assert south_match.read is not None and south_match.read.span == (2.0, 3.0)
    assert south_match.read.original_span == (7.0, 8.0)
    assert result.orientation_by_facade["North"] == "ambiguous"


def test_zero_window_facade_floor_is_not_missing_view_no_data():
    gt = load_gt("sm21_anchor")
    output = json.loads((_SM21_RUN / "0_reading/attempts/001/output.json").read_text())

    result = score_reading_elevation_views(output, gt)
    west_f1 = result.scores["West"]["Floor 1"]
    assert west_f1.gt_count == 0
    assert west_f1.matches == []
    assert west_f1.extras == []
    assert west_f1.no_data is False

    missing = copy.deepcopy(output)
    missing.pop("West_view")
    missing_result = score_reading_elevation_views(missing, gt)
    assert missing_result.scores["West"]["Floor 1"].no_data is True
    assert missing_result.scores["West"]["Floor 2"].no_data is True


def test_unusable_legacy_line_window_is_evidence_not_fabricated_z():
    gt = _tiny_gt()
    output = {
        "South_view": _elevation_view(
            "South",
            [{"id": "legacy", "pen": "window", "geometry": {"kind": "line", "p1": [1, 0], "p2": [2, 0]}}],
        )
    }

    result = score_reading_elevation_views(output, gt)

    assert any(e["type"] == "unusable_elevation_window" for e in result.evidence)
    assert result.summary()["complete_total"] == 0
    assert all(m.read is None for m in result.scores["South"]["Floor 1"].matches)


def test_correction_uses_window_floor_identity_not_z_rebinning():
    gt = {
        "case": "stack",
        "footprint": {"W_m": 10.0, "D_m": 4.0},
        "floors": [
            {"name": "Floor 1", "z_floor": 0.0, "ceiling_height": 3.0, "zones": []},
            {"name": "Floor 2", "z_floor": 3.0, "ceiling_height": 3.0, "zones": []},
        ],
        "windows": [
            {
                "facade": "East",
                "floor": "Floor 1",
                "openings": [{"x_m": 1.0, "width_m": 1.0, "sill_m": 1.0, "head_m": 2.0}],
            },
            {
                "facade": "East",
                "floor": "Floor 2",
                "openings": [{"x_m": 1.0, "width_m": 1.0, "sill_m": 4.0, "head_m": 5.0}],
            },
        ],
    }
    geom = {
        "footprint_x": [0, 10],
        "footprint_y": [0, 4],
        "floors": [
            {"name": "Floor 1", "z_floor": 0, "ceiling_height": 3, "cells": []},
            {"name": "Floor 2", "z_floor": 3, "ceiling_height": 3, "cells": []},
        ],
        "windows": [
            {"id": "wrong_z_but_f2", "floor": "Floor 2", "facade": "East", "span": [1, 2], "z": [1, 2]}
        ],
    }

    result = score_correction_geometry(geom, gt)
    f2 = result.elevation.scores["East"]["Floor 2"].matches[0]

    assert f2.status == "miss"
    assert [e.status for e in result.elevation.scores["East"]["Floor 2"].extras] == ["extra"]
    assert result.elevation.scores["East"]["Floor 2"].extras[0].source_id == "wrong_z_but_f2"
    assert result.elevation.scores["East"]["Floor 1"].matches[0].status == "miss"


def test_floor_ground_and_roof_lines_hit_and_miss():
    gt = _tiny_gt()
    hit = score_reading_elevation_views(
        {
            "South_view": _elevation_view(
                "South",
                [{"id": "fill", "pen": "wall_fill", "geometry": {"kind": "rect", "x_range_m": [0, 10], "y_range_m": [0, 3]}}],
            )
        },
        gt,
    )
    miss = score_reading_elevation_views(
        {
            "South_view": _elevation_view(
                "South",
                [{"id": "fill", "pen": "wall_fill", "geometry": {"kind": "rect", "x_range_m": [0, 10], "y_range_m": [0, 3.5]}}],
            )
        },
        gt,
    )

    assert [line.status for line in hit.floor_lines["South"].matches] == ["complete", "complete"]
    assert hit.floor_lines["South"].extras == []
    assert [line.status for line in miss.floor_lines["South"].matches] == ["complete", "miss"]
    assert [line.product_z for line in miss.floor_lines["South"].extras] == [3.5]
    assert hit.floor_lines["North"].no_data is True
    assert hit.floor_lines["North"].no_data_reason == "missing_elevation_view"
    assert any(e["type"] == "elevation_floor_lines_no_data" for e in hit.evidence) is False


def test_present_elevation_view_without_wall_fill_is_floor_line_no_data_not_miss():
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("hit", (1.0, 2.0), (1.0, 2.0))])},
        _tiny_gt(),
    )

    floor_lines = result.floor_lines["South"]

    assert floor_lines.no_data is True
    assert floor_lines.no_data_reason == "no_product_floor_line_source"
    assert floor_lines.matches == []
    assert floor_lines.extras == []


def test_elevation_policy_criterion_counts_within_miss_extra_and_no_data():
    result = score_reading_elevation_views(
        {"South_view": _elevation_view("South", [_win("within", (1.2, 2.2), (1.0, 2.0))])},
        _tiny_gt(),
    )

    criterion = elevation_windows_placed_criterion(result)

    assert criterion["criterion"] == "elevation_windows_placed"
    assert criterion["suggested_status"] == "severe"
    assert "within_tol=1" in criterion["evidence"]
    assert "no_data_floor_facades=3" in criterion["evidence"]
