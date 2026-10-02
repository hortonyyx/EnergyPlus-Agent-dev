"""Shared developer claim batches: one claim per facade/opening family, each citing only the
elevation of the facade its openings are on; then adopt all and confirm on the candidate."""
import json


def chain(lengths, origin, segment):
    return {"type": "dimension_chain", "lengths": lengths, "unit": "mm", "origin_m": origin,
            "direction": 1, "segment": segment}


def record(candidate, views, claims):
    out = []
    for facade, kind, ids, value, reason in claims:
        basis = "pixels" if value["type"] == "literal" else "annotation_and_pixels"
        claim = {"candidate": candidate, "objects": [{"kind": kind, "id": i} for i in ids], "basis": basis,
                 "reason": reason, "sources": [{"view_id": views[facade]}], "values": {"height": value},
                 "observation_mode": "direct", "unresolved": []}
        out.append({"tool": "record_claim", "arguments": {"claim_json": json.dumps(claim)}})
    return out


def adopt_and_confirm(candidate, claims, claim_ids):
    out = [{"tool": "decide_claim", "arguments": {"claim_id": cid, "disposition": "adopted",
            "reason": "Transcribed from this facade's own elevation chain; matches the drafted values."}}
           for cid in claim_ids]
    operations = [{"op": "update_window" if kind == "window" else "update_opening", "id": i,
                   "changes": {"z": {"claim": cid, "value": "height"}},
                   "reason": "Confirm the drafted height against this facade's elevation evidence"}
                  for cid, (_, kind, ids, _, _) in zip(claim_ids, claims) for i in ids]
    out.append({"tool": "confirm_claims", "arguments": {"candidate": candidate, "operations_json": json.dumps(operations)}})
    return out
