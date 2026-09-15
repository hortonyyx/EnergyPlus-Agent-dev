"""Replayable developer exploration from the original GLB, without prior BIM.

This is an experiment notebook in executable form, not a mandatory Agent pipeline.
Keep the observed sections open: scan holes are not physical openings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def section(triangles, height):
    """Exact triangle / horizontal-plane segments, with original global face IDs."""
    rows = []
    for face_id, tri in enumerate(triangles):
        dz = tri[:, 2] - height
        if dz.min() >= 0 or dz.max() <= 0:
            continue  # no strict crossing; selected levels avoid coplanar faces
        hits = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if dz[a] * dz[b] < 0:
                hits.append(tri[a] + (-dz[a] / (dz[b] - dz[a])) * (tri[b] - tri[a]))
            elif dz[a] == 0:
                hits.append(tri[a])
        unique = np.unique(np.round(hits, 10), axis=0)
        if len(unique) == 2 and np.linalg.norm(unique[1] - unique[0]) > 1e-8:
            rows.append({'face_id': face_id, 'endpoints_xyz_m': unique.tolist()})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesh', type=Path, default=ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    mesh = MeshObservation(args.mesh)
    raw = np.concatenate([p.vertices[p.faces] for p in mesh._parts])
    cross = np.cross(raw[:, 1] - raw[:, 0], raw[:, 2] - raw[:, 0])
    lengths = np.linalg.norm(cross, axis=1)
    normals = cross / np.maximum(lengths[:, None], 1e-12)
    centres = raw.mean(axis=1)
    # Deliberate developer scope: repeated main elevations, excluding roof/ground.
    mask = ((lengths > 1e-10) & (abs(normals[:, 2]) <= np.sin(np.radians(10)))
            & (centres[:, 2] >= 8) & (centres[:, 2] <= 22))
    traces = np.arctan2(normals[mask, 0], -normals[mask, 1])
    weights = lengths[mask] / 2
    resultant = np.sum(weights * np.exp(4j * traces)) / weights.sum()
    family_yaw = -float(np.degrees(np.angle(resultant)) / 4)
    # One of four equivalent orthogonal frames; +X/+Y labels require whole-shape judgement.
    yaw = family_yaw
    angle = np.radians(yaw)
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    triangles = raw @ rotation.T
    direction = {
        'method': 'area-weighted fourth-angle mean of near-vertical triangle traces; orthogonal-family estimate only',
        'original_z_band_m': [8, 22], 'max_tilt_from_vertical_degrees': 10,
        'face_ids': np.flatnonzero(mask).tolist(), 'face_count': int(mask.sum()),
        'surface_area_m2': float(weights.sum()), 'fourfold_resultant_length': float(abs(resultant)),
        'yaw_family_degrees': family_yaw,
        'equivalent_yaws_degrees': [family_yaw + k * 90 for k in range(4)],
        'used_yaw_degrees': yaw, 'translation_m': [0, 0, 0],
        'warning': 'Not a surveyed axis or uncertainty bound. Relief, slanted surfaces and disconnected parallel walls remain. Does not fit wall positions.',
        'frame_choice': 'Smallest absolute yaw used for observation; inspect asymmetric whole L shape before mapping BIM axes. Direction names are local axes, not geographic bearings.',
    }
    write(args.out / 'direction.json', direction)
    sections = []
    # Height samples are diagnostic cuts, never declarations of floor slabs.
    heights = [2.13, 6.53, 12.13, 21.13, 25.53, 28.53]
    plot = Image.new('RGB', (1320, 1460), 'white')
    draw = ImageDraw.Draw(plot)
    draw.text((25, 14), 'Raw mesh sections. Open traces preserved. Heights are NOT floor levels.', fill='#23313d')
    for number, z in enumerate(heights):
        rows = section(triangles, z)
        sections.append({'z_m': z, 'segments': rows})
        left, top = 35 + (number % 3) * 435, 70 + (number // 3) * 690
        scale = 8.2  # Same metric scale on both axes and every panel.
        def screen(x, y):
            return (left + (x + 20) * scale, top + (33 - y) * scale)
        draw.text((left, top - 25), f'z = {z:.2f} m | local X/Y, metres', fill='#23313d')
        for x in range(-20, 26, 5):
            draw.line([screen(x, -38), screen(x, 33)], fill='#e3e6e8')
            draw.text(screen(x, -39), str(x), fill='#677781')
        for y in range(-35, 34, 5):
            draw.line([screen(-20, y), screen(25, y)], fill='#e3e6e8')
            draw.text((left - 26, screen(-20, y)[1] - 5), str(y), fill='#677781')
        for row in rows:
            a, b = row['endpoints_xyz_m']
            draw.line([screen(*a[:2]), screen(*b[:2])], fill='#125477', width=2)
    plot.save(args.out / 'sections.png')
    write(args.out / 'sections.json', {'mesh_sha256': mesh.mesh_sha256, 'yaw_degrees': yaw, 'sections': sections,
          'limitations': ['No closure, snapping, inferred wall filling or BIM-derived geometry.',
                         'A missing trace is missing scan evidence, not proof of an open wall.',
                         'Sampling heights do not establish storeys or slab positions.']})
    # Camera choices are explicit developer operations, replayable from original data.
    views = [
        ('top', [2, -3, 110], [2, -3, 15], 48, 72, None),
        ('street', [-90, 85, 65], [0, -3, 15], 78, 56, None),
        ('courtyard', [100, -95, 65], [0, -3, 15], 78, 56, None),
        ('west', [-100, -3, 17], [0, -3, 17], 70, 38, None),
        ('north', [2, 100, 17], [2, 0, 17], 43, 38, None),
        ('court_long', [100, -11, 17], [0, -11, 17], 47, 38, [[-25, -36, -1], [8, 9, 36]]),
        ('court_short', [10, -100, 17], [10, 10, 17], 25, 38, [[0, 6, -1], [25, 30, 36]]),
    ]
    view_records = []
    for name, eye, target, width, height, bounds in views:
        scale = 1200 / max(width, height)
        _, metadata = mesh.render(args.out / name, eye=eye, target=target, width_m=width, height_m=height,
                                  width_px=round(width * scale), height_px=round(height * scale),
                                  yaw_degrees=yaw, bounds=bounds)
        view_records.append({'name': name, 'camera': metadata['camera'], 'selection_bounds': bounds,
                             'view_span_m': metadata['view_span_m'], 'resolution_px': metadata['resolution_px']})
        print(f'saved {name}', flush=True)
    manifest = {'mode': 'development_assistant_exploration; no product-model call; no new BIM yet',
                'input': mesh.describe(), 'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'prior_context': 'Developer has seen old candidates and known failures. This is not a blind cold start.',
                'geometry_dependencies': 'Original input.glb only. No prior BIM coordinates, parent tile, OSM contour or GT read by this script.',
                'views': view_records, 'section_heights_m': heights}
    write(args.out / 'manifest.json', manifest)
    cards = ''.join(f'<figure><figcaption>{v[0]} · <a href="{v[0]}.json">相机与坐标</a></figcaption><a href="{v[0]}.png"><img src="{v[0]}.png"></a></figure>' for v in views)
    (args.out / 'index.html').write_text('''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Voimatalo 开发探路：原始证据</title><style>body{font:16px/1.65 system-ui;margin:24px auto;max-width:1300px;padding:0 18px;background:#f6f7f8;color:#23313d}h1{font-size:26px}article{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}figure{margin:0;padding:12px;background:white;border:1px solid #dce2e6}img{width:100%;display:block}a{color:#126082}</style><h1>Voimatalo · 开发助手完整探路的原始证据</h1><p>本页是新探路的观察起点，尚未生成新 BIM。只读原始单栋 GLB；开发助手已有旧案例上下文。下方剖切高度是量测取样，不是楼板。扫描缺口保留，不能据此断言墙面敞开。方向名称仅指局部坐标。</p><p><a href="manifest.json">输入及操作记录</a> · <a href="direction.json">方向计算</a> · <a href="sections.json">逐三角面剖切端点</a></p><figure><figcaption>六个高度的原网格剖切</figcaption><a href="sections.png"><img src="sections.png"></a></figure><h2>原纹理整体与立面观察</h2><p>内院两张视图用了明确的三角面中心范围筛选，以露出遮挡后的表面；不是完整相机可见性证明。原图和可查询像素缓冲均保存。</p><article>''' + cards + '</article></html>')
    print(json.dumps({'yaw_family': yaw, 'selected_faces': int(mask.sum()), 'views': len(views), 'sections': len(sections)}))


if __name__ == '__main__':
    main()
