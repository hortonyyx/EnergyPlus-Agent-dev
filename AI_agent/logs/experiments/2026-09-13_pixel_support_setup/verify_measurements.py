"""Post-invocation measurement/source-image transport checks; no semantic verdict."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path
from PIL import Image, ImageChops


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(run):
    assert (run/'response.json').exists() or (run/'summary.json').exists(), 'wait for generation to finish'
    reports = []
    for workspace in [run, *sorted(p for p in run.glob('detail_*') if p.is_dir())]:
        if not (workspace/'inputs.json').exists():
            continue
        manifest = json.loads((workspace/'inputs.json').read_text())
        for path in sorted((workspace/'pixel_profiles').glob('*.json')):
            record = json.loads(path.read_text())
            original = workspace/'images'/record['name']
            assert sha(original) == record['image_sha256'] == manifest['images'][record['name']]['sha256']
            pic = Image.open(original).convert('RGB')
            x0,y0,x1,y1 = record['box_original_pixels']
            crop = pic.crop((x0,y0,x1,y1))
            saved_path = workspace/record['profile_image']
            saved = Image.open(saved_path).convert('RGB')
            assert sha(saved_path) == record['profile_image_sha256']
            assert ImageChops.difference(saved.crop((0,0,crop.width,crop.height)), crop).getbbox() is None
            for candidate in record['candidates']:
                peak = candidate['peak']
                axis = record['axis']
                actual = []
                for other in range(y0 if axis=='x' else x0, y1 if axis=='x' else x1):
                    color = pic.getpixel((peak,other) if axis=='x' else (other,peak))
                    if sum((a-b)**2 for a,b in zip(color,record['rgb'])) <= record['tolerance']**2:
                        actual.append(other)
                claimed = [p for lo,hi in candidate['support_intervals_at_peak'] for p in range(lo,hi+1)]
                assert actual == claimed and len(actual) == candidate['max_count']
            reports.append({'workspace': str(workspace.relative_to(run)), 'record': path.name,
                'candidates': len(record['candidates']), 'original_hash_and_crop_match': True,
                'support_intervals_match_original_pixels': True})
    image_checks = []
    for stream in [*run.glob('*_stream.jsonl'), *run.glob('*_stream.jsonl.gz')]:
        raw = gzip.decompress(stream.read_bytes()).decode() if stream.suffix=='.gz' else stream.read_text()
        workspace = run/stream.name.split('_stream')[0] if stream.name.startswith('detail_') else run
        calls = {}
        for line in raw.splitlines():
            event = json.loads(line)
            for block in event.get('message',{}).get('content',[]):
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block
                if block.get('type') != 'tool_result' or block.get('is_error'):
                    continue
                call = calls.get(block.get('tool_use_id'),{})
                if not call.get('name','').endswith('__view_pixel_profile'):
                    continue
                blocks = block['content']
                meta = json.loads(next(b['text'] for b in blocks if b['type']=='text'))
                img = next(b for b in blocks if b['type']=='image')
                actual = Image.open(io.BytesIO(base64.b64decode(img['source']['data']))).convert('RGB')
                expected = Image.open(workspace/meta['profile_image']).convert('RGB')
                expected.thumbnail((1600,1600))
                assert actual.size == expected.size and ImageChops.difference(actual,expected).getbbox() is None
                assert json.loads((workspace/meta['profile_record']).read_text()) == meta
                image_checks.append({'stream': stream.name, 'profile':meta['profile_record'], 'pixels_and_metadata_match': True})
    result = {'measured_profiles': reports, 'returned_profile_images': image_checks,
        'scope': 'Source hashes, untouched crop, actual peak support, saved/returned image and metadata. No wall/door semantic validation.'}
    (run/'measurement_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'profiles':len(reports),'returned_images':len(image_checks)}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    verify(parser.parse_args().run.resolve())
