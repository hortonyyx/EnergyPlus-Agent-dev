"""Deterministically map two historical excerpts into harness EventLogs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.harness_contracts import (  # noqa: E402
    AdapterRequestPayload,
    EventEnvelope,
    EventLog,
    ExcerptDisclosure,
    ExternalCoordinatorMcpPayload,
    HashedBlobRef,
    HistoricalParentMissing,
    HistoricalTimestampMissing,
    InlineCapture,
    MissingCapture,
    ModelResponsePayload,
    ParameterAudit,
    ParametersNotReported,
    ParametersUnverified,
    RemoteModelIdentity,
    ResponseToolCall,
    RunAggregateUsagePayload,
    SourceRef,
    ThinkingSignature,
    ThinkingUnavailable,
    ToolExecutionPayload,
    UsageMissing,
    UsageReported,
    VersionManifest,
    VersionStamp,
)


SOURCE_DIR = ROOT / "tests/fixtures/harness_stage0/sources"
DEFAULT_OUTPUT_DIR = ROOT / "tests/fixtures/harness_stage0/history"


def _load(name: str) -> dict[str, Any]:
    return json.loads((SOURCE_DIR / name).read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _source_ref(
    metadata: dict[str, Any],
    source_id: str,
    *,
    selector: str | None = None,
    line: int | None = None,
) -> SourceRef:
    relative_path = metadata["path"]
    source_path = ROOT / relative_path
    actual_hash = _digest(source_path)
    if actual_hash != metadata["sha256"]:
        raise ValueError(f"historical source hash changed: {relative_path}")
    selected = selector or metadata["selector"]
    selected_line = line if line is not None else metadata.get("line")
    locator = f"{relative_path}::selector={selected}"
    if selected_line is not None:
        locator += f"::line={selected_line}"
    media_type = "application/gzip" if source_path.suffix == ".gz" else "application/json"
    return SourceRef(
        source_id=source_id,
        source_kind="history",
        locator=locator,
        blob=HashedBlobRef(
            uri=f"repo:///{relative_path}",
            media_type=media_type,
            sha256=actual_hash,
        ),
    )


def _not_captured_versions(model_alias: str, route_id: str) -> VersionManifest:
    missing = VersionStamp(identifier="not_captured")
    return VersionManifest(
        code_commit=missing,
        dependency_lock=missing,
        prompt=missing,
        tool_definitions=missing,
        inference_parameters=missing,
        model_route=missing,
        remote_model=RemoteModelIdentity(
            route_id=route_id,
            remote_alias=model_alias,
            alias_status="unverified",
        ),
    )


def _historical_event(
    *,
    event_id: str,
    run_id: str,
    task_id: str,
    sequence: int,
    payload: Any,
    source_refs: tuple[SourceRef, ...],
) -> EventEnvelope:
    return EventEnvelope(
        event_id=event_id,
        run_id=run_id,
        task_id=task_id,
        parent_task=HistoricalParentMissing(
            reason="the historical excerpt did not persist a stable parent task ID"
        ),
        sequence=sequence,
        occurred_at=HistoricalTimestampMissing(
            reason="the selected historical record did not preserve an event timestamp"
        ),
        source_refs=source_refs,
        payload=payload,
    )


def map_claude_run99() -> EventLog:
    fixture = _load("claude_run99_excerpt.json")
    request = fixture["request"]
    stream = fixture["stream"]
    receipt = fixture["receipt"]

    request_source = _source_ref(
        request["source"], "run99-launch-request", selector=request["source"]["selector"]
    )
    stream_source_metadata = stream["source"]
    receipt_source = _source_ref(
        receipt["source"], "run99-run-receipt", selector=receipt["source"]["selector"]
    )

    events: list[EventEnvelope] = []
    events.append(
        _historical_event(
            event_id="run99-request-boundary",
            run_id="run99",
            task_id="run99-main",
            sequence=0,
            source_refs=(request_source,),
            payload=AdapterRequestPayload(
                adapter="historical-claude-cli",
                final_request_body=MissingCapture(
                    reason=(
                        "agent_request.json is a launcher record; no independently archived "
                        "post-adapter provider request body survives"
                    )
                ),
                parameters=ParameterAudit(
                    requested={
                        "model": request["requested_model"],
                        "reasoning_effort": request["effort"],
                    },
                    provider_report=ParametersNotReported(
                        reason="the selected records do not report effective request parameters"
                    ),
                    effect=ParametersUnverified(
                        reason="requested values are known, but service application is unverified"
                    ),
                ),
                versions=_not_captured_versions(
                    request["requested_model"], "historical-claude-cli"
                ),
            ),
        )
    )

    thinking_record = stream["thinking_message"]
    thinking_message = thinking_record["message"]
    thinking_block = thinking_message["content"][0]
    thinking_source = _source_ref(
        stream_source_metadata,
        "run99-stream-thinking",
        selector=f"jsonl-uuid={thinking_record['event_uuid']}#/message",
        line=thinking_record["line"],
    )
    events.append(
        _historical_event(
            event_id="run99-stream-thinking-line-2",
            run_id="run99",
            task_id="run99-main",
            sequence=1,
            source_refs=(thinking_source,),
            payload=ModelResponsePayload(
                request_event_id="run99-request-boundary",
                thinking=(ThinkingSignature(signature=thinking_block["signature"]),),
                usage=UsageReported(raw_usage=thinking_message["usage"]),
                raw_response=InlineCapture(value=thinking_message),
            ),
        )
    )

    call_record = stream["tool_call_message"]
    call_message = call_record["message"]
    call_block = call_message["content"][0]
    call_source = _source_ref(
        stream_source_metadata,
        "run99-stream-tool-call",
        selector=f"jsonl-uuid={call_record['event_uuid']}#/message",
        line=call_record["line"],
    )
    events.append(
        _historical_event(
            event_id="run99-stream-tool-call-line-3",
            run_id="run99",
            task_id="run99-main",
            sequence=2,
            source_refs=(call_source,),
            payload=ModelResponsePayload(
                request_event_id="run99-request-boundary",
                tool_calls=(
                    ResponseToolCall(
                        call_id=call_block["id"],
                        tool_name=call_block["name"],
                        full_arguments=call_block["input"],
                    ),
                ),
                thinking=(
                    ThinkingUnavailable(
                        reason="this archived stream message contains no thinking field"
                    ),
                ),
                usage=UsageReported(raw_usage=call_message["usage"]),
                raw_response=InlineCapture(value=call_message),
            ),
        )
    )

    result_record = stream["tool_result_message"]
    result_message = result_record["message"]
    result_source = _source_ref(
        stream_source_metadata,
        "run99-stream-tool-result",
        selector=f"jsonl-uuid={result_record['event_uuid']}#/message",
        line=result_record["line"],
    )
    events.append(
        _historical_event(
            event_id="run99-stream-tool-result-line-4",
            run_id="run99",
            task_id="run99-main",
            sequence=3,
            source_refs=(result_source,),
            payload=ToolExecutionPayload(
                call_id=call_block["id"],
                tool_name=call_block["name"],
                full_arguments=call_block["input"],
                raw_result=MissingCapture(
                    reason="the pre-CLI raw MCP response was not independently archived"
                ),
                shown_result=InlineCapture(value=result_message),
                repeatability="read_only",
                outcome="succeeded",
                capture_scope="historical_excerpt",
            ),
        )
    )

    text_record = stream["visible_text_message"]
    text_message = text_record["message"]
    text_blocks = tuple(
        block["text"] for block in text_message["content"] if block["type"] == "text"
    )
    text_source = _source_ref(
        stream_source_metadata,
        "run99-stream-visible-text",
        selector=f"jsonl-uuid={text_record['event_uuid']}#/message",
        line=text_record["line"],
    )
    events.append(
        _historical_event(
            event_id="run99-stream-visible-text-line-6",
            run_id="run99",
            task_id="run99-main",
            sequence=4,
            source_refs=(text_source,),
            payload=ModelResponsePayload(
                request_event_id="run99-request-boundary",
                visible_text=text_blocks,
                thinking=(
                    ThinkingUnavailable(
                        reason="this archived stream message contains no thinking field"
                    ),
                ),
                usage=UsageReported(raw_usage=text_message["usage"]),
                raw_response=InlineCapture(value=text_message),
            ),
        )
    )

    raw_receipt = {
        "actual_model": receipt["actual_model"],
        "elapsed_seconds": receipt["elapsed_seconds"],
        "stop_reason": receipt["stop_reason"],
        "usage": receipt["usage"],
    }
    events.append(
        _historical_event(
            event_id="run99-run-aggregate-usage",
            run_id="run99",
            task_id="run99-main",
            sequence=5,
            source_refs=(receipt_source,),
            payload=RunAggregateUsagePayload(
                usage=UsageReported(raw_usage=receipt["usage"]),
                raw_summary=InlineCapture(value=raw_receipt),
                notes=(
                    "run aggregate usage is preserved separately and is not copied into message usage",
                ),
            ),
        )
    )

    return EventLog(
        mode="excerpt",
        events=tuple(events),
        excerpt=ExcerptDisclosure(
            reason=(
                "selected Claude CLI lifecycle records; the wire request and raw MCP "
                "response were not archived"
            ),
            omitted_event_types=("unselected_stream_messages",),
            source_records=(request_source, thinking_source, call_source, result_source, text_source, receipt_source),
        ),
    )


def map_sol_bridge() -> EventLog:
    fixture = _load("sol_bridge_excerpt.json")
    dispatch = fixture["dispatch"]
    exact = fixture["exact_bridge_call"]
    receipt = fixture["receipt"]
    request_metadata, reply_metadata = exact["sources"]

    dispatch_source = _source_ref(
        dispatch["source"], "sol-dispatch-request", selector=dispatch["source"]["selector"]
    )
    bridge_request_source = _source_ref(
        request_metadata,
        "sol-bridge-request-call-index-3",
        selector=request_metadata["selector"],
    )
    bridge_reply_source = _source_ref(
        reply_metadata,
        "sol-bridge-reply-call-index-3",
        selector=reply_metadata["selector"],
    )
    receipt_source = _source_ref(
        receipt["source"], "sol-controller-receipt", selector=receipt["source"]["selector"]
    )
    dispatch_content = {
        "requested_model": dispatch["requested_model"],
        "reasoning_effort": dispatch["reasoning_effort"],
        "channel": dispatch["channel"],
    }
    call_content = {"tool": exact["tool"], "arguments": exact["arguments"]}
    synthetic_call_id = (
        f"synthetic:archive:{exact['bridge_record_id']}:call-index:{exact['call_index']}"
    )

    events = (
        _historical_event(
            event_id="sol-external-dispatch",
            run_id=fixture["run"],
            task_id="sol-controller-task",
            sequence=0,
            source_refs=(dispatch_source,),
            payload=ExternalCoordinatorMcpPayload(
                phase="dispatch",
                coordinator_task_id="sol-controller-task",
                method="collaboration.spawn_agent",
                request_content=InlineCapture(value=dispatch_content),
                result_content=MissingCapture(
                    reason="completion is archived separately from dispatch"
                ),
            ),
        ),
        _historical_event(
            event_id="sol-model-request-boundary",
            run_id=fixture["run"],
            task_id="sol-controller-task",
            sequence=1,
            source_refs=(dispatch_source,),
            payload=AdapterRequestPayload(
                adapter="historical-external-development-model-runtime",
                final_request_body=MissingCapture(
                    reason=(
                        "the collaboration archive records the requested override but not the "
                        "outer prompt, model messages, or final provider request body"
                    )
                ),
                parameters=ParameterAudit(
                    requested={
                        "model": dispatch["requested_model"],
                        "reasoning_effort": dispatch["reasoning_effort"],
                    },
                    provider_report=ParametersNotReported(
                        reason="controller receipt contains no provider parameter report"
                    ),
                    effect=ParametersUnverified(
                        reason="requested override is archived; effective provider values are unknown"
                    ),
                ),
                versions=_not_captured_versions(
                    dispatch["requested_model"], "historical-collaboration-runtime"
                ),
            ),
        ),
        _historical_event(
            event_id="sol-external-operation",
            run_id=fixture["run"],
            task_id="sol-controller-task",
            sequence=2,
            source_refs=(bridge_request_source, bridge_reply_source),
            payload=ExternalCoordinatorMcpPayload(
                phase="operation",
                coordinator_task_id="sol-controller-task",
                method=exact["tool"],
                request_content=InlineCapture(value=call_content),
                result_content=InlineCapture(value=exact["result"]),
            ),
        ),
        _historical_event(
            event_id="sol-bridge-tool-execution",
            run_id=fixture["run"],
            task_id="sol-controller-task",
            sequence=3,
            source_refs=(bridge_request_source, bridge_reply_source),
            payload=ToolExecutionPayload(
                call_id=synthetic_call_id,
                tool_name=exact["tool"],
                full_arguments=exact["arguments"],
                raw_result=InlineCapture(value=exact["result"]),
                shown_result=MissingCapture(
                    reason="the archive does not prove the development model consumed this return"
                ),
                repeatability="non_idempotent_write",
                outcome="succeeded",
                capture_scope="historical_excerpt",
                operation_key=synthetic_call_id,
                applied_write_id="inference_001",
            ),
        ),
        _historical_event(
            event_id="sol-external-return",
            run_id=fixture["run"],
            task_id="sol-controller-task",
            sequence=4,
            source_refs=(receipt_source,),
            payload=ExternalCoordinatorMcpPayload(
                phase="return",
                coordinator_task_id="sol-controller-task",
                method="collaboration.spawn_agent",
                request_content=MissingCapture(
                    reason="the controller return record contains no repeated dispatch request"
                ),
                result_content=InlineCapture(
                    value={key: value for key, value in receipt.items() if key != "source"}
                ),
            ),
        ),
        _historical_event(
            event_id="sol-run-aggregate-usage",
            run_id=fixture["run"],
            task_id="sol-controller-task",
            sequence=5,
            source_refs=(receipt_source,),
            payload=RunAggregateUsagePayload(
                usage=UsageMissing(reason=receipt["receipt_limit"]),
                raw_summary=InlineCapture(
                    value={key: value for key, value in receipt.items() if key != "source"}
                ),
                notes=(
                    "requested model and completion are archived; provider model, token usage, and billing are unavailable",
                ),
            ),
        ),
    )
    return EventLog(
        mode="excerpt",
        events=events,
        excerpt=ExcerptDisclosure(
            reason=(
                "external coordinator and bridge archive excerpt; the model prompt, model "
                "messages, hidden reasoning, and provider receipt are unavailable. The tool "
                "call ID is a synthetic archive mapping identity, not a provider operation ID."
            ),
            omitted_event_types=("model_response",),
            source_records=(
                dispatch_source,
                bridge_request_source,
                bridge_reply_source,
                receipt_source,
            ),
        ),
    )


def write_mappings(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mappings = {
        "claude_run99_event_log.json": map_claude_run99(),
        "sol_bridge_event_log.json": map_sol_bridge(),
    }
    written: dict[str, Path] = {}
    for name, event_log in mappings.items():
        target = output_dir / name
        serialized = json.dumps(
            event_log.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        target.write_text(serialized + "\n", encoding="utf-8")
        written[name] = target
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    for name, path in write_mappings(args.output_dir).items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
