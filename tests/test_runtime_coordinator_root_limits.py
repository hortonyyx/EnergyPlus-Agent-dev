"""Red-line checks for coordinator-wide tool and wall-clock limits."""

from __future__ import annotations

import asyncio
import pytest

from src.agent import runtime_coordinator
from src.agent.runtime_coordinator import CoordinatorSession
from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore

from test_runtime_delegation import (
    ROOT,
    _CoordinatorTools,
    _MeasuringObserverFrozenTools,
    _answer,
    _profile_call,
    _registered_view,
    _response,
)
from test_agent_runtime import MESSAGES, response
from test_runtime_child_tasks import _child


def _store(tmp_path, limits):
    return EventStore(
        tmp_path / "audit",
        run_id="coordinator-root-limits",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    )


def _inputs(tmp_path):
    run_directory = tmp_path / "bim"
    run_directory.mkdir()
    (run_directory / "inputs.json").write_text('{"revision": 1}', encoding="utf-8")
    return run_directory


def _session(store, coordinator_tools, observer_tools, adapter, limits):
    return CoordinatorSession(
        store=store,
        tools=coordinator_tools,
        observer_tools=observer_tools,
        adapter_factory=lambda _task_id: adapter,
        model="test",
        parameters={"max_tokens": 4096, "temperature": 0.0},
        root=ROOT,
        route_id="offline-test",
        limits=limits,
    )


def test_child_model_may_answer_but_child_tool_cannot_exceed_root_tool_cap(tmp_path):
    limits = RunLimits(
        model_calls=4,
        tool_calls=1,
        seconds=120.0,
        tokens=300_000,
    )
    coordinator_tools = _CoordinatorTools(_inputs(tmp_path))
    observer_tools = _MeasuringObserverFrozenTools(tmp_path / "observer-tools")
    adapter = ScriptedAdapter([
        _response(calls=(_profile_call("profile-after-root-cap"),)),
        _response(text=_answer()),
    ])

    with _store(tmp_path, limits) as store:
        session = _session(store, coordinator_tools, observer_tools, adapter, limits)
        asyncio.run(session.initialize())
        view = _registered_view(store)
        session.views[view.view_id] = view

        consumed = asyncio.run(session.call_tool(
            "revise_bim", {"revision_note": "Consume the one root tool allowance."}
        ))
        assert consumed["isError"] is False

        delegated = asyncio.run(session.call_tool("delegate_to_role", {
            "task_id": "observer-after-root-cap",
            "question": "Use the supplied view only if a root tool allowance remains.",
            "view_ids": [view.view_id],
            "budget": {
                "model_calls": 2,
                "tool_calls": 2,
                "tokens": 100_000,
                "seconds": 60,
            },
        }))

        # The first child request is allowed: a direct answer would consume no
        # tool. Its requested tool must stop before the backing client runs.
        assert delegated["isError"] is False
        assert delegated["structuredContent"]["status"] == "root_tool_budget_exhausted"
        assert len(adapter.requests) == 1
        assert observer_tools.calls == []
        invocations = [
            event
            for event in store.all_events
            if event.payload.event_type == "tool_invocation"
        ]
        assert len(invocations) == 1
        assert invocations[0].task_id == "coordinator"


def test_frozen_write_uses_root_deadline_and_restores_unknown_without_replay(
    tmp_path, monkeypatch
):
    limits = RunLimits(
        model_calls=2,
        tool_calls=2,
        seconds=1.0,
        tokens=100_000,
    )
    monkeypatch.setattr(runtime_coordinator.time, "time", lambda: 100.0)
    coordinator_tools = _CoordinatorTools(_inputs(tmp_path))

    with _store(tmp_path, limits) as store:
        session = _session(
            store,
            coordinator_tools,
            _MeasuringObserverFrozenTools(tmp_path / "observer-tools"),
            ScriptedAdapter([]),
            limits,
        )
        asyncio.run(session.initialize())
        monkeypatch.setattr(runtime_coordinator.time, "time", lambda: 100.25)
        admitted_timeouts = []

        async def cross_deadline(awaitable, timeout):
            admitted_timeouts.append(timeout)
            # The backing write completed at the boundary, but the coordinator
            # did not receive a result before its own deadline. Treating that
            # application as known would be unsafe.
            await awaitable
            raise TimeoutError("deterministic root deadline")

        monkeypatch.setattr(runtime_coordinator.asyncio, "wait_for", cross_deadline)
        first = asyncio.run(session.call_tool(
            "revise_bim", {"revision_note": "Cross the root deadline."}
        ))

        assert admitted_timeouts == [0.75]
        assert first["isError"] is True
        assert first["structuredContent"]["status"] == "unknown_write_outcome"
        assert len(coordinator_tools.calls) == 1
        executions = [
            event.payload
            for event in store.events
            if event.payload.event_type == "tool_execution"
        ]
        assert len(executions) == 1
        assert executions[0].outcome == "unknown"
        inspections = [
            event.payload
            for event in store.events
            if event.payload.event_type == "state_inspection"
        ]
        assert len(inspections) == 1
        assert inspections[0].purpose == "unknown_write_recovery"
        assert inspections[0].conclusion == "inconclusive"

        restored = _session(
            store,
            coordinator_tools,
            _MeasuringObserverFrozenTools(tmp_path / "restored-observer-tools"),
            ScriptedAdapter([]),
            limits,
        )
        asyncio.run(restored.initialize())
        repeated = asyncio.run(restored.call_tool(
            "revise_bim", {"revision_note": "Cross the root deadline."}
        ))

        assert repeated["isError"] is True
        assert repeated["structuredContent"]["status"] == "rejected"
        assert "unknown write outcome" in repeated["structuredContent"]["reason"]
        assert len(coordinator_tools.calls) == 1
        assert len([
            event
            for event in store.events
            if event.payload.event_type == "tool_invocation"
        ]) == 1


def test_resumed_child_rechecks_root_tool_allowance_before_pending_execution(tmp_path):
    class Crash(BaseException):
        pass

    limits = RunLimits(model_calls=6, tool_calls=1, seconds=120, tokens=300_000)
    with _store(tmp_path, limits) as store:
        child = _child(store, tmp_path, "interrupted", [response(("pending", "view", {}))])
        child.root_tool_calls = 1

        def interrupt(boundary, _engine):
            if boundary == "before_tool":
                raise Crash()

        child.fault_hook = interrupt
        with pytest.raises(Crash):
            asyncio.run(child.run(MESSAGES))
        assert child.tools.calls == []

        other = _child(store, tmp_path, "other", [response(("consume", "view", {})), response(text="done")])
        other.root_tool_calls = 1
        assert asyncio.run(other.run(MESSAGES))["status"] == "completed"

        resumed = _child(store, tmp_path, "interrupted", [], tools=child.tools)
        resumed.root_tool_calls = 1
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert receipt["status"] == "root_tool_budget_exhausted"
        assert resumed.tools.calls == []
        assert resumed.adapter.requests == []
        assert sum(e.payload.event_type == "tool_invocation" for e in store.all_events) == 1
