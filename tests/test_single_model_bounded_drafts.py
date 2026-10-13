"""Large single-model drafts and failed saves stay inspectable without flooding context."""
import asyncio
import copy
import json

from scripts.tool_scripts.bim_agent_replies import compact_reply
from scripts.tool_scripts.run_bim_agent import Toolkit, digest
from tests.test_bim_agent_plan_partition import example
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session


def test_large_saved_draft_and_differences_are_bounded_and_exactly_retrievable(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        draft = run / 'plan_drafts' / 'draft_001'
        draft.mkdir(parents=True)
        plan = example()
        plan['regularization'] = {'status': 'pass', 'trace': [
            {'id': f'change-{i}', 'original': '测量依据' * 600, 'adopted': i / 10}
            for i in range(30)]}
        (draft / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
        plan_hash = digest(draft / 'plan.json')
        (draft / 'input.json').write_text(json.dumps({
            'plan_sha256': plan_hash, 'image': 'plan.png',
            'image_sha256': digest(run / 'images/plan.png')}))
        differences = {'plan_sha256': plan_hash, 'status': 'review_required', 'items': [
            {'id': f'finding-{i}', 'bbox': [0, 0, 3, 3], 'evidence': '原图依据' * 500}
            for i in range(20)]}
        (draft / 'drawing_differences.json').write_text(
            json.dumps(differences, ensure_ascii=False), encoding='utf-8')
        (draft / 'result.json').write_text(json.dumps({'drawing_differences': {
            'file': 'plan_drafts/draft_001/drawing_differences.json',
            'sha256': digest(draft / 'drawing_differences.json')}}))
        async with _server_session(run, readonly=False) as session:
            for arguments in ({'draft_id': 'draft_001'},
                              {'draft_id': 'draft_001', 'field': 'plan'},
                              {'draft_id': 'draft_001', 'field': 'regularization'},
                              {'draft_id': 'draft_001', 'field': 'report:/drawing_differences'}):
                result = _json_result(await session.call_tool('inspect_plan_draft', arguments))
                assert len(json.dumps(result, ensure_ascii=False).encode('utf-8')) < 18000
                assert result['plan_sha256'] == plan_hash
            exact = _json_result(await session.call_tool('inspect_plan_draft', {
                'draft_id': 'draft_001', 'field': 'openings', 'object_id': 'D1'}))
            assert exact['value'] == plan['openings'][0]
            page = _json_result(await session.call_tool('inspect_plan_draft', {
                'draft_id': 'draft_001', 'field': 'report:/drawing_differences/items'}))
            assert [row['key'] for row in page['entries']] == list(range(8))
            next_page = _json_result(await session.call_tool('inspect_plan_draft', page['next']))
            assert [row['key'] for row in next_page['entries']] == list(range(8, 16))
            reference = next_page['entries'][0]['value']['full_record']['read']
            assert reference['arguments']['draft_id'] == 'draft_001'
            exact = _json_result(await session.call_tool(reference['tool'], {
                **reference['arguments'], 'field': reference['arguments']['field'] + '/bbox'}))
            assert exact['value'] == differences['items'][8]['bbox']
            nested = _json_result(await session.call_tool('inspect_plan_draft', {
                'draft_id': 'draft_001', 'field': 'plan:/regularization/trace/29/adopted'}))
            assert nested['value'] == 2.9
            assert digest(draft / 'plan.json') == plan_hash
            report_bytes = (draft / 'drawing_differences.json').read_bytes()
            (draft / 'drawing_differences.json').write_text(json.dumps({
                'plan_sha256': plan_hash, 'status': 'pass', 'items': []}))
            refused = await session.call_tool('inspect_plan_draft', {
                'draft_id': 'draft_001', 'field': 'report:/drawing_differences'})
            assert refused.isError
            (draft / 'drawing_differences.json').write_bytes(report_bytes)
            (draft / 'plan.json').write_text('{}')
            refused = await session.call_tool('inspect_plan_draft', {'draft_id': 'draft_001'})
            assert refused.isError
    asyncio.run(scenario())


def test_large_failed_save_reply_keeps_repair_location_and_binds_exact_report(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        raw = {'status': 'error', 'source_geometry_ready': False,
               'error': 'opening D1 lacks a host',
               'repair_hint': {'path': 'plan.openings[0]', 'current': [3, 4]},
               'plan_revision': {'status': 'rejected', 'changes': [
                   {'id': f'object-{i}', 'before': {'evidence': 'saved reading ' * 900},
                    'after': {'host': f'wall-{i}'}} for i in range(100)]}}
        unchanged = copy.deepcopy(raw)
        reply = compact_reply(run, 'revise_plan_bim', raw)
        assert raw == unchanged
        assert len(json.dumps(reply).encode()) < 18000
        assert reply['repair_hint'] == raw['repair_hint'] and reply['error'] == raw['error']
        assert reply['source_geometry_ready'] is False
        assert json.loads((run / reply['details_file']).read_bytes()) == raw
        reference = reply['plan_revision']['reference']['read']
        assert reference['arguments']['report_file'] == reply['details_file']
        async with _server_session(run, readonly=False) as session:
            exact = _json_result(await session.call_tool(reference['tool'], {
                **reference['arguments'], 'json_pointer': '/plan_revision/changes/99/after'}))
            assert exact['value'] == {'host': 'wall-99'}
            other = compact_reply(run, 'revise_plan_bim', {**raw, 'error': 'different save'})
            assert other['details_file'] != reply['details_file']
            first = _json_result(await session.call_tool(reference['tool'], {
                **reference['arguments'], 'json_pointer': '/error'}))
            assert first['value'] == 'opening D1 lacks a host'
    asyncio.run(scenario())


def test_mcp_revision_exception_preserves_full_hint_in_a_bounded_report(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        built = Toolkit(run).build_plan('plan.png', json.dumps(example()))
        assert built['source_geometry_ready']
        record = built['plan_input']
        plan_file = run / record['plan_file']
        before = plan_file.read_bytes()
        trace = 'evidence ' * 150000
        # Missing reason is rejected before geometry mutation; the old repair
        # example echoed this entire value into the model's exception response.
        operations = [{'op': 'set', 'field': 'regularization',
                       'value': {'trace': trace}, 'source_refs': ['synthetic']}]
        async with _server_session(run, readonly=False) as session:
            failure = await session.call_tool('revise_plan_bim', {
                'draft_id': 'draft_001', 'expected_plan_sha256': record['plan_sha256'],
                'operations_json': json.dumps(operations)})
            assert failure.isError
            shown = json.dumps(failure.model_dump(mode='json'), ensure_ascii=False).encode('utf-8')
            assert len(shown) < 49000  # JSON is present in text and structuredContent.
            result = failure.structuredContent
            assert result['status'] == 'error' and 'reason' in result['error']
            assert len(json.dumps(result, ensure_ascii=False).encode('utf-8')) <= 24000
            full = json.loads((run / result['details_file']).read_bytes())
            assert trace in full['repair_hint'] and full['error'] == result['error']
            page = _json_result(await session.call_tool('read_candidate_items', {
                'candidate': '', 'collection': 'report', 'report_file': result['details_file'],
                'json_pointer': '/repair_hint'}))
            assert page['text'] == full['repair_hint'][:600]
            assert plan_file.read_bytes() == before
            assert len(list(run.glob('candidate_*'))) == 1
    asyncio.run(scenario())


def test_compact_reply_bounds_total_size_for_many_large_fields(tmp_path):
    run = _run_with_one_image(tmp_path)
    raw = {'status': 'error', 'error': 'keep the located failure',
           'repair_hint': {'path': 'plan.openings[7]', 'bbox': [1, 2, 3, 4]},
           **{f'auxiliary_{i}': [{'id': f'row-{j}', 'evidence': '依据' * 900}
                               for j in range(12)] for i in range(30)}}
    result = compact_reply(run, 'revise_plan_bim', raw)
    assert len(json.dumps(result, ensure_ascii=False).encode('utf-8')) <= 24000
    assert result['error'] == raw['error'] and result['repair_hint'] == raw['repair_hint']
    assert result['report_view']['reference']['read']['arguments']['json_pointer'] == ''
    assert json.loads((run / result['details_file']).read_bytes()) == raw
