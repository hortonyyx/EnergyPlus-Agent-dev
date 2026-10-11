"""Current source/crop image identity and durable view indexing contracts."""
import base64
import hashlib
import json
from types import SimpleNamespace
from src.agent.runtime_context import update_building_context
from src.agent.runtime_tools import FrozenBimTools, coordinator_role
from src.agent_runtime.context import ContextManager
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts


def digest(data):
    return hashlib.sha256(data).hexdigest()


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
            context=context, store=store,
            _event_source=lambda event: store.source("context-index-test", {"tool": event.payload.tool_name}))
        event = SimpleNamespace(payload=SimpleNamespace(tool_name="record_claim"))
        update_building_context(engine, event, {"structuredContent": {"claim_id": "claim_0001"}})
        view = next(entry for entry in context.state if entry.key == "view:view_0024")
        assert view.value["returned_png_sha256"] == "claim-crop-hash"
        assert store.get_bytes(view.source_refs[0].blob) == path.read_bytes()
        saved = context.state
        assert {entry.key for entry in saved} == {"view:view_0024", "context-retrieval"}
        assert "claim_status" in json.dumps(context.model_state())
        update_building_context(engine, event, {})
        assert context.state == saved



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
