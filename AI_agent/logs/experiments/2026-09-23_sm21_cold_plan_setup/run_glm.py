"""Bounded cold start: one untouched original plan, no seed or reference answers."""
from pathlib import Path
import shutil
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    inputs = HERE / 'inputs'
    inputs.mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'case_tests/e2e_tests/sm21_anchor/case_data/1f_view.png',
                 inputs / '1f_view.png')
    run_experiment(SimpleNamespace(
        command='run', images=inputs, mesh=None, building_input=None,
        out=ROOT / 'AI_agent/logs/experiments/2026-09-23_sm21_cold_plan_glm_run31',
        scope=(
            'Cold-start reconstruction of the single floor in the supplied original plan. '
            'The bounded objective is its complete physical partition layout, plan openings, '
            'and actual door connections. No other floor or elevation is supplied. '
            'Choose explicit assumptions for unobserved vertical heights and state this limitation. '
            'Read the reconstruction and plan_partition references. Establish your own coordinate '
            'frame from original dimension annotations and their image endpoints before building; '
            'retain the calibration evidence and distinguish dimension baselines from wall faces. '
            'Use original-image crops, profiles or region tools to resolve consequential ambiguities. '
            'Declare observed pixel wall paths and apertures for build_plan_bim so deterministic '
            'code constructs rooms and hosts; do not manually enumerate a whole BIM vertex list. '
            'Identify complete physical spaces rather than treating furniture, door swings or text '
            'as walls. Keep shared open circulation intact. Choose observations and revisions '
            'yourself, use failures to re-examine the original, and preserve unresolved findings. '
            'After construction inspect the actual source plan and its original-image overlay, '
            'check both sides of partitions and the original opening inventory, and correct '
            'substantive discrepancies. Use evidence-bound local edits when suitable, keeping '
            'assumptions separate from observations. Deliver the best inspectable candidate '
            'and a truthful account of checked and unverified content. Geometry validity and '
            'agreement with your own annotations do not establish drawing fidelity.'),
        timeout=1800, provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
