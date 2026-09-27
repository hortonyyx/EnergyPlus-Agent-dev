"""Read completed isolated experiments and create a small comparison index."""
import html
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent


def main():
    rows = []
    for number in (63, 64, 65):
        run = HERE.parent / f'2026-09-27_sm24_continuation_claude_run{number}'
        audit = json.loads((run / 'continuation_audit.json').read_text())
        transport = json.loads((run / 'transport_audit.json').read_text())
        delivery = json.loads((run / 'delivery.json').read_text())
        stages = []
        for item in transport['turns']:
            receipt = json.loads((run / f'{item["turn"]}_receipt.json').read_text())
            stages.append(dict(name=item['turn'], elapsed_seconds=receipt['elapsed_seconds'],
                estimated_usd_not_bill=receipt['result']['total_cost_usd'],
                tools=item['tools'], errors=item['errors']))
        rows.append(dict(run=run.name, candidate=audit['candidate'],
            **{key: audit[key] for key in ('counts', 'preserved_vs_seed', 'elapsed_seconds', 'estimated_usd_not_bill',
                'invocations', 'height_coverage', 'strict_partition', 'exterior_match_count', 'continuation')},
            room_use=audit['room_use']['summary'], stages=stages,
            image_count=transport['image_count'],
            original_positions=audit['original_plan']['position_matches'],
            original_hosts=audit['original_plan']['host_matches'],
            original_connections=audit['original_plan']['door_connections_matched'],
            viewer=f'../{run.name}/{delivery["viewer"]}'))
    result = dict(runs=rows, distinct_tests_passed=99, invocations=sum(row['invocations'] for row in rows),
        elapsed_seconds=round(sum(row['elapsed_seconds'] for row in rows), 2),
        estimated_usd_not_bill=sum(row['estimated_usd_not_bill'] for row in rows),
        frozen_repeat=False, cold_start=False,
        limits=['Continuation instruction differs between 63 and 64; task requirement differs in 65.',
                '65 actual follow-up executes plan overlay and 7 relation samples, not the initial use/height reviews.',
                '65 height values match whole drawings/typed GT, but all 9 declared regions omit or clip the complete relevant dimension chain.',
                'No correctness claim based on recorded counts or a model stop.'])
    dump(HERE / 'comparison.json', result)
    table = ''.join(f'<tr><td>run{row["run"][-2:]}</td><td>{row["invocations"]}</td>'
        f'<td>{row["room_use"]["inferred_count"]} 推断 / {row["room_use"]["unknown_count"]} 未知</td>'
        f'<td>{row["height_coverage"]["image_linked_count"]} / 21</td>'
        f'<td>{row["elapsed_seconds"]:.2f} 秒</td><td><a href="{html.escape(row["viewer"])}">查看 BIM</a></td></tr>' for row in rows)
    (HERE / 'index.html').write_text('''<!doctype html><html lang="zh"><meta charset="utf-8">
<title>sm24 保存候选续查</title><style>body{font:16px/1.7 system-ui;max-width:1050px;margin:50px auto;padding:20px;color:#213547}table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccd5df}a{color:#185abc}.note{padding:18px;background:#fff3d5}</style>
<h1>保存候选续查：动作执行与证据质量分别验收</h1>
<p>三次均保留8空间、21门窗、10连接及全部物理几何。run65实际自主追加平面回叠和7组空间关系检查；前两次续查直接停止。</p>
<table><tr><th>实验</th><th>主调用</th><th>用途依据</th><th>高度图像关联</th><th>耗时</th><th>产物</th></tr>''' + table + '''</table>
<p class="note">关联数量不是证据正确率。run65的高度数值与整幅原图及独立GT相符，但9处声明证据框均未完整包含相应尺寸链；房间用途仍有歧义。严格平面尺寸仍severe，位置15/21、宿主21/21、门连接10/10。三次是不同指引/任务的恢复实验，不是冷启动或冻结重复。</p>
<p><a href="README.md">方法与结论</a> · <a href="semantic_review.md">独立语义核查</a> · <a href="../2026-09-27_sm24_continuation_claude_run65/evaluation/claim_crops/all_claim_regions.png">实际证据区域</a></p></html>''', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('invocations', 'elapsed_seconds', 'estimated_usd_not_bill')}, indent=2))


if __name__ == '__main__':
    main()
