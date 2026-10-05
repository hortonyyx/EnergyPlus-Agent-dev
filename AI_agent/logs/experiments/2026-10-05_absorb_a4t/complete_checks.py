"""Complete exact unpassed IDs and recheck the complete failing file, unchanged code."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
validation=importlib.import_module('AI_agent.logs.experiments.2026-10-05_absorb_a4t.validate')


def key(nodeid):
    parts=nodeid.split('::')
    return (parts[0][:-3].replace('/','.')+''.join('.'+p for p in parts[1:-1]),parts[-1])


def main():
    collected=json.loads((HERE/'validation/collection.json').read_text())
    prior=json.loads((HERE/'validation/final2/related.json').read_text())
    assert prior['source_sha256']==collected['source_sha256']==validation.hashes(collected['files'])
    identities={key(n):n for n in collected['nodeids']}
    assert len(identities)==len(collected['nodeids'])
    cases=ET.parse(HERE/'validation/final2/related.xml').getroot().iter('testcase')
    passed=set();failures=[]
    for case in cases:
        if not case.get('classname') and not case.get('name'):
            # pytest's interrupt sentinel is not a collected test or a pass.
            assert not list(case),ET.tostring(case)
            continue
        nodeid=identities[(case.get('classname'),case.get('name'))]
        if case.find('failure') is not None or case.find('error') is not None:failures.append(nodeid)
        elif case.find('skipped') is None:passed.add(nodeid)
    recheck_files=sorted({n.split('::')[0] for n in failures})
    remaining=[n for n in collected['nodeids'] if n not in passed and n.split('::')[0] not in recheck_files]
    targets=recheck_files+remaining
    output=HERE/'validation/completion'
    output.mkdir(parents=True,exist_ok=True)
    work=ROOT/'.tmp_a4t/validation/completion'
    work.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-m','pytest','-v','-n','2','-s','--maxfail=1',*targets,
        '--basetemp='+str(work/'pytest'),'-o','cache_dir='+str(work/'cache'),
        '--junitxml='+str(output/'related.xml')]
    record=dict(model_requests=0,source_sha256=prior['source_sha256'],
        reused_passed_nodeids=sorted(passed),initial_failed_nodeids=failures,
        rechecked_complete_files=recheck_files,pending_nodeids=remaining,command=command,started_epoch=time.time())
    (output/'related.json').write_text(json.dumps(record,indent=2)+'\n')
    print('Reuse',len(passed),'passed; recheck files',recheck_files,'and',len(remaining),'remaining IDs',flush=True)
    with (output/'related.log').open('w') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1',
                 'TMPDIR':str(work),'R3_EVIDENCE_OUT':str(output/'r3_counterexamples')})
    suites=ET.parse(output/'related.xml').getroot().findall('testsuite')
    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    after=validation.hashes(collected['files'])
    all_passed=set(passed)
    for suite in suites:
        for case in suite.findall('testcase'):
            if not any(case.find(k) is not None for k in ('failure','error','skipped')):
                all_passed.add(identities[(case.get('classname'),case.get('name'))])
    record.update(returncode=result.returncode,seconds=round(time.time()-record['started_epoch'],3),**counts,
        source_unchanged_during_run=after==prior['source_sha256'],
        passed=counts['tests']-counts['failures']-counts['errors']-counts['skipped'],
        all_collected_tests_passed=set(collected['nodeids'])==all_passed,
        missing_passed_nodeids=sorted(set(collected['nodeids'])-all_passed))
    (output/'related.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('passed','failures','errors','skipped','seconds',
        'source_unchanged_during_run','all_collected_tests_passed')}),flush=True)
    raise SystemExit(result.returncode or (0 if record['source_unchanged_during_run'] and record['all_collected_tests_passed'] else 1))


if __name__=='__main__':main()
