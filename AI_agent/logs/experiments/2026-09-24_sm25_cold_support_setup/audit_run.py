"""Independent post-generation plan audit; nothing here is exposed to the agent."""
from collections import Counter
import hashlib
import importlib
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
from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.judge.gt import load_gt_document, gt_path
from src.agent.judge.source_partition import compare_partitions

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text())


def interpolate(value, anchors):
    (p0, v0), (p1, v1) = anchors
    return v0 + (value-p0)*(v1-v0)/(p1-p0)


def compare_original(source, observation, transform):
    cal = observation['calibration']
    def world(point):
        return [interpolate(v, cal[a+'_anchors']) for a,v in zip('xy', point)]
    refs = [dict(id=name, floor_id='F1', z_floor=0, height=1,
                 polygon=[world(p) for p in ring])
            for name,ring in observation['space_polygons_pixels'].items()]
    actual = [dict(s, floor_id='F1', z_floor=0, height=1,
                   polygon=[transform(p) for p in s['polygon']]) for s in source['spaces']]
    identities = {name: [s['id'] for s in actual if Polygon(s['polygon']).contains(Point(world(point)))]
                  for name,point in observation['spaces'].items()}
    openings = []
    for opening in source['openings']:
        xy = np.array([transform(v[:2]) for v in opening['vertices']])
        axis = int(np.argmax(np.ptp(xy, axis=0)))
        openings.append(dict(id=opening['id'], kind=opening['kind'], axis='xy'[axis],
            span=[float(xy[:,axis].min()),float(xy[:,axis].max())],
            cross=float(xy[:,1-axis].mean()), space_ids=opening['space_ids'], exterior=opening['exterior']))
    refs_open = observation['apertures']
    costs = np.full((len(refs_open), len(openings)), 1e6)
    errors = {}
    for i,ref in enumerate(refs_open):
        span = sorted(interpolate(v,cal[ref['axis']+'_anchors']) for v in ref['span_pixels'])
        cross = interpolate(ref['cross_pixel'],cal[('y' if ref['axis']=='x' else 'x')+'_anchors'])
        for j,item in enumerate(openings):
            if (ref['kind'],ref['axis']) == (item['kind'],item['axis']):
                along = max(abs(a-b) for a,b in zip(span,item['span']))
                across = abs(cross-item['cross'])
                costs[i,j] = along+across
                errors[i,j] = along,across
    comparisons = []
    connections = {c['opening_id']:c for c in source['connections']}
    for i,j in zip(*linear_sum_assignment(costs)):
        if costs[i,j] >= 1e6:
            continue
        ref,item = refs_open[i],openings[j]
        along,across = errors[i,j]
        expected = sorted(v for name in ref['hosts'] for v in identities[name])
        resolved = all(len(identities[name]) == 1 for name in ref['hosts'])
        exterior = len(ref['hosts']) == 1
        connection = connections.get(item['id'])
        tol = observation['tolerance']
        comparisons.append(dict(reference=ref['id'], actual=item['id'], kind=ref['kind'],
            endpoint_error_m=along, cross_error_m=across,
            position_match=along<=tol['along_m'] and across<=tol['external_cross_m' if exterior else 'internal_cross_m'],
            expected_hosts=expected, actual_hosts=item['space_ids'],
            hosts_match=resolved and sorted(item['space_ids'])==expected and item['exterior']==exterior,
            connection_match=None if ref['kind']!='door' else bool(resolved and connection and
                sorted(connection['space_ids'])==expected and connection['exterior']==exterior)))
    return dict(reference_spaces=refs,candidate_spaces=actual,space_identities=identities,
        comparison=compare_partitions(refs,actual,tolerance_m=observation['tolerance']['original_partition_m']),
        openings=comparisons, positions_matched=sum(r['position_match'] for r in comparisons),
        hosts_matched=sum(r['hosts_match'] for r in comparisons),
        door_connections_matched=sum(r['connection_match'] is True for r in comparisons),
        unmatched_reference=sorted(set(o['id'] for o in refs_open)-set(r['reference'] for r in comparisons)),
        unmatched_actual=sorted(set(o['id'] for o in openings)-set(r['actual'] for r in comparisons)))


