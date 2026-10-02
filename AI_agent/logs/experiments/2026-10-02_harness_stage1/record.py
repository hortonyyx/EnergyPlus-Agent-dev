#!/usr/bin/env python3
"""Generate a behaviour report from current or historical runtime logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent.runtime_behaviour import write_behaviour_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True,
                        help="Output root; each run gets its own directory")
    args = parser.parse_args()
    for run in args.runs:
        summary = write_behaviour_report(run, args.out / run.name)
        print(json.dumps({key: summary[key] for key in
                          ("run", "source_format", "tool_calls", "tool_errors", "first_draft_s")},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
