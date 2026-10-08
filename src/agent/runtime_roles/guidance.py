"""Role-specific drawing guidance derived from the unchanged single-model text."""

from __future__ import annotations

import hashlib
import json

from scripts.tool_scripts.bim_agent_guidance import CORE, DRAWING_METHOD, build_guide
from src.agent.runtime_roles.readers import READER_TOOL_NAMES
from src.agent.roles import room_types_reference
from .plan_format import READER_PLAN_EXAMPLE


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

_PLAN_CORE = """Preserve actual rooms, walls, openings and connections; never shorten/move an opening
to evade a host error. Passing checks is not drawing fidelity. Keep stable IDs and label
assumptions. task.coordinate_contract fixes floor/origin; world x East, y North (arrow),
z Up/absolute. Record conflicting instructions. ALL plan points and first anchor values
are ORIGINAL pixels: read grid labels, or crop origin + original_pixels_per_returned_pixel
times display pixels. Second anchor values, z_floor, ceiling_height and opening z are metres."""

_PLAN_LOOK = """1. View the whole plan once with view_image; identify footprint, floor, north arrow
and overall dimensions. 2. Call view_plan_blocks once: it returns 4-8 enlarged blocks at
about 3x with ORIGINAL pixel grids, boxes and view IDs. Read the floor's walls, openings,
room seeds and dimension annotations together. Do not profile each line before a draft."""

_PLAN_CALIBRATION = """3. Calibrate from overall exterior dimensions; send internal chains in the first trial.
dimension_chains rows: id, axis=x/y, printed segments_mm, total_mm, approximate tick_pixels
(one per extension line, ordered), source_refs. Only chains reaching both outer faces set
scale. start_world_m needs the first tick's contract origin AND visible annotation, cited
together; never guess zero. Otherwise anchors supply origin. Further chains need matching
scale/origin; failed/internal chains never set an axis. Use outer perimeter faces and
partition midlines; start_world_m is metres, axes keep East/North even with reversed ticks."""

_PLAN_DRAFT = """4. Submit ALL floor walls, openings and room seeds together to trial_plan_bim, using
approximate original pixels. Nearby ink is aligned; endpoints within the reported
tolerance (at most 0.30m) connect automatically. If a junction still fails, set the
named endpoint to the error's exact original-pixel target. Openings follow their wall.
Dimensions override ink; missing ink is recorded without moving it. Complete plan example:
{example}
Replace synthetic values with observations. Use partitions[].points, openings[].p1/p2,
space_seeds[].point, not wall/room polygons or opening room/space_id/facade fields.
Seeds label room interiors, never create walls; choose role from the full table below.
Do not duplicate footprint as partitions. Exterior doors/windows lie on footprint;
interior doors/open passages lie on partitions continuing through apertures. Junctions
coincide. Only exterior windows are supported. Door state=unknown/open/closed; omit
window state. Label assumed heights.
For corrections use operations against the latest passed plan (or last resolved draft
before any passes). Each needs reason, source_refs, original-pixel bbox and:
update: collection,id,changes (no id); add: collection,value (complete row);
remove: collection,id; set: field,value (top-level except floor_id/collections).
Collections=partitions/openings/space_seeds; 1-100 operations, each row/field once.
Full plans remain accepted. Audit actual changes; cross-task rework preserves unpointed
objects. Notes may change freely but cannot authorize geometry or room-use changes.""".format(
    example=json.dumps(READER_PLAN_EXAMPLE, ensure_ascii=False, separators=(",", ":")))

_PLAN_DIFFERENCES = """5. Review ONLY trial drawing_differences, hard-rule failures and the overlay.
Target <10cm; accept 10-30cm and record the discrepancy without extra measuring.
Rework substantive room/wall/opening/host/connectivity errors or deviations >30cm.
The 0.30m alignment / 0.60m minimum room-width hard rules still must pass. Use a profile
only when a trial-reported difference remains unclear on its overlay; inspect look_box
on the original. Align to the observed line, never an average. Each topology_issues row
needs topology_decisions: issue_id, retain_opening/continuous_space, basis, bbox. For an
inkless gap, decide whether both ends belong to one physical wall. If not, remove the
artificial separator AND opening together, plus any redundant seed, preserving actual
wall portions. Implement the decision; unresolved text cannot waive it. No warning: omit."""