def audit(run):
    assert (run/'summary.json').is_file(), 'Evaluation follows generation'
    frozen = load(HERE/'frozen_supported_method.json')
    manifest,receipt = load(run/'inputs.json'),load(run/'agent_receipt.json')
    assert manifest['implementation_sha256'] == frozen['implementation_sha256']
    assert all(digest(ROOT/p)==h for p,h in manifest['implementation_sha256'].items())
    assert manifest['scope'] == frozen['scope']
    assert manifest['input_mode']=='original_images_agent_experiment'
    assert manifest['source_input_mode']=='original_images_only'
    assert not any(manifest['input_contents'][k]['included'] for k in
        ('building_declaration','saved_generated_proposal','ground_truth_or_evaluation'))
    assert receipt['actual_model']=='glm-5.3-flash'
    chosen = load(run/'delivery.json')['candidate']
    source,proposal = load(run/chosen/'source_model.json'),load(run/chosen/'proposal.json')
    assert len(source['floors']) == 1
    obs = load(HERE/'original_observations.json')
    assert digest(ROOT/obs['source_image'])==obs['source_sha256']==frozen['image_sha256']
    rows = [json.loads(line) for line in (run/'tools.jsonl').read_text().splitlines()]
    builds = [r for r in rows if r['action']=='build_plan_bim']
    assert obs['recorded_epoch'] < builds[0]['time'], 'Reference predates first declaration'
    origin = source
    origin_candidate = chosen
    lineage = []
    while 'plan_input' not in origin['generation']['provenance']:
        provenance = origin['generation']['provenance']
        parent = provenance['parent_candidate']
        assert Path(parent).name == parent and parent.startswith('candidate_')
        assert parent not in lineage
        assert digest(run/parent/'proposal.json') == provenance['parent_proposal_sha256']
        lineage.append(parent)
        origin_candidate = parent
        origin = load(run/parent/'source_model.json')
    # This run's selected revision changes notes only; the inverse plan frame
    # must never be silently reused after a coordinate-changing revision.
    assert all(source[k] == origin[k] for k in ('floors','spaces','boundaries','openings','connections'))
    plan_input = origin['generation']['provenance']['plan_input']
    assert digest(run/plan_input['plan_file'])==plan_input['plan_sha256']
    plan = load(run/plan_input['plan_file'])
    with tempfile.TemporaryDirectory(prefix='sm25-cold-replay-') as tmp:
        target = Path(tmp)/'candidate'
        export_source_proposal(proposal,target,provenance=source['generation']['provenance'])
        assert load(target/'source_model.json')==source
        assert load(target/'display_geometry.json')==load(run/chosen/'display_geometry.json')
    out = run/'evaluation'; out.mkdir(exist_ok=True)
    def declared_to_original(point):
        return [interpolate(interpolate(v,[(b,a) for a,b in plan[axis+'_anchors']]),
                            obs['calibration'][axis+'_anchors']) for axis,v in zip('xy',point)]
    raw = compare_original(source,obs,lambda p:p)
    reframed = compare_original(source,obs,declared_to_original)
    for name,data in [('original',raw),('declared_frame',reframed)]:
        dump(out/f'{name}_comparison.json',data)
        (out/f'{name}_partition.html').write_text('<!doctype html><meta charset="utf-8">'+
            f'<h1>{name}: independent plan reference, heights excluded</h1>'+
            overlay(data['reference_spaces'],data['candidate_spaces'],'F1'))
    rendered,metadata = render_source_overlay(source,Image.open(run/'images/1f_view.png').convert('RGB'),
        floor_id=source['floors'][0]['id'],image_name='1f_view.png',**obs['calibration'])
    rendered.save(out/'independent_original_overlay.png')
    dump(out/'independent_original_overlay.json',metadata)
    gt = load_gt_document('sm25-L_anchor')
    floor = next(f for f in gt.floors if f.id=='F1')
    gt_refs = [dict(id=z.id,floor_id='F1',z_floor=floor.z_floor_m,height=floor.ceiling_height_m,
                   polygon=z.polygon.exterior.vertices) for z in floor.zones]
    gt_actual = [dict(s,floor_id='F1') for s in source['spaces']]
    dump(out/'gt_partition.json',dict(reference_sha256=digest(gt_path('sm25-L_anchor')),
        scope='F1 only, original XY/heights unmodified; F2 not supplied and excluded',
        comparison=compare_partitions(gt_refs,gt_actual,tolerance_m=.02)))
    finalizer = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run')
    finalizer.finalize(run)
    transport=load(run/'transport_audit.json')
    feedback=[r for r in transport['images'] if any(r['tool'].endswith('__'+n)
        for n in ('build_plan_bim','view_plan_wall_support','view_pixel_profile'))]
    # Failed-draft previews are sent at their native size, unlike overlays and
    # full-path images. The older common audit indexes only 1600px thumbnails.
    native_pixels = {}
    for path in run.rglob('*.png'):
        if 'evaluation' in path.parts:
            continue
        with Image.open(path) as pic:
            key=hashlib.sha256(pic.convert('RGB').tobytes()).hexdigest()
        native_pixels.setdefault(key,[]).append(str(path.relative_to(run)))
    verified_feedback = [dict(r,matching_native_files=native_pixels.get(r['pixels_sha256'],[]))
                         for r in feedback]
    assert all(r['matching_saved_files'] or r['matching_native_files'] for r in verified_feedback)
    dump(out/'actual_feedback_images.json',dict(images=verified_feedback,
        note='Compare exact native draft previews and exact runtime thumbnails independently; no semantic acceptance.'))
    result=dict(candidate=chosen,actual_model=receipt['actual_model'],elapsed_seconds=receipt['elapsed_seconds'],
        estimated_cost_usd_not_bill=receipt.get('result',{}).get('total_cost_usd'),
        cold_input_and_runtime_verified=True,source_replay_exact=True,display_replay_exact=True,
        reference_predates_first_submission=True,plan_origin_candidate=origin_candidate,
        selected_geometry_unchanged_from_plan_origin=True,counts={k:len(source[k]) for k in
            ('spaces','openings','connections','unsupported','unbuilt_openings')},
        opening_kinds=dict(Counter(o['kind'] for o in source['openings'])),
        tools=dict(Counter(r['action'] for r in rows)),transported_image_count=transport['image_count'],
        exact_saved_feedback_images=len(feedback),viewer_has_no_remote_scripts='<script src="http' not in (run/chosen/'viewer.html').read_text(),
        comparisons={name:dict(partition_status=data['comparison']['status'],matched_spaces=data['comparison']['matched_count'],
            positions_matched=data['positions_matched'],hosts_matched=data['hosts_matched'],
            door_connections_matched=data['door_connections_matched'],
            unmatched_reference=data['unmatched_reference'],unmatched_actual=data['unmatched_actual'])
            for name,data in [('original',raw),('declared_frame',reframed)]},
        limitations=obs['limits']+['Single-floor cold start; whole-building autonomy/repeatability and WebGL interaction not evaluated.',
            'Declared-frame transform inverts submitted anchors; no candidate fitting or source mutation. Raw scores retained.'])
    dump(run/'postrun_audit.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--run',type=Path,required=True)
    audit(parser.parse_args().run.resolve())
