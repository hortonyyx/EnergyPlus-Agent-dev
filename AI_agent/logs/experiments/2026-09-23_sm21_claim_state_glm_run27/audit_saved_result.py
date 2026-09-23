"""Independent post-run audit, never passed to the generating model."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from src.agent.execution.bim_claim_state import project


def main():
    run = Path(__file__).resolve().parent
    load = lambda name: json.loads((run/name).read_text())
    receipt = load('agent_receipt.json')
    assert receipt['actual_model'] == receipt['requested_model'] == 'glm-5.3-flash'
    delivery = load('delivery.json')
    chosen = delivery['candidate']
    seed, source = load('seed/source_model.json'), load(f'{chosen}/source_model.json')
    differences = {}
    for field in ('spaces', 'boundaries', 'openings', 'connections'):
        identity = lambda r: r.get('id', r.get('opening_id', json.dumps(r, sort_keys=True)))
        before = {identity(r): r for r in seed[field]}
        after = {identity(r): r for r in source[field]}
        differences[field] = {'added': sorted(after.keys()-before.keys()),
            'removed': sorted(before.keys()-after.keys()),
            'changed': [identity for identity in sorted(before.keys() & after.keys()) if before[identity] != after[identity]]}
    state = project(Toolkit(run).claims(), chosen)
    old = load('seed/proposal.json')
    new = load(f'{chosen}/proposal.json')
    old_doors = {r['id']: r for r in old['geometry']['openings']}
    new_doors = {r['id']: r for r in new['geometry']['openings']}
    moved_doors = ['D_NA', 'D_NB', 'D_NC', 'D_SA', 'D_SB', 'D_SC']
    for identity in moved_doors:
        before, after = old_doors[identity], new_doors[identity]
        assert before['p1'][0] == after['p1'][0] and before['p2'][0] == after['p2'][0]
        assert before['z'] == after['z']
        assert before['space_id'] == after['space_id'] and before.get('other_space_id') == after.get('other_space_id')
    assert seed['connections'] == source['connections']
    audit = {'scope': 'saved-source changes and current evidence state; geometry fidelity evaluated separately',
        'chosen': chosen, 'actual_model': receipt['actual_model'], 'elapsed_seconds': receipt['elapsed_seconds'],
        'source_validation': source.get('validation'), 'differences': differences,
        'claim_states': [{'id': r['id'], 'state': r['state'], 'missing_bindings': r['missing_bindings']} for r in state['claims']],
        'postrun_state_matches_saved_delivery': json.loads(json.dumps(state)) == delivery['current_claim_state'],
        'superseded_notes': state['superseded_notes'],
        'changed_assumptions': {'before': old['assumptions'], 'after': new['assumptions']},
        'unresolved': new['unresolved'],
        'counts': {'spaces': len(source['spaces']), 'openings': len(source['openings']), 'connections': len(source['connections'])},
        'six_moved_doors_preserve_jamb_x_heights_and_connectivity': True,
        'independent_image_check': {
            'image': 'East_view.png', 'object': 'W2_E',
            'observed_chain_floor2_bottom_up_mm': [1000, 1800, 800], 'floor_origin_m': 3.0,
            'expected_z_from_original_m': [4.0, 5.8],
            'actual_z_m': next(w['z'] for w in new['geometry']['windows'] if w['id'] == 'W2_E'),
            'finding': 'The model final answer overstates all-facade height verification; F2 east window remains 0.2m low.',
            'evaluation_only_not_returned_to_model': True}}
    from src.agent.geometry.source_elevation_view import render_source_elevation
    picture, metadata = render_source_elevation(source, 'East')
    picture.save(run/'postrun_elevation_East.png')
    dump(run/'postrun_elevation_East.json', metadata)
    dump(run/'postrun_audit.json', audit)
    print(json.dumps({'chosen': chosen, 'counts': audit['counts'],
        'claim_states': [(r['id'], r['state']) for r in audit['claim_states']],
        'postrun_state_matches_saved_delivery': audit['postrun_state_matches_saved_delivery']}, indent=2))


if __name__ == '__main__':
    main()
