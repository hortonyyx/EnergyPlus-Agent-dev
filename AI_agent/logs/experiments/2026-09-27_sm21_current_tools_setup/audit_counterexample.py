"""A failed claim call stays recorded; a changed successful image still fails."""
from pathlib import Path
import base64
import gzip
import importlib
import io
import json
import shutil
import tempfile

from PIL import Image

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / '2026-09-27_sm21_candidate_budget_claude_run70'


def main():
    module = importlib.import_module('AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.claim_crops')
    with tempfile.TemporaryDirectory(prefix='claim-transport-negative-') as td:
        copy = Path(td) / 'run'
        shutil.copytree(RUN, copy, ignore=shutil.ignore_patterns(
            'evaluation', 'browser_qa', 'runtime_snapshot', 'candidate_*', 'seed'))
        (copy / 'evaluation').mkdir()
        module.audit(copy)  # The same reduced fixture must pass before corruption.
        path = copy / 'agent_stream.jsonl.gz'
        events = [json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]
        calls, changed = {}, False
        for event in events:
            blocks = event.get('message', {}).get('content', [])
            for block in blocks if isinstance(blocks, list) else []:
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block['name']
                if (block.get('type') != 'tool_result' or block.get('is_error')
                        or not calls.get(block.get('tool_use_id'), '').endswith('record_claim')):
                    continue
                for part in block['content']:
                    if part.get('type') != 'image' or changed:
                        continue
                    image = Image.open(io.BytesIO(base64.b64decode(part['source']['data']))).convert('RGB')
                    image.putpixel((0, 0), tuple(255 - value for value in image.getpixel((0, 0))))
                    buf = io.BytesIO()
                    image.save(buf, format='PNG')
                    part['source']['data'] = base64.b64encode(buf.getvalue()).decode()
                    changed = True
        assert changed
        path.write_bytes(gzip.compress(b'\n'.join(json.dumps(event).encode() for event in events) + b'\n'))
        try:
            module.audit(copy)
        except AssertionError as error:
            import traceback
            assert 'actual.size == expected.size' in traceback.extract_tb(error.__traceback__)[-1].line
            rejected = True
        else:
            raise AssertionError('Altered actual image was incorrectly accepted')
    transport = json.loads((RUN / 'evaluation/claim_transport_audit.json').read_text())
    assert len(transport['failed_returns']) == 1 and transport['image_count'] == 8
    validation = json.loads((HERE / 'validation.json').read_text())
    validation['claim_transport_error_handling'] = dict(
        actual_failed_record_claim_preserved=1, run70_successful_claim_previews_checked=8,
        run70_original_view_png_and_pixels_checked=33,
        one_pixel_corruption_rejected_in_temporary_copy=rejected,
        production_runtime_changed=False)
    (HERE / 'validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
    print('Audit preserves failed tool return; one-pixel corruption of successful claim image is rejected.')


if __name__ == '__main__':
    main()
