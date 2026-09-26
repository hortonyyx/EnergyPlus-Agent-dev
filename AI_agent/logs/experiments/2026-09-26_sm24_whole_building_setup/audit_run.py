"""Post-generation sm24 plan and exterior-height checks, with references isolated."""
from collections import Counter
import gzip
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, dump
from src.agent.execution.bim_height_coverage import height_coverage

HERE = Path(__file__).resolve().parent
RUN = HERE.parent/'2026-09-26_sm24_whole_building_claude_run55'
load = lambda p: json.loads(p.read_text())


def audit(run=RUN, frozen_method=HERE/'frozen_method.json'):
    assert (run/'summary.json').is_file(), 'Wait for generation completion'
    manifest=load(run/'inputs.json');receipt=load(run/'agent_receipt.json')
    delivery=load(run/'delivery.json');chosen=delivery['candidate']
    shared=importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run')
    shared.verify_inputs(run,load(frozen_method),manifest,cold=True)
    assert len(manifest['images'])==5
    assert receipt['actual_model'].startswith('claude-sonnet-')
    assert len(list(run.glob('*_receipt.json')))==1
    source,_,_=shared.replay_final(run,chosen)
    assert source['source_model_sha256']==delivery['source_model_sha256']
    toolkit=Toolkit(run)
    assert toolkit.input_view_status()==delivery['input_view_status']
    assert height_coverage(toolkit.claims(),chosen)==delivery['height_coverage']
    actions=[json.loads(line) for line in (run/'tools.jsonl').read_text().splitlines()]
    assert not any(row['action']=='review_detail' for row in actions)
    # The existing independent original-image reference covers all plan apertures.
    # It also performs exact source/display replay and unmodified GT comparison.
    original=importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run')
    original.audit(run)
    plan_report=load(run/'postrun_audit.json')
    dump(run/'evaluation/original_plan_audit.json',plan_report)
    from src.agent.judge.gt import load_gt_document
    partition=load(run/'evaluation/partition.json')
    opening=shared._opening_diagnostic(source,load_gt_document('sm24_anchor'),partition)
    dump(run/'evaluation/exterior_opening_diagnostic.json',opening)
    scope=load(run/'evaluation/reference_scope.json')
    scope.update(heights_acceptance='See exterior_opening_diagnostic.json for separate typed-GT z comparison; original-image partition diagnostic excludes heights.',
        generation_input_note='Five original PNGs, including four elevations; the reused audit historically had plan-only inputs.')
    dump(run/'evaluation/reference_scope.json',scope)
    finalizer=importlib.import_module('AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.finalize_run')
    finalizer.finalize(run)
    ids={};errors=[];finish=[]
    with gzip.open(run/'agent_stream.jsonl.gz','rt') as stream:
        for line in stream:
            content=json.loads(line).get('message',{}).get('content',[])
            for block in content if isinstance(content,list) else []:
                if block.get('type')=='tool_use':ids[block['id']]=block['name']
                if block.get('type')!='tool_result':continue
                tool=ids.get(block['tool_use_id'],'unknown');result=block.get('content',[])
                texts=[result] if isinstance(result,str) else [r['text'] for r in result if r.get('type')=='text']
                if block.get('is_error'):errors.append(dict(tool=tool,text=texts))
                if tool.endswith('finish_bim'):
                    for text in texts:
                        try:payload=json.loads(text)
                        except ValueError:payload={}
                        finish.append(dict(characters=len(text),parseable_summary=bool(payload.get('candidate')),
                            detached_output_notice='persisted-output' in text or 'Full output saved to' in text))
    dump(run/'evaluation/tool_transport.json',dict(actual_tool_call_counts=dict(Counter(ids.values())),
        tool_errors=errors,finish_results=finish,note='Actual CLI tool results; transport is not semantic acceptance.'))
    identity_codes={'source_space_split','source_spaces_merged','missing_source_space','extra_source_space',
                    'floor_assignment_changed','candidate_spaces_overlap'}
    report=dict(candidate=chosen,actual_model=receipt['actual_model'],elapsed_seconds=receipt['elapsed_seconds'],
        cli_estimated_usd_not_bill=receipt['result'].get('total_cost_usd'),
        source_display_replay_exact=True,implementation_and_inputs_verified=True,
        counts={k:len(source[k]) for k in ('floors','spaces','boundaries','openings','connections')},
        kinds=dict(Counter(o['kind'] for o in source['openings'])),
        original_plan=plan_report,
        strict_gt_partition_status=partition['comparison']['status'],
        strict_gt_matched_spaces=partition['comparison']['matched_count'],
        space_identity_findings=[r for r in partition['comparison']['findings'] if r['code'] in identity_codes],
        matched_exterior=len(opening['matched']),all_parameters_and_host_match=sum(all(r.get(k) is True for k in
            ('along_within_judge_tolerance','width_within_judge_tolerance','z_within_judge_tolerance','host_zone_match')) for r in opening['matched']),
        height_mismatches=[r for r in opening['matched'] if r['z_within_judge_tolerance'] is False],
        unmatched_reference=opening['unmatched_reference'],unmatched_built_exterior=opening['unmatched_built_exterior'],
        height_coverage=delivery['height_coverage']['summary'],input_view_status=delivery['input_view_status'],
        assumptions=source['assumptions'],unresolved=source['generation'].get('unresolved',[]),
        transported_images=load(run/'transport_audit.json')['image_count'],finish_results=finish,
        limits=['Single cross-case execution, not repeated success on this whole-building scope.',
                'No internal door height evidence is created by plan matching.',
                'Original-pixel estimates and GT tolerances are independent diagnostics, not surveyed accuracy.',
                'Assumption/evidence consistency requires manual semantic review; no EP or human approval.'])
    dump(run/'whole_building_audit.json',report)
    print(json.dumps({k:report[k] for k in ('candidate','elapsed_seconds','counts','strict_gt_matched_spaces',
        'space_identity_findings','matched_exterior','all_parameters_and_host_match','height_mismatches','height_coverage')},indent=2))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',type=Path,default=RUN)
    parser.add_argument('--frozen',type=Path,default=HERE/'frozen_method.json')
    args=parser.parse_args()
    audit(args.run.resolve(),args.frozen.resolve())
