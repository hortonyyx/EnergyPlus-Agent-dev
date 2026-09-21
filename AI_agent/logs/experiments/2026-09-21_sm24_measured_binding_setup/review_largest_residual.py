"""Select a comparison's largest residual for a fresh local subscription review.

Selection is arithmetic from the completed worker record, not a developer answer.
The reviewer sees originals plus explicitly unverified claims, with no GT or BIM.
"""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, subscription


def pixel_at(metres, anchors):
    (p0, m0), (p1, m1) = anchors
    return p0 + (metres - m0) * (p1 - p0) / (m1 - m0)


def select(record):
    direction = record["direction_separation"]["lower_residual_direction"]
    if direction is None:
        raise ValueError("no relative direction hypothesis; cannot select paired residual")
    pairs = record["directions"][direction]["pairs_by_centre"]
    pair = max(pairs, key=lambda x: x["max_abs_endpoint_residual_m"])
    observations = record["observations"]
    plan = next(x for x in observations["plan"]["openings"] if x["id"] == pair["plan_id"])
    elevation = next(x for x in observations["elevation"]["openings"] if x["id"] == pair["elevation_id"])
    projected = [pixel_at(x, observations["plan"]["axis_anchors"])
                 for x in pair["elevation_span_after_direction_m"]]
    crops = {}
    for view, pixels in (("plan", [*plan["pixels"], *projected]),
                         ("elevation", elevation["pixels"])):
        source = record["original_images"][view]
        axis_index = 0 if source["axis"] == "x" else 1
        box = [0, 0, *source["size"]]
        box[axis_index] = max(0, math.floor(min(pixels)) - 40)
        box[axis_index + 2] = min(source["size"][axis_index], math.ceil(max(pixels)) + 40)
        crops[view] = {"image": source["image"], "box_original_pixels": box}
    return {"selection": "largest absolute endpoint residual under the lower-error direction hypothesis",
            "direction_is_hypothesis_not_acceptance": direction,
            "pair": pair, "unverified_claims": {"plan": plan, "elevation": elevation},
            "suggested_crops": crops,
            "limits": "Projected coordinates select a review area only, not a prescribed opening or correct geometry."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    parent = args.parent.resolve()
    if not (parent / "summary.json").is_file():
        raise ValueError("parent must be completed")
    path = sorted(parent.glob("facade_comparisons/*.json"))[-1]
    record = json.loads(path.read_text())
    selection = select(record)
    prompt = """Independently review the local cross-view discrepancy selected below.
The prior worker's spans, types and prose are UNVERIFIED CLAIMS, not drawing facts.
The direction transform is a hypothesis used to choose the area, not a correct answer.
View both supplied ORIGINAL images, starting with the suggested crops; enlarge or
change crops as needed. For the plan, inspect the complete selected wall stretch,
including both its claimed aperture and the area projected from the elevation.
Distinguish continuous wall strips from window frames, internal furniture and
dimension lines. For each actual aperture or solid-wall interval in this stretch,
give original pixel endpoints, the visible evidence, and any useful dimension label.
Use measurements when they resolve the issue, retaining the actual profile/candidate
references. Inspect enough of the perpendicular direction to establish where the
physical wall is, rather than treating an unrelated interior line as the facade.
State whether the apparent conflict is supported by the drawings or by the prior
worker's reading. Do not assume either view or either prior claim is correct.
Do not build a BIM or review the entire building. Report explicit unresolved details.
Local review selection:\n""" + json.dumps(selection, ensure_ascii=False, indent=2)
    run = args.out.resolve()
    run.mkdir(parents=True, exist_ok=False)
    shutil.copytree(parent / "images", run / "images")
    old = json.loads((parent / "inputs.json").read_text())
    manifest = {"images": old["images"], "scope": prompt,
                "input_mode": "automatically_selected_discrepancy_review",
                "only_input": "Original PNGs and explicitly unverified worker comparison claims; no developer correction, GT or BIM",
                "deadline_epoch": time.time() + args.timeout,
                "parent_comparison": {"path": str(path), "sha256": digest(path)},
                "implementation_sha256": {name: digest(ROOT / name) for name in
                    ("scripts/tool_scripts/run_bim_agent.py", "scripts/tool_scripts/bim_agent_guidance.py",
                     "src/agent/geometry/profile_observation_binding.py", "src/agent/geometry/facade_span_comparison.py",
                     "src/agent/execution/subscription_json.py", str(Path(__file__).relative_to(ROOT)))}}
    dump(run / "selection.json", selection)
    dump(run / "inputs.json", manifest)
    receipt = subscription(run, prompt, model="haiku", name="agent", readonly=True,
                           timeout=args.timeout)
    dump(run / "summary.json", {"scope": manifest["input_mode"],
                                "elapsed_seconds": receipt["elapsed_seconds"],
                                "actual_model": receipt.get("actual_model"),
                                "returncode": receipt.get("returncode"),
                                "timed_out": receipt.get("timed_out", False), "bim_created": False})
    print(json.dumps(json.loads((run / "summary.json").read_text())))


if __name__ == "__main__":
    main()
