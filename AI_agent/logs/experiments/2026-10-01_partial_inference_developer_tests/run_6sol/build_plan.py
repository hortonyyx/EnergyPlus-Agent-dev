import json
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

RUN = Path('/tmp/ep-partial-developer-tests-20261001/run_6sol')
MESH = 'mesh_007 aligned original top; mesh_008 through mesh_011 aligned exterior views; measured mesh pixels in measure1_reply.json'
INFER = 'Interior unseen in admitted mesh; functional office layout inferred from 3.35 m storey rhythm, facade bays, circulation and core locations'
WINDOW = 'Facade window rhythm in mesh_008 through mesh_011; widths and exact jambs regularized as inference'
CORE = 'Stair/lift positions and door positions inferred; roof blocks and tall end bays suggest circulation/service locations'
Z = 3.35

def rect(x1,y1,x2,y2): return [float(x1),float(y1),float(x2),float(y2)]
def ring_union(spaces):
    shapes=[]
    for s in spaces:
        if 'rect' in s: shapes.append(box(*s['rect']))
        else: shapes.append(Polygon(s['polygon']))
    u=unary_union(shapes)
    assert u.geom_type == 'Polygon', u.geom_type
    assert not u.interiors, 'footprint contains a hole'
    assert abs(u.area-sum(g.area for g in shapes))<1e-6, 'overlapping spaces'
    return [[float(x),float(y)] for x,y in list(u.exterior.coords)[:-1]]

def space(i,role,r=None,p=None,reason=INFER):
    d={'id':i,'role':role,'source_refs':[reason],'assumptions':['Use and partition arrangement inferred; no interior drawing supplied']}
    if r is not None: d['rect']=rect(*r)
    if p is not None: d['polygon']=p
    return d

def door(i,a,b,p1,p2,width=2.2):
    return {'id':i,'space':a,'other_space':b,'p1':list(p1),'p2':list(p2),'z':[0,width],
            'source_refs':[INFER], 'assumptions':['Unobserved interior door, position and height inferred'], 'state':'unknown'}

def row(i,facade,plane,spans,z=(0.85,2.50),src=WINDOW):
    return {'id':i,'facade':facade,'plane':plane,'spans':[[round(a,3),round(b,3)] for a,b in spans],
            'z':list(z),'source_refs':[src], 'assumptions':['Aperture outlines regularized from textured facade; exact jambs uncertain']}

def one_span(a,b,w=1.65):
    c=(a+b)/2
    return (c-w/2,c+w/2)

def two_spans(a,b,w=1.55):
    assert b-a>2*w+1.44
    return [(a+0.72,a+0.72+w),(b-0.72-w,b-0.72)]

