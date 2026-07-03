"""Tests for the coordinate-level reading↔gt scorer (judge-side metric)."""
from __future__ import annotations

from pathlib import Path

from src.agent.judge.gt import load_gt
from src.agent.judge import reading_score as rs

# Synthetic gt: 15×8 footprint, one floor, 3 south + corridor + 3 north
# => interior vertical dividers at x=5,10 ; horizontal corridor walls at y=3,5.
_GT = {
    "footprint": {"W_m": 15.0, "D_m": 8.0},
    "floors": [
        {
            "name": "Floor 1",
            "zones": [
                {"rect_m": [0, 0, 5, 3]}, {"rect_m": [5, 0, 10, 3]}, {"rect_m": [10, 0, 15, 3]},
                {"rect_m": [0, 3, 15, 5]},
                {"rect_m": [0, 5, 5, 8]}, {"rect_m": [5, 5, 10, 8]}, {"rect_m": [10, 5, 15, 8]},
            ],
        }
    ],
    "windows": [
        {"facade": "North", "floor": "Floor 1",
         "openings": [{"x_m": 1.24, "width_m": 2.4}, {"x_m": 6.3, "width_m": 2.4}]},
        {"facade": "East", "floor": "Floor 1", "openings": [{"x_m": 3.4, "width_m": 1.2}]},
    ],
}


def _wall(pen, p1, p2):
    return {"pen": pen, "geometry": {"p1": p1, "p2": p2}}


def test_gt_wall_derivation():
    vx, hy = rs.derive_gt_walls(_GT["floors"][0]["zones"], 15.0, 8.0)
    assert vx == [5.0, 10.0]
    assert hy == [3.0, 5.0]


def test_gt_window_derivation():
    win = rs.derive_gt_windows(_GT, "Floor 1")
    assert win["N"] == [(1.24, 3.64), (6.3, 8.7)]
    assert win["E"] == [(3.4, 4.6)]
    assert win["S"] == [] and win["W"] == []


def test_perfect_reading_all_hit():
    reading = {"strokes": [
        # perimeter (boundary — ignored as interior walls)
        _wall("wall", [0, 0], [15, 0]), _wall("wall", [0, 8], [15, 8]),
        _wall("wall", [0, 0], [0, 8]), _wall("wall", [15, 0], [15, 8]),
        # interior dividers (split by corridor => two segments each, deduped)
        _wall("wall", [5, 0], [5, 3]), _wall("wall", [5, 5], [5, 8]),
        _wall("wall", [10, 0], [10, 3]), _wall("wall", [10, 5], [10, 8]),
        _wall("wall", [0, 3], [15, 3]), _wall("wall", [0, 5], [15, 5]),
        # windows
        _wall("window", [1.24, 8], [3.64, 8]), _wall("window", [6.3, 8], [8.7, 8]),
        _wall("window", [15, 3.4], [15, 4.6]),
    ]}
    sc = rs.score_floor(reading, _GT, "Floor 1")
    assert sc.wall_hits() == (4, 4)        # 2 vert + 2 horiz
    assert sc.window_hits() == (3, 3)
    assert sc.max_wall_offset() == 0.0
    assert not sc.extra_vwalls and not sc.extra_hwalls
    assert sc.boundary_hits() == (4, 4)
    assert sc.boundary is not None
    assert sc.boundary["N"].delta == 0.0


def test_boundary_hit_records_delta():
    reading = {"strokes": [
        _wall("wall", [0.12, 0], [0.12, 8]),
        _wall("wall", [14.88, 0], [14.88, 8]),
        _wall("wall", [0, 0.18], [15, 0.18]),
        _wall("wall", [0, 7.76], [15, 7.76]),
    ]}

    sc = rs.score_floor(reading, _GT, "Floor 1")

    assert sc.boundary_hits() == (4, 4)
    assert sc.boundary is not None
    assert sc.boundary["W"].delta == 0.12
    assert sc.boundary["E"].delta == -0.12
    assert sc.boundary["S"].delta == 0.18
    assert sc.boundary["N"].delta == -0.24


