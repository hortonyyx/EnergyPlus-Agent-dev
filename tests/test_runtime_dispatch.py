"""RT1 request admission, rejected usage and timing; no live services."""

import asyncio
import json

import httpx
import pytest

from src.agent_runtime.accounting import account_request_usage, get_cny_price_schedule
from src.agent_runtime.dispatch import DispatchPolicy, RouteDispatcher, get_dispatcher
from src.agent_runtime.failures import http_failure
from src.agent_runtime.loop import RunLimits
from src.harness_contracts import UsageMissing
from test_agent_runtime import MESSAGES, response, runtime


def policy(monkeypatch, **values):
    configured = {"offline": DispatchPolicy(**{
        "initial_concurrency": 5, "max_concurrency": 5,
        "cooldown_seconds": 0.001, "max_cooldown_seconds": 0.002,
        **values})}
    monkeypatch.setattr("src.agent_runtime.dispatch.route_policies", lambda: configured)
    monkeypatch.setattr("src.agent_runtime.loop.route_policies", lambda: configured)


def refused(usage=None):
    body = {"error": {"code": "1302"}, **({"usage": usage} if usage is not None else {})}
    return http_failure(httpx.Response(429, json=body),
                        secret="", provider="glm")


def test_six_runtimes_share_five_slots_and_preserve_wire_bytes(tmp_path, monkeypatch):
    policy(monkeypatch)

    async def run():
        active, peak, rejections = 0, 0, 0
        engines = []

        async def handler(request):
            nonlocal active, peak, rejections
            if active >= 5:
                rejections += 1
                return httpx.Response(429, json={"error": {"code": "1302"}})
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(0.03)
                return httpx.Response(200, json=response(text="done"))
            finally:
                active -= 1

        try:
            for i in range(6):
                directory = tmp_path / str(i)
                directory.mkdir()
                engine = runtime(directory, [])
                engine.adapter = HttpChatAdapterForTest(handler)
                engines.append(engine)
            results = await asyncio.gather(*(e.run(MESSAGES) for e in engines))
            assert rejections == 0 and peak == 5
            assert all(r["status"] == "completed" for r in results)
            assert any(r["timing"]["by_task"]["task"]["queue_seconds"] > 0.01 for r in results)
            wires = [e.adapter.sent[0] for e in engines]
            assert all(wire == wires[0] for wire in wires)
            # The unconfigured path emits exactly the same body.
            directory = tmp_path / "plain"
            directory.mkdir()
            plain = runtime(directory, [response(text="done")])
            plain.versions = plain.versions.model_copy(update={"remote_model":
                plain.versions.remote_model.model_copy(update={"route_id": "unconfigured"})})
            with plain.store:
                assert (await plain.run(MESSAGES))["status"] == "completed"
                assert plain.adapter.requests == [wires[0]]
            assert get_dispatcher("unconfigured") is None
            assert get_dispatcher("offline").in_flight == 0
        finally:
            for engine in engines:
                await engine.adapter.close()
                engine.store.close()

    asyncio.run(run())


class HttpChatAdapterForTest:
    def __init__(self, handler):
        from src.agent_runtime.adapter import HttpChatAdapter
        self.inner = HttpChatAdapter(base_url="https://open.bigmodel.cn/api/coding/paas/v4",
            api_key="offline", transport=httpx.MockTransport(handler))
        self.sent = []

    async def send(self, request, *, timeout):
        self.sent.append(request.wire_bytes)
        return await self.inner.send(request, timeout=timeout)

    async def close(self):
        await self.inner.close()


