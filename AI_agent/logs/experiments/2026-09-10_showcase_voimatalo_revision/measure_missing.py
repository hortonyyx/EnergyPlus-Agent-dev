"""Measure and view the facade projection omitted by the coarse footprint crop."""
import json, math, sys
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from case_tests.textured_mass.prepare_single_building import write_offline_viewer,mask_texture_to_selected_faces

def main():
    out=Path(__file__).resolve().parent/'missing_measurements';out.mkdir(exist_ok=False)
    case=ROOT/'case_tests/textured_mass/single_buildings/voimatalo'
    selection=json.loads((case/'selection.json').read_text());inspection=json.loads((case/'inspection.json').read_text())
    mesh=trimesh.load(ROOT/selection['source_tile']['sanitised_input_path'],force='mesh',process=False)
    origin=selection['source_tile']['input_transform']['origin_original'];cx,cy=Polygon(selection['footprint']['helsinki_local_xy_m']).centroid.coords[0]
    base=inspection['original_base_elevation_m_n2000_estimate'];p=mesh.vertices
    x=p[:,0]+origin[0]-cx;zz=p[:,2]-origin[1]+cy;c,s=math.cos(math.pi/12),math.sin(math.pi/12)
    u=c*x+s*zz;v=s*x-c*zz;z=p[:,1]+origin[2]-base;q=np.c_[u,v,z]
    tri=q[mesh.faces];tc=tri.mean(axis=1);n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=np.linalg.norm(n,axis=1)/2;n/=np.maximum(2*area[:,None],1e-9)
    strip=(tc[:,0]>-.5)&(tc[:,0]<8)&(tc[:,1]>-30.5)&(tc[:,1]<-20)
    flat=strip&(abs(n[:,0])>.8)&(tc[:,2]>6)&(tc[:,2]<24)
    bins=np.arange(-.5,8.25,.25);weights,edges=np.histogram(tc[flat,0],bins=bins,weights=area[flat])
    peaks=sorted(zip(weights,edges[:-1]),reverse=True)[:8]
    summary={'projected_facade_u_area_peaks':[{'u_bin_m':[float(b),float(b+.25)],'triangle_area_m2':float(a)} for a,b in peaks], 'selection_uv_m':[[-.5,-30.5],[8,-20]],'storey_window_evidence':'inspect core_front and core_side images; no semantic labels used'}
    mesh.vertices=np.c_[u,z,-v];cropped=mesh.submesh([np.flatnonzero(strip)],append=True,repair=False)
    tex,_,_=mask_texture_to_selected_faces(cropped)
    if hasattr(cropped.visual.material,'baseColorTexture'):cropped.visual.material.baseColorTexture=tex
    else:cropped.visual.material.image=tex
    viewer=out/'viewer.html';write_offline_viewer(cropped,viewer,'凸出竖向体量的原始网格与贴图')
    html=viewer.read_text().replace('new THREE.PerspectiveCamera(45,innerWidth/innerHeight,0.1,2000)','new THREE.OrthographicCamera(-7,7,17,-17,0.1,2000)')
    viewer.write_text(html)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':700,'height':1700});page.goto(viewer.as_uri());page.wait_for_function("document.getElementById('state').textContent.includes('已加载')")
        page.evaluate("document.querySelector('aside').style.display='none';controls.enableDamping=false")
        for name,pos,target in [('core_front',[100,16,25],[2,16,25]),('core_side',[2,16,125],[2,16,25])]:
            page.evaluate('(v)=>{camera.position.set(...v.pos);controls.target.set(...v.target);controls.update()}',{'pos':pos,'target':target})
            page.wait_for_timeout(450);page.screenshot(path=str(out/(name+'.png')))
        browser.close()
    viewer.unlink();(out/'report.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))

if __name__=='__main__':main()
