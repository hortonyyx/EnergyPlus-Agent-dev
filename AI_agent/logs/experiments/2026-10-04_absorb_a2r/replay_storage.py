"""Read a completed run; materialize and verify A2-R storage in a new directory."""

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter

from src.agent.runtime_behaviour import load_behaviour, write_behaviour_report
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts import HashedBlobRef
from src.harness_contracts.events import CapturedValue


def inventory(files):
    groups = Counter()
    for name, raw in files.items():
        groups[name.split("/")[0]] += len(raw)
    return dict(groups)


def main(run, scratch, report):
    if scratch.exists():
        raise ValueError("scratch already exists; preserve the previous replay")
    scratch.mkdir(parents=True)
    (scratch / "blobs").mkdir()
    old, new = object.__new__(EventStore), object.__new__(EventStore)
    old.directory, new.directory = run.resolve(), scratch.resolve()
    files = {str(p.relative_to(run)): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    rows = [json.loads(line) for line in files["events.jsonl"].splitlines()]
    adapter = TypeAdapter(CapturedValue)
    superseded, cache = set(), {}
    reconstructed, checkpoints, captures = [], [], Counter()

    def recapture(value):
        if isinstance(value, dict):
            if value.get("kind") in {"inline", "blob", "image_references", "json_references"} and ("value" in value or "blob" in value):
                capture = adapter.validate_json(json.dumps(value))
                wire = old.capture_bytes(capture)
                sha = hashlib.sha256(wire).hexdigest()
                key = (sha, capture.kind != "inline")
                if key not in cache:
                    replacement = new.capture(json.loads(wire), force_blob=key[1])
                    assert new.capture_bytes(replacement) == wire
                    cache[key] = replacement
                replacement = cache[key]
                captures[capture.kind + " -> " + replacement.kind] += 1
                if "blob" in value and replacement.model_dump(mode="json") != value:
                    superseded.add(value["blob"]["uri"])
                return replacement.model_dump(mode="json")
            return {key: recapture(child) for key, child in value.items()}
        if isinstance(value, list):
            return [recapture(child) for child in value]
        return value

    updated = []
    for row in rows:
        result = recapture(row)
        payload = row["payload"]
        if payload["event_type"] == "checkpoint":
            previous = HashedBlobRef.model_validate(payload["state"])
            snapshot = old.get_json_tree(previous)
            expected = json_bytes(snapshot)
            # Preserve historical checkpoint semantics exactly, including old
            # pending-picture pointers. The runtime still reads both forms.
            replacement = new.put_json_tree(snapshot)
            assert json_bytes(new.get_json_tree(replacement)) == expected
            superseded.add(previous.uri)
            result["payload"]["state"] = replacement.model_dump(mode="json")
            checkpoints.append({"event_id": row["event_id"], "before_bytes": len(old.get_bytes(previous)),
                                "root_bytes": len(new.get_bytes(replacement)), "restored_exactly": True})
        if payload["event_type"] == "adapter_request":
            before = old.capture_bytes(adapter.validate_json(json.dumps(payload["final_request_body"])))
            after = new.capture_bytes(adapter.validate_json(json.dumps(result["payload"]["final_request_body"])))
            assert before == after
            digest = hashlib.sha256(before).hexdigest()
            assert digest == payload["wire_sha256"]
            reconstructed.append({"event_id": row["event_id"], "wire_sha256": digest,
                                  "wire_bytes": len(before), "reconstructed_exactly": True})
        updated.append(result)

    virtual = dict(files)
    virtual["events.jsonl"] = b"".join(json_bytes(row) + b"\n" for row in updated)
    if checkpoints:
        last = next(row["payload"]["state"] for row in reversed(updated) if row["payload"]["event_type"] == "checkpoint")
        virtual["checkpoint.json"] = json_bytes(last)
    # The new behaviour record is just a verified reference; summary/timeline
    # are regenerated below through the public reader, then compared.
    virtual.pop("behaviour/record.json.gz", None)
    for path in (scratch / "blobs").iterdir():
        virtual["blobs/" + path.name] = path.read_bytes()
    refs = set()

    def scan(value):
        if isinstance(value, dict):
            if value.get("kind") == "sha256" and isinstance(value.get("uri"), str):
                refs.add(value["uri"])
            for item in value.values():
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)

    def scan_bytes(raw):
        try:
            scan(json.loads(raw))
        except (ValueError, UnicodeDecodeError):
            pass

    for name, raw in virtual.items():
        if name not in superseded:
            if name == "events.jsonl":
                for row in updated:
                    scan(row)
            else:
                scan_bytes(raw)
    scanned = set()
    while pending := (refs & superseded) - scanned:
        for name in pending:
            scan_bytes(virtual[name])
        scanned |= pending
    removed = superseded - refs
    for name, raw in virtual.items():
        if name in removed:
            continue
        target = scratch / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    before_behaviour = load_behaviour(run)
    after_summary = write_behaviour_report(scratch, scratch / "behaviour")
    assert before_behaviour["summary"] == after_summary
    restored_report = load_behaviour(scratch / "behaviour/record.json.gz")
    assert restored_report["summary"] == after_summary
    assert restored_report["invocations"] == before_behaviour["invocations"]
    journal = json.loads(files["journal.json"])
    from src.harness_contracts import BudgetAmounts
    with EventStore(scratch, run_id=journal["run_id"], task_id=journal["task_id"],
                    budget_limit=BudgetAmounts.model_validate(journal["budget_limit"])) as checked:
        checked.validate()
        assert checked.latest_checkpoint() is not None
        for event in checked.all_events:
            if event.payload.event_type == "adapter_request":
                wire = checked.capture_bytes(event.payload.final_request_body)
                assert hashlib.sha256(wire).hexdigest() == event.payload.wire_sha256
    after = {str(p.relative_to(scratch)): p.read_bytes() for p in scratch.rglob("*") if p.is_file()}
    before_total, after_total = sum(map(len, files.values())), sum(map(len, after.values()))
    result = {"source_run": str(run), "source_events_sha256": hashlib.sha256(files["events.jsonl"]).hexdigest(),
              "source_files": len(files), "before_bytes": before_total, "after_bytes": after_total,
              "saved_percent": round(100 * (before_total - after_total) / before_total, 2),
              "before_by_group": inventory(files), "after_by_group": inventory(after),
              "checkpoints": checkpoints, "requests": reconstructed, "capture_conversions": dict(captures),
              "superseded_blobs_removed": len(removed), "superseded_blobs_still_referenced": len(superseded & refs),
              "behaviour_summary_and_full_steps_unchanged": True,
              "basis": "Materialized offline conversion; logical bytes, not filesystem blocks; unchanged artifacts and still-referenced old blobs retained. No new whole-case run.",
              "model_requests": 0}
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("before_bytes", "after_bytes", "saved_percent", "behaviour_summary_and_full_steps_unchanged")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    main(args.run, args.scratch, args.report)
