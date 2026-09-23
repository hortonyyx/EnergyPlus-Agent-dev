"""Audit actual image transport and losslessly archive a completed model stream."""
import base64
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path

from PIL import Image


def finalize(run):
    assert (run / 'summary.json').is_file(), 'Wait for generation to finish'
    stream = run / 'agent_stream.jsonl'
    archive = stream.with_suffix('.jsonl.gz')
    raw = stream.read_bytes() if stream.exists() else gzip.decompress(archive.read_bytes())
    saved_pixels = {}
    for path in run.rglob('*.png'):
        if 'evaluation' in path.parts:
            continue
        with Image.open(path) as im:
            im = im.convert('RGB'); im.thumbnail((1600, 1600))
            key = hashlib.sha256(im.tobytes()).hexdigest()
            saved_pixels.setdefault(key, []).append(str(path.relative_to(run)))
    calls, images = {}, []
    for line in raw.splitlines():
        event = json.loads(line)
        content = event.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get('type') == 'tool_use':
                calls[block['id']] = block['name']
            elif block.get('type') == 'tool_result' and isinstance(block.get('content'), list):
                for item in block['content']:
                    if item.get('type') != 'image':
                        continue
                    data = base64.b64decode(item['source']['data'])
                    with Image.open(io.BytesIO(data)) as im:
                        im.load()
                        pixels = hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
                        images.append(dict(tool=calls[block['tool_use_id']], size=list(im.size),
                            sha256=hashlib.sha256(data).hexdigest(), pixels_sha256=pixels,
                            matching_saved_files=saved_pixels.get(pixels, [])))
    tool_rows = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
    result = dict(image_count=len(images), all_images_decode=True, images=images,
        tools=dict(Counter(row['action'] for row in tool_rows)),
        source_stream_sha256=hashlib.sha256(raw).hexdigest(),
        note='Matching uses actual RGB pixels after the runtime 1600px thumbnail. Original views with grids/crops need not have a saved PNG counterpart. Transport is not semantic acceptance.')
    (run / 'transport_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    compressed = gzip.compress(raw, mtime=0)
    assert gzip.decompress(compressed) == raw
    archive.write_bytes(compressed)
    (run / 'stream_archive.json').write_text(json.dumps(dict(original_filename=stream.name,
        original_sha256=hashlib.sha256(raw).hexdigest(), original_bytes=len(raw),
        gzip_file=archive.name, gzip_sha256=hashlib.sha256(compressed).hexdigest(),
        gzip_bytes=len(compressed), lossless_verified=True), indent=2)+'\n')
    if stream.exists():
        stream.unlink()
    print(json.dumps({k: v for k, v in result.items() if k != 'images'}, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    finalize(parser.parse_args().run.resolve())
