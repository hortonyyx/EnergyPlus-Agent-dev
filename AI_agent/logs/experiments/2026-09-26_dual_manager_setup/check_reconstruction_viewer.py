"""Offline source viewer check; no model or geometry edits."""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def check(run):
    run=run.resolve()
    assert (run/'summary.json').exists()
    delivery=json.loads((run/'delivery.json').read_text())
    candidate=run/delivery['candidate']
    source=json.loads((candidate/'source_model.json').read_text())
    out=run/'browser_qa';out.mkdir(exist_ok=False)
    errors=[];external=[];floors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        context=browser.new_context(viewport={'width':1400,'height':1000},offline=True)
        page=context.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
        page.goto((candidate/'viewer.html').as_uri())
        page.wait_for_function('window.GEO && document.querySelector("canvas")')
        page.wait_for_timeout(600)
        assert page.evaluate('GEO.source_model.source_model_sha256')==source['source_model_sha256']
        options=page.locator('#floorSel option').evaluate_all('xs=>xs.map(x=>({value:x.value,text:x.textContent}))')
        assert len(options)-1==len({s['z_floor'] for s in source['spaces']})
        page.screenshot(path=str(out/'whole.png'))
        before=page.locator('canvas').screenshot()
        page.mouse.move(900,500);page.mouse.down();page.mouse.move(1120,630,steps=15);page.mouse.up()
        page.wait_for_timeout(500)
        after=page.locator('canvas').screenshot()
        assert hashlib.sha256(before).digest()!=hashlib.sha256(after).digest()
        page.screenshot(path=str(out/'rotated.png'))
        for option in options:
            if option['value']=='-1':continue
            page.locator('#floorSel').select_option(option['value'])
            page.wait_for_timeout(250)
            page.screenshot(path=str(out/f"floor_{option['value']}.png"));floors.append(option)
        page.goto((run/'delivery.html').as_uri())
        page.wait_for_timeout(400)
        images=page.locator('img').evaluate_all('xs=>xs.map(x=>({src:x.getAttribute("src"),loaded:x.complete&&x.naturalWidth>0}))')
        assert all(i['loaded'] for i in images)
        assert not errors and not external
        browser.close()
    report=dict(status='pass',candidate=delivery['candidate'],source_sha256=source['source_model_sha256'],
                floor_options=floors,rotation_changed_canvas=True,offline=True,external_requests=external,
                page_errors=errors,delivery_images=images,scope='Display/transport only, not image fidelity or human approval.')
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='delivery_images'},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);check(parser.parse_args().run)
