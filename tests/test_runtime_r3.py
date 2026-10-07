"""R3 runs the real runtime and T1 tools against local scripted responses."""

import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from time import monotonic
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from PIL import Image

from scripts.tool_scripts import run_bim_agent as runner
from scripts.tool_scripts import bim_agent_budget
from src.agent import runtime_entry
from src.agent.runtime_configuration import argv_for, load_configuration
from src.agent_runtime import loop
from src.agent_runtime.agent_registry import load_agent_registry
from src.agent.runtime_delegation import run_observer
from src.agent.runtime_tools import FrozenBimTools, local_observer_role
from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


ROOT = Path(__file__).resolve().parents[1]
PLAN = dict(floor_id="local", z_floor=0, ceiling_height=3,
    x_anchors=[[0, 0], [11, 11]], y_anchors=[[0, 7], [7, 0]], basis="synthetic frame",
    footprint_pixels=[[1, 1], [10, 1], [10, 6], [1, 6]],
    partitions=[], openings=[], assumptions=[], unresolved=[])


def _evidence(name, value):
    directory = os.environ.get("R3_EVIDENCE_OUT")
    if directory:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        (target / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class LocalClient:
    """Only the transport is replaced; FastMCP/T1 execute unmodified tools."""

    def __init__(self, run, clock, *, readonly=False):
        servers = []
        with patch.object(FastMCP, "run", lambda server: servers.append(server)):
            runner.serve(run, readonly=readonly)
        self.server, self.clock = servers[0], clock
        self.before_tool_time = None

    async def list_tools(self):
        return [t.model_dump(mode="json", exclude_none=True) for t in await self.server.list_tools()]

    async def call_tool(self, name, arguments):
        if self.before_tool_time is not None:
            self.clock[0] = self.before_tool_time
            self.before_tool_time = None
        value = await self.server.call_tool(name, arguments)
        if isinstance(value, CallToolResult):
            return value.model_dump(mode="json", exclude_none=True)
        content, structured = value if isinstance(value, tuple) else (value, None)
        return {"content": [b.model_dump(mode="json", exclude_none=True) for b in content],
            "isError": False, **({"structuredContent": structured} if structured is not None else {})}


async def _scenario(tmp_path, monkeypatch, actions, *, model_calls=20, preparation_seconds=0):
    images = tmp_path / "images"
    images.mkdir()
    for name in ("plan.png", "upstairs.png"):
        Image.new("RGB", (12, 8), "white").save(images / name)
    clock, clients, requests = [1000.0], [], []
    fake_time = SimpleNamespace(time=lambda: clock[0], monotonic=lambda: clock[0] + monotonic() * 1e-6)
    for module in (loop, runtime_entry, runner, bim_agent_budget):
        monkeypatch.setattr(module, "time", fake_time)

    @asynccontextmanager
    async def client(run_directory, readonly=False, repository_root=None):
        clock[0] += preparation_seconds
        value = LocalClient(run_directory, clock, readonly=readonly)
        clients.append(value)
        yield value

    out = tmp_path / "output"

    class ScenarioAdapter:
        def __init__(self, responses):
            self.responses = iter(responses)

        async def send(self, prepared, *, timeout):
            requests.append(prepared.body)
            row = next(self.responses)
            clock[0] = row.get("now", clock[0])
            clients[0].before_tool_time = row.get("at_tool")
            if row.get("tool"):
                arguments = dict(row.get("arguments", {}))
                if row["tool"] == "assemble_plan_bim":
                    toolkit = runner.Toolkit(out / "bim")
                    arguments["floors_json"] = json.dumps([
                        dict(draft_id=f"draft_{i:03d}",
                            expected_plan_sha256=toolkit.inspect_plan(f"draft_{i:03d}")["plan_sha256"],
                            floor_id=f"F{i}", z_floor=3*(i-1), evidence="synthetic floor scope")
                        for i in (1, 2)])
                message = {"role": "assistant", "content": None, "tool_calls": [{
                    "id": f"call_{len(requests)}", "type": "function", "function": {
                        "name": row["tool"], "arguments": json.dumps(arguments)}}]}
            else:
                message = {"role": "assistant", "content": "Saved results; no further action."}
            return {"id": f"offline_{len(requests)}", "model": "scripted-model",
                "choices": [{"message": message, "finish_reason": "tool_calls" if row.get("tool") else "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}}

    monkeypatch.setattr(runtime_entry, "frozen_bim_client", client)
    monkeypatch.setattr(runtime_entry, "ScriptedAdapter", ScenarioAdapter)
    script = tmp_path / "actions.json"
    script.write_text(json.dumps(actions))
    args = runtime_entry.parser().parse_args(["--out", str(out), "--run-root", str(tmp_path), "--images", str(images),
        "--provider", "scripted", "--script", str(script), "--seconds", "6000",
        "--model-calls", str(model_calls), "--tool-calls", "20", "--tokens", "20000000",
        "--max-candidates", "8", "--floor-plan-image", "plan.png",
        "--floor-plan-image", "upstairs.png", "--no-context"])
    receipt = await runtime_entry.execute(args)
    events = [json.loads(line) for line in (out / "events.jsonl").read_text().splitlines()]
    manifest = json.loads((out / "bim/inputs.json").read_bytes())
    assert manifest["started_epoch"] == 1000 and manifest["deadline_epoch"] == 7000
    assert manifest["time_budget_seconds"] == 6000
    assert receipt["started_epoch"] == manifest["started_epoch"]
    assert receipt["deadline_epoch"] == manifest["deadline_epoch"]
    assert receipt["agent_version"] == load_agent_registry(ROOT)["current_version"]
    return out, receipt, requests, events


def _build(image="plan.png"):
    return {"tool": "build_plan_bim", "arguments": {"image": image, "plan_json": json.dumps(PLAN)}}


def test_half_near_deadline_and_late_tool_refusal_through_runtime(tmp_path, monkeypatch):
    actions = [{"tool": "inputs"}, {"tool": "inputs", "now": 4000},
        {"tool": "inputs", "now": 6101},
        {**_build(), "now": 6999, "at_tool": 7000}]
    out, receipt, requests, events = asyncio.run(_scenario(tmp_path, monkeypatch, actions))
    shown = [m["content"] for request in requests for m in request["messages"] if m["role"] == "tool"]
    text = "\n".join(shown)
    assert "保守剩余（本运行）：时间 100.0 分钟" in text
    assert "最紧额度已过半，尚无草稿的楼层图：plan.png, upstairs.png" in text
    assert "剩余不足15%" in text and "停止新范围探索" in text
    assert "有界复核已列严重问题" in text and "交付并列未决" in text
    assert receipt["status"] == "time_budget_exhausted"
    assert not list((out / "bim").glob("candidate_*"))
    # The final refusal is recorded even though the expired runtime cannot
    # send a further model request to display it.
    saved = "\n".join(p.read_bytes().decode("utf-8", errors="replace") for p in (out / "blobs").rglob("*") if p.is_file())
    assert "Run deadline reached; no further tool actions" in saved
    assert "时间上限已到" in saved
    _evidence("time_boundaries", {"model_requests": 0, "scripted_responses": len(requests),
        "half_reminder": True, "near_reminder": True, "late_action_refused": True,
        "candidate_count": 0, "status": receipt["status"], "clock": [1000, 7000]})


def test_tool_preparation_uses_the_same_start_and_does_not_restart_clock(tmp_path, monkeypatch):
    _, receipt, _, _ = asyncio.run(_scenario(tmp_path, monkeypatch, [{}], preparation_seconds=600))
    assert 600 <= receipt["elapsed_seconds"] < 601
    assert receipt["started_epoch"] == 1000 and receipt["deadline_epoch"] == 7000


def test_claude_receipt_identifies_registered_agent_without_starting_model(tmp_path):
    run = tmp_path / "expired"
    run.mkdir()
    (run / "inputs.json").write_text(json.dumps({"images": {}, "started_epoch": 1, "deadline_epoch": 2}))
    with patch("src.agent_runtime.versions.source_commit", return_value="offline-git-fixture"), \
            patch.object(runner.subprocess, "Popen", side_effect=AssertionError("model launch forbidden")):
        receipt = runner.subscription(run, "offline expired run", model="sonnet", name="agent")
    assert receipt["agent_version"] == load_agent_registry(ROOT)["current_version"]
    assert receipt["timed_out"] and receipt["model_process_started"] is False


@pytest.mark.parametrize("ending", ["deadline", "normal", "model_limit"])
def test_stops_deliver_complete_before_newer_partial(tmp_path, monkeypatch, ending):
    actions = [_build(), _build("upstairs.png"), {"tool": "assemble_plan_bim"}, _build()]
    if ending == "deadline":
        actions += [{"tool": "finish_bim", "arguments": {"candidate": "candidate_04"}},
            {"tool": "inputs", "now": 6999, "at_tool": 7000}]
    elif ending == "normal":
        actions += [{}]
    out, receipt, requests, _ = asyncio.run(_scenario(tmp_path, monkeypatch, actions,
        model_calls=4 if ending == "model_limit" else 20))
    delivery = json.loads((out / "bim/delivery.json").read_bytes())
    assert receipt["status"] == {"deadline": "time_budget_exhausted", "normal": "completed",
                                 "model_limit": "model_budget_exhausted"}[ending]
    assert delivery["candidate"] == "candidate_03"
    assert delivery["selection_origin"] == "latest_complete_fallback_not_agent_selected"
    assert delivery["floor_completeness"]["complete_building"] is True
    assert delivery["floor_completeness"]["latest_saved_candidate"] == "candidate_04"
    assert str(out / "bim/delivery.json") in receipt["artifact_paths"]
    assert receipt["finalization"]["delivery"]["candidate"] == "candidate_03"
    assert (out / "bim/delivery.html").is_file()
    _evidence("full_then_partial_" + ending, {"model_requests": 0, "status": receipt["status"],
        "delivery": receipt["finalization"], "floor_completeness": delivery["floor_completeness"]})


def test_only_partial_saved_is_delivered_as_incomplete(tmp_path, monkeypatch):
    actions = [_build(), {"tool": "inputs", "now": 6999, "at_tool": 7000}]
    out, receipt, _, _ = asyncio.run(_scenario(tmp_path, monkeypatch, actions))
    delivery = json.loads((out / "bim/delivery.json").read_bytes())
    assert delivery["candidate"] == "candidate_01"
    assert delivery["selection_origin"] == "latest_saved_fallback_not_agent_selected"
    assert delivery["floor_completeness"]["complete_building"] is False
    assert delivery["floor_completeness"]["missing_candidate_images"] == ["upstairs.png"]
    assert delivery["generation_status"]["timed_out"] is True
    _evidence("partial_only", {"model_requests": 0, "status": receipt["status"],
        "delivery": receipt["finalization"], "floor_completeness": delivery["floor_completeness"]})


def test_non_timeout_preserves_model_selection(tmp_path, monkeypatch):
    actions = [_build(), _build("upstairs.png"), {"tool": "assemble_plan_bim"},
        {"tool": "finish_bim", "arguments": {"candidate": "candidate_01"}}, {}]
    out, receipt, _, _ = asyncio.run(_scenario(tmp_path, monkeypatch, actions))
    delivery = json.loads((out / "bim/delivery.json").read_bytes())
    assert delivery["candidate"] == "candidate_01" and delivery["selection_origin"] == "agent_selected"
    assert delivery["floor_completeness"]["complete_building"] is False
    assert receipt["status"] == "completed"
    _evidence("explicit_selection", receipt["finalization"])


def test_external_coordinator_also_finalizes_saved_work(tmp_path, monkeypatch):
    from src.agent.runtime_coordinator import CoordinatorSession
    from src.agent.runtime_tools import coordinator_role
    from src.agent_runtime.agent_registry import agent_version_record
    out, _, _, _ = asyncio.run(_scenario(tmp_path, monkeypatch, [_build(), {}]))
    source = out / "bim/candidate_01/source_model.json"
    before = source.read_bytes()
    limits = RunLimits(model_calls=2, tool_calls=2, tokens=100000, seconds=6000)
    with EventStore(tmp_path / "external", run_id="external", task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        tools = FrozenBimTools(None, coordinator_role(limits.ledger_limit()), run_directory=out / "bim")
        session = CoordinatorSession(store=store, tools=tools, observer_tools=tools,
            adapter_factory=None, model="test", parameters={}, limits=limits, start_epoch=1000)
        session.agent_version = agent_version_record(ROOT)
        receipt = session.finalize("time_budget_exhausted")
        assert receipt["finalization"]["delivery"]["candidate"] == "candidate_01"
        assert receipt["finalization"]["delivery"]["complete_building"] is False
        assert source.read_bytes() == before
        store.validate()


def test_floor_scope_configuration_and_input_rejection(tmp_path):
    original = ROOT / "AI_agent/logs/experiments/2026-10-03_runtime_r2/r2bc/configs/migration_sm24_glm_subscription.json"
    value = json.loads(original.read_bytes())
    value["cases"][0]["floor_plan_images"] = ["1f_view.png"]
    config = tmp_path / "configuration.json"
    config.write_text(json.dumps(value))
    case = load_configuration(config)["cases"][0]
    argv = argv_for(case)
    assert argv[argv.index("--floor-plan-image") + 1] == "1f_view.png"
    value["cases"][0]["floor_plan_images"] = ["../unknown.png"]
    config.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="admitted input filenames"):
        load_configuration(config)
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (12, 8)).save(images / "1f_view.png")
    kwargs = dict(images=images, mesh=None, building_input=None, scope="fixture", image_kind="drawings", max_candidates=1)
    with pytest.raises(ValueError, match="admitted input filenames"):
        runtime_entry.prepare_inputs(tmp_path / "bad", **kwargs, floor_plan_images=["unknown.png"])
    run, _, _ = runtime_entry.prepare_inputs(tmp_path / "hint", **kwargs)
    hint = json.loads((run / "inputs.json").read_bytes())
    assert hint["floor_plan_images"] == ["1f_view.png"]
    assert hint["floor_scope_source"] == "input_filename_hint"


@pytest.mark.parametrize("child_seconds, actual_seconds", [(30, 30), (300, 100)])
def test_observer_service_uses_own_deadline_and_cannot_extend_parent(tmp_path, monkeypatch, child_seconds, actual_seconds):
    from src.agent import runtime_delegation, runtime_tools
    from tests.test_runtime_delegation import _registered_view, _package, _response, _answer

    async def scenario():
        clock = [1000.0]
        fake_time = SimpleNamespace(time=lambda: clock[0], monotonic=lambda: clock[0] + monotonic() * 1e-6)
        for module in (loop, runtime_delegation, runner, bim_agent_budget):
            monkeypatch.setattr(module, "time", fake_time)

        @asynccontextmanager
        async def local(run_directory, readonly=False, repository_root=None):
            yield LocalClient(run_directory, clock, readonly=readonly)

        monkeypatch.setattr(runtime_tools, "frozen_bim_client", local)
        root_limits = RunLimits(model_calls=6, tool_calls=6, tokens=1_000_000, seconds=1000)
        limits = RunLimits(model_calls=3, tool_calls=3, tokens=500_000, seconds=child_seconds)
        with EventStore(tmp_path / "audit", run_id="r3-observer", task_id="coordinator",
                        budget_limit=root_limits.ledger_limit()) as store:
            view = _registered_view(store)
            run = tmp_path / "parent"
            run.mkdir()
            manifest_path = run / "inputs.json"
            manifest_path.write_text(json.dumps({"images": {}, "image_kind": "drawings",
                "started_epoch": 1000, "deadline_epoch": 1100, "time_budget_seconds": 100}))
            parent_before = manifest_path.read_bytes()
            frozen = FrozenBimTools(None, local_observer_role(root_limits.ledger_limit()), run_directory=run)
            def nearing(_):
                clock[0] = 1000 + actual_seconds * .9
                return _response(calls=[("reference", "get_bim_reference", {"topic": "geometry"})])
            adapter = ScriptedAdapter([nearing, _response(text=_answer())])
            child = store.for_task("observer-1", parent_task_id="coordinator")
            result = await run_observer(store=child, frozen_tools=frozen, adapter=adapter,
                model="test", parameters={"max_tokens": 4096}, limits=limits,
                package=_package(view), views=[view], notes=[], root=ROOT,
                route={"route_id": "scripted", "model": "test"}, parent_deadline_epoch=1100)
            assert result["status"] == "completed", result
            manifest = json.loads((child.task_directory / "bim/inputs.json").read_bytes())
            assert manifest["started_epoch"] == 1000
            assert manifest["deadline_epoch"] == 1000 + actual_seconds <= 1100
            assert manifest["time_budget_seconds"] == actual_seconds
            assert manifest_path.read_bytes() == parent_before
            tail = adapter.requests[1].decode()
            assert "剩余不足15%" in tail and "停止新范围探索" in tail
            assert "返回已有观察与未核项" in tail
            assert "先按已读信息保存全楼草稿" not in adapter.requests[1].decode()
            store.validate()
            _evidence(f"observer_{child_seconds}", {"model_requests": 0,
                "status": result["status"], "timing": {key: manifest[key] for key in
                    ("started_epoch", "deadline_epoch", "time_budget_seconds")},
                "parent_deadline": 1100, "parent_unchanged": True, "readonly_reminder": True})
    asyncio.run(scenario())
