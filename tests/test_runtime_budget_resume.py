"""Runtime.resume consumes append-only budget releases and late receipts."""

import asyncio
from decimal import Decimal
import json

import pytest

from src.agent_runtime.accounting import account_request_usage
from src.agent_runtime.budget_recovery import reconcile_missing_usage, release_unsent_reservation
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetReconciliation, RunLifecyclePayload, UsageReported
from test_agent_runtime import MESSAGES, response, runtime
from test_runtime_a4r_money import money_engine
from test_runtime_child_tasks import _child


class Crash(BaseException):
    pass


def late_receipt(engine, *, tokens=30):
    store = engine.store
    request = next(e for e in store.events if e.payload.event_type == "adapter_request")
    old = next(e for e in store.events if e.payload.event_type == "budget" and e.payload.action == "settle")
    reserved = next(r for r in engine.budget.ledger.reservations if r.reservation_id == request.payload.reservation_id)
    usage = UsageReported(raw_usage={"prompt_tokens": tokens - 10, "completion_tokens": 10, "total_tokens": tokens})
    original = old.payload.settlement
    accounting = account_request_usage(usage, image_tokens_estimate=original.image_tokens_estimate,
        pricing=engine.cny_pricing)
    settled = original.model_copy(update={"actual": original.actual.model_copy(update={"tokens": tokens}),
        "usage": usage, "estimated_cost_cny": accounting.estimated_cost_cny,
        "token_overrun": max(accounting.budget_charge_tokens - reserved.amounts.tokens, 0),
        "money_cny_overrun": max((accounting.estimated_cost_cny or Decimal(0)) - (reserved.amounts.money_cny or Decimal(0)), Decimal(0))})
    source = store.source("late-provider-receipt", {"request_event_id": request.event_id,
        "settlement_event_id": old.event_id, "settlement": settled.model_dump(mode="json")}, kind="user")
    return reconcile_missing_usage(store, BudgetReconciliation(reservation_id=reserved.reservation_id,
        request_event_id=request.event_id, settlement_event_id=old.event_id, settlement=settled, evidence=source))


