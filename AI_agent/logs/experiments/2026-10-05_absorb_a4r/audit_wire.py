"""Confirm that canonical JSON comparison is comparison of the actual sent bytes."""

import hashlib
import json
from pathlib import Path

from replay_compaction import MemoryStore
from src.agent_runtime.store import EventStore, json_bytes

HERE = Path(__file__).resolve().parent


def main():
    rows = []
    for run in json.loads((HERE / "archive_verification.json").read_bytes())["runs"]:
        store = MemoryStore(HERE / ".tmp/history" / run["run"])
        values = []
        for event in EventStore.read_events(store.directory / "events.jsonl"):
            if event.payload.event_type != "adapter_request":
                continue
            wire = store.capture_bytes(event.payload.final_request_body)
            digest = hashlib.sha256(wire).hexdigest()
            assert digest == event.payload.wire_sha256
            assert json_bytes(json.loads(wire)) == wire
            values.append({"request_id": event.event_id, "sha256": digest, "wire_bytes": len(wire)})
        rows.append({"run": run["run"], "requests": len(values), "wire_is_canonical": True, "wire": values})
    result = {"model_requests": 0, "requests": sum(r["requests"] for r in rows),
        "all_actual_wire_bytes_equal_canonical_bytes": True, "runs": rows}
    (HERE / "wire_canonical_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["requests"])


if __name__ == "__main__":
    main()
