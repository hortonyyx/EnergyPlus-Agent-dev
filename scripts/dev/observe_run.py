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

MILESTONES = {"trial_plan_bim": "first_trial", "submit_plan_reading": "submitted",
              "submit_elevation_reading": "submitted", "assemble_from_readers": "first_assembly",
              "finish_bim": "delivered", "build_plan_bim": "first_build", "assemble_plan_bim": "first_assembly"}


def _stamp(event):
    value = (event.get("occurred_at") or {}).get("value")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() if value else None


def _minutes(value, origin):
    return None if value is None else round((value - origin) / 60, 1)


def observe_events(run: Path) -> dict:
    events = [json.loads(line) for line in (run / "events.jsonl").open(encoding="utf-8")]
    origin = min(t for t in map(_stamp, events) if t)
    tasks: dict[str, dict] = {}
    sent: dict[str, float] = {}
    for event in events:
        when, payload = _stamp(event), event.get("payload") or {}
        kind = payload.get("event_type")
        task = tasks.setdefault(event.get("task_id"), {
            "parent": (event.get("parent_task") or {}).get("task_id"), "start": when, "end": when,
            "first_request": None, "requests": 0, "request_seconds": [], "output_tokens": 0,
            "refused": 0, "tools": collections.Counter(), "tool_errors": 0, "milestones": {}})
        if when:
            task["start"] = min(task["start"] or when, when)
            task["end"] = max(task["end"] or when, when)
        if kind == "adapter_request":
            sent[event["event_id"]] = when
            task["first_request"] = task["first_request"] or when
        elif kind == "model_response":
            task["requests"] += 1
            began = sent.get(payload.get("request_event_id"))
            if began and when:
                task["request_seconds"].append(when - began)
            usage = (payload.get("usage") or {}).get("raw_usage") or {}
            task["output_tokens"] += usage.get("output_tokens") or 0
        elif kind == "model_failure" or (kind == "run_lifecycle" and payload.get("model_failure")):
            task["refused"] += 1
        elif kind == "tool_invocation":
            name = payload.get("tool_name")
            task["tools"][name] += 1
            label = MILESTONES.get(name)
            if label and label not in task["milestones"]:
                task["milestones"][label] = when
        elif kind == "tool_execution" and (payload.get("error") or payload.get("is_error")):
            task["tool_errors"] += 1
    rows = []
    for name, task in sorted(tasks.items(), key=lambda item: item[1]["start"] or 0):
        seconds = task["request_seconds"]
        rows.append({
            "task": name, "parent": task["parent"], "start_min": _minutes(task["start"], origin),
            "first_request_min": _minutes(task["first_request"], origin),
            **{f"{label}_min": _minutes(value, origin) for label, value in task["milestones"].items()},
            "end_min": _minutes(task["end"], origin), "requests": task["requests"],
            "model_min": round(sum(seconds) / 60, 1), "median_request_s": round(statistics.median(seconds), 1) if seconds else None,
            "output_tokens": task["output_tokens"], "refused": task["refused"], "tool_errors": task["tool_errors"],
            "tools": dict(task["tools"].most_common())})
    return {"run": run.name, "format": "events", "total_min": _minutes(max(t["end"] or 0 for t in tasks.values()), origin),
            "tasks": rows}


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
