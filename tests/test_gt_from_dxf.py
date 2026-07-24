"""Phase-C build-only CLI checks; all DXF/GT material stays under tmp_path."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import ezdxf
import pytest

from src.agent.judge.gt import load_gt_file
from src.agent.judge.gt_extraction import (ExtractionError, ExtractionInputs,
                                            extract_gt_v3)
import src.agent.judge.gt_extraction as extraction_module
from src.agent.judge.gt_manifest import (GtExtractionManifestV1,
                                          compute_manifest_sha256,
                                          load_gt_tooling_config)
from src.agent.judge.gt_schema import (REPO_ROOT, canonical_gt_v3_bytes,
                                       compute_gt_implementation_hashes,
                                       compute_gt_v3_content_sha256,
                                       GtWorldIntervalV3)
from scripts.tool_scripts import gt_from_dxf as gfd


_CONFIG = REPO_ROOT / "src/configs/judge_gt.yaml"
_VG_CONFIG = REPO_ROOT / "src/configs/correction.yaml"


def _manifest(path: Path, *, north: bool = True, with_elevation: bool = True) -> GtExtractionManifestV1:
    raw = {
        "manifest_version": 1, "case": "synthetic-L", "source_id": "source",
        "source_dxf_label": path.name, "source_dxf_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "native_units": "m", "metres_per_unit": 1.0,
        "geometry_profile": "c2_simple_orthogonal_no_holes",
        "floors": [{"id": "F1", "name": "Floor 1", "z_floor_m": 0.0, "ceiling_height_m": 3.0}],
        "views": [
            {"kind": "plan", "id": "plan-F1", "floor_id": "F1",
             "clip_box_dxf": {"xmin": -1.0, "ymin": -1.0, "xmax": 5.0, "ymax": 4.0},
             "world_from_source_m": {"m00": 1.0, "m01": 0.0, "m02": 0.0, "m10": 0.0, "m11": 1.0, "m12": 0.0},
             "footprint_boundary": {"entity_types": ["LWPOLYLINE"], "layers": ["OUTER"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": 1},
             "zone_boundaries": {"entity_types": ["LWPOLYLINE"], "layers": ["OUTER"], "handles": [], "handle_mode": "all_matching", "min_count": 1, "max_count": 1},
             "plan_openings": [{"opening_id": "O1", "kind": "window", "geometry_mode": "closed_outline_bbox", "span_world_axis": "x", "entities": [{"handle": "30", "subentity_index": None}]}],
             "zone_seeds": [{"zone_id": "Z1", "name": "Room", "role": "office", "point_world_m": [0.5, 0.5]}],
             "boundary_reference": "outer_skin", "default_wall_thickness_m": None},
            *([] if not with_elevation else [{"kind": "elevation", "id": "elev-S", "floor_ids": ["F1"], "projection_surface_key": "south-full",
             "facade_family": "South", "view_kind": "full", "world_along_coverage": None,
             "direction_semantics": "building_axis", "azimuth_deg": None,
             "clip_box_dxf": {"xmin": 9.0, "ymin": -1.0, "xmax": 14.0, "ymax": 4.0},
             "world_along_from_source_m": {"source_axis": "x", "scale": 1.0, "offset": -10.0},
             "world_z_from_source_m": {"source_axis": "y", "scale": 1.0, "offset": 0.0},
             "segment_scope_mode": "all_family_segments", "boundary_entities": [],
             "opening_entities": [{"evidence_id": "E1", "kind": "window", "geometry_mode": "closed_outline_bbox", "entities": [{"handle": "31", "subentity_index": None}]}]}]),
        ],
        "north_axis": {"value_deg": 27.5, "source_view_id": "plan-F1", "source_entity_handle": "30"} if north else None,
        "raster_overlays": [], "manifest_sha256": "0" * 64,
    }
    raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    return GtExtractionManifestV1.model_validate(raw)


def _dxf(path: Path, *, ring=None, plan_box=(1, 0, 2, .1), second_elevation: bool = False) -> None:
    doc = ezdxf.new("R2010"); doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()
    # Handles are deliberately fixed through creation order: A footprint, B plan
    # opening, C elevation evidence.  The L ring exercises concavity/multi-depth.
    msp.add_lwpolyline(ring or [(0, 0), (4, 0), (4, 1), (2, 1), (2, 3), (0, 3)], close=True, dxfattribs={"layer": "OUTER"})
    x0, y0, x1, y1 = plan_box
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True, dxfattribs={"layer": "OPEN"})
    msp.add_lwpolyline([(11, 1), (12, 1), (12, 2), (11, 2)], close=True, dxfattribs={"layer": "ELEV"})
    if second_elevation:
        msp.add_lwpolyline([(21, 1), (22, 1), (22, 2), (21, 2)], close=True, dxfattribs={"layer": "ELEV"})
    doc.saveas(path)


def _write_manifest(path: Path, manifest: GtExtractionManifestV1) -> None:
    path.write_text(json.dumps(manifest.model_dump(mode="json"), sort_keys=True))


def test_build_only_cli_round_trips_l_candidate_and_nonzero_north(tmp_path):
    dxf = tmp_path / "source.dxf"; _dxf(dxf)
    manifest = _manifest(dxf); manifest_path = tmp_path / "manifest.json"; _write_manifest(manifest_path, manifest)
    out = tmp_path / "candidate.json"
    completed = subprocess.run([sys.executable, "scripts/tool_scripts/gt_from_dxf.py", "--dxf", str(dxf), "--manifest", str(manifest_path), "--config", str(_CONFIG), "--vg-config", str(_VG_CONFIG), "--out", str(out)], cwd=REPO_ROOT, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    doc = load_gt_file(out, allow_legacy=False)
    assert doc.north_axis_deg == 27.5 and doc.openings[0].z_interval.lo == 1.0
    assert len(doc.floors[0].boundary_segments) == 6
    assert canonical_gt_v3_bytes(doc) == out.read_bytes()
    assert doc.content_sha256 == compute_gt_v3_content_sha256(doc)


def test_cli_has_no_legacy_write_or_promote_options_and_refuses_existing_output(tmp_path):
    dxf = tmp_path / "source.dxf"; _dxf(dxf)
    manifest_path = tmp_path / "manifest.json"; _write_manifest(manifest_path, _manifest(dxf))
    out = tmp_path / "candidate.json"; out.write_text("already here")
    command = [sys.executable, "scripts/tool_scripts/gt_from_dxf.py", "--dxf", str(dxf), "--manifest", str(manifest_path), "--config", str(_CONFIG), "--vg-config", str(_VG_CONFIG), "--out", str(out)]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    assert result.returncode != 0 and out.read_text() == "already here"
    help_result = subprocess.run([sys.executable, "scripts/tool_scripts/gt_from_dxf.py", "--help"], cwd=REPO_ROOT, text=True, capture_output=True)
    assert "--config" in help_result.stdout and "--vg-config" in help_result.stdout
    assert "--write" not in help_result.stdout and "--promote" not in help_result.stdout and "overwrite" not in help_result.stdout


def _extract(path: Path, manifest: GtExtractionManifestV1):
    tooling = load_gt_tooling_config(REPO_ROOT / "src/configs/judge_gt.yaml", REPO_ROOT / "src/configs/correction.yaml")
    return extract_gt_v3(ExtractionInputs(path, manifest, tooling, compute_gt_implementation_hashes(REPO_ROOT)))


def test_plan_only_z_and_u_hidden_depth_are_preserved(tmp_path):
    dxf = tmp_path / "u.dxf"
    _dxf(dxf, ring=[(0, 0), (4, 0), (4, 3), (3, 3), (3, 1), (1, 1), (1, 3), (0, 3)])
    doc = _extract(dxf, _manifest(dxf, north=False, with_elevation=False))
    assert doc.north_axis_deg is None and doc.north_axis_source_refs == []
    assert doc.openings[0].z_interval is None
    assert any(not segment.visible_intervals and segment.depth > 0 for segment in doc.floors[0].boundary_segments)


def test_opening_no_candidate_and_tie_fail_closed(tmp_path):
    no_candidate = tmp_path / "no-candidate.dxf"; _dxf(no_candidate, plan_box=(1, 1.4, 2, 1.5))
    with pytest.raises(ExtractionError, match="opening_segment_assignment_no_candidate"):
        _extract(no_candidate, _manifest(no_candidate))
    tie = tmp_path / "tie.dxf"
    _dxf(tie, ring=[(0, 0), (4, 0), (4, .6), (2, .6), (2, 3), (0, 3)], plan_box=(2.5, .25, 3.5, .35))
    with pytest.raises(ExtractionError, match="opening_segment_assignment_ambiguous"):
        _extract(tie, _manifest(tie))


def test_opening_host_uses_its_interval_not_the_entire_shared_facade_segment():
    """A shared facade has several candidate zones; a window may still have one host."""
    def zone(zone_id, ring):
        return SimpleNamespace(id=zone_id, polygon=SimpleNamespace(
            exterior=SimpleNamespace(vertices=ring)))
    floor = SimpleNamespace(zones=[
        zone("Z1", [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0], [0.0, 4.0]]),
        zone("Z2", [[5.0, 0.0], [10.0, 0.0], [10.0, 4.0], [5.0, 4.0]]),
    ])
    segment = SimpleNamespace(p1=[0.0, 0.0], p2=[10.0, 0.0])
    # Whole-segment matching sees both rooms, which is valid for a shared facade.
    assert extraction_module._host_zones(floor, segment) == ["Z1", "Z2"]
    assert extraction_module._host_zones_for_opening(
        floor, segment, GtWorldIntervalV3(lo=1.0, hi=2.0)) == ["Z1"]
    # A window genuinely crossing x=5 has no full-span host and remains fail-closed.
    assert extraction_module._host_zones_for_opening(
        floor, segment, GtWorldIntervalV3(lo=4.5, hi=5.5)) == []
    # Overlapping/corrupt zone boundaries produce multiple hosts rather than a guess.
    ambiguous_floor = SimpleNamespace(zones=[*floor.zones,
        zone("Z3", [[0.0, 0.0], [5.0, 0.0], [5.0, 1.0], [0.0, 1.0]])])
    assert extraction_module._host_zones_for_opening(
        ambiguous_floor, segment, GtWorldIntervalV3(lo=1.0, hi=2.0)) == ["Z1", "Z3"]


def test_sm24_converter_output_runs_full_v3_opening_attachment(tmp_path):
    """Regression: G9 preflight is insufficient; run converter output through full v3 build."""
    from tests import test_tarch_converter_p2_geometry as tarch_p2
    from src.agent.judge import tarch_normalize as tarch

    source = tmp_path / "source.dxf"
    source.write_bytes(tarch_p2.SM24_SOURCE.read_bytes())
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    request, plan_view = tarch_p2._sm24_request(sha)
    tooling = tarch_p2.resolve_converter_tooling(tarch_p2.GT_CONFIG, tarch_p2.VG_CONFIG)
    converted = tarch.run_p2_conversion(source, request, plan_view, tooling, tmp_path / "conversion")
    assert converted.augmented_dxf_path and converted.manifest
    doc = extract_gt_v3(ExtractionInputs(converted.augmented_dxf_path, converted.manifest,
                                          tooling, compute_gt_implementation_hashes(REPO_ROOT)))
    assert len(doc.floors) == 1 and len(doc.floors[0].zones) == 8
    assert len(doc.openings) == 14
    zone_ids = {zone.id for zone in doc.floors[0].zones}
    assert all(opening.host_zone_id in zone_ids for opening in doc.openings)


def test_reordered_dxf_entity_iteration_has_identical_canonical_candidate(monkeypatch, tmp_path):
    dxf = tmp_path / "source.dxf"; _dxf(dxf); manifest = _manifest(dxf)
    first = _extract(dxf, manifest)
    real_readfile = extraction_module.ezdxf.readfile
    def reversed_entities(path):
        doc = real_readfile(path)
        doc.modelspace().entity_space.entities.reverse()
        return doc
    monkeypatch.setattr(extraction_module.ezdxf, "readfile", reversed_entities)
    second = _extract(dxf, manifest)
    assert canonical_gt_v3_bytes(first) == canonical_gt_v3_bytes(second)
    assert first.content_sha256 == second.content_sha256


@pytest.mark.parametrize("location", ["default", "gt_sources", "case_data"])
def test_cli_dxf_source_protected_root_is_rejected_before_read(monkeypatch, tmp_path, location):
    fake_repo = tmp_path / "repo"; default = fake_repo / "default-gt"
    protected = {"default": default,
                 "gt_sources": fake_repo / "case_tests/test_baseline/gt_sources/case",
                 "case_data": fake_repo / "case_tests/e2e_tests/case/case_data"}[location]
    source = protected / "source.dxf"; source.parent.mkdir(parents=True)
    _dxf(source); manifest = _manifest(source); manifest_path = tmp_path / "manifest.json"; _write_manifest(manifest_path, manifest)
    monkeypatch.setattr(gfd, "REPO_ROOT", fake_repo)
    monkeypatch.setattr(gfd, "DEFAULT_GT_DIR", default)
    with pytest.raises(ValueError, match="gt_dxf_source_protected_path"):
        gfd.build_candidate(dxf=source, manifest=manifest_path, config=_CONFIG, vg_config=_VG_CONFIG)


def test_build_profile_snapshot_mismatch_fails_closed(monkeypatch, tmp_path):
    dxf = tmp_path / "source.dxf"; _dxf(dxf); manifest = _manifest(dxf)
    real = extraction_module._build_generator
    def mismatched(inputs, *, recorded_tolerances):
        generator = real(inputs, recorded_tolerances=recorded_tolerances)
        changed = generator.tolerances.model_copy(update={"opening_boundary_max_distance_m": 0.399})
        return generator.model_copy(update={"tolerances": changed})
    monkeypatch.setattr(extraction_module, "_build_generator", mismatched)
    with pytest.raises(ExtractionError, match="gt_build_profile_tolerances_mismatch"):
        _extract(dxf, manifest)


def test_elevation_global_assignment_tie_fails_closed(tmp_path):
    dxf = tmp_path / "source.dxf"; _dxf(dxf); manifest = _manifest(dxf)
    doc = _extract(dxf, manifest)
    view = next(view for view in manifest.views if view.kind == "elevation")
    opening = doc.openings[0]
    evidence = [(None, opening.world_along_interval, opening.z_interval, [])]
    duplicate = opening.model_copy(update={"id": "O2"})
    segments = {segment.id: segment for floor in doc.floors for segment in floor.boundary_segments}
    with pytest.raises(ExtractionError, match="elevation_opening_assignment_ambiguous"):
        extraction_module._assign_elevation(evidence, [opening, duplicate], view, segments, 0.4, 1e-9)


def test_elevation_multi_view_z_disagreement_fails_closed(tmp_path):
    dxf = tmp_path / "source.dxf"; _dxf(dxf, second_elevation=True); manifest = _manifest(dxf)
    raw = manifest.model_dump(mode="python")
    extra = next(view for view in raw["views"] if view["kind"] == "elevation").copy()
    extra.update({"id": "elev-S2", "projection_surface_key": "south-full-2"})
    extra["clip_box_dxf"] = {"xmin": 19.0, "ymin": -1.0, "xmax": 24.0, "ymax": 4.0}
    extra["world_along_from_source_m"] = dict(extra["world_along_from_source_m"], offset=-20.0)
    extra["world_z_from_source_m"] = dict(extra["world_z_from_source_m"], offset=0.5)
    extra["opening_entities"] = [dict(extra["opening_entities"][0], evidence_id="E2", entities=[{"handle": "32", "subentity_index": None}])]
    raw["views"].append(extra); raw["manifest_sha256"] = "0" * 64
    raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    changed = GtExtractionManifestV1.model_validate(raw)
    with pytest.raises(ExtractionError, match="elevation_opening_vertical_disagreement"):
        _extract(dxf, changed)
