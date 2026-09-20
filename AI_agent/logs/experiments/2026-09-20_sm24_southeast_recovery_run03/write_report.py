"""Create a read-only visual report from completed generation and evaluation."""
import html
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
PREVIOUS = RUN.parent / '2026-09-20_sm24_host_recovery_run02'


def read(path):
    return json.loads(path.read_text())


def main():
    summary = read(RUN / 'summary.json')
    candidate = summary['delivery']['candidate']
    source = read(RUN / candidate / 'source_model.json')
    previous = read(PREVIOUS / 'candidate_01/source_model.json')
    aligned = read(RUN / 'frame_aligned_partition.json')['frame_aligned_reference_partition']
    old_spaces = {s['id']: s for s in previous['spaces']}
    changed = [s['id'] for s in source['spaces'] if s['id'] not in old_spaces or
               s['polygon'] != old_spaces[s['id']]['polygon']]
    matches = [m for m in aligned['comparison']['matches'] if m['candidate_id'] in changed]
    old_openings = {o['id']: o for o in previous['openings']}
    connections = []
    for opening in source['openings']:
        old = old_openings.get(opening['id'])
        if opening['kind'] == 'door' and (old is None or old['space_ids'] != opening['space_ids']):
            connections.append({'id': opening['id'], 'before': old['space_ids'] if old else None,
                                'after': opening['space_ids'], 'vertices': opening['vertices']})
    audit = {'source_model_sha256': source['source_model_sha256'],
             'changed_source_spaces': changed, 'local_partition_matches': matches,
             'changed_door_space_membership': connections,
             'whole_partition_status': aligned['status'],
             'evaluation_only': True,
             'limits': ['Reference partition comparison does not verify internal door dimensions.',
                        'This is a developer-scoped saved-plan recovery, not a cold start.',
                        'Whole-building limitations include inherited door heights and West window heads.']}
    (RUN / 'local_quality.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    rows = ''.join(f'<tr><td>{html.escape(m["candidate_id"])}</td><td>{m["iou"]:.4f}</td>'
                   f'<td>{m["boundary_hausdorff_m"]:.4f} m</td><td>{html.escape(m["status"])}</td></tr>'
                   for m in matches)
    doors = ''.join(f'<tr><td>{html.escape(m["id"])}</td><td>{html.escape(str(m["before"]))}</td>'
                    f'<td>{html.escape(str(m["after"]))}</td></tr>' for m in connections)
    overlay_files = sorted((RUN / 'image_overlays').glob('*.png'))
    overlay = str(overlay_files[-1].relative_to(RUN))
    findings = html.escape(read(RUN / 'assessment.json')['conclusion_zh'])
    body = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>sm24 东南空间续修</title><style>body{{max-width:1250px;margin:30px auto;padding:0 20px;font:17px/1.6 system-ui;color:#243247;background:#f5f7fa}}a{{color:#175da4}}figure{{margin:18px 0;padding:15px;background:white;border-radius:9px}}img{{max-width:100%;max-height:950px;display:block;margin:auto}}table{{border-collapse:collapse;background:white}}th,td{{border:1px solid #ccd4df;padding:8px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.note{{padding:16px;border-left:5px solid #517eac;background:#eaf1fa}}@media(max-width:750px){{.pair{{grid-template-columns:1fr}}}}</style>
<h1>东南隔墙、空间与门连通续修</h1><p class="note">{findings}</p>
<p>从上轮已修东侧开口的墙网恢复，开发侧限定检查区域；原五图与建筑声明保留，生成时无GT或正确坐标。耗时{summary['elapsed_seconds']:.2f}秒。</p>
<p><a href="{candidate}/viewer.html">旋转查看实际模型</a> · <a href="README.md">范围与验证</a> · <a href="scope_verification.json">改动范围核验</a> · <a href="assessment.json">质量结论</a></p>
<h2>实际源回叠原图</h2><div class="pair"><figure><figcaption>续修前：东南隔墙与内门缺失</figcaption><img src="../2026-09-20_sm24_host_recovery_run02/image_overlays/overlay_002.png"></figure><figure><figcaption>本轮最终候选</figcaption><img src="{overlay}"></figure></div>
<h2>发生变化的空间：生成后独立对照</h2><p>IoU为面积交并比，越接近1越一致。仅按原图总长声明[0,20,0]平移，没有拟合GT；整案状态仍为{html.escape(aligned['status'])}。</p>
<table><tr><th>实际空间</th><th>面积交并比</th><th>最大边界偏差</th><th>评价</th></tr>{rows}</table>
<h2>门所属空间的变化</h2><p>单个空间表示外门；两个空间表示室内连接。原门顶点保持情况由范围核验单独记录。</p><table><tr><th>门</th><th>原空间</th><th>当前空间</th></tr>{doors}</table>
<figure><figcaption>最终实际源平面</figcaption><img src="{candidate}/plan_F1.png"></figure>
<p>独立核验仅在生成结束后运行。源自洽与离线可查看不等于整楼保真通过。</p></html>'''
    (RUN / 'index.html').write_text(body)


if __name__ == '__main__':
    main()
