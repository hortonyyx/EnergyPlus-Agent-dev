"""Wall evidence survives 2D/3D assembly without moving or borrowing walls."""
import copy
import hashlib
import json

import pytest
from PIL import Image

from scripts.tool_scripts.render_geometry_viewer import build_viewer_html, wall_properties
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.component_attributes import thickness_record, validate_component_attributes
from src.agent.geometry.plan_assembly import assemble_plan_proposals
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.reader_wall_metadata import (
    bind_wall_metadata, bind_wall_readings, validate_wall_metadata, wall_reading_input,
)
from src.agent.geometry.source_bim import build_source_bim, source_view_geometry
from src.agent.geometry.source_model import _digest
from tests.test_plan_partition import _plan


def _known(target="partition:P_vertical", thickness=.2):
    return dict(target=target, thickness_m=thickness, reference_side="negative_face",
                evidence_status="observed", basis="200 mm dimension at the selected wall",
                source_refs=["plan:wall-dimension"])


@pytest.fixture
def example():
    plan = _plan()
    proposal, metadata = compile_plan_partition(plan, image_size=(100, 100), image_name="plan.png")
    source = build_source_bim(ensure_corrected_geometry(proposal["geometry"]),
                              capability_profile="orthogonal_polygon")
    plan["wall_metadata"] = [_known()]
    return plan, proposal, metadata, source


def test_missing_thickness_is_explicit_unknown_and_known_needs_evidence():
    plan = _plan()
    before = copy.deepcopy(plan)
    rows = validate_wall_metadata(plan)
    assert plan == before
    assert len(rows) == 6  # Four authored footprint sides and two partitions.
    assert all(r["thickness_m"] is None and r["evidence_status"] == "unknown" for r in rows)
    assert all(r["reference_side"] == "unknown" and r["source_refs"] == [] for r in rows)
    plan["wall_metadata"] = [_known()]
    assert next(r for r in validate_wall_metadata(plan) if r["target"] == "partition:P_vertical") == _known()


@pytest.mark.parametrize("change", [
    {"thickness_m": 0}, {"thickness_m": -1}, {"thickness_m": True}, {"thickness_m": float("nan")},
    {"thickness_m": None}, {"evidence_status": "unknown"}, {"source_refs": []},
    {"basis": ""}, {"reference_side": "left"}, {"target": "partition:missing"},
])
def test_invalid_thickness_or_unlocatable_wall_is_rejected(change):
    plan = _plan()
    plan["wall_metadata"] = [{**_known(), **change}]
    with pytest.raises(ValueError):
        validate_wall_metadata(plan)


def test_segment_scope_is_explicit_and_cannot_overlap_whole_partition():
    plan = _plan()
    plan["wall_metadata"] = [_known("partition:P_vertical:0")]
    rows = validate_wall_metadata(plan)
    assert next(r for r in rows if r["target"] == "partition:P_vertical:1")["thickness_m"] is None
    assert all(r["target"] != "partition:P_vertical" for r in rows)
    plan["wall_metadata"].append(_known())
    with pytest.raises(ValueError, match="cannot mix"):
        validate_wall_metadata(plan)


def test_t_junction_binds_each_partial_side_without_changing_geometry(example):
    plan, _, metadata, source = example
    before = copy.deepcopy((plan, metadata, source))
    patch = bind_wall_metadata(source, plan, metadata)
    assert (plan, metadata, source) == before
    known = patch["component_attributes"]
    assert len(known) == 3  # One long side and two separate room sides.
    assert all(r["thickness_m"] == .2 and r["host_scope"] == "boundary" for r in known)
    assert all(r["geometry_effect"] == "none" for r in known)
    assert all(r["offsets_m"] is None for r in patch["wall_references"])
    assert validate_component_attributes(source, known) == known
    boundaries = {r["id"]: r for r in source["boundaries"]}
    assert all({p[0] for p in boundaries[r["boundary_ids"][0]]["vertices"]} == {5.0} for r in known)
    changed = copy.deepcopy(source)
    target = next(b for b in changed["boundaries"] if b["id"] == known[0]["boundary_ids"][0])
    target["vertices"][0][2] += .1
    with pytest.raises(ValueError, match="host changed"):
        validate_component_attributes(changed, known)
    # Existing component-wide edits still reject partial counterpart spreading.
    with pytest.raises(ValueError, match="partial contacts"):
        thickness_record(source, known[0]["boundary_ids"][0], .2, basis="test", source_refs=["test"])


def test_authored_footprint_edge_and_world_side_do_not_follow_ring_orientation(example):
    plan, _, metadata, source = example
    plan["wall_metadata"] = [_known("footprint:0", .3)]
    patch = bind_wall_metadata(source, plan, metadata)
    boundaries = {r["id"]: r for r in source["boundaries"]}
    assert patch["component_attributes"]
    assert all({p[1] for p in boundaries[r["boundary_ids"][0]]["vertices"]} == {8.9}
               for r in patch["component_attributes"])
    plan["wall_metadata"] = [_known()]
    baseline = bind_wall_metadata(source, plan)
    plan["partitions"][0]["points"].reverse()
    assert bind_wall_metadata(source, plan) == baseline


