import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[4]
RUN=ROOT/'AI_agent/logs/experiments/2026-09-14_voimatalo_opus_transfer_run01'
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 context=browser.new_context(viewport={'width':1500,'height':1000},offline=True)
 page=context.new_page();errors=[];external=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
 page.goto((RUN/'overlay.html').as_uri())
 page.wait_for_function("window.TRANSFER && document.body.dataset.texture==='ready'")
 results={}
 for mode in ['input','overlay','bim']:
  page.locator('[data-transfer-mode='+mode+']').click();page.wait_for_timeout(400)
  results[mode]=page.evaluate('''() => ({rawVisible:TRANSFER.rawMesh.visible,bimVisible:TRANSFER.root.visible,
    sourceHash:GEO.source_model.source_model_sha256,firstInputVertex:[...TRANSFER.rawMesh.geometry.attributes.position.array.slice(0,3)]})''')
  page.screenshot(path=str(RUN/'browser_qa'/('overlay_'+mode+'.png')))
 assert results['input']['rawVisible'] and not results['input']['bimVisible']
 assert results['overlay']['rawVisible'] and results['overlay']['bimVisible']
 assert not results['bim']['rawVisible'] and results['bim']['bimVisible']
 assert len({r['sourceHash'] for r in results.values()})==1
 browser.close()
 (RUN/'browser_qa/overlay_report.json').write_text(json.dumps({'results':results,'errors':errors,'external':external},indent=2)+'\n')
 assert not errors and not external
 print('Input/BIM/overlay modes and fixed source hash verified offline')
