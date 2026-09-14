"""Check the probe's selected primary edge points against the original mesh faces."""
from pathlib import Path
import json,math,sys
import numpy as np,trimesh
run=Path(sys.argv[1]).resolve();m=trimesh.load(run/'assets/input.glb',force='mesh',process=False)
v=np.c_[m.vertices[:,0],-m.vertices[:,2],m.vertices[:,1]];t=v[m.faces];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-15)
records=[];heading_checks=[]
for row in map(json.loads,(run/'tools.jsonl').read_text().splitlines()):
 if row['action']!='measure_mesh_pixels':continue
 d=row['data'];result=d['result']
 if 'first_two_plan_geometry' in result:
  a,b=[r['world_xyz'] for r in result['queries'][:2]];delta=[y-x for x,y in zip(a,b)];heading=math.degrees(math.atan2(delta[1],delta[0])) if math.hypot(*delta[:2])>1e-7 else None
  assert result['first_two_plan_geometry']['delta_xyz_m']==delta
  assert result['first_two_plan_geometry']['horizontal_heading_degrees']==heading
  heading_checks.append({'observation':d['observation'],'heading_matches_points':True})
 if d['pixels'][:3]==[[517,148],[460,430],[402,715]]:
  for p in result['queries'][:3]:
   records.append({**p,'triangle_normal_in_yaw0_frame':n[p['face_id']].tolist(),
     'diagnostic_u_at_yaw15_m':math.cos(math.pi/12)*p['world_xyz'][0]-math.sin(math.pi/12)*p['world_xyz'][1]})
assert len(records)==3
output={'primary_points':records,'heading_replay':heading_checks,
 'diagnostic_frame_basis':'15 degrees is an approximate diagnostic direction from area-weighted vertical mesh normals, not input to the model or surveyed BIM truth.',
 'same_wall_edge_established':False,
 'interpretation':'Sampled triangles span almost horizontal and sloping surfaces; three nearly collinear projected pixels alone do not prove one physical parapet/wall edge. Their u coordinates in the dominant-wall diagnostic frame drift about 3.59m over the baseline. The 11.4 degree answer remains unverified and was not applied to any BIM.'}
(run/'selected_point_diagnosis.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'heading_checks':len(heading_checks),'diagnostic_u_drift_m':records[-1]['diagnostic_u_at_yaw15_m']-records[0]['diagnostic_u_at_yaw15_m'],'same_wall_edge_established':False}))
