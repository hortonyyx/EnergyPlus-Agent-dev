"""Existing consumers must reject apertures they cannot preserve yet."""
from __future__ import annotations

import copy
import json

import pytest

from scripts.tool_scripts import render_building_3d
from src.agent.correction.multifloor import (
    MultiFloorAssemblyError, assemble_multifloor_geometry, derive_floor_ladder,
)
from src.agent.correction.schema import CorrectedGeometry, WallOpening
from src.agent.geometry import build_geometry
from src.agent.geometry.specs import building_geometry_dict
from tests.test_b2_multifloor_assembly import _RECT, _elevation, _square_floor


@pytest.mark.parametrize("kind", ["door", "open"])
@pytest.mark.parametrize("opening_floor", [0, 1])
def test_multifloor_assembly_refuses_to_discard_explicit_apertures(kind, opening_floor):
    floors = [_square_floor("f0", _RECT), _square_floor("f1", _RECT)]
    floors[opening_floor].openings = [WallOpening(
        id="aperture", kind=kind, space_id=f"f{opening_floor}-c0", other_space_id=None,
        p1=(1, 0), p2=(2, 0), z=(999, 1001), source_refs=["synthetic:declared-aperture"],
    )]
    before = [floor.model_dump() for floor in floors]
    ladder = derive_floor_ladder(_elevation([2900, 3300]))
    with pytest.raises(MultiFloorAssemblyError, match="WALL_OPENING_ASSEMBLY_UNSUPPORTED") as caught:
        assemble_multifloor_geometry(ladder, floors)
    assert caught.value.detail["opening_ids"] == ["aperture"]
    assert [floor.model_dump() for floor in floors] == before


def _building(*, kind="open", with_opening=True):
    geom = CorrectedGeometry.model_validate({
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "A", "x": [0, 5], "y": [0, 8]},
            {"id": "B", "x": [5, 10], "y": [0, 8]},
        ]}],
        "openings": [{"id": "aperture", "kind": kind, "space_id": "A", "other_space_id": "B",
                      "p1": [5, 0], "p2": [5, 8], "z": [0, 3],
                      "source_refs": ["synthetic:whole-wall-aperture"]}] if with_opening else [],
    })
    return building_geometry_dict(build_geometry(geom))


@pytest.mark.parametrize("kind", ["door", "open"])
def test_old_mesh_export_refuses_to_seal_a_source_aperture(kind):
    data = _building(kind=kind)
    before = copy.deepcopy(data)
    with pytest.raises(ValueError, match="refusing to replace their openings with solid walls"):
        render_building_3d._load_scene(data)
    assert data == before


def test_old_mesh_cli_refuses_before_writing_glb_or_png(tmp_path, monkeypatch):
    source = tmp_path / "building_geometry.json"
    source.write_text(json.dumps(_building()))
    glb = tmp_path / "view.glb"
    png = tmp_path / "view.png"
    monkeypatch.setattr("sys.argv", ["render_building_3d", str(source), "--glb", str(glb), "--png", str(png)])
    with pytest.raises(ValueError, match="GLB/PNG export does not yet support"):
        render_building_3d.main()
    assert not glb.exists() and not png.exists()


def test_old_mesh_without_apertures_still_exports_glb(tmp_path):
    mesh = render_building_3d._load_scene(_building(with_opening=False))
    output = tmp_path / "legacy.glb"
    mesh.export(output)
    assert len(mesh.faces) == 24
    assert output.read_bytes().startswith(b"glTF")
