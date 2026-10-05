"""Combine fixed-source coverage, retaining original failures without double counting."""

import hashlib
import gzip
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CHANGED_TEST = "tests/test_harness_stage0_samples.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(path):
    result = {}
    for case in ET.parse(path).iter("testcase"):
        key = case.get("classname") + "::" + case.get("name")
        assert key not in result
        result[key] = not any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
    return result


def main():
    directory = HERE / "validation"
    first, second = [json.loads((directory / (group + ".json")).read_bytes())
                     for group in ("all", "followup")]
    for run in (first, second):
        assert run["source_unchanged_during_run"] and run["head_before"] == run["head_after"]
        assert run["model_requests"] == 0
    assert second["returncode"] == 0
    changed = {name for name, old in first["source_sha256"].items()
               if digest(ROOT / name) != old}
    assert changed == {CHANGED_TEST}, changed
    assert all(digest(ROOT / name) == value for name, value in second["source_sha256"].items())
    combined = cases(directory / "all.xml")
    for key in list(combined):
        if "test_harness_stage0_samples::" in key or "test_runtime_frozen_long_task::" in key:
            del combined[key]
    followup = cases(directory / "followup.xml")
    assert all(key.split("::")[0].split(".")[-1] in {
        "test_harness_stage0_samples", "test_runtime_frozen_long_task", "test_behaviour_c2", "test_bim_claim_transactions"} for key in followup)
    combined.update(followup)
    assert all(combined.values())
    source = {**first["source_sha256"], **second["source_sha256"]}
    assert all(digest(ROOT / name) == value for name, value in source.items())
    counts = {label: sum(module in key for key in combined) for label, module in (
        ("a4r_money", "test_runtime_a4r_money::"), ("long", "test_runtime_long_task::"),
        ("frozen", "test_runtime_frozen_long_task::"))}
    counts["other"] = len(combined) - sum(counts.values())
    live_report = HERE / ".tmp/frozen-followup/run/frozen_replay_report.json"
    archived_report = directory / "frozen_replay_report.json.gz"
    report_bytes = live_report.read_bytes() if live_report.exists() else gzip.decompress(archived_report.read_bytes())
    report = json.loads(report_bytes)
    assert report["receipt"]["status"] == "completed"
    assert len(report["calls"]) == 75 and len(report["requests"]) == 76
    assert all(row["actual_error"] == row["historical_error"] for row in report["calls"])
    archived_report.write_bytes(gzip.compress(report_bytes, mtime=0))
    result = {"tests": len(combined), "passed": len(combined), "failures": 0,
        "test_files": len({key.split("::")[0] for key in combined}), "coverage": counts,
        "original_run": {key: first[key] for key in ("passed", "failures", "errors", "seconds")},
        "followup_run": {key: second[key] for key in ("passed", "failures", "errors", "seconds")},
        "replaced_module": CHANGED_TEST, "source_sha256": source,
        "retried_without_source_changes": "tests/test_runtime_frozen_long_task.py",
        "frozen_replay_report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "replay_tool_calls": len(report["calls"]), "scripted_responses": len(report["requests"]),
        "all_current_source_hashes_verified": True, "unique_cases": sorted(combined),
        "evidence": {name: {"sha256": digest(directory / name), "bytes": (directory / name).stat().st_size}
                     for name in ("all.json", "all.xml", "all.log", "followup.json", "followup.xml", "followup.log",
                                  "frozen_initial_report.json.gz", "frozen_replay_report.json.gz")},
        "model_requests": 0,
        "boundary": "Combined current coverage, not one uninterrupted passing suite. Only the old-sample "
                    "comparison test changed after the full run; historical fixtures, the 900-second replay "
                    "ceiling, and production sources are unchanged. The timed-out file is retried in full. "
                    "Two indirect runtime-behaviour dependency files are additionally included."}
    (directory / "effective.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("tests", "passed", "test_files", "coverage")}))


if __name__ == "__main__":
    main()
