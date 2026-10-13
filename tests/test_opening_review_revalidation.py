"""Reuse observations, never verdicts, after physically unchanged note/use edits."""
import asyncio
import copy
import hashlib
import json

import pytest

from scripts.tool_scripts.run_bim_agent import Toolkit
from src.agent.geometry.bim_delivery import summarize_delivery
from src.agent.geometry.opening_review import review_openings, revalidate_saved_review
from src.agent.geometry.source_model import _digest
from tests.test_opening_review import _source, _images, _review
from tests.test_bim_agent_tools import (_run_with_one_image, _server_session,
                                      _json_result, _two_room_proposal)


def _rehash(source):
    source['source_model_sha256'] = _digest({k: v for k, v in source.items() if k != 'source_model_sha256'})
    return source


def _saved(source, observations=None, calibration=None):
    observations = observations or _review()
    return {**review_openings(source, observations, _images(), plan_calibration=calibration),
            'observations': copy.deepcopy(observations)}


@pytest.mark.parametrize('edit', ['notes', 'use'])
def test_note_or_use_change_recomputes_source_binding_without_mutating_evidence(edit):
    parent = _source()
    saved = _saved(parent)
    source = copy.deepcopy(parent)
    if edit == 'notes':
        source['assumptions'].append('A newly documented simplification')
        source['generation'] = {'provenance': {'parent_candidate': 'candidate_01'}}
    else:
        source['spaces'][0]['role'] = 'conference/meeting/multipurpose'
        source['spaces'][0]['role_evidence'] = {'basis': 'inferred'}
        source['public_names'] = {'changed': 'display name'}
    _rehash(source)
    before = copy.deepcopy((parent, source, saved))
    report = revalidate_saved_review(parent, source, saved, _images())
    assert report == review_openings(source, saved['observations'], _images())
    assert report['source_model_sha256'] == source['source_model_sha256'] != saved['source_model_sha256']
    assert report['drawing_fidelity'] == 'not_evaluated'
    assert (parent, source, saved) == before


@pytest.mark.parametrize('mutation', ['opening', 'host', 'room', 'floor', 'contact', 'unknown'])
def test_physical_or_unknown_source_changes_cannot_reuse_observations(mutation):
    parent = _source()
    source = copy.deepcopy(parent)
    if mutation == 'opening': source['openings'][0]['vertices'][0][2] += 0.1
    elif mutation == 'host': source['opening_hosts'] = []
    elif mutation == 'room': source['spaces'][0]['polygon'][0][0] += 0.1
    elif mutation == 'floor': source['floors'][0]['z_floor'] += 0.1
    elif mutation == 'contact': source['boundary_relations'] = []
    else: source['unknown_future_geometry'] = [1, 2, 3]
    _rehash(source)
    with pytest.raises(ValueError, match='unchanged physical'):
        revalidate_saved_review(parent, source, _saved(parent), _images())


def test_old_pass_is_not_trusted_and_pending_observation_remains_a_finding():
    parent = _source()
    saved = _saved(parent, _review(marks=[_review()['marks'][0]]))
    saved['findings'] = []
    saved['conclusion'] = 'consistent_with_supplied_observations'
    report = revalidate_saved_review(parent, parent, saved, _images())
    assert report['conclusion'] != 'consistent_with_supplied_observations'
    assert 'unaccounted_model_opening' in {row['code'] for row in report['findings']}


@pytest.mark.parametrize('change', ['parent_hash', 'image_hash', 'image_size', 'missing_observations'])
def test_stale_evidence_is_rejected(change):
    parent = _source()
    saved, images = _saved(parent), _images()
    if change == 'parent_hash': saved['source_model_sha256'] = '0' * 64
    elif change == 'image_hash': images['plan.png']['sha256'] = 'b' * 64
    elif change == 'image_size': images['plan.png']['size'] = [101, 80]
    else: saved.pop('observations')
    with pytest.raises(ValueError):
        revalidate_saved_review(parent, parent, saved, images)


def test_calibration_change_is_rejected_but_new_record_with_same_anchors_is_rechecked():
    parent = _source()
    calibration = {'image': 'plan.png', 'floor_id': 'F1', 'image_sha256': 'a' * 64,
                   'calibration_id': 'calibration_001', 'x_anchors': [[0, 0], [99, 4]],
                   'y_anchors': [[0, 0], [79, 2]]}
    saved = _saved(parent, calibration=calibration)
    equivalent = {**calibration, 'calibration_id': 'calibration_002'}
    report = revalidate_saved_review(parent, parent, saved, _images(), plan_calibration=equivalent)
    assert report['location_check']['calibration_id'] == 'calibration_002'
    with pytest.raises(ValueError, match='calibration changed'):
        revalidate_saved_review(parent, parent, saved, _images(),
            plan_calibration={**equivalent, 'x_anchors': [[0, 0], [99, 5]]})
    with pytest.raises(ValueError, match='calibration changed'):
        revalidate_saved_review(parent, parent, saved, _images())


