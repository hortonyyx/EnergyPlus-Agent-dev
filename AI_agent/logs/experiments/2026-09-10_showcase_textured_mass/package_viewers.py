"""Package two checked source variants into a standalone comparison viewer."""
import json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'showcase/2026-09-11-research-report/demos/textured-mass'
ORIGINAL=ROOT/'case_tests/textured_mass/single_buildings/voimatalo/viewer.html'

CSS='''
body{font-family:system-ui,-apple-system,"Noto Sans CJK SC",sans-serif;background:#edf2f2}
#showcasebar{position:fixed;z-index:110;left:22px;right:22px;top:18px;display:flex;align-items:center;gap:24px;justify-content:space-between;background:rgba(255,255,255,.95);border:1px solid #d9e3e3;border-radius:15px;padding:14px 20px;box-shadow:0 5px 25px #173f4610}
.brand strong{font-size:22px;letter-spacing:-.6px;color:#163b43}.brand small{display:block;color:#667e83;font-size:11px;margin-top:4px}
.switches{display:flex;gap:5px;flex-wrap:wrap}#showcasebar button,#showcasebar a{border:0;background:transparent;color:#3c5960;border-radius:7px;padding:10px 13px;cursor:pointer;font:13px inherit;text-decoration:none}#showcasebar button.active{background:#1c535c;color:white}#showcasebar button:hover,#showcasebar a:hover{background:#dceced;color:#16474f}.actions{display:flex;align-items:center;gap:2px}.actions button{font-size:12px!important}
#panel{top:108px;max-height:calc(100% - 170px);width:246px;display:none;font-size:12px}#rinfo{top:108px;max-height:calc(100% - 170px);width:266px;display:none}body.tools #panel,body.tools #rinfo{display:block}
#scene-caption{position:fixed;left:30px;bottom:22px;z-index:50;color:#45666c;background:#ffffffec;padding:13px 17px;border:1px solid #dae5e7;border-radius:10px;font-size:12px;line-height:1.7;max-width:580px}.capsule{display:inline-block;color:#896334;background:#fff2d8;padding:0 7px;border-radius:4px;margin-left:8px}
#variant-links{position:fixed;right:28px;bottom:24px;z-index:60;display:flex;gap:8px}#variant-links a{background:white;border:1px solid #d7e3e4;color:#245a64;padding:10px 14px;border-radius:8px;text-decoration:none;font-size:12px}#variant-links a.active{background:#245a64;color:white}
@media(max-width:1050px){#showcasebar{gap:8px;padding:10px;left:10px;right:10px}.brand strong{font-size:18px}.actions{display:none}#showcasebar button{padding:8px!important}#scene-caption{max-width:55%;left:12px;font-size:11px}#variant-links{right:12px;bottom:16px;flex-direction:column}}
'''

EXTENSION=r'''
  // The original GLB is placed in the exact documented source coordinate frame.
  const raw = __RAW_DATA__;
  function binary(s){return Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer;}
  const rp=new Float32Array(binary(raw.position)), aligned=new Float32Array(rp.length);
  const ca=Math.cos(Math.PI/12),sa=Math.sin(Math.PI/12);
  for(let i=0;i<rp.length;i+=3){aligned[i]=ca*rp[i]+sa*rp[i+2];aligned[i+1]=sa*rp[i]-ca*rp[i+2];aligned[i+2]=rp[i+1];}
  const rg=new THREE.BufferGeometry();rg.setAttribute('position',new THREE.BufferAttribute(aligned,3));rg.setAttribute('uv',new THREE.BufferAttribute(new Float32Array(binary(raw.uv)),2));rg.setIndex(new THREE.BufferAttribute(new Uint32Array(binary(raw.indices)),1));
  const rt=new THREE.TextureLoader().load('data:image/jpeg;base64,'+raw.texture,()=>{document.body.dataset.texture='ready';});rt.encoding=THREE.sRGBEncoding;
  const rm=new THREE.MeshBasicMaterial({map:rt,side:THREE.DoubleSide,transparent:true,opacity:1});const rawMesh=new THREE.Mesh(rg,rm);scene.add(rawMesh);rawMesh.visible=false;
  renderer.outputEncoding=THREE.sRGBEncoding;renderer.setClearColor(0xedf2f2);
  Object.assign(ROLE_COLORS,{office_inferred:0xd6e4e3,corridor_inferred:0xf2d7a0,services_inferred:0xd2c6df,vertical_core_inferred:0xabc7d0,office_merged:0xdce7e5,commercial_merged:0xd4dedc,annex_merged:0xe4dccc,roof_enclosure:0x90aca9,roof_stack:0x90aca9});
  refreshColors();
  function whole(){
    $('floorSel').value='-1';$('explode').value='0';$('explode').dispatchEvent(new Event('input'));
    ['X','Y','Z'].forEach(a=>{const e=$('en'+a);e.checked=false;e.dispatchEvent(new Event('change'));});
    applyFilter();camera.position.set(86,-102,76);camera.zoom=1.15;camera.updateProjectionMatrix();controls.target.set(0,-3,14);controls.update();
  }
  function viewMode(mode){
    window.SHOWCASE_MODE=mode;root.visible=mode!=='input';rawMesh.visible=mode!=='bim';rm.opacity=mode==='overlay'?.45:1;rm.depthWrite=mode!=='overlay';
    if(mode!=='bim')whole();
    const alpha=mode==='overlay'?.40:1;$('opacity').value=alpha;$('opacity').dispatchEvent(new Event('input'));
    document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===mode));
    document.getElementById('mode-caption').textContent=mode==='input'?'真实输入 · GLB 三角网格与完整贴图':mode==='overlay'?'叠合对照 · 同一米制坐标，不随候选重新拟合':'轻量 BIM · 房间/空间体、边界与门窗对象';
  }
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>viewMode(b.dataset.view));
  document.getElementById('whole-model').onclick=()=>{whole();viewMode('bim');};
  document.getElementById('typical-floor').onclick=()=>{
    viewMode('bim');whole();$('floorSel').value='2';$('floorSel').dispatchEvent(new Event('change'));
    $('enZ').checked=true;$('enZ').dispatchEvent(new Event('change'));$('posZ').value='10.9';$('posZ').dispatchEvent(new Event('input'));
    camera.position.set(0,-3.01,120);camera.zoom=1.15;camera.updateProjectionMatrix();controls.target.set(0,-3,9.5);controls.update();
  };
  document.getElementById('explode-model').onclick=()=>{viewMode('bim');whole();$('explodeMode').value='floor';$('explode').value='.28';$('explode').dispatchEvent(new Event('input'));camera.zoom=.8;camera.updateProjectionMatrix();};
  document.getElementById('toggle-tools').onclick=()=>document.body.classList.toggle('tools');
  $('reset').onclick=whole;
  window.SHOWCASE={scene,camera,controls,renderer,root,rawMesh,viewMode,whole,source:SOURCE,surfMeshes};
  whole();viewMode('bim');
'''

