"""After runs stop, index local evidence and summarize the three-reader journal."""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LOCAL = ROOT / "AI_agent/archive/local_backup/d1b"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def manifest(directory, name):
    files = {}
    sizes = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("evidence contains an unexpected symbolic link")
        if path.is_file():
            key = path.relative_to(directory).as_posix()
            raw = path.read_bytes()
            files[key], sizes[key] = hashlib.sha256(raw).hexdigest(), len(raw)
    value = {"directory": directory.relative_to(ROOT).as_posix(), "file_count": len(files),
             "bytes": sum(sizes.values()), "files_sha256": files,
             "archiving": "Raw directory retained for Opus; execution side did not package it."}
    path = HERE / "evidence" / (name + "_manifest.json")
    write(path, value)
    return {key: value[key] for key in ("directory", "file_count", "bytes", "archiving")} | {
        "manifest": path.relative_to(HERE).as_posix(),
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def small_test_details(directory, output_name):
    result = json.loads((directory / "small_test_result.json").read_bytes())
    rows = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    tasks = []
    for record in result["results"]:
        events = [row for row in rows if row["task_id"] == record["task_id"]]
        submissions = [row["payload"] for row in events if row["payload"]["event_type"] == "tool_execution"
                       and row["payload"]["tool_name"].startswith("submit_")]
        usage = result["accounting"]["by_task"][record["task_id"]]
        totals = {field: usage[aggregate] for field, aggregate in {
            "input_tokens": "reported_input_tokens", "output_tokens": "reported_output_tokens",
            "cache_read_input_tokens": "reported_cache_read_tokens",
            "cache_creation_input_tokens": "reported_cache_write_tokens"}.items()}
        folder = next(path.parent for path in (directory / "tasks").glob("*/reader_task.json")
                      if json.loads(path.read_bytes())["task_id"] == record["task_id"])
        receipt = json.loads((folder / "receipt.json").read_bytes())
        trials = [json.loads(path.read_bytes()) for path in (folder / "bim/trial_workspace/trial_receipts").glob("trial_[0-9][0-9][0-9].json")]
        tasks.append({"task_id": record["task_id"], "target": record["target"], "status": record["status"],
            "runtime_status": record["runtime_status"], "elapsed_seconds": receipt["elapsed_seconds"],
            "requests": sum(row["payload"]["event_type"] == "adapter_request" for row in events),
            "first_submission_passed": submissions[0]["outcome"] == "succeeded" if submissions else None,
            "submission_attempts": len(submissions),
            "submission_rejections": sum(row["outcome"] != "succeeded" for row in submissions),
            "answer_repair_requests": sum(row["payload"]["event_type"] == "answer_repair"
                                           and row["payload"]["phase"] == "request" for row in events),
            "tool_calls": collections.Counter(row["payload"]["tool_name"] for row in events
                                               if row["payload"]["event_type"] == "tool_execution"),
            "trial_count": len(trials), "passed_trials": sum(row["status"] == "passed" for row in trials),
            "declared_rework_count": sum(bool(row.get("changes")) for row in trials),
            "reported_raw_usage": totals,
            "reported_token_total_including_cache": usage["provider_reported_tokens"],
            "usage_complete": usage["usage_complete"]})
    value = {"run": directory.relative_to(ROOT).as_posix(), "tasks": tasks,
             "wall_seconds": result["wall_seconds"], "http_requests": result["actual_http_requests"],
             "provider_reported_tokens": result["accounting"]["provider_reported_tokens"],
             "agent_unchanged": result["agent_unchanged"],
             "usage_note": "Anthropic raw input excludes cache read/create; token total here includes all three input categories plus output. Full authoritative aggregate and safety ledger remain in small_test_summary.json.",
             "external_calls": {"glm_subscription": result["actual_http_requests"], "paratera": 0, "deepseek": 0,
                                "coordinator_model": 0, "whole_building_generation": 0}}
    write(HERE / (output_name + ".json"), value)
    return value


def main():
    details = [small_test_details(LOCAL / "small_test_d1b", "small_test_details"),
               small_test_details(LOCAL / "small_test_d1b_final", "small_test_final_details")]
    cumulative = sum(row["http_requests"] for row in details)
    assert cumulative <= 40
    indexes = []
    for folder, label in (("offline_final", "offline_v1"), ("offline_final_v2", "offline_v2")):
        indexes.extend(manifest(LOCAL / folder / case, label + "_" + case)
                       for case in ("sm21", "sm24", "sm25"))
    indexes.extend([manifest(LOCAL / "small_test_d1b", "small_test_v1"),
                    manifest(LOCAL / "small_test_d1b_final", "small_test_v2"),
                    manifest(LOCAL / "preflight_real_replay", "preflight_real_replay")])
    value = {"runs": details, "http_requests": cumulative, "authorized_maximum": 40,
             "provider_reported_tokens": sum(row["provider_reported_tokens"] for row in details),
             "sum_of_batch_wall_seconds": sum(row["wall_seconds"] for row in details),
             "same_budget_comparison": False,
             "note": "The first batch used 23 calls and exposed a wrapper bug. The final fixed-code cold batch used only the original authorization's remaining 17-call shared ceiling; tasks and instructions stayed identical. Missing plan delivery is not scored as observed bad geometry.",
             "paratera_requests": 0, "deepseek_requests": 0, "whole_building_runs": 0}
    write(HERE / "small_test_cumulative.json", value)
    write(HERE / "evidence_index.json", {"runs": indexes})
    print(json.dumps({"small_test": value, "evidence": indexes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
