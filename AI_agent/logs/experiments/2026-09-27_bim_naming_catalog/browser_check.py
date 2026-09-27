"""Exercise actual offline renderer; test-only introspection is never delivered."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent


def check():
    errors, requests = [], []
    evidence = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,args=['--no-sandbox','--use-angle=swiftshader'])
        page = browser.new_page(viewport={'width':1400,'height':960},offline=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
        # Introspection of closure state only in the test browser's in-memory HTML.
        html = (OUT/'synthetic/enclosure_viewer.html').read_text()
        marker = '  refreshColors(); applyFilter(); applyExplode(); applyClipping(); defaultView();'
        assert html.count(marker)==1
        html=html.replace(marker, '  window.__qa={describe,surfMeshes,winMeshes,openingMeshes,enclosureMeshes,EDGES,camera,renderer,pick};\n'+marker)
        page.set_content(html)
        page.wait_for_function('window.__qa && window.__qa.surfMeshes.length>0')
        result=page.evaluate('''() => {
          const q=window.__qa, groups={surface:q.surfMeshes,window:q.winMeshes,opening:q.openingMeshes,region:q.enclosureMeshes};
          const checks=[];
          for(const [kind,meshes] of Object.entries(groups)) for(const mesh of meshes){
            const u=mesh.userData, div=document.createElement('div');
            for(const mode of ['floor','zone','surface']){
              div.innerHTML=q.describe(mode,mesh);
              const text=div.textContent;
              if(!text.includes('名称')) throw Error(kind+' has no name in '+mode);
              const name=div.querySelector('.kv b').textContent;
              if(!/^(F\\d+|Z\\d+_)/.test(name)) throw Error('raw ID used as name: '+name);
              if(mode==='floor' && name !== 'F'+(u.floor+1)) throw Error('wrong floor');
              if(mode==='zone' && !name.includes('_F'+(u.floor+1)+'_')) throw Error('wrong room');
              checks.push({kind,mode,name});
            }
          }
          for(const e of q.EDGES) if(!/^Z\\d+_.*_Edge\\d+$/.test(e.publicName)) throw Error('unnamed edge');
          const colors={};
          for(const m of q.surfMeshes){
            const role=window.GEO.roles[m.userData.zone];
            const color='#'+m.material.color.getHexString();
            if(color!==window.GEO.room_types[role].color) throw Error('palette mismatch '+role+': '+color);
            colors[role]=color;
          }
          return {checks,edge_count:q.EDGES.length,colors};
        }''')
        assert len(result['colors'])==4
        assert any('_Part' in x['name'] for x in result['checks'])
        assert any('_Unknown1' in x['name'] for x in result['checks'])
        evidence['synthetic']=result
        # Real pointer clicks on a raycast-resolved object in each selection mode.
        for mode in ['floor','zone','surface','edge']:
            page.select_option('#colorBy',mode)
            hit=page.evaluate('''() => {const q=window.__qa;
              if(document.querySelector('#colorBy').value==='edge'){
                const e=q.EDGES.find(e=>!e.dup); const v=e.a.clone().add(e.b).multiplyScalar(.5).project(q.camera);
                return {x:(v.x*.5+.5)*1400,y:(-v.y*.5+.5)*960};
              }
              for(let y=200;y<800;y+=15)for(let x=350;x<1100;x+=15)if(q.pick({clientX:x,clientY:y}))return {x,y};
              throw Error('no clickable mesh');}''')
            page.mouse.click(hit['x'],hit['y'])
            assert '名称' in page.locator('#sel').inner_text()
            evidence[mode+'_click']=page.locator('#sel').inner_text()
        page.select_option('#colorBy','zone')
        page.screenshot(path=str(OUT/'synthetic.png'))
        # Delivered real-case HTML has no instrumentation and loads fully offline.
        page.goto((OUT/'sm21/viewer.html').as_uri())
        page.wait_for_selector('canvas')
        assert page.locator('#floorSel option').count()==3
        texts=page.locator('#floorSel option').all_text_contents()
        assert texts[1].startswith('F1 ') and texts[2].startswith('F2 ')
        page.select_option('#floorSel','0'); first=page.locator('canvas').screenshot()
        page.select_option('#floorSel','1'); second=page.locator('canvas').screenshot()
        assert first!=second
        page.select_option('#floorSel','-1')
        page.screenshot(path=str(OUT/'sm21.png'))
        evidence['real_case']={'floor_options':texts,'distinct_floor_images':True,
           'source_sha256':page.evaluate('window.GEO.source_model.source_model_sha256')}
        assert not errors and not requests, (errors,requests)
        browser.close()
    evidence.update(status='pass',page_errors=errors,external_requests=requests,
                    scope='Offline rendering and selection naming; not drawing fidelity.')
    (OUT/'browser_report.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k!='synthetic'},ensure_ascii=False))


if __name__=='__main__':check()
