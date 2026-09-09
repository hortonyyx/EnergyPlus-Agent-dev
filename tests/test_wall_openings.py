from __future__ import annotations

import copy
import json

import pytest
from shapely.geometry import Polygon

from src.agent.correction.schema import CorrectedGeometry, WallOpening
from src.agent.geometry import build_geometry
from src.agent.geometry.modelling import Surface
from src.agent.geometry.openings import OpeningBindingError, attach_openings, visible_wall_parts
from src.agent.geometry.source_model import materialize_source_model
from src.agent.geometry.specs import building_geometry_dict, serialize_geometry
from src.agent.geometry.to_idf import building_to_idf
from src.agent.judge.source_connections import compare_connections


def _geom(**opening_updates):
    aperture = {"id": "hall_door", "kind": "door", "space_id": "A", "other_space_id": "B",
                "p1": [4, 1], "p2": [4, 2], "z": [0, 2.1], "source_refs": ["fixture:door"]}
    aperture.update(opening_updates)
    return CorrectedGeometry.model_validate({
        "footprint_x": [0, 8], "footprint_y": [0, 4],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "A", "x": [0, 4], "y": [0, 4]}, {"id": "B", "x": [4, 8], "y": [0, 4]},
        ]}], "openings": [aperture],
    })


def test_door_roundtrip_two_sides_and_one_connection(tmp_path):
    from src.agent.pipeline import materialize_kernel_geometry

    geom = _geom()
    decoded = CorrectedGeometry.model_validate_json(geom.model_dump_json())
    assert decoded.openings == geom.openings
    bg, issues = materialize_kernel_geometry(decoded, tmp_path)
    assert bg is not None and issues == []
    assert len(bg.openings) == 2 and len(bg.zones) == 2
    assert bg.openings[0].partner == bg.openings[1].name
    source = json.loads((tmp_path / "source_model.json").read_text())
    assert source["validation"]["status"] == "pass"
    assert len(source["openings"]) == 1
    assert source["connections"] == [{"opening_id": "hall_door", "kind": "door", "space_ids": ["A", "B"],
                                      "exterior": False, "state": "unknown"}]
    assert set(source["derived"]["openings"].values()) == {"hall_door"}


@pytest.mark.parametrize("updates", [
    {"other_space_id": None}, {"other_space_id": "missing"}, {"space_id": "missing"},
    {"p1": [3, 1], "p2": [3, 2]}, {"p1": [4, 3], "p2": [4, 5]}, {"z": [0, 3.1]},
])
def test_wrong_room_missing_host_crossed_edge_or_height_are_rejected(updates):
    with pytest.raises(OpeningBindingError):
        build_geometry(_geom(**updates))


def test_exterior_door_has_one_side_and_does_not_invent_a_neighbour():
    geom = _geom(other_space_id=None, p1=[1, 0], p2=[2, 0])
    bg = build_geometry(geom)
    source = materialize_source_model(geom, bg)
    assert len(bg.openings) == 1 and bg.openings[0].partner == ""
    assert source["connections"][0]["space_ids"] == ["A"]
    assert source["connections"][0]["exterior"]


def test_open_aperture_is_open_and_closed_door_retains_state():
    assert _geom(kind="open").openings[0].state == "open"
    with pytest.raises(ValueError, match="unfilled"):
        _geom(kind="open", state="closed")
    geom = _geom(state="closed")
    assert materialize_source_model(geom, build_geometry(geom))["connections"][0]["state"] == "closed"


@pytest.mark.parametrize("updates", [
    {"p1": [float("nan"), 0]}, {"p2": [4, 1]}, {"z": [2, 1]}, {"source_refs": []},
    {"other_space_id": "A"}, {"p2": [5, 2]},
])
def test_invalid_source_apertures_are_not_accepted(updates):
    with pytest.raises(ValueError):
        _geom(**updates)


def test_duplicate_and_overlapping_apertures_are_rejected():
    geom = _geom()
    geom.openings.append(copy.deepcopy(geom.openings[0]))
    with pytest.raises(OpeningBindingError, match="unique"):
        build_geometry(geom)
    geom.openings[1].id = "another_door"
    with pytest.raises(OpeningBindingError, match="overlapping"):
        build_geometry(geom)


@pytest.mark.parametrize("mutation", ["drop", "duplicate", "move", "close", "wrong_space"])
def test_source_mapping_detects_changed_derived_apertures(mutation):
    geom = _geom(kind="open")
    bg = build_geometry(geom)
    if mutation == "drop": bg.openings.pop()
    elif mutation == "duplicate": bg.openings.append(copy.deepcopy(bg.openings[0]))
    elif mutation == "move": bg.openings[0].verts = [(x, y + .1, z) for x, y, z in bg.openings[0].verts]
    elif mutation == "close": bg.openings[0].state = "closed"
    else: bg.openings[0].other_space_id = "wrong"
    assert materialize_source_model(geom, bg)["validation"]["status"] == "severe"


def test_display_subtracts_a_floor_touching_door_and_a_raised_hole():
    for z in ([0, 2.1], [.5, 2.1]):
        geom = _geom(z=z)
        bg = build_geometry(geom)
        parts = visible_wall_parts(building_geometry_dict(bg))
        assert len(parts) == 2
        for pieces in parts.values():
            area = sum(Polygon([(y, height) for _, y, height in part["verts"]],
                               [[(y, height) for _, y, height in ring] for ring in part["holes"]]).area
                       for part in pieces)
            assert area == pytest.approx(12 - (z[1] - z[0]))
            assert bool(pieces[0]["holes"]) == (z[0] > 0)


