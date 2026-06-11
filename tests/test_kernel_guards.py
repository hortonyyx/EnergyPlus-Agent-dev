"""Hard guards added by the 2026-06-11 audit (review H1/H2/M1/M2/L3): the
failure classes every gate is blind to must fail loud (raise / explicit drop),
never silently corrupt geometry. Repro shapes mirror the audit review §2."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.config import CoreTolerances
from src.agent.geometry import build_geometry


def _tol(**over) -> CoreTolerances:
    base = dict(
        axis_jitter_tol_m=0.05,
        structural_snap_grid_m=0.05,
        min_edge_length_m=0.10,
        output_precision_m=0.01,
        window_snap_grid_m=0.01,
        window_clamp_to_parent=True,
        gap_close_threshold_m=0.30,
        gap_arbitration_band_m=1.00,
    )
    base.update(over)
    t = CoreTolerances(**base)
    t.validate()
    return t


def _geom(floors, windows=None) -> CorrectedGeometry:
    return CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=floors, windows=windows or [],
    )


def _floor(name, zf, ch, cells):
    return {"name": name, "z_floor": zf, "ceiling_height": ch, "cells": cells}


# --------------------------------------------------------------------------- #
# H1 — duplicate cell ids must raise (kernel and core)
# --------------------------------------------------------------------------- #
def test_duplicate_cell_id_across_floors_raises_in_kernel():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "Office", "x": [0, 5], "y": [0, 8]},
                                {"id": "Corridor", "x": [5, 10], "y": [0, 8]}]),
        _floor("F2", 3.0, 3.0, [{"id": "Office2", "x": [0, 5], "y": [0, 8]},
                                {"id": "Corridor", "x": [5, 10], "y": [0, 8]}]),
    ])
    with pytest.raises(ValueError, match="duplicate cell id 'Corridor'"):
        build_geometry(g)


def test_duplicate_cell_id_raises_in_core():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "Room", "x": [0, 10], "y": [0, 8]}]),
        _floor("F2", 3.0, 3.0, [{"id": "Room", "x": [0, 10], "y": [0, 8]}]),
    ])
    with pytest.raises(ValueError, match="duplicate cell id 'Room'"):
        apply_deterministic_core(g, _tol())


def test_zone_name_collision_after_sanitize_raises():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "Room 1", "x": [0, 5], "y": [0, 8]},
                                {"id": "Room_1", "x": [5, 10], "y": [0, 8]}]),
    ])
    with pytest.raises(ValueError, match="collide on the EP-safe zone name"):
        build_geometry(g)


# --------------------------------------------------------------------------- #
# H2 — z-stack continuity: small gaps snapped by the core, large gaps raise
# --------------------------------------------------------------------------- #
def test_z_stack_gap_raises_in_kernel():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}]),
        _floor("F2", 3.5, 3.0, [{"id": "F2_A", "x": [0, 10], "y": [0, 8]}]),
    ])
    with pytest.raises(ValueError, match="broken z-stack"):
        build_geometry(g)


def test_z_stack_overlap_raises_in_kernel():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}]),
        _floor("F2", 2.5, 3.0, [{"id": "F2_A", "x": [0, 10], "y": [0, 8]}]),
    ])
    with pytest.raises(ValueError, match="broken z-stack"):
        build_geometry(g)


def test_core_snaps_small_z_gap():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}]),
        _floor("F2", 3.25, 3.0, [{"id": "F2_A", "x": [0, 10], "y": [0, 8]}]),
    ])
    out = apply_deterministic_core(g, _tol())
    assert out.floors[1].z_floor == 3.0
    assert any(e.get("rule_id") == "deterministic_core.z_stack" for e in out.corrections)
    # and the snapped geometry now builds cleanly
    bg = build_geometry(out)
    assert not any(s.stype == "Floor" and s.obc == "Outdoors" for s in bg.surfaces)


def test_core_flags_large_z_gap_unsupported():
    g = _geom([
        _floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}]),
        _floor("F2", 3.5, 3.0, [{"id": "F2_A", "x": [0, 10], "y": [0, 8]}]),
    ])
    out = apply_deterministic_core(g, _tol())
    assert out.floors[1].z_floor == 3.5  # NOT silently moved
    assert any("broken z-stack" in u.get("reason", "") for u in out.unsupported)


# --------------------------------------------------------------------------- #
# M1 — kernel window loss must raise, not note-and-continue
# --------------------------------------------------------------------------- #
def test_window_with_unknown_room_raises():
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
        windows=[{"id": "W1", "floor": "F1", "facade": "South",
                  "span": [2, 4], "z": [1.0, 2.5], "room": None},
                 {"id": "W2", "floor": "F1", "facade": "South",
                  "span": [6, 8], "z": [1.0, 2.5], "room": "F1_A"}],
    )
    with pytest.raises(ValueError, match="window attachment lost 1 of 2"):
        build_geometry(g)


def test_window_without_exterior_wall_raises():
    # F1_B has no South exposure (F1_A spans the full south edge)
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 4]},
                                 {"id": "F1_B", "x": [0, 10], "y": [4, 8]}])],
        windows=[{"id": "W1", "floor": "F1", "facade": "South",
                  "span": [2, 4], "z": [1.0, 2.5], "room": "F1_B"}],
    )
    with pytest.raises(ValueError, match="window attachment lost 1 of 1"):
        build_geometry(g)


def test_full_depth_room_window_attaches_to_correct_facade():
    """H4: a full-depth room has exterior walls on BOTH north and south; the
    South window must land on the south-facing wall (outward normal -y), not
    whichever constant-y wall matched last."""
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
        windows=[{"id": "WS", "floor": "F1", "facade": "South",
                  "span": [2, 4], "z": [1.0, 2.5], "room": "F1_A"},
                 {"id": "WN", "floor": "F1", "facade": "North",
                  "span": [6, 8], "z": [1.0, 2.5], "room": "F1_A"}],
    )
    bg = build_geometry(g)
    assert len(bg.windows) == 2
    wall_by_name = {s.name: s for s in bg.surfaces}
    for w, want_y in zip(bg.windows, [0.0, 8.0]):
        assert all(v[1] == want_y for v in w.verts), (
            f"{w.name} placed at y={w.verts[0][1]}, expected facade plane y={want_y}"
        )
        parent_ys = {v[1] for v in wall_by_name[w.parent].verts}
        assert parent_ys == {want_y}


# --------------------------------------------------------------------------- #
# M2 — post-clamp window sanity: degenerate / full-wall windows drop explicitly
# --------------------------------------------------------------------------- #
def test_core_drops_degenerate_window():
    # z entirely above the floor -> clamped to [top, top] = zero height
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
        windows=[{"id": "W1", "floor": "F1", "facade": "South",
                  "span": [2, 4], "z": [3.5, 4.5], "room": "F1_A"}],
    )
    out = apply_deterministic_core(g, _tol())
    assert out.windows == []
    assert any(u.get("target") == "W1" and "degenerate" in u["reason"]
               for u in out.unsupported)


def test_core_drops_full_wall_window():
    # span and z both beyond the cell/floor -> clamped to the entire wall face
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
        windows=[{"id": "W1", "floor": "F1", "facade": "South",
                  "span": [-1, 11], "z": [-0.5, 4.0], "room": "F1_A"}],
    )
    out = apply_deterministic_core(g, _tol())
    assert out.windows == []
    assert any(u.get("target") == "W1" and "full wall face" in u["reason"]
               for u in out.unsupported)


def test_core_keeps_valid_clamped_window():
    # over-reaching on one side only: clamped result is still a legal window
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
        windows=[{"id": "W1", "floor": "F1", "facade": "South",
                  "span": [1.0, 12.0], "z": [0.9, 9.0], "room": "F1_A"}],
    )
    out = apply_deterministic_core(g, _tol())
    assert len(out.windows) == 1
    assert out.windows[0].span == [1.0, 10.0]
    assert out.windows[0].z == [0.9, 3.0]


# --------------------------------------------------------------------------- #
# L3 — facade vocabulary is constrained (normalized, unknown rejected)
# --------------------------------------------------------------------------- #
def test_facade_case_and_letter_normalized():
    g = _geom(
        [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
        windows=[{"id": "W1", "floor": "F1", "facade": "south",
                  "span": [2, 4], "z": [1.0, 2.5], "room": "F1_A"},
                 {"id": "W2", "floor": "F1", "facade": "N",
                  "span": [2, 4], "z": [1.0, 2.5], "room": "F1_A"}],
    )
    assert g.windows[0].facade == "South"
    assert g.windows[1].facade == "North"


def test_unknown_facade_rejected():
    with pytest.raises(ValidationError):
        _geom(
            [_floor("F1", 0.0, 3.0, [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}])],
            windows=[{"id": "W1", "floor": "F1", "facade": "Northeast",
                      "span": [2, 4], "z": [1.0, 2.5], "room": "F1_A"}],
        )
