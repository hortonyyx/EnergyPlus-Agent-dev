"""Offline recovery review. Run from the repository root with Python -B.

Only this script's newly created TemporaryDirectory trees are mutated/removed.
The historical run is read through EventStore.read_events, never opened as a
writer. Results go to stdout; --output explicitly saves an additional JSON file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXPECTED_HEAD = "6e88fd7395aadde129da11b6ae481d7b472e4385"
BASELINE_PATHS = ("src", "tests", "pyproject.toml", "uv.lock")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_agent_runtime import MESSAGES, response, runtime
from test_runtime_a4r_money import configure
from test_runtime_child_tasks import _child
from test_runtime_recovery_edges import InjectedCrash
from src.agent_runtime.budget import RuntimeBudget
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, RunLifecyclePayload


def crash_case(loop, boundary, tool, expected):
    with tempfile.TemporaryDirectory(prefix="runtime_review_") as directory:
        path = Path(directory)
        first = runtime(path, [response(("call-1", tool, {"value": 1})), response(text="done")])

        def crash(name, engine):
            if name == boundary:
                raise InjectedCrash(name)

        first.fault_hook = crash
        with first.store:
            try:
                loop.run_until_complete(first.run(MESSAGES))
            except InjectedCrash:
                pass
        resumed = runtime(path, [response(text="done")], tools=first.tools)
        with resumed.store:
            result = loop.run_until_complete(resumed.run(MESSAGES, resume=True))
            assert result["status"] == expected
            if boundary == "after_reservation":
                assert len(first.adapter.requests) == len(first.tools.calls) == 0
            if boundary in {"after_response", "after_execution"}:
                assert len(first.tools.calls) == 1
            resumed.store.validate()
            return {
                "expected_current_status": expected,
                "actual_status": result["status"],
                "initial_scripted_adapter_calls": len(first.adapter.requests),
                "resume_scripted_adapter_calls": len(resumed.adapter.requests),
                "total_tool_calls": len(first.tools.calls),
                "committed_calls": resumed.budget.ledger.committed.calls,
                "journal_valid": True,
            }


def cancellation_case(loop):
    with tempfile.TemporaryDirectory(prefix="runtime_cancel_review_") as directory:
        path = Path(directory)
        first = runtime(path, [response(("call-1", "view", {}))])

        async def cancel_during_read():
            entered = asyncio.Event()

            async def wait_forever(name, arguments):
                entered.set()
                await asyncio.Future()

            first.tools.call_tool = wait_forever
            task = asyncio.create_task(first.run(MESSAGES))
            await entered.wait()
            task.cancel()
            return await task

        with first.store:
            first_result = loop.run_until_complete(cancel_during_read())
            assert first_result["status"] == "cancelled"
        resumed = runtime(path, [response(text="done")], tools=first.tools)
        with resumed.store:
            result = loop.run_until_complete(resumed.run(MESSAGES, resume=True))
            assert result["status"] == "resume_pending_operation"
            assert resumed.adapter.requests == []
            resumed.store.validate()
            return {
                "first_status": first_result["status"],
                "expected_current_resume_status": "resume_pending_operation",
                "actual_resume_status": result["status"],
                "resume_scripted_adapter_calls": 0,
                "journal_valid": True,
            }


def sibling_case(loop):
    with tempfile.TemporaryDirectory(prefix="runtime_sibling_review_") as directory:
        path = Path(directory)
        limits = RunLimits(model_calls=6, tool_calls=6, seconds=30, tokens=200000,
                           money_cny=Decimal("1"))
        with EventStore(path / "run", run_id="offline-sibling", task_id="root",
                        budget_limit=limits.ledger_limit()) as root:
            root.append(RunLifecyclePayload(action="start", reason="offline root"))
            first_b = configure(_child(root, path, "B", []))

            def before_request(name, engine):
                if name == "before_request":
                    raise InjectedCrash(name)

            first_b.fault_hook = before_request
            try:
                loop.run_until_complete(first_b.run(MESSAGES))
            except InjectedCrash:
                pass
            child_a = configure(_child(root, path, "A", [response(text="missing", usage=False)]))
            result_a = loop.run_until_complete(child_a.run(MESSAGES))
            resumed_b = configure(_child(root, path, "B", [], tools=first_b.tools))
            result_b = loop.run_until_complete(resumed_b.run(MESSAGES, resume=True))
            assert result_a["status"] == "money_cny_usage_unavailable"
            assert result_b["status"] == "token_reservation_exceeded"
            assert resumed_b.budget.fatal_reason == "money_cny_usage_unavailable"
            assert resumed_b.adapter.requests == []
            root.validate()
            return {
                "A_status": result_a["status"],
                "expected_current_B_resume_status": "token_reservation_exceeded",
                "actual_B_resume_status": result_b["status"],
                "root_fatal": resumed_b.budget.fatal_reason,
                "B_scripted_adapter_calls": 0,
                "journal_valid": True,
            }


def read_historical_ledger():
    run = ROOT / ("AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/"
                  "manual_dispatch_sm25_lite_v1")
    metadata = json.loads((run / "journal.json").read_bytes())
    events = EventStore.read_events(run / "events.jsonl")
    budget = RuntimeBudget.from_events(
        BudgetAmounts.model_validate_json(json.dumps(metadata["budget_limit"])), events)
    reservation = next(r for r in budget.ledger.reservations
                       if r.reservation_id == "plan_f1:request-21")
    settlement = next(s for s in budget.ledger.settlements
                      if s.reservation_id == reservation.reservation_id)
    return {
        "path": str(run.relative_to(ROOT)),
        "access": "read_only_static_event_reader_no_EventStore_constructor",
        "fatal": budget.fatal_reason,
        "limit_cny": str(budget.total_limit.money_cny),
        "committed_cny": str(budget.ledger.committed.money_cny),
        "available_cny": str(budget.available.money_cny),
        "event_count": len(events),
        "unknown_reservation": reservation.model_dump(mode="json"),
        "unknown_settlement": settlement.model_dump(mode="json"),
        "note": "Committed amount includes the unknown reservation hold; it is not an actual provider bill.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="Explicit path for a new JSON result; stdout always receives the full JSON.")
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        raise SystemExit("Run this script from the repository root.")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    comparison = subprocess.run(
        ["git", "diff", "--quiet", EXPECTED_HEAD, "--", *BASELINE_PATHS],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    if comparison.returncode == 1:
        raise SystemExit("Production code or test fixtures differ from the baseline; refusing reproduction.")
    if comparison.returncode != 0:
        raise SystemExit(f"Cannot verify baseline: {comparison.stderr.strip()}")
    output = args.output.resolve() if args.output is not None else None

    # Windows asyncio creates its private wake-up socketpair via loopback.
    # Bootstrap that loop once before forbidding every new connection, then
    # reuse it. No service, HTTP, MCP, DNS or work-model call is made here.
    loop = asyncio.new_event_loop()
    blocked_attempts = []

    def forbidden_network(*args, **kwargs):
        blocked_attempts.append("connection_attempt_blocked")
        raise AssertionError("network forbidden in offline runtime review")

    socket.create_connection = forbidden_network
    socket.socket.connect = forbidden_network
    socket.socket.connect_ex = forbidden_network
    socket.getaddrinfo = forbidden_network

    started = time.perf_counter()
    results = []

    def record(name, kind, function):
        began = time.perf_counter()
        try:
            detail = function()
            result = {"name": name, "kind": kind, "expected_behavior_reproduced": True, **detail}
        except Exception as error:
            result = {"name": name, "kind": kind, "expected_behavior_reproduced": False,
                      "error_type": type(error).__name__, "error": str(error)}
        result["elapsed_seconds"] = time.perf_counter() - began
        results.append(result)

    try:
        for boundary, tool, expected, kind in [
            ("after_reservation", "view", "resume_uncheckpointed_budget_reservation", "gap"),
            ("after_tool", "view", "resume_pending_operation", "gap"),
            ("after_response", "save", "completed", "positive_control"),
            ("after_execution", "save", "completed", "positive_control"),
        ]:
            record(boundary, kind, lambda b=boundary, t=tool, e=expected: crash_case(loop, b, t, e))
        record("cancel_read_only", "gap", lambda: cancellation_case(loop))
        record("sibling_missing_cny", "gap", lambda: sibling_case(loop))
        historical = read_historical_ledger()
    finally:
        loop.close()

    report = {
        "schema": "runtime_independent_recovery_review.v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "baseline_head": EXPECTED_HEAD,
        "actual_head": head,
        "baseline_guard": {"paths": list(BASELINE_PATHS), "tracked_diff_empty": True},
        "runtime_version": "runtime-v2-20261009",
        "domain_version": "domain-v57-20261010",
        "python": sys.version,
        "scope": "six isolated offline microcases plus read-only historical ledger reconstruction",
        "network": {
            "live_model_calls": 0, "http_calls": 0, "mcp_calls": 0,
            "new_connections_and_dns_forbidden_during_scenarios": True,
            "blocked_attempts": len(blocked_attempts),
            "windows_asyncio_bootstrap": "private wake-up socketpair initialized before guard; no service endpoint",
        },
        "filesystem": {
            "temporary_writes_and_cleanup": "only new TemporaryDirectory trees created by this script",
            "durable_output": str(output) if output is not None else None,
            "production_or_historical_evidence_modified": False,
        },
        "results": results,
        "historical_ledger": historical,
        "summary": {
            "cases": len(results),
            "expected_behavior_reproduced": sum(r["expected_behavior_reproduced"] for r in results),
            "failed_to_reproduce": sum(not r["expected_behavior_reproduced"] for r in results),
            "elapsed_seconds": time.perf_counter() - started,
            "meaning": "Reproducing an existing gap is not a quality pass or an implemented fix.",
            "not_covered": ["live providers", "MCP services", "real BIM recovery", "whole-case quality", "full test suite"],
        },
    }
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if output is not None:
        output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if all(r["expected_behavior_reproduced"] for r in results) and not blocked_attempts else 1


if __name__ == "__main__":
    raise SystemExit(main())
