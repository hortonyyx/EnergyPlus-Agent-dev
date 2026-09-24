"""Developer-only controlled replay, never an autonomous output or model input."""
import copy
import json
from pathlib import Path
import importlib
from PIL import Image

from scripts.tool_scripts.run_bim_agent import dump
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.source_image_overlay import render_source_overlay

HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'2026-09-24_sm25_cold_support_glm_run42'
load=lambda p:json.loads(p.read_text())


def main():
    assert (RUN/'summary.json').exists()
    out=HERE/'developer_repair_diagnostic';out.mkdir(exist_ok=False)
    baseline=load(RUN/'plan_drafts/draft_004/plan.json')
    observation=load(HERE/'original_observations.json')
    audit=importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_cold_support_setup.audit_run')
    plan=copy.deepcopy(baseline)
    index=next(i for i,p in enumerate(plan['partitions']) if p['id']=='P_corr_north_w')
    old=plan['partitions'][index]
    # Controlled intervention from original image: the corridor gap is empty.
    # Keep the actual walls below the office blocks and ALL meeting-room walls.
    plan['partitions'][index:index+1]=[
        dict(old,id='P_corr_north_w_left',points=[[513,957],[695,957]],
             source_refs=old['source_refs']+['developer original-image diagnosis: left office bottom wall']),
        dict(old,id='P_corr_north_w_right',points=[[792,957],[975,957]],
             source_refs=old['source_refs']+['developer original-image diagnosis: right office bottom wall'])]
    old_other=[p for p in baseline['partitions'] if p['id']!=old['id']]
    assert [p for p in plan['partitions'] if p['id'] not in {'P_corr_north_w_left','P_corr_north_w_right'}]==old_other
    plan['unresolved'].append('Developer-assisted diagnostic only; not selected or returned to the working model.')
    steps=[]
    for name in ['split_false_wall_only','restore_missing_exterior_door']:
        if name=='restore_missing_exterior_door':
            plan['openings'].append(dict(id='D_west_south_diagnostic',kind='door',
                p1=[513,1000],p2=[513,1035],z=[0,2.1],state='unknown',
                source_refs=['developer evaluation-only original cyan leaf/arc x518-555 y999-1036'],
                assumptions=['Unobserved height assumed 2.1m; operating state unknown.']))
        assert plan['openings'][:len(baseline['openings'])]==baseline['openings']
        proposal,metadata=compile_plan_partition(plan,image_size=(1758,1496),image_name='1f_view.png')
        target=out/name
        report=export_source_proposal(proposal,target,provenance=dict(
            mode='developer_assisted_diagnostic_not_adopted',original_run=str(RUN.relative_to(HERE.parents[3])),
            intervention=name,model_calls=0))
        assert report['source_geometry_ready'],report
        source=load(target/'source_model.json')
        result=audit.compare_original(source,observation,lambda p:p)
        dump(target/'plan.json',plan);dump(target/'comparison.json',result)
        dump(target/'compilation.json',metadata)
        pic,_=render_source_overlay(source,Image.open(HERE/'inputs/1f_view.png').convert('RGB'),
            floor_id='F1',image_name='1f_view.png',**observation['calibration'])
        pic.save(target/'independent_overlay.png')
        old_source=load(RUN/'candidate_01/source_model.json')
        old_open={o['id']:o for o in old_source['openings']}
        new_open={o['id']:o for o in source['openings']}
        assert all(new_open[k]['vertices']==v['vertices'] and new_open[k]['kind']==v['kind']
                   for k,v in old_open.items())
        old_rooms={s['id']:s['polygon'] for s in old_source['spaces'] if s['id'] not in {'corridor_open','F1_S13'}}
        new_rooms={s['id']:s['polygon'] for s in source['spaces']}
        assert all(new_rooms[k]==v for k,v in old_rooms.items())
        steps.append(dict(intervention=name,counts=report['counts'],
            unchanged_other_partition_count=len(old_other),unchanged_original_opening_geometry=len(old_open),
            unchanged_non_corridor_room_polygons=len(old_rooms),partition_status=result['comparison']['status'],
            qualitative_topology_findings=[f for f in result['comparison']['findings'] if f['code'] in
                {'source_space_split','source_spaces_merged','extra_source_space','missing_source_space'}],
            positions_matched=result['positions_matched'],hosts_matched=result['hosts_matched'],
            door_connections_matched=result['door_connections_matched'],
            unmatched_reference=result['unmatched_reference'],unmatched_actual=result['unmatched_actual']))
    dump(out/'summary.json',dict(mode='controlled_developer_intervention_not_autonomous_or_adopted',
        model_calls=0,steps=steps,conclusion='Existing compiler can preserve the gap and all unrelated walls. Failed model retries removed meeting-room declarations; the failure does not prove this geometry is unrepresentable.',
        limitations=['Original midline/exterior-face residuals and west office wall-band sliver retained.',
                     'Developer chose the changed wall and missing door using original evidence. This is not a repaired working-model score.']))
    print(json.dumps(steps,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
