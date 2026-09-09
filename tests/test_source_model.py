from __future__ import annotations

import copy
import json
from pathlib import Path

from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry import Surface, build_geometry
from src.agent.geometry.source_model import materialize_source_model


def _source():
    return CorrectedGeometry.model_validate({
        "schema_version": "2", "footprint_x": [0, 6], "footprint_y": [0, 6],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "hall", "role": "corridor", "x": [0, 6], "y": [0, 6],
             "polygon": [[0, 0], [6, 0], [6, 3], [3, 3], [3, 6], [0, 6]]},
            {"id": "office", "x": [3, 6], "y": [3, 6]},
        ]}],
        "windows": [{"id": "south_window", "floor": "F1", "facade": "South",
                     "span": [1, 2], "z": [1, 2], "room": "hall"}],
    })


def test_l_room_mapping_and_window_identity_survive_face_subdivision():
    geom = _source()
    bg = build_geometry(geom, capability_profile="orthogonal_polygon")
    before = materialize_source_model(geom, bg)
    assert before["validation"]["status"] == "pass"
    assert len(before["spaces"]) == 2
    assert before["openings"][0]["id"] == "south_window"
    # Rendering may triangulate a roof. Both triangles still refer to one source
    # boundary; they never become separate spaces or interior physical walls.
    roof = next(s for s in bg.surfaces if s.stype == "Roof" and len(s.verts) == 4)
    a, b, c, d = roof.verts
    bg.surfaces.remove(roof)
    bg.surfaces.extend([
        Surface("roof_triangle_a", roof.zone, "Roof", [a, b, c], roof.obc),
        Surface("roof_triangle_b", roof.zone, "Roof", [a, c, d], roof.obc),
    ])
    after = materialize_source_model(geom, bg)
    assert after["validation"]["status"] == "pass"
    assert before["spaces"] == after["spaces"]
    assert before["boundaries"] == after["boundaries"]
    assert after["derived"]["surfaces"]["roof_triangle_a"] == after["derived"]["surfaces"]["roof_triangle_b"]


def test_invented_interior_wall_and_missing_source_wall_are_severe():
    geom = _source()
    bg = build_geometry(geom, capability_profile="orthogonal_polygon")
    zone = next(z.zone for z in bg.zone_volumes if z.cell_id == "hall")
    bg.surfaces.append(Surface("fake_wall", zone, "Wall", [
        (1, 0, 0), (1, 3, 0), (1, 3, 3), (1, 0, 3),
    ], "Adiabatic"))
    report = materialize_source_model(geom, bg)["validation"]
    assert report["status"] == "severe"
    assert any(f["code"] == "source.face_without_unique_boundary" and f["surface"] == "fake_wall"
               for f in report["findings"])
    bg.surfaces = [s for s in bg.surfaces if s.stype != "Wall"]
    assert any(f["code"] == "source.boundary_coverage"
               for f in materialize_source_model(geom, bg)["validation"]["findings"])


def test_source_ids_ignore_public_zone_names_and_ring_start():
    geom = _source()
    bg = build_geometry(geom, capability_profile="orthogonal_polygon")
    expected = materialize_source_model(geom, bg)
    changed = copy.deepcopy(geom)
    ring = changed.floors[0].cells[0].polygon
    changed.floors[0].cells[0].polygon = ring[2:] + ring[:2]
    rebuilt = build_geometry(changed, capability_profile="orthogonal_polygon")
    actual = materialize_source_model(changed, rebuilt)
    assert actual["spaces"] == expected["spaces"]
    assert actual["boundaries"] == expected["boundaries"]


