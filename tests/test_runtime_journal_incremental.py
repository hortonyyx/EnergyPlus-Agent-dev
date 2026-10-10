"""Offline parity, safety, and bounded-cost checks for the journal indices."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from src.agent_runtime.store import EventStore
from src.harness_contracts import (BudgetAmounts, BudgetEventPayload, BudgetLedger,
    BudgetReservation, BudgetSettlement, CostUnavailable, KnownParentTask,
    RunLifecyclePayload, UsageReported, AnswerRepairPayload, InlineCapture,
    ToolInvocationPayload, ToolExecutionPayload, TruncationPayload)
from src.harness_contracts.incremental import EventValidationIndex
from test_harness_core_contracts import _event, make_valid_event_log, make_valid_request_payload


def _index(limit=BudgetAmounts(tokens=1000, calls=10)):
    return EventValidationIndex(run_id="run-1", root_task_id="task-main", budget_limit=limit)


def _accept(index, event):
    update = index.prepare(event)
    index.commit(event, update)


def _full(events, limit=BudgetAmounts(tokens=1000, calls=10)):
    store = object.__new__(EventStore)
    store.root_task_id = "task-main"
    store.budget_limit = limit
    return store._validate_events(list(events))


def test_reference_recovery_log_every_prefix_matches_complete_validation():
    events = make_valid_event_log().events
    index = _index()
    for count, event in enumerate(events, 1):
        full = _full(events[:count])
        _accept(index, event)
        assert tuple(index.events_by_id.values()) == full.events


def _reservation(identifier, tokens, task="task-main"):
    return BudgetReservation(reservation_id=identifier, purpose="primary_task",
                             task_id=task, amounts=BudgetAmounts(tokens=tokens, calls=1))


def _settlement(identifier, tokens, overrun=0):
    return BudgetSettlement(reservation_id=identifier,
        actual=BudgetAmounts(tokens=tokens, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": tokens}),
        cost=CostUnavailable(reason="unpriced offline fixture"), token_overrun=overrun)


def test_budget_totals_and_available_match_complete_ledger_at_every_prefix():
    limit = BudgetAmounts(tokens=100, calls=10)
    events = tuple(_event(n, payload) for n, payload in enumerate((
        BudgetEventPayload(action="reserve", reservation=_reservation("a", 60)),
        BudgetEventPayload(action="reserve", reservation=_reservation("b", 40)),
        BudgetEventPayload(action="settle", settlement=_settlement("a", 20)),
        BudgetEventPayload(action="settle", settlement=_settlement("b", 45, 5)),
        BudgetEventPayload(action="reserve", reservation=_reservation("c", 35)),
    )))
    index = _index(limit)
    for count, event in enumerate(events, 1):
        _full(events[:count], limit)
        _accept(index, event)
        ledger = BudgetLedger(total_limit=limit,
            reservations=tuple(e.payload.reservation for e in events[:count] if e.payload.reservation),
            settlements=tuple(e.payload.settlement for e in events[:count] if e.payload.settlement))
        assert index.budget._amounts() == ledger.committed
        assert index.budget.available == ledger.available


@pytest.mark.parametrize("case", ("overbook", "duplicate_reservation", "duplicate_settlement", "cross_task"))
def test_invalid_budget_prefix_rejection_matches_complete_and_preserves_index(case):
    limit = BudgetAmounts(tokens=100, calls=10)
    reserve = _event(0, BudgetEventPayload(action="reserve", reservation=_reservation("a", 60)))
    settled = _event(1, BudgetEventPayload(action="settle", settlement=_settlement("a", 20)))
    prefix = [reserve]
    if case == "duplicate_settlement":
        prefix.append(settled)
        bad = _event(2, settled.payload)
    elif case == "cross_task":
        bad = _event(1, settled.payload).model_copy(update={"task_id": "child", "parent_task": KnownParentTask(task_id="task-main")})
    else:
        bad = _event(1, BudgetEventPayload(action="reserve", reservation=_reservation("a" if case == "duplicate_reservation" else "b", 60)))
    index = _index(limit)
    for event in prefix:
        _accept(index, event)
    before = (dict(index.events_by_id), dict(index.budget.totals), dict(index.budget.settlements))
    with pytest.raises(ValueError):
        _full([*prefix, bad], limit)
    with pytest.raises(ValueError):
        index.prepare(bad)
    assert (index.events_by_id, index.budget.totals, index.budget.settlements) == before


@pytest.mark.parametrize("case", ("repeat_without_retry", "duplicate_applied_write", "unknown_retry_without_inspection", "cross_task_parent"))
def test_invalid_write_and_ancestry_rejection_matches_complete(case):
    events = list(make_valid_event_log().events)
    if case == "repeat_without_retry":
        prefix, bad = events[:3], _event(3, events[2].payload)
    elif case == "duplicate_applied_write":
        prefix, bad = events[:6], _event(6, events[5].payload)
    elif case == "unknown_retry_without_inspection":
        prefix = events[:3]
        bad = _event(3, events[4].payload.model_copy(update={"state_inspection_event_id": None}))
    else:
        prefix = events[:1]
        bad = _event(1, RunLifecyclePayload(action="start", reason="offline fixture")).model_copy(update={
            "task_id": "child", "parent_task": KnownParentTask(task_id="absent")})
    index = _index()
    for event in prefix:
        _accept(index, event)
    with pytest.raises(ValueError):
        _full([*prefix, bad])
    with pytest.raises(ValueError):
        index.prepare(bad)


@pytest.mark.parametrize("kind", ("invocation", "truncation", "repair"))
def test_duplicate_cross_event_receipts_match_complete_rejection(kind):
    if kind == "invocation":
        call = dict(call_id="read", tool_name="read", full_arguments={}, repeatability="read_only")
        prefix = [_event(0, ToolInvocationPayload(**call))]
        receipt = ToolExecutionPayload(**call, invocation_event_id=prefix[0].event_id,
            outcome="succeeded", raw_result=InlineCapture(value="ok"), shown_result=InlineCapture(value="ok"))
    else:
        prefix = list(make_valid_event_log().events[:2])
        prefix[1] = prefix[1].model_copy(update={"payload": prefix[1].payload.model_copy(update={"tool_calls": ()})})
        if kind == "truncation":
            receipt = TruncationPayload(request_event_id=prefix[0].event_id, response_event_id=prefix[1].event_id,
                thinking_characters=0, visible_characters=0, has_tool_calls=False, consecutive_count=1,
                total_count=1, max_consecutive_recoveries=1, max_total_recoveries=1,
                action="continue", reason="offline length fixture")
        else:
            receipt = AnswerRepairPayload(phase="request", attempt=1, invalid_response_event_id=prefix[1].event_id,
                original_answer=InlineCapture(value="bad"), validation_error="invalid offline answer")
    prefix.append(_event(len(prefix), receipt))
    bad = _event(len(prefix), receipt)
    index = _index()
    for event in prefix:
        _accept(index, event)
    _full(prefix)
    with pytest.raises(ValueError):
        _full([*prefix, bad])
    with pytest.raises(ValueError):
        index.prepare(bad)


def test_store_failed_validation_and_failed_fsync_leave_indices_unmodified(tmp_path, monkeypatch):
    limit = BudgetAmounts(tokens=100, calls=10)
    with EventStore(tmp_path, run_id="run-1", task_id="task-main", budget_limit=limit) as store:
        store.append(BudgetEventPayload(action="reserve", reservation=_reservation("a", 60)))
        child = store.for_task("child", "task-main")
        original = store.path.read_bytes()
        with pytest.raises(ValueError):
            store.append(BudgetEventPayload(action="reserve", reservation=_reservation("b", 60)))
        assert store.path.read_bytes() == original
        assert store.event_revision == store.budget_revision == 1
        assert child.timing_totals == store.timing_totals
        monkeypatch.setattr(os, "fsync", lambda _: (_ for _ in ()).throw(OSError("offline disk failure")))
        with pytest.raises(OSError):
            store.append(RunLifecyclePayload(action="start", reason="offline fixture"))
        assert store.event_revision == 1
        assert list(store._index.events_by_id) == [store.events[0].event_id]
        assert len(store.budget_events()) == len(store.budget_events("task-main")) == 1
        assert store.budget_events("child") == []
        with pytest.raises(ValueError, match="reopen"):
            child.append(RunLifecyclePayload(action="start", reason="offline fixture"))
        assert store.timing_totals["journal_write_seconds"] > 0
        assert store.timing_totals["event_validation_seconds"] > 0


def test_hot_append_does_not_replay_history_and_explicit_validate_does(tmp_path, monkeypatch):
    with EventStore(tmp_path, run_id="run-1", task_id="task-main", budget_limit=BudgetAmounts(tokens=100)) as store:
        full = store._validate_events
        calls = []
        def replay(events):
            calls.append(len(events))
            return full(events)
        monkeypatch.setattr(store, "_validate_events", replay)
        for _ in range(20):
            store.append(RunLifecyclePayload(action="start", reason="offline fixture"))
        assert calls == []
        store.validate()
        assert calls == [20]
    with EventStore(tmp_path, run_id="run-1", task_id="task-main", budget_limit=BudgetAmounts(tokens=100)) as reopened:
        assert reopened.event_revision == 20
        reopened.append(RunLifecyclePayload(action="start", reason="offline fixture"))
        assert reopened.event_revision == 21


def test_budget_projection_revision_invalidates_for_requests_and_responses_across_six_tasks(tmp_path):
    limit = BudgetAmounts(tokens=1000, calls=10)
    with EventStore(tmp_path, run_id="run-1", task_id="task-main", budget_limit=limit) as root:
        root.append(BudgetEventPayload(action="reserve", reservation=_reservation("a", 60)))
        assert root.budget_revision == 1
        children = [root.for_task(f"reader-{n}", "task-main") for n in range(6)]
        response = make_valid_event_log().events[1].payload
        for n, child in enumerate(children):
            req = child.append(make_valid_request_payload())
            assert all(task.budget_revision == 2 + n * 2 for task in children)
            child.append(response.model_copy(update={"request_event_id": req.event_id}))
            assert all(task.budget_revision == 3 + n * 2 for task in children)
            child.append(RunLifecyclePayload(action="start", reason="unrelated to budget"))
            assert root.budget_revision == 3 + n * 2
            assert len(root.budget_projection_events(child.task_id)) == 2
        assert root.event_revision == 19 and root.budget_revision == 13
        assert len(root.budget_events()) == 1
        assert len(root.budget_projection_events()) == 13
        copied = root.budget_projection_events()
        copied.clear()
        assert len(root.budget_projection_events()) == 13
        root.validate()
    with EventStore(tmp_path, run_id="run-1", task_id="task-main", budget_limit=limit) as reopened:
        assert reopened.budget_revision == 13
        assert len(reopened.budget_projection_events("reader-5")) == 2


@pytest.mark.parametrize("tokens", (30, 120))
def test_release_reconcile_prefixes_totals_and_duplicate_rejection_match_full(tmp_path, tokens):
    from src.agent_runtime.budget import RuntimeBudget
    from src.agent_runtime.budget_recovery import reconcile_missing_usage, release_unsent_reservation
    from test_runtime_budget_recovery import open_store, reserve, request, missing, receipt, LIMIT
    with open_store(tmp_path) as store:
        reserve(store, "unsent")
        release_unsent_reservation(store, "unsent", reason="offline abandoned intent")
        reservation = reserve(store)
        req = request(store, reservation)
        old = missing(store, reservation)
        proof = receipt(store, req, old, tokens=tokens)
        event = reconcile_missing_usage(store, proof)
        index = EventValidationIndex(run_id=store.run_id, root_task_id=store.task_id, budget_limit=LIMIT)
        for count, prior in enumerate(store.all_events, 1):
            store._validate_events(store.all_events[:count])
            _accept(index, prior)
            ledger = RuntimeBudget.from_events(LIMIT, store.all_events[:count]).ledger
            assert index.budget._amounts() == ledger.committed
            assert index.budget.available == ledger.available
        original = store.path.read_bytes()
        duplicate = event.model_copy(update={"event_id": "duplicate-receipt", "sequence": event.sequence + 1})
        with pytest.raises(ValueError):
            store._validate_events([*store.all_events, duplicate])
        with pytest.raises(ValueError):
            index.prepare(duplicate)
        with pytest.raises(ValueError):
            store.append(event.payload, source_refs=event.source_refs)
        assert store.path.read_bytes() == original
        assert store.event_revision == len(index.events_by_id)


def test_frozen_1269_events_all_prefixes_match_full_validation():
    source = os.environ.get("RUNTIME_JOURNAL_FROZEN_RUN")
    if not source:
        pytest.skip("set RUNTIME_JOURNAL_FROZEN_RUN to the read-only frozen run")
    directory = Path(source)
    metadata = json.loads((directory / "journal.json").read_bytes())
    limit = BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"]))
    events = EventStore.read_events(directory / "events.jsonl")
    assert len(events) == 1269
    index = EventValidationIndex(run_id=metadata["run_id"], root_task_id=metadata["task_id"], budget_limit=limit)
    full = object.__new__(EventStore)
    full.root_task_id, full.budget_limit = metadata["task_id"], limit
    for count, event in enumerate(events, 1):
        log = full._validate_events(events[:count])
        _accept(index, event)
        assert tuple(index.events_by_id.values()) == log.events
        if isinstance(event.payload, BudgetEventPayload):
            ledger = BudgetLedger(total_limit=limit,
                reservations=tuple(e.payload.reservation for e in index.budget.reservations.values()),
                settlements=tuple(e.payload.settlement for e in index.budget.settlements.values()))
            assert index.budget._amounts() == ledger.committed
            assert index.budget.available == ledger.available
