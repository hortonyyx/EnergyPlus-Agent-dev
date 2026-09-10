"""Small subscription-driven BIM experiment; no legacy flow or solver stages.

The model sees only an explicit image inventory and the tools below. MCP owns
file access and geometry execution; the model has no shell/repository tools.
This is an experimental entry point, not a complete product orchestrator.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image as PILImage, ImageDraw
from mcp.server.fastmcp import Image


GUIDE = """Build a viewable lightweight BIM from the supplied drawings. You choose
what to inspect, measure, infer, build and revise. Preserve physical rooms,
partitions, windows, doors and connectivity; never split a room to make a box.
Annotation + pixels is stronger than pixels alone, which is stronger than
inference. Missing evidence permits explicit assumptions, not silent omission.
Use measurements where useful; tools are optional methods, not a fixed workflow.
Use review_detail (Haiku subscription) for at least one small verifiable visual
question; you remain responsible for checking its answer against the drawing.
Do not ask the user for routine geometry choices. No EP/materials are needed.
build_bim saves immutable candidates and returns actual checks. Revise if a
check fails, keep stable object IDs and do not drop known openings to pass.
Inspect the resulting plan with view_candidate and compare to original images.
Geometric consistency is not drawing fidelity. Conclude with exact candidate,
assumptions, unresolved issues and what was/was not verified.

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
                 readonly: bool = False, timeout: int = 900):
    """Only the logged-in subscription; isolated cwd/env, explicit MCP tools."""
    if model not in {"sonnet", "haiku"}:
        raise ValueError("only configured subscription aliases are allowed")
    from src.agent.execution.subscription_json import _isolated_env, _redact_secrets
    command = ["claude", "-p", "--model", model, "--tools", "",
               "--allowedTools", "mcp__bim__*", "--permission-mode", "dontAsk",
               "--strict-mcp-config", "--setting-sources", "",
               "--settings", '{"disableAllHooks":true}',
               "--no-session-persistence", "--output-format", "stream-json", "--verbose",
               "--system-prompt", ("Answer only the supplied local visual question using tools. "
                                    "State uncertainty. Do not plan the whole building."
                                    if readonly else GUIDE)]
    server = [sys.executable, str(Path(__file__).resolve()), "serve", str(run)]
    if readonly:
        server.append("--readonly")
    command.extend(["--mcp-config", json.dumps({"mcpServers": {"bim": {
        "command": server[0], "args": server[1:], "alwaysLoad": True}}})])
    started = time.monotonic()
    record = {"requested_model": model, "channel": "Claude subscription; no API/fallback",
              "readonly": readonly, "timeout_seconds": timeout}
    dump(run / f"{name}_request.json", {**record, "prompt": prompt,
                                       "system_prompt": command[command.index("--system-prompt")+1]})
    stdout_path, stderr_path = run / f"{name}_stream.jsonl", run / f"{name}_stderr.log"
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
    dump(run / f"{name}_receipt.json", record)
    return record


