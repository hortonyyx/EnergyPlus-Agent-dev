"""Replay the exact 251-plan A1-T corpus with pre-A3 and current compilers."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
from collections import Counter
from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.plan_input import normalize_plan_fields, plan_error_hint
from src.agent.geometry.plan_feedback import resolve_plan_lengths

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASELINE='ea802787'
measure=importlib.import_module('AI_agent.logs.experiments.2026-10-03_tool_package_t1.measure_instructions')

def invoke(compiler, value, size, image):
    before=copy.deepcopy(value)
    try:
        output=compiler(value,image_size=tuple(size),image_name=image)
        raw=json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        return dict(accepted=True,output_sha256=hashlib.sha256(raw).hexdigest(),aliases=output[1].get('field_aliases',[]))
    except (ValueError,TypeError,KeyError,IndexError) as e:
        return dict(accepted=False,error_type=type(e).__name__,error=str(e))
    finally:
        assert value==before

def main():
    baseline=measure.baseline_module('src/agent/geometry/plan_partition.py','a3t_old_plan',BASELINE)
    corpus=json.loads((HERE.parent/'2026-10-04_absorb_a1t/replay_results.json').read_text())
    rows=[]
    for entry in corpus['plans']:
        path=(ROOT/entry['path']) if entry['path'].startswith('AI_agent/') else ROOT/'.tmp_a3t/history'/entry['path']
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['plan_sha256'],path
        try:
            plan,_=resolve_plan_lengths(json.loads(raw))
        except (ValueError, TypeError, KeyError) as error:
            plan=None
            old=dict(accepted=False,error_type=type(error).__name__,error=str(error))
            new=copy.deepcopy(old)
        else:
            old=invoke(baseline.compile_plan_partition,plan,entry['image_size'],entry['image'])
            new=invoke(compile_plan_partition,plan,entry['image_size'],entry['image'])
        row=dict(path=entry['path'],input_sha256=entry['plan_sha256'],before=old,after=new)
        if old['accepted']:
            assert new==old,row
            row['outcome']='accepted_byte_identical'
        elif new['accepted']:
            assert new['aliases'],row
            normalized,_=normalize_plan_fields(plan)
            expected=invoke(baseline.compile_plan_partition,normalized,entry['image_size'],entry['image'])
            actual,_=compile_plan_partition(plan,image_size=tuple(entry['image_size']),image_name=entry['image'])
            old_actual,_=baseline.compile_plan_partition(normalized,image_size=tuple(entry['image_size']),image_name=entry['image'])
            assert actual==old_actual and expected['accepted']
            row['outcome']='alias_accepted_and_noted'
        else:
            row['repair_hint']=plan_error_hint(plan,new['error'])
            row['outcome']='rejected_more_precise' if new!=old else 'rejected_same_with_local_format_hint'
        rows.append(row)
    summary=dict(Counter(r['outcome'] for r in rows))
    report=dict(baseline_commit=BASELINE,model_requests=0,total=len(rows),summary=summary,rows=rows,
                scope=__doc__,unchanged_geometry=True)
    (HERE/'plan_replay.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
