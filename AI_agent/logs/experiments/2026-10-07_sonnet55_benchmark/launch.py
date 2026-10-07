"""Launch one benchmark case of bench.json in a fixed run worktree (Claude Code route).

python launch.py <case> <run worktree> <state directory>
Writes <state>/<case>.exit.txt when the runner exits; output goes to
<worktree>/AI_agent/archive/local_backup/bench/<case>.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

case, tree, state = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
bench = json.loads((Path(__file__).parent / "bench.json").read_text(encoding="utf-8"))
spec = bench["cases"][case]
scope = bench["scope_task"] + "\n" + spec["organization"]
out = tree / "AI_agent/archive/local_backup/bench" / case
command = [str(tree / ".venv/Scripts/python.exe"), "scripts/tool_scripts/run_bim_agent.py", "run",
           *bench["common_args"], *spec["args"], "--out", str(out), "--scope", scope]
env = {**os.environ, "VIRTUAL_ENV": str(tree / ".venv"), "PYTHONUTF8": "1",
       "PYTHONPATH": str(tree), "OPENBLAS_NUM_THREADS": "1"}
env["PATH"] = str(tree / ".venv/Scripts") + os.pathsep + env.get("PATH", "")
state.mkdir(parents=True, exist_ok=True)
(state / f"{case}.command.json").write_text(json.dumps(command, ensure_ascii=False, indent=1), encoding="utf-8")
with open(state / f"{case}.stdout.log", "w", encoding="utf-8") as stdout, \
        open(state / f"{case}.stderr.log", "w", encoding="utf-8") as stderr:
    code = subprocess.call(command, cwd=tree, env=env, stdout=stdout, stderr=stderr)
(state / f"{case}.exit.txt").write_text(f"exit={code}\n", encoding="utf-8")
