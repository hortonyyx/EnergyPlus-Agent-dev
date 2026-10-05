"""Existing tool paths expose A4-T diagnostics with immutable A3-T readback."""
import asyncio
import json

from tests.test_bim_agent_tools import _json_result, _run_with_one_image, _server_session
from tests.test_bim_agent_plan_partition import example


def test_save_and_delivery_diagnostics_use_existing_report_readback(tmp_path):
    async def scenario():
        run = _run_with_one_image(tmp_path)
        async with _server_session(run, readonly=False) as session:
            reply = _json_result(await session.call_tool('build_plan_bim',
                {'image':'plan.png','plan_json':json.dumps(example())}))
            report = json.loads((run/reply['details_file']).read_text())
            assert 'building_precision' in reply and 'building_precision' in report
            assert reply['building_precision']['counts'] == report['building_precision']['counts']
            assert reply['drawing_differences']['coverage']['not_checked']
            source = run/reply['candidate']/'source_model.json'
            raw = source.read_bytes()
            finish = _json_result(await session.call_tool('finish_bim',{'candidate':reply['candidate']}))
            assert source.read_bytes() == raw
            # Delivery's full report is reachable even when the handoff is short.
            full = json.loads((run/finish['details_file']).read_text())
            assert 'building_precision' in full
            page = _json_result(await session.call_tool('read_candidate_items',
                {'candidate':'','collection':'report','report_file':finish['details_file'],'limit':12000}))
            assert page['sha256'] == finish['details_sha256']
    asyncio.run(scenario())
