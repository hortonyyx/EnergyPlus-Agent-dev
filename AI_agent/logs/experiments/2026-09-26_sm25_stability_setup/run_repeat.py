"""Repeat run53's exact original-only scope with the current delivery-summary fix."""
import importlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-26_sm25_height_repeat_claude_run54"

if __name__ == "__main__":
    runner = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_height_review_setup.run_cold")
    runner.HERE, runner.RUN = HERE, RUN
    runner.main()
