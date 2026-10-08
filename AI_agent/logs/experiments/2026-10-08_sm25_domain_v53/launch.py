"""Launch the single user-approved run from frozen code; no automatic rerun."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

EXPERIMENT = Path(__file__).resolve().parent
WORKTREE = Path('D:/EnergyPlus-Agent-worktrees/run-sm25-v53-20261008')
CONFIGURATION = EXPERIMENT / 'sm25_v53.json'
OUTPUT = WORKTREE / 'AI_agent/archive/local_backup/sm25_v53/sm25_role_v53'


def write(name, value):
    (EXPERIMENT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    receipt_path = EXPERIMENT / 'launch_receipt.json'
    if receipt_path.exists() or OUTPUT.exists():
        raise SystemExit('This run has already been launched; no automatic rerun is permitted.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORKTREE, text=True).strip()
    assert commit == 'b55d47e7c82bb306c7ea838f00985648eef94304', commit
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=WORKTREE, text=True).strip()
    for args in (
        ['-m', 'src.agent_runtime.agent_registry', 'verify'],
        ['-m', 'src.agent.runtime_configuration', 'check', str(CONFIGURATION)],
    ):
        subprocess.run([sys.executable, *args], cwd=WORKTREE, check=True)
    source = WORKTREE / 'case_tests/e2e_tests/sm25-L_anchor/case_data'
    manifest = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(source.rglob('*')) if p.is_file()}
    write('input_manifest_before.json', manifest)
    command = [sys.executable, '-m', 'src.agent.runtime_configuration', 'launch', str(CONFIGURATION), '--case', 'sm25_role_v53']
    receipt = {'status': 'starting', 'started_utc': datetime.now(timezone.utc).isoformat(),
               'source_commit': commit, 'worktree': str(WORKTREE), 'output': str(OUTPUT),
               'configuration_sha256': hashlib.sha256(CONFIGURATION.read_bytes()).hexdigest(),
               'command': command, 'input_files': len(manifest)}
    write('launch_receipt.json', receipt)
    with (EXPERIMENT / 'launcher.stdout.log').open('w', encoding='utf-8') as stdout, (EXPERIMENT / 'launcher.stderr.log').open('w', encoding='utf-8') as stderr:
        process = subprocess.Popen(command, cwd=WORKTREE, stdout=stdout, stderr=stderr)
        receipt.update(status='running', launcher_pid=process.pid)
        write('launch_receipt.json', receipt)
        print(json.dumps({'status': 'running', 'pid': process.pid, 'output': str(OUTPUT)}, ensure_ascii=False), flush=True)
        code = process.wait()
    after = {p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(source.rglob('*')) if p.is_file()}
    write('input_manifest_after.json', after)
    receipt.update(status='process_exited', exit_code=code, ended_utc=datetime.now(timezone.utc).isoformat(), inputs_unchanged=after == manifest)
    write('launch_receipt.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False), flush=True)
    raise SystemExit(code)


if __name__ == '__main__':
    main()
