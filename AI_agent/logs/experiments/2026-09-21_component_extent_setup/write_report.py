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
    review_only = json.loads((run / "summary.json").read_text()).get("scope") == "automatically_selected_discrepancy_review"
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
    if review_only:
        parts[0] = parts[0].replace(
            "工作模型只收到两张原图和东侧观察任务。以下为它提交的观察及双方向计算，",
            "复查模型收到两张原图及按最大残差选出的未验证旧观察。复查未通过，原答见上方链接，")
    if json.loads((run / "summary.json").read_text()).get("scope") == "developer_selected_vertical_chain_observation":
        start = parts[0].index('<div class="sources">')
        parts[0] = parts[0][:start] + '<div><a href="images/East_view.png"><img alt="原始东立面" src="images/East_view.png"></a></div>'
        parts[0] = parts[0].replace('工作模型只收到两张原图和东侧观察任务。以下为它提交的观察及双方向计算，', '工作模型只收到原东立面和竖向尺寸链任务。原答及独立语义核验见上方链接，')
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
        parts.append('</table>')
        bindings = record.get("measurement_bindings", [])
        parts.append(f'<details><summary>查看 {len(bindings)} 个量测引用</summary><table><tr><th>坐标槽</th><th>扫描 / 候选</th><th>取值</th><th>原图像素</th></tr>')
        for binding in bindings:
            ref = binding["reference"]
            parts.append(f'<tr><td>{esc(binding["slot"])}</td><td>{esc(ref["profile"])} / {esc(ref["candidate"])}</td>'
                         f'<td>{esc(ref.get("at", "peak"))}</td><td>{esc(binding["resolved_pixel"])}</td></tr>')
        parts.append('</table></details>')
        parts.append('<table><tr><th>方向</th><th>均值误差 m</th><th>最大误差 m</th></tr>')
        for direction, data in record["directions"].items():
            parts.append(f'<tr><td>{esc(direction)}</td><td>{esc(data["mean_abs_endpoint_residual_m"])}</td>'
                         f'<td>{esc(data["max_abs_endpoint_residual_m"])}</td></tr>')
        parts.append('</table><pre>' + esc(json.dumps(record["direction_separation"], ensure_ascii=False, indent=2)) + '</pre>')
    component_paths = sorted(run.glob("pixel_region_overviews/overview_*.json")) + sorted(run.glob("pixel_regions/region_*.json"))
    if component_paths:
        parts.append('<h2>实际连通范围记录</h2><p>彩色连通块不是自动认定的构件；下列范围来自模型自行选择的颜色/种子。</p><table><tr><th>记录</th><th>原图</th><th>范围 / 保留块</th><th>实际预览</th></tr>')
        for path in component_paths:
            record = json.loads(path.read_text())
            extent = record.get("bbox_px", str(len(record.get("candidates", []))) + " 个保留块")
            preview = record.get("region_image", record.get("overview_image"))
            parts.append(f'<tr><td><a href="{esc(path.relative_to(run))}">{esc(path.stem)}</a></td><td>{esc(record["name"])}</td><td>{esc(extent)}</td><td><a href="{esc(preview)}">查看原图与范围</a></td></tr>')
        parts.append('</table>')
    parts.append('</html>')
    with (run / "index.html").open("x") as handle:
        handle.write("\n".join(parts))


if __name__ == "__main__":
    main()
