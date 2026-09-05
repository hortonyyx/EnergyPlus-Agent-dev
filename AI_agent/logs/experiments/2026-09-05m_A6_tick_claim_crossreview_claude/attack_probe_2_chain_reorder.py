import json, sys, dataclasses
sys.path.insert(0, "/tmp/a6_review_claude")
from src.agent.correction.tick_claim import (
    TickClaimError, TickSession, TickResponse, TickChoice, TickBatch, digest, freeze,
)

print("=" * 70)
print("ATTACK 1b (refined v2): chain-backed candidate cross-wire -> inverted interval")
print("=" * 70)
doc_chain = {
    "schema": "as_drawn_elevation_v0",
    "image": "elev_B",
    "facade_label": "South",
    "calibration": {},
    "openings": [
        {"id": "O02", "x_range_m": [1.0, 2.0], "z_range_m": [0.5, 1.5],
         "edge_witnesses": {"x0": {"dimension_refs": ["cx_s1"]},
                            "x1": {"dimension_refs": ["cx_s2"]}}},
    ],
}
raw_chain = freeze(doc_chain)
supplement = freeze(dict(
    schema="tick_reading_supplement_v1", source_sha=digest(raw_chain), image="elev_B",
    chains={"cx": dict(axis="x", values_mm=[1000, 1000, 1000],
                       cum_mm=[0, 1000, 2000, 3000], overall_mm=3000,
                       origin_mm=0, direction=1, qualification="drawing_dimension")},
    primary={}, declarations=[]))

s5 = TickSession(raw_chain, image_id="elev_B", supplement=supplement)
x0_candidates = {c.value_u: c.candidate_id for e in s5.packet.edges if e.edge_id == "O02:x0" for c in e.candidates}
x1_candidates = {c.value_u: c.candidate_id for e in s5.packet.edges if e.edge_id == "O02:x1" for c in e.candidates}
print(f"O02:x0 legitimate candidate values (u): {sorted(x0_candidates)}")
print(f"O02:x1 legitimate candidate values (u): {sorted(x1_candidates)}")

real_resp = TickResponse(packet_id=s5.packet.packet_id, choices=(
    TickChoice(edge_id="O02:x0", action="select", candidate_id=x0_candidates[10000], reason="node1"),
    TickChoice(edge_id="O02:x1", action="select", candidate_id=x1_candidates[20000], reason="node2"),
    TickChoice(edge_id="O02:z_low", action="pixel", reason="no chain"),
    TickChoice(edge_id="O02:z_high", action="pixel", reason="no chain"),
))
real_batch5 = s5.submit(real_resp)
legit_rows = json.loads(real_batch5.record)["rows"]
print("legit submit() rows (x0,x1):", [(r["edge_id"], r["value_u"]) for r in legit_rows if "x" in r["edge_id"]])

forged_rows = []
for row in legit_rows:
    row = dict(row)
    if row["edge_id"] == "O02:x0":
        cid = x0_candidates[30000]
        cand = next(c for e in s5.packet.edges if e.edge_id == "O02:x0" for c in e.candidates if c.candidate_id == cid)
        row["choice"] = dict(edge_id="O02:x0", action="select", candidate_id=cid, reason="forged-swap")
        row["candidate"] = json.loads(freeze(dataclasses.asdict(cand)).decode())
        row["value_u"] = 30000
    elif row["edge_id"] == "O02:x1":
        cid = x1_candidates[0]
        cand = next(c for e in s5.packet.edges if e.edge_id == "O02:x1" for c in e.candidates if c.candidate_id == cid)
        row["choice"] = dict(edge_id="O02:x1", action="select", candidate_id=cid, reason="forged-swap")
        row["candidate"] = json.loads(freeze(dataclasses.asdict(cand)).decode())
        row["value_u"] = 0
    forged_rows.append(row)

resp_dict = json.loads(real_batch5.record)["response"]
prec_dict = json.loads(real_batch5.record)["output_precision"]
forged_record5 = freeze(dict(schema="tick_batch_v1", packet_id=s5.packet.packet_id,
                             source_sha=s5.packet.source_sha, image_id=s5.packet.image_id,
                             generation=0, response=resp_dict, output_precision=prec_dict,
                             rows=forged_rows))
forged_id5 = digest(forged_record5)
s5._current = TickBatch(forged_id5, forged_record5)
try:
    facts5 = {f.edge_id: f.value_u for f in s5.consume(forged_id5)}
    x0v, x1v = facts5["O02:x0"], facts5["O02:x1"]
    print(f"FORGED consume() result: x0={x0v} x1={x1v}  inverted={x0v >= x1v}")
    if x0v >= x1v:
        print("CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch built")
        print("from two individually-legitimate, pre-existing candidates of each edge.")
        print("submit()'s `by_id` ordering loop (T:470-480) is entry-only; consume() (T:493)")
        print("never re-checks cross-edge ordering, only per-edge value recomputation.")
except TickClaimError as exc:
    print(f"consume() REJECTED forged batch: {exc.code}")

print()
print("=" * 70)
print("Downstream cascade check: does OpeningReview reject lo>=hi spans?")
print("=" * 70)
import re as _re
src = open("/tmp/a6_review_claude/src/agent/correction/opening_adjudication.py").read()
# Show the exact lines constructing self._plans[oid] from tick facts.
for i, line in enumerate(src.splitlines(), 1):
    if "along_lo_m" in line or "along_hi_m" in line:
        print(f"{i}: {line}")
