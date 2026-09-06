"""Exit invariants still apply when an ordinary bug bypasses submit()."""
from dataclasses import asdict, replace
import json

import pytest

from src.agent.correction.tick_claim import (
    TickBatch, TickChoice, TickResponse, TickSession, digest, freeze,
)
from src.agent.correction.opening_adjudication import OpeningReview
from test_tick_claim_a6 import fixture, response, assert_code
from test_opening_adjudication_a6 import review_fixture


def decided_session():
    raw, supplement = fixture(values=(750, 1250, 1800))
    doc, cfg = json.loads(raw), json.loads(supplement)
    vertical = dict(values_mm=[650, 1450, 950], cum_mm=[0, 650, 2100, 3050], overall_mm=3050)
    doc['calibration']['z'] = vertical
    raw = freeze(doc)
    cfg['source_sha'] = digest(raw)
    cfg['chains']['Z'].update(vertical)
    s = TickSession(raw, image_id='new-cross-row', supplement=freeze(cfg))
    picks = {e.edge_id: next(c.candidate_id for c in e.candidates
                            if c.expression.anchor.index == (1 if e.edge_id.endswith((':x0', ':z_low')) else 2))
             for e in s.packet.edges}
    return s, s.submit(response(s, picks))


def install_record(session, record):
    raw = freeze(record)
    session._current = TickBatch(digest(raw), raw)
    return session._current.batch_id


def forged_case(name):
    s, batch = decided_session()
    record = json.loads(batch.record)
    rows = {r['edge_id']: r for r in record['rows']}

    def select(eid, index):
        candidate = next(c for e in s.packet.edges if e.edge_id == eid
                         for c in e.candidates if c.expression.anchor.index == index)
        rows[eid].update(candidate=json.loads(freeze(asdict(candidate))), value_u=candidate.value_u,
                         choice=TickChoice(edge_id=eid, action='select', candidate_id=candidate.candidate_id,
                                           reason='new diagnostic decision').model_dump())

    if name == 'vertical_inversion':
        select('O:z_low', 3)
        select('O:z_high', 1)
        record['response']['choices'] = [r['choice'] for r in record['rows']]
    elif name == 'duplicate_choice_owner':
        rows['O:x0']['choice']['edge_id'] = 'O:x1'
        record['response']['choices'] = [r['choice'] for r in record['rows']]
    elif name == 'response_subset':
        record['response']['choices'].pop()
    elif name == 'response_row_disagreement':
        select('O:x0', 0)  # still ordered; only the top response remains stale
    elif name == 'extra_row_with_full_coverage':
        record['rows'].append(dict(record['rows'][0]))
    elif name == 'pending_without_missing_source':
        row = rows['O:x0']
        row.update(choice=dict(edge_id='O:x0', action='pixel_pending_evidence', candidate_id=None, reason='no missing source'),
                   candidate=None, tier='pixel_only', value_u=15900, debt_id='invented')
        record['response']['choices'] = [r['choice'] for r in record['rows']]
    elif name == 'unearned_retirement':
        rows['O:x0']['retired_debt_id'] = 'invented'
    elif name == 'wrong_debt':
        rows['O:x0']['debt_id'] = 'invented'
    elif name == 'changed_witness':
        rows['O:x0']['witness'] = {}
    elif name == 'changed_generation':
        record['generation'] += 1
    elif name == 'response_extra_coordinate':
        record['response']['choices'][0]['x'] = 75
    elif name == 'reperceive_cannot_be_a_fact':
        rows['O:x0']['choice'] = dict(edge_id='O:x0', action='reperceive', candidate_id=None, reason='read again')
        record['response']['choices'] = [r['choice'] for r in record['rows']]
    else:
        raise AssertionError(name)
    return s, install_record(s, record)


