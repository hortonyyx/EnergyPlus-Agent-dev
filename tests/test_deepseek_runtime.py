"""Offline official DeepSeek route, image/tool history and request validation."""
import asyncio
import json

import httpx
import pytest

from src.agent_runtime.adapter import HttpChatAdapter
from src.agent_runtime.connections import resolve_connection
from src.agent_runtime.failures import ModelServiceError
from src.agent_runtime.providers import provider_parameters, validate_provider_model
from test_agent_runtime import MESSAGES, response, runtime


def credentials(tmp_path, base="https://api.deepseek.com"):
    path = tmp_path / "deepseek.env"
    path.write_text(f"DEEPSEEK_BASE_URL={base}\nDEEPSEEK_API_KEY=fixture-secret\n")
    return path


def test_credentials_are_explicit_isolated_and_never_redirected(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-must-not-be-used")
    with pytest.raises(ValueError, match="explicit existing"):
        resolve_connection("deepseek", None, model="deepseek-flash")
    with pytest.raises(ValueError, match="official HTTPS"):
        resolve_connection("deepseek", credentials(tmp_path, "https://unreviewed.invalid"), model="deepseek-flash")
    route = resolve_connection("deepseek", credentials(tmp_path), model="deepseek-flash")
    assert route.descriptor.route_id == "deepseek" and route.descriptor.billing_mode == "metered"
    assert "fixture-secret" not in repr(route)
    assert "fixture-secret" not in route.descriptor.model_dump_json()

    async def scenario():
        seen = []
        def handler(request):
            seen.append(request)
            assert str(request.url) == "https://api.deepseek.com/chat/completions"
            assert request.headers["authorization"] == "Bearer fixture-secret"
            return httpx.Response(307, headers={"location": "https://unreviewed.invalid"})
        adapter = HttpChatAdapter(base_url=route.descriptor.base_url, api_key=route.api_key,
                                  transport=httpx.MockTransport(handler))
        from types import SimpleNamespace
        with pytest.raises(ModelServiceError) as error:
            await adapter.send(SimpleNamespace(wire_bytes=b"{}"), timeout=5)
        assert len(seen) == 1 and "fixture-secret" not in str(error.value)
        await adapter.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("kwargs", [{"reasoning_effort": "medium"}, {"temperature": 0},
    {"thinking": False, "reasoning_effort": "high"}, {"output_tokens": 400000}])
def test_unsupported_parameters_fail_before_requests(kwargs):
    with pytest.raises(ValueError):
        provider_parameters("deepseek", model="deepseek-flash", **{"output_tokens": 32000, **kwargs})


def test_model_identity_and_role_config_require_explicit_provider(tmp_path):
    from src.agent.runtime_configuration import argv_for, load_configuration
    from test_role_configuration import case, configuration, role, ROLE_NAMES
    for provider, model in [("paratera", "deepseek-flash"), ("deepseek", "deepseek-v4-pro")]:
        with pytest.raises(ValueError, match="DeepSeek"):
            validate_provider_model(provider, model)
    selected = case()
    selected.update(provider="deepseek", model="deepseek-flash", reasoning_effort="high",
                    credentials_file=str(credentials(tmp_path)))
    selected["roles"] = {name: role("deepseek", "deepseek-flash", "high") for name in ROLE_NAMES}
    path = tmp_path / "configuration.json"
    path.write_text(json.dumps(configuration(selected)))
    loaded = load_configuration(path)["cases"][0]
    command = argv_for(loaded)
    assert command[command.index("--provider") + 1] == "deepseek"
    assert all(row["model"] == "deepseek-flash" for row in loaded["roles"].values())


def deepseek_engine(tmp_path):
    replies = [response(("view-1", "view", {}), reasoning=True), response(text="Done", reasoning=True)]
    for reply in replies:
        reply["usage"]["prompt_cache_hit_tokens"] = 12
    engine = runtime(tmp_path, replies)
    engine.model = "deepseek-flash"
    engine.parameters = provider_parameters("deepseek", model=engine.model, output_tokens=32000)
    engine.strict_model_profile = True
    engine.versions = engine.versions.model_copy(update={"remote_model": engine.versions.remote_model.model_copy(
        update={"route_id": "deepseek", "remote_alias": engine.model})})
    return engine


def test_actual_runtime_replays_reasoning_and_tool_image_without_resizing(tmp_path):
    engine = deepseek_engine(tmp_path)
    with engine.store:
        result = asyncio.run(engine.run(MESSAGES))
        assert result["status"] == "completed" and result["model_calls"] == 2
        assert result["reported_tokens"] == 60
        assert result["billing_usd"] is None and result["estimated_cost_cny"] is None
        requests = [e.payload for e in engine.store.events if e.payload.event_type == "adapter_request"]
        for sent, captured in zip(engine.adapter.requests, requests):
            assert sent == engine.store.capture_bytes(captured.final_request_body)
            body = json.loads(sent)
            assert body["thinking"] == {"type": "enabled"} and body["reasoning_effort"] == "high"
            assert "enable_thinking" not in body and "temperature" not in body and "n" not in body
        second = json.loads(engine.adapter.requests[1])
        assert next(m for m in second["messages"] if m["role"] == "assistant")["reasoning_content"] == "Public protocol test explanation."
        assert [m["role"] for m in second["messages"][-2:]] == ["tool", "user"]
        assert requests[1].images[0].original.sha256 == requests[1].images[0].sent.sha256
        from src.agent_runtime.estimation import estimate_chat_request
        estimate = estimate_chat_request(second, strict=True)
        assert estimate.image_tokens == 1024 and estimate.context_window_tokens == 1048576
        assert estimate.images[0].width == estimate.images[0].resized_width == 4
        from src.agent_runtime.accounting import request_accounting_from_store
        records = [request_accounting_from_store(engine.store, e.event_id).accounting
                   for e in engine.store.events if e.payload.event_type == "adapter_request"]
        assert all(r.reported_cache_read_tokens == 12 for r in records)
        assert records[1].budget_charge_tokens == 30 and records[1].additional_image_tokens == 0
        engine.store.validate()


def test_partial_reasoning_history_is_rejected_without_send(tmp_path):
    engine = deepseek_engine(tmp_path)
    engine.reasoning_history = "current_tool_chain"
    with engine.store, pytest.raises(ValueError, match="reasoning_history=all"):
        asyncio.run(engine.run(MESSAGES))
    assert not engine.adapter.requests
