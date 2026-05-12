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

## CRITICAL: per-floor z values come from zone_specs

The user message starts with a `=== ZONE_SPECS ===` block followed by a
`=== SURFACE_SPECS ===` block. Use them this way:

- zone_specs gives you, for every zone, its `z_floor` (finished-floor level
  in absolute world coords) and its `ceiling_height` (this floor's storey
  height, can differ floor by floor — e.g. F1=3.60, F2=3.60, F3=4.80).
- surface_specs gives you the adjacency / exterior-vs-interior / construction
  / split-pairing semantics.

For every wall vertex you write:
    bottom z = z_floor of that zone
    top z    = z_floor + ceiling_height of that zone
Do NOT use a default 3 m floor height. Do NOT round z_floor down (3.60 m
stays 3.60 m, not 3 m). Different floors may have different `ceiling_height`.

For floor surfaces:    z = z_floor
For ceiling/roof:      z = z_floor + ceiling_height
For interzone floor/ceiling pair, the two zones MUST share the same z value
on the shared boundary (lower zone's ceiling z == upper zone's floor z).

Worked example. Zone `F2_S1` has `z_floor=3.60, ceiling_height=3.60` and
x-range 0..5, y-range 0..3. Its south wall (CCW from outside) has vertices:

    [
      {"X": 0.0, "Y": 0.0, "Z": 3.60},   # SW-top
      {"X": 0.0, "Y": 0.0, "Z": 3.60 + 3.60},  # ← but actually start with bottom; see below
      {"X": 5.0, "Y": 0.0, "Z": 3.60},
      {"X": 5.0, "Y": 0.0, "Z": 7.20}
    ]

(Canonical CCW-from-outside order for a south wall observed from y<0 is
top-left → bottom-left → bottom-right → top-right, so the actual order is
`(0,0,7.20) → (0,0,3.60) → (5,0,3.60) → (5,0,7.20)`. The vital point is
that bottom z = 3.60 and top z = 7.20, **not 3 and 6**.)

## Workflow

1. FIRST call `list_zones` to discover the exact zone names created by
   the zone phase.
2. THEN call `list_constructions` to discover the exact construction
   names and their layer composition (helps you match the right
   construction to each surface type — wall / floor / roof / window).
3. Create each surface via `create_surface`, reusing those names verbatim
   and using zone_specs' per-zone `z_floor` + `ceiling_height` for vertex z.
4. Call `list_surfaces` once at the end to confirm.

## Rules

- `zone_name` and `construction_name` MUST appear verbatim in the
  list_zones / list_constructions results (exact case, underscores).
- If a needed zone or construction is missing after list, STOP and
  report; do NOT invent names or create a surface with a broken reference.
- >= 3 vertices per surface; four-vertex rectangles are most common.
- Order counter-clockwise when viewed from OUTSIDE the zone.
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
- Name convention: '{zone}_{direction}_{type}', e.g.,
  'F1_Office_North_Wall', 'F1_Office_Floor', 'F1_Office_Roof'.
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

    # 2026-05-12: bundle zone_specs + surface_specs so the agent can read each
    # zone's z_floor / ceiling_height for wall vertex Z (see SURFACE_SYSTEM_PROMPT
    # "per-floor z values come from zone_specs"). Previously surface_agent only
    # saw surface_specs → defaulted to 3 m floors → upper-floor windows fell
    # outside their parent wall and EP emitted CHKSBS partial-overlap warnings.
    if state.intake_output:
        specs = (
            "=== ZONE_SPECS (read each zone's z_floor and ceiling_height) ===\n"
            f"{state.intake_output.zone_specs}\n\n"
            "=== SURFACE_SPECS (adjacency / exterior / construction / pairings) ===\n"
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
