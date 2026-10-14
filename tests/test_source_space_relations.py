"""Space identity must remain distinct from connectivity and uncertain samples."""
from copy import deepcopy
import asyncio
import hashlib
import json

import pytest

from src.agent.geometry.source_model import _digest
from src.agent.geometry.source_space_relations import (review_space_relations,
                                                       revalidate_saved_relation_review)


def source(*, merged=False, kind='open'):
    spaces = ([{'id': 'hall', 'floor_id': 'F1', 'polygon': [[0,0],[10,0],[10,10],[0,10]]}]
              if merged else [
                  {'id': 'left', 'floor_id': 'F1', 'polygon': [[0,0],[5,0],[5,10],[0,10]]},
                  {'id': 'right', 'floor_id': 'F1', 'polygon': [[5,0],[10,0],[10,10],[5,10]]}])
    result = {'floors': [{'id': 'F1'}], 'spaces': spaces,
              'openings': [] if merged else [{'id': 'link', 'kind': kind,
                  'space_ids': ['left', 'right'],
                  'vertices': [[5,4,0.5], [5,6,0.5], [5,6,2.5], [5,4,2.5]]}],
              'connections': [] if merged else [{'opening_id': 'link', 'kind': kind,
                  'state': 'open', 'space_ids': ['left', 'right']}]}
    result['source_model_sha256'] = _digest(result)
    return result


def review(model, *, points=None, expected='same_space'):
    return review_space_relations(model, floor_id='F1', image_size=[121,121],
        x_anchors=[[0,0],[100,10]], y_anchors=[[0,10],[100,0]],
        observations=[{'id': 'sample', 'points': points or [[10,20],[80,20]],
                       'expected': expected, 'evidence': 'Caller observed the plan.'}])


@pytest.mark.parametrize('kind', ['open', 'door'])
def test_connection_does_not_merge_spaces_but_is_valid_between_separate_rooms(kind):
    model = source(kind=kind)
    before = deepcopy(model)
    report = review(model)
    row = report['observations'][0]
    assert report['conflict_count'] == 1
    assert row['actual_relation'] == 'separate_spaces'
    assert row['direct_connections'][0]['kind'] == kind
    assert row['points'][0]['world_xy_m'] == [1,8]  # Negative-y calibration, no second flip.
    assert review(model, expected='separate_spaces')['conflict_count'] == 0
    assert model == before


def test_rebuilt_continuous_space_satisfies_same_space_observation():
    row = review(source(merged=True))['observations'][0]
    assert row['actual_relation'] == 'same_space'
    assert row['consistency'] == 'consistent_with_supplied_expectation'
    assert row['direct_connections'] == []


@pytest.mark.parametrize(('point', 'status'), [([50,20], 'on_boundary'),
                                            ([110,20], 'outside_modelled_spaces')])
def test_ambiguous_samples_cannot_approve_or_reject_a_partition(point, status):
    result = review(source(), points=[point, [80,20]])
    row = result['observations'][0]
    assert row['points'][0]['status'] == status
    assert row['actual_relation'] == 'indeterminate'
    assert row['consistency'] == 'not_assessed'
    assert result['unassessed_count'] == 1
    assert result['conflict_count'] == 0


def test_unknown_expectation_is_not_a_success():
    result = review(source(), expected='uncertain')
    assert result['observations'][0]['actual_relation'] == 'separate_spaces'
    assert result['unassessed_count'] == 1
    assert result['drawing_fidelity'] == 'not_evaluated'


@pytest.mark.parametrize('point', [[True,20], [float('nan'),20], [121,20]])
def test_invalid_original_coordinates_are_rejected(point):
    with pytest.raises(ValueError):
        review(source(), points=[point,[80,20]])


def test_altered_source_cannot_reuse_its_hash():
    model = source()
    model['connections'] = []
    with pytest.raises(ValueError, match='does not match source content'):
        review(model)


def _rehash(model):
    model['source_model_sha256'] = _digest({k: v for k, v in model.items()
                                         if k != 'source_model_sha256'})
    return model


