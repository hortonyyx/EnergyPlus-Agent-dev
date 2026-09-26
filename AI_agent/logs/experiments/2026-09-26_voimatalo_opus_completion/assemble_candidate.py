"""Assemble the 09-26 Voimatalo completion candidate from frozen inputs.

Copy of the 09-25 assembler (same pinned 09-16 plan/apertures and 09-25 measured
street windows) driven by ``case_plan_v3.json``.  Only two behaviours differ:
inferred window rows may carry their own ``basis`` (the courtyard glazed column
is justified differently from the north ground shopfronts), and provenance
records this directory's plan.  All geometry still goes through the shared
source-BIM entry point and fails loudly instead of clipping or moving openings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.correction.schema import Cell, CorrectedGeometry, Floor, FootprintRing, Window, WallOpening
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_bim import build_source_bim

FACADE_NAMES = {'west': 'West', 'north': 'North', 'court_long': 'East', 'court_short': 'South', 'annex_east': 'East'}
NORMALS = {'West': [-1, 0], 'East': [1, 0], 'North': [0, 1], 'South': [0, -1]}


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pinned(relative: str, digest: str) -> dict:
    path = ROOT / relative
    if sha256(path) != digest:
        raise ValueError(f'{relative} changed; pinned sha256 {digest}')
    return json.loads(path.read_text())


def clean_ring(poly: Polygon) -> list[list[float]]:
    """CCW orthogonal ring without repeated or collinear vertices."""
    assert poly.geom_type == 'Polygon' and not poly.interiors and poly.is_valid, poly
    points = [(round(x, 5), round(y, 5)) for x, y in list(orient(poly, 1).exterior.coords)[:-1]]
    changed = True
    while changed:
        changed = False
        for index in range(len(points)):
            a, b, c = points[index - 1], points[index], points[(index + 1) % len(points)]
            if b == a or (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                points.pop(index)
                changed = True
                break
    return [list(p) for p in points]


def as_polygon(zone: dict) -> Polygon:
    if 'polygon' in zone:
        return Polygon(zone['polygon'])
    return unary_union([box(*rect) for rect in zone['rects']])


def edges(ring_points):
    for a, b in zip(ring_points, ring_points[1:] + ring_points[:1]):
        delta = np.array(b) - a
        yield a, b, np.array([delta[1], -delta[0]]) / np.linalg.norm(delta)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, default=HERE / 'case_plan_v3.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists(), 'Use a new candidate directory'
    plan = json.loads(args.plan.read_text())
    parent = load_pinned(plan['parent']['plan'], plan['parent']['plan_sha256'])
    observed_document = load_pinned(plan['parent']['apertures'], plan['parent']['apertures_sha256'])
    observed = list(observed_document['openings']) + list(parent.get('additional_openings', []))
    extra = plan.get('extra_observed_windows')
    if extra:
        observed += load_pinned(extra['path'], extra['sha256'])['openings']
    inferred_windows = [{**row, 'inferred_not_observed': True, 'basis': row.get('basis', plan['inferred_windows']['basis'])}
                        for row in plan['inferred_windows']['rows']]

    shell = parent['shell']
    west, east, south, north, inner, step, court = (shell[k] for k in ('west', 'east_end', 'south_end', 'north', 'court_long', 'court_step_x', 'court_short'))
    corner = shell['court_corner_y']
    main_poly = Polygon([[west, south], [inner, south], [inner, corner], [step, corner], [step, court], [east, court], [east, north], [west, north]])
    attic = Polygon(parent['attic_outline'])
    levels = parent['storey_levels_m']
    storey = {f'F{n}': (z, top) for n, (z, top) in enumerate(zip(levels, levels[1:]), 1)}

    floors, rooms, space_evidence, space_roles = [], [], {}, {}

    def add_floor(fid, z, height, rows, footprint, spanning=()):
        cells = []
        for sid, poly, role, evidence in rows:
            ring = clean_ring(poly)
            x0, y0, x1, y1 = poly.bounds
            cells.append(Cell(id=sid, role=role, x=[x0, x1], y=[y0, y1], polygon=ring))
            rooms.append({'id': sid, 'floor': fid, 'z': z, 'height': height, 'poly': Polygon(ring), 'ring': ring, 'role': role})
            space_evidence[sid] = evidence
            space_roles[sid] = role
        floors.append(Floor(name=fid, z_floor=z, ceiling_height=height, cells=cells,
                            footprint=FootprintRing(vertices=clean_ring(footprint)), spanning_space_ids=list(spanning)))

    continuous = {row['key']: row for row in plan['continuous_spaces']}
    continuous_ids = {key: f"{key}_{row['cell']}" for key, row in continuous.items()}

    def local_zones(fid):
        if fid == 'F1':
            return plan['floor_layouts']['F1']
        typical = plan['floor_layouts']['typical']
        assert fid in typical['floors']
        return [zone for zone in typical['zones'] if fid in zone.get('only_floors', typical['floors'])]

    # 09-26: a continuous space outside the frozen shell (the cropped courtyard tower) extends the
    # storey footprints it spans; zones are still clipped to the frozen shell only.
    extensions = {fid: [box(*row['rect']) for row in continuous.values()
                        if row.get('extends_storey_footprint') and fid in row['floors']] for fid in storey}
    for fid, (z, top) in storey.items():
        outline = attic if fid == 'F8' else main_poly
        footprint = unary_union([outline, *extensions[fid]]) if extensions[fid] else outline
        rows = []
        for zone in local_zones(fid):
            poly = as_polygon(zone).intersection(outline)
            # Clipping may leave zero-area touching lines; only area parts count.
            parts = [p for p in getattr(poly, 'geoms', [poly]) if p.geom_type == 'Polygon' and p.area > 1e-9]
            poly = parts[0] if len(parts) == 1 else poly
            if poly.geom_type != 'Polygon' or poly.area < 1e-6:
                raise ValueError(f'{fid}/{zone["key"]}: zone clips to {poly.geom_type}; declare it explicitly')
            rows.append((f'{fid}_{zone["key"]}', poly, zone['role'], zone['evidence']))
        spanning = [continuous_ids[key] for key, row in continuous.items() if fid in row['floors']]
        add_floor(fid, z, top - z, rows, footprint, spanning)
    for key, row in continuous.items():
        poly = box(*row['rect'])
        z0, z1 = row['z']
        add_floor(key, z0, z1 - z0, [(continuous_ids[key], poly, row['role'], row['evidence'])], poly)
    annex = Polygon([[inner, shell['annex_south']], [shell['annex_east'], shell['annex_south']],
                     [shell['annex_east'], court], [step, court], [step, corner], [inner, corner]])
    annex_id = f"ANNEX_{plan['annex']['key']}"
    add_floor('ANNEX', 0, shell['annex_roof'], [(annex_id, annex, plan['annex']['role'], plan['annex']['evidence'])], annex)
    for key, row in parent['roof_volumes'].items():
        poly = unary_union([box(*values) for values in row['rectangles']])
        add_floor(key, row['z'][0], row['z'][1] - row['z'][0], [(f'{key}_enclosure', poly, 'roof_enclosure_simplified', row['evidence'])], poly)

    # Windows: same complete-host rule as the 09-16 assembler; no clipping or shifting.
    windows, mappings = [], []
    for opening in observed + inferred_windows:
        if opening.get('kind', 'window') != 'window':
            raise ValueError('non-window observation must be declared as a door')
        view = opening['view']
        facade = opening.get('facade', FACADE_NAMES.get(view))
        axis = 0 if facade in ('West', 'East') else 1
        plane_key = opening.get('plane_key', view)
        span, zz = opening['span_m'], opening['z_m']
        plane = shell[plane_key]
        if view == 'court_short' and span[1] <= step + 1e-6 and not opening.get('plane_key'):
            plane = corner
        owners = []
        for room in rooms:
            if zz[0] < room['z'] - 1e-6 or zz[1] > room['z'] + room['height'] + 1e-6:
                continue
            for a, b, normal in edges(room['ring']):
                if np.dot(normal, NORMALS[facade]) < .99 or max(abs(a[axis] - plane), abs(b[axis] - plane)) > 1e-5:
                    continue
                lo, hi = sorted([a[1 - axis], b[1 - axis]])
                if lo - 1e-6 <= span[0] and hi + 1e-6 >= span[1]:
                    owners.append(room)
        if len(owners) != 1:
            failure = args.out.with_name(args.out.name + '_host_failure.json')
            write(failure, {'opening': opening, 'plane': plane, 'owners': [r['id'] for r in owners],
                            'reason': 'No clipping, span shifting or silent omission permitted.'})
            raise ValueError(f"Opening {opening['id']} has {len(owners)} complete hosts; see {failure}")
        owner = owners[0]
        windows.append(Window(id=opening['id'], floor=owner['floor'], room=owner['id'], facade=facade, span=span, z=zz))
        mappings.append({**opening, 'owner': owner['id'], 'facade': facade, 'regularised_plane_m': plane})

    by_id = {r['id']: r for r in rooms}
    doors = []

    def connect(aid, bid, z, name, width=.95):
        a, b = by_id[aid], by_id[bid]
        shared = a['poly'].boundary.intersection(b['poly'].boundary)
        lines = [shared] if shared.geom_type == 'LineString' else list(getattr(shared, 'geoms', []))
        lines = [line for line in lines if line.geom_type == 'LineString' and line.length > width + .3]
        if not lines:
            raise ValueError(f'No edge for declared interior connection {aid} / {bid}')
        edge = max(lines, key=lambda line: line.length)
        p1 = edge.interpolate((edge.length - width) / 2)
        p2 = edge.interpolate((edge.length + width) / 2)
        doors.append(WallOpening(id=name, kind='door', space_id=aid, other_space_id=bid,
                                 p1=list(p1.coords)[0], p2=list(p2.coords)[0], z=[z, z + 2.1],
                                 source_refs=['case_plan_v3.json:connections'],
                                 assumptions=['Representative connection; door position, width and count are inferred. Actual internal plan is unknown.']))

    def resolve(fid, key):
        if key in continuous:
            return continuous_ids[key] if fid in continuous[key]['floors'] else None
        if key == annex_id:
            return annex_id
        sid = f'{fid}_{key}'
        return sid if sid in by_id else None

    skipped = []
    for fid, (z, _) in storey.items():
        pairs = plan['connections']['F1' if fid == 'F1' else 'typical']
        for a_key, b_key in pairs:
            aid, bid = resolve(fid, a_key), resolve(fid, b_key)
            if aid is None or bid is None:
                skipped.append([fid, a_key, b_key])
                continue
            connect(aid, bid, z, f'D_{fid}_{a_key}_{b_key}')

    overrides = plan['entrance_space_overrides']
    for row in parent['inferred_entrances']:
        axis, plane = row['axis'], shell[row['plane_key']]
        points = [[plane, s] if axis == 0 else [s, plane] for s in row['span_m']]
        doors.append(WallOpening(id=row['id'], kind='door', space_id=overrides[row['id']], other_space_id=None,
                                 p1=points[0], p2=points[1], z=row['z_m'], source_refs=row['source_refs'],
                                 assumptions=[row['note'], 'Space assignment revised in case_plan_v3.json; geometry unchanged.']))
    for row in plan['inferred_exterior_doors']:
        axis, plane = row['axis'], shell[row['plane_key']]
        points = [[plane, s] if axis == 0 else [s, plane] for s in row['span_m']]
        doors.append(WallOpening(id=row['id'], kind='door', space_id=row['space'], other_space_id=None,
                                 p1=points[0], p2=points[1], z=row['z_m'], source_refs=row['source_refs'],
                                 assumptions=['Inferred completion, not observed: ' + row['basis']]))

    geometry = CorrectedGeometry(schema_version='2', footprint_x=[west, east], footprint_y=[south, north],
                                 floors=floors, windows=windows, openings=doors,
                                 notes='Opus 5.5 developer revision (09-26 courtyard tower completion): interior organisation and completion are explicit hypotheses constrained by observed openings; actual internal layout is unknown.')
    base = build_source_bim(geometry, capability_profile='orthogonal_polygon')
    by_boundary = {b['id']: b for b in base['boundaries']}
    space_of = {s['id']: s for s in base['spaces']}

    # --- Horizontal open contacts: roof-part seams and declared stair/core continuations.
    open_patches, open_reasons = {}, {}
    declared = {(row['lower'], row['upper']): row['reason'] for row in plan['enclosure']['open_horizontal_contacts']}
    used_declared = set()
    for relation in base['boundary_relations']:
        pair = [by_boundary[bid] for bid in relation['boundary_ids']]
        if not all(b['geometry_type'] in ('floor', 'ceiling') for b in pair):
            continue
        roof = all(b['space_id'].startswith('ROOF') for b in pair)
        lower = next((b for b in pair if b['geometry_type'] == 'ceiling'), None)
        upper = next((b for b in pair if b['geometry_type'] == 'floor'), None)
        key = (lower['space_id'], upper['space_id']) if lower and upper else None
        if not roof and key not in declared:
            continue
        reason = ('Logical interface between simplified roof envelope parts; no physical slab or actual room partition is asserted.'
                  if roof else declared[key])
        refs = ['case_plan.json:roof_volumes', 'roof/sections.json'] if roof else ['case_plan_v3.json:enclosure.open_horizontal_contacts']
        if key in declared:
            used_declared.add(key)
        for b in pair:
            open_patches.setdefault(b['id'], []).extend(Polygon([v[:2] for v in r['vertices']]) for r in relation['regions'])
            open_reasons[b['id']] = (reason, refs)
    missing = set(declared) - used_declared
    if missing:
        raise ValueError(f'declared open contacts without source relation: {sorted(missing)}')
    enclosure_rows = []
    for bid, patches in open_patches.items():
        b = by_boundary[bid]
        parent_poly = Polygon([v[:2] for v in b['vertices']])
        contact = unary_union(patches)
        assert parent_poly.buffer(1e-7).covers(contact)
        whole = parent_poly.symmetric_difference(contact).area < 1e-8
        reason, refs = open_reasons[bid]
        for part in ([contact] if contact.geom_type == 'Polygon' else list(contact.geoms)):
            assert not part.interiors
            enclosure_rows.append({'boundary_id': bid, 'condition': 'open', 'scope': 'whole' if whole else 'partial',
                                   **({} if whole else {'vertices': [[x, y, b['vertices'][0][2]] for x, y in list(part.exterior.coords)[:-1]]}),
                                   'evidence_kind': 'manual_annotation', 'source_refs': refs, 'assumptions': [reason]})

    # --- Unknown wall regions (partial), resolved to the single matching wall boundary.
    def wall_on_plane(space_id, axis_name, value, along):
        axis = 0 if axis_name == 'x' else 1
        found = []
        for b in base['boundaries']:
            if b['space_id'] != space_id or b['geometry_type'] != 'wall':
                continue
            v = np.array(b['vertices'])
            if np.ptp(v[:, axis]) > 1e-6 or abs(v[0, axis] - value) > 1e-5:
                continue
            lo, hi = v[:, 1 - axis].min(), v[:, 1 - axis].max()
            if lo - 1e-6 <= along[0] and hi + 1e-6 >= along[1]:
                found.append(b)
        if len(found) != 1:
            raise ValueError(f'{space_id}: expected one wall on {axis_name}={value} covering {along}, found {len(found)}')
        return found[0]

    def expand(row):
        if 'space' in row:
            return [row]
        prefix, suffix = row['space_pattern'].split('{')[0], row['space_pattern'].split('}')[1]
        first, last = (int(v) for v in row['space_pattern'].split('{')[1].split('}')[0].split('..'))
        return [{**row, 'space': f'{prefix}{n}{suffix}'} for n in range(first, last + 1)]

    unknown_rows = [r for row in plan['enclosure']['unknown_wall_regions'] for r in expand(row)]
    for row in unknown_rows:
        space = space_of[row['space']]
        z0, z1 = (space['z_floor'], space['z_floor'] + space['height']) if row['z'] == 'storey' else row['z']
        axis_name, value = row['plane']
        b = wall_on_plane(row['space'], axis_name, value, row['along'])
        a0, a1 = row['along']
        quad = ([[value, a0, z0], [value, a1, z0], [value, a1, z1], [value, a0, z1]] if axis_name == 'x'
                else [[a0, value, z0], [a1, value, z0], [a1, value, z1], [a0, value, z1]])
        v = np.array(b['vertices'])
        axis = 0 if axis_name == 'x' else 1
        whole = (abs(v[:, 1 - axis].min() - a0) < 1e-6 and abs(v[:, 1 - axis].max() - a1) < 1e-6
                 and abs(v[:, 2].min() - z0) < 1e-6 and abs(v[:, 2].max() - z1) < 1e-6)
        enclosure_rows.append({'boundary_id': b['id'], 'condition': 'unknown', 'scope': 'whole' if whole else 'partial',
                               **({} if whole else {'vertices': quad}), 'evidence_kind': 'manual_annotation',
                               'source_refs': ['case_plan_v3.json:enclosure.unknown_wall_regions', 'observations/manifest.json'],
                               'assumptions': [row['reason']]})

    # --- Attic end walls stay unknown; lower short ends are party walls (physical, annotated).
    ends = plan['enclosure']['unknown_attic_ends']
    party = plan['enclosure']['party_walls']
    party_rows = []
    for b in base['boundaries']:
        if b['geometry_type'] != 'wall' or b['adjacent_space_ids']:
            continue
        v = np.array(b['vertices'])
        on_x = lambda value: np.ptp(v[:, 0]) < 1e-6 and abs(v[0, 0] - value) < 1e-5
        on_y = lambda value: np.ptp(v[:, 1]) < 1e-6 and abs(v[0, 1] - value) < 1e-5
        fid = next(r['floor'] for r in rooms if r['id'] == b['space_id'])
        if fid == 'F8' and (on_y(ends['south_y']) or on_x(ends['east_x'])):
            enclosure_rows.append({'boundary_id': b['id'], 'condition': 'unknown', 'scope': 'whole', 'evidence_kind': 'manual_annotation',
                                   'source_refs': ['AI_agent/logs/experiments/2026-09-15_voimatalo_developer_walkthrough/evidence_01/sections.json'],
                                   'assumptions': [ends['reason']]})
        elif on_y(party['south_y']) or on_x(party['east_x']):
            zmax = float(v[:, 2].max())
            if zmax > storey['F7'][1] + 1e-6:
                raise ValueError(f"party wall rule reached above F7: {b['id']}")
            party_rows.append({'boundary_id': b['id'], 'space_id': b['space_id'], 'plane': 'y=-33.4' if on_y(party['south_y']) else 'x=19.5',
                               'z_m': [float(v[:, 2].min()), zmax]})

    proposal = {'geometry': geometry.model_dump(mode='json'), 'mesh_frame': parent['mesh_frame'],
                'assumptions': plan['assumptions'], 'unresolved': plan['unresolved'],
                'enclosure_declaration': {'schema_version': 'source_enclosure_input_v1',
                                          'base_source_model_sha256': base['source_model_sha256'],
                                          'spaces': [], 'boundaries': enclosure_rows}}
    provenance = {'method': 'development_assistant_tool_assisted_revision', 'developer_model': 'claude-opus-5-5',
                  'product_model_calls': 0,
                  'plan_sha256': sha256(args.plan), 'parent_plan_sha256': plan['parent']['plan_sha256'],
                  'apertures_sha256': plan['parent']['apertures_sha256'],
                  'assembler_sha256': sha256(Path(__file__)),
                  'space_evidence': space_evidence, 'space_roles': space_roles,
                  'opening_evidence': mappings,
                  'party_wall_inference': {'reason': party['reason'], 'source_refs': party['source_refs'],
                                           'representation': party['representation'], 'boundaries': party_rows},
                  'skipped_connection_pairs': skipped,
                  'aperture_input_metadata': {k: v for k, v in observed_document.items() if k != 'openings'},
                  'prior_context': 'Developer has seen previous candidates and the user rejection; no independent cold-start claim.'}
    report = export_source_proposal(proposal, args.out, provenance=provenance)
    write(args.out / 'opening_mapping.json', mappings)
    print(json.dumps({'ready': report['source_geometry_ready'], 'status': report['status'], 'error': report.get('error'),
                      'counts': report.get('counts'), 'validation': report.get('source_geometry_self_consistency')}, ensure_ascii=False))
    if not report['source_geometry_ready']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
