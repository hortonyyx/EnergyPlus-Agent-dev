"""Select facade triangles and save metric orthographic UV observations."""
import base64,json,math
from pathlib import Path
import numpy as np
import trimesh
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[4]
LOG=Path(__file__).resolve().parent

def main():
    out=LOG/'facade_views';out.mkdir(exist_ok=False)
    mesh=trimesh.load(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/input.glb',force='mesh')
    a=math.pi/12;c,s=math.cos(a),math.sin(a)
    p=mesh.vertices
    q=np.c_[c*p[:,0]+s*p[:,2],s*p[:,0]-c*p[:,2],p[:,1]]
    triangles=q[mesh.faces];center=triangles.mean(axis=1)
    norm=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]); norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-9)
    # axis, plane coordinate, horizontal range, looking from positive side.
    planes={'west':(0,-13.7,[-33.4,26.1],False),'north':(1,26.1,[-13.7,18.9],True),
      'court_long':(0,.7,[-33.4,9.1],True),'court_short':(1,9.1,[.7,18.9],False),
      'east_short':(0,18.9,[9.1,26.1],True),'south_end':(1,-33.4,[-13.7,.7],False),
      'annex_east':(0,13,[-21.5,9.1],True)}
    original=(LOG/'input_views/observation_viewer.html').read_text()
    report={}
    with sync_playwright() as pw:
      browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
      for name,(axis,plane,hr,positive) in planes.items():
        along=1-axis
        mask=(abs(center[:,axis]-plane)<1.25)&(abs(norm[:,axis])>.55)&(center[:,along]>hr[0]-.8)&(center[:,along]<hr[1]+.8)
        faces=mesh.faces[mask]
        width=hr[1]-hr[0]+2; height=34
        w=round(width*32);h=round(height*32)
        html=original.replace("geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(bytes(data.indices)),1));", "geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(bytes('"+base64.b64encode(faces.astype('<u4').tobytes()).decode()+"')),1));")
        pagefile=out/(name+'.html');pagefile.write_text(html)
        ctx=browser.new_context(viewport={'width':w,'height':h},offline=True);page=ctx.new_page()
        page.goto(pagefile.as_uri());page.wait_for_function("document.getElementById('state').textContent.includes('已加载完整')")
        mid=(hr[0]+hr[1])/2
        target=[plane,16,-mid] if axis==0 else [mid,16,-plane]
        pos=target.copy();pos[0 if axis==0 else 2]+= (150 if positive else -150)*(1 if axis==0 else -1)
        page.evaluate('(v)=>{controls.enableDamping=false;camera.left=-v.width/2;camera.right=v.width/2;camera.top=v.height/2;camera.bottom=-v.height/2;camera.updateProjectionMatrix();camera.position.set(...v.pos);controls.target.set(...v.target);controls.update();}',dict(width=width,height=height,pos=pos,target=target))
        page.wait_for_timeout(400);page.screenshot(path=str(out/(name+'.png')))
        vals=center[mask,axis]; heights=center[mask,2]
        report[name]={'triangle_count':len(faces),'plane_median':float(np.median(vals)),'plane_q10_q90':np.quantile(vals,[.1,.9]).tolist(),
          'axis':axis,'plane_estimate':plane,'along_range':hr,'width_pixels':w,'height_pixels':h,'view_width_m':width,'view_height_m':height,
          'top_z_m':33,'bottom_z_m':-1,'along_pixel_direction':'increasing' if (axis==0 and positive) or (axis==1 and not positive) else 'decreasing'}
        ctx.close()
      browser.close()
    (out/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
