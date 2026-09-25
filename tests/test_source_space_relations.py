"""Space identity must remain distinct from connectivity and uncertain samples."""
from copy import deepcopy

import pytest

from src.agent.geometry.source_model import _digest
from src.agent.geometry.source_space_relations import review_space_relations


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
