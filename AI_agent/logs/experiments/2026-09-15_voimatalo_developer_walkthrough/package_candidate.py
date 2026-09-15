"""Actual source feedback and offline original-mesh/BIM comparison, no fitting."""
from pathlib import Path
import argparse
import html
import json
import runpy
import sys
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.geometry.mesh_bim_frame import render_mesh_bim_overlay
from scripts.tool_scripts.render_geometry_viewer import build_viewer_html

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
args.out.mkdir(exist_ok=False)
source = json.loads((args.candidate / 'source_model.json').read_text())
display = json.loads((args.candidate / 'display_geometry.json').read_text())
frame = source['mesh_frame']
feedback = args.out / 'feedback'
feedback.mkdir()
specs = [('top','F4'),('street',None),('courtyard',None),('west','F4'),('north','F6'),('court_long',None),('court_short',None)]
cards = []
for name, floor in specs:
    observation = json.loads((HERE / 'evidence_01' / (name+'.json')).read_text())
    picture = Image.open(HERE / 'evidence_01' / (name+'.png'))
    result, metadata = render_mesh_bim_overlay(picture, observation, source, floor_id=floor)
    result.save(feedback / (name+'.png'))
    (feedback / (name+'.json')).write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    cards.append(f'<figure><figcaption>{name} · {floor or "全部空间"}</figcaption><a href="feedback/{name}.png"><img src="feedback/{name}.png"></a></figure>')

# Actual height sections include continuous core spaces even though their source
# floor labels differ. Do not create new floor/slab objects to display them.
panels = []
for z in [2.8, 10.4, 26.3]:
    active = [s for s in source['spaces'] if s['z_floor'] <= z < s['z_floor']+s['height']]
    image = Image.new('RGB',(650,950),'white')
    draw = ImageDraw.Draw(image)
    # Use equal metric scaling, leaving blank side margin for labels.
    def point(p): return (60+(p[0]+16)*12, 80+(29-p[1])*12)
    draw.text((25,20),f'Actual source section z={z:g}m; cores included; interior hypothesis',fill='black')
    for s in active:
        color = '#e0e9f0'
        if 'CORE' in s['id']: color = '#ddc7a7'
        if 'services' in s['id']: color = '#c6d6b7'
        if 'ANNEX' in s['id']: color = '#ccd2e6'
        draw.polygon([point(p) for p in s['polygon']], fill=color, outline='#32495a', width=2)
        poly = Polygon(s['polygon']); label = poly.representative_point()
        draw.text(point([label.x,label.y]),s['id'],fill='black',anchor='mm')
    for opening in source['openings']:
        vertices = np.asarray(opening['vertices'])
        if vertices[:,2].min() <= z <= vertices[:,2].max():
            endpoints = np.unique(vertices[:,:2],axis=0)
            if len(endpoints)==2:
                draw.line([point(p) for p in endpoints], fill='#159066' if opening['kind']=='window' else '#d46823',width=4)
    name = f'section_{z:g}'
    image.save(feedback/(name+'.png'))
    (feedback/(name+'.json')).write_text(json.dumps({'source_model_sha256':source['source_model_sha256'], 'z_m':z,'space_ids':[s['id'] for s in active],
        'scope':'Derived section of real source volumes; no added source floor objects; not original-plan evidence'},indent=2)+'\n')
    panels.append(f'<figure><figcaption>源模型水平剖切 z={z:g}m，包含跨层核心</figcaption><img src="feedback/{name}.png"></figure>')

