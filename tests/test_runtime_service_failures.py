"""Offline transport diagnostics and conservative Responses SSE retry policy."""

import asyncio
import json

import httpx
import pytest

from src.agent_runtime.failures import (ModelServiceError, classify_failure,
    http_failure, service_diagnostics, transport_diagnostics)
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.responses import HttpResponsesAdapter
from src.harness_contracts.events import ModelFailureDetails
from test_agent_runtime import MESSAGES
from test_runtime_responses import completed, prepare, provider, response, send, sse, store
from test_runtime_responses_integration import engine_for, native
from test_runtime_responses_integration import metered_native


@pytest.mark.parametrize("kind", ["response.failed", "error", "flat_error"])
@pytest.mark.parametrize("error,category,retryable", [
    ({"type": "service_unavailable_error", "code": "server_is_overloaded"}, "service_unavailable", True),
    ({"code": "server_is_overloaded", "headers": {"x-retry-metadata": "NO_MORE_RETRY"}}, "service_unavailable", False),
    ({"code": "server_is_overloaded", "headers": {"X-Retry-Metadata": "unverified_hint"}}, "service_unavailable", False),
    ({"code": "server_is_overloaded", "headers": {"x-retry-metadata": {"unexpected": True}}}, "service_unavailable", False),
    ({"type": "server_error", "message": "overloaded, please retry"}, "service_error", False),
    ({"type": "service_unavailable_error"}, "service_error", False),
    ({"type": "insufficient_quota", "code": "server_is_overloaded"}, "quota_exhausted", False),
    ({"type": "authentication_error", "code": "server_is_overloaded"}, "permission_denied", False),
    ({"type": "service_unavailable_error", "code": "context_length_exceeded"}, "context_length_exceeded", False),
])
def test_sse_classification_uses_structured_evidence_and_hint_veto(store, kind, error, category, retryable):
    event = ({"type": kind, "response": {"error": error}} if kind == "response.failed" else
             {"type": "error", **error} if kind == "flat_error" else {"type": kind, "error": error})
    # Flat error's envelope type is a protocol tag, not the error's type.
    if kind == "flat_error":
        event["type"] = "error"
        if error.get("type") in {"insufficient_quota", "authentication_error"}:
            event["code"] = error["type"]
    adapter = HttpResponsesAdapter(token_provider=provider(), transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=sse(event), headers={"x-request-id": "req-offline"})))
    with pytest.raises(ModelServiceError) as caught:
        send(adapter, prepare(store))
    failure = classify_failure(caught.value, "request-offline")
    assert failure.category == category and failure.retryable is retryable
    assert failure.request_id == "req-offline" and failure.http_status is None
    assert failure.usage_received is False and caught.value.usage.kind == "missing"
    assert failure.service_error_code == event.get("code", error.get("code"))
    assert ModelFailureDetails.model_validate_json(failure.model_dump_json()) == failure


def test_service_projection_omits_arbitrary_messages_headers_and_requests(store):
    token = "test-oauth-private"
    error = {"type": "service_unavailable_error", "code": "server_is_overloaded",
        "message": "https://user:password@example.invalid/?token=foreign-token",
        "headers": {"authorization": "Bearer other-secret", "cookie": "session=secret",
                    "x-retry-metadata": "NO_MORE_RETRY"},
        "request": {"input": "private prompt and image data"}, "request_id": token}
    adapter = HttpResponsesAdapter(token_provider=provider(token), transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=sse({"type": "error", "error": error}),
                                      headers={"x-request-id": "Bearer " + token})))
    with pytest.raises(ModelServiceError) as caught:
        send(adapter, prepare(store))
    failure = classify_failure(caught.value, "request-offline")
    saved = failure.model_dump_json()
    for secret in (token, "other-secret", "session=secret", "foreign-token", "private prompt", "password@example"):
        assert secret not in saved
    assert failure.request_id == "[redacted]" and failure.retry_hint == "NO_MORE_RETRY"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("error_type,phase", [(httpx.ConnectTimeout, "connect"),
    (httpx.ReadTimeout, "read"), (httpx.WriteError, "write"), (httpx.PoolTimeout, "pool"),
    (httpx.RemoteProtocolError, "awaiting_response_headers")])
