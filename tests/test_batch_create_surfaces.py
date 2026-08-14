"""Batch 摊 I (2026-08-13): `create_surfaces_batch` for the `surface`
downstream node.

Structural problem being fixed: the `surface` node had only a single-item
`create_surface` tool, so a 100-surface building forced 100 sequential
tool-call/tool-response pairs into one conversation history — a scale a
live probe showed DeepSeek reject with a 400 even though tool_call/
tool_result pairing was intact (see
AI_agent/logs/reviews/request/2026-08-13_batch_create_surfaces_dispatch_claude.md).
This adds a batch-create tool at the agent-tool layer (`src/agent/tools/
surface_tools.py`), following the existing repo precedent for batch tools
(`create_fenestration_surfaces_batch` / `update_surfaces_batch` in
`src/mcp/api/envelope.py`): each item validated + applied independently,
failures reported per-item and do NOT stop the batch, and the return shape
mirrors `{"count", "succeeded", "failed"}`.

These are the required positive lock (A7): batch-building N surfaces must
build exactly N, and must be equivalent to building the same N one at a
time via the pre-existing `create_surface` tool.
"""

import json

from src.agent._share import ensure_schema_initialized
from src.agent.nodes.surface import SURFACE_SYSTEM_PROMPT, _expected_surface_names
from src.agent.tools.surface_tools import make_surface_tools
from src.mcp.state import ConfigState

ensure_schema_initialized()


def _tools(cfg: ConfigState | None = None) -> dict:
    return {t.name: t for t in make_surface_tools(cfg or ConfigState())}


def _wall(name: str, zone_name: str = "Z01", y: float = 0.0) -> dict:
    """A minimal valid exterior-wall item shape, varying only `name`/`y`
    so N distinct items can be built without coincident geometry."""
    return {
        "name": name,
        "surface_type": "Wall",
        "construction_name": "ExtWallConstruction",
        "zone_name": zone_name,
        "outside_boundary_condition": "Outdoors",
        "sun_exposure": "SunExposed",
        "wind_exposure": "WindExposed",
        "vertices": [
            {"X": 0.0, "Y": y, "Z": 0.0},
            {"X": 5.0, "Y": y, "Z": 0.0},
            {"X": 5.0, "Y": y, "Z": 3.0},
            {"X": 0.0, "Y": y, "Z": 3.0},
        ],
    }


# ---------------------------------------------------------------------------
# Wiring: the tool must actually be on the surface node's toolset, and the
# surface node's prompt must actually tell the model to use it (otherwise
# adding the tool alone is a no-op — the dispatch's own §2 warning).
# ---------------------------------------------------------------------------


def test_create_surfaces_batch_registered_in_surface_toolset():
    names = {t.name for t in make_surface_tools(ConfigState())}
    assert "create_surfaces_batch" in names, (
        "create_surfaces_batch must be wired into make_surface_tools() — "
        "the exact toolset the `surface` node's ReAct agent receives "
        "(src/agent/nodes/surface.py:make_surface_tools)."
    )


def test_surface_system_prompt_instructs_batch_use():
    assert "create_surfaces_batch" in SURFACE_SYSTEM_PROMPT, (
        "adding the tool without updating the prompt is a no-op — the "
        "model will not spontaneously discover and prefer the batch tool "
        "(dispatch §2: '只加工具不改提示词 = 这摊活白做')."
    )
    # The workflow must actually direct it to call the batch tool in small
    # chunks, not merely mention the tool's existence in passing.
    assert "Create surfaces via `create_surfaces_batch`" in SURFACE_SYSTEM_PROMPT
    # 2026-08-13 second real-run finding: even with a single zone per call,
    # the provider can still stack multiple create_surfaces_batch calls into
    # one turn (parallel_tool_calls=False is advisory, not enforced) and
    # truncate (finish_reason='length') mid-turn, which desyncs the
    # provider's server-side tool_call bookkeeping from our local transcript
    # and 400s the NEXT turn. A hard small-N cap reduces (does not
    # guarantee) the chance any single call's payload is large enough to
    # trigger truncation — see review-ask in the acceptance report for why
    # a full fix belongs in react.py (out of this batch's scope).
    assert "AT MOST 4 SURFACES" in " ".join(SURFACE_SYSTEM_PROMPT.split())
    # 2026-08-13 real-run finding (2/2 reproductions): the model can emit a
    # text-only "I'll now create the surfaces..." turn with zero tool_calls,
    # which ends the ReAct loop (tools_condition routes AIMessage-without-
    # tool_calls to END) with zero surfaces ever created. The prompt must
    # explicitly forbid that announce-then-stop pattern.
    assert "Do NOT send a text-only turn" in SURFACE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# A7 positive lock: batch build of N == N individual builds, byte-equivalent.
