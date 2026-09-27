"""Claims must feed actual edit parameters, not merely decorate arbitrary edits."""
import asyncio
import base64
import io
import json

import pytest
from PIL import Image

from scripts.tool_scripts.run_bim_agent import Toolkit, digest
from src.agent.execution.source_proposal import export_source_proposal
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session
from tests.test_source_proposal import _proposal
from tests.test_proposal_edits import _rectangular_wall_proposal


def setup_run(tmp_path, proposal=None):
    run = _run_with_one_image(tmp_path)
    report = export_source_proposal(proposal or _proposal(), run / "seed")
    assert report["source_geometry_ready"]
    return run, Toolkit(run)


def claim(**changes):
    value = {"candidate": "seed", "objects": [{"kind": "opening", "id": "door"}],
        "basis": "annotation_and_pixels", "reason": "Synthetic labelled vertical chain",
        "sources": [{"image": "plan.png", "box": [0, 0, 12, 8]}],
        "values": {"height": {"type": "dimension_chain", "lengths": [900, 1800, 300],
                    "unit": "mm", "origin_m": 3.0, "direction": -1, "segment": 1}}}
    value.update(changes)
    return value


def adopt(toolkit, data):
    row = toolkit.record_claim(json.dumps(data))
    toolkit.decide_claim(row["id"], "adopted", "Use the declared source evidence")
    return row


def edit(identity, target="door"):
    return {"op": "update_opening", "id": target,
            "changes": {"z": {"claim": identity, "value": "height"}}, "reason": "Apply recorded chain"}


def test_real_parameter_application_and_candidate_provenance_survive_reload(tmp_path):
    run, toolkit = setup_run(tmp_path)
    before = (run / "seed/proposal.json").read_bytes()
    row = adopt(toolkit, claim())
    assert row["resolved_values"]["height"] == [.3, 2.1]
    result = toolkit.revise("seed", json.dumps([edit(row["id"])]))
    assert result["source_geometry_ready"]
    app = result["claim_application"]
    assert app["status"] == "applied" and app["outside_declared_scope"] == []
    assert app["parameters_without_claims"] == []
    assert app["resolved_operations"][0]["changes"]["z"] == [.3, 2.1]
    source = json.loads((run / result["candidate"] / "source_model.json").read_text())
    door = next(row for row in source["openings"] if row["id"] == "door")
    assert sorted({v[2] for v in door["vertices"]}) == [.3, 2.1]
    assert source["generation"]["provenance"]["claim_application"]["claims"][row["id"]]["record"] == row
    assert [(c["kind"], c["id"]) for c in app["changes"]] == [("opening", "door")]
    assert (run / "seed/proposal.json").read_bytes() == before
    persisted = Toolkit(run).claims().status()
    assert persisted["claims"][0]["applied_anywhere"]
    assert persisted["applications"][0] == app


def test_unadopted_retracted_wrong_target_and_stale_claims_leave_failure_records(tmp_path):
    run, toolkit = setup_run(tmp_path)
    row = toolkit.record_claim(json.dumps(claim()))
    with pytest.raises(ValueError, match="adopted"):
        toolkit.revise("seed", json.dumps([edit(row["id"])]))
    toolkit.decide_claim(row["id"], "adopted", "local evidence")
    wrong = {"op": "update_window", "id": "window", "changes": {"z": {"claim": row["id"], "value": "height"}}, "reason": "bad target"}
    with pytest.raises(ValueError, match="targets"):
        toolkit.revise("seed", json.dumps([wrong]))
    good = toolkit.revise("seed", json.dumps([edit(row["id"])]))
    with pytest.raises(ValueError, match="stale"):
        toolkit.revise(good["candidate"], json.dumps([edit(row["id"])]))
    toolkit.decide_claim(row["id"], "retracted", "new conflicting interpretation")
    with pytest.raises(ValueError, match="adopted"):
        toolkit.revise("seed", json.dumps([edit(row["id"])]))
    assert [row["status"] for row in toolkit.claims().status()["applications"]] == ["failed", "failed", "applied", "failed", "failed"]
    assert len(list(run.glob("candidate_*"))) == 1


