"""R1: shared accounting and failure isolation on the real batch dispatcher."""

import asyncio
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from src.agent.runtime_coordinator import CoordinatorSession, SerializedToolAccess
from src.agent.runtime_tools import FrozenBimTools, frozen_bim_client, local_observer_role
from src.agent_runtime.budget import RuntimeBudget
from src.agent_runtime.call_quota import QuotaAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.failures import ModelServiceError
from src.agent_runtime.store import EventStore
from src.harness_contracts import UsageMissing
from test_runtime_delegation import (
    ROOT, _CoordinatorTools, _MeasuringObserverFrozenTools, _answer, _application,
    _registered_view, _response,
)
from test_runtime_frozen_tools import _prepared_run


@pytest.fixture(autouse=True)
def controlled_time(monkeypatch):
    # These checks assert overlap, ordering and budgets, not real-time expiry.
    # Clock/timeout behaviour is exercised by the dedicated time-limit tests.
    import src.agent_runtime.loop as runtime_loop
    import src.agent.runtime_coordinator as coordinator
    import src.agent.runtime_delegation as delegation
    ticks = [0.0]
    def advance():
        ticks[0] += 0.001
    fixed = SimpleNamespace(time=lambda: 2_000_000_000.0 + ticks[0],
                            monotonic=lambda: 100.0 + ticks[0], advance=advance)
    for module in (runtime_loop, coordinator, delegation):
        monkeypatch.setattr(module, "time", fixed)

    async def without_wall_timeout(awaitable, timeout):
        return await awaitable

    monkeypatch.setattr(asyncio, "wait_for", without_wall_timeout)


def _task(name, *, tokens=100_000):
    return {"task_id": name, "question": "Describe the supplied crop.",
            "view_ids": ["view_0001"], "budget": {
                "model_calls": 2, "tool_calls": 2, "tokens": tokens, "seconds": 30}}


class OverlapAdapter:
    def __init__(self, activity, *, fail=False):
        self.activity, self.fail = activity, fail

    async def send(self, prepared, *, timeout):
        self.activity["active"] += 1
        self.activity["peak"] = max(self.activity["peak"], self.activity["active"])
        # Yield by event-loop order, independent of elapsed wall time.
        release = self.activity.setdefault("release", asyncio.Event())
        if self.activity["active"] == self.activity.get("expected_overlap", 1):
            release.set()
        await release.wait()
        import src.agent_runtime.loop as runtime_loop
        runtime_loop.time.advance()
        self.activity["active"] -= 1
        if self.fail:
            # This fixture isolates a permanent child failure. Transient model
            # faults now retry by default and have their own C1 coverage.
            raise ModelServiceError({"category": "permission_denied", "retryable": False,
                "http_status": 403, "usage_received": False}, UsageMissing(reason="injected child failure"))
        return _response(text=_answer())


def _setup(tmp_path, store, limits, factory, concurrency):
    run = tmp_path / "bim"
    run.mkdir()
    (run / "inputs.json").write_text('{"revision": 1}')
    session = CoordinatorSession(store=store, tools=_CoordinatorTools(run),
        observer_tools=_MeasuringObserverFrozenTools(run), adapter_factory=factory,
        model="test", parameters={"max_tokens": 4096}, root=ROOT,
        limits=limits, max_concurrent_observers=concurrency)
    session.views["view_0001"] = _registered_view(store)
    return session


