"""Building entry and exact-wire checks for the stage-2 runtime boundary."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from src.agent.runtime_context import update_building_context
from src.agent.runtime_entry import execute, parser
from src.agent_runtime.context import ContextManager, ContextPolicy
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, HashedBlobRef

from test_agent_runtime import MESSAGES, Tools, response, runtime
from test_runtime_recovery_edges import _summary_response


ROOT = Path(__file__).resolve().parents[1]
STAGE1 = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage1"


def test_exact_image_retrieval_survives_paid_summary_and_multiple_preflights(tmp_path):
    engine = runtime(tmp_path, [response(("v", "view", {})), response(("e", "error", {})),
        _summary_response, response(text="Done")], limits=RunLimits(model_calls=4,
            tool_calls=3, seconds=30.0, tokens=1_000_000, summary_every=2))
    engine.context_policy = ContextPolicy(active_window_messages=1, max_images=1)
    retrieved = []

    def retrieve_after_old_image_leaves_window(boundary, current):
        if boundary != "after_checkpoint" or current.counts["tool_calls"] != 2 or retrieved:
            return
        current.context.project(consume_retrievals=False)
        old = current.context.images[0]
        assert not old.active
        current.context.retrieve_image(old.view_id, old.image.sha256)
        retrieved.append(old.image.sha256)

    engine.fault_hook = retrieve_after_old_image_leaves_window
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == "completed"
        requests = [e.payload for e in engine.store.events if e.payload.event_type == "adapter_request"]
        assert requests[-2].logical_purpose == "context_summary" and not requests[-2].images
        assert [image.sent.sha256 for image in requests[-1].images] == retrieved
        assert engine.context.dump()["retrieval_pins"] == []


def test_context_projection_keeps_frozen_guidance_and_exact_sent_tool_envelopes(tmp_path):
    class RepeatedLargeResult(Tools):
        async def call_tool(self, name, arguments):
            raw = await super().call_tool(name, arguments)
            raw["content"].insert(0, {"type": "text", "text": "exact repeated result " * 8})
            return raw

    engine = runtime(tmp_path, [response(("a", "view", {}), ("b", "view", {})),
        response(("c", "error", {})), response(text="Done")], tools=RepeatedLargeResult(tmp_path / "tools"))
    engine.context_policy = ContextPolicy(active_window_messages=1, max_images=1,
        large_result_bytes=30)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed"
        requests = [e for e in engine.store.events if e.payload.event_type == "adapter_request"]
        for wire, request in zip(engine.adapter.requests, requests, strict=True):
            assert wire == engine.store.capture_bytes(request.payload.final_request_body)
            body = json.loads(wire)
            assert body["messages"][0] == MESSAGES[0]
            assert len(request.payload.images) <= 1
            expected = set()
            for message in body["messages"]:
                if message.get("role") == "assistant":
                    assert not expected
                    expected = {c["id"] for c in message.get("tool_calls", [])}
                elif message.get("role") == "tool":
                    expected.remove(message["tool_call_id"])
                else:
                    assert not expected
            assert not expected
        by_id = {e.event_id: e for e in engine.store.events}
        changed = []
        for event in engine.store.events:
            if event.payload.event_type != "tool_presentation":
                continue
            p = event.payload
            body = engine.store.resolve(by_id[p.request_event_id].payload.final_request_body)
            shown = engine.store.resolve(p.shown_result)
            assert shown["tool_message"] in body["messages"]
            blocks = [b for m in body["messages"] if isinstance(m.get("content"), list)
                for b in m["content"]]
            assert all(block in blocks for block in shown["image_blocks"])
            if p.shown_result != by_id[p.tool_execution_event_id].payload.shown_result:
                assert p.context_event_id
                changed.append(event)
        assert changed
        assert len(engine.context.checklist().entries("user_requirement")) == 1
        assert len(engine.context.checklist().entries("constraint")) == 1


def test_building_state_keeps_hashed_geometry_and_distinguishes_selected_from_current(tmp_path):
    run = tmp_path / "bim"
    (run / "claims").mkdir(parents=True)
    (run / "inferences").mkdir()
    (run / "work_reviews").mkdir()
    (run / "work_reviews/review_0001.json").write_text(json.dumps({"decision": "continue",
        "next_action": "check the door against the original view", "candidate": "candidate_02"}))
    (run / "claims/claim_1.json").write_text(json.dumps({"claim": {
        "uncertain": ["door side"], "width_m": 1.1}}))
    (run / "inferences/inference_1.json").write_text(json.dumps({"declaration": {
        "assumptions": ["opening exists"], "unresolved": ["height"]}}))
    for number in (1, 2):
        folder = run / f"candidate_{number:02d}"
        folder.mkdir()
        (folder / "source_model.json").write_text(json.dumps({
            "spaces": [{"id": f"room-{number}", "height": 3.0, "polygon": [[0, 0], [1, 0], [1, 1]]}],
            "boundaries": [], "openings": [], "assumptions": ["test fixture"],
            "source_model_sha256": f"model-{number}", "source_geometry_sha256": f"geometry-{number}"}))
        (folder / "report.json").write_text(json.dumps({"unresolved": [f"report-{number}"]}))
    (run / "delivery_selection.json").write_text('{"candidate":"candidate_01"}')
    with EventStore(tmp_path / "audit", run_id="r", task_id="t",
            budget_limit=BudgetAmounts(tokens=1000, calls=3)) as store:
        context = ContextManager(store)
        engine = SimpleNamespace(tools=SimpleNamespace(run_directory=run), store=store,
            context=context, _event_source=lambda _: store.source("tool-result", {}))
        event = SimpleNamespace(payload=SimpleNamespace(tool_name="build_bim"))
        update_building_context(engine, event, {"structuredContent": {"candidate": "candidate_02"}})
        # Looking at an older candidate does not silently roll back current state.
        event.payload.tool_name = "inspect_candidate"
        update_building_context(engine, event, {"structuredContent": {"candidate": "candidate_01"}})
        entries = {s.key: s for s in context.state}
        assert entries["current-source-bim"].value["candidate"] == "candidate_02"
        assert entries["selected-source-bim"].value["candidate"] == "candidate_01"
        assert entries["source-bim-objects"].value["spaces"] == ["room-2"]
        assert entries["claims:claim_1"].epistemic_status == "inferred"
        assert entries["inferences:inference_1"].epistemic_status == "inferred"
        unresolved = entries["source-bim-unresolved"]
        assert unresolved.value["report_unresolved"] == ["report-2"]
        assert len(unresolved.source_refs) == 2
        for key in ("source-bim-dimensions", "source-bim-geometry"):
            ref = HashedBlobRef.model_validate_json(json.dumps(entries[key].value["file"]))
            saved = json.loads(store.get_bytes(ref))
            assert saved["spaces"][0]["height"] == 3.0
            assert saved["spaces"][0]["id"] == "room-2"
        assert entries["source-bim-todo"].epistemic_status == "unresolved"
        review = entries["current-work-review"]
        assert review.category == "todo" and review.epistemic_status == "inferred"
        assert review.value["record"]["next_action"] == "check the door against the original view"
        (run / "work_reviews/review_0002.json").write_text('{"decision":"stop","next_action":""}')
        update_building_context(engine, event, {})
        latest = next(s for s in context.state if s.key == "current-work-review")
        assert latest.revision == review.revision + 1
        assert latest.value["record"] == {"decision": "stop", "next_action": ""}


def test_real_frozen_entry_builds_offline_and_completed_resume_does_not_write_again():
    # This calls the real frozen BIM MCP service, with a five-response script.
    # It is a small transport fixture, not a model-driven whole-case generation.
    # pytest's default tmp_path may live outside the repository, but the real
    # entry deliberately permits writes only inside its own worktree.
    with tempfile.TemporaryDirectory(prefix=".stage2-entry-test-", dir=ROOT) as temporary:
        test_directory = Path(temporary)
        brief = test_directory / "building-input.json"
        brief.write_text(json.dumps({"constraints": ["Do not merge the two physical rooms"],
            "thermal_zones": 1}))
        args = parser().parse_args(["--out", str(test_directory / "run"),
            "--images", str(STAGE1 / "offline_inputs"), "--provider", "scripted",
            "--building-input", str(brief),
            "--script", str(STAGE1 / "offline_responses.json"), "--context-window", "3",
            "--model-calls", "6", "--seconds", "180"])
        first = asyncio.run(execute(args))
        assert first["status"] == "completed"
        output = args.out
        before = (output / "events.jsonl").read_bytes()
        bim_before = (output / "bim/candidate_01/source_model.json").read_bytes()
        journal = json.loads((output / "journal.json").read_bytes())
        with EventStore(output, run_id=output.name, task_id="coordinator",
                budget_limit=BudgetAmounts.model_validate_json(json.dumps(journal["budget_limit"]))) as store:
            _, checkpoint, _ = store.latest_checkpoint()
            manager = ContextManager.load(store, checkpoint["context"])
            checklist = manager.checklist()
            requirement = checklist.entries("user_requirement")[0]
            assert "Do not merge the two physical rooms" in json.dumps(requirement.value)
            assert "not a measured" in json.dumps(requirement.value)
            first_request = next(e.payload for e in store.events if e.payload.event_type == "adapter_request")
            assert "Do not merge the two physical rooms" in json.dumps(store.resolve(first_request.final_request_body))
            for category in ("user_requirement", "constraint", "evidence_reference", "artifact_version",
                             "dimension", "object_id", "geometry"):
                assert checklist.entries(category), category
            # This fixture has no open items. C1 retires empty placeholders,
            # while preserving the exact saved report and source references.
            assert not checklist.entries("unresolved") and not checklist.entries("todo")
            states = {entry.key: entry for entry in manager.state}
            unresolved = states["source-bim-unresolved"]
            assert not unresolved.active and unresolved.source_refs
            assert all(not value for value in unresolved.value.values())
            assert not states["source-bim-todo"].active
            manifest = json.loads((output / "versions.json").read_bytes())
            assert len(manifest["dependency_lock"]["identifier"]) == 64
        args.resume = True
        resumed = asyncio.run(execute(args))
        assert resumed["resume_status"] == "already_completed"
        assert (output / "events.jsonl").read_bytes() == before
        assert (output / "bim/candidate_01/source_model.json").read_bytes() == bim_before
