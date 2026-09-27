"""Original-only reconstruction using the newly integrated room catalog."""
import importlib
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / '2026-09-27_sm24_room_types_claude_run59'
SCOPE = importlib.import_module(
    'AI_agent.logs.experiments.2026-09-26_sm24_whole_building_setup.run_cold'
).SCOPE


def main():
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    dump(HERE / 'frozen_method.json', {
        'scope': SCOPE,
        'mode': 'original_images_only_whole_building_room_catalog_validation',
        'image_sha256': {p.name: digest(p) for p in sorted(images.glob('*.png'))},
        'provider': 'claude', 'role': 'sonnet', 'effort': 'medium', 'timeout_seconds': 3000,
        'baseline': 'sm24/run55-56: identical scope and five original PNGs; current implementation includes naming/catalog changes',
        'production_base_commit': '7dcb1d0b',
        'withheld': ['saved plans/BIM', 'calibration', 'GT', 'building declaration',
                     'previous observations', 'developer function interpretations', 'correct counts/heights'],
        'developer_participation': 'Generic task/tool instructions only; no local answers or live intervention.',
        'runtime_delegation': 'prohibited by inherited experiment scope',
        'development_agents': 'Astra only',
    })
    run_experiment(SimpleNamespace(
        command='run', images=images, mesh=None, building_input=None, out=RUN,
        scope=SCOPE, timeout=3000, provider='claude', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None,
    ))


if __name__ == '__main__':
    main()
