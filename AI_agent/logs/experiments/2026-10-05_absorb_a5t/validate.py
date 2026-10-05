"""All direct references to A5-T modules plus BIM/runtime/harness integration."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
MODULES=('run_bim_agent','bim_agent_replies','bim_agent_guidance',
         'bim_agent_feedback','source_naming','wall_placement','bim_agent_precision','agent_versions')


def files(label='final'):
    modules = ('bim_agent_guidance', 'agent_versions') if label == 'naming_reference' else MODULES
    direct={str(p.relative_to(ROOT)) for p in (ROOT/'tests').rglob('test*.py')
            if any(name in p.read_text() for name in modules)}
    if label == 'naming_reference':
        return sorted(direct), sorted(direct)
    selected=direct | {str(p.relative_to(ROOT)) for pattern in
        ('test_bim_*.py','test_runtime_*.py','test_harness_*.py') for p in (ROOT/'tests').glob(pattern)}
    selected.update('tests/'+name+'.py' for name in ('test_agent_runtime','test_building_contracts',
        'test_plan_partition','test_plan_assembly','test_plan_revision','test_plan_measurement_binding',
        'test_stage1_behaviour'))
    return sorted(selected),sorted(direct)


def hashes(selected):
    registry=json.loads((ROOT/'src/agent_runtime/agent_versions.json').read_text())
    paths=set(registry['versions'][registry['current_version']]['files'])|set(selected)
    for pattern in ('src/agent_runtime/*.py','src/harness_contracts/*.py','src/agent/runtime_*.py'):
        paths.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
    paths.add('src/agent_runtime/agent_versions.json')
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    label=sys.argv[1] if len(sys.argv)>1 else 'final'
    output=HERE/'validation'/label
    output.mkdir(parents=True,exist_ok=True)
    work=ROOT/'.tmp_a5t/validation'/label
    work.mkdir(parents=True,exist_ok=True)
    selected,direct=files(label)
    command=[sys.executable,'-m','pytest','-q','-n','2','-s',*selected,
             '--basetemp='+str(work/'pytest'),'-o','cache_dir='+str(work/'cache'),
             '--junitxml='+str(output/'related.xml')]
    before=hashes(selected)
    record=dict(command=command,files=selected,direct_reference_files=direct,
                source_sha256=before,model_requests=0,started_epoch=time.time())
    (output/'related.json').write_text(json.dumps(record,indent=2)+'\n')
    with (output/'related.log').open('w') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1',
                 'TMPDIR':str(work),'R3_EVIDENCE_OUT':str(output/'r3_counterexamples')})
    after=hashes(selected)
    suites=ET.parse(output/'related.xml').getroot().findall('testsuite')
    counts={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
    record.update(returncode=result.returncode,seconds=round(time.time()-record['started_epoch'],3),
        source_unchanged_during_run=before==after,**counts,
        passed=counts['tests']-counts['failures']-counts['errors']-counts['skipped'])
    (output/'related.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('passed','failures','errors','skipped','seconds','source_unchanged_during_run')}),flush=True)
    raise SystemExit(result.returncode or (0 if before==after else 1))


if __name__=='__main__':main()
