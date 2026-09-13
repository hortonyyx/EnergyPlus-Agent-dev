"""Inspect saved source changes after generation, never feed evaluator output back."""
import argparse
import json
from pathlib import Path

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args();r=args.run.resolve()
    summary=json.loads((r/'summary.json').read_text())
    selected=summary['delivery']['candidate']
    before=json.loads((r/'seed/source_model.json').read_text())
    after=json.loads((r/selected/'source_model.json').read_text())
    changes={}
    for kind in ['spaces','boundaries','openings','connections']:
        key='opening_id' if kind=='connections' else 'id'
        a={x[key]:x for x in before[kind]};b={x[key]:x for x in after[kind]}
        changes[kind]={'before_count':len(a),'after_count':len(b),
            'removed_ids':sorted(a.keys()-b.keys()),'added_ids':sorted(b.keys()-a.keys()),
            'changed':{k:{field:{'before':a[k].get(field),'after':b[k].get(field)}
                for field in a[k].keys()|b[k].keys() if a[k].get(field)!=b[k].get(field)}
                for k in sorted(a.keys()&b.keys()) if a[k]!=b[k]}}
    result={'selected':selected,'mode':'post_generation_actual_source_comparison',
        'before_sha256':before['source_model_sha256'],'after_sha256':after['source_model_sha256'],
        'changes':changes,'limits':'Field equality/change is not drawing fidelity or opening correctness.'}
    out=r/'evaluation';out.mkdir(exist_ok=True)
    (out/'source_change_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:{key:len(v) if key=='changed' else v for key,v in row.items()} for k,row in changes.items()},indent=2))
