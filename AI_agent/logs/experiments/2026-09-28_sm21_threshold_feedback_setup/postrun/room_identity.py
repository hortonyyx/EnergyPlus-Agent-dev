"""Supplement existing seed-based opening scores with distinct reference rooms.

Evaluation only. Preserve raw scores and require the independent full partition
audit as well; a seed bijection alone cannot prove complete room shapes.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def review(run):
    original = json.loads((run / "evaluation/original_openings.json").read_text())
    summary = json.loads((run / "summary.json").read_text())
    assert summary["agent_response_completed"], "Do not score an interrupted run as complete"
    admissible, collisions, unresolved = set(), [], []
    for floor in original["floors"]:
        inverse = defaultdict(list)
        for reference, ids in floor["space_identity_by_interior_point"].items():
            if len(ids) != 1:
                unresolved.append({"floor_id": floor["floor_id"], "reference_id": reference,
                                   "candidate_ids": ids})
            for sid in ids:
                inverse[sid].append(reference)
        for sid, refs in inverse.items():
            if len(refs) > 1:
                collisions.append({"floor_id": floor["floor_id"], "candidate_id": sid,
                                   "reference_ids": refs})
            elif len(floor["space_identity_by_interior_point"][refs[0]]) == 1:
                admissible.add(sid)
    rows = []
    for item in original["comparisons"]:
        distinct = bool(item["expected_hosts"]) and all(sid in admissible for sid in item["expected_hosts"])
        rows.append({"floor_id": item["floor_id"], "reference_id": item["reference_id"],
            "opening_id": item["opening_id"], "distinct_reference_room_identity": distinct,
            "host_match_with_distinct_identity": bool(item["host_match"] and distinct),
            "connection_match_with_distinct_identity": None if item["connection_match"] is None
                else bool(item["connection_match"] and distinct)})
    return {"candidate": original["candidate"], "reference_sha256": original["reference_sha256"],
        "reference_room_collisions": collisions, "unresolved_reference_room_seeds": unresolved,
        "raw_hosts": original["hosts"], "raw_connections": original["door_connections"],
        "hosts_with_distinct_reference_room_identity": sum(r["host_match_with_distinct_identity"] for r in rows),
        "connections_with_distinct_reference_room_identity": sum(r["connection_match_with_distinct_identity"] is True for r in rows),
        "comparisons": rows, "model_calls": 0,
        "limit": "Supplementary seed-identity check, not complete partition approval. Preserve existing scores/tolerances; inspect independent full-room shapes and wall/topology findings as well."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    run = parser.parse_args().run.resolve()
    report = review(run)
    (run / "room_identity_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "comparisons"}, ensure_ascii=False))
