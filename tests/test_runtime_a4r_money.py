"""CNY ceilings reserve conservatively, settle reported usage and survive recovery."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.agent.runtime_configuration import argv_for, validate_budget
from src.agent.runtime_entry import parser
from src.agent_runtime.accounting import account_request_usage, require_cny_price_schedule
from src.agent_runtime.budget import RequestEstimate, RuntimeBudget
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, BudgetEventPayload, UsageMissing, UsageReported
from test_agent_runtime import MESSAGES, response, runtime
from test_runtime_child_tasks import _child


PRICE = require_cny_price_schedule("Qwen3.8-27B", route_id="paratera")
ROOT = Path(__file__).resolve().parents[1]


def estimate(*, images=0, output=1000):
    return RequestEstimate.for_model_call(purpose="primary_task", task_id="root",
        input_token_upper_bound=100_000, image_input_tokens_estimate=images,
        additional_image_tokens_estimate=images, output_token_limit=output,
        seconds=Decimal(10), estimate_source="offline upper bound", cny_pricing=PRICE)


def usage(*, cached=0, images=0):
    return UsageReported(raw_usage={"prompt_tokens": 100_000, "completion_tokens": 500,
        "total_tokens": 100_500, "prompt_tokens_details": {
            "cached_tokens": cached, "image_tokens": images, "text_tokens": 100_000 - images}})


@pytest.mark.parametrize("cached", [0, 90_000])
@pytest.mark.parametrize("images", [0, 200, 30_000])
def test_cache_is_discounted_only_after_receipt_and_images_are_billed_again(cached, images):
    budget = RuntimeBudget(BudgetAmounts(money_cny=Decimal("0.6"), calls=3))
    before = budget.reserve("first", estimate(images=images))
    assert before.action == "allow"
    assert before.reservation.amounts.money_cny == Decimal("0.312") + Decimal(images) * Decimal("0.000003")
    evidence = usage(cached=cached, images=images)
    accounting = account_request_usage(evidence, image_tokens_estimate=images, pricing=PRICE)
    settled = budget.settle("first", actual=BudgetAmounts(tokens=100_500, calls=1),
        usage=evidence, estimated_cost_cny=accounting.estimated_cost_cny,
        image_tokens_estimate=images, reported_usage_includes_image_tokens=images > 0,
        additional_image_tokens=images)
    expected = Decimal("0.306") - Decimal(cached) * Decimal("0.0000024") + Decimal(images) * Decimal("0.000003")
    assert settled.settlement.actual.money_cny is None
    assert budget.ledger.charged.money_cny == expected
    assert budget.reserve("next", estimate(images=images)).action == ("allow" if cached else "stop")


@pytest.mark.parametrize("delta,allowed", [("-0.000000001", False), ("0", True), ("0.000000001", True)])
def test_request_is_refused_before_send_when_its_full_hold_cannot_fit(delta, allowed):
    limit = estimate().amounts.money_cny + Decimal(delta)
    budget = RuntimeBudget(BudgetAmounts(money_cny=limit, calls=1))
    result = budget.reserve("last", estimate())
    assert (result.action == "allow") is allowed
    assert len(budget.ledger.reservations) == int(allowed)


@pytest.mark.parametrize("ceiling,status", [("0.4", "stop"), ("1", "allow")])
def test_cny_overrun_records_full_charge_and_recovery_cannot_refund_it(ceiling, status):
    limit = BudgetAmounts(money_cny=Decimal(ceiling), calls=3)
    budget = RuntimeBudget(limit)
    reserved = budget.reserve("first", estimate())
    result = budget.settle("first", actual=BudgetAmounts(tokens=100_500, calls=1),
        usage=usage(), estimated_cost_cny=Decimal("0.5"))
    assert result.action == status
    assert result.settlement.money_cny_overrun == Decimal("0.188")
    events = [BudgetEventPayload(action="reserve", reservation=reserved.reservation),
        BudgetEventPayload(action="settle", settlement=result.settlement)]
    rebuilt = RuntimeBudget.from_events(limit, events)
    assert rebuilt.ledger.charged.money_cny == Decimal("0.5")
    assert rebuilt.available.money_cny == max(Decimal(ceiling) - Decimal("0.5"), 0)
    assert rebuilt.reserve("next", estimate()).action == status


def money_engine(path, replies, *, ceiling="1", tokens=None, **kwargs):
    limits = RunLimits(model_calls=6, tool_calls=6, seconds=30.0, tokens=tokens,
        money_cny=Decimal(ceiling), retry_backoff_seconds=0.0)
    return configure(runtime(path, replies, limits=limits, **kwargs))


def configure(engine):
    engine.model = "Qwen3.8-27B"
    engine.parameters = {"max_tokens": 100, "temperature": 0.0}
    engine.low_output_limit_reason = "offline money-boundary fixture"
    engine.versions = engine.versions.model_copy(update={"remote_model":
        engine.versions.remote_model.model_copy(update={"route_id": "paratera", "remote_alias": engine.model})})
    return engine


@pytest.mark.parametrize("raw", [None, {"total_tokens": 100}, {"prompt_tokens": 10},
    {"prompt_tokens": 10, "completion_tokens": 1, "prompt_tokens_details": {"cached_tokens": 20}}])
def test_missing_or_unpriceable_usage_stops_and_holds_money_after_restart(tmp_path, raw):
    reply = response(("must-not-write", "save", {"value": 7}), usage=False)
    if raw is not None:
        reply["usage"] = raw
    engine = money_engine(tmp_path, [reply, response(text="must not send")])
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "money_cny_usage_unavailable"
        assert result["model_calls"] == 1 and not engine.tools.calls
        charge = engine.budget.ledger.charged.money_cny
        assert charge == engine.budget.ledger.reservations[0].amounts.money_cny
        assert engine.budget.ledger.settlements[0].estimated_cost_cny is None
        engine.store.validate()
    resumed = money_engine(tmp_path, [], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "money_cny_usage_unavailable"
        assert resumed.adapter.requests == []
        assert resumed.budget.ledger.charged.money_cny == charge


def test_unknown_transport_usage_cannot_trigger_a_money_limited_retry(tmp_path):
    engine = money_engine(tmp_path, [ConnectionError("offline"), response(text="not sent")])
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "money_cny_usage_unavailable"
        assert result["model_calls"] == 1 and result["retries"] == 0
        engine.store.validate()


def test_known_retry_is_charged_and_second_request_uses_remaining_cny(tmp_path):
    empty = response(text=None)
    empty["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    engine = money_engine(tmp_path, [empty, response(text="done")])
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed" and result["retries"] == 1
        assert [r.purpose for r in engine.budget.ledger.reservations] == ["primary_task", "retry"]
        assert engine.budget.ledger.charged.money_cny == Decimal("0.00018")
        engine.store.validate()


def test_late_response_keeps_full_cny_charge_even_below_its_token_estimate(tmp_path):
    engine = money_engine(tmp_path, [response(text="late")])
    settle = engine._settle
    engine._settle = lambda reservation, usage, *, seconds: settle(reservation, usage, seconds=100)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "time_budget_exhausted"
        assert engine.budget.ledger.charged.money_cny == Decimal("0.00018")
        assert result["model_calls"] == 1
        engine.store.validate()


def test_crash_before_settlement_recovers_full_cny_charge_before_executing_tools(tmp_path):
    class Crash(BaseException):
        pass
    reply = response(("must-not-write", "save", {}))
    reply["usage"] = usage().raw_usage
    engine = money_engine(tmp_path, [reply], ceiling="0.2")
    engine._settle = lambda *a, **k: (_ for _ in ()).throw(Crash())
    with engine.store, pytest.raises(Crash):
        asyncio.run(engine.run(MESSAGES))
    resumed = money_engine(tmp_path, [], ceiling="0.2", tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "money_budget_exhausted"
        assert resumed.budget.ledger.charged.money_cny == Decimal("0.306")
        assert resumed.budget.available.money_cny == 0
        assert resumed.adapter.requests == [] and resumed.tools.calls == []
        resumed.store.validate()


def test_old_journal_without_cny_field_reopens_but_cannot_gain_a_new_ceiling(tmp_path):
    limits = BudgetAmounts(tokens=1000, calls=2)
    with EventStore(tmp_path / "old", run_id="old", task_id="root", budget_limit=limits):
        pass
    path = tmp_path / "old/journal.json"
    metadata = json.loads(path.read_bytes())
    del metadata["budget_limit"]["money_cny"]
    path.write_text(json.dumps(metadata))
    with EventStore(path.parent, run_id="old", task_id="root", budget_limit=limits):
        pass
    with pytest.raises(ValueError, match="cannot change"):
        EventStore(path.parent, run_id="old", task_id="root",
            budget_limit=limits.model_copy(update={"money_cny": Decimal(1)}))


@pytest.mark.parametrize("tokens,expected", [(None, "completed"), (1, "token_budget_exhausted")])
def test_explicit_token_limit_still_applies_alongside_cny(tmp_path, tokens, expected):
    engine = money_engine(tmp_path, [response(text="done")], tokens=tokens)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == expected


def test_output_reduction_recalculates_cny_and_preserves_image_hold():
    budget = RuntimeBudget(BudgetAmounts(money_cny=Decimal("0.39"), calls=1),
        near_limit_policy="reduce_output", min_output_tokens=10, cny_pricing=PRICE)
    result = budget.reserve("reduced", estimate(images=20_000, output=10_000))
    assert result.action == "reduce_output"
    assert result.output_token_limit == 2500
    assert result.reservation.amounts.money_cny == Decimal("0.39")
    assert result.reservation.amounts.tokens == 122_500


def test_parallel_children_reserve_from_the_same_cny_ceiling(tmp_path):
    limits = RunLimits(model_calls=4, tool_calls=5, seconds=30.0, tokens=None, money_cny=Decimal("0.01"))
    with EventStore(tmp_path / "run", run_id="root", task_id="root", budget_limit=limits.ledger_limit()) as store:
        child_limits = RunLimits(model_calls=2, tool_calls=1, seconds=20.0, tokens=None)
        first = configure(_child(store, tmp_path, "first", [], limits=child_limits))
        second = configure(_child(store, tmp_path, "second", [], limits=child_limits))
        # Long input makes each request fit alone, but their holds cannot fit together.
        messages = [*MESSAGES, {"role": "user", "content": "word " * 1000}]
        class Paused:
            async def send(self, prepared, *, timeout):
                await asyncio.sleep(0.05)
                return response(text="done")
        first.adapter = Paused()
        second.adapter = Paused()
        async def run_both():
            return await asyncio.gather(first.run(messages), second.run(messages))
        results = asyncio.run(run_both())
        assert sorted(r["status"] for r in results) == ["completed", "root_money_budget_exhausted"]
        assert sum(r["model_calls"] for r in results) == 1
        assert RuntimeBudget.from_events(limits.ledger_limit(), store.all_events).ledger.charged.money_cny == Decimal("0.00018")
        store.validate()


@pytest.mark.parametrize("provider,model", [("glm-subscription", "glm-5.3-flash"),
    ("glm-subscription-anthropic", "glm-5.3-flash"), ("paratera", "GLM-5.3-Flash"), ("paratera", "unregistered")])
def test_incomplete_prices_or_subscription_are_rejected_before_credentials(provider, model):
    with pytest.raises(ValueError):
        require_cny_price_schedule(model, route_id=provider)


@pytest.mark.parametrize("tokens", ["omitted", None, 6_000_000])
def test_configuration_supports_explicit_cny_and_optional_tokens(tokens):
    case = json.loads((ROOT / "AI_agent/logs/experiments/2026-10-04_qwen27b_after_a2/configs/sm24_qwen27b_after_a2.json").read_bytes())["cases"][0]
    case["limits"]["money_cny"] = "12.5"
    if tokens == "omitted":
        del case["limits"]["tokens"]
    else:
        case["limits"]["tokens"] = tokens
    arguments = argv_for(case)[3:]
    args = parser().parse_args(arguments)
    assert args.money_cny == Decimal("12.5")
    assert args.tokens == (None if tokens == "omitted" else tokens)
    assert parser().parse_args(["--out", "unused", "--provider", "scripted"]).tokens == 5_000_000


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1", True])
def test_invalid_money_ceiling_is_rejected(amount):
    with pytest.raises(ValueError):
        validate_budget({"model": "Qwen3.8-27B", "provider": "paratera", "limits": {
            "model_calls": 2, "tool_calls": 2, "seconds": 100, "money_cny": amount}})


@pytest.mark.parametrize("reason", ["money_budget_exhausted", "root_money_budget_exhausted", "money_cny_usage_unavailable"])
def test_money_stop_delivers_latest_complete_instead_of_selected_partial(tmp_path, monkeypatch, reason):
    from src.agent.runtime_delivery import finalize_building
    from test_runtime_r3 import _build, _scenario
    actions = [_build(), _build("upstairs.png"), {"tool": "assemble_plan_bim"}, _build()]
    out, _, _, _ = asyncio.run(_scenario(tmp_path, monkeypatch, actions, model_calls=4))
    (out / "bim/delivery_selection.json").write_text('{"candidate":"candidate_04"}')
    result = finalize_building(out / "bim", reason=reason, elapsed_seconds=1)
    assert result["status"] == "delivered"
    assert result["delivery"]["candidate"] == "candidate_03"
    assert result["delivery"]["complete_building"] is True
    delivery = json.loads((out / "bim/delivery.json").read_bytes())
    assert delivery["generation_status"]["runtime_stop_reason"] == reason
    assert delivery["generation_status"]["agent_response_completed"] is False
