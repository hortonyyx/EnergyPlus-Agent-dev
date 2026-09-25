"""Audit the cold run only after generation; reuse the independent audit machinery."""
import importlib
from pathlib import Path

if __name__ == '__main__':
    audit = importlib.import_module('AI_agent.logs.experiments.2026-09-25_sm25_space_relation_setup.audit_run')
    audit.HERE = Path(__file__).resolve().parent
    audit.RUN = audit.HERE.parent/'2026-09-25_sm25_relation_cold_claude_run48'
    audit.main()
