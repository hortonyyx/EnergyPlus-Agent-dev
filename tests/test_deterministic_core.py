"""Deterministic-core guarantees: cluster -> snap-to-grid -> sliver guard, and
the window tier (fine grid + clamp into parent). Constants come from
src/configs/correction.yaml via the config loader."""

from __future__ import annotations

import pytest

from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.config import CoreTolerances, load_core_tolerances


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


def _two_floor(x_f1: float, x_f2: float, windows: list | None = None) -> CorrectedGeometry:
    """Two stacked floors whose mid partition is at x_f1 (F1) vs x_f2 (F2)."""
    return CorrectedGeometry(
        footprint_x=[0.0, 10.0],
        footprint_y=[0.0, 8.0],
        windows=windows or [],
        floors=[
            {
                "name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                "cells": [
                    {"id": "F1_A", "x": [0.0, x_f1], "y": [0.0, 8.0]},
                    {"id": "F1_B", "x": [x_f1, 10.0], "y": [0.0, 8.0]},
                ],
            },
            {
                "name": "F2", "z_floor": 3.6, "ceiling_height": 3.6,
                "cells": [
                    {"id": "F2_A", "x": [0.0, x_f2], "y": [0.0, 8.0]},
                    {"id": "F2_B", "x": [x_f2, 10.0], "y": [0.0, 8.0]},
                ],
            },
        ],
    )


def test_cross_floor_jitter_unified():
    """The same wall read as 4.90 (F1) and 4.95 (F2) becomes one canonical axis."""
    g = apply_deterministic_core(_two_floor(4.90, 4.95), _tol())
    right = {c.x[1] for fl in g.floors for c in fl.cells if c.id.endswith("_A")}
    assert len(right) == 1, f"cross-floor axis not unified: {right}"


def test_snapped_to_grid_no_mm_level_mean():
    """Cluster mean 4.925 must not leak out; result lands on the 50mm grid."""
    g = apply_deterministic_core(_two_floor(4.90, 4.95), _tol())
    val = next(c.x[1] for fl in g.floors for c in fl.cells if c.id == "F1_A")
    assert abs((val / 0.05) - round(val / 0.05)) < 1e-9, f"{val} not on 50mm grid"
    assert val != pytest.approx(4.925), "raw cluster mean leaked"


def test_sliver_guard_min_edge():
    """No two canonical axes end up closer than min_edge_length."""
    # partitions 0.07 apart on the two floors -> distinct clusters, but a 0.07
    # gap would be a sub-min-edge sliver; the guard must collapse them.
    g = apply_deterministic_core(_two_floor(4.90, 4.97), _tol())
    xs = sorted({c.x[0] for fl in g.floors for c in fl.cells} |
                {c.x[1] for fl in g.floors for c in fl.cells})
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert all(gp >= 0.10 - 1e-9 for gp in gaps), f"sliver survived: {xs}"


def test_window_uses_fine_grid_not_structural():
    """A window at 10mm offsets keeps them; it is not forced onto the 50mm grid."""
    g = _two_floor(5.0, 5.0, windows=[{"id": "W", "floor": "F1", "facade": "South",
                  "span": [1.013, 3.987], "z": [0.9, 2.1], "room": "F1_A"}])
    out = apply_deterministic_core(g, _tol())
    w = out.windows[0]
    assert w.span == [1.01, 3.99]  # rounded to 10mm, not snapped to 1.0/4.0
    assert w.z == [0.9, 2.1]


def test_window_clamped_into_parent():
    """An over-reaching window is clamped within its cell span and floor z-range."""
    g = _two_floor(5.0, 5.0, windows=[{"id": "W", "floor": "F1", "facade": "South",
                  "span": [1.0, 12.0], "z": [0.9, 9.0], "room": "F1_A"}])
    out = apply_deterministic_core(g, _tol())
    w = out.windows[0]
    assert w.span[1] <= 5.0  # within F1_A x = [0, 5]
    assert w.z[1] <= 3.6  # within floor z = [0, 3.6]


def test_window_clamp_can_be_disabled():
    g = _two_floor(5.0, 5.0, windows=[{"id": "W", "floor": "F1", "facade": "South",
                  "span": [1.0, 12.0], "z": [0.9, 2.1], "room": "F1_A"}])
    out = apply_deterministic_core(g, _tol(window_clamp_to_parent=False))
    assert out.windows[0].span[1] == 12.0  # snapped only, not clamped


def test_gap_close_internal_wall_reaches_exterior():
    """A cell edge 240mm short of the left exterior wall is pulled onto it."""
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                 "cells": [{"id": "A", "x": [0.24, 5.0], "y": [0.0, 8.0]},
                           {"id": "B", "x": [5.0, 10.0], "y": [0.0, 8.0]}]}],
    )
    out = apply_deterministic_core(g, _tol())
    a = next(c for c in out.floors[0].cells if c.id == "A")
    assert a.x[0] == 0.0, f"gap to exterior not closed: {a.x}"
    assert any(e.get("rule_id") == "deterministic_core.gap_close" for e in out.corrections)


def test_gap_close_leaves_interior_partition_untouched():
    """An interior partition far from any footprint boundary is not pulled."""
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                 "cells": [{"id": "A", "x": [0.0, 5.0], "y": [0.0, 8.0]},
                           {"id": "B", "x": [5.0, 10.0], "y": [0.0, 8.0]}]}],
    )
    out = apply_deterministic_core(g, _tol())
    shared = {c.x[1] for c in out.floors[0].cells if c.id == "A"}
    assert shared == {5.0}, "mid partition at 5.0 must not move to a boundary"


def test_gap_beyond_threshold_not_closed():
    """A 400mm gap (> 300mm) is left for A3, not auto-closed."""
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                 "cells": [{"id": "A", "x": [0.40, 5.0], "y": [0.0, 8.0]}]}],
    )
    out = apply_deterministic_core(g, _tol())
    assert out.floors[0].cells[0].x[0] == 0.40


def test_invariant_gap_close_ordering():
    """gap_close must sit between jitter tol and the arbitration band."""
    with pytest.raises(ValueError):
        _tol(gap_close_threshold_m=0.04)  # below axis_jitter_tol 0.05
    with pytest.raises(ValueError):
        _tol(gap_close_threshold_m=1.5)  # above arbitration band 1.0


def test_invariant_grid_not_above_min_edge():
    """The config guard rejects a structural grid coarser than the sliver floor."""
    with pytest.raises(ValueError):
        _tol(structural_snap_grid_m=0.20, min_edge_length_m=0.10)


def test_default_config_loads():
    """The shipped correction.yaml parses and satisfies its own invariants."""
    tol = load_core_tolerances()
    tol.validate()
    assert tol.structural_snap_grid_m <= tol.min_edge_length_m
