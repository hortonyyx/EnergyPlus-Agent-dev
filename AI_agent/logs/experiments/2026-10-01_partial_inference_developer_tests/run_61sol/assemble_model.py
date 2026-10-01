"""Own architectural interpretation. Exports are made ONLY through the BIM bridge.
Metric spans below are explicitly selected/regularized from saved mesh observations.
This script does not import or call any frozen source builder.
"""
import copy, json
from pathlib import Path
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
RUN=Path('/tmp/ep-partial-developer-tests-20261001/run_61sol')
mesh_hash='9a73349d9d024a128160e8771d4bccba79b6e3462ae4f35d787f35f4ddf337fc'
FLOORS=[]; WINDOWS=[]; DOORS=[]; SPACES={}; META={}
layout_refs=['inference_004: inferred interior; no original interior plan','mesh_009: west window rhythm','mesh_010: courtyard window rhythm','mesh_011: transverse wing']
def rect(x0,y0,x1,y1):return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
def cell(sid,role,p,refs=None,note=None):
 refs=refs or layout_refs
 note=note or 'Physical partition and use are an architectural hypothesis for the office context; the true interior is unavailable.'
 c={'id':sid,'role':role,'x':[min(v[0] for v in p),max(v[0] for v in p)],'y':[min(v[1] for v in p),max(v[1] for v in p)],'polygon':p,'source_refs':refs,'assumptions':[note],'role_evidence':{'role':role,'basis':'inferred','source_refs':refs,'assumptions':[note]}}
 return c
def floor(fid,z,h,cells,footprint,spanning=None):
 f={'name':fid,'z_floor':z,'ceiling_height':h,'cells':cells,'footprint':{'vertices':footprint}}
 if spanning:f['spanning_space_ids']=spanning
 FLOORS.append(f)
 for c in cells:
  SPACES[c['id']]=c;META[c['id']]={'floor':fid,'z':z,'h':h}
 return f
def door(did,s1,s2,p1,p2,z0,z1,kind='door',note=None,refs=None):
 DOORS.append({'id':did,'kind':kind,'space_id':s1,'other_space_id':s2,'p1':p1,'p2':p2,'z':[round(z0,3),round(z1,3)],'state':'open' if kind=='open' else 'unknown','source_refs':refs or ['inference_004: inferred circulation and partition host'],'assumptions':[note or 'Door position, width, head height and operating state are inferred; usable jambs are retained.']})
def row(rid,facade,plane,spans,z,ids,refs,note):
 along=0 if facade in ['North','South'] else 1; axis=1-along
 desired={'North':(0,1),'South':(0,-1),'East':(1,0),'West':(-1,0)}[facade]
 for i,span in enumerate(spans,1):
  owners=[]
  for sid in ids:
   c=SPACES[sid];m=META[sid]
   if z[0]<m['z']-1e-6 or z[1]>m['z']+m['h']+1e-6:continue
   p=c['polygon']
   for a,b in zip(p,p[1:]+p[:1]):
    normal=(b[1]-a[1],a[0]-b[0])
    if abs(a[axis]-plane)<1e-7 and abs(b[axis]-plane)<1e-7 and normal[0]*desired[0]+normal[1]*desired[1]>0 and min(a[along],b[along])-1e-7<=span[0] and max(a[along],b[along])+1e-7>=span[1]:
     owners.append(sid)
  owners=sorted(set(owners))
  if len(owners)!=1:raise ValueError((rid,i,facade,plane,span,z,'owners',owners))
  sid=owners[0]
  WINDOWS.append({'id':f'{rid}_{i:02d}','floor':META[sid]['floor'],'facade':facade,'span':span,'z':[round(v,3) for v in z],'room':sid,'source_refs':refs,'assumptions':[note]})

