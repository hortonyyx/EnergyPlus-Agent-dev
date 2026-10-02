"""Run the 75 historical run99 calls against real, unchanged BIM tools."""

from __future__ import annotations

import asyncio
import base64
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

from PIL import Image

from src.agent.runtime_context import update_building_context
from src.agent.runtime_entry import prepare_inputs
from src.agent.runtime_tools import (
    FrozenBimTools, _result_metadata, coordinator_role, frozen_bim_client,
    write_frozen_materials, write_frozen_tool_catalog,
)
from src.agent_runtime.adapter import ScriptedAdapter
from src.agent_runtime.context import ContextManager, ContextPolicy
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore, json_bytes
from src.agent_runtime.versions import make_versions
from src.harness_contracts import BudgetAmounts

from test_runtime_long_task import Run99Sequence


ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage2"
HISTORY = ROOT / "AI_agent/logs/experiments/2026-09-30_sm21_instruction_fix_run99"
SAMPLE_STEPS = (20, 40, 75)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReplayTools(FrozenBimTools):
    """Check historical arguments, then execute the real tool without substitution."""

    def __init__(self, *args, sequence, store, **kwargs):
        super().__init__(*args, **kwargs)
        self.sequence, self.store = sequence, store
        self.calls = []

    async def call_tool(self, name, arguments):
        historical = self.sequence.steps[len(self.calls)]
        assert name == historical["tool_name"]
        assert arguments == historical["arguments"]
        raw = await super().call_tool(name, arguments)
        metadata = _result_metadata(raw)
        images = [base64.b64decode(b["data"], validate=True)
                  for b in raw.get("content", []) if b.get("type") == "image"]
        self.calls.append({
            "step": historical["ordinal"], "tool": name,
            "arguments_sha256": digest(json_bytes(arguments)),
            "historical_error": historical["is_error"],
            "actual_error": bool(raw.get("isError")),
            "raw_result": self.store.put_json(raw).model_dump(mode="json"),
            "view_id": metadata.get("view_id"),
            "candidate": metadata.get("candidate"),
            "images": [{"sha256": digest(data), "bytes": len(data)} for data in images],
            "historical_images": [{"sha256": item["sha256"], "bytes": item["byte_size"]}
                                  for item in historical["result"]["images"]],
        })
        return raw


