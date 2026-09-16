"""Developer-selected roof simplifications with raw section and aperture evidence."""
from pathlib import Path
import copy, hashlib, json, sys
import numpy as np
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OLD=HERE.parent/'2026-09-15_voimatalo_developer_walkthrough'
sys.path.insert(0,str(ROOT))
from src.agent.geometry.mesh_observation import MeshObservation

def write(path,value):
    assert not path.exists(), 'Use a new output; preserve frozen decisions'
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

plan=json.loads((OLD/'case_plan.json').read_text())
plan['parent_plan_sha256']=hashlib.sha256((OLD/'case_plan.json').read_bytes()).hexdigest()
plan['inherited_evidence_root']=str(OLD.relative_to(ROOT))
plan['shell'].update(attic_west=-11.6,attic_north=24.0,attic_south_end=-31.5,attic_west_north=-12.8)
plan['attic_outline']=[[-11.6,-31.5],[-.1,-31.5],[-.1,9.5],[4.6,9.5],[4.6,8.8],[18.5,8.8],
                       [18.5,24],[-12.8,24],[-12.8,16],[-11.6,16]]
plan['roof_volumes']={
 'ROOF':{'rectangles':[[-11,-31.3,.8,-20.8],[-11,-20.8,-.1,10],[-10.8,10,16.8,23.6],[-12.6,16,-10.8,23.6]],
         'z':[27.8,28.6], 'evidence':'roof/sections.json z27.9 traces and roof/top.png. Curved roof simplified to low envelope; footprint approximate, top is a representative level, not a surveyed flat roof.'},
 'ROOF_N_BASE':{'rectangles':[[-6.8,16,16.3,21.3],[-4,10,6.5,16],[6.5,12.7,16.3,16]],
         'z':[28.6,31.0], 'evidence':'roof/sections.json z29 and z30.5 plus courtyard/top texture: raised northern roof main mass. Contact to lower envelope is logical/open, no slab asserted.'},
 'ROOF_N':{'rectangles':[[-3.5,10,6.5,16.5]], 'z':[31.0,32.1],
         'evidence':'roof/sections.json z31.5 northern contour and original courtyard pixels. Approximate raised roof box, not an occupied storey; base logical/open.'},
 'ROOF_S':{'rectangles':[[-8,-28.5,.8,-20.8]], 'z':[28.6,31.6],
         'evidence':'roof/south_box.png and sections z29/30.5/31.5. Southern raised mass formerly missing beneath the stack. Rounded/tapered cap simplified as prism, no internal room inferred.'},
 'ROOF_STACK':{'rectangles':[[-6.5,-25.5,-5,-23.3]], 'z':[31.6,34.2],
         'evidence':'roof/sections.json z33 contour and roof/south_box.png. Stack outline/height regularised; interior function unknown, logical base open to underlying envelope.'},
}
plan.pop('roof_primary_rectangles');plan.pop('roof_primary_top');plan.pop('roof_upper_volumes')
plan['roof_representation']={'components_not_rooms':True,'horizontal_contacts':'explicit reciprocal open regions; exposed lower roof stays physical',
 'limits':'Piecewise prism approximation of roof envelope, no true curvature or roof thickness. These five parts are NOT five measured rooms or new usable floors.'}
plan['assumptions'][7]='屋顶按原剖切规整为较低长翼、南北凸起和烟囱等五个屋盖几何部件；不是五个实际房间。弧面/局部坡度用棱柱近似，部件相接的水平界面显式双面敞开，外露屋盖保留；27.8m与主楼之间的顶板仍是方案假设。'
plan['assumptions'].append('退台西面按北端与长翼分别规整，北面及南端参考26.5m原截线；西北端两组玻璃和内院角部三组竖窗按新原图像素框补入。其余暗带/窄槽不按重复规则凭空填窗。')

mesh=MeshObservation(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/input.glb')
observations=[]
for name,facade,plane,boxes in [
 ('west','West','attic_west_north',[[208,166,269,210],[282,164,349,211]]),
 ('attic_corner','South','court_corner_y',[[170,200,241,446],[298,213,370,448],[416,211,487,448]])]:
    prefix=HERE/'roof'/name
    meta=json.loads(prefix.with_suffix('.json').read_text());m=meta['pixel_center_mapping']
    origin,dx,dy=[np.array(m[k]) for k in ('top_left_pixel_center_plane_xyz','column_step_world_xyz','row_step_world_xyz')]
    axis=int(np.argmax(abs(dx)));picture=Image.open(prefix.with_suffix('.png'));d=ImageDraw.Draw(picture)
    for i,(left,top,right,bottom) in enumerate(boxes,1):
        a=origin+(left-.5)*dx+(top-.5)*dy;b=origin+(right-.5)*dx+(bottom-.5)*dy
        sid=f'attic_{name}_{i:02}'
        queries=mesh.pixel_query(prefix,[[int((left+right)/2),int((top+bottom)/2)]])['queries']
        assert queries[0]['hit']
        row={'id':sid,'view':name,'facade':facade,'plane_key':plane,'kind':'window','pixel_box':[left,top,right,bottom],
             'pixel_box_convention':'left/top inclusive; right/bottom exclusive','span_m':sorted([float(a[axis]),float(b[axis])]),
             'z_m':sorted([float(a[2]),float(b[2])]),'hit_check':queries,
             'source_refs':[str(prefix.with_suffix('.png').relative_to(ROOT)),str(prefix.with_suffix('.json').relative_to(ROOT))],
             'basis':'developer observed visible glazing group; orthographic pixel bounds; regularised host plane',
             'notes':'Glass category is developer judgement; boundaries and pane divisions approximate. Depth evidence validates host only.'}
        observations.append(row);d.rectangle([left,top,right,bottom],outline='#ffb000',width=2);d.text((left,top-12),sid,fill='#ffb000')
    picture.save(HERE/'roof'/(name+'_apertures.png'))
plan['additional_openings']+=observations
pending=[
 {'id':'attic_west_partial_north_edge','decision':'unresolved','evidence':'roof/west.png left end of glazing band','reason':'Partial/sloped edge at y24 near changing north boundary; do not clip into a complete rectangular window.'},
 {'id':'attic_west_long_dark_band','decision':'unresolved','evidence':'roof/west.png and initial_window_queries.json','reason':'Dark metal/small glazing interpretation insufficient to enumerate openings. No uniform blank-wall or all-window inference.'},
 {'id':'attic_north_dark_band','decision':'unresolved','evidence':'roof/north.png','reason':'Dark continuous metal/occluded strip, no reliable window boundaries.'},
 {'id':'roof_court_short_slots','decision':'simplified_unclassified_surface_details','evidence':'roof/court_short.png','reason':'Small repeated slots in metal envelope may be vents; not treated as building windows without support. Their airflow is not modelled.'},
 {'id':'roof_south_slots','decision':'simplified_unclassified_surface_details','evidence':'roof/south_box.png','reason':'Small dark marks in metal cap are not established windows; stack/curvature represented by envelope masses only.'},
 {'id':'attic_corner_small_marks','decision':'unresolved','evidence':'roof/attic_corner.png right of three tall windows','reason':'Small dark marks are blurry and partly cropped, no complete opening extents.'},
]
write(HERE/'roof'/'opening_decisions.json',{'openings':observations,'unresolved_or_simplified':pending})
write(HERE/'roof_plan.json',plan)
print('Saved revised roof/attic plan with five additional windows')
