"""Evidence for the cropped courtyard protrusion (09-26 Opus development).

Reads only the supplied single-building GLB in the frozen 09-15 frame
(yaw 14.887 deg, zero translation).  Produces
  * close textured views of the protrusion stubs and neighbouring faces,
    each with a metre-grid companion (projection ticks, not measured walls);
  * horizontal mesh sections and a face-stub inventory (``protrusion_measure.json``);
  * a plan plot of the sections (``protrusion_sections.png``);
  * the hole outline on the courtyard wall from the 09-25 retained
    ``court_long_south`` pixel buffer (first hit far behind the courtyard plane).
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
sys.path.insert(0, str(HERE.parent / '2026-09-25_voimatalo_opus_development'))
from src.agent.geometry.mesh_observation import MeshObservation  # noqa: E402
from observe_interior_cues import draw_grid  # noqa: E402

MESH = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb'
PARENT_OBS = HERE.parent / '2026-09-25_voimatalo_opus_development/observations'
YAW = 14.887066917997172
COURT_X = 0.8          # long-wing courtyard wall plane used by the 09-25 candidate

VIEWS = [
    # Close top view of the protrusion footprint, annex south edge and south core roof.
    ('prot_top', [3, -23, 90], [3, -23, 0], 22, 16, None),
    # North face stub above the annex roof, seen from the courtyard north (annex removed by bounds).
    ('prot_north_stub', [2, 30, 16], [2, -22, 16], 9, 24, [[-2, -24, 6.9], [7, -21.2, 30]]),
    # Annex south face and the protrusion's ground footprint seen from the south.
    ('annex_south_face', [7, -80, 5], [7, -21.8, 5], 18, 12, [[0.3, -23.5, -1], [16, -20.5, 12]]),
    # High oblique from the north-east over the annex towards the hole.
    ('prot_oblique_ne', [40, 8, 42], [1, -23, 13], 30, 34, None),
    # Low oblique from the south-east towards the south stub and glazed column.
    ('prot_oblique_se', [35, -50, 14], [1, -25, 14], 18, 30, [[-15, -40, -1], [16, -20.0, 40]]),
]
KEEP_BUFFERS = {'prot_north_stub', 'annex_south_face'}


def triangles(mesh: MeshObservation) -> np.ndarray:
    selected, _ = mesh._operation_parts(YAW, None)  # same frame as render(); read-only use
    return np.concatenate([vertices[part.faces[ids]] for part, vertices, ids in selected])


def section(tris: np.ndarray, z: float, box) -> list[list[float]]:
    zz = tris[:, :, 2]
    segs = []
    for tri in tris[(zz.min(1) < z) & (zz.max(1) > z)]:
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            za, zb = tri[a, 2], tri[b, 2]
            if (za - z) * (zb - z) < 0:
                s = (z - za) / (zb - za)
                pts.append(tri[a] + s * (tri[b] - tri[a]))
        if len(pts) == 2 and any(box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3] for p in pts):
            segs.append([round(float(v), 3) for v in (*pts[0][:2], *pts[1][:2])])
    return segs


def stub(tris, normals, axis_normal: int, centre: float, tol: float, xlim, ylim) -> dict:
    n_abs = np.abs(normals[:, axis_normal])
    c = tris.mean(1)
    pick = (n_abs > 0.7) & (np.abs(c[:, axis_normal] - centre) < tol) & \
        (c[:, 0] > xlim[0]) & (c[:, 0] < xlim[1]) & (c[:, 1] > ylim[0]) & (c[:, 1] < ylim[1])
    if not pick.any():
        return {'faces': 0}
    pts = tris[pick].reshape(-1, 3)
    sign = np.sign(normals[pick, axis_normal])
    return {'faces': int(pick.sum()), 'x_m': [round(float(pts[:, 0].min()), 2), round(float(pts[:, 0].max()), 2)],
            'y_m': [round(float(pts[:, 1].min()), 2), round(float(pts[:, 1].max()), 2)],
            'z_m': [round(float(pts[:, 2].min()), 2), round(float(pts[:, 2].max()), 2)],
            'normal_sign_counts': {'+': int((sign > 0).sum()), '-': int((sign < 0).sum())}}


def hole_outline() -> dict:
    """Rows of the 09-25 court_long_south buffer whose first hit lies far behind the courtyard wall."""
    with np.load(PARENT_OBS / 'court_long_south.npz', allow_pickle=False) as d:
        h, w = (int(v) for v in d['image_shape'])
        idx = np.asarray(d['pixel_indices'])
        pts = np.asarray(d['world_points'])
    rows, cols = idx // w, idx % w
    deep = pts[:, 0] < COURT_X - 3.0          # hit the back of the street wall / far interior
    per_z = {}
    for z in np.arange(1.0, 27.01, 1.0):
        band = deep & (np.abs(pts[:, 2] - z) < 0.25) & (pts[:, 1] > -30) & (pts[:, 1] < -18)
        if band.any():
            ys = pts[band, 1]
            per_z[f'{z:.0f}'] = [round(float(np.percentile(ys, 2)), 2), round(float(np.percentile(ys, 98)), 2)]
    top = float(pts[deep & (pts[:, 1] > -25) & (pts[:, 1] < -22.5), 2].max()) if deep.any() else None
    return {'source': 'observations/court_long_south.npz (09-25, retained)',
            'rule': f'first hit x < {COURT_X - 3.0} m while looking west from the courtyard',
            'deep_hit_y_range_by_z_m': per_z,
            'highest_deep_hit_z_m_in_y_-25_-22.5': round(top, 2) if top is not None else None}


def plot_sections(sections: dict, out: Path):
    xmin, xmax, ymin, ymax = -2.0, 8.0, -30.0, -17.0
    s = 60
    img = Image.new('RGB', (int((xmax - xmin) * s) + 40, int((ymax - ymin) * s) + 40), 'white')
    d = ImageDraw.Draw(img)

    def px(x, y):
        return (20 + (x - xmin) * s, 20 + (ymax - y) * s)
    for x in np.arange(xmin, xmax + 0.01, 1):
        d.line([px(x, ymin), px(x, ymax)], fill=(220, 220, 220))
        d.text(px(x + 0.05, ymax), f'x{x:g}', fill=(120, 0, 0))
    for y in np.arange(ymin, ymax + 0.01, 1):
        d.line([px(xmin, y), px(xmax, y)], fill=(220, 220, 220))
        d.text(px(xmin + 0.05, y), f'y{y:g}', fill=(120, 0, 0))
    palette = [(200, 0, 0), (230, 120, 0), (0, 140, 0), (0, 120, 200), (120, 0, 200), (0, 0, 0)]
    for i, (z, segs) in enumerate(sections.items()):
        col = palette[i % len(palette)]
        for x0, y0, x1, y1 in segs:
            d.line([px(x0, y0), px(x1, y1)], fill=col, width=2)
        d.text((25, 25 + 12 * i), f'z={z} m', fill=col)
    img.save(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists(), 'Use a new output directory'
    args.out.mkdir(parents=True)
    mesh = MeshObservation(MESH)
    records = []
    for name, eye, target, width, height, bounds in VIEWS:
        scale = 1200 / max(width, height)
        image, meta = mesh.render(args.out / name, eye=eye, target=target, width_m=width, height_m=height,
                                  width_px=round(width * scale), height_px=round(height * scale),
                                  yaw_degrees=YAW, bounds=bounds)
        draw_grid(image, meta).save(args.out / f'{name}_grid.png')
        if name not in KEEP_BUFFERS:
            (args.out / f'{name}.npz').unlink()
        records.append({'name': name, 'eye': eye, 'target': target, 'span_m': [width, height],
                        'selection_bounds': bounds, 'pixel_buffer_retained': name in KEEP_BUFFERS})
        print('saved', name, flush=True)

    tris = triangles(mesh)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    box = (-2.0, -30.0, 8.0, -17.0)
    levels = [3.0, 8.0, 12.0, 16.0, 20.0, 24.0, 26.0, 27.5]
    sections = {f'{z:g}': section(tris, z, box) for z in levels}
    plot_sections(sections, args.out / 'protrusion_sections.png')
    c = tris.mean(1)
    footprint = (c[:, 0] > 1.3) & (c[:, 1] > -25.7) & (c[:, 1] < -22.1)
    horiz = np.abs(normals[:, 2]) > 0.9
    annex_roof = horiz & (c[:, 0] > 2) & (c[:, 0] < 12) & (c[:, 1] > -21.6) & (c[:, 1] < -18)
    measure = {
        'mesh_sha256': mesh.mesh_sha256,
        'frame': {'yaw_degrees': YAW, 'translation_m': [0, 0, 0]},
        'north_stub_face_y≈-21.9': stub(tris, normals, 1, -21.9, 0.4, (0.8, 4.0), (-23, -21)),
        'south_stub_face_y≈-25.9': stub(tris, normals, 1, -25.9, 0.4, (0.5, 4.0), (-27, -25)),
        'annex_south_face_y≈-21.75_below_7m': stub(tris, normals, 1, -21.75, 0.3, (2.3, 14.0), (-22.5, -21.0)),
        'triangles_with_centroid_in_footprint_x>1.3_y(-25.7,-22.1)': int(footprint.sum()),
        'annex_roof_z_percentiles_5_50_95': [round(float(v), 2) for v in np.percentile(tris[annex_roof][:, :, 2], [5, 50, 95])],
        'courtyard_hole_from_parent_buffer': hole_outline(),
        'section_levels_m': levels,
        'section_box_xy_m': box,
        'sections': sections,
    }
    (args.out / 'protrusion_measure.json').write_text(json.dumps(measure, indent=1, ensure_ascii=False) + '\n')
    manifest = {'mesh_sha256': mesh.mesh_sha256, 'yaw_degrees': YAW,
                'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'mode': 'development assistant observation of the cropped courtyard protrusion; no model call',
                'inputs': 'input.glb only (+ retained 09-25 court_long_south buffer); no parent tile, OSM, GT or drawings',
                'views': records,
                'caveat': 'Grid lines are orthographic projection ticks; texture reading is developer judgement.'}
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
