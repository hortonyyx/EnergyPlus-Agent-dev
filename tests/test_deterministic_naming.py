"""Regression tests for deterministic public geometry naming."""

from __future__ import annotations

from src.agent.correction.schema import CorrectedGeometry, Window
from src.agent.geometry import build_geometry
from src.agent.geometry.specs import building_geometry_json, geometry_specs_markdown, serialize_geometry


def _json_and_specs(g: CorrectedGeometry) -> tuple[str, str]:
    bg = build_geometry(g)
    zs, ss, fs, _used = serialize_geometry(bg)
    return building_geometry_json(bg), geometry_specs_markdown(zs, ss, fs)


def test_cell_order_does_not_change_geometry_artifacts():
    base = {
        "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
        "cells": [
            {"id": "south", "role": "office", "x": [0, 5], "y": [0, 4]},
            {"id": "east", "role": "meeting room", "x": [5, 10], "y": [0, 4]},
            {"id": "north", "role": "corridor", "x": [0, 10], "y": [4, 8]},
        ],
    }
    g1 = CorrectedGeometry(footprint_x=[0, 10], footprint_y=[0, 8], floors=[base])
    shuffled = {**base, "cells": list(reversed(base["cells"]))}
    g2 = CorrectedGeometry(footprint_x=[0, 10], footprint_y=[0, 8], floors=[shuffled])
    assert _json_and_specs(g1) == _json_and_specs(g2)


def test_role_tokens_and_center_band_are_public_names_only():
    g = CorrectedGeometry(
        footprint_x=[0, 20], footprint_y=[0, 20],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "src-a", "role": "meeting room", "x": [9.6, 10.4], "y": [9.6, 10.4]},
            {"id": "src-b", "role": "entrance/lobby", "x": [14.0, 16.0], "y": [9.0, 11.0]},
            {"id": "src-c", "role": "", "x": [0.0, 1.0], "y": [0.0, 1.0]},
            {"id": "src-d", "role": "会议室", "x": [18.0, 19.0], "y": [18.0, 19.0]},
        ]}],
    )
    bg = build_geometry(g)
    assert any(z.endswith("_Meeting_Room_C") for z in bg.zones)
    assert any("_Entrance_Lobby_E" in z for z in bg.zones)
    assert any("_Office_SW" in z for z in bg.zones)
    assert any("_Office_NE" in z for z in bg.zones)
    assert {zv.cell_id for zv in bg.zone_volumes} == {"src-a", "src-b", "src-c", "src-d"}


def test_windows_group_by_parent_and_sort_along_wall():
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 8],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
            {"id": "room", "x": [0, 10], "y": [0, 8]},
        ]}],
        windows=[
            Window(id="late", floor="F1", facade="South", span=[6, 8], z=[1.0, 2.0], room="room"),
            Window(id="early", floor="F1", facade="South", span=[1, 3], z=[1.0, 2.0], room="room"),
        ],
    )
    bg = build_geometry(g)
    south_parent = bg.windows[0].parent
    assert [w.name for w in bg.windows] == [f"{south_parent}_Win1", f"{south_parent}_Win2"]
    assert [min(v[0] for v in w.verts) for w in bg.windows] == [1.0, 6.0]


def test_pairing_backfill_survives_surface_sorting_and_equal_pieces():
    g = CorrectedGeometry(
        footprint_x=[0, 10], footprint_y=[0, 12],
        floors=[
            {"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0, "cells": [
                {"id": "A", "x": [0, 10], "y": [0, 8]},
                {"id": "B", "x": [0, 5], "y": [8, 12]},
                {"id": "C", "x": [5, 10], "y": [8, 12]},
            ]},
            {"name": "F2", "z_floor": 3.0, "ceiling_height": 3.0, "cells": [
                {"id": "U1", "x": [0, 5], "y": [0, 8]},
                {"id": "U2", "x": [5, 10], "y": [0, 8]},
                {"id": "U3", "x": [0, 10], "y": [8, 12]},
            ]},
        ],
    )
    bg = build_geometry(g)
    by_name = {s.name: s for s in bg.surfaces}
    paired = [s for s in bg.surfaces if s.obc == "Surface"]
    assert paired
    for s in paired:
        other = by_name[s.obc_obj]
        assert other.obc == "Surface"
        assert other.obc_obj == s.name
    lower_a = next(zv.zone for zv in bg.zone_volumes if zv.cell_id == "A")
    assert len([s for s in paired if s.zone == lower_a and s.stype == "Wall"]) == 2
