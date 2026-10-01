"""Real common-viewer regression for clipped surfaces intercepting door clicks."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.execution.source_proposal import export_source_proposal
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def main():
    output = HERE / 'browser_qa'; output.mkdir(exist_ok=True)
    proposal = {'geometry': {'schema_version': '2', 'footprint_x': [0, 6], 'footprint_y': [0, 6],
        'floors': [{'name': 'F1', 'z_floor': 0, 'ceiling_height': 3, 'cells': [
            {'id': 'hall', 'x': [0, 3], 'y': [0, 6], 'role': 'corridor'},
            {'id': 'room', 'x': [3, 6], 'y': [0, 6], 'role': 'office'}]}],
        'windows': [], 'openings': [{'id': 'door', 'kind': 'door', 'space_id': 'hall',
            'other_space_id': 'room', 'p1': [3, 1], 'p2': [3, 2], 'z': [0, 2.1],
            'source_refs': ['synthetic common viewer fixture']}]}, 'assumptions': [], 'unresolved': []}
    candidate = output / 'synthetic'
    if not candidate.exists():
        assert export_source_proposal(proposal, candidate)['source_geometry_ready']
    original = (candidate / 'viewer.html').read_text()
    hook = 'window.QA={camera,controls,renderer,pick};'
    html = original.replace('(function loop(){', hook + '\n(function loop(){', 1)
    page_path = output / 'instrumented_viewer.html'; page_path.write_text(html)
    result = {'errors': [], 'scope': 'synthetic common viewer; no building interpretation or acceptance'}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/tmp/ep-bim-browser-qa/browsers/chromium-1234/chrome-linux64/chrome',
            headless=True, args=['--no-sandbox', '--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1400, 'height': 950})
        page.on('pageerror', lambda e: result['errors'].append(str(e)))
        page.goto(page_path.as_uri()); page.wait_for_function('window.QA')
        page.select_option('#colorBy', 'surface')
        point = page.evaluate('''()=>{const p=new THREE.Vector3(3,1.5,1.0);
            QA.controls.target.copy(p);QA.camera.position.set(12,-8,16);QA.controls.update();
            QA.camera.updateMatrixWorld(); const v=p.clone().project(QA.camera),r=QA.renderer.domElement.getBoundingClientRect();
            return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};}''')
        before = page.evaluate('(p)=>QA.pick({clientX:p.x,clientY:p.y})?.object.userData', point)
        page.check('#enZ')
        page.locator('#posZ').evaluate('(e)=>{e.value=2.2;e.dispatchEvent(new Event("input"));}')
        after = page.evaluate('(p)=>QA.pick({clientX:p.x,clientY:p.y})?.object.userData', point)
        page.mouse.click(point['x'], point['y'])
        selected = page.locator('#sel').inner_text()
        assert before != after, (before, after)
        assert 'door' in str(after).lower(), after
        assert selected and not result['errors'], result
        page.screenshot(path=str(output / 'clipped_door_selected.png'))
        result.update(status='pass', before_cut=before, after_cut=after, actual_click_text=selected)
        browser.close()
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'errors': result['errors']}))


if __name__ == '__main__':
    main()
