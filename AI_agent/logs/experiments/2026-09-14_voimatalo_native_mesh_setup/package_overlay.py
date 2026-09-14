"""Post-run overlay uses the model's DECLARED yaw, never fits its output to mesh."""
from pathlib import Path
import json,re,runpy,sys
ROOT=Path(__file__).resolve().parents[4]
run=Path(sys.argv[1]).resolve();candidate=json.loads((run/'delivery.json').read_text())['candidate']
source=json.loads((run/candidate/'source_model.json').read_text())
proposal=json.loads((run/candidate/'proposal.json').read_text())
matches=re.findall(r'yaw\s*=\s*([+-]?\d+(?:\.\d+)?)', ' '.join(proposal['assumptions']))
assert matches and len(set(matches))==1, 'need one explicit source frame, no inferred alignment'
yaw=float(matches[0])
previous=runpy.run_path(str(ROOT/'AI_agent/logs/experiments/2026-09-14_voimatalo_transfer_setup/package_result.py'))
extension=previous['EXTENSION'].replace('Math.PI/12',f'Math.PI*({yaw})/180')
original=(ROOT/'case_tests/textured_mass/single_buildings/voimatalo/viewer.html').read_text()
data=json.loads(original.split('const data=',1)[1].split(';\nfunction bytes',1)[0])
page=(run/candidate/'viewer.html').read_text().replace('<details open>','<details>')
for name in ['report.json','proposal.json','source_model.json']:page=page.replace('href="'+name+'"','href="'+candidate+'/'+name+'"')
anchor='  (function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();'
assert page.count(anchor)==1
page=page.replace(anchor,extension.replace('__RAW__',json.dumps(data,separators=(',',':')))+anchor)
buttons='<div style="position:fixed;top:12px;left:34%;z-index:200;background:#fffe;padding:10px;border:1px solid #aaa">'+''.join(f'<button data-transfer-mode="{k}">{v}</button>' for k,v in [('bim','实际BIM'),('input','原始纹理'),('overlay','按声明坐标叠合')])+f'<small> 模型声明旋转 {yaw:g}°；不重新拟合</small></div>'
page=page.replace('<body>','<body>'+buttons,1).replace("label('N','#d32f2f'","label('y (local)','#d32f2f'")
(run/'overlay.html').write_text(page)
p=run/'index.html';p.write_text(p.read_text().replace('<a href="observations.html">','<a href="overlay.html">按模型声明坐标叠合</a> · <a href="observations.html">'))
(run/'packaging.json').write_text(json.dumps({'candidate':candidate,'source_hash':source['source_model_sha256'],'declared_yaw_degrees':yaw,'candidate_fitted_to_input':False,'source_mutated':False,'post_run_only':True,'appearance_note':'Overlay displays original atlas without lighting/material tint for visual comparison; actual model observations retain renderer metadata.'},indent=2)+'\n')
print(json.dumps({'candidate':candidate,'yaw':yaw,'overlay':True}))
