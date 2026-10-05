"""Read-only replay of a historical tool/checkpoint scan schedule on both disks.

The final BIM directory is held fixed: this measures scan overhead only, not
model time, tool execution or journal writes. No writes to the 9p worktree.
"""
import argparse
import copy
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.agent.runtime_tools import FrozenBimTools, coordinator_role
from src.harness_contracts import BudgetAmounts


def replay(journal, directory, cached):
    schedule = [json.loads(line)["payload"]["event_type"] for line in journal.read_bytes().splitlines()]
    schedule = [kind for kind in schedule if kind in {"checkpoint", "tool_invocation", "tool_execution"}]
    tools = FrozenBimTools(None, coordinator_role(BudgetAmounts(calls=1)), run_directory=directory)
    rows, state, scans = [], None, 0
    started = time.perf_counter()
    for number, kind in enumerate(schedule):
        before = time.perf_counter()
        if not cached or kind != "checkpoint" or state is None:
            state = tools.snapshot_state()
            scans += 1
        saved = copy.deepcopy(state)
        rows.append(dict(step=number, kind=kind, seconds=time.perf_counter()-before))
    return dict(cached=cached, directory=str(directory), seconds=time.perf_counter()-started,
                filesystem=subprocess.check_output(["findmnt", "-T", str(directory), "-n", "-o", "FSTYPE"], text=True).strip(),
                scan_count=scans, final_snapshot_sha256=saved["snapshot_sha256"], rows=rows,
                checkpoint_median_seconds=statistics.median(r["seconds"] for r in rows if r["kind"] == "checkpoint"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--directory", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"scope": __doc__, "runs": []}
    for directory in args.directory:
        for cached in (False, True):
            result = replay(args.journal, directory, cached)
            report["runs"].append(result)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)
