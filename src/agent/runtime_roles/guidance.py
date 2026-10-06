"""Role-specific drawing guidance derived from the unchanged single-model text."""

from __future__ import annotations

import hashlib
import json

from scripts.tool_scripts.bim_agent_guidance import CORE, DRAWING_METHOD, build_guide
from src.agent.runtime_roles.readers import READER_TOOL_NAMES


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

_ARTIFACT_SCHEMA = """Deliver through submit_plan_reading, never by writing an artifact in the final text.
Copy plan_sha256 from a passed trial; the tool retrieves exactly that saved plan. Do not
retype the plan or put trial summaries inside it. Supply evidence, unresolved,
wall_reference and topology_decisions. Evidence rows are flat objects {"item":"plan.openings:W1",
"source":"the exact task image name","bbox":[left,top,right,bottom],"basis":"optional"}.
Use plan.x_anchors, plan.y_anchors and plan.footprint_pixels plus
plan.partitions:<id>, plan.space_seeds:<id> and plan.openings:<id> as item names.
Every such item needs a localized evidence row. unresolved may add delivery questions,
but cannot change the saved plan. A failed trial cannot be submitted. For a changed trial,
copy the preceding base_plan_sha256 and supply changes [{"item":"plan.openings:W1",
"reason":"specific check/drawing issue","bbox":[left,top,right,bottom]}] for exactly the
changed fields/objects; all unlisted walls, room seeds and openings must stay unchanged.
Across tasks, only the coordinator's rework_targets may change.
Even a failed trial is the next rework base. If an incomplete object has no unique ID yet,
its pointed change uses an index path such as plan.openings[0]; a malformed whole list uses
plan.openings. The rejection lists the exact changed paths. Do not change other objects.
Before representing an inkless gap as a door/open, decide whether its two ends belong to
the same physical wall. If they do not, use one continuous space: remove the artificial
separator and opening, preserving genuine walls on each side. Every topology_issues row
from any trial needs a topology_decisions row with issue_id, decision=retain_opening or
continuous_space, basis explaining that physical-wall judgement, and the local image bbox.
The final plan must implement that decision; unresolved text cannot waive it.
Every opening's p1 and p2 must be on its one declared wall line. Use one consistent
wall_reference {"convention":"centerline","dimension_basis":"centerline",
"basis":"how dimension anchors refer or were converted to this same line","bbox":[...]}
for the whole floor (allowed conventions: centerline, inner_face, outer_face, explicit_face).
When the submit tool points out a problem, fix just that issue, trial the change and submit
again within the budget. After acceptance, end with a short acknowledgement."""

_PLAN_DRAFT = (_SECTIONS[4]
    .replace("DRAFT EVERY FLOOR", "DRAFT THIS FLOOR")
    .replace("build_plan_bim", "trial_plan_bim")
    .replace("Use claim_transaction's facade_count form (claims reference)\n"
             "to record each floor/facade's observed window total, including zero; facade_counts\n"
             "compares these totals after saves and lists uncounted facades. ", "")
    .replace("Draft every floor before refining any one floor in detail;", "Draft this floor before refining it in detail;")
    .replace("Each upper floor comes from its own drawing;\ncombine floors with assemble_plan_bim.",
             "Do not assemble floors; the coordinator does that from accepted artifacts."))

_PLAN_DIFFERENCES = (_SECTIONS[5]
    .replace("drawing_differences compares", "trial_plan_bim returns drawing_differences, which compares")
    .replace("then revise or\nexplain retention.",
             "then change this plan declaration and rerun trial_plan_bim, or record the unresolved reason."))


PLAN_READER_GUIDANCE = "\n\n".join((
    _SHARED_READER_SCOPE,
    CORE,
    _SECTIONS[1].replace("READ THE WHOLE SET", "READ THE ONE PLAN")
                .replace("View every supplied plan and elevation in full.", "View the supplied plan in full."),
    _SECTIONS[2],
    _SECTIONS[3],
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


COORDINATOR_GUIDANCE = """Build the requested lightweight BIM by coordinating focused drawing readers.
Inventory the admitted inputs and coordinate convention, then use delegate_readers for
independent plan and elevation images. Set plan target to its floor ID (F1); elevation target
to North/South/East/West, optionally with /F1 or /F1,F2 to limit floors. Track progress with role_state and read accepted
deliveries through read_role_artifact. Build each floor from its artifact reference with
build_from_artifact; do not retype a reader's plan. Assemble the floors, run
match_elevation, inspect unmatched or conflicting openings, and only then use
apply_elevation_heights for confirmed matches. Compare the assembled source and overlays
to the original drawings, run existing checks, and revise concrete errors before delivery.

If a reader artifact is malformed or its isolated plan trial fails, re-dispatch that same
role as a new task with the previous artifact and a specific problem list. For plan rework,
name rework_targets (plan.partitions:<id>, plan.space_seeds:<id>, plan.openings:<id> or a
specific plan field); everything else must remain unchanged. If a continuous-space/wall-hole
judgement conflicts, inspect only that local image box and re-dispatch the pointed objects.
After assembly the tool automatically compares room counts/adjacency and opening counts/XY
against the accepted floor trials. When differences are reported, inspect them and call
review_role_assembly with the review_id and a reason for every listed change before any
further write or delivery. Fix accidental changes instead of explaining them away. For a bounded
local correction after the evidence is clear, the coordinator may use the existing model
revision tools. The coordinator does not independently draft plan walls or read elevation
heights while a reader task can produce that artifact. Preserve unresolved evidence and
finish through the existing delivery checks."""

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
            "delegate_readers", "read_role_artifact", "build_from_artifact",
            "match_elevation", "apply_elevation_heights", "role_state",
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
