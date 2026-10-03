"""Replay P3's exact responses/results and saved artifacts through C1, offline.

Extract evidence/migration-2026-10-03:attempt_03_run.tar.xz inside this worktree
first. No model or geometry call is made; this evaluates presentation, not BIM
quality or how the model would react to the new context.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path

from src.agent.runtime_context import update_building_context
from src.agent_runtime.adapter import ScriptedAdapter, convert_tool_result
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.loop import Runtime, RunLimits
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts import RoleDefinition, VersionManifest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STATE_PREFIX = "Current runtime state"


def load(path):
    return json.loads(path.read_bytes())


def capture(run, item):
    return item["value"] if item["kind"] == "inline" else load(run / item["blob"]["uri"])


def stats(values):
    return {"total": sum(values), "max": max(values, default=0), "count": len(values)}


async def replay(source, work):
    assert work.is_relative_to(ROOT) and not work.exists()
    implementation = [*ROOT.glob("src/agent_runtime/*.py"),
                      ROOT / "src/agent/runtime_context.py", Path(__file__)]
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in implementation}
    events = [json.loads(line) for line in (source / "events.jsonl").read_text().splitlines()]
    requests = [e for e in events if e["payload"]["event_type"] == "adapter_request"]
    bodies = [capture(source, e["payload"]["final_request_body"]) for e in requests]
    executions = [e for e in events if e["payload"]["event_type"] == "tool_execution"]
    responses = [capture(source, e["payload"]["raw_response"]) for e in events
                 if e["payload"]["event_type"] == "model_response"]
    checkpoint = load(source / load(source / "checkpoint.json")["uri"])
    work.mkdir(parents=True)

    class ReplayTools:
        def __init__(self):
            self.run_directory = work / "bim"
            self.run_directory.mkdir()
            self.index = 0
            self.current = {"files": {}}
            self.last_event = None

        async def list_tools(self):
            return [{"name": t["function"]["name"], "description": t["function"]["description"],
                     "inputSchema": t["function"]["parameters"]} for t in bodies[0]["tools"]]

        def repeatability(self, name):
            return next(e["payload"]["repeatability"] for e in executions if e["payload"]["tool_name"] == name)

        async def call_tool(self, name, arguments):
            event = executions[self.index]
            assert (name, arguments) == (event["payload"]["tool_name"], event["payload"]["full_arguments"])
            self.index += 1
            self.last_event = event
            state_ref = next(s["blob"] for s in event["source_refs"] if s["source_id"] == "tool-state-after")
            self.current = load(source / state_ref["uri"])
            for name, digest in self.current["files"].items():
                target = self.run_directory / name
                assert target.resolve().is_relative_to(self.run_directory)
                original = source / "bim" / name
                data = original.read_bytes() if original.is_file() else b""
                if hashlib.sha256(data).hexdigest() != digest:
                    data = (source / "blobs" / digest).read_bytes()
                assert hashlib.sha256(data).hexdigest() == digest
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists() or target.read_bytes() != data:
                    target.write_bytes(data)
            return capture(source, event["payload"]["raw_result"])

        def snapshot_state(self):
            return self.current

        def artifacts(self):
            return sorted(self.run_directory.rglob("*.json"))

        def image_origins(self, raw):
            return {r["image"]["sha256"]: {"view_id": r["view_id"], "tags": r["tags"]}
                    for r in checkpoint["context"]["images"]
                    if r["source"]["event_id"] == self.last_event["event_id"]}

    limits = RunLimits(model_calls=len(responses), tool_calls=len(executions), seconds=6000,
        tokens=20_000_000, retry_backoff_seconds=0)
    role = RoleDefinition.model_validate_json(json.dumps(checkpoint["config"]["role"]))
    role = role.model_copy(update={"budget": limits.ledger_limit()})
    store = EventStore(work / "audit", run_id="c1-p3-offline-replay", task_id="coordinator",
        budget_limit=limits.ledger_limit())
    adapter = ScriptedAdapter(responses)
    engine = Runtime(store=store, adapter=adapter, tools=ReplayTools(), role=role,
        model=bodies[0]["model"], parameters=checkpoint["config"]["parameters"],
        versions=VersionManifest.model_validate_json(json.dumps(checkpoint["versions"])),
        limits=limits, context_policy=ContextPolicy(), context_update=update_building_context)
    with store:
        receipt = await engine.run(bodies[0]["messages"][:2])
        assert receipt["status"] == "completed", receipt["status"]
        assert engine.tools.index == len(executions)
        after_bodies = [json.loads(body) for body in adapter.requests]
        assert len(after_bodies) == len(bodies)
        before_context = Counter(e["payload"]["action"] for e in events if e["payload"]["event_type"] == "context")
        after_context = Counter(e.payload.action for e in store.events if e.payload.event_type == "context")
        before_state = [len(m["content"]) for b in bodies for m in b["messages"]
                        if isinstance(m.get("content"), str) and m["content"].startswith(STATE_PREFIX)]
        after_state = [len(m["content"]) for b in after_bodies for m in b["messages"]
                       if isinstance(m.get("content"), str) and m["content"].startswith(STATE_PREFIX)]
        conversions, old_tool, new_tool = {}, [], []
        raw_after = [e.payload for e in store.events if e.payload.event_type == "tool_execution"]
        for original, replayed in zip(executions, raw_after, strict=True):
            p = original["payload"]
            raw = capture(source, p["raw_result"])
            assert store.resolve(replayed.raw_result) == raw
            before = capture(source, p["shown_result"])["tool_message"]["content"]
            after = convert_tool_result(p["call_id"], raw, store)[0]["content"]
            old_tool.append(len(before)); new_tool.append(len(after))
            conversions[p["call_id"]] = after
        occurrences = [m for b in bodies for m in b["messages"] if m["role"] == "tool"]
        pairs = [(len(m["content"]), len(conversions[m["tool_call_id"]])) for m in occurrences
                 if "context_reference" not in m["content"]]
        compactions = [e.sequence for e in store.events if e.payload.event_type == "context" and e.payload.action == "compact"]
        actual_requests = [e for e in store.events if e.payload.event_type == "adapter_request"]
        stable_checks, boundaries = 0, []
        def history(b):
            return [m for m in b["messages"] if not (isinstance(m.get("content"), str)
                    and m["content"].startswith(STATE_PREFIX))]
        for i in range(1, len(after_bodies)):
            a, b = history(after_bodies[i-1]), history(after_bodies[i])
            compacted = any(actual_requests[i-1].sequence < seq < actual_requests[i].sequence for seq in compactions)
            if compacted:
                boundaries.append(i+1)
            else:
                assert b[:len(a)] == a
                stable_checks += 1
        current = next(s for s in engine.context.state if s.key == "current-source-bim")
        selected = next(s for s in engine.context.state if s.key == "selected-source-bim")
        assert current.value["candidate"] == selected.value["candidate"] == "candidate_05"
        assert all(s.source_refs for s in engine.context.state)
        store.validate()
        report = {
            "source": {"branch": "evidence/migration-2026-10-03", "archive": "attempt_03_run.tar.xz",
                       "archive_sha256": "814cc29932fa3918fdcc22b4a47a0b9408f6039edcd3ecf60e30e4523ee1b867",
                       "events_sha256": hashlib.sha256((source / "events.jsonl").read_bytes()).hexdigest()},
            "scope": "Offline fixed-trajectory replay of 36 model responses and 55 exact MCP returns; no new inference or geometry execution.",
            "model_requests": 0, "status": receipt["status"], "raw_tool_results_unchanged": True,
            "state_characters": {"before": stats(before_state), "after": stats(after_state)},
            "tool_result_characters_once_each": {"before": stats(old_tool), "after": stats(new_tool)},
            "tool_characters_same_historical_positions": {"before": stats([a for a,b in pairs]), "after": stats([b for a,b in pairs])},
            "context_events": {"before": dict(before_context), "after": dict(after_context),
                               "before_total": sum(before_context.values()), "after_total": sum(after_context.values())},
            "append_only_transitions_checked": stable_checks, "compaction_before_requests": boundaries,
            "policy": engine.context.policy.model_dump(mode="json"),
            "current_candidate": current.value["candidate"], "selected_candidate": selected.value["candidate"],
            "final_audited_state_entries": len(engine.context.state),
            "final_model_state": engine.context.model_state(),
            "implementation_sha256": source_hashes,
            "final_audit_events_sha256": hashlib.sha256(store.path.read_bytes()).hexdigest(),
        }
        assert source_hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in implementation}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "p3_replay.json")
    args = parser.parse_args()
    report = asyncio.run(replay(args.source.resolve(), args.work.resolve()))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "state_characters", "tool_result_characters_once_each", "context_events")}))


if __name__ == "__main__":
    main()
