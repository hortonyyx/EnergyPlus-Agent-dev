"""A3-T: actionable compact replies preserve real evidence and geometry."""
import asyncio
import copy
import hashlib
import json

import pytest

from scripts.tool_scripts.run_bim_agent import Toolkit
from scripts.tool_scripts.bim_agent_replies import compact_reply, read_report, summarize_reply
from src.agent.geometry.plan_partition import compile_plan_partition
from tests.test_bim_agent_plan_partition import example
from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session
from tests.test_plan_partition import _plan


def test_aliases_keep_geometry_and_original_bytes_with_explicit_receipt(tmp_path):
    run = _run_with_one_image(tmp_path)
    original = example()
    alias = copy.deepcopy(original)
    for row in alias['partitions']:
        row['pixels'] = row.pop('points')
    for row in alias.get('space_seeds', []):
        row['pixels'] = row.pop('point')
    canonical, _ = compile_plan_partition(original, image_size=(12, 8), image_name='plan.png')
    compiled, meta = compile_plan_partition(alias, image_size=(12, 8), image_name='plan.png')
    assert compiled == canonical and meta['field_aliases']
    raw = json.dumps(alias)
    result = Toolkit(run).build_plan('plan.png', raw)
    assert result['source_geometry_ready']
    record = result['plan_input']
    assert record['field_aliases'] == meta['field_aliases']
    assert (run / record['submitted_plan_file']).read_text() == raw
    assert json.loads((run / record['plan_file']).read_text()) == original


def test_conflicting_alias_and_unknown_field_do_not_guess(tmp_path):
    run = _run_with_one_image(tmp_path)
    plan = example()
    plan['partitions'][0]['pixels'] = [[1, 1], [2, 1]]
    result = Toolkit(run).build_plan('plan.png', json.dumps(plan))
    assert not result['source_geometry_ready']
    assert 'both pixels and points' in result['error']
    assert result['repair_hint']['path'] == 'plan.partitions[0]'
    assert not list(run.glob('candidate_*'))
    plan = example()
    plan['openings'][0]['pixels'] = plan['openings'][0].pop('p1')
    result = Toolkit(run).build_plan('plan.png', json.dumps(plan))
    assert not result['source_geometry_ready']
    assert result['repair_hint']['path'] == 'plan.openings[0]'
    assert set(result['repair_hint']['example']) >= {'id', 'kind', 'p1', 'p2', 'z', 'source_refs'}


def test_disconnected_endpoint_reports_nearest_declared_line_without_snapping():
    plan = _plan()
    plan['partitions'][1]['points'][-1] = [49, 50]
    before = copy.deepcopy(plan)
    with pytest.raises(ValueError) as exc:
        compile_plan_partition(plan, image_size=(100, 100), image_name='plan.png')
    message = str(exc.value)
    assert "'nearest_line': 'P_vertical'" in message
    assert "'distance_pixels': 1.0" in message
    assert 'no automatic snapping' in message
    assert plan == before


