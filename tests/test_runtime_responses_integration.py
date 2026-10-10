"""Offline full runtime, native Responses history, controls and billing isolation."""

import asyncio
import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from src.agent.runtime_entry import parser, runtime_model_profile
from src.agent.runtime_roles.config import load_roles
from src.agent_runtime.connections import resolve_connection, validate_connection_model
from src.agent_runtime.context import ContextPolicy
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.providers import CHATGPT_SUBSCRIPTION as ROUTE, provider_parameters
from test_agent_runtime import MESSAGES, runtime
from test_runtime_recovery_edges import InjectedCrash


def native(*calls, text=None, incomplete=False, usage=True):
    output = [{"type": "reasoning", "id": "rs_fixture", "summary": [],
               "encrypted_content": "opaque-retained-state"}]
    output += [{"type": "function_call", "id": "fc_" + cid, "call_id": cid,
                "namespace": "runtime", "name": name, "arguments": json.dumps(args),
                "status": "completed"} for cid, name, args in calls]
    if text is not None:
        output.append({"type": "message", "id": "msg_fixture", "role": "assistant",
            "status": "completed", "content": [{"type": "output_text", "text": text, "annotations": []}]})
    raw = {"object": "response", "id": "resp_fixture", "model": "gpt-6-astra",
           "status": "incomplete" if incomplete else "completed", "output": output}
    if incomplete:
        raw["incomplete_details"] = {"reason": "max_output_tokens"}
    if usage:
        raw["usage"] = {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30,
            "input_tokens_details": {"cached_tokens": 12}, "output_tokens_details": {"reasoning_tokens": 6}}
    return raw


def engine_for(tmp_path, responses, **kwargs):
    engine = runtime(tmp_path, responses, **kwargs)
    engine.model = "gpt-6-astra"
    engine.parameters = provider_parameters(ROUTE, output_tokens=32000, reasoning_effort="low")
    engine.versions = engine.versions.model_copy(update={"remote_model":
        engine.versions.remote_model.model_copy(update={"route_id": ROUTE, "remote_alias": engine.model})})
    engine.context_policy = ContextPolicy()
    return engine


def test_responses_round_trip_runtime_tools_images_and_exact_journal(tmp_path):
    engine = engine_for(tmp_path, [native(("v", "view", {}), ("s", "save", {"value": 8})), native(text="Done")])
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed" and result["tool_calls"] == 2
        assert result["reported_tokens"] == 60
        assert result["usage_accounting"]["reported_cache_read_tokens"] == 24
        assert result["usage_accounting"]["billing_modes"] == ["subscription"]
        assert result["usage_accounting"]["budget_charge_tokens"] == 60
        assert result["estimated_cost_cny"] is None and result["billing_usd"] is None
        assert result["subscription_output_policy"]["service_output_cap"] is None
        bodies = [json.loads(w) for w in engine.adapter.requests]
        assert all(b["stream"] is True and b["store"] is False for b in bodies)
        assert all(not ({"messages", "max_tokens", "max_output_tokens", "temperature", "previous_response_id"} & b.keys()) for b in bodies)
        assert any(i.get("encrypted_content") == "opaque-retained-state" for i in bodies[1]["input"])
        assert {i["call_id"] for i in bodies[1]["input"] if i.get("type") == "function_call_output"} == {"v", "s"}
        requests = [e.payload for e in engine.store.events if e.payload.event_type == "adapter_request"]
        assert len(requests[1].images) == 1
        for event, wire in zip(requests, engine.adapter.requests, strict=True):
            assert engine.store.capture_bytes(event.final_request_body) == wire
        shown = [e.payload for e in engine.store.events if e.payload.event_type == "tool_presentation"]
        assert len(shown) == 2 and all(p.protocol_conversion == "responses_v1" for p in shown)
        engine.store.validate()


