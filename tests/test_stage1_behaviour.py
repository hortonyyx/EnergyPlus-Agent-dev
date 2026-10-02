"""Current-event and historical behaviour reader compatibility checks."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

from src.agent.runtime_behaviour import load_behaviour, render_timeline, write_behaviour_report


ROOT = Path(__file__).resolve().parents[1]
REPLAY_PATH = (
    ROOT
    / "AI_agent/logs/experiments/2026-10-02_harness_stage1/replay_history.py"
)


def _envelope(sequence: int, payload: dict, *, second: int) -> dict:
    return {
        "schema_version": "harness.event.v1",
        "event_id": f"event-{sequence}",
        "run_id": "new-run",
        "task_id": "main-task",
        "parent_task": {"kind": "root"},
        "sequence": sequence,
        "occurred_at": {"kind": "known", "value": f"2026-10-02T00:00:{second:02d}+00:00"},
        "source_refs": [],
        "payload": payload,
    }


def _response(sequence: int, calls: list[dict], *, second: int) -> dict:
    return _envelope(sequence, {
        "event_type": "model_response",
        "request_event_id": "request-omitted-from-reader-unit",
        "visible_text": ["inspect then build"],
        "tool_calls": calls,
        "thinking": [{"kind": "unavailable", "reason": "test provider did not expose it"}],
        "usage": {"kind": "reported", "raw_usage": {"input_tokens": 3, "output_tokens": 4}},
        "raw_response": {"kind": "inline", "value": {"id": f"response-{sequence}"}},
    }, second=second)


def _execution(sequence: int, call_id: str, tool: str, arguments: dict, result: dict,
               *, second: int, write: bool = False) -> dict:
    payload = {
        "event_type": "tool_execution",
        "call_id": call_id,
        "tool_name": tool,
        "full_arguments": arguments,
        "raw_result": {"kind": "inline", "value": result},
        "shown_result": {"kind": "inline", "value": result},
        "repeatability": "non_idempotent_write" if write else "read_only",
        "outcome": "succeeded",
        "capture_scope": "complete",
        "operation_key": f"operation:{call_id}" if write else None,
        "applied_write_id": f"write:{call_id}" if write else None,
        "retry_event_id": None,
        "invocation_event_id": None,
    }
    return _envelope(sequence, payload, second=second)


def test_current_event_log_preserves_first_draft_facade_and_height_metrics(tmp_path: Path) -> None:
    run = tmp_path / "new"
    run.mkdir()
    events = [
        _response(0, [
            {"call_id": "view", "tool_name": "view_image",
             "full_arguments": {"name": "East_view.png", "box": [10, 10, 40, 40]}},
            {"call_id": "build", "tool_name": "build_plan_bim",
             "full_arguments": {"image": "1f_view.png", "plan_json": "{}"}},
        ], second=0),
        _execution(1, "view", "view_image", {"name": "East_view.png", "box": [10, 10, 40, 40]},
                   {"name": "East_view.png", "box_original_pixels": [10, 10, 40, 40],
                    "original_size": [100, 100]}, second=2),
        _execution(2, "build", "build_plan_bim", {"image": "1f_view.png", "plan_json": "{}"},
                   {"candidate": "candidate_01"}, second=9, write=True),
        _response(3, [{"call_id": "claim", "tool_name": "record_claim",
                       "full_arguments": {"objects": [{"id": "W1"}]}}], second=11),
        _execution(4, "claim", "record_claim", {"objects": [{"id": "W1"}]},
                   {"id": "claim_0001", "claim": {"objects": [{"id": "W1"}], "reason": "height"},
                    "sources": [{"image": "East_view.png"}], "resolved_values": {"height": [1, 2.8]}},
                   second=12),
    ]
    (run / "events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in events))
    record = load_behaviour(run)
    summary = record["summary"]
    assert summary["source_format"] == "event_envelope_jsonl"
    assert summary["first_draft_s"] == 9.0
    assert summary["elevation_crops_by_facade"] == {"east": 1}
    assert summary["height_provenance_facades"] == {"east": 1}
    assert summary["gaps"] == []
    assert "行为记录：new-run" in render_timeline(record)


def test_legacy_cli_stream_and_bridge_audit_remain_readable(tmp_path: Path) -> None:
    cli = tmp_path / "cli"
    cli.mkdir()
    rows = [
        {"type": "system", "subtype": "init", "timestamp": "2026-10-02T00:00:00Z",
         "model": "legacy-model", "claude_code_version": "test"},
        {"type": "assistant", "timestamp": "2026-10-02T00:00:03Z", "message": {
            "id": "message-1", "usage": {"output_tokens": 2},
            "content": [{"type": "tool_use", "id": "call-1", "name": "mcp__bim__build_plan_bim",
                         "input": {"image": "plan.png", "plan_json": "{}"}}]}},
        {"type": "user", "timestamp": "2026-10-02T00:00:04Z", "message": {
            "content": [{"type": "tool_result", "tool_use_id": "call-1", "is_error": False,
                         "content": [{"type": "text", "text": "{\"candidate\":\"candidate_01\"}"}]}]}},
    ]
    with gzip.open(cli / "agent_stream.jsonl.gz", "wt") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    cli_record = load_behaviour(cli)
    assert cli_record["summary"]["first_draft_s"] == 3.0
    assert cli_record["summary"]["gaps"]

    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "tools.jsonl").write_text(json.dumps({
        "time": 10.0, "readonly": False, "action": "view_elevation_candidate",
        "data": {"facade": "West", "candidate": "candidate_01"},
    }) + "\n")
    bridge_record = load_behaviour(bridge)
    assert bridge_record["source_format"] == "legacy_bridge_audit"
    assert bridge_record["summary"]["elevation_overlays_by_facade"] == {"west": 1}
    assert any("call arguments" in gap for gap in bridge_record["gaps"])


def test_report_writer_keeps_full_record_compressed(tmp_path: Path) -> None:
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "tools.jsonl").write_text(json.dumps({
        "time": 1.0, "readonly": False, "action": "inputs", "data": {},
    }) + "\n")
    out = tmp_path / "report"
    write_behaviour_report(bridge, out)
    assert (out / "summary.json").is_file()
    assert (out / "timeline.md").is_file()
    with gzip.open(out / "record.json.gz", "rt") as stream:
        assert json.load(stream)["source_format"] == "legacy_bridge_audit"


def test_event_blob_is_hash_verified_resolved_and_confined_to_run(tmp_path: Path) -> None:
    run = tmp_path / "blob-run"
    blobs = run / "blobs"
    blobs.mkdir(parents=True)
    raw = json.dumps({"candidate": "candidate_01"}, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    (blobs / digest).write_bytes(raw)
    response = _response(0, [{"call_id": "build", "tool_name": "build_plan_bim",
                              "full_arguments": {"image": "plan.png", "plan_json": "{}"}}], second=0)
    execution = _execution(1, "build", "build_plan_bim",
                           {"image": "plan.png", "plan_json": "{}"}, {}, second=3, write=True)
    capture = {"kind": "blob", "blob": {"kind": "sha256", "uri": f"blobs/{digest}",
                                            "media_type": "application/json", "sha256": digest}}
    execution["payload"]["raw_result"] = capture
    execution["payload"]["shown_result"] = capture
    (run / "events.jsonl").write_text(json.dumps(response) + "\n" + json.dumps(execution) + "\n")
    record = load_behaviour(run)
    assert record["invocations"][0]["steps"][0]["result"] == {"candidate": "candidate_01"}

    outside = tmp_path / "outside.json"
    outside.write_bytes(raw)
    escaped = json.loads(json.dumps(execution))
    escaped["payload"]["raw_result"]["blob"]["uri"] = "../outside.json"
    escaped["payload"]["shown_result"]["blob"]["uri"] = "../outside.json"
    (run / "events.jsonl").write_text(json.dumps(response) + "\n" + json.dumps(escaped) + "\n")
    import pytest
    with pytest.raises(ValueError, match="escapes event-log directory"):
        load_behaviour(run)


def test_semantic_comparison_separates_geometry_hosts_and_connectivity() -> None:
    spec = importlib.util.spec_from_file_location("stage1_replay_history", REPLAY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    before = {
        "floors": [{"id": "F1", "footprint": [[0, 0], [1, 0], [1, 1]], "z_floor": 0, "height": 3}],
        "spaces": [{"id": "R1", "floor_id": "F1", "polygon": [[0, 0], [1, 0], [1, 1]], "z_floor": 0, "height": 3}],
        "boundaries": [{"id": "B1", "space_id": "R1", "geometry_type": "wall", "vertices": [[0, 0, 0], [1, 0, 0]]}],
        "openings": [{"id": "D1", "kind": "door", "host_boundary_id": "B1", "space_ids": ["R1"],
                      "vertices": [[0.2, 0, 0], [0.8, 0, 0], [0.8, 0, 2]], "exterior": True}],
        "opening_hosts": {"D1": ["B1"]},
        "connections": [{"opening_id": "D1", "space_ids": ["R1"], "exterior": True}],
    }
    after = json.loads(json.dumps(before))
    after["openings"][0]["vertices"][0][0] = 0.3
    after["openings"][0]["host_boundary_id"] = "B2"
    after["connections"] = []
    comparison = module.compare_sources(before, after)
    assert comparison["geometry"]["changed"] == ["opening:D1"]
    assert comparison["hosts"]["changed"] == ["opening:D1"]
    assert comparison["connectivity"]["removed"] == before["connections"]
