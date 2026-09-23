"""Replay recorded run27 numbers through shape references; no new interpretation."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.tool_scripts.run_bim_agent import Toolkit, dump, digest
from src.agent.execution.bim_claims import geometry_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    run = parser.parse_args().out.resolve()
    old = ROOT/'AI_agent/logs/experiments/2026-09-23_sm21_claim_state_glm_run27'
    run.mkdir(parents=True, exist_ok=False)
    for name in ('images', 'seed', 'pixel_profiles'):
        shutil.copytree(old/name, run/name)
    manifest = json.loads((old/'inputs.json').read_text())
    manifest.update(provider='offline_no_model', input_mode='developer_shape_binding_replay',
                    scope='Replay existing run27 interpreted values; no fresh observation')
    manifest.pop('deadline_epoch', None)
    manifest['implementation_sha256'] = {name: digest(ROOT/name) for name in manifest['implementation_sha256']}
    dump(run/'inputs.json', manifest)
    toolkit = Toolkit(run)
    data = json.loads((old/'claims/claim_0001.json').read_text())['claim']
    data['value_targets'] = {
        'north_midplane_y': [r for r in data['objects'] if r['id'] == 'CORRIDOR' or r['id'].startswith('N_')],
        'south_midplane_y': [r for r in data['objects'] if r['id'] == 'CORRIDOR' or r['id'].startswith('S_')],
        'north_wall_faces': [], 'south_wall_faces': []}
    claim = toolkit.record_claim(json.dumps(data))
    toolkit.decide_claim(claim['id'], 'adopted', 'Developer replay of recorded GLM observation')
    window = toolkit.record_claim(json.dumps(json.loads((old/'claims/claim_0002.json').read_text())['claim']))
    toolkit.decide_claim(window['id'], 'adopted', 'Replay existing window observation')
    operations = json.loads((old/'claims/application_0001.json').read_text())['resolved_operations']
    for row in operations[0]['spaces']:
        for point in row['polygon']:
            if point[1] in (5.009, 2.99):
                field = 'north_midplane_y' if point[1] == 5.009 else 'south_midplane_y'
                point[1] = {'claim': claim['id'], 'value': field}
    for operation in operations:
        if operation['op'] == 'update_window':
            operation['changes']['z'] = {'claim': window['id'], 'value': 'z'}
            # actual original field name is read, not assumed by this replay
            operation['changes']['z']['value'] = next(iter(window['resolved_values']))
    result = toolkit.revise('seed', json.dumps(operations))
    assert result['source_geometry_ready'], result
    current = json.loads((run/result['candidate']/'proposal.json').read_text())
    original = json.loads((old/'candidate_01/proposal.json').read_text())
    assert geometry_state(current) == geometry_state(original)
    delivery = toolkit.delivery(result['candidate'], selection_origin='developer_shape_binding_replay',
                                generation_status={'state': 'completed', 'model_calls': 0})
    states = {r['id']: r['state'] for r in delivery['current_claim_state']['claims']}
    assert set(states.values()) == {'applied_current'}, states
    app = result['claim_application']
    assert app['scope_check'] == 'checked' and not app['outside_declared_scope']
    assert len([b for b in app['evidence']['bindings'] if b['claim_id'] == claim['id']]) == 16
    dump(run/'summary.json', {'geometry_identical_to_run27_candidate_01': True, 'states': states,
        'shape_coordinate_bindings': 16, 'model_calls': 0,
        'method': 'Developer maps saved values to specific rooms; historical door point edits remain literals',
        'independent_observation': False, 'adopted_building_model': False})
    print(json.dumps(states))


if __name__ == '__main__':
    main()
