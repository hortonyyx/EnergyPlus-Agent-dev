"""Invoice-level regressions, including an image detail differing from the formula."""

from decimal import Decimal
import asyncio
from pathlib import Path
import runpy

import pytest

from src.agent_runtime.accounting import account_request_usage, get_cny_price_schedule
from src.agent_runtime.budget import RequestEstimate, RuntimeBudget
from src.harness_contracts import BudgetAmounts, UsageReported
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from test_agent_runtime import MESSAGES, response, runtime
from test_runtime_child_tasks import _child


@pytest.mark.parametrize("model,expected", [("Qwen3.8-27B", "0.000633"), ("Qwen3.8-Flash", "0.000190")])
def test_invoice_uses_provider_image_detail_before_formula(model, expected):
    raw = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120,
           "prompt_tokens_details": {"text_tokens": 61, "image_tokens": 39, "cached_tokens": 10}}
    account = account_request_usage(raw, image_tokens_estimate=30,
        pricing=get_cny_price_schedule(model, provider="paratera"))
    assert account.provider_reported_tokens == 120 and account.budget_charge_tokens == 159
    assert account.additional_image_tokens == 39 and account.image_charge_source == "provider_reported"
    assert account.estimated_cost_cny == Decimal(expected)
    budget = RuntimeBudget(BudgetAmounts(tokens=200, calls=2))
    estimate = RequestEstimate.for_model_call(purpose="child_task", task_id="child",
        input_token_upper_bound=100, image_input_tokens_estimate=30, additional_image_tokens_estimate=30,
        output_token_limit=20, seconds=Decimal(5), estimate_source="invoice-aware estimate")
    assert estimate.amounts.tokens == 150
    budget.reserve("image", estimate)
    settled = budget.settle("image", actual=BudgetAmounts(tokens=120, calls=1), usage=UsageReported(raw_usage=raw),
        image_tokens_estimate=30, reported_usage_includes_image_tokens=True,
        additional_image_tokens=account.additional_image_tokens)
    assert settled.settlement.token_overrun == 9
    assert settled.settlement.actual.tokens == 120 and budget.ledger.charged.tokens == 159
    assert budget.available.tokens == 41


def test_separate_image_reservation_prevents_overspending_and_survives_reduction():
    estimate = RequestEstimate.for_model_call(purpose="primary_task", task_id="root",
        input_token_upper_bound=100, image_input_tokens_estimate=30, additional_image_tokens_estimate=30,
        output_token_limit=20, seconds=Decimal(5), estimate_source="invoice-aware estimate")
    budget = RuntimeBudget(BudgetAmounts(tokens=140, calls=1))
    assert budget.reserve("image", estimate).action == "stop"
    assert estimate.with_output_token_limit(5, None).amounts.tokens == 135


def test_missing_image_detail_remains_formula_estimate():
    account = account_request_usage({"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        image_tokens_estimate=30, pricing=get_cny_price_schedule("Qwen3.8-27B", provider="paratera"))
    assert account.image_charge_source == "formula_estimate"
    assert account.budget_charge_tokens == 150
    assert account.estimated_cost_cny == Decimal("0.00063")


def test_nine_real_responses_match_all_three_invoice_lines():
    root = Path(__file__).resolve().parents[1]
    script = root / "AI_agent/logs/experiments/2026-10-03_runtime_r2/r2bc/reconcile_billing.py"
    report = runpy.run_path(str(script))["reconcile"]()
    assert report["provider_reported_tokens"] == 126977
    assert report["budget_charge_tokens"] == 138045
    assert report["unrounded_cny"] == "0.926694"
    assert report["invoice_total_cny"] == "0.92669"
    assert all(line["token_error"] == 0 and line["cny_error"] == "0" for line in report["invoice_lines"])


@pytest.mark.parametrize("child", [False, True])
def test_actual_image_request_charges_task_and_root_and_rebuilds_after_restart(tmp_path, child):
    image_response = response(text="OK")
    image_response["usage"] = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120,
        "prompt_tokens_details": {"text_tokens": 34, "image_tokens": 66}}
    replies = [response(("view", "view", {})), image_response]
    root_limits = RunLimits(model_calls=4, tool_calls=5, seconds=30, tokens=200000)
    parent = EventStore(tmp_path / "parent", run_id="parent", task_id="root", budget_limit=root_limits.ledger_limit())
    with parent:
        engine = _child(parent, tmp_path, "child", replies) if child else runtime(tmp_path, replies)
        engine.model = "Qwen3.8-27B"
        engine.parameters["max_tokens"] = 16384
        engine.versions = engine.versions.model_copy(update={"remote_model":
            engine.versions.remote_model.model_copy(update={"route_id": "paratera", "remote_alias": engine.model})})
        with engine.store:
            receipt = asyncio.run(engine.run(MESSAGES))
            assert receipt["status"] == "completed"
            assert receipt["reported_tokens"] == 150
            assert receipt["usage_accounting"]["budget_charge_tokens"] == 216
            assert engine.budget.ledger.charged.tokens == 216
            assert engine.task_budget.ledger.charged.tokens == 216
            rebuilt = RuntimeBudget.from_events(engine.store.budget_limit, engine.store.all_events)
            assert rebuilt.ledger.charged.tokens == 216
            assert rebuilt.ledger.settlements[-1].actual.tokens == 120
            assert rebuilt.ledger.settlements[-1].additional_image_tokens == 66
            engine.store.validate()