def main_template(name,lower=False,ground=False):
    spaces=[];doors=[];rows=[]
    hall=unary_union([box(-7.6,-33.5,-4.2,26.5),box(-4.2,15.8,19,19.2)])
    hp=[[float(x),float(y)] for x,y in list(hall.exterior.coords)[:-1]]
    spaces.append(space('hall','corridor',p=hp))
    wy=[-25.5,-19.5,-13.5,-7.5,-1.5,4.5,10.5,18,26.5]
    for k,(a,b) in enumerate(zip(wy[:-1],wy[1:]),1):
        role='office/enclosed'
        if k==1 and ground: role='lobby'
        elif k==1: role='conference/meeting/multipurpose'
        elif k==6: role='conference/meeting/multipurpose'
        elif k==8: role='lounge/breakroom'
        si=f'west_{k}'
        spaces.append(space(si,role,r=(-14,a,-7.6,b)))
        cy=(a+b)/2
        doors.append(door(f'd_{si}',si,'hall',(-7.6,cy-0.55),(-7.6,cy+0.55)))
    ey=[-28,-21.5,-15,-8.5,-2,4.5,9.5,15.8]
    for k,(a,b) in enumerate(zip(ey[:-1],ey[1:]),1):
        role='office/enclosed'
        if k==4 and lower: role='corridor'
        elif k==2: role='restroom'
        elif k==6: role='copy/print'
        si=f'east_{k}'
        spaces.append(space(si,role,r=(-4.2,a,0.8,b)))
        cy=(a+b)/2
        doors.append(door(f'd_{si}',si,'hall',(-4.2,cy-0.5),(-4.2,cy+0.5)))
    spaces.append(space('south_store','storage',r=(-1.5,-33.5,0.8,-28)))
    doors.append(door('d_south_store','south_store','east_1',(-0.85,-28),(0.15,-28)))
    spaces.append(space('north_west','office/enclosed',r=(-4.2,19.2,0.8,26.5)))
    doors.append(door('d_north_west','north_west','hall',(-4.2,21.7),(-4.2,22.8)))
    sx=[0.8,7,13,19]
    for k,(a,b) in enumerate(zip(sx[:-1],sx[1:]),1):
        si=f'arm_s_{k}'
        spaces.append(space(si,'office/enclosed' if k!=2 else 'conference/meeting/multipurpose',r=(a,9.5,b,15.8)))
        cx=(a+b)/2
        doors.append(door(f'd_{si}',si,'hall',(cx-0.55,15.8),(cx+0.55,15.8)))
    nx=[0.8,7,13]
    for k,(a,b) in enumerate(zip(nx[:-1],nx[1:]),1):
        si=f'arm_n_{k}'
        spaces.append(space(si,'office/enclosed',r=(a,19.2,b,26.5)))
        cx=(a+b)/2
        doors.append(door(f'd_{si}',si,'hall',(cx-0.55,19.2),(cx+0.55,19.2)))
    # The west street facade shows a close and repetitive window rhythm.
    west=[]
    for a,b in zip(wy[:-1],wy[1:]):west+=two_spans(a,b,1.50)
    rows.append(row('west_bays','West',-14,west,(0.65,2.55) if ground else (0.88,2.52)))
    # The courtyard side of the tall bar is obscured by the low wing on the lower two floors.
    east=[]
    for k,(a,b) in enumerate(zip(ey[:-1],ey[1:]),1):
        if b<=9.5 and (not lower or b<=-21.5): east+=two_spans(a,b,1.35)
    east.append(one_span(-33.5,-28,1.15))
    rows.append(row('courtyard_bays','East',0.8,east))
    north=[]
    for a,b in [(-14,-7.6),(-4.2,0.8),(0.8,7),(7,13)]:
        mid=(a+b)/2
        north += [one_span(a,mid,1.25),one_span(mid,b,1.25)]
    rows.append(row('north_bays','North',26.5,north))
    south_arm=[]
    for a,b in zip(sx[:-1],sx[1:]):
        if not lower or a>=13: south_arm.append(one_span(a,b,1.75))
    rows.append(row('arm_court_bays','South',9.5,south_arm))
    rows.append(row('arm_east_bay','East',19,two_spans(9.5,15.8,1.35)))
    rows.append(row('arm_east_hall','East',19,[one_span(15.8,19.2,0.9)],(1.05,2.45)))
    rows.append(row('south_store_window','South',-33.5,[one_span(-1.5,0.8,0.85)]))
    # North and south ends of the main hallway admit daylight on upper floors.
    if not ground:
        rows.append(row('hall_south_light','South',-33.5,[one_span(-7.6,-4.2,0.9)],(1.1,2.55)))
        rows.append(row('hall_north_light','North',26.5,[one_span(-7.6,-4.2,0.9)],(1.1,2.55)))
    return {'footprint':ring_union(spaces),'spaces':spaces,'window_rows':rows,'doors':doors}

def annex_template():
    spaces=[space('hall','corridor',r=(0.8,-21.5,3.5,9.5))]
    doors=[];rows=[]
    ys=[-21.5,-14,-6.5,1,9.5]
    for k,(a,b) in enumerate(zip(ys[:-1],ys[1:]),1):
        si=f'room_{k}'
        role='office' if k in (1,3) else 'conference/meeting/multipurpose'
        spaces.append(space(si,role,r=(3.5,a,13.2,b),reason='mesh_007: flat lower roof and mesh_008: two facade levels; internal division inferred'))
        cy=(a+b)/2
        doors.append(door(f'd_{si}',si,'hall',(3.5,cy-0.6),(3.5,cy+0.6)))
    spans=[]
    for a,b in zip(ys[:-1],ys[1:]): spans+=two_spans(a,b,1.6)
    rows.append(row('east_bays','East',13.2,spans,(0.6,2.55)))
    rows.append(row('south_bays','South',-21.5,[(5,7.4),(9.2,11.6)],(0.65,2.55)))
    return {'footprint':ring_union(spaces),'spaces':spaces,'window_rows':rows,'doors':doors}

