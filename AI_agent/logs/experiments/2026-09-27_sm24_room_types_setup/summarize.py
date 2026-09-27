"""Collect completed experiments without feeding assessment back to generation."""
from collections import Counter
import gzip
import html
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import dump

HERE = Path(__file__).resolve().parent
RUNS = [
    ('run59', '2026-09-27_sm24_room_types_claude_run59', '原图冷启动／初版功能表指引'),
    ('run60', '2026-09-27_sm24_room_types_recovery_claude_run60', '限定功能恢复／保留原几何'),
    ('run61', '2026-09-27_sm24_room_types_cold_claude_run61', '原图冷启动／增加局部修订和通用指引'),
    ('run62', '2026-09-27_sm24_room_types_feedback_claude_run62', '原图冷启动／增加实际候选缺项反馈'),
]
load = lambda path: json.loads(path.read_text())


def main():
    rows = []
    for label, folder, mode in RUNS:
        run = HERE.parent / folder
        assert (run / 'summary.json').is_file(), 'All generation must finish first'
        delivery = load(run / 'delivery.json')
        source = load(run / delivery['candidate'] / 'source_model.json')
        receipt = load(run / 'agent_receipt.json')
        plan = load(run / 'postrun_audit.json')
        actions = [json.loads(line) for line in (run / 'tools.jsonl').read_text().splitlines()]
        topics = [r['data']['topic'] for r in actions if r['action'] == 'get_bim_reference']
        types, errors, finish = {}, [], []
        with gzip.open(run / 'agent_stream.jsonl.gz', 'rt') as stream:
            for line in stream:
                content = json.loads(line).get('message', {}).get('content', [])
                for block in content if isinstance(content, list) else []:
                    if block.get('type') == 'tool_use':
                        types[block['id']] = block['name']
                    if block.get('type') != 'tool_result':
                        continue
                    tool = types.get(block['tool_use_id'], 'unknown')
                    if block.get('is_error'):
                        errors.append(tool)
                    if tool.endswith('finish_bim'):
                        result = block.get('content', [])
                        texts = [result] if isinstance(result, str) else [r['text'] for r in result if r.get('type') == 'text']
                        for text in texts:
                            try:
                                payload = json.loads(text)
                            except ValueError:
                                payload = {}
                            finish.append(dict(characters=len(text), direct_json=bool(payload.get('candidate')),
                                               room_use_review=payload.get('room_use_review')))
        row = dict(run=label, folder=folder, mode=mode, candidate=delivery['candidate'],
            source_sha256=source['source_model_sha256'], rooms=len(source['spaces']),
            roles=dict(Counter(s['role'] for s in source['spaces'])),
            basis_counts=dict(Counter(s.get('role_evidence', {}).get('basis')
                if s.get('role_evidence') else 'unrecorded' for s in source['spaces'])),
            catalog_read='room_types' in topics, reference_topics=topics,
            position_matches=plan['position_matches'], aperture_count=plan['original_aperture_count'],
            host_matches=plan['host_matches'], door_connections_matched=plan['door_connections_matched'],
            original_partition_status=plan['original_partition_status'], strict_gt_partition_status=plan['partition_status'],
            actual_model=receipt['actual_model'], seconds=receipt['elapsed_seconds'],
            cli_estimated_usd_not_bill=receipt['result']['total_cost_usd'],
            source_display_replay_exact=plan['source_replay_exact'] and plan['display_replay_exact'],
            browser=load(run / 'browser_qa/report.json')['status'],
            actual_tool_errors=errors, finish_results=finish,
            no_runtime_delegation=not any(r['action'] == 'review_detail' for r in actions))
        rows.append(row)
        dump(run / 'evaluation/session_comparison_row.json', row)
    result = dict(runs=rows, production_commits=['4de15e27', '26254bde'],
        calls=len(rows), elapsed_seconds=sum(r['seconds'] for r in rows),
        cli_estimated_usd_not_bill=sum(r['cli_estimated_usd_not_bill'] for r in rows),
        limits=['Function inference is not observed use truth.', 'Three cold runs used different implementation stages; not frozen repetitions.',
                'Run60 is bounded recovery; claims from run59 were not imported with the proposal.',
                'Strict partition scores retain original tolerances; no EP or user approval.'])
    dump(HERE / 'comparison.json', result)
    table = ''.join(
        '<tr><td><a href="../' + r['folder'] + '/delivery.html">' + r['run'] + '</a></td>'
        f'<td>{html.escape(r["mode"])}</td><td>{r["rooms"]}</td>'
        f'<td>{r["position_matches"]}/{r["aperture_count"]}</td>'
        f'<td>{r["host_matches"]}/{r["aperture_count"]}，{r["door_connections_matched"]}</td>'
        f'<td>{html.escape(str(r["basis_counts"]))}</td><td>{r["strict_gt_partition_status"]}</td></tr>'
        for r in rows)
    (HERE / 'index.html').write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>sm24 功能依据与还原验证</title>'
        '<style>body{font:16px system-ui;margin:36px;max-width:1200px}table{border-collapse:collapse}'
        'td,th{border:1px solid #ccd3da;padding:10px;text-align:left}p{line-height:1.6}</style>'
        '<h1>sm24：房间功能依据与还原验证</h1>'
        '<p>原平面没有用途文字，家具仅支持用途推断。功能记录和固定配色不证明用途正确；'
        '北侧两处家具存在多种解释。源空间分隔、门窗和连接仍独立核验。</p>'
        '<p><a href="semantic_review.md">独立语义核查</a> · <a href="comparison.json">完整对照数据</a> · '
        '<a href="README.md">实验与限制</a></p>'
        '<table><tr><th>查看</th><th>实验性质</th><th>空间</th><th>原图门窗位置</th><th>宿主，门连接</th>'
        '<th>用途依据记录</th><th>严格GT分区</th></tr>' + table + '</table>'
        '<p>unrecorded：没有结构化功能记录；inferred：模型已明确写为推断；unknown：已说明用途不明。'
        '三次原图冷启动使用不同阶段实现；run60是限定恢复，不能算自主整案。未修改评价容差或旧产物。</p></html>',
        encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'runs'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
