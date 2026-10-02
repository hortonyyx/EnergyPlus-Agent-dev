"""Audited long-context projection with lossless history and image retrieval.

The manager owns no model client and contains no building-domain imports.  It
keeps the durable history, current structured state, and the request projection
as separate things.  A caller may supply a summary callback, but that callback
must use the runtime's normal request/budget/event path.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import inspect
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, Literal

from pydantic import Field, JsonValue, field_validator, model_validator

from src.harness_contracts import (
    ContextEventPayload,
    EventEnvelope,
    HashedBlobRef,
    SourceRef,
)
from src.harness_contracts.base import ContractModel, NonEmptyStr

from .store import EventStore, json_bytes


StateCategory = Literal[
    "user_requirement",
    "constraint",
    "evidence_reference",
    "artifact_version",
    "unresolved",
    "todo",
    "dimension",
    "object_id",
    "geometry",
    "general",
]
EpistemicStatus = Literal[
    "user_stated", "observed", "computed", "inferred", "assumed", "unresolved"
]
HistoryKind = Literal["message", "tool_result", "summary"]

_PROTECTED_CATEGORIES = frozenset(
    {"artifact_version", "dimension", "object_id", "geometry"}
)
_CHECKLIST_CATEGORIES: tuple[StateCategory, ...] = (
    "user_requirement",
    "constraint",
    "evidence_reference",
    "artifact_version",
    "unresolved",
    "todo",
    "dimension",
    "object_id",
    "geometry",
    "general",
)


class ContextPolicy(ContractModel):
    """Deterministic request projection policy."""

    active_window_messages: int = Field(default=16, ge=1)
    large_result_bytes: int = Field(default=8_192, ge=1)
    pinned_tags: tuple[NonEmptyStr, ...] = ()
    preserve_initial_messages: int = Field(default=2, ge=0)
    max_images: int | None = Field(default=12, ge=1)
    max_image_bytes: int | None = Field(default=32_000_000, ge=1)

    @field_validator("pinned_tags")
    @classmethod
    def unique_pinned_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("pinned context tags must be unique")
        return value


class StateEntry(ContractModel):
    """A machine-searchable current-state item, independent of summaries."""

    key: NonEmptyStr
    category: StateCategory
    value: JsonValue
    epistemic_status: EpistemicStatus
    source_refs: tuple[SourceRef, ...] = Field(min_length=1)
    revision: int = Field(default=1, ge=1)
    active: bool = True

    @model_validator(mode="after")
    def status_matches_category(self) -> "StateEntry":
        if self.category == "user_requirement" and self.epistemic_status != "user_stated":
            raise ValueError("user requirements must remain user_stated")
        if self.category == "unresolved" and self.epistemic_status != "unresolved":
            raise ValueError("unresolved entries must remain unresolved")
        return self


class HistoryRecord(ContractModel):
    history_id: NonEmptyStr
    message: dict[str, JsonValue]
    source: SourceRef
    message_blob: HashedBlobRef
    kind: HistoryKind = "message"
    tags: tuple[NonEmptyStr, ...] = ()
    image_keys: tuple[NonEmptyStr, ...] = ()
    summary_slot: NonEmptyStr | None = None
    summary_state_revisions: dict[str, int] = Field(default_factory=dict)
    content_sha256: NonEmptyStr

    @model_validator(mode="after")
    def summary_has_slot(self) -> "HistoryRecord":
        if self.kind == "summary" and self.summary_slot is None:
            raise ValueError("summary records need a summary_slot")
        if self.kind != "summary" and self.summary_slot is not None:
            raise ValueError("summary_slot is only valid for summary records")
        if self.kind != "summary" and self.summary_state_revisions:
            raise ValueError("summary state revisions are only valid for summary records")
        if any(revision < 1 for revision in self.summary_state_revisions.values()):
            raise ValueError("summary state revisions must be positive")
        return self


class ImageRecord(ContractModel):
    key: NonEmptyStr
    view_id: NonEmptyStr
    image: HashedBlobRef
    source: SourceRef
    tags: tuple[NonEmptyStr, ...] = ()
    registration_index: int = Field(ge=0)
    active: bool = True
    removal_event_id: NonEmptyStr | None = None


class SummaryStatement(ContractModel):
    """A summary assertion that must exactly reproduce an existing state item."""

    state_key: NonEmptyStr
    value: JsonValue
    epistemic_status: EpistemicStatus
    source_refs: tuple[SourceRef, ...] = Field(min_length=1)


class SummaryCandidate(ContractModel):
    covered_history_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    statements: tuple[SummaryStatement, ...] = Field(min_length=1)
    text: NonEmptyStr

    @field_validator("covered_history_ids")
    @classmethod
    def unique_history_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("summary history IDs must be unique")
        return value


class SummaryRequest(ContractModel):
    history: tuple[HistoryRecord, ...]
    current_state: tuple[StateEntry, ...]
    instruction: Literal[
        "Select current state statements without changing values or epistemic status. "
        "The returned text must be the canonical rendering of those statements."
    ] = (
        "Select current state statements without changing values or epistemic status. "
        "The returned text must be the canonical rendering of those statements."
    )


class StateChecklist(ContractModel):
    categories: dict[str, tuple[StateEntry, ...]]

    def entries(self, category: StateCategory) -> tuple[StateEntry, ...]:
        return self.categories[category]


class ContextProjection(ContractModel):
    messages: list[dict[str, JsonValue]]
    sources: list[SourceRef]
    checklist: StateChecklist
    decision_event_ids: tuple[NonEmptyStr, ...] = ()
    included_history_ids: tuple[NonEmptyStr, ...] = ()
    omitted_history_ids: tuple[NonEmptyStr, ...] = ()


SummaryCallback = Callable[
    [SummaryRequest], SummaryCandidate | Awaitable[SummaryCandidate]
]


@dataclass(frozen=True)
class _ProjectedRecord:
    record: HistoryRecord
    message: dict


class ContextManager:
    """Maintain lossless history and make an audited, bounded request view."""

    schema_version = "agent-runtime.context.v1"

    def __init__(
        self,
        store: EventStore,
        *,
        policy: ContextPolicy | None = None,
        summary_callback: SummaryCallback | None = None,
    ) -> None:
        self.store = store
        self.policy = policy or ContextPolicy()
        self.summary_callback = summary_callback
        self._history: list[HistoryRecord] = []
        self._state: dict[str, StateEntry] = {}
        self._images: dict[str, ImageRecord] = {}
        self._retrieval_pins: set[str] = set()
        self._compaction_signatures: set[str] = set()
        self._next_history = 0

    @property
    def history(self) -> tuple[HistoryRecord, ...]:
        return tuple(self._history)

    @property
    def state(self) -> tuple[StateEntry, ...]:
        return tuple(self._state[key] for key in sorted(self._state))

    @property
    def images(self) -> tuple[ImageRecord, ...]:
        return tuple(self._images[key] for key in sorted(self._images))

    def ingest(self, messages: list[dict], sources: list[SourceRef]) -> tuple[str, ...]:
        if len(messages) != len(sources):
            raise ValueError("every ingested message needs one source")
        return tuple(self.append(message, source) for message, source in zip(messages, sources))

    def append(
        self,
        message: dict,
        source: SourceRef,
        *,
        kind: HistoryKind = "message",
        tags: tuple[str, ...] = (),
        state_updates: tuple[StateEntry, ...] = (),
        summary_slot: str | None = None,
        summary_state_revisions: dict[str, int] | None = None,
        image_keys: tuple[str, ...] = (),
    ) -> str:
        if kind == "message" and message.get("role") == "tool":
            kind = "tool_result"
        resolved_image_keys = list(image_keys)
        for key in resolved_image_keys:
            if key not in self._images:
                raise ValueError(f"message references an unregistered image: {key}")
        registered_hashes = {self._images[key].image.sha256 for key in resolved_image_keys}
        for index, (digest, data, media_type) in enumerate(_embedded_images(message)):
            if digest in registered_hashes:
                continue
            existing = [
                image for image in self._images.values() if image.image.sha256 == digest
            ]
            if existing:
                for image in sorted(existing, key=lambda item: item.registration_index):
                    if image.key not in resolved_image_keys:
                        resolved_image_keys.append(image.key)
            else:
                ref = self.store.put_bytes(data, media_type)
                resolved_image_keys.append(
                    self.register_image(
                        f"{source.source_id}:image-{index}", ref, source=source
                    )
                )
            registered_hashes.add(digest)
        history_id = f"history-{self._next_history:06d}"
        self._next_history += 1
        copied = copy.deepcopy(message)
        record = HistoryRecord(
            history_id=history_id,
            message=copied,
            source=source,
            message_blob=self.store.put_json(copied),
            kind=kind,
            tags=tuple(tags),
            image_keys=tuple(resolved_image_keys),
            summary_slot=summary_slot,
            summary_state_revisions=dict(summary_state_revisions or {}),
            content_sha256=hashlib.sha256(json_bytes(copied)).hexdigest(),
        )
        self._history.append(record)
        for entry in state_updates:
            self.set_state(entry)
        return history_id

    def set_state(self, entry: StateEntry) -> None:
        previous = self._state.get(entry.key)
        if previous is None:
            if entry.revision != 1:
                raise ValueError("a new state entry starts at revision 1")
        elif entry == previous:
            return
        elif entry.revision != previous.revision + 1:
            raise ValueError("a changed state entry must increment revision by exactly one")
        if entry.category in _PROTECTED_CATEGORIES and all(
            self._is_summary_source(ref) for ref in entry.source_refs
        ):
            raise ValueError(
                "dimensions, object IDs, geometry and artifact versions cannot exist only in a summary"
            )
        self._state[entry.key] = entry

    def _is_summary_source(self, ref: SourceRef) -> bool:
        """Recognize summary provenance by ledger/blob identity, not a label."""

        if ref.source_kind == "generated" and ref.source_id.startswith("context-summary"):
            return True
        blob_sha = ref.blob.sha256 if isinstance(ref.blob, HashedBlobRef) else None
        for event in self.store.events:
            payload = event.payload
            if payload.event_type != "context" or payload.action != "compact":
                continue
            if ref.event_id == event.event_id:
                return True
            if blob_sha is not None and any(
                isinstance(candidate, HashedBlobRef) and candidate.sha256 == blob_sha
                for candidate in (payload.summary, payload.details)
            ):
                return True
            if ref.event_id is None or payload.details is None:
                continue
            try:
                details = json.loads(self.store.get_bytes(payload.details))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if (
                details.get("kind") == "validated_model_summary"
                and details.get("response_event_id") == ref.event_id
            ):
                return True
        return False

    def register_image(
        self,
        view_id: str,
        image: HashedBlobRef,
        *,
        source: SourceRef,
        tags: tuple[str, ...] = (),
    ) -> str:
        # Verifies URI confinement, bytes and digest before accepting identity.
        self.store.get_bytes(image)
        key = self.image_key(view_id, image.sha256)
        candidate = ImageRecord(
            key=key, view_id=view_id, image=image, source=source, tags=tuple(tags),
            registration_index=len(self._images),
        )
        previous = self._images.get(key)
        if previous is not None:
            # The first registration is the provenance authority.  Replaying a
            # tool result or seeing the same bytes again is idempotent and must
            # not replace its source, tags, or registration order.
            return key
        self._images[key] = candidate
        return key

    @staticmethod
    def image_key(view_id: str, sha256: str) -> str:
        if not view_id.strip() or len(sha256) != 64:
            raise ValueError("image identity needs a view_id and SHA-256")
        return f"{view_id}@sha256:{sha256}"

    def retrieve_image(self, view_id: str, sha256: str) -> bytes:
        key = self.image_key(view_id, sha256)
        try:
            record = self._images[key]
        except KeyError as error:
            raise KeyError(f"unknown image identity: {key}") from error
        if record.view_id != view_id or record.image.sha256 != sha256:
            raise ValueError("image identity mismatch")
        data = self.store.get_bytes(record.image)
        if record.active:
            before = self._projection_snapshot()
            details = self.store.put_json(
                {"decision": "retrieve", "view_id": view_id, "sha256": sha256,
                 "already_active": True}
            )
            event = self.store.append(
                self._context_payload(
                    action="retain_image",
                    reason="explicit exact image retrieval; image already active",
                    image=record.image,
                    view_id=view_id,
                    before=before,
                    after=before,
                    details=details,
                ),
                source_refs=(record.source, self._blob_source("context-image-retrieve", details)),
            )
        else:
            if record.removal_event_id is None:
                raise ValueError("removed image lacks its removal event")
            before = self._projection_snapshot()
            details = self.store.put_json(
                {"decision": "retrieve", "view_id": view_id, "sha256": sha256}
            )
            after = self.store.put_json(
                {"active_images": sorted([*self._active_image_keys(), key])}
            )
            event = self.store.append(
                self._context_payload(
                    action="retrieve_image",
                    reason="explicit exact image retrieval",
                    image=record.image,
                    removal_event_id=record.removal_event_id,
                    view_id=view_id,
                    before=before,
                    after=after,
                    details=details,
                ),
                source_refs=(record.source, self._blob_source("context-image-retrieve", details)),
            )
            self._images[key] = record.model_copy(
                update={"active": True, "removal_event_id": None}
            )
        if event.payload.image.sha256 != hashlib.sha256(data).hexdigest():
            raise ValueError("retrieved image bytes differ from the recorded image")
        # An explicit retrieval is a one-request exact pin.  It survives a
        # checkpoint and is consumed only after a valid projection is built.
        self._retrieval_pins.add(key)
        return data

    def checklist(self) -> StateChecklist:
        active = [entry for entry in self.state if entry.active]
        return StateChecklist(
            categories={
                category: tuple(entry for entry in active if entry.category == category)
                for category in _CHECKLIST_CATEGORIES
            }
        )

    def full_history(self) -> tuple[list[dict], list[SourceRef]]:
        """Return exact original messages and their original event/source chain."""

        return (
            [copy.deepcopy(record.message) for record in self._history],
            [record.source for record in self._history],
        )

    restore_history = full_history

    def replay_events(self, events: list[EventEnvelope] | tuple[EventEnvelope, ...]) -> int:
        """Apply context events written after the loaded checkpoint.

        The runtime should first replay durable tool executions and its generic
        state importer, so every referenced image and current-state item exists.
        This method is idempotent for image decisions and skips summaries whose
        context event is already represented in history.
        """

        applied = 0
        represented_events = {
            record.source.event_id for record in self._history if record.source.event_id
        }
        for event in events:
            payload = event.payload
            if payload.event_type != "context":
                continue
            if payload.action in {"retain_image", "remove_image", "retrieve_image"}:
                if not isinstance(payload.image, HashedBlobRef) or payload.view_id is None:
                    raise ValueError("replayed image decision needs hashed image and view_id")
                key = self.image_key(payload.view_id, payload.image.sha256)
                record = self._images.get(key)
                if record is None:
                    raise ValueError(
                        "replay tool results/register_image before context image decisions"
                    )
                if payload.action == "remove_image":
                    self._images[key] = record.model_copy(
                        update={"active": False, "removal_event_id": event.event_id}
                    )
                elif payload.action == "retain_image":
                    self._images[key] = record.model_copy(
                        update={"active": True, "removal_event_id": None}
                    )
                else:
                    if record.removal_event_id not in {None, payload.removal_event_id}:
                        raise ValueError("replayed retrieval does not match current removal")
                    self.store.get_bytes(record.image)
                    self._images[key] = record.model_copy(
                        update={"active": True, "removal_event_id": None}
                    )
                if payload.details is not None:
                    replay_details = json.loads(self.store.get_bytes(payload.details))
                    if replay_details.get("decision") == "retrieve":
                        self._retrieval_pins.add(key)
                applied += 1
                continue
            if payload.action != "compact" or payload.details is None:
                continue
            details = json.loads(self.store.get_bytes(payload.details))
            if details.get("kind") != "validated_model_summary" or event.event_id in represented_events:
                continue
            candidate = SummaryCandidate.model_validate_json(
                json.dumps(details["candidate"])
            )
            if not isinstance(payload.summary, HashedBlobRef):
                raise ValueError("replayed model summary needs a hashed attachment")
            revisions: dict[str, int] = {}
            for statement in candidate.statements:
                current = self._state.get(statement.state_key)
                exact = current is not None and (
                    current.active
                    and current.value == statement.value
                    and current.epistemic_status == statement.epistemic_status
                    and current.source_refs == statement.source_refs
                )
                revisions[statement.state_key] = (
                    current.revision if exact else (current.revision + 1 if current else 1)
                )
            source = SourceRef(
                source_id=f"context-summary-{event.event_id}",
                source_kind="generated",
                locator=payload.summary.uri,
                blob=payload.summary,
                event_id=event.event_id,
            )
            self.append(
                {"role": "system", "content": candidate.text},
                source,
                kind="summary",
                summary_slot="model-summary",
                summary_state_revisions=revisions,
            )
            represented_events.add(event.event_id)
            applied += 1
        return applied

    def build_summary_request(self, history_ids: tuple[str, ...]) -> SummaryRequest:
        selected = self._records(history_ids)
        return SummaryRequest(history=selected, current_state=tuple(
            entry for entry in self.state if entry.active
        ))

    @staticmethod
    def render_summary(statements: tuple[SummaryStatement, ...]) -> str:
        values = [statement.model_dump(mode="json") for statement in statements]
        return json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def validate_summary(self, candidate: SummaryCandidate) -> SummaryCandidate:
        self._records(candidate.covered_history_ids)
        seen: set[str] = set()
        for statement in candidate.statements:
            if statement.state_key in seen:
                raise ValueError("summary cannot repeat a state key")
            seen.add(statement.state_key)
            current = self._state.get(statement.state_key)
            if current is None or not current.active:
                raise ValueError("summary statement does not reference active current state")
            if (
                statement.value != current.value
                or statement.epistemic_status != current.epistemic_status
                or statement.source_refs != current.source_refs
            ):
                raise ValueError(
                    "summary cannot change a value, its epistemic status, or its evidence"
                )
        if candidate.text != self.render_summary(candidate.statements):
            raise ValueError("summary text must be the canonical rendering of validated state")
        return candidate

    async def summarize(self, history_ids: tuple[str, ...]) -> SummaryCandidate:
        if self.summary_callback is None:
            raise ValueError("no audited summary callback was configured")
        result = self.summary_callback(self.build_summary_request(history_ids))
        candidate = await result if inspect.isawaitable(result) else result
        if not isinstance(candidate, SummaryCandidate):
            candidate = SummaryCandidate.model_validate(candidate)
        return self.validate_summary(candidate)

    def compact_with_summary(
        self,
        candidate: SummaryCandidate,
        *,
        summary_slot: str = "model-summary",
        source: SourceRef | None = None,
    ) -> str:
        candidate = self.validate_summary(candidate)
        records = self._records(candidate.covered_history_ids)
        event_ids = self._event_ids(records)
        if not event_ids:
            raise ValueError("context compaction needs prior recorded event references")
        summary_ref = self.store.put_json(candidate.model_dump(mode="json"))
        details = self.store.put_json(
            {"kind": "validated_model_summary",
             "candidate": candidate.model_dump(mode="json"),
             "response_event_id": source.event_id if source else None}
        )
        before = self._projection_snapshot()
        event = self.store.append(
            self._context_payload(
                action="compact",
                reason="validated model summary requested by the runtime",
                summary=summary_ref,
                replaced_event_ids=event_ids,
                before=before,
                after=self.store.put_json({"summary": summary_ref.model_dump(mode="json")}),
                details=details,
            ),
            source_refs=tuple([
                *(r.source for r in records),
                *((source,) if source else ()),
                self._blob_source("context-summary-details", details),
            ]),
        )
        source = SourceRef(
            source_id=f"context-summary-{event.event_id}",
            source_kind="generated",
            locator=summary_ref.uri,
            blob=summary_ref,
            event_id=event.event_id,
        )
        return self.append(
            {"role": "system", "content": candidate.text},
            source,
            kind="summary",
            summary_slot=summary_slot,
            summary_state_revisions={
                statement.state_key: self._state[statement.state_key].revision
                for statement in candidate.statements
            },
        )

    def project(
        self,
        *,
        required_tags: tuple[str, ...] = (),
        required_view_ids: tuple[str, ...] = (),
        consume_retrievals: bool = True,
    ) -> ContextProjection:
        required = set(required_tags) | set(self.policy.pinned_tags)
        exact_retrievals = set(self._retrieval_pins)
        selected, omitted = self._select_history(
            required, set(required_view_ids), exact_retrievals
        )
        image_decisions = self._decide_images(
            selected, required, set(required_view_ids), exact_retrievals
        )
        decision_event_ids = list(self._record_image_decisions(image_decisions))

        newest_large_result: dict[str, str] = {}
        for record in selected:
            if record.kind == "tool_result" and _message_content_size(record.message) >= self.policy.large_result_bytes:
                newest_large_result[_message_content_sha(record.message)] = record.history_id
        referenced_results = [
            record
            for record in selected
            if record.kind == "tool_result"
            and _message_content_size(record.message) >= self.policy.large_result_bytes
            and newest_large_result[_message_content_sha(record.message)] != record.history_id
        ]
        if referenced_results:
            event = self._record_result_reference_compaction(
                referenced_results, newest_large_result
            )
            decision_event_ids.append(event.event_id)

        projected: list[_ProjectedRecord] = []
        last_image_occurrence: dict[str, str] = {}
        for record in selected:
            for key in record.image_keys:
                image = self._images[key]
                if image.active:
                    last_image_occurrence[image.image.sha256] = record.history_id
        sent_image_hashes: set[str] = set()
        for record in selected:
            projected.append(
                _ProjectedRecord(
                    record,
                    self._project_message(
                        record,
                        newest_large_result,
                        last_image_occurrence,
                        sent_image_hashes,
                    ),
                )
            )

        compacted = [r for r in omitted if r.source.event_id is not None]
        if compacted:
            event, compact_message, compact_source = self._record_deterministic_compaction(compacted)
            if event is not None:
                decision_event_ids.append(event.event_id)
                synthetic = HistoryRecord(
                    history_id=f"projection-{event.event_id}",
                    message=compact_message,
                    source=compact_source,
                    message_blob=self.store.put_json(compact_message),
                    kind="summary",
                    summary_slot="deterministic-compaction",
                    content_sha256=hashlib.sha256(json_bytes(compact_message)).hexdigest(),
                )
                # Appending at a group boundary cannot split assistant tool_calls
                # from any of their tool replies.
                projected.append(_ProjectedRecord(synthetic, compact_message))

        checklist = self.checklist()
        if any(checklist.categories.values()):
            state_message = {
                "role": "user",
                "content": "Current runtime state (machine generated; epistemic status is authoritative): "
                + json.dumps(
                    [entry.model_dump(mode="json") for entry in self.state if entry.active],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
            state_ref = self.store.put_json(state_message)
            state_source = SourceRef(
                source_id="context-current-state",
                source_kind="generated",
                locator=state_ref.uri,
                blob=state_ref,
            )
            synthetic = HistoryRecord(
                history_id="projection-current-state",
                message=state_message,
                source=state_source,
                message_blob=state_ref,
                content_sha256=hashlib.sha256(json_bytes(state_message)).hexdigest(),
            )
            projected.append(_ProjectedRecord(synthetic, state_message))

        messages = [item.message for item in projected]
        _validate_projected_tool_protocol(tuple(messages))
        if consume_retrievals:
            self._retrieval_pins.difference_update(exact_retrievals)
        return ContextProjection(
            messages=messages,
            sources=[item.record.source for item in projected],
            checklist=checklist,
            decision_event_ids=tuple(decision_event_ids),
            included_history_ids=tuple(r.history_id for r in selected),
            omitted_history_ids=tuple(r.history_id for r in omitted),
        )

    def acknowledge_projection(self) -> tuple[str, ...]:
        """Consume exact-retrieval pins after the primary response is accepted."""

        consumed = tuple(sorted(self._retrieval_pins))
        self._retrieval_pins.clear()
        return consumed

    def dump(self) -> dict:
        history = []
        for record in self._history:
            item = record.model_dump(mode="json")
            # Checkpoints retain only a content-addressed pointer; this avoids
            # rewriting the full conversation and base64 images each turn.
            item.pop("message")
            history.append(item)
        return {
            "schema_version": self.schema_version,
            "policy": self.policy.model_dump(mode="json"),
            "history": history,
            "state": [entry.model_dump(mode="json") for entry in self.state],
            "images": [record.model_dump(mode="json") for record in self.images],
            "retrieval_pins": sorted(self._retrieval_pins),
            "compaction_signatures": sorted(self._compaction_signatures),
            "next_history": self._next_history,
        }

    @classmethod
    def load(
        cls,
        store: EventStore,
        payload: dict,
        *,
        policy: ContextPolicy | None = None,
        summary_callback: SummaryCallback | None = None,
    ) -> "ContextManager":
        if payload.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported context checkpoint schema")
        saved_policy = ContextPolicy.model_validate_json(json.dumps(payload["policy"]))
        if policy is not None and policy != saved_policy:
            raise ValueError("context policy cannot change while restoring a checkpoint")
        manager = cls(store, policy=saved_policy, summary_callback=summary_callback)
        history = []
        for item in payload["history"]:
            ref = HashedBlobRef.model_validate_json(json.dumps(item["message_blob"]))
            message = json.loads(store.get_bytes(ref))
            history.append(HistoryRecord.model_validate_json(
                json.dumps({**item, "message": message})
            ))
        manager._history = history
        manager._state = {
            entry.key: entry for entry in (
                StateEntry.model_validate_json(json.dumps(item)) for item in payload["state"]
            )
        }
        manager._images = {
            image.key: image for image in (
                ImageRecord.model_validate_json(json.dumps(item)) for item in payload["images"]
            )
        }
        manager._compaction_signatures = set(payload.get("compaction_signatures", ()))
        manager._retrieval_pins = set(payload.get("retrieval_pins", ()))
        manager._next_history = payload["next_history"]
        if manager._next_history < len(manager._history):
            raise ValueError("context checkpoint history counter moved backwards")
        if len(manager._state) != len(payload["state"]) or len(manager._images) != len(payload["images"]):
            raise ValueError("context checkpoint contains duplicate identities")
        history_ids = [record.history_id for record in manager._history]
        if len(history_ids) != len(set(history_ids)):
            raise ValueError("context checkpoint contains duplicate history IDs")
        for record in manager._history:
            if (
                hashlib.sha256(json_bytes(record.message)).hexdigest() != record.content_sha256
                or record.message_blob.sha256 != record.content_sha256
            ):
                raise ValueError("context history message hash mismatch")
            if any(key not in manager._images for key in record.image_keys):
                raise ValueError("context history references a missing image")
        for image in manager._images.values():
            store.get_bytes(image.image)
            if image.active and image.removal_event_id is not None:
                raise ValueError("active checkpoint image cannot retain a removal event")
            if not image.active:
                if image.removal_event_id is None:
                    raise ValueError("removed checkpoint image lacks a removal event")
                matching = [event for event in store.events if event.event_id == image.removal_event_id]
                if (
                    len(matching) != 1
                    or matching[0].payload.event_type != "context"
                    or matching[0].payload.action != "remove_image"
                    or matching[0].payload.image != image.image
                ):
                    raise ValueError("checkpoint image removal reference is invalid")
        if not manager._retrieval_pins <= set(manager._images):
            raise ValueError("context checkpoint has retrieval pins for unknown images")
        return manager

    def _select_history(
        self,
        required_tags: set[str],
        required_view_ids: set[str],
        required_image_keys: set[str],
    ) -> tuple[list[HistoryRecord], list[HistoryRecord]]:
        keep: set[str] = {r.history_id for r in self._history[: self.policy.preserve_initial_messages]}
        keep.update(r.history_id for r in self._history[-self.policy.active_window_messages :])
        keep.update(r.history_id for r in self._history if required_tags & set(r.tags))
        keep.update(
            r.history_id
            for r in self._history
            if any(
                required_tags & set(self._images[key].tags)
                or self._images[key].view_id in required_view_ids
                or key in required_image_keys
                for key in r.image_keys
            )
        )

        # If any member is selected, expand to the whole assistant/tool/image
        # interaction group before removing obsolete standalone summaries.
        for group in _interaction_groups(self._history):
            if keep & {record.history_id for record in group}:
                keep.update(record.history_id for record in group)

        # Only the newest summary in a slot is useful in the request projection.
        newest_summary: dict[str, str] = {}
        for record in self._history:
            if record.summary_slot:
                newest_summary[record.summary_slot] = record.history_id
        for record in self._history:
            if record.summary_slot and newest_summary[record.summary_slot] != record.history_id:
                keep.discard(record.history_id)
            elif record.summary_state_revisions and any(
                key not in self._state
                or not self._state[key].active
                or self._state[key].revision != revision
                for key, revision in record.summary_state_revisions.items()
            ):
                keep.discard(record.history_id)

        selected = [r for r in self._history if r.history_id in keep]
        omitted = [r for r in self._history if r.history_id not in keep]
        return selected, omitted

    def _decide_images(
        self,
        selected: list[HistoryRecord],
        required_tags: set[str],
        required_view_ids: set[str],
        required_image_keys: set[str],
    ) -> dict[str, tuple[bool, str]]:
        selected_keys = {key for record in selected for key in record.image_keys}
        provisional: dict[str, tuple[bool, str]] = {}
        for key, image in self._images.items():
            keep = key in selected_keys and (
                key in required_image_keys
                or
                image.view_id in required_view_ids
                or bool(required_tags & set(image.tags))
                or key in {k for record in selected[-self.policy.active_window_messages :] for k in record.image_keys}
            )
            reason = (
                "explicit exact retrieval"
                if key in required_image_keys
                else "required view_id"
                if image.view_id in required_view_ids
                else "configured pinned tag"
                if required_tags & set(image.tags)
                else "active window"
                if keep
                else "outside the active request policy"
            )
            provisional[key] = (keep, reason)

        # One view_id may have multiple byte versions.  A request that names
        # only the view gets its newest registered version; exact recovery uses
        # retrieve_image(view_id, sha256).
        by_view: dict[str, list[str]] = {}
        for key, (keep, _) in provisional.items():
            if keep:
                by_view.setdefault(self._images[key].view_id, []).append(key)
        for keys in by_view.values():
            if len(keys) <= 1:
                continue
            winner = max(keys, key=lambda key: self._images[key].registration_index)
            pinned = [key for key in keys if key in required_image_keys]
            if pinned:
                winner = max(pinned, key=lambda key: self._images[key].registration_index)
            for key in keys:
                if key != winner:
                    provisional[key] = (False, f"older view version replaced by {winner}")

        # Duplicate bytes are sent once. Required view IDs win, then lexical key.
        by_hash: dict[str, list[str]] = {}
        for key, (keep, _) in provisional.items():
            if keep:
                by_hash.setdefault(self._images[key].image.sha256, []).append(key)
        for keys in by_hash.values():
            if len(keys) <= 1:
                continue
            winner = max(
                keys,
                key=lambda key: (
                    key in required_image_keys,
                    self._images[key].view_id in required_view_ids,
                    self._images[key].registration_index,
                ),
            )
            for key in keys:
                if key != winner:
                    provisional[key] = (False, f"duplicate image bytes retained as {winner}")
        kept = [key for key, (keep, _) in provisional.items() if keep]
        kept.sort(
            key=lambda key: (
                key in required_image_keys,
                self._images[key].view_id in required_view_ids,
                bool(required_tags & set(self._images[key].tags)),
                self._images[key].registration_index,
            ),
            reverse=True,
        )
        used_bytes = 0
        for index, key in enumerate(kept):
            size = len(self.store.get_bytes(self._images[key].image))
            exceeds_count = self.policy.max_images is not None and index >= self.policy.max_images
            exceeds_bytes = (
                self.policy.max_image_bytes is not None
                and used_bytes + size > self.policy.max_image_bytes
            )
            if exceeds_count or exceeds_bytes:
                if (
                    key in required_image_keys
                    or self._images[key].view_id in required_view_ids
                    or bool(required_tags & set(self._images[key].tags))
                ):
                    raise ValueError(
                        "required image exceeds the configured request image limits"
                    )
                provisional[key] = (
                    False,
                    "request image count limit" if exceeds_count else "request image byte limit",
                )
            else:
                used_bytes += size
        return provisional

    def _record_image_decisions(self, decisions: dict[str, tuple[bool, str]]) -> tuple[str, ...]:
        event_ids: list[str] = []
        for key in sorted(decisions):
            keep, reason = decisions[key]
            record = self._images[key]
            before = self._projection_snapshot()
            details = self.store.put_json(
                {"decision": "retain" if keep else "remove", "key": key,
                 "view_id": record.view_id, "sha256": record.image.sha256, "reason": reason}
            )
            after_active = self._active_image_keys()
            if keep:
                after_active.add(key)
                if record.active:
                    action = "retain_image"
                    fields = {}
                else:
                    if record.removal_event_id is None:
                        raise ValueError("removed image lacks its removal event")
                    self.store.get_bytes(record.image)
                    action = "retrieve_image"
                    fields = {"removal_event_id": record.removal_event_id}
            else:
                after_active.discard(key)
                action = "remove_image"
                fields = {}
            after = self.store.put_json({"active_images": sorted(after_active)})
            event = self.store.append(
                self._context_payload(
                    action=action,
                    reason=reason,
                    image=record.image,
                    view_id=record.view_id,
                    before=before,
                    after=after,
                    details=details,
                    **fields,
                ),
                source_refs=(record.source, self._blob_source("context-image-decision", details)),
            )
            event_ids.append(event.event_id)
            self._images[key] = record.model_copy(
                update={
                    "active": keep,
                    "removal_event_id": None if keep else event.event_id,
                }
            )
        return tuple(event_ids)

    def _record_deterministic_compaction(self, records: list[HistoryRecord]):
        event_ids = self._event_ids(tuple(records))
        if not event_ids:
            return None, None, None
        description = {
            "kind": "deterministic_compaction",
            "records": [
                {"history_id": r.history_id, "sha256": r.content_sha256, "kind": r.kind}
                for r in records
            ],
            "current_state_keys": [entry.key for entry in self.state if entry.active],
            "note": "Full messages remain in the context checkpoint and event attachments.",
        }
        signature = hashlib.sha256(json_bytes(description)).hexdigest()
        summary = self.store.put_json(description)
        details = self.store.put_json(
            {"strategy": "exact duplicate/old summary/activity window", **description}
        )
        before = self._projection_snapshot()
        compact_message = {
            "role": "system",
            "content": "Deterministic context compaction: "
            + json.dumps(description, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        }
        after = self.store.put_json(compact_message)
        event = self.store.append(
            self._context_payload(
                action="compact",
                reason="deterministic projection removed repeated or inactive history",
                summary=summary,
                replaced_event_ids=event_ids,
                before=before,
                after=after,
                details=details,
            ),
            source_refs=tuple([*(r.source for r in records), self._blob_source("context-compaction-details", details)]),
        )
        self._compaction_signatures.add(signature)
        source = SourceRef(
            source_id=f"context-compaction-{event.event_id}",
            source_kind="generated",
            locator=summary.uri,
            blob=summary,
            event_id=event.event_id,
        )
        return event, compact_message, source

    def _project_message(
        self,
        record: HistoryRecord,
        newest_large_result: dict[str, str],
        last_image_occurrence: dict[str, str],
        sent_image_hashes: set[str],
    ) -> dict:
        result = copy.deepcopy(record.message)
        if record.kind == "tool_result" and _message_content_size(result) >= self.policy.large_result_bytes:
            content_sha = _message_content_sha(result)
            full_record = newest_large_result.get(content_sha)
            if full_record is not None and full_record != record.history_id:
                result["content"] = json.dumps(
                    {
                        "context_reference": {
                            "content_sha256": content_sha,
                            "full_result_history_id": full_record,
                            "reason": "exact repeated large tool result",
                        }
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
        content = result.get("content")
        if not isinstance(content, list):
            return result
        blocks = []
        for block in content:
            sha = _image_block_hash(block)
            if sha is None:
                blocks.append(block)
                continue
            matches = [
                self._images[key]
                for key in record.image_keys
                if self._images[key].image.sha256 == sha
            ]
            active = [image for image in matches if image.active]
            if (
                active
                and last_image_occurrence.get(sha) == record.history_id
                and sha not in sent_image_hashes
            ):
                blocks.append(block)
                sent_image_hashes.add(sha)
            else:
                identities = ",".join(sorted(image.key for image in matches))
                reason = (
                    "duplicate bytes already retained elsewhere in this request"
                    if active
                    else "outside active context"
                )
                blocks.append({
                    "type": "text",
                    "text": f"Image bytes omitted ({reason}); retrieve exact identity: {identities}",
                })
        result["content"] = blocks
        return result

    def _record_result_reference_compaction(
        self,
        records: list[HistoryRecord],
        newest_large_result: dict[str, str],
    ):
        replacements = [
            {
                "history_id": record.history_id,
                "event_id": record.source.event_id,
                "content_sha256": _message_content_sha(record.message),
                "full_result_history_id": newest_large_result[_message_content_sha(record.message)],
            }
            for record in records
        ]
        event_ids = self._event_ids(records)
        if not event_ids:
            raise ValueError("large-result compaction needs prior recorded event references")
        summary = self.store.put_json({"kind": "large_result_references", "replacements": replacements})
        details = self.store.put_json(
            {"strategy": "exact content hash; preserve tool envelopes", "replacements": replacements}
        )
        return self.store.append(
            self._context_payload(
                action="compact",
                reason="exact repeated large tool results replaced by hash references",
                summary=summary,
                replaced_event_ids=event_ids,
                before=self._projection_snapshot(),
                after=summary,
                details=details,
            ),
            source_refs=tuple(
                [*(record.source for record in records), self._blob_source("context-result-reference", details)]
            ),
        )

    def _records(self, history_ids: tuple[str, ...]) -> tuple[HistoryRecord, ...]:
        by_id = {record.history_id: record for record in self._history}
        try:
            return tuple(by_id[history_id] for history_id in history_ids)
        except KeyError as error:
            raise ValueError(f"unknown history ID: {error.args[0]}") from error

    @staticmethod
    def _event_ids(records: tuple[HistoryRecord, ...] | list[HistoryRecord]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(r.source.event_id for r in records if r.source.event_id))

    def _active_image_keys(self) -> set[str]:
        return {key for key, image in self._images.items() if image.active}

    def _projection_snapshot(self) -> HashedBlobRef:
        return self.store.put_json(
            {"history_ids": [record.history_id for record in self._history],
             "active_images": sorted(self._active_image_keys()),
             "state_revisions": {key: entry.revision for key, entry in sorted(self._state.items())}}
        )

    def _blob_source(self, source_id: str, blob: HashedBlobRef) -> SourceRef:
        return SourceRef(
            source_id=f"{source_id}-{blob.sha256[:12]}",
            source_kind="generated",
            locator=blob.uri,
            blob=blob,
        )

    @staticmethod
    def _context_payload(**values) -> ContextEventPayload:
        # Stage 2 adds audit detail fields while retaining stage-0 compatibility.
        supported = ContextEventPayload.model_fields
        filtered = {key: value for key, value in values.items() if key in supported}
        if values.get("action") == "retain_image" and "retain_image" not in _context_actions():
            raise RuntimeError("ContextEventPayload must support retain_image before projection")
        return ContextEventPayload(**filtered)


def _context_actions() -> set[str]:
    annotation = ContextEventPayload.model_fields["action"].annotation
    return set(getattr(annotation, "__args__", ()))


def _embedded_images(message: dict) -> tuple[tuple[str, bytes, str], ...]:
    content = message.get("content")
    if not isinstance(content, list):
        return ()
    images = []
    for block in content:
        parsed = _image_block_data(block)
        if parsed is not None:
            images.append(parsed)
    return tuple(images)


def _image_block_hash(block) -> str | None:
    parsed = _image_block_data(block)
    return parsed[0] if parsed else None


def _image_block_data(block) -> tuple[str, bytes, str] | None:
    if not isinstance(block, dict) or block.get("type") != "image_url":
        return None
    image = block.get("image_url")
    url = image.get("url") if isinstance(image, dict) else None
    if not isinstance(url, str) or not url.startswith("data:image/") or ";base64," not in url:
        raise ValueError("context images must be captured data URLs")
    _, encoded = url.split(",", 1)
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError as error:
        raise ValueError("invalid image data URL") from error
    media_type = url[5:].split(";", 1)[0]
    return hashlib.sha256(data).hexdigest(), data, media_type


def _message_content_sha(message: dict) -> str:
    return hashlib.sha256(json_bytes(message.get("content"))).hexdigest()


def _message_content_size(message: dict) -> int:
    return len(json_bytes(message.get("content")))


def _has_tool_images(message: dict) -> bool:
    content = message.get("content")
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "image_url" for block in content
    )


def _tool_call_ids(message: dict) -> tuple[str, ...]:
    calls = message.get("tool_calls")
    if message.get("role") != "assistant" or not isinstance(calls, list) or not calls:
        return ()
    ids = tuple(call.get("id") for call in calls if isinstance(call, dict))
    if len(ids) != len(calls) or any(not isinstance(call_id, str) or not call_id for call_id in ids):
        raise ValueError("assistant tool_calls need nonempty string IDs")
    if len(ids) != len(set(ids)):
        raise ValueError("assistant tool_call IDs must be unique")
    return ids


def _interaction_groups(records: list[HistoryRecord]) -> tuple[tuple[HistoryRecord, ...], ...]:
    """Group protocol-atomic assistant/tool/image exchanges."""

    groups: list[tuple[HistoryRecord, ...]] = []
    index = 0
    while index < len(records):
        start = records[index]
        call_ids = _tool_call_ids(start.message)
        if not call_ids:
            groups.append((start,))
            index += 1
            continue
        group = [start]
        index += 1
        while index < len(records) and records[index].message.get("role") == "tool":
            group.append(records[index])
            index += 1
        while index < len(records) and records[index].message.get("role") == "user" and _has_tool_images(records[index].message):
            group.append(records[index])
            index += 1
        groups.append(tuple(group))
    return tuple(groups)


def _validate_projected_tool_protocol(messages: tuple[dict[str, JsonValue], ...]) -> None:
    pending: set[str] | None = None
    seen: set[str] = set()
    for message in messages:
        role = message.get("role")
        calls = _tool_call_ids(message)
        if calls:
            if pending:
                raise ValueError("a new assistant tool batch started before all replies")
            pending = set(calls)
            seen = set()
            continue
        if role == "tool":
            if pending is None:
                raise ValueError("projected context contains an orphan tool reply")
            call_id = message.get("tool_call_id")
            if call_id not in pending or call_id in seen:
                raise ValueError("projected tool reply has an unknown or duplicate call ID")
            seen.add(call_id)
            if seen == pending:
                pending = None
            continue
        if pending is not None:
            raise ValueError("projected context split an assistant tool batch")
    if pending is not None:
        raise ValueError("projected context ended before all tool replies")
