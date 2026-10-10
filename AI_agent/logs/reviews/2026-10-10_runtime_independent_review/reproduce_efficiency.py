r"""Read-only runtime efficiency evidence; print JSON, never write old evidence.

Run from the repository root with:
  .\.venv\Scripts\python.exe -B AI_agent/logs/reviews/2026-10-10_runtime_independent_review/reproduce_efficiency.py

No EventStore writer, HTTP adapter, work model, MCP, credentials, or network is
opened. The optional microbenchmark validates already loaded event prefixes in
memory. It is not a replay of tools or a measurement of the original run's CPU.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from src.agent_runtime.adapter import reasoning_history_messages
from src.agent_runtime.estimation import _text_payload, approximate_text_tokens
from src.agent_runtime.json_tree import read_json_tree
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, EventEnvelope, HashedBlobRef


RUN = Path(
    "AI_agent/archive/local_backup/2026-10-10_sm25_lite_regularization/"
    "manual_dispatch_sm25_lite_v1"
)
FINAL_READER_RECEIPT = RUN / (
    "tasks/c1c3b11072b0cc1a10539ba75831d98e96c9275f8d8498eeb15cff1977aa386d/receipt.json"
)


def file_reference(path: Path) -> dict:
    raw = (REPO / path).read_bytes()
    return {"path": path.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def reasoning_selection_counterexample() -> dict:
    messages = [
        {"role": "system", "content": "guide"},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": None, "reasoning_content": "analysis " * 12000,
         "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "done"},
        {"role": "user", "content": "Current runtime state (machine generated; epistemic status is authoritative): unresolved"},
    ]
    sources = [SimpleNamespace(source_kind=kind) for kind in ["runtime", "user", "runtime", "tool", "generated"]]
    result = {}
    for label, selected_sources in [("projection_without_sources", None), ("wire_selection_with_sources", sources)]:
        selected = reasoning_history_messages(messages, "current_tool_chain", selected_sources)
        result[label] = {
            "reasoning_fields": sum("reasoning_content" in message for message in selected),
            "approximate_text_tokens": approximate_text_tokens(_text_payload({"messages": selected})[0]),
        }
    result.update({
        "source_locations": ["src/agent_runtime/loop.py:377", "src/agent_runtime/adapter.py:88", "src/agent_runtime/adapter.py:120"],
        "scope": "Only explicit current_tool_chain selection. Both 10-10 plan readers use all and are unaffected.",
        "hard_limit_boundary": (
            "loop.py:392-408 prepares and estimates the actual selected wire request, then applies the context gate. "
            "loop.py:437-466 reserves against task and root budgets using that prepared estimate. "
            "The demonstrated defect is missed/late compaction and potentially avoidable early stopping, "
            "not demonstrated bypass of context or budget hard limits. This small counterexample does not run a full Runtime."
        ),
    })
    return result


def collect(repeats: int) -> dict:
    root = (REPO / RUN).resolve()
    raw_lines = (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in raw_lines]
    blob_cache: dict[str, bytes] = {}

    def read_blob(ref: HashedBlobRef) -> bytes:
        path = (root / ref.uri).resolve()
        if not path.is_relative_to(root):
            raise ValueError("blob reference escaped the frozen run")
        if ref.sha256 not in blob_cache:
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != ref.sha256:
                raise ValueError("blob hash mismatch")
            blob_cache[ref.sha256] = data
        return blob_cache[ref.sha256]

    def source(event: dict, name: str) -> dict:
        ref = next((item.get("blob") for item in event.get("source_refs", []) if item["source_id"] == name), None)
        return json.loads(read_blob(HashedBlobRef.model_validate(ref))) if ref else {}

    def request_template(event: dict) -> dict:
        capture = event["payload"]["final_request_body"]
        if capture["kind"] == "inline":
            return capture["value"]
        ref = HashedBlobRef.model_validate(capture["blob"])
        body = read_json_tree(ref, read_blob) if capture["kind"] in {"image_references", "json_references"} else json.loads(read_blob(ref))
        # Compare exact text/arguments and image identity without materializing or
        # printing base64. Hashes of all referenced image bytes are verified.
        for item in capture.get("images", []):
            image = HashedBlobRef.model_validate(item["image"])
            read_blob(image)
            keys = [key.replace("~1", "/").replace("~0", "~") for key in item["location"].split("/")[1:]]
            parent = body
            for key in keys[:-1]:
                parent = parent[int(key)] if isinstance(parent, list) else parent[key]
            key = int(keys[-1]) if isinstance(parent, list) else keys[-1]
            parent[key] = "verified-image-sha256:" + image.sha256
        return body

    responses = {event["payload"]["request_event_id"]: event for event in events if event["payload"]["event_type"] == "model_response"}
    failures = {
        event["payload"]["model_failure"]["request_event_id"]: event
        for event in events
        if event["payload"]["event_type"] == "run_lifecycle" and event["payload"].get("model_failure")
    }
    compactions = [event for event in events if event["payload"]["event_type"] == "context" and event["payload"]["action"] == "compact"]
    previous: dict[str, tuple[dict, list]] = {}
    trace = []
    for event in events:
        payload = event["payload"]
        if payload["event_type"] != "adapter_request":
            continue
        task = event["task_id"]
        messages = request_template(event)["messages"]
        old_event, old_messages = previous.get(task, ({"sequence": -1}, []))
        common = 0
        for old, new in zip(old_messages, messages):
            if old != new:
                break
            common += 1
        response = responses.get(event["event_id"])
        terminal = response or failures.get(event["event_id"], {})
        usage = (response or {}).get("payload", {}).get("usage", {}).get("raw_usage", {})
        details = usage.get("prompt_tokens_details", {})
        trace.append({
            "task_id": task,
            "ordinal": int(payload["reservation_id"].rsplit("-", 1)[-1]),
            "event_id": event["event_id"], "event_line": event["sequence"] + 1,
            "occurred_at": event["occurred_at"]["value"],
            "response_event_id": response["event_id"] if response else None,
            "failure_event_id": terminal.get("event_id") if not response else None,
            "request_round_trip_and_response_processing_seconds": source(terminal, "request-duration").get("elapsed_seconds"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "cached_prompt_tokens": details.get("cached_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "reported_reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens"),
            "reported_image_tokens": details.get("image_tokens"),
            "messages": len(messages), "previous_messages": len(old_messages),
            "unchanged_message_prefix": common,
            "image_slots": len(payload["images"]),
            "unique_image_hashes": len({item["sent"]["sha256"] for item in payload["images"]}),
            "compaction_events_since_previous_request": [
                item["event_id"] for item in compactions
                if item["task_id"] == task and old_event["sequence"] < item["sequence"] < event["sequence"]
            ],
        })
        previous[task] = event, messages

    receipt = json.loads((REPO / FINAL_READER_RECEIPT).read_bytes())
    by_task = receipt["timing"]["by_task"]
    summaries = {}
    for task in sorted(previous):
        rows = [row for row in trace if row["task_id"] == task]
        known = [row for row in rows if row["prompt_tokens"] is not None]
        prompt = sum(row["prompt_tokens"] for row in known)
        cached = sum(row["cached_prompt_tokens"] or 0 for row in known)
        summaries[task] = {
            "requests": len(rows), "responses_with_prompt_usage": len(known),
            "known_prompt_tokens": prompt, "known_cached_prompt_tokens": cached,
            "known_cache_over_prompt": cached / prompt if prompt else None,
            "known_output_tokens": sum(row["output_tokens"] or 0 for row in known),
            "known_reported_reasoning_tokens": sum(row["reported_reasoning_tokens"] or 0 for row in known),
            "timing_from_original_receipt": by_task[task],
        }

    benchmark = []
    if repeats:
        typed_events = [EventEnvelope.model_validate_json(line) for line in raw_lines]
        meta = json.loads((root / "journal.json").read_bytes())
        # Deliberately bypass __init__: no mkdir, writer lock, EventStore append,
        # journal repair, checkpoint, or filesystem mutation is possible here.
        store = object.__new__(EventStore)
        store.root_task_id = meta["task_id"]
        store.budget_limit = BudgetAmounts.model_validate_json(json.dumps(meta["budget_limit"]))
        for count in [100, 300, 600, 900, len(events)]:
            samples = []
            for _ in range(repeats):
                started = time.perf_counter()
                store._validate_events(typed_events[:count])
                samples.append((time.perf_counter() - started) * 1000)
            benchmark.append({"events": count, "samples_ms": samples, "median_ms": statistics.median(samples)})

    configs = {}
    for event in events:
        if event["payload"]["event_type"] == "run_lifecycle" and event["payload"].get("action") == "start" and event["task_id"] in {"plan_f1", "plan_f2"}:
            config = source(event, "runtime-config")
            configs[event["task_id"]] = {
                "source_event_id": event["event_id"], "source_line": event["sequence"] + 1,
                "context_policy": config["context_policy"],
                "reasoning_history": config["reasoning_history"],
                "summary_every": config["limits"]["summary_every"],
            }

    prompt = sum(row["prompt_tokens"] or 0 for row in trace)
    cache = sum(row["cached_prompt_tokens"] or 0 for row in trace)
    return {
        "schema_version": "runtime_efficiency_independent_review_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "review_baseline_head": "6e88fd73",
        "head_binding": "No HEAD equality requirement. Current source hashes are recorded so documentation-only commits do not block reproduction; compare code hashes before interpreting timings after implementation changes.",
        "runtime_version": "runtime-v2-20261009", "domain_version": "domain-v57-20261010",
        "execution_scope": {"offline_only": True, "work_model_calls": 0, "network_calls": 0, "old_evidence_writes": 0, "full_profile_rerun": False},
        "sources": {
            "events": file_reference(RUN / "events.jsonl"),
            "journal": file_reference(RUN / "journal.json"),
            "final_reader_receipt": file_reference(FINAL_READER_RECEIPT),
            "final_accounting": file_reference(Path("AI_agent/logs/experiments/2026-10-10_sm25_lite_regularization/final_accounting.json")),
            "comparison_20261009": file_reference(Path("AI_agent/logs/experiments/2026-10-09_sm25_dev_and_tier4/README.md")),
            "comparison_20261003": file_reference(Path("AI_agent/logs/experiments/2026-10-03_migration_comparison/README.md")),
            "code": [file_reference(Path(path)) for path in ["src/agent_runtime/store.py", "src/harness_contracts/validation.py", "src/harness_contracts/budget.py", "src/agent_runtime/loop.py", "src/agent_runtime/adapter.py", "src/agent_runtime/context.py", "src/agent_runtime/timing.py"]],
        },
        "source_event_count": len(events),
        "aggregate_known_usage": {
            "requests": len(trace), "responses": len(responses), "failed_requests": len(failures),
            "prompt_tokens": prompt, "cached_prompt_tokens": cache, "cache_over_prompt": cache / prompt,
            "output_tokens": sum(row["output_tokens"] or 0 for row in trace),
            "reported_reasoning_tokens": sum(row["reported_reasoning_tokens"] or 0 for row in trace),
            "usage_complete": len(trace) == sum(row["prompt_tokens"] is not None for row in trace),
        },
        "by_task": summaries,
        "plan_context_configuration": configs,
        "request_trace": trace,
        "prefix_validation_microbenchmark": {
            "method": "Current _validate_events on preloaded frozen prefixes; three repetitions by default; no I/O inside the timed region.",
            "python": platform.python_version(), "platform": platform.platform(), "repetitions": repeats,
            "source_locations": ["src/agent_runtime/store.py:322", "src/agent_runtime/store.py:334", "src/harness_contracts/validation.py:473", "src/harness_contracts/validation.py:496", "src/harness_contracts/budget.py:286"],
            "measurements": benchmark,
            "original_review_medians_ms": [{"events": n, "median_ms": ms} for n, ms in [(100, 4.440), (300, 29.109), (600, 104.907), (900, 233.302), (1269, 461.226)]],
            "original_single_profile_observation": {"total_seconds_under_profiler": 1.850, "budget_validation_seconds_under_profiler": 1.839, "budget_ledger_validation_calls": 297, "note": "Previous read-only observation, not rerun by this script; profiler overhead makes these unsuitable as unprofiled timings."},
            "boundary": "This is a current offline microbenchmark, not original-run per-function timing or promised time savings. Do not sum/interpolate it into a precise savings claim.",
        },
        "current_tool_chain_counterexample": reasoning_selection_counterexample(),
        "interpretation_boundaries": [
            "model_seconds is local request round trip plus response handling, including parse/capture; it is not pure provider generation or pure thinking time.",
            "No TTFT/server timeline exists here. Queue, network, prefill, thinking and visible generation cannot be split from these observations.",
            "other_seconds includes unclassified local work and may include other categories; do not attribute it all to EventStore validation.",
            "Parallel task durations cannot be summed into run wall time; synchronous local work can also delay other task callbacks.",
            "Message-prefix comparison uses exact text/arguments and verified image identities, not the provider tokenizer/cache-key algorithm.",
            "F1 requests 3 and 4 retain the entire previous message prefix yet have cache zero; neither was preceded by compaction.",
            "The three actual compactions precede F2 request 22 and F1 requests 7 and 16; each retains only the first two messages of the previous request and reports cache zero.",
            "Token-mode compaction removes old interaction groups and emits a retrieval notice; with summary_every=0 it is not a semantic summary.",
            "10-09 cache 75.81% accompanied assisted delivery; 10-10 cache 81.04% accompanied no BIM. This cannot establish faster completion or superiority over Claude Code.",
            "10-03 Claude Code baseline 1442s and successful Paratera runtime run 2513s differ in route/protocol/parameters; migration success is not speed superiority.",
            "Runtime-only changes cannot currently promise a reduction from about 60 to 30 minutes; domain behavior and provider response/output remain substantial and uncontrolled.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-repeats", type=int, default=3, choices=range(0, 6), help="0 reads evidence and runs only the tiny in-memory reasoning-selection example")
    parser.add_argument("--output", type=Path, help="Explicitly save to a NEW file; existing files and archived evidence destinations are refused")
    args = parser.parse_args()
    target = args.output.resolve() if args.output else None
    if target and (target.exists() or target.is_relative_to((REPO / "AI_agent/archive").resolve())):
        parser.error("output must be a new file outside archived evidence")
    result = collect(args.benchmark_repeats)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if target:
        # Exclusive creation also protects the frozen review evidence from an
        # accidental rerun, including a race after the exists check above.
        with target.open("x", encoding="utf-8", newline="\n") as output:
            output.write(rendered + "\n")
        print(json.dumps({"output": str(target), "events": result["source_event_count"],
            "requests": result["aggregate_known_usage"]["requests"],
            "benchmark_retest": result["prefix_validation_microbenchmark"]["measurements"]}, indent=2))
    else:
        print(rendered)


if __name__ == "__main__":
    main()
