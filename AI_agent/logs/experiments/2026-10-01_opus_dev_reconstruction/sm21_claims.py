"""Developer's sm21 height claims: one claim per facade/storey/opening family, each citing
only the elevation of the facade its openings are on (the behaviour that separated the
good runs from run93/94/99). Writes the request list for the bridge."""
import json
from pathlib import Path
import sys

RUN = Path(__file__).resolve().parents[1] / "2026-10-01_opus_dev_sm21"
CANDIDATE = sys.argv[1] if len(sys.argv) > 1 else "candidate_03"
VIEWS = {"North": "view_0003", "South": "view_0004", "East": "view_0005", "West": "view_0006"}


def chain(lengths, origin, segment):
    return {"type": "dimension_chain", "lengths": lengths, "unit": "mm", "origin_m": origin,
            "direction": 1, "segment": segment}


CLAIMS = [
    ("North", "window", ["F1:W_N1", "F1:W_N2", "F1:W_N3"], chain([1000, 1600, 400], 0.0, 1),
     "North_view.png ground-storey inner chain read upward from the ground line: 1000/1600/400 = 3000; "
     "the 1600 segment spans the sill and head lines shared by the three equal ground-floor windows on this facade."),
    ("North", "window", ["F2:W_N1", "F2:W_N2"], chain([1000, 1800, 800], 3.0, 1),
     "North_view.png upper-storey chain read upward from the 3000 floor line: 1000/1800/800 = 3600; "
     "the 1800 segment spans both upper windows on this facade."),
    ("South", "window", ["F1:W_S2", "F1:W_S3"], chain([1000, 1600, 400], 0.0, 1),
     "South_view.png right-side ground-storey chain read upward from the ground: 1000/1600/400; it measures the "
     "two large ground-floor windows (2400 wide) whose frames span exactly that segment."),
    ("South", "window", ["F1:W_S1"], chain([1500, 600, 900], 0.0, 1),
     "South_view.png left-side ground-storey chain read upward from the ground: 1500/600/900 = 3000; the 600 "
     "segment is the small 1200-wide window's own frame. Order checked from the ground line, not from the slab."),
    ("South", "opening", ["F1:D_S"], chain([2100, 900], 0.0, 0),
     "South_view.png left-side chain 1500/600/900 from the ground: the entrance door's head line is level with the "
     "small window head, so the door spans the first two segments (1500+600 = 2100) from the ground."),
    ("South", "window", ["F2:W_S1", "F2:W_S2", "F2:W_S3", "F2:W_S4"], chain([1000, 1800, 800], 3.0, 1),
     "South_view.png upper-storey chain from the 3000 floor line: 1000/1800/800; spans all four upper windows."),
    ("East", "window", ["F1:W_E"], chain([1000, 1800, 200], 0.0, 1),
     "East_view.png ground-storey chain read upward from the ground: 1000/1800/200 = 3000; this facade's own "
     "window is 1800 tall, unlike the 1600 windows on the north and south facades."),
    ("East", "window", ["F2:W_E"], chain([1000, 1800, 800], 3.0, 1),
     "East_view.png upper-storey chain from the 3000 floor line: 1000/1800/800."),
    ("West", "window", ["F2:W_W"], chain([1000, 1800, 800], 3.0, 1),
     "West_view.png upper-storey chain from the 3000 floor line: 1000/1800/800."),
]
WEST_DOOR = ("West", "opening", ["F1:D_W"], {"type": "literal", "value": [0.0, 2.1], "unit": "m"},
             "West_view.png gives no height dimension for the double door. Its outer frame spans y 440-561 px "
             "against the 3000 floor line at y 388 (173 px = 3.0 m), i.e. 2.098 m, rounded to 2.1 m, equal to the "
             "dimensioned 2100 south entrance door head.")


def requests():
    out = []
    for facade, kind, ids, value, reason in CLAIMS + [WEST_DOOR]:
        basis = "pixels" if value["type"] == "literal" else "annotation_and_pixels"
        claim = {"candidate": CANDIDATE, "objects": [{"kind": kind, "id": i} for i in ids], "basis": basis,
                 "reason": reason, "sources": [{"view_id": VIEWS[facade]}], "values": {"height": value},
                 "observation_mode": "direct", "unresolved": []}
        out.append({"tool": "record_claim", "arguments": {"claim_json": json.dumps(claim)}})
    return out


def adopt_and_confirm(claim_ids):
    out = [{"tool": "decide_claim", "arguments": {"claim_id": cid, "disposition": "adopted",
            "reason": "Transcribed from this facade's own elevation chain; matches the drafted values."}}
           for cid in claim_ids]
    operations = []
    for cid, (_, kind, ids, _, _) in zip(claim_ids, CLAIMS + [WEST_DOOR]):
        for i in ids:
            op = "update_window" if kind == "window" else "update_opening"
            operations.append({"op": op, "id": i, "changes": {"z": {"claim": cid, "value": "height"}},
                               "reason": "Confirm the drafted height against this facade's elevation evidence"})
    out.append({"tool": "confirm_claims", "arguments": {"candidate": CANDIDATE, "operations_json": json.dumps(operations)}})
    return out


if __name__ == "__main__":
    step = sys.argv[2] if len(sys.argv) > 2 else "record"
    data = requests() if step == "record" else adopt_and_confirm(sys.argv[3].split(","))
    path = RUN / "dev_inputs" / f"req_claims_{step}.json"
    path.write_text(json.dumps(data, ensure_ascii=False))
    print(path, len(data))
