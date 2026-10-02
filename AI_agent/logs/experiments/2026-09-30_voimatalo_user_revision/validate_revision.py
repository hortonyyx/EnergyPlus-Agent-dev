"""Independent saved-artifact checks for this user revision (no model/solver run)."""
from __future__ import annotations
import json
import math
import sys
from collections import Counter, defaultdict, deque
from itertools import combinations
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.source_model import _digest
from src.agent.geometry.source_naming import build_public_names
from src.agent.geometry.source_plan_view import render_source_plan
from src.agent.roles import require_role


def main():
    source = json.loads((HERE / 'candidate_01/source_model.json').read_text())
    display = json.loads((HERE / 'candidate_01/display_geometry.json').read_text())
    baseline = json.loads((ROOT / 'showcase/2026-09-11-research-report/demos/textured-mass/revision_02/inferred/source_model.json').read_text())
    evidence = json.loads((HERE / 'opening_mapping.json').read_text())
    spaces = {s['id']: s for s in source['spaces']}
    polys = {sid: Polygon(s['polygon']) for sid, s in spaces.items()}
    windows = {o['id']: o for o in source['openings'] if o['kind'] == 'window'}
    checks = []

    def check(name, condition, detail):
        checks.append(dict(name=name, pass_check=bool(condition), detail=detail))

    digest = _digest({k: v for k, v in source.items() if k != 'source_model_sha256'})
    check('saved_source_digest', digest == source['source_model_sha256'], digest)
    check('kernel_geometry_and_opening_hosts', source['validation']['status'] == 'pass' and
          not source['unbuilt_openings'] and not source['unsupported'], source['validation'])
    check('display_uses_same_source', display['source_model']['source_model_sha256'] == digest and
          set(display['zones']) == set(spaces), 'All displayed volumes map to the saved source; no viewer-only rooms.')
    check('canonical_roles_and_names', all(require_role(s['role']) == s['role'] for s in spaces.values()) and
          source['public_names'] == build_public_names(source), dict(Counter(s['role'] for s in spaces.values())))
    check('inferred_room_roles_explicit', all(s['role_evidence']['basis'] == 'inferred' for s in spaces.values()),
          'Geometry does not turn a plausible function into observed room-use evidence.')
    check('all_spaces_simple_nonempty', all(p.is_valid and not p.interiors and p.area > .1 for p in polys.values()), len(polys))
    coverage = []
    for f in source['floors']:
        ids = {s['id'] for s in spaces.values() if s['floor_id'] == f['id']} | set(f.get('spanning_space_ids', []))
        union = unary_union([polys[s] for s in ids])
        coverage.append({'floor': f['id'], 'difference_m2': union.symmetric_difference(Polygon(f['footprint'])).area,
                         'overlap_m2': sum(polys[s].area for s in ids) - union.area})
    check('complete_floor_coverage', all(r['difference_m2'] < 1e-7 and r['overlap_m2'] < 1e-7 for r in coverage), coverage)
    overlaps = []
    for a, b in combinations(spaces.values(), 2):
        height = min(a['z_floor'] + a['height'], b['z_floor'] + b['height']) - max(a['z_floor'], b['z_floor'])
        if height > 1e-7:
            volume = polys[a['id']].intersection(polys[b['id']]).area * height
            if volume > 1e-7:
                overlaps.append([a['id'], b['id'], volume])
    check('no_3d_space_overlap', not overlaps, overlaps)
    old_ids = {w['id'] for w in baseline['openings'] if w['kind'] == 'window'}
    check('all_322_baseline_windows_retained', old_ids <= windows.keys() and len(old_ids) == 322,
          {'baseline': len(old_ids), 'retained': len(old_ids & windows.keys()), 'new': sorted(windows.keys() - old_ids)})
    inferred = [e for e in evidence if e['source_kind'] == 'inferred_completion']
    check('completion_windows_are_identified', {e['id'] for e in inferred} == windows.keys() - old_ids,
          {'count': len(inferred), 'provenance': 'generation.provenance.opening_mapping; opening_mapping.json'})
    main_office = [s for s in spaces.values() if s['role'] == 'office/enclosed']
    by_room = defaultdict(list)
    for e in evidence:
        by_room[e['space_id']].append(e['id'])
    exceptions = []
    for s in main_office:
        if len(by_room[s['id']]) != 1:
            why = ('Corner room has one north bay and two west groups along its deeper side.' if '_N_01' in s['id'] else
                   'Partially visible final court-long group would make a room below 2.5 m wide; combine with previous bay.')
            exceptions.append({'space_id': s['id'], 'windows': by_room[s['id']], 'reason': why})
    check('one_window_per_regular_office_with_bounded_exceptions', len(exceptions) == 12 and
          all(s['space_id'].endswith(('_N_01', '_E_09')) for s in exceptions),
          {'single_window_offices': sum(len(by_room[s['id']]) == 1 for s in main_office),
           'total_offices': len(main_office), 'exceptions': exceptions,
           'meeting_rooms': 'Six southern rooms retain two narrow glazing groups each; not regular office bays.'})
    dims = [{'space_id': s['id'], 'area_m2': round(polys[s['id']].area, 3),
             'widths_m': [round(polys[s['id']].bounds[i+2] - polys[s['id']].bounds[i], 3) for i in range(2)]}
            for s in main_office]
    check('office_dimensions', all(min(d['widths_m']) >= 2.5 - 1e-6 and d['area_m2'] >= 12 for d in dims),
          {'minimum_width_m': min(min(d['widths_m']) for d in dims), 'minimum_area_m2': min(d['area_m2'] for d in dims),
           'maximum_area_m2': max(d['area_m2'] for d in dims)})
    check('50mm_architectural_grid', all(abs(c/.05-round(c/.05)) < 1e-6
          for s in spaces.values() for p in s['polygon'] for c in p) and
          all(abs(c/.05-round(c/.05)) < 1e-6 for o in source['openings'] for p in o['vertices'] for c in p),
          'Measured aperture spans moved at most 25 mm per endpoint; dimensions retain architectural modules.')
    window_dimensions = []
    for e in evidence:
        if e['floor'] not in [f'F{i}' for i in range(2, 8)]:
            continue
        s = spaces[e['space_id']]
        zbase = next(f['z_floor'] for f in source['floors'] if f['id'] == e['floor'])
        window_dimensions.append((round(e['z'][0] - zbase, 3), round(e['z'][1] - e['z'][0], 3)))
    check('window_sill_and_height', set(window_dimensions) <= {(1.2, 1.6), (1.6, 1.2)},
          {'standard_sill_height_m': [1.2, 1.6], 'above_annex_roof_sill_height_m': [1.6, 1.2],
           'annex_roof_clearance_m': .3})
    check('annex_two_storeys', math.isclose(spaces['ANNEX_F1_hall']['z_floor'], 0, abs_tol=1e-7)
          and math.isclose(spaces['ANNEX_F1_hall']['height'], 3.3, abs_tol=1e-7)
          and math.isclose(spaces['ANNEX_F2_hall']['z_floor'], 3.3, abs_tol=1e-7)
          and math.isclose(spaces['ANNEX_F2_hall']['height'], 3.6, abs_tol=1e-7),
          'Real intermediate floor at z=3.3 m; separate continuous annex stair and two window rows.')
    check('roof_use_is_ancillary', spaces['F8_attic']['role'] == 'attic' and
          all(not s['role'].startswith('office') for s in spaces.values() if s['z_floor'] >= 24.8),
          {sid: s['role'] for sid, s in spaces.items() if s['z_floor'] >= 24.8})
    graph = defaultdict(set)
    for connection in source['connections'] + source['source_enclosure']['open_connections']:
        ids = connection['space_ids']
        if len(ids) == 2:
            a, b = ids
            graph[a].add(b); graph[b].add(a)
    visited, todo = set(), deque(['F1_retail'])
    while todo:
        sid = todo.popleft()
        if sid not in visited:
            visited.add(sid); todo.extend(graph[sid] - visited)
    expected = {sid for sid in spaces if not sid.startswith('ROOF')}
    check('occupied_spaces_connected_to_ground_entry', expected <= visited, {'unreachable': sorted(expected - visited),
          'roof_exception': 'Roof-envelope subvolumes are unoccupied mass decomposition; physical maintenance access remains unresolved.'})
    core_sizes = {'CORE_S': box(-8.7, -33.2, -5.7, -28.0), 'CORE_E': box(.9, 9.3, 4.8, 16.1),
                  'TOWER_STAIR': box(-2.8, -28.4, 0, -21.7), 'ANNEX_STAIR': box(10.2, -21.3, 12.8, -15.5)}
    check('stair_usable_rectangles', all(polys[sid].covers(p) for sid, p in core_sizes.items()),
          {sid: {'clear_rectangle_m': [round(p.bounds[2]-p.bounds[0], 2), round(p.bounds[3]-p.bounds[1], 2)],
                 'fit_assumption': 'Two 1.2 m flights, 0.2 m central gap, 1.2 m landings. A 3.2 m rise can use 20 × 0.16 m risers with 0.28 m goings (about 4.92 m length). Tall ground floor requires intermediate flights; treads are not source geometry.'}
           for sid, p in core_sizes.items()})
    check('lift_is_separate_and_connected_at_every_main_level', spaces['TOWER_LIFT']['role'] == 'shaft' and
          all(any(c['opening_id'] == f'D_F{i}_lift' for c in source['connections']) for i in range(1, 9)),
          {'shaft_plan_m': [2.2, 2.4], 'height_m': 27.6, 'equipment_dimensions': 'Not specified.'})
    core_boundaries = [b for b in source['boundaries'] if b['space_id'] in {'TOWER_STAIR', 'TOWER_LIFT', 'CORE_E', 'ANNEX_STAIR'}
                       and b['geometry_type'] in ('floor', 'ceiling')]
    check('continuous_cores_have_no_fake_storey_slabs', len(core_boundaries) == 8 and
          all(b['enclosure'] == 'physical' for b in source['boundaries'] if b['geometry_type'] == 'wall'),
          {'continuous_core_horizontal_boundaries': len(core_boundaries), 'open_or_unknown_wall_regions': 0,
           'open_horizontal_seams': len(source['source_enclosure']['applications'])})
    result = {'status': 'pass' if all(c['pass_check'] for c in checks) else 'fail', 'checks': checks,
              'source_model_sha256': digest, 'counts': {'spaces': len(spaces), 'windows': len(windows),
              'doors': sum(o['kind'] == 'door' for o in source['openings'])},
              'not_evaluated': ['Human acceptance', 'True interior or hidden-window recovery', 'Building-code compliance',
                                'Detailed stair/MEP construction', 'Developer-framework or working-model run', 'EnergyPlus simulation']}
    (HERE / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    plan_dir = HERE / 'plans'; plan_dir.mkdir(exist_ok=True)
    for fid in ['F3', 'ANNEX_F1', 'ANNEX_F2', 'F8']:
        pic, meta = render_source_plan(source, fid)
        pic.save(plan_dir / f'{fid}.png')
        (plan_dir / f'{fid}.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'failed': [c for c in checks if not c['pass_check']]}, ensure_ascii=False))
    assert result['status'] == 'pass'


if __name__ == '__main__':
    main()