@pytest.mark.parametrize("truncated", [False, True])
def test_native_checkpoint_restart_preserves_items_and_does_not_repeat_write(tmp_path, truncated):
    first = native(("save_once", "save", {"value": 1}), incomplete=truncated)
    limits = RunLimits(model_calls=3, tool_calls=3, seconds=90, tokens=500000)
    engine = engine_for(tmp_path, [first], limits=limits)
    def crash(boundary, _):
        if boundary == "after_response":
            raise InjectedCrash(boundary)
    engine.fault_hook = crash
    with engine.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(engine.run(MESSAGES))
    resumed = engine_for(tmp_path, [native(text="Recovered")], limits=limits, tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == "completed" and result["model_calls"] == 2
        assert len(engine.tools.calls) == (0 if truncated else 1)
        body = json.loads(resumed.adapter.requests[0])
        assert (first["output"][0] in body["input"]) is not truncated
        assert result["truncations"] == int(truncated)
        resumed.store.validate()


def test_missing_usage_stops_without_executing_write_or_fallback(tmp_path):
    engine = engine_for(tmp_path, [native(("x", "save", {"value": 1}), usage=False)])
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "token_usage_unavailable"
        assert result["model_calls"] == 1 and result["tool_calls"] == 0
        assert result["fallback"] is False and not result["usage_complete"]


def test_local_output_allowance_does_not_claim_server_enforcement(tmp_path):
    engine = engine_for(tmp_path, [native(text="Done")])
    engine.limits = engine.limits.model_copy(update={"near_limit": "reduce_output"})
    with engine.store, pytest.raises(ValueError, match="local only"):
        asyncio.run(engine.run(MESSAGES))
    assert not engine.adapter.requests


def test_subscription_rejects_unsupported_opaque_reasoning_trim(tmp_path):
    engine = engine_for(tmp_path, [])
    engine.reasoning_history = "current_tool_chain"
    with engine.store, pytest.raises(ValueError, match="reasoning_history=all"):
        asyncio.run(engine.run(MESSAGES))
    assert not engine.adapter.requests


@pytest.mark.parametrize("effort", ["none", "minimal"])
def test_subscription_rejects_unreviewed_reasoning_effort(effort):
    with pytest.raises(ValueError, match="reviewed ChatGPT models"):
        provider_parameters(ROUTE, output_tokens=32000, reasoning_effort=effort)


def test_subscription_refuses_currency_budget_even_in_direct_runtime(tmp_path):
    limits = RunLimits(model_calls=1, tool_calls=0, seconds=30, tokens=100000, money_usd=Decimal("1"))
    engine = engine_for(tmp_path, [], limits=limits)
    with engine.store, pytest.raises(ValueError, match="metered API"):
        asyncio.run(engine.run(MESSAGES))
    assert not engine.adapter.requests


def test_subscription_connection_ignores_api_keys_and_validates_catalog(monkeypatch, tmp_path):
    from src.agent_runtime import openai_subscription
    monkeypatch.setenv("OPENAI_API_KEY", "paid-key-must-not-be-used")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://wrong.invalid")
    created = []
    class Credentials:
        def __init__(self, directory):
            created.append(directory)
        async def get_access_token(self):
            return "subscription-only-token"
        async def list_models(self):
            return [SimpleNamespace(slug="gpt-6-astra")]
    monkeypatch.setattr(openai_subscription, "SubscriptionCredentials", Credentials)
    connection = resolve_connection(ROUTE, tmp_path / "must-not-read.env", chatgpt_auth_dir=tmp_path / "auth")
    assert created == [tmp_path / "auth"] and connection.api_key == ""
    assert connection.descriptor.billing_mode == "subscription"
    assert connection.descriptor.base_url == "https://api.openai.com/v1"
    asyncio.run(validate_connection_model(connection, "gpt-6-astra"))
    with pytest.raises(ValueError, match="catalog"):
        asyncio.run(validate_connection_model(connection, "not-granted"))


def test_single_and_role_entrypoints_admit_subscription_without_codex():
    args = parser().parse_args(["--out", "unused", "--provider", ROUTE, "--model", "gpt-6-astra"])
    assert args.credentials_file is None
    assert runtime_model_profile(ROUTE, args.model).context_window_tokens == 1050000
    config = {"provider": ROUTE, "model": "gpt-6-astra", "output_tokens": 32000, "reasoning_effort": "low"}
    roles = load_roles({name: copy.deepcopy(config) for name in ("coordinator", "plan_reader", "elevation_reader")})
    assert all(role.provider == ROUTE for role in roles.values())


@pytest.mark.parametrize("mode", ["single_model", "role_division"])
def test_subscription_configuration_needs_no_paid_credentials(tmp_path, mode):
    from test_role_configuration import case, load
    from src.agent.runtime_configuration import argv_for
    value = case(mode)
    value.update(provider=ROUTE, model="gpt-6-astra", reasoning_effort="low")
    value.pop("credentials_file")
    value["chatgpt_auth_dir"] = str(tmp_path / "auth")
    if mode == "role_division":
        value["roles"] = {name: {"provider": ROUTE, "model": "gpt-6-astra",
            "reasoning_effort": "low", "output_tokens": 32000}
            for name in ("coordinator", "plan_reader", "elevation_reader")}
    command = argv_for(load(tmp_path, value)["cases"][0])
    assert "--credentials-file" not in command and "--chatgpt-auth-dir" in command


def test_external_coordinator_rejects_subscription_before_credentials(tmp_path):
    from test_role_configuration import case, load
    value = case("external_coordinator_mcp")
    value.update(provider=ROUTE, model="gpt-6-astra", reasoning_effort="low")
    value.pop("credentials_file")
    with pytest.raises(ValueError, match="external_coordinator_mcp is not supported"):
        load(tmp_path, value)


def test_sse_transport_runtime_executes_only_completed_tool_batches(tmp_path):
    from src.agent_runtime.responses import HttpResponsesAdapter
    responses = [native(("v", "view", {})), native(text="HTTP stream done")]
    requests = []
    async def token():
        return "fake-private-oauth"
    def handler(request):
        assert request.url == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == "Bearer fake-private-oauth"
        requests.append(json.loads(request.content))
        body = {"type": "response.completed", "response": responses[len(requests) - 1]}
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
            text="event: response.completed\ndata: " + json.dumps(body) + "\n\n")
    engine = engine_for(tmp_path, [])
    engine.adapter = HttpResponsesAdapter(token_provider=token, transport=httpx.MockTransport(handler))
    async def scenario():
        try:
            return await engine.run(MESSAGES)
        finally:
            await engine.adapter.close()
    with engine.store:
        result = asyncio.run(scenario())
        assert result["status"] == "completed" and result["tool_calls"] == 1
        assert len(requests) == 2
        engine.store.validate()
    for path in engine.store.directory.rglob("*"):
        if path.is_file():
            assert b"fake-private-oauth" not in path.read_bytes()


