"""Post-generation sm21 checks with unchanged references and multi-turn receipts."""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.bim_height_coverage import height_coverage
from src.agent.roles import room_use_review

HERE = Path(__file__).resolve().parent
load = lambda path: json.loads(path.read_text())


def audit(run):
    assert (run / 'summary.json').is_file(), 'Generation must have finished'
    frozen = load(HERE / f'{run.name}_frozen.json')
    manifest, summary, delivery = [load(run / name) for name in
                                  ('inputs.json', 'summary.json', 'delivery.json')]
    shared = importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run')
    recovery = 'seed_proposal_sha256' in frozen
    producer_root = run / 'runtime_snapshot' if (run / 'runtime_snapshot').is_dir() else shared.ROOT
    assert manifest['scope'] == frozen['scope']
    assert manifest['provider'] == frozen['provider'] == 'claude'
    assert not manifest['input_contents']['ground_truth_or_evaluation']['included']
    assert not manifest['input_contents']['building_declaration']['included']
    assert 'plan_recovery' not in manifest and not (run / 'resume_plan.json').exists()
    assert {k:v['sha256'] for k,v in manifest['images'].items()} == frozen['image_sha256']
    for name, sha in frozen['image_sha256'].items():
        assert digest(run / 'images' / name) == sha
    for name, sha in manifest['implementation_sha256'].items():
        assert digest(producer_root / name) == sha, name
    assert manifest['input_contents']['saved_generated_proposal']['included'] == recovery
    assert (run / 'seed').exists() == recovery
    if recovery:
        assert manifest['seed']['proposal_sha256'] == frozen['seed_proposal_sha256']
        assert digest(run / 'seed/proposal.json') == frozen['seed_proposal_sha256']
        assert manifest['max_candidates'] == frozen['max_candidates']
    else:
        assert 'seed' not in manifest
    if 'max_candidates' in frozen:
        assert manifest['max_candidates'] == frozen['max_candidates']
    assert manifest['continuation_rounds'] == frozen['continuation_rounds']
    receipts = [load(path) for path in sorted(run.glob('*_receipt.json'))]
    assert len(receipts) == summary['subscription_invocations']
    assert all(r['actual_model'].startswith('claude-sonnet-') and r['provider'] == 'claude'
               and r.get('returncode') == 0 and not r.get('timed_out')
               and not r.get('routing_error') and not r['result'].get('is_error') for r in receipts)
    candidate = delivery['candidate']
    source, _, _ = shared.replay_final(run, candidate)
    assemblies = shared.replay_assemblies(run, manifest)
    toolkit = Toolkit(run)
    assert source['source_model_sha256'] == delivery['source_model_sha256']
    assert height_coverage(toolkit.claims(), candidate) == delivery['height_coverage']
    assert toolkit.input_view_status() == delivery['input_view_status']
    assert room_use_review(source) == delivery['room_use_review']
    actions = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
    assert not any(row['action'] == 'review_detail' for row in actions)

    from scripts.tool_scripts.evaluate_bim_agent import evaluate
    from src.agent.judge.gt import load_gt_document
    evaluation = run / 'evaluation/gt'
    if not (evaluation / 'summary.json').exists():
        evaluate(run, 'sm21_anchor', modelling_task='reconstruction',
                 reference_scope=('Six original images and unverified saved proposal; no prior claims, evaluations or local answers.' if recovery else
                                  'Six original images only, no saved model/calibration/claims or local answers.') + ' GT loaded only after generation.', out=evaluation)
    partition = load(evaluation / f'{candidate}_partition.json')
    legacy = importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings')
    openings = legacy.diagnostic(source, load_gt_document('sm21_anchor'), partition)
    dump(evaluation / 'final_opening_diagnostic.json', openings)
    original = importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_original')
    if len(source['floors']) == 2:
        original.audit(run)
        original_report = load(run / 'evaluation/original_openings.json')
    else:
        original_report = dict(status='not_run', reason='Existing correspondence checker requires two floors; incomplete floor count remains a generation finding.')
    archive = importlib.import_module('AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run')
    transports = archive.archive_streams(run)
    identity_codes = {'source_space_split', 'source_spaces_merged', 'missing_source_space',
                      'extra_source_space', 'floor_assignment_changed', 'candidate_spaces_overlap'}
    strict = partition['comparison']
    report = dict(candidate=candidate, source_model_sha256=source['source_model_sha256'],
        input_mode=frozen['mode'], input_and_producer_hashes_verified=True,
        source_display_replay_exact=True, assemblies_replayed=assemblies,
        original_reference_sha256=digest(original.HERE / 'original_reference.json'),
        invocations=len(receipts), actual_models=[r['actual_model'] for r in receipts],
        elapsed_seconds=summary['elapsed_seconds'], estimated_usd_not_bill=summary['estimated_cost_usd'],
        counts={key:len(source[key]) for key in ('floors','spaces','boundaries','openings','connections')},
        kinds=dict(Counter(row['kind'] for row in source['openings'])),
        floor_levels=source['floors'], room_use=delivery['room_use_review'],
        height_coverage=delivery['height_coverage']['summary'], current_claim_state=delivery['current_claim_state'],
        strict_partition_status=strict['status'], matched_spaces=strict['matched_count'],
        space_identity_findings=[r for r in strict['findings'] if r['code'] in identity_codes],
        topology_findings=partition['topology_findings'], original_openings=original_report,
        matched_exterior=len(openings['matched']),
        exterior_parameters_match=sum(all(r.get(k) is True for k in
            ('along_within_judge_tolerance','width_within_judge_tolerance','z_within_judge_tolerance')) for r in openings['matched']),
        height_mismatches=[r for r in openings['matched'] if r['z_within_judge_tolerance'] is False],
        unmatched_reference=openings['unmatched_reference'], unmatched_built_exterior=openings['unmatched_built_exterior'],
        source_assumptions=source['assumptions'], unresolved=source['generation']['unresolved'],
        tools=dict(Counter(row['action'] for row in actions)), transported_images=sum(t['image_count'] for t in transports),
        continuation=summary['continuation'],
        candidate_budget=toolkit.candidate_budget(),
        limits=['Saved-proposal recovery, not a cold start or causal ablation.' if recovery else
                'One current-runtime original-only run, not a frozen repeat or causal ablation.',
                'Image access, view binding and model stop do not certify image understanding.',
                'Existing original/GT references remain unchanged and post-generation only.',
                'No EnergyPlus or user acceptance; internal door heights may remain assumed.'])
    dump(run / 'postrun_audit.json', report)
    baseline = HERE.parent / '2026-09-27_sm21_whole_building_repeat_claude_run58'
    old_inputs, old_delivery = [load(baseline / name) for name in ('inputs.json','delivery.json')]
    old_report = load(baseline / 'postrun_audit.json')
    old_source = load(baseline / old_delivery['candidate'] / 'source_model.json')
    assert old_inputs['scope'] == manifest['scope']
    assert {k:v['sha256'] for k,v in old_inputs['images'].items()} == frozen['image_sha256']
    dump(HERE / f'{run.name}_comparison.json', dict(
        baseline_run=baseline.name, current_run=run.name,
        same_original_images_and_task=True, same_runtime=False, saved_proposal_recovery=recovery,
        baseline=dict(candidate=old_delivery['candidate'], counts=old_report['counts'],
            strict_partition=old_report['strict_partition_status'],
            exterior_parameters_match=old_report['all_parameters_match'],
            original_openings=load(baseline / 'evaluation/original_openings.json'),
            room_use=room_use_review(old_source), height_coverage=old_delivery['height_coverage']['summary']),
        current=report,
        limit='Independent outcome comparison only; runtime, room guidance and continuation policy changed. No causal claim.'))
    print(json.dumps({k:report[k] for k in ('candidate','counts','kinds','invocations','elapsed_seconds',
        'strict_partition_status','space_identity_findings','matched_exterior','exterior_parameters_match',
        'height_coverage')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    audit(parser.parse_args().run.resolve())
