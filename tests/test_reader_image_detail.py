"""Reader pixel frames survive MCP conversion, Responses wire and exact retrieval."""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import io
import json
import re

import pytest
from PIL import Image

from src.agent.runtime_roles.readers import ReaderTools
from src.agent_runtime.adapter import convert_tool_result
from src.agent_runtime.context import ContextManager, ContextPolicy
from src.agent_runtime.estimation import get_model_profile, openai_image_tokens
from src.agent_runtime.responses import build_responses_body, estimate_responses_request
from test_runtime_context import _event_source, _store


SIZE = (2690, 1276)


def picture(size=SIZE):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, "PNG")
    return buffer.getvalue()


def image_parts(body):
    return [block for item in body["input"] for block in item.get("content", [])
            if block.get("type") == "input_image"]


def test_generic_mcp_detail_passthrough_preserves_bytes_and_nonreader_default(tmp_path):
    raw = picture()
    content = {"type": "image", "mimeType": "image/png", "data": base64.b64encode(raw).decode(),
               "_meta": {"other": "retained metadata"}}
    original = {"content": [content]}
    marked = ReaderTools.original_image_detail(original)
    assert original["content"][0]["_meta"] == {"other": "retained metadata"}
    assert marked["content"][0]["data"] == content["data"]
    assert marked["content"][0]["_meta"] == {"other": "retained metadata", "codex/imageDetail": "original"}
    with _store(tmp_path) as store:
        _, pictures, shown, refs = convert_tool_result("reader", marked, store)
        converted = next(row for row in pictures if row["type"] == "image_url")
        assert converted["image_url"]["detail"] == "original"
        assert store.get_bytes(refs[0]) == raw
        assert base64.b64decode(converted["image_url"]["url"].split(",", 1)[1]) == raw
        assert shown["image_blocks"] == pictures
        _, unchanged, _, _ = convert_tool_result("ordinary", original, store)
        assert "detail" not in next(row for row in unchanged if row["type"] == "image_url")["image_url"]
        native = build_responses_body(model="gpt-6-sol", messages=[{"role": "user", "content": unchanged}],
                                      tools=[], parameters={"max_tokens": 1000})
        assert image_parts(native)[0]["detail"] == "high"


