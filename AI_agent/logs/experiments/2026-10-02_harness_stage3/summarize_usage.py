#!/usr/bin/env python3
"""Summarize durable role-run estimates and reported provider usage.

This is a read-only evidence tool except for an explicitly requested output
file. Local reservations and outstanding holds are kept separate from provider
usage; neither is treated as a verified provider bill or price.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DEFAULT_CALIBRATION_SUMMARY = HERE / "calibration/summary.json"
DEFAULT_CALIBRATION_ATTEMPTS = HERE / "calibration/attempts.json"
SCHEMA = "harness-stage3-role-usage/v1"
ROLE_ATTEMPT_LIMIT = 60
CALIBRATION_ATTEMPT_LIMIT = 20


def _inside_worktree(path: Path, *, must_exist: bool = True) -> Path:
    resolved = path.resolve(strict=must_exist)
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"path must stay inside this worktree: {path}")
    return resolved


def _read_bytes(path: Path) -> bytes:
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    ):
        raise ValueError(f"file changed while it was read: {path}")
    return data


def _read_json(path: Path) -> Any:
    return json.loads(_read_bytes(path))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    raw = _read_bytes(path)
    if raw and not raw.endswith(b"\n"):
        raise ValueError(f"incomplete JSONL tail: {path}")
    return [json.loads(line) for line in raw.splitlines()]


def _read_source(run: Path, source: dict[str, Any]) -> Any:
    ref = source["blob"]
    path = (run / ref["uri"]).resolve(strict=True)
    if not path.is_relative_to(run):
        raise ValueError("source blob escapes its run")
    data = _read_bytes(path)
    if hashlib.sha256(data).hexdigest() != ref["sha256"]:
        raise ValueError(f"source blob hash mismatch: {path}")
    return json.loads(data)


def _source_value(run: Path, event: dict[str, Any], source_id: str) -> Any | None:
    matches = [source for source in event.get("source_refs", ())
               if source.get("source_id") == source_id]
    if len(matches) > 1:
        raise ValueError(f"duplicate {source_id!r} sources in {event['event_id']}")
    return _read_source(run, matches[0]) if matches else None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _percent(delta: int, actual: int | None) -> float | None:
    if actual is None or actual == 0:
        return None
    return round(delta * 100.0 / actual, 6)


def _usage_fields(usage: dict[str, Any] | None) -> dict[str, Any]:
    if not usage or usage.get("kind") != "reported":
        return {
            "status": "missing",
            "raw": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "image_tokens": None,
            "reasoning_tokens": None,
        }
    raw = usage.get("raw_usage", {})
    prompt = _integer(raw.get("prompt_tokens", raw.get("input_tokens")))
    completion = _integer(raw.get("completion_tokens", raw.get("output_tokens")))
    total = _integer(raw.get("total_tokens"))
    prompt_details = raw.get("prompt_tokens_details", raw.get("input_tokens_details", {}))
    completion_details = raw.get(
        "completion_tokens_details", raw.get("output_tokens_details", {})
    )
    image = _integer(prompt_details.get("image_tokens")) if isinstance(prompt_details, dict) else None
    reasoning = (_integer(completion_details.get("reasoning_tokens"))
                 if isinstance(completion_details, dict) else None)
    status = "reported" if prompt is not None else "reported_without_prompt_tokens"
    return {
        "status": status,
        "raw": raw,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "image_tokens": image,
        "reasoning_tokens": reasoning,
    }


def _thinking_fields(response: dict[str, Any] | None, usage: dict[str, Any]) -> dict[str, Any]:
    items = response["payload"].get("thinking", ()) if response else ()
    public = [item for item in items if item.get("kind") == "public_content"]
    explicit_counts = [item.get("tokens") for item in items
                       if item.get("kind") == "reported_token_count"
                       and _integer(item.get("tokens")) is not None]
    return {
        "public_content_items": len(public),
        "public_content_characters": sum(len(item.get("content", "")) for item in public),
        "summary_items": sum(item.get("kind") == "summary" for item in items),
        "signature_items": sum(item.get("kind") == "signature" for item in items),
        "unavailable_items": sum(item.get("kind") == "unavailable" for item in items),
        "event_reported_thinking_tokens": sum(explicit_counts) if explicit_counts else None,
        "usage_reported_reasoning_tokens": usage["reasoning_tokens"],
    }


def _discover_runs(roots: Iterable[Path]) -> tuple[list[Path], list[Path]]:
    runs: set[Path] = set()
    attempt_logs: set[Path] = set()
    for supplied in roots:
        root = _inside_worktree(supplied)
        if root.is_file():
            if root.name != "events.jsonl":
                raise ValueError(f"role input file must be events.jsonl: {root}")
            runs.add(root.parent)
            continue
        direct_attempts = root / "role_requests.jsonl"
        if direct_attempts.is_file():
            attempt_logs.add(direct_attempts.resolve())
        direct_events = root / "events.jsonl"
        if direct_events.is_file():
            runs.add(root)
        else:
            runs.update(path.parent.resolve() for path in root.rglob("events.jsonl"))
    return sorted(runs), sorted(attempt_logs)


def _summarize_run(run: Path) -> list[dict[str, Any]]:
    events = _read_jsonl(run / "events.jsonl")
    requests = {event["event_id"]: event for event in events
                if event["payload"]["event_type"] == "adapter_request"}
    responses: dict[str, dict[str, Any]] = {}
    decisions: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    settlements: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = event["payload"]
        if payload["event_type"] == "model_response":
            request_id = payload["request_event_id"]
            if request_id in responses:
                raise ValueError(f"duplicate response for {request_id} in {run}")
            responses[request_id] = event
        if payload["event_type"] == "budget" and payload.get("action") == "reserve":
            decision = _source_value(run, event, "request-budget-decision")
            if decision is not None:
                reservation_id = payload["reservation"]["reservation_id"]
                decisions[reservation_id] = (event, decision)
        if payload["event_type"] == "budget" and payload.get("action") == "settle":
            settlement = payload["settlement"]
            settlements[settlement["reservation_id"]] = settlement

    rows = []
    for request_id, request in sorted(requests.items(), key=lambda item: item[1]["sequence"]):
        reservation_id = request["payload"].get("reservation_id")
        if not reservation_id or reservation_id not in decisions:
            raise ValueError(f"request {request_id} has no estimation decision")
        _, decision = decisions[reservation_id]
        estimate = decision.get("token_estimate")
        if not isinstance(estimate, dict):
            raise ValueError(f"request {request_id} has no token_estimate evidence")
        model = estimate.get("model")
        if not isinstance(model, str) or not model:
            raise ValueError(f"request {request_id} has no estimated model identity")
        response = responses.get(request_id)
        usage = _usage_fields(response["payload"].get("usage") if response else None)
        prompt = usage["prompt_tokens"]
        point = _integer(estimate.get("input_tokens_estimate"))
        upper = _integer(estimate.get("input_tokens_upper_bound"))
        if point is None or upper is None:
            raise ValueError(f"request {request_id} has invalid token estimates")
        duration = _source_value(run, response, "request-duration") if response else None
        elapsed = duration.get("elapsed_seconds") if isinstance(duration, dict) else None
        elapsed = float(elapsed) if isinstance(elapsed, (int, float)) else None
        settlement = settlements.get(reservation_id)
        reservation_tokens = decision.get("reservation", {}).get("amounts", {}).get("tokens")
        settled_tokens = (settlement.get("actual", {}).get("tokens")
                          if settlement is not None else None)
        predicted_image = _integer(estimate.get("image_tokens"))
        reported_image = usage["image_tokens"]
        point_delta = point - prompt if prompt is not None else None
        upper_delta = upper - prompt if prompt is not None else None
        point_percent = (_percent(point_delta, prompt)
                         if point_delta is not None else None)
        rows.append({
            "role_root": run.relative_to(ROOT).as_posix(),
            "run_id": request["run_id"],
            "task_id": request["task_id"],
            "request_event_id": request_id,
            "response_event_id": response["event_id"] if response else None,
            "reservation_id": reservation_id,
            "model": model,
            "profile_name": estimate.get("profile_name"),
            "estimate_source": estimate.get("source"),
            "input_estimate": {
                "point_tokens": point,
                "upper_bound_tokens": upper,
                "text_tokens": _integer(estimate.get("text_tokens")),
                "image_tokens": predicted_image,
            },
            "reported_usage": usage,
            "error": {
                "point_tokens": point_delta,
                "point_percent": point_percent,
                "point_absolute_percent": (abs(point_percent)
                                           if point_percent is not None else None),
                "upper_tokens": upper_delta,
                "upper_percent": (_percent(upper_delta, prompt)
                                  if upper_delta is not None else None),
                "upper_covers_actual": upper >= prompt if prompt is not None else None,
                "image_tokens": (predicted_image - reported_image
                                 if predicted_image is not None and reported_image is not None
                                 else None),
            },
            "thinking": _thinking_fields(response, usage),
            "duration_seconds": elapsed,
            "local_budget": {
                "reservation_tokens": reservation_tokens,
                "settled_actual_tokens": settled_tokens,
                "outstanding_hold_tokens": (reservation_tokens
                                            if settlement is None else None),
            },
        })
    return rows


def _known_sum(values: Iterable[int | None]) -> tuple[int | None, int]:
    known = [value for value in values if value is not None]
    return (sum(known) if known else None, len(known))


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["model"])].append(row)
    result = {}
    for model, model_rows in sorted(grouped.items()):
        point_errors = [row["error"]["point_percent"] for row in model_rows
                        if row["error"]["point_percent"] is not None]
        absolute_errors = [abs(value) for value in point_errors]
        upper_rows = [row for row in model_rows
                      if row["error"]["upper_covers_actual"] is not None]
        image_errors = [row["error"]["image_tokens"] for row in model_rows
                        if row["error"]["image_tokens"] is not None]
        durations = [row["duration_seconds"] for row in model_rows
                     if row["duration_seconds"] is not None]
        prompt_total, prompt_count = _known_sum(
            row["reported_usage"]["prompt_tokens"] for row in model_rows)
        completion_total, completion_count = _known_sum(
            row["reported_usage"]["completion_tokens"] for row in model_rows)
        total_tokens, total_count = _known_sum(
            row["reported_usage"]["total_tokens"] for row in model_rows)
        reasoning_total, reasoning_count = _known_sum(
            row["thinking"]["usage_reported_reasoning_tokens"] for row in model_rows)
        result[model] = {
            "requests": len(model_rows),
            "responses": sum(row["response_event_id"] is not None for row in model_rows),
            "missing_usage_requests": sum(row["reported_usage"]["status"] != "reported"
                                          for row in model_rows),
            "tokens": {
                "estimated_input_point": sum(row["input_estimate"]["point_tokens"]
                                             for row in model_rows),
                "estimated_input_upper_bound": sum(
                    row["input_estimate"]["upper_bound_tokens"] for row in model_rows),
                "reported_prompt": prompt_total,
                "reported_prompt_requests": prompt_count,
                "reported_completion": completion_total,
                "reported_completion_requests": completion_count,
                "reported_total": total_tokens,
                "reported_total_requests": total_count,
            },
            "input_estimation_error": {
                "measured_requests": len(point_errors),
                "mean_signed_percent": round(mean(point_errors), 6) if point_errors else None,
                "mean_absolute_percent": round(mean(absolute_errors), 6) if absolute_errors else None,
                "maximum_absolute_percent": round(max(absolute_errors), 6) if absolute_errors else None,
                "upper_bound_covered_requests": sum(
                    row["error"]["upper_covers_actual"] is True for row in upper_rows),
                "upper_bound_measured_requests": len(upper_rows),
                "upper_bound_coverage_percent": round(
                    100 * sum(row["error"]["upper_covers_actual"] is True for row in upper_rows)
                    / len(upper_rows), 6) if upper_rows else None,
            },
            "image_estimation": {
                "reported_requests": len(image_errors),
                "exact_matches": sum(value == 0 for value in image_errors),
                "mean_absolute_token_error": round(mean(abs(value) for value in image_errors), 6)
                    if image_errors else None,
                "maximum_absolute_token_error": max((abs(value) for value in image_errors),
                                                     default=None),
            },
            "thinking": {
                "public_content_items": sum(row["thinking"]["public_content_items"]
                                            for row in model_rows),
                "public_content_characters": sum(
                    row["thinking"]["public_content_characters"] for row in model_rows),
                "reported_reasoning_tokens": reasoning_total,
                "reported_reasoning_token_requests": reasoning_count,
            },
            "duration_seconds": {
                "measured_requests": len(durations),
                "total": round(sum(durations), 6) if durations else None,
                "mean": round(mean(durations), 6) if durations else None,
                "maximum": round(max(durations), 6) if durations else None,
            },
        }
    return result


def _attempt_summary(paths: list[Path]) -> dict[str, Any]:
    records = []
    files = []
    for path in paths:
        rows = _read_jsonl(path)
        attempts = [row for row in rows if row.get("event") == "attempt"]
        records.extend({"file": path.relative_to(ROOT).as_posix(), **row} for row in attempts)
        files.append(path.relative_to(ROOT).as_posix())
    count = len(records)
    if count > ROLE_ATTEMPT_LIMIT:
        raise ValueError(f"role attempt limit exceeded: {count} > {ROLE_ATTEMPT_LIMIT}")
    return {"files": files, "attempts": count, "limit": ROLE_ATTEMPT_LIMIT,
            "within_limit": True, "records": records}


def _calibration_summary(summary_path: Path, attempts_path: Path) -> dict[str, Any]:
    summary = _read_json(_inside_worktree(summary_path))
    attempts = _read_json(_inside_worktree(attempts_path))
    count = _integer(attempts.get("attempts_reserved"))
    if count is None:
        raise ValueError("calibration attempts counter is missing")
    if count > CALIBRATION_ATTEMPT_LIMIT:
        raise ValueError(
            f"calibration attempt limit exceeded: {count} > {CALIBRATION_ATTEMPT_LIMIT}"
        )
    if _integer(summary.get("requests")) != count:
        raise ValueError("calibration summary and durable attempt counter disagree")
    return {
        "separate_from_role_usage": True,
        "attempts": count,
        "limit": CALIBRATION_ATTEMPT_LIMIT,
        "within_limit": True,
        "summary_path": summary_path.resolve().relative_to(ROOT).as_posix(),
        "attempts_path": attempts_path.resolve().relative_to(ROOT).as_posix(),
        "summary": summary,
    }


def summarize(role_roots: Iterable[Path], *, calibration_summary: Path,
              calibration_attempts: Path) -> dict[str, Any]:
    role_roots = tuple(role_roots)
    runs, attempt_logs = _discover_runs(role_roots)
    if not runs:
        raise ValueError("no role events.jsonl files found")
    if not attempt_logs:
        raise ValueError("no shared role_requests.jsonl attempt journal found")
    rows = [row for run in runs for row in _summarize_run(run)]
    role_attempts = _attempt_summary(attempt_logs)
    role_attempts["event_requests"] = len(rows)
    role_attempts["matches_event_requests"] = role_attempts["attempts"] == len(rows)
    outstanding = [row for row in rows
                   if row["local_budget"]["outstanding_hold_tokens"] is not None]
    reported_total, reported_count = _known_sum(
        row["reported_usage"]["total_tokens"] for row in rows)
    return {
        "schema_version": SCHEMA,
        "role_usage": {
            "roots": [path.resolve().relative_to(ROOT).as_posix() for path in role_roots],
            "runs": len(runs),
            "requests": len(rows),
            "reported_total_tokens": reported_total,
            "reported_total_token_requests": reported_count,
            "missing_usage_requests": sum(row["reported_usage"]["status"] != "reported"
                                          for row in rows),
            "outstanding_local_holds": {
                "requests": len(outstanding),
                "tokens": sum(row["local_budget"]["outstanding_hold_tokens"]
                              for row in outstanding),
                "accounting": "local conservative reservations, excluded from reported usage",
            },
            "attempt_counter": role_attempts,
            "by_model": _aggregate(rows),
            "per_request": rows,
        },
        "calibration": _calibration_summary(calibration_summary, calibration_attempts),
        "accounting_boundary": {
            "unknown_usage": "null and excluded from sums; never counted as zero",
            "provider_bill_or_price": "unverified; no USD billing total is asserted",
            "local_holds": "budget controls only; not provider token usage or a bill",
            "calibration": "reported separately and excluded from role usage aggregates",
        },
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("role_roots", nargs="+", type=Path)
    value.add_argument("--calibration-summary", type=Path,
                       default=DEFAULT_CALIBRATION_SUMMARY)
    value.add_argument("--calibration-attempts", type=Path,
                       default=DEFAULT_CALIBRATION_ATTEMPTS)
    value.add_argument("--output", "-o", type=Path,
                       help="write JSON here; omit to print to stdout")
    return value


def main() -> None:
    args = parser().parse_args()
    result = summarize(args.role_roots, calibration_summary=args.calibration_summary,
                       calibration_attempts=args.calibration_attempts)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        output = _inside_worktree(args.output, must_exist=False)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")


if __name__ == "__main__":
    main()