def test_aperture_survives_computational_face_split():
    geom = _geom(kind="open")
    bg = build_geometry(geom)
    paired = [s for s in bg.surfaces if s.stype == "Wall" and s.obc == "Surface"]
    left, right = paired
    bg.surfaces = [s for s in bg.surfaces if s not in paired]
    for face, partner in [(left, right), (right, left)]:
        for index, (lo, hi) in enumerate([(0, 1.5), (1.5, 4)]):
            vertices = [(4, lo, 0), (4, hi, 0), (4, hi, 3), (4, lo, 3)]
            bg.surfaces.append(Surface(f"{face.name}_{index}", face.zone, "Wall", vertices, "Surface", f"{partner.name}_{index}"))
    bg.openings = attach_openings(geom, bg)
    source = materialize_source_model(geom, bg)
    assert len(bg.openings) == 4 and len(source["openings"]) == 1 and len(source["spaces"]) == 2
    assert source["validation"]["status"] == "pass"


def test_energyplus_output_cannot_silently_seal_openings():
    bg = build_geometry(_geom(kind="open"))
    with pytest.raises(ValueError, match="refusing to silently replace"):
        serialize_geometry(bg)
    with pytest.raises(ValueError, match="refusing to silently replace"):
        building_to_idf(bg)
    assert building_to_idf(bg, boundary_validation_only=True).idfobjects["BUILDINGSURFACE:DETAILED"]


def test_cli_saves_opening_viewer_before_stopping_unsupported_export(tmp_path):
    from scripts.tool_scripts import run_stage
    from src.agent.execution import RunPolicy

    correction = tmp_path / "1_correction/correction_geometry_snapped.json"
    correction.parent.mkdir()
    correction.write_text(_geom().model_dump_json())
    payload, report = run_stage._draw_modelling(tmp_path, RunPolicy())
    assert len(payload["openings"]) == 2 and not report.blocking()
    pointer = json.loads((tmp_path / "_run/source_geometry_review.json").read_text())
    viewer = (tmp_path / pointer["viewer"]).read_text()
    assert '"visible_wall_parts"' in viewer and 'hall_door' in viewer
    with pytest.raises(ValueError, match="refusing to silently replace"):
        run_stage._draw_split_pairing(tmp_path, RunPolicy())
    assert not (tmp_path / "3_split_pairing/geometry_specs.md").exists()


@pytest.mark.parametrize("mutation, code", [
    ("drop", "connection_missing"), ("close", "connection_state_changed"),
    ("wrong_space", "connection_wrong_spaces"), ("wrong_host", "connection_wrong_host"),
])
def test_connection_comparison_catches_lost_or_changed_connections(mutation, code):
    geom = _geom(state="open")
    reference = materialize_source_model(geom, build_geometry(geom))
    changed = copy.deepcopy(reference)
    if mutation == "drop": changed["openings"] = []
    elif mutation == "close": changed["openings"][0]["connectivity"] = "closed"
    elif mutation == "wrong_space": changed["openings"][0]["space_ids"] = ["A", "C"]
    else: changed["openings"][0]["host_boundary_id"] = "another_wall"
    report = compare_connections(reference, changed)
    assert report["status"] == "severe"
    assert code in {f["code"] for f in report["findings"]}
    assert compare_connections(reference, reference)["status"] == "pass"
    assert compare_connections(None, reference)["status"] == "not_evaluated"


def test_viewer_embeds_cut_walls_and_connection_identity():
    from scripts.tool_scripts.render_geometry_viewer import build_viewer_html

    geom = _geom(kind="open")
    bg = build_geometry(geom)
    data = building_geometry_dict(bg)
    data["source_model"] = materialize_source_model(geom, bg)
    page = build_viewer_html(data)
    start = page.index("window.GEO = ") + len("window.GEO = ")
    embedded = json.loads(page[start:page.index(";</script>", start)])
    assert len(embedded["openings"]) == 2
    assert len(embedded["visible_wall_parts"]) == 2
    assert embedded["source_model"]["connections"][0]["state"] == "open"


@pytest.mark.parametrize("candidate", [{}, {"openings": None}, {"openings": {}}, None])
def test_connection_comparison_rejects_missing_or_invalid_candidate_records(candidate):
    assert compare_connections({"openings": []}, candidate)["status"] == "severe"


def test_v3_finalize_preserves_opening_and_proof_detects_later_changes(tmp_path):
    from b5_test_helpers import finalize_empty_window_v3
    from src.agent.correction.deterministic import core_owned_projection_v1
    from src.agent.execution.manifest import hash_obj

    payload = _geom().model_dump(mode="json")
    payload["schema_version"] = "3"
    payload["floors"][0].update(id="f1", footprint={"vertices": [[0, 0], [8, 0], [8, 4], [0, 4]]})
    result = finalize_empty_window_v3(payload, vector_dir=tmp_path)
    assert result.geom.openings == _geom().openings
    projection = core_owned_projection_v1(result.geom)
    before = hash_obj(projection)
    result.geom.openings[0].state = "closed"
    assert hash_obj(core_owned_projection_v1(result.geom)) != before
    result.geom.openings = []
    assert "openings" not in core_owned_projection_v1(result.geom)
    assert "openings" not in result.geom.model_dump(mode="json")
