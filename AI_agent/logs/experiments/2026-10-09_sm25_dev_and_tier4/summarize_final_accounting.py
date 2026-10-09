"""Write one compact, read-only final accounting artifact after root stop.

This is a projection over ``observe_runtime_accounting.observe`` plus public
event/task metadata. It does not open EventStore, acquire writer.lock, inspect
model messages, access credentials, read GT, or make network/model calls.
"""
from __future__ import annotations

import argparse
import collections
from decimal import Decimal
import json
import os
from pathlib import Path

from observe_runtime_accounting import observe, read_events, stamp


ROLES = ("coordinator", "plan_reader", "elevation_reader")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def role_map(run: Path) -> tuple[dict[str, str], dict[str, collections.Counter]]:
    roles = {"coordinator": "coordinator"}
    outcomes = {role: collections.Counter() for role in ROLES}
    for path in sorted((run / "tasks").glob("*/reader_task.json")):
        task = read_json(path)
        task_id, role = task.get("task_id"), task.get("role_id")
        if not isinstance(task_id, str) or role not in {"plan_reader", "elevation_reader"}:
            raise ValueError(f"invalid reader task metadata: {path}")
        if task_id in roles and roles[task_id] != role:
            raise ValueError(f"task role changed: {task_id}")
        roles[task_id] = role
        record = path.with_name("reader_record.json")
        status = read_json(record).get("status") if record.is_file() else "missing_record"
        outcomes[role][status] += 1
    return roles, outcomes


def sum_known(rows: list[dict], field: str):
    values = [row.get(field) for row in rows]
    if not values:
        return 0
    return sum(values) if all(isinstance(value, (int, float)) for value in values) else None


def sum_decimal_known(values: list[str | None]) -> str | None:
    if not values:
        return "0"
    if any(value is None for value in values):
        return None
    return str(sum((Decimal(value) for value in values), Decimal(0)))


def lifecycle_timings(events: list[dict], roles: dict[str, str], initialized_epoch: float,
                      root_stop_epoch: float) -> dict[str, dict]:
    boundaries = collections.defaultdict(lambda: {"starts": [], "stops": []})
    for event in events:
        payload = event.get("payload") or {}
        if payload.get("event_type") != "run_lifecycle":
            continue
        when = stamp(event)
        if when is None:
            continue
        action = payload.get("action")
        if action == "start":
            boundaries[event.get("task_id")]["starts"].append(when)
        elif action == "stop":
            boundaries[event.get("task_id")]["stops"].append(when)

    result = {}
    for role in ROLES:
        if role == "coordinator":
            result[role] = {
                "task_elapsed_seconds_sum": round(root_stop_epoch - initialized_epoch, 3),
                "role_wall_span_seconds": round(root_stop_epoch - initialized_epoch, 3),
                "lifecycle_complete": True,
                "task_elapsed_can_overlap": False,
            }
            continue
        task_ids = sorted(task for task, task_role in roles.items() if task_role == role)
        intervals, incomplete = [], []
        for task in task_ids:
            starts, stops = boundaries[task]["starts"], boundaries[task]["stops"]
            if not starts or not stops or stops[-1] < starts[0]:
                incomplete.append(task)
            else:
                intervals.append((starts[0], stops[-1]))
        result[role] = {
            "task_elapsed_seconds_sum": (
                round(sum(end - start for start, end in intervals), 3) if not incomplete else None
            ),
            "role_wall_span_seconds": (
                round(max(end for _, end in intervals) - min(start for start, _ in intervals), 3)
                if intervals and not incomplete else 0 if not task_ids else None
            ),
            "lifecycle_complete": not incomplete,
            "incomplete_tasks": incomplete,
            "task_elapsed_can_overlap": True,
        }
    return result


