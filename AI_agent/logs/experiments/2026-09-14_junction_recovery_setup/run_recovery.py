"""One bounded source recovery from run18 and a complete fallible observation."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

TASK = """Continue restoration from the saved seed proposal. This increment concerns
physical partitions and spatial continuity in the middle part of the plan, with
the doors/windows whose hosts are affected by an actual partition correction.
Do not redo unrelated parts of the building or optimize first-draft speed.

The complete earlier local observation below is FALLIBLE, NOT APPROVED. Its
claims, IDs, references, door descriptions and assumptions may be wrong. It is
supplied intact, not filtered to correct conclusions. Compare it with original
drawings and the actual seed, decide what is supported, and apply useful local
corrections yourself. Do not merely restate the observation or add notes while
retaining a substantiated physical discrepancy. Independently verify wall end
junctions, the full extent of the spaces on both sides, and which oriented wall
a door swing belongs to. Clean magnified crops retain context around junctions.
Measured grey ink includes furniture, walls, crossings and omissions; it is not
a wall catalogue. Missing color support does not decide whether an opening exists.

Use the existing deterministic geometry, pixel/dimension mapping and inspection
tools. Inspect seed and read the relevant geometry/edit reference. If a change
adds/removes a physical space or exceeds a local edit's supported scope, use a
complete revised build_bim proposal (or build_plan_bim if suitable), preserving
the unaffected geometry and IDs. Do not invent an abstract divider to keep a
space rectangular. Do not delete, clip, resize or silently reclassify openings
just to make the geometry compile: inspect affected openings in the plan and
elevations, then represent supported changes explicitly and keep uncertainty.
The supplied building declaration retains its original meaning; thermal zoning
is not the source-room count. Reliable exterior shape, vertical properties and
unrelated source spaces/openings should remain stable. Old notes are hypotheses;
do not copy them as fresh evidence or infer structural load-bearing from ink alone.

Register an observed image calibration and inspect the NEW actual source plan,
its original-image overlay, and the affected source opening/connection inventory.
Revise conflicts using the original evidence and save an honest final selection
with finish_bim. Record the remaining unexamined scope and unsupported claims.

Development boundary: the developer chose this local aspect, failed seed and
previous observation. No GT, evaluation report, correct source geometry or
developer-approved subset of observations is supplied. This is assisted local
recovery, not an independent cold start or proof of whole-building fidelity.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup = Path(__file__).resolve().parent
    originals = ROOT / "case_tests/e2e_tests/sm24_anchor/case_data"
    seed = ROOT / "AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run18/candidate_01"
    observation = ROOT / "AI_agent/logs/experiments/2026-09-14_sm24_junction_feedback/observation.md"
    profile_root = ROOT / "AI_agent/logs/experiments/2026-09-14_sm24_east_profile_sonnet/detail_01/pixel_profiles"
    profiles = [profile_root / "profile_001.json", profile_root / "profile_002.json"]
    scope = TASK + "\nComplete earlier observation (unmodified):\n" + observation.read_text()
    for path in profiles:
        scope += "\nEarlier measured profile (unmodified; original-pixel references only):\n" + path.read_text()
    (setup / "scope.md").write_text(scope)
    out = ROOT / "AI_agent/logs/experiments/2026-09-14_bim_agent_sm24_run19"
    sources = [ROOT / "scripts/tool_scripts/run_bim_agent.py",
               ROOT / "scripts/tool_scripts/bim_agent_guidance.py",
               ROOT / "scripts/tool_scripts/bim_agent_inputs.py",
               *sorted((ROOT / "src/agent/geometry").glob("*.py")),
               ROOT / "src/agent/execution/source_proposal.py",
               ROOT / "src/agent/execution/subscription_json.py", Path(__file__).resolve()]
    frozen = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources}
    dump(setup / "frozen_inputs.json", {
        "scope_sha256": digest(setup / "scope.md"), "timeout_seconds": 900, "effort": "medium",
        "images": {p.name: digest(p) for p in sorted(originals.glob("*.png"))},
        "building_input_sha256": digest(originals / "testdata_prompt.json"),
        "seed_proposal": {"file": str(seed / "proposal.json"), "sha256": digest(seed / "proposal.json")},
        "prior_observation": {"file": str(observation), "sha256": digest(observation),
                              "included_verbatim": observation.read_text() in scope},
        "prior_profiles": {str(p): digest(p) for p in profiles},
        "frozen_code_sha256": {name: digest(ROOT / name) for name in frozen},
        "input_boundary": "Five originals, original declaration, run18 proposal, complete unapproved prior local observation and two raw measured profiles, plus developer-selected local task. No GT/evaluation, filtered correct claims or corrected geometry; assisted recovery.",
    })
    if args.dry_run:
        print(json.dumps({"out": str(out), "scope_sha256": digest(setup / "scope.md"),
                          "model_called": False}, indent=2))
        return
    try:
        run_experiment(SimpleNamespace(images=originals,
            building_input=originals / "testdata_prompt.json", out=out,
            scope=scope, timeout=900, effort="medium", resume_candidate=seed))
    finally:
        changed = []
        for name, data in frozen.items():
            if (ROOT / name).read_bytes() != data:
                changed.append(name)
            target = out / "implementation" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        dump(out / "frozen_code_verification.json", {
            "all_frozen_sources_unchanged": not changed, "changed_files": changed,
            "files": {name: digest(out / "implementation" / name) for name in frozen},
        })


if __name__ == "__main__":
    main()
