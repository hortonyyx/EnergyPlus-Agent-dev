"""Regenerate both 27B summaries using the production three-column report."""
import hashlib
import json
from pathlib import Path

from src.agent.runtime_behaviour import load_behaviour, render_timeline

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    rows = []
    for name, expected in [('sm24_qwen27b_paratera', (2, 3, 6)), ('sm24_qwen27b_after_a2', (0, 2, 1))]:
        run = ROOT / '.tmp_c3t/history' / name
        record = load_behaviour(run)
        summary = record['summary']
        triple = tuple(summary[k] for k in ('call_errors', 'domain_failures', 'usable_source_drafts'))
        assert triple == expected, (name, triple)
        target = HERE / 'behaviour' / name
        target.mkdir(parents=True, exist_ok=True)
        (target / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
        (target / 'timeline.md').write_text(render_timeline(record).rstrip() + '\n')
        rows.append(dict(run=name, call_errors=triple[0], domain_failures=triple[1], usable_source_drafts=triple[2],
            tool_calls=summary['tool_calls'], source_events_sha256=hashlib.sha256((run/'events.jsonl').read_bytes()).hexdigest(),
            domain_failure_steps=[r['index'] for r in summary['outcomes'] if r['domain_failure']]))
    (HERE / 'behaviour_comparison.json').write_text(json.dumps(dict(model_requests=0, rows=rows,
        scope='Calls, normal-return domain failures and committed usable sources are separate; partial batches can contribute to both the last two columns. Original evidence unchanged.'),
        ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(rows, ensure_ascii=False))


if __name__ == '__main__':
    main()