def test_transport_types_and_cause_chain_survive_without_exception_messages(store, error_type, phase):
    def handle(request):
        try:
            raise ConnectionResetError("credential=private-cause; https://user:pass@example.invalid/")
        except ConnectionResetError as cause:
            raise error_type("Authorization: Bearer private-top", request=request) from cause
    adapter = HttpResponsesAdapter(token_provider=provider(), transport=httpx.MockTransport(handle))
    with pytest.raises(ModelServiceError) as caught:
        send(adapter, prepare(store))
    failure = classify_failure(caught.value, "request-offline")
    assert failure.transport_phase == phase
    assert failure.exception_chain == (f"httpx.{error_type.__name__}", "builtins.ConnectionResetError")
    assert failure.retryable is True and failure.usage_received is False
    assert "private" not in failure.model_dump_json() and "example.invalid" not in failure.model_dump_json()
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("hint", [None, "NO_MORE_RETRY"])
def test_stream_failure_records_read_phase_and_header_id_with_unknown_usage(store, hint):
    class Interrupted(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse({"type": "response.in_progress", "response": response(status="in_progress")})
            raise httpx.ReadError("do not log this")
    headers = {"x-request-id": "req-stream"}
    if hint:
        headers["x-retry-metadata"] = hint
    adapter = HttpResponsesAdapter(token_provider=provider(), transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=Interrupted(), headers=headers)))
    with pytest.raises(ModelServiceError) as caught:
        send(adapter, prepare(store))
    failure = classify_failure(caught.value, "request-offline")
    assert failure.transport_phase == "read" and failure.exception_chain == ("httpx.ReadError",)
    assert failure.request_id == "req-stream"
    assert failure.retry_hint == hint and failure.retryable is (hint is None)
    assert caught.value.usage.kind == "missing" and caught.value.observed_usage.kind == "reported"


def test_exception_chain_is_cycle_safe_and_old_events_remain_readable():
    first, second = httpx.ConnectError("secret"), OSError("secret")
    first.__cause__, second.__cause__ = second, first
    assert transport_diagnostics(first)["exception_chain"] == ("httpx.ConnectError", "builtins.OSError")
    old = ModelFailureDetails.model_validate_json(json.dumps({"request_event_id": "request-1",
        "category": "transport_error", "retryable": True, "usage_received": False}))
    assert old.exception_chain == () and old.service_error_code is None and old.retry_hint is None


def test_http_hint_veto_and_projection_preserve_numeric_usage_without_raw_payload():
    failure = http_failure(httpx.Response(503, json={"error": {"code": "server_is_overloaded",
        "message": "private content", "request": {"Authorization": "Bearer secret"}},
        "usage": {"input_tokens": 12, "output_tokens": 2, "total_tokens": 14}},
        headers={"X-Retry-Metadata": "NO_MORE_RETRY", "X-Request-ID": "req-http"}), secret="secret")
    saved = classify_failure(failure, "request-1")
    assert saved.retryable is False and saved.http_status == 503
    assert saved.service_error_code == "server_is_overloaded" and saved.retry_hint == "NO_MORE_RETRY"
    assert saved.request_id == "req-http" and failure.usage.raw_usage["total_tokens"] == 14
    assert "private content" not in saved.model_dump_json() and "secret" not in saved.model_dump_json()


def test_no_more_retry_wins_conflicting_hints_and_numeric_service_codes_are_preserved():
    details = service_diagnostics({"code": 1305, "headers": {"x-retry-metadata": "unknown"}},
                                  headers={"X-Retry-Metadata": " no_more_retry "})
    assert details["retry_hint"] == "NO_MORE_RETRY" and details["service_error_code"] == "1305"


@pytest.mark.parametrize("hint,repeat,status,requests", [(None, False, "completed", 4),
    (None, True, "model_retries_exhausted:service_unavailable", 3),
    ("NO_MORE_RETRY", False, "service_unavailable", 2),
    ("UNVERIFIED", False, "service_unavailable", 2)])
