"""Package actual native observations and saved BIM without changing either."""
from pathlib import Path
import html,json,os,sys
ROOT=Path(__file__).resolve().parents[4]
run=Path(sys.argv[1]).resolve()
delivery=json.loads((run/'delivery.json').read_text()) if (run/'delivery.json').exists() else None
chosen=delivery['candidate'] if delivery else None
original=ROOT/'case_tests/textured_mass/single_buildings/voimatalo/viewer.html'
frames=f'<iframe title="原三维资产" src="{os.path.relpath(original,run)}"></iframe>'
if chosen:frames+=f'<iframe title="实际源BIM" src="{chosen}/viewer.html"></iframe>'
(run/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Voimatalo 原网格输入实验</title>
<style>body{margin:0;background:#edf1f3;font:16px sans-serif;color:#243442}header{padding:16px}main{display:flex;gap:8px}iframe{width:50%;height:78vh;border:0;background:white}a{color:#176875}</style>
<header><b>原网格直接输入 → Agent按需观察 → 轻量BIM</b><p>本轮不提供预制图片、旧BIM或对齐角度。左侧为原资产交互展示；工作模型实际收到的观察另见下方记录。右侧为本轮实际保存候选，可查看不等于保真通过。</p><a href="observations.html">模型实际生成的观察</a> · <a href="README.md">结果与限制</a> · <a href="delivery.html">交付检查</a></header><main>'''+frames+'</main>')
cards=[]
for p in sorted((run/'mesh_observations').glob('mesh_*.json')):
 m=json.loads(p.read_text());yaw=m['source_coordinate_transform']['yaw_degrees_counterclockwise_about_positive_z'];span=m['view_span_m'];camera=m['camera']
 caption=f'{p.stem} · yaw {yaw:g}° · {span["width"]:.2f} × {span["height"]:.2f} m'
 details={'target':camera['target'],'eye':camera['eye'],'selection_bounds':m['selection_bounds']}
 cards.append(f'<article><a href="mesh_observations/{p.stem}.png"><img src="mesh_observations/{p.stem}.png"></a><b>{html.escape(caption)}</b><details><summary>相机与选区</summary><pre>{html.escape(json.dumps(details,indent=2))}</pre><a href="mesh_observations/{p.name}">完整量测映射</a></details></article>')
(run/'observations.html').write_text('''<!doctype html><meta charset="utf-8"><title>Agent实际观察</title><style>body{font:16px sans-serif;margin:24px;background:#edf1f3;color:#243442}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(450px,1fr));gap:18px}article{background:white;padding:12px;border-radius:8px}img{width:100%}pre{white-space:pre-wrap}</style><h1>Agent实际选择的原网格观察</h1><p>每张图由本次工作模型调用工具生成，保留原像素和三维映射。无光照、双面基础色观察；三角面缺失或选区外空白不证明真实建筑开敞。点击看原分辨率。</p><a href="index.html">返回模型对照</a><main>'''+''.join(cards)+'</main>')
print(json.dumps({'chosen':chosen,'observations':len(cards),'index':str(run/'index.html')}))

if not chosen:
 p=run/'index.html';text=p.read_text().replace('原网格直接输入 → Agent按需观察 → 轻量BIM','原网格直接输入 → 局部观察验证（不生成BIM）').replace('右侧为本轮实际保存候选，可查看不等于保真通过。','本次只核对局部观察，不生成或修改BIM。').replace(' · <a href="delivery.html">交付检查</a>','').replace('iframe{width:50%;','iframe{width:100%;');p.write_text(text)
