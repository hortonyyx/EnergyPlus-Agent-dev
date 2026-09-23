"""Post-generation audit; independent original observations never enter generation."""
from collections import Counter
import json
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point, Polygon

from scripts.tool_scripts.run_bim_agent import digest, dump
from scripts.tool_scripts.diagnose_partition_evidence import overlay
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.judge.gt import load_gt_document, gt_path
from src.agent.judge.partition_evidence import reference_partition
from src.agent.geometry.source_image_overlay import render_source_overlay

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def audit(run):
    assert (run / 'summary.json').is_file(), 'Generation must finish before evaluation'
    load = lambda p: json.loads((run / p).read_text())
    manifest = load('inputs.json')
    chosen = load('delivery.json')['candidate']
    source, proposal = load(f'{chosen}/source_model.json'), load(f'{chosen}/proposal.json')
    observation = json.loads((HERE / 'original_observations.json').read_text())
    assert digest(ROOT / observation['source_image']) == observation['source_sha256']
    assert manifest['images']['1f_view.png']['sha256'] == observation['source_sha256']
    hashes = {p: digest(ROOT / p) == h for p, h in manifest['implementation_sha256'].items()}
    assert all(hashes.values()), 'Runtime implementation changed'
    with tempfile.TemporaryDirectory(prefix='cold-plan-replay-') as tmp:
        target = Path(tmp) / 'candidate'
        export_source_proposal(proposal, target, provenance=source['generation']['provenance'])
        assert json.loads((target / 'source_model.json').read_text()) == source
        assert json.loads((target / 'display_geometry.json').read_text()) == load(f'{chosen}/display_geometry.json')

    def coordinate(value, axis):
        (p0, v0), (p1, v1) = observation['calibration'][axis + '_anchors']
        return v0 + (value - p0) * (v1 - v0) / (p1 - p0)

    spaces = {s['id']: Polygon(s['polygon']) for s in source['spaces']}
    identities = {}
    for name, (x, y) in observation['spaces'].items():
        point = Point(coordinate(x, 'x'), coordinate(y, 'y'))
        identities[name] = [key for key, polygon in spaces.items() if polygon.contains(point)]
    references = observation['apertures']
    actual = []
    for opening in source['openings']:
        xy = np.array(opening['vertices'])[:, :2]
        dim = int(np.argmax(np.ptp(xy, axis=0)))
        actual.append(dict(id=opening['id'], kind=opening['kind'], axis='xy'[dim],
                           span=[float(xy[:, dim].min()), float(xy[:, dim].max())],
                           cross=float(xy[:, 1-dim].mean()), space_ids=opening['space_ids'],
                           exterior=opening['exterior']))
    costs = np.full((len(references), len(actual)), 1e6)
    metrics = {}
    for i, ref in enumerate(references):
        span = sorted(coordinate(v, ref['axis']) for v in ref['span_pixels'])
        cross = coordinate(ref['cross_pixel'], 'y' if ref['axis'] == 'x' else 'x')
        for j, item in enumerate(actual):
            if (ref['kind'], ref['axis']) != (item['kind'], item['axis']):
                continue
            along = max(abs(a-b) for a, b in zip(span, item['span']))
            across = abs(cross-item['cross'])
            costs[i, j] = along+across
            metrics[i, j] = (span, cross, along, across)
    rows, matched_actual, matched_ref = [], set(), set()
    connection_by_id = {r['opening_id']: r for r in source['connections']}
    for i, j in zip(*linear_sum_assignment(costs)):
        if costs[i, j] >= 1e6:
            continue
        matched_actual.add(int(j)); matched_ref.add(int(i))
        ref, item = references[i], actual[j]
        span, cross, along, across = metrics[i, j]
        expected_hosts = sorted(v for name in ref['hosts'] for v in identities[name])
        hosts_resolved = all(len(identities[name]) == 1 for name in ref['hosts'])
        exterior = len(ref['hosts']) == 1
        host_match = (hosts_resolved and sorted(item['space_ids']) == expected_hosts
                      and item['exterior'] == exterior)
        connection = connection_by_id.get(item['id'])
        connection_match = (None if ref['kind'] != 'door' else bool(connection and
            sorted(connection['space_ids']) == expected_hosts and connection['exterior'] == exterior))
        tol = observation['tolerance']
        position_match = along <= tol['along_m'] and across <= tol['external_cross_m' if exterior else 'internal_cross_m']
        rows.append(dict(reference_id=ref['id'], opening_id=item['id'],
            reference_span_m=span, actual_span_m=item['span'], reference_cross_m=cross,
            actual_cross_m=item['cross'], max_endpoint_error_m=along, perpendicular_error_m=across,
            expected_hosts=expected_hosts, actual_hosts=item['space_ids'], host_match=host_match,
            connection_match=connection_match, position_match=position_match))

    # Scope the independent reference AFTER generation. Preserve original XY and
    # report vertical differences rather than grading unseen upper floors.
    gt = load_gt_document('sm21_anchor')
    selected_floors = [f for f in gt.floors if f.name == 'Floor 1']
    assert len(selected_floors) == 1, 'Explicit first-floor reference identity required'
    scoped = gt.model_copy(deep=True)
    scoped.floors = selected_floors
    scoped.windows = [w for w in gt.windows if w.floor == 'Floor 1']
    scoped.doors = [d for d in gt.doors if d.floor == 'Floor 1']
    report = reference_partition(ensure_corrected_geometry(proposal['geometry']), scoped,
                                 source_spaces=source['spaces'])
    target = run / 'evaluation'
    target.mkdir(exist_ok=True)
    calibration = observation['calibration']
    with Image.open(run / 'images/1f_view.png') as original:
        rendered, metadata = render_source_overlay(source, original.convert('RGB'),
            floor_id=source['spaces'][0]['floor_id'],
            x_anchors=calibration['x_anchors'], y_anchors=calibration['y_anchors'],
            basis=calibration['basis'], image_name='1f_view.png')
    rendered.save(target / 'independent_original_overlay.png')
    rendered.crop((720, 520, 1035, 845)).resize((630, 650)).save(
        target / 'independent_corridor_detail.png')
    dump(target / 'independent_original_overlay.json', metadata)
    dump(target / 'partition.json', report)
    dump(target / 'reference_scope.json', dict(case='sm21_anchor',
        original_reference_sha256=digest(gt_path('sm21_anchor')), included_floor_names=['Floor 1'],
        excluded_floor_names=[f.name for f in gt.floors if f.name != 'Floor 1'],
        geometry_transform=None, heights_acceptance='not_evaluated_plan_only_input'))
    dump(target / 'original_openings.json', dict(observation_sha256=digest(HERE / 'original_observations.json'),
        tolerance=observation['tolerance'], space_identity_by_interior_point=identities,
        comparisons=rows, unmatched_reference=[r['id'] for i,r in enumerate(references) if i not in matched_ref],
        unmatched_actual=[r['id'] for i,r in enumerate(actual) if i not in matched_actual]))
    result = dict(mode='post_generation_developer_audit', candidate=chosen,
        source_replay_exact=True, display_replay_exact=True, runtime_hashes_match=True,
        input_contents=manifest['input_contents'],
        counts=dict(spaces=len(spaces), openings=dict(Counter(o['kind'] for o in source['openings'])),
                    connections=len(source['connections']), unsupported=len(source['unsupported']),
                    unbuilt_openings=len(source['unbuilt_openings'])),
        partition_status=report['status'], partition_topology_findings=report['topology_findings'],
        original_aperture_count=len(references), matched_apertures=len(rows),
        position_matches=sum(r['position_match'] for r in rows), host_matches=sum(r['host_match'] for r in rows),
        door_connections_matched=sum(r['connection_match'] is True for r in rows),
        max_aperture_endpoint_error_m=max((r['max_endpoint_error_m'] for r in rows), default=None),
        viewer_has_no_remote_scripts='<script src="http' not in (run/chosen/'viewer.html').read_text(),
        limits=observation['limits']+['One bounded cold start does not establish repeatability or whole-building autonomy.',
                                    'No browser WebGL interaction was tested in this audit.'])
    dump(run / 'postrun_audit.json', result)
    (target / 'partition.html').write_text('<!doctype html><meta charset="utf-8">'+
        overlay(report['reference_spaces'], report['candidate_spaces'], 'Floor 1'), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    audit(parser.parse_args().run.resolve())
