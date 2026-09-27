"""Frozen saved-proposal recovery with bounded autonomous main-agent follow-up."""
import argparse
from pathlib import Path
from types import SimpleNamespace

from scripts.tool_scripts.run_bim_agent import digest, dump, run_experiment

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SEED = HERE.parent / '2026-09-27_sm24_room_types_feedback_claude_run62/candidate_01'
SCOPE = '''Continue reconstructing the supplied target building from its saved
generated proposal and original drawings. Inspect actual saved feedback, decide
what useful in-scope work remains and execute it. Preserve reliable physical
rooms, walls, openings, hosts and connections; choose local revisions when needed.
Do not rebuild the whole plan merely to add evidence or room functions. Check
physical partition/connection fidelity, room uses and the exterior opening heights
against relevant originals. Uses inferred from furniture must be marked inferred;
ambiguous uses and heights without evidence may remain explicitly unknown/assumed.
Use the listed room catalog, located evidence, and confirmation or edits as
appropriate. Reconcile obsolete source notes with actual completed work and
retain real limitations. Choose the order and concrete follow-ups yourself;
there are no supplied target counts, local answers, GT or evaluation. A saved
proposal is a previous model interpretation, not original evidence. Deliver a
viewable candidate and accurately distinguish executed checks from pending work.
Work directly through deterministic/visual tools; no review_detail or delegation.
This is saved-proposal recovery, not an independent cold start.'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='2026-09-27_sm24_continuation_claude_run63')
    parser.add_argument('--explicit-height-records', action='store_true',
                        help='Restore the original whole-building task requirement, not local height answers')
    args = parser.parse_args()
    assert Path(args.run).name == args.run
    images = ROOT / 'case_tests/e2e_tests/sm24_anchor/case_data'
    scope = SCOPE
    if args.explicit_height_records:
        scope += '''
Before delivery, use check_openings(heights_only=true) and current source elevations
to inspect the exterior height families separately on each floor. Record located
image claims and confirm/apply their heights on the actual whole-building candidate;
report any remaining unlinked heights without pretending that returned pictures
alone constitute review. Read the claims reference when using those operations.
Preserve physical plan partitions and opening connections while resolving heights.
No error identities/counts, target heights or previous run results are supplied.'''
    frozen = dict(scope=scope, mode='saved_proposal_autonomous_continuation',
        image_sha256={p.name: digest(p) for p in sorted(images.glob('*.png'))},
        seed_proposal_sha256=digest(SEED / 'proposal.json'),
        provider='claude', role='sonnet', effort='medium', timeout_seconds=1800,
        continuation_rounds=2, shared_total_deadline=True,
        withheld=['GT', 'old evaluations', 'old claim/review files', 'developer room interpretations',
                  'local answer/count/height hints'],
        developer_participation='Generic recovery task and bounded continuation machinery; no per-room directions or live intervention.',
        development_agents='Astra only', runtime_delegation='prohibited',
        explicit_height_records=args.explicit_height_records,
        scope_note='With this flag, restore the verbatim generic height-record requirement from run62; no per-opening directions or values.')
    target = HERE / f'{args.run}_frozen.json'
    assert not target.exists()
    dump(target, frozen)
    run_experiment(SimpleNamespace(
        command='run', images=images, mesh=None, building_input=None, out=HERE.parent / args.run,
        scope=scope, timeout=1800, continuation_rounds=2, provider='claude',
        exploratory_opus=False, effort='medium', resume_candidate=SEED,
        resume_plan=None, plan_image=None,
    ))


if __name__ == '__main__':
    main()
