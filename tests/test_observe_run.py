"""Observation must distinguish attempts, outcomes and unavailable evidence."""
import hashlib
import json

import pytest

from scripts.dev.observe_run import observe_events


def _write_events(path, payloads):
    path.mkdir(exist_ok=True)
    rows = [{"event_id": f"e{i}", "task_id": "reader", "parent_task": {"task_id": "root"},
             "occurred_at": {"value": f"2026-10-09T00:00:{i:02d}Z"}, "payload": payload}
            for i, payload in enumerate(payloads)]
    (path / "events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_failed_submission_is_not_a_milestone_and_requests_include_failures(tmp_path):
    rejected = {"content": [{"type": "text", "text": json.dumps({"status": "rejected"})}]}
    raw = json.dumps(rejected).encode()
    (tmp_path / "result.json").write_bytes(raw)
    _write_events(tmp_path, [
        {"event_type": "adapter_request"},
        {"event_type": "model_response", "request_event_id": "e0", "usage": {"kind": "reported", "raw_usage": {
            "input_tokens": 10, "cache_read_input_tokens": 90, "output_tokens": 7}}},
        {"event_type": "tool_invocation", "tool_name": "submit_plan_reading"},
        {"event_type": "tool_execution", "tool_name": "submit_plan_reading", "outcome": "succeeded",
         "raw_result": {"kind": "blob", "blob": {"kind": "sha256", "uri": "result.json", "sha256": hashlib.sha256(raw).hexdigest(),
                                                    "media_type": "application/json"}}},
        {"event_type": "adapter_request"},
        {"event_type": "run_lifecycle", "model_failure": {"request_event_id": "e4", "category": "timeout"}},
        {"event_type": "tool_execution", "tool_name": "trial_plan_bim", "outcome": "unknown",
         "raw_result": {"kind": "missing", "reason": "interrupted"}},
        {"event_type": "tool_invocation", "tool_name": "submit_plan_reading"},
        {"event_type": "tool_execution", "tool_name": "submit_plan_reading", "outcome": "succeeded",
         "raw_result": {"kind": "inline", "value": {"structuredContent": {"status": "accepted"}, "isError": False}}},
    ])
    report = observe_events(tmp_path)
    task = report["tasks"][0]
    assert (task["requests"], task["responses"], task["requests_missing_usage"]) == (2, 1, 1)
    assert task["tool_outcomes"] == {"failed": 1, "unknown": 1, "succeeded": 1}
    assert task["submitted_min"] == round(8 / 60, 1)
    assert task["cache_read_ratio"] == 0.9
    assert "first_successful_trial_min" not in task
    assert report["requests"][1]["status"] == "failed"
    assert report["capture_errors"][0]["event"] == "e6"


def test_live_partial_tail_is_reported_but_corrupt_completed_line_is_rejected(tmp_path):
    _write_events(tmp_path, [{"event_type": "adapter_request"}])
    path = tmp_path / "events.jsonl"
    with path.open("ab") as handle:
        handle.write(b'{"event_id":')
    report = observe_events(tmp_path)
    assert report["partial_tail"] and report["requests"][0]["status"] == "pending"
    with path.open("ab") as handle:
        handle.write(b"\n")
    with pytest.raises(ValueError):
        observe_events(tmp_path)


def test_complete_json_without_commit_newline_is_not_observed(tmp_path):
    _write_events(tmp_path, [{"event_type": "adapter_request"}])
    path = tmp_path / "events.jsonl"
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    report = observe_events(tmp_path)
    assert report["partial_tail"] and report["tasks"] == []


def test_budget_wait_pairs_keep_unfinished_distinct_from_completed(tmp_path):
    _write_events(tmp_path, [
        {"event_type": "budget_wait", "phase": "begin", "wait_id": "wait1", "reason": "root_time_reservation",
         "active_hold_ids": ["sibling-reservation"]},
        {"event_type": "budget_wait", "phase": "end", "wait_id": "wait1", "reason": "root_time_reservation",
         "elapsed_seconds": "1.0", "outcome": "capacity_changed"},
        {"event_type": "budget_wait", "phase": "begin", "wait_id": "wait2", "reason": "root_time_reservation"},
    ])
    report = observe_events(tmp_path)
    assert report["tasks"][0]["budget_wait_count"] == 2
    assert report["tasks"][0]["budget_wait_seconds"] == 1
    assert [row["outcome"] for row in report["budget_waits"]] == ["capacity_changed", "unfinished"]