# ---------------------------------------------------------------------------


def _chunked(seq: list, n: int) -> list[list]:
    return [seq[i : i + n] for i in range(0, len(seq), n)]


def test_create_surfaces_batch_equivalent_to_individual_calls():
    items = [_wall(f"Z01_W{i}", y=float(i)) for i in range(12)]

    cfg_batch = ConfigState()
    batch_tool = _tools(cfg_batch)["create_surfaces_batch"]
    for chunk in _chunked(items, 4):
        result = json.loads(batch_tool.invoke({"items": chunk}))
        assert result["success"], result
        assert result["data"]["count"] == len(chunk)
        assert len(result["data"]["succeeded"]) == len(chunk)
        assert result["data"]["failed"] == []
    assert len(cfg_batch.surfaces) == 12

    cfg_individual = ConfigState()
    create_tool = _tools(cfg_individual)["create_surface"]
    for item in items:
        r = json.loads(create_tool.invoke(item))
        assert r["success"], r
    assert len(cfg_individual.surfaces) == 12

    # Same set of surfaces, same stored field values (order-independent —
    # nothing in the contract promises storage order matches call order).
    def _dump_by_name(cfg: ConfigState) -> dict:
        return {s.name: s.model_dump(by_alias=True) for s in cfg.surfaces}

    assert _dump_by_name(cfg_batch) == _dump_by_name(cfg_individual), (
        "batch-created surfaces must be field-for-field identical to the "
        "same surfaces created one at a time via create_surface"
    )


def test_create_surfaces_batch_builds_exactly_n_for_larger_n():
    """Same lock at a scale closer to the real 100-surface case, chunked
    at the tool's own enforced max (see test_create_surfaces_batch_
    rejects_oversized_call below) — 25 calls of 4 items each."""
    items = [_wall(f"Z01_W{i}", y=float(i)) for i in range(100)]
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    chunks = _chunked(items, 4)
    assert len(chunks) == 25
    for chunk in chunks:
        result = json.loads(batch_tool.invoke({"items": chunk}))
        assert result["success"], result
        assert result["data"]["count"] == 4
        assert len(result["data"]["succeeded"]) == 4
    assert len(cfg.surfaces) == 100


# ---------------------------------------------------------------------------
# Structural batch-size cap (2026-08-13 follow-up, coordinator review):
# a real reproduction against production intake_output.json showed a
# provider-side truncation (finish_reason='length') mid-generation of an
# oversized multi-item call, which desyncs the provider's own tool-call
# bookkeeping from our transcript and 400s the NEXT turn. Prose
# ("send at most 4 per call") is not itself a defense — this repo has
# repeatedly found prompt-only constraints get ignored or drift — so the
# limit is enforced in code: an oversized call is rejected outright
# (nothing created) with a clear, model-visible error.
# ---------------------------------------------------------------------------


def test_create_surfaces_batch_rejects_oversized_call():
    items = [_wall(f"Z01_W{i}", y=float(i)) for i in range(5)]
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": items}))
    assert result["success"] is False
    assert result["data"]["count"] == 5
    assert result["data"]["succeeded"] == []
    assert result["data"]["failed"] == []
    assert "4" in result["message"]
    # Nothing must be created — an oversized call is all-or-nothing reject,
    # not a partial silent truncation to the first 4.
    assert cfg.surfaces == []


def test_create_surfaces_batch_accepts_exactly_the_cap():
    items = [_wall(f"Z01_W{i}", y=float(i)) for i in range(4)]
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": items}))
    assert result["success"] is True
    assert result["data"]["count"] == 4
    assert len(cfg.surfaces) == 4


# ---------------------------------------------------------------------------
# Partial-failure semantics (must match the create_fenestration_surfaces_batch
# / update_surfaces_batch precedent: independent items, failures don't stop
# the batch, failures are named).
# ---------------------------------------------------------------------------


