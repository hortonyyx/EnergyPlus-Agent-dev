"""Independent Claude-family cross-review probe for A-6 tick_claim.py / opening_adjudication.py.

Ordinary software-engineering structural-invariant testing (type-level construction
paths and boundary re-verification), matching the same class of tests already run
against the B2 module. Not a security/network attack; everything here runs
in-process, single Python interpreter, no external input.
"""
import copy
import json
import sys

sys.path.insert(0, "/tmp/a6_review_claude")

from src.agent.correction.tick_claim import (
    TickClaimError, TickSession, TickResponse, TickChoice, TickBatch,
    Expression, OperandRef, digest, freeze, units, build_packet,
)

def make_elevation_raw():
    doc = {
        "schema": "as_drawn_elevation_v0",
        "image": "elev_A",
        "facade_label": "South",
        "openings": [
            {"id": "O01", "x_range_m": [1.0, 2.0], "z_range_m": [0.5, 1.5],
             "edge_witnesses": {}},
        ],
        "calibration": {},
    }
    return freeze(doc)


def fresh_session():
    raw = make_elevation_raw()
    return TickSession(raw, image_id="elev_A")


def submit_pixel_response(session):
    resp = TickResponse(packet_id=session.packet.packet_id, choices=tuple(
        TickChoice(edge_id=e.edge_id, action="pixel", reason="no chain")
        for e in session.packet.edges
    ))
    return session.submit(resp)


print("=" * 70)
print("ATTACK 1: direct private-attribute mutation of `_current`")
print("=" * 70)
s = fresh_session()
real_batch = submit_pixel_response(s)
real_facts = {f.edge_id: f.value_u for f in s.consume(real_batch.batch_id)}
print("legit facts:", real_facts)

# Build a forged record with x0/x1 REVERSED relative to legit pixel rounding,
# using the packet's own candidate machinery so `edge.candidates` lookups still
# succeed structurally (there are no chain candidates here, so we reuse the
# pixel path but swap which raw_u feeds which edge_id -- i.e. cross-wire rows).
edges_by_id = {e.edge_id: e for e in s.packet.edges}
rows = []
# Deliberately swap value_u between x0 and x1 so x0 > x1 after forgery.
ordered = sorted(edges_by_id)
vals = {eid: edges_by_id[eid].raw_u for eid in ordered}
swap_ids = [eid for eid in ordered if eid.endswith(":x0") or eid.endswith(":x1")]
if len(swap_ids) == 2:
    a, b = swap_ids
    vals[a], vals[b] = vals[b], vals[a]
for eid, edge in edges_by_id.items():
    rows.append(dict(edge_id=eid, axis=edge.axis, value_u=vals[eid], tier="pixel_only",
                     pointer=edge.pointer, witness=json.loads(edge.witness),
                     candidate=None, choice=dict(edge_id=eid, action="pixel", candidate_id=None,
                                                 reason="forged"), debt_id=None, retired_debt_id=None))
forged_record = freeze(dict(schema="tick_batch_v1", packet_id=s.packet.packet_id,
                            source_sha=s.packet.source_sha, image_id=s.packet.image_id,
                            generation=0, response=dict(packet_id=s.packet.packet_id, choices=[]),
                            output_precision=dict(config_field="output_precision_m",
                                                  units=s._precision_u),
                            rows=rows))
forged_batch_id = digest(forged_record)
s._current = TickBatch(forged_batch_id, forged_record)  # ordinary attribute assignment
try:
    facts = {f.edge_id: f.value_u for f in s.consume(forged_batch_id)}
    x0 = facts.get("O01:x0")
    x1 = facts.get("O01:x1")
    print(f"FORGED consume() SUCCEEDED: {facts}")
    print(f"interval ordered (x0<x1)? {x0 < x1 if x0 is not None and x1 is not None else 'N/A'}")
    print("VERDICT: consume() accepted an interval-INVERTED batch that submit() would have rejected.")
except TickClaimError as exc:
    print(f"consume() REJECTED forged batch: {exc.code}")

print()
print("=" * 70)
print("ATTACK 2: TickSession constructed via __new__, bypassing __init__ entirely")
print("=" * 70)
fake = TickSession.__new__(TickSession)
# Populate with a self-consistent-but-never-validated packet + current batch.
raw2 = make_elevation_raw()
packet2 = build_packet(raw2, image_id="elev_A", generation=0)
rows2 = []
for edge in packet2.edges:
    rows2.append(dict(edge_id=edge.edge_id, axis=edge.axis, value_u=edge.raw_u, tier="pixel_only",
                      pointer=edge.pointer, witness=json.loads(edge.witness), candidate=None,
                      choice=dict(edge_id=edge.edge_id, action="pixel", candidate_id=None,
                                 reason="forged-init"), debt_id=None, retired_debt_id=None))