def test_compact_reply_keeps_usable_ids_geometry_images_and_complete_readback(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            response = await session.call_tool('build_plan_bim', {'image':'plan.png','plan_json':json.dumps(example())})
            result = _json_result(response)
            assert len([b for b in response.content if b.type == 'image']) == 2
            raw = (run / result['details_file']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == result['details_sha256']
            full = json.loads(raw)
            assert full['height_coverage'] == result['height_coverage']
            assert full['source_validation'] == result['source_validation']
            assert full['plan_input'] == result['plan_input']
            assert full['plan_compilation']['space_count'] == result['plan_compilation']['space_count']
            for key, identity, fields in (
                ('partition_mapping', 'partition_id', ('pixel_points', 'world_points_m')),
                ('opening_hosts', 'opening_id', ('p1_pixel', 'p2_pixel', 'width_m')),
                ('space_mapping', 'space_id', ('seed', 'source_refs')),
            ):
                selected = result['plan_compilation'][key]
                actual = {row[identity]: row for row in
                          (dict(zip(selected['columns'], values)) for values in selected['rows'])}
                for item in full['plan_compilation'][key]:
                    for field in fields:
                        if field in item:
                            assert actual[item[identity]][field] == item[field]
            returned_ids = [r[0] for f in result['opening_inventory']['floors'] for r in f['rows']]
            assert sorted(returned_ids) == sorted(o['id'] for f in full['opening_inventory']['floors'] for o in f['openings'])
            offset = 0
            pieces = []
            while True:
                page = _json_result(await session.call_tool('read_candidate_items', {
                    'candidate':'','collection':'report','report_file':result['details_file'], 'offset':offset,'limit':12000}))
                pieces.append(page['text'])
                if page['next_offset'] is None:break
                offset = page['next_offset']
            assert ''.join(pieces).encode() == raw
            for path in ['inputs.json', '../private.json', str(tmp_path / 'outside.json')]:
                failure = await session.call_tool('read_candidate_items', {
                    'candidate':'','collection':'report','report_file':path})
                assert failure.isError
    asyncio.run(scenario())


def test_report_detects_tampering_and_does_not_mutate_full_result(tmp_path):
    raw = {'candidate':'candidate_01', 'provenance':{'plan_input':{'id':'draft_001'}},
           'plan_input':{'id':'draft_001'},'error':'keep this error'}
    before = copy.deepcopy(raw)
    compact = compact_reply(tmp_path, 'build_bim', raw)
    assert raw == before and compact['error'] == raw['error']
    (tmp_path / compact['details_file']).write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch'):
        read_report(tmp_path, compact['details_file'], 0, 50)


def test_only_identical_submitted_operations_are_deduplicated():
    submitted = [{'op': 'update_opening', 'id': 'D1', 'changes': {'z': [0, 2.1]}}]
    full = {'claim_application': {'submitted_operations': submitted,
                                 'resolved_operations': copy.deepcopy(submitted),
                                 'changes': [{'kind': 'door', 'id': 'D1'}]}}
    receipt = summarize_reply(full)['claim_application']
    assert receipt['submitted_operations_equal_resolved']
    assert receipt['resolved_operations'] == submitted
    assert receipt['changes'] == full['claim_application']['changes']
    full['claim_application']['resolved_operations'][0]['changes']['z'] = [0, 2.2]
    assert summarize_reply(full)['claim_application'] == full['claim_application']


def test_fixed_parameter_values_are_in_catalog(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            tools = {t.name:t.inputSchema for t in (await session.list_tools()).tools}
            expected = {('pixel_profile','axis'):['x','y'], ('view_pixel_profile','axis'):['x','y'],
                        ('map_dimension_chain','unit'):['mm','m'], ('map_dimension_chain','direction'):[-1,1],
                        ('view_elevation_candidate','facade'):['North','South','East','West'],
                        ('record_work_review','decision'):['continue','stop']}
            for (tool,key), values in expected.items():
                assert tools[tool]['properties'][key]['enum'] == values
            assert 'report' in tools['read_candidate_items']['properties']['collection']['enum']
            assert 'plan_partition' in tools['get_bim_reference']['properties']['topic']['enum']
    asyncio.run(scenario())


def test_empty_profile_explains_color_and_support_adjustments(tmp_path):
    run = _run_with_one_image(tmp_path)
    result = Toolkit(run).profile('plan.png', [0,0,12,8], 'x', [255,0,0], 0)
    diagnostic = result['empty_filter_diagnostics']
    assert 'tolerance' in diagnostic['next_action'] and 'RGB' in diagnostic['next_action']
    import numpy as np
    from scripts.tool_scripts.run_bim_agent import _empty_profile_diagnostics
    diagnostic = _empty_profile_diagnostics(np.full((5,5,3),255), [255,255,255], np.array([1,1,1,1,1]), 4, 5)
    assert 'min_fraction' in diagnostic['next_action'] and 'cross_axis_profile' in diagnostic['next_action']
