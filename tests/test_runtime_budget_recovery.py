"""Offline append-only recovery, exact receipt binding and shared-root accounting."""

from decimal import Decimal
import json

import pytest
from pydantic import ValidationError

from src.agent_runtime.accounting import account_request_usage, get_cny_price_schedule, request_accounting_from_store, summarize_request_accounting
from src.agent_runtime.adapter import prepare_request
from src.agent_runtime.budget import RequestEstimate, RuntimeBudget
from src.agent_runtime.budget_recovery import main, reconcile_missing_usage, release_unsent_reservation
from src.agent_runtime.store import EventStore
from src.harness_contracts import (
    BudgetAmounts, BudgetEventPayload, BudgetReconciliation, BudgetRelease,
    BudgetReservation, BudgetSettlement, CostUnavailable, RunLifecyclePayload,
    UsageMissing, UsageReported,
)
from test_agent_runtime import versions


LIMIT = BudgetAmounts(tokens=100, money_cny=Decimal("1"), seconds=Decimal(100), calls=10)


def reserve(store, name="request-1"):
    reservation = BudgetReservation(reservation_id=name, purpose="primary_task",
        task_id=store.task_id, amounts=BudgetAmounts(tokens=80, money_cny=min(Decimal("0.25"), store.budget_limit.money_cny / 2),
            seconds=Decimal(20), calls=1))
    return store.append(BudgetEventPayload(action="reserve", reservation=reservation))


def request(store, reservation_event):
    version = versions()
    version = version.model_copy(update={"remote_model": version.remote_model.model_copy(
        update={"route_id": "paratera", "remote_alias": "Qwen3.8-27B"})})
    prepared = prepare_request(store=store, model="Qwen3.8-27B",
        messages=[{"role": "user", "content": "offline"}],
        message_sources=[store.source("input", "offline")], tools=[],
        tool_source=store.source("tools", []), parameters={"max_tokens": 10}, versions=version)
    return store.append(prepared.event_payload.model_copy(update={
        "reservation_id": reservation_event.payload.reservation.reservation_id}))


def missing(store, reservation_event):
    old = BudgetSettlement(reservation_id=reservation_event.payload.reservation.reservation_id,
        actual=BudgetAmounts(seconds=Decimal(2), calls=1),
        usage=UsageMissing(reason="offline timeout: receipt unavailable"),
        cost=CostUnavailable(reason="no USD tariff"))
    return store.append(BudgetEventPayload(action="settle", settlement=old))


def receipt(store, req, old, *, tokens=30, cny=None, updates=None):
    reserved = next(e.payload.reservation for e in store.all_events
        if e.payload.event_type == "budget" and e.payload.action == "reserve"
        and e.payload.reservation.reservation_id == req.payload.reservation_id)
    raw = {"prompt_tokens": tokens - 10, "completion_tokens": 10, "total_tokens": tokens}
    if cny is None:
        cny = account_request_usage(raw, image_tokens_estimate=0,
            pricing=get_cny_price_schedule("Qwen3.8-27B", route_id="paratera")).estimated_cost_cny
    new = old.payload.settlement.model_copy(update={
        "actual": BudgetAmounts(tokens=tokens, seconds=Decimal(2), calls=1),
        "usage": UsageReported(raw_usage=raw), "estimated_cost_cny": Decimal(cny),
        "token_overrun": max(tokens - reserved.amounts.tokens, 0),
        "money_cny_overrun": max(Decimal(cny) - reserved.amounts.money_cny, Decimal(0)),
        **(updates or {}),
    })
    data = {"request_event_id": req.event_id, "settlement_event_id": old.event_id,
            "settlement": new.model_dump(mode="json")}
    source = store.source("late-receipt", data, kind="user")
    return BudgetReconciliation(reservation_id=new.reservation_id,
        request_event_id=req.event_id, settlement_event_id=old.event_id,
        settlement=new, evidence=source)


def open_store(path, limit=LIMIT):
    return EventStore(path, run_id="offline", task_id="root", budget_limit=limit)