def test_runtime_sse_retries_are_bounded_and_never_execute_failed_stream_tools(tmp_path, hint, repeat, status, requests):
    seen = []
    error = {"type": "service_unavailable_error", "code": "server_is_overloaded"}
    if hint:
        error["headers"] = {"x-retry-metadata": hint}
    def handle(request):
        seen.append(request.content)
        if len(seen) == 1:
            return httpx.Response(200, content=sse(completed(native(("image", "view", {})))))
        if len(seen) == 2 or repeat:
            partial = native(("never_execute", "save", {"private": "partial"}), usage=False)
            partial["status"] = "in_progress"
            failed = {"object": "response", "status": "failed", "error": error}
            return httpx.Response(200, content=sse({"type": "response.in_progress", "response": partial},
                {"type": "response.failed", "response": failed}), headers={"x-request-id": "req-failed"})
        raw = native(("once", "save", {"value": 3})) if len(seen) == 3 else native(text="Done")
        return httpx.Response(200, content=sse(completed(raw)))
    limits = RunLimits(model_calls=5, tool_calls=5, seconds=90, tokens=None,
                       max_model_retries=1, retry_backoff_seconds=0.001)
    engine = engine_for(tmp_path, [], limits=limits)
    engine.adapter = HttpResponsesAdapter(token_provider=provider(), transport=httpx.MockTransport(handle))
    async def run():
        try:
            return await engine.run(MESSAGES)
        finally:
            await engine.adapter.close()
    with engine.store:
        result = asyncio.run(run())
        assert result["status"] == status and len(seen) == requests
        assert [name for name, args in engine.tools.calls] == (["view", "save"] if status == "completed" else ["view"])
        missing = [e.payload.settlement for e in engine.store.events
            if e.payload.event_type == "budget" and e.payload.action == "settle" and e.payload.settlement.usage.kind == "missing"]
        assert len(missing) == (2 if repeat else 1)
        assert all(s.actual.tokens is None and s.reported_usage_includes_image_tokens is False
                   and s.image_tokens_estimate > 0 for s in missing)
        assert result["usage_complete"] is False
        failures = [e.payload.model_failure for e in engine.store.events
                    if e.payload.event_type == "run_lifecycle" and e.payload.model_failure]
        assert all(f.service_error_code == "server_is_overloaded" and f.request_id == "req-failed" for f in failures)
        assert not any(e.payload.event_type == "run_lifecycle" and e.payload.reason == "invalid_settlement"
                       for e in engine.store.events)
        engine.store.validate()


def context_veto_engine(tmp_path, hint, protocol="http", *, tools=None):
    limits = RunLimits(model_calls=5, tool_calls=2, seconds=90, tokens=500000)
    engine = engine_for(tmp_path, [], limits=limits, **({"tools": tools} if tools else {}))
    seen = []
    def handler(request):
        seen.append(json.loads(request.content))
        if len(seen) == 3:
            reason = {"code": "context_length_exceeded"}
            headers = {"x-retry-metadata": hint} if hint else {}
            if protocol == "http":
                return httpx.Response(400, json={"error": reason}, headers=headers)
            reason["headers"] = headers
            return httpx.Response(200, content=sse({"type": "error", "error": reason}))
        raw = (metered_native(("saved_once", "save", {"value": 8}), input_tokens=1000) if len(seen) == 1
               else metered_native(("last_view", "view", {}), input_tokens=5000) if len(seen) == 2
               else metered_native(text="Recovered", input_tokens=2000))
        return httpx.Response(200, content=sse(completed(raw)))
    engine.adapter = HttpResponsesAdapter(token_provider=provider(), transport=httpx.MockTransport(handler))
    return engine, seen


async def run_and_close(engine, *, resume=False):
    try:
        return await engine.run(MESSAGES, resume=resume)
    finally:
        await engine.adapter.close()


@pytest.mark.parametrize("hint", [None, "NO_MORE_RETRY", "UNVERIFIED"])
@pytest.mark.parametrize("protocol", ["http", "sse"])
def test_context_reorganization_respects_hint_veto_without_repeating_tools(tmp_path, hint, protocol):
    engine, seen = context_veto_engine(tmp_path, hint, protocol)
    with engine.store:
        result = asyncio.run(run_and_close(engine))
        assert result["status"] == ("context_recovery_required" if hint else "completed")
        assert result["model_calls"] == len(seen) == (3 if hint else 4)
        assert [name for name, args in engine.tools.calls] == ["save", "view"]
        assert sum(e.payload.event_type == "context" and e.payload.action == "compact"
                   for e in engine.store.events) == (0 if hint else 1)
        failure = next(e.payload.model_failure for e in engine.store.events
                       if e.payload.event_type == "run_lifecycle" and e.payload.model_failure)
        assert failure.retry_hint == hint and failure.retryable is False
        missing = [e.payload.settlement for e in engine.store.events
                   if e.payload.event_type == "budget" and e.payload.action == "settle"
                   and e.payload.settlement.usage.kind == "missing"]
        assert len(missing) == 1 and missing[0].actual.tokens is None
        engine.store.validate()


