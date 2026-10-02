"""Exercise the actual packaged page in a browser; screenshots are inspection evidence."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8765/AI_agent/logs/experiments/2026-09-30_voimatalo_user_revision/result_01/index.html'


def main():
    output = HERE / 'browser_qa'; output.mkdir(exist_ok=True)
    result = {'url': URL, 'errors': [], 'views': {}, 'checks': []}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path='/tmp/ep-bim-browser-qa/browsers/chromium-1234/chrome-linux64/chrome',
            headless=True, args=['--no-sandbox', '--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1600, 'height': 1050})
        page.on('pageerror', lambda error: result['errors'].append(str(error)))
        response = page.goto(URL, wait_until='load')
        assert response.status == 200
        page.wait_for_function('window.REVISION && document.body.dataset.texture === "ready"')
        for view in ['whole', 'street', 'standard', 'annex1', 'annex2', 'circulation', 'roof']:
            page.click(f'[data-review-view="{view}"]')
            page.wait_for_timeout(250)
            stats = page.evaluate('REVISION.stats()')
            result['views'][view] = stats
            page.screenshot(path=str(output / f'{view}.png'))
        for mode in ['input', 'overlay']:
            page.click(f'[data-transfer-mode="{mode}"]')
            page.wait_for_timeout(250)
            stats = page.evaluate('({mode:document.body.dataset.mode, raw:TRANSFER.rawMesh.visible,bim:TRANSFER.root.visible})')
            assert stats['raw'] and stats['bim'] == (mode == 'overlay')
            result['checks'].append({mode: stats})
            page.screenshot(path=str(output / f'{mode}.png'))
        standard = result['views']['standard']
        assert standard['floor'] == 'F3' and standard['visibleWindows'] == 46
        assert {'CORE_S', 'CORE_E', 'TOWER_STAIR', 'TOWER_LIFT'} <= set(standard['visibleSpaces'])
        for n in [1, 2]:
            stats = result['views'][f'annex{n}']
            assert set(stats['visibleSpaces']) == {f'ANNEX_F{n}_hall', 'ANNEX_STAIR'}
            assert stats['visibleWindows'] == 12
        result['checks'].append({'floor_membership_and_opening_height_filter': 'pass'})

        page.click('[data-review-view="standard"]')
        point = page.evaluate('''()=>{
          const s=REVISION.spaces.F3_E_04;
          const xs=s.polygon.map(p=>p[0]),ys=s.polygon.map(p=>p[1]);
          const v=new THREE.Vector3((Math.min(...xs)+Math.max(...xs))/2,
            (Math.min(...ys)+Math.max(...ys))/2,s.z_floor+.01).project(TRANSFER.camera);
          const r=TRANSFER.renderer.domElement.getBoundingClientRect();
          return {x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};
        }''')
        page.mouse.click(point['x'], point['y'])
        selected = page.locator('#sel').inner_text()
        assert 'F3_E_04' in selected and 'Office_Enclosed' in selected and '推断' in selected, selected
        result['checks'].append({'actual_room_click': selected})
        page.screenshot(path=str(output / 'room_selection.png'))
        # Changing floors after a preset must move the cut plane with the floor.
        index = page.evaluate('REVISION.floors.findIndex(f=>f.id === "F7")')
        page.select_option('#floorSel', str(index))
        assert page.evaluate('REVISION.stats().floor') == 'F7'
        assert float(page.locator('#posZ').input_value()) > 21.6
        result['checks'].append({'change_floor_after_section_preset': 'pass'})
        for href in ['../candidate_01/source_model.json', '../validation.json', 'rooms.csv']:
            assert page.request.get(URL.rsplit('/', 1)[0] + '/' + href).status == 200
        result['checks'].append({'download_links': 'pass'})
        assert not result['errors'], result['errors']
        browser.close()
    result['status'] = 'pass'
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'pass', 'view_count': len(result['views']), 'errors': result['errors']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
