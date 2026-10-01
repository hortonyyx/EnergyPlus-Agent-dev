"""User-guided developer revision of the selected September 10/11 demo.

No external model calls. Interior use/partitions are proposals, not recovered facts.
The selected historic demo and its observations are immutable inputs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import runpy
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.correction.schema import Cell, CorrectedGeometry, Floor, FootprintRing, WallOpening, Window
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_bim import build_source_bim

HERE = Path(__file__).resolve().parent
DEMO = ROOT / 'showcase/2026-09-11-research-report/demos/textured-mass'
BASE = DEMO / 'revision_02/inferred'
REFS = ['2026-09-30 user feedback', str(BASE.relative_to(ROOT) / 'observations.json')]
MAIN = Polygon([[-13.7, -33.4], [.7, -33.4], [.7, 9.1], [18.9, 9.1], [18.9, 26.1], [-13.7, 26.1]])
ATTIC = Polygon([[-12.5, -32.3], [.7, -32.3], [.7, 9.1], [17.8, 9.1], [17.8, 25], [-12.5, 25]])
ANNEX = box(.7, -21.5, 13, 9.1)
PROJECTION = Polygon([[.7, -28.6], [1.15, -28.6], [1.15, -26.1], [2.4, -26.1], [2.4, -21.5], [.7, -21.5]])
TOWER = unary_union([PROJECTION, box(-3, -28.6, .7, -21.5)])
LIFT = box(.2, -26.1, 2.4, -23.7)
CORES = {'CORE_S': box(-8.9, -33.4, -5.5, -27.8),
         'CORE_E': box(.7, 9.1, 5, 16.3),
         'TOWER_STAIR': TOWER.difference(LIFT), 'TOWER_LIFT': LIFT}
ANNEX_STAIR = box(10, -21.5, 13, -15.3)
CORE_UNION = unary_union(list(CORES.values()))
HALL = unary_union([box(-7.9, -33.4, -5.5, 16.3), box(-13.7, 16.3, 18.9, 18.9),
                    box(-5.5, -28.6, -3, -21.5)]).difference(CORE_UNION)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def ring(poly):
    assert poly.is_valid and not poly.interiors, poly.wkt
    return [[round(x, 5), round(y, 5)] for x, y in list(orient(poly.simplify(0), 1).exterior.coords)[:-1]]


def parts(shape):
    return [shape] if shape.geom_type == 'Polygon' else [p for p in shape.geoms if p.geom_type == 'Polygon']


def grid(value):
    return round(round(value / .05) * .05, 2)


def segments(poly):
    points = ring(poly)
    for a, b in zip(points, points[1:] + points[:1]):
        d = np.array(b) - a
        n = np.array([d[1], -d[0]]) / np.linalg.norm(d)
        yield a, b, n


def build_observations():
    old = json.loads((BASE / 'observations.json').read_text())
    obs = copy.deepcopy(old)
    changes = []
    for o, parent in zip(obs, old):
        o['span'] = [grid(v) for v in o['span']]
        o['z'] = [grid(v) for v in o['z']]
        fid = o['floor']
        if fid in [f'F{i}' for i in range(2, 8)]:
            base = 5.6 + (int(fid[1:]) - 2) * 3.2
            o['z'] = [round(base + 1.2, 2), round(base + 2.8, 2)]
            if fid == 'F2' and ((o['evidence']['view'] == 'court_long' and o['span'][1] > -21.5)
                                or (o['evidence']['view'] == 'court_short' and o['span'][0] < 13)):
                o['z'][0] = 7.2  # clear the two-storey annex roof by 0.30 m
        elif fid == 'F8' and o['evidence']['view'] == 'court_long':
            o['z'] = [26.1, 27.3]  # 1.3 m sill, 1.2 m aperture, 0.3 m head
        elif fid == 'ANNEX' and o['z'][0] > 3:
            o['z'] = [4.1, 6.0]
        elif fid == 'TRAFFIC':
            o['z'] = [round(v + .1, 2) for v in o['z']]
        o['source_kind'] = 'retained_observation_architecturally_regularised'
        changes.append({'id': o['id'], 'old_span_m': parent['span'], 'span_m': o['span'],
                        'old_z_m': parent['z'], 'z_m': o['z']})

    def infer(oid, fid, facade, axis, plane, span, z, reason):
        obs.append(dict(id=oid, floor=fid, facade=facade, axis=axis, plane=plane, span=span, z=z,
                        source_kind='inferred_completion',
                        evidence={'view': 'context/courtyard.png; missing_measurements/core_side.png',
                                  'basis': 'explicit_inference_after_missing_texture', 'note': reason}))

    for level in range(2, 8):
        z = round(5.6 + (level - 2) * 3.2, 2)
        infer(f'F{level}_court_short_completion', f'F{level}', 'South', 1, 9.1, [15.5, 17.85],
              [round(z + 1.2, 2), round(z + 2.8, 2)],
              'Exposed final bay: continue adjacent window rhythm across incomplete texture, not an opening-free void.')
    for level, z in [(1, [1, 2.7]), (2, [4.1, 6])]:
        for i, span in enumerate([[3.2, 5.6], [6.5, 8.9], [10.4, 12.4]]):
            infer(f'ANNEX_south_L{level}_{i+1}', 'ANNEX', 'South', 1, -21.5, span, z,
                  'Two-storey front-hall facade is partly occluded; windows inferred at a regular architectural module. Last bay lights the annex stair.')
    return obs, changes


def cuts(lo, hi, windows, min_width=2.5):
    intervals = sorted((a, b) for a, b in windows if a >= lo - .06 and b <= hi + .06)
    result = [lo] + [grid((b + c) / 2) for (a, b), (c, d) in zip(intervals, intervals[1:])] + [hi]
    # Very narrow partial corner groups may share a room; retain each opening.
    while len(result) > 2:
        short = next((i for i, (a, b) in enumerate(zip(result, result[1:])) if b - a < min_width - 1e-6), None)
        if short is None:
            break
        del result[1 if short == 0 else short]
    return result


def build(out):
    obs, regularisation = build_observations()
    floors, rooms, plan_checks = [], [], []

    def add_floor(fid, footprint, z, height, rows, spanning=()):
        cells = []
        for sid, poly, role in rows:
            for k, part in enumerate(parts(poly)):
                if part.area < .1:
                    raise ValueError(f'Tiny space {sid}: {part.area}')
                cell_id = sid if len(parts(poly)) == 1 else f'{sid}_{k+1}'
                x0, y0, x1, y1 = part.bounds
                evidence = dict(role=role, basis='inferred', source_refs=REFS,
                                assumptions=['User-guided architectural use/layout hypothesis; not a measured interior.'])
                cells.append(Cell(id=cell_id, role=role, x=[x0, x1], y=[y0, y1], polygon=ring(part),
                                  role_evidence=evidence, source_refs=REFS,
                                  assumptions=evidence['assumptions']))
                rooms.append(dict(id=cell_id, poly=part, role=role, floor=fid, z=round(z, 2), h=height))
        local = [r['poly'] for r in rooms if r['floor'] == fid]
        shared = [CORES[s] if s in CORES else ANNEX_STAIR for s in spanning]
        cover = unary_union(local + shared)
        missing = footprint.symmetric_difference(cover).area
        overlap = sum(p.area for p in local + shared) - cover.area
        assert missing < 1e-7 and overlap < 1e-7, (fid, missing, overlap)
        plan_checks.append(dict(floor=fid, uncovered_or_excess_m2=missing, overlap_m2=overlap,
                                local_spaces=len(cells), spanning_space_ids=list(spanning)))
        floors.append(Floor(name=fid, z_floor=round(z, 2), ceiling_height=height, cells=cells,
                            footprint=FootprintRing(vertices=ring(footprint)), spanning_space_ids=list(spanning)))

    footprint = MAIN.union(PROJECTION)
    add_floor('F1', footprint, 0, 5.6, [('F1_retail', MAIN.difference(CORE_UNION), 'retail')], CORES)
    for level in range(2, 8):
        fid = f'F{level}'
        rows = [(f'{fid}_hall', HALL, 'corridor')]
        def intervals(view):
            return [o['span'] for o in obs if o['floor'] == fid and
                    (o['evidence']['view'] == view or (view == 'court_short' and o['id'].endswith('completion')))]

        def band(tag, lo, hi, view, make_poly):
            edges = cuts(lo, hi, intervals(view))
            for i, (a, b) in enumerate(zip(edges, edges[1:])):
                poly = make_poly(a, b).difference(CORE_UNION).difference(HALL)
                if poly.is_empty:
                    continue
                rows.append((f'{fid}_{tag}_{i+1:02}', poly, 'office/enclosed'))

        band('W', -33.4, 16.3, 'west', lambda a, b: box(-13.7, a, -7.9, b))
        # The two narrow southern glazing groups form one sensible meeting room;
        # the wider repeating office bays each receive their own room.
        rows.append((f'{fid}_meeting_S', box(-5.5, -33.4, .7, -28.6), 'conference/meeting/multipurpose'))
        band('E', -21.5, 9.1, 'court_long', lambda a, b: box(-5.5, a, .7, b))
        band('N', -13.7, 18.9, 'north', lambda a, b: box(a, 18.9, b, 26.1))
        band('S', 5, 18.9, 'court_short', lambda a, b: box(a, 9.1, b, 16.3))
        rows.extend([(f'{fid}_restroom', box(-5.5, 9.1, .7, 12.7), 'restroom'),
                     (f'{fid}_service', box(-5.5, 12.7, .7, 16.3), 'electrical/mechanical')])
        add_floor(fid, footprint, 5.6 + (level - 2) * 3.2, 3.2, rows, CORES)

    upper_s = ATTIC.intersection(CORES['CORE_S'])
    add_floor('F8', ATTIC.union(PROJECTION), 24.8, 2.8,
              [('F8_attic', ATTIC.difference(CORE_UNION), 'attic'), ('F8_stair_S', upper_s, 'stairwell')],
              ['CORE_E', 'TOWER_STAIR', 'TOWER_LIFT'])
    for sid, poly in CORES.items():
        add_floor(sid, poly, 0, 24.8 if sid == 'CORE_S' else 27.6,
                  [(sid, poly, 'shaft' if sid.endswith('LIFT') else 'stairwell')])
    for level, z, h in [(1, 0, 3.3), (2, 3.3, 3.6)]:
        add_floor(f'ANNEX_F{level}', ANNEX, z, h,
                  [(f'ANNEX_F{level}_hall', ANNEX.difference(ANNEX_STAIR), 'lobby')], ['ANNEX_STAIR'])
    add_floor('ANNEX_STAIR', ANNEX_STAIR, 0, 6.9, [('ANNEX_STAIR', ANNEX_STAIR, 'stairwell')])

    # More articulated short-wing roof, informed by the prior developer's mesh
    # sections. These remain simplified enclosure volumes, not an occupied floor.
    roof_low = unary_union([box(-11, -31.3, .7, -20.8), box(-11, -20.8, -.1, 10),
                            box(-10.8, 10, 6.5, 23.6), box(6.5, 12.7, 16.8, 23.6),
                            box(-12.5, 16, -10.8, 23.6)])
    roof_n = unary_union([box(-6.8, 16, 16.3, 21.3), box(-4, 10, 6.5, 16), box(6.5, 12.7, 16.3, 16)])
    roof_rows = [('ROOF_low', roof_low, 27.6, .8, 'plenum'),
                 ('ROOF_N_base', roof_n, 28.4, 2.4, 'electrical/mechanical'),
                 ('ROOF_N_cap', box(-3.5, 10, 6.5, 16.5), 30.8, 1.1, 'plenum'),
                 ('ROOF_S', box(-8, -28.5, .7, -20.8), 28.4, 3.0, 'electrical/mechanical'),
                 ('ROOF_stack', box(-6.5, -25.5, -5, -23.3), 31.4, 2.6, 'shaft')]
    for sid, poly, z, h, role in roof_rows:
        add_floor(sid, poly, z, h, [(sid, poly, role)])

    windows, mapping = [], []
    for o in obs:
        owners = []
        for r in rooms:
            if o['z'][0] < r['z'] - 1e-6 or o['z'][1] > r['z'] + r['h'] + 1e-6:
                continue
            for a, b, normal in segments(r['poly']):
                axis, other = o['axis'], 1 - o['axis']
                want = {'West': [-1, 0], 'East': [1, 0], 'North': [0, 1], 'South': [0, -1]}[o['facade']]
                if np.dot(normal, want) < .99 or abs(a[axis] - o['plane']) > 1e-5 or abs(b[axis] - o['plane']) > 1e-5:
                    continue
                if min(a[other], b[other]) - 1e-6 <= o['span'][0] and max(a[other], b[other]) + 1e-6 >= o['span'][1]:
                    owners.append(r)
        if len(owners) != 1:
            raise ValueError(f"Opening {o['id']} expected one host, got {[r['id'] for r in owners]}; {o}")
        r = owners[0]
        windows.append(Window(id=o['id'], floor=r['floor'], facade=o['facade'], span=o['span'], z=o['z'], room=r['id'],
                              source_refs=REFS + [o['evidence']['view']], assumptions=[o['evidence']['note']]))
        mapping.append({**o, 'space_id': r['id']})

    doors = []
    by_id = {r['id']: r for r in rooms}
    def shared_segments(a, b):
        intersection = a['poly'].boundary.intersection(b['poly'].boundary)
        lines = [intersection] if intersection.geom_type == 'LineString' else list(getattr(intersection, 'geoms', []))
        # Shapely retains collinear vertices; only straight source edges qualify.
        return [line for line in lines if line.geom_type == 'LineString' and line.length > 1.2
                and (abs(line.bounds[2] - line.bounds[0]) < 1e-6 or abs(line.bounds[3] - line.bounds[1]) < 1e-6)]

    def connect(aid, bid, z, width=.9, name=None):
        a, b = by_id[aid], by_id[bid]
        lines = shared_segments(a, b)
        assert lines, (aid, bid, 'no usable shared edge')
        line = max(lines, key=lambda x: x.length)
        a1, b1 = line.interpolate(line.length / 2 - width / 2), line.interpolate(line.length / 2 + width / 2)
        doors.append(WallOpening(id=name or f'D_{aid}_{bid}', kind='door', space_id=aid, other_space_id=bid,
                                 p1=[grid(a1.x), grid(a1.y)], p2=[grid(b1.x), grid(b1.y)], z=[round(z, 2), round(z + 2.1, 2)],
                                 source_refs=REFS, assumptions=['Inferred usable doorway on a shared wall, aligned to its storey landing.']))

    for level in range(2, 8):
        fid = f'F{level}'
        z = 5.6 + (level - 2) * 3.2
        for r in [r for r in rooms if r['floor'] == fid and r['role'] != 'corridor']:
            targets = [by_id[f'{fid}_hall']] + [by_id[s] for s in ['CORE_S', 'CORE_E', 'TOWER_STAIR']]
            candidates = [(max(l.length for l in shared_segments(r, t)), t) for t in targets if shared_segments(r, t)]
            assert candidates, r['id']
            target = max(candidates, key=lambda x: x[0])[1]
            connect(r['id'], target['id'], z)
        for sid in ['CORE_S', 'CORE_E', 'TOWER_STAIR']:
            connect(f'{fid}_hall', sid, z, 1.2)
        connect('TOWER_STAIR', 'TOWER_LIFT', z, 1.0, f'D_{fid}_lift')
    for sid in ['CORE_S', 'CORE_E', 'TOWER_STAIR']:
        connect('F1_retail', sid, 0, 1.2)
    connect('TOWER_STAIR', 'TOWER_LIFT', 0, 1.0, 'D_F1_lift')
    for sid in ['F8_stair_S', 'CORE_E', 'TOWER_STAIR']:
        connect('F8_attic', sid, 24.8, 1.0)
    connect('TOWER_STAIR', 'TOWER_LIFT', 24.8, 1.0, 'D_F8_lift')
    for level, z in [(1, 0), (2, 3.3)]:
        connect(f'ANNEX_F{level}_hall', 'ANNEX_STAIR', z, 1.2)
        connect(f'ANNEX_F{level}_hall', 'TOWER_STAIR', z, 1.1)
    for name, p1, p2 in [('street', [-13.7, -11.65], [-13.7, -10.05]),
                         ('north', [0, 26.1], [1.6, 26.1])]:
        doors.append(WallOpening(id=f'D_entry_{name}', kind='door', space_id='F1_retail', other_space_id=None,
                                 p1=p1, p2=p2, z=[0, 2.7], source_refs=REFS,
                                 assumptions=['Retained inferred entrance position; 1.6 m width and 2.7 m height regularised.']))

    assumptions = [
        '以用户选定的 2026-09-11 演示版 revision_02/inferred 为基础，由 Astra 开发助手直接修改；非开发模型框架验证或工作模型成绩。',
        '沿用原演示版单体 GLB、量测贴图及有限、无标签的父瓦片局部上下文；附加上下文不是工作模型当前输入能力。',
        '建筑尺度优先于像素拟合：平面采用 50 mm 网格；标准层 3.2 m、普通窗台 1.2 m、窗高 1.6 m，附属体遮挡处保留合理净距。',
        '主要标准层一窗组一办公室；窗组可能包含多扇玻璃。转角一房双向采光、窄窗会议室及交通服务空间是有记录的例外。内部隔墙与用途均为推断。',
        '交通塔保留可见阶梯形外轮廓，楼梯空间向主体内扩展；楼梯井与 2.2×2.4 m 电梯井分开。连贯竖向空间不添加逐层封堵楼板；踏步与设备不作为已知事实。',
        '南侧前厅按明确两排窗分为 0–3.3 m 与 3.3–6.9 m 两层，保留大空间与独立连续楼梯；室内分间未知，未强行细化。',
        '缺图不等于透空：补齐闭合围护，并在露出内院末跨和前厅南面补推断窗；端部与邻楼贴邻的界面仍按实体贴邻墙处理。',
        '顶层大板是阁楼／屋顶附属空间；屋顶局部机电与空腔用途是候选解释，不再标为 Office。短翼按既有网格剖切记录增加高低错落，曲屋面仍简化。',
        '统一采用 src/agent/data/room_types.json 与通用 public_names；空间内部 ID 用于跨修订追踪，公开编号随房间数量与排序重排。',
        '尺寸用于建筑合理性推断，未验证法规、结构、设备安装或疏散设计。',
    ]
    unresolved = ['真实内部隔墙、用途与楼梯踏步未知，等待用户验收。', '屋顶坡曲面、检修入口与设备细节未展开。',
                  '贴邻墙与被遮挡窗的真实性、首层标高和局部层高需更多资料确认。', '尚未开展开发模型框架验证、工作模型回归或能耗模拟。']
    geometry = CorrectedGeometry(schema_version='2', footprint_x=[-13.7, 18.9], footprint_y=[-33.4, 26.1],
                                 floors=floors, windows=windows, openings=doors,
                                 notes='User-guided, architecturally regularised revision of the selected presentation demo.')
    HERE.mkdir(exist_ok=True)
    write(HERE / 'layout_audit.json', {'floors': plan_checks, 'spaces': len(rooms), 'windows': len(windows), 'doors': len(doors)})
    write(HERE / 'observations.json', obs)
    write(HERE / 'opening_regularisation.json', regularisation)
    write(HERE / 'opening_mapping.json', mapping)
    print(f'Layout ready: {len(rooms)} spaces, {len(windows)} windows, {len(doors)} doors', flush=True)
    if args.layout_only:
        return
    base = build_source_bim(geometry, capability_profile='orthogonal_polygon')
    write(HERE / 'base_validation.json', base['validation'])
    assert base['validation']['status'] != 'severe', base['validation']
    boundaries = {b['id']: b for b in base['boundaries']}
    patches = defaultdict(list)
    for rel in base['boundary_relations']:
        pair = [boundaries[bid] for bid in rel['boundary_ids']]
        if not all(b['geometry_type'] in ('floor', 'ceiling') for b in pair):
            continue
        ids = {b['space_id'] for b in pair}
        if not (all(s.startswith('ROOF') for s in ids) or ids == {'CORE_S', 'F8_stair_S'}):
            continue
        for b in pair:
            patches[b['id']].extend(Polygon([v[:2] for v in region['vertices']]) for region in rel['regions'])
    enclosure = []
    for bid, regions in patches.items():
        boundary = boundaries[bid]
        patch = unary_union(regions)
        whole = Polygon([v[:2] for v in boundary['vertices']]).symmetric_difference(patch).area < 1e-8
        for part in parts(patch):
            enclosure.append(dict(boundary_id=bid, condition='open', scope='whole' if whole else 'partial',
                                  **({} if whole else {'vertices': [[x, y, boundary['vertices'][0][2]] for x, y in ring(part)]}),
                                  evidence_kind='manual_annotation', source_refs=REFS,
                                  assumptions=['Continuous stair or roof envelope decomposition: this interface is not a physical slab.']))
    frame = dict(mesh_sha256=hashlib.sha256((DEMO / 'input.glb').read_bytes()).hexdigest(), yaw_degrees=15,
                 translation_m=[0, 0, 0], source_refs=[str(BASE.relative_to(ROOT) / 'source_model.json')],
                 reason='Preserve the selected demo local coordinate frame; approximate architectural alignment, not a surveyed transform.')
    proposal = dict(geometry=geometry.model_dump(mode='json'), mesh_frame=frame, assumptions=assumptions, unresolved=unresolved,
                    enclosure_declaration=dict(schema_version='source_enclosure_input_v1', base_source_model_sha256=base['source_model_sha256'],
                                               spaces=[], boundaries=enclosure))
    provenance = dict(method='Astra developer user-guided demo revision', product_model_calls=0, solver_calls=0,
                      baseline=str(BASE.relative_to(ROOT)), baseline_sha256=hashlib.sha256((BASE / 'source_model.json').read_bytes()).hexdigest(),
                      assembler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      roof_reference='AI_agent/logs/experiments/2026-09-16_voimatalo_completion/case_plan.json',
                      opening_mapping=mapping, scale_changes=regularisation)
    report = export_source_proposal(proposal, out, provenance=provenance)
    print(json.dumps({k: report.get(k) for k in ['source_geometry_ready', 'status', 'error', 'counts']}, ensure_ascii=False), flush=True)
    assert report['source_geometry_ready'], report.get('error') or report['source_geometry_self_consistency']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'candidate_01')
    parser.add_argument('--layout-only', action='store_true')
    args = parser.parse_args()
    build(args.out)
