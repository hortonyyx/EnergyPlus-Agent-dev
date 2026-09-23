"""Historical-value replay and synthetic thickness acceptance, no model calls.

Run from the repository root with an unused --out directory. This is developer
structured input, not autonomous observation and not an adopted building model.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from PIL import Image
from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.component_attributes import thickness_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run = args.out.resolve()
    (run / 'images').mkdir(parents=True, exist_ok=False)
    experiments = ROOT / 'AI_agent/logs/experiments'
    old = experiments / '2026-09-20_sm24_opening_heights_run04'
    image = run / 'images/East_view.png'
    shutil.copy2(old / 'images/East_view.png', image)
    with Image.open(image) as im:
        size = list(im.size)
    historical = experiments / '2026-09-22_sm24_vertical_chains_glm_run13/README.md'
    dump(run / 'inputs.json', {'provider': 'offline_no_model',
        'input_mode': 'developer_structured_historical_replay',
        'images': {'East_view.png': {'size': size, 'sha256': digest(image)}},
        'historical_interpretation': {'path': str(historical.relative_to(ROOT)), 'sha256': digest(historical)},
        'ground_truth_included': False, 'synthetic_thickness_m': .2})
    proposal = json.loads((old / 'candidate_01/proposal.json').read_text())
    assert export_source_proposal(proposal, run / 'seed')['source_geometry_ready']
    toolkit = Toolkit(run)
    observed = toolkit.record_claim(json.dumps({'candidate': 'seed',
        'objects': [{'kind': 'opening', 'id': 'ED1_door'}], 'basis': 'annotation_and_pixels',
        'reason': 'Developer replay of archived GLM vertical chain; no fresh visual observation',
        'observation_mode': 'candidate_review',
        'sources': [{'image': 'East_view.png', 'box': [0, 0, *size]}],
        'values': {'height': {'type': 'dimension_chain', 'lengths': [1900, 2400, 200],
                            'unit': 'mm', 'origin_m': 4.5, 'direction': -1, 'segment': 1}}}))
    toolkit.decide_claim(observed['id'], 'adopted', 'Replay interface check only')
    result = toolkit.revise('seed', json.dumps([{'op': 'update_opening', 'id': 'ED1_door',
        'changes': {'z': {'claim': observed['id'], 'value': 'height'}},
        'reason': 'Replay archived interpretation through computed edit parameter'}]))
    assert result['source_geometry_ready']
    assert result['claim_application']['outside_declared_scope'] == []
    assert [(r['kind'], r['id']) for r in result['claim_application']['changes']] == [('opening', 'ED1_door')]
    source = json.loads((run / result['candidate'] / 'source_model.json').read_text())
    door = next(o for o in source['openings'] if o['id'] == 'ED1_door')
    assert sorted({v[2] for v in door['vertices']}) == [.2, 2.6]
    selections = {}
    for boundary in source['boundaries']:
        kind = 'wall' if boundary['geometry_type'] == 'wall' else 'slab'
        if kind in selections:
            continue
        try:
            thickness_record(source, boundary['id'], .2, basis='synthetic acceptance fixture', source_refs=['fixture'])
        except ValueError:
            continue
        selections[kind] = boundary['id']
    assert set(selections) == {'wall', 'slab'}
    operations = []
    for kind, identity in selections.items():
        claim = toolkit.record_claim(json.dumps({'candidate': result['candidate'],
            'objects': [{'kind': 'boundary', 'id': identity}], 'basis': 'inference',
            'reason': 'Synthetic 0.2 m acceptance value, NOT an observed sm24 thickness', 'sources': [],
            'values': {'thickness': {'type': 'literal', 'value': .2, 'unit': 'm'}}}))
        toolkit.decide_claim(claim['id'], 'adopted', 'Synthetic acceptance only')
        operations.append({'op': 'set_component_thickness', 'boundary_id': identity,
            'thickness_m': {'claim': claim['id'], 'value': 'thickness'},
            'basis': 'synthetic fixture; not observed', 'reason': 'Verify geometry preservation', 'source_refs': ['fixture']})
    thick = toolkit.revise(result['candidate'], json.dumps(operations))
    assert thick['source_geometry_ready']
    after = json.loads((run / thick['candidate'] / 'source_model.json').read_text())
    for key in ('spaces', 'boundaries', 'openings', 'connections'):
        assert source[key] == after[key], key
    assert len(after['component_attributes']) == 2
    app = thick['claim_application']
    assert app['geometry_before_sha256'] == app['geometry_after_sha256']
    dump(run / 'summary.json', {'historical_door_replay': 'pass', 'actual_door_z': [.2, 2.6],
        'thickness_geometry_preserved': True, 'thickness_records': after['component_attributes'],
        'model_calls': 0, 'autonomous_observation': False, 'adopted_building_model': False})
    print('Historical door parameter replay and synthetic wall/slab attribute preservation passed.')


if __name__ == '__main__':
    main()
