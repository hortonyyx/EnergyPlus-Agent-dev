import json,copy
from pathlib import Path
from shapely.geometry import Polygon
from shapely.ops import unary_union
run=Path('/tmp/ep-partial-developer-tests-20261001/run_61sol')
p=json.load(open(run/'candidate_02/proposal.json'));g=p['geometry']
f=next(f for f in g['floors'] if f['name']=='ROOF_PLANT_N');old=copy.deepcopy(f)
f['z_floor']=28.2;f['ceiling_height']=2.5
for c in f['cells']:
 c['polygon']=[[x,21.2 if y==23.3 else y] for x,y in c['polygon']]
 c['y']=[min(q[1] for q in c['polygon']),max(q[1] for q in c['polygon'])]
 c['source_refs'].append('12_height_review: north roof strip near z28.2, raised copper top near z30.7 begins about y21.2')
 c['assumptions'].append('An inferred plant deck at z28.2 separates the raised ancillary room from the lower attic; the actual deck was not visible.')
 c['role_evidence']['source_refs']=c['source_refs'];c['role_evidence']['assumptions']=c['assumptions']
f['footprint']['vertices']=[[x,21.2 if y==23.3 else y] for x,y in f['footprint']['vertices']]
lowpoly=old['footprint']['vertices']
lowcell={'id':'N_ROOF_ATTIC','role':'attic','polygon':lowpoly,'x':[-7,17],'y':[12.8,23.3],'source_refs':['mesh_003','12_height_review: measured lower roof strip z28.2 and raised mass z30.7'],'assumptions':['One continuous inferred attic below the raised northern plant deck, without a fake partition at the previous equipment-storage division. The deck at z28.2 is inferred.'],'role_evidence':{'role':'attic','basis':'inferred','source_refs':['mesh_003','12_height_review'],'assumptions':['Inferred roof void/storage use; no interior evidence was supplied.']}}
lowfloor={'name':'ROOF_LOWER_N','z_floor':25.3,'ceiling_height':2.9,'footprint':{'vertices':lowpoly},'cells':[lowcell]}
g['floors'].append(lowfloor)
for d in g['openings']:
 if d['id']=='R_NW_PLANT_D':d['other_space_id']='N_ROOF_ATTIC'
 if d['id'] in ['N_PLANT_STAIR_D','N_PLANT_STORE_D']:
  d['z']=[28.2,30.3]
  d['source_refs'].append('12_height_review: inferred plant deck at measured lower roof cap')
  d['assumptions'].append('Upper plant door moved to the newly inferred deck, preserving its plan position, width and host adjacency.')
g['openings'].append({'id':'N_ROOF_ATTIC_STAIR_D','kind':'door','space_id':'N_ROOF_ATTIC','other_space_id':'CN_STAIR','p1':[-1.6,16],'p2':[-.4,16],'z':[25.3,27.4],'state':'unknown','source_refs':['mesh_003: roof/contact topology','inference_007: inferred attic access'],'assumptions':['Inferred lower attic access through the actual common stair wall.']})
g.setdefault('corrections',[]).append({'operation':'refine_northern_roof_body_and_deck','before':old,'after':copy.deepcopy(f),'added_floor':lowfloor,'reason':'Original top pixel hits separate a z28.2 lower strip from the raised z30.7 mass. Preserve the lower continuous attic and shorten the upper mechanical room on an explicitly inferred deck; north core remains continuous.','source_refs':['mesh_003','12_height_review']})
p['assumptions'].append('North roof source review separates a continuous attic at z25.3..28.2 from a raised plant room at z28.2..30.7, with its north wall regularized near y21.2. The plant deck and room uses are inferred; the measured stepped roof profile is observed.')
p['unresolved'].append('The northern plant deck z28.2 is an architectural interpretation of the stepped exterior roof, not an observed interior slab. Copper slopes/curves are still approximated by orthogonal source spaces.')
allcells={c['id']:c for f in g['floors'] for c in f['cells']}
for f in g['floors']:
 actual=unary_union([Polygon(c['polygon']) for c in f['cells']]+[Polygon(allcells[s]['polygon']) for s in f.get('spanning_space_ids',[])])
 if actual.symmetric_difference(Polygon(f['footprint']['vertices'])).area>1e-6:raise ValueError(f['name'])
(run/'architectural_proposal_v3.json').write_text(json.dumps(p,indent=2))
(run/'13_build_v3.json').write_text(json.dumps([{'tool':'build_bim','arguments':{'proposal_json':json.dumps(p)}}],indent=2))
