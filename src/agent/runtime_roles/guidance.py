"""Role-specific drawing guidance derived from the unchanged single-model text."""

from __future__ import annotations

import hashlib
import json

from scripts.tool_scripts.bim_agent_guidance import CORE, DRAWING_METHOD, build_guide
from src.agent.runtime_roles.readers import READER_TOOL_NAMES
from .plan_format import COMMON_ROOM_TYPES, READER_PLAN_EXAMPLE
from .submission import WALL_REFERENCE_EXAMPLE


def _numbered_sections() -> dict[int, str]:
    starts = []
    for number in range(1, 7):
        marker = f"\n{number}. "
        index = DRAWING_METHOD.find(marker)
        if index < 0:
            raise RuntimeError(f"unchanged drawing guidance is missing section {number}")
        starts.append((number, index + 1))
    result = {}
    for offset, (number, start) in enumerate(starts):
        end = starts[offset + 1][1] - 1 if offset + 1 < len(starts) else len(DRAWING_METHOD)
        result[number] = DRAWING_METHOD[start:end].strip()
    return result


_SECTIONS = _numbered_sections()

_SHARED_READER_SCOPE = """You are one drawing reader. You receive exactly one original image and a located task.
Use only that image and its returned views, profiles and regions. Do not inspect another
image, change the parent building draft, assemble floors, match facades, or deliver the
whole building. Match the assigned task.target: a plan floor ID, or facade[/floor IDs].
Original-image coordinates are [left, top, right, bottom] pixels."""

_PLAN_CORE = """Preserve actual spaces, walls, doors/windows and connectivity. Never move or shorten
an opening just to clear a host error; recheck its wall and endpoints. Acceptance is not
drawing fidelity. Label assumptions and unresolved marks; choose room uses after geometry.
Keep stable IDs. World x is East, y North by the north arrow, z Up and absolute. These
directions cannot be changed by task instructions; follow the arrow and record conflicts
in unresolved. Use task.coordinate_contract for floor and origin. Every plan POINT is an ORIGINAL
image pixel [x, y]: footprint_pixels, partitions[].points, openings[].p1/p2,
space_seeds[].point and each anchor's first value, read from grid labels or crop origin +
original_pixels_per_returned_pixel, never world metres or display pixels. Metres appear
only as each anchor's second value, z_floor, ceiling_height and opening z."""

_PLAN_CALIBRATION = (_SECTIONS[3]
    .replace("Use one origin for all floors", "Use the coordinator's assigned floor origin")
    .replace("geometry_feedback.axis_orientation reports a mirrored calibration.",
             "axis_orientation reports the effective directions."))

_PLAN_DRAFT = """4. DRAFT THIS FLOOR EARLY. Once the overall dimension chains and divider lines are read,
call trial_plan_bim with a complete plan; its overlay and drawing_differences show where
to look closer. Until a trial returns source_geometry_ready=true, every format/compile
failure can be followed by another full plan, without a hash or change declaration.
Complete minimum example (plan_partition format at image scale):
{example}
Replace the synthetic values with drawing observations. Use partitions[].points,
openings[].p1/p2 and space_seeds[].point, not walls, room polygons or opening room/space_id/
facade fields. Seeds lie inside rooms and name them; they never create walls. A seed role
is optional: omit it or use a room_types code ({room_types}...).
Do not repeat the exterior footprint as partitions; a divider meeting an exterior wall ends
ON the footprint line (same pixel line), not at that wall's inner face. Exterior
doors/windows lie ON the footprint line; interior doors/open passages lie ON their partition. Partitions continue
through door apertures; junction coordinates coincide. No automatic snapping or trimming.
Only exterior windows are supported. Door state=unknown/open/closed; omit window state.
Pixels can use selected profile references (syntax in plan_partition). Label assumed heights.

Once geometry exists, use trial_plan_bim with operations; never retype the whole plan.
The tool remembers the last source-producing baseline; a failed revision does not replace
it. Each operation needs reason, source_refs and bbox in original-image pixels, plus:
update: collection, id, changes (nonempty, no id); add: collection, value (complete row);
remove: collection, id; set: field, value (top-level except floor_id/collections).
Collections are partitions/openings/space_seeds. Edit each row/field once per batch, 1-100
operations. Example (replace with actual evidence):
{{"operations":[{{"op":"update","collection":"openings","id":"D1","changes":{{"p2":[340,264]}},"reason":"observed jamb endpoint","source_refs":["plan.png: door mark"],"bbox":[320,190,360,270]}}]}}
The audit lists actual edits and unchanged IDs/fields; topology edits can change derived
rooms/hosts. Cross-task rework starts at the verified previous artifact and only changes
rework_targets. Failed previous drafts allow full drafting again.""".format(
    example=json.dumps(READER_PLAN_EXAMPLE, ensure_ascii=False, separators=(",", ":")),
    room_types=", ".join(COMMON_ROOM_TYPES))

