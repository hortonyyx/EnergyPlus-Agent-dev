import json,copy
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
run=Path('/tmp/ep-partial-developer-tests-20261001/run_61sol')
p=json.load(open(run/'candidate_01/proposal.json'))
g=p['geometry']
retracted=[w for w in g['windows'] if w['id'] in ['F1_NCORE_S_01','F1_NCORE_S_02']]
g['windows']=[w for w in g['windows'] if w['id'] not in ['F1_NCORE_S_01','F1_NCORE_S_02']]
g.setdefault('corrections',[]).append({'operation':'retract_inferred_windows','ids':[w['id'] for w in retracted],'before':retracted,'reason':'The original attached annex and actual source contacts show this frontage is internal on the ground level. Retract unsupported ground glazing hypothesis; this is not an observed aperture removal.','source_refs':['mesh_003','mesh_010','candidate_01 source.opening_unbuilt']})
f=next(f for f in g['floors'] if f['name']=='ROOF_ATTIC')
before=copy.deepcopy(f)
c=next(c for c in f['cells'] if c['id']=='R_OFFICE_W2')
c['polygon']=[[-12,-8.8],[-7.5,-8.8],[-7.5,8.9],[-7,8.9],[-7,24.5],[-12,24.5]]
c['x']=[-12,-7];c['y']=[-8.8,24.5]
c['source_refs'].extend(['mesh_003: northwest roof strip is physically continuous with the long roof','07_roof_west_measure: northwest roof hits near z28.0..28.2'])
c['assumptions'].append('The continuous northwest roof strip remains one L-shaped occupied attic space; its variable pitched height is regularized to the roof-level cap.')
c['role_evidence']['source_refs']=c['source_refs'];c['role_evidence']['assumptions']=c['assumptions']
f['footprint']['vertices']=[[-12,-32.2],[.1,-32.2],[.1,-29.5],[.8,-29.5],[.8,-21.5],[.1,-21.5],[.1,8.9],[-7,8.9],[-7,24.5],[-12,24.5]]
g['corrections'].append({'operation':'complete_continuous_northwest_roof','space_id':'R_OFFICE_W2','before':before,'after':copy.deepcopy(f),'reason':'Top source review against the original roof requires the observed northwest roof strip. Keep it continuous rather than splitting the open attic into boxes.','source_refs':['mesh_003','mesh_012','07_roof_west_measure']})
for i,y in enumerate([10.5,13.7,16.9,20.1,23.1],1):
 g['windows'].append({'id':f'R_W_NORTH_{i:02d}','floor':'ROOF_ATTIC','facade':'West','span':[y-.65,y+.65],'z':[25.8,27.5],'room':'R_OFFICE_W2','source_refs':['mesh_005: ambiguous dark roof-level band','inference_007: inferred completion of attic glazing'],'assumptions':['Plausible roof opening in the dark band; the exact pane boundaries are not observed.']})
g['openings'].append({'id':'R_NW_PLANT_D','kind':'door','space_id':'R_OFFICE_W2','other_space_id':'N_PLANT','p1':[-7,20.0],'p2':[-7,21.1],'z':[25.3,27.4],'state':'unknown','source_refs':['mesh_003: continuous roof/plant contact','inference_007: inferred ancillary circulation'],'assumptions':['A service door through the actual common wall is inferred; it provides a second route to the northern stair.']})
p['assumptions'].append('The northwest roof strip seen at approximately z28.0..28.2 is retained in one continuous L-shaped attic room with the long wing, with an inferred service door to the plant room. Its flat cap is simplified to z28.9.')
p['assumptions'].append('Two initially inferred ground northern-core windows were explicitly retracted because the attached annex makes this wall internal; all upper core glazing is retained.')
allcells={c['id']:c for f in g['floors'] for c in f['cells']}
checks=[]
for f in g['floors']:
 ps=[Polygon(c['polygon']) for c in f['cells']]+[Polygon(allcells[s]['polygon']) for s in f.get('spanning_space_ids',[])]
 diff=unary_union(ps).symmetric_difference(Polygon(f['footprint']['vertices'])).area
 if diff>1e-6:raise ValueError((f['name'],diff))
 checks.append({'floor':f['name'],'coverage_difference_m2':diff})
(run/'architectural_proposal_v2.json').write_text(json.dumps(p,indent=2))
(run/'assembly_checks_v2.json').write_text(json.dumps(checks,indent=2))
(run/'10_build_v2.json').write_text(json.dumps([{'tool':'build_bim','arguments':{'proposal_json':json.dumps(p)}}],indent=2))
print('Full preserved proposal revised: 2 window retractions, one continuous attic extension, 5 inferred attic windows and 1 plant service door.')
