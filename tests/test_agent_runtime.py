from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from PIL import Image
from pydantic import ValidationError

from src.agent_runtime.adapter import HttpChatAdapter, ScriptedAdapter, parse_response, prepare_request
from src.agent_runtime.loop import RunLimits, Runtime
from src.agent_runtime.store import EventStore
from src.harness_contracts import (
    BudgetAmounts, BudgetLedger, BudgetReservation, BudgetSettlement, CostUnavailable,
    EventLog, InputMaterialRequirement, RemoteModelIdentity, ReturnRequirement,
    RoleDefinition, ToolGrant, UsageMissing, VersionManifest, VersionStamp,
)


def response(*calls, text=None, usage=True, reasoning=False):
    message = {"role": "assistant", "content": text}
    if calls:
        message["tool_calls"] = [{"id": call[0], "type": "function", "function": {
            "name": call[1], "arguments": json.dumps(call[2])}} for call in calls]
    if reasoning:
        message["reasoning_content"] = "Public protocol test explanation."
        message["thinking_signature"] = "signature-is-not-thought"
    value = {"id": "test-response", "model": "test", "choices": [{
        "index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop"}]}
    if usage:
        value["usage"] = {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30,
                           "completion_tokens_details": {"reasoning_tokens": 2}}
    return value


def versions():
    stamp = VersionStamp(identifier="test-v1")
    return VersionManifest(code_commit=stamp, dependency_lock=stamp, prompt=stamp,
        tool_definitions=stamp, inference_parameters=stamp, model_route=stamp,
        remote_model=RemoteModelIdentity(route_id="offline", remote_alias="test", alias_status="unverified"))


class Tools:
    def __init__(self, directory, *, unknown_write=False):
        self.directory = directory
        self.directory.mkdir(exist_ok=True)
        self.calls = []
        self.unknown_write = unknown_write

    async def list_tools(self):
        return [{"name": name, "description": name, "inputSchema": {"type": "object"}}
                for name in ("save", "view", "error")]

    def repeatability(self, name):
        return "non_idempotent_write" if name == "save" else "read_only"

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "save":
            (self.directory / "saved.json").write_text(json.dumps(arguments))
            if self.unknown_write:
                raise ConnectionError("secret fake credential must never be logged")
        if name == "view":
            stream = io.BytesIO()
            Image.new("RGB", (4, 4), (255, 0, 0)).save(stream, format="PNG")
            return {"isError": False, "content": [{"type": "image", "mimeType": "image/png",
                "data": base64.b64encode(stream.getvalue()).decode()}]}
        return {"isError": name == "error", "content": [{"type": "text",
                "text": "intentional tool error" if name == "error" else "saved"}]}

    def snapshot_state(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.artifacts()}

    def artifacts(self):
        return sorted(self.directory.glob("*.json"))


def role(limits, readonly=False):
    return RoleDefinition(role_id="local_observer" if readonly else "coordinator",
        responsibilities=("test the single-role protocol",),
        tool_whitelist=tuple(ToolGrant(tool_name=n, access="write" if n == "save" else "read")
                            for n in (("view", "error") if readonly else ("save", "view", "error"))),
        input_materials=(InputMaterialRequirement(name="task", media_type="text/plain"),),
        return_requirements=(ReturnRequirement(name="answer", schema_ref="test"),),
        budget=limits.ledger_limit(), read_only=readonly)


def runtime(tmp_path, responses, *, limits=None, tools=None, readonly=False):
    limits = limits or RunLimits(model_calls=4, tool_calls=5, seconds=30.0, tokens=100_000)
    store = EventStore(tmp_path / "run", run_id="run-test", task_id="task", budget_limit=limits.ledger_limit())
    engine = Runtime(store=store, adapter=ScriptedAdapter(responses),
        tools=tools or Tools(tmp_path / "tools"), role=role(limits, readonly),
        model="test", parameters={"max_tokens": 256, "temperature": 0.0},
        versions=versions(), limits=limits)
    return engine


