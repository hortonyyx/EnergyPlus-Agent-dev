"""zone_agent node tests.

F-158 (2026-09-03): the original single test drove `zone_agent` against the
**real** DeepSeek provider (`create_llm(node_name="zone")` → langchain_openai →
a billed request to api.deepseek.com). Under the no-billed-calls egress gate
(tests/conftest.py) that either fails loud (with a key, gate blocks) or errors
on the missing key (no key) — either way it must not sit in the default suite.

It is split into two:

* ``test_zone_agent_creates_two_zones`` — offline, in the default suite. The
  provider slot is replaced by a scripted fake chat model, so the test still
  exercises everything that can regress in-repo: the ``zone_agent`` node's own
  composition (create_llm slot → build_react_agent → make_zone_tools), the real
  ``create_zone`` tool mutating ``ConfigState``, the ReAct loop plumbing, result
  extraction and the tail frame-normalization. What it no longer covers is a
  *real model* interpreting the natural-language ``zone_specs`` and choosing the
  right ``create_zone`` calls/names — that dimension moves to the live test
  below (registered as dropped default coverage in the F-158 execution note).

* ``test_zone_agent_creates_two_zones_live`` — the original real-provider path,
  marked ``@pytest.mark.live`` so it is excluded from the default suite and only
  runs with ``-m live`` (and a funded key). This keeps the real-model
  integration coverage available, explicitly and opt-in.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.agent.nodes.zone import zone_agent
from src.agent.state import AgentState, IntakeOutput

_INTAKE_PAYLOAD = {
    "building": {"Name": "Test"},
    "site_location": {
        "Name": "Test",
        "Latitude": 22.5,
        "Longitude": 114.0,
        "Time Zone": 8.0,
        "Elevation": 10.0,
    },
    "zone_specs": (
        "Create two zones: Z01_F1_Office_SW (6x6m, ground floor) "
        "and Z02_F1_Corridor_N (6x2m, ground floor)."
    ),
    "material_specs": "",
    "schedule_specs": "",
    "construction_specs": "",
    "surface_specs": "",
    "fenestration_specs": "",
    "hvac_specs": "",
    "people_specs": "",
    "lights_specs": "",
}


class _ScriptedLLM(BaseChatModel):
    """Stand-in for the provider slot in ``build_react_agent``.

    ``script[i]`` is returned on the i-th ``_generate`` call. ``bind_tools`` is a
    passthrough (the behaviour under test is the node wiring + real tools, not
    tool-schema translation), so tests build ``AIMessage.tool_calls`` directly.
    No network, no provider — runs in the normal full-suite pass.
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
        return ChatResult(generations=[ChatGeneration(message=item)])

    @property
    def _llm_type(self) -> str:
        return "scripted-test-llm"


def _two_zone_script() -> list[AIMessage]:
    """A model turn that requests both zones, then a plain final turn."""
    create_calls = AIMessage(
        content="",
        id="m0",
        tool_calls=[
            {
                "name": "create_zone",
                "args": {"name": "Z01_F1_Office_SW"},
                "id": "m0_0",
                "type": "tool_call",
            },
            {
                "name": "create_zone",
                "args": {"name": "Z02_F1_Corridor_N"},
                "id": "m0_1",
                "type": "tool_call",
            },
        ],
    )
    done = AIMessage(content="Created 2 zones: Z01_F1_Office_SW, Z02_F1_Corridor_N.")
    return [create_calls, done]


def test_zone_agent_creates_two_zones(monkeypatch):
    # Replace the billed provider slot with a scripted fake — the node wiring,
    # the create_zone tool and ConfigState assembly are all still exercised.
    scripted = _ScriptedLLM(script=_two_zone_script())
    monkeypatch.setattr(
        "src.agent.nodes.zone.create_llm", lambda *a, **k: scripted
    )

    intake = IntakeOutput.model_validate(_INTAKE_PAYLOAD)
    out = zone_agent(AgentState(intake_output=intake))
    zones = out["config_state"].zones
    assert len(zones) == 2
    assert {z.name for z in zones} == {"Z01_F1_Office_SW", "Z02_F1_Corridor_N"}


@pytest.mark.live
def test_zone_agent_creates_two_zones_live():
    """Original real-provider integration path. Excluded from the default suite
    (F-158): run with `-m live` and a funded DEEPSEEK_API_KEY. Verifies a real
    model interprets the natural-language zone_specs into the two named zones."""
    intake = IntakeOutput.model_validate(_INTAKE_PAYLOAD)
    out = zone_agent(AgentState(intake_output=intake))
    zones = out["config_state"].zones
    assert len(zones) == 2
    assert {z.name for z in zones} == {"Z01_F1_Office_SW", "Z02_F1_Corridor_N"}