@pytest.mark.parametrize("terminal", ["timeout", "failed"])
def test_stream_partial_usage_retained_without_claiming_final_accounting(tmp_path, terminal):
    from src.agent_runtime.responses import HttpResponsesAdapter
    class InterruptedStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            partial = native(("partial", "save", {"value": 5}))
            partial["status"] = "in_progress"
            yield ("data: " + json.dumps({"type": "response.in_progress", "response": partial}) + "\n\n").encode()
            if terminal == "timeout":
                await asyncio.Event().wait()
            else:
                yield b'data: {"type":"response.failed","response":{"object":"response","status":"failed","error":{"type":"server_error"}}}\n\n'
    async def token():
        return "fake-oauth"
    engine = engine_for(tmp_path, [])
    engine.request_timeout_seconds = 0.1
    engine.adapter = HttpResponsesAdapter(token_provider=token, transport=httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=InterruptedStream())))
    async def scenario():
        try:
            return await engine.run(MESSAGES)
        finally:
            await engine.adapter.close()
    with engine.store:
        result = asyncio.run(scenario())
        assert result["status"] == ("time_budget_exhausted" if terminal == "timeout" else "service_error")
        assert result["tool_calls"] == 0 and result["model_calls"] == 1
        assert result["usage_complete"] is False
        evidence = [source for event in engine.store.events for source in event.source_refs
                    if source.source_id == "observed-stream-usage"]
        assert len(evidence) == 1
        observed = json.loads(engine.store.get_bytes(evidence[0].blob))
        assert observed["completeness"] == "unknown"
        assert observed["usage"]["raw_usage"]["total_tokens"] == 30
        engine.store.validate()
