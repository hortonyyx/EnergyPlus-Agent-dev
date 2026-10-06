"""B1: reference-only state remains lossless, and default wire bytes do not move."""

import base64
import io
import json
import subprocess
import sys
import types
from pathlib import Path

from PIL import Image

from src.agent.runtime_roles.context_policy import role_context_policy
from src.agent_runtime.anthropic import convert_messages
from src.agent_runtime.context import ContextManager, ContextPolicy, StateEntry
from src.agent_runtime.store import json_bytes
from test_runtime_context import _event_source, _store


ROOT = Path(__file__).resolve().parents[1]


def _image_message():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buffer, format="PNG")
    raw = buffer.getvalue()
    return raw, {"role": "user", "content": [{"type": "image_url", "image_url": {
        "url": "data:image/png;base64," + base64.b64encode(raw).decode()}}]}


def _interaction(manager, source, index, picture):
    manager.append({"role": "assistant", "content": "inspect", "tool_calls": [{
        "id": f"call-{index}", "type": "function", "function": {"name": "view", "arguments": "{}"}}]}, source)
    manager.append({"role": "tool", "tool_call_id": f"call-{index}",
                    "content": f"Observation {index}: " + "wall " * 90}, source)
    if picture is not None:
        manager.append(picture, source)


def _wire(projection):
    system, _, messages, _ = convert_messages(projection.messages, projection.sources)
    return json_bytes({"system": system, "messages": messages})


def test_single_model_projection_and_policy_bytes_match_pre_b1_including_compaction(tmp_path):
    name = "src.agent_runtime._b1_context_baseline"
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / "src/agent_runtime/context.py")
    code = subprocess.check_output(["git", "show", "5927bb5f:src/agent_runtime/context.py"], cwd=ROOT)
    sys.modules[name] = module
    try:
        exec(compile(code, module.__file__, "exec"), module.__dict__)
        old_policy = module.ContextPolicy(compact_at_tokens=550)
        policy = ContextPolicy(compact_at_tokens=550)
        assert json_bytes(policy.model_dump(mode="json")) == json_bytes(old_policy.model_dump(mode="json"))
        with _store(tmp_path / "old") as old_store, _store(tmp_path / "new") as new_store:
            old = module.ContextManager(old_store, policy=old_policy)
            new = ContextManager(new_store, policy=policy)
            for manager in (old, new):
                source = _event_source(manager.store, "original input")
                manager.append({"role": "system", "content": "guide"}, source)
                manager.append({"role": "user", "content": "task"}, source)
                state_type = module.StateEntry if manager is old else StateEntry
                manager.set_state(state_type(key="reader-artifacts", category="artifact_version",
                    value=[{"task_id": "reader", "runtime": {"result": "full original record"}}],
                    epistemic_status="computed", source_refs=(source,)))
            picture = _image_message()[1]
            for index in range(9):
                for manager in (old, new):
                    _interaction(manager, manager.history[0].source, index, picture if index % 3 == 0 else None)
                assert _wire(new.project()) == _wire(old.project())
            assert any(e.payload.event_type == "context" and e.payload.action == "compact" for e in new_store.events)
            restored = ContextManager.load(new_store, old.dump())
            assert _wire(restored.project()) == _wire(new.project())
    finally:
        sys.modules.pop(name, None)


def test_role_compaction_preserves_full_records_references_images_and_checkpoint(tmp_path):
    with _store(tmp_path) as store:
        source = _event_source(store, "artifact evidence")
        artifact = store.put_json({"plan": {"openings": ["door-1"]}, "evidence": "original pixels"})
        full = [{"task_id": "plan_F1", "role_id": "plan_reader", "target": "F1", "status": "completed",
                 "artifact": artifact.model_dump(mode="json"), "runtime": {"history": "large ledger " * 1000},
                 "validation": {"unresolved": ["height uncertain"]}},
                {"task_id": "elev_N", "status": "failed", "reason": "image missing"}]
        manager = ContextManager(store, policy=role_context_policy("coordinator", compact_at_tokens=1500))
        manager.append({"role": "system", "content": "guide"}, source)
        manager.append({"role": "user", "content": "Read artifacts using read_role_artifact; complete status via role_state."}, source)
        manager.set_state(StateEntry(key="reader-artifacts", category="artifact_version", value=full,
            epistemic_status="computed", source_refs=(source,)))
        raw, picture = _image_message()
        for i in range(14):
            _interaction(manager, source, i, picture if i == 0 else None)
            manager.project()
        assert manager._archived_history_ids
        projected = manager.project()
        assert "large ledger" not in json.dumps(projected.messages)
        assert "image missing" in json.dumps(projected.messages)
        assert artifact.sha256 in json.dumps(projected.messages)
        assert "read_role_artifact" in json.dumps(projected.messages)
        assert manager.state[0].value == full
        assert json.loads(store.get_bytes(artifact))["plan"]["openings"] == ["door-1"]
        saved = manager.dump()
        restored = ContextManager.load(store, saved)
        assert restored.full_history() == manager.full_history()
        assert restored.project().messages == projected.messages
        assert restored.state == manager.state
        removed = next(image for image in restored.images if not image.active)
        assert restored.retrieve_image(removed.view_id, removed.image.sha256) == raw
        retrieved = restored.project()
        assert picture["content"][0] in retrieved.messages[-2]["content"]
        assert restored.full_history()[0][:2] == manager.full_history()[0][:2]
        store.validate()


def test_reader_policies_keep_existing_projection_and_explicit_overrides():
    for role in ("plan_reader", "elevation_reader"):
        assert role_context_policy(role) == ContextPolicy(compact_at_tokens=100_000)
    policy = role_context_policy("coordinator", compact_at_tokens=75_000, max_images=3)
    assert policy.compact_at_tokens == 75_000 and policy.max_images == 3
    assert policy.compact_to_ratio == 0.3
