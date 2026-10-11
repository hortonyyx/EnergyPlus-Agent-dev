"""Optional legacy source reconstruction evidence; external archives only."""
import copy
import json
from pathlib import Path
import pytest
from tests.archive_paths import archive_path
from tests.test_source_bim import three_rooms
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.geometry.source_bim import build_source_bim
SM21 = archive_path("case_tests/e2e_tests/sm21_anchor/run_2026-07-02_sonnet_flow_e2e")
SM25 = archive_path("AI_agent/logs/experiments/2026-09-09_m0_wall_gap_review_run01")


def test_sm21_preserves_source_rooms_and_all_window_vertices():
    from src.agent.geometry import build_geometry
    from src.agent.geometry.source_model import materialize_source_model
    geom=ensure_corrected_geometry(json.loads((SM21/"1_correction/correction_geometry_snapped.json").read_bytes()))
    old=materialize_source_model(geom,build_geometry(geom))
    source=build_source_bim(geom)
    from src.agent.roles import require_role
    assert source["spaces"] == [{**s, "role": require_role(s["role"])} for s in old["spaces"]]
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
