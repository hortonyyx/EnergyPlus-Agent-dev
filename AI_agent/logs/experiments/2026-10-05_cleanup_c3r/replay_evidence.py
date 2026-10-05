"""Read verified 27B journals; rebuild request sizes and conservative tails."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.bim_agent_budget import time_status
from src.agent_runtime.adapter import reasoning_history_messages
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts import BudgetAmounts, VersionManifest


def reader(run):
    store = object.__new__(EventStore)
    store.directory = run.resolve()
    store._root = store
    journal = json.loads((run / "journal.json").read_bytes())
    store.run_id = journal["run_id"]
    store.task_id = store.root_task_id = journal["task_id"]
    store.budget_limit = BudgetAmounts.model_validate_json(json.dumps(journal["budget_limit"]))
    store._all_events = EventStore.read_events(run / "events.jsonl")
    return store


def text_chars(body):
    body = copy.deepcopy(body)
    for message in body["messages"]:
        if isinstance(message.get("content"), list):
            for block in message["content"]:
                if block.get("type") == "image_url":
                    block["image_url"]["url"] = "<image bytes omitted>"
    return len(json_bytes(body).decode())


def replay(run):
    store = reader(run)
    requests = []
    for event in store.events:
        if event.payload.event_type != "adapter_request":
            continue
        body = store.resolve(event.payload.final_request_body)
        sources = [item.source for item in event.payload.injected_content
                   if item.request_location.startswith("/messages/")]
        after = {**body, "messages": reasoning_history_messages(body["messages"], "current_tool_chain", sources)}
        requests.append(dict(request=len(requests) + 1, event_id=event.event_id,
            before_text_chars=text_chars(body), after_text_chars=text_chars(after),
            before_wire_chars=len(json_bytes(body).decode()), after_wire_chars=len(json_bytes(after).decode()),
            removed_reasoning_chars=sum(len(m.get("reasoning_content", "")) + len(m.get("reasoning", ""))
                for m in body["messages"]) - sum(len(m.get("reasoning_content", "")) + len(m.get("reasoning", ""))
                for m in after["messages"])))
    config = store.get_json_tree(next(e.payload.state for e in reversed(store.events)
                                      if e.payload.event_type == "checkpoint"))["config"]
    manifest = json.loads((run / "bim/inputs.json").read_bytes())
    toolkit = SimpleNamespace(run=run / "bim", manifest=manifest, readonly=False)
    all_events = store.all_events
    delivered = {e.payload.tool_execution_event_id for e in all_events
                 if e.payload.event_type == "tool_presentation"}
    tails = []
    for event in all_events:
        if event.event_id not in delivered:
            continue
        invocation = next(e for e in all_events if e.event_id == event.payload.invocation_event_id)
        store._all_events = [e for e in all_events if e.sequence <= invocation.sequence]
        now = datetime.fromisoformat(event.occurred_at.value.isoformat()).timestamp()
        engine = Runtime(store=store, adapter=None, tools=None, role=None,
            model=config["model"], parameters=config["parameters"],
            versions=VersionManifest.model_validate_json(json.dumps(config["versions"])),
            limits=RunLimits.model_validate_json(json.dumps(config["limits"])))
        engine.started = time.monotonic()
        engine.started_epoch = manifest["started_epoch"]
        engine.elapsed_before = now - engine.started_epoch
        engine._load_budget()
        engine._refresh_counts()
        status = {**engine.remaining_budget_status(), "run_directory": str(toolkit.run.resolve()),
                  "started_epoch": manifest["started_epoch"]}
        scratch = toolkit.run / ".harness_tmp"
        scratch.mkdir(exist_ok=True)
        path = scratch / "budget_status.json"
        path.write_text(json.dumps(status))
        new = time_status(toolkit, now=now)
        path.unlink()
        raw = store.resolve(event.payload.raw_result)
        old = next((block["text"] for block in reversed(raw.get("content", []))
                    if block.get("type") == "text" and "剩余" in block.get("text", "")), None)
        tails.append({"event_id": event.event_id, "tool": event.payload.tool_name,
                      "tool_number": engine.counts["tool_calls"], "old_line": old,
                      "new_line": new["line"], "dimensions": new["dimensions"]})
    return {"run": run.name, "model_service_requests": 0, "requests": requests, "delivered_tool_tails": tails,
        "note": "Original model inputs held fixed; only historical reasoning policy changes. Text counts exclude image base64. "
                "Budget rebuilt immediately before each delivered tool, using original limits and settled/held usage; "
                "this does not predict model behaviour or provider tokenization."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.run.resolve())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"run": result["run"], "requests": len(result["requests"]),
                      "last_delivered_tail": result["delivered_tool_tails"][-1]}, ensure_ascii=False))
