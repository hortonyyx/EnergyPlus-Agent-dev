"""Scripted tools/model and simulated time; no model endpoint is reachable."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as runner
from scripts.tool_scripts.bim_agent_budget import time_status, saved_floor_status, fallback_selection
from tests.test_bim_agent_tools import _run_with_one_image, _add_image


def _clocked_run(tmp_path):
    run = _run_with_one_image(tmp_path)
    _add_image(run, "upstairs.png")
    manifest = json.loads((run / "inputs.json").read_text())
    runner.dump(run / "inputs.json", dict(manifest, started_epoch=1000, deadline_epoch=7000,
        time_budget_seconds=6000, floor_plan_images=["plan.png", "upstairs.png"],
        floor_scope_source="explicit_input_filenames"))
    return run


def test_scripted_tool_returns_at_half_near_and_hard_deadline(tmp_path, monkeypatch):
    async def scenario():
        run = _clocked_run(tmp_path)
        clock = [1000]
        monkeypatch.setattr("scripts.tool_scripts.bim_agent_budget.time.time", lambda: clock[0])
        servers = []
        with patch.object(FastMCP, "run", lambda s: servers.append(s)):
            runner.serve(run)
        server = servers[0]
        results = []
        for offset in [0, 3000, 5101, 6000]:
            clock[0] = 1000 + offset
            result = await server.call_tool("inputs", {})
            content = result.content if hasattr(result, "content") else result[0] if isinstance(result, tuple) else result
            results.append("\n".join(c.text for c in content if c.type == "text"))
        assert "已用 0.0／剩余 100.0 分钟" in results[0]
        assert "时间已过半" in results[1] and "upstairs.png" in results[1]
        assert "停止新的读图" in results[2]
        assert result.isError and "时间上限已到" in results[3]
        assert not list(run.glob("candidate_*"))
        clock[0] = 6500
        error = await server.call_tool("view_image", {"name": "label"})
        assert error.isError and "剩余" in error.content[-1].text
    asyncio.run(scenario())


def test_scripted_model_timeout_delivers_latest_complete_even_after_partial_selection(tmp_path, monkeypatch):
    old = _run_with_one_image(tmp_path)
    _add_image(old, "upstairs.png")
    events = []
    def scripted_model(run, prompt, **kwargs):
        toolkit = runner.Toolkit(run)
        plan = dict(floor_id="local", z_floor=0, ceiling_height=3,
            x_anchors=[[0, 0], [11, 11]], y_anchors=[[0, 7], [7, 0]], basis="synthetic frame",
            footprint_pixels=[[1, 1], [10, 1], [10, 6], [1, 6]],
            partitions=[], openings=[], assumptions=[], unresolved=[])
        rows = []
        for index, image in enumerate(["plan.png", "upstairs.png"], 1):
            built = toolkit.build_plan(image, json.dumps(plan))
            rows.append(dict(draft_id=f"draft_{index:03d}",
                expected_plan_sha256=built["plan_input"]["plan_sha256"], floor_id=f"F{index}",
                z_floor=3*(index-1), evidence="synthetic floor scope"))
        full = toolkit.assemble_plans(json.dumps(rows))
        partial = toolkit.build_plan("plan.png", json.dumps(plan))
        runner.dump(run / "delivery_selection.json", {"candidate": partial["candidate"]})
        # Simulate a process killed halfway through its next save; older complete
        # building and the failure must both survive final handoff.
        torn = run / "candidate_05"
        torn.mkdir()
        (torn / "source_model.json").write_text('{"floors":')
        (torn / "report.json").write_text('{"status":')
        assert saved_floor_status(toolkit)["missing_draft_images"] == []
        assert fallback_selection(toolkit)[0] == full["candidate"]
        events.append((full["candidate"], partial["candidate"]))
        record = dict(returncode=-15, elapsed_seconds=6000, timed_out=True, result={})
        runner.dump(run / "agent_receipt.json", record)
        return record
    monkeypatch.setattr(runner, "subscription", scripted_model)
    out = tmp_path / "scripted"
    runner.run_experiment(SimpleNamespace(images=old / "images", out=out, scope="synthetic two floors",
        timeout=6000, provider="glm", image_kind="drawings", floor_plan_images=["plan.png", "upstairs.png"]))
    delivery = json.loads((out / "delivery.json").read_text())
    assert delivery["candidate"] == events[0][0]
    assert delivery["selection_origin"] == "latest_complete_fallback_not_agent_selected"
    assert delivery["floor_completeness"]["complete_building"]
    assert delivery["generation_status"]["timed_out"]
    assert delivery["floor_completeness"]["unreadable_saved_candidates"][0]["candidate"] == "candidate_05"


def test_single_floor_fallback_reports_missing_upper_floor(tmp_path):
    from tests.test_bim_claims import setup_run
    run, toolkit = setup_run(tmp_path)
    # A saved source without image/floor provenance must not be called complete.
    toolkit.manifest.update(floor_plan_images=["plan.png", "upstairs.png"])
    assert fallback_selection(toolkit) == ("seed", "latest_saved_fallback_not_agent_selected")
    assert saved_floor_status(toolkit, "seed")["complete_building"] is False


def test_no_complete_candidate_still_delivers_latest_viewable_severe_draft(tmp_path):
    from tests.test_source_proposal import _proposal
    toolkit = runner.Toolkit(_run_with_one_image(tmp_path))
    toolkit.manifest.update(floor_plan_images=["plan.png"])
    proposal = _proposal()
    proposal["geometry"]["openings"][0]["other_space_id"] = "missing-room"
    result = toolkit.build(proposal)
    assert not result["source_geometry_ready"]
    candidate, origin = fallback_selection(toolkit)
    assert candidate == result["candidate"] and origin == "latest_saved_fallback_not_agent_selected"
    delivery = toolkit.delivery(candidate, selection_origin=origin)
    assert delivery["viewer_exists"]
    assert delivery["floor_completeness"]["complete_building"] is False
    assert delivery["floor_completeness"]["candidate_source_geometry_ready"] is False


def test_subscription_wait_uses_remaining_deadline_and_never_launches_after_expiry(tmp_path, monkeypatch):
    run = _clocked_run(tmp_path)
    clock, waits = [6500], []
    monkeypatch.setattr(runner.time, "time", lambda: clock[0])
    class ScriptedProcess:
        returncode = 0
        def __init__(self, command, **kwargs):
            kwargs["stdout"].write(json.dumps(dict(type="system", subtype="init", model="claude-sonnet-5")) + "\n")
        def communicate(self, prompt, timeout):
            waits.append(timeout)
    monkeypatch.setattr(runner.subprocess, "Popen", ScriptedProcess)
    runner.subscription(run, "fixture", model="sonnet", name="first", timeout=6000)
    assert waits == [500]
    clock[0] = 7000
    receipt = runner.subscription(run, "fixture", model="sonnet", name="expired", timeout=6000)
    assert waits == [500] and receipt["timed_out"] and receipt["model_process_started"] is False
