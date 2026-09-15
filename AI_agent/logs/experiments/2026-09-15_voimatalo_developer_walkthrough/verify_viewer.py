"""Offline actual artifact QA: registration, rendering, mode switching and rotation."""
import base64,json,sys
from pathlib import Path
import numpy as np,trimesh
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[4];run=Path(sys.argv[1]).resolve()
qa=run/(sys.argv[2] if len(sys.argv)>2 else 'browser_qa');qa.mkdir(exist_ok=False)
source=json.loads((run.parent/'candidate_02/source_model.json').read_text())
frame=source['mesh_frame'];mesh=trimesh.load(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/input.glb',force='mesh',process=False)
raw=mesh.vertices;zup=np.c_[raw[:,0],-raw[:,2],raw[:,1]]
a=np.radians(frame['yaw_degrees']);c,s=np.cos(a),np.sin(a)
expected=zup@np.array([[c,s,0],[-s,c,0],[0,0,1]])+frame['translation_m']
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 context=browser.new_context(viewport={'width':1500,'height':1000},offline=True)
 page=context.new_page();errors=[];external=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
 page.goto((run/'overlay.html').as_uri())
 page.wait_for_function("window.TRANSFER && document.body.dataset.texture==='ready'")
 modes={}
 for mode in ['input','overlay','bim']:
  page.locator('[data-transfer-mode='+mode+']').click();page.wait_for_timeout(300)
  modes[mode]=page.evaluate('''() => ({rawVisible:TRANSFER.rawMesh.visible,bimVisible:TRANSFER.root.visible,
    sourceHash:GEO.source_model.source_model_sha256,firstInputVertices:[...TRANSFER.rawMesh.geometry.attributes.position.array]})''')
  np.testing.assert_allclose(np.array(modes[mode]['firstInputVertices']).reshape(-1,3),expected,atol=3e-6,rtol=0)
  assert modes[mode]['sourceHash']==source['source_model_sha256']
  modes[mode].pop('firstInputVertices')
  page.screenshot(path=str(qa/(mode+'.png')))
 assert modes['input']['rawVisible'] and not modes['input']['bimVisible']
 assert modes['overlay']['rawVisible'] and modes['overlay']['bimVisible']
 assert not modes['bim']['rawVisible'] and modes['bim']['bimVisible']
 before=page.evaluate('TRANSFER.camera.position.toArray()')
 page.mouse.move(1050,550);page.mouse.down();page.mouse.move(1210,650,steps=15);page.mouse.up();page.wait_for_timeout(300)
 after=page.evaluate('TRANSFER.camera.position.toArray()');assert not np.allclose(before,after)
 page.locator('#floorSel').select_option('2');page.wait_for_timeout(250)
 assert page.locator('#floorSel').input_value()=='2'
 page.locator('#explode').evaluate('(el)=>el.value=1');page.locator('#explode').dispatch_event('input')
 page.screenshot(path=str(qa/'rotated_floor.png'))
 page.goto((run/'observations.html').as_uri());page.wait_for_timeout(300)
 image_count=page.locator('img').count();assert image_count==10
 assert page.locator('img').evaluate_all('(xs)=>xs.every(x=>x.complete && x.naturalWidth>0)')
 page.screenshot(path=str(qa/'observations.png'))
 browser.close()
assert not errors and not external
(qa/'report.json').write_text(json.dumps({'source_hash':source['source_model_sha256'],'modes':modes,'rotation_verified':True,'floor_selection_verified':True,'exploded_view_exercised':True,'frame_vertex_mapping_verified':True,'verified_input_vertices':len(expected),'maximum_allowed_absolute_error_m':3e-6,'observation_image_count':image_count,'errors':errors,'external_requests':external},indent=2)+'\n')
print('Offline source/raw/overlay, exact frame mapping, rotation, floor and observation images passed')
