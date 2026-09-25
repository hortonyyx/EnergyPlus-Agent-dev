"""Independent repetition with identical inputs, scope, implementation and budget."""
import importlib
from pathlib import Path

if __name__ == '__main__':
    run = importlib.import_module('AI_agent.logs.experiments.2026-09-25_sm25_relation_cold_setup.run_cold')
    run.HERE = Path(__file__).resolve().parent
    run.RUN = run.HERE.parent/'2026-09-25_sm25_relation_repeat_claude_run49'
    run.main()
