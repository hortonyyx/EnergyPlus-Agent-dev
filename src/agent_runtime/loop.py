"""A bounded, audited single-role conversation, without delegation/compaction."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from pydantic import Field

from src.harness_contracts import (
    BudgetAmounts, BudgetEventPayload, BudgetReservation, BudgetSettlement,
    CostUnavailable, HashedBlobRef, MissingCapture, RunAggregateUsagePayload,
    RunLifecyclePayload, SourceRef, StateInspectionPayload, ToolExecutionPayload,
    ToolInvocationPayload, UsageMissing, UsageReported, authorize_tool_call,
    ToolPresentationPayload,
)
from src.harness_contracts.base import ContractModel
from .adapter import convert_tool_result, parse_response, prepare_request, reported_tokens
from .store import EventStore


class RunLimits(ContractModel):
    model_calls: int = Field(ge=1)
    tool_calls: int = Field(ge=0)
    seconds: float = Field(gt=0)
    tokens: int = Field(ge=1)

    def ledger_limit(self):
        return BudgetAmounts(tokens=self.tokens, calls=self.model_calls,
                             seconds=Decimal(str(self.seconds)))


@dataclass
class Runtime:
    store: EventStore
    adapter: object
    tools: object
    role: object
    model: str
    parameters: dict
    versions: object
    limits: RunLimits
    echo_fields: tuple[str, ...] = ("reasoning_content",)

    async def run(self, messages: list[dict], *, message_sources=None,
                  image_originals=None, resume=False) -> dict:
        self.started = time.monotonic()
        self.elapsed_before = 0.0
        self.messages = list(messages)
        self.sources = list(message_sources or [self.store.source(f"initial-message-{i}", m,
                            kind="user" if m.get("role") == "user" else "runtime")
                            for i, m in enumerate(messages)])
        self.originals = dict(image_originals or {})
        self.counts = {"model_calls": 0, "tool_calls": 0, "reported_tokens": 0,
                       "reserved_tokens": 0, "usage_complete": True}
        self.used_ids = set()
        self.answer = None
        self.pending_write = False
        self.stage = "initialization"
        if self.store.budget_limit != self.limits.ledger_limit():
            raise ValueError("runtime limits differ from persisted budget")
        # Roles may constrain budget further, never broaden it.
        for name, value in (("tokens", self.limits.tokens), ("calls", self.limits.model_calls),
                            ("seconds", Decimal(str(self.limits.seconds)))):
            cap = getattr(self.role.budget, name)
            if cap is not None and value > cap:
                raise ValueError(f"runtime exceeds role budget: {name}")
        specs = await self.tools.list_tools()
        self.specs = [{"type": "function", "function": {
            "name": item["name"], "description": item.get("description", ""),
            "parameters": item["inputSchema"]}} for item in specs]
        self.spec_by_name = {item["name"]: item for item in specs}
        self.tool_source = self.store.source("mcp-tool-definitions", self.specs)
        if self.store.events:
            if not resume:
                raise ValueError("existing journal requires explicit resume")
            reason = self._restore()
            if reason:
                if reason == "already_completed":
                    return {**json.loads((self.store.directory / "receipt.json").read_bytes()),
                            "resume_status": "already_completed"}
                return self._stop(reason)
        else:
            self.store.append(RunLifecyclePayload(action="start", reason="single-role run started"),
                source_refs=(self.store.source("runtime-config", {
                    "model": self.model, "parameters": self.parameters,
                    "limits": self.limits.model_dump(mode="json"),
                    "role": self.role.model_dump(mode="json"),
                    "versions": self.versions.model_dump(mode="json")} ),))
            self._checkpoint()
        try:
            while True:
                reason = self._budget_stop()
                if reason:
                    return self._stop(reason)
                self.stage = "prepare_request"
                prepared = prepare_request(store=self.store, model=self.model,
                    messages=self.messages, message_sources=self.sources,
                    tools=self.specs, tool_source=self.tool_source,
                    parameters=self.parameters, versions=self.versions,
                    image_originals=self.originals)
                reserve = prepared.token_reservation_estimate
                if self.counts["reserved_tokens"] + reserve > self.limits.tokens:
                    return self._stop("token_budget_exhausted")
                reservation = BudgetReservation(
                    reservation_id=f"model-{self.counts['model_calls'] + 1}",
                    purpose="primary_task", task_id=self.store.task_id,
                    amounts=BudgetAmounts(tokens=reserve, calls=1))
                self.store.append(BudgetEventPayload(action="reserve", reservation=reservation))
                self.counts["reserved_tokens"] += reserve
                self.counts["model_calls"] += 1
                self.stage = "model_request"
                request = self.store.append(prepared.event_payload)
                try:
                    raw = await asyncio.wait_for(self.adapter.send(prepared,
                        timeout=self._remaining()), timeout=self._remaining())
                except (Exception, asyncio.CancelledError) as exc:
                    self.counts["usage_complete"] = False
                    self._settle(reservation, UsageMissing(reason="request ended without a service usage receipt"))
                    return self._exception_stop(exc)
                self.stage = "model_response"
                parsed = parse_response(raw, request.event_id, self.store, echo_fields=self.echo_fields)
                response = self.store.append(parsed.event_payload)
                delivered = {e.payload.tool_execution_event_id for e in self.store.events
                    if e.payload.event_type == "tool_presentation"}
                included = {source.event_id for source in self.sources if source.event_id}
                for event in list(self.store.events):
                    if event.payload.event_type == "tool_execution" and event.event_id in included - delivered:
                        self.store.append(ToolPresentationPayload(tool_execution_event_id=event.event_id,
                            request_event_id=request.event_id, response_event_id=response.event_id,
                            shown_result=event.payload.shown_result))
                count = reported_tokens(parsed.event_payload.usage)
                if count is not None:
                    self.counts["reported_tokens"] += count
                else:
                    self.counts["usage_complete"] = False
                if count is not None and count > reserve:
                    # Keep raw billing evidence even when the estimate was wrong.
                    # A settlement over its reservation would be a false valid ledger.
                    return self._stop("token_reservation_exceeded")
                self._settle(reservation, parsed.event_payload.usage)
                if parsed.protocol_error:
                    return self._stop(parsed.protocol_error)
                if count is None:
                    return self._stop("token_usage_unavailable")
                if self.counts["reported_tokens"] >= self.limits.tokens:
                    return self._stop("token_budget_exhausted")
                if self._remaining() <= 0:
                    return self._stop("time_budget_exhausted")
                calls = parsed.event_payload.tool_calls
                if not calls:
                    self.answer = "\n".join(parsed.event_payload.visible_text)
                    self.messages.append(parsed.assistant_message)
                    self.sources.append(self._event_source(response))
                    self._checkpoint()
                    return self._stop("completed")
                if self.counts["tool_calls"] + len(calls) > self.limits.tool_calls:
                    return self._stop("tool_budget_exhausted")
                # Validate the entire batch before any mutating call is sent.
                try:
                    for call in calls:
                        if call.call_id in self.used_ids or call.tool_name not in self.spec_by_name:
                            raise ValueError("unknown tool or reused call identity")
                        repeatability = self.tools.repeatability(call.tool_name)
                        authorize_tool_call(self.role, call.tool_name,
                            "read" if repeatability == "read_only" else "write")
                except ValueError:
                    return self._stop("tool_authorization_failed")
                self.messages.append(parsed.assistant_message)
                self.sources.append(self._event_source(response))
                pictures, picture_events = [], []
                for call in calls:
                    if self._remaining() <= 0:
                        return self._stop("time_budget_exhausted")
                    self.used_ids.add(call.call_id)
                    self.counts["tool_calls"] += 1
                    self.stage = f"tool:{call.tool_name}"
                    repeatability = self.tools.repeatability(call.tool_name)
                    write = repeatability != "read_only"
                    key = f"{self.store.run_id}:{call.call_id}" if write else None
                    before = self.store.put_json(self.tools.snapshot_state()) if write else None
                    intent = self.store.append(ToolInvocationPayload(call_id=call.call_id,
                        tool_name=call.tool_name, full_arguments=call.full_arguments,
                        repeatability=repeatability, operation_key=key, state_before=before))
                    self.pending_write = write
                    try:
                        raw_result = await asyncio.wait_for(self.tools.call_tool(
                            call.tool_name, call.full_arguments), timeout=self._remaining())
                    except (Exception, asyncio.CancelledError) as exc:
                        failed = self.store.append(ToolExecutionPayload(call_id=call.call_id,
                            tool_name=call.tool_name, full_arguments=call.full_arguments,
                            repeatability=repeatability, operation_key=key, outcome="unknown",
                            raw_result=MissingCapture(reason="MCP result not received"),
                            shown_result=MissingCapture(reason="no result was presented"),
                            invocation_event_id=intent.event_id, presentation_status="prepared"))
                        if write:
                            # A file comparison alone cannot prove no late write.
                            # Save observed state and stop without replaying it.
                            self._inspect_unknown(failed.event_id, before)
                        return self._exception_stop(exc, unknown_write=write)
                    self.pending_write = False
                    try:
                        message, blocks, shown, refs = convert_tool_result(call.call_id, raw_result, self.store)
                    except Exception as exc:
                        # Received raw result is known even if its presentation failed.
                        self.store.append(ToolExecutionPayload(call_id=call.call_id,
                            tool_name=call.tool_name, full_arguments=call.full_arguments,
                            raw_result=self.store.capture(raw_result, force_blob=True),
                            shown_result=MissingCapture(reason="MCP presentation conversion failed"),
                            repeatability=repeatability, operation_key=key,
                            outcome="failed", invocation_event_id=intent.event_id, presentation_status="prepared"))
                        return self._exception_stop(exc)
                    execution = self.store.append(ToolExecutionPayload(call_id=call.call_id,
                        tool_name=call.tool_name, full_arguments=call.full_arguments,
                        raw_result=self.store.capture(raw_result, force_blob=True),
                        shown_result=self.store.capture(shown, force_blob=True),
                        repeatability=repeatability, outcome="failed" if raw_result.get("isError") else "succeeded",
                        operation_key=key, applied_write_id=key if write and not raw_result.get("isError") else None,
                        invocation_event_id=intent.event_id, presentation_status="prepared"))
                    self.messages.append(message)
                    self.sources.append(self._event_source(execution))
                    pictures.extend(blocks)
                    if blocks:
                        picture_events.append(execution.event_id)
                    origins = getattr(self.tools, "image_origins", lambda _: {})(raw_result)
                    for ref in refs:
                        origin = origins.get(ref.sha256)
                        path = origin.get("original_path") if isinstance(origin, dict) else origin
                        self.originals[ref.sha256] = self.store.put_bytes(Path(path).read_bytes(),
                            ref.media_type) if path else ref
                if pictures:
                    self.messages.append({"role": "user", "content": pictures})
                    self.sources.append(SourceRef(source_id="tool-images", source_kind="tool",
                        locator=",".join(picture_events), event_id=picture_events[-1],
                        blob=self.store.put_json({"origin_events": picture_events,
                            "conversion": "MCP images after all tool replies, exact image bytes"})))
                self._checkpoint()
        except (Exception, asyncio.CancelledError) as exc:
            return self._exception_stop(exc)

    def _remaining(self):
        return max(0.0, self.limits.seconds - self.elapsed_before - (time.monotonic() - self.started))

    def _budget_stop(self):
        if self._remaining() <= 0:
            return "time_budget_exhausted"
        if self.counts["model_calls"] >= self.limits.model_calls:
            return "model_budget_exhausted"
        if self.counts["reserved_tokens"] >= self.limits.tokens:
            return "token_budget_exhausted"
        return None

    def _event_source(self, event):
        return SourceRef(source_id=event.event_id, source_kind="tool" if
            event.payload.event_type == "tool_execution" else "runtime",
            locator=f"events.jsonl:{event.sequence + 1}", event_id=event.event_id)

    def _settle(self, reservation, usage):
        self.store.append(BudgetEventPayload(action="settle", settlement=BudgetSettlement(
            reservation_id=reservation.reservation_id,
            actual=BudgetAmounts(tokens=reported_tokens(usage), calls=1), usage=usage,
            cost=CostUnavailable(reason="service did not report a billed amount; no price assumed"))))

    def _inspect_unknown(self, event_id, before):
        state = self.store.put_json({"before": before.model_dump(mode="json") if before else None,
            "observed_after": self.tools.snapshot_state(),
            "reason": "snapshot alone cannot prove completion or absence of a late write"})
        self.store.append(StateInspectionPayload(purpose="unknown_write_recovery",
            target_event_id=event_id, persisted_state=state, conclusion="inconclusive"))

    def _exception_stop(self, exc, *, unknown_write=False):
        timeout = isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        cancel = isinstance(exc, asyncio.CancelledError)
        reason = "unknown_write_outcome" if unknown_write else (
            "time_budget_exhausted" if timeout else "cancelled" if cancel else "failed")
        action = "timeout" if timeout else "cancel" if cancel else "failure"
        fields = {"failure_stage": self.stage} if action == "failure" else {}
        # Exception messages can contain credentials, URLs or request headers.
        self.store.append(RunLifecyclePayload(action=action,
            reason=f"{reason}; error_type={type(exc).__name__}", **fields))
        return self._stop(reason)

    def _checkpoint(self):
        snapshot = {"messages": self.messages,
            "sources": [s.model_dump(mode="json") for s in self.sources],
            "image_originals": {k: v.model_dump(mode="json") for k, v in self.originals.items()},
            "counts": self.counts, "used_ids": sorted(self.used_ids),
            "elapsed_seconds": self.limits.seconds - self._remaining(),
            "tool_state": self.tools.snapshot_state(),
            "versions": self.versions.model_dump(mode="json"),
            "last_event_id": self.store.events[-1].event_id}
        ref = self.store.put_json(snapshot)
        self.store.write_json("checkpoint.json", ref.model_dump(mode="json"))

    def _restore(self):
        # Even a refused recovery reports all already-recorded calls/use, never
        # the fresh object's zero counters.
        requests = [e for e in self.store.events if e.payload.event_type == "adapter_request"]
        responses = [e.payload for e in self.store.events if e.payload.event_type == "model_response"]
        reservations = [e.payload.reservation for e in self.store.events
            if e.payload.event_type == "budget" and e.payload.action == "reserve"]
        self.counts.update(model_calls=len(requests),
            tool_calls=sum(e.payload.event_type == "tool_invocation" for e in self.store.events),
            reported_tokens=sum(reported_tokens(p.usage) or 0 for p in responses),
            reserved_tokens=sum(r.amounts.tokens or 0 for r in reservations),
            usage_complete=len(requests) == len(responses) and all(reported_tokens(p.usage) is not None for p in responses))
        path = self.store.directory / "checkpoint.json"
        if not path.exists():
            return "resume_checkpoint_missing"
        ref = HashedBlobRef.model_validate_json(path.read_bytes())
        checkpoint = json.loads(self.store.get_bytes(ref))
        # Orphaned intent is an unknown result, not permission to repeat a write.
        completed = {e.payload.invocation_event_id for e in self.store.events
            if e.payload.event_type == "tool_execution"}
        for event in list(self.store.events):
            p = event.payload
            if p.event_type == "tool_invocation" and event.event_id not in completed:
                result = self.store.append(ToolExecutionPayload(call_id=p.call_id,
                    tool_name=p.tool_name, full_arguments=p.full_arguments,
                    repeatability=p.repeatability, operation_key=p.operation_key,
                    outcome="unknown", raw_result=MissingCapture(reason="interrupted after durable intent"),
                    shown_result=MissingCapture(reason="no result captured before restart"),
                    invocation_event_id=event.event_id, presentation_status="prepared"))
                if p.repeatability != "read_only":
                    self._inspect_unknown(result.event_id, p.state_before)
                return "resume_pending_operation"
        last = next(e.sequence for e in self.store.events if e.event_id == checkpoint["last_event_id"])
        suffix = [e for e in self.store.events if e.sequence > last]
        if any(e.payload.event_type in {"adapter_request", "tool_invocation", "budget"} for e in suffix):
            return "resume_uncheckpointed_operation"
        if any(e.payload.event_type == "run_lifecycle" and e.payload.reason == "completed" for e in suffix):
            return "already_completed"
        safe = checkpoint["tool_state"] == self.tools.snapshot_state() and checkpoint["versions"] == self.versions.model_dump(mode="json")
        inspected = self.store.append(StateInspectionPayload(purpose="resume",
            target_event_id=checkpoint["last_event_id"], persisted_state=ref,
            conclusion="safe_to_resume" if safe else "inconclusive"))
        if not safe:
            return "resume_state_changed"
        self.store.append(RunLifecyclePayload(action="resume", reason="saved state and versions rechecked",
            state_inspection_event_id=inspected.event_id, checkpoint=ref))
        self.messages = checkpoint["messages"]
        self.sources = [SourceRef.model_validate_json(json.dumps(s)) for s in checkpoint["sources"]]
        self.originals = {k: HashedBlobRef.model_validate_json(json.dumps(v)) for k, v in checkpoint["image_originals"].items()}
        self.counts = checkpoint["counts"]
        self.used_ids = set(checkpoint["used_ids"])
        self.elapsed_before = checkpoint["elapsed_seconds"]
        return None

    def _stop(self, reason):
        artifacts = []
        artifact_paths = []
        for path in self.tools.artifacts():
            if path.is_file():
                artifacts.append(self.store.put_bytes(path.read_bytes()))
                artifact_paths.append(str(path))
        receipt = {"status": reason, "answer": self.answer,
            **self.counts, "elapsed_seconds": self.limits.seconds - self._remaining(),
            "limits": self.limits.model_dump(mode="json"), "retries": 0, "fallback": False,
            "billing_usd": None, "artifacts": [r.model_dump(mode="json") for r in artifacts],
            "artifact_paths": artifact_paths,
            "token_accounting": "UTF-8 bytes plus image pixels plus output cap reserved conservatively; service usage kept separately"}
        self.store.append(RunLifecyclePayload(action="stop", reason=reason,
            partial_artifacts=tuple(artifacts)), source_refs=(self.store.source("run-receipt", receipt),))
        usage = (UsageReported(raw_usage={"total_tokens": self.counts["reported_tokens"]})
            if self.counts["usage_complete"] and self.counts["model_calls"] else
            UsageMissing(reason="one or more requests lacked a complete token receipt, or no request was sent"))
        self.store.append(RunAggregateUsagePayload(usage=usage,
            raw_summary=self.store.capture(receipt), notes=("Locally summed request usage; no provider aggregate bill or subscription quota was supplied.",)))
        self.store.write_json("receipt.json", receipt)
        self.store.validate()
        return receipt