def compact_report(run: Path) -> dict:
    report = observe(run, audit_sample=0)
    events, partial_tail, invalid_lines = read_events(run / "events.jsonl")
    if partial_tail or invalid_lines:
        raise ValueError("event journal is not a complete clean JSONL file")
    root_stops = [event for event in events if event.get("task_id") == "coordinator"
                  and (event.get("payload") or {}).get("event_type") == "run_lifecycle"
                  and event["payload"].get("action") == "stop"]
    if len(root_stops) != 1:
        raise ValueError(f"final report requires exactly one root stop event, found {len(root_stops)}")
    receipt_path, summary_path = run / "receipt.json", run / "bim" / "summary.json"
    if not receipt_path.is_file() or not summary_path.is_file():
        raise ValueError("final report requires the terminal root receipt and bim/summary.json")
    receipt, summary = read_json(receipt_path), read_json(summary_path)
    if receipt.get("status") not in {"completed", "failed"}:
        raise ValueError("root receipt is not terminal")

    roles, outcomes = role_map(run)
    observed_tasks = {row["task"] for row in report["tasks"]}
    observed_tasks.update(row["task"] for row in report["tools"])
    unknown_tasks = sorted(task for task in observed_tasks if task not in roles)
    if unknown_tasks:
        raise ValueError("task metadata has no role mapping: " + ", ".join(unknown_tasks))

    inputs = read_json(run / "bim" / "inputs.json")
    initialized_epoch = inputs.get("started_epoch")
    root_stop_epoch = stamp(root_stops[0])
    if not isinstance(initialized_epoch, (int, float)) or root_stop_epoch is None:
        raise ValueError("run timing boundary is incomplete")
    timing = lifecycle_timings(events, roles, float(initialized_epoch), root_stop_epoch)

    task_rows = {row["task"]: row for row in report["tasks"]}
    tool_rows = {row["task"]: row for row in report["tools"]}
    request_rows = collections.defaultdict(list)
    for row in report["requests"]:
        request_rows[roles[row["task"]]].append(row)

    per_role = {}
    for role in ROLES:
        task_ids = sorted(task for task, task_role in roles.items() if task_role == role)
        model_rows = [task_rows[task] for task in task_ids if task in task_rows]
        tools = [tool_rows[task] for task in task_ids if task in tool_rows]
        requests = request_rows[role]
        accounting = [row.get("accounting") for row in requests]
        accounting_complete = len(accounting) == len(requests) and all(isinstance(row, dict) for row in accounting)
        accounting_rows = [row for row in accounting if isinstance(row, dict)]
        tool_names = collections.Counter()
        for row in tools:
            tool_names.update(row["tools"])
        prompts = sum_known(accounting_rows, "prompt_tokens") if accounting_complete else None
        cached = sum_known(accounting_rows, "cached_prompt_tokens") if accounting_complete else None
        costs = [row.get("settled_estimated_cost_cny") for row in model_rows]
        per_role[role] = {
            "tasks": len(task_ids),
            "task_outcomes": dict(sorted(outcomes[role].items())),
            "requests": len(requests),
            "responses": sum(row["status"] == "responded" for row in requests),
            "failed_requests": sum(row["status"] == "failed" for row in requests),
            "pending_requests": sum(row["status"] == "pending" for row in requests),
            **timing[role],
            "cumulative_model_request_seconds": round(sum(
                row.get("cumulative_model_request_seconds") or 0 for row in model_rows), 3),
            "prompt_tokens": prompts,
            "cached_prompt_tokens": cached,
            "uncached_prompt_tokens": (
                prompts - cached if prompts is not None and cached is not None else None
            ),
            "cache_over_prompt": round(cached / prompts, 6) if prompts and cached is not None else None,
            "output_tokens": sum_known(accounting_rows, "output_tokens") if accounting_complete else None,
            "reported_image_tokens": (
                sum_known(accounting_rows, "reported_image_tokens") if accounting_complete else None
            ),
            "image_tokens_estimate": (
                sum_known(accounting_rows, "image_tokens_estimate") if accounting_complete else None
            ),
            "additional_image_tokens": (
                sum_known(accounting_rows, "additional_image_tokens") if accounting_complete else None
            ),
            "provider_total_tokens": (
                sum_known(accounting_rows, "provider_total_tokens") if accounting_complete else None
            ),
            "budget_charge_tokens": (
                sum_known(accounting_rows, "budget_charge_tokens") if accounting_complete else None
            ),
            "settled_estimated_cost_cny": (
                sum_decimal_known(costs) if accounting_complete else None
            ),
            "accounting_complete": accounting_complete and all(
                row.get("accounting_complete") for row in model_rows
            ),
            "tool_invocations": sum(row["invocations"] for row in tools),
            "tool_executions": sum(row["executions"] for row in tools),
            "tool_pending": sum(row["pending"] for row in tools),
            "tool_errors": sum(row["errors"] for row in tools),
            "tools": dict(tool_names.most_common()),
        }

    totals = report["totals"]
    return {
        "schema_version": "manual_dispatch_final_accounting_v1",
        "run": str(run),
        "terminal": {
            "status": receipt.get("status"),
            "stop_reason": receipt.get("stop_reason"),
            "root_stop_event_id": root_stops[0].get("event_id"),
            "delivery_status": summary.get("delivery_status"),
            "source_fidelity": summary.get("source_fidelity", "not_evaluated"),
            "evaluation_status": summary.get("evaluation_status", "not_run"),
            "quality_passed": summary.get("quality_passed"),
        },
        "run_wall_seconds": round(root_stop_epoch - float(initialized_epoch), 3),
        "per_role": per_role,
        "totals": {
            key: totals.get(key) for key in (
                "requests", "responses", "pending", "failed",
                "prompt_tokens", "cached_prompt_tokens", "uncached_prompt_tokens",
                "output_tokens", "reported_image_tokens", "provider_total_tokens",
                "budget_charge_tokens", "settled_estimated_cost_cny",
                "model_calls_fraction", "tool_calls_fraction", "settled_cost_cny_fraction",
                "accounting_complete",
            )
        },
        "integrity": {
            "events": report["event_count"],
            "last_event_id": report["last_event_id"],
            "partial_tail_ignored": False,
            "invalid_complete_lines": 0,
            "settlement_mismatches": report["settlement_audit"]["mismatch_count"],
            "capture_errors": len(report["capture_errors"]),
            "unknown_task_roles": [],
        },
        "basis": {
            "source_helper": "observe_runtime_accounting.py",
            "cost": "settled runtime estimate from configured CNY rates; not a provider bill",
            "cache": "cached tokens are a subset of prompt tokens",
            "image": "provider totals do not add images again; budget charge follows settlements",
            "timing": "reader task elapsed sums may overlap; run wall is initialization to root stop",
            "quality": "generation completion and delivery do not imply source-fidelity or evaluator quality",
        },
    }


def write_json_atomic(path: Path, value: dict) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run, out = args.run.resolve(), args.out.resolve()
    if out.is_relative_to(run):
        raise ValueError("final accounting artifact must be outside the immutable run directory")
    result = compact_report(run)
    write_json_atomic(out, result)
    print(json.dumps({"status": "written", "artifact": str(out),
                      "requests": result["totals"]["requests"],
                      "cost_cny": result["totals"]["settled_estimated_cost_cny"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
