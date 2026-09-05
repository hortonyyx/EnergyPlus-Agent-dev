from dataclasses import replace
from pathlib import Path
import json

import pytest
from pydantic import ValidationError

from src.agent.correction.tick_claim import (
    Expression, OperandRef, TickBatch, TickChoice, TickClaimError, TickResponse,
    TickSession, digest, evaluate, freeze, freeze_prototype_supplement, require_chain,
)

BASE = Path(__file__).resolve().parents[1] / 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype'


def fixture(values=(1600, 2700, 3200), pixels=(1.59, 4.31)):
    nodes = [0]
    for v in values:
        nodes.append(nodes[-1] + v)
    chain = dict(values_mm=list(values), cum_mm=nodes, overall_mm=sum(values))
    doc = dict(schema='as_drawn_elevation_v0', image='test.png', facade_label='South',
               calibration={'x': chain, 'z': dict(values_mm=[1000, 1000], cum_mm=[0, 1000, 2000], overall_mm=2000)},
               openings=[dict(id='O', x_range_m=list(pixels), z_range_m=[0, 1], edge_witnesses={
                   'x0': dict(dimension_refs=['P_s1', 'P_s2']),
                   'x1': dict(dimension_refs=['P_s2', 'P_s3'])})])
    raw = freeze(doc)
    supplement = freeze(dict(schema='tick_reading_supplement_v1', source_sha=digest(raw), image='test.png',
                            chains={'P': dict(**chain, axis='x', direction=1, origin_mm=0, qualification='drawing_dimension'),
                                    'Z': dict(**doc['calibration']['z'], axis='z', direction=1, origin_mm=0, qualification='drawing_dimension')},
                            primary={'x': 'P', 'z': 'Z'}, declarations=[]))
    return raw, supplement


def response(session, choices=None):
    picks = choices or {}
    return TickResponse(packet_id=session.packet.packet_id, choices=tuple(
        TickChoice(edge_id=e.edge_id, action='select' if e.edge_id in picks else 'pixel',
                   candidate_id=picks.get(e.edge_id), reason='test model decision') for e in session.packet.edges))


def assert_code(code, fn):
    with pytest.raises(TickClaimError) as e:
        fn()
    assert e.value.code == code


def test_real_four_views_full_scope_never_auto_claim():
    counts = []
    for face in ('south', 'east', 'north', 'west'):
        raw = (BASE / f'out/sm25_{face}_as_drawn.json').read_bytes()
        sup = freeze_prototype_supplement(raw, (BASE / f'tools/cfg_{face}.json').read_bytes())
        s = TickSession(raw, image_id=face, supplement=sup)
        counts.append(len(s.packet.edges))
        assert s.packet.diagnostics == ('SAME_IMAGE_MODEL_REQUIRED',)
        assert all(e.candidates for e in s.packet.edges)
        assert_code('TICK_BATCH_INVALIDATED', lambda: s.consume('unmade'))
        b = s.submit(response(s))
        facts = s.consume(b.batch_id)
        assert len(facts) == len(json.loads(raw)['openings']) * 4
        assert all(f.tier == 'pixel_only' and f.value_u % 100 == 0 for f in facts)
        if face == 'east':
            x = {f.edge_id: f.value_u for f in facts}
            assert (x['O01:x0'], x['O01:x1']) == (5400, 21600)
    assert counts == [28, 52, 32, 24]


@pytest.mark.parametrize('values,nodes,code', [
    ([900, 1500, 1200], [0, 900, 2450, 3600], 'CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM'),
    ([900, 0, 1500], [0, 900, 900, 2400], 'CHAIN_SEGMENT_NOT_POSITIVE'),
    ([1250, -250, 900], [0, 1250, 1000, 1900], 'CHAIN_SEGMENT_NOT_POSITIVE'),
    ([700, 1100, 1800], [1800, 2500, 3600], 'CHAIN_DOMAIN_INVALID'),
    ([5000, 1930, 1800], [0, 5000, 7000, 8730], 'CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM'),
    ([5000, 1930, 1800], [0, 5000, 5000, 8730], 'CALIBRATION_CHAIN_NODE_NOT_PREFIX_SUM'),
])
def test_chain_counterexamples(values, nodes, code):
    assert_code(code, lambda: require_chain(dict(values_mm=values, cum_mm=nodes, overall_mm=sum(values))))


