"""Post-run viewing uses the selected source's explicit frame, without fitting."""
from pathlib import Path
import html,json,runpy,sys
ROOT=Path(__file__).resolve().parents[4]
run=Path(sys.argv[1]).resolve()
delivery=json.loads((run/'delivery.json').read_text());candidate=delivery['candidate']
source=json.loads((run/candidate/'source_model.json').read_text());frame=source['mesh_frame']
yaw=frame['yaw_degrees'];tx,ty,tz=frame['translation_m']
previous=runpy.run_path(str(ROOT/'AI_agent/logs/experiments/2026-09-14_voimatalo_transfer_setup/package_result.py'))
extension=previous['EXTENSION'].replace('Math.PI/12',f'Math.PI*({yaw})/180')
extension=extension.replace('aligned[i]=ca*rp[i]+sa*rp[i+2]',f'aligned[i]=ca*rp[i]+sa*rp[i+2]+({tx})').replace('aligned[i+1]=sa*rp[i]-ca*rp[i+2]',f'aligned[i+1]=sa*rp[i]-ca*rp[i+2]+({ty})').replace('aligned[i+2]=rp[i+1]',f'aligned[i+2]=rp[i+1]+({tz})')
original=(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/viewer.html').read_text()
data=json.loads(original.split('const data=',1)[1].split(';\nfunction bytes',1)[0])
page=(run/candidate/'viewer.html').read_text().replace('<details open>','<details>')
for name in ['report.json','proposal.json','source_model.json']:page=page.replace('href="'+name+'"','href="'+candidate+'/'+name+'"')
anchor='  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();'
assert page.count(anchor)==1
page=page.replace(anchor,extension.replace('__RAW__',json.dumps(data,separators=(',',':')))+anchor)
buttons='<div style="position:fixed;top:12px;left:34%;z-index:200;background:#fffe;padding:10px;border:1px solid #aaa">'+''.join(f'<button data-transfer-mode="{k}">{v}</button>' for k,v in [('bim','实际BIM'),('input','原始纹理'),('overlay','按源坐标叠合')])+f'<small> 源声明 {yaw:g}° / 平移{frame["translation_m"]}m；未拟合</small></div>'
page=page.replace('<body>','<body>'+buttons,1).replace("label('N','#d32f2f'","label('y (local)','#d32f2f'")
(run/'overlay.html').write_text(page)
views=[]
for p in sorted((run/'mesh_overlays').glob('overlay_*.json')):
 r=json.loads(p.read_text());views.append(f'<section><h3>{html.escape(r["overlay_id"])} · {html.escape(r["candidate"])} / {html.escape(str(r["floor_id"]))}</h3><p>旋转 {r["mesh_frame"]["yaw_degrees"]:g}° · 平移 {r["mesh_frame"]["translation_m"]} m</p><a href="{r["image_file"]}"><img src="{r["image_file"]}" loading="lazy"></a></section>')
(run/'observations.html').write_text('<!doctype html><meta charset="utf-8"><title>模型实际收到的源叠图</title><style>body{font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:1fr 1fr;gap:18px}img{width:100%}</style><h1>生成过程中的原网格 / 实际源叠图</h1><p>源边为穿透显示辅助线；遮挡背面也显示。底图缺面不等于透空或无窗。</p><main>'+''.join(views)+'</main>')
notes=''.join('<li>'+html.escape(n)+'</li>' for n in source['generation']['unresolved'])
(run/'index.html').write_text(f'''<!doctype html><meta charset="utf-8"><title>Voimatalo · 坐标恢复与原网格反馈</title>
<style>body{{font:16px system-ui;margin:28px;color:#243643}}a{{color:#176777}}iframe{{width:100%;height:760px;border:1px solid #bbb}}li{{margin:.5em 0}}</style>
<h1>Voimatalo · 坐标恢复与原网格反馈</h1><p>Sonnet从上一程候选恢复；原GLB、原声明和旧候选，观察与新坐标由模型选择。保留原数值几何，内部仍为假设。</p>
<p><a href="README.md">结果与限制</a> · <a href="overlay.html">旋转查看：原贴图 / BIM / 按源坐标叠合</a> · <a href="observations.html">模型实际收到的前后叠图</a> · <a href="{candidate}/source_model.json">源BIM</a> · <a href="delivery.html">实际交付检查</a></p>
<p>{len(source['spaces'])}空间 · {sum(o['kind']=='window' for o in source['openings'])}窗 · {sum(o['kind']=='door' for o in source['openings'])}门。坐标改善不等于整案保真通过。</p><iframe src="overlay.html" title="原网格与实际BIM"></iframe><h2>模型保存的未解决项</h2><ul>{notes}</ul>''')
(run/'packaging.json').write_text(json.dumps({'candidate':candidate,'source_hash':source['source_model_sha256'],'mesh_frame':frame,'candidate_fitted_to_input':False,'source_mutated':False,'browser_page_post_run_only':True,'raster_overlays_returned_during_generation':True},indent=2)+'\n')
print(json.dumps({'candidate':candidate,'frame':frame,'overlay_count':len(views)}))
