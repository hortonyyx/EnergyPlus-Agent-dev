"""Load an unchanged candidate viewer and select a specified source room in a temporary copy."""
import argparse
import json
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('space_id')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    viewer = (args.candidate / 'viewer.html').resolve()
    source = json.loads((args.candidate / 'source_model.json').read_text())
    room = next(s for s in source['spaces'] if s['id'] == args.space_id)
    xs, ys = zip(*room['polygon'])
    target = [min(xs), (min(ys) + max(ys)) / 2, room['z_floor'] + .5]
    result = {'scope': 'Browser rendering and real canvas selection only; no source changes or architecture acceptance',
              'source_model_sha256': source['source_model_sha256'], 'source_space_id': room['id'],
              'source_floor_id': room['floor_id'], 'errors': [], 'original_viewer_modified': False}
    hook = 'window.QA={camera,controls,renderer,pick,zoneFloor,SOURCE_MAP};'
    instrumented = viewer.read_text().replace('(function loop(){', hook + '\n(function loop(){', 1)
    with tempfile.TemporaryDirectory(prefix='partial_result_browser_') as tmp, sync_playwright() as p:
        path = Path(tmp) / 'instrumented.html'; path.write_text(instrumented)
        browser = p.chromium.launch(
            executable_path='/tmp/ep-bim-browser-qa/browsers/chromium-1234/chrome-linux64/chrome',
            headless=True, args=['--no-sandbox', '--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1600, 'height': 1050})
        page.on('pageerror', lambda e: result['errors'].append(str(e)))
        page.goto(viewer.as_uri()); page.wait_for_function('document.querySelector("canvas")')
        page.wait_for_timeout(300)
        page.screenshot(path=str(args.output / 'whole_building.png'))
        page.goto(path.as_uri()); page.wait_for_function('window.QA')
        mapping = page.evaluate('''sid=>{
          const entry=Object.entries(QA.SOURCE_MAP.zones||{}).find(([z,s])=>s===sid);
          if(!entry) throw new Error('Source room not mapped');
          const index=QA.zoneFloor[entry[0]], option=document.querySelector('#floorSel').options[index+1];
          return {zone:entry[0],index,label:option.textContent,value:option.value};
        }''', room['id'])
        page.select_option('#floorSel', mapping['value']); page.select_option('#colorBy', 'zone')
        page.locator('aside details').evaluate_all('(els)=>els.forEach(e=>e.open=false)')
        page.check('#enZ')
        page.locator('#posZ').evaluate('(e,z)=>{e.value=z;e.dispatchEvent(new Event("input"));}', room['z_floor'] + 1.5)
        point = page.evaluate('''xyz=>{
          const t=new THREE.Vector3(...xyz); QA.controls.target.copy(t);
          QA.camera.position.set(t.x-55,t.y,t.z+12); QA.controls.update();QA.camera.updateMatrixWorld();
          const v=t.clone().project(QA.camera),r=QA.renderer.domElement.getBoundingClientRect();
          return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};
        }''', target)
        hit = page.evaluate('(p)=>QA.pick({clientX:p.x,clientY:p.y})?.object.userData', point)
        page.mouse.click(point['x'], point['y'])
        result.update(floor_mapping=mapping, click_hit=hit, selection_text=page.locator('#sel').inner_text())
        result['selected_expected_space'] = bool(hit and hit.get('zone') == mapping['zone'])
        assert result['selected_expected_space'] and not result['errors'], result
        result['floor_label_matches_source_id'] = mapping['label'].startswith(room['floor_id'] + ' ')
        result['status'] = 'pass' if result['floor_label_matches_source_id'] else 'partial_floor_label_mismatch'
        page.screenshot(path=str(args.output / 'section_room_selected.png'))
        browser.close()
    (args.output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'errors': result['errors'], 'selected': result['selected_expected_space']}))


if __name__ == '__main__':
    main()