CASES = (
    ('vertical_inversion', 'TICK_INTERVAL_NOT_ORDERED'),
    ('duplicate_choice_owner', 'TICK_DECISION_COVERAGE_MISMATCH'),
    ('response_subset', 'TICK_DECISION_COVERAGE_MISMATCH'),
    ('response_row_disagreement', 'TICK_BATCH_RESPONSE_MISMATCH'),
    ('extra_row_with_full_coverage', 'TICK_DECISION_COVERAGE_MISMATCH'),
    ('pending_without_missing_source', 'EVIDENCE_DEBT_WITHOUT_MISSING_SOURCE'),
    ('unearned_retirement', 'TICK_ROW_RECOMPUTE_MISMATCH'),
    ('wrong_debt', 'TICK_ROW_RECOMPUTE_MISMATCH'),
    ('changed_witness', 'TICK_ROW_RECOMPUTE_MISMATCH'),
    ('changed_generation', 'TICK_BATCH_METADATA_MISMATCH'),
    ('response_extra_coordinate', 'TICK_BATCH_RESPONSE_INVALID'),
    ('reperceive_cannot_be_a_fact', 'RETURN_TO_READING'),
)


@pytest.mark.parametrize('name,code', CASES)
def test_consume_rechecks_decision_invariants(name, code):
    session, batch_id = forged_case(name)
    assert_code(code, lambda: session.consume(batch_id))


def test_consumption_is_read_only_and_row_order_is_not_geometry():
    s, batch = decided_session()
    before = (s.history, s.packet, dict(s._previous_debts), s._current)
    original = s.consume(batch.batch_id)
    assert s.consume(batch.batch_id) == original
    assert (s.history, s.packet, s._previous_debts, s._current) == before
    record = json.loads(batch.record)
    record['rows'].reverse()  # harmless serialization permutation
    batch_id = install_record(s, record)
    assert [(f.edge_id, f.value_u) for f in s.consume(batch_id)] == [(f.edge_id, f.value_u) for f in original]


def test_consuming_retirement_replays_precommit_debt_without_retiring_twice():
    raw, supplement = fixture()
    s = TickSession(raw, image_id='debt-replay')
    pending = tuple(TickChoice(edge_id=e.edge_id,
                              action='pixel_pending_evidence' if e.missing_chains else 'pixel', reason='await named chain')
                    for e in s.packet.edges)
    s.submit(TickResponse(packet_id=s.packet.packet_id, choices=pending))
    s.reconsider('supplement arrived', supplement=supplement)
    picks = {e.edge_id: next(c.candidate_id for c in e.candidates if c.expression.anchor.index == i + 1)
             for i, e in enumerate(s.packet.edges[:2])}
    current = s.submit(response(s, picks))
    assert sum(bool(r['retired_debt_id']) for r in json.loads(current.record)['rows']) == 2
    assert s._previous_debts == {}
    before = s.history
    assert s.consume(current.batch_id) == s.consume(current.batch_id)
    assert s.history == before and s._previous_debts == {}
    s.reconsider('another review')
    next_batch = s.submit(response(s, picks))
    assert not any(r['retired_debt_id'] for r in json.loads(next_batch.record)['rows'])
    assert s.consume(next_batch.batch_id)


def test_pending_state_cannot_export_a_restored_current_batch():
    s, batch = decided_session()
    s._blocked = 'REGISTER_PENDING_READING_INPUT'
    assert_code('REGISTER_PENDING_READING_INPUT', lambda: s.consume(batch.batch_id))


@pytest.mark.parametrize('low,high', [(30000, 10000), (20000, 20000)])
def test_plan_assembly_checks_intervals_even_if_tick_consumer_regresses(monkeypatch, low, high):
    plan, pb, elev, eb, bindings, facades, walls = review_fixture()
    facts = tuple(replace(f, value_u=low if f.edge_id == 'S:run0:lo' else high) if f.edge_id in ('S:run0:lo', 'S:run0:hi') else f
                  for f in plan.consume(pb.batch_id))
    monkeypatch.setattr(plan, 'consume', lambda expected: facts)
    assert_code('TICK_PLAN_INTERVAL_NOT_ORDERED', lambda: OpeningReview(
        plan=plan, expected_plan_batch_id=pb.batch_id, bindings=bindings, facades=facades, walls=walls))
