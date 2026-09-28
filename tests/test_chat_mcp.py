"""Exercise real chat response shapes and MCP bytes without model inference."""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

from mcp.types import CallToolResult, ImageContent, TextContent, Tool
from openai.types.chat import ChatCompletion
import pytest

from src.agent.execution.chat_mcp import ChatBudget, run_chat_mcp
from src.configs.config import LLMConfig


CONFIG = LLMConfig(provider="openai", model_name="configured-deployment",
                   temperature=0.2, max_tokens=128, api_key="dummy")


def call(identity="c1", name="observe", arguments="{}"):
    return dict(id=identity, type="function", function=dict(name=name, arguments=arguments))


def response(calls=None, content=None, finish=None, **extra):
    return ChatCompletion.model_validate(dict(id="completion", created=0,
        object="chat.completion", model="actual-deployment",
        choices=[dict(index=0, finish_reason=finish or ("tool_calls" if calls else "stop"),
                      message=dict(role="assistant", content=content, tool_calls=calls, **extra))],
        usage=dict(prompt_tokens=20, completion_tokens=10, total_tokens=30)))


class Client:
    max_retries = 0

    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=self)

    async def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


class Session:
    def __init__(self, result=None):
        self.result = result or CallToolResult(content=[TextContent(type="text", text="receipt-ok")])
        self.calls = []

    async def list_tools(self, cursor=None):
        return SimpleNamespace(nextCursor=None, tools=[Tool(name="observe", inputSchema={"type": "object"})])

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        return self.result


def run(client, session=None, **kwargs):
    return asyncio.run(run_chat_mcp(client, session or Session(), config=CONFIG,
        messages=[dict(role="user", content="Complete the supplied task.")],
        allowed_tools={"observe"}, budget=kwargs.pop("budget", ChatBudget(3, 3, 30)),
        image_input=kwargs.pop("image_input", True), **kwargs))


