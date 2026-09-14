"""Local wall/space-relation observation; independent of source models."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump, prepare_detail_observation, subscription

QUESTION = "Observe only physical partition relationships in the middle-right part of this original plan.\nYour local scope is original pixel box [360,260,630,610]. View the whole plan for orientation,\nthen a clean magnified crop and any measurements needed. You may look just outside this box\nfor wall junctions. No source BIM, expected room count, wall locations or answers are supplied.\nDo not reconstruct the whole floor or calculate metric coordinates.\n\nWithin this scope identify visible physical dividers and their full path between enclosing\nwall junctions, including continuation through an actual doorway. Distinguish them from\nfurniture edges and door-leaf/swing strokes. For each divider give two clear interior-floor\npoints immediately on opposite sides, away from wall thickness and furniture. Explain\nwhether it separates two actual spaces, is merely a free-ended wall fragment within one\nspace, or is uncertain. Two points on opposite sides of some ink do not by themselves prove\na physical room division; cite the wall's extent, end junctions, and aperture evidence.\nIf needed return multiple observed alternatives instead of guessing.\n\nAlso report any clearly continuous interior passage through this local scope as a short\npath of interior points. Such a path must stay within one actual space; crossing a door\nbetween rooms is connectivity, not continuous-space evidence. Pixel components can leak\nthrough doorways and are never room identity by themselves.\n\nReturn a concise JSON object with image, scope_box, partitions, continuities and unresolved.\nEach partition has id, points (a polyline in original pixels), side_a and side_b (interior\npixel points), relation (separates_spaces, wall_fragment, or uncertain), and evidence (what\nvisible marks, junctions and openings support it, with original pixel locations).\nEach continuity has id, path (original-pixel polyline within one continuous space), evidence.\nOnly state measurements/relations you actually checked. Keep unexamined parts explicit.\nNo full-floor space count, BIM output, heights or windows are requested."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", choices=("haiku", "sonnet"), default="haiku")
    args = parser.parse_args()
    run = args.out.resolve()
    run.mkdir(parents=True, exist_ok=False)
    (run / "images").mkdir()
    original = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data/1f_view.png"
    shutil.copy2(original, run / "images" / original.name)
    with Image.open(original) as picture:
        size = list(picture.size)
    files = [ROOT / "scripts/tool_scripts/run_bim_agent.py",
             ROOT / "scripts/tool_scripts/bim_agent_guidance.py",
             *sorted((ROOT / "src/agent/geometry").glob("*.py")),
             ROOT / "src/agent/execution/subscription_json.py", Path(__file__).resolve()]
    optional = ROOT / "scripts/tool_scripts/bim_agent_inputs.py"
    if optional.exists():
        files.append(optional)
    frozen = {str(path.relative_to(ROOT)): path.read_bytes() for path in files}
    dump(run / "inputs.json", {
        "images": {original.name: {"size": size, "sha256": digest(original)}},
        "input_mode": "developer_scoped_local_partition_relations",
        "only_input": "One original plan and an explicitly developer-selected local crop/question; no building declaration, seed, old observation or GT. The crop selection is assistance, not autonomous localization.",
        "implementation_sha256": {name: digest(ROOT / name) for name in frozen},
    })
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, [original.name],
                                             "detail_01", timeout_seconds=240)
    deadline = json.loads((child / "inputs.json").read_text())["deadline_epoch"]
    receipt = subscription(child, "Images: [1f_view.png]\nQuestion: " + QUESTION,
        model=args.model, effort="medium" if args.model == "sonnet" else None,
        name="detail_01", readonly=True, timeout=max(1, deadline - time.time()), log_run=run,
        receipt_context={"observation_source": {"run": "detail_01", "input_sha256": sha,
                              "images": {original.name: digest(original)}}})
    changed = []
    for name, data in frozen.items():
        if (ROOT / name).read_bytes() != data:
            changed.append(name)
        target = run / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    result = receipt.get("result", {})
    dump(run / "summary.json", {
        "actual_model": receipt.get("actual_model"), "effort": receipt.get("effort"),
        "elapsed_seconds": receipt["elapsed_seconds"],
        "completed": bool(result) and not result.get("is_error") and not receipt.get("timed_out"),
        "estimated_cost_usd": result.get("total_cost_usd"),
        "frozen_code_unchanged": not changed, "changed_files": changed,
        "limits": "Developer selected a middle-right crop, observation schema and budget; no answer feedback during execution. Not an autonomous BIM run or matched cost comparison. CLI estimate is not a bill.",
    })
    (run / "observation.md").write_text(result.get("result", "No completed answer"))
    print((run / "summary.json").read_text())


if __name__ == "__main__":
    main()
