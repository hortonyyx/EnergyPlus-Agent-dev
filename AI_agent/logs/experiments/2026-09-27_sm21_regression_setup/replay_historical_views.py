"""Compare current view rendering with bytes actually seen in historical runs."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import tempfile

from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from .preflight import RUNS

HERE = Path(__file__).resolve().parent


def main():
    results = []
    for name in RUNS:
        run = HERE.parent / name
        calls, views = {}, []
        # Primary turns only: isolate image rendering before any continuation.
        for line in gzip.decompress((run / 'agent_stream.jsonl.gz').read_bytes()).splitlines():
            content = json.loads(line).get('message', {}).get('content', [])
            for block in content if isinstance(content, list) else []:
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block
                if block.get('type') != 'tool_result' or block.get('is_error'):
                    continue
                call = calls.get(block['tool_use_id'], {})
                if not call.get('name', '').endswith('__view_image'):
                    continue
                parts = block.get('content', [])
                images = [p for p in parts if p.get('type') == 'image']
                assert len(images) == 1
                views.append((call['input'], base64.b64decode(images[0]['source']['data'])))
        with tempfile.TemporaryDirectory(prefix='bim-view-replay-') as tmp:
            out = Path(tmp)
            (out / 'images').symlink_to(run / 'images', target_is_directory=True)
            (out / 'inputs.json').write_bytes((run / 'inputs.json').read_bytes())
            toolkit = Toolkit(out)
            rows = []
            for params, actual in views:
                picture, _ = toolkit.view(**params)
                replay = base64.b64decode(picture.to_image_content().data)
                assert actual == replay, (name, params)
                rows.append(dict(parameters=params, bytes_identical=True,
                    actual_png_sha256=hashlib.sha256(actual).hexdigest()))
            results.append(dict(run=name, views=rows, primary_view_count=len(rows)))
    dump(HERE / 'historical_view_replay.json', dict(results=results,
        total=sum(r['primary_view_count'] for r in results), bytes_exact=True,
        limit='Original view-image rendering only. Model interpretation, profiles and generated feedback are separate.'))
    print('Historical image returns exactly replayed:', sum(r['primary_view_count'] for r in results))


if __name__ == '__main__':
    main()
