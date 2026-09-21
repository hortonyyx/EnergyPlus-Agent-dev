"""Render saved original-observation comparisons; does not generate a BIM."""
from pathlib import Path
import html
import json

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / 'comparison.json').read_text())

def bar(label, openings, key):
    pieces = []
    for item in openings:
        a, b = item[key]
        pieces.append(f'<span title="{html.escape(item["id"])}: {a:.3f}—{b:.3f} m" '
                      f'style="left:{a/20*100:.3f}%;width:{(b-a)/20*100:.3f}%"></span>')
    return f'<p>{label}</p><div class="axis">{"".join(pieces)}</div>'

body = ['<h1>平面与立面的两个方向，直接算出来</h1>',
        '<p>sm24东侧原图诊断。开口分组、裁区和标定由开发侧选取；代码仅换算并比较区间。无GT、无旧BIM输入，未送入本批模型运行，也未修改任何源模型。</p>']
body.append(bar('平面：从图上方量到下方（0—20米）', d['normalized_inputs']['plan']['openings'], 'metres'))
for key, label in [('elevation_forward','假设一：立面从左到右与平面从上到下同向'),
                   ('elevation_reverse','假设二：立面方向反过来对应平面')]:
    report = d['directions'][key]
    spans = [{'id':p['elevation_id'],'metres':p['elevation_span_after_direction_m']} for p in report['pairs_by_centre']]
    body.append(bar(label, spans, 'metres'))
    body.append(f'<p>最大端点偏差 <strong>{report["max_abs_endpoint_residual_m"]:.4f} 米</strong>；平均绝对偏差 {report["mean_abs_endpoint_residual_m"]:.4f} 米。</p>')
body += ['<p>这组原图观测明显支持反向对应。它不证明自动识别开口、门窗类型、标高或整楼建模已解决。对称布局无法仅凭区间定向；数量不等时脚本保留所有记录，不给方向结论。</p>',
         '<p><a href="observations.json">输入及开发选择说明</a> · <a href="comparison.json">逐开口对照</a> · <a href="verification.json">核验</a></p>',
         '<details><summary>原平面图</summary><img src="images/1f_view.png" alt="原平面图"></details>',
         '<details><summary>原东立面</summary><img src="images/East_view.png" alt="原东立面"></details>']
(HERE/'index.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>东立面方向对照</title><style>body{max-width:1100px;margin:36px auto;padding:0 22px;font:17px/1.6 sans-serif;color:#183044;background:#f6f8fa}h1{font-size:27px}.axis{height:34px;border-left:2px solid #405b70;border-right:2px solid #405b70;background:#dce4ea;position:relative}.axis span{position:absolute;height:100%;background:#087b9b;border:1px solid white;box-sizing:border-box}img{max-width:100%;background:black}details{margin-top:20px}a{color:#006a8d}</style>'+''.join(body)+'</html>',encoding='utf-8')