# Two genuine continuous main cores, with no intermediate source floors.
cs_stair=[[-5.5,-29.5],[.8,-29.5],[.8,-21.5],[-5.5,-21.5],[-5.5,-23],[-3.3,-23],[-3.3,-26],[-5.5,-26]]
cn_stair=[[-3,8.9],[6,8.9],[6,13],[3.8,13],[3.8,16],[-3,16]]
floor('CORE_S_STAIR',0,31.5,[cell('CS_STAIR','stairwell',cs_stair,['inference_005','mesh_003','mesh_004','view_0003'],'Continuous inferred stairwell with landings at the declared storeys; flights and landing solids are omitted.')],cs_stair)
floor('CORE_S_LIFT',0,34.2,[cell('CS_LIFT','shaft',rect(-5.5,-26,-3.3,-23),['inference_005','mesh_003','mesh_004'],'Continuous inferred lift/service shaft; upper cap regularizes the observed roof chimney, whose actual function is uncertain.')],rect(-5.5,-26,-3.3,-23))
floor('CORE_N_STAIR',0,32.0,[cell('CN_STAIR','stairwell',cn_stair,['inference_005','mesh_003','mesh_011'],'Continuous inferred main stair with an integral landing area, including roof access; flights are omitted.')],cn_stair)
floor('CORE_N_LIFT',0,32.0,[cell('CN_LIFT','shaft',rect(3.8,13,6,16),['inference_005','mesh_003','mesh_011'],'Inferred continuous lift shaft opening directly into the transverse hall at each office level.')],rect(3.8,13,6,16))
core_ids=['CS_STAIR','CS_LIFT','CN_STAIR','CN_LIFT']
main_footprint=[[-13.6,-33.4],[.8,-33.4],[.8,8.9],[19,8.9],[19,26],[-13.6,26]]
hall_poly=[[-7.5,-33.4],[-5.5,-33.4],[-5.5,16],[19,16],[19,19.1],[-13.6,19.1],[-13.6,16],[-7.5,16]]
west_cuts=[-33.4,-24.735,-18.667,-12.183,-5.717,.566,6.683,12.725,16]
east_cuts=[-21.5,-15.15,-9.05,-2.7,3.5,8.9]
main_levels=[('F1',0,6.4)]+[(f'F{i+2}',round(6.4+i*3.15,3),3.15) for i in range(6)]
for fid,z,h in main_levels:
 C=[cell(fid+'_HALL','corridor',hall_poly,note='One continuous L/T-shaped circulation space, 2 metres in the long wing and 3.1 metres in the transverse wing; no wall divides its turn.')]
 local_roles={}
 for i,(a,b) in enumerate(zip(west_cuts,west_cuts[1:]),1):
  if i==7:
   for suffix,lo,hi in [('A',a,9.585),('B',9.585,b)]:
    C.append(cell(f'{fid}_W07{suffix}','restroom',rect(-13.6,lo,-7.5,hi)));local_roles[f'{fid}_W07{suffix}']='west'
   continue
  if fid=='F1' and i in [3,4]:
   if i==3:C.append(cell(fid+'_LOBBY','lobby',rect(-13.6,west_cuts[2],-7.5,west_cuts[4]),note='One continuous inferred reception and waiting lobby in the observed tall ground storey; no mezzanine is claimed.'))
   continue
  role='office/enclosed'
  if i==1:role='conference/meeting/multipurpose' if fid!='F1' else 'office'
  if i==2 and fid=='F1':role='storage'
  if i==5:role='conference/meeting/multipurpose'
  if i==6:role='lounge/breakroom'
  if i==8:role='copy/print'
  C.append(cell(f'{fid}_W{i:02d}',role,rect(-13.6,a,-7.5,b)));local_roles[f'{fid}_W{i:02d}']='west'
 C.append(cell(fid+'_E00','office/enclosed',rect(-5.5,-33.4,.8,-29.5)));local_roles[fid+'_E00']='east'
 for i,(a,b) in enumerate(zip(east_cuts,east_cuts[1:]),1):
  role='office/enclosed'
  if i==2 and fid=='F1':role='lobby'
  if i==4:role='office'
  C.append(cell(f'{fid}_E{i:02d}',role,rect(-5.5,a,.8,b)));local_roles[f'{fid}_E{i:02d}']='east'
 C.append(cell(fid+'_COPY','copy/print',rect(-5.5,8.9,-3,12.3)));local_roles[fid+'_COPY']='east'
 C.append(cell(fid+'_ELEC','electrical/mechanical',rect(-5.5,12.3,-3,16)));local_roles[fid+'_ELEC']='east'
 for name,lo,hi,role in [('N01',-13.6,-7.4,'conference/meeting/multipurpose'),('N_TEAM',-7.4,5,'office'),('N04',5,11.2,'office/enclosed'),('N05',11.2,19,'office/enclosed')]:
  C.append(cell(fid+'_'+name,role,rect(lo,19.1,hi,26)));local_roles[fid+'_'+name]='north'
 for name,lo,hi,role in [('S01',6,12.3,'conference/meeting/multipurpose'),('S02',12.3,19,'office')]:
  C.append(cell(fid+'_'+name,role,rect(lo,8.9,hi,16)));local_roles[fid+'_'+name]='south'
 floor(fid,z,h,C,main_footprint,core_ids)
 for sid,position in local_roles.items():
  p=SPACES[sid]['polygon'];b=Polygon(p).bounds
  if position=='west':
   y=b[1]+(.65 if sid.endswith(('A','B')) else .9)
   door(sid+'_D',sid,fid+'_HALL',[-7.5,y],[-7.5,y+.9],z,z+2.1)
  elif position=='east':
   y=b[1]+.75
   door(sid+'_D',sid,fid+'_HALL',[-5.5,y],[-5.5,y+.9],z,z+2.1)
  elif position=='north':
   x=b[0]+1.0
   width=1.6 if sid.endswith('N_TEAM') else .95
   door(sid+'_D',sid,fid+'_HALL',[x,19.1],[x+width,19.1],z,z+2.1)
  else:
   x=b[0]+1.0
   door(sid+'_D',sid,fid+'_HALL',[x,16],[x+1.2,16],z,z+2.1)
 if fid=='F1':door('F1_LOBBY_HALL','F1_LOBBY','F1_HALL',[-7.5,-10.7],[-7.5,-9.1],0,2.4,kind='open')
 door(fid+'_CS_D',fid+'_HALL','CS_STAIR',[-5.5,-28.4],[-5.5,-27.2],z,z+2.2)
 door(fid+'_CS_LIFT_D',fid+'_HALL','CS_LIFT',[-5.5,-25.2],[-5.5,-24.2],z,z+2.2)
 door(fid+'_CN_D',fid+'_HALL','CN_STAIR',[-1.6,16],[-.4,16],z,z+2.2)
 door(fid+'_CN_LIFT_D',fid+'_HALL','CN_LIFT',[4.3,16],[5.3,16],z,z+2.2)

