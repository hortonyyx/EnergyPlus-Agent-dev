"""Post-run exact claim crops and actual MCP image-return comparison; no OCR."""
import argparse
import base64
import gzip
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump


def audit(run):
    assert (run / 'summary.json').is_file()
    folder = run / 'evaluation/claim_crops'
    folder.mkdir(exist_ok=True)
    rows, sheets = [], []
    for path in sorted((run / 'claims').glob('claim_*.json')):
        claim = json.loads(path.read_text())
        tiles = []
        for index, ref in enumerate(claim['sources']):
            original = run / 'images' / ref['image']
            assert digest(original) == ref['sha256']
            left, top, right, bottom = ref['box']
            box = [math.floor(left), math.floor(top), math.ceil(right), math.ceil(bottom)]
            with Image.open(original) as image:
                crop = image.crop(box).convert('RGB')
            name = f'{claim["id"]}_{index}_{Path(ref["image"]).stem}.png'
            crop.save(folder / name)
            tile = Image.new('RGB', (700, 500), '#eeeeee')
            draw = ImageDraw.Draw(tile)
            draw.text((10, 8), f'{claim["id"]} / source {index} / {ref["image"]}', fill='black')
            draw.text((10, 25), str(box) + ' / ' + str(claim['resolved_values']), fill='black')
            crop.thumbnail((680, 440))
            tile.paste(crop, ((700 - crop.width)//2, 55))
            tiles.append(tile)
            rows.append(dict(claim=claim['id'], source_index=index, image=ref['image'],
                claimed_box=ref['box'], rendered_box=box, crop=f'claim_crops/{name}',
                image_sha256=ref['sha256'], resolved=claim['resolved_values']))
        if tiles:
            sheet = Image.new('RGB', (700 * min(3, len(tiles)), 500 * ((len(tiles)+2)//3)), 'white')
            for index, tile in enumerate(tiles):
                sheet.paste(tile, ((index % 3)*700, (index // 3)*500))
            name = f'{claim["id"]}_sheet.png'
            sheet.save(folder / name)
            sheets.append(f'claim_crops/{name}')
    dump(run / 'evaluation/claim_crop_audit.json', dict(rows=rows, sheets=sheets,
        original_hashes_verified=True, semantic_status='requires_manual_review',
        note='Saved original regions only. Correction and image understanding are reviewed separately.'))

    returned, calls = [], {}
    for stream in sorted(run.glob('*_stream.jsonl.gz')):
        for line in gzip.decompress(stream.read_bytes()).splitlines():
            event = json.loads(line)
            content = event.get('message', {}).get('content', [])
            for block in content if isinstance(content, list) else []:
                if block.get('type') == 'tool_use':
                    calls[block['id']] = block['name']
                tool = calls.get(block.get('tool_use_id'), '')
                if block.get('type') != 'tool_result' or not tool.endswith(('record_claim', 'view_claim_evidence')):
                    continue
                parts = block.get('content', [])
                assert isinstance(parts, list) and not block.get('is_error'), block
                pictures, metadata, structured_previews = [], [], []
                for part in parts:
                    if part.get('type') == 'image':
                        pictures.append(part)
                    elif part.get('type') == 'text':
                        try:
                            data = json.loads(part['text'])
                        except ValueError:
                            continue
                        if 'claim_id' in data and 'source_index' in data and 'box_original_pixels' in data:
                            metadata.append(data)
                        if 'evidence_previews' in data:
                            structured_previews = data['evidence_previews']
                # Claude CLI keeps images but replaces individual text blocks with
                # structuredContent. Raw MCP stdio returns both representations.
                if not metadata:
                    metadata = structured_previews
                assert len(pictures) == len(metadata)
                for picture, meta in zip(pictures, metadata):
                    saved = Toolkit(run).claims().read(meta['claim_id'])['sources'][meta['source_index']]
                    assert saved['sha256'] == meta['image_sha256'] == digest(run / 'images' / meta['name'])
                    assert saved['box'] == meta['claimed_box_original_pixels']
                    with Image.open(run / 'images' / meta['name']) as image:
                        expected = image.convert('RGB').crop(meta['box_original_pixels'])
                    if meta['display_scale_requested'] == 1:
                        expected.thumbnail((1600, 1600))
                    else:
                        expected = expected.resize(tuple(meta['returned_size']), Image.Resampling.NEAREST)
                    actual = Image.open(io.BytesIO(base64.b64decode(picture['source']['data']))).convert('RGB')
                    assert actual.size == expected.size and actual.tobytes() == expected.tobytes()
                    returned.append(dict(stream=stream.name, tool=tool, claim=meta['claim_id'],
                        source_index=meta['source_index'], returned_size=list(actual.size), pixels_exact=True))
    assert returned, 'No actual claim previews arrived in the model stream'
    dump(run / 'evaluation/claim_transport_audit.json', dict(returned=returned,
        image_count=len(returned), actual_transport_pixels_match_saved_regions=True,
        note='Deterministic image-content check only, not annotation recognition or adoption acceptance.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
