"""Revise inferred room entrances from the saved demo candidate; no model call."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.correction.schema import CorrectedGeometry, FootprintRing
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_bim import build_source_bim

PREVIOUS = HERE.parent / '2026-09-30_voimatalo_user_revision'
PARENT = PREVIOUS / 'candidate_01'
JAMB = .25  # source partition representative line to nearest aperture edge
WIDTH = .9
REFS = ['2026-10-01 user feedback: paired room entrances beside dividing partitions',
        str((PARENT / 'source_model.json').relative_to(ROOT))]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def fronts(room, target):
    shared = room.boundary.intersection(target.boundary)
    lines = [shared] if shared.geom_type == 'LineString' else list(getattr(shared, 'geoms', []))
    result = []
    for line in lines:
        if line.geom_type != 'LineString' or line.length < WIDTH + 2 * JAMB - 1e-7:
            continue
        x0, y0, x1, y1 = line.bounds
        if abs(x0-x1) < 1e-7:
            result.append(dict(axis=1, plane=round(x0, 5), lo=round(y0, 5), hi=round(y1, 5)))
        elif abs(y0-y1) < 1e-7:
            result.append(dict(axis=0, plane=round(y0, 5), lo=round(x0, 5), hi=round(x1, 5)))
    return result


def xy(front, position):
    return [round(position, 5), front['plane']] if front['axis'] == 0 else [front['plane'], round(position, 5)]


def adjacent(a, b):
    return (a['axis'] == b['axis'] and a['plane'] == b['plane'] and
            (abs(a['hi']-b['lo']) < 1e-7 or abs(b['hi']-a['lo']) < 1e-7))


def swing(poly, front, anchor, toward):
    hinge_at = anchor + toward * JAMB
    hinge = xy(front, hinge_at)
    tangent = [toward, 0] if front['axis'] == 0 else [0, toward]
    midpoint = xy(front, hinge_at + toward * WIDTH / 2)
    normal = [-tangent[1], tangent[0]]
    if not poly.covers(Point(midpoint[0]+.01*normal[0], midpoint[1]+.01*normal[1])):
        normal = [-v for v in normal]
    arc = [[round(hinge[j] + WIDTH*(math.cos(t)*tangent[j]+math.sin(t)*normal[j]), 7) for j in range(2)]
           for t in [i*math.pi/64 for i in range(33)]]
    sector = Polygon([hinge]+arc)
    assert poly.buffer(1e-6).covers(sector), ('Door swing intersects room boundary', front, anchor)
    return {'hinge_xy': hinge, 'arc_xy': arc, 'sector_xy': [hinge]+arc,
            'leaf_open_xy': [hinge, arc[-1]], 'assumption': 'Single leaf opens into its room; illustrative, not observed hardware.'}


def build(output, layout_only=False):
    proposal = json.loads((PARENT / 'proposal.json').read_text())
    parent_source = json.loads((PARENT / 'source_model.json').read_text())
    polys = {s['id']: Polygon(s['polygon']) for s in parent_source['spaces']}
    spaces = {s['id']: s for s in parent_source['spaces']}
    doors = proposal['geometry']['openings']
    originals = {d['id']: copy.deepcopy(d) for d in doors}
    candidates, assignments = {}, {}
    for door in doors:
        sid = door['space_id']
        s = spaces[sid]
        if s['floor_id'] not in [f'F{i}' for i in range(2, 8)] or s['role'] == 'corridor':
            continue
        hallway = f"{s['floor_id']}_hall"
        choices = fronts(polys[sid], polys[hallway])
        target = hallway if choices else door['other_space_id']
        if not choices:
            choices = fronts(polys[sid], polys[target])
        assert choices, door['id']
        family = 'office' if s['role'] == 'office/enclosed' else 'service' if s['role'] in ('restroom', 'electrical/mechanical') else s['role']
        candidates[sid] = {'door': door, 'target': target, 'fronts': choices, 'floor': s['floor_id'], 'family': family}

    # Select a corridor-facing wall that continues the adjacent-room sequence;
    # the longest wall is not necessarily the sensible room entrance facade.
    for sid, row in candidates.items():
        def score(front):
            neighbors = sum(any(adjacent(front, other) for other in r['fronts']) for rid, r in candidates.items()
                            if rid != sid and r['floor'] == row['floor'] and r['target'] == row['target'])
            return neighbors, front['hi']-front['lo'], -front['axis']
        row['front'] = max(row['fronts'], key=score)

    groups = defaultdict(list)
    for sid, row in candidates.items():
        f = row['front']
        groups[(row['floor'], row['target'], row['family'], f['axis'], f['plane'])].append(sid)
    pairs = []
    for key, members in sorted(groups.items()):
        members.sort(key=lambda sid: candidates[sid]['front']['lo'])
        i = 0
        while i < len(members):
            a = members[i]
            if i+1 < len(members):
                b = members[i+1]
                fa, fb = candidates[a]['front'], candidates[b]['front']
                if adjacent(fa, fb):
                    shared_partition = polys[a].boundary.intersection(polys[b].boundary)
                    joint = fa['hi']
                    assert shared_partition.length > 1 and shared_partition.distance(Point(xy(fa, joint))) < 1e-7
                    pair_id = f"PAIR_{len(pairs)+1:03}"
                    assignments[a] = {'anchor': joint, 'toward': -1, 'pair': pair_id, 'paired_space': b}
                    assignments[b] = {'anchor': joint, 'toward': 1, 'pair': pair_id, 'paired_space': a}
                    pairs.append({'id': pair_id, 'spaces': [a, b], 'partition_at': xy(fa, joint),
                                  'door_ids': [candidates[a]['door']['id'], candidates[b]['door']['id']]})
                    i += 2
                    continue
            f = candidates[a]['front']
            old = originals[candidates[a]['door']['id']]
            center = (old['p1'][f['axis']]+old['p2'][f['axis']])/2
            hall = polys[f"{candidates[a]['floor']}_hall"]
            anchor = min([f['lo'], f['hi']], key=lambda x: (hall.distance(Point(xy(f, x))), abs(x-center), x))
            assignments[a] = {'anchor': anchor, 'toward': 1 if anchor == f['lo'] else -1,
                              'pair': None, 'paired_space': None}
            i += 1

    changes = []
    for sid, row in candidates.items():
        a = assignments[sid]
        f, door = row['front'], row['door']
        old = originals[door['id']]
        p1 = xy(f, a['anchor']+a['toward']*JAMB)
        p2 = xy(f, a['anchor']+a['toward']*(JAMB+WIDTH))
        door.update(p1=p1, p2=p2, other_space_id=row['target'])
        door['source_refs'] = list(dict.fromkeys(door['source_refs']+REFS))
        door['assumptions'] = [
            '推断的房间入口：优先直接接走廊，门贴隔墙一侧布置；相邻房间在共同隔墙两侧镜像成对布门。',
            '本版普通房门洞宽统一0.90m，距隔墙代表线留0.25m；该预留为建模假设，不是实测门垛或已解析实体墙厚。',
            '单扇向房间内开启，铰接端靠隔墙；仅核查平面开启空间，未指定真实门扇五金。',
            f"Paired with {a['paired_space']}" if a['pair'] else '序列端部／特殊接入单门：保留靠墙门垛，不为成对而添加门或隔墙。',
        ]
        sw = swing(polys[sid], f, a['anchor'], a['toward'])
        changes.append({'id': door['id'], 'room': sid, 'floor': row['floor'], 'pair': a['pair'],
                        'paired_space': a['paired_space'], 'front': f, 'partition_at': xy(f, a['anchor']),
                        'offset_from_partition_line_m': JAMB, 'width_m': WIDTH, 'swing': sw,
                        'before': {k: old[k] for k in ['p1', 'p2', 'space_id', 'other_space_id', 'z']},
                        'after': {k: door[k] for k in ['p1', 'p2', 'space_id', 'other_space_id', 'z']}})

    proposal['assumptions'].extend([
        '10-01用户修订：标准层房门按门垛与相邻隔墙关系布置，不再默认共墙居中；交通和电梯门按平台／设备关系处理。',
        '两端补实、无窗是依有限邻楼上下文作出的贴邻墙／露出山墙推断；遮挡和露出部分实际有无窗均未确认，不能视作缺图默认无窗。',
        '信息不足且多种推断均合理时，倾向更简单的方案；具体边界暂不固化。前厅交通用户认为稍复杂但可接受，本次保持。',
    ])
    proposal['geometry']['notes'] += ' October 1: inferred room entrances paired beside partitions, corridor access preferred.'
    audit = {'parent_source_model_sha256': parent_source['source_model_sha256'],
             'paired_groups': pairs, 'changed_doors': changes,
             'unchanged_doors': sorted(set(originals)-{r['id'] for r in changes}),
             'scope': 'Standard-storey room entrances. Building entrances, lift doors, stair landing doors and annex circulation retained.'}
    write(HERE / 'door_layout.json', audit)
    print(json.dumps({'room_doors': len(changes), 'pairs': len(pairs),
                      'changed_connections': sum(r['before']['other_space_id'] != r['after']['other_space_id'] for r in changes)}, ensure_ascii=False), flush=True)
    if layout_only:
        return
    geometry = CorrectedGeometry.model_validate(proposal['geometry'])
    for floor in geometry.floors:
        floor.footprint = FootprintRing.model_validate(floor.footprint)
    base = build_source_bim(geometry, capability_profile='orthogonal_polygon')
    write(HERE / 'base_validation.json', base['validation'])
    assert base['validation']['status'] == 'pass', base['validation']
    proposal['enclosure_declaration']['base_source_model_sha256'] = base['source_model_sha256']
    end_walls = []
    for b in base['boundaries']:
        if b['geometry_type'] != 'wall' or b['adjacent_space_ids']:
            continue
        xs, ys = [v[0] for v in b['vertices']], [v[1] for v in b['vertices']]
        if (max(ys)-min(ys) < 1e-7 and min(ys) in [-33.4, -32.3]) or (max(xs)-min(xs) < 1e-7 and min(xs) in [18.9, 17.8]):
            end_walls.append({'boundary_id': b['id'], 'decision': 'inferred solid party/gable wall without windows',
                              'source_refs': ['AI_agent/logs/experiments/2026-09-10_showcase_voimatalo_revision/context/courtyard.png',
                                              'AI_agent/logs/experiments/2026-09-10_showcase_voimatalo_revision/context/top.png'],
                              'assumptions': ['邻楼局部上下文支持贴邻／山墙解释；本候选采用实体无窗墙。露出和遮挡区域的真实窗均未确认，有窗亦属可能合理方案；缺图本身不是无窗依据。']})
    write(HERE / 'end_wall_inference.json', end_walls)
    provenance = copy.deepcopy(parent_source['generation']['provenance'])
    provenance.update(method='Astra developer user-guided partition-side room entrance revision',
                      parent_source_model_sha256=parent_source['source_model_sha256'],
                      parent_proposal_file_sha256=hashlib.sha256((PARENT/'proposal.json').read_bytes()).hexdigest(),
                      assembler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      door_layout=audit, end_wall_inference=end_walls, product_model_calls=0, solver_calls=0)
    report = export_source_proposal(proposal, output, provenance=provenance)
    print(json.dumps({k: report.get(k) for k in ['source_geometry_ready', 'status', 'error', 'counts']}, ensure_ascii=False), flush=True)
    assert report['source_geometry_ready'], report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'candidate_02')
    parser.add_argument('--layout-only', action='store_true')
    args = parser.parse_args()
    build(args.out, args.layout_only)
