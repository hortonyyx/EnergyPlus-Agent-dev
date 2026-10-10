"""Read-only preloaded journal microbenchmark; no writer, tools, or model calls.

python scripts/benchmark_runtime_journal.py --run <frozen-run-directory>
Prints JSON only. The caller may save it in a new evidence directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts
from src.harness_contracts.incremental import EventValidationIndex


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    metadata = json.loads((args.run / "journal.json").read_bytes())
    limit = BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"]))
    events = EventStore.read_events(args.run / "events.jsonl")
    full = object.__new__(EventStore)
    full.root_task_id, full.budget_limit = metadata["task_id"], limit
    def new_index():
        return EventValidationIndex(run_id=metadata["run_id"], root_task_id=metadata["task_id"], budget_limit=limit)
    def measure(callback):
        samples = []
        for _ in range(args.repeats):
            started = time.perf_counter()
            callback()
            samples.append((time.perf_counter() - started) * 1000)
        return {"median_ms": statistics.median(samples), "samples_ms": samples}
    rows = []
    for count in dict.fromkeys(n for n in (100, 300, 600, 900, len(events)) if n <= len(events)):
        prefix = events[:count]
        index = new_index()
        for event in prefix[:-1]:
            index.commit(event, index.prepare(event))
        budget_position = next((n for n in range(count - 1, -1, -1)
                                if events[n].payload.event_type == "budget"), None)
        budget_measurement = None
        if budget_position is not None:
            budget_index = new_index()
            for event in events[:budget_position]:
                budget_index.commit(event, budget_index.prepare(event))
            budget_measurement = {"sequence": events[budget_position].sequence,
                "action": events[budget_position].payload.action,
                **measure(lambda: budget_index.prepare(events[budget_position]))}
        rows.append({"events": count,
            "complete_prefix_validation": measure(lambda: full._validate_events(prefix)),
            "incremental_next_event_type": prefix[-1].payload.event_type,
            "incremental_next_event_validation": measure(lambda: index.prepare(prefix[-1])),
            "incremental_nearest_budget_event": budget_measurement})
    def replay():
        index = new_index()
        for event in events:
            index.commit(event, index.prepare(event))
    print(json.dumps({"source_run": str(args.run.resolve()), "event_count": len(events),
        "events_sha256": hashlib.sha256((args.run / "events.jsonl").read_bytes()).hexdigest(),
        "method": "Preloaded complete prefix versus next-event prepare; I/O excluded. Incremental replay includes all events once. No model or tool calls.",
        "repeats": args.repeats, "rows": rows, "incremental_full_replay": measure(replay)}, indent=2))


if __name__ == "__main__":
    main()