class Toolkit:
    def __init__(self, run: Path, readonly=False):
        self.run = run.resolve()
        self.manifest = json.loads((self.run / "inputs.json").read_text())
        self.readonly = readonly

    def log(self, action, data):
        with (self.run / "tools.jsonl").open("a") as stream:
            stream.write(json.dumps({"time": time.time(), "readonly": self.readonly,
                                     "action": action, "data": data}, ensure_ascii=False) + "\n")

    def image_path(self, name):
        if name not in self.manifest["images"]:
            raise ValueError("choose an exact image name from input inventory")
        path = self.run / "images" / name
        if digest(path) != self.manifest["images"][name]["sha256"]:
            raise ValueError("input image changed")
        return path

    def view(self, name, box=None):
        from mcp.server.fastmcp import Image
        with PILImage.open(self.image_path(name)) as raw:
            pic = raw.convert("RGB")
            if box is not None:
                x0,y0,x1,y1 = box
                if not (0 <= x0 < x1 <= pic.width and 0 <= y0 < y1 <= pic.height):
                    raise ValueError("crop outside original image bounds")
                pic = pic.crop(box)
            pic.thumbnail((1600,1600))
            data = io.BytesIO(); pic.save(data, "PNG")
        self.log("view_image", {"name": name, "box_original_pixels": box,
                                "returned_size": list(pic.size)})
        return Image(data=data.getvalue(), format="png")

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
        return toolkit.manifest

    @server.tool()
    def view_image(name: str, box: list[int] | None = None) -> Image:
        """View a drawing or crop [left,top,right,bottom] in ORIGINAL pixels.
        Full views fit 1600 px; use inventory dimensions when choosing crops.
        """
        return toolkit.view(name, box)

    @server.tool()
    def pixel_profile(name: str, box: list[int], axis: str,
                      rgb: list[int], tolerance: float = 70) -> dict:
        """Measure colored ink runs along x or y in an original-pixel crop.
        You select RGB/tolerance; results have no wall/door semantic labels.
        """
        return toolkit.profile(name, box, axis, rgb, tolerance)

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
        def review_detail(question: str, images: list[str]) -> dict:
            """Ask Haiku one small visual question, e.g. count/locate doors in a region.
            Give image names and original crop coordinates; answer is evidence to check.
            At most two local reviews are available in this experiment.
            """
            for name in images: toolkit.image_path(name)
            used = len(list(run.glob("detail_*_request.json")))
            if used >= 2:
                return {"error": "local review budget exhausted"}
            result = subscription(run, f"Images: {images}\nQuestion: {question}",
                                  model="haiku", name=f"detail_{used+1:02d}",
                                  readonly=True, timeout=240)
            response = {"actual_model": result.get("actual_model"),
                        "timed_out": result.get("timed_out", False),
                        "result": result.get("result", {}).get("result", "No completed answer"),
                        "is_error": result.get("result", {}).get("is_error", False)}
            toolkit.log("review_detail", {"question": question, "images": images,
                                          "response": response})
            return response

        @server.tool()
        def build_bim(proposal_json: str) -> dict:
            """Build/check/save a candidate from the proposal JSON described in your brief.
            Returns errors or actual geometry checks. Six immutable candidates maximum.
            """
            from src.agent.execution.source_proposal import export_source_proposal
            index = len(list(run.glob("candidate_*")))+1
            if index > 6:
                return {"error": "candidate budget exhausted; report saved partial results"}
            candidate = f"candidate_{index:02d}"
            report = export_source_proposal(json.loads(proposal_json), run/candidate,
                provenance={"input_manifest_sha256": digest(run/"inputs.json"),
                            "mode": "original_images_agent_experiment",
                            "generator": "Claude subscription tool loop"})
            result = {"candidate": candidate, **report}
            toolkit.log("build_bim", result)
            return result

        @server.tool()
        def view_candidate(candidate: str, floor_id: str) -> Image:
            """Render a saved candidate's source-space plan, with windows blue/doors red.
            Use exact candidate from build_bim; floor_id is the proposed floor name.
            This is an inspection projection, not evidence from the original drawing.
            """
            if candidate not in {p.name for p in run.glob("candidate_*") if p.is_dir()}:
                raise ValueError("unknown candidate")
            source = json.loads((run/candidate/"source_model.json").read_text())
            rooms = [s for s in source["spaces"] if s["floor_id"] == floor_id]
            if not rooms: raise ValueError("unknown floor_id")
            points = [p for s in rooms for p in s["polygon"]]
            x0,x1 = min(p[0] for p in points),max(p[0] for p in points)
            y0,y1 = min(p[1] for p in points),max(p[1] for p in points)
            scale = min(1000/(x1-x0),700/(y1-y0))
            convert = lambda p: (40+(p[0]-x0)*scale,40+(y1-p[1])*scale)
            pic = PILImage.new("RGB", (1080,800), "white"); draw = ImageDraw.Draw(pic)
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
    dump(run/"inputs.json", {"images":images,"scope":args.scope,
                             "implementation_sha256": {
                                 "scripts/tool_scripts/run_bim_agent.py":digest(Path(__file__)),
                                 "src/agent/execution/source_proposal.py":digest(ROOT/"src/agent/execution/source_proposal.py")},
                             "only_input": "original image bytes and user scope; no GT/history"})
    record = subscription(run, f"Scope: {args.scope}\nStart by listing the supplied images. "
                          "Generate and inspect a useful BIM candidate; report limitations honestly.",
                          model="sonnet", name="agent", timeout=args.timeout)
    candidates = []
    for path in sorted(run.glob("candidate_*/report.json")):
        report = json.loads(path.read_text())
        candidates.append({"candidate":path.parent.name,"status":report.get("status"),
                           "source_geometry_ready":report.get("source_geometry_ready"),
                           "viewer_exists":(path.parent/"viewer.html").is_file(),
                           "counts":report.get("counts")})
    receipts = [json.loads(path.read_text()) for path in sorted(run.glob("*_receipt.json"))]
    estimates = [r.get("result", {}).get("total_cost_usd") for r in receipts]
    estimates_complete = all(isinstance(value, (int, float)) for value in estimates)
    reported_estimate = sum(value for value in estimates if isinstance(value, (int, float)))
    summary = {"candidate_results":candidates,"agent_response_completed":
               bool(record.get("result")) and not record["result"].get("is_error",False),
               "has_viewable_candidate":any(c["viewer_exists"] for c in candidates),
               "elapsed_seconds":record["elapsed_seconds"],"drawing_fidelity":"not_evaluated",
               "subscription_invocations":len(receipts),
               "estimated_cost_usd":reported_estimate if estimates_complete else None,
               "cost_receipts_complete":estimates_complete,
               "reported_partial_cost_usd":reported_estimate,
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
    server=commands.add_parser("serve")
    server.add_argument("run",type=Path)
    server.add_argument("--readonly",action="store_true")
    args=parser.parse_args()
    if args.command=="serve": serve(args.run.resolve(),args.readonly)
    else: run_experiment(args)


if __name__=="__main__": main()
