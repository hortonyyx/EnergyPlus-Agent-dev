"""Post-generation full plan inventory checks; no evaluation data enters generation."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.geometry.source_image_overlay import render_source_overlay

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
load = lambda p: json.loads(p.read_text())


def save_reference():
    prior = HERE.parent / '2026-09-24_sm25_cold_support_setup/original_observations.json'
    first = load(prior)
    first['source_image'] = 'case_tests/e2e_tests/sm25-L_anchor/case_data/1f_view.png'
    second_image = ROOT / 'case_tests/e2e_tests/sm25-L_anchor/case_data/2f_view.png'
    apertures = []

    def add(name, kind, axis, cross, span, hosts):
        apertures.append(dict(id=name, kind=kind, axis=axis, cross_pixel=cross,
                              span_pixels=span, hosts=hosts))

    for name, span in [('NW1', [343, 454]), ('NW2', [486, 597]), ('NE', [713, 741])]:
        add('WN_' + name, 'window', 'x', 346.5, span, [name])
    for number, span in enumerate(([558, 600], [632, 674], [742, 784], [816, 858], [908, 950]), 1):
        add(f'WE{number}', 'window', 'y', 923.5, span, [f'E{number}'])
    add('WW', 'window', 'y', 475.5, [700, 899], ['W'])
    add('WW_C', 'window', 'y', 475.5, [1008, 1063], ['C'])
    add('WN_C', 'window', 'x', 988.5, [942, 1310], ['C'])
    for number, span in enumerate(([558, 642], [674, 757], [917, 1000], [1032, 1116], [1217, 1300]), 1):
        add(f'WS{number}', 'window', 'x', 1252.5, span, [f'S{number}'])
    for name, span in [('NW1', [417, 454]), ('NW2', [486, 524]), ('NE', [704, 741])]:
        add('DN_' + name, 'door', 'x', 522, span, [name, 'C'])
    for number, span in enumerate(([563, 600], [633, 670], [746, 784], [816, 853], [908, 945]), 1):
        add(f'DE{number}', 'door', 'y', 747.5, span, [f'E{number}', 'C'])
    add('DW', 'door', 'y', 651, [630, 704], ['W', 'C'])
    for number, span in enumerate(([604, 642], [674, 711], [963, 1000], [1032, 1070], [1217, 1255]), 1):
        add(f'DS{number}', 'door', 'x', 1077.5, span, [f'S{number}', 'C'])
    second = dict(source_image=str(second_image.relative_to(ROOT)), source_sha256=digest(second_image),
        calibration=dict(x_anchors=[[241, 0], [1387, 25]], y_anchors=[[341, 20], [1258, 0]],
            basis='Original 25000/20000 mm outer extension endpoints; no generated calibration or candidate fit.'),
        spaces=dict(NW1=[350, 430], NW2=[580, 430], NE=[800, 430], W=[550, 800],
                    E1=[850, 570], E2=[850, 660], E3=[850, 750], E4=[850, 850], E5=[850, 940],
                    S1=[550, 1150], S2=[760, 1150], S3=[930, 1150], S4=[1110, 1150], S5=[1300, 1150],
                    C=[705, 800]),
        apertures=apertures, tolerance=first['tolerance'])
    reference = dict(floors=[first, second], prior_first_floor_reference_sha256=digest(prior),
        isolation='Evaluation-only. F1 reference reused unchanged; F2 read from clean original and original cyan components/grey wall scans before opening run53/54 candidate geometry this session.',
        basis='Manual semantic interpretation supported by original pixel components. Door arc bounds identify jamb span on the wall, not another wall.',
        limits=['Approximate original-pixel reference, not a measured survey or automated semantic judge.',
                'Interior points test room identity; complete room shapes remain subject to the separate GT partition check.',
                'No interior height, operating state, material, thickness or vertical circulation validation.',
                'Existing F1 tolerances reused for both floors, with independent original calibration; no fit to candidate.'])
    assert len(second['apertures']) == 30
    dump(HERE / 'original_reference.json', reference)
    return reference


def audit(run, reference, *, output=None):
    assert (run / 'summary.json').is_file()
    delivery = load(run / 'delivery.json')
    source = load(run / delivery['candidate'] / 'source_model.json')
    assert source['source_model_sha256'] == delivery['source_model_sha256']
    floors = sorted(source['floors'], key=lambda f: f['z_floor'])
    assert len(floors) == len(reference['floors']) == 2
    output = output or HERE / run.name
    output.mkdir(exist_ok=True)
    comparisons, floor_reports = [], []
    for floor, obs in zip(floors, reference['floors']):
        name = Path(obs['source_image']).name
        assert digest(run / 'images' / name) == obs['source_sha256']

        def coordinate(value, axis):
            (p0, v0), (p1, v1) = obs['calibration'][axis + '_anchors']
            return v0 + (value - p0) * (v1 - v0) / (p1 - p0)

        spaces = {s['id']: Polygon(s['polygon']) for s in source['spaces'] if s['floor_id'] == floor['id']}
        identities = {key: [sid for sid, poly in spaces.items()
                           if poly.contains(Point(coordinate(p[0], 'x'), coordinate(p[1], 'y')))]
                      for key, p in obs['spaces'].items()}
        actual = []
        for opening in source['openings']:
            if not any(s in spaces for s in opening['space_ids']):
                continue
            xy = np.array(opening['vertices'])[:, :2]
            dim = int(np.argmax(np.ptp(xy, axis=0)))
            actual.append(dict(id=opening['id'], kind=opening['kind'], axis='xy'[dim],
                span=[float(xy[:, dim].min()), float(xy[:, dim].max())], cross=float(xy[:, 1-dim].mean()),
                space_ids=opening['space_ids'], exterior=opening['exterior']))
        costs = np.full((len(obs['apertures']), len(actual)), 1e6)
        metrics = {}
        for i, r in enumerate(obs['apertures']):
            span = sorted(coordinate(v, r['axis']) for v in r['span_pixels'])
            cross = coordinate(r['cross_pixel'], 'y' if r['axis'] == 'x' else 'x')
            for j, a in enumerate(actual):
                if (r['kind'], r['axis']) != (a['kind'], a['axis']):
                    continue
                along = max(abs(x-y) for x, y in zip(span, a['span']))
                across = abs(cross-a['cross'])
                costs[i, j] = along+across
                metrics[i, j] = (along, across)
        matched_r, matched_a = set(), set()
        for i, j in zip(*linear_sum_assignment(costs)):
            if costs[i, j] >= 1e6:
                continue
            matched_r.add(int(i)); matched_a.add(int(j))
            r, a = obs['apertures'][i], actual[j]
            along, across = metrics[i, j]
            hosts = sorted(s for h in r['hosts'] for s in identities[h])
            exterior = len(r['hosts']) == 1
            host_ok = (all(len(identities[h]) == 1 for h in r['hosts']) and
                       len(set(hosts)) == len(r['hosts']) and sorted(a['space_ids']) == hosts and a['exterior'] == exterior)
            connections = [c for c in source['connections'] if c['opening_id'] == a['id']]
            connected = None if r['kind'] != 'door' else bool(host_ok and len(connections) == 1 and
                sorted(connections[0]['space_ids']) == hosts and connections[0]['exterior'] == exterior)
            tol = obs['tolerance']
            position = along <= tol['along_m'] and across <= tol['external_cross_m' if exterior else 'internal_cross_m']
            comparisons.append(dict(floor_id=floor['id'], reference_id=r['id'], kind=r['kind'],
                exterior=exterior, opening_id=a['id'], max_endpoint_error_m=along,
                perpendicular_error_m=across, position_match=bool(position), expected_hosts=hosts,
                actual_hosts=a['space_ids'], host_match=bool(host_ok), connection_match=connected))
        floor_reports.append(dict(floor_id=floor['id'], image=name, space_identity_by_interior_point=identities,
            unmatched_reference=[r['id'] for i, r in enumerate(obs['apertures']) if i not in matched_r],
            unmatched_actual=[a['id'] for i, a in enumerate(actual) if i not in matched_a]))
        with Image.open(run / 'images' / name) as original:
            overlay, metadata = render_source_overlay(source, original.convert('RGB'), floor_id=floor['id'],
                image_name=name, **obs['calibration'])
        overlay.save(output / f'original_{name}')
        dump(output / f'original_{name}.json', metadata)
    internal = [r for r in comparisons if r['kind'] == 'door' and not r['exterior']]
    report = dict(run=run.name, candidate=delivery['candidate'], source_model_sha256=source['source_model_sha256'],
        reference_sha256=digest(HERE / 'original_reference.json'),
        reference_count=sum(len(f['apertures']) for f in reference['floors']), matched=len(comparisons),
        positions=sum(r['position_match'] for r in comparisons), hosts=sum(r['host_match'] for r in comparisons),
        door_connections=sum(r['connection_match'] is True for r in comparisons),
        internal_door_count=len(internal), internal_positions=sum(r['position_match'] for r in internal),
        internal_hosts=sum(r['host_match'] for r in internal),
        internal_connections=sum(r['connection_match'] is True for r in internal),
        floors=floor_reports, comparisons=comparisons, limits=reference['limits'])
    dump(output / 'report.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('floors', 'comparisons', 'limits')}, indent=2))
    return report


if __name__ == '__main__':
    reference = save_reference()
    for name in ('2026-09-26_sm25_height_cold_claude_run53', '2026-09-26_sm25_height_repeat_claude_run54'):
        audit(HERE.parent / name, reference)
