"""Check work-package ownership and unchanged historical version records."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = 'f4d48cf7'


def old(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def main():
    runner = 'scripts/tool_scripts/run_bim_agent.py'
    def function(raw):
        text = raw.decode()
        return next(ast.get_source_segment(text, node).encode() for node in ast.parse(text).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'run_experiment')
    before, after = function(old(runner)), function((ROOT/runner).read_bytes())
    assert before == after
    registry = 'src/agent_runtime/agent_versions.json'
    baseline, current = json.loads(old(registry)), json.loads((ROOT/registry).read_bytes())
    assert all(current['versions'][k] == v for k,v in baseline['versions'].items())
    protected = ['scripts/tool_scripts/evaluate_bim_agent.py', 'src/agent/runtime_entry.py',
                 'src/agent/runtime_context.py']
    unchanged = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected}
    assert all((ROOT/p).read_bytes() == old(p) for p in protected)
    from src.agent_runtime.agent_registry import agent_version_record
    record = agent_version_record(ROOT)
    result = dict(baseline_commit=BASE, agent_version=record['version_id'],
        current_registered_files_verified=len(record['files']),
        run_experiment_bytes_unchanged=True, run_experiment_sha256=hashlib.sha256(after).hexdigest(),
        protected_files_unchanged=unchanged,
        old_version_records_unchanged=len(baseline['versions']),
        new_versions=[k for k in current['versions'] if k not in baseline['versions']], model_requests=0)
    (HERE/'scope_checks.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