@pytest.mark.parametrize("pre_released", [False, True])
def test_resume_releases_unsent_reservation_and_dispatches_only_once(tmp_path, pre_released):
    engine = runtime(tmp_path, [response(text="never sent")])
    def crash(name, _):
        if name == "after_reservation":
            raise Crash()
    engine.fault_hook = crash
    with engine.store:
        with pytest.raises(Crash):
            asyncio.run(engine.run(MESSAGES))
        reservation = engine.budget.ledger.reservations[0]
        if pre_released:
            release_unsent_reservation(engine.store, reservation.reservation_id, reason="operator recovery")
    assert engine.adapter.requests == []
    resumed = runtime(tmp_path, [response(text="resumed once")], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed"
        assert len(resumed.adapter.requests) == 1
        assert result["model_calls"] == 1
        assert len(resumed.budget.ledger.releases) == 1
        assert len(resumed.budget.ledger.reservations) == 2
        assert resumed.budget.ledger.charged.tokens == 30
        resumed.store.validate()


@pytest.mark.parametrize("checkpoint", ["before_response", "blocked_response", "accepted_response"])
@pytest.mark.parametrize("currency", [False, True])
def test_evidenced_missing_usage_resume_accepts_original_response_once(tmp_path, checkpoint, currency):
    factory = money_engine if currency else runtime
    engine = factory(tmp_path, [response(("save-once", "save", {"value": 7}), usage=False)])
    with engine.store:
        stopped = asyncio.run(engine.run(MESSAGES))
        assert stopped["status"] == ("money_cny_usage_unavailable" if currency else "token_usage_unavailable")
        original_response = next(e for e in engine.store.events if e.payload.event_type == "model_response")
        if checkpoint != "before_response":
            if checkpoint == "accepted_response":
                engine._accept_response(original_response)
            else:
                engine.terminal_reason = stopped["status"]
            engine._checkpoint()
        original_line = original_response.model_dump_json()
        late_receipt(engine)
        assert original_response.model_dump_json() == original_line
        assert original_response.payload.usage.kind == "missing"
    assert engine.tools.calls == []
    resumed = factory(tmp_path, [response(text="done")], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed"
        assert result["usage_complete"] is True
        assert result["reported_tokens"] == 60
        assert result["model_calls"] == 2
        assert len(resumed.adapter.requests) == 1
        assert engine.tools.calls == [("save", {"value": 7})]
        assert resumed.budget.ledger.settlements[0].usage.kind == "missing"
        assert resumed.budget.ledger.effective_settlements[0].usage.kind == "reported"
        assert result["usage_accounting"]["reconciled_requests"] == 1
        resumed.store.validate()


def test_reconciliation_over_root_token_limit_still_stops_before_tools_or_send(tmp_path):
    limits = RunLimits(model_calls=3, tool_calls=2, seconds=30, tokens=1000)
    engine = runtime(tmp_path, [response(("save", "save", {"value": 7}), usage=False)], limits=limits)
    with engine.store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "token_usage_unavailable"
        late_receipt(engine, tokens=2000)
    resumed = runtime(tmp_path, [response(text="must not send")], limits=limits, tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "token_budget_exhausted"
        assert result["reported_tokens"] == 2000
        assert result["usage_complete"] is True
        assert resumed.adapter.requests == [] and engine.tools.calls == []
        assert resumed.budget.ledger.charged.tokens == 2000
        resumed.store.validate()


def test_sibling_safe_checkpoint_reports_actual_root_token_fatal(tmp_path):
    limits = RunLimits(model_calls=3, tool_calls=2, seconds=30, tokens=2000)
    with EventStore(tmp_path / "run", run_id="root", task_id="root", budget_limit=limits.ledger_limit()) as root:
        root.append(RunLifecyclePayload(action="start", reason="root"))
        sibling = _child(root, tmp_path, "safe-reader", [])
        def checkpoint_crash(name, _):
            if name == "after_checkpoint":
                raise Crash()
        sibling.fault_hook = checkpoint_crash
        with pytest.raises(Crash):
            asyncio.run(sibling.run(MESSAGES))
        expensive = response(text="full charge")
        expensive["usage"] = {"prompt_tokens": 4990, "completion_tokens": 10, "total_tokens": 5000}
        first = _child(root, tmp_path, "overrun-reader", [expensive])
        assert asyncio.run(first.run(MESSAGES))["status"] == "root_token_budget_exhausted"
        resumed = _child(root, tmp_path, "safe-reader", [response(text="must not send")])
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "root_token_budget_exhausted"
        assert resumed.adapter.requests == []


def test_checkpointed_completed_response_with_reconciliation_needs_no_new_request(tmp_path):
    engine = runtime(tmp_path, [response(text="saved answer", usage=False)])
    with engine.store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "token_usage_unavailable"
        event = next(e for e in engine.store.events if e.payload.event_type == "model_response")
        engine._accept_response(event)
        engine._checkpoint()
        late_receipt(engine)
    resumed = runtime(tmp_path, [], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed"
        assert result["answer"] == "saved answer"
        assert result["usage_complete"] is True
        assert resumed.adapter.requests == []


def test_missing_transport_receipt_can_resume_one_budgeted_retry_after_reconciliation(tmp_path):
    engine = money_engine(tmp_path, [ConnectionError("offline unknown receipt")])
    with engine.store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "money_cny_usage_unavailable"
        assert not any(e.payload.event_type == "model_response" for e in engine.store.events)
        late_receipt(engine)
    resumed = money_engine(tmp_path, [response(text="retry done")], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed"
        assert result["model_calls"] == 2 and result["retries"] == 1
        assert result["usage_complete"] is True
        assert result["reported_tokens"] == 60
        assert len(resumed.adapter.requests) == 1


def test_reconciliation_releases_usage_blocked_truncation_without_erasing_old_stop(tmp_path):
    truncated = response(text="discard partial", usage=False)
    truncated["choices"][0]["finish_reason"] = "length"
    engine = runtime(tmp_path, [truncated])
    with engine.store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "token_usage_unavailable"
        original = next(e for e in engine.store.events if e.payload.event_type == "response_truncation")
        assert original.payload.action == "stop"
        late_receipt(engine)
    resumed = runtime(tmp_path, [response(text="complete response")], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed"
        events = [e for e in resumed.store.events if e.payload.event_type == "response_truncation"]
        assert [e.payload.action for e in events] == ["stop"]
        assert "discard partial" not in json.dumps(resumed.messages)
        assert len(resumed.adapter.requests) == 1
        resumed.store.validate()
