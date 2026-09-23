"""Original plan + failed declaration; no developer-selected discrepancy locations."""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent/'2026-09-23_sm24_wall_context_recovery_glm_run35'
RUN = HERE.parent/'2026-09-23_sm24_self_review_glm_run36'
SCOPE = '''Review and recover the supplied unverified pixel plan against the
original drawing for this single floor. Choose the consequential discrepancies
and observation targets yourself across the complete physical partition layout,
plan apertures and actual door connections. No discrepancy locations, expected
room counts or correct geometry are provided. Treat the old declaration's
interpretations as unverified. Follow full wall paths through their ends and
junctions, trace complete spaces on both sides, and check aperture identity and
hosts against the original. Preserve real continuous spaces and all reliable
objects. Use original-image crops and suitable measurements to resolve your
chosen uncertainties, and let deterministic code perform geometry arithmetic
and room/host construction. A valid compilation or agreement with your own
annotations is not proof of drawing fidelity. Keep the inherited declared
coordinate frame, outer footprint and unobserved heights for this bounded
plan-layout review; these are not certified by being retained. Heights remain
explicit assumptions. Update your pixel declaration or use evidence-bound local
edits as appropriate. Inspect the actual source plan and original-image overlay
after revision. Deliver the best viewable candidate and a truthful account of
what you checked, changed, preserved and left unresolved. This is saved-plan
recovery, not a cold start. No successful old candidate, prior local review,
reference answer or evaluation/GT is supplied.'''


def main():
    old = json.loads((PREVIOUS/'inputs.json').read_text())
    checks = {name: digest(ROOT/name) == value for name, value in old['implementation_sha256'].items()}
    assert all(checks.values()), 'This experiment freezes the run35 production method'
    plan = HERE.parent/'2026-09-23_sm24_cold_plan_glm_run32/plan_drafts/draft_004/plan.json'
    image = HERE.parent/'2026-09-23_sm24_cold_plan_setup/inputs/1f_view.png'
    assert digest(plan) == old['plan_recovery']['raw_sha256']
    assert digest(image) == old['images']['1f_view.png']['sha256']
    dump(HERE/'frozen_method.json', dict(production_hashes_match_run35=checks,
        plan_sha256=digest(plan), image_sha256=digest(image), provider='glm',
        scope=SCOPE, timeout_seconds=1800,
        differences=['No developer-selected discrepancy locations; whole-floor review targets chosen by model.',
                     'Budget raised from 1500 to 1800 seconds for broader review; not a one-variable ablation.'],
        no_previous_success_or_local_review_supplied=True))
    run_experiment(SimpleNamespace(command='run', images=image.parent,
        mesh=None, building_input=None, out=RUN, scope=SCOPE, timeout=1800,
        provider='glm', exploratory_opus=False, effort='medium',
        resume_candidate=None, resume_plan=plan, plan_image='1f_view.png'))


if __name__ == '__main__':
    main()
