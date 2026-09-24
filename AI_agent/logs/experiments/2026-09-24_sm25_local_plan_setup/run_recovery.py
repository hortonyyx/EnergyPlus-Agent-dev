"""One explicitly labelled saved-draft recovery; no evaluation answers admitted."""
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / '2026-09-24_sm25_cold_support_glm_run42'
INPUTS = HERE.parent / '2026-09-24_sm25_cold_support_setup/inputs'
RUN = HERE.parent / '2026-09-24_sm25_local_plan_glm_run43'
SCOPE = '''Reconstruct only the supplied original floor plan as a lightweight source BIM.
An unverified saved pixel declaration from an earlier attempt is supplied for recovery,
not as an answer. Independently inspect the original and saved declaration for consequential
partition, connectivity and aperture coverage errors. Use inspect_plan_draft and
revise_plan_bim for local changes so unrelated declarations are preserved automatically;
get_bim_reference('plan_partition') documents the operations. Resolve errors from the
original, including full paths and spatial context, without deleting other real walls.
Independently check opening coverage against the original, and inspect the final actual
source plan and original overlay. Preserve reliable existing evidence and record uncertain
heights/reference planes as assumptions. Use the available quality budget and report
remaining material discrepancies honestly. No other floors or elevations are requested.'''


def main():
    assert not RUN.exists(), 'Never overwrite an existing experiment'
    plan = PREVIOUS / 'plan_drafts/draft_004/plan.json'
    implementation = ['scripts/tool_scripts/run_bim_agent.py',
        'scripts/tool_scripts/bim_agent_guidance.py', 'scripts/tool_scripts/bim_agent_inputs.py',
        'src/agent/geometry/plan_revision.py', 'src/agent/geometry/plan_partition.py']
    dump(HERE / 'frozen_method.json', dict(scope=SCOPE, mode='saved_draft_recovery_not_cold_start',
        parent_plan=str(plan.relative_to(ROOT)), parent_plan_sha256=digest(plan),
        image_sha256=digest(INPUTS / '1f_view.png'),
        implementation_sha256={p:digest(ROOT / p) for p in implementation},
        developer_participation='Selected run42 draft_004; general preservation/review scope. No correct coordinates, counts, GT, annotated reference or developer-repaired source supplied.',
        evaluation='Reuse existing frozen original reference and GT F1 after generation.'))
    run_experiment(SimpleNamespace(command='run', images=INPUTS, mesh=None,
        building_input=None, out=RUN, scope=SCOPE, timeout=1800, provider='glm',
        exploratory_opus=False, effort='medium', resume_candidate=None,
        resume_plan=plan, plan_image='1f_view.png'))


if __name__ == '__main__':
    main()
