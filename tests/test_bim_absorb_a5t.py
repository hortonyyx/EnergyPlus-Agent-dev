"""A5-T public entrypoints retain measurements and source identity offline."""
import asyncio
import copy
import json
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

from scripts.tool_scripts.bim_agent_guidance import REPLAY_ONLY_TOOLS, filter_tool_catalog
from scripts.tool_scripts.run_bim_agent import Toolkit, serve
from src.agent.geometry.source_naming import build_public_names
from tests.test_bim_agent_tools import _run_with_one_image, _two_room_proposal
from tests.test_source_naming import source


def server(run, **kwargs):
    servers = []
    with patch.object(FastMCP, 'run', lambda s: servers.append(s)):
        serve(run, **kwargs)
    return servers[0]


def test_default_readonly_and_coordinator_hide_replay_handlers(tmp_path):
    run = _run_with_one_image(tmp_path)
    for readonly in (False, True):
        full = asyncio.run(server(run, readonly=readonly).list_tools())
        visible = asyncio.run(server(run, readonly=readonly, enabled_only=True).list_tools())
        assert not {t.name for t in visible} & REPLAY_ONLY_TOOLS
        assert [t.name for t in visible] == [t['name'] for t in filter_tool_catalog(
            [t.model_dump(mode='json', by_alias=True) for t in full])]
        assert {'pixel_profile', 'preview_space_trace', 'view_space_trace', 'select_space_trace'} <= {t.name for t in full}


def test_profile_without_picture_has_identical_measured_values_and_saved_ids(tmp_path):
    run = _run_with_one_image(tmp_path)
    api = server(run, enabled_only=True)
    name = next(iter(Toolkit(run).manifest['images']))
    args = dict(name=name, box=[0, 0, 4, 4], axis='x', rgb=[0, 0, 0])
    image_reply = asyncio.run(api.call_tool('view_pixel_profile', args))
    text_reply = asyncio.run(api.call_tool('view_pixel_profile', {**args, 'include_image': False}))
    assert not getattr(image_reply, 'isError', False) and not getattr(text_reply, 'isError', False)
    image_blocks = getattr(image_reply, 'content', image_reply)
    text_blocks = getattr(text_reply, 'content', text_reply)
    assert any(b.type == 'image' for b in image_blocks)
    assert all(b.type != 'image' for b in text_blocks)
    first, second = [json.loads(p.read_text()) for p in sorted((run/'pixel_profiles').glob('profile_*.json'))]
    for key in ('matching_pixels', 'candidates', 'cross_axis_profile', 'threshold_excluded_support', 'crop_context'):
        assert first[key] == second[key]
    assert second['profile_id'] != first['profile_id']


def test_saved_claim_view_routes_to_the_existing_hash_checked_reader(tmp_path):
    run = _run_with_one_image(tmp_path)
    api = server(run, enabled_only=True)
    from mcp.types import CallToolResult, TextContent
    reply = CallToolResult(content=[TextContent(type='text', text='saved evidence')])
    with patch.object(Toolkit, 'view_claim_evidence', return_value=reply) as read:
        result = asyncio.run(api.call_tool('view_image', dict(claim_id='claim_0001', source_index=2, display_scale=3)))
    assert not result.isError
    read.assert_called_once_with('claim_0001', 2, 3)
    name = next(iter(Toolkit(run).manifest['images']))
    bad = asyncio.run(api.call_tool('view_image', dict(claim_id='claim_0001', name=name)))
    assert bad.isError


def test_merged_candidate_view_and_annotated_position_use_saved_source(tmp_path):
    run = _run_with_one_image(tmp_path)
    toolkit = Toolkit(run)
    built = toolkit.build(json.loads(_two_room_proposal()))
    candidate = built['candidate']
    path = run/candidate/'source_model.json'
    before = path.read_bytes()
    api = server(run, enabled_only=True)
    reply = asyncio.run(api.call_tool('inspect_candidate', dict(candidate=candidate, include_plan=True)))
    assert not reply.isError and any(b.type == 'image' for b in reply.content)
    assert reply.structuredContent['source_plan_view']['candidate'] == candidate
    position = dict(id='p', boundary_id='space/left/wall/1', axis='x', lengths=[2900],
        unit='mm', origin_m=0, direction=1, node=1, offset_m=0,
        basis='synthetic labelled representative plane', source_refs=['plan.png: 2900'])
    reply = asyncio.run(api.call_tool('check_wall_dimensions', dict(candidate=candidate,
        positions_json=json.dumps([position]))))
    assert not getattr(reply, 'isError', False)
    report = json.loads(getattr(reply, 'content', reply)[0].text)['wall_placement']
    assert report['total'] == 1 and report['items'][0]['deviation_m'] == .1
    assert path.read_bytes() == before


def test_row_order_is_stable_across_rounding_boundaries_and_input_order():
    s = source()
    # Match the half-micro rounding boundary that reordered run99's north row.
    for room in s['spaces']:
        jitter = 0.00000000001 if room['id'] == 'east' else 0
        room['polygon'] = [[x, y + 2.5336925 + jitter] for x, y in room['polygon']]
    before = copy.deepcopy(s)
    result = build_public_names(s)
    assert result['spaces']['west'].startswith('Z01_F1_')
    assert result['spaces']['east'].startswith('Z02_F1_')
    assert s == before
    s['spaces'].reverse()
    assert build_public_names(s) == result


def test_centroid_rows_do_not_chain_across_more_than_tolerance():
    from src.agent.geometry.source_naming import _ordered_spaces
    from shapely.geometry import box
    rows = [{'id': key, 'floor_id': 'f'} for key in ('north', 'middle', 'south')]
    polygons = {key: box(x, y, x+1, y+1) for key,x,y in
                [('north',10,1.0000018), ('middle',5,1.0000009), ('south',0,1.0)]}
    ordered = _ordered_spaces(rows, polygons, {'f': 0})
    assert [s['id'] for s in ordered] == ['middle', 'north', 'south']