@pytest.mark.parametrize("detail", ["low", "high", "auto", "original"])
def test_generic_context_checkpoint_and_direct_retrieval_keep_selected_detail(tmp_path, detail):
    raw = picture()
    with _store(tmp_path) as store:
        manager = ContextManager(store, policy=ContextPolicy(image_history_batches=1))
        source = _event_source(store, "original")
        image = store.put_bytes(raw, "image/png")
        # A tool can register bytes before its presentation appends the detail.
        key = manager.register_image("exact", image, source=source)
        message = {"role": "user", "content": [{"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(raw).decode(), "detail": detail}}]}
        manager.append(message, source, image_keys=(key,))
        assert manager.images[0].detail == detail
        restored = ContextManager.load(store, manager.dump())
        assert restored.retrieve_image("exact", image.sha256) == raw
        assert restored.history[-1].message["content"][-1]["image_url"]["detail"] == detail
        assert restored.images[0].source == source


def test_runtime_context_read_preserves_original_detail_on_responses_wire(tmp_path):
    from src.agent_runtime.loop import RunLimits
    from test_agent_runtime import MESSAGES, runtime
    from test_runtime_c1 import ImageHistoryTools
    from test_runtime_responses import response

    class OriginalTools(ImageHistoryTools):
        def image_bytes(self, index):
            return picture((SIZE[0] - index, SIZE[1]))

        async def call_tool(self, name, arguments):
            return ReaderTools.original_image_detail(await super().call_tool(name, arguments))

    def call(identity, name, args):
        return response([{"type": "function_call", "call_id": identity, "name": name,
                          "arguments": json.dumps(args), "status": "completed"}])

    tools = OriginalTools(tmp_path / "tools")
    raw = tools.image_bytes(1)
    digest = hashlib.sha256(raw).hexdigest()
    engine = runtime(tmp_path, [call("first", "view", {"index": 1}),
        call("second", "view", {"index": 2}),
        call("reopen", "read_context_image", {"view_id": "saved-" + digest, "sha256": digest}),
        response()], tools=tools, limits=RunLimits(model_calls=4, tool_calls=3, seconds=60, tokens=1_000_000))
    engine.model = "gpt-6-sol"
    engine.parameters["max_tokens"] = 32000
    engine.versions = engine.versions.model_copy(update={"remote_model": engine.versions.remote_model.model_copy(
        update={"route_id": "chatgpt-subscription"})})
    engine.context_policy = ContextPolicy(image_history_batches=1)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed", result
        last = json.loads(engine.adapter.requests[-1])
        blocks = image_parts(last)
        assert len(blocks) == 1 and blocks[0]["detail"] == "original"
        assert base64.b64decode(blocks[0]["image_url"].split(",", 1)[1]) == raw
        retrieved = next(row for row in engine.store.events if row.payload.event_type == "tool_execution"
                         and row.payload.tool_name == "read_context_image")
        raw_result = engine.store.resolve(retrieved.payload.raw_result)
        assert raw_result["content"][1]["_meta"]["codex/imageDetail"] == "original"
        assert ContextManager.load(engine.store, engine.context.dump()).images[0].detail == "original"
        engine.store.validate()


@pytest.mark.parametrize("role_id", ["plan_reader", "elevation_reader"])
def test_reader_initial_crop_and_trial_wire_use_original_dimensions(tmp_path, monkeypatch, role_id):
    from src.agent.runtime_roles.entry import execute, parser
    from src.agent.runtime_roles.plan_format import READER_PLAN_EXAMPLE
    from src.agent_runtime.adapter import ScriptedAdapter
    from reader_delivery_fixtures import REVIEW, compact_elevation
    from test_agent_runtime import versions
    from test_role_session import elevation
    from test_runtime_responses import response

    def native_versions(*args, **kwargs):
        original = versions()
        return original.model_copy(update={"remote_model": original.remote_model.model_copy(
            update={"route_id": "chatgpt-subscription", "remote_alias": "gpt-6-sol"})})

    monkeypatch.setattr("src.agent.runtime_roles.entry.make_versions", native_versions)
    monkeypatch.setattr("src.agent.runtime_roles.session.make_versions", native_versions)
    images = tmp_path / "inputs"
    images.mkdir()
    raw = picture()
    (images / "drawing.png").write_bytes(raw)
    marker = tmp_path / "script.json"
    marker.write_text("{}")
    routes = {role: {"provider": "scripted", "model": "scripted-model", "output_tokens": 4000}
              for role in ("coordinator", "plan_reader", "elevation_reader")}
    task = {"task_id": "reader", "role_id": role_id, "image": "drawing.png",
            "target": "F1" if role_id == "plan_reader" else "North/F1"}
    args = parser().parse_args(["--out", str(tmp_path / "out"), "--run-root", str(tmp_path),
        "--images", str(images), "--provider", "scripted", "--model", "scripted-model", "--script", str(marker),
        "--roles-json", json.dumps(routes), "--seconds", "120", "--model-calls", "3", "--tool-calls", "4",
        "--tokens", "100000000", "--reader-task-json", json.dumps(task)])

    def call(identity, name, arguments):
        return response([{"type": "function_call", "call_id": identity, "name": name,
                          "arguments": json.dumps(arguments), "status": "completed"}])

    trial_name = "trial_plan_bim" if role_id == "plan_reader" else "trial_elevation_reading"
    trial_args = {"plan": copy.deepcopy(READER_PLAN_EXAMPLE)} if role_id == "plan_reader" else compact_elevation(elevation())
    def accept(request):
        trial_id = "latest" if role_id == "plan_reader" else re.findall(r"elevation_[a-f0-9]{16}", json.dumps(request))[-1]
        return call("submit", "submit_plan_reading" if role_id == "plan_reader" else "submit_elevation_reading",
                    {"trial_id": trial_id, "local_review": REVIEW})

    adapters, stores = [], []
    def factory(task_id, config, store):
        adapter = ScriptedAdapter([
            call("crop", "view_image", {"name": "drawing.png", "box": [0, 0, 800, 600], "display_scale": 1}),
            call("trial", trial_name, trial_args), accept])
        adapters.append(adapter)
        stores.append(store)
        return adapter

    result = asyncio.run(execute(args, adapter_factory=factory))
    assert result["status"] == "completed", result
    assert result["role_accounting"]["requests"] == 3
    assert (tmp_path / "out/bim/images/drawing.png").read_bytes() == raw
    bodies = [json.loads(value) for value in adapters[0].requests]
    assert len(image_parts(bodies[0])) == 1
    profile = get_model_profile("gpt-6-sol")
    assert openai_image_tokens(*SIZE, profile, detail="high")[1:] == (2293, 1088)
    for body in bodies:
        blocks = image_parts(body)
        assert blocks and all(block["detail"] == "original" for block in blocks)
        estimate = estimate_responses_request(body, output_token_limit=4000, profile=profile)
        assert len(estimate.images) == len(blocks)
        for block, item in zip(blocks, estimate.images, strict=True):
            sent = base64.b64decode(block["image_url"].split(",", 1)[1])
            with Image.open(io.BytesIO(sent)) as image:
                assert (item.width, item.height) == image.size
                assert (item.resized_width, item.resized_height) == image.size
    assert (estimate.images[0].width, estimate.images[0].height) == SIZE
    store = stores[0]
    executions = [row for row in store.events if row.payload.event_type == "tool_execution"
                  and row.payload.tool_name in {"view_image", trial_name}]
    sent_images = {block["image_url"] for block in image_parts(bodies[-1])}
    for event in executions:
        value = store.resolve(event.payload.raw_result)
        returned = [block for block in value["content"] if block["type"] == "image"]
        assert returned
        for block in returned:
            assert block["_meta"]["codex/imageDetail"] == "original"
            assert f"data:{block['mimeType']};base64,{block['data']}" in sent_images
