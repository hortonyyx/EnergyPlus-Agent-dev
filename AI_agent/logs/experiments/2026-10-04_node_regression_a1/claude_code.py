"""Claude Code (GLM subscription) leg of the absorption-batch-1 node regression; prepare calls no model.

Reuses the T1 launcher unchanged (same images, task, medium effort, 24 candidates, no
delegation or continuation, 6000 s), but writes preflights here and runs under runs/,
because the T1 run folders already exist and are never overwritten.
"""
import importlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
t1 = importlib.import_module("AI_agent.logs.experiments.2026-10-03_tool_package_t1.glm_tests")
t1.HERE = HERE
t1.PLAN = {case: f"{HERE.name}/runs/{case}_claude_code" for case in ("sm24", "sm25", "sm21")}

if __name__ == "__main__":
    action, case = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    if action == "prepare":
        t1.prepare(6000)
    elif action == "run" and case:
        t1.run_one(case, 6000)
    else:
        raise SystemExit("usage: claude_code.py prepare | run <case>")