def _saved_relations(model, *, legacy=False):
    images = {'plan.png': {'sha256': 'a' * 64, 'size': [121, 121]}}
    calibration = {'image': 'plan.png', 'floor_id': 'F1', 'image_sha256': 'a' * 64,
                   'x_anchors': [[0, 0], [100, 10]], 'y_anchors': [[0, 10], [100, 0]]}
    observations = [{'id': 'conflict', 'points': [[10, 20], [80, 20]],
                     'expected': 'same_space', 'evidence': 'Visible corridor continuity'},
                    {'id': 'uncertain', 'points': [[10, 20], [80, 20]],
                     'expected': 'uncertain', 'evidence': 'Unclear door symbol'}]
    saved = {**review_space_relations(model, floor_id='F1', image_size=[121, 121],
        x_anchors=calibration['x_anchors'], y_anchors=calibration['y_anchors'], observations=observations),
        'image': 'plan.png', 'image_sha256': 'a' * 64, 'image_size': [121, 121]}
    if not legacy:
        saved['submitted_observations'] = deepcopy(observations)
    return saved, images, calibration, observations


@pytest.mark.parametrize('legacy', [False, True])
def test_notes_recompute_conflicts_and_uncertainty_without_rewriting_observations(legacy):
    parent = source()
    current = _rehash({**deepcopy(parent), 'assumptions': ['Explicit note'],
                       'generation': {'provenance': {'parent_candidate': 'candidate_01'}}})
    saved, images, calibration, observations = _saved_relations(parent, legacy=legacy)
    # A previous verdict is not an observation and cannot turn a conflict into a pass.
    saved['conflict_count'] = 0
    saved['observations'][0]['consistency'] = 'consistent_with_supplied_expectation'
    before = deepcopy((parent, current, saved))
    actual = revalidate_saved_relation_review(parent, current, saved, images, calibration=calibration)
    expected = review_space_relations(current, floor_id='F1', image_size=[121, 121],
        x_anchors=calibration['x_anchors'], y_anchors=calibration['y_anchors'], observations=observations)
    assert actual == {**expected, 'submitted_observations': observations}
    assert actual['conflict_count'] == actual['unassessed_count'] == 1
    assert actual['source_model_sha256'] == current['source_model_sha256'] != saved['source_model_sha256']
    assert actual['drawing_fidelity'] == 'not_evaluated'
    assert (parent, current, saved) == before


@pytest.mark.parametrize('change', ['space', 'connection', 'unknown', 'role', 'source_hash',
                                   'parent_binding', 'image', 'calibration', 'submitted'])
def test_relation_revalidation_rejects_changed_geometry_or_evidence(change):
    parent = source()
    current = deepcopy(parent)
    saved, images, calibration, _ = _saved_relations(parent)
    if change == 'space': current['spaces'][0]['polygon'][0][0] += 0.1
    elif change == 'connection': current['connections'] = []
    elif change == 'unknown': current['new_physical_field'] = [1]
    elif change == 'role': current['spaces'][0]['role'] = 'office'
    elif change == 'source_hash': current['source_model_sha256'] = '0' * 64
    elif change == 'parent_binding': saved['source_model_sha256'] = '0' * 64
    elif change == 'image': images['plan.png']['sha256'] = 'b' * 64
    elif change == 'calibration': calibration['x_anchors'][1][1] = 11
    else: saved['submitted_observations'][0]['evidence'] = 'Different observation'
    if change != 'source_hash': _rehash(current)
    with pytest.raises(ValueError):
        revalidate_saved_relation_review(parent, current, saved, images, calibration=calibration)


def _toolkit_relation_fixture(tmp_path):
    from scripts.tool_scripts.run_bim_agent import Toolkit
    from tests.test_bim_agent_tools import _run_with_one_image, _two_room_proposal
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    built = toolkit.build(json.loads(_two_room_proposal()))
    candidate = built['candidate']
    source_path = run / candidate / 'source_model.json'
    model = json.loads(source_path.read_bytes())
    path, calibration = toolkit._save_calibration(candidate=candidate, image='plan.png', floor_id='F1',
        x_anchors=[[0, 0], [11, 6]], y_anchors=[[0, 4], [7, 0]],
        basis='Synthetic original pixel frame', metadata=model)
    observations = [{'id': 'conflict', 'points': [[2, 2], [8, 2]],
                     'expected': 'same_space', 'evidence': 'Observed uninterrupted corridor'},
                    {'id': 'uncertain', 'points': [[2, 2], [8, 2]],
                     'expected': 'uncertain', 'evidence': 'Unclear symbol'}]
    report = toolkit.check_space_relations(candidate, 'plan.png', 'F1', json.dumps(observations))
    return toolkit, candidate, model, report, path, calibration


