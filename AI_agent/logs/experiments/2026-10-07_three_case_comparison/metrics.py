"""Summarize a scored comparison run: substantive errors vs dimensional deviations, time, usage (no model calls).

Usage: python metrics.py <run> [<run> ...]   (run names under AI_agent/archive/local_backup/cmp3; score with
evaluate.py first). Writes metrics_<run>.json next to this file and prints one line per run.
"""
import datetime as dt
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUNS = ROOT / "AI_agent/archive/local_backup/cmp3"


def stamp(event):
    value = (event.get("occurred_at") or {}).get("value")
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def timing(run_dir):
    """Per-task spans and request totals from the event log; the slowest reader is the critical path."""
    events = [json.loads(line) for line in (run_dir / "events.jsonl").open(encoding="utf-8")]
    start = min(t for t in map(stamp, events) if t)
    tasks, sent = {}, {}
    for event in events:
        when, task, payload = stamp(event), event.get("task_id"), event.get("payload") or {}
        row = tasks.setdefault(task, {"first": when, "last": when, "requests": 0, "output_tokens": 0, "model_seconds": 0.0})
        if when:
            row["first"] = min(row["first"] or when, when)
            row["last"] = max(row["last"] or when, when)
        if payload.get("event_type") == "adapter_request":
            sent[event["event_id"]] = when
        elif payload.get("event_type") == "model_response":
            row["requests"] += 1
            usage = (payload.get("usage") or {}).get("raw_usage") or {}
            row["output_tokens"] += usage.get("output_tokens") or 0
            began = sent.get(payload.get("request_event_id"))
            if began and when:
                row["model_seconds"] += (when - began).total_seconds()
    out = {}
    for task, row in tasks.items():
        out[str(task)] = {"start_min": round((row["first"] - start).total_seconds() / 60, 1),
                          "end_min": round((row["last"] - start).total_seconds() / 60, 1),
                          "requests": row["requests"], "output_tokens": row["output_tokens"],
                          "model_minutes": round(row["model_seconds"] / 60, 1)}
    return out


TIERS_M = (0.05, 0.10, 0.30)  # user 10-07: <=5 cm good, 5-10 cm fine, 10-30 cm not a main target, >30 cm needs dedicated work


def tiers(values):
    """Count deviations per user tier: <=5 cm, 5-10 cm, 10-30 cm, >30 cm."""
    counts = {"<=5cm": 0, "5-10cm": 0, "10-30cm": 0, ">30cm": 0}
    for value in values:
        key = "<=5cm" if value <= TIERS_M[0] + 1e-9 else "5-10cm" if value <= TIERS_M[1] + 1e-9             else "10-30cm" if value <= TIERS_M[2] + 1e-9 else ">30cm"
        counts[key] += 1
    return counts


