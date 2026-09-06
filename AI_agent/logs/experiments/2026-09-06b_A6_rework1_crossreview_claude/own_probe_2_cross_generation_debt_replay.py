"""Own same-shape input #2: cross-generation double-retirement replay.

Targets item #17 specifically (retired_debt_id bookkeeping), which GPT's own
test suite covers only with a SINGLE round-trip (debt created at gen0, retired
at gen1, then idempotent re-consume + a THIRD gen with no debt at all). It never
attempts to resurrect a debt that was legitimately retired in an EARLIER
generation by forging it into a LATER, unrelated commit's row.

This is "same class, different mechanism" from GPT's own probe (which forges a
single row inside the SAME batch); mine forges retired_debt_id across generation
boundaries, directly exercising the boundary condition of _retirement_context's
history replay: `if raw == current_record: break`.

Sequence:
  gen0: edge A submitted as pixel_pending_evidence -> debt D created.
  reconsider() -> gen1, D now pending in _previous_debts.
  gen1: edge A submitted chain-backed (supplement now supplies the chain) -> D
        legitimately retires. _previous_debts == {} after this commit (batch1).
  reconsider() -> gen2 (unrelated re-review, no new debt).
  gen2: edge A submitted chain-backed again (same chain) -> batch2, with NO
        retirement (D was already retired in batch1's history).
  ATTACK: forge batch2's row for A to falsely claim retired_debt_id = D (the
  debt already legitimately closed out in batch1). If consume() used the LIVE
  post-commit _previous_debts map (empty at this point) as GPT's own submit()
  logic does, this specific forgery wouldn't even need _retirement_context to
  be exercised differently from a "no debt" case -- so instead we independently
  verify GPT's causal claim in isolation: monkeypatch _retirement_context to
  return the raw live self._previous_debts (the "naive" implementation) and
  show THAT breaks a genuinely legitimate consume() of batch1 itself (the
  retirement commit), which is the scenario GPT's rationale actually describes.
"""
import json
import sys

sys.path.insert(0, "/tmp/a6rw1_review_claude")
from src.agent.correction.tick_claim import (  # noqa: E402
    TickBatch, TickChoice, TickClaimError, TickResponse, TickSession, digest, freeze,
)

print(f"module under test: {__import__('src.agent.correction.tick_claim', fromlist=['x']).__file__}")


def build_session():
    doc = dict(schema="as_drawn_elevation_v0", image="debt_probe.png", facade_label="South",
              calibration={}, openings=[
                  dict(id="A", x_range_m=[1.0, 2.0], z_range_m=[0.5, 1.5],
                       edge_witnesses={"x0": dict(dimension_refs=["cx_s1"])}),
              ])
    raw = freeze(doc)
    s = TickSession(raw, image_id="debt_probe")
    return s


print("=" * 70)
print("Part 1: forge retired_debt_id across a generation boundary")
print("=" * 70)

s = build_session()
edge = next(e for e in s.packet.edges if e.edge_id == "A:x0")
assert edge.missing_chains, "expected A:x0 to have a missing chain so pixel_pending_evidence is legal"

# gen0: pixel_pending_evidence on A:x0 (and pixel on the rest) -> creates debt D.
resp0 = TickResponse(packet_id=s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="pixel_pending_evidence" if e.edge_id == "A:x0" else "pixel",
              reason="await chain") for e in s.packet.edges))
batch0 = s.submit(resp0)
debt_id = next(r["debt_id"] for r in json.loads(batch0.record)["rows"] if r["edge_id"] == "A:x0")
print(f"gen0 debt_id for A:x0: {debt_id}")
assert debt_id

# reconsider -> gen1, supply the missing chain now.
doc1 = json.loads(s.packet.source_bytes)
supplement1 = freeze(dict(schema="tick_reading_supplement_v1", source_sha=digest(s.packet.source_bytes),
                          image="debt_probe.png",
                          chains={"cx": dict(axis="x", values_mm=[1000, 1000], cum_mm=[0, 1000, 2000],
                                             overall_mm=2000, origin_mm=0, direction=1,
                                             qualification="drawing_dimension")},
                          primary={}, declarations=[]))
s.reconsider("supplement arrived", supplement=supplement1)
edge1 = next(e for e in s.packet.edges if e.edge_id == "A:x0")
assert not edge1.missing_chains
node0_cid = next(c.candidate_id for c in edge1.candidates if c.value_u == 0)

resp1 = TickResponse(packet_id=s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="select" if e.edge_id == "A:x0" else "pixel",
              candidate_id=node0_cid if e.edge_id == "A:x0" else None,
              reason="chain now available") for e in s.packet.edges))
