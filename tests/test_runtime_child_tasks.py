"""Task-scoped runtime checks over one durable root-run journal."""

from __future__ import annotations

import asyncio

import pytest

from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.budget import RuntimeBudget
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.harness_contracts import KnownParentTask, RunLifecyclePayload

from test_agent_runtime import MESSAGES, Tools, response, role, versions


def _limits(*, model_calls=2, tool_calls=2, tokens=100_000):
    return RunLimits(
        model_calls=model_calls,
        tool_calls=tool_calls,
        seconds=30.0,
        tokens=tokens,
    )


def _child(root, tmp_path, task_id, responses, *, limits=None, tools=None):
    limits = limits or _limits()
    store = root.for_task(task_id, parent_task_id=root.task_id)
    return Runtime(
        store=store,
        adapter=ScriptedAdapter(responses),
        tools=tools or Tools(tmp_path / f"tools-{task_id}"),
        role=role(limits, readonly=True),
        model="test",
        parameters={"max_tokens": 256, "temperature": 0.0},
        versions=versions(),
        limits=limits,
    )


def test_two_child_tasks_share_root_ledger_but_keep_task_views_and_receipts(tmp_path):
    root_limits = _limits(model_calls=3, tool_calls=4, tokens=200_000)
    with EventStore(
        tmp_path / "run",
        run_id="run-children",
        task_id="coordinator",
        budget_limit=root_limits.ledger_limit(),
    ) as root:
        root.append(RunLifecyclePayload(action="start", reason="coordinator started"))
        first = _child(root, tmp_path, "observe-east", [response(text="east")])
        second = _child(root, tmp_path, "observe-west", [response(text="west")])

        assert first.store.next_reservation_id() == "observe-east:request-1"
        assert asyncio.run(first.run(MESSAGES))["status"] == "completed"
        assert asyncio.run(second.run(MESSAGES))["status"] == "completed"

        assert {event.task_id for event in root.all_events} == {
            "coordinator",
            "observe-east",
            "observe-west",
        }
        assert {event.task_id for event in first.store.events} == {"observe-east"}
        assert {event.task_id for event in second.store.events} == {"observe-west"}
        assert all(
            event.parent_task.kind == "known"
            and event.parent_task.task_id == "coordinator"
            for event in first.store.events + second.store.events
        )
        reservations = RuntimeBudget.from_events(
            root.budget_limit, root.all_events
        ).ledger.reservations
        assert [(item.reservation_id, item.purpose, item.task_id) for item in reservations] == [
            ("observe-east:request-1", "child_task", "observe-east"),
            ("observe-west:request-1", "child_task", "observe-west"),
        ]
        assert first.store.task_directory != second.store.task_directory
        assert (first.store.task_directory / "receipt.json").exists()
        assert (second.store.task_directory / "receipt.json").exists()
        assert root.validate().events == tuple(root.all_events)


def test_child_limit_cannot_borrow_unused_root_budget(tmp_path):
    root_limits = _limits(model_calls=5, tokens=500_000)
    child_limits = _limits(model_calls=2, tokens=1)
    with EventStore(
        tmp_path / "run",
        run_id="run-child-cap",
        task_id="coordinator",
        budget_limit=root_limits.ledger_limit(),
    ) as root:
        engine = _child(
            root, tmp_path, "tiny-child", [], limits=child_limits
        )
        receipt = asyncio.run(engine.run(MESSAGES))

        assert receipt["status"] == "child_token_budget_exhausted"
        assert receipt["model_calls"] == 0
        assert receipt["root_budget_available"]["tokens"] == root_limits.tokens
        assert not [
            event for event in root.all_events
            if event.payload.event_type == "budget"
        ]


def test_exhausted_root_budget_stops_a_later_child_with_explicit_scope(tmp_path):
    root_limits = _limits(model_calls=1, tokens=200_000)
    with EventStore(
        tmp_path / "run",
        run_id="run-root-cap",
        task_id="coordinator",
        budget_limit=root_limits.ledger_limit(),
    ) as root:
        first = _child(root, tmp_path, "first", [response(text="done")])
        second = _child(root, tmp_path, "second", [])

        assert asyncio.run(first.run(MESSAGES))["status"] == "completed"
        receipt = asyncio.run(second.run(MESSAGES))

        assert receipt["status"] == "root_model_budget_exhausted"
        assert receipt["model_calls"] == 0
        reservations = [
            event for event in root.all_events
            if event.payload.event_type == "budget"
            and event.payload.action == "reserve"
        ]
        assert len(reservations) == 1