def test_saved_profile_values_are_used_and_mutated_profiles_rejected(tmp_path):
    run, _ = setup_run(tmp_path)
    path = run / "images/plan.png"
    picture = Image.new("RGB", (12, 8), "white")
    for x in range(12):
        for y in (2, 6):
            picture.putpixel((x, y), (0, 255, 255))
    picture.save(path)
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["images"]["plan.png"]["sha256"] = digest(path)
    (run / "inputs.json").write_text(json.dumps(manifest))
    toolkit = Toolkit(run)
    toolkit.view_profile("plan.png", [0, 0, 12, 8], "y", [0, 255, 255], 0, .5)
    spec = {"type": "image_axis", "image": "plan.png", "axis": "y",
            "anchors": [[0, 3.0], [8, 0.0]], "pixels": [
                {"profile": "profile_001", "candidate": "C01", "at": "peak"},
                {"profile": "profile_001", "candidate": "C02", "at": "peak"}]}
    row = adopt(toolkit, claim(basis="pixels", values={"height": spec}))
    assert row["resolved_values"]["height"] == [.75, 2.25]
    result = toolkit.revise("seed", json.dumps([edit(row["id"])]))
    assert result["claim_application"]["resolved_operations"][0]["changes"]["z"] == [.75, 2.25]
    profile = run / "pixel_profiles/profile_001.json"
    record = json.loads(profile.read_text())
    record["rgb"] = [0, 254, 255]
    profile.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="evidence changed"):
        toolkit.revise("seed", json.dumps([edit(row["id"])]))


@pytest.mark.parametrize("problem", ["nan", "bounds", "object", "image", "unit"])
def test_invalid_claims_never_enter_store(tmp_path, problem):
    _, toolkit = setup_run(tmp_path)
    data = claim()
    if problem == "nan":
        data["values"]["height"]["lengths"][0] = float("nan")
    elif problem == "bounds":
        data["sources"][0]["box"][2] = 13
    elif problem == "object":
        data["objects"][0]["id"] = "absent"
    elif problem == "image":
        data["sources"][0]["image"] = "../secret.png"
    else:
        data["values"]["height"]["unit"] = "cm"
    with pytest.raises(ValueError):
        toolkit.record_claim(json.dumps(data))
    assert toolkit.claims().status()["claims"] == []


def test_valid_claim_with_impossible_geometry_is_not_reported_applied(tmp_path):
    run, toolkit = setup_run(tmp_path)
    row = adopt(toolkit, claim(basis="inference", sources=[], values={
        "height": {"type": "literal", "value": [0, 9], "unit": "m"}}))
    result = toolkit.revise("seed", json.dumps([edit(row["id"])]))
    assert not result["source_geometry_ready"]
    assert result["claim_application"]["status"] == "failed"
    assert (run / result["candidate"] / "application.json").exists()
    delivered = toolkit.delivery("seed", selection_origin="agent_selected")
    assert delivered["adopted_unapplied_claims"] == [row["id"]]
    assert delivered["claim_applications"][0]["status"] == "failed"


def test_shared_wall_move_records_legitimate_hosted_door_and_preserves_other_floor(tmp_path):
    _, toolkit = setup_run(tmp_path, _rectangular_wall_proposal())
    row = adopt(toolkit, claim(objects=[{"kind": "space", "id": x} for x in ("left", "right")],
        basis="pixels", values={"position": {"type": "image_axis", "image": "plan.png", "axis": "x",
            "anchors": [[0, 0], [12, 10]], "pixels": [6]}}))
    result = toolkit.revise("seed", json.dumps([{"op": "move_shared_wall", "space_ids": ["left", "right"],
        "coordinate_m": {"claim": row["id"], "value": "position"}, "reason": "synthetic wall evidence"}]))
    app = result["claim_application"]
    assert app["status"] == "applied" and not app["outside_declared_scope"]
    assert {(row["kind"], row["id"]) for row in app["changes"]} == {("space", "left"), ("space", "right"), ("opening", "between")}


