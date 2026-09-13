"""Drawing trace feedback catches a door-leaf endpoint used as an aperture."""
import asyncio
import json
from PIL import Image
from src.agent.geometry.space_trace import render_space_trace
from tests.test_bim_agent_tools import _run_with_one_image, _server_session, _error_text


def test_trace_keeps_ordered_jog_and_rejects_door_leaf_tip():
    picture=Image.new('RGB',(100,100),'black')
    args=dict(polygon_pixels=[[10,10],[90,10],[90,90],[30,90],[30,40],[10,40]],
              openings=[{'id':'door','p1':[50,10],'p2':[70,10]}],
              x_anchors=[[10,0],[90,8]],y_anchors=[[90,0],[10,8]],basis='synthetic observed footprint')
    _,valid=render_space_trace(picture,**args)
    assert valid['geometrically_executable']
    assert valid['world_polygon']==[[0,8],[8,8],[8,0],[2,0],[2,5],[0,5]]
    assert valid['world_openings'][0]['p2']==[6,8]
    args['openings']=[{'id':'door','p1':[50,10],'p2':[70,30]}]
    _,invalid=render_space_trace(picture,**args)
    assert not invalid['geometrically_executable']
    assert any('swing arc' in e for e in invalid['geometry_errors'])
    assert any('not fully on' in e for e in invalid['geometry_errors'])


def test_readonly_trace_selection_requires_executable_preview(tmp_path):
    async def scenario():
        run=_run_with_one_image(tmp_path)
        params=dict(name='plan.png', polygon_pixels=[[1,1],[10,1],[10,7],[1,7]],
                    openings=[{'id':'door','p1':[4,1],'p2':[6,3]}],
                    x_anchors=[[1,0],[10,9]],y_anchors=[[7,0],[1,6]],basis='synthetic')
        async with _server_session(run,readonly=True) as session:
            result=await session.call_tool('preview_space_trace',params)
            assert not result.isError and result.content[0].type=='image'
            meta=json.loads(result.content[1].text)
            assert not meta['geometrically_executable']
            assert 'geometry errors' in _error_text(await session.call_tool('select_space_trace',{'trace_id':meta['trace_id']}))
            params['openings'][0]['p2']=[6,1]
            result=await session.call_tool('preview_space_trace',params)
            meta=json.loads(result.content[1].text)
            viewed=await session.call_tool('view_space_trace',{'trace_id':meta['trace_id']})
            assert viewed.content[0].data == result.content[0].data
            chosen=await session.call_tool('select_space_trace',{'trace_id':meta['trace_id']})
            assert not chosen.isError
            assert json.loads((run/'trace_selection.json').read_text())['trace_id']==meta['trace_id']
            assert not list(run.glob('candidate_*'))
    asyncio.run(scenario())


def test_readonly_pixel_region_returns_saved_original_bound_candidate(tmp_path):
    async def scenario():
        run=_run_with_one_image(tmp_path)
        async with _server_session(run,readonly=True) as session:
            result=await session.call_tool('view_pixel_region',{'name':'plan.png','seed_pixel':[3,3],
                'background_rgb':[255,255,255],'tolerance':0})
            assert not result.isError and result.content[0].type=='image'
            meta=json.loads(result.content[1].text)
            assert meta['region_pixel_count']==96 and meta['touches_image_border']
            assert meta['bbox_px']==[0,0,12,8]
            assert (run/meta['region_image']).is_file()
            assert json.loads((run/'pixel_regions/region_001.json').read_text())==meta
            assert not list(run.glob('candidate_*'))
    asyncio.run(scenario())
