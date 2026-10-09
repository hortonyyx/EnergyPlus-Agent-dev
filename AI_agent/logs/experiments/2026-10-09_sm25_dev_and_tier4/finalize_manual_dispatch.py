"""Close a manual role-division run after every reader process has stopped.

This script makes no model or network request and never reads evaluation/GT.
It acquires the run's existing nonblocking EventStore writer lock, refuses an
active reader, performs the normal saved-candidate handoff, and records a root
terminal receipt.  ``completed`` means only that the generation workflow ended;
source fidelity and evaluator quality remain explicitly unevaluated.

Successful generation stop:
  python finalize_manual_dispatch.py finalize --config tier4_retry1.json --status completed

Failed generation stop (a delivery is optional):
  python finalize_manual_dispatch.py finalize --config tier4_retry1.json --status failed --reason "operator stop reason"

Offline checks only:
  python finalize_manual_dispatch.py self-test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from src.agent.runtime_behaviour import write_behaviour_report  # noqa: E402
from src.agent.runtime_delivery import finalize_building  # noqa: E402
from src.agent.runtime_roles.accounting import role_accounting  # noqa: E402
from src.agent.runtime_roles.artifacts import ArtifactRegistry  # noqa: E402
from src.agent_runtime.loop import RunLimits  # noqa: E402
from src.agent_runtime.store import EventStore  # noqa: E402
from src.harness_contracts import (  # noqa: E402
    RunAggregateUsagePayload,
    RunLifecyclePayload,
    UsageMissing,
    UsageReported,
)

FINALIZER_ID = "manual_dispatch_terminal_v1"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def limits_from(config: dict) -> RunLimits:
    raw = config["limits"]
    return RunLimits(
        model_calls=raw["model_calls"],
        tool_calls=raw["tool_calls"],
        tokens=raw.get("tokens"),
        money_cny=Decimal(str(raw["money_cny"])),
        seconds=raw["seconds"],
        max_model_retries=raw.get("model_retries", 2),
        retry_backoff_seconds=raw.get("retry_backoff_seconds", 2.0),
    )


def resolve_inside_root(value: str) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"path escapes repository root: {value}")
    return path


def load_context(config_path: Path) -> tuple[dict, Path, Path, dict, dict, RunLimits]:
    config = read_json(config_path)
    if config.get("schema_version") != 1 or config.get("mode") != "manual_coordinator_role_division":
        raise ValueError("unsupported manual-dispatch configuration")
    constraints = config.get("execution_constraints") or {}
    if constraints.get("coordinator_model_requests_allowed") != 0:
        raise ValueError("manual coordinator configuration must allow zero coordinator model requests")
    if constraints.get("automatic_provider_fallback") is not False:
        raise ValueError("automatic provider fallback must remain disabled")
    if constraints.get("deepseek_allowed") is not False:
        raise ValueError("DeepSeek must remain disabled")
    limits = limits_from(config)
    if limits.money_cny is None or limits.money_cny > Decimal("20"):
        raise ValueError("manual dispatch must retain a CNY cap no greater than 20")
    output = resolve_inside_root(config["output"])
    manifest_path = output / "manual_dispatch_manifest.json"
    inputs_path = output / "bim" / "inputs.json"
    journal_path = output / "journal.json"
    events_path = output / "events.jsonl"
    for required in (manifest_path, inputs_path, journal_path, events_path):
        if not required.is_file():
            raise ValueError(f"initialized run file is missing: {required}")
    manifest = read_json(manifest_path)
    if manifest.get("configuration_sha256") != digest(config_path):
        raise ValueError("configuration changed after initialization")
    if manifest.get("batch_id") != config.get("batch_id"):
        raise ValueError("configuration and initialized batch identity differ")
    inputs = read_json(inputs_path)
    started = inputs.get("started_epoch")
    if not isinstance(started, (int, float)):
        raise ValueError("initialized run has no durable start time")
    return config, output, output / "bim", manifest, inputs, limits


def reader_activity(store: EventStore, registry: ArtifactRegistry) -> list[dict]:
    """Return readers whose durable state does not prove they stopped."""

    active = []
    reader_ids = set(registry.records)
    reader_ids.update(event.task_id for event in store.all_events if event.task_id != store.task_id)
    for task_id in sorted(reader_ids):
        record = registry.records.get(task_id)
        lifecycle = [event.payload for event in store.all_events
                     if event.task_id == task_id and event.payload.event_type == "run_lifecycle"]
        last = lifecycle[-1].action if lifecycle else None
        record_status = None if record is None else record.get("status")
        if record_status in {"running", "interrupted"} or last != "stop":
            active.append({"task_id": task_id, "record_status": record_status,
                           "last_lifecycle_action": last})
    return active


def root_terminal(store: EventStore):
    return [event for event in store.events
            if event.payload.event_type == "run_lifecycle" and event.payload.action == "stop"]


def aggregate_usage(accounting: dict):
    requests = accounting.get("requests")
    total = accounting.get("provider_reported_tokens")
    if requests and accounting.get("usage_complete") is True and isinstance(total, int):
        return UsageReported(raw_usage={"total_tokens": total})
    reason = ("no model requests were made" if requests == 0
              else "one or more requests have no complete provider usage receipt")
    return UsageMissing(reason=reason)


def build_receipt(*, status: str, reason: str, manifest: dict, inputs: dict,
                  limits: RunLimits, accounting: dict, finalization: dict,
                  elapsed_seconds: float) -> dict:
    return {
        "status": status,
        "stop_reason": reason,
        "finalizer": FINALIZER_ID,
        "finalized_utc": datetime.now(UTC).isoformat(),
        "started_epoch": inputs["started_epoch"],
        "deadline_epoch": inputs["started_epoch"] + limits.seconds,
        "elapsed_seconds": elapsed_seconds,
        "agent_version": manifest.get("agent"),
        "finalization": finalization,
        "role_accounting": accounting,
        "usage_accounting": accounting,
        "estimated_cost_cny": accounting.get("estimated_cost_cny"),
        "provider_reported_tokens": accounting.get("provider_reported_tokens"),
        "usage_complete": accounting.get("usage_complete"),
        "budget": accounting.get("ledger"),
        "limits": limits.model_dump(mode="json"),
        "coordinator_model_requests": 0,
        "external_model_completion": "not_applicable_manual_coordinator",
        "automatic_fallback": False,
        "generation_completion_semantics": (
            "completed means the manual generation workflow ended; it is not a source-fidelity or quality verdict"
        ),
        "source_fidelity": "not_evaluated",
        "evaluation_status": "not_run",
    }


def build_summary(*, status: str, reason: str, inputs: dict, receipt: dict) -> dict:
    finalization = receipt["finalization"]
    delivery = finalization.get("delivery")
    if delivery:
        delivery = {**delivery, "report": "delivery.json", "viewer": "delivery.html"}
    return {
        "input_mode": inputs.get("input_mode"),
        "source_input_mode": inputs.get("source_input_mode"),
        "input_contents": inputs.get("input_contents"),
        "agent_response_completed": status == "completed",
        "runtime_status": status,
        "stop_reason": reason,
        "elapsed_seconds": receipt["elapsed_seconds"],
        "delivery_status": finalization.get("status"),
        "delivery": delivery,
        "receipt": "../receipt.json",
        "drawing_fidelity": "not_evaluated",
        "source_fidelity": "not_evaluated",
        "evaluation_status": "not_run",
        "quality_passed": None,
        "completion_note": (
            "Generation completion and delivery availability are recorded separately; "
            "the common evaluator has not run."
        ),
        "runtime_mode": "manual_coordinator_role_division",
    }


def finalize_run(config_path: Path, *, status: str, reason: str,
                 finalize_fn=finalize_building,
                 behaviour_fn=write_behaviour_report) -> dict:
    _, output, run, manifest, inputs, limits = load_context(config_path)
    if status not in {"completed", "failed"}:
        raise ValueError("status must be completed or failed")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("a nonempty stop reason is required")
    reason = reason.strip()
    if status == "completed" and reason != "completed":
        raise ValueError("completed generation uses the canonical stop reason 'completed'")
    if status == "failed" and reason == "completed":
        raise ValueError("failed generation needs its actual failure/stop reason")

    # EventStore acquires the existing OS-backed writer.lock nonblockingly before
    # journal or receipt writes. A live dispatcher therefore fails here without
    # modifying the run.
    with EventStore(output, run_id=output.name, task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        registry = ArtifactRegistry(store)
        active = reader_activity(store, registry)
        if active:
            raise ValueError("reader tasks are not durably stopped: " + json.dumps(active, ensure_ascii=False))

        terminals = root_terminal(store)
        receipt_path = output / "receipt.json"
        existing = read_json(receipt_path) if receipt_path.is_file() else None
        if existing is not None:
            if existing.get("finalizer") != FINALIZER_ID:
                raise ValueError("an unrelated root receipt already exists")
            if (existing.get("status"), existing.get("stop_reason")) != (status, reason):
                raise ValueError("run was already finalized with a different status or reason")
            receipt = existing
        else:
            if terminals:
                raise ValueError("root stop event exists without this finalizer's receipt")
            accounting = role_accounting(store, registry)
            coordinator_requests = accounting.get("by_role", {}).get("coordinator", {}).get("requests", 0)
            if coordinator_requests != 0:
                raise ValueError("manual coordinator journal unexpectedly contains model requests")
            elapsed = max(0.0, time.time() - float(inputs["started_epoch"]))
            domain_reason = "completed" if status == "completed" else reason
            finalization = finalize_fn(run, reason=domain_reason, elapsed_seconds=elapsed)
            receipt = build_receipt(status=status, reason=reason, manifest=manifest,
                                    inputs=inputs, limits=limits, accounting=accounting,
                                    finalization=finalization, elapsed_seconds=elapsed)
            # Match the external-coordinator ordering: a durable receipt exists
            # before its terminal lifecycle event refers to it.
            store.write_json("receipt.json", receipt)

        accounting = role_accounting(store, registry)
        store.write_json("role_accounting.json", accounting)
        store.write_json("accounting.json", accounting)
        state_path = output / "role_state.json"
        state = read_json(state_path) if state_path.is_file() else {}
        # Preserve the last coordinator assembly/position projections while
        # refreshing the reader and usage projections from the final journal.
        state["readers"] = registry.state()
        state["usage"] = accounting
        state["coordinator_model_requests"] = 0
        state["terminal"] = {"status": status, "stop_reason": reason}
        store.write_json("role_state.json", state)

        if not terminals:
            store.append(RunLifecyclePayload(action="stop", reason=reason),
                         source_refs=(store.source("manual-coordinator-receipt", receipt),))
        elif len(terminals) != 1 or terminals[0].payload.reason != reason:
            raise ValueError("existing root terminal lifecycle differs from requested stop")

        root_usage = [event for event in store.events
                      if event.payload.event_type == "run_usage_summary"]
        if not root_usage:
            store.append(RunAggregateUsagePayload(
                usage=aggregate_usage(accounting),
                raw_summary=store.capture(receipt),
                notes=("Manual coordinator made zero model requests; reader usage is projected from the shared root journal. Unknown usage remains unknown.",),
            ))
        elif len(root_usage) != 1:
            raise ValueError("root run has multiple aggregate usage summaries")

        summary = build_summary(status=status, reason=reason, inputs=inputs, receipt=receipt)
        store.write_json("bim/summary.json", summary)
        store.validate()
        behaviour_fn(output / "events.jsonl", output / "behaviour", source_root=ROOT)

    return {"status": status, "stop_reason": reason,
            "delivery_status": receipt["finalization"].get("status"),
            "delivery": receipt["finalization"].get("delivery"),
            "usage_complete": receipt.get("usage_complete"),
            "estimated_cost_cny": receipt.get("estimated_cost_cny"),
            "evaluation_status": "not_run"}


def tree_bytes(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file() and path.name != "writer.lock"}


def self_test() -> None:
    """Pure local contract/locking test: no credentials, network, model or GT."""

    with tempfile.TemporaryDirectory(prefix="manual-finalize-", dir=HERE) as raw:
        base = Path(raw)
        output = base / "run"
        run = output / "bim"
        run.mkdir(parents=True)
        config_path = base / "config.json"
        config = {
            "schema_version": 1,
            "batch_id": "mock-manual-finalizer",
            "status": "prepared_not_started",
            "mode": "manual_coordinator_role_division",
            "output": str(output),
            "limits": {"model_calls": 3, "tool_calls": 4, "tokens": None,
                       "money_cny": "1", "seconds": 60},
            "execution_constraints": {"coordinator_model_requests_allowed": 0,
                                      "automatic_provider_fallback": False,
                                      "deepseek_allowed": False},
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")
        started = time.time() - 1
        (run / "inputs.json").write_text(json.dumps({
            "started_epoch": started,
            "input_mode": "mock_original_images",
            "source_input_mode": "original_images_only",
            "input_contents": {"ground_truth_or_evaluation": {"included": False}},
        }), encoding="utf-8")
        manifest = {"batch_id": config["batch_id"],
                    "configuration_sha256": digest(config_path),
                    "agent": {"version_id": "mock", "source_commit": "mock"}}
        (output / "manual_dispatch_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        limits = limits_from(config)

        with EventStore(output, run_id=output.name, task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as held:
            held.append(RunLifecyclePayload(action="start", reason="mock coordinator initialized"))
            held.write_json("role_state.json", {"assembly_review": {"status": "mock_saved"}})
            before = tree_bytes(output)
            try:
                finalize_run(config_path, status="failed", reason="mock_failure",
                             finalize_fn=lambda *a, **k: None,
                             behaviour_fn=lambda *a, **k: None)
            except BlockingIOError:
                pass
            else:
                raise AssertionError("finalizer did not reject an occupied writer lock")
            assert tree_bytes(output) == before

            child = held.for_task("mock_reader", parent_task_id="coordinator")
            child.append(RunLifecyclePayload(action="start", reason="mock reader started"))

        before = tree_bytes(output)
        try:
            finalize_run(config_path, status="failed", reason="mock_failure",
                         finalize_fn=lambda *a, **k: None,
                         behaviour_fn=lambda *a, **k: None)
        except ValueError as error:
            assert "not durably stopped" in str(error)
        else:
            raise AssertionError("finalizer did not reject an active reader")
        assert tree_bytes(output) == before

        with EventStore(output, run_id=output.name, task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            child = store.for_task("mock_reader", parent_task_id="coordinator")
            child.append(RunLifecyclePayload(action="stop", reason="mock reader completed"))

        calls = {"finalize": 0, "behaviour": 0}

        def mock_finalize(run_directory, *, reason, elapsed_seconds):
            calls["finalize"] += 1
            assert run_directory == run and reason == "mock_failure" and elapsed_seconds >= 0
            return {"status": "no_saved_candidate", "delivery": None}

        def mock_behaviour(path, out, *, source_root=None):
            calls["behaviour"] += 1
            assert path == output / "events.jsonl" and source_root == ROOT
            out.mkdir(parents=True, exist_ok=True)
            (out / "mock.json").write_text("{}", encoding="utf-8")

        result = finalize_run(config_path, status="failed", reason="mock_failure",
                              finalize_fn=mock_finalize, behaviour_fn=mock_behaviour)
        receipt = read_json(output / "receipt.json")
        summary = read_json(run / "summary.json")
        state = read_json(output / "role_state.json")
        with EventStore(output, run_id=output.name, task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            root_stops = root_terminal(store)
            aggregate = [event for event in store.events
                         if event.payload.event_type == "run_usage_summary"]
            assert len(root_stops) == len(aggregate) == 1
            assert aggregate[0].payload.usage.kind == "missing"
        assert calls == {"finalize": 1, "behaviour": 1}
        assert result["delivery"] is None and result["evaluation_status"] == "not_run"
        assert receipt["status"] == "failed" and receipt["estimated_cost_cny"] is None
        assert summary["agent_response_completed"] is False
        assert summary["delivery"] is None and summary["quality_passed"] is None
        assert summary["source_fidelity"] == "not_evaluated"
        assert state["assembly_review"] == {"status": "mock_saved"}
        assert state["terminal"] == {"status": "failed", "stop_reason": "mock_failure"}

        def should_not_refinalize(*args, **kwargs):
            raise AssertionError("an idempotent terminal replay must reuse the durable receipt")

        replay = finalize_run(config_path, status="failed", reason="mock_failure",
                              finalize_fn=should_not_refinalize, behaviour_fn=mock_behaviour)
        assert replay["delivery"] is None
        with EventStore(output, run_id=output.name, task_id="coordinator",
                        budget_limit=limits.ledger_limit()) as store:
            assert len(root_terminal(store)) == 1
            assert sum(event.payload.event_type == "run_usage_summary"
                       for event in store.events) == 1

        # Receipt construction must preserve unknown usage as null, never zero.
        unknown = {"requests": 1, "provider_reported_tokens": None,
                   "estimated_cost_cny": None, "usage_complete": False, "ledger": {}}
        probe = build_receipt(status="failed", reason="unknown_usage", manifest=manifest,
                              inputs={"started_epoch": started}, limits=limits,
                              accounting=unknown,
                              finalization={"status": "no_saved_candidate", "delivery": None},
                              elapsed_seconds=1.0)
        assert probe["provider_reported_tokens"] is None
        assert probe["estimated_cost_cny"] is None and probe["usage_complete"] is False

    print(json.dumps({
        "status": "passed",
        "writer_lock_rejected_before_write": True,
        "active_reader_rejected_before_write": True,
        "root_stop_events": 1,
        "idempotent_replay": True,
        "unknown_usage_preserved": True,
        "no_delivery_failure_terminal": True,
        "source_fidelity": "not_evaluated",
        "evaluation_status": "not_run",
        "credentials_read": False,
        "network_requests": 0,
        "model_requests": 0,
        "ground_truth_reads": 0,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-test")
    finalize = sub.add_parser("finalize")
    finalize.add_argument("--config", type=Path, required=True)
    finalize.add_argument("--status", choices=("completed", "failed"), required=True)
    finalize.add_argument("--reason")
    args = parser.parse_args()
    if args.command == "self-test":
        self_test()
        return
    reason = args.reason or ("completed" if args.status == "completed" else None)
    if reason is None:
        parser.error("--reason is required when --status failed")
    result = finalize_run(args.config.resolve(), status=args.status, reason=reason)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
