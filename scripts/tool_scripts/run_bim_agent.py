"""Small subscription-driven BIM experiment; no legacy flow or solver stages.

The model sees only an explicit image inventory and the tools below. MCP owns
file access and geometry execution; the model has no shell/repository tools.
This is an experimental entry point, not a complete product orchestrator.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image as PILImage, ImageDraw
from mcp.server.fastmcp import Image
from mcp.types import CallToolResult, TextContent


GUIDE = """Build a viewable lightweight BIM from the supplied drawings. You choose
what to inspect, measure, infer, build and revise. Preserve physical rooms,
partitions, windows, doors and connectivity; never split a room to make a box.
Annotation + pixels is stronger than pixels alone, which is stronger than
inference. Missing evidence permits explicit assumptions, not silent omission.
Use measurements where useful; tools are optional methods, not a fixed workflow.
map_dimension_chain accumulates dimension labels into metre intervals, including
reversed facade directions, and reports residual against an overall dimension.
Use it for arithmetic instead of mentally adding long chains. The labels and
coordinate convention still need image evidence; a closed sum is not proof.
For wall thickness and annotation baselines, use check_wall_dimensions to list
actual source wall IDs, then calculate explicit endpoint conversions. Preserve
the representative room boundaries: offsets describe wall faces and do not move
rooms or openings. Do not assume an axis is centred or add half a wall thickness
to close a chain. Unknown offsets remain unknown even if total thickness is known.
Optional proposal fields wall_references and wall_dimensions persist these facts.
Prefer local edits of an existing record, retaining its original label/pixels and
the other records. A same-wall thickness label is a valid dimension observation,
not an invalid or redundant chain to delete merely because its sides conflict.
revise_bim operations:
{"op":"update_wall_dimension","id":"dim-A","changes":{"start":{"image":"plan.png"}},
"reason":"explain image evidence","source_refs":["plan.png: observed endpoint"]};
{"op":"update_wall_reference","id":"wall-A","changes":{"evidence_status":"inferred"},
"reason":"explain inferred scope","source_refs":["plan.png: observed versus inferred scope"]}.
Endpoint patches merge into the existing start/end, preserving untouched pixels,
wall_id and image. Other editable dimension fields are axis, direction, value and
unit; only change transcribed numbers when the original actually supports that.
Reference patches may change boundary_id, offsets_m, thickness_m, reference_basis,
thickness_scope or evidence_status. Keep derived output fields out of edits.
revise_bim also accepts {"op":"set_wall_references","wall_references":[...],
"wall_dimensions":[...],"reason":"image basis"}, replacing both whole lists.
Example wall reference (unrelated to supplied drawings):
{"id":"wall-A","boundary_id":"space/room/wall/1","offsets_m":[-0.08,0.16],
"thickness_m":0.24,"reference_basis":"declared representative axis; eccentric",
"thickness_scope":"unknown layer scope","evidence_status":"inferred",
"source_refs":["plan.png: local wall band observation or explicit assumption"]}.
offsets_m are signed along POSITIVE world x for a constant-x wall, or positive
world y for a constant-y wall, independent of which room owns the boundary.
Use offsets_m:null when unknown; thickness_m may also be null. Each reference
covers one complete straight source wall and its congruent counterpart. Partial
shared walls and explicit enclosure declarations are unsupported here. List only
local evidence you have; do not fill all walls with one guessed thickness.
Dimension example: {"id":"dim-A","axis":"x","direction":1,"value":5000,
"unit":"mm","start":{"wall_id":"wall-A","side":"positive","image":"plan.png",
"pixel":[100,200]},"end":{"wall_id":"wall-B","side":"negative",
"image":"plan.png","pixel":[500,200]},"source_refs":["plan.png: visible 5000 label"]}.
side is negative, positive, representative or unknown; axis labels count as
representative only if that correspondence is evidenced. Pixels are original
dimension extension endpoints. Pass dimensions in chain order only when related;
different wall sides are different chain endpoints. Tools preserve raw labels,
conversion terms and model residuals separately; they do not verify your reading.
Check endpoint pixels and world anchors describe the SAME face before calibrating.
Saved overlays show representative boundaries in magenta and declared wall faces
in blue, with observed/inferred/unknown status in metadata. A blue face is derived
from your claim, not independently detected. Geometry edits keep the representative
plane fixed for thickness updates; move_shared_wall carries attached face offsets
with the moved wall. Reflection with such evidence requires a full revised proposal.
Use review_detail (Haiku subscription) when a local second look is useful;
you choose whether to use it and what substantive local question to ask. It
runs with only the selected original images and your submitted question, so it
cannot inspect this run's scope, seed, candidates, history or other images.
That is file-context isolation only: the question is passed through as written,
not cleaned of claims you put in it. You remain responsible for checking its
answer against the drawing. Its prose is a hypothesis, not proof of an opening
or connection.
Do not ask the user for routine geometry choices. No EP/materials are needed.
build_bim saves immutable candidates and returns actual checks. Revise if a
check fails, keep stable object IDs and do not drop known openings to pass.
Inspect the resulting plan with view_candidate and compare to original images.
overlay_candidate can project a saved floor back onto an original plan using
your observed pixel/metre anchors. It is useful for spotting misplaced walls
and openings that a separately scaled model view hides. Its calibration is
your hypothesis, not an automatic image match; inspect the overlaid result.
By default an explicit overlay registers that exact image+floor calibration
for later candidates. After build_bim or revise_bim, every registered view is
projected again from the newly saved source BIM and returned with its real
metadata, so you can inspect the new image before deciding whether to revise.
Each image and floor has its own calibration; a later explicit calibration
replaces only that pair for future projections. Reuse never refits anchors to
new walls. A returned image is not proof that you looked at it or that it is
faithful: calibration remains independently unverified. Keep unresolved
items in set_notes until the new projection has actually been considered.
Geometric consistency is not drawing fidelity. Conclude with exact candidate,
assumptions, unresolved issues and what was/was not verified. Select the saved
candidate with finish_bim before concluding. This records the ACTUAL checks
and wall-dimension contradictions/calibration warnings, even when omitted from
your prose. A same-wall endpoint-order finding concerns the declared sides and
direction, not room placement: inspect and correct those labels before trying
to move a wall. Other nonzero dimension residuals may be genuine geometric or
baseline differences and require image judgement; zero is not a fidelity verdict.
Image views show a labelled grid in ORIGINAL pixel coordinates by default.
Read its labels for crops/calibration, not the displayed thumbnail width/height.
Plan overlays also label saved wall segments and original dimension evidence
points. Compare the actual segment extent with those points, not just a wall's
normal coordinate or a directional name in its ID. The spatial comparison uses
your calibration and does not certify host identity: dimension extension ticks
can lie outside the physical segment. Inspect the original marks and their
extension lines before changing a host or calling the evidence observed.
For a clean close look use coordinate_grid=false. Before registering anchors,
check both endpoints on the original image; large cross-axis scale warnings call
for rechecking endpoint locations. Once a frame is usable, register it before a
revision so the new source is shown in the same frame. Save remaining issues in
set_notes; the delivery also retains tool facts separately from those notes.
Delivery also records current/old opening reviews; follow-up or unreviewed scopes are allowed,
but must not be described as verified. Your prose cannot override this record.
Produce an initial or revised candidate early, then improve it. Do not spend
the whole budget chasing small dimension offsets. When a seed is available,
inspect_candidate('seed') gives the saved proposal and production checks;
continue from it rather than regenerating the whole building. Compare actual
spatial partitions, openings and connectivity with the original, resolve
coordinate conventions, and choose substantive discrepancies for local review
or revision. For spatial partitions, compare the actual room extents and shared
walls with image evidence, not only the saved unresolved list. Crops, measured
coordinates or a calibrated overlay can expose displaced partitions; choose
which is useful. State which partition scope remains unexamined. Do not infer
that reviewing openings also verified the walls or room layout.
Use revise_bim for local changes and code-computed reflections. Never change
facade labels merely to satisfy a host check: geometry and drawing directions
must agree. Door swings, dimension ticks and window marks are different things.
If an opening cannot attach to its declared walls, inspect the reported source
host bounds, including absolute world heights. A height diagnostic describes
the submitted geometry, not an image-derived correction. Preserve a visible
opening while resolving the cause; deleting it just to clear a build failure
does not restore the building.
When correcting an unsupported opening, preserve the reason and source reference.
When reviewing openings, reconcile the actual inventory with distinct marks
on the original plans, including asymmetric details. A note saying "one door"
does not remove a second modeled door. check_openings(candidate) lists the
actual objects; its optional review_json checks your observed marks against
that inventory. Use complete only after inspecting all openings of that kind
on that floor, partial for a local check. Each mark represents ONE aperture
and connection, not a broad crop containing several doors. Review uncertainty
is allowed; do not fabricate observations to make a checklist pass. Recheck
reported mismatches and review any changed candidate again. No GT is used.

