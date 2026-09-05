"""Replay original read-only command lists; preserve all old evidence files."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
os.chdir(ROOT)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
for date, filename, collection in (
    ('2026-09-05e', 'capture_evidence.py', 'commands'),
    ('2026-09-05h', 'capture.py', 'groups'),
):
    original = ROOT / f'AI_agent/logs/experiments/{date}_tick_claim_crossreview_gpt/{filename}'
    namespace = {'__file__': str(original), '__name__': '__capture_commands_only__'}
    # Only load the original command declarations. Its file-output loop is not
    # executed: output belongs to this run. Command strings remain unchanged.
    exec(compile(original.read_text().split('env = dict(os.environ')[0], str(original), 'exec'), namespace)
    output = [f'# {date}: original command list, replayed in current worktree\n']
    for title, command in namespace[collection]:
        p = subprocess.run(['bash', '-c', command], cwd=ROOT, env=env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output.append(f'\n## {title}\n\n```sh\n{command}\n```\n\n```text\n{p.stdout}[exit {p.returncode}]\n```\n')
        print(date, title, 'exit', p.returncode, flush=True)
    (OUT / f'legacy_{date}.md').write_text(''.join(output))
for date in ('2026-09-05e', '2026-09-05h'):
    command = [sys.executable, f'AI_agent/logs/experiments/{date}_tick_claim_crossreview_gpt/probe.py', 'numbers']
    p = subprocess.run(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / f'legacy_{date}_numbers.txt').write_text('$ ' + ' '.join(command) + '\n' + p.stdout + f'\n[exit {p.returncode}]\n')
