"""Measure the uninventoried street-side windows next to the south stair glazing.

The 09-15/09-16 inventory treats y -27.97..-21.14 on the street facade as
blank.  Close renders show a glazed column continuing the stair glazing on
every storey and a narrow column on the top storeys.  This script measures
them deterministically from ``observations/west_band_hi`` (texture colour
profiles against an adjacent wall reference) and checks that the window
centres hit the street facade plane.  Thresholds are stated below; reading
the texture as glass is still developer judgement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation

MESH = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb'
VIEW = HERE / 'observations/west_band_hi'
PARENT_PLAN = ROOT / 'AI_agent/logs/experiments/2026-09-16_voimatalo_completion/case_plan.json'
WEST_PLANE = -13.7
# The scanned street surface near the south end stands up to ~0.45 m proud of the
# regularised plane (09-16 'local forward surface' note); back-wall hits are ~14 m away.
PLANE_TOLERANCE_M = 0.6
EXISTING_STAIR_WINDOW_SOUTH_EDGE = -27.97  # west_corner_large rows, 09-16 inventory
COLUMNS = {
    # key: (sample y-range for the z profile, y search window for the span)
    'wide': ((-27.6, -26.3), (-28.2, -25.6)),
    'narrow': ((-24.8, -24.3), (-25.4, -23.6)),
}
WALL_REFERENCE = (-23.4, -22.6)
RB_DROP = 7.0      # window rows: red-minus-blue at least this much below the wall reference
LUM_DROP = 25.0    # ...or luminance at least this much below it (dark glazing)
MIN_RUN_M = 0.6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'observations/west_band_windows.json')
    args = parser.parse_args()
    assert not args.out.exists(), 'Use a new output path'
    image = np.asarray(Image.open(f'{VIEW}.png').convert('RGB')).astype(float)
    meta = json.loads(Path(f'{VIEW}.json').read_text())
    mapping = meta['pixel_center_mapping']
    tl = np.array(mapping['top_left_pixel_center_plane_xyz'])
    cs = np.array(mapping['column_step_world_xyz'])
    rs = np.array(mapping['row_step_world_xyz'])
    col = lambda y: int(round((y - tl[1]) / cs[1]))
    row = lambda z: int(round((z - tl[2]) / rs[2]))
    z_of = lambda r: float(tl[2] + r * rs[2])
    y_of = lambda c: float(tl[1] + c * cs[1])

    def profile(y_range, rows=None):
        c0, c1 = sorted([col(y_range[0]), col(y_range[1])])
        block = image[:, c0:c1 + 1, :] if rows is None else image[rows[0]:rows[1] + 1, c0:c1 + 1, :]
        return (block[..., 0] - block[..., 2]).mean(axis=1), block.mean(axis=(1, 2))

    wall_rb, wall_lum = profile(WALL_REFERENCE)
    levels = json.loads(PARENT_PLAN.read_text())['storey_levels_m']
    mesh = MeshObservation(MESH)
    windows, rejected = [], []
    for key, (sample, search) in COLUMNS.items():
        rb, lum = profile(sample)
        for number in range(2, 8):
            z0, z1 = levels[number - 1], levels[number]
            r_top, r_bottom = row(z1 - 0.3), row(z0 + 0.3)
            flags = [(rb[r] < wall_rb[r] - RB_DROP) or (lum[r] < wall_lum[r] - LUM_DROP) for r in range(r_top, r_bottom + 1)]
            runs, start = [], None
            for index, flag in enumerate(flags + [False]):
                if flag and start is None:
                    start = index
                elif not flag and start is not None:
                    runs.append((start, index - 1))
                    start = None
            if not runs:
                rejected.append({'column': key, 'storey': f'F{number}', 'reason': 'no window-like rows'})
                continue
            a, b = max(runs, key=lambda run: run[1] - run[0])
            z_hi, z_lo = z_of(r_top + a), z_of(r_top + b)
            if z_hi - z_lo < MIN_RUN_M:
                rejected.append({'column': key, 'storey': f'F{number}', 'reason': f'run {z_hi - z_lo:.2f} m shorter than {MIN_RUN_M} m'})
                continue
            # Horizontal extent at those rows, against the wall reference of the same rows.
            rows = (r_top + a, r_top + b)
            c0, c1 = sorted([col(search[0]), col(search[1])])
            block = image[rows[0]:rows[1] + 1, c0:c1 + 1, :]
            rb_y = (block[..., 0] - block[..., 2]).mean(axis=0)
            lum_y = block.mean(axis=(0, 2))
            ref_rb = float(wall_rb[rows[0]:rows[1] + 1].mean())
            ref_lum = float(wall_lum[rows[0]:rows[1] + 1].mean())
            hit = [(rb_y[i] < ref_rb - RB_DROP) or (lum_y[i] < ref_lum - LUM_DROP) for i in range(len(rb_y))]
            centre = col(float(np.mean(sample))) - c0
            left = right = centre
            while left - 1 >= 0 and hit[left - 1]:
                left -= 1
            while right + 1 < len(hit) and hit[right + 1]:
                right += 1
            ys = sorted([y_of(c0 + left), y_of(c0 + right)])
            windows.append({'column': key, 'storey': f'F{number}', 'z_m': [round(z_lo, 2), round(z_hi, 2)],
                            'measured_span_m': [round(ys[0], 2), round(ys[1], 2)],
                            'wall_reference_rb': round(ref_rb, 1), 'wall_reference_lum': round(ref_lum, 1)})
    # One regular column span per column (median of storeys); clamp so the new
    # column does not overlap the inventoried stair glazing.
    rows_out = []
    for key in COLUMNS:
        found = [w for w in windows if w['column'] == key]
        if not found:
            continue
        lo = float(np.median([w['measured_span_m'][0] for w in found]))
        hi = float(np.median([w['measured_span_m'][1] for w in found]))
        clamp = None
        if lo < EXISTING_STAIR_WINDOW_SOUTH_EDGE + 0.07:
            clamp = {'measured_lower_edge_m': round(lo, 2), 'used_m': EXISTING_STAIR_WINDOW_SOUTH_EDGE + 0.07,
                     'reason': 'glazing continues into the inventoried stair window; a 0.07 m mullion keeps both rectangles separate'}
            lo = EXISTING_STAIR_WINDOW_SOUTH_EDGE + 0.07
        span = [round(lo, 2), round(hi, 2)]
        for w in found:
            yc, zc = float(np.mean(span)), float(np.mean(w['z_m']))
            pixel = [col(yc), row(zc)]
            query = mesh.pixel_query(VIEW, [pixel])['queries'][0]
            on_plane = bool(query.get('hit')) and abs(query['world_xyz'][0] - WEST_PLANE) < PLANE_TOLERANCE_M
            record = {'id': f"west_band_{key}_{w['storey']}", 'view': 'west', 'plane_key': 'west',
                      'span_m': span, 'z_m': w['z_m'], 'visibility': 'developer_profile_measurement',
                      'basis': ('Uninventoried street-facade glazing next to the south stair glazing, measured from texture colour '
                                'profiles (observations/west_band_hi.png) against the adjacent wall; one span per column (median of storeys).'),
                      'profile_evidence': w, 'span_clamp': clamp,
                      'hit_check': {'pixel': pixel, 'hit': bool(query.get('hit')), 'world_xyz': query.get('world_xyz'),
                                    'expected_plane_x_m': WEST_PLANE, 'plane_tolerance_m': PLANE_TOLERANCE_M, 'on_plane': on_plane},
                      'source_refs': ['AI_agent/logs/experiments/2026-09-25_voimatalo_opus_development/observations/west_band_hi.png',
                                      'AI_agent/logs/experiments/2026-09-25_voimatalo_opus_development/observations/west_band_hi.json']}
            (rows_out if on_plane else rejected).append(record if on_plane else {'id': record['id'], 'reason': 'centre does not hit the street facade plane', 'hit_check': record['hit_check']})
    result = {'schema': 'voimatalo_band_window_measurement_v1', 'mesh_sha256': mesh.mesh_sha256,
              'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'thresholds': {'rb_drop': RB_DROP, 'lum_drop': LUM_DROP, 'min_run_m': MIN_RUN_M,
                             'wall_reference_y_m': WALL_REFERENCE, 'columns': COLUMNS},
              'openings': rows_out, 'rejected': rejected,
              'limits': ['Colour-profile reading of photogrammetric texture; reflections and shading can shift edges by ~0.1-0.2 m.',
                         'z ranges are the detected window-like rows, not frame dimensions.',
                         'Glass semantics (window vs glazed panel) are developer judgement.']}
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'accepted': [(r['id'], r['span_m'], r['z_m']) for r in rows_out], 'rejected': rejected}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