def summarize(name):
    run_dir = RUNS / name
    receipt = json.loads((run_dir / "receipt.json").read_text(encoding="utf-8"))
    evaluation = json.loads((HERE / f"evaluation_{name}.json").read_text(encoding="utf-8"))
    candidate = evaluation["candidate"]
    partition = json.loads((HERE / "evaluation" / name / f"{candidate}_partition.json").read_text(encoding="utf-8"))
    comparison = partition["comparison"]
    matches = [m for m in comparison.get("matches", []) if isinstance(m, dict)]
    ious = [m["iou"] for m in matches if isinstance(m.get("iou"), (int, float))]
    hausdorff = [m["boundary_hausdorff_m"] for m in matches if isinstance(m.get("boundary_hausdorff_m"), (int, float))]
    severe = evaluation["severe"]
    substantive_codes = {"space_missing", "space_extra", "space_split", "space_merged", "partition_split", "partition_merged",
                         "false_floor", "connection_changed", "floor_assignment_changed"}
    substantive = [f["code"] for f in severe if f["code"] in substantive_codes
                   or (f["code"] == "opening_position_host_or_connection_changed"
                       and not (f.get("host_match", True) and f.get("connection_match", True)))]
    openings = [f for f in severe if f["code"] == "opening_position_host_or_connection_changed"]
    accounting = receipt.get("role_accounting") or receipt.get("root_usage_accounting") or receipt.get("usage_accounting") or {}
    reported = accounting.get("provider_reported_tokens")
    cached = accounting.get("reported_cache_read_tokens") or 0
    uncached = accounting.get("reported_input_tokens") or 0
    output = accounting.get("reported_output_tokens")
    if reported is None:  # e.g. requests rejected by the service before any usage: sum what the service did report
        cached = uncached = output = 0
        for line in (run_dir / "events.jsonl").open(encoding="utf-8"):
            payload = json.loads(line).get("payload") or {}
            if payload.get("event_type") == "model_response":
                usage = (payload.get("usage") or {}).get("raw_usage") or {}
                cached += usage.get("cache_read_input_tokens") or 0
                uncached += usage.get("input_tokens") or 0
                output += usage.get("output_tokens") or 0
        reported = cached + uncached + output
    quality = json.loads((HERE / "evaluation" / name / f"{candidate}_delivery_quality.json").read_text(encoding="utf-8"))
    opening_rows = quality["opening_inventory"].get("comparisons") or []
    height_rows = quality["exterior_heights"].get("comparisons") or []
    tasks = timing(run_dir)
    readers = {k: v for k, v in tasks.items() if k not in ("coordinator", "None")}
    plan = {k: v for k, v in readers.items() if k.startswith("plan")}
    slowest_plan = max(plan.values(), key=lambda v: v["end_min"]) if plan else None
    row = {
        "run": name, "candidate": candidate, "candidates_saved": evaluation["candidates_saved"],
        "minutes": round(receipt["elapsed_seconds"] / 60, 1),
        "requests": accounting.get("requests") or receipt.get("model_calls"),
        "tokens_reported": reported, "cache_read_share": round(cached / (cached + uncached), 3) if cached + uncached else None,
        "output_tokens": output,
        "rooms_matched": len(matches), "min_iou": round(min(ious), 3) if ious else None,
        "max_boundary_offset_m": round(max(hausdorff), 3) if hausdorff else None,
        "spaces_reference_candidate_matched": [comparison.get("reference_count"), comparison.get("candidate_count"),
                                               comparison.get("matched_count")],
        "strict_tolerance_m": comparison.get("tolerance_m"),
        "partition_finding_codes": sorted({f.get("code") for f in comparison.get("findings", []) if isinstance(f, dict)}),
        "substantive_findings": substantive,
        "openings": evaluation["openings"], "heights": evaluation["heights"],
        "opening_offsets_m": sorted(round(f.get("max_endpoint_error_m") or 0, 2) for f in openings),
        "tiers_opening_along_wall": tiers(r["max_endpoint_error_m"] for r in opening_rows),
        "openings_off_wall_over_30cm": sum(1 for r in opening_rows if r["perpendicular_error_m"] > TIERS_M[2]),
        "tiers_room_boundary": tiers(m["boundary_hausdorff_m"] for m in matches if isinstance(m.get("boundary_hausdorff_m"), (int, float))),
        "tiers_exterior_height": tiers(r["max_z_delta_m"] for r in height_rows if isinstance(r.get("max_z_delta_m"), (int, float))),
        "coordinator": tasks.get("coordinator") if readers else None,
        "slowest_plan_reader_end_min": slowest_plan["end_min"] if slowest_plan else None,
        "tasks": tasks,
    }
    (HERE / f"metrics_{name}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: row[k] for k in ("run", "minutes", "requests", "tokens_reported", "cache_read_share", "output_tokens",
                                          "spaces_reference_candidate_matched", "min_iou", "max_boundary_offset_m",
                                          "partition_finding_codes", "substantive_findings", "openings", "heights",
                                          "opening_offsets_m", "tiers_opening_along_wall", "openings_off_wall_over_30cm",
                                          "tiers_room_boundary", "tiers_exterior_height",
                                          "slowest_plan_reader_end_min", "candidates_saved")},
                     ensure_ascii=False))


if __name__ == "__main__":
    for run_name in sys.argv[1:]:
        summarize(run_name)
