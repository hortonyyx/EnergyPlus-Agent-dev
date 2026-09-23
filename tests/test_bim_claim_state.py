import asyncio
import json

import pytest

from src.agent.execution.bim_claim_state import project
from tests.test_bim_claims import setup_run, adopt, claim, edit
from tests.test_bim_agent_tools import _json_result, _server_session


def window_claim(toolkit, candidate='seed'):
    return adopt(toolkit, claim(candidate=candidate, objects=[{'kind': 'window', 'id': 'window'}],
        values={'height': {'type': 'literal', 'value': [1, 2], 'unit': 'm'}},
        unresolved=['<b>Frame material unexamined</b>']))


def window_check(identity):
    return {'op': 'update_window', 'id': 'window',
        'changes': {'z': {'claim': identity, 'value': 'height'}}, 'reason': 'confirm drawn height'}


def states(toolkit, candidate):
    return {r['id']: r for r in project(toolkit.claims(), candidate)['claims']}


def test_confirmation_has_no_mutation_and_follows_only_unchanged_descendants(tmp_path):
    run, toolkit = setup_run(tmp_path)
    initial = (run/'seed/proposal.json').read_bytes()
    window = window_claim(toolkit)
    toolkit.confirm_claims('seed', json.dumps([window_check(window['id'])]))
    assert (run/'seed/proposal.json').read_bytes() == initial
    assert not list(run.glob('candidate_*'))
    assert states(toolkit, 'seed')[window['id']]['state'] == 'confirmed_unchanged'
    door = adopt(toolkit, claim())
    revised = toolkit.revise('seed', json.dumps([edit(door['id'])]))['candidate']
    current = states(toolkit, revised)
    assert current[window['id']]['state'] == 'confirmed_unchanged'
    assert current[door['id']]['state'] == 'applied_current'
    delivery = toolkit.delivery(revised, selection_origin='agent_selected')
    assert not delivery['adopted_unapplied_claims']
    html = (run/'delivery.html').read_text()
    assert '已核对，无需修改' in html and '&lt;b&gt;Frame material unexamined&lt;/b&gt;' in html
    changed = toolkit.revise(revised, json.dumps([{'op': 'update_window', 'id': 'window',
        'changes': {'z': [1, 2.2]}, 'reason': 'new interpretation', 'source_refs': ['fixture']}]))['candidate']
    assert states(toolkit, changed)[window['id']]['state'] == 'changed_since_check'
    # A sibling rooted at seed must not inherit the door application.
    sibling = toolkit.revise('seed', json.dumps([{'op': 'replace_note', 'field': 'assumptions',
        'old': '<墙体位置由平面推断>', 'replacement': ['Unchanged geometry; note clarified'],
        'reason': 'fixture', 'source_refs': ['fixture']}]))['candidate']
    assert states(toolkit, sibling)[door['id']]['state'] == 'pending_application'
    toolkit.decide_claim(window['id'], 'retracted', 'conflicting source')
    assert states(toolkit, revised)[window['id']]['state'] == 'retracted'


def test_false_or_unbound_confirmation_is_rejected_and_partial_coverage_visible(tmp_path):
    run, toolkit = setup_run(tmp_path)
    row = adopt(toolkit, claim())
    with pytest.raises(ValueError, match='differs'):
        toolkit.confirm_claims('seed', json.dumps([edit(row['id'])]))
    window = adopt(toolkit, claim(objects=[{'kind': 'window', 'id': 'window'}],
        values={'height': {'type': 'literal', 'value': [1, 2], 'unit': 'm'},
                'span': {'type': 'literal', 'value': [1, 2], 'unit': 'm'}}))
    toolkit.confirm_claims('seed', json.dumps([window_check(window['id'])]))
    assert states(toolkit, 'seed')[window['id']]['state'] == 'partially_satisfied'
    unbound = window_check(window['id'])
    unbound['changes']['span'] = [1, 2]
    with pytest.raises(ValueError, match='every confirmed'):
        toolkit.confirm_claims('seed', json.dumps([unbound]))
    assert len(list((run/'claims').glob('confirmation_*'))) == 1


def test_bound_value_overridden_later_in_same_revision_is_not_current(tmp_path):
    _, toolkit = setup_run(tmp_path)
    row = window_claim(toolkit)
    result = toolkit.revise('seed', json.dumps([window_check(row['id']),
        {'op': 'update_window', 'id': 'window', 'changes': {'z': [1, 2.2]},
         'reason': 'Later unbound override in same batch', 'source_refs': ['fixture']}]))
    assert states(toolkit, result['candidate'])[row['id']]['state'] == 'changed_since_check'


def test_explicit_note_replacement_updates_source_and_keeps_history(tmp_path):
    run, toolkit = setup_run(tmp_path)
    replacement = {'op': 'replace_note', 'field': 'assumptions', 'old': '<墙体位置由平面推断>',
        'replacement': ['Wall position now checked; other properties remain unknown'],
        'reason': 'Local image review supersedes the previous assumption', 'source_refs': ['fixture']}
    result = toolkit.revise('seed', json.dumps([replacement]))
    source = json.loads((run/result['candidate']/'source_model.json').read_text())
    assert '<墙体位置由平面推断>' not in source['assumptions']
    assert replacement['replacement'][0] in source['assumptions']
    assert source['generation']['unresolved'] == ['<b>未确认门状态</b>']
    assert project(toolkit.claims(), result['candidate'])['superseded_notes'][0]['before'] == replacement['old']
    assert result['claim_application']['changes'] == []
    with pytest.raises(ValueError, match='exactly match'):
        toolkit.revise(result['candidate'], json.dumps([replacement]))


def test_imported_claim_ids_are_not_mistaken_for_new_run_decisions(tmp_path):
    run, toolkit = setup_run(tmp_path)
    row = adopt(toolkit, claim())
    revised = toolkit.revise('seed', json.dumps([edit(row['id'])]))['candidate']
    proposal = json.loads((run/revised/'proposal.json').read_text())
    other, next_toolkit = setup_run(tmp_path/'next', proposal)
    new = window_claim(next_toolkit)
    assert new['id'] == row['id']  # local numbering restarts
    current = project(next_toolkit.claims(), 'seed')
    assert current['claims'][0]['state'] == 'pending_application'
    assert len(current['inherited_observations']) == 1


def test_confirmation_tool_stdio_and_readonly_exclusion(tmp_path):
    async def scenario():
        run, toolkit = setup_run(tmp_path)
        row = window_claim(toolkit)
        async with _server_session(run, readonly=True) as session:
            assert 'confirm_claims' not in {t.name for t in (await session.list_tools()).tools}
        async with _server_session(run, readonly=False) as session:
            result = _json_result(await session.call_tool('confirm_claims', {
                'candidate': 'seed', 'operations_json': json.dumps([window_check(row['id'])])}))
            assert result['status'] == 'confirmed_unchanged'
            current = _json_result(await session.call_tool('claim_status', {'candidate': 'seed'}))
            assert current['claims'][0]['state'] == 'confirmed_unchanged'
    asyncio.run(scenario())
