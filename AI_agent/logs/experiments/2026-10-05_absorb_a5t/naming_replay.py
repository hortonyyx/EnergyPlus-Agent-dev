"""Recompute public maps on historical source bytes without rebuilding geometry."""
import copy
import hashlib
import importlib
import json
from pathlib import Path

from src.agent.geometry.source_naming import build_public_names, viewer_names

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    measure = importlib.import_module('AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions')
    old = measure.baseline_module('src/agent/geometry/source_naming.py', 'a5t_baseline_naming', 'f4d48cf7')
    runs = list(HERE.parent.glob('2026-10-01_opus_dev_sm2[145]'))
    runs += list(HERE.parent.glob('2026-09-2*_sm2*run5[3-8]'))
    runs += [HERE.parent / n for n in ('2026-09-30_sm21_instruction_fix_run99', '2026-09-30_sm24_instruction_fix_run100')]
    runs += [p.parent for p in (ROOT/'.tmp_a5t/history').rglob('inputs.json')
             if list(p.parent.glob('candidate_*/source_model.json'))]
    rows = []
    for run in sorted(set(runs)):
        path = sorted(run.glob('candidate_*/source_model.json'))[-1]
        raw = path.read_bytes()
        source = json.loads(raw)
        untouched = copy.deepcopy(source)
        before, after = old.build_public_names(source), build_public_names(source)
        assert source == untouched and path.read_bytes() == raw
        reordered = copy.deepcopy(source)
        for field in ('floors','spaces','boundaries','openings'):
            reordered[field].reverse()
        assert build_public_names(reordered) == after
        differences = {kind: [dict(id=identity, before=before[kind][identity], after=value,
                                   archived=source.get('public_names', {}).get(kind, {}).get(identity))
                             for identity,value in after[kind].items() if before[kind][identity] != value]
                       for kind in ('floors','spaces','boundaries','openings','opening_sides')}
        rows.append(dict(source=str(path.relative_to(ROOT)), source_sha256=hashlib.sha256(raw).hexdigest(),
            geometry_and_source_unchanged=True, order_independent=True,
            source_floor_names=after['source_floor_names'], differences=differences))
    result = dict(baseline_commit='f4d48cf7', model_requests=0, candidates=len(rows), rows=rows,
        changed_names={k:sum(len(r['differences'][k]) for r in rows) for k in differences})
    (HERE/'naming_replay.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))


if __name__ == '__main__': main()
