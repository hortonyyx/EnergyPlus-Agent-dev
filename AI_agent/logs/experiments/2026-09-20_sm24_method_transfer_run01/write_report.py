"""Summarize the completed transfer without changing any generation artifact."""
from collections import Counter
import html
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN.parents[3]))
from scripts.tool_scripts.diagnose_partition_evidence import overlay


def read(name):
    return json.loads((RUN / name).read_text())


def main():
    summary = read('summary.json')
    candidate = summary['delivery']['candidate']
    source = read(f'{candidate}/source_model.json')
    partition = read('frame_aligned_partition.json')['frame_aligned_reference_partition']
    openings = read('opening_comparison.json')['translated_frame']
    events = [json.loads(line) for line in (RUN / 'tools.jsonl').read_text().splitlines()]
    first_build = next(i for i, event in enumerate(events) if event['action'] == 'build_plan_bim')
    drafts = [(p.parent.name, json.loads(p.read_text())) for p in sorted((RUN / 'plan_drafts').glob('*/plan.json'))]
    changes = []
    for (before_name, before), (after_name, after) in zip(drafts, drafts[1:]):
        row = {'before': before_name, 'after': after_name}
        for kind in ('partitions', 'openings'):
            old = {item['id']: item for item in before[kind]}
            new = {item['id']: item for item in after[kind]}
            row[f'deleted_{kind}'] = sorted(old.keys() - new.keys())
            row[f'changed_{kind}'] = [
                {'id': key, 'before': old[key], 'after': new[key]}
                for key in old.keys() & new.keys() if old[key] != new[key]
            ]
        changes.append(row)
    report = {
        'result': 'method_transfer_failed', 'candidate': candidate,
        'generation_code_commit': 'ffad2b65',
        'source_geometry_validation': source['validation']['status'],
        'counts': {'spaces': len(source['spaces']), **dict(Counter(o['kind'] for o in source['openings']))},
        'elapsed_seconds': summary['elapsed_seconds'],
        'cli_estimated_cost_usd': summary['estimated_cost_usd'],
        'tool_counts': dict(Counter(e['action'] for e in events)),
        'actions_after_first_build': dict(Counter(e['action'] for e in events[first_build + 1:])),
        'draft_changes': changes,
        'frame_translation_m': [0, 20, 0],
        'frame_basis': read('frame_aligned_partition.json')['translation_basis'],
        'partition_status': partition['status'],
        'topology_findings': partition['topology_findings'],
        'opening_overlap_correspondences': len(openings['matches']),
        'overlap_is_not_accuracy': True,
        'unmatched_reference_openings': openings['missing_gt_openings'],
        'unmatched_source_openings': openings['extra_source_openings'],
        'findings': [
            '东南折角墙和门在编译返工中删除，东南房间与走廊合并；这不是合法源简化。',
            '东立面左右方向未与平面核对，两短窗和外门错位；长窗又被裁短约1.69米。',
            '西侧四扇小窗统一采用大窗高度，窗顶高约0.60米。',
            '三外门底顶采用0–2.4米；相对图示/参照底顶约低0.20米，地坪语义仍需区分。',
            '首份build后无新的原图查看或像素量测；连续四次返工主要消除编译错误。',
        ],
        'limits': [
            '单次Sonnet独立运行，无旧几何或开发坐标输入；不证明其他模型或换例的上限。',
            'GT仅在生成结束后评价；平移只统一原点，未缩放、旋转或拟合参照。',
            '内门无逐门GT；漏门结论由原图与草稿删除记录支持。',
            '后续开口失败局部反馈若已加入代码，不属于本次运行能力，须另验效果。',
        ],
    }
    (RUN / 'quality_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    svg = overlay(partition['reference_spaces'], partition['candidate_spaces'], 'F1')
    rows = ''.join(
        '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in (
            row['source_id'], row['kind'], row['facade'], row['center_abs_error_m'],
            row['width_error_m'], row['z_endpoint_delta_m'])) + '</tr>'
        for row in openings['matches'])
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>sm24 工作模型方法迁移：未通过</title><style>
body{font:16px/1.65 system-ui;max-width:1300px;margin:32px auto;padding:0 20px;background:#f5f7fa;color:#172b3b}
section{background:white;padding:22px;margin:20px 0;border-radius:10px}.warn{border-left:6px solid #ad3535}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.pair img{max-width:100%;max-height:900px;object-fit:contain}
figure{margin:0}svg{width:100%;max-height:850px}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}
a{color:#165da9}@media(max-width:700px){.pair{grid-template-columns:1fr}table{font-size:12px}}
</style><h1>还原方法迁移：本次未通过</h1>
<section class="warn"><p>Sonnet 从五张原图与建筑声明独立生成了7空间、11窗、9门。
几何自洽，源与显示重放、实际离线查看均通过；但东南房间错并、东侧门窗错位，不能替换已有采用基点。</p>
<p>通用方法参考已送达；没有旧BIM、开发坐标、正确数量或GT进入生成。实际运行963.36秒，CLI估算$2.6217162，非订阅账单。</p>
<p><a href="candidate_01/viewer.html">旋转查看失败候选</a> · <a href="../2026-09-16_sm24_developer_reconstruction/index.html">已有开发示范</a> ·
<a href="README.md">过程与限制</a> · <a href="quality_audit.json">改删与质量证据</a></p></section>
<section><h2>原平面与实际源模型</h2><div class="pair"><figure><img src="images/1f_view.png" alt="原平面"><figcaption>原图；东南房间与走廊间存在折角隔墙。</figcaption></figure>
<figure><img src="candidate_01/plan_F1.png" alt="生成源平面"><figcaption>源模型；该隔墙和门被删除，合并为一个空间。</figcaption></figure></div></section>
<section><h2>统一原点后的独立分区对照</h2><p>模型北边y=0、南边y=-20；参照南边y=0。仅平移[0,20,0]，无拟合。
蓝色参照，橙色候选。原坐标与平移后的分区均保留，平移后仍为severe。</p>''' + svg + '''
<p><a href="frame_aligned_partition.json">完整对照</a> · <a href="evaluation/index.html">未经原点转换的原始报告</a></p></section>
<section><h2>门窗逐项差异</h2><p>同类型同立面且沿墙有重叠的11对只是对应候选，不是11项正确。
另外东侧2窗及1外门与参照无重叠，原处缺失、错处新增。单位米；高度差为[底,顶]。</p>
<table><tr><th>源对象</th><th>类型</th><th>立面</th><th>中心误差</th><th>宽差</th><th>高度差</th></tr>''' + rows + '''</table>
<p><a href="opening_comparison.json">全部匹配、漏多项与坐标依据</a></p></section>
<section><h2>核验与下一步</h2><p>五原图与声明字节一致，源和显示数据精确重放，17张有保存对应物的工具返回图逐像素一致；离线旋转与交付页可用。
这些是运输和几何事实，不证明原图保真或用户验收。</p>
<p>本轮后续改动：开口挂墙失败时返回放大的局部原图/声明对照，让后续模型更容易核查报错位置。该改动尚无工作模型效果成绩。</p>
<p><a href="verification.json">重放/输入/用量</a> · <a href="browser_verification.json">离线查看</a> · <a href="viewer_verified.png">实际浏览器截图</a></p></section></html>'''
    (RUN / 'index.html').write_text(document)
    print(json.dumps({key: report[key] for key in ('result', 'counts', 'partition_status', 'opening_overlap_correspondences')}))


if __name__ == '__main__':
    main()