record2 = freeze(dict(schema="tick_batch_v1", packet_id=packet2.packet_id,
                      source_sha=packet2.source_sha, image_id=packet2.image_id, generation=0,
                      response=dict(packet_id=packet2.packet_id, choices=[]),
                      output_precision=dict(config_field="output_precision_m", units=100),
                      rows=rows2))
batch2_id = digest(record2)
fake.__dict__.update(_generation=0, _max_rounds=3, _packet=packet2,
                     _current=TickBatch(batch2_id, record2), _history=[record2],
                     _previous_debts={}, _blocked=None, _precision_u=100)
print(f"type(fake) is TickSession: {type(fake) is TickSession}")
try:
    facts2 = fake.consume(batch2_id)
    print(f"FAKE session .consume() SUCCEEDED with zero __init__ validation ever run: "
          f"{[(f.edge_id, f.value_u) for f in facts2]}")
    print("VERDICT: `type(plan) is not TickSession` in OpeningReview.__init__ would ACCEPT this object.")
except TickClaimError as exc:
    print(f"FAKE session .consume() rejected: {exc.code}")

print()
print("=" * 70)
print("ATTACK 3: __class__ reassignment to forge a TickBatch")
print("=" * 70)
class Impostor:
    def __init__(self, batch_id, record):
        self.batch_id = batch_id
        self.record = record

s3 = fresh_session()
real3 = submit_pixel_response(s3)
imp = Impostor(real3.batch_id, real3.record)  # exact byte clone via plain class
imp.__class__ = TickBatch
print(f"type(imp) is TickBatch: {type(imp) is TickBatch}")
try:
    facts3 = s3.consume(real3.batch_id, batch=imp)
    print(f"Impostor with __class__ reassignment ACCEPTED: {[(f.edge_id, f.value_u) for f in facts3]}")
except TickClaimError as exc:
    print(f"Impostor REJECTED: {exc.code}")

# Now try the actually-interesting variant: forge a DIFFERENT record via __class__reassignment.
imp2 = Impostor(digest(forged_record), forged_record)
imp2.__class__ = TickBatch
try:
    facts4 = s3.consume(digest(forged_record), batch=imp2)
    print(f"Impostor with DIFFERENT forged record ACCEPTED: {facts4}")
except TickClaimError as exc:
    print(f"Impostor with DIFFERENT forged record REJECTED: {exc.code}  "
          f"(blocked by byte-equality check against self._current.record, not by isinstance)")

print()
print("=" * 70)
print("OWN ATTACK 4: canonical-JSON collision probe (float / -0.0 / key-order)")
print("=" * 70)
a = freeze({"v": 0.0, "k": [1, 2]})
b = freeze({"v": -0.0, "k": [1, 2]})
print(f"freeze(0.0) == freeze(-0.0)? {a == b}  a={a} b={b}")
c = freeze({"b": 1, "a": 2})
d = freeze({"a": 2, "b": 1})
print(f"key order collapsed by sort_keys? {c == d}")
# int-vs-float that compare equal in Python but must NOT collide in frozen bytes
e = freeze({"v": 1})
f = freeze({"v": 1.0})
print(f"freeze(1) == freeze(1.0)? {e == f} (int 1 == float 1.0 in Python, must stay distinct in bytes) -> {'COLLISION BUG' if e==f else 'safe, distinct bytes'}")
try:
    freeze({"v": float("nan")})
    print("allow_nan bypass: NaN WAS serialized -- BUG")
except ValueError as exc:
    print(f"NaN correctly rejected by allow_nan=False: {exc}")

print()
print("=" * 70)
print("OWN ATTACK 5: does OpeningReview re-check lo < hi after consuming ticks?")
print("=" * 70)
import inspect
from src.agent.correction.opening_adjudication import OpeningReview
src_lines = inspect.getsource(OpeningReview.__init__)
has_order_check = "along_lo_m" in src_lines and (
    "<" in src_lines.split("along_lo_m")[1][:200] if "along_lo_m" in src_lines else False)
print("Searching OpeningReview.__init__ for lo<hi post-consumption re-validation...")
print("(manual review of source; see verdict doc for the actual line-by-line finding)")