def test_multiple_tool_ids_precede_images_and_explicit_reasoning_echo():
    raw = b"synthetic-image-bytes"
    result = CallToolResult(content=[TextContent(type="text", text="numbers 37 and 84"),
        ImageContent(type="image", mimeType="image/png", data=base64.b64encode(raw).decode())],
        structuredContent={"source": "synthetic"})
    client = Client([response([call("a"), call("b")], reasoning_content="private-transport-field"),
                     response(content="done")])
    events = []
    receipt = run(client, Session(result), assistant_echo_fields=("reasoning_content",), record=events.append)
    assert receipt["response_completed"] and receipt["model_calls"] == 2
    history = client.requests[1]["messages"]
    assert [r["role"] for r in history] == ["user", "assistant", "tool", "tool", "user"]
    assert [r["tool_call_id"] for r in history[2:4]] == ["a", "b"]
    assert history[1]["reasoning_content"] == "private-transport-field"
    assert "private-transport-field" not in json.dumps(events)
    blocks = history[-1]["content"]
    for index, identity in ((0, "a"), (2, "b")):
        assert f"tool_call_id={identity}" in blocks[index]["text"]
        assert base64.b64decode(blocks[index + 1]["image_url"]["url"].split(",", 1)[1]) == raw
    assert json.loads(history[2]["content"])["structuredContent"] == {"source": "synthetic"}
    assert receipt["images"][0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["actual_models"] == ["actual-deployment"]
    assert receipt["usage_complete"]
    assert sum(r["usage"]["total_tokens"] for r in receipt["responses"]) == 60


def test_tool_error_returns_to_model_without_claiming_tool_success():
    session = Session(CallToolResult(isError=True, content=[TextContent(type="text", text="invalid shape")]))
    client = Client([response([call()]), response(content="Unable to complete the geometry.")])
    receipt = run(client, session)
    assert receipt["response_completed"]  # Transport completion, not task quality.
    assert json.loads(client.requests[1]["messages"][-1]["content"])["isError"] is True


@pytest.mark.parametrize("calls", [
    [call("a"), call("a")],
    [call("a"), call("b", name="unconfigured")],
    [call("a"), call("b", arguments="[]")],
    [call("a"), call("b", arguments="broken json")],
])
def test_invalid_batch_executes_no_mutations(calls):
    session = Session()
    receipt = run(Client([response(calls)]), session)
    assert receipt["status"] == "failed"
    assert session.calls == []


def test_tool_budget_rejects_whole_batch_and_model_budget_stops():
    session = Session()
    receipt = run(Client([response([call("a"), call("b")])]), session,
                  budget=ChatBudget(2, 1, 30))
    assert receipt["status"] == "tool_budget_exhausted" and session.calls == []
    client = Client([response([call()])])
    receipt = run(client, budget=ChatBudget(1, 2, 30))
    assert receipt["status"] == "model_budget_exhausted"
    assert receipt["model_calls"] == len(client.requests) == 1
    assert not receipt["response_completed"]


def test_truncated_tool_call_never_executes():
    session = Session()
    receipt = run(Client([response([call()], finish="length")]), session)
    assert receipt["status"] == "incomplete_response" and session.calls == []


def test_http_error_stops_without_retry_or_exposing_error_body():
    class QuotaError(Exception):
        status_code = 429
    client = Client([QuotaError("private-key-do-not-log")])
    receipt = run(client)
    assert receipt["http_status"] == 429 and receipt["status"] == "failed"
    assert len(client.requests) == 1 and not receipt["usage_complete"]
    assert "private-key" not in json.dumps(receipt)


def test_timeout_and_default_sdk_retries_cannot_escape_budget():
    class SlowSession(Session):
        async def call_tool(self, name, args):
            await asyncio.sleep(1)
    receipt = run(Client([response([call()])]), SlowSession(), budget=ChatBudget(2, 2, 0.02))
    assert receipt["status"] == "timed_out"
    client = Client([])
    client.max_retries = 2
    with pytest.raises(ValueError, match="max_retries=0"):
        run(client)
    assert client.requests == []


def test_image_incompatible_deployment_stops_explicitly():
    session = Session(CallToolResult(content=[ImageContent(type="image", mimeType="image/png", data="aGk=")]))
    receipt = run(Client([response([call()])]), session, image_input=False)
    assert receipt["status"] == "failed" and not receipt["response_completed"]


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan"), True])
def test_time_budget_must_be_finite_positive(seconds):
    with pytest.raises(ValueError):
        ChatBudget(1, 1, seconds)


def test_real_sdk_serializes_exact_tool_images_without_network():
    import httpx
    from openai import AsyncOpenAI
    sent = []
    replies = [response([call()]), response(content="received tool image")]

    def handle(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json=replies[len(sent) - 1].model_dump(mode="json"))

    async def scenario():
        http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        async with AsyncOpenAI(api_key="offline-dummy", base_url="https://example.invalid/v1",
                               max_retries=0, http_client=http) as client:
            result = CallToolResult(content=[ImageContent(type="image", mimeType="image/png", data="aGk=")])
            return await run_chat_mcp(client, Session(result), config=CONFIG,
                messages=[dict(role="user", content="test")], allowed_tools={"observe"},
                budget=ChatBudget(2, 1, 10), image_input=True)

    receipt = asyncio.run(scenario())
    assert receipt["response_completed"] and len(sent) == 2
    assert sent[1]["messages"][-2]["tool_call_id"] == "c1"
    assert sent[1]["messages"][-1]["content"][1]["image_url"]["url"] == "data:image/png;base64,aGk="
    assert all(r["max_tokens"] == 128 and r["model"] == CONFIG.model_name for r in sent)


def test_real_bim_mcp_image_and_saved_geometry(tmp_path):
    # Actual stdio MCP and geometry; only the model responses are synthetic.
    from tests.test_bim_agent_tools import _run_with_one_image, _server_session
    run_dir = _run_with_one_image(tmp_path)
    plan = dict(floor_id="F1", z_floor=0, ceiling_height=3,
        x_anchors=[[0, 0], [11, 11]], y_anchors=[[0, 7], [7, 0]], basis="synthetic test",
        footprint_pixels=[[1, 1], [10, 1], [10, 6], [1, 6]],
        partitions=[dict(id="wall", points=[[5, 1], [5, 6]], source_refs=["synthetic"])],
        openings=[dict(id="door", kind="door", p1=[5, 3], p2=[5, 4], z=[0, 2], source_refs=["synthetic"])],
        assumptions=[], unresolved=[])
    client = Client([
        response([call("view", "view_image", json.dumps(dict(name="plan.png", coordinate_grid=False)))]),
        response([call("build", "build_plan_bim", json.dumps(dict(image="plan.png", plan_json=json.dumps(plan))))]),
        response(content="Saved the synthetic two-room model."),
    ])

    async def scenario():
        async with _server_session(run_dir, readonly=False) as session:
            return await run_chat_mcp(client, session, config=CONFIG,
                messages=[dict(role="user", content="synthetic transport check")],
                allowed_tools={"view_image", "build_plan_bim"},
                budget=ChatBudget(3, 2, 60), image_input=True)

    receipt = asyncio.run(scenario())
    assert receipt["response_completed"], receipt
    source = json.loads((run_dir / "candidate_01/source_model.json").read_text())
    assert len(source["spaces"]) == 2 and len(source["connections"]) == 1
    assert (run_dir / "candidate_01/viewer.html").is_file()
    assert receipt["tool_calls"] == 2 and len(receipt["images"]) >= 1
    image_blocks = client.requests[1]["messages"][-1]["content"]
    actual = base64.b64decode(image_blocks[1]["image_url"]["url"].split(",", 1)[1])
    assert hashlib.sha256(actual).hexdigest() == receipt["images"][0]["sha256"]
    assert len(client.requests) == 3
