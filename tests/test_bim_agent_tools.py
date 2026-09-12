"""Offline stdio checks for the small BIM-agent MCP surface."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from PIL import Image

from scripts.tool_scripts.run_bim_agent import (Toolkit, cost_receipt_summary, digest,
                                                review_detail_observation,
                                                terminate_subscription)


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "scripts/tool_scripts/run_bim_agent.py"


def _run_with_one_image(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    images = run / "images"
    images.mkdir(parents=True)
    path = images / "plan.png"
    Image.new("RGB", (12, 8), "white").save(path)
    run.joinpath("inputs.json").write_text(json.dumps({
        "images": {"plan.png": {"size": [12, 8], "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}},
        "scope": "synthetic two-room test input",
        "only_input": "original image bytes and user scope; no GT/history",
    }), encoding="utf-8")
    return run


def _add_image(run: Path, name: str, color: str = "white") -> None:
    path = run / "images" / name
    Image.new("RGB", (12, 8), color).save(path)
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["images"][name] = {"size": [12, 8], "sha256": digest(path)}
    (run / "inputs.json").write_text(json.dumps(manifest), encoding="utf-8")


@asynccontextmanager
async def _server_session(run: Path, *, readonly: bool):
    args = [str(SERVER), "serve", str(run)]
    if readonly:
        args.append("--readonly")
    parameters = StdioServerParameters(command=sys.executable, args=args, cwd=str(ROOT))
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _json_result(result):
    assert not result.isError
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


def _error_text(result) -> str:
    assert result.isError
    return "\n".join(getattr(row, "text", "") for row in result.content)


def _two_room_proposal() -> str:
    return json.dumps({
        "geometry": {
            "schema_version": "2", "footprint_x": [0, 6], "footprint_y": [0, 4],
            "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
                {"id": "left", "role": "office", "x": [0, 3], "y": [0, 4]},
                {"id": "right", "role": "corridor", "x": [3, 6], "y": [0, 4]},
            ]}],
            "windows": [],
            "openings": [{"id": "door", "kind": "door", "space_id": "left", "other_space_id": "right",
                          "p1": [3, 1], "p2": [3, 2], "z": [0, 2.1], "source_refs": ["synthetic"]}],
        },
        "assumptions": ["synthetic fixture"],
        "unresolved": [],
    })


def _two_floor_proposal() -> str:
    proposal = json.loads(_two_room_proposal())
    proposal["geometry"]["floors"].append({
        "name": "F2", "z_floor": 3, "ceiling_height": 3, "cells": [
            {"id": "upper_left", "role": "office", "x": [0, 3], "y": [0, 4]},
            {"id": "upper_right", "role": "corridor", "x": [3, 6], "y": [0, 4]},
        ],
    })
    return json.dumps(proposal)


def test_readonly_stdio_inventory_hash_and_tool_boundary(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=True) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"inputs", "view_image", "pixel_profile", "map_pixels", "map_dimension_chain"} <= tools
            assert "build_bim" not in tools and "review_detail" not in tools
            assert "revise_bim" not in tools and "inspect_candidate" not in tools
            assert "check_openings" not in tools
            assert "finish_bim" not in tools and "overlay_candidate" not in tools
            assert "view_elevation_candidate" not in tools

            inventory = _json_result(await session.call_tool("inputs", {}))
            chain = _json_result(await session.call_tool("map_dimension_chain", {
                "lengths": [540, 4800, 2520, 1600, 540], "origin_m": 10,
                "direction": -1, "expected_total": 10000}))
            assert chain["segments"][3]["span_m"] == [0.54, 2.14]
            assert chain["closure_error_m"] == 0
            assert set(inventory["images"]) == {"plan.png"}
            viewed = await session.call_tool("view_image", {"name":"plan.png", "box":[2, 3, 12, 8]})
            assert viewed.content[0].type == "image"
            metadata = json.loads(viewed.content[1].text)
            assert metadata["box_original_pixels"] == [2, 3, 12, 8]
            assert metadata["returned_size"] == [10, 5]
            assert metadata["original_pixels_per_returned_pixel"] == [1, 1]
            assert inventory["images"]["plan.png"]["sha256"] == hashlib.sha256(
                (run / "images/plan.png").read_bytes()).hexdigest()
            assert (await session.call_tool("view_image", {"name": "plan.png"})).content[0].type == "image"
            for name in ("../outside.png", "ground_truth.png"):
                assert "exact image name" in _error_text(await session.call_tool("view_image", {"name": name}))

            Image.new("RGB", (12, 8), "black").save(run / "images/plan.png")
            assert "input image changed" in _error_text(await session.call_tool("view_image", {"name": "plan.png"}))

    asyncio.run(scenario())


def test_source_elevation_stdio_returns_actual_source_and_changed_height(tmp_path):
    import base64
    import io
    from PIL import ImageChops

    async def scenario():
        run = _run_with_one_image(tmp_path)
        proposal = json.loads(_two_floor_proposal())
        proposal["geometry"]["windows"] = [{
            "id":"south_window", "floor":"F1", "facade":"South", "room":"left",
            "span":[1,2], "z":[0.4,2.2], "source_refs":["synthetic"],
        }]
        async with _server_session(run, readonly=False) as session:
            built = _json_result(await session.call_tool("build_bim", {"proposal_json":json.dumps(proposal)}))
            first = await session.call_tool("view_elevation_candidate", {"candidate":built["candidate"], "facade":"South"})
            metadata = _json_result(first)
            actual = Image.open(io.BytesIO(base64.b64decode(first.content[0].data))).convert("RGB")
            saved = Image.open(run / metadata["elevation_image"]).convert("RGB")
            assert actual.size == saved.size and ImageChops.difference(actual, saved).getbbox() is None
            source = json.loads((run / built["candidate"] / "source_model.json").read_text())
            assert metadata["source_model_sha256"] == source["source_model_sha256"]
            assert "South" == metadata["facade"]
            revised = _json_result(await session.call_tool("revise_bim", {
                "candidate":built["candidate"], "operations_json":json.dumps([{
                    "op":"update_window", "id":"south_window", "changes":{"z":[1,2.6]},
                    "reason":"synthetic height correction", "source_refs":["synthetic"],
                }])}))
            second = await session.call_tool("view_elevation_candidate", {"candidate":revised["candidate"], "facade":"South"})
            updated = _json_result(second)
            assert updated["source_model_sha256"] != metadata["source_model_sha256"]
            assert first.content[0].data != second.content[0].data
            assert "facade" in _error_text(await session.call_tool("view_elevation_candidate", {
                "candidate":revised["candidate"], "facade":"../South"}))

    asyncio.run(scenario())


def test_wall_reference_stdio_calculation_persistence_and_feedback(tmp_path):
    from tests.test_wall_reference import reference, dimension

    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            built = _json_result(await session.call_tool("build_bim", {"proposal_json": _two_room_proposal()}))
            candidate = built["candidate"]
            refs = [reference("west", "space/left/wall/3", [-0.12, 0.12]),
                    reference("shared", "space/left/wall/1", [-0.12, 0.12])]
            d = dimension()
            d["start"]["pixel"], d["end"]["pixel"] = [1, 2], [6, 2]
            checked = _json_result(await session.call_tool("check_wall_dimensions", {
                "candidate": candidate, "references_json": json.dumps(refs), "dimensions_json": json.dumps([d]),
                "include_inventory": True}))
            assert checked["dimension_report"]["dimensions"][0]["residual_m"] == 0
            assert checked["boundary_inventory"]
            await session.call_tool("overlay_candidate", {"candidate": candidate, "image": "plan.png",
                "floor_id": "F1", "x_anchors": [[1, 0], [10, 6]], "y_anchors": [[6, 0], [1, 4]], "basis": "synthetic"})
            result = await session.call_tool("revise_bim", {"candidate": candidate, "operations_json": json.dumps([
                {"op": "set_wall_references", "wall_references": refs, "wall_dimensions": [d], "reason": "synthetic"}])})
            assert not result.isError
            assert any(c.type == "image" for c in result.content)
            revised = _json_result(result)
            source = json.loads((run / revised["candidate"] / "source_model.json").read_text())
            assert len(source["wall_references"]) == 2
            assert source["wall_dimension_report"]["dimensions"][0]["raw_length_m"] == 2.76
            projection = revised["source_image_projections"][0]
            evidence = projection["wall_evidence_projection"]
            assert evidence["scope"]["image_name"] == "plan.png"
            assert [p["pixel"] for p in evidence["endpoints"]] == [[1, 2], [6, 2]]
            assert {p["wall_id"] for p in evidence["endpoints"]} == {"west", "shared"}
            delivered = _json_result(await session.call_tool("finish_bim", {"candidate": revised["candidate"]}))
            assert delivered["source_image_feedback"]["current_source_projections"][0]["wall_evidence_projection"] == evidence
            assert "尺寸证据与所引用墙段的位置对照" in (run / "delivery.html").read_text()
            d["end"]["pixel"] = [12, 2]
            assert "outside original image" in _error_text(await session.call_tool("check_wall_dimensions", {
                "candidate": candidate, "references_json": json.dumps(refs), "dimensions_json": json.dumps([d])}))

    asyncio.run(scenario())


def test_original_coordinate_grid_keeps_crop_and_thumbnail_frame():
    from scripts.tool_scripts.run_bim_agent import coordinate_grid_view
    pic = Image.new("RGB", (800, 400), "white")
    raw = pic.tobytes()
    annotated, meta = coordinate_grid_view(pic, [400, 600, 2000, 1400])
    assert annotated.size == pic.size
    assert pic.tobytes() == raw
    assert annotated.tobytes() != raw
    assert {"original_pixel": 1000, "display_pixel": 300} in meta["ticks"]["x"]
    assert {"original_pixel": 1200, "display_pixel": 300} in meta["ticks"]["y"]


def test_upper_floor_opening_diagnostic_reaches_agent_and_preserves_declared_door(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        proposal = json.loads(_two_floor_proposal())
        proposal["geometry"]["openings"].append({
            "id": "upper_door", "kind": "door", "space_id": "upper_left",
            "other_space_id": "upper_right", "p1": [3, 1], "p2": [3, 2],
            "z": [0, 2.1], "source_refs": ["synthetic upper floor aperture"],
        })
        async with _server_session(run, readonly=False) as session:
            built = _json_result(await session.call_tool("build_bim", {"proposal_json": json.dumps(proposal)}))
            assert built["counts"]["unbuilt_openings"] == 1
            inspected = _json_result(await session.call_tool("inspect_candidate", {"candidate": built["candidate"]}))
            diagnostic = inspected["source_validation"]["findings"][0]["height_host_diagnostic"]
            assert diagnostic["actual_opening_z_bounds_m"] == [0, 2.1]
            assert {tuple(row["expected_z_bounds_m"]) for row in diagnostic["declared_space_bounds"]} == {(3, 6)}
            revised = _json_result(await session.call_tool("revise_bim", {
                "candidate": built["candidate"], "operations_json": json.dumps([{
                    "op": "update_opening", "id": "upper_door", "changes": {"z": [3, 5.1]},
                    "reason": "synthetic correction to absolute floor coordinates",
                    "source_refs": ["synthetic upper floor aperture"],
                }]),
            }))
            assert revised["source_geometry_ready"]
            assert revised["counts"]["unbuilt_openings"] == 0
            assert revised["counts"]["connections"] == 2
            source = json.loads((run / revised["candidate"] / "source_model.json").read_text())
            assert {o["id"] for o in source["openings"]} == {"door", "upper_door"}

    asyncio.run(scenario())


def test_delivery_keeps_numeric_contradiction_and_calibration_warning_with_empty_notes(tmp_path):
    from tests.test_wall_reference import reference, dimension
    from src.agent.geometry.proposal_edits import apply_proposal_edits
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    proposal = json.loads(_two_room_proposal())
    proposal["assumptions"], proposal["unresolved"] = [], []
    proposal["wall_references"] = [reference("west", "space/left/wall/3", [0, 0.24])]
    d = dimension(value=240)
    d["end"]["wall_id"] = "west"
    d["start"]["pixel"], d["end"]["pixel"] = [1, 2], [2, 2]
    proposal["wall_dimensions"] = [d]
    built = toolkit.build(proposal)
    assert built["source_geometry_ready"]
    toolkit.project_overlay(built["candidate"], "plan.png", "F1", [[0,0],[10,6]], [[0,4],[7,0]],
                            "synthetic inconsistent scales", trigger_action="overlay_candidate")
    result = toolkit.delivery(built["candidate"], selection_origin="agent_selected")
    assert result["generation"]["unresolved"] == []
    assert result["wall_dimension_report"]["findings"][0]["code"] == "same_wall_endpoint_order"
    assert result["source_image_feedback"]["current_source_projections"][0]["calibration_warnings"]
    page = (run / "delivery.html").read_text()
    assert "-0.48" in page and ("cross-axis" in page.lower() or "disagree" in page)
    # A new candidate replaces only the evidence, not the source objects.
    d["start"]["side"], d["end"]["side"] = "negative", "positive"
    updated = apply_proposal_edits(proposal, [{"op":"set_wall_references", "wall_references":proposal["wall_references"],
                                             "wall_dimensions":[d], "reason":"synthetic side correction"}])
    new = toolkit.build(updated)
    current = toolkit.delivery(new["candidate"], selection_origin="agent_selected")
    assert current["wall_dimension_report"]["findings"] == []
    assert current["source_image_feedback"]["current_source_projections"] == []
    assert len(current["source_image_feedback"]["old_source_projections"]) == 1


def test_detail_review_uses_isolated_image_only_workspace_and_parent_receipt(tmp_path):
    run = _run_with_one_image(tmp_path)
    _add_image(run, "unselected.png", "black")
    manifest = json.loads((run / "inputs.json").read_text())
    manifest.update(scope="PARENT_SCOPE_MUST_NOT_LEAK", seed={"secret":"PARENT_SEED_MUST_NOT_LEAK"},
                    historical_candidate="PARENT_HISTORY_MUST_NOT_LEAK")
    (run / "inputs.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run / "candidate_01").mkdir()
    (run / "candidate_01" / "proposal.json").write_text("PARENT_CANDIDATE_MUST_NOT_LEAK")
    calls = []

    def fake_subscription(mcp_run, prompt, **kwargs):
        calls.append((mcp_run, prompt, kwargs))
        assert kwargs["model"] == "haiku" and kwargs["readonly"]
        assert kwargs["name"] == "detail_01"
        assert kwargs["log_run"] == run
        assert kwargs["receipt_context"]["observation_source"]["run"] == "detail_01"
        return {"actual_model":"offline-haiku", "returncode":0,
                "result":{"is_error":False, "result":"observed mark", "total_cost_usd":0.75}}

    response = review_detail_observation(Toolkit(run), "What mark is visible at [1,2,3,4]?", ["plan.png"],
                                         invoke=fake_subscription)
    child, prompt, _ = calls[0]
    assert child == run / "detail_01"
    assert prompt == "Images: ['plan.png']\nQuestion: What mark is visible at [1,2,3,4]?"
    assert response["completed"] and response["observation_source"]["input_sha256"] == digest(child / "inputs.json")
    assert response["observation_source"]["images"]["plan.png"] == digest(child / "images/plan.png")
    assert set(json.loads((child / "inputs.json").read_text())["images"]) == {"plan.png"}
    assert (child / "question.txt").read_text() == "What mark is visible at [1,2,3,4]?"
    assert not (child / "images/unselected.png").exists()
    child_text = "\n".join(path.read_text(errors="ignore") for path in child.rglob("*") if path.is_file())
    for secret in ("PARENT_SCOPE_MUST_NOT_LEAK", "PARENT_SEED_MUST_NOT_LEAK",
                   "PARENT_HISTORY_MUST_NOT_LEAK", "PARENT_CANDIDATE_MUST_NOT_LEAK"):
        assert secret not in child_text

    async def readonly_boundary():
        async with _server_session(child, readonly=True) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert "review_detail" not in tools and "build_bim" not in tools
            inventory = _json_result(await session.call_tool("inputs", {}))
            assert set(inventory["images"]) == {"plan.png"}
            assert inventory["images"]["plan.png"]["sha256"] == digest(child / "images/plan.png")

    asyncio.run(readonly_boundary())
    # subscription writes detail receipts in the parent, so the root summary sees
    # this invocation once and does not recurse into the isolated child workspace.
    (run / "agent_receipt.json").write_text(json.dumps({"result":{"total_cost_usd":0.5}}))
    (run / "detail_01_receipt.json").write_text(json.dumps({"result":{"total_cost_usd":0.75}}))
    receipts, costs = cost_receipt_summary(run)
    assert len(receipts) == 2 and costs == {"estimated_cost_usd":1.25,
                                             "cost_receipts_complete":True,
                                             "reported_partial_cost_usd":1.25}


def test_detail_review_refuses_budget_exhaustion_or_too_little_time_without_calling(tmp_path):
    run = _run_with_one_image(tmp_path)
    manifest = json.loads((run / "inputs.json").read_text())
    manifest["deadline_epoch"] = time.time() + 50
    (run / "inputs.json").write_text(json.dumps(manifest), encoding="utf-8")
    invoked = False

    def fake_subscription(*args, **kwargs):
        nonlocal invoked
        invoked = True
        return {}

    response = review_detail_observation(Toolkit(run), "Check the visible mark.", ["plan.png"],
                                         invoke=fake_subscription)
    assert response["completed"] is False and "insufficient remaining budget" in response["error"]
    assert not invoked and not (run / "detail_01").exists()

    manifest.pop("deadline_epoch")
    (run / "inputs.json").write_text(json.dumps(manifest), encoding="utf-8")
    for number in (1, 2):
        (run / f"detail_{number:02d}_request.json").write_text("{}")
    response = review_detail_observation(Toolkit(run), "Check the visible mark.", ["plan.png"],
                                         invoke=fake_subscription)
    assert response == {"error":"local review budget exhausted", "completed":False}
    assert not invoked


def test_detail_review_keeps_partial_text_but_marks_timeout_or_error_unfinished(tmp_path):
    run = _run_with_one_image(tmp_path)

    def interrupted_subscription(*args, **kwargs):
        return {"timed_out":True, "returncode":1,
                "result":{"is_error":False, "result":"partial observation"}}

    response = review_detail_observation(Toolkit(run), "Check the visible mark.", ["plan.png"],
                                         invoke=interrupted_subscription)
    assert response["result"] == "partial observation"
    assert response["timed_out"] and response["completed"] is False
    assert response["is_error"] is False

    empty_run = _run_with_one_image(tmp_path / "empty")
    response = review_detail_observation(Toolkit(empty_run), "Check the visible mark.", ["plan.png"],
                                         invoke=lambda *args, **kwargs: {"returncode":1})
    assert response["result"] == "No completed answer"
    assert response["is_error"] and response["completed"] is False


def test_normal_stdio_builds_candidate_and_returns_plan_image(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert "build_bim" in tools and "view_candidate" in tools
            built = _json_result(await session.call_tool("build_bim", {"proposal_json": _two_room_proposal()}))
            assert built["candidate"] == "candidate_01"
            assert built["source_geometry_ready"]
            assert built["source_image_projections"] == [] and built["projection_errors"] == []
            viewed = await session.call_tool("view_candidate", {"candidate": built["candidate"], "floor_id": "F1"})
            assert not viewed.isError
            assert viewed.content[0].type == "image"
            assert viewed.content[0].mimeType == "image/png"
            assert (run / "candidate_01" / "source_model.json").exists()
            original = (run / "candidate_01" / "proposal.json").read_bytes()
            revised = _json_result(await session.call_tool("revise_bim", {
                "candidate": "candidate_01",
                "operations_json": json.dumps([{"op":"reflect", "axis":"x", "reason":"synthetic frame reflection"}]),
            }))
            assert revised["candidate"] == "candidate_02"
            assert revised["source_geometry_ready"]
            assert (run / "candidate_01" / "proposal.json").read_bytes() == original
            inspected = _json_result(await session.call_tool("inspect_candidate", {"candidate":"candidate_02"}))
            assert inspected["proposal"]["geometry"]["floors"][0]["cells"][0]["x"] == [3, 6]
            review = {"floor_id":"F1", "kind":"door", "image":"plan.png", "coverage":"complete",
                      "marks":[{"mark_id":"m1", "box":[1,1,6,7], "opening_ids":["door"],
                                "space_ids":["left","right"], "basis":"visible", "note":"synthetic aperture"}]}
            before = (run / "candidate_02/source_model.json").read_bytes()
            checked = _json_result(await session.call_tool("check_openings", {
                "candidate":"candidate_02", "review_json":json.dumps(review)}))
            assert checked["drawing_fidelity"] == "not_evaluated"
            saved = json.loads((run / checked["review_file"]).read_text())
            assert saved["observations"] == review
            assert (run / "candidate_02/source_model.json").read_bytes() == before
            assert not checked["findings"]
            assert "opening_reviews/review_001.json" == checked["review_file"]
            empty_north = _json_result(await session.call_tool("check_openings", {
                "candidate": "candidate_02", "review_json": json.dumps({
                    "floor_id": "F1", "kind": "window", "image": "plan.png",
                    "facade": "North", "coverage": "complete", "marks": []})}))
            assert empty_north["review_scope"]["facade"] == "North"
            assert empty_north["model_opening_ids"] == []

            overlaid = await session.call_tool("overlay_candidate", {
                "candidate":"candidate_02", "image":"plan.png", "floor_id":"F1",
                "x_anchors":[[0,0],[11,6]], "y_anchors":[[7,0],[0,4]],
                "basis":"synthetic image extent represents the building footprint",
                "box":[1,1,11,7]})
            assert not overlaid.isError
            assert overlaid.content[0].type == "image"
            overlay_info = json.loads(overlaid.content[1].text)
            assert overlay_info["box_original_pixels"] == [1,1,11,7]
            assert overlay_info["returned_size"] == [10,6]
            assert overlay_info["drawing_fidelity"] == "not_evaluated"
            assert (run / overlay_info["overlay_image"]).is_file()
            assert (run / "candidate_02/source_model.json").read_bytes() == before

            finished = _json_result(await session.call_tool("finish_bim", {"candidate":"candidate_02"}))
            assert finished["candidate"] == "candidate_02"
            assert finished["selection_origin"] == "agent_selected"
            assert finished["drawing_fidelity"] == "not_evaluated"
            assert (run / "delivery.html").is_file()
            assert "逐立面回查范围" in (run / "delivery.html").read_text()
            north_windows = next(s for s in finished["facade_review_scopes"]
                                 if s["floor_id"] == "F1" and s["facade"] == "North" and s["kind"] == "window")
            assert north_windows["review_status"] == "consistent_with_supplied_observations"
            all_windows = next(s for s in finished["opening_review_scopes"]
                               if s["floor_id"] == "F1" and s["kind"] == "window")
            assert all_windows["review_status"] == "partial"
            assert json.loads((run / "delivery.json").read_text())["source_model_sha256"] == checked["source_model_sha256"]
            assert json.loads((run / "delivery_selection.json").read_text())["candidate"] == "candidate_02"

            # Move the shared wall through the public MCP path. Both room sides
            # and the door on that wall move, while prior candidates/reviews stay.
            moved = _json_result(await session.call_tool("revise_bim", {
                "candidate": "candidate_02", "operations_json": json.dumps([{
                    "op": "move_shared_wall", "space_ids": ["left", "right"],
                    "coordinate_m": 3.5, "reason": "synthetic observed partition",
                    "source_refs": ["plan.png: synthetic wall observation"]}])}))
            assert moved["candidate"] == "candidate_03" and moved["source_geometry_ready"]
            assert (run / "candidate_02/source_model.json").read_bytes() == before
            moved_proposal = json.loads((run / "candidate_03/proposal.json").read_text())
            rooms = {cell["id"]: cell for cell in moved_proposal["geometry"]["floors"][0]["cells"]}
            assert rooms["left"]["x"] == [3.5, 6] and rooms["right"]["x"] == [0, 3.5]
            assert moved_proposal["geometry"]["openings"][0]["p1"][0] == 3.5
            assert moved_proposal["geometry"]["openings"][0]["p2"][0] == 3.5
            moved_delivery = _json_result(await session.call_tool("finish_bim", {"candidate":"candidate_03"}))
            assert moved_delivery["source_model_sha256"] != finished["source_model_sha256"]
            assert len(moved_delivery["stale_reviews"]) == 2
            assert all(scope["review_status"] == "not_reviewed"
                       for scope in moved_delivery["opening_review_scopes"])

    asyncio.run(scenario())


def test_registered_source_overlay_feedback_reuses_only_explicit_image_floor_calibrations(tmp_path):
    from src.agent.execution.source_proposal import export_source_proposal

    async def scenario():
        run = _run_with_one_image(tmp_path)
        _add_image(run, "upper.png", "black")
        proposal_json = _two_floor_proposal()
        export_source_proposal(json.loads(proposal_json), run / "seed")
        async with _server_session(run, readonly=False) as session:
            # A model chooses this frame explicitly on a recovered seed.  Nothing
            # registers the other image/floor until the model calls this tool.
            seed_overlay = await session.call_tool("overlay_candidate", {
                "candidate": "seed", "image": "plan.png", "floor_id": "F1",
                "x_anchors": [[0, 0], [11, 6]], "y_anchors": [[7, 0], [0, 4]],
                "basis": "synthetic seed frame"})
            assert not seed_overlay.isError and seed_overlay.content[0].type == "image"
            seed_info = json.loads(seed_overlay.content[1].text)
            assert seed_info["registered_calibration"]["calibration_id"] == "calibration_001"
            seed_overlay_path = run / seed_info["overlay_image"]
            seed_overlay_bytes = seed_overlay_path.read_bytes()
            seed_overlay_metadata = (seed_overlay_path.with_suffix(".json")).read_bytes()

            # build_bim retains its structured JSON and now returns the actual
            # automatic overlay image with the source-bound projection metadata.
            first_call = await session.call_tool("build_bim", {"proposal_json": proposal_json})
            first = _json_result(first_call)
            assert first["source_image_projections"], first["projection_errors"]
            assert first["projection_errors"] == []
            assert first_call.content[0].type == "image"
            first_projection = first["source_image_projections"]
            assert len(first_projection) == 1
            assert first_projection[0]["automatic_projection"] is True
            assert first_projection[0]["trigger_action"] == "build_bim"
            assert first_projection[0]["anchors"] == {"x": [[0.0, 0.0], [11.0, 6.0]],
                                                        "y": [[7.0, 0.0], [0.0, 4.0]]}
            assert first_projection[0]["reused_calibration"]["registered_by_candidate"] == "seed"
            assert first_projection[0]["source_model_sha256"] == json.loads(
                (run / "candidate_01/source_model.json").read_text())["source_model_sha256"]
            first_projection_bytes = (run / first_projection[0]["overlay_image"]).read_bytes()

            upper_overlay = await session.call_tool("overlay_candidate", {
                "candidate": "candidate_01", "image": "upper.png", "floor_id": "F2",
                "x_anchors": [[0, 0], [11, 6]], "y_anchors": [[7, 0], [0, 4]],
                "basis": "synthetic upper floor frame"})
            upper_info = json.loads(upper_overlay.content[1].text)
            assert upper_info["registered_calibration"]["calibration_id"] == "calibration_002"

            # A changed wall creates fresh source-bound views.  The old seed and
            # first-candidate projection artifacts stay byte-for-byte unchanged.
            second = _json_result(await session.call_tool("revise_bim", {
                "candidate": "candidate_01", "operations_json": json.dumps([{
                    "op": "move_shared_wall", "space_ids": ["left", "right"],
                    "coordinate_m": 3.5, "reason": "synthetic overlay correction",
                    "source_refs": ["plan.png: synthetic observation"]}])}))
            assert len(second["source_image_projections"]) == 2
            second_by_floor = {row["floor_id"]: row for row in second["source_image_projections"]}
            assert second_by_floor["F1"]["reused_calibration"]["calibration_id"] == "calibration_001"
            assert second_by_floor["F2"]["reused_calibration"]["calibration_id"] == "calibration_002"
            assert (run / second_by_floor["F1"]["overlay_image"]).read_bytes() != first_projection_bytes
            assert seed_overlay_path.read_bytes() == seed_overlay_bytes
            assert seed_overlay_path.with_suffix(".json").read_bytes() == seed_overlay_metadata

            # Recalibrating one exact image/floor supersedes only that pair.
            replaced = await session.call_tool("overlay_candidate", {
                "candidate": "candidate_02", "image": "plan.png", "floor_id": "F1",
                "x_anchors": [[0, 0], [10, 6]], "y_anchors": [[7, 0], [0, 4]],
                "basis": "synthetic corrected F1 frame"})
            assert json.loads(replaced.content[1].text)["registered_calibration"]["calibration_id"] == "calibration_003"
            third = _json_result(await session.call_tool("revise_bim", {
                "candidate": "candidate_02", "operations_json": json.dumps([{
                    "op": "reflect", "axis": "x", "reason": "synthetic new source"}])}))
            third_by_floor = {row["floor_id"]: row for row in third["source_image_projections"]}
            assert third_by_floor["F1"]["reused_calibration"]["calibration_id"] == "calibration_003"
            assert third_by_floor["F1"]["anchors"]["x"] == [[0.0, 0.0], [10.0, 6.0]]
            assert third_by_floor["F2"]["reused_calibration"]["calibration_id"] == "calibration_002"

            # Hash validation happens through Toolkit.image_path before a failed
            # explicit projection can affect the saved source candidate.
            before_failure = (run / "candidate_03/source_model.json").read_bytes()
            Image.new("RGB", (12, 8), "red").save(run / "images/plan.png")
            failed = await session.call_tool("overlay_candidate", {
                "candidate": "candidate_03", "image": "plan.png", "floor_id": "F1",
                "x_anchors": [[0, 0], [11, 6]], "y_anchors": [[7, 0], [0, 4]],
                "basis": "must reject changed input"})
            assert "input image changed" in _error_text(failed)
            assert (run / "candidate_03/source_model.json").read_bytes() == before_failure

            # Automatic reuse reports the same input failure, but still returns
            # the candidate and the unaffected F2 image instead of hiding feedback.
            fourth_call = await session.call_tool("build_bim", {"proposal_json": proposal_json})
            fourth = _json_result(fourth_call)
            assert fourth["candidate"] == "candidate_04"
            assert len(fourth["source_image_projections"]) == 1
            assert fourth["source_image_projections"][0]["floor_id"] == "F2"
            assert len(fourth["projection_errors"]) == 1
            assert fourth["projection_errors"][0]["floor_id"] == "F1"
            assert "input image changed" in fourth["projection_errors"][0]["error"]
            assert fourth_call.content[0].type == "image"
            delivery = _json_result(await session.call_tool("finish_bim", {"candidate": "candidate_04"}))
            feedback = delivery["source_image_feedback"]
            assert feedback["current_source_projections"][0]["floor_id"] == "F2"
            assert feedback["old_source_projections"]
            assert feedback["floors_without_registered_views"] == []
            assert feedback["calibration_independently_verified"] is False
            assert delivery["drawing_fidelity"] == "not_evaluated"

    asyncio.run(scenario())


def test_recovery_imports_only_proposal_and_rebuilds_production_checks(tmp_path, monkeypatch):
    from scripts.tool_scripts import run_bim_agent as runner
    from src.agent.execution.source_proposal import export_source_proposal
    source = tmp_path / "old_candidate"
    proposal = json.loads(_two_room_proposal())
    export_source_proposal(proposal, source)
    old_report = source / "report.json"
    # An old directory may later acquire evaluator output. It must not enter
    # a generating model's new recovery workspace.
    old_report.write_text(json.dumps({"independent_evaluation":"DO_NOT_EXPOSE"}))
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (12, 8), "white").save(images / "plan.png")

    def offline_subscription(run, prompt, **kwargs):
        manifest = json.loads((run / "inputs.json").read_text())
        assert manifest["input_mode"] == "saved_candidate_recovery"
        assert json.loads((run / "seed/proposal.json").read_text()) == proposal
        assert "DO_NOT_EXPOSE" not in (run / "seed/report.json").read_text()
        assert json.loads((run / "seed/report.json").read_text())["source_geometry_ready"]
        receipt = {"elapsed_seconds": 0, "result":{"is_error":False,"total_cost_usd":0}}
        runner.dump(run / "agent_receipt.json", receipt)
        return receipt

    monkeypatch.setattr(runner, "subscription", offline_subscription)
    args = SimpleNamespace(images=images, out=tmp_path / "recovery", scope="synthetic recovery",
                           timeout=30, resume_candidate=source)
    runner.run_experiment(args)
    assert json.loads(old_report.read_text())["independent_evaluation"] == "DO_NOT_EXPOSE"
    delivery = json.loads((args.out / "delivery.json").read_text())
    assert delivery["candidate"] == "seed"
    assert delivery["selection_origin"] == "latest_saved_fallback_not_agent_selected"
    assert delivery["drawing_fidelity"] == "not_evaluated"
    assert "DO_NOT_EXPOSE" not in json.dumps(delivery)


def _ended_or_zombie(pid: int) -> bool:
    """A zombie has stopped executing; init will reap an orphan shortly."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True,
                           text=True, check=False).stdout.strip()
    return state.startswith("Z")


