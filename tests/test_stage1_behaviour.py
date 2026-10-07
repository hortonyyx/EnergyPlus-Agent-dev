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


def _request(sequence: int, model: str, *, second: int) -> dict:
    versions = {
        name: {"identifier": f"test-{name}"}
        for name in ("code_commit", "dependency_lock", "prompt", "tool_definitions",
                     "inference_parameters", "model_route")
    }
    versions["remote_model"] = {
        "route_id": "test-route", "remote_alias": model, "fixed_revision": None,
        "alias_status": "unverified", "evidence": None,
    }
    return _envelope(sequence, {
        "event_type": "adapter_request",
        "adapter": "test-adapter",
        "final_request_body": {"kind": "inline", "value": {"model": model, "messages": []}},
        "injected_content": [],
        "images": [],
        "parameters": {
            "requested": {},
            "provider_report": {"kind": "not_reported", "reason": "test"},
            "effect": {"kind": "unverified", "reason": "test"},
        },
        "versions": versions,
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
                   {"candidate": "candidate_01", "source_geometry_ready": True}, second=9, write=True),
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


def test_current_log_reads_request_model_and_counts_only_successful_views(tmp_path: Path) -> None:
    run = tmp_path / "current-views"
    run.mkdir()
    events = [
        _request(0, "Qwen-test", second=0),
        _response(1, [
            {"call_id": "full", "tool_name": "view_image",
             "full_arguments": {"name": "plan.png"}},
            {"call_id": "missing", "tool_name": "view_image",
             "full_arguments": {"name": "missing.png"}},
        ], second=1),
        _execution(2, "full", "view_image", {"name": "plan.png"},
                   {"transport_wrapper": "no top-level image metadata"}, second=2),
        _execution(3, "missing", "view_image", {"name": "missing.png"},
                   {"error": "not found"}, second=3),
    ]
    events[-1]["payload"]["outcome"] = "failed"
    (run / "events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in events))
    summary = load_behaviour(run)["summary"]
    assert summary["model"] == "Qwen-test"
    assert summary["full_views_before_first_draft"] == 1
    assert summary["crops_before_first_draft"] == 0


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
                         "content": [{"type": "text", "text": "{\"candidate\":\"candidate_01\",\"source_geometry_ready\":true}"}]}]}},
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
    first_bytes = (out / "record.json.gz").read_bytes()
    write_behaviour_report(bridge, out)
    assert (out / "record.json.gz").read_bytes() == first_bytes


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
    assert record["invocations"][0]["steps"][0]["model_visible_result"] == {"candidate": "candidate_01"}

    outside = tmp_path / "outside.json"
    outside.write_bytes(raw)
    escaped = json.loads(json.dumps(execution))
    escaped["payload"]["raw_result"]["blob"]["uri"] = "../outside.json"
    escaped["payload"]["shown_result"]["blob"]["uri"] = "../outside.json"
    (run / "events.jsonl").write_text(json.dumps(response) + "\n" + json.dumps(escaped) + "\n")
    import pytest
    with pytest.raises(ValueError, match="escapes event-log directory"):
        load_behaviour(run)


def test_prepared_result_counts_as_visible_only_after_presentation_event(tmp_path: Path) -> None:
    run = tmp_path / "presentation-run"
    run.mkdir()
    response = _response(0, [{"call_id": "view", "tool_name": "view_image",
                              "full_arguments": {"name": "North_view.png", "box": [1, 1, 9, 9]}}], second=0)
    execution = _execution(1, "view", "view_image",
                           {"name": "North_view.png", "box": [1, 1, 9, 9]},
                           {"name": "North_view.png", "box_original_pixels": [1, 1, 9, 9],
                            "original_size": [10, 10]}, second=1)
    execution["payload"]["presentation_status"] = "prepared"
    (run / "events.jsonl").write_text(json.dumps(response) + "\n" + json.dumps(execution) + "\n")
    pending = load_behaviour(run)
    step = pending["invocations"][0]["steps"][0]
    assert step["prepared_result"]["name"] == "North_view.png"
    assert step["model_visible_result"] is None and not step["delivered_to_model"]
    assert pending["summary"]["elevation_crops_by_facade"] == {}
    assert pending["summary"]["undelivered_tool_results"] == 1

    presentation = _envelope(2, {
        "event_type": "tool_presentation",
        "tool_execution_event_id": "event-1",
        "request_event_id": "request-next",
        "response_event_id": "response-next",
        "shown_result": execution["payload"]["shown_result"],
    }, second=2)
    with (run / "events.jsonl").open("a") as stream:
        stream.write(json.dumps(presentation) + "\n")
    delivered = load_behaviour(run)
    step = delivered["invocations"][0]["steps"][0]
    assert step["model_visible_result"]["name"] == "North_view.png"
    assert step["delivered_to_model"] and step["presentation_event_id"] == "event-2"
    assert delivered["summary"]["elevation_crops_by_facade"] == {"north": 1}


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


def test_run99_archived_snapshot_and_current_input_guard_preserve_delivery_exactly() -> None:
    spec = importlib.util.spec_from_file_location("stage1_replay_history", REPLAY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = module.RUNS["run99"]
    evidence = module.snapshot_code_evidence(run)
    assert evidence["status"] == "complete"
    assert evidence["snapshot_exact_file_count"] == evidence["file_count"] == 44
    by_path = {row["path"]: row for row in evidence["files"]}
    # A1-T intentionally adds pre-kernel validation to the exporter. The archive
    # must still match all 44 original hashes; the unchanged kernel files must
    # still match too. For the current exporter, protect the actual source and
    # display bytes below instead of prohibiting every new input check forever.
    assert all(
        by_path[path]["current_matches_snapshot"]
        for path in module.SNAPSHOT_REPLAY_CURRENT_MATCH_PATHS
        if path != "src/agent/execution/source_proposal.py"
    )
    candidate = json.loads((run / "delivery.json").read_text())["candidate"]
    replay = module.replay_delivered(
        run,
        candidate,
        naming_module=run / "runtime_snapshot/src/agent/geometry/source_naming.py",
        code_scope="archived_naming_and_current_guarded_exporter_unchanged_kernel",
    )
    # N1 (10-07, bim_names_v3) hyphenates multi-word use tokens through the current room-type
    # catalogue. Only those names may differ; objects, geometry, hosts and connectivity replay unchanged.
    assert replay["status"] == "semantic_match"
    assert set(replay["top_level_differences"]) == {"public_names", "room_type_catalog", "source_model_sha256"}
    semantic = replay["semantic_comparison"]
    assert not any(semantic[key][part] for key in ("objects", "geometry", "hosts")
                   for part in ("added", "removed", "changed"))
    assert not semantic["connectivity"]["added"] and not semantic["connectivity"]["removed"]
    names = replay["public_names_comparison"]
    assert not names["added"] and not names["removed"]
    assert len(names["changed_examples"]) == len(names["changed"]) > 0
    for row in names["changed_examples"]:
        zone, floor, *use, quadrant = row["saved"].split("_")
        assert row["current"] == "_".join([zone, floor, "-".join(use), quadrant])
