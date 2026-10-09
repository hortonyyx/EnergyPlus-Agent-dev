"""Read-only live accounting/behaviour view for a runtime events.jsonl run.

No EventStore is opened, no writer lock is acquired, and no run file is changed.
The script never reads model messages, visible text, raw responses, or reasoning.
It uses only event metadata, usage/settlement receipts, and public tool results.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path
import statistics
import sys

from pydantic import TypeAdapter


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent_runtime.accounting import (  # noqa: E402
    account_request_usage,
    get_cny_price_schedule,
)
from src.agent_runtime.store import EventStore  # noqa: E402
from src.harness_contracts.events import CapturedValue  # noqa: E402


MILESTONES = {
    "trial_plan_bim": "first_trial",
    "submit_plan_reading": "plan_submission",
    "submit_elevation_reading": "elevation_submission",
    "assemble_from_readers": "first_assembly",
    "build_plan_bim": "first_build",
    "assemble_plan_bim": "first_assembly",
    "finish_bim": "finish",
}


class _ReadOnlyCaptureStore(EventStore):
    """Use the production capture resolver without EventStore.__init__/locks."""

    def __init__(self, directory: Path):
        self.directory = directory.resolve()


def read_events(path: Path) -> tuple[list[dict], bool, int]:
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    events, partial_tail, invalid_lines = [], False, 0
    for index, line in enumerate(lines):
        if index == len(lines) - 1 and not line.endswith(b"\n"):
            partial_tail = True
            break
        try:
            events.append(json.loads(line))
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid_lines += 1
    return events, partial_tail, invalid_lines


def stamp(event: dict) -> float | None:
    value = (event.get("occurred_at") or {}).get("value")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() if value else None


def minutes(value: float | None, origin: float) -> float | None:
    return None if value is None else round((value - origin) / 60, 2)


def tool_body(store: _ReadOnlyCaptureStore, payload: dict) -> tuple[dict, dict, str | None]:
    capture = payload.get("raw_result")
    if not capture or capture.get("kind") == "missing":
        return {}, {}, "result not captured"
    try:
        raw = store.resolve(TypeAdapter(CapturedValue).validate_json(json.dumps(capture)))
    except (ValueError, OSError) as error:
        return {}, {}, f"{type(error).__name__}: {error}"
    if not isinstance(raw, dict):
        return {}, {}, None
    body = raw.get("structuredContent")
    if not isinstance(body, dict):
        body = raw
        for part in raw.get("content", []):
            if part.get("type") != "text":
                continue
            try:
                decoded = json.loads(part.get("text", ""))
            except (TypeError, ValueError):
                continue
            if isinstance(decoded, dict):
                body = decoded
                break
    return raw, body, None


def nested_counter(raw: dict, key: str) -> int | None:
    for details_name in ("prompt_tokens_details", "input_tokens_details"):
        details = raw.get(details_name)
        value = details.get(key) if isinstance(details, dict) else None
        if type(value) is int and value >= 0:
            return value
    return None


def add_optional(values: list[int | None]) -> int | None:
    return sum(values) if values and all(value is not None for value in values) else None


def decimal_sum(values: list[str | None]) -> str | None:
    return str(sum((Decimal(value) for value in values if value is not None), Decimal(0))) if values else None


def outcome_is_error(raw: dict, body: dict, payload: dict) -> bool:
    if payload.get("outcome") == "failed":
        return True
    return bool(raw.get("isError") or body.get("isError")
                or body.get("status") in {"rejected", "failed", "error"})


def observe(run: Path, audit_sample: int) -> dict:
    event_path = run / "events.jsonl"
    events, partial_tail, invalid_lines = read_events(event_path)
    if not events:
        raise ValueError("events.jsonl has no complete readable event")
    origin = min(value for value in map(stamp, events) if value is not None)
    observed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = json.loads((run / "manual_dispatch_manifest.json").read_text(encoding="utf-8"))
    limits = manifest.get("limits") or {}

    requests = {}
    responses = {}
    failures = {}
    settlements = {}
    invocations = {}
    executions = []
    lifecycle = collections.defaultdict(list)
    task_event_bounds = collections.defaultdict(list)
    for event in events:
        payload = event.get("payload") or {}
        kind, task, when = payload.get("event_type"), event.get("task_id"), stamp(event)
        if when is not None:
            task_event_bounds[task].append(when)
        if kind == "adapter_request":
            requests[event["event_id"]] = {"event": event, "time": when, "payload": payload}
        elif kind == "model_response":
            responses[payload.get("request_event_id")] = {"event": event, "time": when, "payload": payload}
        elif kind == "model_failure":
            failures[payload.get("request_event_id")] = {"event": event, "time": when, "payload": payload}
        elif kind == "run_lifecycle":
            lifecycle[task].append({"time": when, "payload": payload})
            failure = payload.get("model_failure")
            if isinstance(failure, dict) and failure.get("request_event_id"):
                failures[failure["request_event_id"]] = {"event": event, "time": when, "payload": failure}
        elif kind == "budget" and payload.get("action") == "settle":
            settlement = payload.get("settlement") or {}
            settlements[settlement.get("reservation_id")] = {"event": event, "time": when, "value": settlement}
        elif kind == "tool_invocation":
            invocations[event["event_id"]] = {"event": event, "time": when, "payload": payload}
        elif kind == "tool_execution":
            executions.append({"event": event, "time": when, "payload": payload})

    role_rows = collections.defaultdict(lambda: {
        "requests": 0, "responses": 0, "pending": 0, "failed": 0,
        "request_seconds": [], "accounting": [], "settled_costs": [],
    })
    request_rows = []
    accounting_audit = []
    settlement_mismatches = []
    for request_id, item in sorted(requests.items(), key=lambda pair: pair[1]["time"] or 0):
        event, payload, began = item["event"], item["payload"], item["time"]
        task = event.get("task_id")
        role = role_rows[task]
        role["requests"] += 1
        response, failure = responses.get(request_id), failures.get(request_id)
        status = "responded" if response else "failed" if failure else "pending"
        role[status if status != "responded" else "responses"] += 1
        ended = (response or failure or {}).get("time")
        if began is not None and ended is not None:
            role["request_seconds"].append(ended - began)
        request_row = {
            "request_event_id": request_id, "task": task, "status": status,
            "start_min": minutes(began, origin), "end_min": minutes(ended, origin),
        }
        if response:
            usage = (response["payload"].get("usage") or {})
            raw = usage.get("raw_usage") if usage.get("kind") == "reported" else None
            settlement_item = settlements.get(payload.get("reservation_id"))
            settlement = settlement_item["value"] if settlement_item else None
            identity = ((payload.get("versions") or {}).get("remote_model") or {})
            route_id, model = identity.get("route_id"), identity.get("remote_alias")
            image_estimate = (settlement or {}).get("image_tokens_estimate") or 0
            pricing = get_cny_price_schedule(model, route_id=route_id) if model and route_id else None
            normalized = account_request_usage(
                raw,
                image_tokens_estimate=image_estimate,
                pricing=pricing,
                billing_mode=("subscription" if route_id in {
                    "glm-subscription", "glm-subscription-anthropic"} else "metered_or_unknown"),
            )
            raw = raw or {}
            cached = (normalized.reported_cache_read_tokens
                      if normalized.reported_cache_read_tokens is not None
                      else nested_counter(raw, "cached_tokens"))
            text_tokens = nested_counter(raw, "text_tokens")
            reported_image = normalized.reported_image_tokens
            effective_tokens = None
            if settlement and (settlement.get("actual") or {}).get("tokens") is not None:
                actual_tokens = settlement["actual"]["tokens"]
                additional = settlement.get("additional_image_tokens")
                effective_tokens = actual_tokens + (additional if additional is not None else
                    0 if settlement.get("reported_usage_includes_image_tokens") else image_estimate)
            accounting = {
                "prompt_tokens": normalized.reported_input_tokens,
                "cached_prompt_tokens": cached,
                "uncached_prompt_tokens": (
                    normalized.reported_input_tokens - cached
                    if normalized.reported_input_tokens is not None and cached is not None else None),
                "text_tokens": text_tokens,
                "output_tokens": normalized.reported_output_tokens,
                "reported_image_tokens": reported_image,
                "provider_total_tokens": normalized.provider_reported_tokens,
                "image_tokens_estimate": normalized.image_tokens_estimate,
                "additional_image_tokens": normalized.additional_image_tokens,
                "budget_charge_tokens": effective_tokens,
                "estimated_cost_cny": (settlement or {}).get("estimated_cost_cny"),
                "usage_complete": normalized.provider_reported_tokens is not None,
                "cost_settled": bool(settlement and settlement.get("estimated_cost_cny") is not None),
            }
            role["accounting"].append(accounting)
            if accounting["estimated_cost_cny"] is not None:
                role["settled_costs"].append(accounting["estimated_cost_cny"])
            request_row["accounting"] = accounting
            receipt_checks = {
                "response_usage_equals_settlement_usage": bool(settlement and settlement.get("usage") == usage),
                "provider_total_equals_settlement_actual": bool(settlement and
                    normalized.provider_reported_tokens == (settlement.get("actual") or {}).get("tokens")),
                "normalizer_cost_equals_settlement_cost": bool(settlement and
                    str(normalized.estimated_cost_cny) == str(settlement.get("estimated_cost_cny"))),
                "normalizer_additional_images_equal_settlement": bool(settlement and
                    normalized.additional_image_tokens == settlement.get("additional_image_tokens")),
            }
            if not all(receipt_checks.values()):
                settlement_mismatches.append({"request_event_id": request_id, **receipt_checks})
            accounting_audit.append({
                "request_event_id": request_id, "task": task,
                "raw_usage": {
                    "prompt_tokens": raw.get("prompt_tokens"),
                    "cached_tokens": nested_counter(raw, "cached_tokens"),
                    "text_tokens": nested_counter(raw, "text_tokens"),
                    "image_tokens": nested_counter(raw, "image_tokens"),
                    "completion_tokens": raw.get("completion_tokens"),
                    "total_tokens": raw.get("total_tokens"),
                },
                "normalized": accounting,
                "receipt_checks": receipt_checks,
            })
        request_rows.append(request_row)

    task_summaries = []
    for task, role in sorted(role_rows.items()):
        accounting = role.pop("accounting")
        seconds = role.pop("request_seconds")
        prompts = [row["prompt_tokens"] for row in accounting]
        cached = [row["cached_prompt_tokens"] for row in accounting]
        uncached = [row["uncached_prompt_tokens"] for row in accounting]
        outputs = [row["output_tokens"] for row in accounting]
        images = [row["reported_image_tokens"] for row in accounting]
        provider_totals = [row["provider_total_tokens"] for row in accounting]
        budget_tokens = [row["budget_charge_tokens"] for row in accounting]
        prompt_total, cache_total, image_total = add_optional(prompts), add_optional(cached), add_optional(images)
        task_summaries.append({
            "task": task, **role,
            "cumulative_model_request_seconds": round(sum(seconds), 3),
            "request_time_can_overlap": True,
            "median_request_seconds": round(statistics.median(seconds), 3) if seconds else None,
            "prompt_tokens": prompt_total,
            "cached_prompt_tokens": cache_total,
            "uncached_prompt_tokens": add_optional(uncached),
            "cache_over_prompt": (round(cache_total / prompt_total, 6)
                                  if prompt_total and cache_total is not None else None),
            "output_tokens": add_optional(outputs),
            "reported_image_tokens": image_total,
            "image_over_prompt": (round(image_total / prompt_total, 6)
                                  if prompt_total and image_total is not None else None),
            "provider_total_tokens": add_optional(provider_totals),
            "budget_charge_tokens": add_optional(budget_tokens),
            "settled_estimated_cost_cny": decimal_sum(role["settled_costs"]),
            "accounting_complete": (role["pending"] == 0 and role["failed"] == 0
                                    and len(accounting) == role["responses"]
                                    and all(row["usage_complete"] and row["cost_settled"] for row in accounting)),
        })
        task_summaries[-1].pop("settled_costs", None)

    store = _ReadOnlyCaptureStore(run)
    tool_by_task = collections.defaultdict(collections.Counter)
    tool_outcomes = collections.defaultdict(collections.Counter)
    capture_errors = []
    milestones = {}
    for invocation_id, item in invocations.items():
        event, payload, when = item["event"], item["payload"], item["time"]
        task, name = event.get("task_id"), payload.get("tool_name")
        tool_by_task[task][name] += 1
        label = MILESTONES.get(name)
        if label:
            milestones.setdefault(label + "_attempt", {"task": task, "min": minutes(when, origin), "tool": name})
    for item in executions:
        event, payload, when = item["event"], item["payload"], item["time"]
        task, name = event.get("task_id"), payload.get("tool_name")
        raw, body, capture_error = tool_body(store, payload)
        if capture_error:
            capture_errors.append({"event_id": event["event_id"], "reason": capture_error})
        failed = outcome_is_error(raw, body, payload)
        tool_outcomes[task]["failed" if failed else "succeeded"] += 1
        label = MILESTONES.get(name)
        accepted = (not failed and not capture_error and
                    (body.get("status") in {None, "accepted", "passed", "completed", "not_evaluated"}))
        if label and accepted:
            milestones.setdefault(label + "_success", {
                "task": task, "min": minutes(when, origin), "tool": name,
                **({"candidate": body["candidate"]} if body.get("candidate") else {}),
            })

    execution_ids = {item["payload"].get("invocation_event_id") for item in executions}
    tool_rows = []
    for task in sorted(set(tool_by_task) | set(tool_outcomes)):
        tool_rows.append({
            "task": task,
            "invocations": sum(tool_by_task[task].values()),
            "executions": sum(tool_outcomes[task].values()),
            "pending": sum(1 for event_id, row in invocations.items()
                           if row["event"].get("task_id") == task and event_id not in execution_ids),
            "errors": tool_outcomes[task]["failed"],
            "tools": dict(tool_by_task[task].most_common()),
        })

    totals = {
        "requests": sum(row["requests"] for row in task_summaries),
        "responses": sum(row["responses"] for row in task_summaries),
        "pending": sum(row["pending"] for row in task_summaries),
        "failed": sum(row["failed"] for row in task_summaries),
    }
    for field in ("prompt_tokens", "cached_prompt_tokens", "uncached_prompt_tokens", "output_tokens", "reported_image_tokens",
                  "provider_total_tokens", "budget_charge_tokens"):
        totals[field] = add_optional([row[field] for row in task_summaries])
    costs = [row["settled_estimated_cost_cny"] for row in task_summaries
             if row["settled_estimated_cost_cny"] is not None]
    totals["settled_estimated_cost_cny"] = decimal_sum(costs)
    totals["accounting_complete"] = (totals["pending"] == 0 and totals["failed"] == 0
                                     and all(row["accounting_complete"] for row in task_summaries))
    totals["model_calls_fraction"] = [totals["requests"], limits.get("model_calls")]
    totals["tool_calls_fraction"] = [sum(row["invocations"] for row in tool_rows), limits.get("tool_calls")]
    totals["budget_tokens_fraction"] = [totals["budget_charge_tokens"], limits.get("tokens")]
    totals["settled_cost_cny_fraction"] = [totals["settled_estimated_cost_cny"], limits.get("money_cny")]
    totals["cache_over_prompt"] = (round(totals["cached_prompt_tokens"] / totals["prompt_tokens"], 6)
                                   if totals["prompt_tokens"] and totals["cached_prompt_tokens"] is not None else None)
    totals["image_over_prompt"] = (round(totals["reported_image_tokens"] / totals["prompt_tokens"], 6)
                                   if totals["prompt_tokens"] and totals["reported_image_tokens"] is not None else None)

    input_path = run / "bim" / "inputs.json"
    initialized_epoch = (json.loads(input_path.read_text(encoding="utf-8")).get("started_epoch")
                         if input_path.is_file() else origin)
    root_stops = [stamp(event) for event in events if event.get("task_id") == "coordinator"
                  and (event.get("payload") or {}).get("event_type") == "run_lifecycle"
                  and event["payload"].get("action") == "stop"]
    wall_end = root_stops[-1] if root_stops else dt.datetime.fromisoformat(observed_at).timestamp()
    return {
        "run": str(run), "observed_at_utc": observed_at,
        "event_count": len(events), "last_event_id": events[-1].get("event_id"),
        "partial_tail_ignored": partial_tail, "invalid_complete_lines": invalid_lines,
        "elapsed_minutes": minutes(max(value for value in map(stamp, events) if value is not None), origin),
        "run_wall_minutes": minutes(wall_end, initialized_epoch),
        "limits": {key: limits.get(key) for key in ("model_calls", "tool_calls", "seconds", "tokens", "money_cny")},
        "totals": totals, "tasks": task_summaries, "requests": request_rows,
        "tools": tool_rows, "milestones": milestones,
        "settlement_audit": {
            "settled_response_count": len(accounting_audit),
            "mismatch_count": len(settlement_mismatches),
            "mismatches": settlement_mismatches,
            "first_records": accounting_audit[:audit_sample],
            "normalizer": "src.agent_runtime.accounting.account_request_usage",
        },
        "capture_errors": capture_errors,
        "diagnostic_boundary": {
            "reporting_issue": ("scripts/dev/observe_run.py reads Anthropic-style input/output/cache keys directly; "
                                "Paratera reports prompt/completion and nested cached/image tokens, so zeros there "
                                "are an observer calculation defect."),
            "model_behaviour": ("Request failures, pending work, tool choices, tool errors and milestones above are "
                                "runtime evidence. This report does not infer model capability from the old zero-token display."),
            "token_note": ("prompt includes text plus reported image tokens; cached tokens are a subset of prompt text. "
                           "uncached_prompt equals prompt minus cached; do not add cache to prompt. provider_total is "
                           "provider prompt+completion and never adds images again. budget_charge separately adds the "
                           "image billing line recorded by settlement."),
            "cost_note": "CNY values are settled runtime estimates from configured rates, not provider bills.",
            "time_note": ("run_wall_minutes is initialization to observation or final root stop; elapsed_minutes is only the saved event span and excludes the current pending wait. Per-role cumulative model request seconds "
                          "can overlap under concurrency and must not be summed into wall time."),
        },
    }


def display(value) -> str:
    return "-" if value is None else str(value)


def print_table(report: dict) -> None:
    totals = report["totals"]
    print(f"run: {report['run']}")
    print(f"observed: {report['observed_at_utc']} | run wall: {report['run_wall_minutes']} min | saved event span: {report['elapsed_minutes']} min | "
          f"events: {report['event_count']} | partial_tail_ignored: {report['partial_tail_ignored']}")
    print("\n| role | req | resp | pending | failed | prompt | cached | uncached | cache/prompt | output | image/prompt | provider total | budget tokens | settled CNY | complete |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in report["tasks"]:
        print(f"| {row['task']} | {row['requests']} | {row['responses']} | {row['pending']} | {row['failed']} | "
              f"{display(row['prompt_tokens'])} | {display(row['cached_prompt_tokens'])} | "
              f"{display(row['uncached_prompt_tokens'])} | {display(row['cache_over_prompt'])} | "
              f"{display(row['output_tokens'])} | {display(row['image_over_prompt'])} | "
              f"{display(row['provider_total_tokens'])} | {display(row['budget_charge_tokens'])} | "
              f"{display(row['settled_estimated_cost_cny'])} | {row['accounting_complete']} |")
    print("\nTotals:")
    print(json.dumps({key: totals[key] for key in (
        "requests", "responses", "pending", "failed", "prompt_tokens", "cached_prompt_tokens", "uncached_prompt_tokens",
        "cache_over_prompt", "output_tokens", "reported_image_tokens", "image_over_prompt",
        "provider_total_tokens", "budget_charge_tokens", "settled_estimated_cost_cny",
        "model_calls_fraction", "tool_calls_fraction", "budget_tokens_fraction",
        "settled_cost_cny_fraction", "accounting_complete")}, ensure_ascii=False, indent=2))
    print("\nTools:")
    for row in report["tools"]:
        print(f"- {row['task']}: {row['invocations']} calls, {row['errors']} errors, "
              f"{row['pending']} pending; {row['tools']}")
    print("\nMilestones:")
    for name, row in report["milestones"].items():
        print(f"- {name}: {row}")
    audit = report["settlement_audit"]
    print(f"\nSettlement audit: {audit['settled_response_count']} settled responses, "
          f"{audit['mismatch_count']} mismatches; first {len(audit['first_records'])} records included in JSON mode.")
    print("\nBoundary: old zero-token observation is a reporting calculation defect; "
          "request/tool behaviour is reported separately above.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--format", choices=("table", "json", "both"), default="table")
    parser.add_argument("--audit-sample", type=int, default=2)
    args = parser.parse_args()
    if args.audit_sample < 0:
        raise SystemExit("--audit-sample must be non-negative")
    run = args.run.resolve()
    report = observe(run, args.audit_sample)
    if args.format in {"table", "both"}:
        print_table(report)
    if args.format == "both":
        print("\nJSON:")
    if args.format in {"json", "both"}:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
