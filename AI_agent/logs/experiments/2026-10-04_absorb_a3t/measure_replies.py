"""Replay the summary function on every targeted historical tool result.

This normalized JSON count is supplementary; mcp_reply_comparison.json measures
actual MCP text against A2-T. The main purpose here is the downstream-value audit.
Neither implies any subsequent model behavior or quality result.
"""
from collections import defaultdict
import importlib
import json
from pathlib import Path
from scripts.tool_scripts.bim_agent_replies import summarize_reply

HERE = Path(__file__).resolve().parent
AUDIT = importlib.import_module('AI_agent.logs.experiments.2026-10-04_absorb_a3t.audit_usage')

def chars(value):return len(json.dumps(value,ensure_ascii=False))

def main():
    rows=[]; totals=defaultdict(lambda:dict(calls=0,before=0,after=0))
    for name,path in AUDIT.records():
        steps=AUDIT.steps(path)
        for i,call in enumerate(steps):
            if call['tool'] not in AUDIT.TOOLS:continue
            data=AUDIT.result(call)
            summary=summarize_reply(data)
            # Account for the exact fixed file-reader overhead in real replies.
            if summary!=data:
                summary.update(details_file='tool_reports/build_bim_'+'a'*64+'.json',details_sha256='a'*64,
                    details_read='read_candidate_items(candidate="", collection="report", report_file=details_file); offset/limit page by characters.')
            later={AUDIT.token(v) for s in steps[i+1:] for _,v in AUDIT.leaves(s.get('arguments',{}),decode=True)}
            kept={AUDIT.token(v) for _,v in AUDIT.leaves(summary)}
            lost=defaultdict(set)
            for key in AUDIT.FIELDS & data.keys():
                for p,v in AUDIT.leaves(data[key],key):
                    if AUDIT.token(v) in later and AUDIT.token(v) not in kept:
                        lost[p].add(json.dumps(v,ensure_ascii=False))
            row=dict(run=name,step=call['index'],tool=call['tool'],before=chars(data),after=chars(summary),
                     reused_values_not_inline={p:sorted(v) for p,v in lost.items()})
            rows.append(row)
            for group in (call['tool'],'ALL'):
                t=totals[group];t['calls']+=1;t['before']+=row['before'];t['after']+=row['after']
    for t in totals.values():t['reduction_percent']=round(100*(1-t['after']/t['before']),2)
    (HERE/'reply_comparison.json').write_text(json.dumps(dict(method=__doc__,model_requests=0,totals=dict(totals),rows=rows),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(totals),indent=2))
    lost=defaultdict(set)
    for row in rows:
        for p,vs in row['reused_values_not_inline'].items():lost[p].update(vs)
    print('NOT INLINE',json.dumps({p:sorted(vs) for p,vs in lost.items()},ensure_ascii=False,indent=2))
    assert not lost, 'A possibly reused historical value was removed from the inline reply'

if __name__=='__main__':main()
