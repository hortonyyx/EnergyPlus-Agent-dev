"""Root-ledger admission, settlement, recovery, and conservative unknowns."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.agent_runtime.budget import PriceSchedule, RequestEstimate, RuntimeBudget
from src.harness_contracts import (
    BudgetAmounts,
    BudgetEventPayload,
    BudgetLedger,
    BudgetReservation,
    BudgetSettlement,
    CostUnavailable,
    EstimatedCostUpperBound,
    EventEnvelope,
    EventLog,
    KnownTimestamp,
    RootTask,
    UsageMissing,
    UsageReported,
)


PRICING = PriceSchedule(
    model_route="configured/test-model",
    source="checked-in test price table; estimate only",
    input_usd_per_million=Decimal("2"),
    output_usd_per_million=Decimal("4"),
)


def estimate(
    purpose="primary_task",
    *,
    task_id="root-task",
    input_tokens=40,
    output_tokens=60,
    seconds="30",
    pricing=None,
):
    return RequestEstimate.for_model_call(
        purpose=purpose,
        task_id=task_id,
        input_token_upper_bound=input_tokens,
        output_token_limit=output_tokens,
        seconds=Decimal(seconds),
        estimate_source="adapter byte/pixel allowance plus explicit output cap",
        pricing=pricing,
    )


def event(sequence, payload, *, task_id="root-task"):
    return EventEnvelope(
        event_id=f"event-{sequence}",
        run_id="run",
        task_id=task_id,
        parent_task=RootTask(),
        sequence=sequence,
        occurred_at=KnownTimestamp(value=datetime.now(UTC)),
        payload=payload,
    )


def test_settlement_releases_surplus_before_the_next_reservation():
    budget = RuntimeBudget(
        BudgetAmounts(
            tokens=200, seconds=Decimal("100"), calls=4
        )
    )
    first = budget.reserve("primary-1", estimate())
    assert first.action == "allow"
    settled = budget.settle(
        "primary-1",
        actual=BudgetAmounts(tokens=40, seconds=Decimal("10"), calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 40}),
    )
    assert settled.action == "allow"
    assert budget.ledger.charged.tokens == 40
    assert budget.ledger.outstanding.tokens is None
    assert budget.available.tokens == 160

    second = budget.reserve("primary-2", estimate())
    assert second.action == "allow"
    assert budget.ledger.committed.tokens == 140


def test_ledger_charges_settled_actual_plus_outstanding_not_all_history():
    first = BudgetReservation(
        reservation_id="first",
        purpose="primary_task",
        amounts=BudgetAmounts(tokens=80, calls=1),
        task_id="root-task",
    )
    second = BudgetReservation(
        reservation_id="second",
        purpose="retry",
        amounts=BudgetAmounts(tokens=50, calls=1),
        task_id="root-task",
    )
    settlement = BudgetSettlement(
        reservation_id="first",
        actual=BudgetAmounts(tokens=30, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 30}),
        cost=CostUnavailable(reason="no money limit or bill"),
    )
    ledger = BudgetLedger(
        total_limit=BudgetAmounts(tokens=100, calls=3),
        reservations=(first, second),
        settlements=(settlement,),
    )
    assert ledger.charged.tokens == 30
    assert ledger.outstanding.tokens == 50
    assert ledger.committed.tokens == 80
    assert ledger.available.tokens == 20


def test_event_log_rejects_a_transient_overallocation_even_if_later_settlement_frees_it():
    first = BudgetReservation(
        reservation_id="first",
        purpose="primary_task",
        amounts=BudgetAmounts(tokens=80, calls=1),
        task_id="root-task",
    )
    second = BudgetReservation(
        reservation_id="second",
        purpose="retry",
        amounts=BudgetAmounts(tokens=30, calls=1),
        task_id="root-task",
    )
    settlement = BudgetSettlement(
        reservation_id="first",
        actual=BudgetAmounts(tokens=50, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 50}),
        cost=CostUnavailable(reason="no money limit or bill"),
    )
    with pytest.raises(ValidationError, match="effective charges and outstanding"):
        EventLog(
            mode="complete",
            events=(
                event(0, BudgetEventPayload(action="reserve", reservation=first)),
                event(1, BudgetEventPayload(action="reserve", reservation=second)),
                event(2, BudgetEventPayload(action="settle", settlement=settlement)),
            ),
            budget_limit=BudgetAmounts(tokens=100, calls=3),
        )

    valid = EventLog(
        mode="complete",
        events=(
            event(0, BudgetEventPayload(action="reserve", reservation=first)),
            event(1, BudgetEventPayload(action="settle", settlement=settlement)),
            event(2, BudgetEventPayload(action="reserve", reservation=second)),
        ),
        budget_limit=BudgetAmounts(tokens=100, calls=3),
    )
    assert valid.events[-1].payload.reservation.reservation_id == "second"


def test_missing_usage_stays_unknown_and_keeps_conservative_token_and_price_holds():
    budget = RuntimeBudget(
        BudgetAmounts(
            tokens=500,
            money_usd=Decimal("1"),
            seconds=Decimal("60"),
            calls=2,
        ),
        pricing=PRICING,
    )
    admitted = budget.reserve("summary", estimate("context_summary", pricing=PRICING))
    reserved = admitted.reservation.amounts
    settled = budget.settle(
        "summary",
        actual=BudgetAmounts(tokens=None, seconds=Decimal("4"), calls=1),
        usage=UsageMissing(reason="provider omitted the usage object"),
    )
    assert settled.action == "allow"
    assert settled.settlement.actual.tokens is None
    assert settled.settlement.cost.kind == "estimated_upper_bound"
    assert settled.settlement.actual.money_usd is None
    assert budget.ledger.charged.tokens == reserved.tokens
    assert budget.ledger.charged.money_usd == reserved.money_usd
    assert budget.ledger.charged.seconds == Decimal("4")


def test_money_limit_requires_a_configured_estimate_source():
    budget = RuntimeBudget(
        BudgetAmounts(tokens=500, money_usd=Decimal("1"), calls=2)
    )
    decision = budget.reserve("primary", estimate())
    assert decision.action == "stop"
    assert decision.reason == "money_estimate_unavailable"
    assert budget.ledger.reservations == ()


def test_near_limit_stop_or_explicit_output_reduction_never_silently_truncates():
    limits = BudgetAmounts(
        tokens=100,
        money_usd=Decimal("1"),
        seconds=Decimal("60"),
        calls=2,
    )
    requested = estimate(
        input_tokens=60, output_tokens=60, pricing=PRICING
    )
    stopped = RuntimeBudget(limits, pricing=PRICING).reserve("a", requested)
    assert stopped.action == "stop"
    assert stopped.exceeded_dimensions == ("tokens",)

    reduced = RuntimeBudget(
        limits,
        near_limit_policy="reduce_output",
        min_output_tokens=8,
        pricing=PRICING,
    ).reserve("a", requested)
    assert reduced.action == "reduce_output"
    assert reduced.output_token_limit == 40
    assert reduced.effective_estimate.output_token_limit == 40
    assert reduced.reservation.amounts.tokens == 100
    assert requested.output_token_limit == 60


def test_reduction_stops_when_even_the_configured_minimum_cannot_fit():
    budget = RuntimeBudget(
        BudgetAmounts(tokens=65, seconds=Decimal("60"), calls=2),
        near_limit_policy="reduce_output",
        min_output_tokens=8,
    )
    decision = budget.reserve(
        "a", estimate(input_tokens=60, output_tokens=60)
    )
    assert decision.action == "stop"
    assert decision.reason == "minimum_output_cannot_fit_available_budget"


def test_all_request_purposes_share_one_root_ledger():
    budget = RuntimeBudget(
        BudgetAmounts(tokens=400, seconds=Decimal("120"), calls=4)
    )
    purposes = ("primary_task", "child_task", "context_summary", "retry")
    for index, purpose in enumerate(purposes):
        decision = budget.reserve(
            f"request-{index}",
            estimate(purpose, input_tokens=40, output_tokens=60),
        )
        assert decision.action == "allow"
    assert [item.purpose for item in budget.ledger.reservations] == list(purposes)
    assert budget.available.tokens == 0
    assert budget.available.calls == 0


@pytest.mark.parametrize(
    "actual,dimension",
    [
        (BudgetAmounts(tokens=101, seconds=Decimal("10"), calls=1), "tokens"),
        (BudgetAmounts(tokens=80, seconds=Decimal("31"), calls=1), "seconds"),
    ],
)
def test_actual_over_reservation_keeps_the_hold_and_returns_a_fatal_stop(actual, dimension):
    budget = RuntimeBudget(
        BudgetAmounts(tokens=500, seconds=Decimal("100"), calls=4)
    )
    budget.reserve("a", estimate())
    decision = budget.settle(
        "a",
        actual=actual,
        usage=UsageReported(raw_usage={"total_tokens": actual.tokens}),
    )
    assert decision.action == "stop"
    assert decision.reason == "actual_usage_exceeds_reservation"
    assert decision.exceeded_dimensions == (dimension,)
    assert budget.ledger.settlements == ()
    assert budget.ledger.outstanding.tokens == 100
    assert budget.reserve("b", estimate()).action == "stop"


def test_runtime_budget_recovers_settled_and_outstanding_state_from_events():
    budget = RuntimeBudget(
        BudgetAmounts(tokens=300, seconds=Decimal("100"), calls=3)
    )
    first = budget.reserve("a", estimate()).reservation
    settlement = budget.settle(
        "a",
        actual=BudgetAmounts(tokens=30, seconds=Decimal("3"), calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 30}),
    ).settlement
    second = budget.reserve("b", estimate("child_task")).reservation
    records = (
        BudgetEventPayload(action="reserve", reservation=first),
        BudgetEventPayload(action="settle", settlement=settlement),
        BudgetEventPayload(action="reserve", reservation=second),
    )
    recovered = RuntimeBudget.from_events(
        budget.total_limit, records, near_limit_policy="reduce_output"
    )
    assert recovered.ledger == budget.ledger
    assert recovered.available.tokens == 170


def test_event_recovery_detects_reported_overrun_left_without_a_false_settlement():
    reservation = BudgetReservation(
        reservation_id="request-1",
        purpose="primary_task",
        amounts=BudgetAmounts(tokens=100, calls=1),
        task_id="root-task",
    )
    records = (
        BudgetEventPayload(action="reserve", reservation=reservation),
        SimpleNamespace(
            event_id="request-event",
            payload=SimpleNamespace(
                event_type="adapter_request", reservation_id="request-1"
            ),
        ),
        SimpleNamespace(
            event_id="response-event",
            payload=SimpleNamespace(
                event_type="model_response",
                request_event_id="request-event",
                usage=UsageReported(raw_usage={"total_tokens": 120}),
            ),
        ),
    )
    recovered = RuntimeBudget.from_events(
        BudgetAmounts(tokens=500, calls=3), records
    )
    assert recovered.fatal_reason == "actual_usage_exceeds_reservation"
    assert recovered.reserve("next", estimate()).action == "stop"


def test_price_configuration_never_turns_an_estimate_into_reported_cost():
    budget = RuntimeBudget(
        BudgetAmounts(tokens=500, money_usd=Decimal("1"), calls=2),
        pricing=PRICING,
    )
    reservation = budget.reserve(
        "a", estimate(pricing=PRICING)
    ).reservation
    decision = budget.settle(
        "a",
        actual=BudgetAmounts(tokens=50, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 50}),
    )
    assert decision.settlement.cost == EstimatedCostUpperBound(
        usd=reservation.amounts.money_usd,
        reason="configured price estimate retained because no provider bill was supplied",
    )
    assert decision.settlement.actual.money_usd is None
