"""Verify R2 captured evidence locally, without credentials or model requests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

from src.agent_runtime.agent_registry import agent_version_record
from src.harness_contracts import BudgetAmounts, EventEnvelope, EventLog


ROOT = Path(__file__).resolve().parents[4]
DELIVERY = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(name):
    return json.loads((DELIVERY / name).read_bytes())


def source_references(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            yield value
        for child in value.values():
            yield from source_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from source_references(child)


def main():
    manifest = read_json("live_truncation_probe_manifest.json")
    archive_path = DELIVERY / "live_truncation_probe.tar.xz"
    assert digest(archive_path.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive_path) as archive:
        stored = {name for name, record in manifest["files"].items() if record["kind"] == "stored"}
        assert set(archive.getnames()) == stored
        files = {name: archive.extractfile(name).read() for name in archive.getnames()}
    for name, record in manifest["files"].items():
        if record["kind"] == "repository":
            source = (ROOT / record["path"]).resolve()
            assert source.is_relative_to(ROOT)
            files[name] = source.read_bytes()
    for name, data in files.items():
        record = manifest["files"][name]
        assert digest(data) == record["sha256"] and len(data) == record["bytes"], name

    events = tuple(EventEnvelope.model_validate_json(line)
                   for line in files["events.jsonl"].splitlines())
    receipt = json.loads(files["receipt.json"])
    limit = BudgetAmounts.model_validate_json(json.dumps(receipt["budget"]["total_limit"]))
    EventLog(mode="complete", events=events, budget_limit=limit)

    def resolve(capture):
        return json.loads(files[capture.blob.uri]) if capture.kind == "blob" else capture.value

    requests = [e for e in events if e.payload.event_type == "adapter_request"]
    responses = [e for e in events if e.payload.event_type == "model_response"]
    truncations = [e for e in events if e.payload.event_type == "response_truncation"]
    settlements = [e for e in events if e.payload.event_type == "budget"
                   and e.payload.action == "settle"]
    assert len(requests) == len(responses) == len(settlements) == 2
    assert len(truncations) == 1 and truncations[0].payload.action == "continue"
    raw = [resolve(e.payload.raw_response) for e in responses]
    assert [r["choices"][0]["finish_reason"] for r in raw] == ["length", "stop"]
    retry = resolve(requests[1].payload.final_request_body)
    assert retry["max_tokens"] == 128
    assert not any(m["role"] == "assistant" for m in retry["messages"])
    assert any("previous response exceeded the output limit" in m.get("content", "")
               for m in retry["messages"])
    assert "reasoning_content" not in json.dumps(retry)
    assert not any(e.payload.event_type == "tool_invocation" for e in events)
    totals = {k: sum(r["usage"][k] for r in raw)
              for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    assert totals == {"prompt_tokens": 209, "completion_tokens": 160, "total_tokens": 369}
    assert sum(e.payload.settlement.actual.tokens for e in settlements) == 369
    result = read_json("truncation_probe_result.json")
    assert receipt["status"] == result["status"] == "completed"
    assert receipt["answer"] == result["answer"] == "OK"
    assert receipt["reported_tokens"] == result["reported_tokens"] == 369
    assert result["estimated_cost_cny"] == "0.0006152"
    tickets = [json.loads(line) for line in (DELIVERY / "paratera_requests.jsonl").read_bytes().splitlines()]
    assert len([t for t in tickets if t["event"] == "attempt"]) == 2
    assert len([t for t in tickets if t["event"] == "response"]) == 2
    assert all(t["limit"] == 5 and t["category"] == "r2_truncation_probe_only" for t in tickets)
    fixture = read_json("truncation_evidence_audit.json")["existing_offline_counterexample"]
    assert digest((ROOT / fixture["path"]).read_bytes()) == fixture["sha256"]

    calibration = read_json("image_accounting_calibration.json")
    for reference in source_references(calibration):
        assert digest((ROOT / reference["path"]).read_bytes()) == reference["sha256"]
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    recomputed = json.loads(subprocess.check_output(
        [sys.executable, str(DELIVERY / "calibrate_image_accounting.py")], cwd=ROOT, env=env))
    qwen = recomputed["qwen_event_calibration"]
    assert recomputed["sources"]["historical_elevation_probe"] == calibration["evidence"]["historical_elevation_probe"]
    assert qwen["classifications"]["top_level_includes_image"]["requests"] == 62
    assert qwen["bill_tokens_covered"] == qwen["formula_tokens_for_covered_buckets"] == 72_406
    assert qwen["covered_difference"] == qwen["formula_max_absolute_token_error_when_reported"] == 0
    assert qwen["bill_coverage_percent"] == 100.0
    assert len(qwen["matched_bill_buckets"]) == 10 and qwen["unmatched_bill_buckets"] == []
    assert recomputed["bill"]["image_tokens"] == 72_406
    assert recomputed["glm_formula_calibration"]["large_image_overestimate_tokens"] == 1_139
    assert recomputed["external_requests_made"] == 0
    (DELIVERY / "image_accounting_recomputed.json").write_text(
        json.dumps(recomputed, ensure_ascii=False, indent=2) + "\n")
    current = agent_version_record(ROOT)
    assert current["version_id"] == "5bb10538" and len(current["files"]) == 45
    report = {"status": "passed", "archive_stored_files": len(stored), "resolved_files": len(files), "live_events": len(events),
        "live_requests": len(requests), "live_usage": totals, "current_agent_version": current["version_id"],
        "registered_files_verified": len(current["files"]), "qwen_matched_bill_tokens": 72_406,
        "qwen_maximum_absolute_error": 0, "new_external_requests": 0,
        "note": "Archive captures the earlier live probe revision; final code is covered by offline validation."}
    (DELIVERY / "evidence_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
