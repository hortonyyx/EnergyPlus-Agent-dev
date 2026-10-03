"""Pack or verify the completed subscription probe entirely offline."""

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

from src.agent.runtime_r1_preparation import load_configuration
from src.agent_runtime.agent_registry import agent_version_record
from src.harness_contracts import BudgetAmounts, EventEnvelope, EventLog

from reconcile_billing import reconcile

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pack():
    records = {}
    lock = (ROOT / "uv.lock").read_bytes()
    with tarfile.open(HERE / "subscription_probe.tar.xz", "w:xz") as archive:
        for path in sorted((HERE / "live").rglob("*")):
            if not path.is_file() or path.name.endswith(".lock"):
                continue
            data = path.read_bytes()
            name = str(path.relative_to(HERE / "live"))
            record = {"sha256": digest(data), "bytes": len(data)}
            if data == lock:
                record.update(kind="repository", path="uv.lock")
            else:
                record["kind"] = "stored"
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                archive.addfile(info, io.BytesIO(data))
            records[name] = record
    manifest = {"files": records, "archive_sha256": digest((HERE / "subscription_probe.tar.xz").read_bytes()),
        "note": "Exact new request/response/event bytes; unchanged dependency lock referenced by path and SHA-256."}
    (HERE / "subscription_probe_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def verify():
    manifest = json.loads((HERE / "subscription_probe_manifest.json").read_bytes())
    assert digest((HERE / "subscription_probe.tar.xz").read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(HERE / "subscription_probe.tar.xz") as archive:
        assert set(archive.getnames()) == {name for name, r in manifest["files"].items() if r["kind"] == "stored"}
        files = {name: archive.extractfile(name).read() for name in archive.getnames()}
    for name, record in manifest["files"].items():
        if record["kind"] == "repository":
            path = (ROOT / record["path"]).resolve()
            assert path.is_relative_to(ROOT)
            files[name] = path.read_bytes()
        assert digest(files[name]) == record["sha256"] and len(files[name]) == record["bytes"]
    totals = {}
    details = []
    for phase in ("visual_tool", "truncation"):
        prefix = phase + "/"
        events = tuple(EventEnvelope.model_validate_json(line) for line in files[prefix + "events.jsonl"].splitlines())
        receipt = json.loads(files[prefix + "receipt.json"])
        EventLog(mode="complete", events=events, budget_limit=BudgetAmounts.model_validate_json(json.dumps(receipt["budget"]["total_limit"])))
        def resolve(capture):
            return json.loads(files[prefix + capture.blob.uri]) if capture.kind == "blob" else capture.value
        requests = [e.payload for e in events if e.payload.event_type == "adapter_request"]
        responses = [e.payload for e in events if e.payload.event_type == "model_response"]
        settlements = [e.payload.settlement for e in events if e.payload.event_type == "budget" and e.payload.action == "settle"]
        assert len(requests) == len(responses) == len(settlements) == 2
        raw = [resolve(r.raw_response) for r in responses]
        body = [resolve(r.final_request_body) for r in requests]
        assert receipt["status"] == "completed" and receipt["answer"] == "OK"
        assert receipt["estimated_cost_cny"] is None and receipt["billing_usd"] is None
        assert receipt["usage_accounting"]["billing_modes"] == ["subscription"]
        for request, sent in zip(requests, body):
            assert request.versions.remote_model.route_id == "glm-subscription"
            assert sent["model"] == "glm-5.3-flash" and sent["stream"] is False
            assert not {"n", "temperature", "thinking", "enable_thinking", "reasoning_effort"} & sent.keys()
            assert request.parameters.requested == {"max_tokens": 32000 if phase == "visual_tool" else 512}
            code_ref = request.versions.code_commit.evidence.blob
            code = json.loads(files[prefix + code_ref.uri])
            for source, sha in code["files"].items():
                assert digest((ROOT / source).read_bytes()) == sha, source
        if phase == "visual_tool":
            assert [r["choices"][0]["finish_reason"] for r in raw] == ["tool_calls", "stop"]
            assert len(requests[0].images) == len(requests[1].images) == 1
            sent = requests[0].images[0].sent
            assert digest(files[prefix + sent.uri]) == sent.sha256
            encoded = body[0]["messages"][1]["content"][1]["image_url"]["url"].split(",", 1)[1]
            assert base64.b64decode(encoded) == files[prefix + sent.uri]
            calls = [e.payload for e in events if e.payload.event_type == "tool_invocation"]
            assert len(calls) == 1 and calls[0].tool_name == "report_color" and calls[0].full_arguments == {"color": "green"}
            assert any(m["role"] == "tool" for m in body[1]["messages"])
            assert raw[0]["choices"][0]["message"]["reasoning_content"]
        else:
            assert [r["choices"][0]["finish_reason"] for r in raw] == ["length", "stop"]
            assert not any(m["role"] == "assistant" for m in body[1]["messages"])
            assert "reasoning_content" not in json.dumps(body[1])
            assert any("previous response exceeded the output limit" in m.get("content", "") for m in body[1]["messages"])
            assert receipt["truncations"] == 1
        tokens = sum(r["usage"]["total_tokens"] for r in raw)
        assert sum(s.actual.tokens for s in settlements) == tokens == receipt["reported_tokens"]
        totals[phase] = tokens
        details += [{"phase": phase, "request": index + 1, "usage": r["usage"],
            "finish_reason": r["choices"][0]["finish_reason"],
            "thinking_characters": len(r["choices"][0]["message"].get("reasoning_content") or "")} for index, r in enumerate(raw)]
    tickets = [json.loads(line) for line in (HERE / "subscription_requests.jsonl").read_bytes().splitlines()]
    assert len([t for t in tickets if t["event"] == "attempt"]) == 4
    assert len([t for t in tickets if t["event"] == "response"]) == 4
    assert not any(t["event"] == "failure" for t in tickets)
    assert all(t["limit"] == 6 and t["model"] == "glm-5.3-flash" for t in tickets)
    bill = reconcile()
    saved = json.loads((HERE / "billing_reconciliation.json").read_bytes())
    assert bill == saved
    config = load_configuration(HERE / "configs/migration_sm24_glm_subscription.json")
    case = config["cases"][0]
    baseline_path = ROOT / "AI_agent/logs/experiments/2026-10-02_sm24_glm_baseline/agent_request.json"
    baseline = json.loads(baseline_path.read_bytes())
    assert case["scope"].encode() == baseline["prompt"].encode()
    assert not (ROOT / case["output"]).exists()
    inputs = json.loads((baseline_path.parent / "inputs.json").read_bytes())["images"]
    assert set(inputs) == {p.name for p in (ROOT / case["input"]).glob("*.png")}
    for name, record in inputs.items():
        assert digest((ROOT / case["input"] / name).read_bytes()) == record["sha256"]
    from scripts.tool_scripts.bim_agent_guidance import build_guide
    guide = build_guide(images=case["image_kind"], mesh=False)
    assert guide == baseline["system_prompt"]
    agent = agent_version_record(ROOT)
    assert agent["version_id"] == "5bb10538"
    result = {"status": "passed", "external_requests_made": 0, "live_attempts_verified": 4,
        "maximum_authorized_attempts": 6, "failed_attempts": 0, "provider_reported_tokens": sum(totals.values()),
        "requests": details, "billing_reconciliation": bill["status"], "agent_version": agent["version_id"],
        "frozen_files_verified": len(agent["files"]), "task_sha256": digest(case["scope"].encode()),
        "baseline_request_sha256": digest(baseline_path.read_bytes()), "whole_building_run": False,
        "baseline_images_verified": len(inputs), "guide_sha256": digest(guide.encode()),
        "probe_source_matches_delivery": True,
        "resolved_probe_files": len(files), "archive_bytes": (HERE / "subscription_probe.tar.xz").stat().st_size}
    (HERE / "delivery_verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", action="store_true")
    args = parser.parse_args()
    if args.pack:
        pack()
    verify()
