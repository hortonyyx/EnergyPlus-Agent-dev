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
from src.agent.nodes.surface import SURFACE_SYSTEM_PROMPT
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
    # The workflow must actually tell it to call the batch tool for ALL
    # surfaces, not merely mention the tool's existence in passing.
    assert "ALL surfaces via `create_surfaces_batch`" in SURFACE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# A7 positive lock: batch build of N == N individual builds, byte-equivalent.
# ---------------------------------------------------------------------------


def test_create_surfaces_batch_equivalent_to_individual_calls():
    items = [_wall(f"Z01_W{i}", y=float(i)) for i in range(12)]

    cfg_batch = ConfigState()
    batch_tool = _tools(cfg_batch)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": items}))
    assert result["success"], result
    assert result["data"]["count"] == 12
    assert len(result["data"]["succeeded"]) == 12
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
    """Same lock at a scale closer to the real 100-surface case."""
    items = [_wall(f"Z01_W{i}", y=float(i)) for i in range(100)]
    cfg = ConfigState()
    batch_tool = _tools(cfg)["create_surfaces_batch"]
    result = json.loads(batch_tool.invoke({"items": items}))
    assert result["success"], result
    assert result["data"]["count"] == 100
    assert len(result["data"]["succeeded"]) == 100
    assert len(cfg.surfaces) == 100


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
