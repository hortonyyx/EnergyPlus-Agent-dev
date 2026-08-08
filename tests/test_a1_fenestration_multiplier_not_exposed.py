"""A-1 (2026-08-08 interface sweep §4): `create_fenestration`'s `multiplier`
parameter was a model-visible knob the geometry kernel never consumed (the
kernel emits exactly one polygon per physical opening; `multiplier` never
appears in `geometry/specs.py` / `intakeoutput.py` / `state.py`), the
fenestration prompt never mentioned it, and no gate compared it to anything —
the vertex-drift gate only ever looked at coordinates. Fix taken (option ①,
see AI_agent/logs/reviews/request/2026-08-08_interface_sweep_round1_fixes_design.md
摊二): remove the parameter from the tool's exposed surface entirely, rather
than defaulting it to 1 or rejecting non-1 values — the model has no argument
that could carry a non-1 value at all.

This is a structural-risk fix: no run has been shown to actually emit a
non-1 multiplier. These are regression locks for "the parameter stays gone
and the underlying record stays pinned to 1", not evidence a defect ever
fired in production.
"""

import json

from src.agent._share import ensure_schema_initialized
from src.agent.tools.fenestration_tools import make_fenestration_tools
from src.mcp.state import ConfigState

ensure_schema_initialized()


def _tools(cfg: ConfigState | None = None) -> dict:
    return {t.name: t for t in make_fenestration_tools(cfg or ConfigState())}


def test_create_fenestration_tool_schema_has_no_multiplier_field():
    """Removed-即red guard for the *interface*: if `multiplier` is ever added
    back to `create_fenestration`'s signature, this must fail. Introspects
    the LangChain tool's declared args schema — not a hand-maintained list —
    so it tracks whatever the `@tool`-decorated function actually exposes."""
    tools = _tools()
    create = tools["create_fenestration"]
    assert "multiplier" not in create.args, (
        "create_fenestration must not expose a `multiplier` parameter to the "
        "model — the geometry kernel builds exactly one surface per window "
        "and never consumes it (A-1, 2026-08-08 interface sweep §4)."
    )


def test_create_fenestration_call_site_cannot_pass_multiplier():
    """Removed-即red guard for the *call path*: even if a caller tries to
    smuggle a `multiplier` kwarg through `.invoke`, the underlying function
    has no such parameter to receive it — LangChain's tool-args validation
    silently drops keys the wrapped function does not declare, so the value
    can never reach `ft.create(...)`. Prove that end-to-end: the resulting
    stored record must still land on the schema default (1), not the 5 an
    attacker/model tried to smuggle through."""
    cfg = ConfigState()
    tools = _tools(cfg)
    create = tools["create_fenestration"]
    payload = {
        "name": "Z01_W1_Win1",
        "surface_type": "Window",
        "construction_name": "GlassConstruction",
        "building_surface_name": "Z01_Wall_S",
        "vertices": [
            {"X": 1.0, "Y": 0.0, "Z": 0.8},
            {"X": 2.0, "Y": 0.0, "Z": 0.8},
            {"X": 2.0, "Y": 0.0, "Z": 2.0},
            {"X": 1.0, "Y": 0.0, "Z": 2.0},
        ],
        "multiplier": 5,
    }
    try:
        create.invoke(payload)
    except Exception:
        return  # rejecting the call outright also satisfies the lock
    # If the call was accepted (LangChain dropped the unknown key), the
    # smuggled value of 5 must not have reached the stored record.
    assert len(cfg.fenestrations) == 1
    assert cfg.fenestrations[0].multiplier == 1, (
        "a `multiplier` kwarg the model has no business passing must not "
        "reach the stored FenestrationSurfaceSchema record"
    )


def test_created_fenestration_multiplier_always_one():
    """Behavioral lock: with no `multiplier` argument available at all, every
    fenestration the tool creates must land with `Multiplier == 1` on the
    stored record (FenestrationSurfaceSchema's own default), never anything
    the model could have overridden."""
    cfg = ConfigState()
    tools = _tools(cfg)
    result = json.loads(
        tools["create_fenestration"].invoke(
            {
                "name": "Z01_W1_Win1",
                "surface_type": "Window",
                "construction_name": "GlassConstruction",
                "building_surface_name": "Z01_Wall_S",
                "vertices": [
                    {"X": 1.0, "Y": 0.0, "Z": 0.8},
                    {"X": 2.0, "Y": 0.0, "Z": 0.8},
                    {"X": 2.0, "Y": 0.0, "Z": 2.0},
                    {"X": 1.0, "Y": 0.0, "Z": 2.0},
                ],
            }
        )
    )
    assert result["success"], result
    assert len(cfg.fenestrations) == 1
    assert cfg.fenestrations[0].multiplier == 1
