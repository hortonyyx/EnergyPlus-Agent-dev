"""Post-run raw-surface distances: geometric diagnostic, not surveyed facade truth."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[4]
run=Path(sys.argv[1]).resolve()
scene=trimesh.load(run/'assets/input.glb',force='scene',process=False)
triangles=[]
for name in scene.graph.nodes_geometry:
 transform,geometry_name=scene.graph[name]
 geometry=scene.geometry[geometry_name]
 v=trimesh.transform_points(geometry.vertices,transform)
 v=np.column_stack((v[:,0],-v[:,2],v[:,1]))
 triangles.append(v[geometry.faces])
t=np.concatenate(triangles)
cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(cross,axis=1)
n=np.divide(cross,norm[:,None],out=np.zeros_like(cross),where=norm[:,None]>1e-12)
centres=t.mean(axis=1)
# Same physical original-mesh subset for every candidate; independent of its yaw.
selected=(norm>1e-9)&(np.abs(n[:,2])<=np.sin(np.radians(10)))&(centres[:,2]>=8)&(centres[:,2]<=22)
p=centres[selected];weights=norm[selected]/2
trace_angles=np.degrees(np.arctan2(n[selected,0],-n[selected,1]))
seed=json.loads((run/'seed/source_model.json').read_text())
frames=[('seed_explicit_old_statement',seed,{'yaw_degrees':8,'translation_m':[0,0,0]})]
for path in sorted(run.glob('candidate_*/source_model.json')):
 source=json.loads(path.read_text())
 if 'mesh_frame' in source:frames.append((path.parent.name,source,source['mesh_frame']))

def weighted_quantile(v,w,q):
 order=np.argsort(v);v=v[order];w=w[order]
 return float(v[min(len(v)-1,np.searchsorted(np.cumsum(w),q*w.sum()))])

results=[]
for name,source,frame in frames:
 a=np.radians(frame['yaw_degrees']);c,s=np.cos(a),np.sin(a)
 x=p@np.array([[c,s,0],[-s,c,0],[0,0,1]])+frame['translation_m']
 distances=np.full(len(x),np.inf)
 for b in source['boundaries']:
  if b['geometry_type']!='wall' or b.get('adjacent_space_ids'):continue
  v=np.array(b['vertices']);zmin,zmax=v[:,2].min(),v[:,2].max()
  unique=np.unique(v[:,:2],axis=0)
  if len(unique)!=2:continue
  p0,p1=unique;edge=p1-p0;length2=edge@edge
  fraction=np.clip((x[:,:2]-p0)@edge/length2,0,1)
  d=np.linalg.norm(x[:,:2]-(p0+fraction[:,None]*edge),axis=1)
  eligible=(x[:,2]>=zmin)&(x[:,2]<=zmax)
  distances[eligible]=np.minimum(distances[eligible],d[eligible])
 finite=np.isfinite(distances)
 axis_error=np.abs((trace_angles+frame['yaw_degrees']+45)%90-45)
 results.append({'weighted_median_axis_error_degrees':weighted_quantile(axis_error,weights,.5),'candidate':name,'mesh_frame':frame,'sample_count':len(p),
  'matched_height_sample_count':int(finite.sum()),'matched_surface_area_m2':float(weights[finite].sum()),
  'weighted_mean_distance_m':float(np.average(distances[finite],weights=weights[finite])),
  'weighted_median_distance_m':weighted_quantile(distances[finite],weights[finite],.5),
  'weighted_p90_distance_m':weighted_quantile(distances[finite],weights[finite],.9)})
report={'scope':'One-sided distance from original near-vertical triangle centroids at raw Z 8..22m to candidate exterior wall segments at matching heights. Area weighted. Original subset fixed before candidate transforms.',
 'not_ground_truth':True,'limitations':['Photogrammetric noise and exterior relief remain; not survey accuracy.', 'No source-to-mesh completeness measure; missing source surfaces/windows/interiors are not certified.', 'The seed +8 degree/zero translation frame is transcribed from its old explicit assumption for evaluation only; not a new angle supplied to the model.'],
 'results':results}
(run/'placement_diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['candidate','weighted_mean_distance_m','weighted_median_distance_m','weighted_p90_distance_m','weighted_median_axis_error_degrees']} for r in results]))