_PLAN_DIFFERENCES = """5. RESOLVE THE DIFFERENCES. trial_plan_bim returns drawing_differences and
building_precision: review clues, not drawing-fidelity verdicts. Recheck look_box or the
named source object, then revise by operations or explain retention. Align to an existing
line, never an average; preserve real rooms, openings and connections.
Before turning an inkless gap into a door/open, decide whether its ends belong to the
same physical wall. If not, remove the artificial separator and opening in the SAME
revision; remove a redundant seed if the merged space contains two seeds. Preserve real
wall portions. Each reported topology_issues row needs a located
topology_decisions row: issue_id, decision=retain_opening/continuous_space, basis and bbox.
The final plan must implement it; unresolved text cannot waive it. No warnings: pass []."""

_ARTIFACT_SCHEMA = """Deliver through submit_plan_reading. Copy plan_sha256 from the successful trial;
the tool retrieves that saved plan. Supply evidence, unresolved, wall_reference and
topology_decisions. If axis_orientation puts North at image_bottom or East at image_left,
also supply north_arrow with the original arrow bbox, drawing-based basis,
world_north_toward and world_east_toward matching the reported directions. Instructions
and overlays are not arrow evidence. Normal orientation requires no north_arrow.
Evidence rows: {{"item":"plan.openings:W1","source":"the exact task image name",
"bbox":[left,top,right,bottom],"basis":"observed mark"}}. Cover plan.x_anchors,
plan.y_anchors, plan.footprint_pixels and every plan.partitions:<id>,
plan.space_seeds:<id>, plan.openings:<id> with localized boxes. unresolved may add questions,
but does not edit the saved plan. A failed trial cannot be submitted.
wall_reference separately describes perimeter and partitions, matching step 3:
{wall_example}
Allowed conventions: centerline/inner_face/outer_face/explicit_face. Each dimension_basis
names that category's reference line after the conversion explained in basis. Categories
may differ; each bbox locates its dimension chain. Only declaration consistency is checked.
If submission rejects an item, correct that issue (operations if the plan changes) and
resubmit. After acceptance, end with a short acknowledgement.""".format(
    wall_example=json.dumps(WALL_REFERENCE_EXAMPLE, separators=(",", ":")))

PLAN_READER_GUIDANCE = "\n\n".join((
    _SHARED_READER_SCOPE,
    _PLAN_CORE,
    _SECTIONS[1].replace("READ THE WHOLE SET", "READ THE ONE PLAN")
                .replace("View every supplied plan and elevation in full.", "View the supplied plan in full."),
    _SECTIONS[2],
    _PLAN_CALIBRATION,
    _PLAN_DRAFT,
    _PLAN_DIFFERENCES,
    "Allowed tools: " + ", ".join(READER_TOOL_NAMES["plan_reader"]) + ".",
    _ARTIFACT_SCHEMA,
))


ELEVATION_EXAMPLE = {
    "orientation": "North",
    "view_direction": "South",
    "x_calibration": {
        "pixel_start": 100,
        "pixel_end": 900,
        "world_start_m": 10,
        "world_end_m": 0,
        "world_axis": "x",
    },
    "elevations": [
        {"id": "ground", "kind": "ground", "value_m": 0,
         "evidence_type": "annotation", "bbox": [80, 700, 180, 760]},
    ],
    "openings": [
        {"id": "W1", "floor_id": "F1", "kind": "window", "x_px": [200, 300],
         "width_m": 2.5, "sill_m": 1.0, "head_m": 2.4,
         "evidence_type": "annotation_and_pixels", "bbox": [190, 300, 310, 650]},
    ],
    "counts": [{"floor_id": "F1", "window_count": 1, "door_count": 0}],
    "unresolved": [],
}

