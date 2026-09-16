"""Case-specific developer demonstration using shared source geometry operations.

All building decisions live in case_plan.json and aperture observations. This
script is a replayable example, not the future Agent's mandatory workflow.
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


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def ring(p):
    assert p.geom_type == 'Polygon' and not p.interiors and p.is_valid
    return [[round(x, 5), round(y, 5)] for x, y in list(orient(p, 1).exterior.coords)[:-1]]


def edges(p):
    points = ring(p)
    for a, b in zip(points, points[1:] + points[:1]):
        delta = np.array(b) - a
        yield a, b, np.array([delta[1], -delta[0]]) / np.linalg.norm(delta)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, default=HERE / 'case_plan.json')
    parser.add_argument('--apertures', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists(), 'Use a new candidate directory'
    plan = json.loads(args.plan.read_text())
    observed_document = json.loads(args.apertures.read_text())
    observed = observed_document
    if isinstance(observed, dict):
        observed = observed['openings']
    observed += plan.get('additional_openings', [])
    shell = plan['shell']
    west, east, south, north, inner, step, court = (shell[k] for k in ('west', 'east_end', 'south_end', 'north', 'court_long', 'court_step_x', 'court_short'))
    corner = shell['court_corner_y']
    def outline(w, e, s, n, inner_x=inner):
        return Polygon([[w, s], [inner_x, s], [inner_x, corner], [step, corner], [step, court], [e, court], [e, n], [w, n]])
    main_poly = outline(west, east, south, north)
    attic = Polygon(plan['attic_outline'])
    core_polys = {key: box(*values) for key, values in plan['inferred_core_rectangles'].items()}
    cores_union = unary_union(list(core_polys.values()))
    service_polys = {key: box(*values).difference(cores_union) for key, values in plan['inferred_service_rectangles'].items()}
    floors, rooms = [], []
    space_evidence = {}
    def add_floor(fid, z, height, rows, footprint, spanning=()):
        cells = []
        for key, poly, role, evidence in rows:
            sid = f'{fid}_{key}'
            x0, y0, x1, y1 = poly.bounds
            cells.append(Cell(id=sid, role=role, x=[x0, x1], y=[y0, y1], polygon=ring(poly)))
            rooms.append({'id': sid, 'floor': fid, 'z': z, 'height': height, 'poly': poly, 'role': role})
            space_evidence[sid] = evidence
        floors.append(Floor(name=fid, z_floor=z, ceiling_height=height, cells=cells, footprint=FootprintRing(vertices=ring(footprint)), spanning_space_ids=list(spanning)))
    services_union = unary_union(list(service_polys.values()))
    levels = plan['storey_levels_m']
    for number, (z, top) in enumerate(zip(levels, levels[1:]), 1):
        poly = attic if number == 8 else main_poly
        room_poly = poly.difference(cores_union.union(services_union))
        rows = [('open', room_poly, 'commercial_open_hypothesis' if number == 1 else 'office_open_hypothesis',
                 'Interior scenario: one connected L-shaped tenant/open-work space including circulation. Actual partitions are unavailable; do not interpret as verified open-plan layout.')]
        rows += [(key, p.intersection(poly), 'service_and_lobby_hypothesis', 'Explicit connected service/lobby-room hypothesis around the core; dimensions and partitions are not observations.') for key, p in service_polys.items()]
        add_floor(f'F{number}', z, top-z, rows, poly, [key+'_continuous' for key in core_polys])
    for key, poly in core_polys.items():
        add_floor(key, levels[0], levels[-1]-levels[0], [('continuous', poly, 'vertical_circulation_hypothesis',
                  'Continuous vertical circulation volume. Position, use and landing doors are internal hypotheses. No intermediate source slabs; no stair/elevator detail claimed.')], poly)
    annex = Polygon([[inner, shell['annex_south']], [shell['annex_east'], shell['annex_south']],
                     [shell['annex_east'], court], [step, court], [step, corner], [inner, corner]])
    add_floor('ANNEX', 0, shell['annex_roof'], [('open', annex, 'annex_merged_hypothesis',
              'Observed low mass, with one merged interior. Two window rows do not establish an internal slab. Main-building contact partition is assumed; actual connection is unknown.')], annex)
    for key, row in plan['roof_volumes'].items():
        poly = unary_union([box(*values) for values in row['rectangles']])
        add_floor(key, row['z'][0], row['z'][1]-row['z'][0], [('enclosure', poly, 'roof_enclosure_simplified', row['evidence'])], poly)

    facade_names = {'west': 'West', 'north': 'North', 'court_long': 'East', 'court_short': 'South', 'annex_east': 'East'}
    normals = {'West': [-1, 0], 'East': [1, 0], 'North': [0, 1], 'South': [0, -1]}
    windows, mappings = [], []
    for opening in observed:
        if opening.get('kind', 'window') != 'window':
            raise ValueError('Observed non-window must be placed explicitly in plan.inferred_entrances, never silently converted')
        view = opening['view']
        facade = opening.get('facade', facade_names.get(view))
        axis = 0 if facade in ('West', 'East') else 1
        plane_key = opening.get('plane_key', {'west': 'west', 'north': 'north', 'court_long': 'court_long', 'court_short': 'court_short', 'annex_east': 'annex_east'}.get(view))
        span, zz = opening['span_m'], opening['z_m']
        plane = shell[plane_key]
        if view == 'court_short' and span[1] <= step + 1e-6 and not opening.get('plane_key'):
            plane = corner
        owners = []
        for room in rooms:
            if zz[0] < room['z'] - 1e-6 or zz[1] > room['z'] + room['height'] + 1e-6:
                continue
            for a, b, normal in edges(room['poly']):
                if np.dot(normal, normals[facade]) < .99 or max(abs(a[axis]-plane), abs(b[axis]-plane)) > 1e-5:
                    continue
                lo, hi = sorted([a[1-axis], b[1-axis]])
                if lo - 1e-6 <= span[0] and hi + 1e-6 >= span[1]:
                    owners.append(room)
        if len(owners) != 1:
            failure = args.out.with_name(args.out.name + '_host_failure.json')
            write(failure, {'opening': opening, 'plane': plane, 'owners': [r['id'] for r in owners], 'plan': str(args.plan), 'reason': 'No clipping, span shifting or silent omission permitted.'})
            raise ValueError(f"Opening {opening['id']} has {len(owners)} complete hosts; see {failure}")
        owner = owners[0]
        windows.append(Window(id=opening['id'], floor=owner['floor'], room=owner['id'], facade=facade, span=span, z=zz))
        mappings.append({**opening, 'owner': owner['id'], 'facade': facade, 'regularised_plane_m': plane})

    doors = []
    by_id = {r['id']: r for r in rooms}
    # Choose a shared edge for each explicitly hypothesised connection. This
    # computes coordinates; it does not infer that such a door actually exists.
    def connect(aid, bid, z, name, width=.95):
        a, b = by_id[aid], by_id[bid]
        shared = a['poly'].boundary.intersection(b['poly'].boundary)
        lines = [shared] if shared.geom_type == 'LineString' else list(getattr(shared, 'geoms', []))
        lines = [line for line in lines if line.geom_type == 'LineString' and line.length > width + .3]
        if not lines:
            raise ValueError(f'No edge for declared interior connection {aid} / {bid}')
        edge = max(lines, key=lambda line: line.length)
        p1 = edge.interpolate((edge.length-width)/2)
        p2 = edge.interpolate((edge.length+width)/2)
        doors.append(WallOpening(id=name, kind='door', space_id=aid, other_space_id=bid,
                     p1=list(p1.coords)[0], p2=list(p2.coords)[0], z=[z, z+2.1],
                     source_refs=['case_plan.json: explicit hypothetical circulation scenario'],
                     assumptions=['Connection, landing and doorway dimensions are inferred; actual internal plan is unknown.']))
    for number, z in enumerate(levels[:-1], 1):
        fid = f'F{number}'
        for key in service_polys:
            connect(f'{fid}_open', f'{fid}_{key}', z, f'D_{fid}_{key}')
        for key in core_polys:
            connect(f'{fid}_open', f'{key}_continuous', z, f'D_{fid}_{key}')
    for row in plan['inferred_entrances']:
        axis, plane = row['axis'], shell[row['plane_key']]
        points = [[plane, s] if axis == 0 else [s, plane] for s in row['span_m']]
        doors.append(WallOpening(id=row['id'], kind='door', space_id=row['space_id'], other_space_id=None,
                     p1=points[0], p2=points[1], z=row['z_m'], source_refs=row['source_refs'], assumptions=[row['note']]))
    geometry = CorrectedGeometry(schema_version='2', footprint_x=[west, east], footprint_y=[south, north],
                                 floors=floors, windows=windows, openings=doors, notes='Developer tool-assisted partial-inference demonstration; source geometry is newly assembled, actual internal layout is unknown.')
    base = build_source_bim(geometry, capability_profile='orthogonal_polygon')
    unknown = []
    # Roof parts describe simplified exterior envelope components, not rooms.
    # Their horizontal contacts are logical seams, explicitly open on both sides.
    by_boundary = {b['id']: b for b in base['boundaries']}
    roof_contacts = {}
    for relation in base['boundary_relations']:
        pair = [by_boundary[bid] for bid in relation['boundary_ids']]
        if not all(b['space_id'].startswith('ROOF') for b in pair):
            continue
        if not all(b['geometry_type'] in ('floor', 'ceiling') for b in pair):
            continue
        for b in pair:
            roof_contacts.setdefault(b['id'], []).extend(Polygon([v[:2] for v in r['vertices']]) for r in relation['regions'])
    for bid, patches in roof_contacts.items():
        b = by_boundary[bid]
        parent = Polygon([v[:2] for v in b['vertices']])
        contact = unary_union(patches)
        assert parent.buffer(1e-7).covers(contact)
        whole = parent.symmetric_difference(contact).area < 1e-8
        parts = [contact] if contact.geom_type == 'Polygon' else list(contact.geoms)
        for p in parts:
            assert not p.interiors, 'Declare non-holed individual roof contact regions'
            unknown.append({'boundary_id': bid, 'condition': 'open', 'scope': 'whole' if whole else 'partial',
                            **({} if whole else {'vertices': [[x,y,b['vertices'][0][2]] for x,y in list(p.exterior.coords)[:-1]]}),
                            'evidence_kind': 'manual_annotation', 'source_refs': ['case_plan.json:roof_volumes', 'roof/sections.json'],
                            'assumptions': ['Logical interface between simplified roof envelope parts; no physical slab or actual room partition is asserted.']})
    for boundary in base['boundaries']:
        if boundary['geometry_type'] != 'wall' or boundary['adjacent_space_ids']:
            continue
        v = np.array(boundary['vertices'])
        is_end = (np.ptp(v[:, 0]) < 1e-6 and abs(v[0, 0]-east) < 1e-5) or (np.ptp(v[:, 1]) < 1e-6 and abs(v[0, 1]-south) < 1e-5)
        is_attic_end = (np.ptp(v[:, 0]) < 1e-6 and abs(v[0, 0]-shell['attic_east_end']) < 1e-5) or (np.ptp(v[:, 1]) < 1e-6 and abs(v[0, 1]-shell['attic_south_end']) < 1e-5)
        is_core_gap = ('services_s' in boundary['space_id'] and np.ptp(v[:, 0]) < 1e-6
                       and min(abs(v[0,0]-inner),abs(v[0,0]-shell['attic_court_long'])) < 1e-5
                       and v[:,1].min() >= -27.4-1e-5 and v[:,1].max() <= -23.7+1e-5)
        if is_end or is_attic_end or is_core_gap:
            unknown.append({'boundary_id': boundary['id'], 'condition': 'unknown', 'scope': 'whole',
                            'evidence_kind': 'manual_annotation', 'source_refs': ['evidence_01/sections.json: missing or incomplete traces in supplied single-building mesh'],
                            'assumptions': ['Logical boundary retained; supplied asset does not establish enclosure/openings here. No parent-tile evidence imported.']})
    proposal = {'geometry': geometry.model_dump(mode='json'), 'mesh_frame': plan['mesh_frame'],
                'assumptions': plan['assumptions'], 'unresolved': plan['unresolved'],
                'enclosure_declaration': {'schema_version': 'source_enclosure_input_v1',
                    'base_source_model_sha256': base['source_model_sha256'], 'spaces': [], 'boundaries': unknown}}
    provenance = {'method': 'development_assistant_tool_assisted_new_assembly', 'product_model_calls': 0,
                  'plan_sha256': hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                  'apertures_sha256': hashlib.sha256(args.apertures.read_bytes()).hexdigest(),
                  'assembler_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'space_evidence': space_evidence, 'opening_evidence': mappings,
                  'aperture_input_metadata': {k:v for k,v in observed_document.items() if k!='openings'} if isinstance(observed_document,dict) else {},
                  'prior_context': 'Development assistant has seen previous results; no independent cold-start claim.'}
    report = export_source_proposal(proposal, args.out, provenance=provenance)
    write(args.out / 'opening_mapping.json', mappings)
    print(json.dumps({'ready': report['source_geometry_ready'], 'status': report['status'], 'error': report.get('error'), 'counts': report.get('counts'), 'validation': report.get('source_geometry_self_consistency')}, ensure_ascii=False))
    if not report['source_geometry_ready']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
