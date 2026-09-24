"""One explicitly labelled saved-draft recovery; no evaluation answers admitted."""
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / '2026-09-24_sm25_continuous_space_glm_run44'
INPUTS = HERE.parent / '2026-09-24_sm25_cold_support_setup/inputs'
RUN = HERE.parent / '2026-09-24_sm25_partition_feedback_glm_run45'
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
remaining material discrepancies honestly. No other floors or elevations are requested.
Developer review feedback from the original and the saved source: the vertical corridor
and the lower horizontal wing corridor are ONE continuous physical space, but the current
source keeps them as two spaces joined by PASS_corr_s. This is a material partition error,
not a missing-connectivity problem. Recheck that location in the original, then correct the
actual separating partition geometry and the now-unnecessary passage using local edits.
Preserve the real walls on either side of the continuous route and all unrelated rooms and
existing doors/windows. Determine wall extents from the original; no corrected coordinates
are supplied. Inspect the final source to verify that the two corridor portions now belong
to the same source space. Keep successful prior corrections and explicit assumptions.'''


def main():
    assert not RUN.exists(), 'Never overwrite an existing experiment'
    plan = PREVIOUS / 'plan_drafts/draft_003/plan.json'
    implementation = ['scripts/tool_scripts/run_bim_agent.py',
        'scripts/tool_scripts/bim_agent_guidance.py', 'scripts/tool_scripts/bim_agent_inputs.py',
        'src/agent/geometry/plan_revision.py', 'src/agent/geometry/plan_partition.py']
    dump(HERE / 'frozen_method.json', dict(scope=SCOPE, mode='saved_draft_recovery_not_cold_start',
        parent_plan=str(plan.relative_to(ROOT)), parent_plan_sha256=digest(plan),
        image_sha256=digest(INPUTS / '1f_view.png'),
        implementation_sha256={p:digest(ROOT / p) for p in implementation},
        developer_participation='Selected run44 draft_003 (same geometry as final candidate_03; notes-only cleanup not imported). Explicit original-image feedback identifies the corridor split and PASS_corr_s; model must derive the geometric edits. This is developer-targeted recovery. No correct coordinates, counts, GT, annotated reference or developer-repaired source supplied.',
        evaluation='Reuse existing frozen original reference and GT F1 after generation.'))
    run_experiment(SimpleNamespace(command='run', images=INPUTS, mesh=None,
        building_input=None, out=RUN, scope=SCOPE, timeout=1800, provider='glm',
        exploratory_opus=False, effort='medium', resume_candidate=None,
        resume_plan=plan, plan_image='1f_view.png'))


if __name__ == '__main__':
    main()