door('MAIN_ENTRANCE','F1_LOBBY',None,[-13.6,-12],[-13.6,-10.2],0,2.7,refs=['mesh_008: tall street glazing band','inference_004: inferred entrance leaf position'],note='The entrance façade is supported by the street glazing; exact leaf position is inferred within the lobby frontage.')
door('SOUTH_EXIT','F1_HALL',None,[-7.1,-33.4],[-5.9,-33.4],0,2.3)
door('EAST_EXIT','F1_HALL',None,[19,17.1],[19,18.5],0,2.4)

# Lower annex: a continuous stair, L-shaped hall and broad rooms.
annex_stair=rect(9.1,-22,13.1,-16)
floor('ANNEX_STAIR',0,7,[cell('A_STAIR','stairwell',annex_stair,['inference_006','mesh_003','mesh_010'],'Independent inferred continuous annex stair and upper landing; actual location is unknown.')],annex_stair)
annex_fp=rect(.8,-22,13.1,8.9)
annex_hall=[[.8,-22],[2.8,-22],[2.8,-18],[9.1,-18],[9.1,-16],[2.8,-16],[2.8,8.9],[.8,8.9]]
for fid,z in [('A1',0),('A2',3.5)]:
 C=[cell(fid+'_HALL','corridor',annex_hall,['inference_006'], 'One continuous inferred annex corridor with a stair spur; no partition divides the turn.'),cell(fid+'_STORE','storage',rect(2.8,-22,9.1,-18),['inference_006']),cell(fid+'_MEETING_S','conference/meeting/multipurpose',rect(2.8,-16,13.1,-13),['inference_006'])]
 if fid=='A1':
  C.extend([cell(fid+'_MEETING_C','conference/meeting/multipurpose',rect(2.8,-13,13.1,-3.7),['inference_006']),cell(fid+'_MEETING_N','conference/meeting/multipurpose',rect(2.8,-3.7,13.1,8.9),['inference_006'])])
 else:C.append(cell(fid+'_OPEN_OFFICE','office',rect(2.8,-13,13.1,8.9),['inference_006'],'One continuous open office with no invented partition between the skylight/furniture zones.'))
 floor(fid,z,3.5,C,annex_fp,['A_STAIR'])
 door(fid+'_STORE_D',fid+'_STORE',fid+'_HALL',[4,-18],[4.9,-18],z,z+2.1)
 door(fid+'_MEETING_S_D',fid+'_MEETING_S',fid+'_HALL',[2.8,-14.8],[2.8,-13.8],z,z+2.1)
 if fid=='A1':
  door(fid+'_MEETING_C_D',fid+'_MEETING_C',fid+'_HALL',[2.8,-10.5],[2.8,-8.9],z,z+2.2)
  door(fid+'_MEETING_N_D',fid+'_MEETING_N',fid+'_HALL',[2.8,2.0],[2.8,3.6],z,z+2.2)
 else:door(fid+'_OPEN_OFFICE_D',fid+'_OPEN_OFFICE',fid+'_HALL',[2.8,1.0],[2.8,2.6],z,z+2.2)
 door(fid+'_STAIR_D',fid+'_HALL','A_STAIR',[9.1,-17.55],[9.1,-16.45],z,z+2.1)
