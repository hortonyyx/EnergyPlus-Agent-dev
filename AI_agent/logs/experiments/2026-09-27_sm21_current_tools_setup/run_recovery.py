"""Saved-proposal recovery after making the candidate export quota explicit."""
import argparse
import importlib
from pathlib import Path
import subprocess
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / '2026-09-27_sm21_current_tools_claude_run69'
SEED = PRIOR / 'candidate_06'
SCOPE = importlib.import_module(
    'AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold').SCOPE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='2026-09-27_sm21_candidate_budget_claude_run70')
    args = parser.parse_args()
    assert Path(args.run).name == args.run
    run = HERE.parent / args.run
    target = HERE / f'{args.run}_frozen.json'
    assert not target.exists() and not run.exists()
    images = ROOT / 'case_tests/e2e_tests/sm21_anchor/case_data'
    dump(target, dict(scope=SCOPE, mode='saved_candidate_recovery_with_explicit_export_budget',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        seed_proposal_sha256=digest(SEED / 'proposal.json'),
        prior_run=str(PRIOR.relative_to(ROOT)), seed_candidate=SEED.name,
        provider='claude', role='sonnet', effort='medium',
        max_candidates=24, timeout_seconds=1800, continuation_rounds=2,
        shared_total_deadline=True, candidate_history_imported=False,
        withheld=['GT', 'old evaluations', 'prior claims/decisions/confirmations',
                  'old calibration files', 'developer local observations', 'correct counts/heights'],
        developer_participation='Same generic whole-building task. Saved proposal and its original model-authored notes remain unverified. No local answers or live intervention.',
        development_agents='Astra only', runtime_delegation='prohibited',
        producer_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip(),
        comparison_limit='Recovery, not cold start or a causal ablation. New run has a fresh explicit export quota; old candidates are not imported.'))
    run_experiment(SimpleNamespace(command='run', images=images, mesh=None,
        building_input=None, out=run, scope=SCOPE, timeout=1800,
        max_candidates=24, continuation_rounds=2, provider='claude',
        exploratory_opus=False, effort='medium', resume_candidate=SEED,
        resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
