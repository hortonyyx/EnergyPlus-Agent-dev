"""Cross-event checks that cannot live on an individual payload."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import ContractModel, NonEmptyStr
from .budget import BudgetAmounts, BudgetLedger
from .events import (
    AdapterRequestPayload,
    BudgetEventPayload,
    ContextEventPayload,
    EventEnvelope,
    ModelResponsePayload,
    RunLifecyclePayload,
    StateInspectionPayload,
    ToolExecutionPayload,
)
from .refs import SourceRef


class ExcerptDisclosure(ContractModel):
    reason: NonEmptyStr
    omitted_event_types: tuple[NonEmptyStr, ...]
    missing_event_ids: tuple[NonEmptyStr, ...] = ()
    source_records: tuple[SourceRef, ...]


class EventLog(ContractModel):
    mode: Literal["complete", "excerpt"]
    events: tuple[EventEnvelope, ...]
    budget_limit: BudgetAmounts | None = None
    excerpt: ExcerptDisclosure | None = None

    @model_validator(mode="after")
    def validate_event_log(self) -> EventLog:
        if not self.events:
            raise ValueError("event log cannot be empty")
        if self.mode == "excerpt":
            if self.excerpt is None or not self.excerpt.source_records:
                raise ValueError("excerpt mode needs disclosure and source records")
        elif self.excerpt is not None:
            raise ValueError("complete logs cannot carry excerpt disclosure")

        event_by_id: dict[str, EventEnvelope] = {}
        run_ids: set[str] = set()
        previous_sequence = -1
        for event in self.events:
            if event.event_id in event_by_id:
                raise ValueError(f"duplicate event_id: {event.event_id}")
            if event.sequence <= previous_sequence:
                raise ValueError("event sequence must be strictly increasing")
            previous_sequence = event.sequence
            event_by_id[event.event_id] = event
            run_ids.add(event.run_id)
            if self.mode == "complete":
                if event.occurred_at.kind == "historical_missing":
                    raise ValueError("complete logs require known timestamps")
                if event.parent_task.kind == "historical_missing":
                    raise ValueError("complete logs require known task ancestry")
                if (
                    isinstance(event.payload, ToolExecutionPayload)
                    and event.payload.capture_scope == "historical_excerpt"
                ):
                    raise ValueError(
                        "complete logs cannot contain historical-excerpt tool captures"
                    )
                if (
                    isinstance(event.payload, AdapterRequestPayload)
                    and event.payload.final_request_body.kind == "missing"
                ):
                    raise ValueError("complete logs require the exact final adapter request")
        if len(run_ids) != 1:
            raise ValueError("one EventLog represents exactly one run")

        missing_ids = set(self.excerpt.missing_event_ids if self.excerpt else ())
        self._validate_response_requests(event_by_id, missing_ids)
        self._validate_inspections(event_by_id, missing_ids)
        self._validate_recovery(event_by_id, missing_ids)
        self._validate_context(event_by_id, missing_ids)
        self._validate_budget_events()
        self._validate_duplicate_writes()
        return self

    def _validate_inspections(
        self, event_by_id: dict[str, EventEnvelope], missing_ids: set[str]
    ) -> None:
        for event in self.events:
            payload = event.payload
            if not isinstance(payload, StateInspectionPayload):
                continue
            _require_prior_event(
                payload.target_event_id,
                event,
                event_by_id,
                missing_ids,
                "state inspection target",
            )

    def _validate_response_requests(
        self, event_by_id: dict[str, EventEnvelope], missing_ids: set[str]
    ) -> None:
        for event in self.events:
            payload = event.payload
            if not isinstance(payload, ModelResponsePayload):
                continue
            request = _require_prior_event(
                payload.request_event_id,
                event,
                event_by_id,
                missing_ids,
                "model request",
            )
            if request is not None and not isinstance(
                request.payload, AdapterRequestPayload
            ):
                raise ValueError("request_event_id must reference an adapter request")

    def _validate_recovery(
        self, event_by_id: dict[str, EventEnvelope], missing_ids: set[str]
    ) -> None:
        for event in self.events:
            payload = event.payload
            if not isinstance(payload, RunLifecyclePayload):
                continue
            if payload.action == "retry":
                original = _require_prior_event(
                    payload.retry_of_event_id,
                    event,
                    event_by_id,
                    missing_ids,
                    "retry target",
                )
                if original is None:
                    continue
                tool = original.payload
                if isinstance(tool, AdapterRequestPayload):
                    continue
                if not isinstance(tool, ToolExecutionPayload):
                    raise ValueError("retry target must be a model request or tool execution")
                if tool.outcome == "succeeded":
                    raise ValueError("a successful tool execution cannot be retried")
                if tool.outcome != "unknown":
                    continue
                if tool.repeatability == "read_only":
                    continue
                inspection = _require_prior_event(
                    payload.state_inspection_event_id,
                    event,
                    event_by_id,
                    missing_ids,
                    "unknown-write state inspection",
                )
                if inspection is None:
                    raise ValueError("unknown write retry needs a recorded state inspection")
                check = inspection.payload
                if not isinstance(check, StateInspectionPayload):
                    raise ValueError("state_inspection_event_id must reference an inspection")
                if (
                    check.purpose != "unknown_write_recovery"
                    or check.target_event_id != original.event_id
                    or check.conclusion != "not_applied"
                ):
                    raise ValueError(
                        "unknown write retry requires persisted state proving not_applied"
                    )
            elif payload.action == "resume":
                inspection = _require_prior_event(
                    payload.state_inspection_event_id,
                    event,
                    event_by_id,
                    missing_ids,
                    "resume state inspection",
                )
                if inspection is None or not isinstance(
                    inspection.payload, StateInspectionPayload
                ):
                    raise ValueError("resume needs a recorded prior state inspection")
                check = inspection.payload
                if check.purpose != "resume" or check.conclusion != "safe_to_resume":
                    raise ValueError("resume inspection must conclude safe_to_resume")
                if payload.checkpoint != check.persisted_state:
                    raise ValueError("resume checkpoint must match the inspected persisted state")

        for event in self.events:
            tool = event.payload
            if not isinstance(tool, ToolExecutionPayload) or tool.retry_event_id is None:
                continue
            retry_event = _require_prior_event(
                tool.retry_event_id,
                event,
                event_by_id,
                missing_ids,
                "tool retry",
            )
            if retry_event is None or not isinstance(
                retry_event.payload, RunLifecyclePayload
            ):
                raise ValueError("retry_event_id must reference a retry lifecycle event")
            retry = retry_event.payload
            if retry.action != "retry":
                raise ValueError("retry_event_id must reference a retry action")
            original = event_by_id.get(retry.retry_of_event_id)
            if original is not None and isinstance(
                original.payload, ToolExecutionPayload
            ):
                if original.payload.operation_key != tool.operation_key:
                    raise ValueError("retried tool must preserve the operation_key")
                if original.payload.tool_name != tool.tool_name:
                    raise ValueError("retried tool must preserve the tool name")
                if original.payload.full_arguments != tool.full_arguments:
                    raise ValueError("retried tool must preserve the full arguments")

        previous_write_by_key: dict[str, EventEnvelope] = {}
        for event in self.events:
            tool = event.payload
            if (
                not isinstance(tool, ToolExecutionPayload)
                or tool.repeatability == "read_only"
            ):
                continue
            operation_key = tool.operation_key
            assert operation_key is not None
            previous = previous_write_by_key.get(operation_key)
            if previous is not None:
                if tool.retry_event_id is None:
                    raise ValueError(
                        "a repeated write operation needs a recorded retry event"
                    )
                retry_event = event_by_id[tool.retry_event_id]
                retry = retry_event.payload
                if (
                    not isinstance(retry, RunLifecyclePayload)
                    or retry.action != "retry"
                    or retry.retry_of_event_id != previous.event_id
                ):
                    raise ValueError(
                        "a repeated write retry must target the immediately previous attempt"
                    )
            previous_write_by_key[operation_key] = event

    def _validate_context(
        self, event_by_id: dict[str, EventEnvelope], missing_ids: set[str]
    ) -> None:
        for event in self.events:
            payload = event.payload
            if not isinstance(payload, ContextEventPayload):
                continue
            if payload.action == "compact":
                for replaced_id in payload.replaced_event_ids:
                    _require_prior_event(
                        replaced_id,
                        event,
                        event_by_id,
                        missing_ids,
                        "compressed event",
                    )
                continue
            if payload.action != "retrieve_image":
                continue
            removal = _require_prior_event(
                payload.removal_event_id,
                event,
                event_by_id,
                missing_ids,
                "image removal",
            )
            if removal is None:
                continue
            previous = removal.payload
            if not isinstance(previous, ContextEventPayload) or previous.action != "remove_image":
                raise ValueError("removal_event_id must reference an image removal")
            if previous.image != payload.image:
                raise ValueError("retrieved image must match the removed image reference")

    def _validate_budget_events(self) -> None:
        reservations = []
        settlements = []
        reservation_events: dict[str, EventEnvelope] = {}
        for event in self.events:
            payload = event.payload
            if not isinstance(payload, BudgetEventPayload):
                continue
            if payload.reservation is not None:
                if payload.reservation.task_id != event.task_id:
                    raise ValueError("budget reservation task must match event task")
                reservations.append(payload.reservation)
                reservation_events[payload.reservation.reservation_id] = event
            if payload.settlement is not None:
                reservation_event = reservation_events.get(
                    payload.settlement.reservation_id
                )
                if reservation_event is None:
                    raise ValueError("budget must be reserved before it is settled")
                if reservation_event.task_id != event.task_id:
                    raise ValueError("budget settlement task must match reservation task")
                settlements.append(payload.settlement)
        if reservations or settlements:
            if self.budget_limit is None:
                raise ValueError("budget events require the run's total budget limit")
            BudgetLedger(
                total_limit=self.budget_limit,
                reservations=tuple(reservations),
                settlements=tuple(settlements),
            )

    def _validate_duplicate_writes(self) -> None:
        applied_ids: set[str] = set()
        applied_operations: set[str] = set()
        for event in self.events:
            payload = event.payload
            if not isinstance(payload, ToolExecutionPayload):
                continue
            if payload.applied_write_id is None:
                continue
            if payload.applied_write_id in applied_ids:
                raise ValueError(f"duplicate applied_write_id: {payload.applied_write_id}")
            applied_ids.add(payload.applied_write_id)
            if payload.operation_key in applied_operations:
                raise ValueError(
                    f"operation applied more than once: {payload.operation_key}"
                )
            applied_operations.add(payload.operation_key)  # type: ignore[arg-type]


def validate_event_log(events: tuple[EventEnvelope, ...], **kwargs: object) -> EventLog:
    """Convenience helper for callers that already accumulated event envelopes."""

    return EventLog(events=events, **kwargs)


def _require_prior_event(
    referenced_id: str | None,
    current: EventEnvelope,
    event_by_id: dict[str, EventEnvelope],
    missing_ids: set[str],
    label: str,
) -> EventEnvelope | None:
    if referenced_id is None:
        raise ValueError(f"{label} reference is required")
    referenced = event_by_id.get(referenced_id)
    if referenced is None:
        if referenced_id in missing_ids:
            return None
        raise ValueError(f"{label} event does not exist: {referenced_id}")
    if referenced.sequence >= current.sequence:
        raise ValueError(f"{label} must precede the referencing event")
    return referenced
