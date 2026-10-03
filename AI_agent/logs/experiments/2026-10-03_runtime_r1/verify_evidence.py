"""Reuse the accepted stage-3 structural checks for an R1 compact archive.

This verifies capture and accounting, not architectural answer quality.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
STAGE3 = ROOT / "AI_agent/logs/experiments/2026-10-02_harness_stage3"
HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_independent_event_roots(checks, view, runs):
    # The experiment used two independent directories named "coordinator".
    # Preserve those original run IDs and validate each complete journal with
    # the accepted validator. Archive paths supply the collection namespace;
    # never rewrite raw evidence merely to make its leaf names globally unique.
    assert len({run.base for run in runs}) == len(runs)
    counts = [checks._validate_event_logs(view, [run]) for run in runs]
    by_raw_id = {}
    for run in runs:
        by_raw_id.setdefault(run.run_id, []).append(run.base)
    return {key: sum(row[key] for row in counts)
            for key in ("runs", "events", "blob_references")} | {
        "root_identities": [{"archive_root": run.base, "raw_run_id": run.run_id} for run in runs],
        "duplicate_raw_ids_across_independent_roots": {
            key: paths for key, paths in by_raw_id.items() if len(paths) > 1},
        "identity_scope": "archive root plus original run_id; no raw evidence was rewritten"}


def verify_facade_protocol(view, runs):
    from src.agent.runtime_r1_facade import evaluate_batches, validate_protocol

    protocol = view.json("facade_experiment/protocol.json")
    manifest_path = HERE / "facade_cases.json"
    assert protocol["manifest_sha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    for path, expected in protocol["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    cases = {row["case_id"]: row for row in json.loads(manifest_path.read_bytes())["cases"]}
    assert validate_protocol(ROOT, manifest_path, HERE / "facade_references.json")["ok"]
    batches = view.json("facade_experiment/batch_results.json")
    evaluation = evaluate_batches(batches, json.loads((HERE / "facade_references.json").read_bytes()))
    assert evaluation == view.json("facade_experiment/evaluation.json")
    assert len(runs) == 2
    summaries = {}
    for run in runs:
        mode = run.base.split("/")[1]
        assert mode in {"concurrent", "sequential"}
        expected_tasks = {f"{mode}_{case}" for case in cases}
        requests = [e for e in run.events if e.payload.event_type == "adapter_request"]
        assert set(e.task_id for e in requests) == expected_tasks
        per_task = Counter(e.task_id for e in requests)
        assert all(1 <= count <= 2 for count in per_task.values())
        assert batches[mode]["requests"] == len(requests)
        batch_outcomes = {row["package"]["task_id"]: row for row in batches[mode]["results"]}
        assert set(batch_outcomes) == expected_tasks
        packages = [path for path in view.keys if path.startswith(run.base + "/tasks/")
                    and path.endswith("/delegation.json")]
        assert len(packages) == 4
        for path in packages:
            saved = view.json(path)
            package = saved["package"]
            assert view.json(path.removesuffix("delegation.json") + "observation.json") == batch_outcomes[package["task_id"]]
            case = cases[package["task_id"].removeprefix(mode + "_")]
            assert package["question"] == case["question"]
            assert saved["arguments"]["budget"] == case["budget"]
            assert [row["original"]["sha256"] for row in saved["views"]] == [case["image_sha256"]]
        for event in requests:
            body = view.capture(run.base, event.payload.final_request_body)
            assert body["model"] == protocol["model"]
            assert body["temperature"] == protocol["temperature"]
            assert body["enable_thinking"] == protocol["enable_thinking"]
        active, peak = set(), 0
        by_reservation = {e.payload.reservation_id: e.event_id for e in requests}
        for event in run.events:
            p = event.payload
            if p.event_type == "adapter_request":
                active.add(event.event_id)
                peak = max(peak, len(active))
            elif p.event_type == "model_response":
                active.discard(p.request_event_id)
            elif p.event_type == "budget" and p.settlement is not None:
                active.discard(by_reservation.get(p.settlement.reservation_id))
        assert not active
        assert peak <= protocol["conditions"][mode]
        assert peak == 4 if mode == "concurrent" else peak == 1
        repairs = [e.payload for e in run.events if e.payload.event_type == "answer_repair"]
        summaries[mode] = {"requests_per_task": dict(per_task), "peak_requests_in_flight": peak,
            "repair_requests": sum(p.phase == "request" for p in repairs),
            "repair_results": sum(p.phase == "result" for p in repairs),
            "accepted_repairs": sum(p.phase == "result" and p.accepted for p in repairs),
            "evaluation_recomputed_from_original_results": True}
    return summaries


def verify_glm_calibration():
    from src.agent_runtime.estimation import estimate_chat_request

    directory = HERE / "glm_calibration"
    source = load_module("r1_glm_calibration_source", directory / "run_calibration.py")
    saved = json.loads((directory / "responses.json").read_bytes())["rows"]
    rows = [json.loads(line) for line in (directory / "quota.jsonl").read_bytes().splitlines()]
    attempts = [r for r in rows if r["event"] == "attempt"]
    responses = [r for r in rows if r["event"] == "response"]
    assert [r["ticket"] for r in attempts] == list(range(1, 6))
    assert [r["ticket"] for r in responses] == list(range(1, 6))
    assert all(r["limit"] == 5 for r in rows)
    verified = []
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for case, record, response in zip(source.cases(), saved, responses, strict=True):
        body = {"model": source.MODEL, "messages": case["messages"],
                "stream": False, "n": 1, **source.PARAMETERS}
        assert record["request"] == source.sanitized_body(body, case.get("image"))
        assert record["image"] == case.get("image")
        usage = record["response"]["usage"]
        assert usage == response["usage"]
        estimate = estimate_chat_request(body, strict=True)
        assert estimate.input_tokens_upper_bound >= usage["prompt_tokens"]
        for key in totals:
            totals[key] += usage[key]
        verified.append({"case": record["case"],
            "input_upper_bound": estimate.input_tokens_upper_bound,
            "reported_input": usage["prompt_tokens"],
            "requested_output_limit": estimate.output_token_limit,
            "reported_completion": usage["completion_tokens"],
            "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens"),
            "reservation_tokens": estimate.reservation_tokens,
            "reported_total": usage["total_tokens"],
            "total_exceeds_reservation": usage["total_tokens"] > estimate.reservation_tokens})
    return {"attempts": len(attempts), "limit": 5, "reported_usage": totals,
        "input_upper_bounds_cover_all": True,
        "total_request_estimates_cover_all": not any(r["total_exceeds_reservation"] for r in verified),
        "rows": verified,
        "limitation": "The endpoint reported reasoning plus visible output above max_tokens in two responses. One total exceeded the present reservation; input calibration is not a total-request guarantee."}


def verify(archive_path, quota_path=None, quota_limit=None):
    pack = load_module("r1_evidence_pack", STAGE3 / "evidence_pack.py")
    checks = load_module("r1_stage3_checks", STAGE3 / "verify_delivery.py")
    archive = pack.read_archive(archive_path)
    view = checks.ArchiveView(archive)
    auditor = checks.Auditor()
    runs = checks._load_runs(view, auditor)
    report = {
        "archive": str(archive_path.relative_to(ROOT)),
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "archive_bytes": archive_path.stat().st_size,
        "blobs": checks._validate_blob_inventory(view),
        "events": verify_independent_event_roots(checks, view, runs),
        "parentage_and_budget": checks._validate_parentage(runs),
        "wire_requests_and_images": checks._validate_wire_requests(view, runs),
        "external_operations": checks._validate_external_operations(view, runs),
        "child_packages": checks._validate_child_packages(view, runs, {}),
        "fixed_facade_protocol": verify_facade_protocol(view, runs),
        "glm_calibration": verify_glm_calibration(),
        "semantic_correctness": "evaluated separately against withheld facade references",
    }
    if quota_path:
        raw = quota_path.read_bytes()
        assert raw == view.read("facade_experiment/request_quota.jsonl")
        assert not raw or raw.endswith(b"\n"), "torn quota journal"
        rows = [json.loads(line) for line in raw.splitlines()]
        attempts = [r for r in rows if r["event"] == "attempt"]
        finished = [r for r in rows if r["event"] in {"response", "failure"}]
        assert attempts and len(attempts) <= quota_limit
        assert all(r["limit"] == quota_limit for r in rows)
        assert [r["ticket"] for r in attempts] == list(range(1, len(attempts) + 1))
        assert Counter(r["ticket"] for r in attempts) == Counter(r["ticket"] for r in finished)
        assert len(attempts) == report["wire_requests_and_images"]["adapter_requests"]
        canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False)
        response_usage = [e.payload.usage.raw_usage for run in runs for e in run.events
                          if e.payload.event_type == "model_response" and e.payload.usage.kind == "reported"]
        quota_usage = [r["usage"] for r in finished
                       if r["event"] == "response" and r.get("usage_status") == "reported"]
        assert Counter(map(canonical, response_usage)) == Counter(map(canonical, quota_usage))
        report["quota"] = {"attempts": len(attempts), "limit": quota_limit,
            "failures": sum(r["event"] == "failure" for r in finished),
            "reported_usage": checks._usage_counts(quota_usage),
            "attempts_without_usage": len(attempts) - len(quota_usage)}
    report["status"] = "passed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--quota", type=Path)
    parser.add_argument("--quota-limit", type=int)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.archive.resolve(), args.quota, args.quota_limit)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
