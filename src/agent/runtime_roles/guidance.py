"""Role-specific drawing guidance derived from the unchanged single-model text."""

from __future__ import annotations

import hashlib
import json

from scripts.tool_scripts.bim_agent_guidance import CORE, DRAWING_METHOD, build_guide
from src.agent.runtime_roles.readers import READER_TOOL_NAMES
from .plan_format import COMMON_ROOM_TYPES, READER_PLAN_EXAMPLE


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

_PLAN_CALIBRATION = """3. CALIBRATE FROM DIMENSIONS. For each overall chain add a dimension_chains row:
id, axis=x/y, printed segments_mm, total_mm, approximate tick_pixels in chain order
(one per extension line), and source_refs. Its end ticks must reach both outer faces.
When task.coordinate_contract gives the first tick's world coordinate, also give
start_world_m and cite both the visible annotation and that origin contract in source_refs.
Never guess zero. The chain then sets exact scale and origin while old anchors are audited.
Without start_world_m, legacy anchors still supply the origin and the report says so.
If another overall chain on the same axis exposes additional perimeter or divider ticks,
include it too; code uses those ticks only after its scale and origin agree with the first chain.
Failed or internal chains do not set the axis. Use perimeter outer faces and partition
midlines. Keep x east and y north; tick order may run opposite pixel direction. Bare world
lengths and start_world_m are metres."""

_PLAN_DRAFT = """4. DRAFT THIS FLOOR EARLY. Once the overall dimension chains and divider lines are read,
call trial_plan_bim with a complete plan; its overlay and drawing_differences show where
to look closer. Full plans are accepted at any stage. Operations need a remembered
plan: a verified baseline, or the last resolved draft before any trial passes.
Complete minimum example (plan_partition format at image scale):
{example}
Replace the synthetic values with drawing observations. Use partitions[].points,
openings[].p1/p2 and space_seeds[].point, not walls, room polygons or opening room/space_id/
facade fields. Seeds lie inside rooms and name them; they never create walls. A seed role
is optional: omit it or use a room_types code ({room_types}...).
Do not repeat the exterior footprint as partitions. Approximate pixels suffice: trial code
searches a scale-derived 0.30 m radius for perimeter outer-face ink, divider midlines and jamb
edges. Openings and junctions follow their wall. Missing ink is recorded without a move;
dimensions override ink.
Exterior doors/windows lie on the footprint; interior doors/open passages lie on their partition. Partitions continue
through door apertures and junction coordinates coincide after alignment.
Only exterior windows are supported. Door state=unknown/open/closed; omit window state.
Use a profile only for a mark still unclear after trial; do not measure every wall. Label assumed heights.

For local corrections, send operations to avoid retyping unchanged rows. The tool uses
the last verified baseline if present; failed drafts remain editable before it. Each operation
needs reason, source_refs and bbox in original-image pixels, plus:
update: collection, id, changes (nonempty, no id); add: collection, value (complete row);
remove: collection, id; set: field, value (top-level except floor_id/collections).
Collections are partitions/openings/space_seeds. Edit each row/field once per batch, 1-100
operations. Example (replace with actual evidence):
{{"operations":[{{"op":"update","collection":"openings","id":"D1","changes":{{"p2":[340,264]}},"reason":"observed jamb endpoint","source_refs":["plan.png: door mark"],"bbox":[320,190,360,270]}}]}}
The audit lists actual edits and unchanged IDs/fields; topology edits can change derived
rooms/hosts. Cross-task rework preserves unpointed objects in either input format. Notes
(basis, assumptions, unresolved, source descriptions) may change without naming a rework
target; they cannot authorize geometry or room-use changes.""".format(
    example=json.dumps(READER_PLAN_EXAMPLE, ensure_ascii=False, separators=(",", ":")),
    room_types=", ".join(COMMON_ROOM_TYPES))

_PLAN_DIFFERENCES = """5. RESOLVE THE DIFFERENCES. trial_plan_bim returns drawing_differences,
building_precision and a compact reading_alignment summary; the full list stays with the plan.
Geometry under the 0.30 m alignment / 0.60 m minimum room-width rules must pass before
saving; drawing differences still need original-image review. Recheck look_box or the
named source object, then revise rejected objects by operations. Align to an existing
line, never an average; preserve real rooms, openings and connections.
Before turning an inkless gap into a door/open, decide whether its ends belong to the
same physical wall. If not, remove the artificial separator and opening in the SAME
revision; remove a redundant seed if the merged space contains two seeds. Preserve real
wall portions. Each reported topology_issues row needs a located
topology_decisions row: issue_id, decision=retain_opening/continuous_space, basis and bbox.
The final plan must implement it; unresolved text cannot waive it. No warnings: omit decisions."""

_ARTIFACT_SCHEMA = """Deliver through submit_plan_reading with {"trial_id":"latest"}, or the latest passed
trial_id/plan_sha256. The tool retrieves the immutable saved plan and generates original
pixel evidence for every anchor, footprint, partition, seed and opening. Do not resend
the plan or an evidence table. Generated boxes locate declarations, not proof that they
were correctly observed; anchor bands do not locate printed dimensions. Keep assumptions
in the plan. Optional notes: {"item":"plan.space_seeds:S1","kind":"inferred","basis":"use inferred from furniture"};
kind is assumption/inferred/unresolved. Optional unresolved adds delivery questions.
Wall defaults are perimeter=outer_face and partitions=centerline, explicitly modeling
conventions. If different, supply only that wall_reference category with convention and
basis explaining the dimension-to-line conversion; optional dimension_basis must match
convention, optional bbox locates the actual supporting annotation. Conventions allowed:
centerline/inner_face/outer_face/explicit_face. Defaults never move geometry.
Supply topology_decisions only for reported warnings. If axis_orientation puts North at
image_bottom or East at image_left, supply north_arrow with the original arrow bbox, drawing-based basis,
world_north_toward and world_east_toward matching the reported directions. Instructions
and overlays are not arrow evidence. Normal orientation requires no north_arrow.
A failed or stale trial cannot be submitted. Correct the named rejection and resubmit;
plan changes require another trial. After acceptance, end with a short acknowledgement."""

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

