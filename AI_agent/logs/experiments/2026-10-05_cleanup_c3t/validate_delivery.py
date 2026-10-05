"""Check file ownership, immutable history, registration and chosen final BIMs."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

from src.agent_runtime.agent_registry import agent_version_record

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def baseline(path):
    return subprocess.check_output(['git', 'show', 'a5baa32d:' + path], cwd=ROOT)


def functions(text):
    def walk(body, prefix=''):
        result = {}
        for node in body:
            if isinstance(node, ast.ClassDef):
                result.update(walk(node.body, prefix + node.name + '.'))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[prefix + node.name] = ast.dump(node, include_attributes=False)
        return result
    return walk(ast.parse(text).body)


def main():
    scopes = {
        'src/agent/runtime_context.py': {'update_building_context'},
        'src/agent/runtime_coordinator.py': {'CoordinatorSession.source_bim',
            'CoordinatorSession._execute_frozen', 'CoordinatorSession._restore_indexes'},
        'src/agent/runtime_tools.py': {'_result_metadata'},
    }
    changed_functions = {}
    for path, allowed in scopes.items():
        before, after = functions(baseline(path)), functions((ROOT / path).read_bytes())
        changed = {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)}
        assert changed <= allowed, (path, changed - allowed)
        changed_functions[path] = sorted(changed)
    path = 'scripts/tool_scripts/bim_agent_budget.py'
    assert baseline(path) == (ROOT / path).read_bytes()
    path = 'scripts/tool_scripts/bim_agent_guidance.py'
    def finishing(raw):
        return next(ast.dump(n, include_attributes=False) for n in ast.parse(raw).body
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FINISHING' for t in n.targets))
    assert finishing(baseline(path)) == finishing((ROOT / path).read_bytes())
    registry_path = 'src/agent_runtime/agent_versions.json'
    old, new = json.loads(baseline(registry_path)), json.loads((ROOT / registry_path).read_bytes())
    assert all(new['versions'][key] == value for key, value in old['versions'].items())
    registered = agent_version_record(ROOT)
    paths = subprocess.check_output(['git', 'diff', '--name-only', 'a5baa32d'], cwd=ROOT, text=True).splitlines()
    assert all(p.startswith(('scripts/tool_scripts/', 'tests/', str(HERE.relative_to(ROOT)) + '/'))
        or p in scopes or p in {'src/agent/runtime_behaviour.py', registry_path} for p in paths)
    verified = 0
    for experiment in ('2026-10-04_node_regression_a1', '2026-10-04_qwen27b_probe', '2026-10-04_qwen27b_after_a2'):
        for manifest in (HERE.parent / experiment / 'evidence').glob('*_manifest.json'):
            row = json.loads(manifest.read_bytes())
            root = ROOT / '.tmp_c3t/history' / row['extracted_root']
            for relative, digest in row['files_sha256'].items():
                assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest
                verified += 1
    chosen = []
    after = json.loads((HERE / 'after.json').read_bytes())
    for entry in after['precision']:
        root = ROOT / '.tmp_c3t/history' / entry['run']
        root = root / 'bim' if (root / 'bim').is_dir() else root
        delivery = root / 'delivery.json'
        assert json.loads(delivery.read_bytes())['candidate'] == entry['candidate']
        assert hashlib.sha256((root / entry['candidate'] / 'source_model.json').read_bytes()).hexdigest() == entry['source_sha256']
        chosen.append(dict(run=entry['run'], candidate=entry['candidate'],
            delivery_sha256=hashlib.sha256(delivery.read_bytes()).hexdigest()))
    result = dict(agent_version=registered['version_id'], registered_file_count=len(registered['files']),
        old_versions_preserved=True, changed_functions=changed_functions,
        c3r_budget_and_finishing_unchanged=True, historical_files_reverified=verified,
        finals_match_archived_deliveries=chosen, model_requests=0)
    (HERE / 'validation/delivery.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
