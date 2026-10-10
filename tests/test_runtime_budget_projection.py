"""Shared projection cache invalidation and mutable admission isolation."""
from decimal import Decimal

from src.agent_runtime.budget import RequestEstimate, RuntimeBudget
from src.agent_runtime.budget_projection import load_budget_projection
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, BudgetEventPayload, RunLifecyclePayload


def test_reuse_isolated_from_uncommitted_reserve_and_child_append(tmp_path, monkeypatch):
    limit = BudgetAmounts(tokens=1000, calls=10, seconds=Decimal(100))
    original = RuntimeBudget.from_events.__func__
    builds = []

    def tracked(cls, *args, **kwargs):
        builds.append(1)
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(RuntimeBudget, "from_events", classmethod(tracked))
    with EventStore(tmp_path, run_id="cache", task_id="root", budget_limit=limit) as store:
        root = load_budget_projection(store, limit)
        estimate = RequestEstimate.for_model_call(purpose="child_task", task_id="child",
            input_token_upper_bound=10, output_token_limit=10,
            seconds=Decimal(10), estimate_source="offline")
        decision = root.reserve("hold", estimate)
        assert root.available.tokens == 980
        # A failed append or abandoned admission cannot poison the next caller.
        assert load_budget_projection(store, limit).available == limit
        assert len(builds) == 1
        child = store.for_task("child", "root")
        child.append(RunLifecyclePayload(action="start", reason="offline"))
        assert load_budget_projection(child, limit).available == limit
        assert len(builds) == 1
        child.append(BudgetEventPayload(action="reserve", reservation=decision.reservation))
        assert load_budget_projection(store, limit).available.tokens == 980
        assert load_budget_projection(child, limit).available.tokens == 980
        assert len(builds) == 2
        assert load_budget_projection(store, limit, task_id="root").available == limit
        assert load_budget_projection(child, limit, task_id="child").available.tokens == 980
        assert len(builds) == 4


def test_cache_key_keeps_limit_and_policy_separate(tmp_path):
    total = BudgetAmounts(tokens=100, calls=10, seconds=Decimal(100))
    with EventStore(tmp_path, run_id="keys", task_id="root", budget_limit=total) as store:
        first = load_budget_projection(store, total, min_output_tokens=10)
        second = load_budget_projection(store, total, min_output_tokens=20,
            near_limit_policy="reduce_output")
        small = load_budget_projection(store, total.model_copy(update={"tokens": 50}))
        assert first.min_output_tokens == 10
        assert second.min_output_tokens == 20 and second.near_limit_policy == "reduce_output"
        assert small.available.tokens == 50 and first.available.tokens == 100
