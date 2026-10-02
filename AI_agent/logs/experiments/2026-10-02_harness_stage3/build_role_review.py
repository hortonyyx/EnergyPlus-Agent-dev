"""Build a local, source-linked review page without copying image bytes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def build(run_roots, output, evaluations):
    records = []
    for run_root in run_roots:
        for path in sorted(run_root.glob("*/role_case.json")):
            row = json.loads(path.read_bytes())
            row["batch"] = run_root.name
            records.append(row)
    manifest = json.loads((HERE / "role_cases/manifest.json").read_bytes())
    references = json.loads((HERE / "role_cases/references.json").read_bytes())
    evaluated = json.loads(evaluations.read_bytes()) if evaluations and evaluations.is_file() else {}
    data = {"runs": records, "cases": manifest["cases"], "references": references["cases"],
            "evaluation": evaluated}
    for case in data["cases"]:
        for row in case["images"]:
            row["href"] = os.path.relpath(ROOT / row["path"], output.parent)
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    document = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>阶段 3 · 局部观察角色复核</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font:16px/1.55 system-ui,sans-serif;max-width:1400px;margin:28px auto;padding:0 24px;color:#20252a;background:#f7f8fa}
h1{font-size:28px}h2{font-size:21px}small{color:#4c5966}select{font:inherit;max-width:100%;padding:8px;margin:6px 14px 6px 0}
article{background:white;padding:22px;border:1px solid #d8dde4;border-radius:10px;margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f8;padding:12px}
.row{display:grid;grid-template-columns:minmax(300px,1.2fr) minmax(270px,1fr);gap:24px}.visual{width:100%;height:auto;border:1px solid #d8dde4}.status{font-weight:700;color:#92431a}.good{color:#126443}.facts{font-size:14px;color:#48505b}li{margin:7px 0}
.ref{fill:none;stroke:#19a264;stroke-width:3;stroke-dasharray:9 6;vector-effect:non-scaling-stroke}.obs{fill:#0078d418;stroke:#0078d4;stroke-width:2;vector-effect:non-scaling-stroke}
@media(max-width:800px){.row{display:block}}a{color:#1468a0}label{display:inline-block;margin:8px 16px 8px 0}
</style>
<h1>阶段 3 · 局部观察角色复核</h1>
<p>本页展示所有保留的角色运行。蓝框为模型返回的原图定位，绿虚线为人工参照范围；参照框只是复核提示，不按像素交并比自动判对。失败和格式错误同样保留。没有真实照片，照片题使用明确标记的渲染代替品。</p>
<p>JSON 合法不等于建筑判断正确。当前页面只展示可见答案、工具行为和用量，不展示模型公开的思考全文；完整请求和回包在无损证据归档中。</p>
<select id="case"><option value="">全部题目</option></select><select id="model"><option value="">全部模型</option></select><select id="batch"><option value="">全部批次</option></select>
<label><input id="reference" type="checkbox" checked>显示人工参照框</label><label><input id="observation" type="checkbox" checked>显示模型定位框</label>
<div id="count"></div><main id="main"></main>
<script id="data" type="application/json">__DATA__</script><script>
const D=JSON.parse(document.getElementById('data').textContent), $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const c of D.cases)$('case').insertAdjacentHTML('beforeend',`<option value="${esc(c.case_id)}">${esc(c.case_id)}</option>`);
for(const key of ['model','batch'])for(const value of [...new Set(D.runs.map(r=>r[key]))])$(key).insertAdjacentHTML('beforeend',`<option>${esc(value)}</option>`);
function rect(box, cls, text){const [x,y,x1,y1]=box;return `<rect class="${cls}" x="${x}" y="${y}" width="${x1-x}" height="${y1-y}"><title>${esc(text)}</title></rect>`;}
function section(title, rows){return `<h3>${title}</h3><ul>${(rows||[]).map(x=>`<li>${esc(x.statement)}</li>`).join('')||'<li>未提供</li>'}</ul>`;}
function draw(){const runs=D.runs.filter(r=>['case','model','batch'].every(k=>!$(k).value||r[k==='case'?'case_id':k]===$(k).value));
$('count').textContent=`显示 ${runs.length} / ${D.runs.length} 个运行。`;
$('main').innerHTML=runs.map(r=>{const c=D.cases.find(c=>c.case_id===r.case_id), ref=D.references.find(x=>x.case_id===r.case_id), source=c.images[0], result=r.outcome.result;
const refs=$('reference').checked?(ref.expected_localizations||[]).map(b=>rect(b.bbox_px,'ref',b.label)).join(''):'';
const obs=$('observation').checked&&result?(result.directly_seen||[]).map(b=>rect(b.location.box_original_pixels,'obs',b.observation_id+': '+b.statement)).join(''):'';
const review=(D.evaluation.results||[]).find(x=>x.batch===r.batch&&x.run_id===r.run_id);
const usage=(r.usage||[]).filter(u=>u.kind==='reported').map(u=>u.raw_usage);const tokens=usage.reduce((s,u)=>s+(u.total_tokens||0),0);
const body=result?section('直接看到',result.directly_seen)+section('解释',result.interpretations)+section('不确定',result.uncertain):`<pre>${esc(r.outcome.validation_error||r.outcome.runtime?.answer||'没有返回可采用的局部观察结果。')}</pre>`;
return `<article><h2>${esc(r.batch)} · ${esc(r.model)} · ${esc(c.case_id)}</h2><p>${esc(c.question)}</p><p class="facts">题组 ${esc(c.test_group)} · 输入 ${esc(c.input_kind)} · 信息 ${esc(c.information_sufficiency)} · 照片代替品 ${c.photo_surrogate?'是':'否'}</p><p class="status">运行状态：${esc(r.status)}${review?' · 人工结论：'+esc(review.verdict):''}</p>${review?`<p>${esc(review.reason)}</p>`:''}<div class="row"><div><svg class="visual" viewBox="0 0 ${source.width_px} ${source.height_px}" xmlns="http://www.w3.org/2000/svg"><image href="${esc(source.href)}" width="${source.width_px}" height="${source.height_px}"/>${refs}${obs}</svg><small>原图 ${source.width_px} × ${source.height_px} · <a href="${esc(source.href)}">打开原图</a><br>SHA-256 ${esc(source.sha256)}</small></div><div>${body}<p class="facts">模型请求 ${r.model_requests} · 实报 token ${tokens} · 收到用量 ${usage.length}/${r.model_requests} 条</p></div></div></article>`;}).join('');}
for(const id of ['case','model','batch','reference','observation'])$(id).addEventListener('change',draw);draw();
</script></html>'''
    output.write_text(document.replace("__DATA__", payload), encoding="utf-8")
    return {"page": str(output), "runs": len(records), "image_bytes_copied": 0}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs", type=Path, action="append", required=True)
    p.add_argument("--out", type=Path, default=HERE / "role_review.html")
    p.add_argument("--evaluations", type=Path)
    args = p.parse_args()
    if not args.out.resolve().is_relative_to(ROOT):
        raise ValueError("review output must stay in this worktree")
    print(json.dumps(build(args.runs, args.out, args.evaluations), ensure_ascii=False))
