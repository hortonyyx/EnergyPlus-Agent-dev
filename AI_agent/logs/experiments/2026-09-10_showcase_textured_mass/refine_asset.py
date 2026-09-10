"""SOTA developer interpretation of measured UV facades, with an explicit interior hypothesis.

Only showcase assets are written. Reuses source geometry, contact, opening and
enclosure checks. This is deliberately not a product-model/cold-start result.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from src.agent.correction.schema import CorrectedGeometry,Floor,Cell,FootprintRing,Window,WallOpening
from src.agent.geometry.source_bim import build_source_bim,source_view_geometry
from src.agent.geometry.source_enclosure import apply_source_enclosure
from src.agent.geometry.source_model import _digest
from scripts.tool_scripts.render_geometry_viewer import build_viewer_html
LOG=Path(__file__).resolve().parent
ASSET=ROOT/'showcase/2026-09-11-research-report/demos/textured-mass'
MAIN=Polygon([[-13.7,-33.4],[.7,-33.4],[.7,9.1],[18.9,9.1],[18.9,26.1],[-13.7,26.1]])
ATTIC=Polygon([[-12.5,-32.3],[.7,-32.3],[.7,9.1],[17.8,9.1],[17.8,25.0],[-12.5,25.0]])
ANNEX=box(.7,-21.5,13,9.1)
CORES={'CORE_S':box(-7.9,-33.4,-5.5,-28.8),'CORE_E':box(.7,9.1,5,16.3)}

def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def ring(p):return [[round(x,5),round(y,5)] for x,y in list(orient(p.simplify(0),1).exterior.coords)[:-1]]
def segments(p):
    r=ring(p)
    for a,b in zip(r,r[1:]+r[:1]):
        d=np.array(b)-a;n=np.array([d[1],-d[0]])/np.linalg.norm(d)
        yield a,b,n
def parts(p):return [p] if p.geom_type=='Polygon' else list(p.geoms)

def observations():
    measure=json.loads((LOG/'facade_views/measurements.json').read_text());out=[]
    # These are aperture/group rectangles read by the main assistant from
    # measured orthographic renders. They are not fitted to a generated BIM.
    boxes={
      'west':[(66,142),(169,245),(271,344),(370,445),(470,544),(570,645),(671,746),(772,848),(873,950),(975,1051),(1076,1152),(1177,1253),(1278,1355),(1380,1457),(1482,1559),(1639,1679),(1688,1792),(1805,1895)],
      'north':[(61,135),(165,238),(265,340),(367,442),(469,545),(571,648),(674,751),(776,853),(879,957),(980,1057)],
      'court_long':[(62,107),(130,176),(435,508),(530,609),(632,708),(733,809),(833,909),(935,1012),(1036,1114),(1138,1215),(1240,1317),(1341,1385)],
      'court_short':[(37,98),(202,285),(306,383),(405,480)],
    }
    zrows=[(6.85,8.40),(10.0,11.6),(13.15,14.8),(16.35,18.0),(19.55,21.15),(22.75,24.35)]
    def add(fid,view,px,z0,z1,tag,confidence='observed_group_regularised'):
        m=measure[view]; lo,hi=m['along_range']; ppm=m['width_pixels']/m['view_width_m']
        vals=[lo-1+p/ppm for p in px] if m['along_pixel_direction']=='increasing' else [hi+1-p/ppm for p in px]
        span=sorted(round(v,3) for v in vals)
        axis=m['axis'];plane=m['plane_estimate'];facade={'west':'West','north':'North','court_long':'East','court_short':'South','annex_east':'East'}[view]
        if view=='court_long' and span[1]>-21.5 and fid=='F2':z0=max(z0,7.0)
        if view=='court_short' and span[0]<13 and fid=='F2':z0=max(z0,7.0)
        out.append(dict(id=f'{fid}_{tag}',floor=fid,facade=facade,span=span,z=[z0,z1],axis=axis,plane=plane,
             evidence={'view':view,'pixel_x':list(px),'pixel_y':[(33-z1)*32,(33-z0)*32],'basis':confidence,
             'note':'Main assistant interpretation of the actual metric UV rendering; a window group may contain multiple panes. No per-sash truth claim.'}))
    for j,z in enumerate(zrows):
        for view,groups in boxes.items():
            for k,px in enumerate(groups):add(f'F{j+2}',view,px,*z,f'{view}_{k+1:02}')
    for o in out:
        if o['id'].endswith('court_long_12'):
            o['evidence']['note']='Corner window is partially visible; the projected return face contaminates pixels beyond the corner. Visible width retained, full aperture uncertain.'
    # Street glazing is visually irregular, with entrances excluded explicitly.
    for k,px in enumerate([(64,142),(174,237),(275,337),(376,443),(480,544),(582,645),(684,748),(786,850),(887,951),(989,1053),(1092,1157),(1303,1375),(1440,1510)]):
        add('F1','west',px,1.25,4.45,f'west_shop_{k+1:02}','observed_glazing_approximate')
    for k,px in enumerate([(65,142),(173,240),(273,342),(378,448),(478,545),(684,754),(787,855),(886,960),(985,1053)]):
        add('F1','north',px,1.0,4.2,f'north_shop_{k+1:02}','low_visibility_glazing_hypothesis')
    for k,px in enumerate([(62,107),(130,176)]):add('F1','court_long',px,1.5,4.5,f'court_ground_{k+1:02}')
    for k,px in enumerate([(495,547),(565,613),(632,674),(696,740),(758,804),(897,940),(964,1006)]):
        add('F8','court_long',px,26.20,27.45,f'roof_court_{k+1:02}')
    # The tall street glazing at the setback's northern end is retained as 3 groups.
    for k,span in enumerate([(16.7,19),(19.35,21.8),(22.15,24.4)]):
        out.append(dict(id=f'F8_west_glazing_{k+1}',floor='F8',facade='West',span=list(span),z=[25.3,27.0],axis=0,plane=-12.5,
            evidence={'view':'input_views/street.png','basis':'visible_glazing_estimated','note':'Street-side roof setback glazing; dimensions estimated from oblique view.'}))
    for j,(z0,z1) in enumerate([(1,2.7),(4,5.95)]):
        for k,px in enumerate([(39,112),(141,214),(246,319),(349,421),(451,523),(553,625),(655,727),(757,829),(855,925)]):
            add('ANNEX','annex_east',px,z0,z1,f'annex_row{j+1}_{k+1:02}')
    return out

def snap_cuts(lo,hi,desired,intervals):
    spans=sorted((max(lo,a),min(hi,b)) for a,b in intervals if b>lo and a<hi)
    gaps=[];end=lo
    for a,b in spans:
        if a-end>.22:gaps.append((a+end)/2)
        end=max(end,b)
    if hi-end>.22:gaps.append((hi+end)/2)
    result=[lo]
    for d in desired:
        options=[g for g in gaps if g>result[-1]+2.6 and g<hi-2.6]
        if options:result.append(min(options,key=lambda g:abs(g-d)))
    return sorted(set(result+[hi]))

def inferred_layout(fid,obs):
    rooms=[]
    def add(name,poly,role):
        for k,p in enumerate(parts(poly)):
            if p.area>.01:rooms.append(dict(id=f'{fid}_{name}_{k}',poly=p,role=role))
    hall=Polygon([[-7.9,-28.8],[-5.5,-28.8],[-5.5,16.3],[18.9,16.3],[18.9,18.9],[-13.7,18.9],[-13.7,16.3],[-7.9,16.3]])
    add('hall',hall,'corridor_inferred')
    def intervals(view):return [o['span'] for o in obs if o['floor']==fid and o['evidence']['view']==view]
    w=snap_cuts(-33.4,16.3,[-27,-21,-15,-9,-3,3,9],intervals('west'))
    e=snap_cuts(-33.4,9.1,[-28,-22,-16,-10,-4,3],intervals('court_long'))
    n=snap_cuts(-13.7,18.9,[-8,-2.5,3,8.5,14],intervals('north'))
    south=snap_cuts(5,18.9,[9,12,15.5],intervals('court_short'))
    for i,(a,b) in enumerate(zip(w,w[1:])):add(f'office_w{i+1}',box(-13.7,a,-7.9,b),'office_inferred')
    for i,(a,b) in enumerate(zip(e,e[1:])):add(f'office_e{i+1}',box(-5.5,a,.7,b),'office_inferred')
    for i,(a,b) in enumerate(zip(n,n[1:])):add(f'office_n{i+1}',box(a,18.9,b,26.1),'office_inferred')
    add('services',box(-5.5,9.1,.7,16.3),'services_inferred')
    for i,(a,b) in enumerate(zip(south,south[1:])):add(f'office_s{i+1}',box(a,9.1,b,16.3),'office_inferred')
    return rooms

def build(interiors=False, output=None):
    version='inferred' if interiors else 'exterior';out=output or ASSET/version;out.mkdir(parents=True,exist_ok=False)
    obs=observations();floors=[];rooms=[];metadata={}
    core_union=unary_union(list(CORES.values()))
    def floor(fid,poly,z,h,layout=None,role='office_merged'):
        rows=layout or [dict(id=f'{fid}_merged',poly=poly,role=role)]
        cells=[]
        for r in rows:
            assert not r['poly'].interiors,'Source ring cannot silently omit a hole'
            x0,y0,x1,y1=r['poly'].bounds
            cells.append(Cell(id=r['id'],role=r['role'],x=[x0,x1],y=[y0,y1],polygon=ring(r['poly'])))
            r.update(floor=fid,z=z,h=h);rooms.append(r);metadata[r['id']]={'role':r['role'],'basis':'interior_hypothesis' if 'inferred' in r['role'] else 'observed_envelope_merged','plan_area_m2':r['poly'].area}
        assert not poly.interiors
        floors.append(Floor(name=fid,z_floor=z,ceiling_height=h,cells=cells,footprint=FootprintRing(vertices=ring(poly))))
    for i in range(8):
        fid=f'F{i+1}';z=0 if i==0 else 5.6+(i-1)*3.2;h=5.6 if i==0 else (2.8 if i==7 else 3.2)
        footprint=ATTIC if i==7 else MAIN
        if interiors and i<7:footprint=footprint.difference(core_union)
        layout=inferred_layout(fid,obs) if interiors and 0<i<7 else None
        floor(fid,footprint,z,h,layout,role='commercial_merged' if i==0 else 'office_merged')
    if interiors:
        for fid,p in CORES.items():floor(fid,p,0,24.8,role='vertical_core_inferred')
    floor('ANNEX',ANNEX,0,6.9,role='annex_merged')
    floor('ROOF_N',box(-8,13,15.6,23),27.6,3.1,role='roof_enclosure')
    floor('ROOF_S',box(-11.8,-31,-2.3,-23),27.6,2.5,role='roof_enclosure')
    floor('ROOF_STACK',box(-9,-28,-7,-26),30.1,3.6,role='roof_stack')
    windows=[];by_window={}
    def edge_owners(o):
        results=[];axis=o['axis'];other=1-axis
        for r in rooms:
            if o['z'][0]<r['z']-1e-7 or o['z'][1]>r['z']+r['h']+1e-7:continue
            for a,b,n in segments(r['poly']):
                want={'West':[-1,0],'East':[1,0],'North':[0,1],'South':[0,-1]}[o['facade']]
                if np.dot(n,want)<.99 or abs(a[axis]-o['plane'])>1e-5 or abs(b[axis]-o['plane'])>1e-5:continue
                if min(a[other],b[other])-1e-6<=o['span'][0] and max(a[other],b[other])+1e-6>=o['span'][1]:results.append(r)
        return results
    for o in obs:
        owners=edge_owners(o)
        if len(owners)!=1:
            write(out/'failed_window.json',{'opening':o,'owners':[r['id'] for r in owners]});raise ValueError(f"{o['id']}: found {len(owners)} owners")
        r=owners[0];windows.append(Window(id=o['id'],floor=r['floor'],facade=o['facade'],span=o['span'],z=o['z'],room=r['id']));by_window[o['id']]=o['evidence']
    doors=[]
    if interiors:
        # Continuous core volumes omit intermediate slabs. Connections are
        # proposed landing doorways; stair flights/elevators are not modelled.
        cores=[r for r in rooms if r['floor'] in CORES]
        for f in floors[:7]:
            rows=[r for r in rooms if r['floor']==f.name];halls=[r for r in rows if r['role']=='corridor_inferred'];targets=halls+cores
            for r in rows:
                if r in halls:continue
                candidates=[]
                for t in targets:
                    edge=r['poly'].boundary.intersection(t['poly'].boundary)
                    for e in ([edge] if edge.geom_type=='LineString' else list(getattr(edge,'geoms',[]))):
                        if e.geom_type=='LineString' and e.length>1.05:candidates.append((e.length,t,e))
                if not candidates:raise ValueError('No proposed circulation connection for '+r['id'])
                _,t,e=max(candidates,key=lambda row:row[0]);mid=e.length/2;p1=e.interpolate(mid-.45);p2=e.interpolate(mid+.45)
                doors.append(WallOpening(id='D_'+r['id'],kind='door',space_id=r['id'],other_space_id=t['id'],p1=list(p1.coords)[0],p2=list(p2.coords)[0],z=[r['z'],r['z']+2.1],state='unknown',source_refs=['explicit hypothetical office-layout scenario; no interior evidence'],assumptions=['Inferred door and circulation connection.']))
            for c in cores:
                for h in halls:
                    edge=c['poly'].boundary.intersection(h['poly'].boundary)
                    lines=[edge] if edge.geom_type=='LineString' else list(getattr(edge,'geoms',[]))
                    lines=[e for e in lines if e.geom_type=='LineString' and e.length>1.2]
                    if lines:
                        e=max(lines,key=lambda e:e.length);mid=e.length/2
                        doors.append(WallOpening(id=f'D_{f.name}_{c["id"]}',kind='door',space_id=h['id'],other_space_id=c['id'],p1=list(e.interpolate(mid-.5).coords)[0],p2=list(e.interpolate(mid+.5).coords)[0],z=[h['z'],h['z']+2.1],state='unknown',source_refs=['explicit hypothetical vertical-core landing'],assumptions=['Continuous shaft volume; stair flights and actual core position unverified.']))
    # Ground entries are illustrative hypotheses in two clear gaps between shop groups.
    for name,facade,p1,p2 in [('street','West',[-13.7,-11.65],[-13.7,-10.0]),('north','North',[.0,26.1],[1.65,26.1])]:
        owner=next(r for r in rooms if r['floor']=='F1')
        doors.append(WallOpening(id='D_entry_'+name,kind='door',space_id=owner['id'],other_space_id=None,p1=p1,p2=p2,z=[0,2.9],state='unknown',source_refs=['ground-level UV view; entrance hypothesis in visible glazing break'],assumptions=['Exact entrance position, threshold and dimensions unverified.']))
    geom=CorrectedGeometry(schema_version='2',footprint_x=[-13.7,18.9],footprint_y=[-33.4,26.1],floors=floors,windows=windows,openings=doors)
    source=build_source_bim(geom,capability_profile='orthogonal_polygon')
    write(out/'geometry_check.json',source['validation'])
    if source['validation']['status']!='pass':
        write(out/'unbuilt.json',source['unbuilt_openings']);raise ValueError(source['validation'])
    assumptions=[
      '本轮由主助手直接判读真实 GLB 和量测后的 UV 立面，按相对高精度目标制作；是展示/探索成果，非产品模型独立自动生成成绩。',
      'L形主体、低层附属体、沿街退台和屋顶体量按网格与贴图估计规整。外墙采用代表面，未制作材料分层或精细实体墙。',
      '六排标准层窗组逐立面定位，标准层间距约3.2m；首层5.6m和顶层2.8m仍为估计。窗组内细窗框暂未逐扇拆分。',
      '两个端部原网格基本缺失，使用灰色未知边界，不沿这些端面补造规则窗排。',
      '低层附属体保留一个合并空间，未知内部楼板不强行生成；其与主楼连接界面按抽象分界处理。',
      '屋顶曲面规整成可用的体量/水平顶面，地面坡度与门槛简化，遮挡区和窗洞尺寸仍需更多资料核对。',
    ]
    if interiors:assumptions.append('内部为明确的办公布局假设：走廊、办公室、服务空间和两处连续竖向核心；不是实际房间还原。核心中不添加逐层封堵楼板，楼梯踏步和电梯未展开。')
    else:assumptions.append('本版各层只保留合并空间，真实内部隔墙、核心筒和内门未知。')
    source['assumptions']=assumptions
    for s in source['spaces']:s['evidence']=metadata[s['id']];s['source_refs']=['input.glb','metric UV observations']
    for o in source['openings']:
        if o['kind']=='window':o['source_refs']=[f"facade_views/{by_window[o['id']]['view']}.png"];o['assumptions']=[by_window[o['id']]['note']];o['evidence']=by_window[o['id']]
    virtual=[]
    for b in source['boundaries']:
        if b['geometry_type']=='wall' and any(('ANNEX' in b['space_id']) != ('ANNEX' in a) for a in b['adjacent_space_ids']):b['kind']='virtual';virtual.append(b['id'])
    source['generation']={'method':'main_assistant_SOTA_direct_interpretation','variant':version,'additional_product_model_calls':0,'solver_calls':0,
      'input_glb_sha256':hashlib.sha256((ASSET/'input.glb').read_bytes()).hexdigest(),'local_frame':{'units':'m','up':'Z','u':'cos15*GLB.x+sin15*GLB.z','v':'sin15*GLB.x-cos15*GLB.z','z':'GLB.y'},
      'observed_windows':by_window,'interior_hypothesis':interiors,'virtual_mass_junctions':virtual,
      'unresolved':['Actual room layout and internal doors','Roof curvature and interior access to attic','Ground slope and exact storey levels','Occluded facades and exact sash inventory','No thermal or other simulation evaluation']}
    source['source_model_sha256']=_digest({k:v for k,v in source.items() if k!='source_model_sha256'})
    unknown=[]
    for b in source['boundaries']:
        if b['geometry_type']!='wall' or b['adjacent_space_ids']:continue
        p=np.array(b['vertices']);cond=(np.ptp(p[:,1])<1e-6 and p[0,1]<-32.2) or (np.ptp(p[:,0])<1e-6 and p[0,0]>17.7)
        if cond and not any(b['id'] in hs for hs in source['opening_hosts'].values()):
            unknown.append({'boundary_id':b['id'],'condition':'unknown','scope':'whole','source_refs':['metric end-facade renders contain no complete wall surface'],'assumptions':['Possible neighbouring-building occlusion or mesh crop gap; actual enclosure and openings unknown.'],'evidence_kind':'manual_annotation'})
    declaration={'schema_version':'source_enclosure_input_v1','base_source_model_sha256':source['source_model_sha256'],'boundaries':unknown}
    source=apply_source_enclosure(source,declaration)
    display=source_view_geometry(source)
    for p in source['spaces']:
        if p['role']=='vertical_core_inferred':assert p['height']==24.8
    cross_sections=[]
    for z in [2,6,10,14,18,22,26]:
        polys=[r['poly'] for r in rooms if r['z']<=z<r['z']+r['h'] and r['floor'] not in ['ANNEX','ROOF_N','ROOF_S','ROOF_STACK']]
        actual=unary_union(polys);expected=MAIN if z<24.8 else ATTIC
        error=actual.symmetric_difference(expected).area;assert error<1e-6
        cross_sections.append({'z':z,'main_floor_coverage_difference_m2':error})
    report={'variant':version,'main_storeys':8,'spaces':len(source['spaces']),'window_groups':len(windows),'doors':len(doors),'interior_hypothesis':interiors,
       'source_validation':source['validation'],'coverage_sections':cross_sections,'unknown_boundaries':len(unknown),'source_sha256':source['source_model_sha256'],
       'actual_interiors_verified':False,'generation':'Direct main-assistant interpretation + deterministic tools; no separate product-model invocation.'}
    write(out/'source_model.json',source);write(out/'display_geometry.json',display);write(out/'proposal.json',geom.model_dump(mode='json'));write(out/'observations.json',obs);write(out/'report.json',report)
    title='Voimatalo · '+('空间推理方案（内部为假设）' if interiors else '外壳与楼层还原示意')
    (out/'viewer.html').write_text(build_viewer_html(display,title=title))
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--interiors',action='store_true');parser.add_argument('--out',type=Path);a=parser.parse_args();build(a.interiors,a.out)