batch1 = s.submit(resp1)
row1 = next(r for r in json.loads(batch1.record)["rows"] if r["edge_id"] == "A:x0")
print(f"gen1 A:x0 retired_debt_id: {row1['retired_debt_id']}  (should equal gen0 debt: {row1['retired_debt_id'] == debt_id})")
assert row1["retired_debt_id"] == debt_id
assert s._previous_debts == {}, "debt should be fully retired after batch1"

# reconsider -> gen2, unrelated re-review, no debt involved this time.
s.reconsider("routine re-review")
resp2 = TickResponse(packet_id=s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="select" if e.edge_id == "A:x0" else "pixel",
              candidate_id=node0_cid if e.edge_id == "A:x0" else None,
              reason="same decision again") for e in s.packet.edges))
batch2 = s.submit(resp2)
row2 = next(r for r in json.loads(batch2.record)["rows"] if r["edge_id"] == "A:x0")
print(f"gen2 A:x0 retired_debt_id (legit, should be None): {row2['retired_debt_id']}")
assert row2["retired_debt_id"] is None

# ATTACK: forge batch2 to claim it ALSO retires the already-closed gen0 debt.
record2 = json.loads(batch2.record)
for row in record2["rows"]:
    if row["edge_id"] == "A:x0":
        row["retired_debt_id"] = debt_id
record2["response"]["choices"] = [r["choice"] for r in record2["rows"]]
forged_bytes = freeze(record2)
forged_id = digest(forged_bytes)
s._current = TickBatch(forged_id, forged_bytes)
try:
    s.consume(forged_id)
    print("UNEXPECTED ACCEPT: double-retirement forgery was NOT caught")
    raise SystemExit(1)
except TickClaimError as exc:
    print(f"consume() REJECTED double-retirement-across-generations forgery: {exc.code}")
    assert exc.code == "TICK_ROW_RECOMPUTE_MISMATCH", exc.code

print()
print("=" * 70)
print("Part 2: falsify/verify GPT's claim about the post-commit map directly")
print("=" * 70)
print("Claim (execution doc item #17): 'if consume() replayed the already-popped")
print("post-commit _previous_debts map instead of _retirement_context, it would")
print("wrongly reject a LEGITIMATE retirement'. Testing this by monkeypatching")
print("_retirement_context to return the live self._previous_debts instead.")

s2 = build_session()
resp0 = TickResponse(packet_id=s2.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="pixel_pending_evidence" if e.edge_id == "A:x0" else "pixel",
              reason="await chain") for e in s2.packet.edges))
batch0b = s2.submit(resp0)
s2.reconsider("supplement arrived", supplement=supplement1)
edge1b = next(e for e in s2.packet.edges if e.edge_id == "A:x0")
node0_cid_b = next(c.candidate_id for c in edge1b.candidates if c.value_u == 0)
resp1 = TickResponse(packet_id=s2.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action="select" if e.edge_id == "A:x0" else "pixel",
              candidate_id=node0_cid_b if e.edge_id == "A:x0" else None,
              reason="chain now available") for e in s2.packet.edges))
batch1b = s2.submit(resp1)  # THIS is the batch that legitimately retires the debt.
print(f"legit batch1b retired_debt_id present: "
      f"{any(r['retired_debt_id'] for r in json.loads(batch1b.record)['rows'])}")
assert s2._previous_debts == {}, "post-commit map is now empty -- debt already popped"

# Monkeypatch consume's retirement lookup to the NAIVE (post-commit map) version.
original_method = TickSession._retirement_context
TickSession._retirement_context = lambda self, current_record: dict(self._previous_debts)
try:
    try:
        s2.consume(batch1b.batch_id)
        print("naive post-commit-map consume(): ACCEPTED (unexpected)")
        naive_outcome = "ACCEPTED"
    except TickClaimError as exc:
        print(f"naive post-commit-map consume(): REJECTED {exc.code}  <-- false rejection of a LEGITIMATE batch")
        naive_outcome = f"REJECTED {exc.code}"
finally:
    TickSession._retirement_context = original_method

# Now confirm the REAL (shipped) implementation accepts the same legitimate batch.
real_facts = s2.consume(batch1b.batch_id)
print(f"real _retirement_context consume(): ACCEPTED, {len(real_facts)} facts")

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"naive (post-commit map) outcome on a LEGITIMATE retiring batch: {naive_outcome}")
print("real (_retirement_context replay) outcome on the same batch: ACCEPTED")
assert naive_outcome.startswith("REJECTED"), \
    "expected the naive post-commit-map approach to falsely reject the legitimate retirement"
print("PASS: GPT's claim is CONFIRMED BY DIRECT SUBSTITUTION -- the naive approach")
print("really does misfire on this exact legitimate batch; _retirement_context is not")
print("cosmetic, and the cross-generation double-retirement forgery is independently caught.")