MESSAGES = [{"role": "system", "content": "unchanged system guidance"},
            {"role": "user", "content": "exercise tool protocol"}]


def test_single_role_keeps_complete_request_result_images_errors_and_public_thinking(tmp_path):
    engine = runtime(tmp_path, [response(("a", "view", {}), ("b", "error", {}),
        ("c", "save", {"value": 7}), reasoning=True), response(text="Done")])
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == "completed"
        assert receipt["model_calls"] == 2 and receipt["tool_calls"] == 3
        log = engine.store.validate()
        assert log.mode == "complete" and receipt["reported_tokens"] == 60
        requests = [e.payload for e in log.events if e.payload.event_type == "adapter_request"]
        for sent, captured in zip(engine.adapter.requests, requests):
            assert sent == engine.store.get_bytes(captured.final_request_body.blob)
        body = engine.store.resolve(requests[-1].final_request_body)
        assert [m["role"] for m in body["messages"][-4:]] == ["tool", "tool", "tool", "user"]
        assert requests[-1].images[0].original.sha256 == requests[-1].images[0].sent.sha256
        tool_events = [e.payload for e in log.events if e.payload.event_type == "tool_execution"]
        assert [e.outcome for e in tool_events] == ["succeeded", "failed", "succeeded"]
        shown = engine.store.resolve(tool_events[0].shown_result)
        assert shown["image_blocks"][-1]["image_url"]["url"].startswith("data:image/png")
        thoughts = [e.payload.thinking for e in log.events if e.payload.event_type == "model_response"][0]
        assert {x.kind for x in thoughts} == {"public_content", "signature", "reported_token_count"}
        assert receipt["billing_usd"] is None
        assert len(receipt["artifacts"]) == 1
        assert len([e for e in log.events if e.payload.event_type == "tool_presentation"]) == 3


@pytest.mark.parametrize("lim,responses,status", [
    (RunLimits(model_calls=1, tool_calls=2, seconds=10.0, tokens=100_000),
     [response(("v", "view", {}))], "model_budget_exhausted"),
    (RunLimits(model_calls=2, tool_calls=0, seconds=10.0, tokens=100_000),
     [response(("w", "save", {}))], "tool_budget_exhausted"),
    (RunLimits(model_calls=2, tool_calls=2, seconds=10.0, tokens=1),
     [], "token_budget_exhausted"),
    (RunLimits(model_calls=2, tool_calls=2, seconds=0.000001, tokens=100_000),
     [], "time_budget_exhausted"),
])
def test_all_budget_dimensions_stop_without_an_extra_operation(tmp_path, lim, responses, status):
    engine = runtime(tmp_path, responses, limits=lim)
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == status
        assert receipt["model_calls"] <= lim.model_calls
        assert receipt["tool_calls"] <= lim.tool_calls
        assert engine.store.events[-2].payload.reason == status
        assert engine.store.validate().mode == "complete"


def test_unknown_write_inspects_persisted_state_and_does_not_repeat(tmp_path):
    tools = Tools(tmp_path / "tools", unknown_write=True)
    engine = runtime(tmp_path, [response(("a", "save", {"value": 1}))], tools=tools)
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == "unknown_write_outcome"
        assert len(tools.calls) == 1 and len(receipt["artifacts"]) == 1
        checks = [e.payload for e in engine.store.events if e.payload.event_type == "state_inspection"]
        assert checks[0].conclusion == "inconclusive"
        observed = json.loads(engine.store.get_bytes(checks[0].persisted_state))
        assert observed["observed_after"] == tools.snapshot_state()
        assert "secret fake credential" not in engine.store.path.read_text()


def test_readonly_role_rejects_entire_batch_before_write(tmp_path):
    engine = runtime(tmp_path, [response(("r", "view", {}), ("w", "save", {}))], readonly=True)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "tool_authorization_failed"
        assert engine.tools.calls == []


