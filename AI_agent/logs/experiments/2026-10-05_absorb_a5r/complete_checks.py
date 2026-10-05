"""Recheck only failed baseline cases under the explicit proposed registration.

Raw unregistered results remain intact. Frozen replay is tracked separately so
it is never repeated just because its first check hit the registration gate.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def case_id(case):
    parts = case.get('classname', '').split('.')
    module = next(p for p in parts if p.startswith('test_'))
    suffix = parts[parts.index(module)+1:]
    return '::'.join(['tests/'+module+'.py', *suffix, case.get('name')])


def cases(path):
    return ET.parse(path).getroot().findall('.//testcase')


def status(case):
    return next((name for name in ('failure','error','skipped') if case.find(name) is not None), 'pass')


def rerun():
    failed = [c for c in cases(HERE/'validation/all.xml') if status(c) in {'failure','error'}]
    record = []
    nodes = []
    for case in failed:
        node = case_id(case)
        error = case.find('failure')
        if error is None:
            error = case.find('error')
        text = (error.get('message','') + '\n' + (error.text or ''))
        record.append(dict(node_id=node, cause='default_registry_mismatch' if 'AgentVersionMismatch' in text else 'other', message=error.get('message')))
        if not node.startswith('tests/test_runtime_frozen_long_task.py::'):
            nodes.append(node)
    out = HERE/'validation'
    (out/'baseline_failure_causes.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    sources=json.loads((out/'all.json').read_bytes())['source_sha256']
    def hashes():
        return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    before=hashes()
    command=[sys.executable,'-m','pytest','-n','2','-s','-p',
             'AI_agent.logs.experiments.2026-10-05_absorb_a5r.proposed_registry_checks',*nodes,
             '--basetemp='+str(HERE/'.tmp/proposed-failed'),
             '--junitxml='+str(out/'proposed-failed.xml'),
             '-o','cache_dir='+str(HERE/'.tmp/proposed-failed-cache')]
    env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(HERE/'.tmp')}
    started=datetime.now(timezone.utc).isoformat()
    clock=time.monotonic()
    with (out/'proposed-failed.log').open('w') as stream:
        result=subprocess.run(command,cwd=ROOT,env={**os.environ,**env},stdout=stream,stderr=subprocess.STDOUT)
    data=dict(command=command,environment=env,started_utc=started,seconds=time.monotonic()-clock,
        returncode=result.returncode,source_unchanged_during_run=before==hashes(),
        same_source_as_baseline=before==sources,source_sha256=before,model_requests=0,
        authority='conditional_on_proposed_registry',production_registry_modified=False)
    (out/'proposed-failed.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:data[k] for k in ('returncode','seconds','source_unchanged_during_run','same_source_as_baseline')}))
    return result.returncode


def summarize():
    original={case_id(c):status(c) for c in cases(HERE/'validation/all.xml')}
    final=dict(original)
    for name in ('proposed-failed','proposed-frozen'):
        for case in cases(HERE/f'validation/{name}.xml'):
            final[case_id(case)]=status(case)
    counts=lambda data:{value:sum(s==value for s in data.values()) for value in ('pass','failure','error','skipped')}
    result=dict(authority='conditional_on_proposed_registry',production_entry='requires_combined_A5_registration',
        baseline=counts(original),integration_rehearsal=counts(final),
        remaining=[node for node,value in final.items() if value not in {'pass','skipped'}],
        checked_files=len({n.split('::')[0] for n in final}),test_cases=len(final),model_requests=0)
    (HERE/'validation/effective.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['rerun','summarize'])
    args=parser.parse_args()
    if args.action=='rerun':
        raise SystemExit(rerun())
    summarize()
