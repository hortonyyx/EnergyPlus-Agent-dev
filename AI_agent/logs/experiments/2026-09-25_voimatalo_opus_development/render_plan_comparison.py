"""Old/new source-model plan cuts at chosen heights, side by side.

Both panels are drawn from the saved source models only (spaces active at the
cut height, openings whose z-range contains it, declared unknown/open wall
regions).  Colours encode the declared role category, not observed use.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon

CATEGORIES = [
    ('vertical_circulation', '#d9b98c', 'stair / lift core'),
    ('stair_landing', '#e8cfa6', 'stair landing'),
    ('corridor', '#f3eab0', 'corridor'),
    ('entrance', '#f6c9a6', 'entrance / lobby'),
    ('service', '#bfd8b0', 'WC / service'),
    ('back_of_house', '#cfe0c4', 'back of house'),
    ('corner_office', '#b9cde8', 'corner / meeting'),
    ('office', '#d7e3f2', 'office band (merged cells)'),
    ('retail', '#f0d6e6', 'retail'),
    ('annex', '#d6d2ec', 'annex hall'),
    ('commercial', '#f0d6e6', 'commercial (old)'),
    ('roof', '#e4dde9', 'roof part'),
]


def category(role: str):
    for key, colour, label in CATEGORIES:
        if key in role:
            return colour, label
    return '#eeeeee', 'other'


def font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def panel(source: dict, z: float, title: str, bounds, size=(760, 1060)) -> Image.Image:
    width, height = size
    image = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(image)
    (x0, y0), (x1, y1) = bounds
    margin = 40
    scale = min((width - 2 * margin) / (x1 - x0), (height - 2 * margin - 60) / (y1 - y0))

    def pt(p):
        return (margin + (p[0] - x0) * scale, height - margin - (p[1] - y0) * scale)

    draw.text((12, 8), title, fill='black', font=font(17))
    draw.text((12, 32), f'source cut z = {z:g} m (spaces active at this height)', fill='#444', font=font(13))
    active = [s for s in source['spaces'] if s['z_floor'] <= z < s['z_floor'] + s['height']]
    legend = {}
    for space in active:
        colour, label = category(space.get('role', ''))
        legend[label] = colour
        draw.polygon([pt(p) for p in space['polygon']], fill=colour, outline='#2c3e50', width=2)
    for space in active:
        poly = Polygon(space['polygon'])
        c = poly.representative_point()
        name = space['id'].split('_', 1)[1] if space['id'].startswith('F') else space['id']
        draw.text(pt((c.x, c.y)), name, fill='black', anchor='mm', font=font(11))
    unknown = []
    for boundary in source['boundaries']:
        if boundary['geometry_type'] != 'wall' or boundary['space_id'] not in {s['id'] for s in active}:
            continue
        for region in boundary.get('enclosure_regions', []):
            v = np.asarray(region['vertices'], float)
            if v[:, 2].min() - 1e-6 <= z <= v[:, 2].max() + 1e-6:
                ends = sorted({(round(a, 4), round(b, 4)) for a, b in v[:, :2]})
                if len(ends) >= 2:
                    unknown.append((ends[0], ends[-1], region['condition']))
    for a, b, condition in unknown:
        draw.line([pt(a), pt(b)], fill='#9b59b6' if condition == 'unknown' else '#16a085', width=7)
    for opening in source['openings']:
        v = np.asarray(opening['vertices'], float)
        if v[:, 2].min() <= z <= v[:, 2].max():
            ends = np.unique(np.round(v[:, :2], 6), axis=0)
            if len(ends) == 2:
                colour = '#12805c' if opening['kind'] == 'window' else '#d35400'
                draw.line([pt(ends[0]), pt(ends[1])], fill=colour, width=5)
    counts = {'spaces': len(active),
              'windows': sum(1 for o in source['openings'] if o['kind'] == 'window' and min(p[2] for p in o['vertices']) <= z <= max(p[2] for p in o['vertices'])),
              'doors': sum(1 for o in source['openings'] if o['kind'] == 'door' and min(p[2] for p in o['vertices']) <= z <= max(p[2] for p in o['vertices']))}
    draw.text((12, 50), f"{counts['spaces']} spaces cut · {counts['windows']} windows · {counts['doors']} doors at this height",
              fill='#444', font=font(13))
    y = height - 20 - 16 * len(legend)
    for label, colour in legend.items():
        draw.rectangle([width - 250, y, width - 236, y + 12], fill=colour, outline='#2c3e50')
        draw.text((width - 230, y - 1), label, fill='black', font=font(12))
        y += 16
    draw.line([(12, height - 60), (22, height - 60)], fill='#12805c', width=5)
    draw.text((26, height - 67), 'window', fill='black', font=font(12))
    draw.line([(12, height - 44), (22, height - 44)], fill='#d35400', width=5)
    draw.text((26, height - 51), 'door', fill='black', font=font(12))
    draw.line([(12, height - 28), (22, height - 28)], fill='#9b59b6', width=5)
    draw.text((26, height - 35), 'unknown enclosure', fill='black', font=font(12))
    return image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old', type=Path, required=True)
    parser.add_argument('--new', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--z', type=float, action='append', required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    old = json.loads(args.old.read_text())
    new = json.loads(args.new.read_text())
    points = np.asarray([p for s in new['spaces'] for p in s['polygon']], float)
    bounds = (points.min(axis=0) - 1.0, points.max(axis=0) + 1.0)
    written = []
    for z in args.z:
        left = panel(old, z, 'OLD candidate_04 (09-16, user rejected)', bounds)
        right = panel(new, z, 'NEW 09-25 development candidate', bounds)
        both = Image.new('RGB', (left.width + right.width + 10, left.height), '#888888')
        both.paste(left, (0, 0))
        both.paste(right, (left.width + 10, 0))
        path = args.out / f'plan_compare_z{z:g}.png'
        both.save(path)
        written.append(path.name)
    (args.out / 'plan_compare.json').write_text(json.dumps({
        'old_source_model_sha256': old['source_model_sha256'], 'new_source_model_sha256': new['source_model_sha256'],
        'heights_m': args.z, 'images': written,
        'scope': 'Derived drawings of saved source models; colours encode declared role categories, not observed use.'},
        indent=2) + '\n')
    print(written)


if __name__ == '__main__':
    main()
