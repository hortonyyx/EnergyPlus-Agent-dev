"""Inspect the actual delivered source in an offline browser, with no model calls."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);args=parser.parse_args()
    run=args.run.resolve();out=run/'browser_qa';out.mkdir(exist_ok=False)
    selected=json.loads((run/'delivery.json').read_text())['candidate']
    errors=[];external=[];failed=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        ctx=browser.new_context(viewport={'width':1500,'height':1000},offline=True)
        page=ctx.new_page()
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:failed.append(r.url))
        page.on('request',lambda r:external.append(r.url) if r.url.startswith(('https:','http:')) else None)
        page.goto((run/selected/'viewer.html').as_uri())
        page.wait_for_function('window.GEO && window.GEO.source_model && document.querySelector("canvas")')
        page.wait_for_timeout(700)
        actual=page.evaluate('''() => ({spaces:window.GEO.source_model.spaces.length,
            openings:window.GEO.source_model.openings.length,
            hash:window.GEO.source_model.source_model_sha256,
            options:[...document.querySelector('#floorSel').options].map(o=>({value:o.value,text:o.text}))})''')
        source=json.loads((run/selected/'source_model.json').read_text())
        assert actual['hash']==source['source_model_sha256']
        assert actual['spaces']==len(source['spaces']) and actual['openings']==len(source['openings'])
        page.screenshot(path=str(out/'whole.png'))
        before=page.locator('canvas').screenshot()
        page.mouse.move(1000,460);page.mouse.down();page.mouse.move(1180,520,steps=14);page.mouse.up()
        page.wait_for_timeout(500)
        after=page.locator('canvas').screenshot()
        assert before!=after
        page.screenshot(path=str(out/'rotated.png'))
        options=[o['value'] for o in actual['options'] if o['value']!='-1']
        floor_value=options[min(2,len(options)-1)]
        page.select_option('#floorSel',floor_value)
        page.wait_for_timeout(400)
        page.screenshot(path=str(out/'single_floor.png'))
        page.select_option('#floorSel','-1')
        page.locator('#explodeMode').select_option('floor')
        page.locator('#explode').evaluate("n=>{n.value='.2';n.dispatchEvent(new Event('input'))}")
        page.wait_for_timeout(400)
        page.screenshot(path=str(out/'exploded.png'))
        page.goto((run/'index.html').as_uri())
        page.wait_for_timeout(900)
        assert page.locator('iframe').count()==2
        page.screenshot(path=str(out/'comparison.png'))
        browser.close()
    result={'offline':True,'actual':actual,'rotates':before!=after,'floor_selected':floor_value,
            'page_errors':errors,'failed_requests':failed,'external_requests':external}
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert not errors and not failed and not external,result
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
