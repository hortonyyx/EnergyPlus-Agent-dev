"""Reproducible self-test for role references and scorer (all Git access read-only)."""
from __future__ import annotations

import io
import json
import subprocess
import tarfile
from pathlib import Path

from score_role_answers import score, source_answer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def git_bytes(spec: str) -> bytes:
    return subprocess.run(["git", "show", spec], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE).stdout


def direct_json(spec: str) -> dict:
    return json.loads(git_bytes(spec))


def archive_json(spec: str, member: str) -> dict:
    with tarfile.open(fileobj=io.BytesIO(git_bytes(spec)), mode="r:xz") as archive:
        extracted = archive.extractfile(member)
        if extracted is None:
            raise FileNotFoundError(member)
        return json.load(extracted)


GOOD = [
    ("opus_sm21", "sm21_anchor", "4db92a2c:AI_agent/logs/experiments/2026-10-01_opus_dev_sm21/candidate_04/source_model.json"),
    ("opus_sm24", "sm24_anchor", "4db92a2c:AI_agent/logs/experiments/2026-10-01_opus_dev_sm24/candidate_02/source_model.json"),
    ("opus_sm25", "sm25-L_anchor", "4db92a2c:AI_agent/logs/experiments/2026-10-01_opus_dev_sm25/candidate_04/source_model.json"),
]

BAD = [
    ("c3_qwen27b_sm24", "sm24_anchor",
     "evidence/node-regression-c3-2026-10-05:sm24_qwen27b_c3_run.tar.xz",
     "sm24_qwen27b_c3/bim/candidate_04/source_model.json"),
    ("c3_runtime_sm25", "sm25-L_anchor",
     "evidence/node-regression-c3-2026-10-05:sm25_runtime_anthropic_run.tar.xz",
     "sm25_runtime_anthropic/bim/candidate_06/source_model.json"),
]


def compact(report: dict) -> dict:
    floors = []
    for row in report["floors"]:
        if row["status"] == "missing":
            floors.append(row)
            continue
        floors.append({
            "floor_id": row["floor_id"], "status": row["status"],
            "rooms": {"status": row["rooms"]["status"],
                      "matched": row["rooms"]["matched_count"],
                      "reference": row["rooms"]["reference_count"]},
            "partitions": row["partitions"],
            "openings": {key: row["openings"][key] for key in
                         ("status", "reference_count", "matched", "positions",
                          "unmatched_reference", "unmatched_answer")},
        })
    elevations = report["elevations"]
    return {"status": report["status"], "floors": floors,
            "elevations": {key: elevations[key] for key in
                           ("status", "reference_count", "matched", "within_tolerance",
                            "unmatched_reference", "unmatched_answer")}}


def main() -> None:
    results = []
    for name, case, spec in GOOD:
        reference = json.loads((HERE / "references" / f"{case}.json").read_bytes())
        report = score(reference, source_answer(direct_json(spec), case))
        results.append({"name": name, "expected": "near_full", "git_source": spec,
                        "result": compact(report)})
    for name, case, archive, member in BAD:
        reference = json.loads((HERE / "references" / f"{case}.json").read_bytes())
        report = score(reference, source_answer(archive_json(archive, member), case))
        results.append({"name": name, "expected": "known_error_reproduced",
                        "git_source": archive, "archive_member": member,
                        "result": compact(report)})
    output = {"schema_version": "role_reference_self_test_v1", "results": results,
              "assertions": {
                  "opus_all_plan_openings_full": all(
                      all(f.get("openings", {}).get("positions") == f.get("openings", {}).get("reference_count")
                          for f in row["result"]["floors"])
                      for row in results[:3]),
                  "qwen_sm24_room_split_detected": any(
                      f.get("rooms", {}).get("status") == "severe" for f in results[3]["result"]["floors"]),
                  "runtime_sm25_opening_regression_detected": sum(
                      f.get("openings", {}).get("positions", 0) for f in results[4]["result"]["floors"]) == 22,
              }}
    if not all(output["assertions"].values()):
        raise AssertionError(json.dumps(output["assertions"], ensure_ascii=False))
    target = HERE / "self_test_results.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["assertions"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
