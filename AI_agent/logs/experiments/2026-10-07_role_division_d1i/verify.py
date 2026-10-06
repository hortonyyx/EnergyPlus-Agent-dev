"""Audit the saved offline replay evidence; no model requests or Git writes."""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from src.agent_runtime.agent_registry import agent_version_record
from scripts.tool_scripts.bim_agent_facade_checks import _pixel_box

from importlib import import_module

replay = import_module("AI_agent.logs.experiments.2026-10-07_role_division_d1i.replay")
HERE, ROOT = replay.HERE, replay.ROOT


def main():
    before, after = [json.loads((HERE / (label + ".json")).read_bytes()) for label in ("before", "after")]
    # Enrich earlier replay output without re-running tools or changing its result.
    for label, bundle in (("before", before), ("after", after)):
        for row in bundle["replays"] + ([bundle["saved_run6_candidate_02"]] if label == "before" else []):
            scratch = Path(row["scratch"])
            if scratch.is_dir():
                row.update(replay.saved_evidence(scratch))
        replay.save(HERE / (label + ".json"), bundle)
    summaries = []
    for old, new in zip(before["replays"], after["replays"], strict=True):
        assert old["run"] == new["run"]
        matched = {item["source_opening_id"] for match in new["matches"] for item in match["result"]["matches"]}
        rows = {row["opening_id"]: row for row in new["height_coverage"]["openings"]}
        assert all(rows[identity]["status"] == "located_applied" for identity in matched)
        assert all(row["status"] == "missing" for identity, row in rows.items() if identity not in matched)
        assert old["geometry"] == new["geometry"] and old["geometry_sha256"] == new["geometry_sha256"]
        assert all(new[key] for key in ("reader_bytes_unchanged", "source_archives_unchanged"))
        assert new["saved_candidates"] == old["saved_candidates"] == 2
        assert new["repeat_created_candidates"] == 0 and new["internal_tools"].count("claim_transaction") == 1
        assert new["model_service_requests"] == 0
        # Delivery binds the canonical model hash, not the JSON file byte hash.
        assert new["selected"]["source_model_sha256"] == new["height_coverage"]["source_model_sha256"]
        archive = replay.ARCHIVES / new["run"]
        assert all(replay.digest(archive / path) == digest for path, digest in new["copied_inputs"].items())
        summaries.append({"run": new["run"], "before": old["height_coverage"]["summary"],
            "after": new["height_coverage"]["summary"], "safe_matches": len(matched),
            "source_geometry_unchanged": True, "geometry_sha256": new["geometry_sha256"],
            "reader_bytes_unchanged": True, "archive_hashes_rechecked": True,
            "selected_source_hash_matches": True, "saved_candidates": 2, "repeat_new_candidates": 0})

    original = before["saved_run6_candidate_02"]
    original_source = replay.ARCHIVES / "sm24_run6/bim/candidate_02/source_model.json"
    assert replay.digest(original_source) == original["source_file_sha256"]
    source = json.loads(original_source.read_bytes())
    by_id = {row["id"]: row for row in source["openings"]}
    calibration = {(row["image"], row["facade"]): row for row in original["calibrations"]}
    matches = {row["source_opening_id"]: (m["result"]["orientation"], row) for m in before["replays"][0]["matches"]
               for row in m["result"]["matches"]}
    updated = {row["opening_id"]: row for row in after["replays"][0]["height_coverage"]["openings"]}
    table = []
    for row in original["coverage"]["openings"]:
        identity = row["opening_id"]
        item = {"opening_id": identity, "facade": row["facade"], "before_status": row["status"],
                "after_status": updated[identity]["status"], "original_issues": row["issues"]}
        if identity in matches:
            facade, match = matches[identity]
            record = next(v for (name, side), v in calibration.items() if side == facade)
            box = _pixel_box(by_id[identity], facade, record["transform"])
            raw = match["bbox"]
            item.update(reader_opening_id=match["artifact_opening_id"], reader_bbox=raw,
                        original_projected_bbox=box, own_facade_calibration_present=True,
                        region_overflow_px={edge: round(max(0, delta), 3) for edge, delta in zip(
                            ("left", "top", "right", "bottom"),
                            (raw[0] - box[0], raw[1] - box[1], box[2] - raw[2], box[3] - raw[3]), strict=True)})
        else:
            item.update(reader_opening_id=None, reason="No safe match and no current image height binding")
        table.append(item)

    registry = json.loads((ROOT / "src/agent_runtime/agent_versions.json").read_bytes())
    base = json.loads(subprocess.check_output([
        "git", "--no-optional-locks", "show", "HEAD:src/agent_runtime/agent_versions.json"], cwd=ROOT))
    assert all(registry["versions"].get(k) == v for k, v in base["versions"].items())
    record = agent_version_record(ROOT, "t1-20261007-d1i.1")
    previous = base["versions"][base["current_version"]]
    changed = [path for path, metadata in previous["files"].items() if record["files"][path] != metadata]
    added = sorted(set(record["files"]) - set(previous["files"]))
    assert changed == ["src/agent/runtime_roles/height_writes.py"]
    assert added == ["src/agent/runtime_roles/height_evidence.py"]
    assert record["tool_catalog_sha256"] == previous["tool_catalog_sha256"]
    tests = [{"file": path.name, **ET.parse(path).getroot().find("testsuite").attrib}
             for path in sorted(HERE.glob("*_tests.xml"))]
    assert len(tests) == 2 and sum(int(row["tests"]) for row in tests) == 196
    assert all(int(row[key]) == 0 for row in tests for key in ("errors", "failures", "skipped"))
    evidence = {"scope": "offline only; coverage is current evidence location, not a new drawing quality judgment",
        "replays": summaries, "saved_run6_original_summary": original["coverage"]["summary"],
        "run6_opening_table": table, "model_service_requests": 0, "paratera_requests": 0, "deepseek_requests": 0,
        "version": record["version_id"], "registered_files": len(record["files"]),
        "new_module_registered": "src/agent/runtime_roles/height_evidence.py" in record["files"],
        "old_version_records_unchanged": True, "version_file_hash_verification": "passed",
        "changed_registered_files": changed, "added_registered_files": added,
        "shared_tool_catalog_hashes_unchanged": True,
        "tool_catalog_hashes": record["tool_catalog_sha256"], "tests": tests}
    replay.save(HERE / "verification.json", evidence)
    print(json.dumps({k: v for k, v in evidence.items() if k not in {"run6_opening_table", "tool_catalog_hashes"}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