def test_release_is_append_only_idempotent_and_restartable(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        before = store.path.read_bytes()
        released = release_unsent_reservation(store, "request-1", reason="reserve-before-intent crash")
        assert store.path.read_bytes().startswith(before)
        assert release_unsent_reservation(store, "request-1", reason="reserve-before-intent crash") == released
        with pytest.raises(ValueError, match="conflicting release"):
            release_unsent_reservation(store, "request-1", reason="different")
        with pytest.raises(ValueError, match="released reservation"):
            request(store, r)
    with open_store(tmp_path) as reopened:
        budget = RuntimeBudget.from_events(LIMIT, reopened.all_events)
        assert budget.ledger.outstanding == BudgetAmounts()
        assert budget.available == LIMIT
        assert len(budget.ledger.reservations) == len(budget.ledger.releases) == 1


def test_intent_without_response_must_not_be_released(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        request(store, r)
        before = store.path.read_bytes()
        with pytest.raises(ValueError, match="not proven unsent"):
            release_unsent_reservation(store, "request-1", reason="must refuse")
        assert store.path.read_bytes() == before
        assert RuntimeBudget.from_events(LIMIT, store.all_events).ledger.outstanding.tokens == 80


def test_missing_settlement_stays_fatal_until_sourced_reconciliation(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        stopped = RuntimeBudget.from_events(LIMIT, store.all_events)
        assert stopped.fatal_reason == "money_cny_usage_unavailable"
        assert stopped.ledger.charged.tokens == 80
        assert stopped.ledger.charged.money_cny == Decimal("0.25")
        before = store.path.read_bytes()
        proof = receipt(store, req, old)
        appended = reconcile_missing_usage(store, proof)
        assert reconcile_missing_usage(store, proof) == appended
        assert store.path.read_bytes().startswith(before)
        budget = RuntimeBudget.from_events(LIMIT, store.all_events)
        assert budget.fatal_reason is None
        assert budget.ledger.charged.tokens == 30
        assert budget.ledger.charged.money_cny == Decimal("0.00018")
        assert budget.ledger.settlements[0].usage.kind == "missing"
        assert budget.ledger.settlements[0].actual.tokens is None
        assert budget.ledger.effective_settlements[0].usage.kind == "reported"
        record = request_accounting_from_store(store, req.event_id)
        info = record.receipt_dict()
        assert info["original_usage_kind"] == "missing"
        assert "timeout" in info["original_missing_reason"]
        assert info["usage_basis"] == "reconciled_provider_reported"
        assert info["reconciliation_event_id"] == appended.event_id
        assert Decimal(info["estimated_cost_cny"]) == Decimal("0.00018")
        assert summarize_request_accounting([record])["provider_reported_tokens"] == 30
        assert summarize_request_accounting([record])["usage_complete"] is True
    with open_store(tmp_path) as reopened:
        assert RuntimeBudget.from_events(LIMIT, reopened.all_events).ledger.charged.tokens == 30


@pytest.mark.parametrize("tokens,cny,reason", [(120, "0.00045", "token_budget_exhausted"),
    (30, "0.00018", "money_budget_exhausted")])
def test_late_real_overrun_remains_fatal_and_cannot_be_reconciled_down(tmp_path, tokens, cny, reason):
    limit = LIMIT if reason == "token_budget_exhausted" else LIMIT.model_copy(update={"money_cny": Decimal("0.00015")})
    with open_store(tmp_path, limit) as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        reconcile_missing_usage(store, receipt(store, req, old, tokens=tokens, cny=cny))
        budget = RuntimeBudget.from_events(limit, store.all_events)
        assert budget.fatal_reason == reason
        assert budget.ledger.charged.tokens == tokens
        assert budget.ledger.charged.money_cny == Decimal(cny)
        assert budget.available.tokens == max(100 - tokens, 0)
        with pytest.raises(ValueError, match="conflicting reconciliation"):
            reconcile_missing_usage(store, receipt(store, req, old, tokens=20))


@pytest.mark.parametrize("change", ["seconds", "calls", "images", "missing_cny", "binding", "source"])
def test_reconciliation_rejects_known_charge_changes_and_false_sources(tmp_path, change):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        updates = {"seconds": {"actual": BudgetAmounts(tokens=30, seconds=Decimal(1), calls=1)},
            "calls": {"actual": BudgetAmounts(tokens=30, seconds=Decimal(2), calls=0)},
            "images": {"image_tokens_estimate": 1}, "missing_cny": {"estimated_cost_cny": None}}.get(change)
        proof = receipt(store, req, old, updates=updates)
        if change == "binding":
            proof = proof.model_copy(update={"request_event_id": "event-does-not-exist"})
        if change == "source":
            proof = proof.model_copy(update={"evidence": store.source("wrong", {"usage": 0})})
        before = store.path.read_bytes()
        with pytest.raises((ValueError, ValidationError)):
            reconcile_missing_usage(store, proof)
        assert store.path.read_bytes() == before


def test_root_and_child_recovery_charge_only_original_task(tmp_path):
    with open_store(tmp_path) as root:
        root.append(RunLifecyclePayload(action="start", reason="root"))
        child = root.for_task("reader", "root")
        r = reserve(child)
        req = request(child, r)
        old = missing(child, r)
        event = reconcile_missing_usage(root, receipt(root, req, old))
        assert event.task_id == "reader" and event.parent_task.task_id == "root"
        root_budget = RuntimeBudget.from_events(LIMIT, root.all_events)
        child_budget = RuntimeBudget.from_events(LIMIT, child.events)
        assert root_budget.ledger.charged == child_budget.ledger.charged
        assert root_budget.ledger.charged.calls == 1
        sibling = root.for_task("sibling", "root")
        with pytest.raises(ValueError, match="another task"):
            reconcile_missing_usage(sibling, receipt(root, req, old))


def test_cli_commands_are_published_and_replay_existing_journal(tmp_path, capsys):
    with open_store(tmp_path) as store:
        reserve(store)
    assert main([str(tmp_path), "release", "request-1", "--reason", "cli offline recovery"]) == 0
    assert json.loads(capsys.readouterr().out)["payload"]["action"] == "release"


def test_budget_clone_has_independent_mutable_admission_state():
    original = RuntimeBudget(BudgetAmounts(tokens=1000, calls=3, seconds=Decimal(20)))
    copied = original.clone()
    estimate = RequestEstimate.for_model_call(purpose="primary_task", task_id="root",
        input_token_upper_bound=10, output_token_limit=10, seconds=Decimal(2), estimate_source="offline")
    assert copied.reserve("copy-only", estimate).action == "allow"
    assert original.ledger.reservations == ()
    assert original.available.tokens == 1000


def test_reconciliation_requires_complete_reported_usage(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        with pytest.raises(ValidationError, match="reported token usage"):
            receipt(store, req, old, updates={"usage": UsageReported(raw_usage={"prompt_tokens": 20})})


def test_source_matching_wrong_request_binding_is_rejected(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        proof = receipt(store, req, old)
        data = {"request_event_id": r.event_id, "settlement_event_id": old.event_id,
            "settlement": proof.settlement.model_dump(mode="json")}
        proof = proof.model_copy(update={"request_event_id": r.event_id,
            "evidence": store.source("wrong-request", data)})
        with pytest.raises(ValueError, match="prior request"):
            reconcile_missing_usage(store, proof)


def test_existing_real_usage_cannot_be_replaced_by_reconciliation(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = store.append(BudgetEventPayload(action="settle", settlement=BudgetSettlement(
            reservation_id="request-1", actual=BudgetAmounts(tokens=60, seconds=Decimal(2), calls=1),
            usage=UsageReported(raw_usage={"total_tokens": 60}),
            cost=CostUnavailable(reason="no USD tariff"), estimated_cost_cny=Decimal("0.2"))))
        with pytest.raises(ValueError, match="missing-usage settlement"):
            reconcile_missing_usage(store, receipt(store, req, old))
        assert RuntimeBudget.from_events(LIMIT, store.all_events).ledger.charged.tokens == 60


def test_cli_reconciliation_captures_input_and_is_idempotent(tmp_path, capsys):
    with open_store(tmp_path / "run") as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        proof = receipt(store, req, old)
        data = store.get_bytes(proof.evidence.blob)
    receipt_path = tmp_path / "late-receipt.json"
    receipt_path.write_bytes(data)
    argv = [str(tmp_path / "run"), "reconcile", "--receipt", str(receipt_path)]
    assert main(argv) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["payload"]["action"] == "reconcile"
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out)["event_id"] == first["event_id"]


def test_root_release_preserves_child_ancestry_and_shared_capacity(tmp_path):
    with open_store(tmp_path) as root:
        root.append(RunLifecyclePayload(action="start", reason="root"))
        child = root.for_task("reader", "root")
        reserve(child)
        released = release_unsent_reservation(root, "request-1", reason="child unsent crash")
        assert released.task_id == "reader" and released.parent_task.task_id == "root"
        assert RuntimeBudget.from_events(LIMIT, root.all_events).available == LIMIT


def test_writer_lock_prevents_cli_recovery_during_active_run(tmp_path):
    with open_store(tmp_path) as store:
        reserve(store)
        before = store.path.read_bytes()
        with pytest.raises((OSError, ValueError)):
            main([str(tmp_path), "release", "request-1", "--reason", "cannot race"])
        assert store.path.read_bytes() == before


def test_sourced_but_understated_currency_cannot_release_the_unknown_hold(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = missing(store, r)
        with pytest.raises(ValueError, match="evidenced usage and rate"):
            reconcile_missing_usage(store, receipt(store, req, old, cny="0"))
        assert RuntimeBudget.from_events(LIMIT, store.all_events).fatal_reason == "money_cny_usage_unavailable"


def test_frozen_request_rate_is_used_instead_of_current_price_table(tmp_path):
    with open_store(tmp_path) as store:
        schedule = {"provider": "paratera", "model": "Qwen3.8-27B",
            "text_input_cny_per_million": "6", "output_cny_per_million": "24",
            "image_input_cny_per_million": "6", "cached_input_cny_per_million": "1.2",
            "source": "offline frozen request rate", "image_billing_status": "bill_observed_separate_at_text_input_rate"}
        reservation = BudgetReservation(reservation_id="request-1", purpose="primary_task",
            task_id="root", amounts=BudgetAmounts(tokens=80, money_cny=Decimal("0.25"), seconds=Decimal(20), calls=1))
        r = store.append(BudgetEventPayload(action="reserve", reservation=reservation),
            source_refs=(store.source("request-budget-decision", {"cny_reservation": {"price_schedule": schedule}}),))
        req = request(store, r)
        old = missing(store, r)
        with pytest.raises(ValueError, match="evidenced usage and rate"):
            reconcile_missing_usage(store, receipt(store, req, old))
        reconcile_missing_usage(store, receipt(store, req, old, cny="0.00036"))
        assert RuntimeBudget.from_events(LIMIT, store.all_events).ledger.charged.money_cny == Decimal("0.00036")
        assert request_accounting_from_store(store, req.event_id).accounting.estimated_cost_cny == Decimal("0.00036")


def test_reconciling_one_child_does_not_clear_another_child_unknown_hold(tmp_path):
    limit = LIMIT.model_copy(update={"tokens": 200})
    with open_store(tmp_path, limit) as root:
        root.append(RunLifecyclePayload(action="start", reason="root"))
        tasks = []
        for name in ("first", "second"):
            child = root.for_task(name, "root")
            r = reserve(child, name=name)
            tasks.append((request(child, r), missing(child, r)))
        req, old = tasks[0]
        reconcile_missing_usage(root, receipt(root, req, old))
        budget = RuntimeBudget.from_events(limit, root.all_events)
        assert budget.fatal_reason == "money_cny_usage_unavailable"
        assert budget.ledger.charged.tokens == 110
        assert budget.ledger.charged.money_cny == Decimal("0.25018")
        req, old = tasks[1]
        reconcile_missing_usage(root, receipt(root, req, old))
        assert RuntimeBudget.from_events(limit, root.all_events).fatal_reason is None


def test_late_reported_image_line_updates_charge_but_retains_original_estimate(tmp_path):
    with open_store(tmp_path) as store:
        r = reserve(store)
        req = request(store, r)
        old = store.append(BudgetEventPayload(action="settle", settlement=BudgetSettlement(
            reservation_id="request-1", actual=BudgetAmounts(seconds=Decimal(2), calls=1),
            usage=UsageMissing(reason="timeout"), cost=CostUnavailable(reason="no USD tariff"),
            image_tokens_estimate=100, additional_image_tokens=100)))
        proof = receipt(store, req, old, cny="0.00024", updates={
            "usage": UsageReported(raw_usage={"prompt_tokens": 20, "completion_tokens": 10,
                "total_tokens": 30, "prompt_tokens_details": {"image_tokens": 20, "text_tokens": 0}}),
            "additional_image_tokens": 20, "reported_usage_includes_image_tokens": True})
        reconcile_missing_usage(store, proof)
        ledger = RuntimeBudget.from_events(LIMIT, store.all_events).ledger
        assert ledger.settlements[0].additional_image_tokens == 100
        assert ledger.effective_settlements[0].additional_image_tokens == 20
        assert ledger.charged.tokens == 50
        assert ledger.charged.money_cny == Decimal("0.00024")