def test_missing_boundary_on_nonempty_reading_is_miss():
    reading = {"strokes": [
        _wall("wall", [5, 0], [5, 3]),
        _wall("window", [1.24, 8], [3.64, 8]),
    ]}

    sc = rs.score_floor(reading, _GT, "Floor 1")

    assert sc.boundary_hits() == (0, 4)
    assert sc.boundary is not None
    assert all(match.read is None for match in sc.boundary.values())


def test_empty_reading_boundary_is_no_data():
    sc = rs.score_floor({"strokes": []}, _GT, "Floor 1")

    assert sc.boundary is None
    assert sc.boundary_hits() == (0, 0)


def test_rect_geometry_scores_like_equivalent_line():
    # A window/wall may be emitted as a `rect` (x_range_m/y_range_m) instead of a
    # `line` (p1/p2); both are legal reading-schema shapes and must score the same.
    rect_reading = {"strokes": [
        {"pen": "wall", "geometry": {"kind": "rect", "x_range_m": [5, 5], "y_range_m": [0, 3]}},
        {"pen": "wall", "geometry": {"kind": "rect", "x_range_m": [10, 10], "y_range_m": [0, 8]}},
        {"pen": "wall", "geometry": {"kind": "rect", "x_range_m": [0, 15], "y_range_m": [3, 3]}},
        {"pen": "wall", "geometry": {"kind": "rect", "x_range_m": [0, 15], "y_range_m": [5, 5]}},
        {"pen": "window", "geometry": {"kind": "rect", "x_range_m": [1.24, 3.64], "y_range_m": [7.8, 8.0]}},
        {"pen": "window", "geometry": {"kind": "rect", "x_range_m": [6.3, 8.7], "y_range_m": [7.8, 8.0]}},
        {"pen": "window", "geometry": {"kind": "rect", "x_range_m": [14.9, 15.0], "y_range_m": [3.4, 4.6]}},
    ]}
    sc = rs.score_floor(rect_reading, _GT, "Floor 1")
    assert sc.wall_hits() == (4, 4)
    assert sc.window_hits() == (3, 3)


def test_offset_within_tol_counts_as_hit_with_delta():
    reading = {"strokes": [
        _wall("wall", [4.88, 0], [4.88, 3]), _wall("wall", [9.76, 0], [9.76, 3]),
        _wall("wall", [0, 2.94], [15, 2.94]), _wall("wall", [0, 4.82], [15, 4.82]),
    ]}
    sc = rs.score_floor(reading, _GT, "Floor 1")
    assert sc.wall_hits() == (4, 4)
    assert sc.max_wall_offset() == 0.24  # the 10→9.76 line


def test_displaced_wall_beyond_tol_is_miss_plus_extra():
    # dividers read 0.36 m off (4.64 / 9.64) → outside 0.30 tol → miss + extra
    reading = {"strokes": [
        _wall("wall", [4.64, 0], [4.64, 3]), _wall("wall", [9.64, 0], [9.64, 3]),
        _wall("wall", [0, 3], [15, 3]), _wall("wall", [0, 5], [15, 5]),
    ]}
    sc = rs.score_floor(reading, _GT, "Floor 1")
    assert sc.wall_hits() == (2, 4)              # verticals missed, horizontals hit
    assert sorted(sc.extra_vwalls) == [4.64, 9.64]


def test_floor_name_mapping():
    assert rs.floor_name_for_image("1f_view", _GT) == "Floor 1"
    assert rs.floor_name_for_image("2f_view", _GT) is None  # only 1 floor in synthetic gt


def test_sm21_phase1_reading_score_regression_floor():
    gt = load_gt("sm21_anchor")
    scores = rs.score_reading_dir(
        Path("case_tests/e2e_tests/smalloffice_21_pre/phase1"),
        "sm21_anchor",
    )
    assert scores

    wall_hits = wall_total = window_hits = window_total = 0
    for score in scores.values():
        wh, wt = score.wall_hits()
        nh, nt = score.window_hits()
        wall_hits += wh
        wall_total += wt
        window_hits += nh
        window_total += nt

    assert wall_hits == wall_total == 9
    assert window_total == 15
    assert window_hits >= 14
    assert gt is not None and gt["case"] == "sm21_anchor"
