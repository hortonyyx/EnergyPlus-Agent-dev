"""Explicitly requested design discussion over the existing Claude subscription."""
from datetime import datetime, timezone
import hashlib
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from src.agent.execution.subscription_json import _isolated_env, _redact_secrets


def run(name):
    archived = HERE / f"{name}_prompt.md.gz"
    prompt = (gzip.decompress(archived.read_bytes()).decode() if archived.exists()
              else (HERE / f"{name}_prompt.md").read_text())
    command = ["claude", "-p", "--model", "claude-opus-5-5", "--effort", "high",
        "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--permission-mode", "dontAsk", "--setting-sources", "",
        "--settings", '{"disableAllHooks":true}', "--disable-slash-commands",
        "--no-session-persistence", "--output-format", "stream-json", "--verbose",
        "--system-prompt", "你是受用户邀请参与项目设计讨论的开发审阅者。只根据所给资料进行独立批评和方案推理。没有工具，不执行代码，不调用其他模型。区分事实、推断与建议，不声称运行过实验。用中文给出可操作的结论。"]
    record = {"requested_model": "claude-opus-5-5", "effort": "high",
        "channel": "existing Claude subscription; isolated environment; no API/fallback",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "timeout_seconds": 1200, "command": command}
    receipt = HERE / f"{name}_receipt.json"
    if receipt.exists():
        raise FileExistsError(receipt)
    start = time.monotonic()
    stdout_path, stderr_path = HERE / f"{name}_stream.jsonl", HERE / f"{name}_stderr.log"
    with tempfile.TemporaryDirectory(prefix="opus55-design-") as cwd:
        with stdout_path.open("x") as stdout, stderr_path.open("x") as stderr:
            process = subprocess.Popen(command, cwd=cwd, env=_isolated_env(),
                stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, text=True,
                start_new_session=True)
            try:
                process.communicate(prompt, timeout=1200)
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            record["returncode"] = process.returncode
    record["elapsed_seconds"] = round(time.monotonic() - start, 2)
    for path in (stdout_path, stderr_path):
        path.write_text(_redact_secrets(path.read_text()))
    for line in stdout_path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            record["actual_model"] = event.get("model")
        if event.get("type") == "assistant":
            record.setdefault("assistant_models", [])
            model = event.get("message", {}).get("model")
            if model and model not in record["assistant_models"]:
                record["assistant_models"].append(model)
        if event.get("type") == "result":
            record["result"] = event
            (HERE / f"{name}_response.md").write_text(event.get("result", ""))
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k:v for k,v in record.items() if k not in {"result", "command"}}, ensure_ascii=False))


if __name__ == "__main__":
    run(sys.argv[1])
