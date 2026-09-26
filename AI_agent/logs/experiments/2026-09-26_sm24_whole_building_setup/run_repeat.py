"""Independent repetition; no first-run result enters the new product call."""
import importlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

if __name__=='__main__':
    runner=importlib.import_module('AI_agent.logs.experiments.2026-09-26_sm24_whole_building_setup.run_cold')
    original=json.loads((HERE/'frozen_method.json').read_text())
    assert runner.SCOPE==original['scope']
    runner.RUN=HERE.parent/'2026-09-26_sm24_whole_building_repeat_claude_run56'
    runner.HERE=HERE/'repeat'
    runner.HERE.mkdir(exist_ok=True)
    runner.main()
