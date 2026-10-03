"""Validate deterministic, source-faithful mappings of two historical runs."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from src.harness_contracts import EventLog


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tests/fixtures/harness_stage0/sources"
HISTORY_DIR = ROOT / "tests/fixtures/harness_stage0/history"
MAPPER_PATH = (
    ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage0/map_history.py"
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _mapper() -> ModuleType:
    spec = importlib.util.spec_from_file_location("stage0_map_history", MAPPER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event(log: EventLog, event_id: str):
    return next(item for item in log.events if item.event_id == event_id)


def test_checked_in_history_logs_validate_and_every_event_has_hashed_selector() -> None:
    for path in sorted(HISTORY_DIR.glob("*_event_log.json")):
        log = EventLog.model_validate_json(path.read_text(encoding="utf-8"))
        assert log.mode == "excerpt"
        assert log.excerpt is not None
        for event in log.events:
            assert event.source_refs, event.event_id
            for source in event.source_refs:
                assert source.blob is not None and source.blob.kind == "sha256"
                assert "::selector=" in source.locator
                relative = source.blob.uri.removeprefix("repo:///")
                assert _digest(ROOT / relative) == source.blob.sha256


def test_run99_preserves_actual_stream_order_full_messages_and_per_message_usage() -> None:
    source = _load(SOURCE_DIR / "claude_run99_excerpt.json")
    log = EventLog.model_validate_json(
        (HISTORY_DIR / "claude_run99_event_log.json").read_text(encoding="utf-8")
    )
    assert [event.event_id for event in log.events] == [
        "run99-request-boundary",
        "run99-stream-thinking-line-2",
        "run99-stream-tool-call-line-3",
        "run99-stream-tool-result-line-4",
        "run99-stream-visible-text-line-6",
        "run99-run-aggregate-usage",
    ]

    request = log.events[0].payload
    assert request.final_request_body.kind == "missing"
    assert request.parameters.requested == {
        "model": source["request"]["requested_model"],
        "reasoning_effort": source["request"]["effort"],
    }
    assert request.parameters.provider_report.kind == "not_reported"
    assert request.parameters.effect.kind == "unverified"
    assert {
        request.versions.code_commit.identifier,
        request.versions.dependency_lock.identifier,
        request.versions.prompt.identifier,
        request.versions.tool_definitions.identifier,
        request.versions.inference_parameters.identifier,
        request.versions.model_route.identifier,
    } == {"not_captured"}

    stream = source["stream"]
    mapped_messages = (
        (log.events[1], stream["thinking_message"]),
        (log.events[2], stream["tool_call_message"]),
        (log.events[4], stream["visible_text_message"]),
    )
    for event, original in mapped_messages:
        assert event.payload.raw_response.value == original["message"]
        assert event.payload.usage.raw_usage == original["message"]["usage"]

    signature = stream["thinking_message"]["message"]["content"][0]
    assert signature["thinking"] == ""
    assert log.events[1].payload.thinking[0].kind == "signature"
    assert log.events[1].payload.thinking[0].signature == signature["signature"]

    tool_result = log.events[3].payload
    assert tool_result.outcome == "succeeded"
    assert tool_result.raw_result.kind == "missing"
    assert tool_result.shown_result.value == stream["tool_result_message"]["message"]
    assert tool_result.capture_scope == "historical_excerpt"

    aggregate = log.events[5].payload
    assert aggregate.event_type == "run_usage_summary"
    assert aggregate.usage.raw_usage == source["receipt"]["usage"]
    assert aggregate.usage.raw_usage != log.events[4].payload.usage.raw_usage
    assert aggregate.raw_summary.value["stop_reason"] == source["receipt"]["stop_reason"]


def test_sol_bridge_maps_dispatch_operation_tool_return_and_missing_receipt() -> None:
    source = _load(SOURCE_DIR / "sol_bridge_excerpt.json")
    log = EventLog.model_validate_json(
        (HISTORY_DIR / "sol_bridge_event_log.json").read_text(encoding="utf-8")
    )
    assert [event.payload.event_type for event in log.events] == [
        "external_coordinator_mcp",
        "adapter_request",
        "external_coordinator_mcp",
        "tool_execution",
        "external_coordinator_mcp",
        "run_usage_summary",
    ]
    assert [log.events[index].payload.phase for index in (0, 2, 4)] == [
        "dispatch",
        "operation",
        "return",
    ]

    request = log.events[1].payload
    assert request.final_request_body.kind == "missing"
    assert request.parameters.requested == {
        "model": source["dispatch"]["requested_model"],
        "reasoning_effort": source["dispatch"]["reasoning_effort"],
    }
    assert request.versions.prompt.identifier == "not_captured"
    assert request.versions.remote_model.alias_status == "unverified"

    exact = source["exact_bridge_call"]
    expected_call = {"tool": exact["tool"], "arguments": exact["arguments"]}
    assert log.events[2].payload.request_content.value == expected_call
    assert log.events[2].payload.result_content.value == exact["result"]

    tool = log.events[3].payload
    assert tool.call_id == (
        f"synthetic:archive:{exact['bridge_record_id']}:call-index:{exact['call_index']}"
    )
    assert tool.full_arguments == exact["arguments"]
    assert tool.raw_result.value == exact["result"]
    assert tool.shown_result.kind == "missing"
    assert tool.outcome == "succeeded"
    assert tool.applied_write_id == "inference_001"
    assert '"inference_id": "inference_001"' in exact["result"]["content"][0]["text"]

    returned = log.events[4].payload
    assert returned.method == "collaboration.spawn_agent"
    assert returned.request_content.kind == "missing"
    assert returned.result_content.value == {
        key: value for key, value in source["receipt"].items() if key != "source"
    }

    aggregate = log.events[5].payload
    assert aggregate.usage.kind == "missing"
    assert aggregate.raw_summary.value["provider_actual_model_receipt"] is None
    assert aggregate.raw_summary.value["token_usage"] is None
    assert aggregate.raw_summary.value["billing"] is None
    assert "synthetic archive mapping identity" in log.excerpt.reason


def test_mapper_is_deterministic_and_matches_checked_in_history(tmp_path: Path) -> None:
    mapper = _mapper()
    first = tmp_path / "first"
    second = tmp_path / "second"
    mapper.write_mappings(first)
    mapper.write_mappings(second)

    expected_names = {"claude_run99_event_log.json", "sol_bridge_event_log.json"}
    assert {path.name for path in first.glob("*.json")} == expected_names
    for name in expected_names:
        assert (first / name).read_bytes() == (second / name).read_bytes()
        # New optional runtime fields default to absent/None in preserved history.
        # Compare every typed field without rewriting historical source archives.
        assert EventLog.model_validate_json((first / name).read_bytes()) == EventLog.model_validate_json(
            (HISTORY_DIR / name).read_bytes())


def test_history_does_not_promote_missing_versions_or_aggregate_usage_to_observations() -> None:
    for path in HISTORY_DIR.glob("*_event_log.json"):
        log = EventLog.model_validate_json(path.read_bytes())
        for event in log.events:
            payload = event.payload
            if payload.event_type == "adapter_request":
                assert payload.final_request_body.kind == "missing"
                assert payload.versions.remote_model.alias_status == "unverified"
                assert payload.versions.dependency_lock.identifier == "not_captured"
            elif payload.event_type == "tool_execution":
                # Archives retain service IDs only when captured; otherwise the
                # synthetic identity says so instead of impersonating a call ID.
                if path.name == "sol_bridge_event_log.json":
                    assert payload.call_id.startswith("synthetic:")
                else:
                    source = _load(SOURCE_DIR / "claude_run99_excerpt.json")
                    assert payload.call_id == source["stream"]["tool_result_message"]["message"]["content"][0]["tool_use_id"]
            elif payload.event_type == "run_usage_summary":
                assert payload.raw_summary.kind == "inline"