door('MAIN_ANNEX_LINK','F1_E02','A1_HALL',[.8,-12.3],[.8,-10.7],0,2.4,kind='open',refs=['inference_006: inferred ground connection of attached annex','mesh_003: shared building contact'])
door('ANNEX_SERVICE_EXIT','A1_HALL',None,[1.25,-22],[2.25,-22],0,2.2)
door('ANNEX_STAIR_EXIT','A_STAIR',None,[10.0,-22],[11.2,-22],0,2.2)

# Windowed attic roof and distinct plant/tower rooms. Pitched/curved roofs are simplified.
rf_fp=[[-12,-32.2],[.1,-32.2],[.1,-29.5],[.8,-29.5],[.8,-21.5],[.1,-21.5],[.1,8.9],[-12,8.9]]
rf=[cell('R_HALL','corridor',rect(-7.5,-32.2,-5.5,8.9),['inference_007']),cell('R_STORE_S','attic',rect(-12,-32.2,-7.5,-21.5),['inference_007']),cell('R_OFFICE_W1','office',rect(-12,-21.5,-7.5,-8.8),['inference_007']),cell('R_OFFICE_W2','office',rect(-12,-8.8,-7.5,8.9),['inference_007']),cell('R_STORE_E0','storage',rect(-5.5,-32.2,.1,-29.5),['inference_007']),cell('R_OFFICE_E1','office',rect(-5.5,-21.5,.1,-11.25),['inference_007']),cell('R_MEETING_E2','conference/meeting/multipurpose',rect(-5.5,-11.25,.1,-2.6),['inference_007']),cell('R_SERVICE_E3','electrical/mechanical',rect(-5.5,-2.6,.1,8.9),['inference_007'],'Inferred attic service room in the roof region without a reliable office-window row; includes a route to the northern stair.')]
floor('ROOF_ATTIC',25.3,3.6,rf,rf_fp,['CS_STAIR','CS_LIFT'])
for sid,xx,y in [('R_STORE_S',-7.5,-31),('R_OFFICE_W1',-7.5,-20.3),('R_OFFICE_W2',-7.5,-7.5),('R_STORE_E0',-5.5,-31),('R_OFFICE_E1',-5.5,-20.2),('R_MEETING_E2',-5.5,-9.8),('R_SERVICE_E3',-5.5,1.2)]:
 door(sid+'_D',sid,'R_HALL',[xx,y],[xx,y+.9],25.3,27.4)
