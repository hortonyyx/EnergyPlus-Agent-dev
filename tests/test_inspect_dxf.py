"""Tests for inspect_dxf.py on a synthetic 天正-style merged DXF.

Builds (with ezdxf) a single model space holding multiple views (two floor plans +
four elevations) with layers split by COMPONENT TYPE (WALL / WINDOW / DOOR) and 图名
title texts — i.e. the structure inspect_dxf must cope with — then asserts the
inspector reports units, classifies component layers, finds the titles, and spatially
separates the views. Proves the toolchain before the real merged DXF arrives."""

from __future__ import annotations

import sys
import hashlib
import json
import subprocess
from pathlib import Path

import ezdxf

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import inspect_dxf as idx  # noqa: E402
from src.agent.judge.gt_manifest import GtExtractionManifestV1, compute_manifest_sha256


def _box(msp, layer, x0, y0, x1, y1):
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
                       dxfattribs={"layer": layer})


def _build_synthetic(path: Path) -> None:
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # millimetres (天正 default)
    for lyr in ("WALL", "WINDOW", "DOOR", "PUB_DIM", "PUB_TEXT"):
        doc.layers.add(lyr)
    msp = doc.modelspace()

    # two floor plans (15000 x 8000 mm), spaced apart in model space
    for i, (ox, title) in enumerate([(0, "一层平面图"), (25000, "二层平面图")]):
        _box(msp, "WALL", ox, 0, ox + 15000, 8000)              # footprint
        msp.add_line((ox + 5000, 0), (ox + 5000, 8000), dxfattribs={"layer": "WALL"})  # partition
        for wx in (ox + 2000, ox + 7000, ox + 12000):           # 3 windows on south wall
            msp.add_line((wx, 0), (wx + 1500, 0), dxfattribs={"layer": "WINDOW"})
        msp.add_line((ox + 500, 0), (ox + 1400, 0), dxfattribs={"layer": "DOOR"})
        msp.add_text(title, dxfattribs={"layer": "PUB_TEXT"}).set_placement((ox + 5000, -1500))

    # four elevations (15000 x 6600 mm), placed below the plans
    for i, (ox, title) in enumerate([(0, "南立面图"), (25000, "北立面图"),
                                     (50000, "东立面图"), (75000, "西立面图")]):
        oy = -20000
        _box(msp, "WALL", ox, oy, ox + 15000, oy + 6600)
        for wx in (ox + 3000, ox + 9000):
            _box(msp, "WINDOW", wx, oy + 4000, wx + 1200, oy + 5800)
        msp.add_text(title, dxfattribs={"layer": "PUB_TEXT"}).set_placement((ox + 5000, oy - 1500))

    doc.saveas(str(path))


def test_inspector_reads_synthetic_tianzheng_dxf(tmp_path):
    p = tmp_path / "merged.dxf"
    _build_synthetic(p)
    rep = idx.inspect(p)

    assert rep["units"] == "mm"
    assert rep["proxy_or_unsupported"] == 0          # plain entities, nothing to explode

    # component layers classified from their names
    kinds = {l["layer"]: l["kind"] for l in rep["layers"]}
    assert kinds["WALL"] == "wall"
    assert kinds["WINDOW"] == "window"
    assert kinds["DOOR"] == "door"

    # all six 图名 titles found
    titles = {t["text"] for t in rep["titles"]}
    assert "一层平面图" in titles and "二层平面图" in titles
    assert "南立面图" in titles and {"北立面图", "东立面图", "西立面图"} <= titles

    # the six views are spatially separated into distinct candidate regions
    assert len(rep["candidate_view_regions"]) >= 6


def test_inspector_flags_units_and_extents(tmp_path):
    p = tmp_path / "merged.dxf"
    _build_synthetic(p)
    rep = idx.inspect(p)
    assert rep["entity_total"] > 0
    # drawing spans the full multi-view layout in mm
    assert rep["extents"][2] - rep["extents"][0] > 80000


def _cli_manifest(path: Path) -> dict:
    selector = {"entity_types": ["LWPOLYLINE"], "layers": ["WALL"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": 1}
    zones = {"entity_types": ["LINE"], "layers": ["WALL"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": 1}
    raw = {"manifest_version": 1, "case": "cli", "source_id": "src", "source_dxf_label": path.name, "source_dxf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "native_units": "mm", "metres_per_unit": 0.001, "geometry_profile": "c2_simple_orthogonal_no_holes", "floors": [{"id": "F1", "name": "F1", "z_floor_m": 0.0, "ceiling_height_m": 3.0}], "views": [{"kind": "plan", "id": "plan-F1", "floor_id": "F1", "clip_box_dxf": {"xmin": -10.0, "ymin": -10.0, "xmax": 15010.0, "ymax": 8010.0}, "world_from_source_m": {"m00": 1.0, "m01": 0.0, "m02": 0.0, "m10": 0.0, "m11": 1.0, "m12": 0.0}, "footprint_boundary": selector, "zone_boundaries": zones, "plan_openings": [], "zone_seeds": [{"zone_id": "Z1", "name": "Z1", "role": "office", "point_world_m": [1.0, 1.0]}, {"zone_id": "Z2", "name": "Z2", "role": "office", "point_world_m": [10.0, 1.0]}], "boundary_reference": "outer_skin", "default_wall_thickness_m": None}], "north_axis": None, "raster_overlays": [], "manifest_sha256": "0" * 64}
    raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    return raw


def test_manifest_inspector_cli_exit_and_json_contract(tmp_path):
    dxf = tmp_path / "merged.dxf"; _build_synthetic(dxf)
    root = Path.cwd(); config = root / "src/configs/judge_gt.yaml"; vg = root / "src/configs/correction.yaml"
    command = [sys.executable, "scripts/tool_scripts/inspect_dxf.py", "--dxf", str(dxf), "--config", str(config), "--vg-config", str(vg)]
    unbound = subprocess.run(command, cwd=root, text=True, capture_output=True)
    assert unbound.returncode == 2 and json.loads(unbound.stdout)["status"] == "UNBOUND"
    manifest = tmp_path / "manifest.json"; manifest.write_text(json.dumps(_cli_manifest(dxf)))
    out = tmp_path / "report.json"
    passed = subprocess.run([*command, "--manifest", str(manifest), "--json-out", str(out)], cwd=root, text=True, capture_output=True)
    assert passed.returncode == 0 and json.loads(passed.stdout)["status"] == "PASS"
    assert json.loads(out.read_text())["status"] == "PASS"
    blocked_payload = _cli_manifest(dxf); blocked_payload["source_dxf_sha256"] = "b" * 64; blocked_payload["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**blocked_payload))
    blocked_manifest = tmp_path / "blocked.json"; blocked_manifest.write_text(json.dumps(blocked_payload))
    blocked = subprocess.run([*command, "--manifest", str(blocked_manifest)], cwd=root, text=True, capture_output=True)
    assert blocked.returncode == 1 and json.loads(blocked.stdout)["status"] == "BLOCKED"
    exists = subprocess.run([*command, "--manifest", str(manifest), "--json-out", str(out)], cwd=root, text=True, capture_output=True)
    assert exists.returncode == 3 and not exists.stdout
    malformed = subprocess.run([*command, "--manifest", str(tmp_path / "missing.json")], cwd=root, text=True, capture_output=True)
    assert malformed.returncode == 3 and not malformed.stdout
