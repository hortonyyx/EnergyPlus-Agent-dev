"""A locally recovered door preserves floors, provenance and host constraints."""
import copy
import asyncio
import json

import pytest

from src.agent.execution.bim_height_coverage import height_coverage
from src.agent.execution.bim_claim_state import project
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.proposal_edits import apply_proposal_edits
from tests.test_bim_claims import setup_run, adopt, claim
from tests.test_bim_agent_tools import _server_session, _json_result
from tests.test_proposal_edits import _rectangular_wall_proposal


def addition(**changes):
    row = {'op': 'add_opening', 'opening': {'id': 'new', 'kind': 'door',
        'space_id': 'upper_left', 'other_space_id': 'upper_right',
        'p1': [4, 2.5], 'p2': [4, 3.5], 'z': [3, 5.1], 'state': 'unknown'},
        'reason': 'Synthetic upper-floor door evidence', 'source_refs': ['plan: new door']}
    row['opening'].update(changes)
    return row


def test_addition_preserves_other_floor_and_existing_objects(tmp_path):
    original = _rectangular_wall_proposal()
    frozen = copy.deepcopy(original)
    revised = apply_proposal_edits(original, [addition()])
    assert original == frozen
    for field in ('floors', 'windows'):
        assert revised['geometry'][field] == original['geometry'][field]
    assert revised['geometry']['openings'][:-1] == original['geometry']['openings']
    report = export_source_proposal(revised, tmp_path / 'out')
    assert report['source_geometry_ready']
    source = json.loads((tmp_path / 'out/source_model.json').read_text())
    door = next(o for o in source['openings'] if o['id'] == 'new')
    assert door['space_ids'] == ['upper_left', 'upper_right']
    assert {v[2] for v in door['vertices']} == {3, 5.1}


@pytest.mark.parametrize('changes', [
    {'z': [0, 2.1]}, {'other_space_id': 'right'}, {'p1': [3, 2.5], 'p2': [3, 3.5]},
    {'p1': [4, 1.5], 'p2': [4, 2.5]},
])
def test_bad_height_host_or_overlap_remains_blocked(tmp_path, changes):
    revised = apply_proposal_edits(_rectangular_wall_proposal(), [addition(**changes)])
    report = export_source_proposal(revised, tmp_path / 'out')
    assert not report['source_geometry_ready']


def test_duplicate_id_is_rejected():
    with pytest.raises(ValueError, match='already exists'):
        apply_proposal_edits(_rectangular_wall_proposal(), [addition(id='left_south')])


def observation(identity):
    return {'kind': 'as_drawn_opening_unbuilt', 'input_id': 'upper_plan',
            'observation_ids': [identity], 'floor_id': 'F2', 'reason': 'ambiguous host'}


def resolve(identity, opening='new'):
    return {'op': 'resolve_unbuilt_observation', 'input_id': 'upper_plan',
        'observation_ids': [identity], 'opening_ids': [opening],
        'reason': 'These wall-face observations describe the same physical door',
        'source_refs': ['upper_plan: checked both sides']}


def test_two_observations_can_resolve_to_one_door_with_old_records_retained(tmp_path):
    proposal = _rectangular_wall_proposal()
    proposal['geometry']['unsupported'] = [observation('face-a'), observation('face-b')]
    revised = apply_proposal_edits(proposal, [addition(), resolve('face-a'), resolve('face-b')])
    assert revised['geometry']['unsupported'] == []
    assert [a['before'] for a in revised['geometry']['corrections'][1:]] == proposal['geometry']['unsupported']
    assert export_source_proposal(revised, tmp_path / 'out')['source_geometry_ready']
    for operation in (resolve('absent'), resolve('face-a', 'missing'), resolve('face-a', 'between')):
        with pytest.raises(ValueError):
            apply_proposal_edits(proposal, [operation])


