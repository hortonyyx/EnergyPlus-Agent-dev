"""Compare completed recoveries without relabeling them as cold or causal tests."""
import html
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent


def main():
    rows, inputs = [], []
    for number in (66, 67):
        run = HERE.parent / f'2026-09-27_sm24_claim_regions_claude_run{number}'
        load = lambda name: json.loads((run / name).read_text())
        audit, summary = load('continuation_audit.json'), load('summary.json')
        semantic, transport = load('evaluation/semantic_review.json'), load('transport_audit.json')
        inputs.append(json.loads((HERE / f'{run.name}_frozen.json').read_text()))
        rows.append(dict(run=run.name, candidate=audit['candidate'],
            source_model_sha256=audit['source_model_sha256'],
            invocations=audit['invocations'], actual_models=audit['actual_models'],
            elapsed_seconds=audit['elapsed_seconds'], estimated_usd_not_bill=audit['estimated_usd_not_bill'],
            counts=audit['counts'], geometry_preserved=all(audit['preserved_vs_seed'].values()),
            room_use=audit['room_use']['summary'], height_coverage=audit['height_coverage'],
            position_matches=audit['original_plan']['position_matches'],
            host_matches=audit['original_plan']['host_matches'],
            door_connections_matched=audit['original_plan']['door_connections_matched'],
            strict_partition=audit['strict_partition'], exterior_match_count=audit['exterior_match_count'],
            semantic=semantic, transported_images=transport['image_count'],
            claim_preview_images=load('evaluation/claim_transport_audit.json')['image_count'],
            errors=[error for turn in transport['turns'] for error in turn['errors']],
            browser_pass=load('browser_qa/room_types.json')['status']=='pass',
            continuation=summary['continuation']))
    fields = ('scope', 'image_sha256', 'seed_proposal_sha256', 'prior_claim_file_sha256',
              'provider', 'role', 'effort', 'timeout_seconds', 'continuation_rounds')
    same = {key: inputs[0][key] == inputs[1][key] for key in fields}
    assert all(same.values())
    report = dict(runs=rows, frozen_inputs_equal=same,
        total_invocations=sum(r['invocations'] for r in rows),
        total_elapsed_seconds=round(sum(r['elapsed_seconds'] for r in rows), 2),
        total_estimated_usd_not_bill=sum(r['estimated_usd_not_bill'] for r in rows),
        distinct_offline_tests_passed=104,
        interpretation='Same recovery task/inputs, changed tool/reference implementation between runs. Neither a frozen producer repeat nor a causal comparison or cold generation.',
        preserved_baselines=['sm21/run58','sm24/run56','sm25/run54'])
    dump(HERE / 'comparison.json', report)
    body = ['<!doctype html><html lang="zh"><meta charset="utf-8"><title>还原：房间合理选型与高度依据</title>',
        '<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.6}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:10px;text-align:left}a{color:#135b9f}</style>',
        '<h1>房间合理选型与高度依据回查</h1>',
        '<p>限定保存稿恢复；没有向生成输入GT、开发者修正框或高度答案。两次实现不同，不能解释为冷启动、冻结重复或因果对照。用途允许合理推断；原几何和关系保持。</p>',
        '<table><tr><th>运行 / 查看</th><th>房间</th><th>空间 / 开口 / 连接</th><th>依据核验</th><th>调用 / 时长</th></tr>']
    for row in rows:
        name = row['run']
        body.append(f'<tr><td><a href="../{name}/delivery.html">{name.rsplit("_",1)[-1]} BIM</a><br><a href="../{name}/evaluation/semantic_review.md">独立核验</a></td>'
            f'<td>{row["room_use"]["inferred_count"]}推断 / {row["room_use"]["unknown_count"]}未知</td>'
            f'<td>{row["counts"]["spaces"]} / {row["counts"]["openings"]} / {row["counts"]["connections"]}</td>'
            f'<td>{html.escape(row["semantic"]["status"])}</td><td>{row["invocations"]} / {row["elapsed_seconds"]}s</td></tr>')
    body.append('</table><p>原平面位置15/21在容差内、宿主21/21、门连接10/10；严格分区仍severe。14外开口的GT参数对应，7内门高仍假设。局部恢复不替换原整栋基线。</p><p><a href="comparison.json">完整对照JSON</a> · <a href="README.md">方法及限制</a></p></html>')
    (HERE / 'index.html').write_text('\n'.join(body), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs','frozen_inputs_equal')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
