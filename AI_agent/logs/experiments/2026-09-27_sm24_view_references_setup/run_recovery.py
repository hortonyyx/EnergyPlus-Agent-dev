"""Recover run67 using view references; previous model claims remain hypotheses."""
import argparse
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRIOR = HERE.parent / '2026-09-27_sm24_claim_regions_claude_run67'
SEED = PRIOR / 'candidate_02'
# Keep the prior generic task wording; tool guidance teaches the new operation.
SCOPE = importlib.import_module('AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.run_recovery').SCOPE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='2026-09-27_sm24_view_references_claude_run68')
    args = parser.parse_args()
    assert Path(args.run).name == args.run
    declarations, hashes = [], {}
    for path in sorted((PRIOR / 'claims').glob('claim_*.json')):
        declaration = json.loads(path.read_text())['claim']
        declaration['candidate'] = 'seed'
        declarations.append(declaration)
        hashes[path.name] = digest(path)
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    scope = SCOPE + json.dumps(declarations, ensure_ascii=False, indent=2)
    frozen = dict(scope=scope, mode='saved_proposal_and_unverified_claim_recovery_with_view_refs',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        seed_proposal_sha256=digest(SEED / 'proposal.json'),
        prior_claim_file_sha256=hashes, prior_run=str(PRIOR.relative_to(ROOT)),
        prior_claims=declarations, provider='claude', role='sonnet', effort='medium',
        timeout_seconds=1800, continuation_rounds=2, shared_total_deadline=True,
        withheld=['GT', 'old evaluations', 'old decisions/confirmations',
                  'corrected boxes', 'developer room/height interpretations'],
        developer_participation='Same generic bounded review instructions as run67; changed saved seed and new view-reference/replacement tools. No directed crop choices or live intervention.',
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