def test_sm21_pipeline_writes_source_sidecar_without_changing_legacy_payload(tmp_path):
    from src.agent.pipeline import materialize_kernel_geometry
    from src.agent.geometry.specs import building_geometry_dict

    root = Path(__file__).resolve().parents[1]
    original = root / "case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e/1_correction/correction_geometry_snapped.json"
    geom = CorrectedGeometry.model_validate_json(original.read_text())
    bg, issues = materialize_kernel_geometry(geom, tmp_path)
    assert bg is not None and issues == []
    source = json.loads((tmp_path / "source_model.json").read_text())
    assert len(source["spaces"]) == 14
    assert len(source["openings"]) == 15
    assert source["validation"]["status"] == "pass"
    assert json.loads((tmp_path / "building_geometry.json").read_text()) == building_geometry_dict(bg)


def test_duplicate_or_moved_window_cannot_pass_source_mapping():
    geom = _source()
    bg = build_geometry(geom, capability_profile="orthogonal_polygon")
    bg.windows.append(copy.deepcopy(bg.windows[0]))
    assert any(f["code"] == "source.duplicate_opening"
               for f in materialize_source_model(geom, bg)["validation"]["findings"])
    bg.windows.pop()
    bg.windows[0].verts = [(x + .5, y, z) for x, y, z in bg.windows[0].verts]
    assert any(f["code"] == "source.opening_geometry_changed"
               for f in materialize_source_model(geom, bg)["validation"]["findings"])


def test_source_failure_stops_pipeline_but_preserves_viewable_candidate(tmp_path, monkeypatch):
    import src.agent.geometry as kernel
    from src.agent.pipeline import materialize_kernel_geometry

    geom = _source()
    broken = build_geometry(geom, capability_profile="orthogonal_polygon")
    broken.windows.append(copy.deepcopy(broken.windows[0]))
    monkeypatch.setattr(kernel, "build_geometry", lambda *_args, **_kwargs: broken)
    bg, issues = materialize_kernel_geometry(geom, tmp_path, capability_profile="orthogonal_polygon")
    assert bg is None
    assert any(issue.startswith("source.duplicate_opening") for issue in issues)
    assert (tmp_path / "building_geometry.json").exists()
    assert json.loads((tmp_path / "source_model.json").read_text())["validation"]["status"] == "severe"

    from scripts.tool_scripts import run_stage
    from src.agent.execution import RunPolicy

    monkeypatch.setattr(run_stage, "_load_snapped_with_proof", lambda _run: (geom, None))
    payload, report = run_stage._draw_modelling(tmp_path, RunPolicy(capability_profile="orthogonal_polygon"))
    assert payload == {} and report.blocking()
    viewer = (tmp_path / "manual_review/geometry_viewer.html").read_text()
    assert '"source_model"' in viewer and 'source.duplicate_opening' in viewer
    assert not (tmp_path / "_run/geometry_approval.json").exists()


def test_sm24_historical_three_wall_counterexample():
    from scripts.tool_scripts.diagnose_source_partitions import (
        GROUPS, ROOT, extra_internal_walls, sm24_partition_reference, spaces,
    )
    from src.agent.judge.source_partition import compare_partitions

    old = ROOT / "case_tests/e2e_tests/sm24_anchor/run_2026-06-24_opus_reading"
    geom = CorrectedGeometry.model_validate_json((old / "1_correction/correction_geometry_snapped.json").read_text())
    archived = json.loads((old / "2_modelling/building_geometry.json").read_text())
    reference, id_map = sm24_partition_reference(geom, json.loads(GROUPS.read_text()))
    assert len(extra_internal_walls(archived, id_map)) == 3
    comparison = compare_partitions(spaces(reference), spaces(geom))
    assert comparison["status"] == "severe"
    assert sum(f["code"] == "source_space_split" for f in comparison["findings"]) == 2
    # This explicitly bounded preview retains 11 windows in the full candidate.
    assert len(reference.windows) == 11
    preview = reference.model_copy(update={"windows": []}, deep=True)
    bg = build_geometry(preview, capability_profile="orthogonal_polygon")
    source = materialize_source_model(preview, bg)
    assert len(source["spaces"]) == 8
    assert source["validation"]["status"] == "pass"