def test_segment_domain_anchor_and_axis_half_signs():
    raw, sup = fixture()
    ref = lambda domain, i: OperandRef(digest(raw), 'P', domain, i)
    wrong = Expression('anchored_sum', ref('node', 0), (ref('node', 1), ref('node', 2)))
    assert_code('OPERAND_REF_DOMAIN', lambda: evaluate(wrong, raw=raw, supplement=sup, axis='x'))
    right = replace(wrong, operands=(ref('segment', 0), ref('segment', 1)))
    assert evaluate(right, raw=raw, supplement=sup, axis='x') == 43000
    diff = Expression('anchored_diff', ref('node', 1), (ref('node', 1), ref('node', 2)))
    assert evaluate(diff, raw=raw, supplement=sup, axis='x') == 43000
    assert evaluate(replace(diff, direction='negative'), raw=raw, supplement=sup, axis='x') == -11000
    cfg = json.loads(sup)
    cfg['declarations'] = [dict(axis='x', qualification='drawing_dimension', quantity='wall_thickness', callout_id='W', kind='full', value_mm=220)]
    thickness = OperandRef(digest(raw), 'declarations', 'declaration', 0)
    axis = Expression('axis_half_wall', ref('node', 1), (thickness,), 'positive', 'full')
    assert evaluate(axis, raw=raw, supplement=freeze(cfg), axis='x') == 17100
    assert evaluate(replace(axis, direction='negative'), raw=raw, supplement=freeze(cfg), axis='x') == 14900
    cfg['declarations'][0]['value_mm'] = 20.1
    assert_code('WALL_THICKNESS_HALF_UNGRID', lambda: evaluate(axis, raw=raw, supplement=freeze(cfg), axis='x'))
    cfg['declarations'][0]['value_mm'] = 20.2
    assert evaluate(axis, raw=raw, supplement=freeze(cfg), axis='x') == 16101
    cfg['declarations'][0]['qualification'] = 'pixel_only'
    assert_code('OPERAND_NOT_DECLARED', lambda: evaluate(axis, raw=raw, supplement=freeze(cfg), axis='x'))
    assert_code('OPERAND_CROSS_IMAGE', lambda: evaluate(replace(diff, anchor=replace(ref('node', 1), source_sha='b'*64)), raw=raw, supplement=sup, axis='x'))


def test_coverage_and_batch_replacement_and_reconsideration():
    raw, sup = fixture()
    s = TickSession(raw, image_id='test', supplement=sup)
    r = response(s)
    assert_code('TICK_DECISION_COVERAGE_MISMATCH', lambda: s.submit(r.model_copy(update={'choices': r.choices[:-1]})))
    b = s.submit(r)
    changed = json.loads(b.record)
    changed['rows'][0]['value_u'] += 100
    other = freeze(changed)
    assert_code('TICK_BATCH_NOT_CURRENT_DECISION', lambda: s.consume(b.batch_id, TickBatch(digest(other), other)))
    s.reconsider('whole building model questions first edge')
    assert_code('TICK_BATCH_INVALIDATED', lambda: s.consume(b.batch_id))
    assert_code('STALE_TICK_RESPONSE', lambda: s.submit(r))
    b2 = s.submit(response(s))
    assert b.batch_id != b2.batch_id
    assert s.consume(b2.batch_id)


@pytest.mark.parametrize('chosen', [(0, 0), (2, 0)])
def test_collapsed_or_reversed_interval_returns_to_first_step(chosen):
    raw, sup = fixture()
    refs = tuple((e, Expression('node', OperandRef(digest(raw), 'P', 'node', i)))
                 for e, i in zip(('O:x0', 'O:x1'), chosen))
    s = TickSession(raw, image_id='test', supplement=sup, expressions=refs)
    picks = {e.edge_id: next(c.candidate_id for c in e.candidates if c.expression.anchor.index == chosen[j])
             for j, e in enumerate(s.packet.edges[:2])}
    assert_code('RETURN_TO_STEP_ONE_INTERVAL', lambda: s.submit(response(s, picks)))
    assert s.packet.generation == 1


def test_debt_supplement_reclaim_retirement():
    raw, sup = fixture()
    s = TickSession(raw, image_id='test')
    choices = tuple(TickChoice(edge_id=e.edge_id, action='pixel_pending_evidence' if e.missing_chains else 'pixel', reason='await reading supplement') for e in s.packet.edges)
    b = s.submit(TickResponse(packet_id=s.packet.packet_id, choices=choices))
    assert sum(f.debt_id is not None for f in s.consume(b.batch_id)) == 2
    s.reconsider('reading supplied named chains', supplement=sup)
    picks = {e.edge_id: next(c.candidate_id for c in e.candidates if c.expression.anchor.index == i + 1) for i, e in enumerate(s.packet.edges[:2])}
    b2 = s.submit(response(s, picks))
    assert len([r for r in json.loads(b2.record)['rows'] if r['retired_debt_id']]) == 2
    assert_code('TICK_BATCH_INVALIDATED', lambda: s.consume(b.batch_id))


