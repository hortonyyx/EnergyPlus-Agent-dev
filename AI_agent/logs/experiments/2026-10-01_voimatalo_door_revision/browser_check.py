"""Real viewer checks for paired-door inspection and inference provenance."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8765/AI_agent/logs/experiments/2026-10-01_voimatalo_door_revision/result_02/index.html'


def main():
    output = HERE / 'browser_qa'; output.mkdir(exist_ok=True)
    result = {'errors': [], 'checks': [], 'url': URL}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/tmp/ep-bim-browser-qa/browsers/chromium-1234/chrome-linux64/chrome',
                                   headless=True, args=['--no-sandbox', '--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width':1600,'height':1050})
        page.on('pageerror', lambda e: result['errors'].append(str(e)))
        assert page.goto(URL,wait_until='load').status == 200
        page.wait_for_function('window.REVISION && document.body.dataset.texture === "ready"')
        assert page.evaluate('REVISION.stats().floor') == 'F3'
        page.screenshot(path=str(output/'standard.png'))
        result['checks'].append({'standard_floor':page.evaluate('REVISION.stats()')})
        page.select_option('#colorBy','surface')
        point = page.evaluate('''()=>{
          const m=REVISION.doors.find(m=>m.visible&&m.userData.sourceId==='D_F3_E_03_F3_hall');
          m.geometry.computeBoundingBox();const center=m.geometry.boundingBox.getCenter(new THREE.Vector3());
          TRANSFER.controls.target.copy(center);TRANSFER.camera.position.copy(center.clone().add(new THREE.Vector3(10,-10,18)));
          TRANSFER.controls.update();TRANSFER.camera.updateMatrixWorld();
          const v=center.clone().project(TRANSFER.camera),r=TRANSFER.renderer.domElement.getBoundingClientRect();
          return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};
        }''')
        page.wait_for_timeout(200)
        page.mouse.click(point['x'],point['y'])
        text=page.locator('#sel').inner_text()
        assert '隔墙双侧成对' in text and '0.25 m' in text and '0.90 m' in text, text
        result['checks'].append({'actual_door_click':text})
        page.screenshot(path=str(output/'door_selection.png'))
        for view in ['whole','annex2','roof']:
            page.click(f'[data-review-view="{view}"]');page.wait_for_timeout(200)
            page.screenshot(path=str(output/f'{view}.png'))
            result['checks'].append({view:page.evaluate('REVISION.stats()')})
        for mode in ['input','overlay']:
            page.click(f'[data-transfer-mode="{mode}"]')
            assert page.evaluate('document.body.dataset.mode')==mode
        result['checks'].append({'texture_overlay_controls':'pass'})
        for href in ['../candidate_02/source_model.json','../validation.json','rooms.csv','doors.html','F3_doors.svg']:
            assert page.request.get(URL.rsplit('/',1)[0]+'/'+href).status==200
        plan=browser.new_page(viewport={'width':1250,'height':1200})
        plan.goto(URL.rsplit('/',1)[0]+'/doors.html',wait_until='load')
        assert '19组成对房门' in plan.locator('body').inner_text()
        assert plan.locator('svg g').count()==41
        plan.screenshot(path=str(output/'door_plan.png'))
        result['checks'].append({'source_plan_with_41_room_entrances':'pass'})
        assert not result['errors'],result['errors']
        browser.close()
    result['status']='pass'
    (output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'pass','errors':result['errors'],'checks':len(result['checks'])}))


if __name__ == '__main__':
    main()
