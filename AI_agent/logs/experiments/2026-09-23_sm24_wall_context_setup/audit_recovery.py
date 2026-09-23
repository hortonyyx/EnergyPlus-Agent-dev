"""Post-generation evaluation in both original and explicitly declared frames."""
import argparse
import importlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

from scripts.tool_scripts.run_bim_agent import dump
from src.agent.judge.source_partition import compare_partitions
from scripts.tool_scripts.diagnose_partition_evidence import overlay

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'2026-09-23_sm24_cold_plan_setup'


def audit(run):
    assert (run/'summary.json').exists(), 'Evaluation follows generation'
    importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run').audit(run)
    load = lambda p: json.loads(p.read_text())
    raw_audit = load(run/'postrun_audit.json')
    raw_audit['limits'] = [line for line in raw_audit['limits'] if not line.startswith('One bounded cold start')]
    raw_audit['limits'].append('Developer-targeted saved-plan recovery, not a cold start or autonomous problem selection.')
    dump(run/'postrun_audit.json', raw_audit)
    obs = load(OLD/'original_observations.json')
    plan = load(run/'resume_plan.json')
    chosen = load(run/'delivery.json')['candidate']
    source = load(run/chosen/'source_model.json')
    original = load(HERE.parent/'2026-09-23_sm24_cold_plan_glm_run32/candidate_01/source_model.json')
    # Scope freezes the declared frame. Refuse an implicit fitted comparison.
    calibrations = list(run.glob('overlay_calibrations/*.json'))
    assert calibrations, 'A registered calibration is required for this declared-frame diagnostic'
    for path in calibrations:
        calibration = load(path)
        for axis in 'xy':
            if axis+'_anchors' in calibration:
                assert calibration[axis+'_anchors'] == plan[axis+'_anchors']

    def interpolate(v, anchors):
        (a, b), (c, d) = anchors
        return b+(v-a)*(d-b)/(c-a)

    def original_xy(xy):
        return [interpolate(v, obs['calibration'][axis+'_anchors']) for v, axis in zip(xy, 'xy')]

    def reframe(xy):
        return original_xy([interpolate(v, [(b, a) for a, b in plan[axis+'_anchors']])
                            for v, axis in zip(xy, 'xy')])

    refs = [dict(id=k, floor_id='F1', z_floor=0, height=1, polygon=[original_xy(p) for p in ring])
            for k, ring in obs['space_polygons_pixels'].items()]
    actual = [dict(s, floor_id='F1', z_floor=0, height=1, polygon=[reframe(p) for p in s['polygon']])
              for s in source['spaces']]
    coverage = {r['id']: [dict(candidate=s['id'],
        reference_area_fraction=Polygon(r['polygon']).intersection(Polygon(s['polygon'])).area/Polygon(r['polygon']).area)
        for s in actual if Polygon(r['polygon']).intersection(Polygon(s['polygon'])).area > .1] for r in refs}
    identities = {name: [s['id'] for s in actual if Polygon(s['polygon']).contains(Point(original_xy(xy)))]
                  for name, xy in obs['spaces'].items()}
    openings = []
    for o in source['openings']:
        xy = np.array([reframe(p[:2]) for p in o['vertices']])
        dim = int(np.argmax(np.ptp(xy, axis=0)))
        openings.append(dict(id=o['id'], kind=o['kind'], axis='xy'[dim],
            span=[float(xy[:, dim].min()), float(xy[:, dim].max())], cross=float(xy[:, 1-dim].mean()),
            space_ids=o['space_ids'], exterior=o['exterior']))
    costs = np.full((len(obs['apertures']), len(openings)), 1e6)
    metrics = {}
    for i, ref in enumerate(obs['apertures']):
        span = sorted(interpolate(v, obs['calibration'][ref['axis']+'_anchors']) for v in ref['span_pixels'])
        cross = interpolate(ref['cross_pixel'], obs['calibration'][('y' if ref['axis']=='x' else 'x')+'_anchors'])
        for j, item in enumerate(openings):
            if (ref['kind'], ref['axis']) == (item['kind'], item['axis']):
                along = max(abs(a-b) for a, b in zip(span, item['span']))
                across = abs(cross-item['cross'])
                costs[i, j] = along+across
                metrics[i, j] = along, across
    comparisons = []
    connections = {c['opening_id']: c for c in source['connections']}
    for i, j in zip(*linear_sum_assignment(costs)):
        if costs[i, j] >= 1e6:
            continue
        ref, item = obs['apertures'][i], openings[j]
        along, across = metrics[i, j]
        expected = sorted(v for name in ref['hosts'] for v in identities[name])
        resolved = all(len(identities[name]) == 1 for name in ref['hosts'])
        exterior = len(ref['hosts']) == 1
        connection = connections.get(item['id'])
        tol = obs['tolerance']
        comparisons.append(dict(reference=ref['id'], actual=item['id'],
            endpoint_error_m=along, cross_error_m=across,
            position_match=along <= tol['along_m'] and across <= tol['external_cross_m' if exterior else 'internal_cross_m'],
            hosts_match=resolved and sorted(item['space_ids']) == expected and item['exterior'] == exterior,
            connection_match=None if ref['kind'] != 'door' else bool(resolved and connection and
                sorted(connection['space_ids']) == expected and connection['exterior'] == exterior)))
    old_openings = {o['id']: o for o in original['openings']}
    preserved = [o['id'] for o in source['openings'] if o['id'] in old_openings and
                 o['vertices'] == old_openings[o['id']]['vertices'] and o['kind'] == old_openings[o['id']]['kind']]
    report = dict(mode='diagnostic_only_declared_anchor_transform_not_adopted', candidate=chosen,
        method='Invert unchanged submitted anchors, then apply frozen independent original anchors; no fit, no height acceptance, raw candidate/evaluation untouched.',
        declared_anchors={a: plan[a] for a in ('x_anchors', 'y_anchors')}, independent_anchors=obs['calibration'],
        reference_spaces=refs, candidate_spaces=actual, reference_area_coverage=coverage,
        comparison=compare_partitions(refs, actual, tolerance_m=obs['tolerance']['original_partition_m']),
        openings=comparisons, source_opening_count=len(openings), reference_opening_count=len(obs['apertures']),
        positions_matched=sum(r['position_match'] for r in comparisons), hosts_matched=sum(r['hosts_match'] for r in comparisons),
        door_connections_matched=sum(r['connection_match'] is True for r in comparisons),
        unchanged_opening_geometry=preserved,
        changed_opening_geometry=[o['id'] for o in source['openings'] if o['id'] not in preserved],
        removed_openings=sorted(set(old_openings)-{o['id'] for o in source['openings']}))
    dump(run/'evaluation/declared_frame_diagnostic.json', report)
    (run/'evaluation/declared_frame_partition.html').write_text(
        '<!doctype html><meta charset="utf-8"><h1>Declared-frame diagnostic; no candidate mutation</h1>'+overlay(refs, actual, 'F1'))
    print(json.dumps({k: report[k] for k in ('candidate', 'positions_matched', 'hosts_matched',
        'door_connections_matched', 'changed_opening_geometry', 'removed_openings')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run.resolve())
