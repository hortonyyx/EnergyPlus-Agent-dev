"""Post-run timing and actual tool inventory; no drawing judgement."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    run = parser.parse_args().run.resolve()
    summary = json.loads((run/'summary.json').read_text())
    rows = [json.loads(line) for line in (run/'tools.jsonl').read_text().splitlines()]
    origin = rows[0]['time'] if rows else None
    calls = []
    for path in sorted(run.glob('*_receipt.json')):
        receipt = json.loads(path.read_text())
        result = receipt.get('result', {})
        calls.append({
            'name': path.name.removesuffix('_receipt.json'),
            'model': receipt.get('actual_model'),
            'effort': receipt.get('effort'),
            'elapsed_seconds': receipt.get('elapsed_seconds'),
            'timed_out': receipt.get('timed_out', False),
            'returncode': receipt.get('returncode'),
            'result_present': bool(result),
            'is_error': result.get('is_error'),
            'cli_estimated_cost_usd': result.get('total_cost_usd'),
            'usage': result.get('usage'),
            'model_usage': result.get('modelUsage'),
        })
    stream = run/'agent_stream.jsonl'
    opener = open
    if not stream.exists():
        stream = stream.with_suffix('.jsonl.gz')
        opener = gzip.open
    attempts = Counter()
    with opener(stream, 'rt') as handle:
        for line in handle:
            event = json.loads(line)
            for block in event.get('message', {}).get('content', []):
                if block.get('type') == 'tool_use':
                    attempts[block['name'].split('__')[-1]] += 1
    report = {
        'run': run.name,
        'calls': calls,
        'recorded_parent_actions': dict(Counter(row['action'] for row in rows)),
        'actual_parent_tool_attempts': dict(attempts),
        'parent_timeline_from_first_logged_action_seconds': [
            {'elapsed_seconds': round(row['time']-origin, 2), 'action': row['action'],
             'remaining_seconds': row.get('data', {}).get('remaining_seconds')}
            for row in rows],
        'saved_source_candidates': [path.parent.name for path in sorted(run.glob('candidate_*/source_model.json'))],
        'delivery': summary.get('delivery'),
        'limitations': [
            'Parent elapsed includes awaited local calls; do not add child time as end-to-end latency.',
            'CLI costs are reported estimates, not subscription bills. Missing timeout costs stay unknown.',
            'A logged image response or saved candidate is not proof of faithful interpretation.',
            'Timeline starts at first logged tool action, not process launch.',
        ],
    }
    (run/'execution_summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'delivery','parent_timeline_from_first_logged_action_seconds'}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
