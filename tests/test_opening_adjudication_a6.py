import json
from dataclasses import replace

import pytest

from src.agent.correction.opening_adjudication import (
    FacadeInput, InferredDimensions, OpeningChoice, OpeningReview,
    PlanBinding, SpatialResponse,
)
from src.agent.correction.projection_bridge import CutLineV1
from src.agent.correction.tick_claim import TickSession, freeze
from test_tick_claim_a6 import fixture, response, assert_code


def review_fixture():
    # Three plan openings on the South, one East with no elevation drawing.
    doc = dict(schema='as_drawn_plan_v0', image='plan.png', wall_bands=[
        dict(id='S', constant_world_axis='y', opening_runs=[
            dict(run_m=[1.6, 4.3]), dict(run_m=[4.5, 5.5]), dict(run_m=[6, 7])]),
        dict(id='E', constant_world_axis='x', opening_runs=[dict(run_m=[1, 2])])])
    p = TickSession(freeze(doc), image_id='plan')
    pb = p.submit(response(p))
    raw, sup = fixture()
    elev = json.loads(raw)
    elev['structure_lines'] = []
    elev['openings'][0]['x_range_m'] = [1.6, 4.3]
    elev['openings'].append(dict(id='Q', x_range_m=[4.6, 5.7], z_range_m=[0.5, 1.5]))
    e = TickSession(freeze(elev), image_id='south')
    eb = e.submit(response(e))
    walls = (
        CutLineV1('x', 0.12, 0, 7.5, 0.12, 'wall', 'S'),
        CutLineV1('x', 2.88, 0, 7.5, 0.12, 'wall', 'N'),
        CutLineV1('y', 0.12, 0, 3, 0.12, 'wall', 'W'),
        CutLineV1('y', 7.38, 0, 3, 0.12, 'wall', 'E'))
    bindings = tuple(PlanBinding(f'S:run{i}', 'South', 'S', 'room',
                                CutLineV1('x', .12, 0, 1, .12, 'opening', f'S:run{i}'), floor_origin_u=0) for i in range(3)) + (
        PlanBinding('E:run0', 'East', 'E', 'room', CutLineV1('y', 7.38, 0, 1, .12, 'opening', 'E:run0'), floor_origin_u=0),)
    facades = tuple(FacadeInput(f, e if f == 'South' else None, eb.batch_id if f == 'South' else None, mirrored=False, local_x_positive='image_left_to_right')
                    for f in ('South', 'East', 'North', 'West'))
    return p, pb, e, eb, bindings, facades, walls


def make_review():
    p, pb, e, eb, bindings, facades, walls = review_fixture()
    return OpeningReview(plan=p, expected_plan_batch_id=pb.batch_id, bindings=bindings,
                         facades=facades, walls=walls), e


def spatial_response(review):
    return SpatialResponse(packet_id=review.packet.packet_id,
                           choices=(OpeningChoice(plan_opening_id='S:run0', action='pair', elevation_opening_id='O', reason='same identity'),
                                    OpeningChoice(plan_opening_id='S:run1', action='pair', elevation_opening_id='Q', reason='same identity, size differs'),
                                    OpeningChoice(plan_opening_id='S:run2', action='register', reason='not drawn on present South elevation'),
                                    OpeningChoice(plan_opening_id='E:run0', action='infer', inferred_dimensions=InferredDimensions(height_mm=1513, sill_above_floor_mm=827), reason='model hypothesis')),
                           whole_building_review='accept', reason='fixture building review')


def test_four_categories_exact_elevation_register_and_inference():
    review, _ = make_review()
    result = review.submit(spatial_response(review))
    outcomes = json.loads(result.record)['outcomes']
    assert [o['classification'] for o in outcomes] == ['①', '②a', '②b', '③']
    assert outcomes[0]['span_u'] == [16000, 43000]
    assert outcomes[1]['span_u'] == [46000, 57000]
    assert outcomes[1]['wall_id'] == 'S' and outcomes[1]['room_id'] == 'room'
    assert outcomes[2]['span_u'] is None and outcomes[2]['z_u'] is None
    assert outcomes[3]['source'] == 'inferred' and not outcomes[3]['score_eligible']
    assert outcomes[3]['z_u'] == [8300, 23400]
    assert len(review.scoreable_openings(result.result_id)) == 2
    assert len(json.loads(review.packet.record)['plan_facts']) == 8


