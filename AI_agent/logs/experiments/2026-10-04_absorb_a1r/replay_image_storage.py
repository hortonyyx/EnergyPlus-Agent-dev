"""Offline exact reconstruction and conservative live-file size estimate.

Input: extracted evidence/node-regression-2026-10-04 sm24 runtime directory.
Output blobs go only to --scratch; original evidence is never modified.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter

from src.agent_runtime.store import EventStore, json_bytes
from src.agent_runtime.adapter import decode_image_url
from src.harness_contracts import BudgetAmounts
from src.harness_contracts import HashedBlobRef
from src.harness_contracts.events import CapturedValue, _resolve_json_pointer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    old = object.__new__(EventStore)
    old.directory = args.run.resolve()
    files = {str(f.relative_to(old.directory)): f.read_bytes()
             for f in old.directory.rglob("*") if f.is_file()}
    rows = [json.loads(line) for line in files["events.jsonl"].splitlines()]
    changed, cache, requests = set(), {}, []
    adapter = TypeAdapter(CapturedValue)
    with EventStore(args.scratch, run_id="offline-image-replay", task_id="replay",
                    budget_limit=BudgetAmounts(tokens=1, calls=0)) as new:
        def recapture(value):
            if isinstance(value, dict):
                if value.get("kind") in {"inline", "blob"} and (
                    "value" in value or "blob" in value
                ):
                    captured = adapter.validate_json(json.dumps(value))
                    wire = old.capture_bytes(captured)
                    sha = hashlib.sha256(wire).hexdigest()
                    if sha not in cache:
                        replacement = new.capture(json.loads(wire), force_blob=captured.kind == "blob")
                        assert new.capture_bytes(replacement) == wire
                        cache[sha] = replacement
                    replacement = cache[sha]
                    if replacement.kind == "image_references":
                        if captured.kind == "blob":
                            changed.add(captured.blob.uri)
                        return replacement.model_dump(mode="json")
                    return value
                return {k: recapture(v) for k, v in value.items()}
            if isinstance(value, list):
                return [recapture(v) for v in value]
            return value

        updated = []
        for row in rows:
            result = recapture(row)
            payload = row["payload"]
            if payload["event_type"] == "adapter_request":
                wire = old.capture_bytes(adapter.validate_json(json.dumps(payload["final_request_body"])))
                captured = adapter.validate_json(json.dumps(result["payload"]["final_request_body"]))
                assert new.capture_bytes(captured) == wire
                sha = hashlib.sha256(wire).hexdigest()
                assert sha == payload["final_request_body"]["blob"]["sha256"]
                result["payload"]["wire_sha256"] = sha
                for image in payload["images"]:
                    for name in ("original", "sent"):
                        old.get_bytes(HashedBlobRef.model_validate_json(json.dumps(image[name])))
                    data, _ = decode_image_url(_resolve_json_pointer(json.loads(wire), image["request_reference"]))
                    assert hashlib.sha256(data).hexdigest() == image["sent"]["sha256"]
                requests.append({"event_id": row["event_id"], "wire_sha256": sha,
                                 "wire_bytes": len(wire), "images": len(payload["images"]),
                                 "source_images_differ_from_sent": sum(i["original"]["sha256"] != i["sent"]["sha256"] for i in payload["images"]),
                                 "reconstructed_exactly": True})
            updated.append(result)
        virtual = dict(files)
        virtual["events.jsonl"] = b"".join(json_bytes(row) + b"\n" for row in updated)
        # Same request-record output policy as runtime_behaviour: references
        # must not be expanded back into another full copy in record.json.gz.
        behaviour = json.loads(gzip.decompress(files["behaviour/record.json.gz"]))
        request_by_id = {row["event_id"]: row["payload"] for row in updated
                         if row["payload"]["event_type"] == "adapter_request"}
        for row in behaviour["requests"]:
            payload = request_by_id[row["event_id"]]
            captured = payload["final_request_body"]
            if captured["kind"] == "image_references":
                row["final_request_body"] = captured
                row["final_request_encoding"] = "captured_value"
            else:
                row["final_request_encoding"] = "expanded_json"
            row["wire_sha256"] = payload["wire_sha256"]
            row["injected_content"] = payload["injected_content"]
        behaviour["events"] = updated
        virtual["behaviour/record.json.gz"] = gzip.compress(
            json.dumps(behaviour, ensure_ascii=False, indent=1).encode(), mtime=0)
        for f in (new.directory / "blobs").iterdir():
            virtual["blobs/" + f.name] = f.read_bytes()
        # Keep any superseded capture still referenced by a checkpoint/source.
        # All other files, including old compressed behaviour reports, remain.
        references = set()
        def scan(v):
            if isinstance(v, dict):
                if v.get("kind") == "sha256" and isinstance(v.get("uri"), str):
                    references.add(v["uri"])
                for child in v.values():
                    scan(child)
            elif isinstance(v, list):
                for child in v:
                    scan(child)
        def scan_bytes(raw):
            try:
                scan(json.loads(raw))
            except (ValueError, UnicodeDecodeError):
                pass
        for name, raw in virtual.items():
            if name not in changed:
                if name == "events.jsonl":
                    for row in updated:
                        scan(row)
                else:
                    scan_bytes(raw)
        scanned = set()
        while (retained := (changed & references) - scanned):
            for name in retained:
                scan_bytes(virtual[name])
            scanned |= retained
        removed = changed - references
        before = sum(map(len, files.values()))
        after = sum(len(raw) for name, raw in virtual.items() if name not in removed)
        report = {"source_branch": "evidence/node-regression-2026-10-04",
            "source_archive": "sm24_runtime_subscription_run.tar.xz",
            "events_sha256": hashlib.sha256(files["events.jsonl"]).hexdigest(),
            "request_count": len(requests), "requests": requests,
            "before_bytes": before, "after_bytes_estimate": after,
            "saved_bytes": before - after, "saved_percent": round(100 * (before-after) / before, 2),
            "superseded_blobs_removed": len(removed), "superseded_blobs_still_referenced": len(changed & references),
            "behaviour_before_bytes": len(files["behaviour/record.json.gz"]),
            "behaviour_after_bytes_estimate": len(virtual["behaviour/record.json.gz"]),
            "basis": "logical file bytes; recapture request/injected/tool captures and corresponding behaviour request references; retain other files and still-referenced old blobs; filesystem blocks excluded",
            "model_requests": 0}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode() + b"\n")
    print(json.dumps({k: v for k, v in report.items() if k != "requests"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
