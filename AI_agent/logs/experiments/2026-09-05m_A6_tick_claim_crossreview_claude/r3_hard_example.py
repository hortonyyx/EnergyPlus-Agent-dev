import sys
sys.path.insert(0, "/tmp/a6_review_claude")
from src.agent.correction.tick_claim import (
    TickClaimError, Expression, OperandRef, digest, freeze, evaluate,
)
raw = freeze(dict(schema='as_drawn_elevation_v0', image='r3.png', facade_label='South',
                  calibration={}, openings=[dict(id='O', x_range_m=[1.6, 4.3], z_range_m=[0, 1],
                  edge_witnesses={})]))
sup = freeze(dict(schema='tick_reading_supplement_v1', source_sha=digest(raw), image='r3.png',
                  chains={'P': dict(values_mm=[1600, 2700, 3200], cum_mm=[0, 1600, 4300, 7500],
                                    overall_mm=7500, axis='x', origin_mm=0, direction=1,
                                    qualification='drawing_dimension')},
                  primary={}, declarations=[]))
anchor = OperandRef(digest(raw), 'P', 'node', 0)

print("Correctly-shaped hard example: node1 + node2 (domain='node') fed into anchored_sum")
bad_expr = Expression('anchored_sum', anchor, (
    OperandRef(digest(raw), 'P', 'node', 1), OperandRef(digest(raw), 'P', 'node', 2)))
try:
    v = evaluate(bad_expr, raw=raw, supplement=sup, axis='x')
    print(f"UNEXPECTED: evaluate() returned {v} (should reject node-as-segment: 1600+4300=5900)")
except TickClaimError as exc:
    print(f"evaluate() REJECTED as designed: {exc.code} (would have produced {1600+4300}=5900 if allowed)")

good_expr = Expression('anchored_sum', anchor, (
    OperandRef(digest(raw), 'P', 'segment', 0), OperandRef(digest(raw), 'P', 'segment', 1)))
v2 = evaluate(good_expr, raw=raw, supplement=sup, axis='x')
print(f"Legit segment0+segment1 sum: {v2} units = {v2/10}mm (true value 4300mm)")
assert v2 == 43000
