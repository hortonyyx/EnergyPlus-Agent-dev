"""Original-only cold start with actual candidate use-review feedback."""
import importlib
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / '2026-09-27_sm24_room_types_feedback_claude_run62'
SCOPE = importlib.import_module(
    'AI_agent.logs.experiments.2026-09-27_sm24_room_types_setup.run_cold'
).SCOPE


def main():
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    dump(HERE / 'feedback_cold_frozen_method.json', dict(
        scope=SCOPE, mode='original_images_only_candidate_use_feedback',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        provider='claude', role='sonnet', effort='medium', timeout_seconds=3000,
        scope_changes_from_run59=[],
        change_from_run61='Candidate build/inspection/delivery report saved per-room function-basis coverage and unrecorded IDs; generic action hint, no role answers or blocking gate.',
        withheld=['saved plans/BIM', 'GT', 'old observations/calibration', 'building declaration',
                  'developer room interpretations', 'prior results or correct counts'],
        developer_participation='Generic task/tool feedback only; no local hints or live intervention.',
        development_agents='Astra only', runtime_delegation='prohibited by experiment scope',
    ))
    run_experiment(SimpleNamespace(
        command='run', images=images, mesh=None, building_input=None, out=RUN,
        scope=SCOPE, timeout=3000, provider='claude', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None,
    ))


if __name__ == '__main__':
    main()
