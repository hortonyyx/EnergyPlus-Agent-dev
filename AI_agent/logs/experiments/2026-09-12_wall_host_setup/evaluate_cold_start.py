"""Reuse the existing independent evaluator after generation completes."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
run = Path(sys.argv[1]).resolve()
assert (run / "summary.json").exists(), "Generation must finish first"
path = ROOT / "AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run06/evaluate.py"
spec = importlib.util.spec_from_file_location("post_generation_evaluator", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.RUN = run
module.main()
