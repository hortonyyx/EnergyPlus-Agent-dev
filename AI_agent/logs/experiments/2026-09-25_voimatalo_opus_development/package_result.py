"""Package the 09-25 candidate for offline review next to the rejected candidate_04.

Reuses the 09-16 packager functions (raster source overlays on original mesh
views, source sections, textured/BIM overlay viewer) unchanged, and adds the
old/new plan comparison plus the new 09-25 observation views.  Nothing here
moves or refits the source model.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import runpy
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
OLD_DIR = HERE.parent / '2026-09-16_voimatalo_completion'
EVIDENCE = HERE.parent / '2026-09-15_voimatalo_developer_walkthrough/evidence_01'
OLD = runpy.run_path(str(OLD_DIR / 'package_candidate.py'), run_name='voimatalo_package_0916')
PLANS = runpy.run_path(str(HERE / 'render_plan_comparison.py'), run_name='voimatalo_plan_compare')

PRIMARY_VIEWS = ['top:F4', 'street', 'courtyard', 'west:F4', 'north:F6', 'court_long', 'court_short']
NEW_VIEWS = ['west_south', 'court_long_south', 'court_short_corner', 'south_end', 'east_end']
PLAN_HEIGHTS = [1.5, 14.0, 26.5]


def rel(target: Path, page_dir: Path) -> str:
    return Path(os.path.relpath(target.resolve(), page_dir.resolve())).as_posix()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, default=HERE / 'candidate_01')
    parser.add_argument('--out', type=Path, default=HERE / 'result_01')
    parser.add_argument('--old-candidate', type=Path, default=OLD_DIR / 'candidate_04')
    parser.add_argument('--old-result', type=Path, default=OLD_DIR / 'result_04')
    parser.add_argument('--new-observations', type=Path, default=HERE / 'observations')
    args = parser.parse_args()
    candidate, output = args.candidate.resolve(), args.out.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    feedback = output / 'feedback'
    feedback.mkdir()
    source = json.loads((candidate / 'source_model.json').read_text())
    display = json.loads((candidate / 'display_geometry.json').read_text())
    old_source_path = args.old_candidate.resolve() / 'source_model.json'

    cards = []
    for value in PRIMARY_VIEWS:
        name, floor_id = OLD['parse_view'](value)
        cards.append(OLD['observation_card'](source=source, observation_dir=EVIDENCE.resolve(), name=name, floor_id=floor_id,
                                             output_dir=feedback, output_stem=f'primary_{name}', caption_prefix='09-15原观察 · '))
    for name in NEW_VIEWS:
        cards.append(OLD['observation_card'](source=source, observation_dir=args.new_observations.resolve(), name=name, floor_id=None,
                                             output_dir=feedback, output_stem=f'new_{name}', caption_prefix='09-25新观察 · '))
    section_heights = OLD['default_section_heights'](source)
    section_cards = [OLD['source_section'](source, z, feedback) for z in section_heights]

    plan_dir = output / 'plans'
    old_source = json.loads(old_source_path.read_text())
    import numpy as np
    points = np.asarray([p for s in source['spaces'] for p in s['polygon']], float)
    bounds = (points.min(axis=0) - 1.0, points.max(axis=0) + 1.0)
    plan_dir.mkdir()
    plan_cards = []
    for z in PLAN_HEIGHTS:
        left = PLANS['panel'](old_source, z, 'OLD candidate_04 (09-16, user rejected)', bounds)
        right = PLANS['panel'](source, z, 'NEW 09-25 development candidate', bounds)
        from PIL import Image
        both = Image.new('RGB', (left.width + right.width + 10, left.height), '#888888')
        both.paste(left, (0, 0))
        both.paste(right, (left.width + 10, 0))
        name = f'plan_compare_z{z:g}.png'
        both.save(plan_dir / name)
        plan_cards.append(f'<figure><figcaption>旧/新源模型平面 z={z:g}m</figcaption><a href="plans/{name}"><img src="plans/{name}"></a></figure>')

    (output / 'overlay.html').write_text(OLD['build_overlay_viewer'](source, display, OLD['DEFAULT_RAW_VIEWER'].resolve()), encoding='utf-8')
    style = ('<style>body{font:16px/1.6 system-ui;margin:24px;color:#233b4c;max-width:1500px}a{color:#116b7a}'
             'main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}figure{margin:0;'
             'border:1px solid #cdd5dc;padding:10px}img{width:100%}iframe{width:100%;height:820px;border:1px solid #cdd5dc}'
             'table{border-collapse:collapse}td,th{border:1px solid #cdd5dc;padding:4px 8px;vertical-align:top}</style>')
    (output / 'observations.html').write_text(
        '<!doctype html><html lang="zh"><meta charset="utf-8"><title>09-25 候选：原网格叠图与剖切</title>' + style
        + '<h1>原网格上的实际源叠图（09-25 候选）</h1><p>紫色为源外墙边，绿色为窗，橙色为门，按记录坐标关系投影；扫描缺面不代表真实透空。'
        'West/north/top 视图只画指定楼层，其余画全部空间。</p><main>' + ''.join(cards)
        + '</main><h2>候选源模型水平剖切</h2><p>内部为方案假设；跨层核心按实际空间相交显示，没有添加中间楼板。</p><main>'
        + ''.join(section_cards) + '</main></html>', encoding='utf-8')

    counts = {'spaces': len(source['spaces']),
              'windows': sum(o['kind'] == 'window' for o in source['openings']),
              'doors': sum(o['kind'] == 'door' for o in source['openings']),
              'inferred_windows': sum(o['kind'] == 'window' and o['id'].startswith('north_F1_inferred') for o in source['openings']),
              'unknown_boundaries': sum(1 for b in source['boundaries'] if any(r['condition'] == 'unknown' for r in b.get('enclosure_regions', [])))}
    old_counts = {'spaces': len(old_source['spaces']),
                  'windows': sum(o['kind'] == 'window' for o in old_source['openings']),
                  'doors': sum(o['kind'] == 'door' for o in old_source['openings']),
                  'unknown_boundaries': sum(1 for b in old_source['boundaries'] if any(r['condition'] == 'unknown' for r in b.get('enclosure_regions', [])))}
    links = {
        'source_model': rel(candidate / 'source_model.json', output),
        'report': rel(candidate / 'report.json', output),
        'plan': rel(HERE / 'case_plan_v2.json', output),
        'readme': rel(HERE / 'README.md', output),
        'validation': rel(HERE / 'validation/candidate_01_validation.md', output),
        'old_result': rel(args.old_result.resolve() / 'index.html', output),
        'new_observations': rel(args.new_observations.resolve() / 'manifest.json', output),
    }
    rows = [
        ('观测（原网格/纹理，沿用）', '外壳、八层标高、退台与屋盖五部件；287组窗坐标不变；西侧店面玻璃与玻璃店门；两短端扫描系统性缺失与相邻屋面剪影；南端沿街高玻璃竖带（每层两道横带）；无窗沿街带；南北屋顶凸起；内院被裁凸出体的扫描洞'),
        ('推断（本轮新增，均可调整）', '双面走廊办公组织：L形走廊连通南北两端交通组；南端主楼梯间（高玻璃竖带后）+西南主入口、电梯/服务核、卫生间；北端转角楼梯电梯核+服务间；西北角会议/大办公室；首层零售、门厅、后勤；北面首层店面窗5组与3处门、西南主入口门；两短端判为无窗贴邻山墙'),
        ('简化（本档合并）', '同侧连续单间办公室合并为一个办公带；首层零售租户合并；附属低体一个大厅；每对空间一扇代表门；楼梯梯段/电梯井不建实体；屋盖棱柱近似'),
        ('仍未知（保留为未知或未建）', '真实内部隔墙与门位；内院被裁凸出体的深度/用途；短翼内院东端扫描洞；退台两端开口；首层内院缺面；内院南端多格玻璃竖带与暗槽的语义'),
    ]
    table = '<table><tr><th>边界</th><th>内容</th></tr>' + ''.join(
        f'<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>' for a, b in rows) + '</table>'
    notes = ''.join('<li>' + html.escape(n) + '</li>' for n in source.get('generation', {}).get('unresolved', []))
    (output / 'index.html').write_text(
        f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>Voimatalo 09-25 开发候选（待验收）</title>{style}'
        '<h1>Voimatalo · 09-25 内部组织与缺失补全开发候选（待用户验收）</h1>'
        '<p>Opus 5.5 开发助手在 09-16 candidate_04 的外壳/楼层/开口之上重做内部组织，并补全扫描缺失处的合理围护与开口。'
        '不是工作模型成绩，也不是真实内部复原；所有内部分隔与门都是与外部观测约束相容的方案假设。</p>'
        f'<p><b>新候选：</b>{counts["spaces"]}个源空间体 · {counts["windows"]}组窗（其中{counts["inferred_windows"]}组为北面首层补全推断） · '
        f'{counts["doors"]}处门 · {counts["unknown_boundaries"]}个含未知区域的边界。'
        f'<br><b>旧 candidate_04：</b>{old_counts["spaces"]}个空间体 · {old_counts["windows"]}组窗 · {old_counts["doors"]}处门 · '
        f'{old_counts["unknown_boundaries"]}个未知边界。空间数增加不是成功标准。</p>'
        f'<p><a href="overlay.html">打开旋转查看（原纹理/BIM/叠合）</a> · <a href="observations.html">原网格叠图与剖切</a> · '
        f'<a href="{html.escape(links["old_result"])}">旧候选查看页（对照）</a> · <a href="{html.escape(links["source_model"])}">源BIM</a> · '
        f'<a href="{html.escape(links["report"])}">源检查报告</a> · <a href="{html.escape(links["plan"])}">方案与依据</a> · '
        f'<a href="{html.escape(links["validation"])}">验证</a> · <a href="{html.escape(links["readme"])}">说明</a></p>'
        f'<h2>观测 / 推断 / 简化 / 未知</h2>{table}'
        f'<h2>旧/新平面对照（首层、标准层、退台层）</h2><main>{"".join(plan_cards)}</main>'
        '<h2>旋转查看</h2><iframe src="overlay.html" title="原纹理/BIM/叠合"></iframe>'
        f'<h2>未决</h2><ul>{notes}</ul></html>', encoding='utf-8')
    packaging = {'schema': 'voimatalo_candidate_package_0925_v1', 'candidate': rel(candidate, ROOT),
                 'source_model_sha256': source['source_model_sha256'], 'mesh_frame': source['mesh_frame'],
                 'source_mutated': False, 'fitted_during_packaging': False,
                 'counts': counts, 'old_counts': old_counts, 'old_candidate': rel(args.old_candidate.resolve(), ROOT),
                 'reused_functions': 'AI_agent/logs/experiments/2026-09-16_voimatalo_completion/package_candidate.py',
                 'primary_views': PRIMARY_VIEWS, 'new_views': NEW_VIEWS,
                 'raster_overlays': len(cards), 'raw_roof_section_images': 0,
                 'height_sections': section_heights, 'plan_comparison_heights': PLAN_HEIGHTS, 'links': links}
    (output / 'packaging.json').write_text(json.dumps(packaging, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(counts))


if __name__ == '__main__':
    main()
