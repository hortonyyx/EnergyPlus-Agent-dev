"""Summarize post-generation evidence; never edits the model or its input."""
import html
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent


def main():
    comparison = json.loads((RUN / 'opening_comparison.json').read_text())
    east = [row for row in comparison['translated_frame']['matches'] if row['facade'] == 'East']
    audit = {
        'scope': 'developer-scoped recovery of East exterior openings from a failed declaration; not cold start',
        'assessment': 'horizontal placement and window heights improved; door vertical datum unresolved/incorrect; whole-building fidelity failed',
        'evaluation_only_translation_m': comparison['explicit_translation_m'],
        'translation_basis': comparison['translation_basis'],
        'east_openings': east,
        'east_max_horizontal_endpoint_error_m': max(abs(v) for row in east for v in row['endpoint_delta_m']),
        'east_door_vertical_error_m': next(row['z_endpoint_delta_m'] for row in east if row['kind'] == 'door'),
        'original_drawing_review': {
            'reviewer': 'development assistant, after generation',
            'viewed': ['images/East_view.png', 'image_overlays/overlay_002.png', 'candidate_01/elevation_East.png', 'viewer_verified.png'],
            'east_door_dimension_chain_mm': [200, 2400, 1900],
            'finding': 'East original shows door base 200mm above facade baseline and top 2600mm; source uses 0/2400mm while retaining other facade heights. The inherited threshold/frame explanation is not accepted as evidence.',
            'remaining_partition_error': 'SE dogleg partition/door omitted; SE room merged into corridor. Inherited source note claiming no full-height wall remains wrong.',
        },
        'limits': ['No controlled ablation isolates the new crop from scoped recovery instructions.',
                   '14 positive-overlap exterior correspondences are not 14 passed openings.',
                   'West short-window heads remain 0.60m high; all three exterior-door base/top values remain about 0.20m low.',
                   '7 spaces versus 8 reference spaces; whole-building partition remains severe; not adopted as the whole-building baseline.'],
    }
    (RUN / 'quality_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    rows = ''.join('<tr><td>{}</td><td>{:.3f}</td><td>{:.3f}</td><td>{}</td></tr>'.format(
        html.escape(row['source_id']), 1000 * row['center_abs_error_m'], 1000 * row['width_error_m'],
        ' / '.join(f'{1000*v:.1f}' for v in row['z_endpoint_delta_m'])) for row in east)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>sm24 东侧开口续修</title><style>body{max-width:1200px;margin:30px auto;padding:0 20px;font:17px/1.65 system-ui;color:#253144;background:#f6f7fa}a{color:#145ba2}figure{margin:20px 0;background:white;padding:18px;border-radius:10px}img{max-width:100%;max-height:850px;display:block;margin:auto}table{border-collapse:collapse;background:white}td,th{padding:10px;border:1px solid #ccd3dd}.warn{border-left:5px solid #c16b14;padding:14px;background:#fff1dd}</style>
<h1>东侧一门三窗位置已修正，整楼仍未通过</h1>
<p>从原失败墙网续修，Sonnet 576.51秒完成。开发侧限定东立面范围，模型重看原图、量测并修订；生成时无GT、正确坐标或评测结论。</p>
<p class="warn">门窗水平端点误差均小于2厘米，三窗高度正确；东门底/顶仍低约20厘米。东南房间错并、西侧四短窗高度错误保留。最终7空间/11窗/9门，不替代整楼工作基点。</p>
<p><a href="candidate_01/viewer.html">旋转查看实际模型</a> · <a href="README.md">范围与验证</a> · <a href="quality_audit.json">独立评价</a> · <a href="recovery_verification.json">恢复输入/改动核验</a></p>
<h2>生成后独立对照</h2><p>单位：毫米。按原图20000mm总长显式平移[0,20,0]，未拟合GT；原坐标评价同时保留。负宽差表示较窄。</p>
<table><tr><th>开口</th><th>中心位置误差</th><th>宽度差</th><th>底 / 顶差</th></tr>''' + rows + '''</table>
<figure><figcaption>原东立面：从左到右对应平面南→北；左竖链明确为200+2400+1900。</figcaption><img src="images/East_view.png"></figure>
<figure><figcaption>最终实际源东立面：三窗已对应，门底仍错误落在0。</figcaption><img src="candidate_01/elevation_East.png"></figure>
<figure><figcaption>失败时实际返回模型的原图/声明局部对照。提供了证据，但单次实验不能隔离反馈与限定任务各自的作用。</figcaption><img src="plan_drafts/draft_001/opening_host_failure.png"></figure>
<figure><figcaption>最终源回叠原图：东侧开口恢复；东南折角墙和内门仍缺失。</figcaption><img src="image_overlays/overlay_002.png"></figure>
<p>源/显示精确重放、离线旋转查看通过；这些只证明模型自洽可看，不替代图纸保真。</p></html>'''
    (RUN / 'index.html').write_text(page)


if __name__ == '__main__':
    main()
