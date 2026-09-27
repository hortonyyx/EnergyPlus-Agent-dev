"""Frozen, explicitly scoped recovery of prior unverified image references."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / '2026-09-27_sm24_continuation_claude_run65'
SEED = PRIOR / 'candidate_01'
SCOPE = '''Continue the supplied saved BIM using its original drawings. This is a
bounded evidence-location and room-use review, not a cold reconstruction. Preserve
physical rooms, partitions, opening plan positions, hosts and connections; do not
rebuild the plan. Previous height declarations below are unverified model hypotheses,
not ground truth. Record each unchanged declaration against candidate seed first,
without adopting it, so the actual returned source crops can be examined. Check that
each cited region contains the numbers, dimension endpoints and object context used
by its interpretation. Inspect the original beyond the crop when needed. Choose
whether to retain, correct or retract each hypothesis. If correcting it, record a
new claim and retract the obsolete record; never overwrite the old one. Confirm
adopted heights against the saved candidate when they match, or locally revise
only where original evidence supports an actual change. Read the claims reference.
Do not treat numerical consistency or a tool's image return as semantic approval.

For room uses, prefer a plausible listed use over unknown, including a broad
inference from building context or furniture; mark inference and allow later user
adjustment. Avoid prolonged attempts to distinguish similar plausible uses. Review
existing unknown uses, retain reasonable assigned uses, and preserve physical
partitions. Update saved notes to reflect actual checks and remaining assumptions.
Deliver the viewable candidate and distinguish completed work from limitations.
No review_detail or delegation. No GT, evaluation, corrected boxes, developer
height answers or per-room interpretations are supplied. Prior declarations follow:
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='2026-09-27_sm24_claim_regions_claude_run66')
    args = parser.parse_args()
    assert Path(args.run).name == args.run
    declarations, hashes = [], {}
    for path in sorted((PRIOR / 'claims').glob('claim_*.json')):
        record = json.loads(path.read_text())
        declaration = record['claim']
        declaration['candidate'] = 'seed'
        declarations.append(declaration)
        hashes[path.name] = digest(path)
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    scope = SCOPE + json.dumps(declarations, ensure_ascii=False, indent=2)
    frozen = dict(scope=scope, mode='saved_proposal_and_unverified_claim_recovery',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        seed_proposal_sha256=digest(SEED / 'proposal.json'),
        prior_claim_file_sha256=hashes, prior_run=str(PRIOR.relative_to(ROOT)),
        prior_claims=declarations, provider='claude', role='sonnet', effort='medium',
        timeout_seconds=1800, continuation_rounds=2, shared_total_deadline=True,
        withheld=['GT', 'old evaluations', 'old claim decisions/confirmations',
                  'corrected regions', 'developer room/height interpretations'],
        developer_participation='Explicit bounded location-review task and prior model declarations; no local correction hints or live intervention.',
        development_agents='Astra only', runtime_delegation='prohibited')
    target = HERE / f'{args.run}_frozen.json'
    assert not target.exists()
    dump(target, frozen)
    run_experiment(SimpleNamespace(command='run', images=images, mesh=None,
        building_input=None, out=HERE.parent / args.run, scope=scope, timeout=1800,
        continuation_rounds=2, provider='claude', exploratory_opus=False,
        effort='medium', resume_candidate=SEED, resume_plan=None, plan_image=None))


if __name__ == '__main__':
    main()