class ObserveReplay:
    """Independent expectations come from actual files/results, never state counts."""

    def __init__(self, output):
        self.output = output
        self.steps = []
        self.requests = []
        self.retrievals = []
        self.retrieved_at = set()

    def __call__(self, boundary, engine):
        step = engine.counts["tool_calls"]
        if (boundary == "after_checkpoint" and engine.pending_response_id is None
                and step in SAMPLE_STEPS and step not in self.retrieved_at):
            # This is the tool-batch checkpoint, before the NEXT projection.
            # Pin an old view that a preceding request already removed.
            view_id = {20: "view_0001", 40: "view_0007", 75: "view_0024"}[step]
            old = next(image for image in engine.context.images
                       if image.view_id == view_id and not image.active)
            raw = engine.context.retrieve_image(old.view_id, old.image.sha256)
            assert raw == engine.store.get_bytes(old.image)
            self.retrieved_at.add(step)
            self.retrievals.append({"after_step": step, "view_id": old.view_id,
                "sha256": old.image.sha256, "bytes": len(raw)})
        if boundary == "before_request":
            self.capture_state(engine, step)
        if boundary == "after_request":
            event = next(e for e in reversed(engine.store.events)
                         if e.payload.event_type == "adapter_request")
            payload = event.payload
            raw = engine.store.get_bytes(payload.final_request_body.blob)
            pixels = 0
            for image in payload.images:
                with Image.open(io.BytesIO(engine.store.get_bytes(image.sent))) as decoded:
                    pixels += decoded.width * decoded.height
            reservation_event = next(e for e in reversed(engine.store.events)
                if e.payload.event_type == "budget" and e.payload.action == "reserve"
                and e.payload.reservation.reservation_id == payload.reservation_id)
            decision = json.loads(engine.store.get_bytes(reservation_event.source_refs[0].blob))
            estimate = len(raw) + pixels + json.loads(raw)["max_tokens"]
            assert estimate == decision["reservation"]["amounts"]["tokens"]
            assert estimate <= engine.limits.context_tokens
            assert decision["action"] == "allow"
            state_prefix = "Current runtime state (machine generated; epistemic status is authoritative): "
            transmitted_state = [json.loads(m["content"][len(state_prefix):])
                for m in json.loads(raw)["messages"]
                if isinstance(m.get("content"), str) and m["content"].startswith(state_prefix)]
            assert transmitted_state == [[entry.model_dump(mode="json")
                                          for entry in engine.context.state if entry.active]]
            self.requests.append({"request": len(self.requests) + 1, "after_step": step,
                "event_id": event.event_id, "reservation_event_id": reservation_event.event_id,
                "wire_bytes": len(raw), "image_pixels": pixels,
                "estimated_tokens": estimate, "context_limit": engine.limits.context_tokens,
                "decision": decision, "within_budget": True,
                "image_hashes": [image.sent.sha256 for image in payload.images]})

    def capture_state(self, engine, step):
        run, store, context = engine.tools.run_directory, engine.store, engine.context
        state = {entry.key: entry for entry in context.state}
        views = {json.loads(path.read_bytes())["view_id"]: path
                 for path in (run / "image_views").glob("view_*.json")}
        expected_views = set(views)
        assert {entry.value["view_id"] for entry in state.values()
                if entry.key.startswith("view:")} == expected_views
        for view_id, path in views.items():
            entry = state["view:" + view_id]
            assert entry.value["record"]["sha256"] == digest(path.read_bytes())
            assert entry.source_refs[0].blob.sha256 == digest(path.read_bytes())
            assert any(image.view_id == view_id and image.image.sha256 == entry.value["returned_png_sha256"]
                       for image in context.images)
        claims = sorted((run / "claims").glob("claim_*.json"))
        assert {key.removeprefix("claims:") for key in state if key.startswith("claims:")} == {
            path.stem for path in claims}
        for path in claims:
            entry = state["claims:" + path.stem]
            assert entry.epistemic_status == "inferred"
            assert entry.source_refs[0].blob.sha256 == digest(path.read_bytes())
            claim = json.loads(path.read_bytes())
            assert all(source["view_id"] in expected_views for source in claim["sources"])
        candidates = sorted(run.glob("candidate_*/source_model.json"))
        current = None
        if candidates:
            path = candidates[-1]
            source = json.loads(path.read_bytes())
            report_path = path.parent / "report.json"
            report = json.loads(report_path.read_bytes())
            current = state["current-source-bim"].value
            assert current["candidate"] == path.parent.name
            assert current["file"]["sha256"] == digest(path.read_bytes())
            assert current["source_model_sha256"] == source["source_model_sha256"]
            assert current["source_geometry_sha256"] == source["source_geometry_sha256"]
            for key in ("source-bim-geometry", "source-bim-dimensions"):
                assert state[key].value["file"] == current["file"]
            assert state["source-bim-objects"].value == {
                name: [obj["id"] for obj in source[name]]
                for name in ("spaces", "boundaries", "openings")}
            unresolved = state["source-bim-unresolved"]
            assert unresolved.value["report_unresolved"] == report["unresolved"]
            assert state["source-bim-todo"].value["unresolved"] == unresolved.value
            assert digest(report_path.read_bytes()) in {ref.blob.sha256 for ref in unresolved.source_refs}
            assert all(store.get_bytes(ref.blob) for ref in unresolved.source_refs)
        else:
            assert "current-source-bim" not in state
        checklist = context.checklist().model_dump(mode="json")
        row = {"step": step, "state_entries": len(state),
            "state_bytes": len(json_bytes([entry.model_dump(mode="json") for entry in context.state])),
            "checklist_bytes": len(json_bytes(checklist)),
            "categories": {name: len(entries) for name, entries in context.checklist().categories.items()},
            "expected_view_ids": sorted(expected_views), "expected_claim_ids": [p.stem for p in claims],
            "current_source_bim": current,
            "context_actions": dict(Counter(e.payload.action for e in store.events
                                             if e.payload.event_type == "context"))}
        if step in SAMPLE_STEPS:
            ref = store.put_json(checklist)
            row["checklist"] = ref.model_dump(mode="json")
            store.write_json(f"state_step_{step:02d}.json", checklist)
        self.steps.append(row)
        if step in SAMPLE_STEPS or step >= 46:
            print(f"frozen replay step={step} state={len(state)} bytes={row['state_bytes']} "
                  f"candidate={current['candidate'] if current else None}", flush=True)


