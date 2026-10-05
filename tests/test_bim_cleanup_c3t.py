"""C3-T real saves and failed/partial application; strictly offline."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.tool_scripts.bim_agent_saved_result import read_saved_result, result_metadata
from src.agent.runtime_context import update_building_context
from src.agent.runtime_coordinator import CoordinatorSession
from src.agent.runtime_behaviour import summarise
from src.agent_runtime.context import ContextManager, ContextPolicy
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts
from tests.test_bim_absorb_a5t import server
from tests.test_bim_claims import setup_run, claim, edit
from tests.test_source_proposal import _proposal


class LocalTools:
    def __init__(self, run):
        self.run_directory = run
        self.api = server(run)
        self.calls = []

    def repeatability(self, name):
        return "non_idempotent_write"

    def snapshot_state(self):
        return {"candidates": sorted(p.name for p in self.run_directory.glob("candidate_*"))}

    async def call_tool(self, name, arguments):
        self.calls.append(name)
        value = await self.api.call_tool(name, arguments)
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, tuple):
            return dict(content=[v.model_dump(mode="json") for v in value[0]], structuredContent=value[1])
        return dict(content=[v.model_dump(mode="json") for v in value])

    def image_origins(self, raw):
        return {}


def coordinator(store, tools):
    return CoordinatorSession(store=store, tools=tools, observer_tools=tools,
        adapter_factory=lambda _: pytest.fail("no model request"), model="offline", parameters={})


@pytest.mark.parametrize("outcome", ["completed", "failed", "partial"])
def test_transaction_current_source_effects_and_recovery(tmp_path, outcome):
    run, toolkit = setup_run(tmp_path)
    first = toolkit.build(_proposal())["saved_candidate"]
    valid = dict(claim=claim(candidate=first), action="apply", operations=[edit("$claim")])
    invalid = dict(claim={}, action="apply")
    entries = {"completed": [valid], "failed": [invalid], "partial": [valid, invalid]}[outcome]
    tools = LocalTools(run)
    with EventStore(tmp_path / "audit", run_id="c3t", task_id="root",
                    budget_limit=BudgetAmounts(tokens=1000, calls=10)) as store:
        session = coordinator(store, tools)
        context = ContextManager(store, policy=ContextPolicy(compact_at_tokens=400))
        engine = SimpleNamespace(tools=tools, store=store, context=context,
                                 _event_source=lambda e: store.source("tool-result", {}).model_copy(update={"event_id": e.event_id}))
        # Seed a real prior current state; this is the regression missed by the
        # old fallback-to-latest-files logic.
        before = SimpleNamespace(payload=SimpleNamespace(tool_name="build_bim"), event_id=None)
        update_building_context(engine, before, {"structuredContent": toolkit.build(_proposal())})
        old = next(s.value["candidate"] for s in context.state if s.key == "current-source-bim")
        raw = asyncio.run(session._execute_frozen("claim_transaction",
            dict(candidate=first, entries_json=json.dumps(entries)), application={"task_id": "observed"}))
        data = result_metadata(raw)
        assert not raw.get("isError") and data["status"] == outcome
        applied = outcome != "failed"
        final = data["saved_candidate"] if applied else old
        assert data["save_effects"]["geometry_applied"] is applied
        assert data["save_effects"]["audit_written"]
        assert bool(data["save_effects"]["created_candidates"]) is applied
        assert ("observed" in session.applied) is applied
        event = next(e for e in reversed(store.events) if e.payload.event_type == "tool_execution")
        assert event.payload.applied_write_id  # The transaction audit was durably written.
        assert any(s.source_id == "observation-application-attempt" for s in event.source_refs)
        update_building_context(engine, event, raw)
        assert next(s.value["candidate"] for s in context.state if s.key == "current-source-bim") == final
        assert session.source_bim()["candidate"] == final
        if applied:
            assert data["claim_application"]["status"] == "applied"
            assert data["source_plan_views"]  # Same feedback as an ordinary revision.
            assert any(b["type"] == "image" for b in raw["content"])
            door = json.loads((run/final/"proposal.json").read_text())["geometry"]["openings"][0]
            assert door["z"] == [.3, 2.1]
        # Force a genuine context compaction, then load its durable checkpoint.
        for i in range(5):
            context.append({"role": "user", "content": "old observation " * 100},
                store.source(f"history-{i}", {}).model_copy(update={"event_id": event.event_id}))
            context.project()
        assert any(e.payload.event_type == "context" and e.payload.action == "compact" for e in store.events)
        restored = ContextManager.load(store, context.dump())
        engine.context = restored
        update_building_context(engine, event, raw)
        resumed = coordinator(store, tools)
        assert next(s.value["candidate"] for s in restored.state if s.key == "current-source-bim") == final
        assert resumed.source_bim()["candidate"] == final
        assert ("observed" in resumed.applied) is applied
        assert tools.calls == ["claim_transaction"]  # Recovery never repeats committed entries.
        record = dict(run="fixture", _source_root=str(run), source_format="test", gaps=[], invocations=[dict(
            steps=[dict(index=1, tool="claim_transaction", arguments={}, result_data=data, is_error=False, t_call=1)])])
        summary = summarise(record)
        assert (summary["call_errors"], summary["domain_failures"], summary["usable_source_drafts"]) == (
            0, int(outcome != "completed"), int(applied))


def test_noop_revision_and_confirm_are_not_geometry_application(tmp_path):
    run, toolkit = setup_run(tmp_path)
    result = toolkit.revise("seed", json.dumps([dict(op="set_notes", assumptions=["inferred"], unresolved=[])]))
    assert result["saved_candidate"] == result["candidate"]
    assert not result["save_effects"]["geometry_applied"]
    assert result["save_effects"]["created_candidates"] == [result["candidate"]]
    assert read_saved_result({"candidate": result["candidate"]}, tool="inspect_candidate", run=run)["saved_candidate"] is None