def test_stdio_notes_and_use_revision_save_linked_current_reviews_without_reentering_marks(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            built = _json_result(await session.call_tool('build_bim', {'proposal_json': _two_room_proposal()}))
            candidate = built['candidate']
            observations = {'floor_id': 'F1', 'kind': 'door', 'image': 'plan.png', 'coverage': 'complete',
                'marks': [{'mark_id': 'd1', 'box': [1, 1, 6, 7], 'opening_ids': ['door'],
                           'space_ids': ['left', 'right'], 'basis': 'visible', 'note': 'synthetic aperture'}]}
            checked = _json_result(await session.call_tool('check_openings', {
                'candidate': candidate, 'review_json': json.dumps(observations)}))
            original_path = run / checked['review_file']
            original = original_path.read_bytes()
            for operations in [[{'op': 'replace_note', 'field': 'assumptions', 'old': 'synthetic fixture',
                    'replacement': ['Reviewed synthetic fixture'], 'reason': 'document review',
                    'source_refs': ['plan.png']}],
                [{'op': 'set_space_role', 'space_id': 'left', 'role': 'conference/meeting/multipurpose',
                  'basis': 'inferred', 'assumptions': ['synthetic use'], 'reason': 'document observed furniture',
                  'source_refs': ['plan.png']}]]:
                parent = candidate
                revised = _json_result(await session.call_tool('revise_bim', {
                    'candidate': parent, 'operations_json': json.dumps(operations)}))
                candidate = revised['candidate']
                refresh = revised['opening_review_revalidation']
                assert not refresh['skipped'] and len(refresh['reports']) == 1
                assert 'rechecked' in revised['opening_review']
                path = run / refresh['reports'][0]['review_file']
                fresh = json.loads(path.read_bytes())
                assert fresh['observations'] == observations
                prior = run / fresh['revalidated_from']['review_file']
                assert fresh['revalidated_from']['review_sha256'] == hashlib.sha256(prior.read_bytes()).hexdigest()
                assert fresh['revalidated_from']['candidate'] == parent
                assert refresh['reports'][0]['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
                source = json.loads((run / candidate / 'source_model.json').read_bytes())
                summary = summarize_delivery(source, [fresh])
                door = next(x for x in summary['opening_review_scopes'] if x['kind'] == 'door')
                assert door['review_status'] == 'consistent_with_supplied_observations'
                assert original_path.read_bytes() == original
            # Physical edits continue requiring new observations, not automatic rebinding.
            moved = _json_result(await session.call_tool('revise_bim', {'candidate': candidate,
                'operations_json': json.dumps([{'op': 'move_shared_wall', 'space_ids': ['left', 'right'],
                    'coordinate_m': 3.5, 'reason': 'physical change', 'source_refs': ['plan.png']}])}))
            assert 'opening_review_revalidation' not in moved
            assert moved['opening_review'].startswith('not_reviewed')
            restored = _json_result(await session.call_tool('revise_bim', {'candidate': moved['candidate'],
                'operations_json': json.dumps([{'op': 'move_shared_wall', 'space_ids': ['left', 'right'],
                    'coordinate_m': 3, 'reason': 'restore geometry', 'source_refs': ['plan.png']}])}))
            noted = _json_result(await session.call_tool('revise_bim', {'candidate': restored['candidate'],
                'operations_json': json.dumps([{'op': 'replace_note', 'field': 'assumptions',
                    'old': 'Reviewed synthetic fixture', 'replacement': ['Restored physical candidate'],
                    'reason': 'record restoration', 'source_refs': ['plan.png']}])}))
            assert not noted['opening_review_revalidation']['reports']
            assert noted['opening_review'].startswith('not_reviewed')
            assert len(list((run / 'opening_reviews').glob('review_*.json'))) == 3
            assert original_path.read_bytes() == original
    asyncio.run(scenario())


@pytest.mark.parametrize('invalid', ['actual_image_bytes', 'missing_observations', 'invalid_json',
                                   'null_observations', 'list_observations', 'null_calibration', 'list_calibration'])
def test_toolkit_does_not_create_revalidated_reports_for_invalid_saved_evidence(tmp_path, invalid):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    parent = toolkit.build(json.loads(_two_room_proposal()))['candidate']
    source = json.loads((run / parent / 'source_model.json').read_bytes())
    observations = {'floor_id': 'F1', 'kind': 'door', 'image': 'plan.png', 'coverage': 'complete',
        'marks': [{'mark_id': 'd1', 'box': [1, 1, 6, 7], 'opening_ids': ['door'],
                   'space_ids': ['left', 'right'], 'basis': 'visible', 'note': 'synthetic aperture'}]}
    saved = {'candidate': parent, **review_openings(source, observations, toolkit.manifest['images']),
             'observations': observations}
    if invalid == 'missing_observations': saved.pop('observations')
    if invalid == 'null_observations': saved['observations'] = None
    if invalid == 'list_observations': saved['observations'] = []
    if invalid == 'null_calibration': saved['location_check'] = None
    if invalid == 'list_calibration': saved['location_check'] = []
    folder = run / 'opening_reviews'
    folder.mkdir()
    original = folder / 'review_001.json'
    original.write_text('invalid' if invalid == 'invalid_json' else json.dumps(saved), encoding='utf8')
    before = original.read_bytes()
    if invalid == 'actual_image_bytes':
        (run / 'images/plan.png').write_bytes(b'changed input image')
    result = toolkit.revalidate_opening_reviews(parent, 'synthetic-current', source)
    assert not result['reports'] and len(result['skipped']) == 1
    assert list(folder.iterdir()) == [original]
    assert original.read_bytes() == before
