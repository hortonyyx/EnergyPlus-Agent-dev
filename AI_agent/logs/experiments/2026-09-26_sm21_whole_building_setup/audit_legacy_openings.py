"""Legacy-GT diagnostic for exterior openings only; no production conversion."""
import importlib
from pathlib import Path
from scipy.optimize import linear_sum_assignment
from scripts.tool_scripts.run_bim_agent import digest
from src.agent.judge.gt_schema import LegacyGroundTruthV2
from src.agent.judge.score_config import load_judge_score_config

ROOT=Path(__file__).resolve().parents[4]

def diagnostic(source,gt,partition):
    assert isinstance(gt,LegacyGroundTruthV2)
    shared=importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run')
    config=load_judge_score_config(ROOT/'src/configs/judge_score.yaml')
    spaces={s['id']:s for s in source['spaces']};built=[];unclassified=[]
    for o in source['openings']:
        if not o['exterior']:continue
        facade,reason=shared._source_exterior_facade(source,o)
        if facade is None:
            unclassified.append(dict(id=o['id'],reason=reason));continue
        axis=0 if facade in {'North','South'} else 1
        built.append(dict(id=o['id'],kind=o['kind'],floor=partition['floor_mapping'][spaces[o['space_ids'][0]]['floor_id']],facade=facade,along=[min(v[axis] for v in o['vertices']),max(v[axis] for v in o['vertices'])],z=[min(v[2] for v in o['vertices']),max(v[2] for v in o['vertices'])]))
    targets=[]
    for i,group in enumerate(gt.windows):
        for j,o in enumerate(group.openings):
            targets.append(dict(id=f'window_group_{i}_item_{j}',kind='window',floor=group.floor,facade=group.facade,along=[o.x_m,o.x_m+o.width_m],z=[o.sill_m,o.head_m]))
    for i,o in enumerate(gt.doors):
        targets.append(dict(id=f'door_{i}',kind='door',floor=o.floor,facade=o.facade,along=[o.x_m,o.x_m+o.width_m],z=[o.sill_m,o.head_m]))
    matched=[];used_built=set();used_gt=set()
    for key in sorted({(r['floor'],r['kind'],r['facade']) for r in targets}):
        refs=[r for r in targets if (r['floor'],r['kind'],r['facade'])==key]
        cands=[r for r in built if (r['floor'],r['kind'],r['facade'])==key]
        if not refs or not cands:continue
        costs=[]
        for r in refs:
            cost=[]
            for c in cands:
                a,b=r['along'],c['along'];centre=abs((sum(a)-sum(b))/2);overlap=max(0,min(a[1],b[1])-max(a[0],b[0]))
                cost.append(centre+abs((a[1]-a[0])-(b[1]-b[0])) if overlap>0 and centre<=config.opening_match_center_tol_m else 1e6)
            costs.append(cost)
        for i,j in zip(*linear_sum_assignment(costs)):
            if costs[i][j]>=1e6:continue
            r,c=refs[i],cands[j];used_gt.add(r['id']);used_built.add(c['id'])
            along=max(abs(a-b) for a,b in zip(r['along'],c['along']));width=abs((r['along'][1]-r['along'][0])-(c['along'][1]-c['along'][0]));z=[abs(a-b) for a,b in zip(r['z'],c['z'])]
            matched.append(dict(reference_id=r['id'],opening_id=c['id'],floor=key[0],kind=key[1],facade=key[2],reference_along_m=r['along'],candidate_along_m=c['along'],reference_z_m=r['z'],candidate_z_m=c['z'],max_along_endpoint_delta_m=along,width_delta_m=width,z_endpoint_delta_m=z,along_within_judge_tolerance=along<=config.along_claim_tol_m,width_within_judge_tolerance=width<=config.width_claim_tol_m,z_within_judge_tolerance=z[0]<=config.sill_claim_tol_m and z[1]<=config.head_claim_tol_m,host_zone_match=None))
    return dict(mode='legacy_v2_exterior_parameter_diagnostic_not_full_judge_score',judge_config_sha256=digest(ROOT/'src/configs/judge_score.yaml'),tolerances_m=dict(match_center=config.opening_match_center_tol_m,along=config.along_claim_tol_m,width=config.width_claim_tol_m,sill=config.sill_claim_tol_m,head=config.head_claim_tol_m),matched=matched,unmatched_reference=sorted(r['id'] for r in targets if r['id'] not in used_gt),unmatched_built_exterior=sorted(r['id'] for r in built if r['id'] not in used_built),source_exposed_edge_unclassified=unclassified,internal_openings_not_in_exterior_GT=[o['id'] for o in source['openings'] if not o['exterior']],limits=['Legacy exterior GT has no opening host-zone fields; hosts/connections checked separately against original plans.', 'Legacy x_m is world X for North/South and world Y for East/West; sill/head are global Z, not floor-relative.', 'Same judge-config tolerances as typed diagnostic; pairing is not semantic acceptance.'])