def test_missing_usage_is_unknown_and_stops_a_token_limited_run(tmp_path):
    engine = runtime(tmp_path, [response(text="Done", usage=False)])
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == "token_usage_unavailable"
        settlements = [e.payload.settlement for e in engine.store.events
            if e.payload.event_type == "budget" and e.payload.action == "settle"]
        assert settlements[0].actual.tokens is None
        assert settlements[0].cost.kind == "unavailable"
        assert engine.store.events[-1].payload.usage.kind == "missing"


def test_prepared_tool_image_is_not_marked_delivered_when_call_budget_stops(tmp_path):
    engine = runtime(tmp_path, [response(("v", "view", {}))],
        limits=RunLimits(model_calls=1, tool_calls=2, seconds=30.0, tokens=100_000))
    with engine.store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "model_budget_exhausted"
        tool = next(e.payload for e in engine.store.events if e.payload.event_type == "tool_execution")
        assert tool.presentation_status == "prepared" and tool.shown_result.kind == "blob"
        assert not [e for e in engine.store.events if e.payload.event_type == "tool_presentation"]


@pytest.mark.parametrize("malformed", ["call_dict", "stop_with_call", "bad_message", "truncated"])
def test_malformed_response_always_keeps_raw_event_and_never_executes_tools(tmp_path, malformed):
    raw = response(("w", "save", {"value": 3}))
    if malformed == "call_dict":
        raw["choices"][0]["message"]["tool_calls"] = {"bad": "shape"}
    elif malformed == "stop_with_call":
        raw["choices"][0]["finish_reason"] = "stop"
    elif malformed == "bad_message":
        raw["choices"][0]["message"] = 12
    else:
        raw["choices"][0]["finish_reason"] = "length"
    engine = runtime(tmp_path, [raw])
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] != "completed" and engine.tools.calls == []
        record = next(e.payload for e in engine.store.events if e.payload.event_type == "model_response")
        assert engine.store.resolve(record.raw_response) == raw


