"""C1: real wire formatting and bounded service failures, entirely offline."""

import asyncio
import base64
import hashlib
import io
import json

import httpx
import pytest
from PIL import Image

from src.agent_runtime.adapter import HttpChatAdapter, convert_tool_result
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.context import ContextManager, ContextPolicy, StateEntry
from test_agent_runtime import MESSAGES, Tools, response, runtime


class ImageHistoryTools(Tools):
    def image_bytes(self, index):
        stream = io.BytesIO()
        Image.new("RGB", (8, 8), (index * 20, 80, 100)).save(stream, format="PNG")
        return stream.getvalue()

    async def call_tool(self, name, arguments):
        assert name == "view"  # read_context_image must stay in Runtime.
        self.calls.append((name, arguments))
        raw = self.image_bytes(arguments["index"])
        return {"isError": False, "content": [
            {"type": "text", "text": f"source view {arguments['index']}"},
            *[{"type": "image", "mimeType": "image/png", "data": base64.b64encode(raw).decode()}
              for _ in range(arguments.get("count", 1))]]}

    def image_origins(self, raw):
        encoded = next(block["data"] for block in raw["content"] if block["type"] == "image")
        sha = hashlib.sha256(base64.b64decode(encoded)).hexdigest()
        return {sha: {"view_id": "saved-" + sha}}


def _wire_images(value):
    if isinstance(value, list):
        return [raw for item in value for raw in _wire_images(item)]
    if not isinstance(value, dict):
        return []
    if value.get("type") in {"image_url", "input_image"}:
        url = value["image_url"]
        return [base64.b64decode((url["url"] if isinstance(url, dict) else url).split(",", 1)[1])]
    if value.get("type") == "image" and isinstance(value.get("source"), dict):
        return [base64.b64decode(value["source"]["data"])]
    return [raw for child in value.values() for raw in _wire_images(child)]


@pytest.mark.parametrize("enabled", [False, True])
def test_image_history_initial_attachments_are_runtime_owned_not_tool_claimed(tmp_path, enabled):
    class TaggedTools(ImageHistoryTools):
        async def call_tool(self, name, arguments):
            result = await super().call_tool(name, arguments)
            result["content"].insert(0, {"type": "text", "text": "runtime-initial-input"})
            result["tags"] = ["runtime-initial-input"]
            return result

        def image_origins(self, raw):
            return {key: {**value, "tags": ["runtime-initial-input"]}
                    for key, value in super().image_origins(raw).items()}

    tools = TaggedTools(tmp_path / "tools")
    initial = [tools.image_bytes(i) for i in (6, 7)]
    messages = [*MESSAGES, *[{"role": "user", "content": [{"type": "image_url", "image_url": {
        "url": "data:image/png;base64," + base64.b64encode(raw).decode()}}]} for raw in initial]]
    engine = runtime(tmp_path, [response(("a", "view", {"index": 1})),
                               response(("b", "view", {"index": 2})), response(text="Done")], tools=tools)
    engine.context_policy = ContextPolicy(image_history_batches=1 if enabled else None)
    with engine.store:
        assert asyncio.run(engine.run(messages))["status"] == "completed"
        assert [_wire_images(json.loads(wire)) for wire in engine.adapter.requests] == [initial,
            [*initial, tools.image_bytes(1)],
            [*initial, *([] if enabled else [tools.image_bytes(1)]), tools.image_bytes(2)]]
        assert all(("runtime-initial-input" in row.tags) == enabled for row in engine.context.history[:4])
        assert all("runtime-initial-input" not in row.tags for row in engine.context.history[4:])
        assert any(spec["function"]["name"] == "read_context_image" for spec in engine.specs) == enabled
        restored = ContextManager.load(engine.store, engine.context.dump())
        assert [row.tags for row in restored.history] == [row.tags for row in engine.context.history]
        engine.store.validate()


