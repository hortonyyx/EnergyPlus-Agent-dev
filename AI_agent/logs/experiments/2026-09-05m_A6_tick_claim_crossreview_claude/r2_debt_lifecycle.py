import json, sys
sys.path.insert(0, "/tmp/a6_review_claude")
from src.agent.correction.tick_claim import (
    TickSession, TickResponse, TickChoice, Expression, OperandRef,
    TickClaimError, digest, freeze, evaluate,
)

print("=" * 70)
print("R-3 hard example: cum=[0,1600,4300,7500], segment_len via index 1/2 = 5900 vs true 4300")
print("=" * 70)
raw = freeze(dict(schema='as_drawn_elevation_v0', image='r3.png', facade_label='South',
                  calibration={}, openings=[dict(id='O', x_range_m=[1.6, 4.3], z_range_m=[0, 1],
                  edge_witnesses={})]))
sup = freeze(dict(schema='tick_reading_supplement_v1', source_sha=digest(raw), image='r3.png',
                  chains={'P': dict(values_mm=[1600, 2700, 3200], cum_mm=[0, 1600, 4300, 7500],
                                    overall_mm=7500, axis='x', origin_mm=0, direction=1,
                                    qualification='drawing_dimension')},
                  primary={}, declarations=[]))
anchor = OperandRef(digest(raw), 'P', 'node', 0)
# node1+node2 as "segment sum" -- forged contiguous segment refs at index 1,2
bad_expr = Expression('anchored_sum', anchor, (
    OperandRef(digest(raw), 'P', 'segment', 1), OperandRef(digest(raw), 'P', 'segment', 2)))
try:
    v = evaluate(bad_expr, raw=raw, supplement=sup, axis='x')
    print(f"UNEXPECTED: evaluate() returned {v} (should have been rejected)")
except TickClaimError as exc:
    print(f"evaluate() REJECTED as designed: {exc.code} (would have produced {1600+4300}=5900 if allowed)")

good_expr = Expression('anchored_sum', anchor, (
    OperandRef(digest(raw), 'P', 'segment', 0), OperandRef(digest(raw), 'P', 'segment', 1)))
v2 = evaluate(good_expr, raw=raw, supplement=sup, axis='x')
print(f"Legit segment0+segment1 sum: {v2} units = {v2/10}mm (true value 4300mm)")
assert v2 == 43000

print()
print("=" * 70)
print("R-2 hard example: TickSession's OWN debt tracking (obligation=None is the OLD B4 issue,")
print("not this module's path -- verify NEW module's retire logic independently)")
print("=" * 70)
raw2 = freeze(dict(schema='as_drawn_elevation_v0', image='r2.png', facade_label='South',
                   calibration={}, openings=[dict(id='O', x_range_m=[1.0, 2.0], z_range_m=[0, 1],
                   edge_witnesses={'x0': dict(dimension_refs=[], missing_chain_refs=['P'])})]))
# missing_chains logic comes from `named` vs `chains` mismatch in build_packet; use a
# witness that references an as-yet-unsupplied chain to trigger `missing`.
raw2b = freeze(dict(schema='as_drawn_elevation_v0', image='r2.png', facade_label='South',
                    calibration={}, openings=[dict(id='O', x_range_m=[1.0, 2.0], z_range_m=[0, 1],
                    edge_witnesses={'x0': dict(dimension_refs=['P_s1'])})]))
s = TickSession(raw2b, image_id='r2')
edge = next(e for e in s.packet.edges if e.edge_id == 'O:x0')
print(f"O:x0 missing_chains (no supplement supplied 'P'): {edge.missing_chains}")
resp = TickResponse(packet_id=s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id,
              action='pixel_pending_evidence' if e.edge_id == 'O:x0' else 'pixel',
              reason='awaiting supplement') for e in s.packet.edges))
batch1 = s.submit(resp)
row1 = next(r for r in json.loads(batch1.record)['rows'] if r['edge_id'] == 'O:x0')
print(f"debt_id after first submit: {row1['debt_id']}  tier: {row1['tier']}")
assert row1['debt_id'] is not None

# Now supply the missing chain via reconsider and select a chain-backed candidate.
sup2 = freeze(dict(schema='tick_reading_supplement_v1', source_sha=digest(raw2b), image='r2.png',
                   chains={'P': dict(values_mm=[1000, 1000], cum_mm=[0, 1000, 2000], overall_mm=2000,
                                     axis='x', origin_mm=0, direction=1, qualification='drawing_dimension')},
                   primary={}, declarations=[]))
s.reconsider('supplied missing chain P', supplement=sup2)
edge2 = next(e for e in s.packet.edges if e.edge_id == 'O:x0')
cand = next(c for c in edge2.candidates if c.expression.anchor.index == 1)
resp2 = TickResponse(packet_id=s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action='select' if e.edge_id == 'O:x0' else 'pixel',
              candidate_id=cand.candidate_id if e.edge_id == 'O:x0' else None,
              reason='resolved with new evidence') for e in s.packet.edges))
batch2 = s.submit(resp2)
row2 = next(r for r in json.loads(batch2.record)['rows'] if r['edge_id'] == 'O:x0')
print(f"After reconsider+select(chain_backed): retired_debt_id={row2['retired_debt_id']} == original debt {row1['debt_id']}? "
      f"{row2['retired_debt_id'] == row1['debt_id']}")
assert row2['retired_debt_id'] == row1['debt_id']
print("CONFIRMED: this module's OWN debt lifecycle (pixel_pending_evidence -> reconsider "
      "with supplement -> select chain_backed) actually retires the SAME debt_id it minted;")
print("this does NOT touch or depend on the legacy B4 obligation=None/assert_backed path at all.")
