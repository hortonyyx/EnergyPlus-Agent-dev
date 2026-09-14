"""Package actual selected source and original input for post-run inspection."""
import argparse
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
EXTENSION=r'''
 const raw=__RAW__;
 function transferBytes(s){return Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer;}
 const rp=new Float32Array(transferBytes(raw.position)), aligned=new Float32Array(rp.length);
 const ca=Math.cos(Math.PI/12),sa=Math.sin(Math.PI/12);
 for(let i=0;i<rp.length;i+=3){aligned[i]=ca*rp[i]+sa*rp[i+2];aligned[i+1]=sa*rp[i]-ca*rp[i+2];aligned[i+2]=rp[i+1];}
 const rg=new THREE.BufferGeometry();rg.setAttribute('position',new THREE.BufferAttribute(aligned,3));
 rg.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(transferBytes(raw.uv)),2));
 rg.setIndex(new THREE.BufferAttribute(new Uint32Array(transferBytes(raw.indices)),1));
 const rt=new THREE.TextureLoader().load('data:image/jpeg;base64,'+raw.texture,()=>document.body.dataset.texture='ready');
 rt.encoding=THREE.sRGBEncoding;renderer.outputEncoding=THREE.sRGBEncoding;
 const rm=new THREE.MeshBasicMaterial({map:rt,side:THREE.DoubleSide,transparent:true});
 const rawMesh=new THREE.Mesh(rg,rm);scene.add(rawMesh);rawMesh.visible=false;
 function transferMode(mode){
   $('floorSel').value='-1';$('explode').value='0';$('explode').dispatchEvent(new Event('input'));
   ['X','Y','Z'].forEach(a=>{$('en'+a).checked=false;$('en'+a).dispatchEvent(new Event('change'));});
   applyFilter();root.visible=mode!=='input';rawMesh.visible=mode!=='bim';
   rm.opacity=mode==='overlay'?.55:1;rm.depthWrite=mode!=='overlay';
   $('opacity').value=mode==='overlay'?.3:1;$('opacity').dispatchEvent(new Event('input'));
   document.body.dataset.mode=mode;
 }
 document.querySelectorAll('[data-transfer-mode]').forEach(b=>b.onclick=()=>transferMode(b.dataset.transferMode));
 window.TRANSFER={mode:transferMode,rawMesh,root,camera,controls,renderer};
 transferMode('bim');
'''

def main():
 parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);args=parser.parse_args()
 run=args.run.resolve();delivery=json.loads((run/'delivery.json').read_text());candidate=delivery['candidate']
 source=json.loads((run/candidate/'source_model.json').read_text())
 original=(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/viewer.html').read_text()
 data=json.loads(original.split('const data=',1)[1].split(';\nfunction bytes',1)[0])
 page=(run/candidate/'viewer.html').read_text()
 page=page.replace('<details open>','<details>')
 for name in ['report.json','proposal.json','source_model.json']:
  page=page.replace('href="'+name+'"','href="'+candidate+'/'+name+'"')
 anchor='  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();'
 assert page.count(anchor)==1
 page=page.replace(anchor,EXTENSION.replace('__RAW__',json.dumps(data,separators=(',',':')))+anchor)
 buttons='<div style="position:fixed;top:12px;left:34%;z-index:200;background:#fffe;padding:10px;border:1px solid #aaa">'+''.join(f'<button data-transfer-mode="{k}">{v}</button>' for k,v in [('bim','工作模型 BIM'),('input','原始贴图'),('overlay','固定坐标叠合')])+'<small> 局部坐标；内部为假设</small></div>'
 page=page.replace('<body>','<body>'+buttons,1).replace("label('N','#d32f2f'","label('y (local)','#d32f2f'")
 (run/'overlay.html').write_text(page)
 counts={kind:sum(o['kind']==kind for o in source['openings']) for kind in ['window','door','open']}
 notes=''.join('<li>'+html.escape(n)+'</li>' for n in source['generation']['unresolved'])
 original_relative='../../../../case_tests/textured_mass/single_buildings/voimatalo/viewer.html'
 index=f'''<!doctype html><meta charset="utf-8"><title>Voimatalo · 工作模型迁移</title>
 <style>body{{font:16px system-ui;margin:24px;color:#243643}}a{{color:#176777}}.views{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}iframe{{width:100%;height:680px;border:1px solid #bbb}}li{{margin:.5em 0}}@media(max-width:1000px){{.views{{grid-template-columns:1fr}}}}</style>
 <h1>Voimatalo · 工作模型迁移</h1>
 <p>Opus探索性生成；输入视图由开发侧预先准备。模型未获得旧BIM或内部平面。内部空间为假设，尚未验证真实布局。</p>
 <p>{len(source['spaces'])}空间 · {counts['window']}窗组 · {counts['door']}门 · 源几何检查：{html.escape(source['validation']['status'])}。几何自洽不等于建筑保真。</p>
 <p><a href="overlay.html">打开可切换贴图 / BIM / 固定坐标叠合的查看器</a> · <a href="{candidate}/source_model.json">源BIM</a> · <a href="delivery.html">实际交付检查</a> · <a href="README.md">结果与限制</a></p>
 <div class="views"><section><h2>原始单体网格</h2><iframe title="原始贴图" src="{original_relative}"></iframe></section><section><h2>本轮实际生成</h2><iframe title="生成BIM" src="{candidate}/viewer.html"></iframe></section></div>
 <h2>模型记录的未解决项</h2><ul>{notes}</ul>'''
 (run/'index.html').write_text(index)
 (run/'packaging.json').write_text(json.dumps({'candidate':candidate,'source_hash':source['source_model_sha256'],
   'input_transform':'x=cos15*GLB.x+sin15*GLB.z; y=sin15*GLB.x-cos15*GLB.z; z=GLB.y',
   'candidate_fitted_to_input':False,'source_mutated':False,'model_did_not_see_this_post_run_page':True},indent=2)+'\n')

if __name__=='__main__':main()