def single_template(i,role,r,rows=None):
    ss=[space(i,role,r=r,reason=CORE if role in ('stairwell','shaft','electrical/mechanical') else MESH)]
    return {'footprint':ring_union(ss),'spaces':ss,'window_rows':rows or [],'doors':[]}

def single_polygon_template(i,role,p,rows=None):
    ss=[space(i,role,p=p,reason=MESH)]
    return {'footprint':ring_union(ss),'spaces':ss,'window_rows':rows or [],'doors':[]}

templates={
    'ground':main_template('ground',lower=True,ground=True),
    'second':main_template('second',lower=True),
    'upper':main_template('upper'),
    'annex':annex_template(),
}
core_z=[]
for i in range(8): core_z.append((round(i*Z+1.05,3),round(i*Z+2.55,3)))
templates['south_stair']=single_template('stair','stairwell',(-14,-33.5,-7.6,-25.5),[
    row(f'west_s_{i+1}','West',-14,[one_span(-33.5,-25.5,1.15)],zz,CORE) for i,zz in enumerate(core_z)])
templates['north_stair']=single_template('stair','stairwell',(13,19.2,19,26.5),[
    row(f'east_n_{i+1}','East',19,two_spans(19.2,26.5,1.20),zz,CORE) for i,zz in enumerate(core_z)] + [
    row(f'north_n_{i+1}','North',26.5,two_spans(13,19,1.20),zz,CORE) for i,zz in enumerate(core_z)])
templates['lift']=single_template('shaft','shaft',(-4.2,-33.5,-1.5,-28))
templates['roof_bar']=single_polygon_template('attic','attic',[
    [-7.6,-32],[0.2,-32],[0.2,25],[-12,25],[-12,-25.5],[-7.6,-25.5]], [
    row('dormers','East',0.2,[one_span(a,a+5,1.7) for a in [-25,-19,-13,-7,-1,5]],(0.7,2.0),
        'mesh_008/mesh_007: small high roof-window rhythm; positions simplified')])
templates['roof_arm']=single_template('attic','attic',(0.2,13,18,25))
templates['roof_link']=single_template('attic','attic',(0.2,9.5,6.5,13))
templates['south_plant']=single_template('plant','electrical/mechanical',(-8,-29,0.8,-21))
templates['north_plant']=single_template('plant','electrical/mechanical',(-3.5,9.5,6.5,17))
templates['south_chimney']=single_template('shaft','shaft',(-6.2,-25.3,-5.2,-23.8))

instances=[]
for i in range(8):
    t='ground' if i==0 else ('second' if i==1 else 'upper')
    instances.append({'id':f'F{i+1}','template':t,'z':round(i*Z,3),'height':Z})
for i in range(2): instances.append({'id':f'A{i+1}','template':'annex','z':round(i*Z,3),'height':Z})
instances+= [
    {'id':'SCORE','template':'south_stair','z':0,'height':round(8*Z+3,3)},
    {'id':'NCORE','template':'north_stair','z':0,'height':round(8*Z,3)},
    {'id':'LIFT','template':'lift','z':0,'height':round(8*Z,3)},
    {'id':'ROOF_BAR','template':'roof_bar','z':round(8*Z,3),'height':3.0},
    {'id':'ROOF_ARM','template':'roof_arm','z':round(8*Z,3),'height':3.0},
    {'id':'ROOF_LINK','template':'roof_link','z':round(8*Z,3),'height':3.0},
    {'id':'S_PLANT','template':'south_plant','z':round(8*Z+3,3),'height':1.6},
    {'id':'N_PLANT','template':'north_plant','z':round(8*Z+3,3),'height':2.3},
    {'id':'S_CHIMNEY','template':'south_chimney','z':round(8*Z+4.6,3),'height':2.9},
]

def connection(i,a,b,p1,p2,z1,z2,reason=CORE):
    return {'id':i,'kind':'door','space_id':a,'other_space_id':b,'p1':list(p1),'p2':list(p2),
            'z':[round(z1,3),round(z2,3)],'state':'unknown','source_refs':[reason],
            'assumptions':['Passage inferred for a functional office plan; opening not visible in exterior mesh']}

