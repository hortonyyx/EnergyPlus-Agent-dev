import json, sys
sys.path.insert(0, "/tmp/a6_review_claude")
from src.agent.correction.tick_claim import (
    TickSession, TickResponse, TickChoice, TickClaimError, TickBatch, digest, freeze,
)
from src.agent.correction.opening_adjudication import (
    OpeningReview, PlanBinding, FacadeInput, SpatialResponse, OpeningChoice,
)
from src.agent.correction.projection_bridge import CutLineV1

print("=" * 70)
print("R-1 end-to-end: whole_building_review=return_to_step_one invalidates plan batch")
print("=" * 70)
plan_doc = dict(schema='as_drawn_plan_v0', image='plan1',
                wall_bands=[dict(id='B1', constant_world_axis='y',
                                 opening_runs=[dict(run_m=[1.0, 2.0], edge_witnesses={})])])
plan_raw = freeze(plan_doc)
plan_s = TickSession(plan_raw, image_id='plan1')
plan_resp = TickResponse(packet_id=plan_s.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action='pixel', reason='no chain') for e in plan_s.packet.edges))
plan_batch = plan_s.submit(plan_resp)
facts = {f.edge_id: f for f in plan_s.consume(plan_batch.batch_id)}
line = CutLineV1(origin_id='B1:run0', kind='opening', axis='x', pos_m=0.0,
                 half_thickness_m=0.1, along_lo_m=0.0, along_hi_m=0.0)
binding = PlanBinding('B1:run0', 'South', 'W1', 'R1', line, floor_origin_u=0)
walls = (CutLineV1(origin_id='W1', kind='wall', axis='x', pos_m=0.0,
                   half_thickness_m=0.1, along_lo_m=0.0, along_hi_m=100.0),)
facades = tuple(FacadeInput(fam, None, None) for fam in ('South', 'North', 'East', 'West'))
review = OpeningReview(plan=plan_s, expected_plan_batch_id=plan_batch.batch_id,
                       bindings=(binding,), facades=facades, walls=walls)
resp = SpatialResponse(packet_id=review.packet.packet_id, choices=(
    OpeningChoice(plan_opening_id='B1:run0', action='register', reason='no facade info'),),
    whole_building_review='return_to_step_one', reason='reading mis-scanned this run',
    reconsider_image_ids=('plan1',))
try:
    review.submit(resp)
    print("UNEXPECTED: submit() with return_to_step_one did not raise")
except TickClaimError as exc:
    print(f"submit() returns named exit: {exc.code}  detail={exc.detail}")
try:
    plan_s.consume(plan_batch.batch_id)
    print("BUG: old plan batch is STILL consumable after return_to_step_one")
except TickClaimError as exc:
    print(f"CONFIRMED: old plan batch invalidated -- consume() now raises {exc.code}")

print()
print("=" * 70)
print("R-4 end-to-end: replacing current with a batch from an INDEPENDENT session")
print("(same source bytes, freshly re-submitted) must be rejected")
print("=" * 70)
raw_common = freeze(dict(schema='as_drawn_elevation_v0', image='dup', facade_label='South',
                         calibration={}, openings=[dict(id='O', x_range_m=[1.0, 2.0],
                         z_range_m=[0, 1], edge_witnesses={})]))
sA = TickSession(raw_common, image_id='dup')
sB = TickSession(raw_common, image_id='dup')  # a second, independently-constructed session
respA = TickResponse(packet_id=sA.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action='pixel', reason='A') for e in sA.packet.edges))
respB = TickResponse(packet_id=sB.packet.packet_id, choices=tuple(
    TickChoice(edge_id=e.edge_id, action='pixel', reason='B') for e in sB.packet.edges))
batchA = sA.submit(respA)
batchB = sB.submit(respB)
print(f"same source bytes -> same packet_id? {sA.packet.packet_id == sB.packet.packet_id}")
print(f"same source bytes -> same batch_id (since content identical)? {batchA.batch_id == batchB.batch_id}")
# Try to consume sA's current using sB's batch object as the `batch=` param.
try:
    facts = sA.consume(batchA.batch_id, batch=batchB)
    print(f"Cross-session batch substitution ACCEPTED (expected if content byte-identical): {[(f.edge_id, f.value_u) for f in facts]}")
except TickClaimError as exc:
    print(f"Cross-session batch substitution REJECTED: {exc.code}")
