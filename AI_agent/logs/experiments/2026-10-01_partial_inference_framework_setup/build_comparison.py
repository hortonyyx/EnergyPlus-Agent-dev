"""Build a small review entry from independently written evaluation facts."""
from html import escape
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / '2026-10-01_partial_inference_developer_tests'


def main():
    data = json.loads((OUTPUT / 'comparison.json').read_text())
    cards = []
    for row in data['models']:
        notes = ''.join(f'<li>{escape(note)}</li>' for note in row['findings'])
        cards.append(f'''<article><h2>{escape(row['label'])}</h2>
<p class="status">{escape(row['verdict'])}</p>
<p>{row['spaces']} 空间 · {row['windows']} 窗组 · {row['doors']} 门 · {row['minutes']:.1f} 分钟</p>
<p><a class="button" href="{escape(row['viewer'])}" target="_blank">打开三维模型 ↗</a>
<a href="{escape(row['review'])}">独立复核记录</a></p>
<ul>{notes}</ul><a href="{escape(row['plan'])}" target="_blank">
<img src="{escape(row['plan'])}" alt="{escape(row['label'])} 标准层源平面"></a>
<p class="muted">实际保存源的标准层平面；点击放大。数量用于说明规模，不代表质量排名。</p></article>''')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>部分推理 · 开发模型验证</title>
<style>body{margin:0;background:#f3f5f8;color:#233044;font:16px/1.65 system-ui,sans-serif}
main{max-width:1440px;margin:auto;padding:32px}h1{font-size:29px;margin:0 0 12px}h2{margin-top:0}
.lead{max-width:1040px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin-top:26px}
article{background:white;border:1px solid #dce2ea;border-radius:12px;padding:22px}img{width:100%;height:auto;border:1px solid #edf0f5}
a{color:#175bb4}.button{display:inline-block;background:#175bb4;color:white;text-decoration:none;padding:8px 14px;border-radius:6px;margin-right:12px}
.status{font-weight:650;color:#945207}.muted,footer{color:#667385;font-size:14px}li{margin:8px 0}footer{margin-top:24px}
@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:18px}}</style><main>
<h1>部分推理建模 · 开发模型验证</h1>'''
    page += f'<p class="lead">{escape(data["conclusion"])}</p>'
    page += '''<p><a href="../2026-10-01_voimatalo_door_revision/result_02/accepted.html" target="_blank">打开用户已验收精细版 ↗</a>
 · <a href="README.md">试验结果与边界</a></p><div class="grid">'''
    page += ''.join(cards) + '</div>'
    page += f'<footer>{escape(data["conditions"])}</footer></main></html>\n'
    (OUTPUT / 'index.html').write_text(page)


if __name__ == '__main__':
    main()
