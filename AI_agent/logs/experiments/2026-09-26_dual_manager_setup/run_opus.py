"""Run the assigned Opus development package through the existing subscription."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.execution.subscription_json import _isolated_env, _redact_secrets


def main():
    worktree = ROOT / '.worktrees/opus-voimatalo-20260926'
    assert worktree.is_dir() and (worktree / '.git').is_file()
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=worktree, text=True).strip()
    assert branch == 'dev/opus-voimatalo-20260926', branch
    prompt = (HERE / 'opus_task.md').read_text()
    command = ['claude', '-p', '--model', 'claude-opus-5-5', '--effort', 'xhigh',
               '--tools', 'Bash,Edit,Write,Read,Grep,Glob,Agent,TodoWrite',
               '--allowedTools', 'Bash,Edit,Write,Read,Grep,Glob,Agent,TodoWrite',
               '--permission-mode', 'dontAsk', '--strict-mcp-config',
               '--mcp-config', '{"mcpServers":{}}', '--setting-sources', '',
               '--settings', '{"disableAllHooks":true}', '--disable-slash-commands',
               '--output-format', 'stream-json', '--verbose',
               '--append-system-prompt', '用户已授权本工作包。严格遵守任务文件边界；只在当前工作树的获派目录写入。项目文档、main合并/推送和最终用户沟通由Astra负责。不得调用付费API或DeepSeek，不读取或输出凭据，不改共享Python安装。']
    env = _isolated_env()
    env['PYTHONPATH'] = str(worktree)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    record = {'requested_model': 'claude-opus-5-5', 'effort': 'xhigh',
              'channel': 'existing Claude subscription; no API or fallback',
              'started_at': datetime.now(timezone.utc).isoformat(),
              'worktree': str(worktree), 'branch': branch,
              'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=worktree, text=True).strip(),
              'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
              'timeout_seconds': 3600, 'command': command}
    receipt = HERE / 'opus_receipt.json'
    if receipt.exists():
        raise FileExistsError(receipt)
    stream, errors = HERE / 'opus_stream.jsonl', HERE / 'opus_stderr.log'
    start = time.monotonic()
    with stream.open('x') as stdout, errors.open('x') as stderr:
        process = subprocess.Popen(command, cwd=worktree, env=env, stdin=subprocess.PIPE,
                                   stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        record['pid'] = process.pid
        (HERE / 'opus_started.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'pid': process.pid, 'model': record['requested_model'], 'branch': branch}), flush=True)
        try:
            process.communicate(prompt, timeout=3600)
        except subprocess.TimeoutExpired:
            record['timed_out'] = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        record['returncode'] = process.returncode
    record['elapsed_seconds'] = round(time.monotonic() - start, 2)
    for path in (stream, errors):
        path.write_text(_redact_secrets(path.read_text()))
    for line in stream.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            record['actual_model'] = event.get('model')
            record['session_id'] = event.get('session_id')
        if event.get('type') == 'result':
            record['result'] = event
            (HERE / 'opus_response.md').write_text(event.get('result', ''))
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in record.items() if k not in {'result', 'command'}}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