_ARTIFACT_SCHEMA = """6. submit_plan_reading({"trial_id":"latest"}) or latest passed trial_id/plan_sha256.
Never resend plan/evidence: generated boxes locate declarations, not prove observation;
anchor bands do not locate dimensions. Optional notes={item,kind,basis}, kind=
assumption/inferred/unresolved; unresolved lists delivery questions.
wall_reference defaults: perimeter=outer_face, partitions=centerline; no geometry move.
Overrides: convention=centerline/inner_face/outer_face/explicit_face, dimension-to-line
basis; optional matching dimension_basis and annotation bbox. For axis_orientation North
at image_bottom or East at image_left, north_arrow needs original arrow bbox, drawing
basis and matching world_north_toward/world_east_toward; overlays/instructions cannot prove
it. Normal orientation needs none. Reject failed/stale trials; retry changed plans before
submission. Correct named rejections, then acknowledge briefly."""

PLAN_READER_GUIDANCE = "\n\n".join((
    _SHARED_READER_SCOPE,
    _PLAN_CORE,
    _PLAN_LOOK,
    _PLAN_CALIBRATION,
    _PLAN_DRAFT,
    _PLAN_DIFFERENCES,
    room_types_reference(),
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


COORDINATOR_GUIDANCE = """Inventory inputs; delegate_readers for plans AND elevations together with a common
origin. Targets: floor ID or North/South/East/West[/F1,F2]. First dispatch fills missing
readers and waits for all. Instructions contain drawing facts/questions only.
Read results with role_state and read_role_artifact.

assemble_from_readers builds accepted floors, resolves levels, carries uses and located
safe heights. Audited regularization needs no confirmation. Check openings/result, then
finish_bim. Reassemble new reader deliveries; unchanged inputs reuse receipts.
level_overrides cite {task_id,elevation_id}: absolute z_floor or ceiling_height=top Z-floor Z.

Target <10cm. Compare independent opening endpoints/width after identity matching.
10-30cm automatically retain plan with a note. Every >30cm difference must be explicitly
decided before finish_bim. role_state(position_details=true) lists readings;
role_state(position_decision_id=...) returns both original crops and view_ids.
Optional edit_bim position_decision: decision_id, choice=keep_plan/use_elevation/
reread_plan/reread_elevation, reason, view_ids. Above 30cm inspect both original crops;
choosing a side requires both saved views, while reread remains delivery-blocking until a
new reader delivery is assembled and decided. use_elevation stays on its host; conflicting numeric width needs keep_plan or
rereading, never pixel-width replacement. Never average positions. One-sided or unsafe
height matches stay unresolved.

Rework substantive room/opening/host/connectivity errors. Re-dispatch with new task_id,
previous_task_id,issues. Plan rework_targets: plan.partitions:<id>,plan.space_seeds:<id>,
plan.openings:<id>,plan.openings or a plan field; preserve the rest. Actual reader-geometry
changes need review_role_assembly with reasons; height/use/note edits retain confirmation.
Missing-floor decisions accept partial delivery; stale/unverified reader lineage needs repair.

edit_bim heights go separately: id,sill_m,head_m,reader_evidence={task_id,sha256,opening_id}
reuse the immutable reader's original box without new views. Independent evidence uses
image,bbox. use(id,role,image) defaults to inferred; position(id,along_start_m,along_end_m,
image) needs geometry review; note(text) needs none. Do not draft walls or reread heights
when a reader can. Preserve unresolved evidence; check_openings reuses unchanged checks."""


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