def package(variant,target):
    rawhtml=ORIGINAL.read_text();data=json.loads(rawhtml.split('const data=',1)[1].split(';\nfunction bytes',1)[0])
    html=(OUT/variant/'viewer.html').read_text()
    inferred=variant=='inferred'
    label='内部空间推理方案' if inferred else '外壳与楼层模型'
    caption='标准层内部为推断布局；蓝灰为竖向核心，米色为走廊。' if inferred else '各层为合并空间；内部房间尚未展开。'
    report=json.loads((OUT/variant/'report.json').read_text())
    bar=f'''<header id="showcasebar"><div class="brand"><strong>Voimatalo</strong><small>HELSINKI / {label}</small></div><nav class="switches" aria-label="显示模式"><button data-view="bim" class="active">轻量 BIM</button><button data-view="input">真实贴图</button><button data-view="overlay">叠合对照</button></nav><nav class="actions"><button id="whole-model">整体</button><button id="typical-floor">典型层</button><button id="explode-model">分层展开</button><button id="toggle-tools">工具</button></nav></header>
    <div id="scene-caption"><strong id="mode-caption"></strong><br>主楼 8 层 · {report['window_groups']} 窗组 · {report['spaces']} 个空间体<span class="capsule">辅助推理探索</span><br>{caption}灰色面表示信息未知。<br>拖动旋转 · 滚轮缩放 · 右键平移 · 局部 u / v / z 坐标</div>
    <nav id="variant-links"><a href="envelope.html" class="{'active' if not inferred else ''}">外壳与楼层</a><a href="index.html" class="{'active' if inferred else ''}">空间推理方案</a><a href="{variant}/source_model.json" download>源 BIM JSON ↓</a></nav>'''
    html=html.replace('</style>',CSS+'</style>',1).replace('<body>','<body>'+bar,1)
    anchor='  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();'
    assert html.count(anchor)==1
    html=html.replace(anchor,EXTENSION.replace('__RAW_DATA__',json.dumps(data,separators=(',',':')))+anchor)
    html=html.replace('<h1>Geometry inspection</h1>','<h1>查看与量测</h1>')
    # With the lower storey filtered out, its reciprocal ceiling cannot stand
    # in for this storey's floor. Restore only those existing floor meshes.
    original='surfMeshes.forEach(m=>m.visible = sw && okF(m.userData));'
    assert html.count(original)==1
    html=html.replace(original,"surfMeshes.forEach(m=>m.visible = sw && (okF(m.userData) || (f>=0 && m.userData.floor===f && m.userData.type==='Floor')));")
    # Local +v is not true north. Do not inherit the generic viewer's N label.
    html=html.replace("label('N','#d32f2f'", "label('v','#d32f2f'")
    html=html.replace("[['x',0xcc1111", "[['u',0xcc1111").replace("['y',0x11aa11", "['v',0x11aa11")
    html=html.replace('const WINDOW_COLOR = 0x1e5ad2','const WINDOW_COLOR = 0x34798b')
    # Small translation of ordinary viewer controls; source content is unchanged.
    for a,b in [('all floors','全部标高'),('select by','着色方式'),('wall opacity','围护透明度'),('exploded view','展开显示'),('by floor','按楼层'),('by zone','按空间'),('wall / floor / roof faces','显示实体边界'),('clear measure','清除量测'),('save PNG','保存图片'),('reset view','复位')]:html=html.replace(a,b)
    (OUT/target).write_text(html)

def main():
    package('inferred','index.html');package('exterior','envelope.html')
    html=ORIGINAL.read_text().replace('尚未生成 BIM','真实贴图输入（无房间语义）')
    html=html.replace('max-width:500px','max-width:440px')
    (OUT/'input_viewer.html').write_text(html)
    # Facade HTMLs are disposable render inputs; PNGs/metric mapping and code
    # retain the review evidence without seven copies of the same texture.
    for p in (Path(__file__).resolve().parent/'facade_views').glob('*.html'):p.unlink()
    print('Packaged index.html, envelope.html, input_viewer.html')

if __name__=='__main__':main()
