"""Offline MCP replay of two unchanged real model declarations that failed hosting."""
import asyncio
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from tests.test_bim_agent_tools import _server_session, _json_result

ORIGINAL = HERE.parent / '2026-09-20_sm24_method_transfer_run01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


async def main():
    run = HERE / 'replay'
    (run / 'images').mkdir(parents=True, exist_ok=False)
    image_name = '1f_view.png'
    image_path = run / 'images' / image_name
    shutil.copy2(ORIGINAL / 'images' / image_name, image_path)
    with Image.open(image_path) as original_image:
        image_size = list(original_image.size)
    dump(run / 'inputs.json', {
        'scope': 'Offline unchanged failing-declaration replay; no model invocation',
        'images': {image_name: {'size': image_size, 'sha256': sha(image_path)}},
        'only_input': 'Frozen original plan and failed model declarations, no GT',
        'implementation_sha256': {name: sha(REPO / name) for name in (
            'scripts/tool_scripts/run_bim_agent.py',
            'src/agent/geometry/plan_partition.py',
            'src/agent/geometry/plan_draft_view.py')},
    })
    rows = []
    async with _server_session(run, readonly=False) as session:
        for draft in ('draft_003', 'draft_004'):
            folder = ORIGINAL / 'plan_drafts' / draft
            raw = (folder / 'plan.json').read_text()
            before_sha = sha(folder / 'plan.json')
            old = json.loads((folder / 'result.json').read_text())
            reply = await session.call_tool('build_plan_bim', {'image': image_name, 'plan_json': raw})
            result = _json_result(reply)
            assert result['status'] == 'error' and result['error'] == old['error']
            assert result['source_geometry_ready'] is False
            record = result['plan_input']
            assert (run / record['plan_file']).read_text() == raw
            images = [block for block in reply.content if block.type == 'image']
            assert len(images) == 2
            view = record['host_failure_view']
            metadata = view['metadata']
            assert metadata == json.loads((run / view['metadata_file']).read_text())
            assert metadata['image']['sha256'] == sha(image_path)
            assert metadata['plan']['sha256'] == before_sha
            assert sha(run / view['image_file']) == view['image_sha256']
            returned = Image.open(io.BytesIO(base64.b64decode(images[1].data))).convert('RGB')
            saved = Image.open(run / view['image_file']).convert('RGB')
            assert returned.size == saved.size and ImageChops.difference(returned, saved).getbbox() is None
            assert max(returned.size) <= 1600
            clean = Image.open(image_path).convert('RGB').crop(tuple(metadata['crop_original_pixels']))
            clean = clean.resize(tuple(metadata['panel_size_pixels']), Image.Resampling.NEAREST)
            actual = returned.crop(tuple(metadata['panels']['clean_original']))
            assert actual.size == clean.size and ImageChops.difference(actual, clean).getbbox() is None
            assert sha(folder / 'plan.json') == before_sha
            rows.append({'original_draft': draft, 'original_plan_sha256': before_sha,
                         'original_declaration_unchanged': True, 'error_unchanged': True,
                         'error': result['error'], 'mcp_returned_images': len(images),
                         'local_image_pixels_match_saved': True, 'clean_panel_pixels_match_original': True,
                         'metadata_returned_to_model': True, 'image_size': list(returned.size),
                         'host_failure_view': view})
    assert not list(run.glob('candidate_*'))
    assert not (run / 'overlay_calibrations').exists()
    dump(HERE / 'verification.json', {
        'mode': 'offline_real_failed_declaration_replay', 'model_calls': 0,
        'new_candidates': 0, 'no_calibration_registered': True, 'cases': rows,
        'limit': 'Shows correct failure evidence delivery, not working-model interpretation or recovery',
    })
    print(json.dumps({'real_failures_replayed': len(rows), 'model_calls': 0, 'result': 'pass'}))


if __name__ == '__main__':
    asyncio.run(main())