def test_interrupted_run_keeps_candidate_and_labels_delivery_incomplete(tmp_path, monkeypatch):
    from scripts.tool_scripts import run_bim_agent as runner
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (12, 8), "white").save(images / "plan.png")

    def interrupted_subscription(run, prompt, **kwargs):
        runner.Toolkit(run).build(json.loads(_two_room_proposal()))
        receipt = {"elapsed_seconds": 2, "returncode": 1,
                   "result":{"is_error":True,"total_cost_usd":0,
                             "result":"You've hit your session limit"}}
        runner.dump(run / "agent_receipt.json", receipt)
        return receipt

    monkeypatch.setattr(runner, "subscription", interrupted_subscription)
    args = SimpleNamespace(images=images, out=tmp_path / "interrupted", scope="synthetic run",
                           timeout=30, resume_candidate=None)
    runner.run_experiment(args)
    delivery = json.loads((args.out / "delivery.json").read_text())
    summary = json.loads((args.out / "summary.json").read_text())
    assert summary["has_viewable_candidate"] and not summary["agent_response_completed"]
    assert delivery["candidate"] == "candidate_01"
    assert delivery["generation_status"]["state"] == "interrupted"
    assert delivery["generation_status"]["error"] == "You've hit your session limit"
    assert "未正常完成" in (args.out / "delivery.html").read_text()
    assert (args.out / "candidate_01/viewer.html").exists()
    assert delivery["drawing_fidelity"] == "not_evaluated"


def test_terminate_subscription_stops_parent_and_nested_session_child(tmp_path):
    child_pid_path = tmp_path / "nested-child.pid"
    parent_code = """
from pathlib import Path
import subprocess
import sys
import time

child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
Path(sys.argv[1]).write_text(str(child.pid), encoding="utf-8")
time.sleep(60)
"""
    parent = subprocess.Popen([sys.executable, "-c", parent_code, str(child_pid_path)],
                              start_new_session=True)
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while not child_pid_path.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        assert child_pid_path.exists(), "nested session did not start"
        child_pid = int(child_pid_path.read_text(encoding="utf-8"))

        terminate_subscription(parent)
        assert parent.poll() is not None
        deadline = time.monotonic() + 3
        while not _ended_or_zombie(child_pid) and time.monotonic() < deadline:
            time.sleep(.02)
        assert _ended_or_zombie(child_pid), "nested sleep process survived termination"
    finally:
        for pid in (parent.pid, child_pid):
            if pid is None or _ended_or_zombie(pid):
                continue
            try:
                os.killpg(os.getpgid(pid), 9)
            except ProcessLookupError:
                pass