@pytest.mark.parametrize("hint", [None, "NO_MORE_RETRY", "UNVERIFIED"])
def test_rate_limit_redispatch_respects_hint_veto_with_zero_failure_retries(tmp_path, monkeypatch, hint):
    from test_agent_runtime import runtime, response as chat_response
    from test_runtime_dispatch import policy, HttpChatAdapterForTest
    policy(monkeypatch, initial_concurrency=1, max_concurrency=1)
    seen = []
    def handler(request):
        seen.append(request.content)
        return (httpx.Response(429, json={"error": {"code": "1302"}},
                              headers={"x-retry-metadata": hint} if hint else {})
                if len(seen) == 1 else httpx.Response(200, json=chat_response(text="Done")))
    engine = runtime(tmp_path, [], limits=RunLimits(model_calls=3, tool_calls=0, seconds=30,
                     tokens=None, max_model_retries=0))
    engine.adapter = HttpChatAdapterForTest(handler)
    with engine.store:
        result = asyncio.run(run_and_close(engine))
        assert result["status"] == ("temporary_rate_limit" if hint else "completed")
        assert result["model_calls"] == len(seen) == (1 if hint else 2)
        assert result["retries"] == 0 and not engine.tools.calls
        assert (any(engine._redispatch_parent(e) for e in engine.store.events
                    if e.payload.event_type == "adapter_request")) is (hint is None)
        engine.store.validate()


@pytest.mark.parametrize("hint", [None, "NO_MORE_RETRY", "UNVERIFIED"])
def test_resume_compacted_context_checkpoint_cannot_override_retry_hint(tmp_path, hint):
    from test_runtime_recovery_edges import InjectedCrash
    engine, seen = context_veto_engine(tmp_path, hint)
    settle = engine._settle
    def legacy_checkpoint(*args, **kwargs):
        result = settle(*args, **kwargs)
        if len(seen) == 3:
            # Reproduce a durable checkpoint from the former bypass, with
            # a smaller projection and retry_of already set despite the hint.
            failure = next(e.payload.model_failure for e in reversed(engine.store.events)
                           if e.payload.event_type == "run_lifecycle" and e.payload.model_failure)
            assert engine._compact_before_retry(*engine._project()[:2]) is not None
            engine.retry_of = failure.request_event_id
            engine._checkpoint()
            raise InjectedCrash("legacy context retry ready")
        return result
    engine._settle = legacy_checkpoint
    with engine.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(run_and_close(engine))
    resumed = engine_for(tmp_path, [metered_native(text="Recovered", input_tokens=2000)],
                         limits=engine.limits, tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == ("context_recovery_required" if hint else "completed")
        assert len(resumed.adapter.requests) == (0 if hint else 1)
        assert [name for name, args in engine.tools.calls] == ["save", "view"]
        assert sum(e.payload.event_type == "context" and e.payload.action == "compact"
                   for e in resumed.store.events) == 1
        resumed.store.validate()


@pytest.mark.parametrize("hint", [None, "NO_MORE_RETRY", "UNVERIFIED"])
def test_resume_rate_checkpoint_veto_wins_even_if_old_failure_says_retryable(tmp_path, monkeypatch, hint):
    from test_agent_runtime import runtime, response as chat_response
    from test_runtime_dispatch import policy
    from test_runtime_recovery_edges import InjectedCrash
    policy(monkeypatch)
    failure = http_failure(httpx.Response(429, json={"error": {"code": "1302"}},
        headers={"x-retry-metadata": hint} if hint else {}), secret="", provider="glm")
    # Defensive recovery of an inconsistent historical/injected retry decision.
    failure.details["retryable"] = True
    limits = RunLimits(model_calls=3, tool_calls=0, seconds=30, tokens=None, max_model_retries=0)
    engine = runtime(tmp_path, [failure], limits=limits)
    settle = engine._settle
    def legacy_checkpoint(*args, **kwargs):
        settle(*args, **kwargs)
        failed_request = next(e.payload.model_failure.request_event_id for e in reversed(engine.store.events)
                              if e.payload.event_type == "run_lifecycle" and e.payload.model_failure)
        engine.redispatch_of = failed_request
        engine._checkpoint()
        raise InjectedCrash("legacy rate redispatch ready")
    engine._settle = legacy_checkpoint
    with engine.store:
        with pytest.raises(InjectedCrash):
            asyncio.run(engine.run(MESSAGES))
    resumed = runtime(tmp_path, [chat_response(text="Done")], limits=limits, tools=engine.tools)
    with resumed.store:
        result = asyncio.run(resumed.run(MESSAGES, resume=True))
        assert result["status"] == ("temporary_rate_limit" if hint else "completed")
        assert len(resumed.adapter.requests) == (0 if hint else 1)
        assert result["retries"] == 0 and not resumed.tools.calls
        resumed.store.validate()