door('R_CS_D','R_HALL','CS_STAIR',[-5.5,-28.4],[-5.5,-27.2],25.3,27.5)
door('R_CS_LIFT_D','R_HALL','CS_LIFT',[-5.5,-25.2],[-5.5,-24.2],25.3,27.5)
door('R_CN_D','R_SERVICE_E3','CN_STAIR',[-2.2,8.9],[-1,8.9],25.3,27.5)
plant_fp=[[-7,12.8],[-3,12.8],[-3,16],[6,16],[6,12.8],[17,12.8],[17,23.3],[-7,23.3]]
plant_main=[[-7,12.8],[-3,12.8],[-3,16],[6,16],[6,12.8],[12.3,12.8],[12.3,23.3],[-7,23.3]]
floor('ROOF_PLANT_N',25.3,5.4,[cell('N_PLANT','electrical/mechanical',plant_main,['inference_007','mesh_003: measured broad roof z approximately 30.7'],'Inferred roof plant room; the actual broad copper roof is regularized as a flat-capped orthogonal ancillary volume.'),cell('N_PLANT_STORE','storage',rect(12.3,12.8,17,23.3),['inference_007'])],plant_fp)
door('N_PLANT_STAIR_D','N_PLANT','CN_STAIR',[-1.6,16],[-.4,16],25.3,27.5)
door('N_PLANT_STORE_D','N_PLANT','N_PLANT_STORE',[12.3,20.2],[12.3,21.3],25.3,27.4)
floor('ROOF_MACHINE_S',28.9,2.6,[cell('S_MACHINE','electrical/mechanical',rect(-8,-28.8,-5.5,-22),['inference_007','mesh_003: south cap near z31.4'],'Inferred lift/stair machinery ancillary room beside the continuous south core.')],rect(-8,-28.8,-5.5,-22))
door('S_MACHINE_STAIR_D','S_MACHINE','CS_STAIR',[-5.5,-28],[-5.5,-26.9],28.9,31.0)

