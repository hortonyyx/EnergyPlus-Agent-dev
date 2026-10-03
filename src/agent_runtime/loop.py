"""Audited single-role runtime with bounded context and durable recovery."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field

from src.harness_contracts import (
    BudgetAmounts, BudgetEventPayload, CheckpointPayload, HashedBlobRef,
    MissingCapture, RunAggregateUsagePayload, RunLifecyclePayload, SourceRef,
    StateInspectionPayload, ToolExecutionPayload, ToolInvocationPayload,
    ToolPresentationPayload, UsageMissing, UsageReported, authorize_tool_call,
)
from src.harness_contracts.base import ContractModel
from .adapter import convert_tool_result, parse_response, prepare_request, reported_tokens
from .budget import PriceSchedule, RequestEstimate, RuntimeBudget
from .estimation import get_model_profile
from .store import EventStore


class RunLimits(ContractModel):
    model_calls: int = Field(ge=1)
    tool_calls: int = Field(ge=0)
    seconds: float = Field(gt=0)
    tokens: int = Field(ge=1)
    money_usd: Decimal | None = Field(default=None, ge=0)
    near_limit: Literal["stop", "reduce_output"] = "stop"
    min_output_tokens: int = Field(default=1, ge=1)
    context_tokens: int | None = Field(default=None, ge=1)
    max_model_retries: int = Field(default=0, ge=0)
    summary_every: int = Field(default=0, ge=0)

    def ledger_limit(self):
        return BudgetAmounts(tokens=self.tokens, calls=self.model_calls,
            seconds=Decimal(str(self.seconds)), money_usd=self.money_usd)


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
    context_policy: object | None = None
    pricing: PriceSchedule | None = None
    context_update: object | None = None
    fault_hook: object | None = None
    required_context_tags: tuple[str, ...] = ()
    required_view_ids: tuple[str, ...] = ()
    retrieve_images: tuple[tuple[str, str], ...] = ()
    strict_model_profile: bool = False
    root_tool_calls: int | None = None

    async def run(self, messages: list[dict], *, message_sources=None,
                  image_originals=None, resume=False) -> dict:
        self.started = time.monotonic()
        self.started_epoch = time.time()
        self.elapsed_before = 0.0
        self.messages, self.sources = [], []
        self.originals = dict(image_originals or {})
        self.used_ids = set()
        self.pending_response_id = None
        self.pending_pictures, self.pending_picture_events = [], []
        self.answer = None
        self.stage = "initialization"
        self.terminal_reason = None
        self.retry_of = None
        self.last_summary_at = 0
        self.context = None
        if self.context_policy is not None:
            from .context import ContextManager
            self.context = ContextManager(self.store, policy=self.context_policy)
        if self.store.is_root_task and self.store.budget_limit != self.limits.ledger_limit():
            raise ValueError("runtime limits differ from persisted budget")
        for name, value in self.limits.ledger_limit().model_dump().items():
            cap = getattr(self.role.budget, name)
            if cap is not None and value is not None and value > cap:
                raise ValueError(f"runtime exceeds role budget: {name}")
        self._load_budget()
        self._refresh_counts()
        specs = await self.tools.list_tools()
        self.specs = [{"type": "function", "function": {
            "name": t["name"], "description": t.get("description", ""),
            "parameters": t["inputSchema"]}} for t in specs]
        self.spec_by_name = {t["name"]: t for t in specs}
        self.tool_source = self.store.source("mcp-tool-definitions", self.specs)
        if self.store.events:
            if not resume:
                raise ValueError("existing journal requires explicit resume")
            reason = self._restore()
            if reason == "already_completed":
                return {**json.loads((self.store.task_directory / "receipt.json").read_bytes()),
                        "resume_status": reason}
            if reason:
                return self._stop(reason)
        else:
            self.store.append(RunLifecyclePayload(action="start", reason="single-role run started"),
                source_refs=(self.store.source("runtime-config", self._config()),))
            sources = list(message_sources or [self.store.source(f"initial-message-{i}", m,
                kind="user" if m.get("role") == "user" else "runtime")
                for i, m in enumerate(messages)])
            for message, source in zip(messages, sources, strict=True):
                self._append_message(message, source)
            if self.context:
                from .context import StateEntry
                for i, (message, source) in enumerate(zip(messages, sources, strict=True)):
                    if message.get("role") == "user":
                        # Keep the full user input, rather than an inferred paraphrase.
                        self.context.set_state(StateEntry(key=f"user-input-{i}",
                            category="user_requirement", value=(message["content"] if isinstance(message.get("content"), str)
                                else [b for b in message.get("content", []) if b.get("type") != "image_url"]),
                            epistemic_status="user_stated", source_refs=(source,)))
                        self.context.set_state(StateEntry(key=f"user-constraints-{i}",
                            category="constraint", value={"user_input_key": f"user-input-{i}",
                                "basis": "Keep constraints in the complete original user statement; no semantic extraction or expansion."},
                            epistemic_status="user_stated", source_refs=(source,)))
            self._checkpoint()
        try:
            for view_id, digest in self.retrieve_images:
                if self.context is None:
                    raise ValueError("image retrieval requires context management")
                self.context.retrieve_image(view_id, digest)
                self._checkpoint()
            while True:
                if self.terminal_reason:
                    return self._stop(self.terminal_reason)
                if self.pending_response_id:
                    reason = await self._execute_pending()
                    if reason:
                        return self._stop(reason)
                    continue
                reason = self._budget_stop()
                if reason:
                    return self._stop(reason)
                # Deterministic projection always precedes any optional paid summary.
                projection = self._project()
                if (self.context and self.limits.summary_every
                        and self.counts["tool_calls"] - self.last_summary_at >= self.limits.summary_every):
                    reason = await self._summarize()
                    if reason:
                        return self._stop(reason)
                    projection = self._project()
                if self.context:
                    # Make selection/retrieval decisions recoverable before sending.
                    self._checkpoint()
                self._fault("before_request")
                result, reason = await self._model_call(
                    projection[0], projection[1], purpose="retry" if self.retry_of else "primary_task",
                    tools=self.specs, context_event_id=projection[2])
                if reason:
                    return self._stop(reason)
                self._accept_response(result)
                self.retry_of = None
                self._checkpoint()
        except (Exception, asyncio.CancelledError) as exc:
            return self._exception_stop(exc)

    def _config(self):
        model_profile = asdict(get_model_profile(
            self.model, strict=self.strict_model_profile))
        # The persisted JSON decodes tuples as lists. Normalize here so resume
        # compares the live profile with the same shape that was saved.
        model_profile["aliases"] = list(model_profile["aliases"])
        return {"model": self.model, "parameters": self.parameters,
            "model_profile": model_profile,
            "strict_model_profile": self.strict_model_profile,
            "root_tool_calls": self.root_tool_calls,
            "role": self.role.model_dump(mode="json"),
            "versions": self.versions.model_dump(mode="json"),
            "limits": self.limits.model_dump(mode="json"),
            "context_policy": self.context_policy.model_dump(mode="json") if self.context_policy else None,
            "pricing": self.pricing.model_dump(mode="json") if self.pricing else None,
            "echo_fields": list(self.echo_fields),
            "required_context_tags": list(self.required_context_tags),
            "required_view_ids": list(self.required_view_ids)}

    def _load_budget(self):
        self.budget = RuntimeBudget.from_events(self.store.budget_limit, self.store.all_events,
            near_limit_policy=self.limits.near_limit, min_output_tokens=self.limits.min_output_tokens,
            pricing=self.pricing)
        self.task_budget = RuntimeBudget.from_events(self.limits.ledger_limit(), self.store.events,
            near_limit_policy=self.limits.near_limit, min_output_tokens=self.limits.min_output_tokens,
            pricing=self.pricing)

    def _refresh_counts(self):
        requests = [e for e in self.store.events if e.payload.event_type == "adapter_request"]
        responses = [e.payload for e in self.store.events if e.payload.event_type == "model_response"]
        self.counts = {"model_calls": len(requests),
            "tool_calls": sum(e.payload.event_type == "tool_invocation" for e in self.store.events),
            "reported_tokens": sum(reported_tokens(r.usage) or 0 for r in responses),
            "reserved_tokens": self.task_budget.ledger.committed.tokens or 0,
            "usage_complete": len(requests) == len(responses) and all(reported_tokens(r.usage) is not None for r in responses)}

    def _project(self):
        if self.context is None:
            return self.messages, self.sources, None
        p = self.context.project(required_tags=self.required_context_tags,
            required_view_ids=self.required_view_ids, consume_retrievals=False)
        return list(p.messages), list(p.sources), p.decision_event_ids[-1] if p.decision_event_ids else None

    async def _model_call(self, messages, sources, *, purpose, tools, context_event_id=None):
        parameters = dict(self.parameters)
        degradation = None
        logical_purpose = "context_summary" if purpose == "context_summary" else "primary_task"
        while True:
            self.stage = "prepare_request"
            prepared = prepare_request(store=self.store, model=self.model,
                messages=messages, message_sources=sources, tools=tools,
                tool_source=self.tool_source, parameters=parameters, versions=self.versions,
                image_originals=self.originals,
                strict_model_profile=self.strict_model_profile)
            profile_limit = prepared.context_window_tokens
            configured_limit = self.limits.context_tokens
            available_limits = tuple(limit for limit in (profile_limit, configured_limit)
                                     if limit is not None)
            effective_context_limit = min(available_limits) if available_limits else None
            if (effective_context_limit is not None
                    and prepared.token_reservation_estimate > effective_context_limit):
                if profile_limit is not None and profile_limit <= effective_context_limit:
                    return None, "model_profile_context_limit_exhausted"
                return None, "configured_context_limit_exhausted"
            self._load_budget()
            remaining = self._remaining()
            if remaining <= 0:
                return None, self._scoped_budget_reason("time", task=True)
            # Wall-clock deadline covers tools, summaries, retries, and restart downtime.
            seconds = min(
                Decimal(str(remaining)),
                self.budget.available.seconds,
                self.task_budget.available.seconds,
            )
            if seconds <= 0:
                return None, self._scoped_budget_reason(
                    "time", task=self.task_budget.available.seconds <= 0
                )
            budget_purpose = (
                "child_task"
                if purpose == "primary_task" and not self.store.is_root_task
                else purpose
            )
            estimate = RequestEstimate.for_model_call(purpose=budget_purpose, task_id=self.store.task_id,
                input_token_upper_bound=prepared.input_token_upper_bound,
                output_token_limit=prepared.output_token_limit, seconds=seconds,
                estimate_source=prepared.estimate_source,
                pricing=self.pricing)
            reservation_id = self.store.next_reservation_id()
            task_decision = self.task_budget.reserve(reservation_id, estimate)
            if task_decision.action == "stop":
                return None, self._budget_reason(
                    task_decision,
                    scope=None if self.store.is_root_task else "child",
                )
            effective = task_decision.effective_estimate
            decision = self.budget.reserve(reservation_id, effective)
            if decision.action == "stop":
                return None, self._budget_reason(
                    decision,
                    scope="root" if not self.store.is_root_task else None,
                )
            if task_decision.action == "reduce_output" or decision.action == "reduce_output":
                reduction = (
                    decision
                    if decision.action == "reduce_output"
                    else task_decision
                )
                degradation = reduction.model_dump(mode="json")
                key = "max_tokens" if "max_tokens" in parameters else "max_completion_tokens"
                parameters[key] = reduction.output_token_limit
                # No event or request has been emitted yet. Re-estimate exact wire bytes.
                self._load_budget()
                continue
            reservation = decision.reservation
            self.store.append(BudgetEventPayload(action="reserve", reservation=reservation),
                source_refs=(self.store.source("request-budget-decision", {
                    **decision.model_dump(mode="json"), "original_output_limit": self.parameters.get("max_tokens", self.parameters.get("max_completion_tokens")),
                    "actual_output_limit": prepared.output_token_limit,
                    "near_limit_action": "reduce_output" if degradation else "allow",
                    "degradation": degradation,
                    "token_estimate": asdict(prepared.token_estimate),
                    "context_limits": {"model_profile": profile_limit,
                        "configured": configured_limit,
                        "effective": effective_context_limit}}),))
            self._fault("after_reservation")
            if self.retry_of:
                self.store.append(RunLifecyclePayload(action="retry", reason="explicit bounded model retry",
                    retry_of_event_id=self.retry_of, attempt=self._retry_count() + 2))
                self._fault("after_retry")
            self.stage = "model_request"
            request = self.store.append(prepared.event_payload.model_copy(update={
                "reservation_id": reservation.reservation_id, "logical_purpose": logical_purpose}))
            self._refresh_counts()
            self._fault("after_request")
            sent_at = time.monotonic()
            try:
                raw = await asyncio.wait_for(self.adapter.send(prepared, timeout=self._remaining()), timeout=self._remaining())
            except (Exception, asyncio.CancelledError) as exc:
                settlement_stop = self._settle(reservation.reservation_id, UsageMissing(reason="request ended without a service usage receipt"),
                             seconds=time.monotonic() - sent_at)
                self._refresh_counts()
                if settlement_stop:
                    return None, settlement_stop
                if (not isinstance(exc, (asyncio.CancelledError, TimeoutError))
                        and self._retry_count() < self.limits.max_model_retries):
                    self.retry_of, purpose = request.event_id, "retry"
                    continue
                return None, self._exception_reason(exc)
            self.stage = "model_response"
            parsed = parse_response(raw, request.event_id, self.store, echo_fields=self.echo_fields)
            elapsed = time.monotonic() - sent_at
            response = self.store.append(parsed.event_payload,
                source_refs=(self.store.source("request-duration", {"elapsed_seconds": elapsed,
                    "basis": "local monotonic wall time from send through returned response"}),))
            reason = self._settle(reservation.reservation_id, parsed.event_payload.usage,
                                  seconds=elapsed)
            self._refresh_counts()
            self._present_tools(prepared.body, sources, request, response, context_event_id)
            self._fault("after_response")
            if reason:
                return None, reason
            if parsed.protocol_error:
                return None, parsed.protocol_error
            if reported_tokens(parsed.event_payload.usage) is None:
                return None, "token_usage_unavailable"
            if self._remaining() <= 0:
                return None, "time_budget_exhausted"
            return response, None

    def _settle(self, reservation_id, usage, *, seconds):
        if any(s.reservation_id == reservation_id for s in self.budget.ledger.settlements):
            return None
        charged_seconds = Decimal(str(max(0.0, seconds))) if seconds is not None else None
        actual = BudgetAmounts(tokens=reported_tokens(usage), calls=1, seconds=charged_seconds)
        task_decision = self.task_budget.settle(reservation_id,
            actual=actual, usage=usage)
        if task_decision.action == "stop":
            decision = task_decision
        else:
            decision = self.budget.settle(reservation_id,
                actual=actual, usage=usage)
        if decision.action == "stop":
            self.store.append(RunLifecyclePayload(action="failure", failure_stage="budget_settlement",
                reason=decision.reason), source_refs=(self.store.source("budget-violation", {
                    "decision": decision.model_dump(mode="json"), "observed": actual.model_dump(mode="json"),
                    "usage": usage.model_dump(mode="json")}),))
            if "seconds" in decision.exceeded_dimensions:
                # Cancellation cleanup can cross the deadline by milliseconds.
                # Keep the observed duration and conservative hold unchanged,
                # but identify the exhausted time allowance in the receipt.
                task_limited = self.task_budget.available.seconds <= self.budget.available.seconds
                return self._scoped_budget_reason("time", task=task_limited)
            return "token_reservation_exceeded" if "tokens" in decision.exceeded_dimensions else decision.reason
        self.store.append(BudgetEventPayload(action="settle", settlement=decision.settlement))
        return None

    def _present_tools(self, body, sources, request, response, context_event_id):
        delivered = {e.payload.tool_execution_event_id for e in self.store.events if e.payload.event_type == "tool_presentation"}
        events = {e.event_id: e for e in self.store.events}
        for message, source in zip(body["messages"], sources, strict=True):
            event = events.get(source.event_id)
            if (message.get("role") != "tool" or event is None or event.payload.event_type != "tool_execution"
                    or event.event_id in delivered or event.payload.shown_result.kind == "missing"):
                continue
            original = self.store.resolve(event.payload.shown_result)
            original_blocks = original.get("image_blocks", [])
            shown_blocks = []
            all_blocks = [b for m in body["messages"] if isinstance(m.get("content"), list) for b in m["content"]]
            for block in original_blocks:
                if block in all_blocks:
                    shown_blocks.append(block)
            actual = {**original, "tool_message": message, "image_blocks": shown_blocks}
            capture = event.payload.shown_result if actual == original else self.store.capture(actual, force_blob=True)
            self.store.append(ToolPresentationPayload(tool_execution_event_id=event.event_id,
                request_event_id=request.event_id, response_event_id=response.event_id,
                shown_result=capture, context_event_id=context_event_id))
            delivered.add(event.event_id)

    def _accept_response(self, event):
        if any(source.event_id == event.event_id for source in self.sources):
            return
        parsed = parse_response(self.store.resolve(event.payload.raw_response), event.payload.request_event_id,
                                self.store, echo_fields=self.echo_fields)
        if parsed.protocol_error:
            self.terminal_reason = parsed.protocol_error
            return
        calls = parsed.event_payload.tool_calls
        invoked = {e.payload.call_id for e in self.store.events if e.payload.event_type == "tool_invocation"}
        additional = sum(c.call_id not in invoked for c in calls)
        if self.counts["tool_calls"] + additional > self.limits.tool_calls:
            self.terminal_reason = "tool_budget_exhausted"
            return
        if self.root_tool_calls is not None:
            root_used = sum(e.payload.event_type == "tool_invocation" for e in self.store.all_events)
            if root_used + additional > self.root_tool_calls:
                self.terminal_reason = self._scoped_budget_reason("tool")
                return
        try:
            for call in calls:
                if call.call_id in self.used_ids or call.tool_name not in self.spec_by_name:
                    raise ValueError("unknown tool or reused call identity")
                repeatability = self.tools.repeatability(call.tool_name)
                authorize_tool_call(self.role, call.tool_name, "read" if repeatability == "read_only" else "write")
        except ValueError:
            self.terminal_reason = "tool_authorization_failed"
            return
        if self.context:
            self.context.acknowledge_projection()
        self._append_message(parsed.assistant_message, self._event_source(event))
        if calls:
            self.pending_response_id = event.event_id
        else:
            self.answer = "\n".join(parsed.event_payload.visible_text)
            self.terminal_reason = "completed"

    async def _execute_pending(self):
        event = next(e for e in self.store.events if e.event_id == self.pending_response_id)
        for call in event.payload.tool_calls:
            if call.call_id in self.used_ids:
                continue
            if self._remaining() <= 0:
                return "time_budget_exhausted"
            # A pending response may survive a process interruption while
            # another task consumes the root allowance before it resumes.
            if self.root_tool_calls is not None and sum(
                    e.payload.event_type == "tool_invocation" for e in self.store.all_events
            ) >= self.root_tool_calls:
                return self._scoped_budget_reason("tool")
            self.stage = f"tool:{call.tool_name}"
            self._fault("before_tool")
            repeatability = self.tools.repeatability(call.tool_name)
            write = repeatability != "read_only"
            key = f"{self.store.run_id}:{call.call_id}" if write else None
            before = self.store.put_json(self.tools.snapshot_state())
            intent = self.store.append(ToolInvocationPayload(call_id=call.call_id,
                tool_name=call.tool_name, full_arguments=call.full_arguments,
                repeatability=repeatability, operation_key=key, state_before=before))
            self._refresh_counts()
            try:
                raw = await asyncio.wait_for(self.tools.call_tool(call.tool_name, call.full_arguments), timeout=self._remaining())
            except (Exception, asyncio.CancelledError) as exc:
                failed = self._unknown_execution(intent)
                if write:
                    self._inspect_unknown(failed.event_id, before)
                return "unknown_write_outcome" if write else self._exception_reason(exc)
            self._fault("after_tool")
            try:
                _, _, shown, _ = convert_tool_result(call.call_id, raw, self.store)
            except Exception:
                self.store.append(ToolExecutionPayload(call_id=call.call_id,
                    tool_name=call.tool_name, full_arguments=call.full_arguments,
                    raw_result=self.store.capture(raw, force_blob=True),
                    shown_result=MissingCapture(reason="MCP presentation conversion failed"),
                    repeatability=repeatability, operation_key=key, outcome="failed",
                    invocation_event_id=intent.event_id, presentation_status="prepared"))
                return "tool_presentation_failed"
            execution = self.store.append(ToolExecutionPayload(call_id=call.call_id,
                tool_name=call.tool_name, full_arguments=call.full_arguments,
                raw_result=self.store.capture(raw, force_blob=True),
                shown_result=self.store.capture(shown, force_blob=True),
                repeatability=repeatability, operation_key=key,
                outcome="failed" if raw.get("isError") else "succeeded",
                applied_write_id=key if write and not raw.get("isError") else None,
                invocation_event_id=intent.event_id, presentation_status="prepared"),
                source_refs=(self.store.source("tool-state-after", self.tools.snapshot_state()),))
            self._fault("after_execution")
            self._accept_execution(execution)
            self._checkpoint()
        self._finish_tool_batch()
        self._checkpoint()
        return None

    def _accept_execution(self, event):
        p = event.payload
        if p.call_id in self.used_ids:
            return
        if p.shown_result.kind == "missing":
            self.terminal_reason = "resume_pending_operation" if p.outcome == "unknown" else "tool_presentation_failed"
            return
        raw = self.store.resolve(p.raw_result)
        shown = self.store.resolve(p.shown_result)
        self._append_message(shown["tool_message"], self._event_source(event), kind="tool_result")
        self.pending_pictures.extend(shown["image_blocks"])
        if shown["image_blocks"]:
            self.pending_picture_events.append(event.event_id)
        origins = getattr(self.tools, "image_origins", lambda _: {})(raw)
        for ref_dict in json.loads(shown["tool_message"]["content"]).get("images", []):
            ref = HashedBlobRef.model_validate_json(json.dumps(ref_dict))
            origin = origins.get(ref.sha256, {})
            path = origin.get("original_path") if isinstance(origin, dict) else origin
            self.originals[ref.sha256] = self.store.put_bytes(Path(path).read_bytes(), ref.media_type) if path else ref
            if self.context:
                view_id = origin.get("view_id") if isinstance(origin, dict) else None
                self.context.register_image(view_id or f"{p.call_id}:{ref.sha256}", ref,
                    source=self._event_source(event), tags=tuple(origin.get("tags", ())) if isinstance(origin, dict) else ())
        self.used_ids.add(p.call_id)
        if self.context_update and self.context:
            self.context_update(self, event, raw)

    def _finish_tool_batch(self):
        if self.pending_pictures:
            self._append_message({"role": "user", "content": self.pending_pictures},
                SourceRef(source_id="tool-images", source_kind="tool",
                    locator=",".join(self.pending_picture_events), event_id=self.pending_picture_events[-1],
                    blob=self.store.put_json({"origin_events": self.pending_picture_events,
                        "conversion": "MCP images after all tool replies, exact image bytes"})))
        self.pending_pictures, self.pending_picture_events = [], []
        self.pending_response_id = None

    def _append_message(self, message, source, *, kind="message"):
        self.messages.append(message)
        self.sources.append(source)
        if self.context:
            self.context.append(message, source, kind=kind)

    def _unknown_execution(self, invocation):
        p = invocation.payload
        return self.store.append(ToolExecutionPayload(call_id=p.call_id, tool_name=p.tool_name,
            full_arguments=p.full_arguments, repeatability=p.repeatability, operation_key=p.operation_key,
            outcome="unknown", raw_result=MissingCapture(reason="interrupted after durable intent; result not captured"),
            shown_result=MissingCapture(reason="no result was presented"),
            invocation_event_id=invocation.event_id, presentation_status="prepared"))

    def _inspect_unknown(self, event_id, before):
        state = self.store.put_json({"before": before.model_dump(mode="json") if before else None,
            "observed_after": self.tools.snapshot_state(),
            "reason": "snapshot alone cannot prove completion or absence of a late write"})
        self.store.append(StateInspectionPayload(purpose="unknown_write_recovery",
            target_event_id=event_id, persisted_state=state, conclusion="inconclusive"))

    def _checkpoint(self):
        snapshot = {"messages": self.messages if self.context is None else None,
            "sources": [s.model_dump(mode="json") for s in self.sources] if self.context is None else None,
            "context": self.context.dump() if self.context else None,
            "image_originals": {k: v.model_dump(mode="json") for k, v in self.originals.items()},
            "counts": self.counts, "used_ids": sorted(self.used_ids), "answer": self.answer,
            "pending_response_id": self.pending_response_id,
            "pending_pictures": self.store.put_json(self.pending_pictures).model_dump(mode="json"),
            "pending_picture_events": self.pending_picture_events,
            "terminal_reason": self.terminal_reason, "retry_of": self.retry_of,
            "last_summary_at": self.last_summary_at,
            "elapsed_seconds": self.limits.seconds - self._remaining(), "started_epoch": self.started_epoch,
            "tool_state": self.tools.snapshot_state(), "config": self._config(),
            "versions": self.versions.model_dump(mode="json"), "last_event_id": self.store.events[-1].event_id}
        ref = self.store.put_json(snapshot)
        self.store.append(CheckpointPayload(state=ref, after_event_id=snapshot["last_event_id"]))
        self.store.write_json("checkpoint.json", ref.model_dump(mode="json"))
        self._fault("after_checkpoint")

    def _restore(self):
        found = self.store.latest_checkpoint()
        if found is None:
            return "resume_checkpoint_missing"
        ref, saved, sequence = found
        self.started_epoch = saved.get("started_epoch", time.time() - saved["elapsed_seconds"])
        self.elapsed_before = max(saved["elapsed_seconds"], time.time() - self.started_epoch)
        self.started = time.monotonic()
        # Resume may not change prompts, tools, policy, budgets, route, or code.
        if saved.get("config", self._config()) != self._config():
            return "resume_configuration_changed"
        if saved["versions"] != self.versions.model_dump(mode="json"):
            return "resume_state_changed"
        suffix = [e for e in self.store.events if e.sequence > sequence]
        if any(e.payload.event_type == "run_lifecycle" and e.payload.reason == "completed" for e in suffix):
            if (self.store.task_directory / "receipt.json").exists():
                return "already_completed"
        if saved.get("context"):
            from .context import ContextManager
            self.context = ContextManager.load(self.store, saved["context"], policy=self.context_policy)
            self.messages, self.sources = self.context.full_history()
        else:
            self.messages = saved["messages"]
            self.sources = [SourceRef.model_validate_json(json.dumps(s)) for s in saved["sources"]]
        self.originals = {k: HashedBlobRef.model_validate_json(json.dumps(v)) for k, v in saved["image_originals"].items()}
        self.used_ids = set(saved["used_ids"])
        self.answer, self.terminal_reason = saved.get("answer"), saved.get("terminal_reason")
        self.pending_response_id = saved.get("pending_response_id")
        self.pending_pictures = json.loads(self.store.get_bytes(HashedBlobRef.model_validate_json(json.dumps(saved["pending_pictures"])))) if saved.get("pending_pictures") else []
        self.pending_picture_events = saved.get("pending_picture_events", [])
        self.retry_of = saved.get("retry_of")
        self.last_summary_at = saved.get("last_summary_at", 0)
        requested_reservations = {e.payload.reservation_id for e in self.store.events
            if e.payload.event_type == "adapter_request" and e.payload.reservation_id}
        if any(r.reservation_id not in requested_reservations for r in self.task_budget.ledger.reservations):
            # The durable request always precedes send. A reservation without one
            # was never sent, but no release contract exists yet: keep the hold.
            return "resume_uncheckpointed_budget_reservation"
        expected_state = saved["tool_state"]
        committed_summaries = set()
        for event in suffix:
            if event.payload.event_type == "context" and event.payload.details:
                details = json.loads(self.store.get_bytes(event.payload.details))
                if details.get("kind") == "validated_model_summary":
                    committed_summaries.add(details.get("response_event_id"))
        # First reconstruct all durable results, then inspect the real saved state.
        for event in suffix:
            p = event.payload
            if p.event_type == "model_response":
                request = next(e for e in self.store.events if e.event_id == p.request_event_id)
                reservation_id = request.payload.reservation_id
                if reservation_id:
                    timing = next((s.blob for s in event.source_refs if s.source_id == "request-duration"), None)
                    elapsed = json.loads(self.store.get_bytes(timing))["elapsed_seconds"] if timing else None
                    reason = self._settle(reservation_id, p.usage, seconds=elapsed)
                    if reason:
                        return reason
                    if reported_tokens(p.usage) is None:
                        return "token_usage_unavailable"
                    reservation = next(r for r in self.budget.ledger.reservations if r.reservation_id == reservation_id)
                    if request.payload.logical_purpose == "context_summary" or reservation.purpose == "context_summary":
                        if event.event_id in committed_summaries:
                            self.last_summary_at = self.counts["tool_calls"]
                        else:
                            try:
                                self._accept_summary(event)
                            except ValueError:
                                return "summary_validation_failed"
                        continue
                self._accept_response(event)
            elif p.event_type == "tool_execution":
                self._accept_execution(event)
                after = next((s.blob for s in event.source_refs if s.source_id == "tool-state-after"), None)
                if after:
                    expected_state = json.loads(self.store.get_bytes(after))
            elif p.event_type == "context" and self.context:
                self.context.replay_events([event])
        if self.context:
            self.messages, self.sources = self.context.full_history()
        complete = {e.payload.invocation_event_id for e in self.store.events if e.payload.event_type == "tool_execution"}
        for event in list(self.store.events):
            p = event.payload
            if p.event_type == "tool_invocation" and event.event_id not in complete:
                result = self._unknown_execution(event)
                if p.repeatability != "read_only":
                    self._inspect_unknown(result.event_id, p.state_before)
                return "resume_pending_operation"
        for event in self.store.events:
            if event.payload.event_type == "tool_execution" and event.payload.outcome == "unknown":
                if event.payload.repeatability != "read_only":
                    self._inspect_unknown(event.event_id, None)
                return "resume_pending_operation"
        safe = expected_state == self.tools.snapshot_state()
        inspected = self.store.append(StateInspectionPayload(purpose="resume",
            target_event_id=saved["last_event_id"], persisted_state=ref,
            conclusion="safe_to_resume" if safe else "inconclusive"))
        if not safe:
            return "resume_state_changed"
        responded = {e.payload.request_event_id for e in self.store.events if e.payload.event_type == "model_response"}
        retried = {e.payload.retry_of_event_id for e in self.store.events
            if e.payload.event_type == "run_lifecycle" and e.payload.action == "retry"}
        dangling = [e for e in self.store.events if e.payload.event_type == "adapter_request"
                    and e.event_id not in responded and e.event_id not in retried]
        if dangling:
            request = dangling[-1]
            if request.payload.reservation_id:
                self._settle(request.payload.reservation_id, UsageMissing(reason="process interrupted with request outcome unknown"), seconds=None)
            if self._retry_count() >= self.limits.max_model_retries:
                return "resume_request_outcome_unknown"
            if request.payload.logical_purpose == "context_summary":
                return "resume_request_outcome_unknown"
            self.retry_of = request.event_id
        self._refresh_counts()
        if self.budget.fatal_reason:
            return "token_reservation_exceeded"
        self.store.append(RunLifecyclePayload(action="resume", reason="durable results replayed and saved state rechecked",
            state_inspection_event_id=inspected.event_id, checkpoint=ref))
        self._checkpoint()
        return None

    async def _summarize(self):
        # A constrained summary may rearrange existing state; it cannot invent facts.
        from .context import SummaryCandidate
        projection = self.context.project(required_tags=self.required_context_tags,
            required_view_ids=self.required_view_ids, consume_retrievals=False)
        history_ids = projection.omitted_history_ids or tuple(r.history_id for r in self.context.history
            if r.source.event_id and r.kind != "summary")
        if not history_ids:
            self.last_summary_at = self.counts["tool_calls"]
            return None
        request = self.context.build_summary_request(history_ids)
        content = {"instruction": request.instruction,
            "response_schema": SummaryCandidate.model_json_schema(),
            "covered_history_ids": list(history_ids),
            "history_references": [{"history_id": r.history_id,
                "message_blob": r.message_blob.model_dump(mode="json"), "source": r.source.model_dump(mode="json")}
                for r in request.history],
            "current_state": [s.model_dump(mode="json") for s in request.current_state],
            "text_encoding": "JSON array of statements, UTF-8, sorted keys, no whitespace separators; values and epistemic status must be exact"}
        messages = [{"role": "system", "content": "Select useful existing state entries for a compact index. Return only the required JSON object; do not add or reinterpret facts."},
                    {"role": "user", "content": json.dumps(content, ensure_ascii=False)}]
        sources = [self.store.source(f"context-summary-request-{i}", m) for i, m in enumerate(messages)]
        response, reason = await self._model_call(messages, sources,
            purpose="context_summary", tools=[])
        if reason:
            return reason
        try:
            self._accept_summary(response)
        except ValueError:
            return "summary_validation_failed"
        self.retry_of = None
        self._checkpoint()
        return None

    def _accept_summary(self, response):
        from .context import SummaryCandidate
        if response.payload.tool_calls:
            raise ValueError("context summaries cannot invoke tools")
        text = "\n".join(response.payload.visible_text)
        candidate = SummaryCandidate.model_validate_json(text)
        self.context.compact_with_summary(candidate, source=self._event_source(response))
        self.last_summary_at = self.counts["tool_calls"]

    def _remaining(self):
        return max(0.0, self.limits.seconds - self.elapsed_before - (time.monotonic() - self.started))

    def _budget_stop(self):
        if self._remaining() <= 0:
            return self._scoped_budget_reason("time", task=True)
        if self.counts["model_calls"] >= self.limits.model_calls:
            return self._scoped_budget_reason("model", task=True)
        if self.task_budget.available.calls <= 0:
            return self._scoped_budget_reason("model", task=True)
        if self.task_budget.available.tokens <= 0:
            return self._scoped_budget_reason("token", task=True)
        if (self.task_budget.available.money_usd is not None
                and self.task_budget.available.money_usd <= 0):
            return self._scoped_budget_reason("money", task=True)
        if self.task_budget.available.seconds <= 0:
            return self._scoped_budget_reason("time", task=True)
        if self.budget.available.calls <= 0:
            return self._scoped_budget_reason("model")
        if self.budget.available.tokens <= 0:
            return self._scoped_budget_reason("token")
        if self.budget.available.money_usd is not None and self.budget.available.money_usd <= 0:
            return self._scoped_budget_reason("money")
        if self.budget.available.seconds <= 0:
            return self._scoped_budget_reason("time")
        return None

    def _budget_reason(self, decision, *, scope=None):
        names = {"calls": "model", "tokens": "token", "seconds": "time", "money_usd": "money"}
        if decision.exceeded_dimensions:
            reason = names[decision.exceeded_dimensions[0]] + "_budget_exhausted"
            return f"{scope}_{reason}" if scope else reason
        return decision.reason

    def _scoped_budget_reason(self, dimension, *, task=False):
        reason = f"{dimension}_budget_exhausted"
        if self.store.is_root_task:
            return reason
        return f"{'child' if task else 'root'}_{reason}"

    def _retry_count(self):
        return sum(e.payload.event_type == "run_lifecycle" and e.payload.action == "retry" for e in self.store.events)

    def _fault(self, name):
        if self.fault_hook:
            self.fault_hook(name, self)

    def _event_source(self, event):
        return SourceRef(source_id=event.event_id, source_kind="tool" if event.payload.event_type == "tool_execution" else "runtime",
            locator=f"events.jsonl:{event.sequence + 1}", event_id=event.event_id)

    def _exception_reason(self, exc):
        timeout = isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        cancel = isinstance(exc, asyncio.CancelledError)
        reason = self._scoped_budget_reason("time", task=True) if timeout else "cancelled" if cancel else "failed"
        action = "timeout" if timeout else "cancel" if cancel else "failure"
        fields = {"failure_stage": self.stage} if action == "failure" else {}
        self.store.append(RunLifecyclePayload(action=action,
            reason=f"{reason}; error_type={type(exc).__name__}", **fields))
        return reason

    def _exception_stop(self, exc):
        return self._stop(self._exception_reason(exc))

    def _stop(self, reason):
        self._refresh_counts()
        artifacts, paths = [], []
        for path in self.tools.artifacts():
            if path.is_file():
                artifacts.append(self.store.put_bytes(path.read_bytes()))
                paths.append(str(path))
        costs = [s.cost for s in self.task_budget.ledger.settlements]
        estimated = self.task_budget.ledger.committed.money_usd
        receipt = {"status": reason, "answer": self.answer,
            **self.counts, "elapsed_seconds": self.limits.seconds - self._remaining(),
            "limits": self.limits.model_dump(mode="json"), "retries": self._retry_count(), "fallback": False,
            "billing_usd": str(sum(c.usd for c in costs)) if costs and all(c.kind == "reported" for c in costs) else None,
            "estimated_money_upper_bound_usd": str(estimated) if estimated is not None else None,
            "artifacts": [r.model_dump(mode="json") for r in artifacts], "artifact_paths": paths,
            "token_accounting": "service token use plus outstanding/unknown holds; estimates are not billing",
            "budget": self.budget.ledger.model_dump(mode="json"),
            "root_budget_available": self.budget.available.model_dump(mode="json"),
            "task_budget": self.task_budget.ledger.model_dump(mode="json"),
            "task_budget_available": self.task_budget.available.model_dump(mode="json"),
            "budget_scope": "root" if self.store.is_root_task else "child"}
        self.store.append(RunLifecyclePayload(action="stop", reason=reason, partial_artifacts=tuple(artifacts)),
            source_refs=(self.store.source("run-receipt", receipt),))
        usage = UsageReported(raw_usage={"total_tokens": self.counts["reported_tokens"]}) if self.counts["usage_complete"] and self.counts["model_calls"] else UsageMissing(reason="one or more requests lacked complete usage, or none were sent")
        self.store.append(RunAggregateUsagePayload(usage=usage,
            raw_summary=self.store.capture(receipt), notes=("Locally summed usage; no aggregate provider bill was supplied.",)))
        self.store.write_json("receipt.json", receipt)
        self.store.validate()
        return receipt
