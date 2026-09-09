"""Legacy windows may touch a proven host edge without moving or losing them."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from src.agent.correction.schema import CorrectedGeometry, Window
from src.agent.geometry import Surface, build_geometry
from src.agent.geometry.modelling import _find_parent_wall
from src.agent.geometry.source_model import materialize_source_model


def _window(span, facade="South"):
    return Window(id="W", floor="F1", facade=facade, span=span, z=[1, 2], room="A")


def _wall(name, span, *, facade="South", plane=0, zone="A", obc="Outdoors"):
    lo, hi = span
    if facade in {"South", "North"}:
        vertices = [(lo, plane, 0), (hi, plane, 0), (hi, plane, 3), (lo, plane, 3)]
    else:
        vertices = [(plane, lo, 0), (plane, hi, 0), (plane, hi, 3), (plane, lo, 3)]
    if facade in {"North", "West"}:
        vertices.reverse()
    return Surface(name, zone, "Wall", vertices, obc)


def _two_rooms(span):
    return CorrectedGeometry.model_validate({
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "A", "x": [0, 5], "y": [0, 8]},
            {"id": "B", "x": [5, 10], "y": [0, 8]},
        ]}],
        "windows": [_window(span).model_dump()],
    })


@pytest.mark.parametrize("facade", ["South", "North", "East", "West"])
@pytest.mark.parametrize("span", [[0, 1], [4, 5], [0, 5], [.01, 4.99], [1, 4]])
def test_unique_wall_accepts_edges_and_near_edges_on_each_facade(facade, span):
    wall = _wall("host", [0, 5], facade=facade)
    window = _window(span, facade)
    before = copy.deepcopy((wall, window))
    assert _find_parent_wall([wall], "A", window) is wall
    assert (wall, window) == before


@pytest.mark.parametrize("overrun", [0.5e-6, 1e-6, 1e-5, .01, .1])
@pytest.mark.parametrize("end", ["lower", "upper"])
def test_unproven_overrun_is_rejected_even_below_pairing_buffer(overrun, end):
    wall = _wall("host", [0, 5])
    span = [-overrun, 1] if end == "lower" else [4, 5 + overrun]
    assert _find_parent_wall([wall], "A", _window(span)) is None


@pytest.mark.parametrize("other_span", [[-1, 0], [-1, -.01], [1, 2], [1.01, 2]])
def test_touching_or_nearby_segment_does_not_make_unique_host_ambiguous(other_span):
    host = _wall("host", [0, 1])
    neighbor = _wall("neighbor", other_span)
    for walls in ([host, neighbor], [neighbor, host]):
        assert _find_parent_wall(walls, "A", _window([0, 1])) is host


@pytest.mark.parametrize("other_plane", [0, 2])
def test_two_covering_walls_are_still_ambiguous(other_plane):
    walls = [_wall("first", [0, 5]), _wall("second", [0, 5], plane=other_plane)]
    for candidates in (walls, list(reversed(walls))):
        with pytest.raises(ValueError, match="ambiguous parent wall"):
            _find_parent_wall(candidates, "A", _window([0, 1]))


def test_window_crossing_two_segments_of_one_room_has_no_single_host():
    walls = [_wall("first", [0, 5]), _wall("second", [5, 10])]
    assert _find_parent_wall(walls, "A", _window([4, 6])) is None


def test_paired_wall_endpoint_proves_numerical_erosion_without_moving_window():
    geom = _two_rooms([4, 5])
    original = geom.model_dump()
    bg = build_geometry(geom)
    window = bg.windows[0]
    parent = next(s for s in bg.surfaces if s.name == window.parent)
    assert max(v[0] for v in parent.verts) == pytest.approx(4.999999, abs=1e-12)
    assert sorted({v[0] for v in window.verts}) == [4, 5]
    assert geom.model_dump() == original
    assert materialize_source_model(geom, bg)["validation"]["status"] == "pass"


@pytest.mark.parametrize("zone,plane", [("B", 0), ("A", .1)])
def test_other_room_or_other_plane_cannot_prove_endpoint_erosion(zone, plane):
    exterior = _wall("host", [1e-6, 5])
    shared = _wall("shared", [0, 8], facade="East", plane=plane, zone=zone, obc="Surface")
    assert _find_parent_wall([exterior, shared], "A", _window([0, 1])) is None


@pytest.mark.parametrize("overrun", [0.5e-6, 1e-6, 1e-5, .01, .1])
def test_window_crossing_into_other_room_is_not_rescued_by_pairing_buffer(overrun):
    with pytest.raises(ValueError, match="window attachment lost"):
        build_geometry(_two_rooms([4, 5 + overrun]))


def test_sm24_rebuild_keeps_all_eleven_source_windows_and_mapping():
    root = Path(__file__).resolve().parents[1]
    path = root / "case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading/1_correction/correction_geometry_snapped.json"
    geom = CorrectedGeometry.model_validate_json(path.read_text())
    before = geom.model_dump()
    bg = build_geometry(geom)
    source_windows = {w.id: w for w in geom.windows}
    surfaces = {s.name: s for s in bg.surfaces}
    source_rooms = {z.zone: z.cell_id for z in bg.zone_volumes}
    assert len(bg.windows) == len(source_windows) == 11
    assert {w.source_window_id for w in bg.windows} == set(source_windows)
    for window in bg.windows:
        source = source_windows[window.source_window_id]
        parent = surfaces[window.parent]
        axis = 1 if source.facade in {"East", "West"} else 0
        assert sorted({v[axis] for v in window.verts}) == source.span
        assert sorted({v[2] for v in window.verts}) == source.z
        assert source_rooms[parent.zone] == source.room
    edge_window = next(w for w in bg.windows if w.source_window_id == "win_east_2")
    assert min(v[1] for v in surfaces[edge_window.parent].verts) == pytest.approx(15.050001, abs=1e-12)
    assert min(v[1] for v in edge_window.verts) == 15.05
    assert geom.model_dump() == before
    source = materialize_source_model(geom, bg)
    assert source["validation"]["status"] == "pass"
    assert len(source["openings"]) == 11