@pytest.mark.parametrize('change', ['report_file', 'image_bytes', 'calibration_file', 'new_calibration',
                                   'malformed_log', 'nonobject_log', 'malformed_log_record'])
def test_toolkit_does_not_rebind_tampered_or_recalibrated_relation_reports(tmp_path, change):
    toolkit, parent, model, saved, calibration_path, calibration = _toolkit_relation_fixture(tmp_path)
    report_path = toolkit.run / saved['review_file']
    if change == 'report_file':
        altered = deepcopy(saved)
        altered['submitted_observations'][0]['expected'] = 'separate_spaces'
        report_path.write_text(json.dumps(altered), encoding='utf8')
    elif change == 'image_bytes':
        (toolkit.run / 'images/plan.png').write_bytes(b'changed image')
    elif change == 'calibration_file':
        calibration_path.write_bytes(calibration_path.read_bytes() + b' ')
    elif change == 'new_calibration':
        toolkit._save_calibration(candidate=parent, image='plan.png', floor_id='F1',
            x_anchors=[[0, 0], [11, 7]], y_anchors=calibration['y_anchors'],
            basis='Revised coordinate reading', metadata=model)
    else:
        bad_row = {'malformed_log': '{broken', 'nonobject_log': '[]',
                   'malformed_log_record': '{"action":"check_source_space_relation","data":[]}' }[change]
        with (toolkit.run / 'tools.jsonl').open('a', encoding='utf8') as stream:
            stream.write(bad_row + '\n')
    before = report_path.read_bytes()
    source_before = (toolkit.run / parent / 'source_model.json').read_bytes()
    result = toolkit.revalidate_space_relations(parent, 'synthetic-current', model)
    assert not result['reports'] and len(result['skipped']) == 1
    assert list((toolkit.run / 'space_relation_reviews').iterdir()) == [report_path]
    assert report_path.read_bytes() == before
    assert (toolkit.run / parent / 'source_model.json').read_bytes() == source_before


@pytest.mark.parametrize('calibration_contents', ['{broken', '[]'])
def test_notes_save_survives_unavailable_relation_calibration(tmp_path, calibration_contents):
    from tests.test_bim_agent_tools import _server_session, _json_result

    async def scenario():
        toolkit, parent, _, saved, calibration_path, _ = _toolkit_relation_fixture(tmp_path)
        original_review = (toolkit.run / saved['review_file']).read_bytes()
        async with _server_session(toolkit.run, readonly=False) as session:
            opening = _json_result(await session.call_tool('check_openings', {'candidate': parent,
                'review_json': json.dumps({'floor_id': 'F1', 'kind': 'door', 'image': 'plan.png',
                    'coverage': 'complete', 'marks': [{'mark_id': 'd1', 'box': [1, 1, 6, 7],
                        'opening_ids': ['door'], 'space_ids': ['left', 'right'],
                        'basis': 'visible', 'note': 'synthetic aperture'}]})}))
            opening_path = toolkit.run / opening['review_file']
            original_opening = opening_path.read_bytes()
            calibration_path.write_text(calibration_contents, encoding='utf8')
            raw = await session.call_tool('revise_bim', {'candidate': parent,
                'operations_json': json.dumps([{'op': 'set_notes',
                    'assumptions': ['Updated notes'], 'unresolved': ['Still uncertain']}])})
            assert not raw.isError
            result = _json_result(raw)
        current = toolkit.run / result['candidate']
        assert result['source_geometry_ready'] and (current / 'source_model.json').is_file()
        assert json.loads((current / 'proposal.json').read_bytes())['assumptions'] == ['Updated notes']
        for key in ('space_relation_revalidation', 'opening_review_revalidation'):
            assert result[key]['status'] == 'unavailable' and not result[key]['reports']
        assert result['building_precision']['status'] == 'unavailable'
        assert not (current / 'precision_report.json').exists()
        assert len(list((toolkit.run / 'space_relation_reviews').glob('*.json'))) == 1
        assert len(list((toolkit.run / 'opening_reviews').glob('*.json'))) == 1
        assert (toolkit.run / saved['review_file']).read_bytes() == original_review
        assert opening_path.read_bytes() == original_opening
    asyncio.run(scenario())


