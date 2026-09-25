"""Deterministic and offline-browser validation of the 09-25 candidate.

Reuses the 09-16 checks where their semantics still fit (exact proposal
replay, overlap, roof interfaces, link resolution, browser transport) and adds
checks for this revision: retention of every old window rectangle, the new
partition/window-pier rule, continuous vertical spaces with declared open
contacts, reachability through doors *and* open contacts, room dimensions,
unchanged exterior shell and enclosure bookkeeping.  No check treats the
inferred interior as observed truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
OLD_DIR = HERE.parent / '2026-09-16_voimatalo_completion'
OLD = runpy.run_path(str(OLD_DIR / 'verify_candidate.py'), run_name='voimatalo_verify_0916')
MESH = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb'
TOL = 1e-6


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_assembly_replay(candidate: Path, plan: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix='voimatalo-0925-replay-') as temp:
        out = Path(temp) / 'candidate'
        command = [sys.executable, str(HERE / 'assemble_candidate.py'), '--plan', str(plan), '--out', str(out)]
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=600, check=False)
        files = {}
        for name in ['source_model.json', 'proposal.json', 'opening_mapping.json', 'report.json']:
            a, b = candidate / name, out / name
            files[name] = {'exact_bytes': a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes(),
                           'sha256': sha256(a) if a.is_file() else None}
        ok = process.returncode == 0 and all(row['exact_bytes'] for row in files.values())
        return {'status': 'pass' if ok else 'fail', 'returncode': process.returncode,
                'stderr_tail': process.stderr[-2000:], 'files': files,
                'command': ['python', 'assemble_candidate.py', '--plan', str(plan.relative_to(ROOT)), '--out', '<temporary>']}


def check_window_retention(source: dict, baseline: dict, plan: dict) -> dict:
    current = {o['id']: o for o in source['openings']}
    old_windows = {o['id']: o for o in baseline['openings'] if o['kind'] == 'window'}
    missing = sorted(set(old_windows) - set(current))
    moved = sorted(k for k in set(old_windows) & set(current) if current[k]['vertices'] != old_windows[k]['vertices'])
    rehosted = sorted(k for k in set(old_windows) & set(current) if current[k]['space_ids'] != old_windows[k]['space_ids'])
    added = sorted(k for k, o in current.items() if o['kind'] == 'window' and k not in old_windows)
    measured = {r['id'] for r in read(ROOT / plan['extra_observed_windows']['path'])['openings']}
    inferred = {r['id'] for r in plan['inferred_windows']['rows']}
    unexplained = sorted(set(added) - measured - inferred)
    return {'status': 'pass' if not missing and not moved and not unexplained else 'fail',
            'baseline_window_count': len(old_windows), 'candidate_window_count': sum(o['kind'] == 'window' for o in current.values()),
            'missing_old_window_ids': missing, 'geometry_changed_old_window_ids': moved,
            'rehosted_old_window_count': len(rehosted),
            'added_measured_window_ids': sorted(set(added) & measured), 'added_inferred_window_ids': sorted(set(added) & inferred),
            'added_unexplained': unexplained,
            'interpretation': 'Every candidate_04 window keeps identical vertices; owner space changes are expected re-hosting.'}


def check_openings_built(source: dict, candidate: Path) -> dict:
    proposal = read(candidate / 'proposal.json')
    declared = {r['id'] for r in proposal['geometry']['windows'] + proposal['geometry']['openings']}
    built = {o['id'] for o in source['openings']}
    windows = [o for o in source['openings'] if o['kind'] == 'window']
    doors = [o for o in source['openings'] if o['kind'] == 'door']
    ok = declared == built and not source.get('unbuilt_openings') and all(o['exterior'] and len(o['space_ids']) == 1 for o in windows)
    return {'status': 'pass' if ok else 'fail', 'declared': len(declared), 'built': len(built),
            'declared_not_built': sorted(declared - built), 'unbuilt_openings': source.get('unbuilt_openings', []),
            'windows': len(windows), 'doors': len(doors), 'exterior_doors': sorted(o['id'] for o in doors if o['exterior']),
            'windows_all_single_exterior_host': all(o['exterior'] and len(o['space_ids']) == 1 for o in windows)}


def check_reachability(source: dict) -> dict:
    roof = {s['id'] for s in source['spaces'] if 'roof' in s['role']}
    graph = {s['id']: set() for s in source['spaces']}
    graph['__EXTERIOR__'] = set()
    for o in source['openings']:
        if o['kind'] != 'door':
            continue
        a, b = (o['space_ids'][0], '__EXTERIOR__') if o['exterior'] else o['space_ids']
        graph[a].add(b)
        graph[b].add(a)
    opens = []
    for c in source['source_enclosure']['open_connections']:
        if c['exterior'] or any(s in roof for s in c['space_ids']):
            continue
        a, b = c['space_ids']
        graph[a].add(b)
        graph[b].add(a)
        opens.append(sorted(c['space_ids']))
    seen, stack = {'__EXTERIOR__'}, ['__EXTERIOR__']
    while stack:
        for n in graph[stack.pop()]:
            if n not in seen:
                seen.add(n)
                stack.append(n)
    usable = {s['id'] for s in source['spaces']} - roof
    unreachable = sorted(usable - seen)
    vertical = {s['id'] for s in source['spaces'] if 'vertical_circulation' in s['role']}
    landing = {s['id'] for s in source['spaces'] if 'stair_landing' in s['role']}
    storeys = {}
    for fid in [f'F{n}' for n in range(2, 9)]:
        reach = set()
        for n in graph.get(f'{fid}_corridor', ()):
            if n in vertical:
                reach.add(n)
            elif n in landing:
                # A set-back top landing counts through its open contact to the stair/core it tops.
                reach.update(m for m in graph[n] if m in vertical)
        storeys[fid] = sorted(reach)
    two_routes = all(len(v) >= 2 for v in storeys.values())
    return {'status': 'pass' if not unreachable and two_routes else 'fail', 'unreachable_usable_space_ids': unreachable,
            'open_contacts_used': sorted(map(list, {tuple(x) for x in opens})),
            'upper_storey_corridor_vertical_routes': storeys, 'every_upper_storey_has_two_vertical_routes': two_routes,
            'interpretation': 'Declared, partly inferred door/open-contact graph; not real-plan evidence.'}


def check_continuous(source: dict, plan: dict) -> dict:
    rows = []
    open_pairs = {tuple(sorted(c['space_ids'])) for c in source['source_enclosure']['open_connections'] if not c['exterior']}
    floors = {f['id']: f for f in source['floors']}
    for row in plan['continuous_spaces']:
        sid = f"{row['key']}_{row['cell']}"
        horizontal = [b for b in source['boundaries'] if b['space_id'] == sid and b['geometry_type'] in ('floor', 'ceiling')]
        z_values = sorted({round(v[2], 6) for b in horizontal for v in b['vertices']})
        referenced = sorted(f['id'] for f in source['floors'] if sid in f.get('spanning_space_ids', []))
        ok = len(horizontal) == 2 and z_values == [round(v, 6) for v in row['z']] and referenced == sorted(row['floors'])
        rows.append({'space_id': sid, 'horizontal_boundaries': len(horizontal), 'z_values_m': z_values,
                     'referenced_by_storeys': referenced, 'status': 'pass' if ok else 'fail'})
    contacts = []
    for row in plan['enclosure']['open_horizontal_contacts']:
        pair = tuple(sorted([row['lower'], row['upper']]))
        contacts.append({'pair': list(pair), 'open_connection_present': pair in open_pairs})
    ok = all(r['status'] == 'pass' for r in rows) and all(c['open_connection_present'] for c in contacts)
    return {'status': 'pass' if ok else 'fail', 'continuous_spaces': rows, 'declared_open_contacts': contacts,
            'interpretation': 'Only bottom/top horizontal boundaries: no intermediate slabs inside stair/core volumes.'}


def check_open_contact_display(source: dict, display: dict, plan: dict) -> dict:
    """Declared stair/core open contacts must be open on both sides and not drawn as slabs."""
    spaces = {s['id']: s for s in source['spaces']}
    rows = []
    for row in plan['enclosure']['open_horizontal_contacts']:
        lower, upper = spaces[row['lower']], spaces[row['upper']]
        z = lower['z_floor'] + lower['height']
        contact = Polygon(lower['polygon']).intersection(Polygon(upper['polygon']))
        for sid, kind in ((lower['id'], 'ceiling'), (upper['id'], 'floor')):
            b = OLD['horizontal_boundary'](source, sid, kind, z)
            opened = OLD['boundary_open_geometry'](b)
            slab = contact.intersection(OLD['display_physical_geometry'](display, b['id'])).area
            rows.append({'space_id': sid, 'boundary_id': b['id'], 'contact_area_m2': round(contact.area, 4),
                         'missing_open_m2': round(contact.difference(opened).area, 6),
                         'open_outside_contact_m2': round(opened.difference(contact).area, 6),
                         'physical_display_inside_contact_m2': round(slab, 6)})
    ok = all(r['missing_open_m2'] <= TOL and r['open_outside_contact_m2'] <= TOL and r['physical_display_inside_contact_m2'] <= TOL for r in rows)
    return {'status': 'pass' if ok else 'fail', 'sides': rows}


def facade_lines(source: dict, fid: str):
    floor = next(f for f in source['floors'] if f['id'] == fid)
    ring = floor['footprint']
    return [LineString([a, b]) for a, b in zip(ring, ring[1:] + ring[:1])]


def check_partitions_on_piers(source: dict) -> dict:
    """Every interior partition end on a facade lies outside window spans of that storey."""
    spaces = {s['id']: s for s in source['spaces']}
    windows = [o for o in source['openings'] if o['kind'] == 'window']
    storeys = [f for f in source['floors'] if f['id'].startswith('F') and f['id'][1:].isdigit()]
    conflicts, checked = [], 0
    for floor in storeys:
        z0, z1 = floor['z_floor'], floor['z_floor'] + floor['height']
        members = [s for s in source['spaces'] if s['floor_id'] == floor['id']] + [spaces[i] for i in floor.get('spanning_space_ids', [])]
        edges = facade_lines(source, floor['id'])
        # Partition end points = polygon vertices of members that lie on a facade edge but are not footprint corners.
        corners = {tuple(np.round(p, 5)) for p in floor['footprint']}
        ends = set()
        for s in members:
            for p in s['polygon']:
                key = tuple(np.round(p, 5))
                if key in corners:
                    continue
                if any(e.distance(Point(p)) < 1e-6 for e in edges):
                    ends.add(key)
        for p in ends:
            checked += 1
            for w in windows:
                v = np.asarray(w['vertices'])
                if v[:, 2].max() <= z0 + 1e-6 or v[:, 2].min() >= z1 - 1e-6:
                    continue
                seg = LineString(np.unique(np.round(v[:, :2], 6), axis=0))
                if seg.distance(Point(p)) < 1e-6 and not any(Point(p).distance(Point(q)) < 1e-6 for q in seg.coords):
                    conflicts.append({'storey': floor['id'], 'partition_end_xy': list(p), 'window_id': w['id']})
    return {'status': 'pass' if not conflicts else 'fail', 'partition_ends_checked': checked, 'conflicts': conflicts,
            'interpretation': 'Inferred partitions meet the facade in window piers; no observed window is crossed.'}


def widest_inscribed_width(poly: Polygon) -> float:
    lo, hi = 0.0, 50.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if poly.buffer(-mid / 2, join_style=2).is_empty:
            hi = mid
        else:
            lo = mid
    return lo


def check_dimensions(source: dict) -> dict:
    """Plausibility only: no usable space may be narrow everywhere; narrow alcoves are listed."""
    rows, problems = [], []
    for s in source['spaces']:
        if 'roof' in s['role']:
            continue
        poly = Polygon(s['polygon'])
        need = 2.0 if 'corridor' in s['role'] else 2.4
        d = (need - 0.05) / 2
        opened = poly.buffer(-d, join_style=2).buffer(d, join_style=2)
        narrow_area = poly.area - (opened.area if not opened.is_empty else 0.0)
        width = widest_inscribed_width(poly)
        rows.append({'space_id': s['id'], 'role': s['role'], 'area_m2': round(poly.area, 1),
                     'widest_part_m': round(width, 2), 'area_narrower_than_rule_m2': round(narrow_area, 2)})
        if width < need - 0.05:
            problems.append({'space_id': s['id'], 'widest_part_m': round(width, 2), 'required_m': need})
    alcoves = [r for r in rows if r['area_narrower_than_rule_m2'] > 0.01]
    return {'status': 'pass' if not problems else 'fail', 'problems': problems, 'narrow_alcoves': alcoves, 'spaces': rows,
            'rule': 'every usable space has a part at least 2.4 m wide (corridors 2.0 m); narrower alcoves are listed, not failed'}


def check_shell_unchanged(source: dict, baseline: dict) -> dict:
    new = {f['id']: Polygon(f['footprint']) for f in source['floors']}
    old = {f['id']: Polygon(f['footprint']) for f in baseline['floors']}
    rows = []
    for fid in [f'F{n}' for n in range(1, 9)] + ['ANNEX', 'ROOF', 'ROOF_N_BASE', 'ROOF_N', 'ROOF_S', 'ROOF_STACK']:
        diff = new[fid].symmetric_difference(old[fid]).area
        zn = next(f for f in source['floors'] if f['id'] == fid)
        zo = next(f for f in baseline['floors'] if f['id'] == fid)
        rows.append({'floor_id': fid, 'footprint_symmetric_difference_m2': round(diff, 8),
                     'z_and_height_equal': abs(zn['z_floor'] - zo['z_floor']) < TOL and abs(zn['height'] - zo['height']) < TOL})
    ok = all(r['footprint_symmetric_difference_m2'] <= TOL and r['z_and_height_equal'] for r in rows)
    return {'status': 'pass' if ok else 'fail', 'floors': rows,
            'interpretation': 'Storey outlines, levels, annex and roof parts identical to candidate_04; changes are interior and openings only.'}


def check_enclosure(source: dict, baseline: dict, candidate: Path) -> dict:
    unknown = lambda s: sorted(b['id'] for b in s['boundaries'] if any(r['condition'] == 'unknown' for r in b.get('enclosure_regions', [])))
    new_unknown, old_unknown = unknown(source), unknown(baseline)
    reasons_ok = all(r['assumptions'] for b in source['boundaries'] for r in b.get('enclosure_regions', []))
    party = read(candidate / 'report.json')['provenance']['party_wall_inference']['boundaries']
    party_ids = {row['boundary_id'] for row in party}
    hosted = {bid for o in source['openings'] for bid in source['opening_hosts'][o['id']]}
    party_with_openings = sorted(party_ids & hosted)
    kinds = {}
    for b in source['boundaries']:
        kinds[b['kind']] = kinds.get(b['kind'], 0) + 1
    ok = reasons_ok and not party_with_openings and not (party_ids & set(new_unknown))
    return {'status': 'pass' if ok else 'fail', 'old_unknown_boundary_count': len(old_unknown), 'new_unknown_boundary_count': len(new_unknown),
            'new_unknown_boundary_ids': new_unknown, 'party_wall_boundary_count': len(party_ids),
            'party_walls_with_openings': party_with_openings, 'every_region_has_reason': reasons_ok, 'boundary_kinds': kinds}


def markdown(report: dict) -> str:
    names = {'source_replay': 'Exact source proposal replay', 'assembly_replay': 'Frozen plan/observation assembly replay',
             'no_overlap': 'No positive-volume source-space overlap', 'shell_unchanged': 'Exterior shell/levels/roof identical to candidate_04',
             'window_retention': 'All 287 candidate_04 windows kept unchanged; additions explained',
             'openings_built': 'Declared openings all built; windows single exterior host',
             'partitions_on_piers': 'Inferred partitions meet facades in window piers',
             'continuous_spaces': 'Continuous stair/core volumes without intermediate slabs',
             'open_contact_display': 'Declared stair/core open contacts open on both sides, no displayed slab',
             'roof_interfaces': 'Roof-part contacts open; F8/core-to-roof slab kept',
             'reachability': 'Reachable via doors/open contacts; two vertical routes per upper storey',
             'dimensions': 'Room/corridor widths plausible', 'enclosure': 'Enclosure bookkeeping (unknown reasons, party walls)',
             'result_links': 'Packaged links resolve', 'browser': 'Offline original/BIM/overlay viewer and images'}
    lines = ['# Voimatalo 09-25 candidate_01 validation', '', f"Overall required checks: **{report['overall']}**", '',
             '| Check | Status |', '|---|---|']
    for key, label in names.items():
        if key in report['checks']:
            lines.append(f"| {label} | {report['checks'][key]['status']} |")
    w = report['checks']['window_retention']
    e = report['checks']['enclosure']
    r = report['checks']['reachability']
    lines += ['', '## Key numbers', '',
              f"- Windows: candidate_04 {w['baseline_window_count']} → candidate_01 {w['candidate_window_count']}; old missing {len(w['missing_old_window_ids'])}, old geometry changed {len(w['geometry_changed_old_window_ids'])}, re-hosted {w['rehosted_old_window_count']}; added measured {len(w['added_measured_window_ids'])}, added inferred {len(w['added_inferred_window_ids'])}.",
              f"- Unknown-enclosure boundaries: {e['old_unknown_boundary_count']} → {e['new_unknown_boundary_count']}; party-wall boundaries {e['party_wall_boundary_count']} (none with openings).",
              f"- Upper-storey corridor vertical routes: {r['upper_storey_corridor_vertical_routes']}.",
              f"- Partition ends on facades checked: {report['checks']['partitions_on_piers']['partition_ends_checked']}.",
              '', '## Limits', '',
              '- Door/open-contact reachability follows the declared, inferred scheme; it does not verify the real interior.',
              '- Shell identity is against candidate_04 (itself an approximate regularisation); no new mesh-fidelity score is claimed.',
              '- Browser transport proves the saved artefacts display unchanged; visual plausibility needs human review of the saved screenshots and plans.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, default=HERE / 'candidate_01')
    parser.add_argument('--result', type=Path, default=HERE / 'result_01')
    parser.add_argument('--baseline', type=Path, default=OLD_DIR / 'candidate_04')
    parser.add_argument('--plan', type=Path, default=HERE / 'case_plan_v2.json')
    parser.add_argument('--report-dir', type=Path, default=HERE / 'validation')
    parser.add_argument('--skip-browser', action='store_true')
    args = parser.parse_args()
    candidate, result = args.candidate.resolve(), args.result.resolve()
    source_path = candidate / 'source_model.json'
    source, baseline = read(source_path), read(args.baseline.resolve() / 'source_model.json')
    display = read(candidate / 'display_geometry.json')
    plan = read(args.plan)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    checks = {
        'source_replay': OLD['check_source_export_replay'](candidate, source_path, source),
        'assembly_replay': check_assembly_replay(candidate, args.plan.resolve()),
        'no_overlap': OLD['check_no_overlap'](source),
        'shell_unchanged': check_shell_unchanged(source, baseline),
        'window_retention': check_window_retention(source, baseline, plan),
        'openings_built': check_openings_built(source, candidate),
        'partitions_on_piers': check_partitions_on_piers(source),
        'continuous_spaces': check_continuous(source, plan),
        'open_contact_display': check_open_contact_display(source, display, plan),
        'roof_interfaces': OLD['check_roof_interfaces'](source, display),
        'reachability': check_reachability(source),
        'dimensions': check_dimensions(source),
        'enclosure': check_enclosure(source, baseline, candidate),
    }
    if not args.skip_browser:
        qa_dir = args.report_dir / 'candidate_01_browser_qa'
        if qa_dir.exists():
            shutil.rmtree(qa_dir)  # this validator's own previous screenshots
        checks['browser'] = OLD['browser_qa'](result, qa_dir, source, MESH)

    def write_reports():
        overall = 'pass' if all(c['status'] == 'pass' for c in checks.values()) else 'fail'
        report = {'schema': 'voimatalo_0925_validation_v1', 'overall': overall,
                  'candidate': str(candidate.relative_to(ROOT)), 'source_model_sha256': source['source_model_sha256'],
                  'baseline': str(args.baseline.resolve().relative_to(ROOT)), 'validator_sha256': sha256(Path(__file__)),
                  'checks': checks}
        (args.report_dir / 'candidate_01_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        (args.report_dir / 'candidate_01_validation.md').write_text(markdown(report))
        return overall
    # Links are checked after the reports exist, because the result page links to them.
    write_reports()
    checks['result_links'] = OLD['check_result_links'](result)
    overall = write_reports()
    print(json.dumps({k: v['status'] for k, v in checks.items()} | {'overall': overall}, indent=1))


if __name__ == '__main__':
    main()
