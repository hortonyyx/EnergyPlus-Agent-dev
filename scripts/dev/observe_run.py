"""Per-role behaviour timeline of one run, for the dev model's observation notes (no model calls).

Usage: python scripts/dev/observe_run.py <run directory> [--json out.json]

New runtime (events.jsonl): one row per task (coordinator, each reader task) with start,
first request, first trial, submission/delivery, end (minutes from run start), requests,
model minutes, median seconds per request, output tokens, refused requests and tool counts.
Claude Code route (agent_stream.jsonl + tools.jsonl): main agent and each worker subagent with
turns, tool counts and output tokens; key tool times come from tools.jsonl.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import statistics
from pathlib import Path

from pydantic import TypeAdapter
from src.agent_runtime.store import EventStore
from src.harness_contracts.events import CapturedValue

MILESTONES = {"trial_plan_bim": "first_trial", "submit_plan_reading": "submitted",
              "submit_elevation_reading": "submitted", "assemble_from_readers": "first_assembly",
              "finish_bim": "delivered", "build_plan_bim": "first_build", "assemble_plan_bim": "first_assembly"}


class _ReadOnlyStore(EventStore):
    """Reuse verified capture readers without acquiring a writer or changing a run."""

    def __init__(self, directory):
        self.directory = Path(directory).resolve()


def _tool_body(store, payload):
    capture = payload.get("raw_result")
    if not capture or capture.get("kind") == "missing":
        return {}, {}, "result not captured"
    try:
        raw = store.resolve(TypeAdapter(CapturedValue).validate_json(json.dumps(capture)))
    except (ValueError, OSError) as error:
        return {}, {}, str(error)
    if not isinstance(raw, dict):
        return {}, {}, None
    body = raw.get("structuredContent")
    if not isinstance(body, dict):
        body = raw
        for part in raw.get("content", []):
            if part.get("type") == "text":
                try:
                    decoded = json.loads(part.get("text", ""))
                    if isinstance(decoded, dict):
                        body = decoded
                        break
                except ValueError:
                    pass
    return raw, body, None


def _stamp(event):
    value = (event.get("occurred_at") or {}).get("value")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() if value else None


def _minutes(value, origin):
    return None if value is None else round((value - origin) / 60, 1)


def observe_events(run: Path) -> dict:
    lines = (run / "events.jsonl").read_bytes().splitlines(keepends=True)
    events, partial_tail = [], False
    for index, line in enumerate(lines):
        if index == len(lines) - 1 and not line.endswith(b"\n"):
            partial_tail = True
            break
        events.append(json.loads(line))
    if not events:
        return {"run": run.name, "format": "events", "schema_version": 2,
                "tasks": [], "timeline": [], "partial_tail": partial_tail}
    origin = min(t for t in map(_stamp, events) if t)
    store = _ReadOnlyStore(run)
    tasks: dict[str, dict] = {}
    sent: dict[str, float] = {}
    requests, timeline, capture_errors, budget_waits = {}, [], [], {}
    for event in events:
        when, payload = _stamp(event), event.get("payload") or {}
        kind = payload.get("event_type")
        task = tasks.setdefault(event.get("task_id"), {
            "parent": (event.get("parent_task") or {}).get("task_id"), "start": when, "end": when,
            "first_request": None, "requests": 0, "responses": 0, "request_seconds": [], "output_tokens": 0,
            "input_tokens": 0, "cache_read_tokens": 0, "cache_creation_tokens": 0, "usage_responses": 0,
            "refused": 0, "tools": collections.Counter(), "tool_outcomes": collections.Counter(),
            "tool_errors": 0, "milestones": {}, "compactions": 0,
            "budget_wait_count": 0, "budget_wait_seconds": 0, "budget_wait_outcomes": collections.Counter()})
        if when:
            task["start"] = min(task["start"] or when, when)
            task["end"] = max(task["end"] or when, when)
        if kind == "adapter_request":
            sent[event["event_id"]] = when
            task["requests"] += 1
            task["first_request"] = task["first_request"] or when
            requests[event["event_id"]] = {"event": event["event_id"], "task": event.get("task_id"),
                "start_min": _minutes(when, origin), "status": "pending"}
        elif kind == "model_response":
            task["responses"] += 1
            began = sent.get(payload.get("request_event_id"))
            if began and when:
                task["request_seconds"].append(when - began)
            usage = (payload.get("usage") or {}).get("raw_usage") or {}
            task["output_tokens"] += usage.get("output_tokens") or 0
            if (payload.get("usage") or {}).get("kind") == "reported":
                task["usage_responses"] += 1
                task["input_tokens"] += usage.get("input_tokens") or 0
                task["cache_read_tokens"] += usage.get("cache_read_input_tokens") or 0
                task["cache_creation_tokens"] += usage.get("cache_creation_input_tokens") or 0
            row = requests.get(payload.get("request_event_id"))
            if row is not None:
                row.update(status="responded", response_event=event["event_id"], usage=usage,
                           elapsed_s=round(when - began, 3) if began and when else None)
        elif kind == "model_failure" or (kind == "run_lifecycle" and payload.get("model_failure")):
            task["refused"] += 1
            failure = payload.get("model_failure") or payload
            row = requests.get(failure.get("request_event_id"))
            began = sent.get(failure.get("request_event_id"))
            if began and when:
                task["request_seconds"].append(when - began)
            if row is not None:
                row.update(status="failed", failure_event=event["event_id"],
                           reason=failure.get("category", payload.get("reason")),
                           elapsed_s=round(when - began, 3) if began and when else None)
        elif kind == "tool_invocation":
            name = payload.get("tool_name")
            task["tools"][name] += 1
            label = MILESTONES.get(name)
            if label:
                # Attempts are distinct from successful results. A trial's first
                # invocation remains useful even when no draft can be compiled.
                task["milestones"].setdefault(label + "_attempt", when)
                if label == "first_trial":
                    task["milestones"].setdefault(label, when)
        elif kind == "tool_execution":
            raw, body, capture_error = _tool_body(store, payload)
            if capture_error:
                capture_errors.append({"event": event["event_id"], "reason": capture_error})
            outcome = payload.get("outcome", "unknown")
            if outcome == "succeeded" and (raw.get("isError") or body.get("isError")
                    or body.get("status") in {"rejected", "failed", "error"}):
                outcome = "failed"
            task["tool_outcomes"][outcome] += 1
            task["tool_errors"] += outcome == "failed"
            name = payload.get("tool_name")
            label = MILESTONES.get(name)
            if outcome == "succeeded" and not capture_error and label:
                if label == "first_trial":
                    if body.get("status") == "passed":
                        task["milestones"].setdefault("first_successful_trial", when)
                elif label == "submitted":
                    if body.get("status") == "accepted":
                        task["milestones"].setdefault(label, when)
                else:
                    task["milestones"].setdefault(label, when)
            timeline.append({"event": event["event_id"], "task": event.get("task_id"),
                "min": _minutes(when, origin), "tool": name, "outcome": outcome,
                "invocation_event": payload.get("invocation_event_id"),
                **({"failure": payload["failure"]} if payload.get("failure") else {}),
                "result": {k: body[k] for k in ("status", "reason", "error_type", "candidate", "draft",
                    "draft_id", "artifact_sha256", "next_action") if k in body}})
        elif kind == "context" and payload.get("action") == "compact":
            task["compactions"] += 1
        elif kind == "budget_wait":
            key = (event.get("task_id"), payload["wait_id"])
            if payload["phase"] == "begin":
                task["budget_wait_count"] += 1
                budget_waits[key] = {"task": event.get("task_id"), "wait_id": payload["wait_id"],
                    "begin_event": event["event_id"], "begin_min": _minutes(when, origin),
                    "reason": payload["reason"], "active_hold_ids": payload.get("active_hold_ids", []),
                    "outcome": "unfinished"}
            else:
                duration = float(payload["elapsed_seconds"])
                task["budget_wait_seconds"] += duration
                task["budget_wait_outcomes"][payload["outcome"]] += 1
                budget_waits.setdefault(key, {"task": event.get("task_id"), "wait_id": payload["wait_id"],
                                             "begin_event": None}).update(
                    end_event=event["event_id"], end_min=_minutes(when, origin),
                    elapsed_seconds=duration, outcome=payload["outcome"])
    rows = []
    for name, task in sorted(tasks.items(), key=lambda item: item[1]["start"] or 0):
        seconds = task["request_seconds"]
        total_input = task["input_tokens"] + task["cache_read_tokens"] + task["cache_creation_tokens"]
        rows.append({
            "task": name, "parent": task["parent"], "start_min": _minutes(task["start"], origin),
            "first_request_min": _minutes(task["first_request"], origin),
            **{f"{label}_min": _minutes(value, origin) for label, value in task["milestones"].items()},
            "end_min": _minutes(task["end"], origin), "requests": task["requests"],
            "responses": task["responses"], "requests_missing_usage": task["requests"] - task["usage_responses"],
            "model_min": round(sum(seconds) / 60, 1), "median_request_s": round(statistics.median(seconds), 1) if seconds else None,
            "output_tokens": task["output_tokens"], "refused": task["refused"], "tool_errors": task["tool_errors"],
            "tool_outcomes": dict(task["tool_outcomes"]), "compactions": task["compactions"],
            "budget_wait_count": task["budget_wait_count"],
            "budget_wait_seconds": round(task["budget_wait_seconds"], 3),
            "budget_wait_outcomes": dict(task["budget_wait_outcomes"]),
            "input_tokens": task["input_tokens"], "cache_read_tokens": task["cache_read_tokens"],
            "cache_creation_tokens": task["cache_creation_tokens"],
            "cache_read_ratio": task["cache_read_tokens"] / total_input if total_input else None,
            "tools": dict(task["tools"].most_common())})
    return {"run": run.name, "format": "events", "schema_version": 2,
            "total_min": _minutes(max(t["end"] or 0 for t in tasks.values()), origin),
            "partial_tail": partial_tail, "last_event_id": events[-1]["event_id"],
            "tasks": rows, "requests": list(requests.values()), "timeline": timeline,
            "budget_waits": list(budget_waits.values()),
            "capture_errors": capture_errors}


def observe_cli(run: Path) -> dict:
    agents: dict[str, dict] = {}
    names = {}
    for line in (run / "agent_stream.jsonl").open(encoding="utf-8"):
        event = json.loads(line)
        if event.get("type") != "assistant":
            continue
        owner = event.get("parent_tool_use_id") or "main"
        row = agents.setdefault(owner, {"turns": 0, "tools": collections.Counter(), "output_tokens": 0})
        row["turns"] += 1
        row["output_tokens"] += ((event.get("message") or {}).get("usage") or {}).get("output_tokens") or 0
        for block in (event.get("message") or {}).get("content") or []:
            if block.get("type") == "tool_use":
                row["tools"][block["name"].replace("mcp__bim__", "")] += 1
                if block["name"] == "Agent":
                    names[block["id"]] = (block.get("input") or {}).get("description")
    times, origin = collections.defaultdict(list), None
    for line in (run / "tools.jsonl").open(encoding="utf-8"):
        record = json.loads(line)
        origin = origin or record.get("time")
        times[record.get("action")].append(record.get("time"))
    receipt = json.loads((run / "agent_receipt.json").read_text(encoding="utf-8"))
    result = receipt.get("result") or {}
    return {"run": run.name, "format": "claude_code", "total_min": round(receipt.get("elapsed_seconds", 0) / 60, 1),
            "models": {k: {"output": v.get("outputTokens"), "cache_read": v.get("cacheReadInputTokens")}
                       for k, v in (result.get("modelUsage") or {}).items()},
            "cost_estimate_usd": result.get("total_cost_usd"),
            "key_times_min": {action: [_minutes(t, origin) for t in values][:3] for action, values in times.items()
                              if action in MILESTONES or action in ("revise_bim", "record_claims", "overlay_candidate")},
            "agents": [{"agent": "main" if owner == "main" else f"worker:{names.get(owner, owner)}",
                        "turns": row["turns"], "output_tokens": row["output_tokens"],
                        "tools": dict(row["tools"].most_common())} for owner, row in agents.items()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    report = observe_events(args.run) if (args.run / "events.jsonl").is_file() else observe_cli(args.run)
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
