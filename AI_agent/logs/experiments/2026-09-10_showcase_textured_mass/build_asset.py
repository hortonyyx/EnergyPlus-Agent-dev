"""Developer-assisted exterior interpretation, assembled by the existing BIM kernel.

No product-model experiment, GT, EnergyPlus, or edits to production code.
Dimensions below are explicit estimates from the GLB and its orthographic views.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from src.agent.correction.schema import CorrectedGeometry, Floor, Cell, FootprintRing, Window, WallOpening
from src.agent.geometry.source_bim import build_source_bim, source_view_geometry
from src.agent.geometry.source_model import _digest
from scripts.tool_scripts.render_geometry_viewer import build_viewer_html

OUT=ROOT/'showcase/2026-09-11-research-report/demos/textured-mass'
LOG=Path(__file__).resolve().parent
MAIN=[[-13.7,-33.4],[0.7,-33.4],[0.7,9.1],[18.9,9.1],[18.9,26.1],[-13.7,26.1]]
ATTIC=[[-12.6,-32.3],[-0.4,-32.3],[-0.4,10.2],[17.8,10.2],[17.8,25.0],[-12.6,25.0]]
ANNEX=[[0.7,-21.5],[13.0,-21.5],[13.0,9.1],[0.7,9.1]]

def write(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'source_model.json').exists(): raise FileExistsError('Use a new version directory rather than overwrite a saved model')
    floors=[]; windows=[]; doors=[]; evidence={}
    def add_floor(fid,ring,z,h,role,description):
        xs,ys=zip(*ring); sid=f'{fid}_merged'
        floors.append(Floor(name=fid,z_floor=z,ceiling_height=h,
            cells=[Cell(id=sid,role=role,x=[min(xs),max(xs)],y=[min(ys),max(ys)],polygon=ring)],
            footprint=FootprintRing(vertices=ring)))
        evidence[sid]={'basis':'developer_assisted_inference','description':description,'internal_partitions':'unknown; merged expression'}
        return sid
    for i in range(8):
        z=0 if i==0 else 5.6+(i-1)*3.2
        h=5.6 if i==0 else (2.8 if i==7 else 3.2)
        add_floor(f'F{i+1}',ATTIC if i==7 else MAIN,z,h,
            'commercial_merged' if i==0 else 'office_merged',
            'Observed L-shaped exterior and window rows; floor levels estimated. Attic setback regularised.' if i else 'Street commercial level, approximate common ground plane; actual ground slope and mezzanines unresolved.')
    add_floor('ANNEX',ANNEX,0,7.2,'annex_merged','Low attached body from GLB. Its internal floors are not resolved; two visible rows of glazing do not become asserted slabs.')
    add_floor('ROOF_N',[[-8,13],[15.6,13],[15.6,23],[-8,23]],27.6,3.1,'roof_enclosure','Visible roof volume simplified as one enclosure; use and interior unknown.')
    add_floor('ROOF_S',[[-11.8,-31],[-2.3,-31],[-2.3,-23],[-11.8,-23]],27.6,2.5,'roof_enclosure','Visible southern rooftop enclosure, simplified.')
    add_floor('ROOF_STACK',[[-9,-28],[-7,-28],[-7,-26],[-9,-26]],30.1,3.6,'roof_stack','Visible rooftop stack approximated as a small prism; not an occupied room.')

    def row(fid,facade,lo,hi,count,z0,z1,tag,width_fraction=.71,skip=()):
        for k,center in enumerate(np.linspace(lo,hi,count)):
            if any(abs(center-c)<1.5 for c in skip): continue
            pitch=(hi-lo)/(count-1) if count>1 else 2
            half=min(pitch*width_fraction/2,1.2)
            wid=f'{fid}_{tag}_{k+1:02}'
            windows.append(Window(id=wid,floor=fid,facade=facade,span=[round(center-half,3),round(center+half,3)],z=[round(z0,3),round(z1,3)],room=f'{fid}_merged'))
            evidence[wid]={'basis':'estimated_window_group','view':tag,'description':'Facade glazing group pattern observed in UV views; count, width and position regularised. Not a measured single-sash inventory.'}
    for i in range(1,7):
        fid=f'F{i+1}'; z=5.6+(i-1)*3.2
        row(fid,'West',-31.4,24.1,25,z+1.0,z+2.7,'west')
        row(fid,'North',-11.8,17.0,14,z+1.0,z+2.7,'north')
        row(fid,'East',-31.3,7.0,18,z+1.0,z+2.7,'courtyard_long')
        row(fid,'East',11.2,24.0,7,z+1.0,z+2.7,'east_short')
        row(fid,'South',-11.7,-1.3,6,z+1.0,z+2.7,'south_end')
        row(fid,'South',2.7,16.9,7,z+1.0,z+2.7,'courtyard_short')
    # F2 east inner windows intersect the annex until z=7.2: those lower parts
    # are unobserved/occluded. Keep only the observed portion above its roof.
    for w in windows:
        if w.floor=='F2' and w.facade=='East' and w.span[0]>-21.5 and w.span[1]<9.1:
            w.z=[7.35,8.3]
            evidence[w.id]['description']+=' Lower portion hidden by annex; first row is clipped to an explicit estimated above-roof interval.'
    row('F1','West',-30.6,23.0,17,1.0,4.4,'street_ground',.83,skip=(-15.0,))
    row('F1','North',-11.4,16.5,9,1.0,4.4,'north_ground',.83,skip=(4.0,))
    row('F1','East',11.2,24.0,5,1.0,4.4,'east_ground',.76)
    row('F1','East',-31.2,-23.1,4,1.0,4.4,'south_court_ground',.72)
    row('F8','West',-29.7,22.5,20,25.3,26.9,'attic_west',.74)
    row('F8','North',-10.8,15.8,12,25.3,26.9,'attic_north',.74)
    row('F8','East',-29.7,8.0,16,25.3,26.9,'attic_courtyard',.74)
    row('F8','East',12.2,23.0,5,25.3,26.9,'attic_east',.74)
    row('F8','South',1.7,15.8,7,25.3,26.9,'attic_inner_south',.74)
    for level,(z0,z1) in enumerate([(0.9,2.9),(4.1,6.2)]):
        row('ANNEX','East',-19.5,7.0,12,z0,z1,f'annex_east_{level}',.75,skip=(-7.1,) if level==0 else ())
        row('ANNEX','South',2.6,11.1,4,z0,z1,f'annex_south_{level}',.75)
    for fid,name,p1,p2 in [('F1','street',[-13.7,-16.1],[-13.7,-13.9]),('F1','north',[3.1,26.1],[4.9,26.1]),('ANNEX','annex',[13,-8],[13,-6.2])]:
        did=f'D_{name}'
        doors.append(WallOpening(id=did,kind='door',space_id=f'{fid}_merged',other_space_id=None,p1=p1,p2=p2,z=[0,2.9],state='unknown',
            source_refs=['UV street/courtyard views; entrance location is a developer estimate'],assumptions=['Entrance hypothesis for demonstration; exact threshold, dimensions and operating state unverified.']))
        evidence[did]={'basis':'inferred_entrance','description':'Plausible opening at ground level; not independently verified.'}
    geometry=CorrectedGeometry(schema_version='2',footprint_x=[-13.7,18.9],footprint_y=[-33.4,26.1],floors=floors,windows=windows,openings=doors,
        notes='Showcase-only developer-assisted interpretation of real textured mesh; no product-model run or GT. Source is in a local frame rotated 15 degrees about GLB Y.')
    source=build_source_bim(geometry,capability_profile='orthogonal_polygon')
    if source['validation']['status']!='pass':
        write(LOG/'failed_build.json',source['validation']); write(LOG/'failed_unbuilt.json',source['unbuilt_openings'])
        raise ValueError(source['validation'])
    source['assumptions']=[
        '展示用辅助推理模型：外形、楼层和窗组依据真实 GLB / UV 视图估计并规整；不代表产品独立自动生成。',
        '办公主体按八层表达，标准层高约3.2m；首层与退台顶层高度估计，屋顶设备体另列。',
        '各主楼楼层为合并空间，内部隔墙、核心筒、房间数量和内门未知；未凭空绘制房间布局。',
        '低层附属体保留一个合并空间，不把不确定的内部楼板当成已知；其与主楼接触面为抽象分界，非已证实体隔墙。',
        '窗组沿可见重复纹理估计，包含成组窗与简化间距；遮挡面和门位仍有推断，不能称逐窗准确还原。',
        '地面坡度、曲面屋盖、构造厚度和细部均简化；外壳几何一致性不代表真实建筑信息全部准确。',
    ]
    by_space={s['id']:s for s in source['spaces']}
    for s in source['spaces']:
        s['source_refs']=['input.glb','orthographic UV views',f'observations:{s["id"]}']
        s['representation']='merged_space' if s['id'].startswith(('F','ANNEX')) else 'roof_enclosure'
        s['evidence']=evidence[s['id']]
    virtual=[]
    for b in source['boundaries']:
        if b['geometry_type']=='wall' and any(('ANNEX' in b['space_id']) != ('ANNEX' in a) for a in b['adjacent_space_ids']):
            b['kind']='virtual'; b['source_refs']=['abstract junction of height-differing observed masses; physical partition unknown'];virtual.append(b['id'])
    for o in source['openings']:
        if o['kind']=='window':
            o['source_refs']=['input.glb',f'UV-view:{evidence[o["id"]]["view"]}']
            o['assumptions']=[evidence[o['id']]['description']]
    source['generation']={'method':'developer_assisted_textured_mass_showcase','model_calls':0,'solver_calls':0,
        'input_glb_sha256':hashlib.sha256((OUT/'input.glb').read_bytes()).hexdigest(),
        'source_frame':{'input_glb_up':'Y','source_up':'Z','u':'cos(15deg)*GLB.x+sin(15deg)*GLB.z','v':'sin(15deg)*GLB.x-cos(15deg)*GLB.z','z':'GLB.y'},
        'evidence':evidence,'virtual_junction_boundaries':virtual,
        'adapter':'Typed legacy Floor.footprint -> existing source kernel, solely inside this showcase script; production interfaces unchanged.',
        'unresolved':['True interior layout and vertical circulation','Window-by-window completeness and occluded facades','Ground slope, roof surfaces and exact floor heights','Entrances need independent verification']}
    source['source_model_sha256']=_digest({k:v for k,v in source.items() if k!='source_model_sha256'})
    display=source_view_geometry(source)
    write(OUT/'source_model.json',source);write(OUT/'display_geometry.json',display);write(OUT/'proposal.json',geometry.model_dump(mode='json'))
    write(OUT/'observations.json',evidence)
    title='Voimatalo · 真实贴图体量的辅助推理示意'
    (OUT/'bim_viewer.html').write_text(build_viewer_html(display,title=title))
    report={'generation_mode':'developer_assisted; not an autonomous product-model run','model_calls':0,'solver_calls':0,
        'counts':{'main_storeys':8,'merged_main_spaces':8,'annex_spaces':1,'roof_volumes':3,'window_groups':len(windows),'inferred_entrances':len(doors)},
        'source_validation':source['validation'],'virtual_junction_boundaries':virtual,
        'interpretation_scope':'Exterior and merged floor volumes; no true internal-room reconstruction',
        'input_format':{'type':'GLB/glTF 2.0','bytes':(OUT/'input.glb').stat().st_size,'embedded_texture':'JPEG'},
        'source_sha256':source['source_model_sha256']}
    write(OUT/'report.json',report);write(LOG/'build_report.json',report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