check_openings review_json example (unrelated to supplied drawings):
{"floor_id":"F1","kind":"door","image":"plan.png","coverage":"complete",
 "marks":[{"mark_id":"door-mark-1","box":[10,20,40,60],
 "opening_ids":["D1"],"space_ids":["room","hall"],"basis":"visible",
 "note":"one leaf and arc in a wall gap"}]}.
Use original-image pixels for box. An exterior opening lists only its indoor
space ID in space_ids; never add an ID named 'outside' or 'outdoors'. Use no
opening_ids when an observed aperture has not been modeled. Separate paired
arcs serving different rooms into separate marks; a double-leaf door serving
one connection is one aperture. basis may be visible, inferred or uncertain.
The tool checks consistency with your observations, not their visual truth.
For an elevation review, add optional facade: North, South, East or West.
It limits coverage to exterior openings whose actual source host faces that
direction; a file name alone does not establish the physical facade. Complete
then means the WHOLE named facade for that floor/kind, not every facade on the
floor. Submit marks:[] when a fully inspected facade has no aperture of that
kind. All actual exterior directions, including zero-opening directions, need
complete reviews before facade reviews can cover a floor/kind. Interior or
unclassifiable openings stay explicitly uncovered. Without facade the original
whole-floor plan scope remains unchanged. Use partial for incomplete views.

revise_bim takes candidate plus an operations_json list. Operations include:
{"op":"reflect","axis":"y","reason":"explain the chosen frame change"};
{"op":"update_window","id":"W1","changes":{"span":[1,2]},
 "reason":"explain","source_refs":["image: observation or explicit assumption"]};
{"op":"update_opening","id":"D1","changes":{"p1":[3,1],"p2":[3,2]},
 "reason":"explain","source_refs":["image: observation or explicit assumption"]};
{"op":"move_shared_wall","space_ids":["F1_left","F1_right"],"coordinate_m":3.5,
 "reason":"explain observed partition displacement","source_refs":["plan: observed wall"]};
{"op":"remove_opening","id":"D1","reason":"explain reclassification",
 "source_refs":["image: observation"]};
{"op":"set_notes","assumptions":["updated assumptions"],"unresolved":[]}.
Reflect transforms the entire proposal around the footprint midpoint on that
axis, including rooms, window directions/spans and door coordinates. It preserves
identities and connectivity. Replace stale directional assumptions with set_notes.
Source IDs remain stable even if they contain an obsolete direction in their name.
move_shared_wall is a local operation for two same-floor rectangular cells
sharing one complete edge. It derives the wall axis from their existing geometry
and moves both sides to coordinate_m together; openings hosted between those
two cells move with the wall. Other objects retain their world coordinates and
are checked by the normal builder. Polygon cells, partial shared sides and
explicit enclosure declarations are unsupported by this edit; no new rooms or
walls are invented. Preserve image basis and check the resulting geometry.
For edits not supported by revise_bim, submit a complete revised proposal with
build_bim, retaining the reliable geometry, IDs, source references and caveats.

Geometry adapter input is a JSON string containing:
{"geometry":{"schema_version":"2","footprint_x":[0,6],"footprint_y":[0,4],
"floors":[{"name":"F1","z_floor":0,"ceiling_height":3,"cells":[
{"id":"F1_left","role":"office","x":[0,3],"y":[0,4]},
{"id":"F1_right","role":"corridor","x":[3,6],"y":[0,4]}]}],
"windows":[{"id":"W1","floor":"F1","facade":"West","span":[1,2],
"z":[1,2],"room":"F1_left"}],
"openings":[{"id":"D1","kind":"door","space_id":"F1_left",
"other_space_id":"F1_right","p1":[3,1],"p2":[3,2],"z":[0,2.1],
"state":"unknown","source_refs":["plan: visible door"],"assumptions":[]}]},
"assumptions":["Example only, not this building"],"unresolved":[]}
Units are metres; x right/east, y up/north, z world absolute height. Window
span uses x on North/South and y on East/West. Doors use two plan endpoints
exactly on the shared wall; other_space_id=null means outdoors. Heights are
absolute also on upper floors. Door state is unknown unless evidenced.
Nonrectangular rooms use polygon:[[x,y],...] (CCW, unclosed, orthogonal) and
x/y bounding intervals. These rooms must stay intact. Rooms cover each floor
without gaps/overlap: use an explicitly declared representative wall plane to
abstract thickness. Do not add fake interior walls or floor void closures.
Keep source_refs on cells/windows when available and list assumptions clearly.
The current tool supports orthogonal floors; explicitly report unsupported
geometry. The example numbers/counts are unrelated to the supplied drawings.
"""


def dump(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinate_grid_view(pic, region):
    """Label original pixels on a disposable model view, keeping its affine frame."""
    if min(pic.size) < 100:
        return pic, {"shown": False, "reason": "small unscaled detail"}
    pic = pic.copy()
    draw = ImageDraw.Draw(pic)
    x0, y0, x1, y1 = region
    sx, sy = pic.width / (x1-x0), pic.height / (y1-y0)
    step = 100 if max(x1-x0, y1-y0) < 800 else 200
    ticks = {"x": [], "y": []}
    def label(point, value):
        bounds = draw.textbbox(point, value)
        draw.rectangle((bounds[0]-2, bounds[1]-1, bounds[2]+2, bounds[3]+1), fill="black")
        draw.text(point, value, fill="white")
    for value in range(((x0+step-1)//step)*step, x1, step):
        x = round((value-x0)*sx)
        for y in range(0, pic.height, 16):
            draw.line([(x,y),(x,min(y+4,pic.height-1))], fill=(80,160,190))
        label((min(max(x+3, 3), pic.width-48), 3), f"x={value}")
        ticks["x"].append({"original_pixel":value,"display_pixel":x})
    for value in range(((y0+step-1)//step)*step, y1, step):
        y = round((value-y0)*sy)
        for x in range(0, pic.width, 16):
            draw.line([(x,y),(min(x+4,pic.width-1),y)], fill=(80,160,190))
        label((3,min(max(y+3,17),pic.height-16)), f"y={value}")
        ticks["y"].append({"original_pixel":value,"display_pixel":y})
    return pic, {"shown":True,"units":"original image pixels","ticks":ticks,
                 "note":"Blue dotted grid/white labels are viewing aids, not drawing evidence."}


def terminate_subscription(process):
    """Stop this invocation and nested review sessions, including their MCPs."""
    rows = subprocess.check_output(["ps", "-eo", "pid=,ppid="], text=True)
    parents = {int(pid): int(parent) for pid, parent in (row.split() for row in rows.splitlines())}
    descendants = {process.pid}
    while True:
        expanded = descendants | {pid for pid, parent in parents.items() if parent in descendants}
        if expanded == descendants:
            break
        descendants = expanded
    groups = set()
    for pid in descendants:
        try:
            group = os.getpgid(pid)
            if group != os.getpgrp():
                groups.add(group)
        except ProcessLookupError:
            pass
    for group in groups:
        try:
            os.killpg(group, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        for group in groups:
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()


def subscription(run: Path, prompt: str, *, model: str, name: str,
                 readonly: bool = False, timeout: int = 900,
                 log_run: Path | None = None, receipt_context: dict | None = None):
    """Only the logged-in subscription; isolated cwd/env, explicit MCP tools.

    ``run`` is the MCP-visible workspace. ``log_run`` can retain a child
    observation's request, stream and receipt alongside its parent run.
    """
    if model not in {"sonnet", "haiku"}:
        raise ValueError("only configured subscription aliases are allowed")
    run = run.resolve()
    log_run = (log_run or run).resolve()
    from src.agent.execution.subscription_json import _isolated_env, _redact_secrets
    command = ["claude", "-p", "--model", model, "--tools", "",
               "--allowedTools", "mcp__bim__*", "--permission-mode", "dontAsk",
               "--strict-mcp-config", "--setting-sources", "",
               "--settings", '{"disableAllHooks":true}',
               "--no-session-persistence", "--output-format", "stream-json", "--verbose",
               "--system-prompt", ("Answer only the supplied local visual question using tools. "
                                    "Inspect a suitable crop; cite original pixel locations of marks. "
                                    "Separate door arcs, gaps and dimension ticks. State uncertainty; "
                                    "do not infer a connection just because rooms are adjacent. "
                                    "Do not plan the whole building."
                                    if readonly else GUIDE)]
    if not readonly:
        command.extend(["--effort", "medium"])
    server = [sys.executable, str(Path(__file__).resolve()), "serve", str(run)]
    if readonly:
        server.append("--readonly")
    command.extend(["--mcp-config", json.dumps({"mcpServers": {"bim": {
        "command": server[0], "args": server[1:], "alwaysLoad": True}}})])
    started = time.monotonic()
    record = {"requested_model": model, "channel": "Claude subscription; no API/fallback",
              "readonly": readonly, "timeout_seconds": timeout,
              "effort": None if readonly else "medium"}
    if receipt_context:
        record.update(receipt_context)
    dump(log_run / f"{name}_request.json", {**record, "prompt": prompt,
                                       "system_prompt": command[command.index("--system-prompt")+1]})
    stdout_path, stderr_path = log_run / f"{name}_stream.jsonl", log_run / f"{name}_stderr.log"
    with tempfile.TemporaryDirectory(prefix="bim-agent-cwd-") as cwd:
        with stdout_path.open("x") as stdout, stderr_path.open("x") as stderr:
            env = {**_isolated_env(), "ENABLE_TOOL_SEARCH": "false"}
            process = subprocess.Popen(command, cwd=cwd, env=env,
                                       stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                       text=True, start_new_session=True)
            try:
                process.communicate(prompt, timeout=timeout)
                record["returncode"] = process.returncode
            except subprocess.TimeoutExpired:
                terminate_subscription(process)
                record["timed_out"] = True
    for path in (stdout_path, stderr_path):
        path.write_text(_redact_secrets(path.read_text()))
    record["elapsed_seconds"] = round(time.monotonic() - started, 2)
    for line in stdout_path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            record["actual_model"] = event.get("model")
        if event.get("type") == "result":
            record["result"] = event
    dump(log_run / f"{name}_receipt.json", record)
    return record


DETAIL_MAX_TIMEOUT_SECONDS = 240
DETAIL_COMPLETION_RESERVE_SECONDS = 45
DETAIL_MIN_TIMEOUT_SECONDS = 15
DETAIL_OBSERVATION_LOCK = threading.Lock()


def prepare_detail_observation(toolkit: "Toolkit", question: str, images: list[str], name: str):
    """Make one immutable, image-only MCP workspace for a local observation."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("local review question must be non-empty")
    if not images:
        raise ValueError("choose at least one original image for local review")
    if len(set(images)) != len(images):
        raise ValueError("choose each local review image only once")
    sources = {image: toolkit.image_path(image) for image in images}
    child = toolkit.run / name
    child.mkdir(exist_ok=False)
    child_images = child / "images"
    child_images.mkdir()
    selected = {}
    for image, source in sources.items():
        target = child_images / image
        shutil.copy2(source, target)
        with PILImage.open(target) as picture:
            size = list(picture.size)
        selected[image] = {"size": size, "sha256": digest(target)}
        if selected[image]["sha256"] != toolkit.manifest["images"][image]["sha256"]:
            raise ValueError("selected original image changed while preparing local review")
    # Keep the caller's wording verbatim. File isolation cannot make a leading
    # question independent if the caller itself includes a candidate claim.
    (child / "question.txt").write_text(question, encoding="utf-8")
    manifest = {
        "images": selected,
        "input_mode": "isolated_detail_observation",
        "only_input": (
            "selected original image copies and local question; no parent scope, "
            "seed, candidates, history or evaluation"
        ),
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
    }
    dump(child / "inputs.json", manifest)
    return child, digest(child / "inputs.json")