COMPACT_ELEVATION_EXAMPLE = {key: value for key, value in ELEVATION_EXAMPLE.items()
                             if key not in {"orientation", "view_direction", "x_calibration"}}
COMPACT_ELEVATION_EXAMPLE["x_calibration"] = {
    "pixel_start": 100, "pixel_end": 900, "distance_start_m": 0, "distance_end_m": 10,
    "facade_length_m": 10}
COMPACT_ELEVATION_EXAMPLE["z_calibration"] = {
    "pixel_start": 300, "pixel_end": 700, "world_start_m": 3, "world_end_m": 0}
COMPACT_ELEVATION_EXAMPLE["openings"] = [
    {"id": "W1", "floor_id": "F1", "kind": "window", "opening_bbox": [200, 380, 300, 567],
     "evidence_type": "pixels"}]

_ELEVATION_SCHEMA = """Submit a rough box per opening and two independent image calibrations:
{example}
Replace the example with original observations. x_calibration distances increase from the
image-left building edge; retain any partial-chain offset and give total facade_length_m.
The task fixes facade and world direction. z_calibration pairs top/bottom pixels with
absolute Z metres, decreasing down the image. Locate the supporting level marks in
elevations (ground/floor/eave/roof/other; floor needs floor_id).
opening_bbox is the approximate aperture [left,top,right,bottom] in ORIGINAL pixels;
bbox, if supplied, is a separate evidence crop. Use evidence_type=pixels only for pixel
estimates without annotation support; rough boxes suffice. For annotation, mixed or other
bases, supply x_px/width_m/sill_m/head_m: these readings are retained. The tool checks ink
within 0.30m and changes only pure pixels with a unique continuous line. It preserves
floor-contact sills and records numeric/ink disagreements for review. Do not measure four profiles.
Keep openings in image order within each floor and count every window/door. Keep unclear
marks and mirrored/nonstandard views in unresolved; never borrow plan positions.
Correct a named rejection and resubmit. After acceptance, acknowledge without copying readings.""".format(
    example=json.dumps(COMPACT_ELEVATION_EXAMPLE, ensure_ascii=False, separators=(",", ":")))

ELEVATION_READER_GUIDANCE = "\n\n".join((
    _SHARED_READER_SCOPE,
    CORE,
    _SECTIONS[2],
    "Read the assigned facade independently. Locate its overall dimensions and absolute level marks, then rough opening boxes; the tool refines edges.",
    "Allowed tools: " + ", ".join(READER_TOOL_NAMES["elevation_reader"]) + ".",
    _ELEVATION_SCHEMA,
    "Do not copy plan positions or apply heights to a building draft.",
))


COORDINATOR_GUIDANCE = """Build lightweight BIM through drawing readers. Inventory inputs, then delegate_readers
(plans first) with common origin and target: plan floor ID; elevation North/South/East/West,
optionally /F1,F2. Instructions give building facts or rework questions; the runtime supplies
method and coordinates. Use role_state for progress and read_role_artifact for deliveries.

assemble_from_readers selects current deliveries, resolves levels, carries uses and writes
safe heights. Fits identify openings; position decisions compare UNFITTED independent
endpoints and width. Within 10cm retain plan, never average. For pending positions use
role_state(position_details=true) for both readings and image boxes, then edit_bim with
action=position_decision, decision_id, choice and reason. Choose keep_plan/use_elevation
or reread_plan/reread_elevation with a concrete defect. 10-30cm may batch keep_plan with
reasons; above 30cm view BOTH cited boxes and pass view_ids before choosing either side.
use_elevation moves only along the existing host; an out-of-host interval is rejected.
If a retained numeric width conflicts with its pixel interval, keep_plan or re-read;
use_elevation cannot replace that width with a pixel-derived width.
Re-read choices need delegate_readers rework and reassembly; they cannot waive delivery.
One-sided openings remain conflicts. Resolve levels with level_overrides: floor_id,
z_floor/ceiling_height and *_evidence={task_id,elevation_id}; height=top Z-floor Z.
Re-call after rework/edits; unchanged inputs reuse receipts. Check drawings before delivery.

Re-dispatch failures with new task_id, previous_task_id and specific issues. Plan rework
needs rework_targets: plan.partitions:<id>, plan.space_seeds:<id>, plan.openings:<id> or a
plan field; preserve the rest. Inspect local boxes for continuous-space/wall-hole conflicts.
Assembly compares rooms, adjacency and opening XY against reader trials. Inspect changes,
then review_role_assembly with review_id and a reason per change before further writes;
fix accidental changes. Missing-floor decisions allow partial delivery; stale plans require
reassembly. Other small corrections use edit_bim: height, use, position or note, with reason.
Use defaults to inferred; height needs located evidence in a separate batch. Room uses
already carry reader evidence. The coordinator does not independently draft plan walls or
read heights when a reader can. Keep unresolved evidence and finish through delivery checks."""

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
            "review_role_assembly", "edit_bim",
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
