from langchain_core.messages import AIMessage

from src.agent.llm import create_llm
from src.agent.nodes._share import invoke_with_self_repair
from src.agent.react import build_react_agent
from src.agent.state import AgentState, AgentStateUpdate
from src.agent.tools import make_surface_tools
from src.agent.trace import TraceCollector, record_phase_trace

SURFACE_SYSTEM_PROMPT = """You are a building geometry expert for EnergyPlus.
Given surface specifications + zone specifications, create all
BuildingSurface:Detailed objects (walls, floors, roofs, ceilings) with
3D vertex polygons.

Vertices MUST be a list of dicts, each with explicit X / Y / Z keys (not
a bare [x, y, z] list). Meters, in the global (world) coordinate system.

## CRITICAL: transcribe vertices verbatim from surface_specs — do NOT recompute them

The user message starts with a `=== ZONE_SPECS ===` block followed by a
`=== SURFACE_SPECS ===` block. Use them this way:

- surface_specs already lists, for every surface, its COMPLETE vertex
  polygon as absolute world-coordinate (X, Y, Z) tuples, already in
  CCW-from-outside order. This is the authoritative geometry. Copy each
  vertex's X, Y, Z straight into the `create_surface` call, IN THE SAME
  ORDER they are listed. Do NOT recompute, re-derive, reorder, round, drop,
  or add vertices. Do NOT use zone_specs' `z_floor` / `ceiling_height` to
  compute a vertex Z value — surface_specs' own Z values are already
  correct and already reflect each zone's floor level and storey height.
- zone_specs is for zone NAMES and adjacency / construction semantics only
  (e.g. confirming which zone a surface belongs to). It is NOT a source of
  vertex coordinates for surface creation.

The only "work" you do on a vertex is copy it — no arithmetic.

## Workflow

1. FIRST call `list_zones` to discover the exact zone names created by
   the zone phase.
2. THEN call `list_constructions` to discover the exact construction
   names and their layer composition (helps you match the right
   construction to each surface type — wall / floor / roof / window).
3. Create each surface via `create_surface`, reusing zone/construction
   names verbatim and transcribing surface_specs' own vertex list for
   that surface exactly (same coordinates, same order).
4. Call `list_surfaces` once at the end to confirm.

## Rules

- `zone_name` and `construction_name` MUST appear verbatim in the
  list_zones / list_constructions results (exact case, underscores).
- If a needed zone or construction is missing after list, STOP and
  report; do NOT invent names or create a surface with a broken reference.
- >= 3 vertices per surface; four-vertex rectangles are most common.
- surface_specs' vertex order is already CCW-from-outside — transcribe it
  as given; do NOT re-derive or re-sort the vertex order yourself.
- No two vertices may coincide (tolerance 1e-10 m).
- outside_boundary_condition:
    * Walls/roofs facing outdoors: 'Outdoors',
      sun_exposure='SunExposed', wind_exposure='WindExposed'
    * Floors on ground slab: 'Ground',
      sun_exposure='NoSun', wind_exposure='NoWind'
    * Internal partitions between zones: 'Surface',
      sun_exposure='NoSun', wind_exposure='NoWind',
      and outside_boundary_condition_object must reference the matching
      partner surface in the other zone
    * Adiabatic walls (e.g., between identical thermal zones): 'Adiabatic'
- surface_type is one of Wall, Floor, Roof, Ceiling (case-insensitive).
- Surface names are deterministic public names from surface_specs. Walls use
  the short zone handle plus ring order, e.g. 'Z01_W1'; horizontal faces use
  'Z01_Floor', 'Z01_Ceiling', or 'Z01_Roof' with numeric suffixes for pieces.
  Transcribe them exactly.
"""


def surface_agent(state: AgentState) -> AgentStateUpdate:
    local = state.config_state.model_copy(deep=True)
    tools = make_surface_tools(local)
    collector = TraceCollector(phase="surface")

    agent = build_react_agent(
        llm=create_llm(node_name="surface"),
        tools=tools,
        system_prompt=SURFACE_SYSTEM_PROMPT,
        trace_collector=collector,
    )

    # 2026-05-12: bundle zone_specs + surface_specs so the agent has zone
    # names/adjacency alongside the surface geometry.
    # 2026-08-06 (F-12): surface_specs already carries each surface's complete
    # absolute-world-coordinate vertex polygon (kernel-computed, CCW-from-
    # outside) — the agent transcribes those verbatim (see SURFACE_SYSTEM_PROMPT
    # "transcribe vertices verbatim from surface_specs"). zone_specs is kept
    # only for zone names / adjacency, NOT as a vertex-Z source anymore: the
    # prior "derive Z from zone_specs" instruction caused the LLM to
    # re-derive wall vertices instead of copying surface_specs' own values,
    # producing a different start-vertex/order than the deterministic kernel
    # emitted (VERTEX_FRAME_DRIFT in src/validator/output_coordinates.py).
    if state.intake_output:
        specs = (
            "=== ZONE_SPECS (zone names / adjacency only — NOT a vertex source) ===\n"
            f"{state.intake_output.zone_specs}\n\n"
            "=== SURFACE_SPECS (authoritative vertices — transcribe verbatim) ===\n"
            f"{state.intake_output.surface_specs}"
        )
    else:
        specs = state.user_input
    result = invoke_with_self_repair(agent, local, specs, phase="surface")

    final = [
        m for m in result["messages"] if isinstance(m, AIMessage) and not m.tool_calls
    ]
    summary = final[-1].content if final else "surface done"

    record_phase_trace("surface", collector.export())
    return AgentStateUpdate(
        config_state=local,
        messages=[AIMessage(content=f"[surface] {summary}")],
    )