@pytest.mark.parametrize("concurrency, expected_peak", [(4, 3), (1, 1)])
def test_batch_isolates_failure_and_child_budget_and_counts_every_attempt(tmp_path, concurrency, expected_peak):
    async def scenario():
        limits = RunLimits(model_calls=8, tool_calls=8, tokens=400_000, seconds=300)
        activity = {"active": 0, "peak": 0, "expected_overlap": expected_peak}
        quota = tmp_path / "quota.jsonl"
        with EventStore(tmp_path / "audit", run_id="parallel-test", task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            factory = lambda task: QuotaAdapter(OverlapAdapter(activity, fail=task == "failure"),
                quota, limit=3, category="offline-r1")
            session = _setup(tmp_path, store, limits, factory, concurrency)
            await session.initialize()
            tasks = [_task("good-a"), _task("over-budget", tokens=1),
                     _task("failure"), _task("good-b")]
            result = await session.call_tool("delegate_to_roles", {"tasks": tasks})
            assert not result["isError"]
            rows = result["structuredContent"]["results"]
            assert [r["status"] for r in rows] == [
                "completed", "child_token_budget_exhausted", "permission_denied", "completed"]
            assert activity["peak"] == expected_peak
            assert [r["package"]["task_id"] for r in rows] == [t["task_id"] for t in tasks]
            ledger = RuntimeBudget.from_events(store.budget_limit, store.all_events).ledger
            assert len(ledger.reservations) == len(ledger.settlements) == 3
            assert len({r.reservation_id for r in ledger.reservations}) == 3
            assert ledger.committed.tokens <= limits.tokens
            assert ledger.committed.calls == 3
            last_stop = next(e for e in reversed(store.all_events)
                if e.payload.event_type == "run_lifecycle" and e.payload.action == "stop")
            receipt_source = next(ref for ref in last_stop.source_refs if ref.source_id == "run-receipt")
            final_receipt = json.loads(store.get_bytes(receipt_source.blob))
            assert final_receipt["root_budget_available"] == ledger.available.model_dump(mode="json")
            assert len([e for e in store.all_events if e.payload.event_type == "adapter_request"]) == 3
            assert store.validate().events == tuple(store.all_events)
            before = len([e for e in store.all_events if e.payload.event_type == "adapter_request"])
            reused = await session.call_tool("delegate_to_roles", {"tasks": tasks})
            assert all(r["reused_saved_result"] for r in reused["structuredContent"]["results"])
            assert len([e for e in store.all_events if e.payload.event_type == "adapter_request"]) == before
        tickets = [json.loads(line) for line in quota.read_text().splitlines()]
        assert [r["ticket"] for r in tickets if r["event"] == "attempt"] == [1, 2, 3]
        assert len([r for r in tickets if r["event"] == "failure"]) == 1
        assert len([r for r in tickets if r["event"] == "response"]) == 2
    asyncio.run(scenario())


def test_parallel_results_are_rechecked_against_saved_version_before_application(tmp_path):
    async def scenario():
        limits = RunLimits(model_calls=4, tool_calls=4, tokens=400_000, seconds=300)
        activity = {"active": 0, "peak": 0, "expected_overlap": 2}
        with EventStore(tmp_path / "audit", run_id="version-test", task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            session = _setup(tmp_path, store, limits, lambda task: OverlapAdapter(activity), 4)
            await session.initialize()
            reply = await session.call_tool("delegate_to_roles", {"tasks": [_task("east"), _task("west")]})
            assert all(row["status"] == "completed" for row in reply["structuredContent"]["results"])
            assert session.inspect("west")["applicable"]
            (tmp_path / "bim/inputs.json").write_text('{"revision": 2}')
            rejected = await session.call_tool("apply_local_observation", _application("west"))
            assert rejected["isError"]
            assert "stale source model version" in rejected["structuredContent"]["reason"]
            assert session.tools.calls == []
            store.validate()
    asyncio.run(scenario())


def test_duplicate_batch_identity_is_rejected_before_any_child_request(tmp_path):
    async def scenario():
        limits = RunLimits(model_calls=4, tool_calls=4, tokens=400_000, seconds=300)
        with EventStore(tmp_path / "audit", run_id="duplicate-test", task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            session = _setup(tmp_path, store, limits, lambda task: None, 4)
            await session.initialize()
            reply = await session.call_tool("delegate_to_roles", {"tasks": [_task("same"), _task("same")]})
            assert reply["isError"]
            assert not [e for e in store.all_events if e.payload.event_type == "adapter_request"]
    asyncio.run(scenario())


def test_parallel_batch_preserves_root_request_cap(tmp_path):
    async def scenario():
        limits = RunLimits(model_calls=2, tool_calls=4, tokens=400_000, seconds=300)
        activity = {"active": 0, "peak": 0, "expected_overlap": 2}
        with EventStore(tmp_path / "audit", run_id="root-cap-test", task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            session = _setup(tmp_path, store, limits, lambda task: OverlapAdapter(activity), 4)
            await session.initialize()
            reply = await session.call_tool("delegate_to_roles", {"tasks": [_task(f"child-{i}") for i in range(4)]})
            statuses = [row["status"] for row in reply["structuredContent"]["results"]]
            assert statuses.count("completed") == 2
            assert statuses.count("root_model_budget_exhausted") == 2
            ledger = RuntimeBudget.from_events(store.budget_limit, store.all_events).ledger
            assert ledger.committed.calls == 2
            store.validate()
    asyncio.run(scenario())


def test_real_frozen_service_serializes_concurrent_views_without_mixing_results(tmp_path):
    async def scenario():
        run = _prepared_run(tmp_path)
        async with frozen_bim_client(run, readonly=True, repository_root=ROOT) as client:
            limits = RunLimits(model_calls=4, tool_calls=4, seconds=60, tokens=100_000)
            original = FrozenBimTools(client, local_observer_role(limits.ledger_limit()), run_directory=run)
            tools = SerializedToolAccess(original, asyncio.Lock())
            boxes = [[1, 1, 5, 5], [2, 2, 8, 6], [3, 1, 10, 7], [0, 0, 12, 8]]
            results = await asyncio.gather(*(tools.call_tool("view_image", {
                "name": "plan.png", "box": box, "coordinate_grid": False}) for box in boxes))
            for reply, box in zip(results, boxes, strict=True):
                assert not reply["isError"]
                origin = next(iter(tools.image_origins(reply).values()))
                assert origin["box_original_pixels"] == box
                assert Path(origin["original_path"]) == run / "images" / "plan.png"
    asyncio.run(scenario())
