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

PROMPT = """Read the vertical dimension chains for the exterior openings in the
supplied original East elevation. This is a narrow original-image transcription
and height task, not a facade horizontal matching task or a BIM task. You have
no previous observations or model. Identify the physical opening groups and the
vertical chains that actually refer to them; panels within a door are not separate
wall openings. For every inspected chain, give its original-image label boxes,
transcribed values and units, dimension-line x position, ordered extension-endpoint
y pixels, and which opening bbox/group the chain refers to. Use clean magnified
crops including the complete chain and the related opening; inspect the top and
bottom ends, not only the middle label. You may use pixel profiles or colour regions
to measure anchors and distinguish lines, but a colour component is not a semantic
opening. Keep the building base/roof, opening head/sill and any other reference
levels distinct. If the visible labels determine a sill and head height relative
to an observed base, compute them explicitly in metres from those labels; do not
replace an exact label by a coarser pixel estimate. Use map_dimension_chain for
arithmetic only after correctly transcribing the actual chain. Report each group,
its bottom/top, the source chain, uncertainties and any unexamined groups. Do not
invent labels or infer a shared sill for unrelated groups. Do not create a BIM.
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
                "input_mode": "developer_selected_vertical_chain_observation",
                "only_input": "One original PNG and a vertical-chain task; no seed, historical observations, developer measurements or GT",
                "deadline_epoch": time.time() + args.timeout,
                "implementation_sha256": {}}
    for name in ("East_view.png",):
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
                 "src/agent/geometry/pixel_region.py",
                 "src/agent/geometry/pixel_region_overview.py",
                 "src/agent/execution/subscription_json.py",
                 str(Path(__file__).relative_to(ROOT))):
        manifest["implementation_sha256"][name] = digest(ROOT / name)
    dump(run / "inputs.json", manifest)
    receipt = subscription(run, PROMPT, model="haiku", name="agent", readonly=True,
                           timeout=args.timeout)
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