@pytest.mark.parametrize("kind", ["wall", "floor"])
def test_component_thickness_persists_without_changing_geometry(tmp_path, kind):
    run, toolkit = setup_run(tmp_path)
    source = json.loads((run / "seed/source_model.json").read_text())
    boundary = next(b for b in source["boundaries"] if b["geometry_type"] == kind and
                    (b["counterpart_ids"] if kind == "wall" else True))
    row = adopt(toolkit, claim(objects=[{"kind": "boundary", "id": boundary["id"]}],
        basis="declared", sources=[], values={"thickness": {"type": "literal", "value": .2, "unit": "m"}}))
    result = toolkit.revise("seed", json.dumps([{"op": "set_component_thickness", "boundary_id": boundary["id"],
        "thickness_m": {"claim": row["id"], "value": "thickness"}, "basis": "declared overall thickness",
        "reason": "retain building property"}]))
    app = result["claim_application"]
    assert app["status"] == "applied" and not app["changes"]
    assert app["geometry_before_sha256"] == app["geometry_after_sha256"]
    new = json.loads((run / result["candidate"] / "source_model.json").read_text())
    assert len(new["component_attributes"]) == 1
    assert new["component_attributes"][0]["thickness_m"] == .2
    assert len(new["component_attributes"][0]["boundary_ids"]) == (2 if kind == "wall" else 1)
    for field in ("spaces", "boundaries", "openings", "connections"):
        assert new[field] == source[field]


def test_stdio_claim_tools_are_coordinator_only_and_feed_revise(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path)
        async with _server_session(run, readonly=True) as session:
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert not names.intersection({"record_claim", "view_claim_evidence", "decide_claim", "claim_status", "revise_bim"})
        async with _server_session(run, readonly=False) as session:
            row = _json_result(await session.call_tool("record_claim", {"claim_json": json.dumps(claim())}))
            _json_result(await session.call_tool("decide_claim", {"claim_id": row["id"], "disposition": "adopted", "reason": "source chain"}))
            built = _json_result(await session.call_tool("revise_bim", {"candidate": "seed", "operations_json": json.dumps([edit(row["id"])])}))
            assert built["claim_application"]["status"] == "applied"
            status = _json_result(await session.call_tool("claim_status", {}))
            assert status["claims"][0]["applied_anywhere"]
    asyncio.run(scenario())


def test_stdio_claim_returns_exact_bounded_crops_and_can_view_remaining_source(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path)
        original = Image.new("RGB", (12, 8))
        original.putdata([(x * 20, y * 30, 100) for y in range(8) for x in range(12)])
        original.save(run / "images/plan.png")
        manifest = json.loads((run / "inputs.json").read_text())
        manifest["images"]["plan.png"]["sha256"] = digest(run / "images/plan.png")
        (run / "inputs.json").write_text(json.dumps(manifest))
        refs = [{"image": "plan.png", "box": box} for box in
                ([0, 0, 6, 8], [6, 0, 12, 8], [1.2, 2.3, 1.3, 2.4], [3, 4, 9, 8])]
        async with _server_session(run, readonly=False) as session:
            reply = await session.call_tool("record_claim", {"claim_json": json.dumps(claim(sources=refs))})
            row = _json_result(reply)
            assert row["unpreviewed_source_indices"] == [3]
            assert [p["source_index"] for p in row["evidence_previews"]] == [0, 1, 2]
            images = [part for part in reply.content if part.type == "image"]
            assert len(images) == 3
            for part, box, metadata in zip(images, ([0, 0, 6, 8], [6, 0, 12, 8], [1, 2, 2, 3]), row["evidence_previews"]):
                actual = Image.open(io.BytesIO(base64.b64decode(part.data))).convert("RGB")
                expected = original.crop(box)
                assert actual.size == expected.size and actual.tobytes() == expected.tobytes()
                assert metadata["box_original_pixels"] == box
                assert metadata["coordinate_grid"] == {"shown": False}
            assert row["evidence_previews"][2]["claimed_box_original_pixels"] == refs[2]["box"]
            more = await session.call_tool("view_claim_evidence", {"claim_id": row["id"], "source_index": 3, "display_scale": 2})
            metadata = _json_result(more)
            assert metadata["returned_size"] == [12, 8]
            actual = Image.open(io.BytesIO(base64.b64decode(more.content[0].data))).convert("RGB")
            expected = original.crop(refs[3]["box"]).resize((12, 8), Image.Resampling.NEAREST)
            assert actual.tobytes() == expected.tobytes()
            saved = json.loads((run / "claims" / (row["id"] + ".json")).read_text())
            assert "evidence_previews" not in saved and saved["claim"]["sources"] == refs
            assert saved["verification"] == "not_independently_verified"
    asyncio.run(scenario())