def test_child_primary_and_retry_keep_distinct_root_ledger_purposes(tmp_path):
    root_limits = _limits(model_calls=4, tokens=200_000)
    child_limits = _limits(model_calls=3).model_copy(
        update={"max_model_retries": 1}
    )
    with EventStore(
        tmp_path / "run",
        run_id="run-child-retry",
        task_id="coordinator",
        budget_limit=root_limits.ledger_limit(),
    ) as root:
        engine = _child(
            root,
            tmp_path,
            "retry-child",
            [ConnectionError("offline"), response(text="recovered")],
            limits=child_limits,
        )
        receipt = asyncio.run(engine.run(MESSAGES))

        assert receipt["status"] == "completed"
        reservations = RuntimeBudget.from_events(
            root.budget_limit, root.all_events
        ).ledger.reservations
        assert [item.purpose for item in reservations] == ["child_task", "retry"]
        assert [item.reservation_id for item in reservations] == [
            "retry-child:request-1",
            "retry-child:request-2",
        ]


def test_child_recovery_replays_durable_response_without_second_request(tmp_path):
    class Crash(BaseException):
        pass

    limits = _limits(model_calls=2)
    tools = Tools(tmp_path / "tools-recovery")
    with EventStore(
        tmp_path / "run",
        run_id="run-child-recovery",
        task_id="coordinator",
        budget_limit=_limits(model_calls=4).ledger_limit(),
    ) as root:
        engine = _child(
            root, tmp_path, "recover-child", [response(text="durable")],
            limits=limits, tools=tools,
        )

        def fail_after_response(boundary, _engine):
            if boundary == "after_response":
                raise Crash()

        engine.fault_hook = fail_after_response
        with pytest.raises(Crash):
            asyncio.run(engine.run(MESSAGES))
        before = len([
            event for event in engine.store.events
            if event.payload.event_type == "adapter_request"
        ])

        resumed = _child(
            root, tmp_path, "recover-child", [], limits=limits, tools=tools
        )
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))

        assert receipt["status"] == "completed"
        assert resumed.adapter.requests == []
        assert before == 1
        assert len([
            event for event in resumed.store.events
            if event.payload.event_type == "adapter_request"
        ]) == 1
        assert len([
            event for event in resumed.store.events
            if event.payload.event_type == "budget"
            and event.payload.action == "reserve"
        ]) == 1


def test_task_ancestry_survives_reopen_and_rejects_missing_or_changed_parent(tmp_path):
    directory = tmp_path / "run"
    limits = _limits(model_calls=3)
    with EventStore(
        directory,
        run_id="run-ancestry",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as root:
        parent = root.for_task("parent", parent_task_id="coordinator")
        parent.append(RunLifecyclePayload(action="start", reason="parent started"))
        nested = root.for_task("nested", parent_task_id="parent")
        nested.append(RunLifecyclePayload(action="start", reason="nested started"))
        with pytest.raises(ValueError, match="does not exist"):
            root.for_task("orphan", parent_task_id="missing")
        with pytest.raises(ValueError, match="persisted ancestry"):
            root.for_task("nested", parent_task_id="coordinator")

    with EventStore(
        directory,
        run_id="run-ancestry",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as reopened:
        nested = reopened.for_task("nested", parent_task_id="parent")
        assert len(nested.events) == 1
        assert nested.events[0].parent_task.task_id == "parent"
        assert reopened.validate().events == tuple(reopened.all_events)


def test_reopen_rejects_a_persisted_task_parent_cycle(tmp_path):
    directory = tmp_path / "run"
    limits = _limits(model_calls=3)
    with EventStore(
        directory,
        run_id="run-cycle",
        task_id="coordinator",
        budget_limit=limits.ledger_limit(),
    ) as root:
        parent = root.for_task("parent", parent_task_id="coordinator")
        parent.append(RunLifecyclePayload(action="start", reason="parent started"))
        nested = root.for_task("nested", parent_task_id="parent")
        nested.append(RunLifecyclePayload(action="start", reason="nested started"))

    path = directory / "events.jsonl"
    events = EventStore.read_events(path)
    events[0] = events[0].model_copy(
        update={"parent_task": KnownParentTask(task_id="nested")}
    )
    path.write_text(
        "".join(event.model_dump_json() + "\n" for event in events),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cycle"):
        EventStore(
            directory,
            run_id="run-cycle",
            task_id="coordinator",
            budget_limit=limits.ledger_limit(),
        )


def test_child_read_only_role_is_enforced_before_any_tool_runs(tmp_path):
    with EventStore(
        tmp_path / "run",
        run_id="run-read-only",
        task_id="coordinator",
        budget_limit=_limits(model_calls=2).ledger_limit(),
    ) as root:
        engine = _child(
            root,
            tmp_path,
            "observer",
            [response(("write", "save", {"value": 7}))],
        )
        receipt = asyncio.run(engine.run(MESSAGES))

        assert receipt["status"] == "tool_authorization_failed"
        assert engine.tools.calls == []
        assert not list((tmp_path / "tools-observer").glob("*.json"))
