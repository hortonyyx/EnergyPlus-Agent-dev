"""Offline end-to-end external MCP exercise; no real model is called."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent_runtime.mcp_tools import McpToolClient
from src.agent_runtime.store import EventStore
from src.agent.runtime_tools import FROZEN_DEFINITIONS_SHA256, validate_frozen_catalog
from src.harness_contracts import BudgetAmounts, EventLog


def response(text=None, attack=False):
    message = {"role": "assistant", "content": text}
    if attack:
        message["tool_calls"] = [{"id": "write-attempt", "type": "function",
            "function": {"name": "build_bim", "arguments": "{}"}}]
    return {"model": "scripted-model", "choices": [{"index": 0, "message": message,
        "finish_reason": "tool_calls" if attack else "stop"}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        "fixture_notice": "scripted offline protocol response; tokens are synthetic"}


async def demo(out):
    if not out.resolve().is_relative_to(ROOT):
        raise ValueError("demo writes only inside this worktree")
    work = out.parent / (out.name + "_driver")
    work.mkdir(parents=True, exist_ok=False)
    answer = json.dumps({"directly_seen": [{"observation_id": "border", "statement":
        "A black vertical boundary is visible. Synthetic observation for protocol verification.",
        "view_id": "view_0001", "box_original_pixels": [19, 20, 26, 100]}],
        "interpretations": [], "uncertain": [{"uncertainty_id": "height", "statement":
        "This synthetic plan does not establish the door height; any height change remains an explicit coordinator assumption."}]})
    fixture = work / "responses.json"
    fixture.write_text(json.dumps({"observer_1": [response(answer)], "observer_2": [response(answer)],
        "attack": [response(attack=True)], "tiny_budget": [response(answer)]}))
    base_args = ["-m", "src.agent.runtime_coordinator", "--out", str(out),
        "--images", str(ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage1/offline_inputs"),
        "--provider", "scripted", "--script", str(fixture), "--tokens", "200000",
        "--model-calls", "10", "--output-tokens", "2048"]

    def client(resume=False):
        return McpToolClient(command=sys.executable, args=[*base_args, *(["--resume"] if resume else [])],
            cwd=ROOT, run_directory=work, env={"PYTHONPATH": str(ROOT)})

    async def call(c, name, arguments, error=False):
        raw = await c.call_tool(name, arguments)
        assert raw["isError"] == error, (name, raw)
        return raw.get("structuredContent", raw)

    proposal = {"geometry": {"schema_version": "2", "footprint_x": [0, 6], "footprint_y": [0, 4],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "left", "role": "office", "x": [0, 3], "y": [0, 4]},
            {"id": "right", "role": "corridor", "x": [3, 6], "y": [0, 4]}]}],
        "windows": [], "openings": [{"id": "door", "kind": "door", "space_id": "left",
            "other_space_id": "right", "p1": [3, 1], "p2": [3, 2], "z": [0, 2.1],
            "source_refs": ["synthetic offline fixture; dimensions assumed"]}]},
        "assumptions": ["Offline two-room fixture; not a real building or quality result."], "unresolved": []}
    budget = {"model_calls": 2, "tool_calls": 2, "seconds": 120, "tokens": 50_000}
    async with client() as c:
        catalog = await c.list_tools()
        frozen = [t for t in catalog if t["name"] not in {
            "delegate_to_role", "inspect_local_observation", "apply_local_observation", "runtime_state"}]
        validate_frozen_catalog(frozen, readonly=False)
        await call(c, "view_image", {"name": "plan.png", "box": [10, 10, 180, 200], "coordinate_grid": False})
        await call(c, "build_bim", {"proposal_json": json.dumps(proposal)})
        await call(c, "inspect_candidate", {"candidate": "candidate_01"})
        for task in ("observer_1", "observer_2"):
            result = await call(c, "delegate_to_role", {"task_id": task, "question":
                "Locate the left border; state whether this plan determines door height.",
                "view_ids": ["view_0001"], "budget": budget})
            assert result["status"] == "completed", result
        observed = await call(c, "inspect_local_observation", {"task_id": "observer_1"})
        assert observed["applicable"]
        operations = [{"op": "update_opening", "id": "door", "changes": {"z": [0, 2.2]},
            "reason": "Offline coordinator explicitly changes the assumed door height to exercise revision.",
            "source_refs": ["synthetic fixture; explicit assumption, not a measured height"]}]
        await call(c, "apply_local_observation", {"task_id": "observer_1", "tool_name": "revise_bim",
            "arguments": {"candidate": "candidate_01", "operations_json": json.dumps(operations)},
            "reason": "Exercise an explicitly assumed local revision and stale-result rejection."})
        await call(c, "view_candidate", {"candidate": "candidate_02", "floor_id": "F1"})
        before = hashlib.sha256((out / "bim/candidate_02/source_model.json").read_bytes()).hexdigest()
        stale = await call(c, "apply_local_observation", {"task_id": "observer_2", "tool_name": "revise_bim",
            "arguments": {"candidate": "candidate_02", "operations_json": json.dumps(operations)},
            "reason": "Deliberate stale result test."}, error=True)
        assert "stale" in stale["reason"]
        after = hashlib.sha256((out / "bim/candidate_02/source_model.json").read_bytes()).hexdigest()
        assert before == after
        attack = await call(c, "delegate_to_role", {"task_id": "attack", "question": "Offline authorization attack.",
            "view_ids": ["view_0001"], "budget": budget})
        assert attack["status"] == "tool_authorization_failed", attack
        tiny = await call(c, "delegate_to_role", {"task_id": "tiny_budget", "question": "Do not exceed the task budget.",
            "view_ids": ["view_0001"], "budget": {**budget, "tokens": 1}})
        assert "budget_exhausted" in tiny["status"] and tiny["runtime"]["model_calls"] == 0, tiny
        await call(c, "finish_bim", {"candidate": "candidate_02"})
    # Reopen the real stdio service, restoring the same log and saved child
    # results. No child request or BIM write should repeat after reconnect.
    initial = EventStore.read_events(out / "events.jsonl")
    async with client(resume=True) as c:
        checked = await call(c, "inspect_local_observation", {"task_id": "observer_2"})
        assert not checked["applicable"] and "stale" in checked["applicability_reason"]
        await call(c, "runtime_state", {})
    events = EventStore.read_events(out / "events.jsonl")
    count = lambda ev, kind: sum(e.payload.event_type == kind for e in ev)
    assert count(initial, "adapter_request") == count(events, "adapter_request") == 3
    assert count(initial, "tool_invocation") == count(events, "tool_invocation")
    metadata = json.loads((out / "journal.json").read_bytes())
    EventLog(mode="complete", events=tuple(events), budget_limit=BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"])))
    assert (out / "bim/candidate_02/viewer.html").is_file()
    report = {"status": "passed", "real_model_calls": 0, "scripted_model_calls": 3,
        "frozen_tool_definitions_sha256": FROZEN_DEFINITIONS_SHA256["coordinator"],
        "events": len(events), "source_spaces": 2, "source_openings": 1,
        "source_revision": "door height assumption changed 2.1 -> 2.2 m; actual frozen revise_bim",
        "delivered_crop": [10, 10, 180, 200], "stale_result_rejected": True,
        "read_only_attack_rejected": True, "child_budget_stopped_before_send": True,
        "reconnect_repeated_requests_or_writes": False,
        "usage_notice": "All usage in this demonstration is synthetic fixture data.",
        "viewer": "bim/candidate_02/viewer.html"}
    (out / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    asyncio.run(demo(p.parse_args().out.resolve()))
