"""Post-generation checks only; reuse prior original/GT/source/transport audits."""
import argparse
import importlib
import json
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    previous = importlib.import_module("AI_agent.logs.experiments.2026-09-28_reconstruction_behavior.evaluate_run")
    with patch.object(previous, "HERE", HERE):
        previous.audit(args.run.resolve())
    report = args.run / "postrun_audit.json"
    if report.exists():
        data = json.loads(report.read_text())
        assert data["invocations"] == 1


if __name__ == "__main__":
    main()
