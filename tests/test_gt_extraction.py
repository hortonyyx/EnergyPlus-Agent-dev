"""Phase-B manifest-bound plan polygonization checks (all source files are tmp)."""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path
from types import SimpleNamespace

import ezdxf
import pytest

from src.agent.judge.gt_extraction import (ExtractionError, ExtractionInputs,
                                            InspectionInputs,
                                            extract_plan_geometry,
                                            inspect_extraction_inputs)
import src.agent.judge.gt_extraction as extraction_module
from src.agent.judge.gt_manifest import (GtExtractionManifestV1,
                                          compute_manifest_sha256,
                                          load_gt_tooling_config,
                                          validate_manifest_view_clips)
from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
from src.agent.judge.gt_schema import GtEntityRefV3


def _manifest(path: Path, rings: list[list[tuple[float, float]]]) -> GtExtractionManifestV1:
    floors, views = [], []
    for index, ring in enumerate(rings, 1):
        offset = (index - 1) * 20.0
        floors.append({"id": f"F{index}", "name": f"Floor {index}", "z_floor_m": float(index - 1) * 3.0, "ceiling_height_m": 3.0})
        xs, ys = [p[0] + offset for p in ring], [p[1] for p in ring]
        selector = {"entity_types": ["LWPOLYLINE"], "layers": ["OUTER"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": 1}
        zones = {"entity_types": ["LINE"], "layers": ["ZONE"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": 1}
        views.append({"kind": "plan", "id": f"plan-F{index}", "floor_id": f"F{index}",
                      "clip_box_dxf": {"xmin": min(xs) - 1.0, "ymin": min(ys) - 1.0, "xmax": max(xs) + 1.0, "ymax": max(ys) + 1.0},
                      "world_from_source_m": {"m00": 1.0, "m01": 0.0, "m02": -offset, "m10": 0.0, "m11": 1.0, "m12": 0.0},
                      "footprint_boundary": selector, "zone_boundaries": zones, "plan_openings": [],
                      "zone_seeds": [{"zone_id": f"Z{index}a", "name": "A", "role": "office", "point_world_m": [0.5, 0.5]},
                                     {"zone_id": f"Z{index}b", "name": "B", "role": "office", "point_world_m": [3.5, 0.5]}],
                      "boundary_reference": "outer_skin", "default_wall_thickness_m": None})
    raw = {"manifest_version": 1, "case": "synthetic", "source_id": "src", "source_dxf_label": path.name,
           "source_dxf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "native_units": "m", "metres_per_unit": 1.0,
           "geometry_profile": "c2_simple_orthogonal_no_holes", "floors": floors, "views": views,
           "north_axis": None, "raster_overlays": [], "manifest_sha256": "0" * 64}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    return GtExtractionManifestV1.model_validate(raw)


def _dxf(path: Path, ring: list[tuple[float, float]], *, dangle: bool = False, cut: bool = False, bulge: bool = False) -> None:
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("OUTER"); doc.layers.add("ZONE")
    msp = doc.modelspace()
    for index in range(2):
        offset = index * 20.0
        points = [(x + offset, y) for x, y in ring]
        if bulge:
            msp.add_lwpolyline([(x, y, 0.25) for x, y in points], format="xyb", close=True, dxfattribs={"layer": "OUTER"})
        else:
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": "OUTER"})
        msp.add_line((offset + 2.0, 0.0), (offset + 2.0, 1.0), dxfattribs={"layer": "ZONE"})
        if dangle:
            msp.add_line((offset + 2.0, 1.0), (offset + 2.0, 2.0), dxfattribs={"layer": "ZONE"})
        if cut:
            msp.add_line((offset, 0.5), (offset + 1.0, 0.5), dxfattribs={"layer": "ZONE"})
    doc.saveas(path)


def _manifest_from_payload(payload: dict) -> GtExtractionManifestV1:
    payload["manifest_sha256"] = "0" * 64
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        payload["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**payload))
    return GtExtractionManifestV1.model_validate(payload)


@pytest.mark.parametrize("ring", [
    [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (2.0, 1.0), (2.0, 3.0), (0.0, 3.0)],
    [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (3.0, 3.0), (3.0, 1.0), (1.0, 1.0), (1.0, 3.0), (0.0, 3.0)],
])
def test_extracts_two_floor_l_or_u_plan_with_manifest_ancestry(tmp_path, ring):
    path = tmp_path / "source.dxf"; _dxf(path, ring)
    manifest = _manifest(path, [ring, ring])
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    hashes = compute_gt_implementation_hashes(REPO_ROOT)
    result = extract_plan_geometry(ExtractionInputs(path, manifest, tooling, hashes))
    assert len(result.floors) == 2
    assert all(len(floor.zones) == 2 and floor.footprint.interior_rings == [] for floor in result.floors)
    assert result.floors[0].footprint.exterior.vertices == result.floors[1].footprint.exterior.vertices
    assert all(ref.source_id == "src" for floor in result.floors for refs in floor.boundary_edge_sources.values() for ref in refs)


@pytest.mark.parametrize("kwargs,code", [({"dangle": True}, "dxf_inspection_blocked"), ({"bulge": True}, "dxf_inspection_blocked")])
def test_plan_preflight_rejects_residual_or_bulge(tmp_path, kwargs, code):
    ring = [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (2.0, 1.0), (2.0, 3.0), (0.0, 3.0)]
    path = tmp_path / "source.dxf"; _dxf(path, ring, **kwargs)
    manifest = _manifest(path, [ring, ring])
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    hashes = compute_gt_implementation_hashes(REPO_ROOT)
    with pytest.raises(ExtractionError, match=code):
        extract_plan_geometry(ExtractionInputs(path, manifest, tooling, hashes))


def test_inspection_without_manifest_is_unbound(tmp_path):
    ring = [(0.0, 0.0), (4.0, 0.0), (4.0, 3.0), (0.0, 3.0)]
    path = tmp_path / "source.dxf"; _dxf(path, ring)
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    report = inspect_extraction_inputs(InspectionInputs(path, None, tooling, compute_gt_implementation_hashes(REPO_ROOT)))
    assert report.status == "UNBOUND"


def test_manifest_overlap_centerline_hash_unit_and_seed_ambiguity_fail_closed(tmp_path):
    ring = [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (2.0, 1.0), (2.0, 3.0), (0.0, 3.0)]
    path = tmp_path / "source.dxf"; _dxf(path, ring)
    manifest = _manifest(path, [ring, ring])
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    hashes = compute_gt_implementation_hashes(REPO_ROOT)
    for mutate, code in [
        (lambda p: p["views"][1]["clip_box_dxf"].update({"xmin": 0.0, "xmax": 4.0}), "dxf_view_clip_overlap"),
        (lambda p: p["views"][0].update({"boundary_reference": "centerline", "default_wall_thickness_m": 0.24}), "dxf_centerline_unsupported_in_phase_b"),
        (lambda p: p.update({"native_units": "mm", "metres_per_unit": 0.001}), "dxf_unit_mismatch"),
        (lambda p: p["views"][0]["clip_box_dxf"].update({"ymin": 0.0}), "dxf_entity_clip_boundary"),
    ]:
        raw = manifest.model_dump(mode="python"); mutate(raw); changed = _manifest_from_payload(raw)
        report = inspect_extraction_inputs(InspectionInputs(path, changed, tooling, hashes))
        assert report.status == "BLOCKED" and any(issue.code == code for issue in report.issues)
    raw = manifest.model_dump(mode="python"); raw["views"][0]["zone_seeds"].append({"zone_id": "Zextra", "name": "extra", "role": "office", "point_world_m": [0.5, 0.5]})
    with pytest.raises(ExtractionError, match="dxf_zone_seed_ambiguous"):
        extract_plan_geometry(ExtractionInputs(path, _manifest_from_payload(raw), tooling, hashes))
    raw = manifest.model_dump(mode="python"); raw["views"][0]["zone_seeds"][0]["point_world_m"] = [0.0005, 0.5]
    with pytest.raises(ExtractionError, match="dxf_zone_seed_near_boundary"):
        extract_plan_geometry(ExtractionInputs(path, _manifest_from_payload(raw), tooling, hashes))
    raw = manifest.model_dump(mode="python"); raw["source_dxf_sha256"] = "b" * 64; changed = _manifest_from_payload(raw)
    report = inspect_extraction_inputs(InspectionInputs(path, changed, tooling, hashes))
    assert report.status == "BLOCKED" and report.issues[0].code == "dxf_source_hash_mismatch"
    with pytest.raises(ValueError, match="dxf_view_clip_overlap"):
        raw = manifest.model_dump(mode="python"); raw["views"][1]["clip_box_dxf"].update({"xmin": 0.0, "xmax": 4.0})
        validate_manifest_view_clips(_manifest_from_payload(raw), topology_area_tolerance_m2=tooling.tolerances.dxf_topology_area_tolerance_m2)


def test_axis_alignment_tolerance_is_independent_from_node_join_tolerance():
    ref = GtEntityRefV3(source_id="src", view_id="plan", entity_handle="A", subentity_index=None, role="footprint_boundary")
    segments = [((0.0, 0.0), (2.0, 0.005), ref)]
    snapped = extraction_module._snap_segments(segments, node_join_tolerance=0.001, axis_alignment_tolerance=0.01)
    assert snapped[0][1] == (2.0, 0.0)
    with pytest.raises(ExtractionError, match="dxf_nonorthogonal_edge"):
        extraction_module._snap_segments(segments, node_join_tolerance=0.001, axis_alignment_tolerance=0.001)


def test_polygonize_full_classifies_true_dangles_and_true_cut_edges():
    ref = GtEntityRefV3(source_id="src", view_id="plan", entity_handle="A", subentity_index=None, role="footprint_boundary")
    square = [((0.0, 0.0), (1.0, 0.0)), ((1.0, 0.0), (1.0, 1.0)), ((1.0, 1.0), (0.0, 1.0)), ((0.0, 1.0), (0.0, 0.0))]
    dangle = [*square, ((0.0, 0.5), (0.5, 0.5))]
    right_square = [((3.0, 0.0), (4.0, 0.0)), ((4.0, 0.0), (4.0, 1.0)), ((4.0, 1.0), (3.0, 1.0)), ((3.0, 1.0), (3.0, 0.0))]
    cut = [*square, *right_square, ((1.0, 0.0), (3.0, 0.0))]
    for segments, expected in ((dangle, {"dangle_count": 1, "cut_count": 0}), (cut, {"dangle_count": 0, "cut_count": 1})):
        diagnostics = {}
        with pytest.raises(ExtractionError, match="dxf_polygonize_residual"):
            extraction_module._polygonize([(start, end, ref) for start, end in segments], tolerance=0.000001, diagnostics=diagnostics)
        assert {key: diagnostics[key] for key in expected} == expected


def test_proxy_inside_bound_view_is_blocked(tmp_path, monkeypatch):
    ring = [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (2.0, 1.0), (2.0, 3.0), (0.0, 3.0)]
    path = tmp_path / "source.dxf"; _dxf(path, ring)
    manifest = _manifest(path, [ring, ring])
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    monkeypatch.setattr(extraction_module, "DXFTagStorage", object)
    report = inspect_extraction_inputs(InspectionInputs(path, manifest, tooling, compute_gt_implementation_hashes(REPO_ROOT)))
    assert report.status == "BLOCKED" and any(issue.code == "dxf_requires_graphics_export" for issue in report.issues)


def test_proxy_bbox_enclosure_extent_failure_and_outside_info(tmp_path, monkeypatch):
    ring = [(0.0, 0.0), (4.0, 0.0), (4.0, 1.0), (2.0, 1.0), (2.0, 3.0), (0.0, 3.0)]
    path = tmp_path / "source.dxf"; _dxf(path, ring)
    manifest = _manifest(path, [ring, ring])
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    inputs = InspectionInputs(path, manifest, tooling, compute_gt_implementation_hashes(REPO_ROOT))
    monkeypatch.setattr(extraction_module, "DXFTagStorage", object)
    def extent(xmin, ymin, xmax, ymax):
        return SimpleNamespace(has_data=True, extmin=SimpleNamespace(x=xmin, y=ymin), extmax=SimpleNamespace(x=xmax, y=ymax))
    monkeypatch.setattr(extraction_module.bbox, "extents", lambda *_args, **_kwargs: extent(-100.0, -100.0, 100.0, 100.0))
    report = inspect_extraction_inputs(inputs)
    assert report.status == "BLOCKED" and any(issue.code == "dxf_requires_graphics_export" for issue in report.issues)
    monkeypatch.setattr(extraction_module.bbox, "extents", lambda *_args, **_kwargs: extent(100.0, 100.0, 110.0, 110.0))
    report = inspect_extraction_inputs(inputs)
    assert report.status == "PASS" and any(issue.severity == "INFO" and issue.code == "dxf_proxy_outside_bound_views" for issue in report.issues)
    def bad_extent(*_args, **_kwargs):
        raise RuntimeError("unreadable proxy")
    monkeypatch.setattr(extraction_module.bbox, "extents", bad_extent)
    report = inspect_extraction_inputs(inputs)
    assert report.status == "BLOCKED" and any(issue.code == "dxf_proxy_extent_unavailable" for issue in report.issues)
