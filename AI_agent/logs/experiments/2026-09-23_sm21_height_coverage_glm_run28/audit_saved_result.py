"""Post-generation source/drawing audit. Never supplied to the working model."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if not (ROOT/'scripts/tool_scripts').is_dir():
    ROOT = Path('/workspaces/EnergyPlus-Agent-dev')
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, dump, digest
from src.agent.execution.bim_claims import geometry_state
from src.agent.execution.bim_claim_state import project
from src.agent.geometry.source_elevation_view import render_source_elevation


def main():
    run = ROOT/'AI_agent/logs/experiments/2026-09-23_sm21_height_coverage_glm_run28'
    load = lambda name: json.loads((run/name).read_text())
    receipt, delivery, manifest = load('agent_receipt.json'), load('delivery.json'), load('inputs.json')
    chosen = delivery['candidate']
    before, after = load('seed/proposal.json'), load(f'{chosen}/proposal.json')
    old, new = load('seed/source_model.json'), load(f'{chosen}/source_model.json')
    assert receipt['actual_model'] == receipt['requested_model'] == 'glm-5.3-flash'
    geometry_before, geometry_after = geometry_state(before), geometry_state(after)
    changes = []
    for kind in ('windows', 'openings'):
        a = {r['id']: r for r in geometry_before.get(kind, [])}
        b = {r['id']: r for r in geometry_after.get(kind, [])}
        assert a.keys() == b.keys(), 'scope added/removed an opening'
        for identity in a:
            if a[identity].get('z') != b[identity].get('z'):
                changes.append({'id':identity, 'before_z':a[identity].get('z'), 'after_z':b[identity].get('z')})
        for row in geometry_before.get(kind, []) + geometry_after.get(kind, []):
            row.pop('z', None)
    assert geometry_before == geometry_after, 'a non-height geometry field changed'
    assert old['spaces'] == new['spaces'] and old['boundaries'] == new['boundaries']
    assert old['connections'] == new['connections']
    # Developer read of the four ORIGINAL dimensioned elevations, isolated from generation.
    checks = []
    for row in after['geometry']['windows']:
        if row['floor'] == 'F2':
            expected, chain, origin = [4.0, 5.8], [1000,1800,800], 3.0
        elif row['facade'] == 'East':
            expected, chain, origin = [1.0,2.8], [1000,1800,200], 0.0
        elif row['id'] == 'W_S1':
            expected, chain, origin = [1.5,2.1], [1500,600,900], 0.0
        else:
            expected, chain, origin = [1.0,2.6], [1000,1600,400], 0.0
        checks.append({'id':row['id'], 'image':row['facade']+'_view.png', 'floor':row['floor'],
            'chain_bottom_up_mm':chain, 'floor_origin_m':origin,
            'expected_z_m':expected, 'actual_z_m':row['z'],
            'matches_dimension_chain': all(abs(a-b)<1e-8 for a,b in zip(expected,row['z']))})
    state = project(Toolkit(run).claims(), chosen)
    hash_checks = {name: digest(ROOT/name) == value for name,value in manifest['implementation_sha256'].items()}
    assert all(hash_checks.values()), 'runtime implementation changed'
    report = {'selected':chosen, 'actual_model':receipt['actual_model'],
        'elapsed_seconds':receipt['elapsed_seconds'], 'changes':changes,
        'counts':{key:len(new[key]) for key in ('spaces','boundaries','openings','connections')},
        'plan_horizontal_openings_and_connections_preserved':True,
        'window_height_checks':checks, 'matching_window_heights':sum(r['matches_dimension_chain'] for r in checks),
        'external_door_note':'Door tops lack direct numeric labels here; pixel-based visual estimates are recorded separately, not asserted exact.',
        'claims':[{'id':r['id'],'state':r['state'],'missing_bindings':r['missing_bindings']} for r in state['claims']],
        'confirmation_records':len(list((run/'claims').glob('confirmation_*.json'))),
        'height_coverage_summary':delivery['height_coverage']['summary'],
        'implementation_hashes_match':True,
        'state_matches_saved_delivery':json.loads(json.dumps(state))==delivery['current_claim_state'],
        'independent_evaluation_only_not_returned_to_model':True,
        'not_evaluated':['opening plan matching','all partitions drawing fidelity','internal door heights','human approval','EP']}
    for facade in ('North','South','East','West'):
        picture, metadata = render_source_elevation(new,facade)
        picture.save(run/f'postrun_elevation_{facade}.png')
        dump(run/f'postrun_elevation_{facade}.json',metadata)
    dump(run/'postrun_audit.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
