"""Source geometry must not depend on a solver's surface partition."""
import copy
import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.correction.schema import CorrectedGeometry, WallOpening
from src.agent.geometry.source_bim import build_source_bim, source_view_geometry, _on_wall
from src.agent.geometry.source_model import _digest

ROOT = Path(__file__).resolve().parents[1]
SM21 = ROOT / "case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e"
SM25 = ROOT / "AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_run01"


def three_rooms():
    return CorrectedGeometry.model_validate({
        "schema_version": "2", "footprint_x": [0,6], "footprint_y": [0,6],
        "floors": [{"name":"F1", "z_floor":0, "ceiling_height":3, "cells":[
            {"id":"hall", "x":[0,3], "y":[0,6]},
            {"id":"a", "x":[3,6], "y":[0,3]},
            {"id":"b", "x":[3,6], "y":[3,6]}]}],
        "windows":[{"id":"w", "floor":"F1", "facade":"West", "span":[1,2], "z":[1,2], "room":"hall"}],
        "openings":[{"id":"door", "kind":"door", "space_id":"hall", "other_space_id":"a",
                     "p1":[3,1], "p2":[3,2], "z":[0,2.1], "source_refs":["test:explicit"]}]
    })


def test_long_boundary_contacts_multiple_rooms_without_splitting_or_ep(monkeypatch):
    import src.agent.geometry.build as build
    import src.agent.geometry.split_pairing as pairing
    import src.agent.geometry.to_idf as idf
    import src.validator.interzone as interzone

    def forbidden(*args, **kwargs):
        pytest.fail("source BIM invoked the EP geometry path")

    monkeypatch.setattr(build, "pair_surfaces", forbidden)
    monkeypatch.setattr(pairing, "pair_surfaces", forbidden)
    monkeypatch.setattr(build, "build_geometry", forbidden)
    monkeypatch.setattr(idf, "building_to_idf", forbidden)
    monkeypatch.setattr(interzone, "validate_interzone_surface_pairs", forbidden)
    source = build_source_bim(three_rooms(), capability_profile="orthogonal_polygon")
    assert source["validation"]["status"] == "pass"
    hall_walls = [b for b in source["boundaries"] if b["space_id"] == "hall" and b["geometry_type"] == "wall"]
    assert len(hall_walls) == 4
    shared = next(b for b in hall_walls if b["adjacent_space_ids"] == ["a", "b"])
    assert len(shared["counterpart_ids"]) == 2
    assert source["opening_hosts"]["door"][0] == shared["id"]
    assert len(source["connections"]) == 1
    assert source["connections"][0]["space_ids"] == ["hall", "a"]
    assert not any(k in json.dumps(source) for k in ('"obc"', '"obc_obj"', '"construction"', '"derived"'))
    display = source_view_geometry(source)
    assert len(display["surfaces"]) == 18


@pytest.mark.parametrize("other,p1,p2", [("b",[3,1],[3,2]), (None,[3,1],[3,2]), ("a",[3,2],[3,4])])
def test_wrong_or_partial_door_connection_stays_unbuilt(other,p1,p2):
    geom=three_rooms()
    geom.openings[0] = WallOpening.model_validate({**geom.openings[0].model_dump(), "other_space_id":other,"p1":p1,"p2":p2})
    source=build_source_bim(geom,capability_profile="orthogonal_polygon")
    assert source["validation"]["status"] == "severe"
    assert [o["id"] for o in source["unbuilt_openings"]] == ["door"]
    assert not source["connections"]
    assert len(source["openings"]) == 1
    assert len(source_view_geometry(source)["surfaces"]) == 18


@pytest.mark.parametrize("change", ["floor", "internal", "too_wide", "duplicate", "overlap"])
def test_window_identity_floor_host_and_overlap_are_checked(change):
    geom=three_rooms()
    if change=="floor": geom.windows[0].floor="F2"
    if change=="internal": geom.windows[0].facade="East"
    if change=="too_wide": geom.windows[0].span=[-1,7]
    if change in {"duplicate","overlap"}:
        other=geom.windows[0].model_copy(deep=True)
        if change=="overlap": other.id="w2"
        geom.windows.append(other)
    source=build_source_bim(geom,capability_profile="orthogonal_polygon")
    assert source["validation"]["status"] == "severe"


def test_short_edges_and_layer_contacts_do_not_trigger_ep_minimum():
    geom=three_rooms()
    geom.floors[0].cells[1].y=[0,.065]
    geom.floors[0].cells[2].y=[.065,6]
    geom.openings=[]
    upper=geom.floors[0].model_copy(deep=True)
    upper.name="F2";upper.z_floor=3
    for cell in upper.cells: cell.id+="_up"
    geom.floors.append(upper)
    source=build_source_bim(geom,capability_profile="orthogonal_polygon")
    assert source["validation"]["status"] == "pass"
    assert len(source["spaces"])==6 and len(source["boundaries"])==36
    assert sum(r["space_ids"]==["a","a_up"] for r in source["boundary_relations"])==1


def test_missing_room_and_overlapping_room_block_source_geometry():
    geom=three_rooms();geom.floors[0].cells.pop()
    assert any(f["code"]=="source.floor_coverage" for f in build_source_bim(geom,capability_profile="orthogonal_polygon")["validation"]["findings"])
    geom=three_rooms();geom.floors[0].cells[2].y=[2,6]
    assert any(f["code"]=="source.space_overlap" for f in build_source_bim(geom,capability_profile="orthogonal_polygon")["validation"]["findings"])


