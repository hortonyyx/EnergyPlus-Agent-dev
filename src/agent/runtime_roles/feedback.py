"""Small model-facing views; immutable reader and assembly receipts stay complete."""

from __future__ import annotations

import copy
import hashlib


def reader_batch_reply(value, first_submissions):
    results = []
    for record in value["results"]:
        summary = record.get("summary") or {}
        if record.get("artifact"):
            if record["role_id"] == "plan_reader":
                sentence = (f"{summary.get('space_seeds', 0)} spaces, "
                            f"{summary.get('partitions', 0)} partitions, "
                            f"{summary.get('openings', 0)} openings")
            else:
                sentence = f"{summary.get('orientation', record['target'])}: {summary.get('openings', 0)} openings"
            sentence += f"; {len(summary.get('unresolved', []))} unresolved notes."
        else:
            sentence = " ".join(str(record.get("reason") or record["status"]).split())[:400]
        artifact = record.get("artifact")
        row = {"task_id": record["task_id"], "role_id": record["role_id"],
               "target": record["target"], "status": record["status"],
               "artifact": {key: artifact[key] for key in ("path", "sha256")} if artifact else None,
               "summary": sentence,
               "first_submission_passed": first_submissions.get(record["task_id"])}
        if record.get("reused_saved_result"):
            row["reused_saved_result"] = True
        results.append(row)
    return {"status": value["status"], "results": results,
            "details": "read_role_artifact(task_id) returns the complete verified record and artifact."}


def assembly_reply(value, receipt_path, *, receipt_file=None):
    """Factor identical decision guidance without discarding located evidence."""
    reply = copy.deepcopy(value)
    receipt = {"file": receipt_file or str(receipt_path),
               "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()}
    reply["receipt"] = receipt
    reply["reader_notes"] = {"count": len(value.get("reader_notes", [])),
        "reference": "receipt.response.reader_notes",
        "read": "read_role_artifact(task_id) includes each delivery's unresolved notes."}
    guidance = {}
    for row in reply.get("decisions", []):
        pair = {key: row[key] for key in ("reason", "action") if key in row}
        if not pair:
            continue
        identity = next((key for key, item in guidance.items() if item == pair), None)
        if identity is None:
            identity = f"g{len(guidance) + 1}"
            guidance[identity] = pair
        row["guidance"] = identity
        for key in pair:
            del row[key]
    if guidance:
        reply["decision_guidance"] = guidance
    return reply
