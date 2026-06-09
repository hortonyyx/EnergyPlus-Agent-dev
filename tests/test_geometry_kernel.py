"""Deterministic geometry kernel: clean inputs must produce a gate-clean surface
graph (split-pairing correct), and overlapping cells must be flagged.

Validated against the real InterZone gate (the spec of 'correct')."""

from __future__ import annotations

from src.agent.correction.schema import CorrectedGeometry, Window
from src.agent.geometry import build_geometry
from src.agent.geometry.to_idf import building_to_idf
from src.validator.interzone import validate_interzone_surface_pairs


def _gate(geom: CorrectedGeometry) -> list[str]:
    return validate_interzone_surface_pairs(building_to_idf(build_geometry(geom)))


def test_single_floor_multiroom_clean():
    """4 tiling rooms on one floor → interior walls paired, perimeter Outdoors."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "A", "x": [0, 5], "y": [0, 4]},
            {"id": "B", "x": [5, 10], "y": [0, 4]},
            {"id": "C", "x": [0, 5], "y": [4, 8]},
            {"id": "D", "x": [5, 10], "y": [4, 8]},
        ]}],
    )
    assert _gate(g) == []


def test_two_floor_aligned_clean():
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
                {"id": "F1_L", "x": [0, 5], "y": [0, 8]},
                {"id": "F1_R", "x": [5, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0, "cells": [
                {"id": "F2_L", "x": [0, 5], "y": [0, 8]},
                {"id": "F2_R", "x": [5, 10], "y": [0, 8]}]},
        ],
    )
    assert _gate(g) == []


def test_two_floor_misaligned_splitpair_clean():
    """Partitions at x=5 (F1) vs x=4 (F2) force cross-floor floor/ceiling split."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
                {"id": "F1_L", "x": [0, 5], "y": [0, 8]},
                {"id": "F1_R", "x": [5, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0, "cells": [
                {"id": "F2_L", "x": [0, 4], "y": [0, 8]},
                {"id": "F2_R", "x": [4, 10], "y": [0, 8]}]},
        ],
    )
    issues = _gate(g)
    assert issues == [], issues


def test_setback_clean():
    """Upper floor smaller than lower → lower ceiling part interzone, part roof."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
                {"id": "F1_A", "x": [0, 10], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0, "cells": [
                {"id": "F2_A", "x": [0, 6], "y": [0, 8]}]},  # setback in x
        ],
    )
    issues = _gate(g)
    assert issues == [], issues
    # the exposed part of F1's ceiling must be a Roof (Outdoors)
    bg = build_geometry(g)
    assert any(s.stype == "Roof" and s.zone == "F1_A" for s in bg.surfaces)


def test_lshape_polygon_clean():
    """Non-rectangular (L-shaped) room via explicit polygon — kernel is polygon-native."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 10],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "L", "x": [0, 10], "y": [0, 10],
             "polygon": [[0, 0], [10, 0], [10, 6], [6, 6], [6, 10], [0, 10]]},
            {"id": "M", "x": [6, 10], "y": [6, 10],
             "polygon": [[6, 6], [10, 6], [10, 10], [6, 10]]},
        ]}],
    )
    assert _gate(g) == []


def test_overlap_is_flagged():
    """Overlapping cells (a phase2a tiling defect) must be reported in notes."""
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "Room", "x": [0, 5], "y": [3, 5]},
            {"id": "Corridor", "x": [0, 10], "y": [3, 5]},  # overlaps Room
        ]}],
    )
    bg = build_geometry(g)
    assert any("OVERLAP" in n for n in bg.notes)


# --------------------------------------------------------------------------- #
# Step-2 coverage: benchmark the kernel against sm20-grade geometry (3 floors,
# different partition count per floor → maximally misaligned cross-floor split-
# pairing). This is the case the one-step LLM got right and staged phase2 broke;
# it must pass the real gate by construction, proving the kernel covers the
# geometry edge cases rules.md used to delegate to the LLM.
# --------------------------------------------------------------------------- #
def _sm20_shaped() -> CorrectedGeometry:
    """3 floors, footprint 15×8, misaligned partitions: 4 / 3 / 2 cells.

    F1 breaks at x=4,8,11 · F2 at x=5,10 · F3 at x=7 — no two floors share a
    break, so every floor/ceiling pair must be cut at the union of both stacks'
    x-breaks and paired 1:1."""
    return CorrectedGeometry(
        footprint_x=[0, 15], footprint_y=[0, 8],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6, "cells": [
                {"id": "F1_A", "x": [0, 4], "y": [0, 8]},
                {"id": "F1_B", "x": [4, 8], "y": [0, 8]},
                {"id": "F1_C", "x": [8, 11], "y": [0, 8]},
                {"id": "F1_D", "x": [11, 15], "y": [0, 8]}]},
            {"name": "F2", "z_floor": 3.6, "ceiling_height": 3.6, "cells": [
                {"id": "F2_A", "x": [0, 5], "y": [0, 8]},
                {"id": "F2_B", "x": [5, 10], "y": [0, 8]},
                {"id": "F2_C", "x": [10, 15], "y": [0, 8]}]},
            {"name": "F3", "z_floor": 7.2, "ceiling_height": 3.6, "cells": [
                {"id": "F3_A", "x": [0, 7], "y": [0, 8]},
                {"id": "F3_B", "x": [7, 15], "y": [0, 8]}]},
        ],
    )


def test_sm20_shaped_misaligned_three_floor_clean():
    """The whole 4/3/2 misaligned stack passes the InterZone gate with 0 issues."""
    issues = _gate(_sm20_shaped())
    assert issues == [], issues


def test_window_attaches_on_upper_floors():
    """A window on each floor's south facade attaches to the right exterior wall
    with z inside the parent wall — the multi-floor fenestration path rules.md
    Step 6 used to drive by hand (CHKSBS-prevention)."""
    g = _sm20_shaped()
    # south facade (y=0), span along x; z absolute (sill/head within each floor)
    g.windows = [
        Window(id="W1", floor="F1", facade="South", span=[1.0, 3.0], z=[0.9, 2.4], room="F1_A"),
        Window(id="W2", floor="F2", facade="South", span=[1.0, 3.0], z=[4.5, 6.0], room="F2_A"),
        Window(id="W3", floor="F3", facade="South", span=[1.0, 3.0], z=[8.1, 9.6], room="F3_A"),
    ]
    bg = build_geometry(g)
    assert len(bg.windows) == 3, bg.notes
    assert not any("no exterior wall" in n or "not found" in n for n in bg.notes), bg.notes
    # each window's z sits inside its parent wall's z-range
    for w in bg.windows:
        parent = next(s for s in bg.surfaces if s.name == w.parent)
        zs_w = [v[2] for v in w.verts]
        zs_p = [v[2] for v in parent.verts]
        assert min(zs_p) - 1e-6 <= min(zs_w) and max(zs_w) <= max(zs_p) + 1e-6
