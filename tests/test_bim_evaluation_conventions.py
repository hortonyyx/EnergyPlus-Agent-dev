"""Documented offsets are separate; real geometry/reading defects remain visible."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.judge.conventions import classify_conventions, load_policy, reading_report
from src.agent.judge.gt import gt_path, load_gt_document
from src.agent.judge.partition_evidence import reference_partition
from src.agent.judge.plan_inventory import compare_plan_inventory, compare_exterior_heights
from scripts.tool_scripts.evaluate_bim_agent import evaluate

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT/'AI_agent/logs/experiments'


def fixture(case):
    run = EXP/f'2026-10-01_opus_dev_{case}'
    selected = json.loads((run/'delivery.json').read_bytes())['candidate']
    source = json.loads((run/selected/'source_model.json').read_bytes())
    proposal = json.loads((run/selected/'proposal.json').read_bytes())
    manifest = json.loads((run/'inputs.json').read_bytes())
    key = 'sm25-L_anchor' if case == 'sm25' else case + '_anchor'
    return run, source, proposal, manifest, key


def score(source, proposal, manifest, key):
    gt = load_gt_document(key)
    raw = reference_partition(ensure_corrected_geometry(proposal['geometry']), gt, source_spaces=source['spaces'])
    policy, obs = load_policy(key, gt_path(key), manifest)
    inventory = compare_plan_inventory(source, obs, raw['floor_mapping'])
    heights = compare_exterior_heights(source, gt, raw)
    return raw, classify_conventions(raw, source, policy, inventory=inventory, heights=heights)


@pytest.mark.parametrize('case,ground,walls', [('sm21',0,0), ('sm24',8,0), ('sm25',14,6)])
def test_developer_cases_keep_reference_bytes_and_separate_known_offsets(case, ground, walls):
    _, source, proposal, manifest, key = fixture(case)
    original = deepcopy(source)
    reference = gt_path(key).read_bytes()
    raw, quality = score(source, proposal, manifest, key)
    assert source == original and gt_path(key).read_bytes() == reference
    changes = quality['convention_differences']
    assert sum('ground_threshold' in d['category'] for d in changes) == ground
    assert sum('single_line_half_wall' in d['category'] for d in changes) == walls
    assert quality['status'] in {'pass','minor'}
    if ground:
        assert raw['comparison']['status'] == 'severe'
        assert all(d['original_finding']['severity'] == 'severe' for d in changes)


@pytest.mark.parametrize('mutation', ['ground_over_limit', 'roof_shift', 'wall_over_limit',
                                    'door_removed', 'door_wrong_connection', 'window_added', 'window_height',
                                    'orphan_opening', 'orphan_connection'])
def test_substantive_or_out_of_tolerance_changes_stay_severe(mutation):
    _, source, proposal, manifest, key = fixture('sm25')
    if mutation == 'ground_over_limit':
        for s in source['spaces']:
            if s['floor_id']=='F1': s['z_floor'] = .201
    elif mutation == 'roof_shift':
        for s in source['spaces']:
            if s['floor_id']=='F1': s['height'] += .1
    elif mutation == 'wall_over_limit':
        for s in source['spaces']:
            if s['floor_id']=='F1':
                for p in s['polygon']:
                    if 5 <= p[0] <= 8.94001 and abs(p[1]-14)<1e-6: p[1] = 13.86
    elif mutation == 'door_removed':
        oid = next(o['id'] for o in source['openings'] if o['kind']=='door')
        source['openings'] = [o for o in source['openings'] if o['id']!=oid]
        source['connections'] = [o for o in source['connections'] if o['opening_id']!=oid]
    elif mutation == 'door_wrong_connection':
        source['connections'][0]['space_ids'] = ['wrong-room']
    elif mutation == 'window_added':
        window = deepcopy(next(o for o in source['openings'] if o['kind']=='window'))
        window['id'] += '-spurious'
        source['openings'].append(window)
    elif mutation == 'window_height':
        window = next(o for o in source['openings'] if o['kind']=='window')
        for p in window['vertices']: p[2] += .2
    elif mutation == 'orphan_opening':
        opening = deepcopy(source['openings'][0])
        opening.update(id='orphan', space_ids=['missing-space'])
        source['openings'].append(opening)
    elif mutation == 'orphan_connection':
        source['connections'].append(dict(source['connections'][0], opening_id='missing-opening'))
    _, quality = score(source, proposal, manifest, key)
    assert quality['status'] == 'severe'
    assert any(f['severity']=='severe' for f in quality['retained_findings'])


def test_allowance_never_uses_candidate_chosen_average():
    _, source, proposal, manifest, key = fixture('sm25')
    for s in source['spaces']:
        if s['floor_id']=='F1':
            for p in s['polygon']:
                if abs(p[1]-14)<1e-6 and 5 <= p[0] <= 8.94001: p[1]=14.06
    _, result = score(source, proposal, manifest, key)
    assert result['status']=='severe'
    assert any(f['code']=='partition_boundary_changed' for f in result['retained_findings'])


def test_readings_survive_later_delivery_and_failed_drafts(tmp_path):
    run, _, _, _, _ = fixture('sm24')
    draft = json.loads((run/'plan_drafts/draft_001/plan.json').read_bytes())
    for name, value in [('draft_001', draft), ('draft_002', dict(draft, z_floor=10.))]:
        p=tmp_path/'plan_drafts'/name
        p.mkdir(parents=True)
        (p/'plan.json').write_text(json.dumps(value))
    result=reading_report(tmp_path)
    assert [r['declaration']['z_floor'] for r in result['records']] == [.2,10.]
    assert result['reading_accuracy']=='not_inferred_from_delivery_quality'
    assert reading_report(tmp_path/'no-records')['status']=='not_available'


def test_historical_runtime_is_scoreable_without_manifest_patches(tmp_path):
    run, source, proposal, manifest, key = fixture('sm24')
    root = tmp_path/'runtime'
    bim = root/'bim'
    candidate = bim/'candidate_01'
    candidate.mkdir(parents=True)
    # Reproduce the missing fields in pre-A5 runtime inputs.
    for field in ('implementation_sha256','input_contents'):
        manifest.pop(field,None)
    raw=json.dumps(manifest).encode()
    (bim/'inputs.json').write_bytes(raw)
    (candidate/'source_model.json').write_text(json.dumps(source))
    (candidate/'proposal.json').write_text(json.dumps(proposal))
    (root/'receipt.json').write_text(json.dumps({'status':'completed'}))
    result=evaluate(root,key,modelling_task='reconstruction',reference_scope='offline fixture')
    assert (bim/'inputs.json').read_bytes()==raw
    assert not (bim/'summary.json').exists()
    assert result['candidates'][0]['delivery_quality_status']=='pass'
    assert (bim/'evaluation/reading_readings.json').is_file()
    assert (bim/'evaluation/delivery_quality.json').is_file()


def test_unfinished_runtime_cannot_be_evaluated(tmp_path):
    (tmp_path/'bim').mkdir()
    (tmp_path/'bim/inputs.json').write_text('{}')
    (tmp_path/'receipt.json').write_text('{"status":"running"}')
    with pytest.raises(RuntimeError,match='wait until generator finishes'):
        evaluate(tmp_path,'sm24_anchor',modelling_task='reconstruction',reference_scope='test')


def test_cross_floor_alignment_uses_existing_line_and_preserves_identity():
    _, source, proposal, manifest, key = fixture('sm25')
    for space in source['spaces']:
        if space['floor_id'] == 'F1':
            for point in space['polygon']:
                if abs(point[1] - 16.) < 1e-6 and 11.05 < point[0] < 15.01:
                    point[1] = 16.06
    _, quality = score(source, proposal, manifest, key)
    assert sum('cross_floor_alignment' in d['category'] for d in quality['convention_differences']) == 2
    assert quality['status'] in {'pass', 'minor'}


def test_corrupt_raw_reading_is_recorded_instead_of_dropped(tmp_path):
    folder = tmp_path/'plan_drafts/draft_001'
    folder.mkdir(parents=True)
    raw = '{"z_floor": .2, "partitions": ['
    (folder/'plan.json').write_text(raw)
    report = reading_report(tmp_path)
    assert report['records'][0]['raw_text'] == raw
    assert report['records'][0]['status'] == 'unparseable_saved_reading'


def test_missing_inventory_cannot_certify_delivery():
    _, source, proposal, manifest, key = fixture('sm24')
    raw, _ = score(source, proposal, manifest, key)
    result = classify_conventions(raw, source, {}, inventory={'status':'not_evaluated'},
                                  heights={'status':'not_evaluated'})
    assert result['status'] == 'severe'
    assert not result['convention_differences']


@pytest.mark.parametrize('mutation', ['millimetre_split', 'merge'])
def test_wall_convention_cannot_hide_a_changed_room_partition(mutation):
    from shapely.geometry import Polygon, box
    _, source, proposal, manifest, key = fixture('sm25')
    room = next(s for s in source['spaces'] if s['id'] == 'F1:LM1')
    if mutation == 'millimetre_split':
        original = Polygon(room['polygon'])
        room['polygon'] = list(original.intersection(box(0, 0, 8.939, 20)).exterior.coords)[:-1]
        source['spaces'].append(dict(room, id='F1:sliver',
            polygon=list(original.intersection(box(8.939, 0, 10, 20)).exterior.coords)[:-1]))
        expected = 'source_space_split'
    else:
        second = next(s for s in source['spaces'] if s['id'] == 'F1:LM2')
        room['polygon'] = list(Polygon(room['polygon']).union(Polygon(second['polygon'])).exterior.coords)[:-1]
        source['spaces'].remove(second)
        expected = 'source_spaces_merged'
    _, result = score(source, proposal, manifest, key)
    assert result['status'] == 'severe'
    assert expected in {f['code'] for f in result['retained_findings'] if f['severity'] == 'severe'}
    assert not any('F1:LM1' in d.get('candidate_ids', []) for d in result['convention_differences'])


def test_good_delivery_does_not_reclassify_a_bad_saved_reading(tmp_path):
    run, source, proposal, manifest, key = fixture('sm24')
    raw, quality = score(source, proposal, manifest, key)
    assert quality['status'] == 'pass'
    original = run/'plan_drafts/draft_001'
    target = tmp_path/'plan_drafts/draft_001'
    target.mkdir(parents=True)
    declaration = json.loads((original/'plan.json').read_bytes())
    declaration['z_floor'] = 10.
    (target/'plan.json').write_text(json.dumps(declaration))
    (target/'compilation.json').write_bytes((original/'compilation.json').read_bytes())
    readings = reading_report(tmp_path, reference_spaces=raw['reference_spaces'])
    assert readings['records'][0]['declaration']['z_floor'] == 10.
    assert readings['records'][0]['strict_reading_partition']['status'] == 'severe'
