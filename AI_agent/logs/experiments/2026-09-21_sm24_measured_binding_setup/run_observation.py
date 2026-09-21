"""Fresh original-only local observation; no previous BIM or measured answers."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, subscription
from PIL import Image

PROMPT = """Inspect the entire east facade's openings independently in the supplied
original floor plan and East elevation. Produce a complete local observation of
their positions and correspondence, separating windows, doors and uncertain marks.
You have no previous model or measurements. Read the facade_correspondence reference
for a generic measurement/comparison method. Choose your own original-image crops,
dimension anchors and measurements. Retain the original pixel intervals and evidence
for EVERY observed opening in each view separately; do not derive one list from the
other. Bind your axis length to observed original dimension labels/endpoints.
For endpoints measured with view_pixel_profile, submit saved profile_id/candidate
references in compare_facade_spans pixel slots (including measured axis anchors),
so the tool adopts the actual measurements. Do not retype visual estimates of
those measured coordinates. You choose the profiles and which candidate edges
belong to each opening; the reference format is in facade_correspondence. Plain
numeric coordinates remain valid for explicitly identified visual estimates when
no suitable measurement is available. Keep those estimates distinct from measured
references. If you revise your interpretation, submit a new comparison record.
Use compare_facade_spans to compare both axis directions, inspect the absolute
errors and any count mismatch, and recheck consequential conflicts against originals.
Report each correspondence with observed type and uncertainty. For elevation opening
bottom/top heights, report only what you can bind to a directly inspected dimension
chain or explicit inference; keep different chains and opening groups separate.
Your final answer must cite the saved comparison record and distinguish actual
measurements, visual estimates, assumptions and unexamined items. This is a local
observation task, not a whole-building BIM task. Do not create or request a BIM.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    run = args.out.resolve()
    run.mkdir(parents=True, exist_ok=False)
    (run / "images").mkdir()
    manifest = {"images": {}, "scope": PROMPT,
                "input_mode": "developer_selected_local_original_observation",
                "only_input": "Two original PNGs and a local task; no seed, historical observations, developer measurements or GT",
                "deadline_epoch": time.time() + args.timeout,
                "implementation_sha256": {}}
    for name in ("1f_view.png", "East_view.png"):
        source = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data" / name
        target = run / "images" / name
        shutil.copyfile(source, target)
        with Image.open(target) as pic:
            manifest["images"][name] = {"size": list(pic.size), "sha256": digest(target)}
    for name in ("scripts/tool_scripts/run_bim_agent.py",
                 "scripts/tool_scripts/bim_agent_guidance.py",
                 "src/agent/geometry/facade_span_comparison.py",
                 "src/agent/geometry/profile_observation_binding.py",
                 "src/agent/geometry/dimension_chain.py",
                 "src/agent/execution/subscription_json.py",
                 str(Path(__file__).relative_to(ROOT))):
        manifest["implementation_sha256"][name] = digest(ROOT / name)
    dump(run / "inputs.json", manifest)
    receipt = subscription(run, PROMPT, model="sonnet", name="agent", readonly=True,
                           timeout=args.timeout, effort="medium")
    dump(run / "summary.json", {"scope": manifest["input_mode"],
                                "elapsed_seconds": receipt["elapsed_seconds"],
                                "actual_model": receipt.get("actual_model"),
                                "returncode": receipt.get("returncode"),
                                "timed_out": receipt.get("timed_out", False),
                                "comparison_records": [str(p.relative_to(run)) for p in
                                                       sorted(run.glob("facade_comparisons/*.json"))],
                                "bim_created": False})
    print(json.dumps(json.loads((run / "summary.json").read_text())))


if __name__ == "__main__":
    main()
