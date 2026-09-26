"""Matched visual/measured probes and a separately labelled adaptive method probe."""
import argparse
import importlib
import json
from pathlib import Path
import shutil
import time

from PIL import Image
from scripts.tool_scripts.run_bim_agent import digest, dump, subscription

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
COMMON = """Inspect the single room containing the long rectangular desk near the
bottom-right corner of 1f_view.png. Identify its COMPLETE physical boundary, each
turn, and all door apertures on that boundary. Trace the room rather than the desk.
Also describe how the circulation immediately outside its interior door continues
around the room's upper boundary; distinguish an actual wall from an open continuation.
Use the full original and self-selected clean/magnified crops. All coordinates in
your final answer MUST be ORIGINAL pixels (x right, y down). Pick one representative
line through each drawn wall band, close the logical room boundary across actual
door gaps, and do not draw both wall faces as separate partitions. No guessed metric
conversion is needed. You have no generated geometry, previous observations, correct
counts, reference outlines or evaluation. The developer selected this local subject;
this is not whole-building reconstruction. Do not ask another model.

Return ONLY one JSON object, optionally in a json code fence, using this schema:
{"image":"1f_view.png","room_polygon_pixels":[[x,y],...],
 "doors":[{"id":"D1","p1":[x,y],"p2":[x,y],"destination":"interior_or_exterior",
 "evidence":"original location and visible jamb/swing evidence"}],
 "boundary_reasoning":"explain full boundary and turns",
 "circulation_reasoning":"describe complete nearby open continuation or separation",
 "measurements_used":[{"record":"saved profile/region id if any","use":"how it changed or supported the interpretation"}],
 "uncertainties":["actual remaining uncertainties"]}.
Vertices must run in cyclic order, without repeating the starting point. Door
endpoints are the two wall jambs, not hinge-to-leaf-tip. Do not fabricate tool IDs.
Geometry validity, colour components or matching pixels do not certify wall identity.
"""
METHODS = {
    "visual": """For this controlled direct-view condition, use inputs and view_image only.
Do not call numeric pixel/profile/region/trace/mapping/reference tools. Estimate
original-pixel coordinates from direct original views and explicitly label them
visual estimates. This restriction concerns observation method, not the answer.""",
    "measured": """For this controlled tool-assisted condition, use view_pixel_profile and/or
view_pixel_region_overview plus view_pixel_region to obtain saved numerical pixel
evidence for the complete boundary and its turns. Choose colours, crops, axes,
thresholds and region seeds yourself from the original. Compare the clean original
with masks, trace beyond crop edges and inspect adjoining spaces. Region components
can include furniture or connected spaces; profile peaks can be only local junctions.
Check both directions and the full wall extent before interpretation. Use measured
coordinates where the physical correspondence is justified; keep unsupported parts
as explicit visual estimates. Cite actual saved profile/region IDs and their role.
Do not merely call a tool and then ignore its evidence.""",
    "region_first": """This is a subsequent method-development probe, not an unchanged
repetition of the initial comparison. Work in this order:
1. View the original and locate the requested subject. Use view_pixel_region_overview
on the CLEAR FLOOR BACKGROUND colour, not wall or window ink. Select the candidate
around the requested subject by comparing its numbered location with the original.
2. Use view_pixel_region at that candidate's returned seed. Read its complete
outer_polygon_pixels and compare its clean/marked view. A region can contain
several connected spaces or be cut by furniture and door arcs; it is not a room.
3. Walk the complete contour, retaining actual wall turns. Resolve each departure
from a wall as furniture, door swing, open continuation, or uncertainty by looking
at the original. Use profiles for wall-band locations and the two jamb endpoints.
Do not replace a measured contour with its rectangular bounding box. Do not extend
a profile peak beyond its actual support intervals to invent a wall.
4. Check every proposed door lies ON the final room perimeter and agrees with its
visible jambs; a nearby door on another room is not this room's door. Examine the
space immediately beyond each door before deciding interior versus exterior.
5. Return the same requested JSON schema, citing actual region/profile IDs and
explaining what each measured contour feature means. Unsupported coordinates remain
explicit estimates. Do not ask another model or treat numerical geometry as proof
of semantic correctness.""",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("condition", choices=METHODS)
    parser.add_argument("--model", choices=("haiku", "sonnet"), default="haiku")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()
    run = HERE.parent / f"2026-09-26_sm24_local_{args.condition}_{args.model}{args.suffix}"
    run.mkdir(exist_ok=False)
    (run / "images").mkdir()
    original = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png"
    target = run / "images/1f_view.png"
    shutil.copy2(original, target)
    prompt = COMMON + "\n" + METHODS[args.condition]
    manifest = dict(images={"1f_view.png": {"sha256": digest(target), "size": list(Image.open(target).size)}},
        scope=prompt, provider="claude", input_mode="controlled_local_observation",
        observation_condition=args.condition, deadline_epoch=time.time() + args.timeout,
        only_input="One original PNG plus developer-selected local subject and observation method. No candidate/GT/reference answer.",
        implementation_sha256={name: digest(ROOT / name) for name in (
            "scripts/tool_scripts/run_bim_agent.py", "scripts/tool_scripts/bim_agent_guidance.py",
            "src/agent/geometry/pixel_region.py", "src/agent/geometry/pixel_region_overview.py",
            "src/agent/execution/subscription_json.py")},
        comparison_limits=["Method instructions differ; tool access is not server-enforced.",
            "Check actual actions for compliance; one pair is not statistical/causal proof.",
            "Development-selected local subject, not autonomous whole-building generation."])
    dump(run / "inputs.json", manifest)
    receipt = subscription(run, prompt, model=args.model, name="agent", readonly=True,
                           timeout=args.timeout, effort="medium" if args.model == "sonnet" else None)
    completed = (receipt.get("returncode") == 0 and not receipt.get("timed_out")
                 and not receipt.get("result", {}).get("is_error") and bool(receipt.get("result")))
    summary = dict(condition=args.condition, actual_model=receipt.get("actual_model"),
        elapsed_seconds=receipt["elapsed_seconds"], completed=completed,
        estimated_cost_usd=receipt.get("result", {}).get("total_cost_usd"),
        subscription_invocations=1, bim_created=False)
    dump(run / "summary.json", summary)
    # Preserve the answer verbatim; extracting/evaluating coordinates is post-run work.
    (run / "answer.txt").write_text(receipt.get("result", {}).get("result", ""))
    if (run / "tools.jsonl").exists():
        finalize = importlib.import_module("AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run")
        finalize.finalize(run)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
