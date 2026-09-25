"""Post-generation audit, with identical-method comparison against run48."""
import importlib
import json
from pathlib import Path

if __name__ == '__main__':
    audit = importlib.import_module('AI_agent.logs.experiments.2026-09-25_sm25_space_relation_setup.audit_run')
    audit.HERE = Path(__file__).resolve().parent
    audit.RUN = audit.HERE.parent/'2026-09-25_sm25_relation_repeat_claude_run49'
    first = audit.HERE.parent/'2026-09-25_sm25_relation_cold_setup/frozen_method.json'
    assert json.loads(first.read_text()) == json.loads((audit.HERE/'frozen_method.json').read_text())
    audit.main()