def test_input_and_output_coverage_and_no_inference_when_facade_exists():
    p, pb, e, eb, bindings, facades, walls = review_fixture()
    assert_code('PLAN_TOPOLOGY_COVERAGE_MISMATCH', lambda: OpeningReview(plan=p, expected_plan_batch_id=pb.batch_id, bindings=bindings[:-1], facades=facades, walls=walls))
    assert_code('FACADE_AVAILABILITY_MANIFEST_INCOMPLETE', lambda: OpeningReview(plan=p, expected_plan_batch_id=pb.batch_id, bindings=bindings, facades=facades[:-1], walls=walls))
    wrong_axis = (replace(bindings[0], family='East'),) + bindings[1:]
    assert_code('PLAN_HOST_BINDING_MISMATCH', lambda: OpeningReview(plan=p, expected_plan_batch_id=pb.batch_id, bindings=wrong_axis, facades=facades, walls=walls))
    review, _ = make_review()
    r = spatial_response(review)
    assert_code('SPATIAL_DECISION_COVERAGE_MISMATCH', lambda: review.submit(r.model_copy(update={'choices': r.choices[:-1]})))
    infer = OpeningChoice(plan_opening_id='S:run0', action='infer', inferred_dimensions=InferredDimensions(height_mm=1500, sill_above_floor_mm=900), reason='bad')
    assert_code('INFERENCE_REQUIRES_ABSENT_FACADE', lambda: review.submit(r.model_copy(update={'choices': (infer,) + r.choices[1:]})))


def test_whole_building_reconsider_invalidates_prior_results():
    review, elev = make_review()
    result = review.submit(spatial_response(review))
    elev.reconsider('overall review now disputes South edge')
    assert_code('TICK_BATCH_INVALIDATED', lambda: review.consume(result.result_id))
    assert_code('TICK_BATCH_INVALIDATED', lambda: review.scoreable_openings(result.result_id))
    review, elev = make_review()
    r = SpatialResponse(packet_id=review.packet.packet_id, choices=(), whole_building_review='return_to_step_one', reason='wrong tick identity', reconsider_image_ids=('south',))
    assert_code('RETURN_TO_STEP_ONE_FROM_SPATIAL', lambda: review.submit(r))
    assert elev.packet.generation == 1


def test_pair_identity_not_reused_and_whole_review_pending_not_scoreable():
    review, _ = make_review()
    r = spatial_response(review)
    same = r.choices[1].model_copy(update={'elevation_opening_id': 'O'})
    assert_code('PAIR_IDENTITY_REUSED', lambda: review.submit(r.model_copy(update={'choices': (r.choices[0], same) + r.choices[2:]})))
    result = review.submit(r.model_copy(update={'whole_building_review': 'register'}))
    assert review.scoreable_openings(result.result_id) == ()


def test_mutable_caller_inputs_cannot_change_frozen_choices_or_manifest():
    from src.agent.correction.tick_claim import Expression, OperandRef, digest
    raw, sup = fixture()
    operands = [OperandRef(digest(raw), 'P', 'segment', 0)]
    expr = Expression('anchored_sum', OperandRef(digest(raw), 'P', 'node', 0), operands)
    source_buffer, supplement_buffer = bytearray(raw), bytearray(sup)
    s = TickSession(source_buffer, image_id='mutable', supplement=supplement_buffer,
                    expressions=(('O:x0', expr),))
    candidate = next(c for c in s.packet.edges[0].candidates if c.expression.operation == 'anchored_sum')
    operands.append(OperandRef(digest(raw), 'P', 'segment', 1))
    source_buffer.clear()
    supplement_buffer.clear()
    batch = s.submit(response(s, {'O:x0': candidate.candidate_id}))
    assert s.consume(batch.batch_id)[0].value_u == candidate.value_u == 16000
    p, pb, e, eb, bindings, facades, walls = review_fixture()
    mutable_facades, mutable_bindings = list(facades), list(bindings)
    r = OpeningReview(plan=p, expected_plan_batch_id=pb.batch_id, bindings=mutable_bindings,
                      facades=mutable_facades, walls=walls)
    with pytest.raises(AttributeError):
        r.packet = replace(r.packet, record=b'{}')
    mutable_bindings.clear()
    result = r.submit(spatial_response(r))
    mutable_facades.clear()
    e.reconsider('source invalidated')
    assert_code('TICK_BATCH_INVALIDATED', lambda: r.consume(result.result_id))
