"""E-a′: the production source is consumed without a v0 intermediate."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from src.agent.correction.tick_claim import (
    Expression, HISTORICAL_PLAN_V0_PRODUCER, OperandRef, TickSession,
    digest, evaluate, freeze,
)
from src.agent.reading.vector_contract import classify_vector_json
from test_tick_claim_a6 import response, assert_code

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out'


def plan_doc(name='sm25_1f_v2'):
    return json.loads((OUT / f'{name}.json').read_bytes())


@pytest.mark.parametrize('name,count', [('sm25_1f_v2',85), ('sm25_2f_v2',87), ('sm24_1f_v2',87)])
def test_real_native_candidate_scope_and_original_bytes(name,count):
    raw = (OUT / f'{name}.json').read_bytes()
    session = TickSession(raw, image_id=name)
    assert session.packet.source_bytes == raw
    assert session.packet.supplement_bytes is None
    assert len(session.packet.edges) == count * 2
    doc = json.loads(raw)
    assert {e.edge_id for e in session.packet.edges} == {
        f"{o['id']}:{role}" for o in doc['hypotheses']['opening_candidates'] for role in ('lo','hi')}
    assert all(e.pointer.startswith('/hypotheses/opening_candidates/') for e in session.packet.edges)
    assert all(e.candidates for e in session.packet.edges)
    batch = session.submit(response(session))
    assert len(session.consume(batch.batch_id)) == count * 2
    assert all(f.tier == 'pixel_only' for f in session.consume(batch.batch_id))


@pytest.mark.parametrize('pairs,status', [([], 'SELECTED'), (None, 'ABSENT_NO_MODEL_SELECTION'),
                                        ('keep', 'SELECTED_INCOMPLETE'), ('keep', None)])
def test_ea4_model_selection_required(pairs,status):
    doc = plan_doc()
    if pairs != 'keep':
        doc['hypotheses']['pairs'] = pairs
    doc['hypotheses']['pairs_status'] = status
    # Classifier behavior must stay legal/ADAPT even when this consumer refuses.
    assert classify_vector_json(doc).contract_id == 'as_drawn_plan'
    assert_code('TICK_PLAN_MODEL_SELECTION_REQUIRED',
                lambda: TickSession(freeze(doc), image_id='plan'))


@pytest.mark.parametrize('legacy', [False,True])
def test_ea5_missing_hypotheses_named_refusal(legacy):
    doc = plan_doc()
    del doc['hypotheses']
    if legacy:
        doc['strokes'] = []
    assert classify_vector_json(doc).contract_id == 'unknown'
    assert_code('TICK_PLAN_MALFORMED_DECLARED_CONTRACT',
                lambda: TickSession(freeze(doc), image_id='plan'))


def test_native_declared_chain_origin_direction_and_thickness_are_operands():
    raw=freeze(plan_doc())
    ref=OperandRef(digest(raw),'C_left_overall','node',1)
    assert evaluate(Expression('node',ref),raw=raw,supplement=None,axis='y') == 0
    ref=OperandRef(digest(raw),'C_top_fine','node',1)
    thickness=OperandRef(digest(raw),'/declarations/thickness_callouts_mm','declaration',0)
    assert evaluate(Expression('axis_half_wall',ref,(thickness,),thickness_kind='full'),
                    raw=raw,supplement=None,axis='x') == 23600
    session=TickSession(raw,image_id='plan')
    edge=next(e for e in session.packet.edges if e.axis=='x')
    candidate=next(c for c in edge.candidates if c.expression.anchor==ref)
    # Native declared nodes are offered, never selected merely by proximity.
    assert candidate.value_u == 22400


@pytest.mark.parametrize('mutation,code', [
    ('gap_span','TICK_PLAN_OPENING_GAP_DRIFT'),
    ('gap_missing','TICK_PLAN_GAP_COVERAGE_MISMATCH'),
    ('pair_measurement','TICK_PLAN_SELECTED_PAIR_DRIFT'),
    ('type_foreign','TICK_PLAN_OPENING_TYPE_UNKNOWN_ID'),
])
def test_native_redundant_channels_cannot_drift(mutation,code):
    doc=plan_doc(); hyp=doc['hypotheses']
    if mutation=='gap_span': hyp['opening_candidates'][0]['span_m'][0] += .001
    if mutation=='gap_missing':
        removed=hyp['opening_candidates'].pop()
        hyp['opening_types'].pop(removed['id'],None)
    if mutation=='pair_measurement': hyp['pairs'][0]['spacing_m'] += .001
    if mutation=='type_foreign': hyp['opening_types']['invented']='window'
    assert_code(code,lambda: TickSession(freeze(doc),image_id='plan'))


def test_v0_producer_is_explicitly_historical_and_still_readable():
    path=ROOT/HISTORICAL_PLAN_V0_PRODUCER
    assert '2026-08-23_as_drawn_reading_prototype' in path.parts
    assert '"schema": "as_drawn_plan_v0"' in path.read_text()
    raw=(OUT/'sm25_1f_as_drawn.json').read_bytes()
    session=TickSession(raw,image_id='history')
    assert session.packet.source_bytes==raw
    assert all(e.pointer.startswith('/wall_bands/') for e in session.packet.edges)