connections=[]
for i in range(8):
    floor=f'F{i+1}'; z=i*Z
    connections.append(connection(f'd_{floor}_south_stair',f'{floor}:hall','SCORE:stair',(-7.6,-30.5),(-7.6,-29.3),z,z+2.20))
    connections.append(connection(f'd_{floor}_north_stair',f'{floor}:hall','NCORE:stair',(15.4,19.2),(16.6,19.2),z,z+2.20))
    connections.append(connection(f'd_{floor}_lift',f'{floor}:hall','LIFT:shaft',(-4.2,-31.3),(-4.2,-30.1),z,z+2.20))
for i in range(2):
    floor=f'F{i+1}'; annex=f'A{i+1}';z=i*Z
    connections.append(connection(f'd_{floor}_annex',f'{floor}:east_4',f'{annex}:hall',(0.8,-5.8),(0.8,-4.6),z,z+2.2))
connections.append(connection('street_lobby','F1:west_1',None,(-14,-23.1),(-14,-21.9),0,2.45,
                              'mesh_010: street-level facade and openings; entrance location inferred'))
connections.append(connection('south_exit','F1:hall',None,(-6.8,-33.5),(-5.5,-33.5),0,2.45,
                              'mesh_011: south end facade incomplete; secondary entrance inferred'))
connections.append(connection('annex_east_exit','A1:room_3',None,(13.2,-3.6),(13.2,-2.4),0,2.45,
                              'mesh_008: low courtyard wing; exterior access inferred'))
connections.append(connection('roof_stair_access','SCORE:stair','ROOF_BAR:attic',(-7.6,-30.3),(-7.6,-29.1),8*Z,8*Z+2.20,
                              'Continuous southwest stair is inferred to reach the roof attic; access doorway is not visible'))
connections.append(connection('roof_bar_to_arm','ROOF_BAR:attic','ROOF_ARM:attic',(0.2,20.2),(0.2,21.4),8*Z,8*Z+2.20,
                              'Connection between observed adjoining roof volumes inferred for roof circulation'))
connections.append(connection('roof_bar_to_link','ROOF_BAR:attic','ROOF_LINK:attic',(0.2,10.4),(0.2,11.6),8*Z,8*Z+2.20,
                              'Connection between observed adjoining roof volumes inferred for roof circulation'))
connections.append(connection('roof_link_to_arm','ROOF_LINK:attic','ROOF_ARM:attic',(2.2,13),(3.4,13),8*Z,8*Z+2.20,
                              'Connection between observed adjoining roof volumes inferred for roof circulation'))

plan={'templates':templates,'instances':instances,'connections':connections,
      'assumptions':[
          'Yaw +15 degrees aligns the dominant original-mesh wall traces with the BIM axes; source registration uses zero translation.',
          'Eight main office storeys at 3.35 m and two lower-wing storeys are inferred from approximately repeated facade bands and ~27 m parapet.',
          'The detailed interior circulation, enclosed rooms, doors, shafts and their uses are architectural inference; no interiors are supplied.',
          'The southwest stair is continued into the main roof attic, and inter-attic access doors are inferred so roof spaces are reachable.',
          'Curved metal roofs are represented by three flat-topped attic volumes plus two roof mechanical volumes and one chimney in this orthogonal source schema.',
          'Window module dimensions are regularized from repeated but noisy texture marks.'
      ],
      'unresolved':[
          'True internal partition, stair, lift, service and entry positions remain unverified by original interior evidence.',
          'Exact roof curvature, dormer geometry and parapet profiles are unsupported by the orthogonal source representation.',
          'Some outer mesh surfaces are missing, noisy or occluded; exact opening counts and jambs on these facades remain uncertain.'
          ,'Access hatches from attic to rooftop plant housings are unresolved because the source schema contains no observed horizontal hatch detail.'
      ]}

out=RUN/'plan.json'
out.write_text(json.dumps(plan,indent=2))
(RUN/'build_call.json').write_text(json.dumps([{'tool':'build_parametric_bim','arguments':{'plan_json':json.dumps(plan)}}]))
print('plan',out,'templates',len(templates),'instances',len(instances),'connections',len(connections))
print('main spaces',len(templates['upper']['spaces']),'main windows per upper template',sum(len(r['spans']) for r in templates['upper']['window_rows']))
print('main footprint',templates['upper']['footprint'])