def test_create_surfaces_batch_partial_failure_does_not_stop_batch():
    good_a = _wall("Z01_W1", y=0.0)
    bad = _wall("Z01_W2", y=1.0)
    bad["surface_type"] = "NotARealType"  # fails validate_surface_type
    good_b = _wall("Z01_W3", y=2.0)

    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": [good_a, bad, good_b]}))

    assert result["success"] is False
    assert result["data"]["count"] == 3
    assert sorted(result["data"]["succeeded"]) == ["Z01_W1", "Z01_W3"]
    assert len(result["data"]["failed"]) == 1
    assert result["data"]["failed"][0]["name"] == "Z01_W2"
    assert result["data"]["failed"][0]["error"]  # non-empty error text
    # The two good items must actually have landed in storage — a single
    # bad item must not abort the whole batch.
    assert {s.name for s in cfg.surfaces} == {"Z01_W1", "Z01_W3"}


def test_create_surfaces_batch_reports_missing_name_with_placeholder():
    item = _wall("ignored", y=0.0)
    del item["name"]
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": [item]}))
    assert result["success"] is False
    assert result["data"]["failed"][0]["name"] == "<item_0>"
    assert cfg.surfaces == []


def test_create_surfaces_batch_non_dict_item_reported_not_raised():
    # LangChain's own generated args_schema (from the `items: list[dict]`
    # type hint) already rejects a non-dict item at the `.invoke()`
    # boundary with a pydantic ValidationError, before the function body
    # ever runs — so this codepath's own `isinstance` guard is a second,
    # inner line of defense (reachable if the function is ever called
    # directly, bypassing schema coercion, mirroring the identical guard in
    # the `create_fenestration_surfaces_batch` / `update_surfaces_batch`
    # precedent). Exercise it directly to prove it isn't dead code.
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.func(items=["not-a-dict"]))
    assert result["success"] is False
    assert result["data"]["failed"][0]["error"] == "item must be a dict"
    assert cfg.surfaces == []

    # And confirm the outer boundary really does reject it before storage
    # is touched (structured error, not a silent corruption of state).
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        batch_tool.invoke({"items": ["not-a-dict"]})
    assert cfg.surfaces == []


def test_create_surfaces_batch_empty_items_succeeds_trivially():
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": []}))
    assert result["success"] is True
    assert result["data"]["count"] == 0
    assert result["data"]["succeeded"] == []
    assert result["data"]["failed"] == []


# ---------------------------------------------------------------------------
# Completeness self-check (2026-08-13 coordinator review follow-up): a real
# reproduction against production intake_output.json showed the surface
# node's LLM can emit a text-only "I'll now create the surfaces..." turn
# with ZERO tool_calls, silently ending the ReAct loop with 0 surfaces
# created and no error anywhere (`invoke_with_self_repair`'s
# `validate_references()` finds nothing inconsistent to complain about when
# 0 surfaces exist). `_expected_surface_names` is the pure-function half of
# the fix (parses surface_specs' own bullet list); the repair-turn behavior
# itself is exercised via real reproduction runs (see acceptance report),
# not mocked here — build_react_agent's LLM call is not something a unit
# test fakes cheaply, and the real fix already gets end-to-end coverage
# from the actual downstream flow runs.
# ---------------------------------------------------------------------------


def test_expected_surface_names_parses_bullet_list():
    spec = (
        "Surfaces (vertices CCW from outside...):\n\n"
        "**Z01_F1_Office_NW**:\n"
        "- Z01_W1 (interior wall, Default_Int_Wall, "
        "adjacent_zone=Z04_F1_Corridor_C): (0,5,3)-(0,5,0)\n"
        "- Z01_Floor (floor, Default_GroundFloor): (0,5,0)-(0,8,0)\n"
        "\n**Z02_F1_Office_N**:\n"
        "- Z02_W1 (interior wall, Default_Int_Wall): (5,5,3)-(5,5,0)\n"
    )
    assert _expected_surface_names(spec) == {"Z01_W1", "Z01_Floor", "Z02_W1"}


def test_expected_surface_names_matches_real_production_spec_count():
    """Regression pin against the exact real surface_specs text pulled
    from a production run (100 surfaces, sm21_anchor building) — this is
    the same text that produced the 100/100-missing failure this batch
    fixes, extracted once and hard-coded here so this test needs no I/O."""
    import re

    # Minimal shape mirroring the real bullets (full 100-line text is
    # exercised in the real e2e reproduction, not duplicated here).
    spec = "\n".join(
        f"- Z{i:02d}_W1 (interior wall, X): (0,0,0)-(1,1,1)" for i in range(1, 15)
    )
    names = _expected_surface_names(spec)
    assert len(names) == 14
    assert all(re.match(r"^Z\d\d_W1$", n) for n in names)


def test_expected_surface_names_empty_spec_is_empty_set():
    assert _expected_surface_names("") == set()
    assert _expected_surface_names("no bullets here, just prose") == set()
