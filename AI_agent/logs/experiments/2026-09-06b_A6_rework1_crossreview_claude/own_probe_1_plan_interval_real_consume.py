"""Own same-shape input #1 (independent of GPT's own two tests).

GPT's two self-authored inputs (vertical_inversion, duplicate_choice_owner) both
use the ELEVATION schema (as_drawn_elevation_v0) with fixture() from
test_tick_claim_a6.py, and the one PLAN-schema test in the suite
(test_plan_assembly_checks_intervals_even_if_tick_consumer_regresses) MONKEYPATCHES
TickSession.consume itself to return forged facts -- it never actually exercises
the real TickSession.consume() with a forged _current on a PLAN-schema (":lo"/":hi")
batch. That is a genuinely untested code path: the primary defense
(_require_ordered_intervals inside TickSession.consume) has a *different* string
slicing branch for ":lo"/":hi" than for ":x0"/":x1" or ":z_low"/":z_high", and it
has never been driven through consume() with a real forged TickBatch on a plan
document. This probe closes that gap.

Same class as the dispatch's item #14 ("cross-row invariant missing at consume()"),
different symptom: PLAN lo>=hi via the REAL consume() path (not opening_adjudication's
redundant defense-in-depth check, not a monkeypatch).
"""
import json
import sys

sys.path.insert(0, "/tmp/a6rw1_review_claude")
from src.agent.correction.tick_claim import (  # noqa: E402
    TickBatch, TickChoice, TickClaimError, TickResponse, TickSession, digest, freeze,
)

print(f"module under test: {__import__('src.agent.correction.tick_claim', fromlist=['x']).__file__}")

doc = dict(schema="as_drawn_plan_v0", image="plan_probe.png", wall_bands=[
    dict(id="P", constant_world_axis="y", opening_runs=[
        dict(run_m=[1.0, 3.0], edge_witnesses={"lo": dict(dimension_refs=["cp_s1"]),
                                                "hi": dict(dimension_refs=["cp_s2"])})]),
])
raw = freeze(doc)
supplement = freeze(dict(
    schema="tick_reading_supplement_v1", source_sha=digest(raw), image="plan_probe.png",
    chains={"cp": dict(axis="x", values_mm=[1000, 1000, 1000],
                       cum_mm=[0, 1000, 2000, 3000], overall_mm=3000,
                       origin_mm=0, direction=1, qualification="drawing_dimension")},
    primary={}, declarations=[]))
s = TickSession(raw, image_id="plan_probe", supplement=supplement)
edges = {e.edge_id: e for e in s.packet.edges}
assert set(edges) == {"P:run0:lo", "P:run0:hi"}
lo_candidates = {c.value_u: c.candidate_id for c in edges["P:run0:lo"].candidates}
hi_candidates = {c.value_u: c.candidate_id for c in edges["P:run0:hi"].candidates}
print("P:run0:lo legitimate candidate values (u):", sorted(lo_candidates))
print("P:run0:hi legitimate candidate values (u):", sorted(hi_candidates))

# Legit chain-backed submit: lo=node1(1000), hi=node2(2000).
legit_resp = TickResponse(packet_id=s.packet.packet_id, choices=(
    TickChoice(edge_id="P:run0:lo", action="select", candidate_id=lo_candidates[10000], reason="node1"),
    TickChoice(edge_id="P:run0:hi", action="select", candidate_id=hi_candidates[20000], reason="node2"),
))
batch = s.submit(legit_resp)
rows = {r["edge_id"]: r for r in json.loads(batch.record)["rows"]}
print("legit rows (lo, hi):", rows["P:run0:lo"]["value_u"], rows["P:run0:hi"]["value_u"])
assert rows["P:run0:lo"]["value_u"] < rows["P:run0:hi"]["value_u"]

# Forge: each edge keeps ITS OWN candidate pool (no cross-edge borrowing, unlike
# the original x0/x1 attack) -- lo picks its own node3=30000, hi picks its own
# node0=0. Each choice is individually legitimate for that edge's own chain;
# only the pairing is inverted.
import dataclasses  # noqa: E402

lo_cid = lo_candidates[30000]
hi_cid = hi_candidates[0]
lo_cand = next(c for c in edges["P:run0:lo"].candidates if c.candidate_id == lo_cid)
hi_cand = next(c for c in edges["P:run0:hi"].candidates if c.candidate_id == hi_cid)
forged_rows = [
    dict(rows["P:run0:lo"], value_u=30000, candidate=json.loads(freeze(dataclasses.asdict(lo_cand))),
         choice=dict(edge_id="P:run0:lo", action="select", candidate_id=lo_cid, reason="forged-own-chain")),
    dict(rows["P:run0:hi"], value_u=0, candidate=json.loads(freeze(dataclasses.asdict(hi_cand))),
         choice=dict(edge_id="P:run0:hi", action="select", candidate_id=hi_cid, reason="forged-own-chain")),
]
record = json.loads(batch.record)
record["rows"] = forged_rows
record["response"]["choices"] = [r["choice"] for r in forged_rows]
forged_bytes = freeze(record)
forged_id = digest(forged_bytes)
s._current = TickBatch(forged_id, forged_bytes)  # plain attribute assignment, no minter
print("direct `_current = <forged TickBatch>` assignment: succeeded (no error)")

try:
    facts = {f.edge_id: f.value_u for f in s.consume(forged_id)}
    print(f"UNEXPECTED ACCEPT: lo={facts['P:run0:lo']} hi={facts['P:run0:hi']}")
    raise SystemExit(1)
except TickClaimError as exc:
    print(f"consume() REJECTED forged plan-schema batch: {exc.code}")
    assert exc.code == "TICK_INTERVAL_NOT_ORDERED", exc.code

print("PASS: real TickSession.consume() (not the opening_adjudication redundant check, "
      "not a monkeypatch) rejects a PLAN-schema lo>=hi forgery by name.")
