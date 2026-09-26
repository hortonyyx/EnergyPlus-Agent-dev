"""Deterministic and offline-browser validation of the 09-26 tower completion.

Reuses the 09-16 and 09-25 checks unchanged where their semantics fit and adds
checks for this revision only: plan/assembly replay from this directory,
retention of every 09-25 space/window/door, the exact footprint change, and the
tower itself (contacts, landing doors, measured bounds, no intermediate slab,
reachability).  No check treats the inferred tower use as observed truth.
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
from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
OLD_DIR = HERE.parent / '2026-09-16_voimatalo_completion'
PREV_DIR = HERE.parent / '2026-09-25_voimatalo_opus_development'
OLD = runpy.run_path(str(OLD_DIR / 'verify_candidate.py'), run_name='voimatalo_verify_0916')
V25 = runpy.run_path(str(PREV_DIR / 'verify_candidate.py'), run_name='voimatalo_verify_0925')
MESH = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/input.glb'
TOWER_ID = 'TOWER_C_lift_tower'
CORE_ID = 'CORE_S_continuous'
TOL = 1e-6


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True, timeout=600, check=False)


def check_plan_and_assembly_replay(candidate: Path, plan: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix='voimatalo-0926-replay-') as temp:
        temp = Path(temp)
        p1 = run([str(HERE / 'build_plan_v3.py'), '--out', str(temp / 'plan.json')])
        plan_same = p1.returncode == 0 and (temp / 'plan.json').read_bytes() == plan.read_bytes()
        p2 = run([str(HERE / 'assemble_candidate.py'), '--plan', str(plan), '--out', str(temp / 'candidate')])
        files = {}
        for name in ['source_model.json', 'proposal.json', 'opening_mapping.json', 'report.json']:
            a, b = candidate / name, temp / 'candidate' / name
            files[name] = {'exact_bytes': a.is_file() and b.is_file() and a.read_bytes() == b.read_bytes(), 'sha256': sha256(a)}
    ok = plan_same and p2.returncode == 0 and all(r['exact_bytes'] for r in files.values())
    return {'status': 'pass' if ok else 'fail', 'plan_rebuilt_identical': plan_same, 'plan_sha256': sha256(plan),
            'assembly_returncode': p2.returncode, 'stderr_tail': (p1.stderr + p2.stderr)[-2000:], 'files': files}


def check_retention_vs_0925(source: dict, prev: dict) -> dict:
    """Every 09-25 space, window and door is kept with identical geometry and hosts."""
    new_s, old_s = {s['id']: s for s in source['spaces']}, {s['id']: s for s in prev['spaces']}
    changed_spaces = sorted(k for k in old_s if k not in new_s or any(
        new_s[k][f] != old_s[k][f] for f in ('polygon', 'z_floor', 'height', 'role', 'floor_id')))
    new_o, old_o = {o['id']: o for o in source['openings']}, {o['id']: o for o in prev['openings']}
    missing = sorted(set(old_o) - set(new_o))
    moved = sorted(k for k in set(old_o) & set(new_o) if new_o[k]['vertices'] != old_o[k]['vertices'])
    rehosted = sorted(k for k in set(old_o) & set(new_o) if new_o[k]['space_ids'] != old_o[k]['space_ids'])
    added = sorted(set(new_o) - set(old_o))
    expected_added = {f'court_glazed_col_F{n}_inferred' for n in range(2, 8)} | {f'D_F{n}_CORE_S_TOWER_C' for n in range(1, 8)}
    ok = not changed_spaces and not missing and not moved and not rehosted and set(added) == expected_added \
        and sorted(set(new_s) - set(old_s)) == [TOWER_ID]
    return {'status': 'pass' if ok else 'fail', 'prev_spaces': len(old_s), 'spaces': len(new_s),
            'added_spaces': sorted(set(new_s) - set(old_s)), 'changed_or_missing_prev_spaces': changed_spaces,
            'prev_windows': sum(o['kind'] == 'window' for o in old_o.values()), 'prev_doors': sum(o['kind'] == 'door' for o in old_o.values()),
            'windows': sum(o['kind'] == 'window' for o in new_o.values()), 'doors': sum(o['kind'] == 'door' for o in new_o.values()),
            'missing_prev_openings': missing, 'geometry_changed_prev_openings': moved, 'rehosted_prev_openings': rehosted,
            'added_openings': added, 'unexpected_added': sorted(set(added) - expected_added)}


def check_footprint_change(source: dict, prev: dict, plan: dict) -> dict:
    tower = next(r for r in plan['continuous_spaces'] if r['key'] == 'TOWER_C')
    rect = box(*tower['rect'])
    new = {f['id']: f for f in source['floors']}
    old = {f['id']: f for f in prev['floors']}
    rows = []
    for fid, f in old.items():
        n = new[fid]
        a, b = Polygon(n['footprint']), Polygon(f['footprint'])
        expected = b.union(rect) if fid in tower['floors'] else b
        rows.append({'floor_id': fid, 'added_m2': round(a.difference(b).area, 6), 'removed_m2': round(b.difference(a).area, 6),
                     'equals_expected': a.symmetric_difference(expected).area <= TOL,
                     'z_and_height_equal': abs(n['z_floor'] - f['z_floor']) < TOL and abs(n['height'] - f['height']) < TOL})
    ok = all(r['equals_expected'] and r['z_and_height_equal'] and r['removed_m2'] <= TOL for r in rows)
    return {'status': 'pass' if ok else 'fail', 'tower_rect': tower['rect'], 'floors': rows,
            'interpretation': 'F1-F7 footprints grow by exactly the tower rectangle; every other part of the 09-25 shell is identical.'}


def polygon_area_3d(vertices) -> float:
    v = np.asarray(vertices, float)
    return float(np.linalg.norm(np.cross(v, np.roll(v, -1, axis=0)).sum(axis=0)) / 2)


def check_tower(source: dict, plan: dict, measure: dict) -> dict:
    spaces = {s['id']: s for s in source['spaces']}
    t = spaces[TOWER_ID]
    walls = [b for b in source['boundaries'] if b['space_id'] == TOWER_ID and b['geometry_type'] == 'wall']
    horizontal = [b for b in source['boundaries'] if b['space_id'] == TOWER_ID and b['geometry_type'] != 'wall']
    rel_area = {}
    for r in source['boundary_relations']:
        ids = r['boundary_ids']
        owners = {next(b['space_id'] for b in source['boundaries'] if b['id'] == i) for i in ids}
        if TOWER_ID in owners:
            other = (owners - {TOWER_ID}).pop()
            area = sum(polygon_area_3d(reg['vertices']) for reg in r['regions'])
            rel_area[other] = round(rel_area.get(other, 0) + area, 3)
    doors = sorted((o for o in source['openings'] if o['kind'] == 'door' and TOWER_ID in o['space_ids']),
                   key=lambda o: min(v[2] for v in o['vertices']))
    storeys = {f['id']: (f['z_floor'], f['z_floor'] + f['height']) for f in source['floors'] if f['id'][1:].isdigit()}
    door_rows = []
    for o in doors:
        z0 = min(v[2] for v in o['vertices'])
        fid = next(k for k, (a, b) in storeys.items() if a - TOL <= z0 < b)
        door_rows.append({'id': o['id'], 'storey': fid, 'other': [s for s in o['space_ids'] if s != TOWER_ID], 'exterior': o['exterior']})
    hosted = {bid for o in source['openings'] for bid in source['opening_hosts'][o['id']]}
    exterior_walls = [b for b in walls if not b['adjacent_space_ids']]
    north = measure['north_stub_face_y≈-21.9']
    annex_face = measure['annex_south_face_y≈-21.75_below_7m']
    hole = measure['courtyard_hole_from_parent_buffer']['deep_hit_y_range_by_z_m']
    upper = [v for z, v in hole.items() if 7 <= int(z) <= 25]
    hole_lo = float(np.median([v[0] for v in upper]))
    hole_hi = float(np.median([v[1] for v in upper]))
    x0, y0, x1, y1 = Polygon(t['polygon']).bounds
    bounds = {'east_face_x': x1, 'east_face_min_from_north_stub_x': 2.38, 'east_face_max_from_annex_facade_x': 2.9,
              'north_stub_max_x_incl_annex_edge': north['x_m'][1], 'annex_facade_min_x': annex_face['x_m'][0],
              'hole_median_y_range_z7_25': [round(hole_lo, 2), round(hole_hi, 2)], 'tower_y_range': [y0, y1],
              'south_face_offset_from_hole_m': round(abs(y0 - hole_lo), 2), 'north_face_offset_from_hole_m': round(abs(y1 - hole_hi), 2)}
    checks = {
        'z_range_0_25.25': abs(t['z_floor']) < TOL and abs(t['z_floor'] + t['height'] - 25.25) < TOL,
        'only_bottom_and_top_horizontal_boundaries': len(horizontal) == 2,
        'full_contact_with_south_core_m2': rel_area.get(CORE_ID, 0) >= 4.2 * 25.25 - 0.01,
        'contact_with_annex_limited_to_annex_height': 0 < rel_area.get('ANNEX_hall', 0) <= 1.7 * 6.7 + 0.01,
        'one_landing_door_per_storey_F1_F7': [r['storey'] for r in door_rows] == [f'F{n}' for n in range(1, 8)]
        and all(r['other'] == [CORE_ID] and not r['exterior'] for r in door_rows),
        'exterior_walls_without_openings_or_unknown_regions': all(b['id'] not in hosted and not b.get('enclosure_regions') for b in exterior_walls),
        'within_measured_bounds': 2.38 - TOL <= x1 <= 2.9 + TOL and bounds['south_face_offset_from_hole_m'] <= 0.25
        and bounds['north_face_offset_from_hole_m'] <= 0.3 and abs(x0 - 0.8) < TOL,
    }
    return {'status': 'pass' if all(checks.values()) else 'fail', 'checks': checks, 'contact_area_m2_by_space': rel_area,
            'landing_doors': door_rows, 'exterior_wall_ids': [b['id'] for b in exterior_walls], 'measured_bounds': bounds,
            'interpretation': 'Position, width and full height follow the measured crop remnants; depth is constrained to '
                              '[2.38, 2.9] m east edge; lift use and windowless exterior faces are inference, recorded as such.'}


def check_dimensions_with_shaft(source: dict) -> dict:
    result = V25['check_dimensions'](source)
    shaft = [p for p in result['problems'] if 'lift_shaft' in next(s['role'] for s in source['spaces'] if s['id'] == p['space_id'])]
    remaining = [p for p in result['problems'] if p not in shaft]
    return {**result, 'status': 'pass' if not remaining else 'fail', 'problems': remaining, 'exempt_shaft_volumes': shaft,
            'exemption': 'The tower is a shaft volume, not an occupied room; the 2.4 m room-width rule does not apply to it.'}


def markdown(report: dict) -> str:
    names = {'source_replay': 'Exact source proposal replay', 'plan_assembly_replay': 'Plan rebuild + assembly replay (byte-identical)',
             'no_overlap': 'No positive-volume source-space overlap', 'footprint_change': 'Only change to the shell = tower rectangle on F1-F7',
             'retention_vs_0925': 'All 80 spaces / 300 windows / 88 doors of 09-25 unchanged; additions exactly the tower items',
             'window_retention_vs_0916': 'All 287 candidate_04 windows unchanged; additions explained',
             'openings_built': 'Declared openings all built; windows single exterior host',
             'partitions_on_piers': 'Partitions meet facades in window piers', 'continuous_spaces': 'Continuous volumes without intermediate slabs',
             'open_contact_display': 'Declared open contacts open on both sides, no displayed slab', 'roof_interfaces': 'Roof-part contacts open; slabs kept',
             'reachability': 'Reachable via doors/open contacts; two vertical routes per upper storey', 'tower': 'Tower contacts, landing doors, measured bounds',
             'dimensions': 'Room/corridor widths plausible (shaft exempt)', 'enclosure': 'Enclosure bookkeeping (unknown reasons, party walls)',
             'result_links': 'Packaged links resolve', 'browser': 'Offline original/BIM/overlay viewer and images',
             'browser_tower_view': 'Offline viewer aimed at the tower (overlay/BIM screenshots)'}
    lines = ['# Voimatalo 09-26 candidate_02 validation', '', f"Overall required checks: **{report['overall']}**", '',
             f"Source sha256 `{report['source_model_sha256']}`", '', '| Check | Status |', '|---|---|']
    lines += [f"| {label} | {report['checks'][k]['status']} |" for k, label in names.items() if k in report['checks']]
    r, t, e = report['checks']['retention_vs_0925'], report['checks']['tower'], report['checks']['enclosure']
    lines += ['', '## Key numbers', '',
              f"- 09-25 → 09-26: spaces {r['prev_spaces']} → {r['spaces']}, windows {r['prev_windows']} → {r['windows']}, doors {r['prev_doors']} → {r['doors']}; "
              f"prev openings missing {len(r['missing_prev_openings'])}, moved {len(r['geometry_changed_prev_openings'])}, re-hosted {len(r['rehosted_prev_openings'])}.",
              f"- Tower contact areas: {t['contact_area_m2_by_space']}; landing doors on {[d['storey'] for d in t['landing_doors']]}.",
              f"- Measured bounds: {t['measured_bounds']}.",
              f"- Unknown-enclosure boundaries: {e['old_unknown_boundary_count']} (09-25) → {e['new_unknown_boundary_count']}.",
              '', '## Limits', '',
              '- The tower use (lifts) and its windowless exterior are inference; the checks prove consistency, not the real use.',
              '- Reachability follows the declared door/open-contact scheme; it does not verify the real interior.',
              '- Technical checks are not the user acceptance of this completion.']
    return '\n'.join(lines) + '\n'


def browser_tower_view(result: Path, qa_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright
    errors, shots = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_context(viewport={'width': 1400, 'height': 1000}, offline=True).new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((result / 'overlay.html').as_uri())
        page.wait_for_function("window.TRANSFER && document.body.dataset.texture==='ready'")
        # The viewer is z-up in the BIM frame: look at the tower from the south-east courtyard side.
        page.evaluate("""() => {const c=TRANSFER.camera, t=TRANSFER.controls;
            t.target.set(1.6, -23.8, 12); c.position.set(40, -62, 32); c.updateProjectionMatrix(); t.update();}""")
        for mode in ['overlay', 'bim', 'input']:
            page.locator(f'[data-transfer-mode={mode}]').click()
            page.wait_for_timeout(400)
            name = f'tower_{mode}.png'
            page.screenshot(path=str(qa_dir / name))
            shots.append(name)
        browser.close()
    return {'status': 'pass' if not errors else 'fail', 'errors': errors, 'screenshots': shots,
            'note': 'Camera aimed at the courtyard tower; screenshots are for human review, not an automatic visual verdict.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, default=HERE / 'candidate_02')
    parser.add_argument('--result', type=Path, default=HERE / 'result_02')
    parser.add_argument('--plan', type=Path, default=HERE / 'case_plan_v3.json')
    parser.add_argument('--report-dir', type=Path, default=HERE / 'validation')
    parser.add_argument('--skip-browser', action='store_true')
    args = parser.parse_args()
    candidate, result, plan_path = args.candidate.resolve(), args.result.resolve(), args.plan.resolve()
    source_path = candidate / 'source_model.json'
    source, plan = read(source_path), read(plan_path)
    prev = read(PREV_DIR / 'candidate_01/source_model.json')
    base04 = read(OLD_DIR / 'candidate_04/source_model.json')
    display = read(candidate / 'display_geometry.json')
    measure = read(HERE / 'observations/protrusion_measure.json')
    args.report_dir.mkdir(parents=True, exist_ok=True)
    checks = {
        'source_replay': OLD['check_source_export_replay'](candidate, source_path, source),
        'plan_assembly_replay': check_plan_and_assembly_replay(candidate, plan_path),
        'no_overlap': OLD['check_no_overlap'](source),
        'footprint_change': check_footprint_change(source, prev, plan),
        'retention_vs_0925': check_retention_vs_0925(source, prev),
        'window_retention_vs_0916': V25['check_window_retention'](source, base04, plan),
        'openings_built': V25['check_openings_built'](source, candidate),
        'partitions_on_piers': V25['check_partitions_on_piers'](source),
        'continuous_spaces': V25['check_continuous'](source, plan),
        'open_contact_display': V25['check_open_contact_display'](source, display, plan),
        'roof_interfaces': OLD['check_roof_interfaces'](source, display),
        'reachability': V25['check_reachability'](source),
        'tower': check_tower(source, plan, measure),
        'dimensions': check_dimensions_with_shaft(source),
        'enclosure': V25['check_enclosure'](source, prev, candidate),
    }
    if not args.skip_browser:
        qa_dir = args.report_dir / 'candidate_02_browser_qa'
        if qa_dir.exists():
            shutil.rmtree(qa_dir)  # this validator's own previous screenshots
        checks['browser'] = OLD['browser_qa'](result, qa_dir, source, MESH)
        checks['browser_tower_view'] = browser_tower_view(result, qa_dir)

    def write_reports():
        overall = 'pass' if all(c['status'] == 'pass' for c in checks.values()) else 'fail'
        report = {'schema': 'voimatalo_0926_validation_v1', 'overall': overall, 'candidate': str(candidate.relative_to(ROOT)),
                  'source_model_sha256': source['source_model_sha256'], 'previous': 'AI_agent/logs/experiments/2026-09-25_voimatalo_opus_development/candidate_01',
                  'validator_sha256': sha256(Path(__file__)), 'checks': checks}
        (args.report_dir / 'candidate_02_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        (args.report_dir / 'candidate_02_validation.md').write_text(markdown(report))
        return overall
    write_reports()
    checks['result_links'] = OLD['check_result_links'](result)
    overall = write_reports()
    print(json.dumps({k: v['status'] for k, v in checks.items()} | {'overall': overall}, indent=1))


if __name__ == '__main__':
    main()