@pytest.mark.parametrize("protocol", ["chat", "responses", "anthropic"])
def test_image_history_local_read_is_delivered_exactly_with_all_batch_occurrences(tmp_path, protocol):
    from test_runtime_anthropic import native_response
    from test_runtime_responses import response as responses_response

    def reply(*calls, text=None):
        if protocol == "anthropic":
            return native_response(*calls, text=text)
        if protocol == "responses":
            return responses_response([{"type": "function_call", "call_id": cid, "name": name,
                "arguments": json.dumps(args), "status": "completed"} for cid, name, args in calls]
                if calls else None)
        return response(*calls, text=text)

    tools = ImageHistoryTools(tmp_path / "tools")
    old = tools.image_bytes(1)
    old_sha = hashlib.sha256(old).hexdigest()
    reread = {"view_id": "saved-" + old_sha, "sha256": old_sha}
    script = [reply(("original", "view", {"index": 1})),
              reply(*[(f"diag-{i}", "view", {"index": i + 2, "count": 2}) for i in range(4)]),
              reply(("reread", "read_context_image", reread)), reply(text="Done")]
    engine = runtime(tmp_path, script, tools=tools,
        limits=RunLimits(model_calls=4, tool_calls=6, seconds=60, tokens=1_000_000))
    engine.context_policy = ContextPolicy(image_history_batches=1, max_images=1)
    if protocol == "responses":
        engine.versions = engine.versions.model_copy(update={"remote_model": engine.versions.remote_model.model_copy(
            update={"route_id": "chatgpt-subscription"})})
    elif protocol == "anthropic":
        from src.agent_runtime.providers import GLM_SUBSCRIPTION_ANTHROPIC, provider_parameters
        engine.model = "glm-5.3-flash"
        engine.parameters = provider_parameters(GLM_SUBSCRIPTION_ANTHROPIC, output_tokens=32000)
        engine.versions = engine.versions.model_copy(update={"remote_model": engine.versions.remote_model.model_copy(
            update={"route_id": GLM_SUBSCRIPTION_ANTHROPIC, "remote_alias": engine.model})})
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed" and result["tool_calls"] == 6
        bodies = [json.loads(wire) for wire in engine.adapter.requests]
        assert [_wire_images(body) for body in bodies] == [[], [old],
            [tools.image_bytes(i + 2) for i in range(4) for _ in range(2)], [old]]
        assert "archived_image" in json.dumps(bodies[2])
        executions = {event.event_id: event.payload for event in engine.store.events
                      if event.payload.event_type == "tool_execution"}
        presentations = [event.payload for event in engine.store.events
                         if event.payload.event_type == "tool_presentation"]
        assert len(presentations) == 6 and not engine._undelivered_image_events()
        for presentation in presentations:
            execution = executions[presentation.tool_execution_event_id]
            shown = engine.store.resolve(presentation.shown_result)
            assert shown["image_blocks"] == engine.store.resolve(execution.shown_result)["image_blocks"]
        reader = next(event for event in executions.values() if event.tool_name == "read_context_image")
        assert reader.outcome == "succeeded" and reader.repeatability == "read_only"
        registered = next(image for image in engine.context.images if image.image.sha256 == old_sha)
        assert engine.store.get_bytes(registered.image) == old
        metadata = engine.store.resolve(reader.raw_result)["structuredContent"]
        assert metadata["registered_source"]["event_id"] == registered.source.event_id
        assert len(tools.calls) == 5  # Runtime reader never called external tools.
        for event, wire in zip((e.payload for e in engine.store.events
                               if e.payload.event_type == "adapter_request"), engine.adapter.requests):
            assert engine.store.capture_bytes(event.final_request_body) == wire
        engine.store.validate()


