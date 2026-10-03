"""R2-C image-token, token-ledger, and CNY accounting checks."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.agent_runtime.accounting import (
    StoredRequestAccounting,
    account_request_usage,
    get_cny_price_schedule,
    summarize_request_accounting,
)
from src.agent_runtime.budget import RequestEstimate, RuntimeBudget
from src.agent_runtime.estimation import conservative_compatibility_profile, get_model_profile
from src.harness_contracts import (
    BudgetAmounts,
    BudgetLedger,
    BudgetReservation,
    BudgetSettlement,
    CostUnavailable,
    UsageMissing,
    UsageReported,
)


def test_qwen_breakdown_stays_reported_and_invoice_charges_images_again():
    pricing = get_cny_price_schedule("Qwen/Qwen3.8-27B", provider="paratera")
    result = account_request_usage(
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_tokens_details": {
                "cached_tokens": 10,
                "text_tokens": 70,
                "image_tokens": 30,
            },
        },
        image_tokens_estimate=30,
        pricing=pricing,
    )
    assert result.provider_reported_tokens == 120
    assert result.reported_image_tokens == 30
    assert result.image_tokens_estimate == 30
    assert result.reported_usage_includes_image_tokens is True
    assert result.budget_charge_tokens == 150
    assert result.additional_image_tokens == 30
    assert result.image_charge_source == "provider_reported"
    assert result.estimated_cost_cny == Decimal("0.000606")
    assert result.cost_estimate_complete is True
    assert "not bills" not in result.receipt_dict()["note"]


def test_glm_without_image_breakdown_adds_estimate_but_keeps_cost_incomplete():
    pricing = get_cny_price_schedule(
        "zai-org/GLM-5.3-Flash", route_id="paratera"
    )
    result = account_request_usage(
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        image_tokens_estimate=30,
        pricing=pricing,
    )
    assert result.provider_reported_tokens == 120
    assert result.reported_image_tokens is None
    assert result.reported_usage_includes_image_tokens is False
    assert result.budget_charge_tokens == 150
    assert result.estimated_cost_cny is None
    assert result.known_cost_components_cny == Decimal("0.000136")
    assert result.cost_estimate_complete is False
    assert result.image_billing_status == "unknown_until_a_glm_image_bill_is_observed"


def test_image_detail_without_an_exact_text_plus_image_sum_is_not_trusted():
    result = account_request_usage(
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_tokens_details": {"text_tokens": 50, "image_tokens": 30},
        },
        image_tokens_estimate=30,
        pricing=get_cny_price_schedule("Qwen3.8-27B", provider="paratera"),
    )
    assert result.reported_image_tokens == 30
    assert result.reported_usage_includes_image_tokens is False
    assert result.budget_charge_tokens == 150


def test_missing_usage_keeps_reported_and_budget_charge_unknown():
    result = account_request_usage(
        UsageMissing(reason="provider omitted usage"),
        image_tokens_estimate=66,
        pricing=get_cny_price_schedule("Qwen3.8-Flash", provider="paratera"),
    )
    assert result.provider_reported_tokens is None
    assert result.image_tokens_estimate == 66
    assert result.budget_charge_tokens is None
    assert result.estimated_cost_cny is None
    assert result.cost_estimate_complete is False


def test_request_estimate_exposes_image_subset_without_double_reserving():
    estimate = RequestEstimate.for_model_call(
        purpose="primary_task",
        task_id="root",
        input_token_upper_bound=100,
        image_input_tokens_estimate=30,
        output_token_limit=20,
        seconds=Decimal("5"),
        estimate_source="test estimate",
    )
    assert estimate.image_input_tokens_estimate == 30
    assert estimate.amounts.tokens == 120
    with pytest.raises(ValidationError, match="cannot exceed"):
        estimate.model_copy(
            update={"image_input_tokens_estimate": 101}
        ).__class__.model_validate(
            estimate.model_dump() | {"image_input_tokens_estimate": 101}
        )


def test_settlement_adds_unreported_image_estimate_to_effective_charge():
    reservation = BudgetReservation(
        reservation_id="request-1",
        purpose="primary_task",
        task_id="root",
        amounts=BudgetAmounts(tokens=100, calls=1),
    )
    settlement = BudgetSettlement(
        reservation_id="request-1",
        actual=BudgetAmounts(tokens=90, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 90}),
        cost=CostUnavailable(reason="no provider bill"),
        image_tokens_estimate=20,
        reported_usage_includes_image_tokens=False,
        token_overrun=10,
    )
    ledger = BudgetLedger(
        total_limit=BudgetAmounts(tokens=200, calls=2),
        reservations=(reservation,),
        settlements=(settlement,),
    )
    assert settlement.actual.tokens == 90
    assert settlement.effective_tokens == 110
    assert ledger.charged.tokens == 110
    assert ledger.available.tokens == 90


def test_runtime_settlement_preserves_raw_usage_and_charges_image_estimate():
    budget = RuntimeBudget(BudgetAmounts(tokens=200, calls=2))
    budget.reserve(
        "request-1",
        RequestEstimate.for_model_call(
            purpose="primary_task",
            task_id="root",
            input_token_upper_bound=100,
            image_input_tokens_estimate=20,
            output_token_limit=20,
            seconds=Decimal("5"),
            estimate_source="test estimate",
        ),
    )
    decision = budget.settle(
        "request-1",
        actual=BudgetAmounts(tokens=90, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 90}),
        image_tokens_estimate=20,
        reported_usage_includes_image_tokens=False,
    )
    assert decision.action == "allow"
    assert decision.settlement.actual.tokens == 90
    assert decision.settlement.image_tokens_estimate == 20
    assert budget.ledger.charged.tokens == 110


def test_reported_image_breakdown_is_not_charged_twice():
    reservation = BudgetReservation(
        reservation_id="request-1",
        purpose="primary_task",
        task_id="root",
        amounts=BudgetAmounts(tokens=120, calls=1),
    )
    settlement = BudgetSettlement(
        reservation_id="request-1",
        actual=BudgetAmounts(tokens=110, calls=1),
        usage=UsageReported(raw_usage={"total_tokens": 110}),
        cost=CostUnavailable(reason="no provider bill"),
        image_tokens_estimate=20,
        reported_usage_includes_image_tokens=True,
    )
    ledger = BudgetLedger(
        total_limit=BudgetAmounts(tokens=200, calls=2),
        reservations=(reservation,),
        settlements=(settlement,),
    )
    assert settlement.effective_tokens == 110
    assert ledger.charged.tokens == 110


def test_actual_tokens_cannot_replace_raw_provider_usage_with_an_estimate():
    with pytest.raises(ValidationError, match="preserve provider-reported"):
        BudgetSettlement(
            reservation_id="request-1",
            actual=BudgetAmounts(tokens=110, calls=1),
            usage=UsageReported(raw_usage={"total_tokens": 90}),
            cost=CostUnavailable(reason="no provider bill"),
            image_tokens_estimate=20,
        )


def test_model_profile_output_recommendations_and_unknown_defaults():
    assert get_model_profile("GLM-5.3-Flash").recommended_min_output_tokens == 32_000
    unknown = conservative_compatibility_profile("offline-fixture")
    assert unknown.recommended_min_output_tokens is None
    assert "unverified" in unknown.output_limit_source


def test_run_summary_keeps_models_and_child_tasks_separate():
    qwen = account_request_usage(
        {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        image_tokens_estimate=3,
        pricing=get_cny_price_schedule("Qwen3.8-27B", provider="paratera"),
    )
    glm = account_request_usage(
        {"prompt_tokens": 20, "completion_tokens": 4, "total_tokens": 24},
        image_tokens_estimate=0,
        pricing=get_cny_price_schedule("GLM-5.3-Flash", provider="paratera"),
    )
    summary = summarize_request_accounting(
        (
            StoredRequestAccounting("request-1", "root", "Qwen3.8-27B", "paratera", qwen),
            StoredRequestAccounting("request-2", "child-1", "GLM-5.3-Flash", "paratera", glm),
        )
    )
    assert summary["provider_reported_tokens"] == 36
    assert summary["image_tokens_estimate"] == 3
    assert summary["budget_charge_tokens"] == 39
    assert set(summary["by_model"]) == {"Qwen3.8-27B", "GLM-5.3-Flash"}
    assert summary["by_task"]["child-1"]["provider_reported_tokens"] == 24
