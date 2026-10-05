"""Run whole test files referencing C3-T modules, plus BIM integration checks."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    registry = json.loads((ROOT / 'src/agent_runtime/agent_versions.json').read_bytes())
    version = registry['current_version']
    changed = subprocess.check_output(['git', 'diff', '--name-only', 'a5baa32d'], cwd=ROOT, text=True).splitlines()
    modules = [p for p in changed if p.endswith('.py') and p.startswith(('src/', 'scripts/'))]
    selected = {}
    for path in sorted((ROOT / 'tests').glob('test_*.py')):
        contents = path.read_text()
        hits = [m for m in modules if re.search(r'\b' + re.escape(Path(m).stem) + r'\b', contents)]
        if not hits and (path.name.startswith('test_bim_') or path.name == 'test_building_precision.py'):
            hits = ['additional BIM integration or unchanged precision kernel check']
        if hits:
            selected[path.relative_to(ROOT).as_posix()] = hits
    selection = dict(baseline='a5baa32d', modules=modules, tests=selected,
        selection='Direct filename/module-name references; add all BIM test files and precision kernel tests.')
    (HERE / 'validation/selected_tests.json').write_text(json.dumps(selection, indent=2) + '\n')
    xml = HERE / 'validation/related_final.xml'
    xml.unlink(missing_ok=True)
    (HERE / 'validation/related_final.json').unlink(missing_ok=True)
    command = [sys.executable, '-m', 'pytest', '-n', '2', '-s',
        '--basetemp=.tmp_c3t/pytest_related_final', '--junitxml=' + str(xml), *selected]
    start = time.monotonic()
    with (HERE / 'validation/related_final.log').open('w') as output:
        run = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT)},
                             stdout=output, stderr=subprocess.STDOUT)
    suites = ET.parse(xml).getroot()
    cases = list(suites.iter('testcase'))
    failed = [c.attrib for c in cases if c.find('failure') is not None or c.find('error') is not None]
    skipped = [c.attrib for c in cases if c.find('skipped') is not None]
    result = dict(agent_version=version, registered_source_commit=registry['versions'][version]['source_commit'],
        exit_code=run.returncode, test_files=len(selected), tests=len(cases),
        passed=len(cases)-len(failed)-len(skipped), failed=failed, skipped=skipped,
        elapsed_seconds=round(time.monotonic()-start, 2), command=command, model_requests=0)
    (HERE / 'validation/related_final.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'command'}), flush=True)
    raise SystemExit(run.returncode)


if __name__ == '__main__':
    main()
