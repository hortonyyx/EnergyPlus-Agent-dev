"""F-26 (2026-08-13): downstream ReAct-loop LLM call resilience.

Real-run investigation (`AI_agent/logs/reviews/request/
2026-08-13_downstream_surface_break_dispatch_claude.md`) found the `surface`
node crashing the whole `flow --with-ep` run with a provider 400
("insufficient tool messages following tool_calls message"). A live repro
against deepseek-v4-pro (the `surface`/`construction`/`fenestration` model)
showed the mechanism: at least one turn returned **28** `tool_calls` in a
single `AIMessage` despite `bind_tools(..., parallel_tool_calls=False)`, and
the LOCAL message history stayed perfectly paired (0 unpaired ids, 0
duplicate ids, 30/30 tool_calls matched by ToolMessages) right up to the
failing call — the provider's own turn validator is what broke on the next
request, not our wiring. `src/agent/react.py` preserves every provider-
emitted tool call so `ToolNode` can reply to every id, and wraps the LLM call
in a bounded retry that leaves diagnostic evidence instead of silently
propagating a bare provider error through the whole flow.

These tests exercise both mechanisms against a scripted fake `BaseChatModel`
— no network, no real provider — so they run in the normal full-suite pass.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from src.agent.react import (
    MAX_LLM_CALL_ATTEMPTS,
    ReactLLMCallError,
    ReactState,
    _preserve_all_tool_calls,
    _message_pairing_summary,
    build_react_agent,
)


class _ScriptedLLM(BaseChatModel):
    """Test double standing in for the provider slot in `build_react_agent`.

    `script[i]` is consulted on the i-th `_generate()` call: an `AIMessage`
    is returned as-is (lets a test hand back >1 tool_calls in one turn, the
    exact shape the real deepseek-v4-pro run produced), an `Exception`
    instance is raised instead (simulates a transient provider/transport
    failure). `bind_tools` is a passthrough: tests build `AIMessage.tool_calls`
    directly rather than relying on real tool-schema binding, since the
    behavior under test lives entirely in `llm_node`, not in tool-schema
    translation.
    """

    script: list[Any]
    calls: int = 0

    def bind_tools(self, tools: Any, *, tool_choice: Any = None, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: Any,
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        item = self.script[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return ChatResult(generations=[ChatGeneration(message=item)])

    @property
    def _llm_type(self) -> str:
        return "scripted-test-llm"


@tool
def noop_a(x: int) -> str:
    """Record a call to tool a."""
    return f"a:{x}"


@tool
def noop_b(x: int) -> str:
    """Record a call to tool b."""
    return f"b:{x}"


def _ai_with_calls(call_specs: list[tuple[str, dict]], *, msg_id: str) -> AIMessage:
    return AIMessage(
        content="",
        id=msg_id,
        tool_calls=[
            {"name": name, "args": args, "id": f"{msg_id}_{i}", "type": "tool_call"}
            for i, (name, args) in enumerate(call_specs)
        ],
    )


# ---------------------------------------------------------------------------
# _preserve_all_tool_calls: pure-function unit tests
# ---------------------------------------------------------------------------


def test_preserve_all_tool_calls_keeps_multi_call_response():
    response = _ai_with_calls(
        [("noop_a", {"x": 1}), ("noop_b", {"x": 2}), ("noop_a", {"x": 3})],
        msg_id="m1",
    )
    result = _preserve_all_tool_calls(response, phase="test")
    assert result is response
    assert [call["id"] for call in result.tool_calls] == ["m1_0", "m1_1", "m1_2"]


def test_preserve_all_tool_calls_passthrough_for_single_call():
    response = _ai_with_calls([("noop_a", {"x": 1})], msg_id="m2")
    result = _preserve_all_tool_calls(response, phase="test")
    assert result is response  # identity: no copy made when already <= 1


def test_preserve_all_tool_calls_passthrough_for_no_calls():
    response = AIMessage(content="done", id="m3")
    result = _preserve_all_tool_calls(response, phase="test")
    assert result is response
    assert result.tool_calls == []


# ---------------------------------------------------------------------------
# Wiring-level lock: prove build_react_agent's live path preserves every id,
# not just the standalone function (08-11 lesson: a pure-function assertion
# alone would pass even if llm_node stopped calling it).
# ---------------------------------------------------------------------------


def test_multi_call_turn_answers_every_id_through_the_real_graph_wiring():
    """The provider-shaped failure mode, replayed end-to-end.

    Turn 1 returns 2 tool_calls in one AIMessage (mirrors the real deepseek
    behavior with parallel_tool_calls=False). The ReAct graph must execute
    both and send one ToolMessage for each id before its next LLM turn.
    """
    first_turn = _ai_with_calls([("noop_a", {"x": 1}), ("noop_b", {"x": 2})], msg_id="t1")
    final_turn = AIMessage(content="done", id="t2")
    llm = _ScriptedLLM(script=[first_turn, final_turn])
    agent = build_react_agent(llm=llm, tools=[noop_a, noop_b], system_prompt="test")

    result = agent.invoke(ReactState(messages=[]))

    tool_messages = [m for m in result["messages"] if type(m).__name__ == "ToolMessage"]
    assert [(message.tool_call_id, message.content) for message in tool_messages] == [
        ("t1_0", "a:1"),
        ("t1_1", "b:2"),
    ]
    # Exactly two LLM turns: the batch, then the final no-tool-calls turn.
    # A cap-to-one regression makes this assertion fail with only t1_0.
    assert llm.calls == 2


# ---------------------------------------------------------------------------
# Bounded retry + evidence-on-exhaustion
# ---------------------------------------------------------------------------


def test_llm_call_retries_on_transient_failure_then_succeeds(monkeypatch):
    monkeypatch.setattr("src.agent.react.time.sleep", lambda _seconds: None)
    final_turn = AIMessage(content="done", id="ok")
    llm = _ScriptedLLM(
        script=[
            RuntimeError("transient connection reset"),
            RuntimeError("transient connection reset"),
            final_turn,
        ]
    )
    assert MAX_LLM_CALL_ATTEMPTS >= 3, "test assumes at least 3 attempts are allowed"
    agent = build_react_agent(llm=llm, tools=[noop_a], system_prompt="test")

    result = agent.invoke(ReactState(messages=[]))

    assert llm.calls == 3  # 2 failures + 1 success, all within budget
    assert result["messages"][-1].content == "done"


def test_llm_call_raises_react_llm_call_error_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("src.agent.react.time.sleep", lambda _seconds: None)
    llm = _ScriptedLLM(
        script=[RuntimeError(f"boom {i}") for i in range(MAX_LLM_CALL_ATTEMPTS + 2)]
    )
    agent = build_react_agent(llm=llm, tools=[noop_a], system_prompt="test")

    with pytest.raises(ReactLLMCallError) as excinfo:
        agent.invoke(ReactState(messages=[]))

    # bounded: never called more than the declared attempt budget, even
    # though the script has more failures queued up than that.
    assert llm.calls == MAX_LLM_CALL_ATTEMPTS
    # evidence, not a swallowed/bare exception: the message-pairing summary
    # is attached so a crash is diagnosable (which node, message-history
    # shape) instead of just the provider's own error text.
    message = str(excinfo.value)
    assert "total messages" in message
    assert "unpaired tool_call_ids" in message
    assert "boom" in message  # underlying provider error preserved
    assert excinfo.value.__cause__ is not None  # `raise ... from last_exc`


def test_llm_call_does_not_retry_forever_when_every_attempt_fails(monkeypatch):
    """Never-ending failures still terminate — no silent infinite loop."""
    monkeypatch.setattr("src.agent.react.time.sleep", lambda _seconds: None)
    llm = _ScriptedLLM(script=[RuntimeError("always fails")] * 1000)
    agent = build_react_agent(llm=llm, tools=[noop_a], system_prompt="test")

    with pytest.raises(ReactLLMCallError):
        agent.invoke(ReactState(messages=[]))

    assert llm.calls == MAX_LLM_CALL_ATTEMPTS


# ---------------------------------------------------------------------------
# _message_pairing_summary: evidence-content unit tests
# ---------------------------------------------------------------------------


def test_message_pairing_summary_flags_unpaired_tool_call():
    dangling = _ai_with_calls([("noop_a", {"x": 1})], msg_id="d1")
    summary = _message_pairing_summary([dangling])
    assert "unpaired tool_call_ids at end: ['d1_0']" in summary


def test_message_pairing_summary_flags_multi_call_turn():
    multi = _ai_with_calls([("noop_a", {"x": 1}), ("noop_b", {"x": 2})], msg_id="m")
    summary = _message_pairing_summary([multi])
    assert "multi-call turns" in summary
    assert "m_0" in summary and "m_1" in summary


def test_message_pairing_summary_reports_clean_pairing_as_empty():
    from langchain_core.messages import ToolMessage

    ai = _ai_with_calls([("noop_a", {"x": 1})], msg_id="c")
    tm = ToolMessage(content="a:1", tool_call_id="c_0")
    summary = _message_pairing_summary([ai, tm])
    assert "unpaired tool_call_ids at end: []" in summary
    assert "DUPLICATE tool_call ids within AIMessage.tool_calls: {}" in summary
    assert "DUPLICATE tool_call_id across ToolMessages: {}" in summary


def test_message_pairing_summary_includes_content_lengths_and_finish_reason():
    ai = _ai_with_calls([("noop_a", {"x": 1})], msg_id="metadata")
    ai.response_metadata["finish_reason"] = "tool_calls"
    from langchain_core.messages import ToolMessage

    summary = _message_pairing_summary([ai, ToolMessage(content="done", tool_call_id="metadata_0")])

    assert "content_len=0 finish_reason='tool_calls'" in summary
    assert "ToolMessage id=None content_len=4 tool_call_id=metadata_0" in summary
