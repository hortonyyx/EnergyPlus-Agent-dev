"""Summarize saved generation attempts after the invocation has ended."""
import json
from pathlib import Path
from collections import Counter
from scripts.tool_scripts.run_bim_agent import dump


def summarize(run):
    assert (run/'summary.json').exists()
    rows=[json.loads(s) for s in (run/'tools.jsonl').read_text().splitlines()]
    builds=[r for r in rows if r['action']=='build_plan_bim']
    attempts=[]
    for row in builds:
        data=row['data']; record=data['plan_input']
        plan=json.loads((run/record['plan_file']).read_text())
        attempts.append(dict(seconds_from_first_tool=round(row['time']-rows[0]['time'],2),
            plan_file=record['plan_file'],candidate=data.get('candidate'),
            error=data.get('error'),source_geometry_ready=data.get('source_geometry_ready'),
            counts=data.get('counts'),declared_partition_count=len(plan['partitions']),
            declared_opening_kinds=dict(Counter(o['kind'] for o in plan['openings'])),
            unresolved=plan['unresolved']))
    out=run/'evaluation';out.mkdir(exist_ok=True)
    dump(out/'observation_and_edit_trace.json',dict(
        note='Actual model-chosen sequence; no developer intervention after run42 launch.',
        attempts=attempts,
        actions=[dict(action=r['action'],seconds_from_first_tool=round(r['time']-rows[0]['time'],2),
            candidate=r['data'].get('candidate'),error=r['data'].get('error')) for r in rows]))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,required=True)
    summarize(parser.parse_args().run.resolve())
