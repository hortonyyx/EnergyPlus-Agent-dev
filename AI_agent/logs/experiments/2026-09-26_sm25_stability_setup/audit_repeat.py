"""Reuse post-generation checks without changing prior runs or their evaluation."""
import importlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "2026-09-26_sm25_height_repeat_claude_run54"

if __name__ == "__main__":
    audit = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_height_review_setup.audit_cold")
    audit.HERE, audit.RUN = HERE, RUN
    audit.main()
    report_path = RUN / "postrun_audit.json"
    report = json.loads(report_path.read_text())
    report['limits'][0] = ('Independent repetition of run53 original-only scope; current bounded '
        'delivery summary differs from run53. Same case; not cross-case generalization.')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