@pytest.mark.parametrize('parent_contents', [None, '[]'])
def test_relation_shared_parent_context_failure_is_unavailable(tmp_path, parent_contents):
    toolkit, parent, model, saved, _, _ = _toolkit_relation_fixture(tmp_path)
    parent_path = toolkit.run / parent / 'source_model.json'
    if parent_contents is None:
        parent_path.unlink()
    else:
        parent_path.write_text(parent_contents, encoding='utf8')
    result = toolkit.revalidate_space_relations(parent, 'synthetic-current', model)
    assert result['status'] == 'unavailable' and not result['reports']
    assert len(list((toolkit.run / 'space_relation_reviews').glob('*.json'))) == 1


def test_precision_artifact_write_failure_after_notes_is_not_hidden(tmp_path, monkeypatch):
    from pathlib import Path
    toolkit, parent, _, _, _, _ = _toolkit_relation_fixture(tmp_path)
    write_text = Path.write_text

    def failed_precision_write(path, *args, **kwargs):
        if path.name == 'precision_report.json':
            raise OSError('precision artifact write failed')
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', failed_precision_write)
    with pytest.raises(OSError, match='precision artifact write failed'):
        toolkit.revise(parent, json.dumps([{'op': 'set_notes',
            'assumptions': ['Updated notes'], 'unresolved': []}]))


def test_stdio_notes_revalidate_relations_and_exact_read_but_physical_edits_stay_stale(tmp_path):
    from tests.test_bim_agent_tools import _server_session, _json_result

    async def scenario():
        toolkit, candidate, _, saved, _, _ = _toolkit_relation_fixture(tmp_path)
        run = toolkit.run
        original = run / saved['review_file']
        original_bytes = original.read_bytes()
        expected_observations = saved['submitted_observations']
        operations = [
            {'op': 'replace_note', 'field': 'assumptions', 'old': 'synthetic fixture',
             'replacement': ['Reviewed synthetic fixture'], 'reason': 'Clarify note', 'source_refs': ['plan.png']},
            {'op': 'set_notes', 'assumptions': ['Current note'], 'unresolved': ['Still uncertain']}]
        async with _server_session(run, readonly=False) as session:
            for operation in operations:
                parent = candidate
                reply = _json_result(await session.call_tool('revise_bim', {
                    'candidate': parent, 'operations_json': json.dumps([operation])}))
                candidate = reply['candidate']
                refresh = reply['space_relation_revalidation']
                assert not refresh['skipped'] and len(refresh['reports']) == 1
                small = refresh['reports'][0]
                assert small['sample_count'] == 2
                assert small['conflict_count'] == small['unassessed_count'] == 1
                # Follow only the reader returned in the actual model-visible MCP reply.
                reference = small['details']
                page = _json_result(await session.call_tool(reference['read']['tool'],
                    {**reference['read']['arguments'], 'json_pointer': '/submitted_observations'}))
                assert page['value'] == expected_observations
                fresh_path = run / small['review_file']
                fresh = json.loads(fresh_path.read_bytes())
                prior = run / fresh['revalidated_from']['review_file']
                assert fresh['revalidated_from']['candidate'] == parent
                assert fresh['revalidated_from']['review_sha256'] == hashlib.sha256(prior.read_bytes()).hexdigest()
                assert small['sha256'] == hashlib.sha256(fresh_path.read_bytes()).hexdigest()
                assert fresh['submitted_observations'] == expected_observations
                status = toolkit.space_relation_status(json.loads((run / candidate / 'source_model.json').read_bytes()))
                assert status['sample_count'] == 2 and status['status'] == 'observations_require_follow_up'
                assert status['conflict_count'] == status['unassessed_count'] == 1
                assert original.read_bytes() == original_bytes
            for coordinate in (3.5, 3):
                reply = _json_result(await session.call_tool('revise_bim', {
                    'candidate': candidate, 'operations_json': json.dumps([{'op': 'move_shared_wall',
                        'space_ids': ['left', 'right'], 'coordinate_m': coordinate,
                        'reason': 'Physical change', 'source_refs': ['plan.png']}])}))
                candidate = reply['candidate']
                assert 'space_relation_revalidation' not in reply
            noted = _json_result(await session.call_tool('revise_bim', {
                'candidate': candidate, 'operations_json': json.dumps([{'op': 'set_notes',
                    'assumptions': ['Restored geometry'], 'unresolved': []}])}))
            assert not noted['space_relation_revalidation']['reports']
            current = json.loads((run / noted['candidate'] / 'source_model.json').read_bytes())
            assert toolkit.space_relation_status(current)['status'] == 'not_reviewed'
            assert original.read_bytes() == original_bytes
    asyncio.run(scenario())
