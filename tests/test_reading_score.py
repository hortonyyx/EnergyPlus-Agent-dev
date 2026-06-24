"""Tests for the coordinate-level reading↔gt scorer (judge-side metric)."""
from __future__ import annotations

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