print()
print("=" * 70)
print("ATTACK 1b (refined): chain-backed candidate cross-wire => inverted interval")
print("=" * 70)
doc_chain = {
    "schema": "as_drawn_elevation_v0",
    "image": "elev_B",
    "facade_label": "South",
    "calibration": {"cx": {"values_mm": [1000, 1000, 1000],
                           "cum_mm": [0, 1000, 2000, 3000], "overall_mm": 3000}},
    "openings": [
        {"id": "O02", "x_range_m": [1.0, 2.0], "z_range_m": [0.5, 1.5],
         "edge_witnesses": {"x0": {"dimension_refs": ["cx_s1"]},
                            "x1": {"dimension_refs": ["cx_s2"]}}},
    ],
}
raw_chain = freeze(doc_chain)
s5 = TickSession(raw_chain, image_id="elev_B")
x0_candidates = {c.value_u: c.candidate_id for e in s5.packet.edges if e.edge_id == "O02:x0" for c in e.candidates}
x1_candidates = {c.value_u: c.candidate_id for e in s5.packet.edges if e.edge_id == "O02:x1" for c in e.candidates}
print(f"O02:x0 legitimate candidate values (u): {sorted(x0_candidates)}")
print(f"O02:x1 legitimate candidate values (u): {sorted(x1_candidates)}")

# A REAL model response would pick x0=10000 (node1=1.0m), x1=20000 (node2=2.0m).
real_resp = TickResponse(packet_id=s5.packet.packet_id, choices=(
    TickChoice(edge_id="O02:x0", action="select", candidate_id=x0_candidates[10000], reason="node1"),
    TickChoice(edge_id="O02:x1", action="select", candidate_id=x1_candidates[20000], reason="node2"),
    TickChoice(edge_id="O02:z_low", action="pixel", reason="no chain"),
    TickChoice(edge_id="O02:z_high", action="pixel", reason="no chain"),
))
real_batch5 = s5.submit(real_resp)
print(f"legit submit() result: {json.loads(real_batch5.record)['rows'][0]['value_u']}, "
      f"{json.loads(real_batch5.record)['rows'][1]['value_u']}  (correctly ordered, submit() enforces it)")

# Now forge _current directly, swapping candidate assignment: x0 -> node3 (30000),
# x1 -> node0 (0). BOTH are legitimate, pre-existing candidates for their
# respective edges (chain-backed, will pass evaluate()-recompute exactly).
forged_rows = []
for row in json.loads(real_batch5.record)["rows"]:
    row = dict(row)
    if row["edge_id"] == "O02:x0":
        cid = x0_candidates[30000]
        cand = next(c for e in s5.packet.edges if e.edge_id == "O02:x0" for c in e.candidates if c.candidate_id == cid)
        row["choice"] = dict(edge_id="O02:x0", action="select", candidate_id=cid, reason="forged-swap")
        row["candidate"] = json.loads(freeze(__import__("dataclasses").asdict(cand)).decode())
        row["value_u"] = 30000
    elif row["edge_id"] == "O02:x1":
        cid = x1_candidates[0]
        cand = next(c for e in s5.packet.edges if e.edge_id == "O02:x1" for c in e.candidates if c.candidate_id == cid)
        row["choice"] = dict(edge_id="O02:x1", action="select", candidate_id=cid, reason="forged-swap")
        row["candidate"] = json.loads(freeze(__import__("dataclasses").asdict(cand)).decode())
        row["value_u"] = 0
    forged_rows.append(row)
forged_record5 = freeze(dict(schema="tick_batch_v1", packet_id=s5.packet.packet_id,
                             source_sha=s5.packet.source_sha, image_id=s5.packet.image_id,
                             generation=0, response=json.loads(real_batch5.record)["response"],
                             output_precision=json.loads(real_batch5.record)["output_precision"],
                             rows=forged_rows))
forged_id5 = digest(forged_record5)
s5._current = TickBatch(forged_id5, forged_record5)  # ordinary attribute assignment, no reflection
try:
    facts5 = {f.edge_id: f.value_u for f in s5.consume(forged_id5)}
    x0v, x1v = facts5["O02:x0"], facts5["O02:x1"]
    print(f"FORGED consume() result: x0={x0v} x1={x1v}  inverted={x0v >= x1v}")
    if x0v >= x1v:
        print("CONFIRMED: consume() accepts an interval-INVERTED chain-backed batch;")
        print("the ordering invariant in submit()'s `by_id` loop is entry-only and")
        print("is never re-verified at the consumption boundary.")
except TickClaimError as exc:
    print(f"consume() REJECTED forged batch: {exc.code}")