_ELEVATION_SCHEMA = """Deliver by calling submit_elevation_reading with these structured parameters;
free text is not a delivery. Complete minimum example:
{example}
Replace every example value with observations from the assigned image. orientation is North,
South, East or West. view_direction uses the same enum and must be North/South for a
North/South facade or East/West for an East/West facade. Image left-to-right world direction:
North facade viewed South decreases X; South viewed North increases X; East viewed West
increases Y; West viewed East decreases Y. Opening x_px stays in ascending image-pixel order
even when the corresponding world coordinate decreases.
x_calibration requires pixel_start, pixel_end, world_start_m and world_end_m; world_axis is
optional and must be x for North/South or y for East/West. elevation kind is ground, floor,
eave, roof or other; kind=floor also requires floor_id. opening kind is window or door.
evidence_type is annotation, pixels, annotation_and_pixels, visual_estimate, assumption or
declared. sill_m/head_m and elevation value_m are absolute building Z metres. Openings stay
left-to-right within each floor, counts must equal the listed openings, bboxes use localized
original-image [left,top,right,bottom], and unresolved is a string list. image, schema_version
and artifact_id are bound by the runtime, not tool parameters. A rejection identifies the
field and minimum example; correct that item and resubmit within the task budget. After
acceptance, end with a short acknowledgement without copying the readings.""".format(
    example=json.dumps(ELEVATION_EXAMPLE, ensure_ascii=False, separators=(",", ":")))

ELEVATION_READER_GUIDANCE = "\n\n".join((
    _SHARED_READER_SCOPE,
    CORE,
    _SECTIONS[2],
    _SECTIONS[6].split("Use view_elevation_candidate", 1)[0].strip(),
    "Allowed tools: " + ", ".join(READER_TOOL_NAMES["elevation_reader"]) + ".",
    _ELEVATION_SCHEMA,
    "Do not copy plan positions or apply heights to a building draft.",
))


COORDINATOR_GUIDANCE = """Build lightweight BIM by coordinating drawing readers. Inventory inputs, then
delegate_readers for independent images (plans start first). Give a common origin and
target: plan floor ID; elevation North/South/East/West, optionally /F1,F2. Runtime fixes
x East, y North by the north arrow, z Up; never redefine directions in instructions.
Use role_state for progress and read_role_artifact for accepted deliveries.

Call assemble_from_readers once after deliveries. It selects the latest accepted plan
per floor and elevation per facade, resolves levels, builds/assembles floors, matches
openings and writes safe heights together. Read its decisions: missing/conflicting
levels retain plan assumptions, unmatched openings remain unresolved. Inspect cited
marks; resolve levels with level_overrides (floor_id, z_floor/ceiling_height and each
*_evidence: task_id + elevation_id). Heights equal cited top Z minus floor Z. Re-call
after reader rework or a local revision; unchanged inputs reuse the saved candidate.
Compare source/overlays to drawings, run checks and fix concrete errors before delivery.

Re-dispatch failures as a new task with previous_task_id and specific issues. For plan
rework, name rework_targets (plan.partitions:<id>, plan.space_seeds:<id>,
plan.openings:<id> or a plan field); preserve everything else. Inspect the local box for
continuous-space/wall-hole conflicts. Assembly compares room counts, adjacency and
opening XY with reader trials. If changes appear, inspect and call review_role_assembly
with review_id and a reason per change before further writes; fix accidental changes.
Use existing revision tools for bounded corrections after evidence is clear. The
coordinator does not independently draft plan walls or read elevation heights when a
reader can do it. Preserve unresolved evidence and finish through delivery checks."""

ROLE_GUIDANCE = {
    "coordinator": COORDINATOR_GUIDANCE,
    "plan_reader": PLAN_READER_GUIDANCE,
    "elevation_reader": ELEVATION_READER_GUIDANCE,
}


def get_role_guide(role_id: str) -> str:
    try:
        return ROLE_GUIDANCE[role_id]
    except KeyError as error:
        raise ValueError(f"unknown role guide {role_id!r}; choose {sorted(ROLE_GUIDANCE)}") from error


def get_role_tool_names(role_id: str) -> tuple[str, ...]:
    if role_id in READER_TOOL_NAMES:
        return READER_TOOL_NAMES[role_id]
    if role_id == "coordinator":
        return (
            "delegate_readers", "read_role_artifact", "assemble_from_readers", "role_state",
            "review_role_assembly",
        )
    raise ValueError(f"unknown role catalog {role_id!r}")


def guidance_catalog() -> dict[str, object]:
    single = build_guide(images="drawings", mesh=False)
    roles = {
        role_id: {
            "character_count": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "tools": list(get_role_tool_names(role_id)),
        }
        for role_id, text in ROLE_GUIDANCE.items()
    }
    return {
        "single_model": {
            "character_count": len(single),
            "sha256": hashlib.sha256(single.encode("utf-8")).hexdigest(),
            "unchanged_source": "scripts/tool_scripts/bim_agent_guidance.py:build_guide",
        },
        "roles": roles,
    }