def test_partial_thickness_and_nearby_wall_cannot_be_silently_spread(example):
    plan, _, metadata, source = example
    plan["wall_metadata"] = [_known("partition:P_vertical:0")]
    with pytest.raises(ValueError, match="different wall metadata"):
        bind_wall_metadata(source, plan, metadata)
    plan["wall_metadata"] = [_known()]
    shifted = copy.deepcopy(source)
    for wall in shifted["boundaries"]:
        if wall["geometry_type"] == "wall" and {p[0] for p in wall["vertices"]} == {5.0}:
            for point in wall["vertices"]:
                point[0] += .01
    with pytest.raises(ValueError, match="not fully covered"):
        bind_wall_metadata(shifted, plan, metadata)


def test_floor_assembly_rebinds_duplicate_local_ids_and_retains_values_on_reload(example, tmp_path):
    plan, proposal, metadata, _ = example
    lower, upper = copy.deepcopy(proposal), copy.deepcopy(proposal)
    lower["wall_readings"] = [wall_reading_input(plan, metadata)]
    plan["wall_metadata"][0]["thickness_m"] = .3
    upper["wall_readings"] = [wall_reading_input(plan, metadata)]
    inputs = [dict(proposal=lower, floor_id="L1", z_floor=0),
              dict(proposal=upper, floor_id="L2", z_floor=3.2)]
    before = copy.deepcopy(inputs)
    combined = assemble_plan_proposals(inputs)
    assert inputs == before
    path = tmp_path / "assembled"
    report = export_source_proposal(combined, path)
    assert report["source_geometry_ready"], report
    source = json.loads((path / "source_model.json").read_text(encoding="utf-8"))
    display = source_view_geometry(source)  # Includes source digest validation.
    spaces = {r["id"]: r for r in source["spaces"]}
    boundaries = {r["id"]: r for r in source["boundaries"]}
    for record in source["component_attributes"]:
        floors = {spaces[boundaries[bid]["space_id"]]["floor_id"] for bid in record["boundary_ids"]}
        assert floors in ({"L1"}, {"L2"})
        assert record["thickness_m"] == (.2 if floors == {"L1"} else .3)
    assert len(source["component_attributes"]) == 6
    assert display["source_model"]["component_attributes"] == source["component_attributes"]
    reloaded = json.loads((path / "proposal.json").read_text(encoding="utf-8"))
    assert bind_wall_readings(source, reloaded["wall_readings"])["component_attributes"] == source["component_attributes"]


def test_viewer_shows_known_unknown_and_conflicting_values_with_basis(example):
    plan, _, metadata, source = example
    source.update(bind_wall_metadata(source, plan, metadata))
    source["source_model_sha256"] = _digest({k: v for k, v in source.items() if k != "source_model_sha256"})
    properties = wall_properties(source)
    known = next(k for k, v in properties.items() if v["thickness_m"] == .2)
    unknown = next(v for v in properties.values() if v["thickness_m"] is None)
    assert properties[known]["basis"] == [_known()["basis"]]
    assert properties[known]["reference_side"] == "negative_face"
    assert properties[known]["evidence_status"] == "observed"
    assert unknown["evidence_status"] == "unknown"
    page = build_viewer_html(source_view_geometry(source))
    start = page.index("window.GEO = ") + len("window.GEO = ")
    embedded = json.loads(page[start:page.index(";</script>", start)])
    assert embedded["wall_properties"] == properties
    for record in source["component_attributes"]:
        if known in record["boundary_ids"]:
            record["thickness_m"] = .25
    assert wall_properties(source)[known]["conflict"]
    assert wall_properties(source)[known]["thickness_m"] is None


def test_tool_build_and_assembly_keep_thickness_without_model_calls(tmp_path):
    from scripts.tool_scripts.run_bim_agent import Toolkit
    run = tmp_path / "run"
    (run / "images").mkdir(parents=True)
    image = run / "images/plan.png"
    Image.new("RGB", (100, 100), "white").save(image)
    (run / "inputs.json").write_text(json.dumps({
        "images": {"plan.png": {"size": [100, 100], "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}},
        "scope": "synthetic wall metadata", "only_input": "synthetic image"}), encoding="utf-8")
    toolkit = Toolkit(run)
    plan = _plan()
    plan["wall_metadata"] = [_known()]
    first = toolkit.build_plan("plan.png", json.dumps(plan))
    assert first["source_geometry_ready"], first
    plan["wall_metadata"][0]["thickness_m"] = .3
    second = toolkit.build_plan("plan.png", json.dumps(plan))
    assert second["source_geometry_ready"], second
    floors = []
    for result, fid, z in ((first, "L1", 0), (second, "L2", 3.2)):
        draft = result["plan_input"]
        source = json.loads((run / result["candidate"] / "source_model.json").read_text(encoding="utf-8"))
        assert source["component_attributes"]
        floors.append(dict(draft_id=draft["plan_file"].split("/")[-2],
                           expected_plan_sha256=draft["plan_sha256"], floor_id=fid, z_floor=z,
                           evidence="synthetic separate floor identity"))
    assembled = toolkit.assemble_plans(json.dumps(floors))
    assert assembled["source_geometry_ready"], assembled
    source = json.loads((run / assembled["candidate"] / "source_model.json").read_text(encoding="utf-8"))
    assert sorted(r["thickness_m"] for r in source["component_attributes"]) == [.2, .2, .2, .3, .3, .3]
