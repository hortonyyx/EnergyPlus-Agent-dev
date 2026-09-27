"""Check actual saved note updates and preservation of the repeated BIM."""
from collections import Counter
import json

from .run_repeat import HERE, RUN
from scripts.tool_scripts.run_bim_agent import dump


def main():
    load = lambda p: json.loads(p.read_text())
    delivery = load(RUN / 'delivery.json')
    assert delivery['candidate'] == 'candidate_04'
    before = load(RUN / 'candidate_03/source_model.json')
    source = load(RUN / delivery['candidate'] / 'source_model.json')
    fields = ('floors', 'spaces', 'boundaries', 'openings', 'connections')
    assert all(before[k] == source[k] for k in fields)
    proposal = load(RUN / delivery['candidate'] / 'proposal.json')
    previous = load(RUN / 'candidate_03/proposal.json')
    assert previous['assumptions'] != proposal['assumptions']
    claims = delivery['current_claim_state']['claims']
    coverage = delivery['height_coverage']['summary']
    assert coverage['image_linked_count'] == 15
    assert Counter(c['state'] for c in claims) == {'confirmed_unchanged': 4, 'deferred': 2}
    partition = load(RUN / 'evaluation/gt/candidate_04_partition.json')['comparison']
    dump(HERE / 'verification.json', dict(candidate=delivery['candidate'],
        physical_records_preserved=list(fields), source_assumptions_actually_updated=True,
        remaining_exact_duplicate_notes={field: {k: v for k, v in Counter(proposal[field]).items() if v > 1}
                                        for field in ('assumptions', 'unresolved')},
        confirmed_height_claims=4, deferred_exterior_door_claims=2,
        image_linked_windows=15, internal_doors_assumed=12,
        max_boundary_hausdorff_m=max(r['boundary_hausdorff_m'] for r in partition['matches']),
        min_iou=min(r['iou'] for r in partition['matches']),
        audits_used_model_calls=0,
        limits=['Unchanged geometry and confirmed claims do not independently prove image interpretation.',
                'Compiler-default thickness language is unsupported by measured component attributes.']))


if __name__ == '__main__':
    main()
