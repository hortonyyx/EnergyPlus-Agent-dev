#!/usr/bin/env python3
"""Create a local comparison page from the two frozen historical pilot rounds."""
from collections import Counter
from html import escape
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent.parent / "2026-09-21_historical_sm21_pilot_run01"
scores = json.loads((RUN / "controller_evaluation/legacy_scores.json").read_text())
parts = ['''<!doctype html><html lang="zh"><meta charset="utf-8">
<title>sm21 旧方法独立试跑</title><style>
body{max-width:1350px;margin:24px auto;padding:0 20px;font:17px/1.6 sans-serif;background:#f5f6f8;color:#17202a}
img{width:100%;height:auto;background:#111;border:1px solid #bbb}figure{margin:20px 0}
table{border-collapse:collapse}td,th{padding:8px 18px;border:1px solid #bbb}a{color:#1454a0}
</style><h1>sm21 旧规则/CV：一层独立试跑</h1>
<p>两轮均未通过原图核查，没有新 BIM。第二轮收到原图问题反馈后，标定锚点仍完全不变。
旧规则/六 CV 工具来自 723；宿主改成白名单 MCP，排除同墙网示例，无任意脚本能力，因此不是完整历史环境重放。</p>
<p>红线为提交墙，蓝框为提交窗；原图的青色线不是本次提交。
下方旧评分在两轮冻结后才由评测侧读取 GT，不回灌模型，也不折算整案百分制。</p>
<p><a href="README.md">完整说明</a> · <a href="controller_evaluation/legacy_scores.json">旧坐标评分</a> ·
<a href="controller_evaluation/legacy_gate.json">旧结构检查</a></p>
<figure><figcaption>原始一层图</figcaption><img src="workspace/case_data/1f_view.png" alt="原始一层平面"></figure>''']
for label, number in [("pilot_01", "001"), ("pilot_02", "002")]:
    folder = RUN / "invocations" / label
    receipt = json.loads((folder / "receipt.json").read_text())
    base = f"invocations/{label}/snapshot/0_reading/submissions/{number}"
    reading = json.loads((RUN / base / "1f_view.json").read_text())
    counts = Counter(s["pen"] for s in reading["strokes"])
    score = scores[label]
    parts.append(f'''<h2>{escape(label)}：未通过</h2>
<p>{receipt['elapsed_seconds']:.3f} 秒；{counts['wall']} 墙线、{counts['window']} 窗框、{len(reading['dimensions'])} 条尺寸。
旧一层评分墙命中 {score['wall_hits'][0]}/{score['wall_hits'][1]}，窗命中 {score['window_hits'][0]}/{score['window_hits'][1]}。
外围数字边界 4/4 不检查原图配准，不能抵消下图错位。</p>
<p><a href="invocations/{label}/answer.md">模型原结论（包含错误自检）</a> ·
<a href="invocations/{label}/source_review.json">开发原图核查</a> ·
<a href="invocations/{label}/verification.json">传输与证据核验</a> ·
<a href="{base}/1f_view.json">可编辑 reading</a></p>
<figure><figcaption>{label} 原图回叠</figcaption><img src="{base}/1f_view_source_overlay.png" alt="{label} 原图回叠"></figure>
<figure><figcaption>{label} 旧工具独立绘图</figcaption><img src="{base}/1f_view_render.png" alt="{label} 独立绘图"></figure>''')
parts.append('</html>')
(RUN / 'index.html').write_text('\n'.join(parts) + '\n')
print(RUN / 'index.html')
