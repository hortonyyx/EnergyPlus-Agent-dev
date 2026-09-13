"""Original-bound overview transport through both MCP surfaces."""
import asyncio
import base64
import json
from tests.test_bim_agent_tools import _run_with_one_image, _server_session
from scripts.tool_scripts.run_bim_agent import digest


def test_overview_saved_response_and_source_isolation(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        original_hash = digest(run/'images/plan.png')
        for readonly in (True, False):
            async with _server_session(run, readonly=readonly) as session:
                result = await session.call_tool('view_pixel_region_overview', {
                    'name': 'plan.png', 'background_rgb': [255,255,255],
                    'tolerance': 0, 'min_pixels': 1, 'include_border': True})
                assert not result.isError
                metadata = json.loads(result.content[1].text)
                assert metadata['image_sha256'] == original_hash
                image_path = run/metadata['overview_image']
                assert base64.b64decode(result.content[0].data) == image_path.read_bytes()
                assert json.loads(image_path.with_suffix('.json').read_text()) == metadata
                assert digest(run/'images/plan.png') == original_hash
                assert not list(run.glob('candidate_*'))
                rejected = await session.call_tool('view_pixel_region_overview', {
                    'name': '../not-selected.png', 'background_rgb':[255,255,255]})
                assert rejected.isError
    asyncio.run(scenario())
