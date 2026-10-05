"""Offline C3-R timing: unchanged run99 calls, real tools, no model transport."""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from src.agent.runtime_tools import FrozenBimTools, coordinator_role
from src.agent_runtime import loop
from src.agent_runtime.context import ContextManager
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts
import test_runtime_frozen_long_task as replay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--snapshot-directory", type=Path, action="append", default=[])
    args = parser.parse_args()
    timings, stack = defaultdict(list), []

    def instrument(owner, name, label):
        original = getattr(owner, name)
        def timed(*a, **kw):
            started = time.perf_counter()
            frame = [0.0]
            stack.append(frame)
            try:
                return original(*a, **kw)
            finally:
                elapsed = time.perf_counter() - started
                stack.pop()
                if stack:
                    stack[-1][0] += elapsed
                timings[label].append({"seconds": elapsed, "exclusive_seconds": elapsed - frame[0]})
        setattr(owner, name, timed)

    instrument(loop.Runtime, "_checkpoint", "checkpoint")
    instrument(FrozenBimTools, "snapshot_state", "snapshot_scan")
    instrument(EventStore, "append", "event_append")
    instrument(ContextManager, "project", "context_projection")
    instrument(ContextManager, "full_history", "context_history")
    instrument(replay, "update_building_context", "building_context")
    instrument(loop, "prepare_request", "request_preparation")
    started = time.perf_counter()
    result = asyncio.run(replay.replay_frozen_run99(args.output))
    elapsed = time.perf_counter() - started
    snapshots = []
    for directory in args.snapshot_directory:
        tools = FrozenBimTools(None, coordinator_role(BudgetAmounts(calls=1)), run_directory=directory)
        samples = []
        for _ in range(3):
            start = time.perf_counter()
            state = tools.snapshot_state()
            samples.append(time.perf_counter() - start)
        snapshots.append({"directory": str(directory), "seconds": samples,
                          "file_count": len(state["files"]), "sha256": state["snapshot_sha256"]})
    report = {"replay_seconds": elapsed, "receipt_status": result["receipt"]["status"],
              "calls": len(result["calls"]), "requests": len(result["requests"]),
              "model_service_requests": 0, "timings": dict(timings), "snapshots": snapshots,
              "summary": {name: {"count": len(rows),
                  "total_seconds": sum(row["seconds"] for row in rows),
                  "exclusive_seconds": sum(row["exclusive_seconds"] for row in rows),
                  "median_seconds": statistics.median(row["seconds"] for row in rows)}
                  for name, rows in timings.items()},
              "note": "Inclusive totals overlap; exclusive totals do not. Real tools, scripted model responses. Historical snapshots are read-only."}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"timings"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
