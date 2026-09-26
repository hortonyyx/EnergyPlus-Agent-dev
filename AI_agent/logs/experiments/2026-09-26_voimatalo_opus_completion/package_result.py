"""Package the 09-26 courtyard-tower completion for offline review.

Reuses the 09-16 packager functions (raster overlays of the source on original
mesh views, source sections, textured/BIM rotating viewer) and the 09-25 plan
panel.  Adds a per-view comparison for the completed part:
original scan | 09-25 candidate_01 on the scan | 09-26 candidate_02 on the scan,
plus local old/new plans.  Nothing here moves or refits the source model.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import runpy
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
OLD_DIR = HERE.parent / '2026-09-16_voimatalo_completion'
PREV_DIR = HERE.parent / '2026-09-25_voimatalo_opus_development'
OLD = runpy.run_path(str(OLD_DIR / 'package_candidate.py'), run_name='voimatalo_package_0916')
PLANS = runpy.run_path(str(PREV_DIR / 'render_plan_comparison.py'), run_name='voimatalo_plan_compare')
from src.agent.geometry.mesh_bim_frame import render_mesh_bim_overlay  # noqa: E402

# (observation directory, view name, caption)
COMPARE_VIEWS = [
    (HERE / 'observations', 'prot_oblique_se', '从内院东南低角度看被裁处'),
    (HERE / 'observations', 'prot_oblique_ne', '从附属低体上空东北方向看被裁处'),
    (PREV_DIR / 'observations', 'court_long_south', '内院长墙南段正视（09-25 观察）'),
    (HERE / 'observations', 'prot_top', '被裁处俯视'),
]
CARD_VIEWS = [(HERE / 'observations', n) for n in ('prot_oblique_se', 'prot_oblique_ne', 'prot_top', 'annex_south_face')] + \
             [(PREV_DIR / 'observations', n) for n in ('court_long_south', 'court_southeast_oblique')]
PLAN_HEIGHTS = [1.5, 14.0]
LOCAL_BOUNDS = (np.array([-15.0, -35.0]), np.array([8.0, -14.0]))


def rel(target: Path, page_dir: Path) -> str:
    return Path(os.path.relpath(target.resolve(), page_dir.resolve())).as_posix()


def label(image: Image.Image, text: str) -> Image.Image:
    out = image.convert('RGB').copy()
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, out.width, 30], fill=(255, 255, 255))
    d.text((8, 6), text, fill=(0, 0, 0), font=PLANS['font'](18))
    return out


def triptych(obs_dir: Path, name: str, prev_source: dict, source: dict, out: Path):
    observation = json.loads((obs_dir / f'{name}.json').read_text())
    picture = Image.open(obs_dir / f'{name}.png')
    before, _ = render_mesh_bim_overlay(picture, observation, prev_source, floor_id=None)
    after, _ = render_mesh_bim_overlay(picture, observation, source, floor_id=None)
    panels = [label(picture, '1 original scan (input.glb)'), label(before, '2 09-25 candidate_01 on scan'),
              label(after, '3 09-26 candidate_02 on scan')]
    height = max(p.height for p in panels)
    canvas = Image.new('RGB', (sum(p.width for p in panels) + 20, height), '#888888')
    x = 0
    for p in panels:
        canvas.paste(p, (x, 0))
        x += p.width + 10
    canvas.save(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, default=HERE / 'candidate_02')
    parser.add_argument('--prev-candidate', type=Path, default=PREV_DIR / 'candidate_01')
    parser.add_argument('--out', type=Path, default=HERE / 'result_02')
    args = parser.parse_args()
    candidate, output = args.candidate.resolve(), args.out.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    feedback, compare, plan_dir = output / 'feedback', output / 'compare', output / 'plans'
    for d in (feedback, compare, plan_dir):
        d.mkdir()
    source = json.loads((candidate / 'source_model.json').read_text())
    display = json.loads((candidate / 'display_geometry.json').read_text())
    prev_source = json.loads((args.prev_candidate.resolve() / 'source_model.json').read_text())

    compare_cards = []
    for obs_dir, name, caption in COMPARE_VIEWS:
        triptych(obs_dir, name, prev_source, source, compare / f'{name}.png')
        compare_cards.append(f'<figure><figcaption>{html.escape(caption)}：原扫描 ｜ 09-25 候选叠在原扫描上 ｜ 本轮候选叠在原扫描上'
                             f'</figcaption><a href="compare/{name}.png"><img src="compare/{name}.png"></a></figure>')
    plan_cards = []
    for z in PLAN_HEIGHTS:
        left = PLANS['panel'](prev_source, z, '09-25 candidate_01 (south end)', LOCAL_BOUNDS, size=(640, 640))
        right = PLANS['panel'](source, z, '09-26 candidate_02 (south end)', LOCAL_BOUNDS, size=(640, 640))
        both = Image.new('RGB', (left.width + right.width + 10, left.height), '#888888')
        both.paste(left, (0, 0))
        both.paste(right, (left.width + 10, 0))
        name = f'plan_compare_z{z:g}.png'
        both.save(plan_dir / name)
        plan_cards.append(f'<figure><figcaption>南端局部平面 z={z:g} m：左 09-25，右本轮</figcaption>'
                          f'<a href="plans/{name}"><img src="plans/{name}"></a></figure>')

    cards = [OLD['observation_card'](source=source, observation_dir=obs_dir.resolve(), name=name, floor_id=None,
                                     output_dir=feedback, output_stem=f'{obs_dir.parent.name[:10]}_{name}',
                                     caption_prefix=('09-26新观察 · ' if obs_dir.parent == HERE else '09-25观察 · '))
             for obs_dir, name in CARD_VIEWS]
    section_heights = OLD['default_section_heights'](source)
    section_cards = [OLD['source_section'](source, z, feedback) for z in section_heights]
    (output / 'overlay.html').write_text(OLD['build_overlay_viewer'](source, display, OLD['DEFAULT_RAW_VIEWER'].resolve()), encoding='utf-8')
    style = ('<style>body{font:16px/1.6 system-ui;margin:24px;color:#233b4c;max-width:1600px}a{color:#116b7a}'
             'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(640px,1fr));gap:16px}figure{margin:0;'
             'border:1px solid #cdd5dc;padding:10px}img{width:100%}iframe{width:100%;height:820px;border:1px solid #cdd5dc}'
             'table{border-collapse:collapse}td,th{border:1px solid #cdd5dc;padding:4px 8px;vertical-align:top}</style>')
    (output / 'observations.html').write_text(
        '<!doctype html><html lang="zh"><meta charset="utf-8"><title>09-26 候选：原网格叠图与剖切</title>' + style
        + '<h1>原网格上的实际源叠图（09-26 候选）</h1><p>紫色为源外墙边，绿色为窗，橙色为门，按记录坐标关系投影；扫描缺面不代表真实透空。</p><main>'
        + ''.join(cards) + '</main><h2>候选源模型水平剖切</h2><p>内部为方案假设；跨层核心和塔体按实际空间相交显示，没有添加中间楼板。</p><main>'
        + ''.join(section_cards) + '</main></html>', encoding='utf-8')

    count = lambda s, kind: sum(o['kind'] == kind for o in s['openings'])
    counts = {'spaces': len(source['spaces']), 'windows': count(source, 'window'), 'doors': count(source, 'door'),
              'unknown_boundaries': sum(1 for b in source['boundaries'] if any(r['condition'] == 'unknown' for r in b.get('enclosure_regions', [])))}
    prev_counts = {'spaces': len(prev_source['spaces']), 'windows': count(prev_source, 'window'), 'doors': count(prev_source, 'door'),
                   'unknown_boundaries': sum(1 for b in prev_source['boundaries'] if any(r['condition'] == 'unknown' for r in b.get('enclosure_regions', [])))}
    links = {'source_model': rel(candidate / 'source_model.json', output), 'report': rel(candidate / 'report.json', output),
             'plan': rel(HERE / 'case_plan_v3.json', output), 'readme': rel(HERE / 'README.md', output),
             'validation': rel(HERE / 'validation/candidate_02_validation.md', output),
             'measure': rel(HERE / 'observations/protrusion_measure.json', output),
             'sections': rel(HERE / 'observations/protrusion_sections.png', output),
             'prev_result': rel(PREV_DIR / 'result_01/index.html', output)}
    rows = [
        ('原扫描看到了什么（观测）', '内院长墙南段 y -25.8 到 -21.9 之间每一层、从地面到约 27 m 都是一个“洞”，从内院看进去直接看到沿街墙的背面；洞的两侧各有一小段从墙面伸出来的侧墙残片（北侧伸出约 1.6 m，南侧约 0.5 m），一直到约 25.6–26 m 高；附属低体的南墙从 x≈2.4 往东是扫描到的朝南外墙（有窗）；俯视图里这块没有任何屋顶残留。'),
        ('怎么解释（判断）', '这是一栋贴在内院墙上的全高小塔体，被“单体裁切”一起切掉了，不是透空、也不是通道。侧墙残片给出宽度（约 4.2 m）和最少伸出量；附属低体南墙露在外面给出最大伸出量（不超过约 2.9 m）。取 1.7 m 深、顶在主屋面 25.25 m。'),
        ('补成了什么（推断）', '一个从首层到七层的连续塔体空间（不加中间楼板），每层一扇门通向南核（F1–F7 共 7 扇）；北面首层段与附属低体贴邻。用途按电梯井塔推断：南核随之改读为电梯厅＋可放次楼梯的核心，其院面多格玻璃竖列在二至七层补为逐层推断窗（6 组，窗高沿用同层旁边已观测的院面窗）。'),
        ('仍不确定', '塔体深度只能约束在约 1.6–2.1 m；用途也可能是卫生间/服务竖向叠层或管井，那样东面可能有小窗；塔顶以上到约 27 m 的扫描洞、玻璃竖列首层段仍标未知；电梯台数、梯段不建模。短翼内院东端扫描洞本轮未处理。'),
    ]
    table = '<table><tr><th>项</th><th>内容</th></tr>' + ''.join(
        f'<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>' for a, b in rows) + '</table>'
    notes = ''.join('<li>' + html.escape(n) + '</li>' for n in source.get('generation', {}).get('unresolved', []))
    (output / 'index.html').write_text(
        f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>Voimatalo 09-26 内院塔体补全（待验收）</title>{style}'
        '<h1>Voimatalo · 09-26 内院被裁突出体补全开发候选（待用户验收）</h1>'
        '<p>Opus 5.5 开发助手在 09-25 candidate_01 之上只补一处外部缺失：内院南段被单体裁切掉的突出体，以及与它相连的南核院面。'
        '其余空间、窗和门与 09-25 完全相同。不是工作模型成绩，内部与用途仍是方案假设。</p>'
        f'<p><b>本轮：</b>{counts["spaces"]}个源空间体 · {counts["windows"]}组窗 · {counts["doors"]}处门 · {counts["unknown_boundaries"]}个含未知区域的边界。'
        f'<br><b>09-25：</b>{prev_counts["spaces"]}个空间体 · {prev_counts["windows"]}组窗 · {prev_counts["doors"]}处门 · {prev_counts["unknown_boundaries"]}个未知边界。</p>'
        f'<p><a href="overlay.html">打开旋转查看（原纹理/BIM/叠合）</a> · <a href="observations.html">原网格叠图与剖切</a> · '
        f'<a href="{html.escape(links["prev_result"])}">09-25 查看页（对照）</a> · <a href="{html.escape(links["source_model"])}">源BIM</a> · '
        f'<a href="{html.escape(links["report"])}">源检查报告</a> · <a href="{html.escape(links["plan"])}">方案声明</a> · '
        f'<a href="{html.escape(links["measure"])}">量测记录</a> · <a href="{html.escape(links["validation"])}">验证</a> · '
        f'<a href="{html.escape(links["readme"])}">说明</a></p>'
        f'<h2>这一处怎么补的</h2>{table}'
        f'<h2>原扫描 / 09-25 / 本轮 对照</h2><p>紫线=源外墙边，绿=窗，橙=门。第 2 格里洞口位置只有一段标“未知”的墙；第 3 格多出伸向内院的塔体轮廓、通向南核的门和玻璃竖列窗。</p>'
        f'<main>{"".join(compare_cards)}</main>'
        f'<h2>网格剖切（量测依据）</h2><main><figure><figcaption>不同高度的原网格水平剖切（彩线），洞口两侧的侧墙残片与附属低体南墙</figcaption>'
        f'<a href="{html.escape(links["sections"])}"><img src="{html.escape(links["sections"])}"></a></figure></main>'
        f'<h2>南端局部平面（首层、标准层）</h2><main>{"".join(plan_cards)}</main>'
        '<h2>旋转查看</h2><iframe src="overlay.html" title="原纹理/BIM/叠合"></iframe>'
        f'<h2>未决</h2><ul>{notes}</ul></html>', encoding='utf-8')
    packaging = {'schema': 'voimatalo_candidate_package_0926_v1', 'candidate': rel(candidate, ROOT),
                 'source_model_sha256': source['source_model_sha256'], 'mesh_frame': source['mesh_frame'],
                 'source_mutated': False, 'fitted_during_packaging': False,
                 'counts': counts, 'prev_counts': prev_counts, 'prev_candidate': rel(args.prev_candidate.resolve(), ROOT),
                 'compare_views': [n for _, n, _ in COMPARE_VIEWS],
                 'raster_overlays': len(cards), 'raw_roof_section_images': 0,
                 'height_sections': section_heights, 'plan_comparison_heights': PLAN_HEIGHTS, 'links': links}
    (output / 'packaging.json').write_text(json.dumps(packaging, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
