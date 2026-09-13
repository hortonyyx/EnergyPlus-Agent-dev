"""Local annotation extraction with magnified views; no BIM or reference inputs."""
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

OUT = ROOT / "AI_agent/logs/experiments/2026-09-13_sm24_dimension_observation"
QUESTION = """Transcribe only the OUTERMOST CHAINED dimensions along the LEFT and
BOTTOM sides of the supplied floor plan: distinguish a chain of subdivisions
from the single overall dimension and from the inner window/door spacing chains.
Do not read the whole building or count rooms. Inspect the actual extension lines
to describe what endpoints the labels measure; leave their reference-face meaning
uncertain if unclear. Use display_scale=4 on suitable small detail crops and
coordinate_grid=false when labels obscure drawing text. All returned locations
must remain in original-image pixels.
For each of these two chains, return the labels exactly in page order (top-to-bottom
on the left, left-to-right at the bottom), units, approximate original-pixel boxes
or extension endpoints, and a brief note separating visible fact from assumption.
Use map_dimension_chain for arithmetic; do not fill an unlabelled remainder to
force closure. Compare its sum to the visible overall label, if readable.
Finish within the remaining time with a compact JSON response, no more than
400 words. No BIM, old coordinates, room counts, previous observation or GT is
provided. This is annotation evidence only, not a reconstructed room layout."""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.out.resolve()
    OUT.mkdir(exist_ok=False)
    (OUT / "images").mkdir()
    name = "1f_view.png"
    target = OUT / "images" / name
    shutil.copy2(ROOT / "case_tests/e2e_tests/sm24_anchor/case_data" / name, target)
    with Image.open(target) as im:
        size = list(im.size)
    dump(OUT / "inputs.json", {
        "images": {name: {"size": size, "sha256": digest(target)}},
        "input_mode": "developer_scoped_original_annotation_observation",
        "only_input": "one original plan and local question; no BIM, prior reading, correct labels or GT",
        "implementation_sha256": {"scripts/tool_scripts/run_bim_agent.py": digest(ROOT / "scripts/tool_scripts/run_bim_agent.py")},
    })
    child, input_sha = prepare_detail_observation(Toolkit(OUT), QUESTION, [name], "detail_01", timeout_seconds=180)
    source = {"run": "detail_01", "input_sha256": input_sha, "images": {name: digest(target)}}
    deadline = json.loads((child / "inputs.json").read_text())["deadline_epoch"]
    receipt = subscription(child, f"Images: {[name]}\nQuestion: {QUESTION}", model=args.model, name="detail_01",
                           readonly=True, timeout=deadline-time.time(), log_run=OUT,
                           receipt_context={"observation_source": source})
    result = receipt.get("result", {})
    response = {"actual_model": receipt.get("actual_model"), "timed_out": receipt.get("timed_out", False),
                "completed": bool(result) and not result.get("is_error", False) and not receipt.get("timed_out", False)
                             and receipt.get("returncode") == 0,
                "result": result.get("result", "No completed answer"), "observation_source": source}
    dump(OUT / "response.json", response)
    print(json.dumps(response, ensure_ascii=False, indent=2))