@pytest.mark.parametrize("crash_at", ["after_execution", "before_request"])
def test_image_history_reader_retry_and_resume_preserve_exact_delivery(tmp_path, crash_at):
    class Crash(BaseException):
        pass

    tools = ImageHistoryTools(tmp_path / "tools")
    old = tools.image_bytes(1)
    sha = hashlib.sha256(old).hexdigest()
    script = [response(("a", "view", {"index": 1})), response(("b", "view", {"index": 2})),
              response(("read", "read_context_image", {"view_id": "saved-" + sha, "sha256": sha}))]
    limits = RunLimits(model_calls=6, tool_calls=3, seconds=60, tokens=1_000_000, retry_backoff_seconds=0)
    engine = runtime(tmp_path, script, tools=tools, limits=limits)
    engine.context_policy = ContextPolicy(image_history_batches=1)

    def fault(name, current):
        if name == crash_at and any(e.payload.event_type == "tool_execution" and e.payload.call_id == "read"
                                    for e in current.store.events):
            raise Crash()

    engine.fault_hook = fault
    with engine.store, pytest.raises(Crash):
        asyncio.run(engine.run(MESSAGES))
    engine = runtime(tmp_path, [httpx.ReadTimeout("offline retry"), response(text="Done")], tools=tools, limits=limits)
    engine.context_policy = ContextPolicy(image_history_batches=1)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES, resume=True))
        assert result["status"] == "completed" and result["tool_calls"] == 3 and result["retries"] == 1
        assert len(tools.calls) == 2
        assert [_wire_images(json.loads(wire)) for wire in engine.adapter.requests] == [[old], [old]]
        assert engine.adapter.requests[0] == engine.adapter.requests[1]
        events = [e for e in engine.store.events if e.payload.event_type == "tool_execution"
                  and e.payload.tool_name == "read_context_image"]
        assert len(events) == 1 and not engine.context.dump()["retrieval_pins"]
        presentations = [e for e in engine.store.events if e.payload.event_type == "tool_presentation"
                         and e.payload.tool_execution_event_id == events[0].event_id]
        assert len(presentations) == 1
        assert asyncio.run(engine._call_tool("read_context_image", {"view_id": "saved-" + sha,
            "sha256": "0" * 64}))["isError"]
        original = next(i for i in engine.context.images if i.image.sha256 == sha)
        path = engine.store.directory / original.image.uri
        path.write_bytes(b"tampered")
        assert asyncio.run(engine._call_tool("read_context_image", {"view_id": "saved-" + sha,
            "sha256": sha}))["isError"]
        path.write_bytes(old)
        engine.store.validate()


@pytest.mark.parametrize("text,structured,expected", [
    ('{"x":1}', {"x": 1}, '{"x":1}'),
    ('{"x":1}\nTime remaining: 20s', {"x": 1}, '{"x":1}\nTime remaining: 20s'),
    ('{"x":{"a":1}}', {"x": {"a": 1, "b": 2}}, '{"x":{"a":1}}\n{"x":{"b":2}}'),
    ('{"x":true}', {"x": 1}, '{"x":true}\n{"x":1}'),
    ('plain text', {"x": 1}, 'plain text\n{"x":1}'),
])
def test_tool_result_contains_exact_text_and_only_unrepresented_fields(tmp_path, text, structured, expected):
    engine = runtime(tmp_path, [])
    raw = {"content": [{"type": "text", "text": text}], "structuredContent": structured}
    with engine.store:
        original = json.dumps(raw)
        message, _, shown, _ = convert_tool_result("call", raw, engine.store)
        assert message["content"] == expected
        assert json.dumps(raw) == original
        assert shown["tool_message"] == message
        error, *_ = convert_tool_result("call", {**raw, "isError": True}, engine.store)
        assert error["content"] == "Tool error (isError=true):\n" + expected


