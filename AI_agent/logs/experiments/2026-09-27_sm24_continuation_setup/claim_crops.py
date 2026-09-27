"""Expose exactly the recorded claim regions for post-generation human inspection."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.tool_scripts.run_bim_agent import digest, dump


def main(run):
    assert (run / 'summary.json').is_file()
    folder = run / 'evaluation/claim_crops'
    folder.mkdir(exist_ok=True)
    rows, tiles = [], []
    for path in sorted((run / 'claims').glob('claim_*.json')):
        claim = json.loads(path.read_text())
        for index, ref in enumerate(claim['sources'], 1):
            original = run / 'images' / ref['image']
            assert digest(original) == ref['sha256']
            box = [int(v) for v in ref['box']]
            with Image.open(original) as image:
                assert all(float(a) == b for a, b in zip(ref['box'], box))
                assert 0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height
                crop = image.crop(box).convert('RGB')
            name = f'{claim["id"]}_{index}_{Path(ref["image"]).stem}.png'
            crop.save(folder / name)
            tile = Image.new('RGB', (600, 440), '#eeeeee')
            draw = ImageDraw.Draw(tile)
            draw.text((10, 8), f'{claim["id"]} / {ref["image"]} / {box}', fill='black')
            draw.text((10, 25), str(claim['resolved_values']), fill='black')
            crop.thumbnail((580, 380))
            tile.paste(crop, ((600 - crop.width)//2, 55))
            tiles.append(tile)
            rows.append(dict(claim=claim['id'], image=ref['image'], original_box=box,
                crop=f'claim_crops/{name}', image_sha256=ref['sha256'], resolved=claim['resolved_values']))
    sheet = Image.new('RGB', (1800, 440*((len(tiles)+2)//3)), 'white')
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 3)*600, (index // 3)*440))
    sheet.save(folder / 'all_claim_regions.png')
    dump(run / 'evaluation/claim_crop_audit.json', dict(rows=rows,
        original_hashes_and_bounds_verified=True, semantic_status='requires_manual_review',
        note='Exact declared claim regions; the generator saw whole originals. This view neither adds evidence nor corrects claims.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    main(parser.parse_args().run.resolve())
