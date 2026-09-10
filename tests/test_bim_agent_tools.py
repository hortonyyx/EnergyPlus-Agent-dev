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

from scripts.tool_scripts.run_bim_agent import terminate_subscription


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


def test_readonly_stdio_inventory_hash_and_tool_boundary(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=True) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {"inputs", "view_image", "pixel_profile", "map_pixels"} <= tools
            assert "build_bim" not in tools and "review_detail" not in tools
            assert "revise_bim" not in tools and "inspect_candidate" not in tools
            assert "check_openings" not in tools
            assert "finish_bim" not in tools and "overlay_candidate" not in tools

            inventory = _json_result(await session.call_tool("inputs", {}))
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


def test_normal_stdio_builds_candidate_and_returns_plan_image(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert "build_bim" in tools and "view_candidate" in tools
            built = _json_result(await session.call_tool("build_bim", {"proposal_json": _two_room_proposal()}))
            assert built["candidate"] == "candidate_01"
            assert built["source_geometry_ready"]
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
            assert json.loads((run / "delivery.json").read_text())["source_model_sha256"] == checked["source_model_sha256"]
            assert json.loads((run / "delivery_selection.json").read_text())["candidate"] == "candidate_02"

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
