"""Re-score the seven specified saved runs; no regeneration or model requests."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.tool_scripts.evaluate_bim_agent import evaluate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = HERE.parent
CASES = [
    ('sm24_runtime_anthropic', 'sm24_anchor', HERE / '.tmp/history/sm24_runtime_anthropic'),
    ('sm25_runtime_anthropic', 'sm25-L_anchor', HERE / '.tmp/history/sm25_runtime_anthropic'),
    ('sm24_qwen27b_paratera', 'sm24_anchor', HERE / '.tmp/history/sm24_qwen27b_paratera'),
    ('sm24_qwen27b_after_a2', 'sm24_anchor', HERE / '.tmp/history/sm24_qwen27b_after_a2'),
    *[(f'opus_dev_{case}', f'{case}-L_anchor' if case == 'sm25' else f'{case}_anchor',
       EXP / f'2026-10-01_opus_dev_{case}') for case in ('sm21', 'sm24', 'sm25')],
]


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    rows = []
    for name, case, root in CASES:
        run = root / 'bim' if (root / 'bim').is_dir() else root
        selected = load(run / 'delivery.json')['candidate']
        guarded = [run / 'inputs.json', run / 'delivery.json',
                   ROOT / 'case_tests/test_baseline/gt' / case / 'gt.json']
        guarded += list(run.glob('candidate_*/source_model.json')) + list(run.glob('candidate_*/proposal.json'))
        guarded += list(run.glob('plan_drafts/*/*.json'))
        before = {str(p.relative_to(ROOT)): digest(p) for p in guarded}
        target = HERE / 'evaluation' / name
        result = evaluate(root, case, modelling_task='reconstruction',
            reference_scope='Offline A5-R re-evaluation of the immutable saved run; no new generation, GT unchanged.', out=target)
        after = {str(p.relative_to(ROOT)): digest(p) for p in guarded}
        assert before == after
        raw = load(target / f'{selected}_partition.json')
        quality = load(target / f'{selected}_delivery_quality.json')
        reading = load(target / 'reading_readings.json')
        row = dict(run=name, case=case, candidate=selected, original_inputs_unchanged=True,
            source_sha256=digest(run / selected / 'source_model.json'),
            strict_partition_before=raw['comparison']['status'],
            partition_after=quality['partition']['status'], delivery_quality_status=quality['status'],
            convention_counts=dict(Counter(c for d in quality['convention_differences'] for c in d['category'])),
            convention_differences=quality['convention_differences'],
            retained_severe_findings=[f for f in quality['retained_findings'] if f['severity']=='severe'],
            retained_counts=dict(Counter(f['code'] for f in quality['retained_findings'])),
            openings={k: quality['opening_inventory'].get(k) for k in ('reference_count','matched','positions','hosts','door_connections')},
            heights={k: quality['exterior_heights'].get(k) for k in ('expected','matched','within')},
            reading_record_count=len(reading['records']),
            strict_reading_partitions=[dict(path=r['path'], status=r['strict_reading_partition']['status'])
                for r in reading['records'] if 'strict_reading_partition' in r],
            historical_normalization=reading['normalization_history_status'],
            evidence_files_sha256=before, report=str(target.relative_to(ROOT) / 'index.html'))
        rows.append(row)
        print(json.dumps({k:row[k] for k in ('run','candidate','strict_partition_before','partition_after',
            'delivery_quality_status','convention_counts','retained_counts','openings','heights')},ensure_ascii=False),flush=True)
    (HERE / 'reevaluation.json').write_text(json.dumps(dict(model_requests=0, runs=rows),ensure_ascii=False,indent=2)+'\n')

if __name__ == '__main__':
    main()