# Facade spans: own observed endpoint interpretation, with declared regularization.
west_spans=[[-32.65,-30.55],[-28.38,-25.95],[-23.52,-22.28],[-21.48,-19.12],[-18.22,-16.02],[-14.92,-12.62],[-11.75,-9.55],[-8.45,-6.22],[-5.22,-3.05],[-2.12,.08],[1.05,3.15],[3.92,6.38],[6.98,9.12],[10.05,12.25],[13.2,15.4],[16.35,18.55],[19.5,21.7],[22.65,24.85]]
east_spans=[[-20.92,-18.75],[-17.82,-15.72],[-14.85,-12.58],[-11.82,-9.38],[-8.68,-6.22],[-5.45,-3.05],[-2.32,.02],[.75,3.22],[3.82,6.35],[6.95,8.65]]
north_spans=[[round(c-1.05,2),round(c+1.05,2)] for c in [-11.8,-8.7,-5.6,-2.5,.6,3.7,6.8,9.9,13.0,16.1]]
cross_east=[[10.35,12.55],[13.45,15.65],[16.55,18.75],[19.65,21.85],[22.75,24.95]]
cross_south=[[7.0,9.1],[10.0,11.75],[12.95,14.65],[15.8,17.8]]
south_end=[[-12.5,-10.5],[-9.8,-8.1],[-7.15,-5.85],[-4.6,-2.8],[-1.7,.1]]
for n,(fid,z,h) in enumerate(main_levels):
 ids=[c['id'] for c in next(f for f in FLOORS if f['name']==fid)['cells']]
 if n==0:
  wg=[[-32.2,-25.3],[-24.0,-19.2],[-18,-15.5],[-14.5,-12.6],[-9.8,-6.3],[-5.1,-.05],[1.1,6.1],[7.1,9.2],[10.0,12.3],[13.2,15.4],[16.6,18.8],[19.8,22.2],[22.8,25.4]]
  row(fid+'_WEST_GLASS','West',-13.6,wg,[1.0,5.4],ids,['mesh_008','mesh_009: continuous tall street glazing'],'Ground glazing bays and door distinction are inferred from a blurred continuous band; not copied from the office window row.')
  row(fid+'_E_END','East',.8,[[-32.6,-30.3]],[1.1,4.8],ids,['mesh_004','inference_004'],'Ground end window completed from the upper pattern; aperture limits are inferred.')
  row(fid+'_NORTH_GLASS','North',26,north_spans,[1.0,5.4],ids,['mesh_006','inference_004'],'Ground openings are a plausible continuation in the heavily shadowed/incomplete facade.')
  row(fid+'_E_CROSS_GLASS','East',19,[v for i,v in enumerate(cross_east) if i!=2],[1.0,5.4],ids,['mesh_004','mesh_006'],'Ground east wing openings are inferred from the street glazing and upper bay rhythm.')
  row(fid+'_E_EXIT_FANLIGHT','East',19,[cross_east[2]],[3.0,5.4],ids,['inference_004'],'Inferred glazing over the east exit, preserving a usable entrance aperture below.')
  row(fid+'_S_CROSS_GLASS','South',8.9,[[13.35,15.5],[16.1,18.5]],[1.1,5.3],ids,['mesh_011','inference_004'],'Only the uncovered part of the southern transverse facade is glazed; the annex contact is kept solid.')
  row(fid+'_S_END','South',-33.4,[south_end[i] for i in [0,1,3,4]],[1.1,4.8],ids,['inference_004','mesh_007'],'The mostly missing southern end is completed with plausible openings; the corridor end remains a door.')
 else:
  ze=[z+.6,z+2.5];zw=[z+.45,z+2.4]
  row(fid+'_WEST','West',-13.6,west_spans,zw,ids,['mesh_005','mesh_009','07_roof_west_measure: selected complete top-row endpoints'],'Selected observed groups are regularized and repeated across the six visibly regular office rows. Mullions within grouped frame apertures are omitted; end groups remain distinct.')
  row(fid+'_EAST','East',.8,east_spans,ze,ids,['mesh_004','mesh_010','06_observe_record: selected courtyard top-row endpoints'],'Observed courtyard groups repeated as a regularized row. The final partly occluded corner aperture is inferred to end at y8.65 with a jamb before the transverse wing.')
  row(fid+'_E_END','East',.8,[[-32.6,-30.3]],ze,ids,['mesh_004'],'Regularized observed two-window end bay.')
  row(fid+'_NORTH','North',26,north_spans,[z+.55,z+2.45],ids,['mesh_006'],'Grouped observed frame rhythm in a shadowed facade; individual lower-row edges are approximate.')
  row(fid+'_E_CROSS','East',19,cross_east,[z+.55,z+2.45],ids,['mesh_004','mesh_006','mesh_012'],'Observed transverse end rhythm regularized, including a hall window rather than cutting it with a partition.')
  row(fid+'_S_CROSS','South',8.9,cross_south,[z+.6,z+2.5],ids,['mesh_011','06_observe_record: facade plane and aperture endpoints'],'Grouped observed southern transverse windows, with separate widths from the other facades.')
  row(fid+'_S_END','South',-33.4,south_end,[z+.6,z+2.4],ids,['mesh_007','inference_004'],'Southern end opening pattern is inferred where mesh is missing or occluded; no measured aperture claim is made.')
 # Core glazing belongs to the continuous source core, not to duplicated rooms.
 row(fid+'_SCORE_E','East',.8,[[-28.9,-27.7]],[z+(1.0 if n==0 else .6),z+(4.9 if n==0 else 2.5)],['CS_STAIR'],['mesh_004','view_0003','inference_005'],'Narrow stair glazing is regularized from the visible end-core strip; exact panes/landing offsets are unknown.')
 row(fid+'_NCORE_S','South',8.9,[[1.2,2.8],[4.0,5.4]],[z+(1.0 if n==0 else .6),z+(5.0 if n==0 else 2.5)],['CN_STAIR'],['mesh_011','inference_005'],'Two inferred glazed stair/landing bays in the northern core frontage; the part contacting the long wing is not glazed.')

