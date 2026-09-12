"""Resume saved sm24 proposal with originals; never read evaluation-side evidence."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

SCOPE = (
    "Resume the saved reconstruction using the supplied original drawings. Focus on "
    "physical room partitions and continuous spaces. Inspect the actual saved source "
    "plan early, relate it to the original plan using drawing-supported coordinates, "
    "and revise substantive discrepancies you can establish from those inputs. "
    "Do not split continuous spaces for rectangular convenience. Use deterministic "
    "measurement and transformation tools where helpful, retain existing exterior "
    "apertures, and check door hosts and connections affected by any room changes. "
    "A saved proposal and its notes are hypotheses, not evidence of correctness. "
    "Persist useful revisions promptly, inspect the resulting source against the "
    "original, record remaining assumptions and uncertainty, and select the saved "
    "candidate with finish_bim within budget. If you choose a local review_detail "
    "task, ask for visible evidence without prefilled dimensions, counts or expected "
    "answers, and resolve any disagreement against the original before relying on it."
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm24_run02")
    parser.add_argument("--dry-run", action="store_true", help="Print inputs without calling a model or creating a run")
    args = parser.parse_args()
    config = SimpleNamespace(
        images=ROOT / "case_tests/e2e_tests/sm24_anchor/case_data",
        out=args.out.resolve(),
        resume_candidate=ROOT / "AI_agent/logs/experiments/2026-09-12_bim_agent_sm24_run01/candidate_01",
        timeout=600,
        scope=SCOPE,
    )
    if args.dry_run:
        print(json.dumps(vars(config), default=str, ensure_ascii=False, indent=2))
    else:
        if config.out.exists():
            raise SystemExit("Choose a fresh --out directory; existing experiments are preserved.")
        from scripts.tool_scripts.run_bim_agent import run_experiment
        run_experiment(config)
