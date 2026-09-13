"""Image-only local partition observation; no seed, old reading, counts or GT."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import (
    Toolkit, digest, dump, prepare_detail_observation,
    review_detail_observation, subscription,
)
from PIL import Image

QUESTION = """Read only the physical partition layout on the supplied floor plan.
Do not design a building or reconstruct window heights. Establish which visible
strokes are physical partition walls, which are furniture or dimension marks,
and where partitions have doors or genuinely open ends. Do not assume rectangular
rooms or that adjacent furniture groups require separate rooms.
Use a small evidence ledger: for each major interior partition give an ID,
original-pixel endpoints/continuous intervals, visible gaps or open ends, the
connected spatial regions, and observed/inferred/uncertain status. List distinct
door marks separately with original-pixel boxes and the two regions they connect.
Describe the continuous circulation region and any nonrectangular boundaries.
Inspect crops and use the available pixel_profile measurement for uncertain
strokes where appropriate, selecting ink RGB and tolerance from this drawing;
the measurement has no semantic labels. If using world coordinates, first verify
the actual dimension extension endpoints, use map_pixels/map_dimension_chain for
arithmetic, and distinguish wall faces from representative axes. Pixel evidence
with explicit uncertainty is preferable to unsupported precise metres.
Return a compact structured JSON evidence ledger and a short list of unresolved
items within 240 seconds. This is an independent local observation: no expected
room counts or correct wall coordinates are supplied. Your observations will
need checking against the original before any BIM changes are made."""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--out", type=Path, default=ROOT / "AI_agent/logs/experiments/2026-09-13_sm24_plan_observation")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(exist_ok=False)
    (out / "images").mkdir()
    name = "1f_view.png"
    original = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data" / name
    target = out / "images" / name
    shutil.copy2(original, target)
    with Image.open(target) as im:
        size = list(im.size)
    dump(out / "inputs.json", {
        "images": {name: {"size": size, "sha256": digest(target)}},
        "input_mode": "developer_scoped_local_method_probe",
        "only_input": "one original plan and neutral procedural question; no seed, historical reading, counts or GT",
        "implementation_sha256": {"scripts/tool_scripts/run_bim_agent.py": digest(ROOT / "scripts/tool_scripts/run_bim_agent.py")},
    })
    if args.model == "haiku":
        response = review_detail_observation(Toolkit(out), QUESTION, [name])
    else:
        child, input_sha = prepare_detail_observation(
            Toolkit(out), QUESTION, [name], "detail_01", timeout_seconds=240)
        source = {"run": "detail_01", "input_sha256": input_sha,
                  "images": {name: digest(target)}}
        remaining = json.loads((child / "inputs.json").read_text())["deadline_epoch"] - time.time()
        receipt = subscription(child, f"Images: {[name]}\nQuestion: {QUESTION}",
                               model=args.model, name="detail_01", readonly=True,
                               timeout=remaining, log_run=out,
                               receipt_context={"observation_source": source})
        result = receipt.get("result", {})
        response = {"actual_model": receipt.get("actual_model"),
                    "completed": bool(result) and not result.get("is_error", False)
                        and not receipt.get("timed_out", False) and receipt.get("returncode") == 0,
                    "timed_out": receipt.get("timed_out", False),
                    "returncode": receipt.get("returncode"),
                    "result": result.get("result", "No completed answer"),
                    "is_error": result.get("is_error", not bool(result)),
                    "observation_source": source, "remaining_seconds": None}
    dump(out / "response.json", response)
    print(json.dumps(response, ensure_ascii=False, indent=2))
