"""Audit explicitly developer-targeted recovery separately from general review."""
import importlib
from pathlib import Path

if __name__ == '__main__':
    audit = importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_local_plan_setup.audit_run')
    delta = importlib.import_module('AI_agent.logs.experiments.2026-09-24_sm25_continuous_space_setup.audit_run')
    audit.HERE = Path(__file__).resolve().parent
    audit.RUN = audit.HERE.parent / '2026-09-24_sm25_partition_feedback_glm_run45'
    audit.main()
    delta.compare_recovery(audit.RUN, previous=audit.RUN.parent / '2026-09-24_sm25_continuous_space_glm_run44/candidate_03')
