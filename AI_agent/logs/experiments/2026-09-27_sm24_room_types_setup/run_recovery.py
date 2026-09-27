"""Bounded use-only recovery; no developer room labels or evaluation enters it."""
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SEED = HERE.parent / '2026-09-27_sm24_room_types_claude_run59/candidate_01'
RUN = HERE.parent / '2026-09-27_sm24_room_types_recovery_claude_run60'
SCOPE = '''Review room functions in the supplied saved building proposal against
the supplied original drawings. This is a bounded semantic recovery, not a fresh
geometry reconstruction. Preserve every room polygon, level, boundary, window,
door, host and connection. Read room_types and edits, inspect the actual current
spaces and the original room interiors, then use revise_bim set_space_role to
record each room's appropriate listed use or unknown, with original-image location,
observed/inferred/unknown basis and any assumptions. Furniture supports inference,
not observed text labels. Do not split a continuous physical space to separate uses.
Do not force a known use where the evidence is insufficient. Reconcile obsolete
global role notes without dropping unrelated height or geometry limitations.
Do not rebuild the plan or retype the full proposal to classify rooms. Inspect
the final source roles/evidence and deliver the best saved candidate with truthful
limits. Work directly with the tools; no review_detail or other delegation.
No developer room labels, target counts, correct answer, GT or evaluation is supplied.'''


def main():
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    dump(HERE / 'recovery_frozen_method.json', dict(
        scope=SCOPE, mode='saved_proposal_room_function_recovery',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        seed_proposal_sha256=digest(SEED / 'proposal.json'),
        provider='claude', role='sonnet', effort='medium', timeout_seconds=1800,
        developer_participation='Explicit use-review task and new operation; no per-room hints or live intervention.',
        withheld=['GT', 'previous evaluation', 'developer function interpretations'],
        development_agents='Astra only', runtime_delegation='prohibited',
    ))
    run_experiment(SimpleNamespace(
        command='run', images=images, mesh=None, building_input=None, out=RUN,
        scope=SCOPE, timeout=1800, provider='claude', exploratory_opus=False, effort='medium',
        resume_candidate=SEED, resume_plan=None, plan_image=None,
    ))


if __name__ == '__main__':
    main()
