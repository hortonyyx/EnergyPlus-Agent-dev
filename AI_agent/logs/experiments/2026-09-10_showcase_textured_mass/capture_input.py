"""Render measured, rotated views of the existing textured mesh; no BIM answers."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / 'input_views'

def main():
    OUT.mkdir(exist_ok=False)
    original = ROOT / 'case_tests/textured_mass/single_buildings/voimatalo/viewer.html'
    html = original.read_text()
    html = html.replace('const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,0.1,2000);',
        'const camera=new THREE.OrthographicCamera(-48,48,36,-36,0.1,2000);')
    html = html.replace('scene.add(new THREE.Mesh(geometry,material));',
        'const inputMesh=new THREE.Mesh(geometry,material);inputMesh.rotation.y=Math.PI/12;scene.add(inputMesh);')
    html = html.replace('</style>', 'aside{display:none}</style>')
    local = OUT / 'observation_viewer.html'
    local.write_text(html)
    views = {
        'courtyard': [90,62,95], 'street': [-80,50,-90],
        'east': [150,15,0], 'west': [-150,15,0],
        'north': [0,15,-150], 'south': [0,15,150],
        'top': [0,150,0.01],
    }
    report={'input':str(original.relative_to(ROOT)), 'rotation_y_degrees':15,
            'frame':'local u east along short facade; v along long wing; y is height; orthographic 96x72m', 'views':{}}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        ctx=browser.new_context(viewport={'width':1600,'height':1200},offline=True)
        page=ctx.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(local.as_uri()); page.wait_for_function("document.getElementById('state').textContent.includes('已加载完整')")
        page.evaluate('controls.enableDamping=false')
        for name,position in views.items():
            page.evaluate('(p)=>{camera.position.set(...p);controls.target.set(0,15,0);camera.up.set(0,1,0);controls.update();}',position)
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUT/(name+'.png')))
            report['views'][name]={'position':position,'target':[0,15,0]}
        report['errors']=errors; browser.close()
    (OUT/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not errors, errors
    print(json.dumps(report))

if __name__=='__main__': main()
