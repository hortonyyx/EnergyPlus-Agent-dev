"""Observed wall coordinates must drive the actual space vertices."""
import json

import pytest

from tests.test_bim_claims import setup_run, adopt, claim
from tests.test_bim_claim_state import states
from tests.test_source_proposal import _proposal


def shape_case(tmp_path):
    proposal = _proposal()
    proposal['geometry']['openings'] = []
    run, toolkit = setup_run(tmp_path, proposal)
    refs = [{'kind': 'space', 'id': s} for s in ('hall', 'room')]
    axis = {'type': 'image_axis', 'image': 'plan.png', 'axis': 'x',
            'anchors': [[0, 0], [12, 6]], 'pixels': [7, 9]}
    row = adopt(toolkit, claim(objects=refs, values={
        'faces': axis, 'midplane': {**axis, 'reduction': 'midpoint'},
        'outer': {'type': 'literal', 'value': 6, 'unit': 'm'}},
        value_targets={'faces': [], 'midplane': refs, 'outer': refs[1:]}))
    ref = lambda field: {'claim': row['id'], 'value': field}
    op = {'op': 'reshape_spaces', 'spaces': [
        {'id': 'hall', 'polygon': [[0, 0], [ref('midplane'), 0], [ref('midplane'), 6], [0, 6]]},
        {'id': 'room', 'polygon': [[ref('midplane'), 0], [ref('outer'), 0], [ref('outer'), 6], [ref('midplane'), 6]]}],
        'reason': 'Measured wall faces define the representative midplane'}
    return run, toolkit, row, op


def test_joint_reshape_uses_measured_midpoint_and_specific_value_targets(tmp_path):
    run, toolkit, row, op = shape_case(tmp_path)
    assert row['resolved_values']['midplane'] == 4
    result = toolkit.revise('seed', json.dumps([op]))
    assert result['source_geometry_ready']
    app = result['claim_application']
    assert app['scope_check'] == 'checked' and app['outside_declared_scope'] == []
    assert len(app['evidence']['bindings']) == 6
    assert len(app['parameters_without_claims']) == 10  # unchanged literal coordinates
    current = states(toolkit, result['candidate'])[row['id']]
    assert current['state'] == 'applied_current' and current['missing_bindings'] == []
    cells = json.loads((run/result['candidate']/'proposal.json').read_text())['geometry']['floors'][0]['cells']
    assert cells[0]['x'] == [0, 4] and cells[1]['x'] == [4, 6]
    assert len(current['retained_bindings']) == 6


@pytest.mark.parametrize('field', ['faces', 'outer'])
def test_supporting_values_and_other_object_parameters_cannot_drive_a_vertex(tmp_path, field):
    _, toolkit, _, op = shape_case(tmp_path)
    op['spaces'][0]['polygon'][1][0]['value'] = field
    with pytest.raises(ValueError, match='targets'):
        toolkit.revise('seed', json.dumps([op]))


def test_same_batch_overwrite_does_not_hide_behind_another_retained_vertex(tmp_path):
    _, toolkit, row, op = shape_case(tmp_path)
    # Still-valid stepped partition keeps some old x=4 vertices but moves others.
    overwrite = {'op': 'reshape_spaces', 'spaces': [
        {'id': 'hall', 'polygon': [[0, 0], [3.5, 0], [3.5, 3], [4, 3], [4, 6], [0, 6]]},
        {'id': 'room', 'polygon': [[3.5, 0], [6, 0], [6, 6], [4, 6], [4, 3], [3.5, 3]]}],
        'reason': 'Subsequent unbound reinterpretation', 'source_refs': ['fixture']}
    result = toolkit.revise('seed', json.dumps([op, overwrite]))
    assert result['source_geometry_ready']
    current = states(toolkit, result['candidate'])[row['id']]
    assert current['state'] != 'applied_current'
    assert ['midplane', 'space', 'hall'] in current['missing_bindings']


def test_explicit_mapping_requires_all_values_and_declared_objects(tmp_path):
    _, toolkit = setup_run(tmp_path)
    for mapping in ({}, {'height': [{'kind': 'window', 'id': 'window'}]}, {'height': []}):
        with pytest.raises(ValueError, match='value_targets|application value target'):
            toolkit.record_claim(json.dumps(claim(value_targets=mapping)))


def test_height_coverage_is_exposed_in_mcp_and_delivery(tmp_path):
    import asyncio
    from tests.test_bim_agent_tools import _server_session, _json_result
    from scripts.tool_scripts.run_bim_agent import delivery_tool_reply

    async def scenario():
        run, toolkit = setup_run(tmp_path)
        async with _server_session(run, readonly=False) as session:
            report = _json_result(await session.call_tool('check_openings', {
                'candidate': 'seed', 'heights_only': True}))
            coverage = report['height_coverage']
            assert {row['opening_id'] for row in coverage['openings']} == {'window', 'door'}
            assert all(row['coverage_state'] == 'unchecked' for row in coverage['openings'])
        delivery = toolkit.delivery('seed', selection_origin='test')
        assert 'height_coverage' in delivery_tool_reply(delivery)
        assert '开口高度观察范围' in (run/'delivery.html').read_text()
    asyncio.run(scenario())


def test_existing_polygon_can_be_confirmed_with_all_coordinates_bound(tmp_path):
    proposal = _proposal()
    proposal['geometry']['floors'][0]['cells'][0]['polygon'] = [[0, 0], [3, 0], [3, 6], [0, 6]]
    run, toolkit = setup_run(tmp_path, proposal)
    initial = (run/'seed/proposal.json').read_bytes()
    row = adopt(toolkit, claim(objects=[{'kind': 'space', 'id': 'hall'}],
        values={name: {'type': 'literal', 'value': value, 'unit': 'm'}
                for name, value in [('left', 0), ('right', 3), ('bottom', 0), ('top', 6)]}))
    ref = lambda field: {'claim': row['id'], 'value': field}
    polygon = [[ref(x), ref(y)] for x, y in [('left', 'bottom'), ('right', 'bottom'),
                                            ('right', 'top'), ('left', 'top')]]
    toolkit.confirm_claims('seed', json.dumps([{'op': 'reshape_spaces',
        'spaces': [{'id': 'hall', 'polygon': polygon}], 'reason': 'Confirm existing measured polygon'}]))
    assert (run/'seed/proposal.json').read_bytes() == initial
    assert states(toolkit, 'seed')[row['id']]['state'] == 'confirmed_unchanged'
    assert not list(run.glob('candidate_*'))
