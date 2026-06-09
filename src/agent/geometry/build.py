"""Deterministic geometry build — orchestrator.

Input  : CorrectedGeometry (room cells per floor, polygon or x/y rect, + windows)
Output : BuildingGeometry (zones + fully-resolved surfaces + windows)

Two stages, split into modules:
  - `modelling`     建模·几何: cells -> zone volumes + face vertex realization
  - `split_pairing` 切配·仿真: which faces exist + 1:1 reciprocal correspondence

This module wires them together and re-exports the output dataclasses so existing
imports (`from src.agent.geometry.build import BuildingGeometry/Surface/Window`)
keep working. Geometry only — no physics.
"""

from __future__ import annotations

from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry.modelling import (
    BuildingGeometry,
    NameRegistry,
    Surface,
    Window,
    attach_windows,
    build_zone_volumes,
)
from src.agent.geometry.split_pairing import pair_surfaces

__all__ = ["BuildingGeometry", "Surface", "Window", "build_geometry"]


def build_geometry(geom: CorrectedGeometry) -> BuildingGeometry:
    out = BuildingGeometry()

    # 建模·几何: cells -> zone volumes (+ tiling guard notes)
    zvs, overlap_notes = build_zone_volumes(geom)
    out.zones = [zv.zone for zv in zvs]
    out.notes.extend(overlap_notes)

    # 切配·仿真: zone volumes -> cut + paired surfaces
    registry = NameRegistry()
    out.surfaces = pair_surfaces(zvs, registry)

    # windows -> sub-surface on the room's exterior wall on that facade
    zv_by_cell = {zv.cell_id: zv for zv in zvs}
    out.windows, win_notes = attach_windows(geom, out.surfaces, zv_by_cell, registry)
    out.notes.extend(win_notes)

    return out