@pytest.mark.parametrize('boundary', [1935, 2473])
def test_chain_values_immune_to_output_grid(boundary):
    raw, sup = fixture(values=(boundary, 2000, 3000))
    s = TickSession(raw, image_id='test', supplement=sup)
    picks = {e.edge_id: next(c.candidate_id for c in e.candidates if c.expression.anchor.index == i + 1) for i, e in enumerate(s.packet.edges[:2])}
    b = s.submit(response(s, picks))
    facts = s.consume(b.batch_id)
    assert facts[0].value_u == boundary * 10


def test_response_has_no_cross_image_review_or_coordinate_fields():
    with pytest.raises(ValidationError):
        TickResponse(packet_id='x', choices=(), whole_building_review={})
    with pytest.raises(ValidationError):
        TickChoice(edge_id='x', action='pixel', reason='r', x=1.5)


@pytest.mark.parametrize('first,second,total,key', [
    (2600, 5200, 10400, 275.0),  # original R-2 collision
    (1800, 3600, 7200, 318.5),  # NEW same-shape input A
    (2150, 6450, 8600, 407.2),  # NEW same-shape input B
])
def test_collision_preserves_both_chain_identities_regardless_of_write_order(first, second, total, key):
    raw, sup = fixture(values=(first, second-first, total-second))
    doc, cfg = json.loads(raw), json.loads(sup)
    doc['openings'][0]['edge_witnesses']['x0']['dimension_refs'] += ['Q_s1', 'Q_s2']
    doc['openings'][0]['edge_witnesses']['x0']['nearest_tick_px'] = key
    fingerprints = []
    for flattened in (first, second):
        doc['dimension_witnesses'] = {'x': {str(key): flattened}}
        raw = freeze(doc)
        cfg['source_sha'] = digest(raw)
        cfg['chains']['Q'] = dict(values_mm=[second, total-second], cum_mm=[0, second, total],
                                  overall_mm=total, axis='x', origin_mm=0, direction=1, qualification='drawing_dimension')
        s = TickSession(raw, image_id='collision', supplement=freeze(cfg))
        edge = s.packet.edges[0]
        identities = {(c.expression.anchor.chain_id, c.expression.anchor.index, c.value_u) for c in edge.candidates}
        fingerprints.append(identities)
        assert {('P', 1, first*10), ('Q', 1, second*10)} <= identities
        assert_code('TICK_BATCH_INVALIDATED', lambda: s.consume('not-decided'))
    assert fingerprints[0] == fingerprints[1]


def test_round_limit_cannot_resubmit_old_packet():
    raw, sup = fixture()
    s = TickSession(raw, image_id='test', supplement=sup, max_rounds=1)
    r = response(s)
    b = s.submit(r)
    assert_code('REGISTER_PENDING_ROUND_LIMIT', lambda: s.reconsider('still wrong'))
    assert_code('TICK_BATCH_INVALIDATED', lambda: s.consume(b.batch_id))
    assert_code('REGISTER_PENDING_ROUND_LIMIT', lambda: s.submit(r))


def test_real_plan_scope_and_declared_negative_y_direction():
    raw = (BASE / 'out/sm25_1f_as_drawn.json').read_bytes()
    sup = freeze_prototype_supplement(raw, (BASE / 'tools/cfg_1f_full.json').read_bytes())
    s = TickSession(raw, image_id='plan', supplement=sup)
    assert len(s.packet.edges) == 102
    cfg = json.loads(sup)
    primary_y = cfg['primary']['y']
    assert cfg['chains'][primary_y]['direction'] == -1
    expr = Expression('node', OperandRef(digest(raw), primary_y, 'node', 1))
    assert evaluate(expr, raw=raw, supplement=sup, axis='y') == 153400
    b = s.submit(response(s))
    assert len(s.consume(b.batch_id)) == 102


def test_original_center_and_declared_width_derive_non_nodes():
    raw, sup = fixture(values=(900, 2100, 4500))
    n = lambda i: OperandRef(digest(raw), 'P', 'node', i)
    center_minus_half_width = Expression('axis_half_span', n(2), (n(0), n(1)), 'negative')
    assert evaluate(center_minus_half_width, raw=raw, supplement=sup, axis='x') == 25500
    assert evaluate(replace(center_minus_half_width, direction='positive'), raw=raw, supplement=sup, axis='x') == 34500
    assert 2550 not in json.loads(sup)['chains']['P']['cum_mm']
