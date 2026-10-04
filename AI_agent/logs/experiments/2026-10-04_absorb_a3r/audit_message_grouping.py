"""Strengthen A's block audit by retaining the exact native message grouping.

Read archived Git bytes in memory; never extract or modify historical runs.
Only the final runtime-state block is excluded. Each retained native message
is canonically serialized and compared byte for byte, including its grouping.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

from pydantic import TypeAdapter
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts.events import CapturedValue

HERE = Path(__file__).resolve().parent
STATE = "Current runtime state (machine generated; epistemic status is authoritative): "


class MemoryReader(EventStore):
    def __init__(self, files):
        self.files = files

    def get_bytes(self, ref):
        raw = self.files[ref.uri]
        assert hashlib.sha256(raw).hexdigest() == ref.sha256
        return raw


def references(value):
    if isinstance(value, dict):
        if "uri" in value and "sha256" in value:
            yield value["uri"]
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def messages_without_tail(body, strip_cache=False):
    messages = copy.deepcopy(body["messages"])
    tail = messages[-1]["content"] if messages else []
    if tail and tail[-1].get("type") == "text" and tail[-1].get("text", "").startswith(STATE):
        tail.pop()
        if not tail:
            messages.pop()
    if strip_cache:
        for message in messages:
            for block in message["content"]:
                block.pop("cache_control", None)
    return [json_bytes(message) for message in messages]


def main():
    verification = json.loads((HERE / "archive_verification.json").read_bytes())
    first_audit = json.loads((HERE / "prefix_audit.json").read_bytes())
    results = {"model_requests": 0, "method": __doc__, "runs": {}}
    for name, archive in verification["runs"].items():
        raw = subprocess.check_output(["git", "show", verification["source_commit"] + ":" + archive["archive"]])
        assert hashlib.sha256(raw).hexdigest() == archive["archive_sha256"]
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r|xz") as bundle:
            for member in bundle:
                if member.isfile() and member.name.endswith("/events.jsonl"):
                    events = [json.loads(line) for line in bundle.extractfile(member).read().splitlines()]
                    prefix = member.name[:-len("events.jsonl")]
                    break
            else:
                raise ValueError("missing archived event stream")
        requests = [e["payload"] for e in events if e["payload"]["event_type"] == "adapter_request"]
        # These A1 captures predate A2's recursive JSON tree. Refuse an unknown
        # storage shape rather than silently miss its dependent blobs.
        assert all(r["final_request_body"]["kind"] in {"inline", "blob", "image_references"} for r in requests)
        wanted = set().union(*(set(references(r["final_request_body"])) for r in requests))
        files = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r|xz") as bundle:
            for member in bundle:
                key = member.name.removeprefix(prefix)
                if member.isfile() and key in wanted:
                    files[key] = bundle.extractfile(member).read()
        assert set(files) == wanted
        reader, adapter = MemoryReader(files), TypeAdapter(CapturedValue)
        previous = None
        rows = []
        for step, request in enumerate(requests, 1):
            wire = reader.capture_bytes(adapter.validate_json(json.dumps(request["final_request_body"])))
            assert hashlib.sha256(wire).hexdigest() == request["wire_sha256"]
            body = json.loads(wire)
            if previous is not None:
                row = {"step": step}
                for strip_cache, key in ((False, "exact_grouped_prefix"), (True, "prefix_except_cache_mark")):
                    left = messages_without_tail(previous, strip_cache)
                    right = messages_without_tail(body, strip_cache)
                    row[key] = left == right[:len(left)]
                row["explicit_compaction"] = first_audit["runs"][name]["rows"][step - 1]["explicit_compaction"]
                rows.append(row)
            previous = body
        results["runs"][name] = {
            "requests_reconstructed": len(requests),
            "exact_grouped_prefix_pairs": sum(row["exact_grouped_prefix"] for row in rows),
            "grouped_prefix_pairs_except_cache_mark": sum(row["prefix_except_cache_mark"] for row in rows),
            "unexplained_grouping_break_steps": [row["step"] for row in rows
                if not row["prefix_except_cache_mark"] and not row["explicit_compaction"]],
            "rows": rows,
        }
        print(name, {k: v for k, v in results["runs"][name].items() if k != "rows"}, flush=True)
    (HERE / "message_grouping_audit.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
