"""Dispatch section 2 targeted checks for items #16 and #3.

#16: "no rename, no private minter, no type seal -- session._current = <forged
TickBatch> assignment should still work; content gets rejected at the output
gate." Verify BOTH halves: the assignment succeeds AND the forged content is
rejected, using a batch that is NOT interval-inverted (so we isolate this from
item #14's fix and specifically exercise the *other* full-row content checks).

#3: "current must not be already-decided" is submit-side; the corresponding
consume-side claim is that if `_current` gets corrupted by an ordinary bug
(not through submit()), the content full-check at the output still catches it,
rather than relying on any type/identity gate. Demonstrate this with a forged
TickBatch of the correct type placed directly onto `_current` (simulating "an
ordinary bug set _current outside submit()"), where the *type* is correct
(isinstance/type checks would all pass) but the *content* is wrong.
"""
import json
import sys

sys.path.insert(0, "/tmp/a6rw1_review_claude")
from src.agent.correction.tick_claim import (  # noqa: E402
    TickBatch, TickChoice, TickClaimError, TickResponse, TickSession, digest, freeze,
)

print(f"module under test: {__import__('src.agent.correction.tick_claim', fromlist=['x']).__file__}")

doc = dict(schema="as_drawn_elevation_v0", image="item16_probe.png", facade_label="South",
          calibration={}, openings=[
              dict(id="A", x_range_m=[1.0, 2.0], z_range_m=[0.5, 1.5], edge_witnesses={}),
          ])
raw = freeze(doc)
s = TickSession(raw, image_id="item16_probe")
batch = s.submit(TickResponse(packet_id=s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="pixel", reason="pixel tier") for e in s.packet.edges)))
print(f"legit batch committed: {batch.batch_id}")

record = json.loads(batch.record)
# Tamper with a non-interval field: flip one row's value_u to an arbitrary
# pixel-rounded-looking number that does NOT match a real recompute.
for row in record["rows"]:
    if row["edge_id"] == "A:z_low":
        row["value_u"] = row["value_u"] + 100000  # not interval-related; content-only forgery
record["response"] = record["response"]  # unchanged -- forged only in rows/derived record
forged_bytes = freeze(record)
forged_id = digest(forged_bytes)

print()
print("--- item #16: plain attribute assignment, no minter, no private constructor ---")
before_type_ok = isinstance(s._current, TickBatch)
s._current = TickBatch(forged_id, forged_bytes)  # ordinary Python assignment
after_type_ok = isinstance(s._current, TickBatch) and type(s._current) is TickBatch
print(f"assignment executed without raising: True")
print(f"isinstance(_current, TickBatch) before={before_type_ok} after={after_type_ok} "
      f"(type gate alone would ACCEPT this forgery)")
try:
    s.consume(forged_id)
    print("UNEXPECTED: forged content was accepted at output")
    raise SystemExit(1)
except TickClaimError as exc:
    print(f"consume() REJECTED at the CONTENT gate: {exc.code}")
    assert exc.code in ("TICK_ROW_RECOMPUTE_MISMATCH", "TICK_VALUE_RECOMPUTE_MISMATCH"), exc.code
print("CONFIRMED: the block is content-level (full-row recompute), not a type/identity seal --")
print("matches the docstring's own claim ('ordinary API encapsulation, not a defence against")
print("Python reflection'): reflection still WORKS, the numbers just don't survive.")

print()
print("--- item #3: current corrupted by an 'ordinary bug' outside submit(), correct type ---")
s2 = TickSession(raw, image_id="item16_probe_2")
legit2 = s2.submit(TickResponse(packet_id=s2.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="pixel", reason="pixel tier") for e in s2.packet.edges)))
# Simulate "an ordinary bug" restoring an unrelated, previously-valid-looking
# TickBatch onto _current without going through submit() -- e.g. a bad cache
# restore, or a stale object handed back from elsewhere. Type is exactly right.
stale_but_wrong_record = json.loads(legit2.record)
stale_but_wrong_record["source_sha"] = digest(b"totally different source bytes")
stale_bytes = freeze(stale_but_wrong_record)
stale_id = digest(stale_bytes)
s2._current = TickBatch(stale_id, stale_bytes)  # "ordinary bug", correct type, wrong content
try:
    s2.consume(stale_id)
    print("UNEXPECTED: stale/corrupted current was accepted")
    raise SystemExit(1)
except TickClaimError as exc:
    print(f"consume() REJECTED the corrupted-by-ordinary-bug current: {exc.code}")
    assert exc.code == "TICK_BATCH_SOURCE_MISMATCH", exc.code
print("CONFIRMED: item #3's consume-side counterpart holds -- a same-typed but wrong-content")
print("_current (as an ordinary bug, not a submit() call, would produce) is caught by the")
print("full content checks, not by any type gate (which would have passed it).")
