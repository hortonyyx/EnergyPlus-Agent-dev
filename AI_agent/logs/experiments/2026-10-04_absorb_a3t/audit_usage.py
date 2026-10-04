"""Conservative downstream exact-value usage audit before changing replies.

A matching parameter is possible reuse, not proof of its information source.
JSON strings in arguments are decoded; all later calls in the run are checked.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from src.agent.runtime_behaviour import tool_result_data

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = ROOT / '.tmp_a3t' / 'history'
TOOLS = {'build_bim','build_plan_bim','build_parametric_bim','revise_bim','revise_plan_bim','assemble_plan_bim','check_openings','finish_bim'}
FIELDS = {'plan_compilation','opening_inventory','inventory','source_image_projections','provenance','height_coverage','located_height_coverage','facade_inventory','current_claim_state','source_image_feedback','claim_application','plan_input','plan_revision'}

def records():
    for name in ('sm24_runtime_anthropic','sm25_runtime_anthropic','sm24_qwen27b_paratera'):
        yield name, WORK / name / 'behaviour/record.json.gz'
    for case in ('sm24','sm25'):
        name=f'2026-10-03_{case}_glm_tools_t1'
        yield name, HERE.parent/'2026-10-01_behaviour_records/records'/name/'record.json.gz'

def steps(path):
    return [s for i in json.loads(gzip.decompress(path.read_bytes()))['invocations'] for s in i['steps']]

def result(step):
    return step.get('result_data') or tool_result_data(step.get('result_text','')) or {}

def leaves(value, path='', decode=False):
    if isinstance(value, str) and decode:
        try:
            decoded=json.loads(value)
            if isinstance(decoded, (dict,list)):
                yield from leaves(decoded,path,decode);return
        except ValueError:
            pass
    if isinstance(value,dict):
        for key,item in value.items():
            yield from leaves(item,path+'.'+key,decode)
    elif isinstance(value,list):
        for item in value:
            yield from leaves(item,path+'[]',decode)
    elif isinstance(value,(int,float,str)) and not isinstance(value,bool):
        yield path,value

def token(value):
    return ('number',float(value)) if isinstance(value,(int,float)) else ('text',value)

def main():
    rows=[]
    for name,path in records():
        calls=steps(path); matches=[]; sizes=Counter()
        for i,call in enumerate(calls):
            if call['tool'] not in TOOLS:continue
            data=result(call)
            later={}
            for s in calls[i+1:]:
                for p,v in leaves(s.get('arguments',{}),decode=True):
                    later.setdefault(token(v),dict(step=s['index'],tool=s['tool'],argument=p))
            fields={}
            for key in sorted(FIELDS & data.keys()):
                used=defaultdict(dict)
                for p,v in leaves(data[key],key):
                    if token(v) in later:
                        used[p].setdefault(json.dumps(v),dict(value=v,**later[token(v)]))
                fields[key]={p:list(v.values()) for p,v in used.items()}
                sizes[key]+=len(json.dumps(data[key],ensure_ascii=False,indent=2))
            matches.append(dict(step=call['index'],tool=call['tool'],fields=fields))
        rows.append(dict(run=name,record_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                         tool_calls=len(calls),audited_returns=len(matches),field_characters=dict(sizes),matches=matches))
        print(name,len(calls),len(matches),dict(sizes),flush=True)
    (HERE/'usage_audit.json').write_text(json.dumps(dict(method=__doc__,model_requests=0,runs=rows),ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
