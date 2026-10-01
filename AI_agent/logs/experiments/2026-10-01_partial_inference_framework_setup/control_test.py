"""Record external-controller start and integrity checks; never invokes a model."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/ep-partial-developer-tests-20261001')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_runtime(name):
    manifest = json.loads((HERE / 'test_manifest.json').read_text())
    runtime = WORK / name.replace('run_', 'runtime_')
    actual = {str(p.relative_to(runtime)): sha(p) for p in runtime.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    expected = manifest['runtime_files']
    changed = [p for p in expected if actual.get(p) != expected[p]]
    added = sorted(set(actual) - set(expected))
    return {'status': 'pass' if not changed and not added else 'changed',
            'checked_files': len(expected), 'changed_or_missing': changed, 'added': added}


def main():
    action, name = sys.argv[1:]
    if name not in {'run_61sol', 'run_6sol'} or action not in {'start', 'verify'}:
        raise ValueError('use start|verify run_61sol|run_6sol')
    run = WORK / name
    integrity = verify_runtime(name)
    assert integrity['status'] == 'pass', integrity
    if action == 'verify':
        request = json.loads((run / 'controller_request.json').read_text())
        integrity['inputs_unchanged'] = sha(run / 'inputs.json') == request['active_inputs_sha256']
        integrity['prompt_unchanged'] = sha(run / 'DEVELOPER_TASK.txt') == request['developer_prompt_sha256']
        integrity['task_unchanged'] = sha(run / 'task.txt') == request['task_sha256']
        integrity['guide_unchanged'] = sha(run / 'guide.txt') == request['guide_sha256']
        integrity['verified_utc'] = datetime.now(timezone.utc).isoformat()
        if not all(integrity[k] for k in ('inputs_unchanged', 'prompt_unchanged', 'task_unchanged', 'guide_unchanged')):
            integrity['status'] = 'changed'
        (run / 'controller_integrity.json').write_text(json.dumps(integrity, indent=2) + '\n')
        print(json.dumps(integrity)); return
    path = run / 'inputs.json'
    manifest = json.loads(path.read_text())
    prepared = sha(path)
    started = time.time()
    manifest.update(start_epoch=started, deadline_epoch=started + 3600)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    request = {'status': 'dispatch_pending', 'requested_model': manifest['development_model'],
        'reasoning_effort': 'max', 'channel': manifest['execution_channel'],
        'start_epoch': started, 'start_utc': datetime.fromtimestamp(started, timezone.utc).isoformat(),
        'deadline_epoch': manifest['deadline_epoch'], 'max_seconds': 3600,
        'prepared_inputs_sha256': prepared, 'active_inputs_sha256': sha(path),
        'developer_prompt_sha256': sha(run / 'DEVELOPER_TASK.txt'), 'runtime_integrity': integrity,
        'task_sha256': sha(run / 'task.txt'), 'guide_sha256': sha(run / 'guide.txt'),
        'token_usage': None, 'billing': None,
        'usage_note': 'Not exposed by collaboration tool; no inferred token/cost figures.',
        'submodels': 0, 'automatic_restarts': 0, 'fallbacks': 0}
    with (run / 'controller_request.json').open('x') as stream:
        json.dump(request, stream, ensure_ascii=False, indent=2)
    print(json.dumps(request, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
