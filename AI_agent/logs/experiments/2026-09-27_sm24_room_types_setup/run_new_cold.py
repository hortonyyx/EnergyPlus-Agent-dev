"""Original-only retest after semantic editing/evidence support; no recovery seed."""
from pathlib import Path
from types import SimpleNamespace
import importlib

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = importlib.import_module(
    'AI_agent.logs.experiments.2026-09-27_sm24_room_types_setup.run_cold'
).SCOPE
RUN = HERE.parent / '2026-09-27_sm24_room_types_cold_claude_run61'


def main():
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    dump(HERE / 'new_cold_frozen_method.json', dict(
        scope=SCOPE, mode='original_images_only_with_room_use_review_support',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        provider='claude', role='sonnet', effort='medium', timeout_seconds=3000,
        scope_changes_from_run59=[],
        implementation_changes=['Room evidence retained in source BIM', 'set_space_role use-only edit',
                                'Generic room function review guidance and HTML evidence'],
        withheld=['saved plans/BIM', 'GT', 'old observations/calibration', 'building declaration',
                  'developer room labels/references', 'prior results or correct counts'],
        developer_participation='Generic task/tool instruction only; no local hints or live intervention.',
        development_agents='Astra only', runtime_delegation='prohibited by experiment scope',
    ))
    run_experiment(SimpleNamespace(
        command='run', images=images, mesh=None, building_input=None, out=RUN,
        scope=SCOPE, timeout=3000, provider='claude', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None,
    ))


if __name__ == '__main__':
    main()