def test_display_preserves_full_boundary_area_holes_and_partial_contact_visibility():
    from src.agent.correction.schema import SourceBoundary
    geom=three_rooms()
    source=build_source_bim(geom,capability_profile="orthogonal_polygon")
    display=source_view_geometry(source)
    for boundary in source["boundaries"]:
        if boundary["geometry_type"] != "wall": continue
        b=SourceBoundary.model_validate(boundary)
        full=_on_wall(b.vertices,b).area
        holes=sum(_on_wall(o["vertices"],b).area for o in source["openings"] if b.id in source["opening_hosts"][o["id"]])
        parts=display["display_surface_parts"][b.id]
        displayed=sum(_on_wall(p["verts"],b).area-sum(_on_wall(h,b).area for h in p["holes"]) for p in parts)
        assert displayed == pytest.approx(full-holes)
    assert any(p["duplicate_at_rest"] for parts in display["display_surface_parts"].values() for p in parts)
    assert source["source_model_sha256"]==_digest({k:v for k,v in source.items() if k!="source_model_sha256"})
    changed=copy.deepcopy(source);changed["spaces"][0]["height"]+=1
    with pytest.raises(ValueError,match="digest"): source_view_geometry(changed)


def test_sm21_preserves_source_rooms_and_all_window_vertices():
    from src.agent.geometry import build_geometry
    from src.agent.geometry.source_model import materialize_source_model
    geom=ensure_corrected_geometry(json.loads((SM21/"1_correction/correction_geometry_snapped.json").read_bytes()))
    old=materialize_source_model(geom,build_geometry(geom))
    source=build_source_bim(geom)
    assert source["spaces"]==old["spaces"]
    assert len(source["boundaries"])==84
    assert source["validation"]["status"]=="pass"
    verts=lambda s:{o["id"]:sorted(map(tuple,o["vertices"])) for o in s["openings"]}
    assert verts(source)==verts(old)


def test_sm25_verified_candidate_preserves_openings_and_unresolved_observations():
    from src.agent.output_coordinates import _verify_b5_bundle
    p=SM25/"1_correction/attempts/001"
    geom=ensure_corrected_geometry(json.loads((p/"output.json").read_bytes()))
    with pytest.raises(ValueError,match="requires VerifiedWindowHostProof"):
        build_source_bim(geom,capability_profile="orthogonal_polygon")
    proof=_verify_b5_bundle(raw_output_bytes=(p/"output.json").read_bytes(),
        raw_feature_states_bytes=(p/"feature_states.json").read_bytes(),
        raw_window_resolver_inputs_bytes=(p/"window_resolver_inputs.json").read_bytes(),
        raw_window_hosts_bytes=(p/"window_hosts.json").read_bytes())
    source=build_source_bim(geom,capability_profile="orthogonal_polygon",window_host_proof=proof)
    assert len(source["spaces"])==29 and len(source["boundaries"])==190
    assert len(source["openings"])==60 and len(source["connections"])==29
    assert not source["unbuilt_openings"] and len(source["unsupported"])==2
    assert source["validation"]["status"]=="severe"
    old=json.loads((SM25/"2_modelling/source_model.json").read_bytes())
    verts=lambda s:{o["id"]:sorted(map(tuple,o["vertices"])) for o in s["openings"]}
    assert verts(source)==verts(old)
    geom.floors[0].ceiling_height+=.1
    with pytest.raises(ValueError,match="mutated"):
        build_source_bim(geom,capability_profile="orthogonal_polygon",window_host_proof=proof)


def test_export_source_bim_is_separate_readonly_and_rejects_overwrite(tmp_path):
    from src.agent.execution.source_bim import export_source_bim
    out=tmp_path/"bim"
    report=export_source_bim(SM21,out,capability_profile="rectangular")
    assert report["source_geometry_ready"]
    assert report["drawing_fidelity"]=="not_evaluated"
    assert report["model_calls"]==report["solver_calls"]==0
    assert (out/"viewer.html").exists() and (out/"source_model.json").exists()
    assert not (out/"_run/geometry_approval.json").exists()
    with pytest.raises(FileExistsError): export_source_bim(SM21,out,capability_profile="rectangular")
    bad=export_source_bim(tmp_path/"missing",tmp_path/"failure",capability_profile="rectangular")
    assert bad["status"]=="error" and not bad["source_geometry_ready"]


def test_partition_evaluation_consumes_emitted_spaces_instead_of_correct_input():
    from src.agent.judge.gt import load_gt_document
    from src.agent.judge.partition_evidence import reference_partition
    geom=ensure_corrected_geometry(json.loads((SM21/"1_correction/correction_geometry_snapped.json").read_bytes()))
    source=build_source_bim(geom)
    broken=copy.deepcopy(source["spaces"])
    broken[0]["floor_id"]="missing_floor"
    result=reference_partition(geom,load_gt_document("sm21_anchor"),source_spaces=broken)
    assert result["status"]=="severe"
    assert result["topology_findings"]
    assert broken[0]["floor_id"]=="missing_floor"
