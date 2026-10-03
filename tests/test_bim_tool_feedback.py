"""Offline regressions for T1's observed interface failures."""
import asyncio
import json
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts.bim_agent_feedback import resolve_image_name
from scripts.tool_scripts.run_bim_agent import Toolkit, serve
from tests.test_bim_agent_tools import _run_with_one_image, _add_image, _server_session


def test_unique_image_aliases_and_ambiguous_names():
    images = {"East_view.png": {}, "West_view.png": {}}
    assert resolve_image_name(images, "EAST_VIEW") == "East_view.png"
    assert resolve_image_name(images, "east_VIEW.PNG") == "East_view.png"
    images["East_view.jpg"] = {}
    with pytest.raises(ValueError, match="ambiguous.*East_view.*Available filenames"):
        resolve_image_name(images, "East_view")
    for name in ("p1", "../East_view.png", "/East_view.png"):
        with pytest.raises(ValueError, match="Available filenames"):
            resolve_image_name(images, name)


@pytest.mark.parametrize("scale,used", [(0.7, 1), (9, 8), (-3, 1)])
def test_zoom_clamps_without_changing_original(tmp_path, scale, used):
    run = _run_with_one_image(tmp_path)
    original = (run / "images/plan.png").read_bytes()
    data = Toolkit(run).view("PLAN", display_scale=scale)
    info = json.loads(data[1])
    assert info["name"] == "plan.png"
    assert info["display_scale_requested"] == scale and info["display_scale_used"] == used
    assert "clamped" in info["display_scale_note"]
    assert (run / "images/plan.png").read_bytes() == original


def test_alias_error_and_image_results_survive_real_stdio(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            result = await session.call_tool("view_image", {"name": "PLAN", "display_scale": 0.5})
            assert not result.isError and any(c.type == "image" for c in result.content)
            assert "actual filename 'plan.png'" in "\n".join(c.text for c in result.content if c.type == "text")
            bad = await session.call_tool("pixel_profile", dict(name="p1", box=[0, 0, 4, 4], axis="x", rgb=[255, 255, 255]))
            assert bad.isError and "Available filenames: [\"plan.png\"]" in bad.content[0].text
            assert len((await session.list_tools()).tools) == 42
    asyncio.run(scenario())


def test_plan_format_failure_supplies_correct_minimum_without_edit(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        servers = []
        with patch.object(FastMCP, "run", lambda s: servers.append(s)):
            serve(run)
        server = servers[0]
        # Exercise the response boundary with the actual compiler's format rejection.
        from src.agent.geometry.plan_revision import apply_plan_revision
        args = dict(draft_id="draft_001", expected_plan_sha256="0"*64,
                    operations_json=json.dumps([dict(op="update", collection="partitions", id="P1", points=[[1, 2], [4, 2]])]))
        with patch.object(Toolkit, "revise_plan", lambda *_: apply_plan_revision({}, json.loads(args["operations_json"]))):
            result = await server.call_tool("revise_plan_bim", args)
        assert result.isError
        text = result.content[0].text
        assert "missing changes, reason, source_refs" in text and '"changes": {"points"' in text
        assert not list(run.glob("candidate_*"))
    asyncio.run(scenario())