def test_claim_preview_preserves_record_and_geometry_and_rejects_changed_original(tmp_path):
    run, toolkit = setup_run(tmp_path)
    row = toolkit.record_claim(json.dumps(claim()))
    before = (run / "seed/source_model.json").read_bytes()
    saved = (run / "claims" / (row["id"] + ".json")).read_bytes()
    toolkit.view_claim_evidence(row["id"])
    corrected = toolkit.record_claim(json.dumps(claim(sources=[{"image": "plan.png", "box": [1, 1, 10, 7]}])))
    toolkit.decide_claim(row["id"], "retracted", "wrong located region")
    toolkit.view_claim_evidence(corrected["id"])
    assert (run / "seed/source_model.json").read_bytes() == before
    assert (run / "claims" / (row["id"] + ".json")).read_bytes() == saved
    assert toolkit.claims().status()["applications"] == []
    with pytest.raises(ValueError, match="coordinator"):
        Toolkit(run, readonly=True).view_claim_evidence(row["id"])
    for index in (-1, 1, True):
        with pytest.raises(ValueError, match="source_index"):
            toolkit.view_claim_evidence(row["id"], index)
    Image.new("RGB", (12, 8), "red").save(run / "images/plan.png")
    with pytest.raises(ValueError, match="image changed"):
        toolkit.view_claim_evidence(row["id"])
    # Even re-admitting changed bytes cannot make an old claim refer to them.
    toolkit.manifest["images"]["plan.png"]["sha256"] = digest(run / "images/plan.png")
    with pytest.raises(ValueError, match="claim original image changed"):
        toolkit.view_claim_evidence(row["id"])


def test_stdio_inferred_claim_without_images_has_no_preview(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path)
        async with _server_session(run, readonly=False) as session:
            reply = await session.call_tool("record_claim", {"claim_json": json.dumps(claim(basis="inference", sources=[]))})
            row = _json_result(reply)
            assert row["evidence_previews"] == [] and row["unpreviewed_source_indices"] == []
            assert not any(part.type == "image" for part in reply.content)
    asyncio.run(scenario())


def test_stdio_whole_image_reference_binds_original_extent_without_guessing_box(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path)
        async with _server_session(run, readonly=False) as session:
            reply = await session.call_tool("record_claim", {"claim_json": json.dumps(
                claim(sources=[{"image": "plan.png"}]))})
            row = _json_result(reply)
            assert row["claim"]["sources"][0]["box"] is None
            assert row["sources"][0] == {"image": "plan.png", "box": [0, 0, 12, 8],
                "size": [12, 8], "sha256": digest(run / "images/plan.png")}
            assert row["resolved_values"]["height"] == [.3, 2.1]
            assert row["evidence_previews"][0]["box_original_pixels"] == [0, 0, 12, 8]
            actual = Image.open(io.BytesIO(base64.b64decode(reply.content[0].data))).convert("RGB")
            with Image.open(run / "images/plan.png") as original:
                assert actual.tobytes() == original.convert("RGB").tobytes()
            assert row["verification"] == "not_independently_verified"
    asyncio.run(scenario())
