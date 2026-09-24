"""Post-generation full-path recovery audit using the unchanged original reference."""
import argparse
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.judge.source_partition import compare_partitions
from scripts.tool_scripts.diagnose_partition_evidence import overlay

HERE = Path(__file__).resolve().parent
OLD = HERE.parent/'2026-09-23_sm24_cold_plan_setup'


def audit(run):
    assert (run/'summary.json').exists(), 'Evaluation follows generation'
    importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run').audit(run)
    load = lambda p: json.loads(p.read_text())
    raw = load(run/'postrun_audit.json')
    raw['limits'] = [v for v in raw['limits'] if not v.startswith('One bounded cold start')]
    raw['limits'].append('Saved-plan recovery with explicit full-path tool use; not a cold start or repeated stability test.')
    dump(run/'postrun_audit.json', raw)
    obs = load(OLD/'original_observations.json')
    chosen = load(run/'delivery.json')['candidate']
    source = load(run/chosen/'source_model.json')
    # Take the actual generating declaration, never a draft chosen by its score.
    provenance = source['generation']['provenance']
    plan_input = provenance['plan_input']
    assert digest(run/plan_input['plan_file']) == plan_input['plan_sha256']
    plan = load(run/plan_input['plan_file'])
    manifest = load(run/'inputs.json')
    frozen = load(HERE/'experiment.json')
    assert manifest['scope'] == frozen['scope']
    assert manifest['input_mode'] == 'saved_plan_recovery'
    assert manifest['source_input_mode'] == 'original_images_only'
    assert digest(run/'resume_plan.json') == frozen['input_plan_sha256']
    assert not (run/'seed').exists()
    assert manifest['images']['1f_view.png']['sha256'] == frozen['image_sha256']
    assert not any(manifest['input_contents'][k]['included'] for k in
                   ('building_declaration', 'saved_generated_proposal', 'ground_truth_or_evaluation'))
    receipt = load(run/'agent_receipt.json')
    assert receipt['actual_model'] == 'glm-5.3-flash'
    assert list(receipt['result']['modelUsage']) == ['glm-5.3-flash']

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
    report = dict(mode='diagnostic_only_declared_anchor_transform_not_adopted', candidate=chosen,
        method='Invert the actual submitted anchors, then apply frozen independent original anchors; no fit, no height acceptance, raw candidate/evaluation untouched.',
        declared_anchors={a: plan[a] for a in ('x_anchors', 'y_anchors')}, independent_anchors=obs['calibration'],
        reference_spaces=refs, candidate_spaces=actual, reference_area_coverage=coverage,
        comparison=compare_partitions(refs, actual, tolerance_m=obs['tolerance']['original_partition_m']),
        openings=comparisons, source_opening_count=len(openings), reference_opening_count=len(obs['apertures']),
        positions_matched=sum(r['position_match'] for r in comparisons), hosts_matched=sum(r['hosts_match'] for r in comparisons),
        door_connections_matched=sum(r['connection_match'] is True for r in comparisons),
        plan_file=plan_input['plan_file'],
        unmatched_reference=sorted(set(o['id'] for o in obs['apertures'])-set(r['reference'] for r in comparisons)),
        unmatched_actual=sorted(set(o['id'] for o in openings)-set(r['actual'] for r in comparisons)))
    dump(run/'evaluation/declared_frame_diagnostic.json', report)
    (run/'evaluation/declared_frame_partition.html').write_text(
        '<!doctype html><meta charset="utf-8"><h1>Declared-frame diagnostic; no candidate mutation</h1>'+overlay(refs, actual, 'F1'))
    importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run').finalize(run)
    rows = [json.loads(s) for s in (run/'tools.jsonl').read_text().splitlines()]
    dump(run/'evaluation/observation_and_edit_trace.json', dict(
        note='Actual model-chosen sequence; no developer intervention or semantic acceptance implied.',
        trace=[dict(action=r['action'], seconds_from_first_tool=round(r['time']-rows[0]['time'], 2),
                    box=r['data'].get('box_original_pixels', r['data'].get('box')),
                    candidate=r['data'].get('candidate'), counts=r['data'].get('counts'),
                    error=r['data'].get('error')) for r in rows]))
    calls = [r for r in load(run/'transport_audit.json')['images'] if r['tool'].endswith('__overlay_candidate')]
    overlays = [r['data'] for r in rows if r['action'] == 'overlay_candidate']
    assert len(calls) == len(overlays)
    for call, meta in zip(calls, overlays):
        with Image.open(run/meta['overlay_image']) as im:
            im = im.convert('RGB')
            if meta.get('box_original_pixels'):
                im = im.crop(meta['box_original_pixels'])
            im.thumbnail((1600, 1600))
            assert hashlib.sha256(im.tobytes()).hexdigest() == call['pixels_sha256']
    dump(run/'evaluation/recovery_audit.json', dict(
        input_mode=manifest['input_mode'], frozen_method_and_original_verified=True,
        actual_model=receipt['actual_model'], elapsed_seconds=receipt['elapsed_seconds'],
        cli_estimated_usd_not_bill=receipt['result']['total_cost_usd'],
        tools=dict(Counter(r['action'] for r in rows)), exact_returned_overlay_count=len(calls),
        declared_frame_partition_status=report['comparison']['status'],
        declared_frame_spaces_matched=report['comparison']['matched_count'],
        declared_frame_positions_matched=report['positions_matched'],
        declared_frame_hosts_matched=report['hosts_matched'],
        declared_frame_door_connections_matched=report['door_connections_matched'],
        limitations=['A single tool-directed saved-plan recovery; no cold-start, repeatability or full-height acceptance.',
                     'Declared-frame diagnostic does not replace raw original/GT scores.']))
    print(json.dumps({k: report[k] for k in ('candidate', 'positions_matched', 'hosts_matched',
        'door_connections_matched', 'unmatched_reference', 'unmatched_actual')}, indent=2))



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run.resolve())