extension = runpy.run_path(str(ROOT/'AI_agent/logs/experiments/2026-09-14_voimatalo_transfer_setup/package_result.py'))['EXTENSION']
extension = extension.replace('Math.PI/12',f'Math.PI*({frame["yaw_degrees"]})/180')
tx,ty,tz = frame['translation_m']
extension = extension.replace('aligned[i]=ca*rp[i]+sa*rp[i+2]',f'aligned[i]=ca*rp[i]+sa*rp[i+2]+({tx})').replace('aligned[i+1]=sa*rp[i]-ca*rp[i+2]',f'aligned[i+1]=sa*rp[i]-ca*rp[i+2]+({ty})').replace('aligned[i+2]=rp[i+1]',f'aligned[i+2]=rp[i+1]+({tz})')
original = (ROOT/'case_tests/textured_mass/single_buildings/voimatalo/viewer.html').read_text()
raw = json.loads(original.split('const data=',1)[1].split(';\nfunction bytes',1)[0])
page = build_viewer_html(display,title='Voimatalo · 开发助手推理草稿（内部为假设）')
anchor = '  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();'
assert page.count(anchor)==1
page = page.replace(anchor,extension.replace('__RAW__',json.dumps(raw,separators=(',',':')))+anchor)
buttons = '<aside style="position:fixed;left:33%;top:10px;z-index:200;background:#fffe;padding:9px">'+''.join(f'<button data-transfer-mode="{k}">{v}</button>' for k,v in [('bim','实际BIM'),('input','原始纹理'),('overlay','按记录坐标叠合')])+'</aside>'
page = page.replace("row('floors',BASES.length)", "row('基准标高组',BASES.length)")
page = page.replace('<body>','<body>'+buttons,1).replace("label('N','#d32f2f'","label('y (local)','#d32f2f'")
(args.out/'overlay.html').write_text(page)
style = '<style>body{font:16px/1.6 system-ui;margin:24px;color:#233b4c}a{color:#116b7a}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:16px}figure{margin:0;border:1px solid #cdd5dc;padding:10px}img{width:100%}iframe{width:100%;height:800px;border:1px solid #cdd5dc}</style>'
(args.out/'observations.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>开发助手实际源反馈</title>'+style+'<h1>原网格上的实际源叠图</h1><p>紫色为源墙边，绿色为窗，橙色为门。源线穿透显示，背面的边也会显示；扫描缺面不代表真实透空。这些是开发生成后的检查，不是Sonnet收到的反馈。</p><main>'+''.join(cards)+'</main><h2>包含贯通核心的真实高度剖切</h2><p>内部为假设；跨层核心沿实际高度相交显示，没有添加楼板。</p><main>'+''.join(panels)+'</main></html>')
counts = {'spaces':len(source['spaces']), 'windows':sum(o['kind']=='window' for o in source['openings']), 'doors':sum(o['kind']=='door' for o in source['openings']), 'connections':len(source['connections'])}
notes=''.join('<li>'+html.escape(note)+'</li>' for note in source['generation']['unresolved'])
candidate_name = args.candidate.name
(args.out/'index.html').write_text(f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>Voimatalo 开发示范草稿</title>{style}<h1>Voimatalo · 开发助手的部分推理草稿</h1><p>原单体网格＋建筑声明，经开发助手观察、量测和确定性装配。尚无工作模型达标案例，本页也不是工作模型成绩。</p><p>8个主楼楼层 · {counts["spaces"]}个空间体 · {counts["windows"]}组窗 · {counts["doors"]}处门。内部布局和门为假设；短端及局部缺面用未知围护表示。开口与屋顶仍有未完成项。</p><p><a href="overlay.html">打开旋转查看</a> · <a href="observations.html">原网格叠图与水平剖切</a> · <a href="../{candidate_name}/source_model.json">源BIM</a> · <a href="../{candidate_name}/report.json">源检查</a> · <a href="../README.md">方法和范围</a></p><iframe src="overlay.html" title="原网格/BIM/叠合"></iframe><h2>仍需继续处理</h2><ul>{notes}</ul></html>')
(args.out/'packaging.json').write_text(json.dumps({'candidate':candidate_name,'source_model_sha256':source['source_model_sha256'],'mesh_frame':frame,'source_mutated':False,'fitted_during_packaging':False,'counts':counts,'raster_overlays':len(cards),'height_sections':len(panels)},indent=2)+'\n')
print(json.dumps(counts))