@pytest.mark.parametrize("failure,expected_calls,status", [
    ("503", 2, "completed"),
    ("empty", 2, "completed"),
    ("timeout", 2, "completed"),
    ("rate", 2, "completed"),
    ("plain_rate", 2, "completed"),
    ("plain_quota", 1, "quota_exhausted"),
    ("quota", 1, "quota_exhausted"),
    ("ambiguous429", 1, "unclassified_rate_limit"),
    ("permission", 1, "permission_denied"),
    ("permission_insufficient", 1, "permission_denied"),
    ("capacity", 2, "completed"),
    ("parameter", 1, "invalid_request"),
    ("exhausted", 3, "model_retries_exhausted:service_unavailable"),
])
def test_mocktransport_failure_classification_and_bounded_retry(tmp_path, failure, expected_calls, status):
    seen = []
    empty = response(text="")
    empty["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def handler(request):
        seen.append(request.content)
        if len(seen) > 1 and failure != "exhausted":
            return httpx.Response(200, json=response(text="OK"))
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-test-key", request=request)
        if failure == "empty":
            return httpx.Response(200, json=empty)
        if failure.startswith("plain_"):
            return httpx.Response(429, headers={"x-request-id": "request-one"},
                text="temporary rate limit" if failure == "plain_rate" else "quota exhausted")
        code, kind = {"503": (503, "server_error"), "capacity": (503, "server_error"),
            "permission_insufficient": (403, "insufficient_permissions"), "rate": (429, "rate_limit_exceeded"),
            "quota": (429, "insufficient_quota"), "ambiguous429": (429, "unknown"),
            "permission": (403, "permission_denied"), "parameter": (400, "invalid_parameter"),
            "exhausted": (503, "server_error")}[failure]
        message = "insufficient server capacity; workers exhausted" if failure == "capacity" else "service failure"
        return httpx.Response(code, headers={"x-request-id": "request-one"}, json={"error": {
            "type": kind, "message": message + "; secret-test-key", "api_key": "other-secret"},
            "padding": "字" * 3000})

    engine = runtime(tmp_path, [], limits=RunLimits(model_calls=5, tool_calls=0,
        seconds=20, tokens=100000, retry_backoff_seconds=0.001))
    engine.adapter = HttpChatAdapter(base_url="https://test.invalid/v1", api_key="secret-test-key",
        transport=httpx.MockTransport(handler))

    async def run():
        try:
            return await engine.run(MESSAGES)
        finally:
            await engine.adapter.close()
    with engine.store:
        receipt = asyncio.run(run())
        assert receipt["status"] == status
        assert receipt["model_calls"] == len(seen) == expected_calls
        assert all(sent == seen[0] for sent in seen)
        failures = [e.payload.model_failure for e in engine.store.events
                    if e.payload.event_type == "run_lifecycle" and e.payload.model_failure]
        assert len(failures) == (3 if failure == "exhausted" else 1)
        for item in failures:
            assert item.usage_received == (failure == "empty")
            if item.body_excerpt is not None:
                assert len(item.body_excerpt.encode()) <= 2048
                assert item.request_id == "request-one"
        assert len([e for e in engine.store.events if e.payload.event_type == "budget"
                    and e.payload.action == "settle"]) == expected_calls
        engine.store.validate()
    # Include the lock file after closing its Windows-exclusive handle.
    for path in engine.store.directory.rglob("*"):
        if path.is_file():
            assert b"secret-test-key" not in path.read_bytes()
            assert b"other-secret" not in path.read_bytes()


def test_scripted_turns_keep_prefix_then_compact_once_with_exact_saved_state(tmp_path):
    class HistoryTools(Tools):
        async def call_tool(self, name, arguments):
            raw = await super().call_tool(name, arguments)
            # Several whole interactions fit; the final tool result crosses the
            # token threshold. The newest interaction is indivisible.
            raw["content"].insert(0, {"type": "text", "text": "observation " * arguments["words"]})
            return raw

    script = [response((f"v-{i}", "view", {"words": 20 if i < 10 else 1200})) for i in range(11)]
    script.append(response(text="Done"))
    engine = runtime(tmp_path, script, tools=HistoryTools(tmp_path / "tools"),
        limits=RunLimits(model_calls=12, tool_calls=11, seconds=90, tokens=1000000))
    engine.context_policy = ContextPolicy(compact_at_tokens=3000)

    def update(current, event, raw):
        source = current._event_source(event)
        for key, category, value, status in (
            ("current-source-bim", "artifact_version", {"candidate": "candidate_05", "sha256": "a" * 64}, "computed"),
            ("pending", "unresolved", ["Verify the north window height."], "unresolved"),
            ("view:first", "evidence_reference", {"view_id": "view_0001"}, "observed"),
            ("context-retrieval", "general", ["Read saved evidence using claim_status(candidate='candidate_05')."], "computed"),
        ):
            old = next((s for s in current.context.state if s.key == key), None)
            current.context.set_state(StateEntry(key=key, category=category, value=value,
                epistemic_status=status, source_refs=(source,), revision=old.revision + 1 if old else 1))
    engine.context_update = update
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == "completed"
        bodies = [json.loads(wire) for wire in engine.adapter.requests]
        strip_state = lambda body: [m for m in body["messages"] if not (
            isinstance(m.get("content"), str) and m["content"].startswith("Current runtime state"))]
        stable = [strip_state(body) for body in bodies]
        for before, after in zip(stable[:10], stable[1:11]):
            assert after[:len(before)] == before
        compactions = [e for e in engine.store.events if e.payload.event_type == "context"
                       and e.payload.action == "compact"]
        assert len(compactions) == 1
        final = bodies[-1]["messages"]
        assert final[:2] == MESSAGES
        assert "Verify the north window height." in final[-1]["content"]
        assert "candidate_05" in final[-1]["content"]
        assert "claim_status" in final[-1]["content"]
        assert "a" * 64 not in final[-1]["content"] and "blobs/" not in final[-1]["content"]
        assert engine.context.checklist().entries("evidence_reference")[0].value == {"view_id": "view_0001"}
        assert all(s.source_refs for s in engine.context.state)
        checkpoint = engine.context.dump()
        before_events = len(engine.store.events)
        restored = ContextManager.load(engine.store, checkpoint)
        assert restored.project().messages == engine.context.project().messages
        assert len(engine.store.events) == before_events
        tampered = json.loads(json.dumps(checkpoint))
        tampered["archived_history_ids"].append(engine.context.history[-1].history_id)
        with pytest.raises(ValueError, match="archived history differs"):
            ContextManager.load(engine.store, tampered)
        engine.store.validate()


def test_state_retracts_resolved_items_and_preserves_original_text_once(tmp_path):
    from types import SimpleNamespace
    from src.agent.runtime_context import update_building_context

    engine = runtime(tmp_path, [])
    run = tmp_path / "bim"
    (run / "claims").mkdir(parents=True)
    issue = "North window: check the 4800 mm dimension chain."
    for index in range(1, 4):
        (run / f"claims/claim_{index:04d}.json").write_text(json.dumps({"claim": {"unresolved": [issue]}}))
    with engine.store:
        engine.context = ContextManager(engine.store)
        engine.tools.run_directory = run
        event = engine.store.append(__import__('src.harness_contracts', fromlist=['RunLifecyclePayload']).RunLifecyclePayload(
            action="start", reason="state fixture"))
        tool_event = SimpleNamespace(payload=SimpleNamespace(tool_name="claim_status"))
        engine._event_source = lambda _: engine.store.source("state-test", {"original": True})
        update_building_context(engine, tool_event, {})
        state_text = json.dumps(engine.context.model_state())
        assert state_text.count(issue) == 1
        for index in range(1, 4):
            (run / f"claims/decision_{index:04d}.json").write_text(json.dumps({
                "claim_id": f"claim_{index:04d}", "disposition": "retracted", "reason": "superseded"}))
        update_building_context(engine, tool_event, {})
        assert issue not in json.dumps(engine.context.model_state())
        assert not engine.context.checklist().entries("unresolved")
        assert not engine.context.checklist().entries("evidence_reference")
        assert all(not s.active for s in engine.context.state if s.key.startswith("claim"))


@pytest.mark.parametrize('bound,status', [('calls', 'model_budget_exhausted'), ('deadline', 'time_budget_exhausted')])
def test_retry_obeys_call_budget_and_does_not_sleep_past_deadline(tmp_path, bound, status):
    seen = []
    def handler(request):
        seen.append(request.content)
        return httpx.Response(503, json={'error': {'type': 'server_error'},
            'usage': {'prompt_tokens': 5, 'completion_tokens': 0, 'total_tokens': 5}})
    engine = runtime(tmp_path, [], limits=RunLimits(model_calls=1 if bound == 'calls' else 4,
        tool_calls=0, seconds=1, tokens=100000, retry_backoff_seconds=10))
    engine.adapter = HttpChatAdapter(base_url='https://test.invalid/v1', api_key='secret',
        transport=httpx.MockTransport(handler))
    async def run():
        try:
            return await engine.run(MESSAGES)
        finally:
            await engine.adapter.close()
    with engine.store:
        receipt = asyncio.run(run())
        assert receipt['status'] == status and len(seen) == 1
        assert receipt['reported_tokens'] == 5
        assert receipt['usage_complete']
        assert receipt['usage_accounting']['provider_reported_tokens'] == 5
        failures = [e.payload.model_failure for e in engine.store.events
            if e.payload.event_type == 'run_lifecycle' and e.payload.model_failure]
        assert failures[0].usage_received
        assert not any(e.payload.event_type == 'run_lifecycle' and e.payload.action == 'retry'
            for e in engine.store.events)
        engine.store.validate()


def test_zero_usage_empty_reply_recovers_without_accepting_empty_history(tmp_path):
    from test_runtime_recovery_edges import InjectedCrash
    empty = response(text='')
    empty['usage'] = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    limits = RunLimits(model_calls=3, tool_calls=0, tokens=100000, seconds=30, retry_backoff_seconds=0)
    original = runtime(tmp_path, [empty], limits=limits)
    def crash(name, current):
        if name == 'after_response':
            raise InjectedCrash(name)
    original.fault_hook = crash
    with original.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(original.run(MESSAGES))
    resumed = runtime(tmp_path, [response(text='Recovered')], limits=limits, tools=original.tools)
    with resumed.store:
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert receipt['status'] == 'completed'
        assert receipt['model_calls'] == 2
        assert json.loads(resumed.adapter.requests[0])['messages'] == MESSAGES
        assert len([e for e in resumed.store.events if e.payload.event_type == 'run_lifecycle'
            and e.payload.model_failure and e.payload.model_failure.category == 'empty_response']) == 1
        resumed.store.validate()


def test_repeated_active_image_retrieval_is_idempotent_and_checkpointed(tmp_path):
    engine = runtime(tmp_path, [])
    with engine.store:
        manager = ContextManager(engine.store)
        source = engine.store.source('image-input', {'name': 'plan.png'})
        image = engine.store.put_bytes(b'image fixture', 'image/png')
        key = manager.register_image('view-1', image, source=source)
        manager.retrieve_image('view-1', image.sha256)
        count = len(engine.store.events)
        history = len(manager.history)
        manager.retrieve_image('view-1', image.sha256)
        assert len(manager.history) == history and len(engine.store.events) == count
        restored = ContextManager.load(engine.store, manager.dump())
        assert restored.acknowledge_projection() == (key,)
        assert not any(e.payload.event_type == 'context' for e in engine.store.events)


def test_compaction_image_volume_counts_repeated_bytes_in_each_message(tmp_path):
    from src.harness_contracts import RunLifecyclePayload
    from test_runtime_context import _image_message
    engine = runtime(tmp_path, [])
    with engine.store:
        event = engine.store.append(RunLifecyclePayload(action='start', reason='image volume fixture'))
        source = engine._event_source(event)
        image_bytes = b'one image' * 10
        manager = ContextManager(engine.store, policy=ContextPolicy(compact_at_tokens=500,
            compact_to_ratio=0.9, max_image_bytes=len(image_bytes)))
        for message in MESSAGES:
            manager.append(message, source)
        image = engine.store.put_bytes(image_bytes, 'image/png')
        key = manager.register_image('view', image, source=source)
        for _ in range(3):
            manager.append(_image_message(image_bytes), source, image_keys=(key,))
        projected = manager.project(token_estimator=lambda messages: len(messages) * 100)
        actual_images = [b for m in projected.messages if isinstance(m.get('content'), list)
            for b in m['content'] if b.get('type') == 'image_url']
        assert len(actual_images) == 1
        assert len(projected.omitted_history_ids) == 2
        assert manager.full_history()[0][-3:] == [_image_message(image_bytes)] * 3
        engine.store.validate()
