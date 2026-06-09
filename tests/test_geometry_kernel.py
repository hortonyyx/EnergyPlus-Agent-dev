"""Deterministic geometry kernel: clean inputs must produce a gate-clean surface
graph (split-pairing correct), and overlapping cells must be flagged.

Validated against the real InterZone gate (the spec of 'correct')."""

from __future__ import annotations

from src.agent.correction.schema import CorrectedGeometry
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
