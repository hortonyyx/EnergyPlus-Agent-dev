"""Reproduce public object histories and bounded development-side findings.

Semantic interpretations below were checked against the original PNGs. This is
an offline review of this saved run, not a production judge or model invocation.
"""
from collections import Counter
import importlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-28_sm21_behavior_repeat_run83'
load = lambda path: json.loads(path.read_text())


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def physical(source):
    fields = dict(floors=['id', 'footprint', 'height', 'z_floor'],
        spaces=['id', 'floor_id', 'polygon', 'height', 'z_floor'],
        boundaries=['id', 'space_id', 'adjacent_space_ids', 'counterpart_ids', 'kind', 'geometry_type', 'vertices'],
        openings=['id', 'kind', 'vertices', 'host_boundary_id', 'space_ids', 'exterior', 'connectivity'],
        connections=['kind', 'opening_id', 'space_ids', 'exterior', 'state'])
    return {kind: [{key: row[key] for key in keys} for row in source[kind]] for kind, keys in fields.items()}


def main():
    audit = importlib.import_module('AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.audit')
    runner = importlib.import_module('scripts.tool_scripts.run_bim_agent')
    report = load(RUN / 'postrun_audit.json')
    receipt = load(RUN / 'agent_receipt.json')
    assert receipt['returncode'] == 0 and not receipt['result']['is_error']
    assert report['counts']['spaces'] == 13 and report['counts']['connections'] == 13
    assert any(r['code'] == 'source_spaces_merged' for r in report['space_identity_findings'])
    traces = audit.analyze(83, ['F1:W_N1', 'F1:W_S1', 'F2:W_east'])
    dump(RUN / 'object_traces.json', traces)
    before, after = [load(RUN / name / 'source_model.json') for name in ('candidate_03', 'candidate_04')]
    assert physical(before) == physical(after), 'Role/note edits must not change physical geometry'
    drafts = [load(RUN / f'plan_drafts/draft_{i:03d}/plan.json') for i in (2, 3, 4)]
    assert all(len(p['partitions']) == 5 and len(p['space_seeds']) == 6 for p in drafts)
    windows = []
    for identity in ('W_S1', 'W_S3'):
        original, revised = [next(o for o in p['openings'] if o['id'] == identity) for p in (drafts[1], drafts[2])]
        windows.append(dict(id=identity, before=[original['p1'], original['p2']], after=[revised['p1'], revised['p2']],
                            declared_partitions_unchanged=drafts[1]['partitions'] == drafts[2]['partitions']))
        assert revised['p2'][0] - revised['p1'][0] < original['p2'][0] - original['p1'][0]
    original = report['original_openings']
    multiplicity = Counter(identity for f in original['floors']
        for identities in f['space_identity_by_interior_point'].values() for identity in identities)
    ambiguous = {identity for identity, count in multiplicity.items() if count > 1}
    independent = [r for r in original['comparisons'] if not (set(r['expected_hosts']) & ambiguous)]
    public = load(RUN / 'behavior_audit.json')
    findings = [
        dict(topic='F2 north two rooms and two doors', first_action=67, repeated_at_action=76,
             result='merged_two_source_spaces_and_replaced_two_doors_with_one_wide_door',
             evidence=['plan_drafts/draft_002/plan.json', 'images/2f_view.png', 'candidate_04/source_model.json'],
             observation='The first F2 declaration calls the north half one hall, rejects an unfilled line near x=718, and declares one broad door. The actual central partition is around original x=1120; two distinct door arcs flank it. The cited x=718 is not that partition. No north-partition-specific profile/crop was requested; the two broader original views still exposed it.',
             feedback='Action76 checks an asserted same_space observation against the already merged source. Agreement verifies the assertion/source consistency, not the original interpretation.'),
        dict(topic='F2 south windows and incorrectly placed partitions', actions=[69, 70],
             result='host_error_cleared_by_shortening_two_windows_without_repairing_partition_positions',
             evidence=['plan_revisions/revision_002.json', 'plan_drafts/draft_003/opening_host_failure.png', 'images/2f_view.png'],
             changes=windows,
             observation='The error feedback carried the clean original plus declared geometry and explicitly warned against shortening only to clear a host error. The next action shortened W_S1/W_S3; no intervening original view or profile. Source generation succeeded, but original/GT width-position mismatches remain.'),
        dict(topic='F1 south small window', actions=[53, 78, 82],
             result='wrong_height_family_retained_and_confirmed',
             evidence=['claims/claim_0001.json', 'images/South_view.png', 'object_traces.json'],
             actual_z_m=[1.0, 2.6], original_z_m=[1.5, 2.1],
             observation='Small window receives the regular family in the first floor draft; all seven F1 windows later share the North-view claim. Arithmetic and confirmation are internally consistent, but the South-view left chain describes a distinct small-window family.'),
        dict(topic='Counterexamples and successful actions', actions=[69, 82, 85],
             result='valid_repairs_and_correct_first_drafts_retained_separately',
             observation='The five F2 doors were successfully moved from floor-local [0,2.1] to absolute [3,5.1]. F1 regular window and F2 east window were already correct in the selected dimensions in their first drafts; confirming them did not create that correctness. F2 floor height3.6 and total6.6 were saved correctly. Last role/note edit fills13 use records and preserves all physical geometry.'),
    ]
    facts = dict(completed=True, quality='failed_source_partition_and_opening_fidelity',
        candidate=report['candidate'], source_model_sha256=report['source_model_sha256'],
        source_geometry_replay=True, physical_geometry_preserved_by_final_role_edit=True,
        interpretation='Public behavior and saved results only; no hidden reasoning, GT feedback, tolerance change or new model call.',
        original_hosts_raw=original['hosts'], original_connections_raw=original['door_connections'],
        host_identity_caveat='Original point-based correspondence maps both north reference rooms to hall; raw host/connection counts do not establish correct source identity.',
        ambiguous_space_ids=sorted(ambiguous),
        hosts_with_independent_room_identity=sum(r['host_match'] for r in independent),
        connections_with_independent_room_identity=sum(r['connection_match'] is True for r in independent),
        original_positions=original['positions'], original_reference_openings=original['reference_count'],
        findings=findings, limitations=[
            'One completed run after a prior interrupted run; not two successful repetitions or causal isolation.',
            'Delivered image bytes, 15 window confirmations and 13 room-use records do not certify image understanding.',
            'No new production behavior change in this run; role/API work stayed outside its40 frozen production files.',
            'Internal door height assumptions remain allowed; opening existence, host and connection are still independently required.',
        ], evidence_sha256={name:runner.digest(RUN / name) for name in (
            'agent_receipt.json', 'agent_stream.jsonl.gz', 'postrun_audit.json', 'candidate_04/source_model.json',
            'plan_drafts/draft_002/plan.json', 'plan_revisions/revision_002.json', 'claims/claim_0001.json',
            'images/2f_view.png', 'images/South_view.png')})
    assert facts['hosts_with_independent_room_identity'] == 25
    assert facts['connections_with_independent_room_identity'] == 12
    dump(RUN / 'manual_review.json', facts)
    public['semantic_review'] = 'completed; see manual_review.json; original partition/opening fidelity failed'
    dump(RUN / 'behavior_audit.json', public)
    print(json.dumps({k:facts[k] for k in ('quality', 'ambiguous_space_ids', 'hosts_with_independent_room_identity', 'connections_with_independent_room_identity')}))


if __name__ == '__main__':
    main()
