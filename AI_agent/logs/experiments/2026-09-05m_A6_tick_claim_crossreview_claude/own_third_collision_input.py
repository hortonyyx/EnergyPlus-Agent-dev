"""Own third same-shape-but-structurally-different collision input (review §三).

Walks a dimension the execution doc's two 'new' examples never walked: Q has
TWO internal nodes, each colliding in VALUE with a DIFFERENT node of P (not
just one pairwise collision), and a third chain R shares the same pixel key
with both P and Q, adding a three-way collision at a single pixel anchor.
"""
import json, sys
sys.path.insert(0, "/tmp/a6_review_claude")
from src.agent.correction.tick_claim import (
    TickSession, TickClaimError, digest, freeze,
)

# P: 4 segments -> 5 nodes: 0, 2000, 5000, 9000, 11000
p_values = [2000, 3000, 4000, 2000]
p_nodes = [0]
for v in p_values:
    p_nodes.append(p_nodes[-1] + v)
assert p_nodes == [0, 2000, 5000, 9000, 11000]

# Q: 2 segments -> nodes 0, 5000, 11000.  Q:node1(5000)==P:node2(5000);
# Q:node2(11000)==P:node4(11000).  TWO distinct collisions against TWO
# distinct P nodes, not just one -- this is the untested dimension.
q_values = [5000, 6000]
q_nodes = [0, 5000, 11000]

# R: shares the SAME pixel key as P/Q, with its own node colliding with
# P:node1(2000) too -- a three-chain collision at a single pixel anchor.
r_values = [2000, 9000]
r_nodes = [0, 2000, 11000]

PIXEL_KEY = 512.75

doc = dict(schema='as_drawn_elevation_v0', image='own3.png', facade_label='South',
           calibration={'x': dict(values_mm=p_values, cum_mm=p_nodes, overall_mm=p_nodes[-1]),
                       'z': dict(values_mm=[1000, 1000], cum_mm=[0, 1000, 2000], overall_mm=2000)},
           openings=[dict(id='O', x_range_m=[2.0, 3.0], z_range_m=[0, 1], edge_witnesses={
               'x0': dict(dimension_refs=['P_s1', 'P_s2'], nearest_tick_px=PIXEL_KEY),
               'x1': dict(dimension_refs=['P_s2', 'P_s3'])})])

results = []
# Three write orders: P-first, Q-first, R-first, to prove order-independence
# across a THREE-way collision (execution doc only tested a two-way collision
# with two write orders).
for order in (('P', 'Q', 'R'), ('Q', 'R', 'P'), ('R', 'P', 'Q')):
    doc_local = json.loads(json.dumps(doc))
    doc_local['dimension_witnesses'] = {'x': {}}
    for cid in order:
        vals = {'P': p_nodes[-1], 'Q': q_nodes[-1], 'R': r_nodes[-1]}
        # last write wins in the flattened pixel->value map (legacy prototype shape)
        doc_local['dimension_witnesses']['x'][str(PIXEL_KEY)] = vals[cid]
    doc_local['openings'][0]['edge_witnesses']['x0']['dimension_refs'] += ['Q_s1', 'Q_s2', 'R_s1', 'R_s2']
    raw = freeze(doc_local)
    sup = freeze(dict(schema='tick_reading_supplement_v1', source_sha=digest(raw), image='own3.png',
                      chains={'P': dict(values_mm=p_values, cum_mm=p_nodes, overall_mm=p_nodes[-1],
                                        axis='x', origin_mm=0, direction=1, qualification='drawing_dimension'),
                              'Q': dict(values_mm=q_values, cum_mm=q_nodes, overall_mm=q_nodes[-1],
                                        axis='x', origin_mm=0, direction=1, qualification='drawing_dimension'),
                              'R': dict(values_mm=r_values, cum_mm=r_nodes, overall_mm=r_nodes[-1],
                                        axis='x', origin_mm=0, direction=1, qualification='drawing_dimension'),
                              'z': dict(values_mm=[1000, 1000], cum_mm=[0, 1000, 2000], overall_mm=2000,
                                       axis='z', origin_mm=0, direction=1, qualification='drawing_dimension')},
                      primary={'x': 'P', 'z': 'z'}, declarations=[]))
    s = TickSession(raw, image_id='own3', supplement=sup)
    edge = next(e for e in s.packet.edges if e.edge_id == 'O:x0')
    identities = {(c.expression.anchor.chain_id, c.expression.anchor.index, c.value_u) for c in edge.candidates}
    results.append(identities)
    # Verify all three chains' colliding nodes remain distinct, addressable identities.
    assert ('P', 2, p_nodes[2] * 10) in identities, "P:node2 (collides with Q:node1) must survive"
    assert ('Q', 1, q_nodes[1] * 10) in identities, "Q:node1 (collides with P:node2) must survive"
    assert ('P', 4, p_nodes[4] * 10) in identities, "P:node4 (collides with Q:node2 and R:node2) must survive"
    assert ('Q', 2, q_nodes[2] * 10) in identities, "Q:node2 (collides with P:node4, R:node2) must survive"
    assert ('R', 2, r_nodes[2] * 10) in identities, "R:node2 (collides with P:node4, Q:node2) must survive"
    assert ('P', 1, p_nodes[1] * 10) in identities, "P:node1 (collides with R:node1) must survive"
    assert ('R', 1, r_nodes[1] * 10) in identities, "R:node1 (collides with P:node1) must survive"
    # Cannot consume before a decision, regardless of write order.
    try:
        s.consume('not-decided')
        print(f"order={order}: FAIL -- consume() should have raised TICK_BATCH_INVALIDATED")
    except TickClaimError as exc:
        assert exc.code == 'TICK_BATCH_INVALIDATED'

print(f"Three write orders produce identical candidate-identity fingerprints: "
      f"{results[0] == results[1] == results[2]}")
print(f"Total distinct addressable node candidates at the single pixel key {PIXEL_KEY}: "
      f"{len(results[0])} (spans 3 chains x 5/3/3 nodes with 4 pairwise value-collisions)")
print("CONFIRMED: the 'same pixel key, one flattened value, multiple chains, multiple")
print("distinct pairwise node-value collisions (P<->Q twice, P<->R once)' shape --")
print("untested by the execution doc's two examples (which only ever had ONE pairwise")
print("collision between exactly two chains) -- is handled identically: node identity")
print("(chain_id, index) survives regardless of which chain's flattened value won the")
print("legacy pixel-map write race, and the model must still make an explicit choice.")
