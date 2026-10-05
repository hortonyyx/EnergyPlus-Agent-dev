"""Explicit dimensions check saved positions, without treating missing data as pass."""
import copy

import pytest

from src.agent.geometry.wall_placement import annotation_tolerances, wall_placement_report


def fixture(coordinates=(0, 4.015, 8.03)):
    source = dict(schema_version='source_bim_v2', spaces=[dict(id='room', floor_id='F1')],
        boundaries=[dict(id=f'b{i}', space_id='room', kind='physical', geometry_type='wall',
            vertices=[[x,0,0],[x,5,0],[x,5,3],[x,0,3]], counterpart_ids=[])
            for i,x in enumerate(coordinates)])
    refs = [dict(id=f'w{i}', boundary_id=f'b{i}', offsets_m=[-.06,.06], thickness_m=.12,
        reference_basis='explicit centre line', thickness_scope='wall', evidence_status='observed',
        source_refs=['plan.png: observed wall']) for i in range(len(coordinates))]
    def end(i, side='representative'):
        return dict(wall_id=f'w{i}', side=side, image='plan.png', pixel=[10+i*20,10])
    dims = [dict(id=f'd{i}', axis='x', direction=1, value=4000, unit='mm',
        start=end(i), end=end(i+1), source_refs=['plan.png: 4000 label']) for i in range(len(coordinates)-1)]
    return source, refs, dims


def test_cumulative_chain_finds_drift_even_when_individual_spans_are_in_tolerance():
    args = fixture()
    untouched = copy.deepcopy(args)
    report = wall_placement_report(*args)
    assert report['checked_positions'] == 2
    assert report['total'] == 1
    finding = report['items'][0]
    assert finding['boundary_ids'] == ['b2'] and finding['anchor_boundary_ids'] == ['b0']
    assert finding['deviation_m'] == .03 and finding['expected_coordinate_m'] == 8
    assert [d['id'] for d in finding['annotations']] == ['d0','d1']
    assert args == untouched and not report['geometry_changed'] and not report['delivery_blocked']
    assert wall_placement_report(args[0], args[1], list(reversed(args[2]))) == report


def test_wall_face_conversion_keeps_representative_geometry_unshifted():
    source, refs, dims = fixture((0,4,8))
    for d in dims:
        d['start']['side'] = 'positive'
        d['end']['side'] = 'negative'
        d['value'] = 3880
    report = wall_placement_report(source, refs, dims)
    assert report['total'] == 0 and report['checked_positions'] == 2
    dims[0]['end']['side'] = 'unknown'
    report = wall_placement_report(source, refs, dims)
    assert report['total'] == 0 and report['checked_positions'] == 1
    assert report['skipped'][0]['reason'] == 'unknown_wall_face_offsets'


def test_missing_stale_and_same_wall_evidence_do_not_invent_position_checks():
    source, refs, dims = fixture()
    assert wall_placement_report(source, [], [])['status'] == 'not_assessed'
    refs[0]['boundary_id'] = 'missing'
    report = wall_placement_report(source, refs, dims)
    assert report['total'] == 0 and report['checked_positions'] == 0
    assert report['skipped'][0]['reason'] == 'invalid_or_stale_wall_evidence'
    source, refs, dims = fixture()
    dims[0]['end']['wall_id'] = 'w0'
    report = wall_placement_report(source, refs, dims[:1])
    assert report['checked_positions'] == 0 and report['total'] == 0


def test_reverse_direction_and_tolerance_boundary():
    source, refs, dims = fixture((8,4.02,0))
    for d in dims:
        d['direction'] = -1
    report = wall_placement_report(source, refs, dims)
    assert report['total'] == 0 and report['checked_positions'] == 2
    assert wall_placement_report(source, refs, dims, tolerance_m=.01)['total'] == 1


def test_pixel_error_budget_is_axis_and_floor_specific_and_reports_the_tradeoff():
    calibrations = [dict(floor_id='F1', x_anchors=[[0,0],[1000,10]], y_anchors=[[0,0],[100,10]]),
                    dict(floor_id='F2', x_anchors=[[0,0],[100,20]], y_anchors=[[0,0],[100,20]])]
    tolerances = annotation_tolerances(calibrations)
    assert tolerances == {'F1': {'x': .04, 'y': .4}, 'F2': {'x': .8, 'y': .8}}
    report = wall_placement_report(*fixture((0,4.03,8.07)), floor_tolerances=tolerances)
    assert report['total'] == 1 and report['items'][0]['deviation_m'] == .07
    assert report['items'][0]['tolerance_m'] == .04
    assert 'four original pixels' in report['tolerance_source']
    assert wall_placement_report(*fixture((0,4.03,8.03)), floor_tolerances=tolerances)['total'] == 0
    with pytest.raises(ValueError, match='scale'):
        annotation_tolerances([{**calibrations[0], 'x_anchors': [[0,0],[1,1000]]}])


def test_explicit_chain_node_checks_partial_shared_wall_and_does_not_guess_faces():
    source, _, _ = fixture((0,4.07,8))
    source['boundaries'][1]['counterpart_ids'] = ['b2']  # unequal extents/position do not expand the target
    position = dict(id='p1', boundary_id='b1', axis='x', lengths=[4000,4000], unit='mm',
        origin_m=0, direction=1, node=1, offset_m=0,
        basis='explicit representative plane', source_refs=['plan.png: 4000 + 4000'])
    report = wall_placement_report(source, [], [], positions=[position])
    assert report['checked_positions'] == 1 and report['total'] == 1
    assert report['items'][0]['deviation_m'] == .07
    assert report['items'][0]['boundary_ids'] == ['b1']
    with pytest.raises(ValueError, match='offset_m'):
        wall_placement_report(source, [], [], positions=[{**position, 'offset_m': None}])
    with pytest.raises(ValueError, match='node'):
        wall_placement_report(source, [], [], positions=[{**position, 'node': 3}])


@pytest.mark.parametrize('tolerance', [0, -1, float('inf'), float('nan'), True])
def test_invalid_tolerance_is_rejected(tolerance):
    with pytest.raises(ValueError):
        wall_placement_report(*fixture(), tolerance_m=tolerance)
