"""Standalone inspection page for completed caller observations, not a BIM score."""
import argparse
import html
import json
from pathlib import Path


def esc(value):
    return html.escape(str(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run
    parts = ['''<!doctype html><html lang="zh"><meta charset="utf-8">
<title>sm24 原图局部开口观察</title><style>
body{font:16px/1.6 system-ui;max-width:1200px;margin:32px auto;padding:0 20px;color:#172536}
table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #cbd5e1;padding:8px;text-align:left}
img{max-width:100%;background:#000}pre{white-space:pre-wrap;background:#f1f5f9;padding:16px}
.sources{display:grid;grid-template-columns:1fr 2fr;gap:16px;align-items:start}
@media(max-width:700px){.sources{grid-template-columns:1fr}}
</style><h1>sm24 原图局部开口观察</h1>
<p>工作模型只收到两张原图和东侧观察任务。以下为它提交的观察及双方向计算，
不能当作独立验收或整案 BIM 成绩；语义核验见 README。</p>
<p><a href="README.md">结果与限制</a> · <a href="answer.md">模型原答</a> ·
<a href="verification.json">输入与工具返回核验</a></p>
<div class="sources"><a href="images/1f_view.png"><img alt="原始平面图" src="images/1f_view.png"></a>
<a href="images/East_view.png"><img alt="原始东立面" src="images/East_view.png"></a></div>''']
    for path in sorted(run.glob("facade_comparisons/*.json")):
        record = json.loads(path.read_text())
        parts.append(f'<h2>{esc(path.stem)}</h2><p><a href="facade_comparisons/{esc(path.name)}">原始记录</a></p>')
        parts.append('<table><tr><th>图</th><th>原图轴标定</th><th>开口 ID</th><th>原图像素区间</th><th>类型（模型判读）</th></tr>')
        for view in ("plan", "elevation"):
            data = record["observations"][view]
            for opening in data["openings"]:
                parts.append(f'<tr><td>{view}</td><td>{esc(data["axis_anchors"])}</td>'
                             f'<td>{esc(opening["id"])}</td><td>{esc(opening["pixels"])}</td>'
                             f'<td>{esc(opening.get("kind", opening.get("type", "未标")))}</td></tr>')
        parts.append('</table><table><tr><th>方向</th><th>均值误差 m</th><th>最大误差 m</th></tr>')
        for direction, data in record["directions"].items():
            parts.append(f'<tr><td>{esc(direction)}</td><td>{esc(data["mean_abs_endpoint_residual_m"])}</td>'
                         f'<td>{esc(data["max_abs_endpoint_residual_m"])}</td></tr>')
        parts.append('</table><pre>' + esc(json.dumps(record["direction_separation"], ensure_ascii=False, indent=2)) + '</pre>')
    parts.append('</html>')
    with (run / "index.html").open("x") as handle:
        handle.write("\n".join(parts))


if __name__ == "__main__":
    main()
