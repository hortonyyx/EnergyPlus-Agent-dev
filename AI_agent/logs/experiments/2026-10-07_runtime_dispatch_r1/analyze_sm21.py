"""Project the completed sm21 journal without opening it for writing."""

import argparse
import hashlib
import json
from pathlib import Path

from src.agent_runtime.store import EventStore
from src.agent_runtime.timing import project_saved_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    source = args.directory.resolve()
    watched = [source / name for name in ("events.jsonl", "receipt.json", "journal.json")]
    hashes = lambda: {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    before = hashes()
    result = project_saved_run(source)
    receipt = json.loads((source / "receipt.json").read_bytes())
    old_usage = receipt["root_usage_accounting"]
    result["original_receipt"] = {"status": receipt["status"],
        **{name: old_usage[name] for name in
           ("requests", "provider_reported_tokens", "budget_charge_tokens", "usage_complete")}}
    result["refusals"] = [{"task_id": e.task_id,
        "seconds_after_root_start": round(e.occurred_at.value.timestamp() - receipt["started_epoch"], 3),
        "request_event_id": e.payload.model_failure.request_event_id,
        "http_status": e.payload.model_failure.http_status,
        "service_error_type": e.payload.model_failure.service_error_type}
        for e in EventStore.read_events(source / "events.jsonl")
        if e.payload.event_type == "run_lifecycle" and e.payload.model_failure
        and e.payload.model_failure.category == "temporary_rate_limit"]
    result["source_hashes"] = before
    result["source_unchanged"] = hashes() == before
    assert result["source_unchanged"]
    target = Path(__file__).with_name("sm21_timing_usage.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps({"original": result["original_receipt"],
        "projected": {key: result["usage_accounting"][key] for key in
            ("requests", "provider_reported_tokens", "budget_charge_tokens", "usage_complete",
             "rejected_unprocessed_requests")}, "source_unchanged": result["source_unchanged"]}, indent=2))


if __name__ == "__main__":
    main()
