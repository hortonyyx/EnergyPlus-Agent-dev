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

            inventory = _json_result(await session.call_tool("inputs", {}))
            assert set(inventory["images"]) == {"plan.png"}
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

    asyncio.run(scenario())


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
