"""Verify real delivered room colors and clickable public names offline."""
import argparse
import importlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check(run):
    base = importlib.import_module(
        'AI_agent.logs.experiments.2026-09-26_sm25_height_review_setup.browser_check'
    )
    base.check(run)
    delivery = json.loads((run / 'delivery.json').read_text())
    errors, external = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--use-angle=swiftshader'])
        page = browser.new_page(viewport={'width': 1400, 'height': 960}, offline=True)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url)
                if request.url.startswith(('http:', 'https:')) else None)
        original = (run / delivery['viewer']).read_text()
        marker = '  refreshColors(); applyFilter(); applyExplode(); applyClipping(); defaultView();'
        assert original.count(marker) == 1
        page.set_content(original.replace(marker,
            '  window.__qa={describe,surfMeshes,winMeshes,openingMeshes,enclosureMeshes,EDGES,pick};\n' + marker))
        page.wait_for_function('window.__qa && window.__qa.surfMeshes.length > 0')
        evidence = page.evaluate('''() => {
          const q=window.__qa, checks=[], colors={}, roleEvidence={};
          for(const [kind,meshes] of Object.entries({surface:q.surfMeshes,window:q.winMeshes,
                 opening:q.openingMeshes,region:q.enclosureMeshes})) {
            for(const mesh of meshes) for(const mode of ['floor','zone','surface']) {
              const div=document.createElement('div'); div.innerHTML=q.describe(mode,mesh);
              const name=div.querySelector('.kv b')?.textContent;
              if(!name || !/^(F\\d+|Z\\d+_)/.test(name)) throw Error('missing public name');
              if(mode==='zone' && name!==window.GEO.source_model.public_names.spaces[mesh.userData.zone])
                throw Error('wrong source room name');
              if(mode==='zone') {
                const space=window.GEO.source_model.spaces.find(s=>s.id===mesh.userData.zone);
                if(space.role_evidence) {
                  const e=space.role_evidence, text=div.textContent;
                  if(!text.includes(({observed:'图文明确',inferred:'推断',unknown:'待判定'})[e.basis]))
                    throw Error('function basis absent from room panel');
                  for(const note of [...e.source_refs,...e.assumptions,...space.source_refs,...space.assumptions])
                    if(!text.includes(note)) throw Error('room evidence missing from panel: '+note);
                  roleEvidence[space.id]={role:space.role,basis:e.basis,text};
                }
              }
              checks.push({kind,mode,name});
            }
          }
          for(const mesh of q.surfMeshes) {
            const role=window.GEO.roles[mesh.userData.zone];
            const actual='#'+mesh.material.color.getHexString();
            if(actual!==window.GEO.room_types[role].color) throw Error('incorrect room color');
            colors[role]=actual;
          }
          for(const edge of q.EDGES) if(!/^Z\\d+_.*_Edge\\d+$/.test(edge.publicName))
            throw Error('unnamed edge');
          return {checks,colors,role_evidence:roleEvidence,edge_count:q.EDGES.length};
        }''')
        # Exercise the actual mouse handler in all three object selection modes.
        for mode in ['floor', 'zone', 'surface']:
            page.select_option('#colorBy', mode)
            point = page.evaluate('''() => {
              for(let y=200;y<800;y+=15) for(let x=350;x<1100;x+=15)
                if(window.__qa.pick({clientX:x,clientY:y})) return {x,y};
              throw Error('no selectable geometry');
            }''')
            page.mouse.click(point['x'], point['y'])
            evidence[mode + '_click'] = page.locator('#sel').inner_text()
            assert '名称' in evidence[mode + '_click']
        assert not errors and not external, (errors, external)
        assert original == (run / delivery['viewer']).read_text()
        browser.close()
    evidence.update(status='pass', offline=True, page_errors=errors, external_requests=external,
                    source_sha256=delivery['source_model_sha256'],
                    limit='Names and actual material colors only; function truth is reviewed separately.')
    (run / 'browser_qa/room_types.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in evidence.items() if k not in {'checks', 'role_evidence'}}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    check(parser.parse_args().run.resolve())