annex_e=[[-21.6,-19.65],[-18.55,-16.45],[-15.5,-13.4],[-12.5,-10.4],[-9.4,-7.3],[-6.3,-4.2],[-3.2,-1.1],[-.1,2.0],[3.0,5.1],[6.1,8.2]]
for fid,z in [('A1',0),('A2',3.5)]:
 ids=[c['id'] for c in next(f for f in FLOORS if f['name']==fid)['cells']]+['A_STAIR']
 row(fid+'_EAST','East',13.1,annex_e,[z+(1.0 if z==0 else .6),z+(2.9 if z==0 else 2.5)],ids,['mesh_004','mesh_010: two annex rows'],'Approximate observed east annex bay groups regularized at each of its two independent storey levels.')
 row(fid+'_SOUTH','South',-22,[[3.6,5.7],[6.4,8.4]],[z+.8,z+2.6],ids,['mesh_012','inference_006'],'Southern annex windows are inferred where the end mesh is incomplete.')

rfids=[c['id'] for c in rf]
row('R_E_DORMERS','East',.1,[[-18.72,-17.25],[-16.85,-15.45],[-14.82,-13.38],[-12.95,-11.52],[-10.98,-9.62],[-8.98,-7.65],[-6.38,-4.98],[-4.38,-2.95]],[25.8,27.7],rfids,['mesh_010: visible nonuniform roof-window series','mesh_012'],'Observed dormer aperture rhythm is retained; the pitched hosts are simplified into setback vertical attic walls.')
row('R_W_DORMERS','West',-12,[[-19.9,-18.4],[-16.7,-15.2],[-13.5,-12.0],[-10.3,-8.95],[-7.1,-5.7],[-3.9,-2.5],[-.7,.7],[2.5,3.9],[5.7,7.1]],[25.8,27.5],rfids,['mesh_005: dark setback roof strip','inference_007'],'Western roof openings are inferred within the ambiguous dark roof strip and are not claimed to be individually observed.')
row('R_SCORE_E','East',.8,[[-28.9,-27.7]],[26.0,28.7],['CS_STAIR'],['mesh_004','inference_005'],'Inferred stair glazing in the observed tall end tower.')
row('R_NCORE_S','South',8.9,[[1.2,2.8],[4.0,5.4]],[26.0,28.8],['CN_STAIR'],['mesh_011','inference_005'],'Inferred roof landing glazing within the observed raised northern tower.')

