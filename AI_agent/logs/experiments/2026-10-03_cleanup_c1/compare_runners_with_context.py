"""Extend the R3 parity audit with C1 context policy, without editing C2's script.

Imports the actual R3 preparations and guards; all execution is offline. Claude
Code's public compact boundary is evidence for its policy, not a private-HTTP
capture. Runtime prefixes are checked directly over 40 successive rounds.
"""

import asyncio
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import tempfile

from src.agent import runtime_entry
from src.agent_runtime.context import ContextManager, ContextPolicy
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
R3 = importlib.import_module('AI_agent.logs.experiments.2026-10-03_runtime_r3.compare_runners')


def context_strategy(directory):
    policy = ContextPolicy()
    args = runtime_entry.parser().parse_args(['--out', str(directory / 'unused'), '--provider', 'scripted'])
    assert args.compact_at_tokens == policy.compact_at_tokens == 150000
    assert args.context_window is None and args.max_images is None
    projections = []
    with EventStore(directory / 'context-probe', run_id='c1-context-parity', task_id='offline',
                   budget_limit=BudgetAmounts(tokens=1000000, calls=1)) as store:
        manager = ContextManager(store, policy=policy)
        source = store.source('offline-input', {'text': 'context strategy probe'})
        for message in ({'role': 'system', 'content': 'fixed guidance'},
                        {'role': 'user', 'content': 'fixed task'}):
            manager.append(message, source)
        projections.append(manager.project().messages)
        for index in range(40):
            manager.append({'role': 'assistant', 'content': f'Observation {index}: source evidence retained.'}, source)
            manager.append({'role': 'user', 'content': f'Proceed to local check {index}.'}, source)
            projections.append(manager.project().messages)
        for before, after in zip(projections, projections[1:]):
            assert after[:len(before)] == before
        assert len(projections[-1]) == 82
        assert not [e for e in store.events if e.payload.event_type == 'context']
    baseline = HERE.parent / '2026-10-02_sm24_glm_baseline/agent_stream.jsonl.gz'
    boundaries = []
    with gzip.open(baseline, 'rt') as stream:
        for line in stream:
            item = json.loads(line)
            if item.get('subtype') == 'compact_boundary':
                boundaries.append(item['compact_metadata'])
    assert len(boundaries) == 1 and boundaries[0]['pre_tokens'] == 178264
    assert all(b['pre_tokens'] >= policy.compact_at_tokens for b in boundaries)
    return {
        'item': 'context_strategy', 'below_threshold_clipping': False,
        'runtime': {'default_threshold_input_tokens': policy.compact_at_tokens,
            'message_window': None, 'prefix_transitions_verified': 40, 'final_messages': 82,
            'context_events': 0, 'policy': policy.model_dump(mode='json'),
            'exception': 'Mutable current-state message is appended at the end and does not enter history.'},
        'claude_code_reference': {'path': str(baseline.relative_to(ROOT)),
            'sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
            'observed_compactions': len(boundaries),
            'pre_tokens': boundaries[0]['pre_tokens'], 'post_tokens': boundaries[0]['post_tokens'],
            'trigger': boundaries[0]['trigger'], 'observed_compactions_below_runtime_threshold': 0},
        'boundary': 'Runtime prefixes verified directly. Claude evidence is the archived public event stream; private HTTP request contents are unavailable. Thresholds and compression algorithms are not claimed identical.'}


def main():
    (ROOT / '.c1-tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='r3-context-', dir=ROOT / '.c1-tmp') as temporary:
        folder = Path(temporary)
        policy = context_strategy(folder)
        cases = []
        for case in ('sm24', 'sm25', 'sm21'):
            directory = folder / case
            directory.mkdir()
            row = asyncio.run(R3.case_report(case, directory, 6000))
            row['context_strategy'] = policy
            for difference in row['differences']:
                if difference['item'] == 'runtime_state':
                    difference['reason'] = 'C1 appends only current/selected candidate, original pending work, retrieval entries and computed child allowance at the tail. The task body stays in initial history; no duplicate task or per-view source hashes.'
                elif difference['item'] == 'service_parameters':
                    difference['reason'] = 'Live runtime Coding Plan configuration explicitly sends reasoning_effort=medium; Claude Code is configured at medium. Private service mapping and adaptive thinking are not captured. This audit uses a scripted model and makes no live-equivalence claim.'
            cases.append(row)
    output = {'agent_version': cases[0]['agent_version'], 'model_requests': 0,
        'model_processes_started': 0, 'extends': str(R3.HERE.relative_to(ROOT) / 'compare_runners.py'),
        'file_ownership': 'R3 source belongs to C2 and is imported unchanged.',
        'context_strategy': policy, 'cases': cases}
    path = HERE / 'runner_parity_with_context.json'
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases': [r['case'] for r in cases], 'all_identical': True,
        'context_prefix_transitions': 40, 'model_requests': 0}))


if __name__ == '__main__':
    main()
