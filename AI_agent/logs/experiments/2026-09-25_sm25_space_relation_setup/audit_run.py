"""After-generation source, transport and independent-reference checks."""
from collections import Counter
import importlib
import json
from pathlib import Path
import tempfile

from PIL import Image

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.plan_revision import apply_plan_revision
from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.geometry.source_space_relations import review_space_relations
from src.agent.judge.gt import load_gt_document, gt_path
from src.agent.judge.source_partition import compare_partitions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / '2026-09-25_sm25_space_relation_glm_run46'
load = lambda path: json.loads(path.read_text())


def main():
    assert (RUN/'summary.json').exists(), 'Evaluation follows completed generation'
    frozen, manifest = load(HERE/'frozen_method.json'), load(RUN/'inputs.json')
    receipt, summary, delivery = [load(RUN/name) for name in
                                 ['agent_receipt.json','summary.json','delivery.json']]
    assert receipt['provider'] == manifest['provider']
    if manifest['provider'] == 'glm':
        assert receipt['actual_model'] == 'glm-5.3-flash'
    else:
        assert manifest['provider'] == 'claude' and receipt['actual_model'].startswith('claude-sonnet-')
    assert manifest['scope'] == frozen['scope']
    assert not manifest['input_contents']['ground_truth_or_evaluation']['included']
    assert not manifest['input_contents']['saved_generated_proposal']['included']
    assert digest(RUN/'images/1f_view.png') == frozen['image_sha256']
    cold = frozen.get('mode') == 'original_image_only_cold_start'
    if cold:
        assert manifest['input_mode'] == 'original_images_agent_experiment'
        assert manifest['source_input_mode'] == 'original_images_only'
        assert not manifest['input_contents']['building_declaration']['included']
        assert not manifest['input_contents'].get('saved_pixel_plan',{}).get('included',False)
        assert not (RUN/'resume_plan.json').exists()
    else:
        assert digest(RUN/manifest['plan_recovery']['frozen_path']) == frozen['parent_plan_sha256']
    for path, sha in manifest['implementation_sha256'].items():
        assert digest(ROOT/path) == sha, path
    setup_only = []
    for path, sha in frozen['implementation_sha256'].items():
        assert digest(ROOT/path) == sha, path
        if path in manifest['implementation_sha256']:
            assert manifest['implementation_sha256'][path] == sha
        else:
            setup_only.append(path)
    candidate = delivery['candidate']
    source, proposal = [load(RUN/candidate/name) for name in ['source_model.json','proposal.json']]
    with tempfile.TemporaryDirectory(prefix='space-relation-source-replay-') as tmp:
        out = Path(tmp)/'candidate'
        export_source_proposal(proposal, out, provenance=source['generation']['provenance'])
        assert load(out/'source_model.json') == source
        assert load(out/'display_geometry.json') == load(RUN/candidate/'display_geometry.json')
    revisions = []
    for path in sorted((RUN/'plan_drafts').glob('*/input.json')):
        record = load(path)
        if 'revision' not in record:
            continue
        binding = record['revision']
        assert digest(RUN/binding['file']) == binding['sha256']
        revision = load(RUN/binding['file'])
        parent = RUN/('resume_plan.json' if revision['parent_draft_id'] == 'resume' else
                     f"plan_drafts/{revision['parent_draft_id']}/plan.json")
        assert digest(parent) == revision['parent_plan_sha256'] == binding['parent_plan_sha256']
        updated, report = apply_plan_revision(load(parent), json.loads(revision['operations_json']))
        assert updated == load(path.parent/'plan.json')
        assert all(report[key] == revision[key] for key in report)
        revisions.append({'draft':path.parent.name,'changes':report['changes']})
    checked_reviews = []
    for path in sorted((RUN/'space_relation_reviews').glob('*.json')):
        report = load(path)
        cal = load(RUN/report['calibration_file'])
        assert digest(RUN/report['calibration_file']) == report['calibration_sha256']
        assert digest(RUN/'images'/report['image']) == report['image_sha256']
        old_source = load(RUN/report['candidate']/'source_model.json')
        observations = [{'id':row['id'],'points':[p['pixel'] for p in row['points']],
                         'expected':row['expected'],'evidence':row['evidence']}
                        for row in report['observations']]
        replay = review_space_relations(old_source,floor_id=report['floor_id'],
            image_size=manifest['images'][report['image']]['size'],
            x_anchors=cal['x_anchors'],y_anchors=cal['y_anchors'],observations=observations)
        assert all(report[key] == value for key,value in replay.items())
        checked_reviews.append({'file':str(path.relative_to(RUN)),
            'candidate':report['candidate'],'conflict_count':report['conflict_count'],
            'unassessed_count':report['unassessed_count'],'sample_count':len(observations)})
    out = RUN/'evaluation'
    out.mkdir(exist_ok=True)
    previous = importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_cold_support_setup.audit_run')
    observations = load(HERE.parent/'2026-09-24_sm25_cold_support_setup/original_observations.json')
    assert observations['source_sha256'] == frozen['image_sha256']
    original = previous.compare_original(source,observations,lambda point:point)
    dump(out/'original_comparison.json',original)
    (out/'original_partition.html').write_text('<!doctype html><meta charset="utf-8">'+
        previous.overlay(original['reference_spaces'],original['candidate_spaces'],'F1'))
    picture, metadata = render_source_overlay(source,Image.open(RUN/'images/1f_view.png').convert('RGB'),
        floor_id='F1',image_name='1f_view.png',**observations['calibration'])
    picture.save(out/'independent_original_overlay.png')
    dump(out/'independent_original_overlay.json',metadata)
    reframed = None
    if cold:
        # Invert the actual selected plan's anchors; no fitting to the reference.
        plan_binding = source['generation']['provenance']['plan_input']
        plan_path = RUN/plan_binding['plan_file']
        assert digest(plan_path) == plan_binding['plan_sha256']
        plan = load(plan_path)
        def declared_to_original(point):
            return [previous.interpolate(previous.interpolate(v,[(b,a) for a,b in plan[axis+'_anchors']]),
                observations['calibration'][axis+'_anchors']) for axis,v in zip('xy',point)]
        reframed = previous.compare_original(source,observations,declared_to_original)
        dump(out/'declared_frame_comparison.json',reframed)
        (out/'declared_frame_partition.html').write_text('<!doctype html><meta charset="utf-8">'+
            previous.overlay(reframed['reference_spaces'],reframed['candidate_spaces'],'F1'))
    gt = load_gt_document('sm25-L_anchor')
    floor = next(row for row in gt.floors if row.id == 'F1')
    refs = [dict(id=z.id,floor_id='F1',z_floor=floor.z_floor_m,height=floor.ceiling_height_m,
                 polygon=z.polygon.exterior.vertices) for z in floor.zones]
    actual = [dict(row,floor_id='F1') for row in source['spaces']]
    gt_checks = {'raw_3d':compare_partitions(refs,actual,tolerance_m=.02),
        'plan_only_8cm':compare_partitions([dict(r,z_floor=0,height=1) for r in refs],
                                         [dict(r,z_floor=0,height=1) for r in actual],tolerance_m=.08)}
    dump(out/'gt_partition.json',{'reference_sha256':digest(gt_path('sm25-L_anchor')),
        'scope':'F1 only; GT unchanged and excluded from generation.', 'comparisons':gt_checks})
    finalizer = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run')
    finalizer.finalize(RUN)
    if not cold:
        compare = importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_continuous_space_setup.audit_run')
        compare.compare_recovery(RUN,HERE.parent/'2026-09-24_sm25_continuous_space_glm_run44/candidate_03')
    actions = [json.loads(line) for line in (RUN/'tools.jsonl').read_text().splitlines()]
    result = {'mode':'original_image_only_cold_start' if cold else 'saved_draft_recovery_without_developer_error_location_not_cold_start',
        'candidate':candidate,'actual_model':receipt['actual_model'],
        'elapsed_seconds':receipt['elapsed_seconds'],'subscription_invocations':summary['subscription_invocations'],
        'cost_receipts_complete':summary['cost_receipts_complete'],
        'estimated_main_cost_usd_not_bill':receipt.get('result',{}).get('total_cost_usd'),
        'frozen_inputs_verified':True,'implementation_hashes_verified':True,
        'modules_frozen_by_setup_manifest_only':setup_only,'source_display_replay_exact':True,
        'local_revisions_replayed':revisions,'space_relation_reviews_replayed':checked_reviews,
        'final_space_relation_status':delivery['space_relation_review'],
        'counts':{key:len(source[key]) for key in ['spaces','openings','connections','unsupported','unbuilt_openings']},
        'opening_kinds':dict(Counter(row['kind'] for row in source['openings'])),
        'tools':dict(Counter(row['action'] for row in actions)),
        'transported_image_count':load(RUN/'transport_audit.json')['image_count'],
        'original_comparison':{'partition_status':original['comparison']['status'],
            'matched_spaces':original['comparison']['matched_count'],
            **{key:original[key] for key in ['positions_matched','hosts_matched','door_connections_matched',
                                           'unmatched_reference','unmatched_actual']}},
        'gt_status':{name:row['status'] for name,row in gt_checks.items()},
        'limitations':[('Single-floor cold start; multi-floor autonomy and repeatability not established.' if cold else
                        'Saved failed draft supplied; not independent cold-start or multi-floor verification.'),
                       'Sampled caller observations do not establish entire-plan fidelity.',
                       'Height assumptions and dimensional residuals remain separately reportable.']}
    if reframed is not None:
        result['declared_frame_comparison'] = {'partition_status':reframed['comparison']['status'],
            'matched_spaces':reframed['comparison']['matched_count'],
            **{k:reframed[k] for k in ['positions_matched','hosts_matched','door_connections_matched',
                                      'unmatched_reference','unmatched_actual']}}
    dump(RUN/'postrun_audit.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
