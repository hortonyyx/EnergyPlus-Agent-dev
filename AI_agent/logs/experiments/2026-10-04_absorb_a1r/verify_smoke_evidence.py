"""Restore and verify the four captured small requests, entirely offline."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import tarfile

from src.agent.runtime_behaviour import load_behaviour
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts
from src.harness_contracts.events import _resolve_json_pointer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if not scratch.is_relative_to(ROOT) or scratch.exists():
        raise ValueError("use a new scratch directory inside this worktree")
    manifest = json.loads((HERE / "subscription_smoke_manifest.json").read_bytes())
    archive = HERE / manifest["archive"]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest["archive_sha256"]
    scratch.mkdir(parents=True)
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(scratch, filter="data")
    for item in manifest["files"]:
        target = scratch / item["path"]
        assert target.resolve().is_relative_to(scratch)
        if not item["packaged"]:
            data = (ROOT / item["shared_source"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == item["sha256"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        data = target.read_bytes()
        assert len(data) == item["bytes"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
    quota = [json.loads(line) for line in (scratch / "request_quota.jsonl").read_text().splitlines()]
    assert sum(row["event"] == "attempt" for row in quota) == 4
    results = {}
    for part in ("roundtrip", "truncation"):
        run = scratch / part
        meta = json.loads((run / "journal.json").read_bytes())
        limits = BudgetAmounts.model_validate_json(json.dumps(meta["budget_limit"]))
        with EventStore(run, run_id=meta["run_id"], task_id=meta["task_id"], budget_limit=limits) as store:
            requests = [e.payload for e in store.events if e.payload.event_type == "adapter_request"]
            responses = [store.resolve(e.payload.raw_response) for e in store.events if e.payload.event_type == "model_response"]
            assert len(requests) == len(responses) == 2
            bodies = []
            image_count = 0
            for request in requests:
                wire = store.capture_bytes(request.final_request_body)
                assert hashlib.sha256(wire).hexdigest() == request.wire_sha256
                body = json.loads(wire)
                bodies.append(body)
                for image in request.images:
                    assert base64.b64decode(_resolve_json_pointer(body, image.request_reference), validate=True) == store.get_bytes(image.sent)
                    assert store.get_bytes(image.original) == store.get_bytes(image.sent)
                    image_count += 1
            if part == "roundtrip":
                replayed = next(m["content"] for m in bodies[1]["messages"] if m["role"] == "assistant")
                assert replayed == responses[0]["content"]
                assert any(b["type"] == "thinking" and b.get("signature") for b in replayed)
                assert responses[1]["usage"]["cache_read_input_tokens"] > 0
                assert responses[0]["stop_reason"] == "tool_use"
                assert responses[1]["stop_reason"] == "end_turn"
                results[part] = {"thinking_and_signature_replayed_exactly": True,
                    "cache_read_tokens_second_request": responses[1]["usage"]["cache_read_input_tokens"]}
            else:
                assert responses[0]["stop_reason"] == "max_tokens"
                assert not any(m["role"] == "assistant" for m in bodies[1]["messages"])
                assert responses[1]["stop_reason"] == "end_turn"
                assert any(b.get("text") == "OK" for b in responses[1]["content"])
                assert not any(e.payload.event_type == "tool_execution" for e in store.events)
                results[part] = {"truncated_response_not_replayed": True, "recovery_completed": True,
                    "partial_tools_executed": 0}
            store.validate()
            results[part].update({"wire_hashes_verified": len(requests), "original_image_occurrences_verified": image_count,
                "event_contracts_valid": True})
        load_behaviour(run)
        results[part]["behaviour_reader_valid"] = True
    record = {"files_verified": len(manifest["files"]), "archive_sha256": manifest["archive_sha256"],
        "captured_requests": 4, "new_model_requests": 0, "paratera": 0, "deepseek": 0, "results": results}
    (HERE / "smoke_verification.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