def test_reduction_priority_recovery_and_cancelled_waiters():
    async def run():
        now = [0.0]
        gate = RouteDispatcher("test", DispatchPolicy(3, 3, recovery_seconds=10,
            cooldown_seconds=1), clock=lambda: now[0])
        leases = [await gate.acquire(timeout=1) for _ in range(3)]
        normal = asyncio.create_task(gate.acquire(timeout=1))
        await asyncio.sleep(0)
        assert leases[2].rejected()["limit"] == 2
        leases[2].release()
        priority = asyncio.create_task(gate.acquire(timeout=1, redispatch_of="refused-request"))
        await asyncio.sleep(0)
        now[0] = 1.1
        leases[1].release()
        retried = await priority
        assert not normal.done()
        assert retried.succeeded() is None  # Quiet interval has not elapsed.
        now[0] = 12.0
        assert retried.succeeded()["limit"] == 3
        waiting = await normal
        for lease in (retried, waiting, leases[0]):
            lease.release()
        # A cancelled/expired waiter must never occupy the head or leak a slot.
        gate = RouteDispatcher("single", DispatchPolicy(1, 1))
        held = await gate.acquire(timeout=1)
        cancelled = asyncio.create_task(gate.acquire(timeout=1))
        await asyncio.sleep(0)
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        with pytest.raises(TimeoutError):
            await gate.acquire(timeout=0.001)
        held.release()
        final = await gate.acquire(timeout=0.1)
        final.release()
        assert gate.in_flight == 0 and not gate.queue and not gate.waiters

    asyncio.run(run())


def test_known_refusals_are_zero_even_with_images_but_unknown_usage_stays_unknown():
    pricing = get_cny_price_schedule("Qwen3.8-27B", route_id="paratera")
    accounting = account_request_usage(refused().usage, image_tokens_estimate=900, pricing=pricing)
    assert accounting.budget_charge_tokens == 0 and accounting.additional_image_tokens == 0
    assert accounting.estimated_cost_cny == 0 and accounting.cost_estimate_complete
    assert accounting.image_tokens_estimate == 900  # Keep the pre-send estimate as evidence.
    assert accounting.usage_basis == "rejected_before_processing"
    unknown = account_request_usage(UsageMissing(reason="network outcome unknown"),
        image_tokens_estimate=900, pricing=pricing)
    assert unknown.provider_reported_tokens is None and unknown.budget_charge_tokens is None
    for code in ("1308", "9999"):
        failure = http_failure(httpx.Response(429, json={"error": {"code": code}}), secret="", provider="glm")
        assert failure.usage.kind == "missing"
    reported = http_failure(httpx.Response(429, json={"error": {"code": "1302"},
        "usage": {"prompt_tokens": 5, "completion_tokens": 0}}), secret="", provider="glm")
    assert reported.usage.raw_usage == {"prompt_tokens": 5, "completion_tokens": 0}


