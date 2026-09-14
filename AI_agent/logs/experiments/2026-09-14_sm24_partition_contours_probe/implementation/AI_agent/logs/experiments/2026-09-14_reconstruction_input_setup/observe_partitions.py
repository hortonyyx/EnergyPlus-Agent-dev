"""Bounded original-plan probe: inspect component contours before semantic grouping."""
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

QUESTION = """Identify the physical spaces and circulation in this original floor plan.
This is a bounded observation experiment, before metric dimensions or BIM assembly.
No expected room count, prior observation, coordinates, or generated model is supplied.

Test this observation method: after viewing the plan, use the numbered pixel-region
overview to locate floor regions, then inspect the returned seed contours with
view_pixel_region for the regions you classify as floor. Follow the actual tool
bounds, not remembered positions on the overview. Components are not rooms: furniture
and door leaves can divide a room's pixels, and openings may connect several spaces.
Do not give the same confidence to an overview guess and an inspected contour.

For adjacent regions you propose to merge or separate, inspect the original across
their actual facing edges. Identify the entire separator from one wall junction to
the next, its endpoints in ORIGINAL pixels, and any gap/door along it. A furniture
explanation needs visible evidence about its ends and relation to enclosing walls.
Trace bends/extensions of circulation in the original; adjacency is not a connection.
If uncertain, keep the alternatives explicit. Do not replace a missing observation
with a room-count assumption. No metric dimensions, calibration, heights or windows
are required for this task.

Answer concisely with (1) physical-space inventory: label, actual inspected region
IDs/seeds, complete extent including bends; (2) adjacent-space separators: space pair,
full wall/door/open span/furniture/unknown, path endpoints in original pixels, cited
view or measurement, and observed/inferred status; (3) unresolved or uninspected
regions. Any merger of floor regions must have a separator entry. Region IDs must
refer to the actual returned inventory; do not cite exterior annotation blobs as rooms.
Work within 240 seconds and reserve the last 30 seconds for the answer. This is an
observation, not a claim that a complete BIM or automatic fidelity pass exists.
"""


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
        "input_mode": "developer_scoped_contour_partition_observation",
        "only_input": "One original plan and generic contour/partition question; no building declarations, seed, old observations or GT.",
        "implementation_sha256": {name: digest(ROOT / name) for name in frozen},
    })
    child, sha = prepare_detail_observation(Toolkit(run), QUESTION, [original.name],
                                             "detail_01", timeout_seconds=240)
    deadline = json.loads((child / "inputs.json").read_text())["deadline_epoch"]
    receipt = subscription(child, "Images: [1f_view.png]\nQuestion: " + QUESTION,
        model=args.model, effort="low" if args.model == "sonnet" else None,
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
        "limits": "Developer chose the plan, contour-first method and budget; no answer feedback during execution. Not an autonomous BIM run or matched cost comparison. CLI estimate is not a bill.",
    })
    (run / "observation.txt").write_text(result.get("result", "No completed answer"))
    print((run / "summary.json").read_text())


if __name__ == "__main__":
    main()
