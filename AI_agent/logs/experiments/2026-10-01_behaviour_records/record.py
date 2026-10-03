"""Historical command entry for the shared, offline BIM behaviour recorder.

Both CLI streams and runtime events use src.agent.runtime_behaviour. This file
only preserves the experiment-directory/default-output convention; parsing,
metrics and reports have a single implementation.
"""
import argparse
import json
from pathlib import Path

from src.agent.runtime_behaviour import write_behaviour_report

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent


def record(run, out=None):
    run = Path(run)
    run = run if run.is_absolute() else EXPERIMENTS / run
    return write_behaviour_report(run, out or HERE / "records" / run.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", help="run directories (CLI or runtime), or experiment names")
    parser.add_argument("--output-root", type=Path, default=HERE / "records")
    args = parser.parse_args()
    for name in args.runs:
        summary = record(Path(name), args.output_root / Path(name).name)
        print(json.dumps({key: summary[key] for key in (
            "run", "model", "elapsed_seconds", "tool_calls", "call_errors", "domain_failures",
            "usable_source_drafts", "first_draft_s")}, ensure_ascii=False))