async def replay_frozen_run99(output):
    output = output.resolve()
    assert output.is_relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    sequence = Run99Sequence()
    manifest = json.loads((HISTORY / "inputs.json").read_bytes())
    run, guide, task = prepare_inputs(output, images=HISTORY / "images", mesh=None,
        building_input=None, scope=manifest["scope"], image_kind="drawings", max_candidates=24)
    limits = RunLimits(model_calls=80, tool_calls=80, seconds=900, tokens=80_000_000,
                       context_tokens=12_000_000)
    role = coordinator_role(limits.ledger_limit())
    observer = ObserveReplay(output)
    with EventStore(output, run_id="run99-frozen-tools", task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        async with frozen_bim_client(run, repository_root=ROOT) as client:
            tools = ReplayTools(client, role, run_directory=run, sequence=sequence, store=store)
            catalog = await tools.list_tools()
            write_frozen_materials(output / "frozen", repository_root=ROOT)
            write_frozen_tool_catalog(output / "frozen", catalog, readonly=False)
            specs = [{"type": "function", "function": {"name": t["name"],
                "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in catalog]
            parameters = {"max_tokens": 64, "temperature": 0.0}
            versions = make_versions(store, root=ROOT, prompt=guide, tools=specs,
                parameters=parameters, route={"route_id": "scripted-run99", "model": "offline-run99-fixture"},
                code_paths=("src/agent/runtime_context.py", "src/agent/runtime_tools.py",
                    "src/agent/runtime_entry.py", "scripts/tool_scripts", "src/agent/geometry",
                    "src/agent/correction", "src/agent/execution", "tests/test_runtime_frozen_long_task.py"))
            store.write_json("versions.json", versions.model_dump(mode="json"))
            adapter = ScriptedAdapter(sequence.scripted_responses())
            engine = Runtime(store=store, adapter=adapter, tools=tools, role=role,
                model="offline-run99-fixture", parameters=parameters, versions=versions, limits=limits,
                context_policy=ContextPolicy(active_window_messages=8, max_images=2, max_image_bytes=250_000),
                context_update=update_building_context, fault_hook=observer)
            receipt = await engine.run([{"role": "system", "content": guide},
                                        {"role": "user", "content": task}])
            report = {"receipt": receipt, "steps": observer.steps, "requests": observer.requests,
                "calls": tools.calls, "retrievals": observer.retrievals,
                "limits": limits.model_dump(mode="json"),
                "source": {"path": str(HISTORY.relative_to(ROOT)),
                    "inputs_sha256": digest((HISTORY / "inputs.json").read_bytes())},
                "boundary": "Real frozen tools; historical arguments unchanged; model responses scripted; "
                    "usage 20 tokens/response is synthetic, not service usage. No whole-case model run."}
            store.write_json("frozen_replay_report.json", report)
            assert receipt["status"] == "completed", receipt
            assert len(tools.calls) == 75 and len(observer.requests) == 76
            assert [c["step"] for c in tools.calls if c["actual_error"]] == [18, 19, 56, 58, 62, 63, 73]
            assert all(c["actual_error"] == c["historical_error"] for c in tools.calls)
            for retrieval in observer.retrievals:
                request = observer.requests[retrieval["after_step"]]
                assert retrieval["sha256"] in request["image_hashes"]
            final = observer.steps[-1]
            for category in ("evidence_reference", "artifact_version", "unresolved", "todo",
                             "dimension", "object_id", "geometry"):
                assert final["categories"][category] > 0
            assert len(final["expected_claim_ids"]) == 3
            assert final["context_actions"]["compact"] >= 60
            assert final["context_actions"]["remove_image"] > 0
            return report


def test_real_frozen_tools_keep_run99_state_across_75_steps():
    # Always own a temporary directory inside this worktree, regardless of pytest --basetemp.
    retained = os.environ.get("STAGE2_FROZEN_REPLAY_OUT")
    if retained:
        asyncio.run(replay_frozen_run99(Path(retained)))
        return
    with tempfile.TemporaryDirectory(prefix=".stage2-frozen-long-", dir=ROOT) as temporary:
        asyncio.run(replay_frozen_run99(Path(temporary) / "run"))


def test_saved_claim_view_is_indexed_without_top_level_view_id(tmp_path):
    run = tmp_path / "bim"
    (run / "image_views").mkdir(parents=True)
    path = run / "image_views/view_0024.json"
    path.write_text(json.dumps({"view_id": "view_0024", "name": "South_view.png",
        "returned_png_sha256": "claim-crop-hash", "box_original_pixels": [0, 0, 450, 600]}))
    with EventStore(tmp_path / "events", run_id="claim-view", task_id="test",
                    budget_limit=BudgetAmounts(tokens=1000, calls=2)) as store:
        context = ContextManager(store)
        engine = SimpleNamespace(tools=SimpleNamespace(run_directory=run),
                                 context=context, store=store)
        event = SimpleNamespace(payload=SimpleNamespace(tool_name="record_claim"))
        update_building_context(engine, event, {"structuredContent": {"claim_id": "claim_0001"}})
        view = next(entry for entry in context.state if entry.key == "view:view_0024")
        assert view.value["returned_png_sha256"] == "claim-crop-hash"
        assert store.get_bytes(view.source_refs[0].blob) == path.read_bytes()
        update_building_context(engine, event, {})
        assert context.state == (view,)


def test_claim_preview_image_keeps_its_original_view_id(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "inputs.json").write_text('{}')
    original, returned = b"original PNG bytes", b"returned crop PNG bytes"
    (tmp_path / "images/South_view.png").write_bytes(original)
    preview = {"name": "South_view.png", "view_id": "view_0024",
        "image_sha256": digest(original), "returned_png_sha256": digest(returned),
        "box_original_pixels": [0, 0, 450, 600]}
    tools = FrozenBimTools(None, coordinator_role(BudgetAmounts(calls=1)), run_directory=tmp_path)
    origins = tools.image_origins({"structuredContent": {"claim_id": "claim_0001",
        "evidence_previews": [preview]}, "content": [{"type": "image", "mimeType": "image/png",
        "data": base64.b64encode(returned).decode()}]})
    origin = origins[digest(returned)]
    assert origin["view_id"] == "view_0024"
    assert origin["original_sha256"] == digest(original)
    assert origin["box_original_pixels"] == preview["box_original_pixels"]
