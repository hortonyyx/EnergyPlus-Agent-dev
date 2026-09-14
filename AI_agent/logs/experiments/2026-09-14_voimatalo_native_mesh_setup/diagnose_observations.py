"""Post-run geometric diagnostics, never supplied as observations to the agent."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
run=Path(sys.argv[1]).resolve()
m=trimesh.load(run/'assets/input.glb',force='mesh',process=False)
v=np.c_[m.vertices[:,0],-m.vertices[:,2],m.vertices[:,1]]
t=v[m.faces];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(cross,axis=1);area=norm/2
normal=cross/np.maximum(norm[:,None],1e-15)
mask=(abs(normal[:,2])<.15)&(area>.1)
align=(-np.rad2deg(np.arctan2(normal[mask,1],normal[mask,0])))%90
hist,edges=np.histogram(align,bins=np.arange(0,91),weights=area[mask])
peaks=np.argsort(hist)[-6:][::-1]
views=[]
for p in sorted((run/'mesh_observations').glob('mesh_*.json')):
 d=json.loads(p.read_text());mapping=d['pixel_center_mapping'];ratio=mapping['pixel_width_m']/mapping['pixel_height_m']
 views.append({'observation':p.stem,'yaw':d['source_coordinate_transform']['yaw_degrees_counterclockwise_about_positive_z'],
               'pixel_width_m':mapping['pixel_width_m'],'pixel_height_m':mapping['pixel_height_m'],'pixel_aspect_ratio':ratio})
result={'diagnostic_only':True,'normal_filter':{'max_abs_z':.15,'min_triangle_area_m2':.1},
 'dominant_vertical_surface_alignment_bins':[{'yaw_interval_degrees':[float(edges[i]),float(edges[i+1])],'triangle_area_m2':float(hist[i])} for i in peaks],
 'views':views,'interpretation':'Area-weighted mesh normals support an approximate alignment, not surveyed BIM truth. Unequal horizontal/vertical metres per pixel distort apparent angles even though coordinate mapping remains numerically explicit; view-based angle guessing needs scrutiny.'}
(run/'observation_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
