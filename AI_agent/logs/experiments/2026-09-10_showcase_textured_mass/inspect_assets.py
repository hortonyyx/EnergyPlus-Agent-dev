"""Offline check of the actual packaged model and its presentation controls."""
import argparse,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[4]
ASSET=ROOT/'showcase/2026-09-11-research-report/demos/textured-mass'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(exist_ok=False)
    report={'offline':True,'pages':{}}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        ctx=browser.new_context(viewport={'width':1600,'height':1000},offline=True)
        for name,filename in [('inferred','index.html'),('exterior','envelope.html')]:
            page=ctx.new_page();errors=[];external=[];failed=[]
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('requestfailed',lambda r:failed.append(r.url[:160]))
            page.on('request',lambda r:external.append(r.url[:160]) if r.url.startswith(('https:','http:')) else None)
            path=ASSET/filename;page.goto(path.as_uri(),wait_until='load')
            page.wait_for_function("window.SHOWCASE && document.body.dataset.texture==='ready'")
            page.wait_for_timeout(750)
            item={'file':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':page.evaluate('({spaces:SHOWCASE.source.spaces.length,openings:SHOWCASE.source.openings.length,status:SHOWCASE.source.validation.status,mode:SHOWCASE_MODE})')}
            page.screenshot(path=str(a.out/(name+'_bim.png')))
            canvas=page.locator('canvas').first;before=canvas.screenshot()
            page.mouse.move(800,450);page.mouse.down();page.mouse.move(990,470,steps=12);page.mouse.up();page.wait_for_timeout(500)
            item['orbit_changes_canvas']=before!=canvas.screenshot()
            page.locator('[data-view=input]').click();page.wait_for_timeout(600);page.screenshot(path=str(a.out/(name+'_input.png')))
            item['input_mode']=page.evaluate('({root:SHOWCASE.root.visible,raw:SHOWCASE.rawMesh.visible})')
            page.locator('[data-view=overlay]').click();page.wait_for_timeout(500);page.screenshot(path=str(a.out/(name+'_overlay.png')))
            item['overlay_mode']=page.evaluate('({root:SHOWCASE.root.visible,raw:SHOWCASE.rawMesh.visible})')
            page.locator('#typical-floor').click();page.wait_for_timeout(650);page.screenshot(path=str(a.out/(name+'_plan.png')))
            item['plan_control']={'floor':page.locator('#floorSel').input_value(),'section_z':page.locator('#posZ').input_value(),'section_enabled':page.locator('#enZ').is_checked()}
            item['visible_plan_floor_faces']=page.evaluate("SHOWCASE.surfMeshes.filter(m=>m.visible && m.userData.type==='Floor' && m.userData.floor===2).length")
            page.locator('#explode-model').click();page.wait_for_timeout(650);page.screenshot(path=str(a.out/(name+'_exploded.png')))
            item['explode']=page.locator('#explode').input_value()
            page.locator('#toggle-tools').click();item['tools_visible']=page.locator('#panel').is_visible()
            item.update(page_errors=errors,external_requests=external,failed_requests=failed);report['pages'][name]=item
            page.close()
        browser.close()
    (a.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    for x in report['pages'].values():
        assert not x['page_errors'] and not x['external_requests'] and not x['failed_requests']
        assert x['orbit_changes_canvas'] and x['input_mode']=={'root':False,'raw':True} and x['overlay_mode']=={'root':True,'raw':True}
        assert x['plan_control']['floor']=='2' and x['plan_control']['section_enabled'] and x['tools_visible']
        assert x['visible_plan_floor_faces']>0

if __name__=='__main__':main()