def review_detail_observation(
        toolkit: "Toolkit", question: str, images: list[str], *, invoke=subscription) -> dict:
    """Run one bounded, readonly local observation and retain parent receipts."""
    # FastMCP may serve sync tools concurrently. Keep allocation, receipt creation
    # and the bounded invocation together so two calls cannot both claim detail_01.
    with DETAIL_OBSERVATION_LOCK:
        used = len(list(toolkit.run.glob("detail_*_request.json")))
        if used >= 2:
            return {"error": "local review budget exhausted", "completed": False}
        remaining = toolkit.remaining_seconds()
        if remaining is not None:
            timeout = min(DETAIL_MAX_TIMEOUT_SECONDS, remaining - DETAIL_COMPLETION_RESERVE_SECONDS)
            if timeout < DETAIL_MIN_TIMEOUT_SECONDS:
                return {"error": "insufficient remaining budget for local review",
                        "completed": False, "remaining_seconds": remaining}
        else:
            timeout = DETAIL_MAX_TIMEOUT_SECONDS
        name = f"detail_{used + 1:02d}"
        child, input_sha256 = prepare_detail_observation(toolkit, question, images, name)
        source = {"run": name, "input_sha256": input_sha256,
                  "images": {image: toolkit.manifest["images"][image]["sha256"] for image in images}}
        result = invoke(child, f"Images: {images}\nQuestion: {question}", model="haiku", name=name,
                        readonly=True, timeout=timeout, log_run=toolkit.run,
                        receipt_context={"observation_source": source})
        result_event = result.get("result")
        completed = (bool(result_event) and not result_event.get("is_error", False)
                     and not result.get("timed_out", False) and result.get("returncode") == 0)
        return {"actual_model": result.get("actual_model"),
                "timed_out": result.get("timed_out", False),
                "returncode": result.get("returncode"),
                "result": result_event.get("result", "No completed answer") if result_event else "No completed answer",
                "is_error": result_event.get("is_error", False) if result_event else True,
                "completed": completed,
                "observation_source": source,
                "remaining_seconds": toolkit.remaining_seconds()}


def cost_receipt_summary(run: Path):
    """Read each root receipt once; detail child folders deliberately have none."""
    receipts = [json.loads(path.read_text()) for path in sorted(run.glob("*_receipt.json"))]
    estimates = [receipt.get("result", {}).get("total_cost_usd") for receipt in receipts]
    complete = all(isinstance(value, (int, float)) for value in estimates)
    partial = sum(value for value in estimates if isinstance(value, (int, float)))
    return receipts, {"estimated_cost_usd": partial if complete else None,
                      "cost_receipts_complete": complete,
                      "reported_partial_cost_usd": partial}


