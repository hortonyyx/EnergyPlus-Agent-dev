"""Post-generation recovery audit; reuse frozen references, never feed them back."""
from collections import Counter
import base64
import hashlib
import gzip
import io
import importlib
import json
from pathlib import Path
import tempfile

from PIL import Image

from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.plan_revision import apply_plan_revision
from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.judge.gt import load_gt_document, gt_path
from src.agent.judge.source_partition import compare_partitions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / '2026-09-24_sm25_local_plan_glm_run43'
OLD = HERE.parent / '2026-09-24_sm25_cold_support_setup'
load = lambda p: json.loads(p.read_text())


def main():
    assert (RUN / 'summary.json').exists(), 'Evaluation follows generation'
    frozen, manifest = load(HERE / 'frozen_method.json'), load(RUN / 'inputs.json')
    receipt = load(RUN / 'agent_receipt.json')
    assert receipt['actual_model'] == 'glm-5.3-flash'
    assert all(digest(ROOT / p) == h for p,h in manifest['implementation_sha256'].items())
    for p, h in frozen['implementation_sha256'].items():
        assert digest(ROOT / p) == manifest['implementation_sha256'][p] == h
    assert manifest['scope'] == frozen['scope']
    assert digest(RUN / 'images/1f_view.png') == frozen['image_sha256']
    assert digest(RUN / manifest['plan_recovery']['frozen_path']) == frozen['parent_plan_sha256']
    assert not manifest['input_contents']['ground_truth_or_evaluation']['included']
    assert not manifest['input_contents']['saved_generated_proposal']['included']
    candidate = load(RUN / 'delivery.json')['candidate']
    source = load(RUN / candidate / 'source_model.json')
    proposal = load(RUN / candidate / 'proposal.json')
    origin = source
    ancestry = []
    while 'plan_input' not in origin['generation']['provenance']:
        provenance = origin['generation']['provenance']
        parent = provenance['parent_candidate']
        assert Path(parent).name == parent and parent not in ancestry
        assert digest(RUN / parent / 'proposal.json') == provenance['parent_proposal_sha256']
        ancestry.append(parent)
        origin = load(RUN / parent / 'source_model.json')
    same_geometry = all(source[k] == origin[k] for k in ('floors','spaces','boundaries','openings','connections'))
    plan_input = origin['generation']['provenance']['plan_input']
    assert digest(RUN / plan_input['plan_file']) == plan_input['plan_sha256']
    plan = load(RUN / plan_input['plan_file'])
    baseline = load(RUN / 'resume_plan.json')
    declaration_delta = {}
    for field in ('partitions','openings','space_seeds'):
        old_rows = {r['id']:r for r in baseline.get(field,[])}
        new_rows = {r['id']:r for r in plan.get(field,[])}
        declaration_delta[field] = dict(added=sorted(new_rows.keys()-old_rows.keys()),
            removed=sorted(old_rows.keys()-new_rows.keys()),
            changed=sorted(k for k in old_rows.keys() & new_rows.keys() if old_rows[k] != new_rows[k]),
            unchanged=sorted(k for k in old_rows.keys() & new_rows.keys() if old_rows[k] == new_rows[k]))
    revisions = []
    for record_path in sorted((RUN / 'plan_drafts').glob('*/input.json')):
        record = load(record_path)
        if 'revision' not in record:
            continue
        binding = record['revision']
        assert digest(RUN / binding['file']) == binding['sha256']
        rev = load(RUN / binding['file'])
        parent_path = RUN / ('resume_plan.json' if rev['parent_draft_id'] == 'resume'
                            else 'plan_drafts/' + rev['parent_draft_id'] + '/plan.json')
        assert digest(parent_path) == rev['parent_plan_sha256'] == binding['parent_plan_sha256']
        updated, report = apply_plan_revision(load(parent_path), json.loads(rev['operations_json']))
        assert updated == load(record_path.parent / 'plan.json')
        assert all(report[k] == rev[k] for k in report)
        revisions.append(dict(draft=record_path.parent.name, revision=binding,
            unchanged_counts={k:len(v) for k,v in report['unchanged_ids'].items()},
            targets=[dict(field=r['field'], id=r['id']) for r in report['changes']]))
    with tempfile.TemporaryDirectory(prefix='sm25-local-replay-') as tmp:
        target = Path(tmp) / 'candidate'
        export_source_proposal(proposal, target, provenance=source['generation']['provenance'])
        assert load(target / 'source_model.json') == source
        assert load(target / 'display_geometry.json') == load(RUN / candidate / 'display_geometry.json')
    out = RUN / 'evaluation'; out.mkdir(exist_ok=True)
    previous = importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_cold_support_setup.audit_run')
    obs = load(OLD / 'original_observations.json')
    assert obs['source_sha256'] == frozen['image_sha256']
    def reframe(point):
        return [previous.interpolate(previous.interpolate(v, [(b,a) for a,b in plan[axis+'_anchors']]),
                obs['calibration'][axis+'_anchors']) for axis,v in zip('xy',point)]
    comparisons = {'original': previous.compare_original(source, obs, lambda p:p)}
    if same_geometry:
        comparisons['declared_frame'] = previous.compare_original(source, obs, reframe)
    for name, data in comparisons.items():
        dump(out / f'{name}_comparison.json', data)
        (out / f'{name}_partition.html').write_text('<!doctype html><meta charset="utf-8">'+
            previous.overlay(data['reference_spaces'],data['candidate_spaces'],'F1'))
    picture, meta = render_source_overlay(source, Image.open(RUN / 'images/1f_view.png').convert('RGB'),
        floor_id=source['floors'][0]['id'], image_name='1f_view.png', **obs['calibration'])
    picture.save(out / 'independent_original_overlay.png')
    dump(out / 'independent_original_overlay.json', meta)
    gt = load_gt_document('sm25-L_anchor')
    floor = next(f for f in gt.floors if f.id == 'F1')
    refs = [dict(id=z.id, floor_id='F1', z_floor=floor.z_floor_m, height=floor.ceiling_height_m,
        polygon=z.polygon.exterior.vertices) for z in floor.zones]
    actual = [dict(s, floor_id='F1') for s in source['spaces']]
    gt_checks = { 'raw_3d': compare_partitions(refs, actual, tolerance_m=.02),
        'plan_only_8cm': compare_partitions([dict(r,z_floor=0,height=1) for r in refs],
            [dict(r,z_floor=0,height=1) for r in actual],tolerance_m=.08)}
    dump(out / 'gt_partition.json', dict(reference_sha256=digest(gt_path('sm25-L_anchor')),
        scope='F1 only. Raw 3D and separately labelled plan-only tolerance; GT unmodified.', comparisons=gt_checks))
    finalizer = importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run')
    finalizer.finalize(RUN)
    transport = load(RUN / 'transport_audit.json')
    narrative, calls = [], []
    for line in gzip.decompress((RUN / 'agent_stream.jsonl.gz').read_bytes()).splitlines():
        event = json.loads(line)
        if event.get('type') != 'assistant':
            continue
        for block in event.get('message',{}).get('content',[]):
            if block.get('type') == 'text':
                narrative.append(block['text'])
            elif block.get('type') == 'tool_use':
                calls.append(dict(name=block['name'], input=block['input']))
    dump(out / 'model_actions.json', dict(assistant_text=narrative, tool_calls=calls,
        note='Extracted public assistant messages and tool inputs; actual images audited separately.'))
    native = {}
    for p in RUN.rglob('*.png'):
        if 'evaluation' in p.parts:
            continue
        with Image.open(p) as im:
            key = hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
        native.setdefault(key, []).append(str(p.relative_to(RUN)))
    feedback = [dict(r, matching_native_files=native.get(r['pixels_sha256'], []))
        for r in transport['images'] if any(r['tool'].endswith('__'+name)
        for name in ('build_plan_bim','revise_plan_bim','view_plan_wall_support','view_pixel_profile'))]
    assert all(r['matching_saved_files'] or r['matching_native_files'] for r in feedback)
    dump(out / 'actual_feedback_images.json', dict(images=feedback))
    detail_runs = []
    for path in sorted(RUN.glob('detail_*_receipt.json')):
        rec = load(path)
        assert rec['actual_model'] == 'glm-5.3-flash' and rec['provider'] == 'glm'
        detail_id = path.name.removesuffix('_receipt.json')
        detail_manifest = load(RUN / detail_id / 'inputs.json')
        assert detail_manifest['images']['1f_view.png']['sha256'] == frozen['image_sha256']
        stream = RUN / (detail_id + '_stream.jsonl')
        archive = stream.with_suffix('.jsonl.gz')
        raw = stream.read_bytes() if stream.exists() else gzip.decompress(archive.read_bytes())
        detail_images = 0
        for line in raw.splitlines():
            event = json.loads(line)
            for block in event.get('message',{}).get('content',[]):
                if isinstance(block, dict) and block.get('type') == 'tool_result' and isinstance(block.get('content'),list):
                    for item in block['content']:
                        if item.get('type') == 'image':
                            with Image.open(io.BytesIO(base64.b64decode(item['source']['data']))) as im:
                                im.load(); detail_images += 1
        zipped = gzip.compress(raw, mtime=0)
        assert gzip.decompress(zipped) == raw
        archive.write_bytes(zipped)
        if stream.exists():
            stream.unlink()
        detail_runs.append(dict(id=detail_id, actual_model=rec['actual_model'],
            timed_out=rec.get('timed_out',False), elapsed_seconds=rec['elapsed_seconds'],
            result_available=rec.get('result') is not None, transported_image_count=detail_images,
            stream_sha256=hashlib.sha256(raw).hexdigest(), archive_sha256=digest(archive),
            lossless_archive=True))
    summary = load(RUN / 'summary.json')
    rows = [json.loads(s) for s in (RUN / 'tools.jsonl').read_text().splitlines()]
    result = dict(mode='saved_draft_recovery_not_cold_start', candidate=candidate,
        actual_model=receipt['actual_model'], elapsed_seconds=receipt['elapsed_seconds'],
        estimated_main_cost_usd_not_bill=receipt.get('result',{}).get('total_cost_usd'),
        subscription_invocations=summary['subscription_invocations'],
        cost_receipts_complete=summary['cost_receipts_complete'], detail_runs=detail_runs,
        frozen_input_runtime_verified=True, source_display_replay_exact=True,
        selected_geometry_unchanged_from_plan_origin=same_geometry, revisions=revisions,
        declaration_delta_from_resume=declaration_delta,
        counts={k:len(source[k]) for k in ('spaces','openings','connections','unsupported','unbuilt_openings')},
        opening_kinds=dict(Counter(o['kind'] for o in source['openings'])),
        tools=dict(Counter(r['action'] for r in rows)), transported_image_count=transport['image_count'],
        model_tool_calls=dict(Counter(r['name'] for r in calls)),
        exact_saved_feedback_images=len(feedback),
        comparisons={name:dict(partition_status=d['comparison']['status'],
            matched_spaces=d['comparison']['matched_count'], positions_matched=d['positions_matched'],
            hosts_matched=d['hosts_matched'], door_connections_matched=d['door_connections_matched'],
            unmatched_reference=d['unmatched_reference'],unmatched_actual=d['unmatched_actual']) for name,d in comparisons.items()},
        gt_status={name:d['status'] for name,d in gt_checks.items()},
        limitations=['Explicit old-draft recovery, not autonomous cold start or multi-floor validation.',
            'Existing developer original reference reused only after generation. GT F1 evaluation only.',
            'No browser WebGL interaction test; height assumptions and reference-plane residuals remain separately reportable.'])
    dump(RUN / 'postrun_audit.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
