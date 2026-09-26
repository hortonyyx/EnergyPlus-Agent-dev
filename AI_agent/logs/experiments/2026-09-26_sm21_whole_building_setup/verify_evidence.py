"""Bounded real-artifact checks for height-only edits and the legacy diagnostic."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
from scripts.tool_scripts.run_bim_agent import digest, dump
from src.agent.judge.gt import load_gt_document

HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'2026-09-26_sm21_whole_building_claude_run57'
load=lambda p:json.loads(p.read_text())

def main():
    assert (RUN/'summary.json').is_file()
    delivery=load(RUN/'delivery.json');old=load(RUN/'candidate_03/source_model.json');source=load(RUN/delivery['candidate']/'source_model.json')
    assert old['floors']==source['floors'] and old['spaces']==source['spaces'] and old['boundaries']==source['boundaries'] and old['connections']==source['connections']
    previous={o['id']:o for o in old['openings']}; changes=[]
    for o in source['openings']:
        before=previous[o['id']]
        assert [v[:2] for v in before['vertices']]==[v[:2] for v in o['vertices']]
        for key in ('kind','space_ids','host_boundary_id','exterior'):assert before[key]==o[key]
        if before['vertices']!=o['vertices']:
            changes.append(o['id']);assert o['exterior']
    assert len(changes)==17
    module=importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.audit_legacy_openings')
    gt=load_gt_document('sm21_anchor');partition=load(RUN/'evaluation/gt/candidate_04_partition.json')
    baseline=module.diagnostic(source,gt,partition)
    assert len(baseline['matched'])==17 and not baseline['unmatched_reference'] and not baseline['unmatched_built_exterior']
    assert all(all(r[k] for k in ('along_within_judge_tolerance','width_within_judge_tolerance','z_within_judge_tolerance')) for r in baseline['matched'])
    altered=deepcopy(source);sample=next(o for o in altered['openings'] if o['exterior']);oid=sample['id']
    for v in sample['vertices']:v[2]+=0.5
    shifted=module.diagnostic(altered,gt,partition)
    assert next(r for r in shifted['matched'] if r['opening_id']==oid)['z_within_judge_tolerance'] is False
    omitted=deepcopy(source);omitted['openings']=[o for o in omitted['openings'] if o['id']!=oid]
    missing=module.diagnostic(omitted,gt,partition)
    assert len(missing['matched'])==16 and len(missing['unmatched_reference'])==1
    assert len(baseline['internal_openings_not_in_exterior_GT'])==12
    prior=load(HERE.parent/'2026-09-26_sm24_whole_building_repeat_claude_run56/inputs.json');manifest=load(RUN/'inputs.json')
    assert prior['scope']==manifest['scope']
    report=dict(candidate=delivery['candidate'],source_model_sha256=source['source_model_sha256'],
        all_floor_space_boundary_connection_records_unchanged=True,all_opening_xy_kind_hosts_unchanged=True,
        changed_exterior_z_ids=changes,internal_door_heights_unchanged=True,
        legacy_diagnostic_controls=dict(baseline_parameters_match=17,height_shift_detected=True,omitted_opening_detected=True,controls_in_memory_only=True),
        same_scope_as_run55_56=True,changed_production_paths_since_run56=[p for p,h in manifest['implementation_sha256'].items() if prior['implementation_sha256'].get(p)!=h],
        input_hashes_rechecked={n:digest(RUN/'images'/n)==data['sha256'] for n,data in manifest['images'].items()},
        model_call_count=1,model_calls_for_audits=0)
    dump(HERE/'verification.json',report);print(json.dumps(report,indent=2))

if __name__=='__main__':main()
