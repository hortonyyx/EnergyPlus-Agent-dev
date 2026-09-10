"""Presentation-only camera/visibility setup; the source viewers are unchanged."""
import importlib.util
import json
from pathlib import Path
import tempfile
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'showcase/2026-09-11-research-report/assets'
spec=importlib.util.spec_from_file_location('capture',HERE/'assets_capture/capture_assets.py')
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

with tempfile.TemporaryDirectory(prefix='bim-slide-stills-') as temp, sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1600,'height':900},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://**/*',lambda r:r.abort())
    page.route('https://**/*',lambda r:r.abort())
    for name in ('sm25-model','voimatalo-model','voimatalo-input'):
        content=helper.PAGES[name].read_text()
        content=content.replace('const scene = new THREE.Scene();','const scene = window.captureScene = new THREE.Scene();')
        content=content.replace('const scene=new THREE.Scene();','const scene=window.captureScene=new THREE.Scene();')
        content=content.replace('const root=new THREE.Group();','const root=window.captureRoot=new THREE.Group();')
        local=Path(temp)/f'{name}.html'
        local.write_text(content)
        page.goto(local.as_uri())
        page.wait_for_timeout(1200)
        if name=='sm25-model':
            page.locator('#explode').evaluate("el=>{el.value='0.32';el.dispatchEvent(new Event('input'));}")
        helper.hide_ui(page)
        page.evaluate('''() => {
          const scene=window.captureScene, root=window.captureRoot;
          scene.background=new THREE.Color(0xf8f9f7);
          if(root) scene.children.forEach(child=>{if(child!==root&&!child.isLight)child.visible=false;});
        }''')
        helper.nudge_view(page,-0.08,0.02)
        box=page.locator('canvas').bounding_box()
        page.mouse.move(800,450)
        for _ in range(10 if name=='sm25-model' else 11 if name=='voimatalo-model' else 13):
            page.mouse.wheel(0,-100)
        page.wait_for_timeout(400)
        if name=='sm25-model':
            page.evaluate('''() => {
              window.captureRoot.traverse(o=>{
                if(o.userData && o.userData.kind==='surface' && /Ceiling|Roof/.test(o.userData.type)) o.visible=false;
              });
            }''')
        page.wait_for_timeout(250)
        page.screenshot(path=str(OUT/f'{name}.png'))
    browser.close()
    assert not errors,errors
(HERE/'clean_stills_report.json').write_text(json.dumps({'source_viewers_modified':False,'display_only':'Hidden UI, grid and axes; sm25 floors exploded 0.32; ceiling/roof visibility for illustration only. White background.','page_errors':errors},indent=2)+'\n')