@pytest.mark.parametrize("reported_zero", [False, True])
def test_refusals_do_not_spend_failure_retries_and_recovery_keeps_zero_charge(tmp_path, monkeypatch, reported_zero):
    from test_runtime_recovery_edges import InjectedCrash
    policy(monkeypatch)
    limits = RunLimits(model_calls=6, tool_calls=0, seconds=30, tokens=100000, max_model_retries=0)
    first = refused({"prompt_tokens": 0, "completion_tokens": 0} if reported_zero else None)
    engine = runtime(tmp_path, [first, refused(), response(text="done")], limits=limits)
    settle = engine._settle
    def crash(*args, **kwargs):
        if reported_zero:
            settle(*args, **kwargs)
        raise InjectedCrash()

    engine._settle = crash
    with engine.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(engine.run(MESSAGES))
    resumed = runtime(tmp_path, [refused(), response(text="done")], limits=limits, tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed" and result["retries"] == 0
        assert result["model_calls"] == 3 and result["usage_complete"]
        assert result["usage_accounting"]["provider_reported_tokens"] == 30
        assert result["usage_accounting"]["rejected_unprocessed_requests"] == 2 - int(reported_zero)
        assert result["timing"]["by_task"]["task"]["model_duration_complete"]
        requests = [e for e in resumed.store.events if e.payload.event_type == "adapter_request"]
        wires = [resumed.store.capture_bytes(e.payload.final_request_body) for e in requests]
        assert wires == [wires[0]] * 3
        resumed.store.validate()


def test_cancel_in_queue_sends_nothing_and_does_not_reserve_budget(tmp_path, monkeypatch):
    policy(monkeypatch, initial_concurrency=1, max_concurrency=1)
    engine = runtime(tmp_path, [response(text="not sent")])

    async def run():
        gate = get_dispatcher("offline")
        lease = await gate.acquire(timeout=1)
        task = asyncio.create_task(engine.run(MESSAGES))
        try:
            async with asyncio.timeout(5):
                while not gate.queue:
                    await asyncio.sleep(0.001)
            await asyncio.sleep(0.02)
            task.cancel()
            receipt = await task
            assert receipt["status"] == "cancelled" and receipt["model_calls"] == 0
            assert receipt["budget"]["reservations"] == []
            assert receipt["timing"]["by_task"]["task"]["queue_seconds"] > 0
            assert not engine.adapter.requests and not gate.queue
        finally:
            lease.release()

    with engine.store:
        asyncio.run(run())


def test_parent_timing_does_not_add_parallel_child_waits(tmp_path):
    from src.agent_runtime.loop import Runtime
    from src.agent_runtime.timing import project_saved_run
    from test_agent_runtime import Tools, role, versions
    limits = RunLimits(model_calls=10, tool_calls=5, seconds=60, tokens=100000)
    parent = runtime(tmp_path, [response(("children", "view", {})), response(text="done")], limits=limits)
    children = {}

    class WaitingAdapter:
        async def send(self, request, *, timeout):
            await asyncio.sleep(0.05)
            return response(text="child done")

    class ParentTools(Tools):
        async def call_tool(self, name, arguments):
            async def child(task_id):
                engine = Runtime(store=parent.store.for_task(task_id, parent_task_id="task"),
                    adapter=WaitingAdapter(), tools=Tools(tmp_path / task_id),
                    role=role(limits), model="test", parameters={"max_tokens": 256},
                    versions=versions(), limits=limits, request_timeout_seconds=1)
                children[task_id] = await engine.run(MESSAGES)
            await asyncio.gather(child("a"), child("b"))
            return {"content": [{"type": "text", "text": "children done"}]}

    parent.tools = ParentTools(tmp_path / "parent-tools")
    with parent.store:
        receipt = asyncio.run(parent.run(MESSAGES))
        assert receipt["status"] == "completed"
        timings = receipt["timing"]
        root = timings["by_task"]["task"]
        assert 0 < root["child_wait_seconds"] < sum(c["elapsed_seconds"] for c in children.values())
        assert root["tool_seconds"] + root["child_wait_seconds"] == pytest.approx(root["tool_inclusive_seconds"])
        latest = max(children, key=lambda task: children[task]["started_epoch"] + children[task]["elapsed_seconds"])
        assert timings["critical_path"]["last_child_task_id"] == latest
        assert timings["critical_path"]["root_tail_seconds"] >= 0
        assert all(row["model_duration_complete"] and row["queue_duration_complete"] and row["tool_duration_complete"]
                   for row in timings["by_task"].values())
    # Timing survives closing the writer; projection itself is read-only.
    projected = project_saved_run(parent.store.directory)
    assert projected["timing"]["critical_path"] == timings["critical_path"]
    assert projected["timing"]["by_task"]["task"]["child_wait_seconds"] == root["child_wait_seconds"]


@pytest.mark.parametrize("mixed", [False, True])
def test_redispatch_keeps_call_protection_and_failure_retry_history(tmp_path, monkeypatch, mixed):
    policy(monkeypatch)
    unavailable = http_failure(httpx.Response(503, json={"error": {"type": "overloaded"}}), secret="")
    values = [unavailable, refused(), unavailable] if mixed else [refused(), refused()]
    engine = runtime(tmp_path, values, limits=RunLimits(model_calls=5 if mixed else 2,
        tool_calls=0, seconds=30, tokens=100000, max_model_retries=1 if mixed else 0,
        retry_backoff_seconds=0))
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == ("model_retries_exhausted:service_unavailable" if mixed else "model_budget_exhausted")
        assert result["model_calls"] == len(values) and result["retries"] == int(mixed)
        assert result["usage_complete"] is not mixed
        engine.store.validate()


def test_budget_reprepare_preserves_wait_before_first_send(tmp_path, monkeypatch):
    policy(monkeypatch, initial_concurrency=1, max_concurrency=1)
    engine = runtime(tmp_path, [response(text="done")], limits=RunLimits(model_calls=2,
        tool_calls=0, seconds=30, tokens=100000, near_limit="reduce_output"))
    engine.parameters["max_tokens"] = 200000

    async def run():
        gate = get_dispatcher("offline")
        lease = await gate.acquire(timeout=1)
        task = asyncio.create_task(engine.run(MESSAGES))
        try:
            async with asyncio.timeout(5):
                while not gate.queue:
                    await asyncio.sleep(0.001)
            await asyncio.sleep(0.03)
        finally:
            lease.release()
        result = await task
        assert result["status"] == "completed" and result["model_calls"] == 1
        assert result["timing"]["by_task"]["task"]["queue_seconds"] > 0.01
        assert json.loads(engine.adapter.requests[0])["max_tokens"] < 200000

    with engine.store:
        asyncio.run(run())


def test_native_single_model_wire_unchanged_with_dispatch_enabled(tmp_path, monkeypatch):
    from test_runtime_anthropic import ROUTE, native_engine, native_response
    policies, wires = {}, []
    monkeypatch.setattr("src.agent_runtime.dispatch.route_policies", lambda: policies)
    monkeypatch.setattr("src.agent_runtime.loop.route_policies", lambda: policies)
    for enabled in (False, True):
        if enabled:
            policies[ROUTE] = DispatchPolicy(5, 8)
        path = tmp_path / str(enabled)
        path.mkdir()
        engine = native_engine(path, [native_response(("image", "view", {})), native_response(text="done")],
            limits=RunLimits(model_calls=3, tool_calls=2, seconds=30, tokens=500000))
        with engine.store:
            assert asyncio.run(engine.run(MESSAGES))["status"] == "completed"
            wires.append(engine.adapter.requests)
    assert wires[0] == wires[1] and len(wires[0]) == 2


def test_expired_run_reports_elapsed_time_beyond_deadline(tmp_path):
    import time
    engine = runtime(tmp_path, [], limits=RunLimits(model_calls=1, tool_calls=0,
                                                   seconds=1, tokens=100000))
    engine.start_epoch = time.time() - 2
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "time_budget_exhausted" and result["model_calls"] == 0
        assert result["elapsed_seconds"] >= 2
        assert result["timing"]["by_task"]["task"]["elapsed_seconds"] >= 2


def test_response_recovery_clears_old_redispatch_before_next_turn(tmp_path, monkeypatch):
    from test_runtime_recovery_edges import InjectedCrash
    policy(monkeypatch)
    engine = runtime(tmp_path, [refused()])
    def crash(*args, **kwargs):
        raise InjectedCrash()
    engine._settle = crash
    with engine.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(engine.run(MESSAGES))

    resumed = runtime(tmp_path, [response(("view-1", "view", {}))], tools=engine.tools)
    def checkpoint_then_crash(name, current):
        if name == "before_request":
            current._checkpoint()
        elif name == "after_response":
            raise InjectedCrash()
    resumed.fault_hook = checkpoint_then_crash
    with resumed.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(resumed.run(MESSAGES, resume=True))

    final = runtime(tmp_path, [response(text="done")], tools=engine.tools)
    with final.store:
        receipt = asyncio.run(final.run(MESSAGES, resume=True))
        assert receipt["status"] == "completed" and receipt["model_calls"] == 3
        assert receipt["retries"] == 0 and len(engine.tools.calls) == 1
        last = [e for e in final.store.events if e.payload.event_type == "adapter_request"][-1]
        assert final._redispatch_parent(last) is None
        final.store.validate()


def test_recovered_unknown_tool_does_not_turn_downtime_into_measured_tool_time(tmp_path):
    from test_runtime_recovery_edges import InjectedCrash
    engine = runtime(tmp_path, [response(("read", "view", {}))])
    def crash(name, current):
        if name == "after_tool":
            raise InjectedCrash()
    engine.fault_hook = crash
    with engine.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(engine.run(MESSAGES))
    resumed = runtime(tmp_path, [], tools=engine.tools)
    with resumed.store:
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert receipt["status"] == "resume_pending_operation" and len(engine.tools.calls) == 1
        row = receipt["timing"]["by_task"]["task"]
        assert row["tool_calls"] == 1 and not row["tool_duration_complete"]