def test_resume_completed_run_does_not_append_duplicate_stop_or_usage(tmp_path):
    engine = runtime(tmp_path, [response(text="Done")])
    with engine.store:
        asyncio.run(engine.run(MESSAGES))
        before = engine.store.path.read_bytes()
    resumed = runtime(tmp_path, [], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["resume_status"] == "already_completed"
        assert resumed.store.path.read_bytes() == before


def test_resume_rejects_changed_model_profile(tmp_path, monkeypatch):
    engine = runtime(tmp_path, [response(text="Done")])
    with engine.store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "completed"

    from src.agent_runtime import loop as runtime_loop
    original = runtime_loop.get_model_profile("test")
    monkeypatch.setattr(runtime_loop, "get_model_profile", lambda *args, **kwargs:
                        replace(original, text_fixed_margin=original.text_fixed_margin + 1))
    resumed = runtime(tmp_path, [], tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "resume_configuration_changed"


@pytest.mark.parametrize(
    ("model", "configured_limit", "output_tokens", "expected"),
    [
        ("test", 200, 256, "configured_context_limit_exhausted"),
        ("Qwen3.8-27B", None, 262_144, "model_profile_context_limit_exhausted"),
    ],
)
def test_context_limits_stop_before_adapter_send(
        tmp_path, model, configured_limit, output_tokens, expected):
    limits = RunLimits(model_calls=1, tool_calls=0, seconds=30.0,
                       tokens=1_000_000, context_tokens=configured_limit)
    engine = runtime(tmp_path, [], limits=limits)
    engine.model = model
    engine.parameters["max_tokens"] = output_tokens
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == expected
        assert engine.adapter.requests == []
        assert not [event for event in engine.store.events
                    if event.payload.event_type == "adapter_request"]


def test_actual_token_overrun_preserves_full_settlement_and_exhausts_root(tmp_path):
    raw = response(text="Done")
    raw["usage"]["total_tokens"] = 1_000_000
    engine = runtime(tmp_path, [raw])
    with engine.store:
        receipt = asyncio.run(engine.run(MESSAGES))
        assert receipt["status"] == "token_budget_exhausted"
        assert receipt["reported_tokens"] == 1_000_000
        settlements = [e.payload.settlement for e in engine.store.events
                       if e.payload.event_type == "budget" and e.payload.action == "settle"]
        assert len(settlements) == 1
        assert settlements[0].actual.tokens == 1_000_000
        assert settlements[0].token_overrun > 0
        assert engine.budget.ledger.charged.tokens == 1_000_000
        assert receipt["root_budget_available"]["tokens"] == 0


def test_crash_at_safe_checkpoint_resumes_without_repeating_completed_write(tmp_path):
    class Crash(BaseException):
        pass

    engine = runtime(tmp_path, [response(("w", "save", {"value": 8}))])
    save = engine._checkpoint

    def crash_after_saved_turn():
        save()
        if engine.counts["tool_calls"]:
            raise Crash()

    engine._checkpoint = crash_after_saved_turn
    with engine.store:
        with pytest.raises(Crash):
            asyncio.run(engine.run(MESSAGES))
    resumed = runtime(tmp_path, [response(text="Continued")], tools=engine.tools)
    with resumed.store:
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert receipt["status"] == "completed"
        assert receipt["model_calls"] == 2 and len(engine.tools.calls) == 1
        assert any(e.payload.event_type == "run_lifecycle" and e.payload.action == "resume"
                   for e in resumed.store.events)


def test_answer_repair_response_replays_without_duplicate_request_or_event(tmp_path):
    class Crash(BaseException):
        pass

    invalid = '{"answer": 7})'
    corrected = '{"answer": 7}'
    engine = runtime(tmp_path, [response(text=invalid), response(text=corrected)])
    engine.answer_validator = json.loads
    engine.max_answer_repairs = 1

    def crash_after_repair_response(name, running):
        if name == "after_response" and running.counts["model_calls"] == 2:
            raise Crash()

    engine.fault_hook = crash_after_repair_response
    with engine.store:
        with pytest.raises(Crash):
            asyncio.run(engine.run(MESSAGES))

    resumed = runtime(tmp_path, [])
    resumed.answer_validator = json.loads
    resumed.max_answer_repairs = 1
    with resumed.store:
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert receipt["status"] == "completed"
        assert receipt["answer"] == corrected
        assert resumed.adapter.requests == []
        repairs = [event.payload for event in resumed.store.events
                   if event.payload.event_type == "answer_repair"]
        assert [repair.phase for repair in repairs] == ["request", "result"]
        assert repairs[-1].accepted is True
        assert len([event for event in resumed.store.events
                    if event.payload.event_type == "adapter_request"]) == 2


def test_interrupted_answer_repair_request_is_never_retried_on_resume(tmp_path):
    class Crash(BaseException):
        pass

    limits = RunLimits(model_calls=3, tool_calls=0, seconds=30.0,
                       tokens=100_000, max_model_retries=1)
    engine = runtime(tmp_path,
        [response(text='{"answer": 7}}'), response(text='{"answer": 7}')],
        limits=limits)
    engine.answer_validator = json.loads
    engine.max_answer_repairs = 1

    def crash_after_durable_repair_request(name, running):
        if name == "after_request" and running.counts["model_calls"] == 2:
            raise Crash()

    engine.fault_hook = crash_after_durable_repair_request
    with engine.store:
        with pytest.raises(Crash):
            asyncio.run(engine.run(MESSAGES))
        assert len(engine.adapter.requests) == 1

    resumed = runtime(tmp_path, [response(text='{"answer": 7}')],
                      limits=limits)
    resumed.answer_validator = json.loads
    resumed.max_answer_repairs = 1
    with resumed.store:
        receipt = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert receipt["status"] == "resume_request_outcome_unknown"
        assert resumed.adapter.requests == []
        assert len([event for event in resumed.store.events
                    if event.payload.event_type == "adapter_request"]) == 2
        repairs = [event.payload for event in resumed.store.events
                   if event.payload.event_type == "answer_repair"]
        assert [repair.phase for repair in repairs] == ["request"]


def test_resume_rejects_changed_saved_state(tmp_path):
    limits = RunLimits(model_calls=1, tool_calls=2, seconds=30.0, tokens=100_000)
    engine = runtime(tmp_path, [response(("w", "save", {"value": 7}))], limits=limits)
    with engine.store:
        asyncio.run(engine.run(MESSAGES))
    (tmp_path / "tools/saved.json").write_text('{"value":999}')
    resumed = runtime(tmp_path, [], limits=limits, tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "resume_state_changed"
        assert resumed.adapter.requests == []


def test_exact_http_wire_body_matches_recorded_bytes_and_never_logs_key(tmp_path):
    engine = runtime(tmp_path, [])
    received = []

    def handle(request):
        received.append(request.content)
        assert request.headers["authorization"] == "Bearer test-secret"
        return httpx.Response(200, json=response(text="OK", reasoning=True))

    async def exercise():
        adapter = HttpChatAdapter(base_url="https://example.invalid/v1", api_key="test-secret",
                                  transport=httpx.MockTransport(handle))
        engine.adapter = adapter
        try:
            return await engine.run(MESSAGES)
        finally:
            await adapter.close()

    with engine.store:
        result = asyncio.run(exercise())
        assert result["status"] == "completed"
        request = next(e.payload for e in engine.store.events if e.payload.event_type == "adapter_request")
        assert engine.store.get_bytes(request.final_request_body.blob) == received[0]
        assert all(b"test-secret" not in p.read_bytes() for p in engine.store.directory.rglob("*") if p.is_file())


def test_store_detects_corruption_and_torn_tail(tmp_path):
    engine = runtime(tmp_path, [response(text="OK")])
    with engine.store:
        asyncio.run(engine.run(MESSAGES))
        ref = engine.store.put_bytes(b"abc")
        (engine.store.directory / ref.uri).write_bytes(b"tampered")
        with pytest.raises(ValueError, match="hash mismatch"):
            engine.store.get_bytes(ref)
    with (tmp_path / "run/events.jsonl").open("ab") as output:
        output.write(b'{"partial":')
    with pytest.raises(ValueError, match="incomplete"):
        runtime(tmp_path, [])


@pytest.mark.parametrize("bad", [True, "10", 1.2])
def test_core_budget_does_not_coerce_noninteger_tokens(bad):
    with pytest.raises(ValidationError):
        BudgetAmounts(tokens=bad)


def test_unknown_cost_is_valid_without_money_budget_but_cannot_fake_money_limit():
    from decimal import Decimal

    reservation = BudgetReservation(reservation_id="a", purpose="primary_task", task_id="t",
                                    amounts=BudgetAmounts(tokens=100, calls=1))
    settlement = BudgetSettlement(reservation_id="a", actual=BudgetAmounts(calls=1),
        usage=UsageMissing(reason="no receipt"), cost=CostUnavailable(reason="no bill"))
    BudgetLedger(total_limit=BudgetAmounts(tokens=100, calls=1),
                 reservations=(reservation,), settlements=(settlement,))
    with pytest.raises(ValidationError, match="unknown cost cannot settle"):
        BudgetLedger(total_limit=BudgetAmounts(tokens=100, calls=1, money_usd=Decimal("1")),
            reservations=(reservation.model_copy(update={"amounts": BudgetAmounts(
                tokens=100, calls=1, money_usd=Decimal("1"))}),), settlements=(settlement,))


def test_runtime_core_imports_stay_independent_of_building_layer():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for file in (root / "src/agent_runtime").glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(), filename=str(file))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level <= 1, (file.name, "cannot import parent application")
                names = [node.module or ""] if not node.level else []
            else:
                continue
            for name in names:
                assert name not in {"src", "agent", "scripts"}, (file.name, name)
                assert not name.startswith(("src.agent.", "scripts.")), (file.name, name)
                assert name != "src.agent", (file.name, name)
