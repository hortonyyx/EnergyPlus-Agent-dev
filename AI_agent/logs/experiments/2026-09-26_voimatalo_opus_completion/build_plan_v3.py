"""Derive case_plan_v3.json from the frozen 09-25 case_plan_v2.json.

Every change against v2 is written here explicitly (and listed in the plan's
``revision_from_v2``) so a reviewer can see exactly what the 09-26 completion
adds: the courtyard tower that the single-building crop removed, its door to
the south core on every storey it serves, and the partly scanned glazed
column on the same core wall.  Nothing else in v2 is touched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
V2 = HERE.parent / '2026-09-25_voimatalo_opus_development/case_plan_v2.json'
OBS = HERE / 'observations/protrusion_measure.json'

# Tower footprint (BIM frame): west face on the courtyard wall plane, north face on
# the annex south plane, south/east from the measured stubs (see README table).
TOWER = {'x': [0.8, 2.5], 'y': [-25.9, -21.7], 'z': [0.0, 25.25]}
GLAZED_SPAN = [-27.75, -26.15]
# Sill/head band of the observed courtyard windows of the same storey (court_long R06..R01, S02 column).
STOREY_BANDS = {'F2': 'court_long_R06_S02', 'F3': 'court_long_R05_S02', 'F4': 'court_long_R04_S02',
                'F5': 'court_long_R03_S02', 'F6': 'court_long_R02_S02', 'F7': 'court_long_R01_S02'}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=HERE / 'case_plan_v3.json')
    args = parser.parse_args()
    v2 = json.loads(V2.read_text())
    plan = copy.deepcopy(v2)
    measure = json.loads(OBS.read_text())
    mapping = {r['id']: r for r in json.loads((V2.parent / 'candidate_01/opening_mapping.json').read_text())}

    plan['schema'] = 'voimatalo_developer_case_decisions_v3'
    plan['mode'] = ('Opus 5.5 09-26 development completion on top of the 09-25 case_plan_v2 (itself on 09-16 candidate_04). '
                    'Developer has seen all prior candidates; not a cold start and not a working-model result.')
    plan['derived_from'] = {'plan': str(V2.relative_to(ROOT)), 'plan_sha256': sha256(V2),
                            'builder': str(Path(__file__).relative_to(ROOT))}

    tower_obs = {k: measure[k] for k in ('north_stub_face_y≈-21.9', 'south_stub_face_y≈-25.9',
                                         'annex_south_face_y≈-21.75_below_7m')}
    tower_basis = (
        'Cropped courtyard tower. Observed: (1) a hole in the courtyard wall y -25.8..-21.9 at every height z 1..27 m '
        '(first hits land on the back of the street wall); (2) side-wall stubs on both hole edges running out of the '
        'courtyard plane from ground to z 25.6/26.05 m - north stub on y≈-21.9 reaching x≈2.4, south stub on y≈-25.9 '
        'reaching x≈1.3; (3) the annex south facade (y -21.75, windows at z 4.3-6.0) is a scanned, south-facing exterior '
        'face from x≈2.4 eastwards, so the tower cannot reach further east than ≈2.9 m at ground level; (4) nothing of the '
        'tower roof remains in the top view. Reading: a 4.2 m wide, ≈1.7 m deep full-height tower attached to the south '
        'core, cut away by the single-building crop. Depth x 0.8..2.5 is the measured stub (≥2.4) rounded inside the '
        'annex-facade bound (≤2.9); top 25.25 m aligns with the main roof slab (stubs end 0.35-0.8 m higher, read as parapet).')
    plan['continuous_spaces'].append({
        'key': 'TOWER_C', 'cell': 'lift_tower',
        'rect': [TOWER['x'][0], TOWER['y'][0], TOWER['x'][1], TOWER['y'][1]], 'z': TOWER['z'],
        'floors': ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7'],
        'role': 'vertical_circulation_lift_shaft_tower_hypothesis',
        'extends_storey_footprint': True,
        'evidence': tower_basis + ' Use: lift shafts serving F1-F7 from the south core (count not modelled); a WC/service '
                    'stack is the main alternative. Exterior faces are windowless because of the lift reading, not because '
                    'the scan shows blank walls (the east face and roof are cropped away).',
        'observation_refs': ['observations/protrusion_measure.json', 'observations/prot_oblique_se_grid.png',
                             'observations/annex_south_face_grid.png', 'observations/prot_top_grid.png'],
    })
    for row in plan['continuous_spaces']:
        if row['key'] == 'CORE_S':
            row['evidence'] = (
                'South service core: lift lobby in front of the courtyard lift tower TOWER_C (09-26 completion: the lifts '
                'are now assumed in the tower, one landing door per storey F1-F7) and room for a secondary stair lit by the '
                'multi-pane courtyard glazed column; in the windowless courtyard-side band under the southern raised roof '
                'mass. Continues into the set-back F8 landing through an open contact. Shafts, cars and stair flights are '
                'not modelled.')
    plan['connections']['F1'].append(['CORE_S', 'TOWER_C'])
    plan['connections']['typical'].append(['CORE_S', 'TOWER_C'])
    plan['connections']['note'] += ' 09-26: CORE_S/TOWER_C is the lift landing door on F1-F7 (skipped on F8, where neither exists).'

    # Unknown regions: the core's courtyard wall now splits into (a) the tower contact (interior wall with doors),
    # (b) the glazed column (inferred windows on F2-F7, ground storey stays unknown).
    regions = []
    for row in plan['enclosure']['unknown_wall_regions']:
        if row.get('space') == 'CORE_S_continuous':
            regions.append({**row, 'along': [-27.9, -25.9], 'z': [0.0, 5.6],
                            'reason': 'Ground storey of the courtyard glazed column beside the tower: the scan shows only '
                                      'fragments here and the courtyard ground is partly occluded; openings not decided. '
                                      'Upper storeys carry inferred windows (09-26).'})
        elif row.get('space') == 'F8_core_s_landing':
            regions.append({**row, 'reason': 'Above the inferred courtyard tower (top ≈25.25-26 m) the crop hole continues '
                                             'to ≈27 m; attic wall openings here stay unknown.'})
        else:
            regions.append(row)
    plan['enclosure']['unknown_wall_regions'] = regions

    glazed_basis = ('Partly scanned multi-pane glazed column on the courtyard face of the south core directly south of the '
                    'tower hole (court_strip_hi: glazing y≈-27.9..-26.0, visible on some storeys, crop holes on others). '
                    'Span trimmed 0.1-0.15 m inside the visible frame; sill/head copied from the observed courtyard window '
                    'of the same storey (column S02). Completion hypothesis, not a measured window per storey.')
    rows = plan['inferred_windows']['rows']
    for fid, ref in STOREY_BANDS.items():
        rows.append({'id': f'court_glazed_col_{fid}_inferred', 'view': 'court_long', 'plane_key': 'court_long',
                     'span_m': GLAZED_SPAN, 'z_m': mapping[ref]['z_m'], 'basis': glazed_basis,
                     'band_copied_from': ref})
    plan['inferred_windows']['basis_note'] = 'Rows with their own "basis" keep it; others use the shared basis above.'

    plan['assumptions'].append(
        '09-26 Opus 5.5 补全：内院南段被单体裁切掉的突出体按实测残留补成全高塔体（x 0.8–2.5、y -25.9–-21.7、z 0–25.25），'
        '判为电梯井塔，逐层F1–F7经南核进出；外墙无窗是电梯读法的结果，不是扫描看到的实墙。另一种读法是卫生间/服务竖向叠层。')
    plan['assumptions'].append(
        '09-26：南核院面多格玻璃竖列按可见部分补为F2–F7逐层推断窗（跨度取可见框内，窗台/窗顶沿用同层已观测院面窗）；首层该段仍未知。')
    plan['unresolved'] = [u for u in plan['unresolved'] if '内院被裁凸出体' not in u and '南端电梯只假设' not in u]
    # Coordinator correction: inherited backend text was not an EP validation.
    plan['unresolved'] = [u for u in plan['unresolved'] if '负荷会被当作外墙失真' not in u]
    plan['unresolved'].append('贴邻山墙的实际相邻条件及后端映射未验证；不能自动一律设为室外或绝热。本轮没有运行EnergyPlus，也未评估负荷影响。')
    plan['unresolved'] += [
        '内院塔体：位置、宽度与高度范围由残留约束，完整体量仍为补全假设；深度1.7 m只在≈1.6–2.1 m范围内有约束，顶部≈25.3–26 m；用途（电梯井/卫生间叠层/管井）与外墙开口未观测，按电梯读法无窗。电梯台数未建模，次楼梯只在南核中预留，未建梯段。',
        '南核院面玻璃竖列的逐层窗高按邻窗推断；首层同段和退台层塔顶以上的扫描洞仍未知。短翼内院东端扫描洞（x>15.3）本轮未处理。',
    ]
    plan['revision_from_v2'] = {
        'added_continuous_space': 'TOWER_C_lift_tower',
        'added_connections': ['F1: CORE_S/TOWER_C', 'typical: CORE_S/TOWER_C'],
        'added_inferred_windows': [f'court_glazed_col_{f}_inferred' for f in STOREY_BANDS],
        'changed_unknown_regions': ['CORE_S_continuous x=0.8: along -27.9..-21.8 z 0..25.25 -> along -27.9..-25.9 z 0..5.6',
                                    'F8_core_s_landing: reason text only'],
        'changed_storey_footprints': 'F1-F7 footprints = frozen shell + tower rectangle (7.14 m² each); F8, annex and roof parts unchanged',
        'changed_text': ['CORE_S evidence', 'connections.note', 'assumptions (+2)', 'unresolved (-2/+2)', 'Astra: remove inherited unverified EP-load/adiabatic assertion; clarify residual-derived volume uncertainty'],
        'unchanged': 'shell, storeys, roof parts, all other spaces/zones, all 300 windows and 88 doors of candidate_01',
        'tower_observations': tower_obs,
    }
    args.out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print('wrote', args.out, sha256(args.out))


if __name__ == '__main__':
    main()
