"""Combine unchanged successful coverage with the complete affected-file rerun.

Never overwrite the original failure. All selected source hashes must still
match; repeated cases are replaced, not counted twice. This reads offline
evidence only and cannot launch a model or pytest.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
REPLAY_TEST = "tests/test_runtime_frozen_long_task.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cases(path):
    result = {}
    for case in ET.parse(path).iter("testcase"):
        key = case.get("classname") + "::" + case.get("name")
        assert key not in result, key
        result[key] = not any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
    return result


def main():
    directory = HERE / "validation"
    first = json.loads((directory / "all.json").read_bytes())
    second = json.loads((directory / "frozen.json").read_bytes())
    for result in (first, second):
        assert result["source_unchanged_during_run"]
        assert result["head_before"] == result["head_after"]
        assert result["model_requests"] == 0
    assert second["returncode"] == 0
    changed = {name for name, old in first["source_sha256"].items()
               if sha((ROOT / name).read_bytes()) != old}
    assert changed == {REPLAY_TEST}, changed
    assert all(sha((ROOT / name).read_bytes()) == digest
               for name, digest in second["source_sha256"].items())
    combined = cases(directory / "all.xml")
    affected = {key for key in combined if "test_runtime_frozen_long_task::" in key}
    for key in affected:
        del combined[key]
    followup = cases(directory / "frozen.xml")
    assert all("test_runtime_frozen_long_task::" in key for key in followup)
    combined.update(followup)
    assert len(combined) == 447 and all(combined.values())
    run = HERE / ".tmp/frozen-replay-1/run"
    live_report = run / "frozen_replay_report.json"
    archived_report = directory / "frozen_replay_report.json.gz"
    report_bytes = (live_report.read_bytes() if live_report.exists()
                    else gzip.decompress(archived_report.read_bytes()))
    report = json.loads(report_bytes)
    assert report["receipt"]["status"] == "completed"
    assert len(report["calls"]) == 75 and len(report["requests"]) == 76
    assert [c["step"] for c in report["calls"] if c["actual_error"]] == [18, 19, 56, 58, 62, 63, 73]
    assert all(c["actual_error"] == c["historical_error"] for c in report["calls"])
    packed = gzip.compress(report_bytes, mtime=0)
    archived_report.write_bytes(packed)
    files = {name: {"sha256": sha((directory / name).read_bytes()),
                    "bytes": (directory / name).stat().st_size}
             for name in ("all.json", "all.xml", "all.log", "frozen.json", "frozen.xml",
                          "frozen.log", "frozen_replay_report.json.gz")}
    source = {**first["source_sha256"], **second["source_sha256"]}
    result = {
        "tests": len(combined), "passed": sum(combined.values()), "failures": 0,
        "coverage": {"short": 433, "long": 10, "frozen": 4},
        "original_run": {"passed": first["passed"], "failures": first["failures"]},
        "followup_run": {"passed": second["passed"], "failures": second["failures"]},
        "replaced_module": REPLAY_TEST, "source_sha256": source,
        "all_current_source_hashes_verified": True,
        "unique_cases": sorted(combined), "evidence": files,
        "replay_report_uncompressed_sha256": sha(report_bytes),
        "replay_report_uncompressed_bytes": len(report_bytes),
        "replay_calls": len(report["calls"]), "scripted_model_responses": len(report["requests"]),
        "legacy_catalog_additions": report["historical_catalog_additions"],
        "model_requests": 0,
        "boundary": "Combined coverage, not one uninterrupted passing suite. Original failure retained. "
                    "75-call real-tool replay uses retained legacy APIs only in the test; all original "
                    "arguments, errors, state/image hashes and compaction assertions remain unchanged. "
                    "The compressed report is retained; temporary runtime blobs are not included."
    }
    (directory / "effective.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("tests", "passed", "failures", "coverage", "replay_calls")}))


if __name__ == "__main__":
    main()