class Toolkit:
    def __init__(self, run: Path, readonly=False):
        self.run = run.resolve()
        self.manifest = json.loads((self.run / "inputs.json").read_text())
        self.readonly = readonly

    def log(self, action, data):
        with (self.run / "tools.jsonl").open("a") as stream:
            stream.write(json.dumps({"time": time.time(), "readonly": self.readonly,
                                     "action": action, "data": data}, ensure_ascii=False) + "\n")

    def candidate_path(self, candidate):
        allowed = {p.name for p in self.run.glob("candidate_*") if p.is_dir()}
        if (self.run / "seed").is_dir():
            allowed.add("seed")
        if candidate not in allowed:
            raise ValueError("unknown candidate")
        return self.run / candidate

    def remaining_seconds(self):
        deadline = self.manifest.get("deadline_epoch")
        return max(0, round(deadline - time.time())) if deadline else None

    def delivery(self, candidate, *, selection_origin, generation_status=None):
        """Build the handoff from saved source/check records, never model prose."""
        from src.agent.geometry.bim_delivery import summarize_delivery
        path = self.candidate_path(candidate)
        source = json.loads((path / "source_model.json").read_text())
        reviews = [json.loads(p.read_text()) for p in
                   sorted((self.run / "opening_reviews").glob("review_*.json"))]
        result = {"candidate": candidate, "selection_origin": selection_origin,
                  "viewer": f"{candidate}/viewer.html", "source_model": f"{candidate}/source_model.json",
                  "viewer_exists": (path / "viewer.html").is_file(),
                  "generation_status": generation_status or {"state":"in_progress"},
                  **summarize_delivery(source, reviews)}
        result["source_image_feedback"] = self._delivery_projection_status(candidate, source)
        dump(self.run / "delivery.json", result)
        # A separate handoff preserves the immutable candidate's original report.
        statuses = {"not_reviewed":"未回查", "partial":"仅有局部回查",
                    "consistent_with_supplied_observations":"与所报观察一致",
                    "observations_require_follow_up":"仍需跟进"}
        kinds = {"door":"门洞", "window":"窗", "passage":"空通道"}
        scopes = result["opening_review_scopes"]
        rows = "".join(
            f'<tr><td>{html.escape(s["floor_id"])}</td><td>{kinds[s["kind"]]}</td>'
            f'<td>{s["built_count"]}</td><td>{statuses[s["review_status"]]}</td></tr>'
            for s in scopes)
        facades = {"North":"北", "South":"南", "East":"东", "West":"西"}
        facade_scopes = result.get("facade_review_scopes", [])
        facade_rows = "".join(
            f'<tr><td>{html.escape(s["floor_id"])}</td><td>{facades[s["facade"]]}</td>'
            f'<td>{kinds[s["kind"]]}</td><td>{s["built_count"]}</td>'
            f'<td>{statuses[s["review_status"]]}</td></tr>' for s in facade_scopes)
        facade_table = (
            '<details><summary>逐立面回查范围</summary>'
            '<p>零个已建开口也需明确观察；内部及无法确定方向的开口不能靠立面回查覆盖。'
            '与所报观察一致仍不代表原图保真。</p><table>'
            '<tr><th>楼层</th><th>立面</th><th>类别</th><th>已建数量</th><th>回查状态</th></tr>'
            f'{facade_rows}</table></details>' if facade_rows else '')
        notes = "".join(f'<li>{html.escape(s)}</li>' for s in result["generation"]["unresolved"])
        assumptions = "".join(f'<li>{html.escape(s)}</li>' for s in result["assumptions"])
        counts = result["counts"]
        geometry_status = {"pass":"通过", "warning":"有警告", "severe":"有严重问题"}.get(
            (result.get("source_validation") or {}).get("status"), "未评价")
        selected = "模型选定" if selection_origin == "agent_selected" else "系统保留的最新候选，模型未显式选定"
        run_status = result["generation_status"]
        run_note = {"completed":"本次模型调用正常结束。", "in_progress":"模型调用尚未结束。",
                    "interrupted":"本次模型调用未正常完成，以下保留已生成候选。"}[run_status["state"]]
        if run_status.get("error"):
            run_note += " " + html.escape(run_status["error"])
        feedback = result["source_image_feedback"]
        wall_report = result.get("wall_dimension_report") or {}
        wall_findings = wall_report.get("findings", [])
        wall_rows = "".join(
            f'<tr><td>{html.escape(d["id"])}</td><td>{d["raw_length_m"]}</td>'
            f'<td>{d["representative_length_m"]}</td><td>{d["residual_m"]}</td></tr>'
            for d in wall_report.get("dimensions", []))
        finding_rows = "".join(f'<li>{html.escape(f["dimension_id"])}：{html.escape(f["message"])}</li>'
                               for f in wall_findings)
        calibration_rows = "".join(
            f'<li>{html.escape(row["image"])} / {html.escape(row["floor_id"])}：'
            f'{html.escape(str(warning.get("guidance", warning.get("type"))))}</li>'
            for row in feedback["current_source_projections"] for warning in row.get("calibration_warnings", []))
        host_rows = "".join(
            f'<tr><td>{html.escape(row["image"])} / {html.escape(row["floor_id"])}</td>'
            f'<td>{html.escape(point["marker"])} · {html.escape(point["dimension_id"])}</td>'
            f'<td>{html.escape(", ".join(point["boundary_ids"]))}</td>'
            f'<td>{point["tangential_outside_distance_m"]}</td></tr>'
            for row in feedback["current_source_projections"]
            for point in (row.get("wall_evidence_projection") or {}).get("endpoints", []))
        host_html = (
            '<details><summary>尺寸证据与所引用墙段的位置对照</summary>'
            '<p>图中 W 为已引用墙段，D 的 S/E 为原记录起点/终点。下表距离表示证据点沿墙方向'
            '超出该墙段范围的长度，依赖本图标定；0 不证明归属正确，尺寸引出线也可能合理地落在墙段外。</p>'
            '<table><tr><th>原图 / 楼层</th><th>证据点</th><th>所引用墙段</th>'
            f'<th>沿墙超出范围（米）</th></tr>{host_rows}</table></details>' if host_rows else '')
        evidence_html = (
            '<h2>尺寸与标定的实际反馈</h2><p>以下为工具计算，原始数值及未处理问题不会被模型总结覆盖。'
            '尺寸残差不自动等于建模错误；同墙侧面次序冲突应先核对端点。单位：米。</p>'
            '<table><tr><th>尺寸</th><th>原标注</th><th>换算后代表面距</th><th>模型减换算值</th></tr>'
            f'{wall_rows}</table><ul>{finding_rows}{calibration_rows}</ul>{host_html}'
            if wall_rows or calibration_rows else '')
        current_projection_rows = "".join(
            f'<li>{html.escape(row["image"])} / {html.escape(row["floor_id"])}：'
            f'<a href="{html.escape(row["overlay_image"])}">当前源回叠图</a></li>'
            for row in feedback["current_source_projections"])
        old_projection_rows = "".join(
            f'<li>{html.escape(row["image"])} / {html.escape(row["floor_id"])}：'
            f'{html.escape(row["source_model_sha256"][:12])}</li>'
            for row in feedback["old_source_projections"])
        uncovered_rows = "".join(
            f'<li>{html.escape(row["image"])} / {html.escape(row["floor_id"])}（当前源无该楼层）</li>'
            for row in feedback["registered_calibration_uncovered_floors"])
        unregistered_floor_rows = "".join(
            f'<li>{html.escape(floor_id)}（当前源没有任何登记图面）</li>'
            for floor_id in feedback["floors_without_registered_views"])
        projection_error_rows = "".join(
            f'<li>{html.escape(str(row.get("image")))} / {html.escape(str(row.get("floor_id")))}：'
            f'{html.escape(row["error"])}</li>' for row in feedback["projection_errors"])
        missing_or_failed_rows = uncovered_rows + projection_error_rows
        feedback_html = (
            '<h2>原图回叠反馈</h2><p>标定由模型提供，尚未独立验证；图像已生成不代表已审视或原图保真。</p>'
            f'<p>当前源投影 {len(feedback["current_source_projections"])} 份；旧源投影 '
            f'{len(feedback["old_source_projections"])} 份；登记但当前楼层未覆盖 '
            f'{len(feedback["registered_calibration_uncovered_floors"])} 份；当前源无登记图面楼层 '
            f'{len(feedback["floors_without_registered_views"])} 个。</p>'
            f'<ul>{current_projection_rows or "<li>当前源没有成功的回叠图。</li>"}</ul>'
            f'<details><summary>旧源投影</summary><ul>{old_projection_rows or "<li>无</li>"}</ul></details>'
            f'<details><summary>未覆盖或失败</summary><ul>{missing_or_failed_rows or "<li>无</li>"}'
            f'{unregistered_floor_rows}</ul></details>')
        (self.run / "delivery.html").write_text(
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<title>BIM 候选与实际检查</title><style>body{font:16px system-ui;'
            'max-width:1100px;margin:30px auto;padding:0 16px;line-height:1.6}'
            'table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #ccc;text-align:left}'
            'iframe{width:100%;height:680px;border:1px solid #ccc}</style>'
            '<h1>BIM 候选与实际检查</h1><p>以下状态来自保存的源模型和回查记录。'
            '几何自洽或观察对应不等于原图保真；未核查和待处理问题见下方记录。</p>'
            f'<p>{run_note}</p>'
            f'<p>{selected}：{html.escape(candidate)}。{counts["spaces"]} 个空间，'
            f'{counts["openings"]} 个已建开口，{counts["unbuilt_openings"]} 个未建开口。'
            f'几何自洽：{geometry_status}；原图保真：未评价。</p>'
            f'<p><a href="{result["viewer"]}">打开模型</a>'
            f' · <a href="{result["source_model"]}">源 BIM</a> · '
            '<a href="delivery.json">检查记录</a></p>'
            '<table><tr><th>楼层</th><th>类别</th><th>已建数量</th><th>原图观察回查</th></tr>'
            f'{rows}</table><p>{len(result["stale_reviews"])} 份旧源回查未用于当前候选。</p>'
            f'{facade_table}'
            f'<h2>尚未解决</h2><ul>{notes or "<li>模型未填写；仍需结合上表判断未核查范围。</li>"}</ul>'
            f'<details><summary>模型采用的假设</summary><ul>{assumptions}</ul></details>'
            f'{feedback_html}'
            f'{evidence_html}'
            f'<iframe title="保存的 BIM 候选" src="{result["viewer"]}"></iframe>'
            '</html>', encoding="utf-8")
        return result

    def build(self, proposal, *, action="build_bim", parent=None, operations=None):
        from src.agent.execution.source_proposal import export_source_proposal
        index = len(list(self.run.glob("candidate_*"))) + 1
        if index > 6:
            return {"error": "candidate budget exhausted; report saved partial results"}
        candidate = f"candidate_{index:02d}"
        provenance = {"input_manifest_sha256": digest(self.run/"inputs.json"),
                      "mode": self.manifest.get("input_mode", "original_images_agent_experiment"),
                      "generator": "Claude subscription tool loop"}
        if parent is not None:
            provenance.update(parent_candidate=parent,
                              parent_proposal_sha256=digest(self.candidate_path(parent)/"proposal.json"))
        report = export_source_proposal(proposal, self.run/candidate, provenance=provenance)
        if operations is not None:
            dump(self.run/candidate/"operations.json", operations)
        result = {"candidate": candidate, "remaining_seconds": self.remaining_seconds(), **report}
        source_path = self.run / candidate / "source_model.json"
        if source_path.exists():
            from src.agent.geometry.opening_review import opening_inventory
            result["opening_inventory"] = opening_inventory(json.loads(source_path.read_text()))
            result["opening_review"] = "not_reviewed; compare this inventory with distinct drawing marks"
            projections, errors = self.project_registered_calibrations(candidate, action)
            result["source_image_projections"] = projections
            result["projection_errors"] = errors
        self.log(action, result)
        return result

    def image_path(self, name):
        if name not in self.manifest["images"]:
            raise ValueError("choose an exact image name from input inventory")
        path = self.run / "images" / name
        if digest(path) != self.manifest["images"][name]["sha256"]:
            raise ValueError("input image changed")
        return path

    def _calibration_records(self):
        """Return immutable explicit calibration records in registration order."""
        folder = self.run / "overlay_calibrations"
        records = []
        for path in sorted(folder.glob("calibration_*.json")) if folder.is_dir() else []:
            record = json.loads(path.read_text())
            if not isinstance(record, dict):
                raise ValueError(f"invalid overlay calibration record: {path.name}")
            records.append((path, record))
        return records

    def registered_calibrations(self):
        """The latest explicit calibration for each exact original-image/floor pair."""
        latest = {}
        for path, record in self._calibration_records():
            image = record.get("image")
            floor_id = record.get("floor_id")
            if not isinstance(image, str) or not isinstance(floor_id, str):
                raise ValueError(f"invalid overlay calibration identity: {path.name}")
            latest[(image, floor_id)] = (path, record)
        return list(latest.values())

    def _save_calibration(self, *, candidate, image, floor_id, x_anchors, y_anchors, basis, metadata):
        """Append an explicit calibration. Later records supersede only the same pair."""
        folder = self.run / "overlay_calibrations"
        folder.mkdir(exist_ok=True)
        index = len(list(folder.glob("calibration_*.json"))) + 1
        path = folder / f"calibration_{index:03d}.json"
        record = {
            "schema_version": "source_overlay_calibration_v1",
            "calibration_id": path.stem,
            "image": image,
            "floor_id": floor_id,
            "image_sha256": self.manifest["images"][image]["sha256"],
            "x_anchors": x_anchors,
            "y_anchors": y_anchors,
            "basis": basis,
            "registered_by_candidate": candidate,
            "registered_source_model_sha256": metadata["source_model_sha256"],
            "calibration_basis": "caller_supplied_not_independently_verified",
            "calibration_unverified": True,
        }
        dump(path, record)
        return path, record

    def _save_overlay(self, pic, metadata, *, box=None):
        """Persist a full immutable projection and make the corresponding tool view."""
        folder = self.run / "image_overlays"
        folder.mkdir(exist_ok=True)
        stem = f"overlay_{len(list(folder.glob('overlay_*.json'))) + 1:03d}"
        original_size = list(pic.size)
        region = box or [0, 0, pic.width, pic.height]
        if box is not None:
            x0, y0, x1, y1 = box
            if not (0 <= x0 < x1 <= pic.width and 0 <= y0 < y1 <= pic.height):
                raise ValueError("crop outside original image bounds")
        # The stored overlay is full resolution.  The returned image follows the
        # same bounded presentation convention as view_image.
        pic.save(folder / f"{stem}.png")
        presented = pic.crop(region)
        presented.thumbnail((1600, 1600))
        metadata.update(
            overlay_image=f"image_overlays/{stem}.png",
            original_size=original_size,
            box_original_pixels=region,
            returned_size=list(presented.size),
            original_pixels_per_returned_pixel=[
                (region[2] - region[0]) / presented.width,
                (region[3] - region[1]) / presented.height,
            ],
            remaining_seconds=self.remaining_seconds(),
        )
        dump(folder / f"{stem}.json", metadata)
        data = io.BytesIO()
        presented.save(data, "PNG")
        return Image(data=data.getvalue(), format="png"), metadata

    def project_overlay(self, candidate, image, floor_id, x_anchors, y_anchors, basis, *,
                        trigger_action, box=None, calibration=None, automatic=False):
        """Render and persist one projection from an immutable saved source BIM."""
        from src.agent.geometry.source_image_overlay import render_source_overlay
        path = self.candidate_path(candidate)
        source = json.loads((path / "source_model.json").read_text())
        image_path = self.image_path(image)
        with PILImage.open(image_path) as raw:
            pic, metadata = render_source_overlay(source, raw, floor_id=floor_id,
                x_anchors=x_anchors, y_anchors=y_anchors, basis=basis, image_name=image)
        metadata.update(
            candidate=candidate,
            image=image,
            image_sha256=self.manifest["images"][image]["sha256"],
            trigger_action=trigger_action,
            automatic_projection=automatic,
        )
        if calibration is not None:
            calibration_path, calibration_record = calibration
            metadata["reused_calibration"] = {
                "calibration_id": calibration_record["calibration_id"],
                "calibration_file": str(calibration_path.relative_to(self.run)),
                "registered_by_candidate": calibration_record["registered_by_candidate"],
                "registered_source_model_sha256": calibration_record["registered_source_model_sha256"],
                "image_sha256": calibration_record["image_sha256"],
                "x_anchors": calibration_record["x_anchors"],
                "y_anchors": calibration_record["y_anchors"],
                "basis": calibration_record["basis"],
            }
        return self._save_overlay(pic, metadata, box=box)

    def project_registered_calibrations(self, candidate, action):
        """Reuse only caller-registered frames; projection failures preserve the BIM."""
        projections = []
        errors = []
        try:
            calibrations = self.registered_calibrations()
        except Exception as error:
            calibrations = []
            errors.append({"candidate": candidate, "trigger_action": action,
                           "error": f"could not load registered calibrations: {error}"})
        for calibration in calibrations:
            calibration_path, record = calibration
            error_context = {
                "candidate": candidate,
                "trigger_action": action,
                "image": record.get("image"),
                "floor_id": record.get("floor_id"),
                "calibration_file": str(calibration_path.relative_to(self.run)),
            }
            try:
                _, metadata = self.project_overlay(
                    candidate, record["image"], record["floor_id"], record["x_anchors"],
                    record["y_anchors"], record["basis"], trigger_action=action,
                    calibration=calibration, automatic=True)
                projections.append(metadata)
            except Exception as error:
                errors.append({**error_context, "error": str(error)})
        if errors:
            dump(self.candidate_path(candidate) / "projection_errors.json", {
                "candidate": candidate,
                "trigger_action": action,
                "projection_errors": errors,
            })
        return projections, errors

    def overlay_image(self, metadata):
        """Load only a projection created by this toolkit for MCP image content."""
        relative = metadata.get("overlay_image")
        if not isinstance(relative, str) or not relative.startswith("image_overlays/"):
            raise ValueError("invalid saved overlay reference")
        path = (self.run / relative).resolve()
        folder = (self.run / "image_overlays").resolve()
        if not path.is_file() or folder not in path.parents:
            raise ValueError("saved overlay is unavailable")
        with PILImage.open(path) as raw:
            pic = raw.convert("RGB")
            pic.thumbnail((1600, 1600))
            data = io.BytesIO()
            pic.save(data, "PNG")
        return Image(data=data.getvalue(), format="png")

    def _delivery_projection_status(self, candidate, source):
        """Describe stored projection evidence without treating it as a visual verdict."""
        source_hash = source.get("source_model_sha256")
        folder = self.run / "image_overlays"
        projections = []
        for path in sorted(folder.glob("overlay_*.json")) if folder.is_dir() else []:
            record = json.loads(path.read_text())
            if isinstance(record, dict) and record.get("mode") == "source_image_overlay":
                projections.append(record)
        current = [row for row in projections
                   if row.get("candidate") == candidate and row.get("source_model_sha256") == source_hash]
        old = [row for row in projections if row.get("source_model_sha256") != source_hash]
        floor_ids = {row.get("id") for row in source.get("floors", []) if isinstance(row, dict)}
        uncovered = []
        try:
            calibrations = self.registered_calibrations()
            calibration_load_errors = []
        except Exception as error:
            calibrations = []
            calibration_load_errors = [{"candidate": candidate, "trigger_action": "finish_bim",
                                        "error": f"could not load registered calibrations: {error}"}]
        registered_floor_ids = {calibration["floor_id"] for _, calibration in calibrations}
        for calibration_path, calibration in calibrations:
            if calibration["floor_id"] not in floor_ids:
                uncovered.append({
                    "image": calibration["image"], "floor_id": calibration["floor_id"],
                    "calibration_file": str(calibration_path.relative_to(self.run)),
                })
        error_path = self.candidate_path(candidate) / "projection_errors.json"
        errors = json.loads(error_path.read_text()).get("projection_errors", []) if error_path.is_file() else []
        errors = [*errors, *calibration_load_errors]
        fields = ("image", "floor_id", "overlay_image", "source_model_sha256", "trigger_action",
                  "automatic_projection", "reused_calibration", "anchors", "basis", "image_sha256")
        def compact(row):
            return {**{field: row[field] for field in fields if field in row},
                    "calibration_warnings": row.get("scale", {}).get("warnings", []),
                    "wall_evidence_projection": row.get("wall_evidence_projection")}
        return {
            "current_source_projections": [compact(row) for row in current],
            "old_source_projections": [compact(row) for row in old],
            "registered_calibration_uncovered_floors": uncovered,
            "floors_without_registered_views": sorted(floor_id for floor_id in floor_ids
                                                       if floor_id not in registered_floor_ids),
            "projection_errors": errors,
            "calibration_independently_verified": False,
            "drawing_fidelity": "not_evaluated",
        }

    def view(self, name, box=None, coordinate_grid=True):
        from mcp.server.fastmcp import Image
        with PILImage.open(self.image_path(name)) as raw:
            pic = raw.convert("RGB")
            original_size = list(pic.size)
            region = box or [0, 0, pic.width, pic.height]
            if box is not None:
                x0,y0,x1,y1 = box
                if not (0 <= x0 < x1 <= pic.width and 0 <= y0 < y1 <= pic.height):
                    raise ValueError("crop outside original image bounds")
                pic = pic.crop(box)
            pic.thumbnail((1600,1600))
            grid = {"shown": False}
            if coordinate_grid:
                pic, grid = coordinate_grid_view(pic, region)
            data = io.BytesIO(); pic.save(data, "PNG")
        metadata = {"name": name, "original_size": original_size, "coordinate_grid": grid,
                    "box_original_pixels": region, "returned_size": list(pic.size),
                    "original_pixels_per_returned_pixel": [
                        (region[2] - region[0]) / pic.width,
                        (region[3] - region[1]) / pic.height],
                    "coordinate_note": "Original pixel = crop origin + returned pixel * scale. Use ORIGINAL pixels for the next crop or measurement."}
        metadata["remaining_seconds"] = self.remaining_seconds()
        self.log("view_image", metadata)
        return [Image(data=data.getvalue(), format="png"), json.dumps(metadata)]

    def profile(self, name, box, axis, rgb, tolerance):
        import numpy as np
        with PILImage.open(self.image_path(name)) as raw:
            x0,y0,x1,y1 = box
            if not (0 <= x0 < x1 <= raw.width and 0 <= y0 < y1 <= raw.height):
                raise ValueError("box outside original image bounds")
            pixels = np.asarray(raw.convert("RGB").crop(box)).astype(float)
        if len(rgb) != 3 or not all(0 <= c <= 255 for c in rgb) or not 0 <= tolerance <= 442:
            raise ValueError("RGB in 0..255 and distance tolerance in 0..442 required")
        mask = np.linalg.norm(pixels - np.asarray(rgb), axis=2) <= tolerance
        if axis not in {"x", "y"}:
            raise ValueError("axis must be x or y")
        counts = mask.sum(axis=0 if axis == "x" else 1)
        offset = x0 if axis == "x" else y0
        # Return runs of positive support plus maxima, without naming objects.
        runs = []; start = None
        for i, count in enumerate([*counts, 0]):
            if count > 0 and start is None: start = i
            if count == 0 and start is not None:
                peak = start + int(counts[start:i].argmax())
                runs.append({"pixels": [start+offset, i-1+offset], "peak": peak+offset,
                             "max_count": int(counts[peak])})
                start = None
        result = {"axis": axis, "runs": runs, "matching_pixels": int(mask.sum())}
        self.log("pixel_profile", {"name": name, "box": box, "rgb": rgb,
                                   "tolerance": tolerance, "result": result})
        return result


def serve(run: Path, readonly=False):
    from mcp.server.fastmcp import FastMCP, Image
    toolkit = Toolkit(run, readonly)
    server = FastMCP("bim", log_level="WARNING")

    @server.tool()
    def inputs() -> dict:
        """List available original images, original pixel dimensions and input scope."""
        toolkit.log("inputs", {})
        return {**toolkit.manifest, "remaining_seconds": toolkit.remaining_seconds()}

    @server.tool()
    def view_image(name: str, box: list[int] | None = None, coordinate_grid: bool = True):
        """View a drawing or crop [left,top,right,bottom] in ORIGINAL pixels.
        Full views fit 1600 px; grid labels keep original coordinates after scaling.
        Use coordinate_grid=false for unmarked evidence; stored originals are unchanged.
        """
        return toolkit.view(name, box, coordinate_grid)

    @server.tool()
    def pixel_profile(name: str, box: list[int], axis: str,
                      rgb: list[int], tolerance: float = 70) -> dict:
        """Measure colored ink runs along x or y in an original-pixel crop.
        You select RGB/tolerance; results have no wall/door semantic labels.
        """
        return toolkit.profile(name, box, axis, rgb, tolerance)

    @server.tool()
    def map_dimension_chain(lengths: list[float], unit: str = "mm",
                            origin_m: float = 0.0, direction: int = 1,
                            expected_total: float | None = None) -> dict:
        """Accumulate observed dimension labels into ordered world-metre spans.
        lengths and expected_total use unit mm or m; origin_m is always metres.
        direction -1 walks from a known high coordinate toward lower coordinates.
        No OCR or semantic validation: retain evidence for labels and orientation.
        """
        from src.agent.geometry.dimension_chain import map_dimension_chain as calculate
        result = calculate(lengths, unit=unit, origin_m=origin_m,
                           direction=direction, expected_total=expected_total)
        toolkit.log("map_dimension_chain", {"lengths": lengths, "result": result})
        return result

    def candidate_result(result) -> CallToolResult:
        """Keep JSON structured output while attaching newly generated feedback views."""
        content = []
        for metadata in result.get("source_image_projections", []):
            try:
                content.append(toolkit.overlay_image(metadata).to_image_content())
            except Exception as error:
                result.setdefault("projection_errors", []).append({
                    "candidate": result.get("candidate"), "trigger_action": "mcp_result_packaging",
                    "image": metadata.get("image"), "floor_id": metadata.get("floor_id"),
                    "overlay_image": metadata.get("overlay_image"), "error": str(error),
                })
        content.append(TextContent(type="text", text=json.dumps(result, ensure_ascii=False)))
        return CallToolResult(content=content, structuredContent=result)

    @server.tool()
    def map_pixels(points: list[list[float]], x_anchors: list[list[float]],
                   y_anchors: list[list[float]]) -> dict:
        """Convert selected original pixel points to metres with two anchors per axis.
        Each anchor is [pixel_position, world_metres]. Y normally has negative
        slope. Anchors must come from your observed dimensions or explicit assumption;
        this tool does arithmetic and does not establish the drawing scale for you.
        """
        import math
        def fit(anchors):
            if len(anchors)!=2 or any(len(a)!=2 for a in anchors):
                raise ValueError("exactly two [pixel, metre] anchors per axis")
            if not all(math.isfinite(v) for a in anchors for v in a):
                raise ValueError("anchors must be finite")
            (p0,w0),(p1,w1)=anchors
            if p0==p1 or w0==w1: raise ValueError("distinct anchors required")
            slope=(w1-w0)/(p1-p0)
            return slope,w0-slope*p0
        ax,bx=fit(x_anchors); ay,by=fit(y_anchors)
        if any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in points):
            raise ValueError("points must be finite [x,y]")
        result={"world_points":[[round(ax*x+bx,6),round(ay*y+by,6)] for x,y in points],
                "metres_per_pixel":[ax,ay]}
        toolkit.log("map_pixels",{"points":points,"x_anchors":x_anchors,
                                  "y_anchors":y_anchors,"result":result})
        return result

    if not readonly:
        @server.tool()
        def check_wall_dimensions(candidate: str, references_json: str = "", dimensions_json: str = "",
                                  include_inventory: bool = False) -> dict:
            """List real wall hosts or convert explicit wall-face dimensions without changing geometry.
            Inputs use GUIDE wall_references/wall_dimensions format. Empty strings
            reuse saved evidence. Persist new evidence separately via revise_bim.
            Inventory is included only when no references exist or explicitly requested.
            """
            from src.agent.geometry.wall_reference import resolve_wall_references, convert_wall_dimensions
            path = toolkit.candidate_path(candidate)
            source = json.loads((path / "source_model.json").read_text())
            proposal = json.loads((path / "proposal.json").read_text())
            references = json.loads(references_json) if references_json else proposal.get("wall_references", [])
            dimensions = json.loads(dimensions_json) if dimensions_json else proposal.get("wall_dimensions", [])
            for d in dimensions:
                for end in ("start", "end"):
                    endpoint = d[end]
                    x, y = endpoint["pixel"]
                    with PILImage.open(toolkit.image_path(endpoint["image"])) as pic:
                        if not (0 <= x < pic.width and 0 <= y < pic.height):
                            raise ValueError("dimension endpoint outside original image")
            walls = resolve_wall_references(source, references)
            result = {"candidate": candidate, "source_model_sha256": source["source_model_sha256"],
                      "dimension_report": convert_wall_dimensions(walls, dimensions), "walls": walls}
            if include_inventory or not references:
                result["boundary_inventory"] = [{k: b[k] for k in ("id", "space_id", "vertices", "counterpart_ids")}
                                                 for b in source["boundaries"] if b["geometry_type"] == "wall"]
            toolkit.log("check_wall_dimensions", result)
            return result

        @server.tool()
        def inspect_candidate(candidate: str = "seed") -> dict:
            """Read a saved candidate's proposal and production geometry checks.
            No independent evaluation or reference answer is exposed.
            """
            path = toolkit.candidate_path(candidate)
            proposal = json.loads((path/"proposal.json").read_text())
            report = json.loads((path/"report.json").read_text())
            result = {"candidate": candidate, "proposal": proposal,
                      "wall_dimension_report": report.get("wall_dimension_report"),
                      "source_validation": report.get("source_validation"),
                      "counts": report.get("counts"),
                      "remaining_seconds": toolkit.remaining_seconds()}
            toolkit.log("inspect_candidate", {"candidate": candidate})
            return result

        @server.tool()
        def check_openings(candidate: str, review_json: str = "") -> dict:
            """List actual openings, or check original-image marks against them.
            review_json is documented in the brief. Saves a source-hash-bound
            review independently; never modifies the BIM or certifies image truth.
            """
            from src.agent.geometry.opening_review import facade_inventory, opening_inventory, review_openings
            path = toolkit.candidate_path(candidate)
            source = json.loads((path / "source_model.json").read_text())
            if not review_json:
                result = {"candidate": candidate, "inventory": opening_inventory(source),
                          "facade_inventory": facade_inventory(source),
                          "drawing_fidelity": "not_evaluated"}
            else:
                observations = json.loads(review_json)
                toolkit.image_path(observations["image"])
                report = review_openings(source, observations, toolkit.manifest["images"])
                folder = run / "opening_reviews"
                folder.mkdir(exist_ok=True)
                target = folder / f"review_{len(list(folder.glob('review_*.json'))) + 1:03d}.json"
                result = {"candidate": candidate, "review_file": str(target.relative_to(run)), **report}
                dump(target, {**result, "observations": observations})
            result["remaining_seconds"] = toolkit.remaining_seconds()
            toolkit.log("check_openings", result)
            return result

        @server.tool()
        def finish_bim(candidate: str) -> dict:
            """Select a saved BIM and persist a handoff based on actual checks.
            Unreviewed/pending scopes remain explicit. This does not certify image
            fidelity or prevent further work; call again to choose another candidate.
            """
            result = toolkit.delivery(candidate, selection_origin="agent_selected")
            dump(run / "delivery_selection.json", {
                "candidate": candidate, "source_model_sha256": result["source_model_sha256"]})
            toolkit.log("finish_bim", result)
            return {**{k:v for k,v in result.items() if k != "opening_inventory"},
                    "remaining_seconds": toolkit.remaining_seconds()}

        @server.tool()
        def overlay_candidate(candidate: str, image: str, floor_id: str,
                              x_anchors: list[list[float]], y_anchors: list[list[float]],
                              basis: str, box: list[int] | None = None,
                              reuse_on_revision: bool = True):
            """Project actual source geometry onto an AXIS-ALIGNED original plan.
            Each axis needs two [ORIGINAL pixel position, world metres] anchors,
            like map_pixels; basis explains the observed dimension and wall reference.
            No GT, auto-registration, perspective correction or visual verdict.
            Optional box crops the result in ORIGINAL pixels. Colours: magenta
            source boundaries, orange doors/passages, lime windows.
            Wall/evidence labels compare saved segment extents with original
            dimension pixels on this exact image. Distances depend on your
            calibration; extension-line ticks may lie outside a valid host.
            By default, this explicit caller-supplied calibration is saved and only
            reused for the same image/floor after later build_bim or revise_bim.
            """
            image_content, metadata = toolkit.project_overlay(
                candidate, image, floor_id, x_anchors, y_anchors, basis,
                trigger_action="overlay_candidate", box=box)
            if reuse_on_revision:
                calibration_path, calibration = toolkit._save_calibration(
                    candidate=candidate, image=image, floor_id=floor_id,
                    x_anchors=metadata["anchors"]["x"], y_anchors=metadata["anchors"]["y"],
                    basis=basis, metadata=metadata)
                metadata["registered_calibration"] = {
                    "calibration_id": calibration["calibration_id"],
                    "calibration_file": str(calibration_path.relative_to(run)),
                    "reuse_on_revision": True,
                }
                # This sidecar was created during this same explicit request;
                # earlier projection files are never changed or replaced.
                dump(run / metadata["overlay_image"].replace(".png", ".json"), metadata)
            else:
                metadata["registered_calibration"] = {"reuse_on_revision": False}
            toolkit.log("overlay_candidate", metadata)
            return [image_content, json.dumps(metadata)]

        @server.tool()
        def revise_bim(candidate: str, operations_json: str) -> CallToolResult:
            """Apply local edits/reflection with code and save a new checked BIM.
            See brief for operations. The prior candidate remains unchanged.
            Opening changes/removals and shared-wall moves require a reason and source_refs.
            """
            from src.agent.geometry.proposal_edits import apply_proposal_edits
            path = toolkit.candidate_path(candidate)
            proposal = json.loads((path/"proposal.json").read_text())
            operations = json.loads(operations_json)
            updated = apply_proposal_edits(proposal, operations)
            return candidate_result(toolkit.build(
                updated, action="revise_bim", parent=candidate, operations=operations))

        @server.tool()
        def review_detail(question: str, images: list[str]) -> dict:
            """Ask Haiku one small visual question, e.g. count/locate doors in a region.
            Give image names and original crop coordinates, and describe observable
            original-image evidence rather than a candidate conclusion. The submitted
            question is not text-cleaned, so this only isolates file context. At most
            two local reviews are available in this experiment.
            """
            response = review_detail_observation(toolkit, question, images)
            toolkit.log("review_detail", {"question": question, "images": images,
                                          "response": response})
            return response

        @server.tool()
        def build_bim(proposal_json: str) -> CallToolResult:
            """Build/check/save a candidate from the proposal JSON described in your brief.
            Returns errors or actual geometry checks. Six immutable candidates maximum.
            """
            return candidate_result(toolkit.build(json.loads(proposal_json)))

        @server.tool()
        def view_candidate(candidate: str, floor_id: str) -> Image:
            """Render a saved candidate's source-space plan, with windows blue/doors red.
            Use exact candidate from build_bim; floor_id is the proposed floor name.
            This is an inspection projection, not evidence from the original drawing.
            """
            path = toolkit.candidate_path(candidate)
            source = json.loads((path/"source_model.json").read_text())
            rooms = [s for s in source["spaces"] if s["floor_id"] == floor_id]
            if not rooms: raise ValueError("unknown floor_id")
            points = [p for s in rooms for p in s["polygon"]]
            x0,x1 = min(p[0] for p in points),max(p[0] for p in points)
            y0,y1 = min(p[1] for p in points),max(p[1] for p in points)
            scale = min(1000/(x1-x0),700/(y1-y0))
            convert = lambda p: (40+(p[0]-x0)*scale,40+(y1-p[1])*scale)
            pic = PILImage.new("RGB", (1080,800), "white"); draw = ImageDraw.Draw(pic)
            draw.text((1040, 15), "+Y / N", fill="black", anchor="rt")
            draw.line([(1050,70),(1050,30)], fill="black", width=3)
            draw.polygon([(1050,25),(1045,35),(1055,35)], fill="black")
            from shapely.geometry import Polygon
            for i,space in enumerate(rooms):
                ring = [convert(p) for p in space["polygon"]]
                draw.polygon(ring, fill=(220+(i*11)%30,225,235), outline="black", width=3)
                pt = Polygon(space["polygon"]).representative_point()
                draw.text(convert((pt.x,pt.y)), space["id"], fill="black", anchor="mm")
            ids = {s["id"] for s in rooms}
            for opening in source["openings"]:
                if not ids.intersection(opening["space_ids"]): continue
                pts = list(dict.fromkeys(tuple(v[:2]) for v in opening["vertices"]))
                draw.line([convert(p) for p in pts], fill="blue" if opening["kind"]=="window" else "red", width=6)
            data = io.BytesIO(); pic.save(data,"PNG")
            pic.save(run/candidate/f"plan_{rooms[0]['floor_id'].replace('/', '_')}.png")
            toolkit.log("view_candidate", {"candidate":candidate,"floor_id":floor_id})
            return Image(data=data.getvalue(), format="png")

    server.run()


