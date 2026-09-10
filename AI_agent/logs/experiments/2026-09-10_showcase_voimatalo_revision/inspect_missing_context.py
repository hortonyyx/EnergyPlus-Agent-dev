"""Inspect a small part of the label-free parent tile, without changing inputs."""
import json, math, sys
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from case_tests.textured_mass.prepare_single_building import write_offline_viewer,mask_texture_to_selected_faces

def main():
    out=Path(__file__).resolve().parent/'context';out.mkdir(exist_ok=False)
    case=ROOT/'case_tests/textured_mass/single_buildings/voimatalo'
    selection=json.loads((case/'selection.json').read_text());inspection=json.loads((case/'inspection.json').read_text())
    mesh=trimesh.load(ROOT/selection['source_tile']['sanitised_input_path'],force='mesh',process=False)
    origin=selection['source_tile']['input_transform']['origin_original']
    footprint=Polygon(selection['footprint']['helsinki_local_xy_m'])
    cx,cy=footprint.centroid.coords[0];base=inspection['original_base_elevation_m_n2000_estimate']
    p=mesh.vertices
    x=p[:,0]+origin[0]-cx; zz=p[:,2]-origin[1]+cy
    c,s=math.cos(math.pi/12),math.sin(math.pi/12)
    u=c*x+s*zz;v=s*x-c*zz;z=p[:,1]+origin[2]-base
    q=np.c_[u,v,z];tc=q[mesh.faces].mean(axis=1)
    mask=(tc[:,0]>-22)&(tc[:,0]<32)&(tc[:,1]>-46)&(tc[:,1]<37)&(tc[:,2]>-1)
    # Keep original UV and complete triangles; unlike the single-building crop,
    # this evidence includes a narrow context strip that can reveal occlusion.
    mesh.vertices=np.c_[u,z,-v]
    cropped=mesh.submesh([np.flatnonzero(mask)],append=True,repair=False)
    tex,_,_=mask_texture_to_selected_faces(cropped)
    if hasattr(cropped.visual.material,'baseColorTexture'):cropped.visual.material.baseColorTexture=tex
    else:cropped.visual.material.image=tex
    viewer=out/'context_viewer.html';write_offline_viewer(cropped,viewer,'Voimatalo 局部裁剪上下文（仅供判断遮挡）')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1500,'height':1100});page.goto(viewer.as_uri())
        page.wait_for_function("document.getElementById('state').textContent.includes('已加载')")
        page.evaluate("document.querySelector('aside').style.display='none';controls.enableDamping=false")
        for name,pos,target in [('courtyard',[88,65,95],[0,13,3]),('top',[0,125,3.01],[0,0,3]),('south',[5,30,125],[0,13,25]),('east',[120,32,-10],[8,13,-12])]:
            page.evaluate('(v)=>{camera.position.set(...v.pos);controls.target.set(...v.target);controls.update()}',{'pos':pos,'target':target})
            page.wait_for_timeout(450);page.screenshot(path=str(out/(name+'.png')))
        browser.close()
    # Render input is disposable; keep source code, screenshots and summary.
    viewer.unlink()
    summary={'source':selection['source_tile']['sanitised_input_path'],'faces':len(cropped.faces),'context_only':True,'labels_read':False,'modelled_environment':False,'frame':'u=cos15*x+sin15*z; v=sin15*x-cos15*z; height=GLB.y','bounds_uv_m':[[-22,-46],[32,37]]}
    (out/'report.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(summary)

if __name__=='__main__':main()
