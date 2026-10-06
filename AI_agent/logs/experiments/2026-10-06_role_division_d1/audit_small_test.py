"""Recalculate role statistics from saved evidence, without opening a run writer.

The live process predates the final D1 record seal and accounting additions.
This audit reads its original journal/receipts; it does not upgrade artifacts,
resume a reader, or make a provider request.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from src.agent.runtime_roles.accounting import role_accounting
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts


HERE = Path(__file__).resolve().parent


class ReadOnlyJournal:
    get_bytes = EventStore.get_bytes

    def __init__(self, directory):
        self.directory = directory.resolve()
        metadata = json.loads((directory / "journal.json").read_bytes())
        self.task_id = metadata["task_id"]
        self.budget_limit = BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"]))
        self.all_events = EventStore.read_events(directory / "events.jsonl")


class ReadOnlyRecords:
    def __init__(self, directory):
        self.records = {}
        self.paths = {}
        for path in sorted((directory / "tasks").glob("*/reader_record.json")):
            record = json.loads(path.read_bytes())
            self.records[record["task_id"]] = record
            self.paths[record["task_id"]] = path.parent

    def child(self, task_id):
        return SimpleNamespace(task_directory=self.paths[task_id])


def assess_passed_trial(run):
    """Compare the last successful intermediate draft, not a delivered artifact."""
    from math import dist
    from scipy.optimize import linear_sum_assignment
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    diagnosis = json.loads((HERE / "small_test_diagnosis.json").read_bytes())
    trial = [row for row in diagnosis["plan_reader"]["trials"] if row["status"] == "passed"][-1]
    receipt = HERE / trial["receipt"]
    trial_root = receipt.parent.parent
    actual_path = trial_root / trial["candidate"] / "source_model.json"
    root = HERE.parents[3]
    reference_root = root / "AI_agent/logs/experiments/2026-10-01_opus_dev_sm24"
    selection = json.loads((reference_root / "delivery_selection.json").read_bytes())
    reference_path = reference_root / selection["candidate"] / "source_model.json"
    actual, reference = (json.loads(p.read_bytes()) for p in (actual_path, reference_path))
    assert len(actual["floors"]) == len(reference["floors"]) == 1
    a_polys = [Polygon(row["polygon"]) for row in actual["spaces"]]
    r_polys = [Polygon(row["polygon"]) for row in reference["spaces"]]
    iou = lambda a, b: a.intersection(b).area / a.union(b).area
    costs = [[1 - iou(a, r) for a in a_polys] for r in r_polys]
    r_indices, a_indices = linear_sum_assignment(costs)
    rooms = [{"reference_id": reference["spaces"][int(r)]["id"],
              "trial_id": actual["spaces"][int(a)]["id"], "iou": 1 - costs[r][a]}
             for r, a in zip(r_indices, a_indices)]
    openings = []
    center = lambda o: tuple(sum(p[i] for p in o["vertices"]) / len(o["vertices"]) for i in (0, 1))
    width = lambda o: max(dist(a[:2], b[:2]) for a in o["vertices"] for b in o["vertices"])
    for kind in ("window", "door"):
        for exterior in (True, False):
            a_rows = [o for o in actual["openings"] if o["kind"] == kind and o["exterior"] == exterior]
            r_rows = [o for o in reference["openings"] if o["kind"] == kind and o["exterior"] == exterior]
            if not a_rows or not r_rows:
                continue
            costs = [[dist(center(r), center(a)) for a in a_rows] for r in r_rows]
            r_indices, a_indices = linear_sum_assignment(costs)
            for r, a in zip(r_indices, a_indices):
                openings.append({"reference_id": r_rows[r]["id"], "trial_id": a_rows[a]["id"],
                    "kind": kind, "exterior": exterior,
                    "center_xy_error_m": costs[r][a], "width_error_m": abs(width(r_rows[r]) - width(a_rows[a]))})
    count = lambda s: {"rooms": len(s["spaces"]),
                       **{k: sum(o["kind"] == k for o in s["openings"]) for k in ("window", "door")}}
    return {"status": "passed_trial_intermediate_not_validated_delivery",
        "reference_kind": "Opus 10-01 reviewed source, not exact ground truth",
        "source": actual_path.relative_to(root).as_posix(),
        "source_sha256": hashlib.sha256(actual_path.read_bytes()).hexdigest(),
        "reference": reference_path.relative_to(root).as_posix(),
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "counts": {"trial": count(actual), "reference": count(reference)},
        "footprint_iou": iou(unary_union(a_polys), unary_union(r_polys)),
        "room_assignment": "maximum one-to-one XY polygon IoU; same input world coordinates, no fitted alignment",
        "room_matches": rooms,
        "minimum_room_iou": min(row["iou"] for row in rooms),
        "opening_assignment": "minimum one-to-one XY center distance within same kind/exterior class",
        "opening_matches": openings,
        "opening_center_xy_error_mean_m": sum(o["center_xy_error_m"] for o in openings) / len(openings),
        "opening_center_xy_error_max_m": max(o["center_xy_error_m"] for o in openings),
        "opening_width_error_mean_m": sum(o["width_error_m"] for o in openings) / len(openings),
        "opening_width_error_max_m": max(o["width_error_m"] for o in openings),
        "quality_boundary": "These are geometric diagnostics of an intermediate draft. "
            "No final delivery, topology/room-type acceptance, or height accuracy is inferred; no new model call."}


def main():
    run = HERE / "small_test"
    before = {str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in run.rglob("*") if path.is_file()}
    store = ReadOnlyJournal(run)
    accounting = role_accounting(store, ReadOnlyRecords(run))
    original = json.loads((run / "small_test_result.json").read_bytes())
    trial_assessment = assess_passed_trial(run)
    after = {str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in run.rglob("*") if path.is_file()}
    assert before == after, "audit must not mutate original evidence"
    assert accounting["requests"] == original["accounting"]["requests"] == 28
    result = {
        "schema_version": "d1-small-test-posthoc-v1",
        "run": "small_test",
        "original_files_unchanged": True,
        "original_file_count": len(before),
        "journal_sha256": before["events.jsonl"],
        "wall_seconds": original["wall_seconds"],
        "new_model_requests": 0,
        "new_reader_tasks": 0,
        "live_version_label": sorted({e.payload.versions.agent_version.identifier
            for e in store.all_events if e.payload.event_type == "adapter_request"}),
        "version_boundary": "Live requests used the in-progress D1 source manifest under the previous registry label. "
            "They are not a live rerun of registered t1-20261006-d1.1. "
            "Final profile transport, failed-trial receipts, record seals and accounting were verified offline.",
        "accounting": accounting,
        "cache_fraction_of_reported_input": accounting["reported_cache_read_tokens"] /
            (accounting["reported_cache_read_tokens"] + accounting["reported_input_tokens"]),
        "subscription_money_note": "No per-request CNY bill; null is not a zero-cost claim.",
    }
    (HERE / "small_test_posthoc.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "small_test_plan_trial_assessment.json").write_text(
        json.dumps(trial_assessment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"requests": accounting["requests"],
        "wall_seconds": result["wall_seconds"],
        "cache_fraction": result["cache_fraction_of_reported_input"],
        "by_role": {role: {k: v for k, v in row.items() if k in {
            "requests", "reported_input_tokens", "reported_cache_read_tokens", "reported_output_tokens",
            "request_seconds", "task_elapsed_seconds_sum", "task_wall_span_seconds", "tool_calls",
            "format_errors", "repair_requests", "repair_successes", "repair_failures",
            "first_pass_rate", "after_repair_rate", "delivery_failures"}}
            for role, row in accounting["by_role"].items()},
        "intermediate_trial": {k: v for k, v in trial_assessment.items() if k in {
            "status", "counts", "footprint_iou", "minimum_room_iou", "opening_center_xy_error_mean_m",
            "opening_center_xy_error_max_m", "opening_width_error_mean_m", "opening_width_error_max_m"}}},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
