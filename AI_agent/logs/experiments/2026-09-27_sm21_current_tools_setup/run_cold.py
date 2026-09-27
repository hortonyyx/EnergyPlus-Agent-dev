"""Independent original-only sm21 run with current tools and bounded continuation."""
import argparse
import importlib
from pathlib import Path
import subprocess
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = importlib.import_module(
    'AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold').SCOPE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='2026-09-27_sm21_current_tools_claude_run69')
    args = parser.parse_args()
    assert Path(args.run).name == args.run
    run = HERE.parent / args.run
    frozen = HERE / f'{args.run}_frozen.json'
    assert not run.exists() and not frozen.exists(), 'Keep every prior run intact'
    images = ROOT / 'case_tests/e2e_tests/sm21_anchor/case_data'
    assert len(list(images.glob('*.png'))) == 6
    dump(frozen, dict(scope=SCOPE, mode='original_images_only_whole_building_current_tools',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        provider='claude', role='sonnet', effort='medium', timeout_seconds=3000,
        continuation_rounds=2, max_candidates=24, shared_total_deadline=True,
        withheld=['saved plans/BIM', 'prior claims/decisions', 'old calibration',
                  'GT', 'old evaluations', 'building declaration', 'correct counts/heights',
                  'developer local observations'],
        developer_participation='Same generic whole-building task as run57/58; current tool guidance and two optional continuation rounds. No local answers or live intervention.',
        development_agents='Astra only', runtime_delegation='prohibited',
        producer_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT,text=True).strip(),
        comparison_limit='Changed runtime/guidance and continuation policy; not a frozen repeat or causal ablation.'))
    run_experiment(SimpleNamespace(command='run', images=images, mesh=None,
        building_input=None, out=run, scope=SCOPE, timeout=3000,
        continuation_rounds=2, max_candidates=24, provider='claude', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
