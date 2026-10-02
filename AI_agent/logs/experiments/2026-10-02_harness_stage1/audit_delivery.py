"""Read-only audit of recorded stage-1 runs and protected source paths."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.agent_runtime.adapter import decode_image_url
from src.agent_runtime.store import EventStore
from src.harness_contracts import BudgetAmounts, EventLog
from src.harness_contracts.events import _resolve_json_pointer

HERE = Path(__file__).resolve().parent


def audit_run(directory):
    meta = json.loads((directory / "journal.json").read_bytes())
    events = EventStore.read_events(directory / "events.jsonl")
    EventLog(mode="complete", events=tuple(events),
        budget_limit=BudgetAmounts.model_validate_json(json.dumps(meta["budget_limit"])))

    def read_blob(ref):
        path = (directory / ref.uri).resolve()
        assert path.is_relative_to(directory.resolve())
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == ref.sha256
        return data

    def capture(value):
        if value.kind == "inline":
            return value.value
        assert value.kind == "blob"
        return json.loads(read_blob(value.blob))

    blobs = list((directory / "blobs").iterdir())
    for path in blobs:
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == path.name
    requests, images, sent_tools = 0, 0, 0
    for event in events:
        payload = event.payload
        if payload.event_type == "adapter_request":
            requests += 1
            body = capture(payload.final_request_body)
            for injection in payload.injected_content:
                assert capture(injection.content) == _resolve_json_pointer(body, injection.request_location)
            for transmission in payload.images:
                images += 1
                image, _ = decode_image_url(_resolve_json_pointer(body, transmission.request_reference))
                assert image == read_blob(transmission.sent)
                read_blob(transmission.original)
        elif payload.event_type == "tool_presentation":
            sent_tools += 1
            capture(payload.shown_result)
        elif payload.event_type == "model_response":
            capture(payload.raw_response)
        elif payload.event_type == "tool_execution":
            capture(payload.raw_result)
            capture(payload.shown_result)
    return {"events": len(events), "verified_blobs": len(blobs),
        "requests": requests, "image_transmissions": images,
        "delivered_tool_results": sent_tools, "contract_mode": "complete", "status": "passed"}


def main():
    frozen_paths = ["scripts/tool_scripts", "src/agent/geometry", "src/agent/correction", "src/agent/execution"]
    protected_paths = ["AI_agent/Agent.md", "AI_agent/project",
        str((HERE / "brief.md").relative_to(ROOT))]
    frozen = subprocess.check_output(["git", "diff", "--name-only", "5bb10538", "--", *frozen_paths], cwd=ROOT, text=True).splitlines()
    protected = subprocess.check_output(["git", "diff", "--name-only", "3047caac", "--", *protected_paths], cwd=ROOT, text=True).splitlines()
    assert not frozen and not protected
    report = {"frozen_base": "5bb10538", "task_base": "3047caac",
        "frozen_changed_files": frozen, "protected_changed_files": protected,
        "runs": {p.name: audit_run(p) for p in [HERE / "offline_run", HERE / "paratera_probe_01"]},
        "model_call_boundary": {"Paratera": 2, "whole_building": 0, "DeepSeek": 0, "GLM_subscription": 0},
        "note": "No external request; this checks existing artifacts and does not regenerate them."}
    (HERE / "delivery_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