def test_unbuilt_observations_are_readable_even_when_geometry_is_summarized(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path, _rectangular_wall_proposal())
        path = run / 'seed/proposal.json'
        proposal = json.loads(path.read_text())
        proposal['geometry']['unsupported'] = [observation('face-a'), observation('face-b')]
        path.write_text(json.dumps(proposal))
        async with _server_session(run, readonly=False) as session:
            result = _json_result(await session.call_tool('read_candidate_items', {
                'candidate': 'seed', 'collection': 'unsupported', 'floor_id': 'F2', 'limit': 1}))
            assert result['items'] == [observation('face-a')]
            assert result['next_offset'] == 1 and result['total'] == 2
    asyncio.run(scenario())


def test_creation_claims_bind_existing_hosts_and_go_stale_when_door_moves(tmp_path):
    run, toolkit = setup_run(tmp_path, _rectangular_wall_proposal())
    refs = [{'kind': 'space', 'id': s} for s in ('upper_left', 'upper_right')]
    row = adopt(toolkit, claim(objects=refs, basis='inference', sources=[],
        reason='Assumed upper-floor height; no image height evidence',
        values={'height': {'type': 'literal', 'value': [3.0, 5.1], 'unit': 'm'}}))
    operation = addition(z={'claim': row['id'], 'value': 'height'})
    result = toolkit.revise('seed', json.dumps([operation]))
    assert result['source_geometry_ready']
    assert result['claim_application']['outside_declared_scope'] == []
    assert project(toolkit.claims(), result['candidate'])['claims'][0]['state'] == 'applied_current'
    coverage = height_coverage(toolkit.claims(), result['candidate'])
    assert 'new' in json.dumps(coverage)
    # Explicitly inspect per-opening state rather than mistake the plan for a height check.
    def rows(value):
        if isinstance(value, dict):
            if value.get('opening_id') == 'new':
                yield value
            for child in value.values():
                yield from rows(child)
        elif isinstance(value, list):
            for child in value:
                yield from rows(child)
    assert any(r.get('coverage_state') == 'non_image_evidence_only' for r in rows(coverage))
    changed = toolkit.revise(result['candidate'], json.dumps([{'op': 'update_opening', 'id': 'new',
        'changes': {'p1': [4, 2.4], 'p2': [4, 3.4]}, 'reason': 'New observation', 'source_refs': ['plan: moved']}]))
    assert changed['source_geometry_ready']
    assert project(toolkit.claims(), changed['candidate'])['claims'][0]['state'] != 'applied_current'


def test_added_door_plan_points_use_both_host_claims_without_claiming_height(tmp_path):
    run, toolkit = setup_run(tmp_path, _rectangular_wall_proposal())
    hosts = [{'kind': 'space', 'id': s} for s in ('upper_left', 'upper_right')]
    values = {k: {'type': 'literal', 'value': v, 'unit': 'm'}
              for k, v in {'start': [4.0, 2.5], 'end': [4.0, 3.5]}.items()}
    bad = adopt(toolkit, claim(objects=hosts[:1], values=values))
    operation = addition(p1={'claim': bad['id'], 'value': 'start'},
                         p2={'claim': bad['id'], 'value': 'end'})
    with pytest.raises(ValueError, match='targets'):
        toolkit.revise('seed', json.dumps([operation]))
    good = adopt(toolkit, claim(objects=hosts, values=values))
    operation['opening'].update(p1={'claim': good['id'], 'value': 'start'},
                                p2={'claim': good['id'], 'value': 'end'})
    result = toolkit.revise('seed', json.dumps([operation]))
    assert result['source_geometry_ready']
    app = result['claim_application']
    assert app['parameters_without_claims'] == [{'operation_index': 0, 'parameter': 'z'}]
    assert app['outside_declared_scope'] == []
    state = project(toolkit.claims(), result['candidate'])
    assert next(c for c in state['claims'] if c['id'] == good['id'])['state'] == 'applied_current'
    coverage = height_coverage(toolkit.claims(), result['candidate'])
    assert coverage['summary']['image_linked_count'] == 0
