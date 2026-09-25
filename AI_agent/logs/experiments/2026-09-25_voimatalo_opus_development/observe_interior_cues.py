"""Close textured views for interior-organisation cues (09-25 Opus development).

Reads only the supplied single-building GLB. Views reuse the frozen 09-15 frame
(yaw 14.887 deg, zero translation). Each PNG gets a companion ``*_grid.png``
with BIM-local metre ticks so facade features can be read in plan/height
coordinates. Grid lines are projection annotations, not measured walls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation

MESH = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb'
YAW = 14.887066917997172

# name, eye, target, width_m, height_m, selection bounds, (horizontal axis, tick range)
VIEWS = [
    # Street facade, south half: vertical glazed strip and blank band near the south end.
    ('west_south', [-100, -21, 15], [0, -21, 15], 26, 34, None),
    # Street facade, north half incl. north-west corner.
    ('west_north', [-100, 12, 15], [0, 12, 15], 30, 34, None),
    # Courtyard long wall, south part (annex excluded by bounds so the wall is visible).
    ('court_long_south', [100, -22, 15], [0, -22, 15], 26, 34, [[-25, -40, -1], [3.5, -14, 40]]),
    # Courtyard long wall north part, behind the annex (annex faces excluded).
    ('court_long_north', [100, 0, 15], [0, 0, 15], 24, 34, [[-25, -22, 7.0], [3.5, 12, 40]]),
    # Inner corner / short courtyard facade.
    ('court_short_corner', [6, -100, 15], [6, 10, 15], 18, 34, [[-2, 5, -1], [22, 30, 40]]),
    # Oblique from the courtyard towards the south-east part of the long wing (cropped protrusion).
    ('court_southeast_oblique', [60, -70, 30], [0, -24, 14], 30, 34, None),
    # South short end of the long wing.
    ('south_end', [-6, -100, 15], [-6, 0, 15], 22, 34, None),
    # East short end of the short wing.
    ('east_end', [100, 17, 15], [0, 17, 15], 22, 34, [[10, 5, -1], [25, 30, 40]]),
    # Top view with metre grid.
    ('top_grid', [2, -3, 110], [2, -3, 15], 40, 64, None),
    # High-resolution strips used by measure_band_windows.py and the stair reading.
    ('west_band_hi', [-100, -24.5, 15.5], [0, -24.5, 15.5], 8, 20, None),
    ('west_strip_hi', [-100, -30, 16], [0, -30, 16], 6, 14, None),
    ('court_strip_hi', [100, -27, 16], [0, -27, 16], 6, 14, [[-25, -40, -1], [3.5, -14, 40]]),
]
# Queryable pixel buffers kept for the depth / window claims; the others are
# deleted after rendering (deterministically regenerable by rerunning).
KEEP_BUFFERS = {'court_long_south', 'west_band_hi', 'court_strip_hi'}


def draw_grid(image: Image.Image, meta: dict, step: float = 1.0) -> Image.Image:
    mapping = meta['pixel_center_mapping']
    tl = np.array(mapping['top_left_pixel_center_plane_xyz'])
    cs = np.array(mapping['column_step_world_xyz'])
    rs = np.array(mapping['row_step_world_xyz'])
    w, h = image.size
    out = image.convert('RGB').copy()
    d = ImageDraw.Draw(out)
    # Horizontal screen axis in world, vertical screen axis in world.
    ch = cs / np.linalg.norm(cs)
    rh = rs / np.linalg.norm(rs)
    for axis_vec, step_vec, n, vertical in ((ch, cs, w, True), (rh, rs, h, False)):
        comp = int(np.argmax(np.abs(axis_vec)))
        if abs(axis_vec[comp]) < 0.999:
            continue  # oblique axis: skip grid
        start = tl[comp]
        stop = tl[comp] + step_vec[comp] * (n - 1)
        lo, hi = sorted([start, stop])
        for value in np.arange(np.ceil(lo / step) * step, hi, step):
            px = (value - start) / step_vec[comp]
            major = abs(value / 5 - round(value / 5)) < 1e-6
            colour = (220, 30, 30) if major else (255, 160, 60)
            if vertical:
                d.line([(px, 0), (px, h)], fill=colour, width=1)
                if major:
                    d.text((px + 2, 2), f"{'xyz'[comp]}{value:g}", fill=(200, 0, 0))
            else:
                d.line([(0, px), (w, px)], fill=colour, width=1)
                if major:
                    d.text((2, px + 1), f"{'xyz'[comp]}{value:g}", fill=(200, 0, 0))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists(), 'Use a new output directory'
    args.out.mkdir(parents=True)
    mesh = MeshObservation(MESH)
    records = []
    for name, eye, target, width, height, bounds in VIEWS:
        scale = 1400 / max(width, height)
        image, meta = mesh.render(args.out / name, eye=eye, target=target, width_m=width, height_m=height,
                                  width_px=round(width * scale), height_px=round(height * scale),
                                  yaw_degrees=YAW, bounds=bounds)
        draw_grid(image, meta).save(args.out / f'{name}_grid.png')
        if name not in KEEP_BUFFERS:
            (args.out / f'{name}.npz').unlink()
        records.append({'name': name, 'eye': eye, 'target': target, 'span_m': [width, height],
                        'selection_bounds': bounds, 'camera': meta['camera'],
                        'pixel_buffer_retained': name in KEEP_BUFFERS})
        print('saved', name, flush=True)
    manifest = {'mesh_sha256': mesh.mesh_sha256, 'yaw_degrees': YAW,
                'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'mode': 'development assistant observation for interior organisation cues; no model call',
                'inputs': 'input.glb only; no parent tile, OSM, GT or interior drawings',
                'views': records,
                'caveat': 'Grid lines are orthographic projection ticks; texture reading is developer judgement.'}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
