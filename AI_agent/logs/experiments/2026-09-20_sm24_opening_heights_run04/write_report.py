"""Render the completed, post-generation exterior-height comparison."""
import html
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def main():
    summary = load(RUN / 'summary.json')
    candidate = summary['delivery']['candidate']
    comparison = load(RUN / 'opening_comparison.json')['translated_frame']
    assessment = load(RUN / 'assessment.json')
    previous = load(RUN.parent / '2026-09-20_sm24_southeast_recovery_run03/candidate_01/source_model.json')
    old = {item['id']: sorted(set(v[2] for v in item['vertices'])) for item in previous['openings']}
    rows = ''
    for item in comparison['matches']:
        def heights(values):
            return ' / '.join(f'{v:.3f}' for v in values)
        rows += '<tr>' + ''.join(f'<td>{html.escape(value)}</td>' for value in [
            item['facade'], item['source_id'], heights(old[item['source_id']]),
            heights(item['source_z_m']), heights(item['gt_z_m']),
            f'{max(abs(v) for v in item["z_endpoint_delta_m"]):.6f}']) + '</tr>'
    figures = ''
    for side in ('North', 'South', 'East', 'West'):
        figures += f'<h2>{side}</h2><div class="pair"><figure><figcaption>原立面</figcaption><img src="images/{side}_view.png"></figure><figure><figcaption>最终实际源立面</figcaption><img src="{candidate}/elevation_{side}.png"></figure></div>'
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>sm24 外门窗高度续修</title><style>body{{max-width:1300px;margin:30px auto;padding:0 20px;font:17px/1.6 system-ui;color:#253247;background:#f5f7fa}}a{{color:#175da4}}figure{{margin:8px 0;padding:12px;background:white;border-radius:8px}}img{{max-width:100%;display:block;margin:auto}}table{{border-collapse:collapse;background:white;font-size:15px}}td,th{{padding:7px;border:1px solid #cdd4de}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}.note{{background:#eaf2fa;padding:16px;border-left:5px solid #467bac}}@media(max-width:750px){{.pair{{grid-template-columns:1fr}}}}</style>
<h1>外门窗竖向基准与高度续修</h1><p class="note">{html.escape(assessment['conclusion_zh'])}</p>
<p>从已恢复东南房间的墙网局部续修，Sonnet运行{summary['elapsed_seconds']:.2f}秒。开发指定外开口高度范围，生成时无GT或正确数值。</p>
<p><a href="{candidate}/viewer.html">旋转查看模型</a> · <a href="README.md">过程与边界</a> · <a href="scope_verification.json">改动核验</a> · <a href="opening_comparison.json">生成后独立对照</a></p>
<h2>全部可比外开口：底 / 顶高度（米）</h2><table><tr><th>立面</th><th>开口</th><th>此前</th><th>当前</th><th>独立参照</th><th>最大高度差</th></tr>{rows}</table>
<p>下图源立面按各面轴向绘制（方向见图下方），按开口身份与原立面对应。高度对照不认证平面分区、内门高度或细部构造。</p>{figures}
<p>评测仅在生成结束后执行。平面沿用原图总长支持的[0,20,0]平移，没有拟合GT或回写源模型；其他墙位偏差继续保留。</p></html>'''
    (RUN / 'index.html').write_text(page)


if __name__ == '__main__':
    main()