def run_experiment(args):
    run = args.out.resolve(); run.mkdir(parents=True, exist_ok=False)
    (run/"images").mkdir()
    images = {}
    for path in sorted(args.images.glob("*.png")):
        target = run/"images"/path.name
        shutil.copy2(path,target)
        with PILImage.open(target) as im: size=list(im.size)
        images[path.name] = {"size":size,"sha256":digest(target)}
    if not images: raise ValueError("no PNG drawings in input directory")
    seed_path = getattr(args, "resume_candidate", None)
    manifest = {"images":images,"scope":args.scope,
                             "input_mode": "saved_candidate_recovery" if seed_path else "original_images_agent_experiment",
                             "deadline_epoch": time.time() + args.timeout,
                             "implementation_sha256": {
                                 "scripts/tool_scripts/run_bim_agent.py":digest(Path(__file__)),
                                 "src/agent/execution/source_proposal.py":digest(ROOT/"src/agent/execution/source_proposal.py"),
                                 "src/agent/geometry/proposal_edits.py":digest(ROOT/"src/agent/geometry/proposal_edits.py"),
                                 "src/agent/geometry/opening_review.py":digest(ROOT/"src/agent/geometry/opening_review.py"),
                                 "src/agent/geometry/bim_delivery.py":digest(ROOT/"src/agent/geometry/bim_delivery.py"),
                                 "src/agent/geometry/source_image_overlay.py":digest(ROOT/"src/agent/geometry/source_image_overlay.py"),
                                 "src/agent/geometry/source_bim.py":digest(ROOT/"src/agent/geometry/source_bim.py"),
                                 "src/agent/geometry/wall_reference.py":digest(ROOT/"src/agent/geometry/wall_reference.py"),
                                 "src/agent/geometry/dimension_chain.py":digest(ROOT/"src/agent/geometry/dimension_chain.py")},
                             "only_input": "original images, user scope, optional saved generated proposal; no GT/evaluation"}
    if seed_path:
        raw = (seed_path/"proposal.json").read_bytes()
        # Only the proposal is imported, never a report that might hold evaluation.
        proposal = json.loads(raw)
        manifest["seed"] = {"candidate": "seed", "proposal_sha256":hashlib.sha256(raw).hexdigest(),
                            "source":str(seed_path.resolve()), "mode":"previous_generated_proposal_recovery"}
        from src.agent.execution.source_proposal import export_source_proposal
        report = export_source_proposal(proposal, run/"seed", provenance=manifest["seed"])
        if not (run/"seed"/"source_model.json").exists():
            raise ValueError(f"seed cannot be materialized: {report.get('error')}")
    dump(run/"inputs.json", manifest)
    continuation = ("A saved proposal is available as seed. Compare its actual spatial partitions, "
                    "openings and connectivity with the original images. Choose substantive "
                    "discrepancies for local review or revision, while preserving reliable geometry; "
                    "do not redo a full reading." if seed_path else
                    "Generate an initial candidate early, then inspect and revise it.")
    record = subscription(run, f"Scope: {args.scope}\nBudget: {args.timeout} seconds. "
                          f"Start by listing supplied inputs. {continuation} "
                          "Report limitations honestly, and finish within the budget.",
                          model="sonnet", name="agent", timeout=args.timeout)
    candidates = []
    for path in sorted(run.glob("candidate_*/report.json")):
        report = json.loads(path.read_text())
        candidates.append({"candidate":path.parent.name,"status":report.get("status"),
                           "source_geometry_ready":report.get("source_geometry_ready"),
                           "viewer_exists":(path.parent/"viewer.html").is_file(),
                           "counts":report.get("counts")})
    selection = run / "delivery_selection.json"
    delivery = None
    response_completed = bool(record.get("result")) and not record["result"].get("is_error",False)
    generation_status = {"state":"completed" if response_completed else "interrupted",
                         "agent_response_completed":response_completed,
                         "elapsed_seconds":record["elapsed_seconds"],
                         "returncode":record.get("returncode"),
                         "timed_out":record.get("timed_out", False)}
    if record.get("result", {}).get("is_error"):
        generation_status["error"] = str(record["result"].get("result", "Model invocation failed"))[:1000]
    if selection.exists():
        chosen = json.loads(selection.read_text())["candidate"]
        delivery = Toolkit(run).delivery(chosen, selection_origin="agent_selected", generation_status=generation_status)
    else:
        saved = sorted(run.glob("candidate_*/source_model.json"))
        if not saved and (run / "seed/source_model.json").exists():
            saved = [run / "seed/source_model.json"]
        if saved:
            delivery = Toolkit(run).delivery(saved[-1].parent.name,
                selection_origin="latest_saved_fallback_not_agent_selected", generation_status=generation_status)
    receipts, cost_summary = cost_receipt_summary(run)
    summary = {"input_mode":manifest["input_mode"], "candidate_results":candidates,
               "agent_response_completed":response_completed,
               "has_viewable_candidate":any(c["viewer_exists"] for c in candidates) or bool(delivery and delivery["viewer_exists"]),
               "elapsed_seconds":record["elapsed_seconds"],"drawing_fidelity":"not_evaluated",
               "opening_reviews":[str(p.relative_to(run)) for p in sorted((run/"opening_reviews").glob("review_*.json"))],
               "delivery": {"candidate":delivery["candidate"], "selection_origin":delivery["selection_origin"],
                            "report":"delivery.json", "viewer":"delivery.html"} if delivery else None,
               "subscription_invocations":len(receipts),
               **cost_summary,
               "not_evaluated":["independent GT comparison","human approval","EnergyPlus"],
               "estimated_cost_note":"CLI estimates are not subscription bills"}
    dump(run/"summary.json",summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    run=commands.add_parser("run")
    run.add_argument("--images",type=Path,required=True)
    run.add_argument("--out",type=Path,required=True)
    run.add_argument("--scope",default="Reconstruct the building shown in all supplied drawings.")
    run.add_argument("--timeout",type=int,default=900)
    run.add_argument("--resume-candidate",type=Path,help="Recover from a saved proposal directory, not an independent cold start")
    server=commands.add_parser("serve")
    server.add_argument("run",type=Path)
    server.add_argument("--readonly",action="store_true")
    args=parser.parse_args()
    if args.command=="serve": serve(args.run.resolve(),args.readonly)
    else: run_experiment(args)


if __name__=="__main__": main()