ASSUMPTIONS=[
'Exterior massing is constrained by admitted mesh_003 through mesh_012 and metric mesh pixel hits. The 15-degree local yaw is fixed, with zero translation; axes are local building axes, not surveyed geographic bearings.',
'All interior partitions, use assignments and door leaf positions are architectural inferences. A saved role_evidence record is supplied for every physical source space; the true interior has not been recovered.',
'The main building has one tall ground storey z0..6.4 and six 3.15m office storeys z6.4..25.3, inferred from six regular facade rows over a tall glass band. No unobserved mezzanine is inserted.',
'Continuous stairwell/shaft source spaces span the levels without cloned rooms or intermediate floor slabs. Stair flights, landings, lift machinery and door leaves are beyond this lightweight volume model.',
'Window frames with two closely spaced panes are represented by one grouped aperture. Structural bay wall strips are retained; pane mullions and decorative facade fins are omitted.',
'The courtyard annex is two 3.5m storeys with an inferred independent stair. Its upper open office is a single continuous room; the main/annex ground passage is inferred.',
'Roof mansards and curved copper plant caps are deliberately simplified as setback orthogonal spaces with flat caps: occupied roof offices, attic storage, mechanical plant and core continuations are distinct.',
'Missing southern end, some core glazing, ground entrances, western attic openings and shadowed lower transverse openings are explicitly inferred; door state is unknown. Geometry consistency is not original-image fidelity or code compliance.'
]
UNRESOLVED=[
'No interior plans, floor slab survey, structural information or actual stair/landing geometry were supplied. Repeated upper interior layout is only one plausible office interpretation.',
'The original mesh is incomplete around the ground perimeter and end faces; the partly occluded eastern corner aperture and several shadowed facade dimensions are regularized rather than precisely recovered.',
'Observed four elongated annex roof skylights are not represented as horizontal apertures because this common source kernel supports wall-hosted openings; their roof locations remain visible in mesh_003 and view_0001.',
'Pitched/curved roof surfaces, parapet relief, cornices, wall thickness, furniture, balconies and decorative mullions are omitted or represented by the orthogonal envelope. Roof/service use boundaries are inferred.',
'The exact function of the highest south roof cap (lift ventilation or chimney) is uncertain; it is represented as a continuous service shaft. Native z0 is used as ground datum, although noise and street grade vary.',
'Stairwell source volumes provide storey connectivity and plausible clear room dimensions but do not demonstrate travel-distance, fire separation, accessibility or stair code compliance.'
]
proposal={'geometry':{'schema_version':'2','footprint_x':[-13.6,19],'footprint_y':[-33.4,26],'floors':FLOORS,'windows':WINDOWS,'openings':DOORS,'notes':'Independent fine office BIM architectural interpretation; all evidence and uncertainty retained in run artifacts.'},'mesh_frame':{'mesh_sha256':mesh_hash,'yaw_degrees':15,'translation_m':[0,0,0],'reason':'Bounded original long-wall direction evidence near 90 degrees at yaw15, confirmed by the complete asymmetric footprint and distinct transverse wing. Representative wall planes are regularized around measured surface hits.','source_refs':['directions_001','directions_002','mesh_003','mesh_004','mesh_005','06_observe_record: metric hits']},'assumptions':ASSUMPTIONS,'unresolved':UNRESOLVED}
# Own assembly arithmetic check only; the common BIM source kernel remains authoritative.
checks=[]
for f in FLOORS:
 polys=[Polygon(c['polygon']) for c in f['cells']]+[Polygon(SPACES[s]['polygon']) for s in f.get('spanning_space_ids',[])]
 actual=unary_union(polys);expected=Polygon(f['footprint']['vertices'])
 difference=expected.symmetric_difference(actual).area
 overlaps=sum(polys[i].intersection(polys[j]).area for i in range(len(polys)) for j in range(i+1,len(polys)))
 checks.append({'floor':f['name'],'coverage_difference_m2':difference,'plan_overlap_m2':overlaps})
 if difference>1e-6 or overlaps>1e-6:raise ValueError(checks[-1])
(RUN/'architectural_proposal_v1.json').write_text(json.dumps(proposal,indent=2))
(RUN/'assembly_checks_v1.json').write_text(json.dumps(checks,indent=2))
(RUN/'08_build.json').write_text(json.dumps([{'tool':'build_bim','arguments':{'proposal_json':json.dumps(proposal)}}],indent=2))
print('Explicit proposal:',len(FLOORS),'floor/volume groups',len(SPACES),'physical spaces',len(WINDOWS),'window groups',len(DOORS),'door/open connections')
print('Own arithmetic checks saved; no source export yet.')
