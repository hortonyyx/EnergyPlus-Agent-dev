"""Run the three explicitly requested, read-only Claude subscription reviews."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]


def run(name):
    output = ROOT / f"{name}_stream.jsonl"
    if any((ROOT / f"{name}{suffix}").exists() for suffix in (
        "_stream.jsonl", "_stream.jsonl.gz", "_run.json", "_report.md", "_stderr.log",
    )):
        raise FileExistsError(f"Refusing to rerun or overwrite completed/in-progress review {name}")
    env = {k: v for k, v in os.environ.items() if k in {
        "PATH", "HOME", "LANG", "LC_ALL", "CLAUDE_CODE_OAUTH_TOKEN",
    }}
    command = [
        "claude", "-p", "--model", "sonnet", "--effort", "high",
        "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob",
        "--permission-mode", "dontAsk", "--strict-mcp-config",
        "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "",
        "--settings", '{"disableAllHooks":true}',
        "--no-session-persistence", "--output-format", "stream-json", "--verbose",
    ]
    record = {"name": name, "command": command, "cwd": str(REPO),
              "started_at": datetime.now(timezone.utc).isoformat(),
              "channel": "Claude logged-in subscription; no API keys/endpoints; no fallback"}
    start = time.monotonic()
    with output.open("x") as stream, (ROOT / f"{name}_stderr.log").open("x") as stderr:
        try:
            result = subprocess.run(command, input=(ROOT / f"{name}_prompt.md").read_text(),
                                    text=True, cwd=REPO, env=env, stdout=stream,
                                    stderr=stderr, timeout=1200)
            record["returncode"] = result.returncode
        except subprocess.TimeoutExpired:
            record["timeout"] = True
    record["elapsed_seconds"] = round(time.monotonic() - start, 2)
    for line in output.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            record["actual_model"] = event.get("model")
        if event.get("type") == "result":
            record["result"] = event
            (ROOT / f"{name}_report.md").write_text(event.get("result", ""))
    (ROOT / f"{name}_run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "result"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(run, ["history", "architecture", "options"]))
