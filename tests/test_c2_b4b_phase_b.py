"""B4b Phase-B contract probes: each B1..B5 exit has a named assertion."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.agent.correction.facade_applicability import (
    ApplicabilityIntervalV1, ClaimApplicabilityV1, OpeningApplicabilityV1,
)
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import CompletenessAssertion, Coverage, OpeningEvidence, RequiredViewEntry, UserSourceRef, ViewManifest
from src.agent.judge.opening_claim_score import (
    OpeningAssignment, OpeningObservation, assign_openings, bind_correction_window_segment, build_absence_opening_claims, classify_extra_observation,
    build_correction_host_resolver, derive_absence_ledger, derive_product_ledger, derive_reference_ledger, eligible_units, gt_openings_to_va_claims, gt_to_va_visibility, fuse_source_results, score_plan_claims, summarize_claim_rows,
)
from src.agent.judge.score_inputs import frame_transform_sha256, materialize_va_elevation_bindings
from src.agent.judge.score_schema import CLAIM_ORDER, ElevationScoreViewBindingV1, JudgeScoreConfigV1, JudgeScoreViewBindingsV1, PlanScoreViewBindingV1, ScoreContractError, canonical_sha256
from src.agent.judge.segment_score import PlanSegment, assign_plan_segments, coerce_plan_observations, extract_correction_plan_segments, extract_gt_plan_segments, score_plan_segments
from tests.b4b_contract_fixture import make_b4b_gt_document


def config():
    return JudgeScoreConfigV1(schema_version="1", plan_axis_alignment_tol_m=.05, plan_position_tol_m=.3,
        plan_extent_tol_m=.3, claim_complete_epsilon_m=.05, opening_match_center_tol_m=.4,
        opening_assignment_tie_epsilon=1e-9, along_claim_tol_m=.4, width_claim_tol_m=.4,
        sill_claim_tol_m=.3, head_claim_tol_m=.3, floor_line_tol_m=.3)


def seg(key, p1, p2, *, floor="F", exterior=True):
    return PlanSegment(key, floor, p1, p2, exterior=exterior)


def claim(*, name="along", status="partially_applicable", intervals=((0., .1),), target=(0., 1.)):
    applicable = tuple(ApplicabilityIntervalV1(lo=lo, hi=hi) for lo, hi in intervals)
    return ClaimApplicabilityV1(claim=name, status=status,
        reason="partial_observable_coverage" if status == "partially_applicable" else "full_observable_coverage",
        target_world_interval=ApplicabilityIntervalV1(lo=target[0], hi=target[1]), applicable_intervals=applicable,
        unobserved_intervals=(), considered_source_view_ids=(), supporting_source_view_ids=(), facade_segment_ids=(), source_evidence=())


def real_va_context(*, complete_plan=False, complete_elevation=False, negative_only_elevation=False):
    """Typed GT + reviewed bindings + real Va context; no ledger doubles."""
    gt = make_b4b_gt_document()
    H = "a" * 64
    plan_claims = ["existence", "host", "along", "width"]
    elevation_claims = ["existence", "along", "width", "sill", "head", "appearance"]
    def evidence(kind, complete=False):
        if complete:
            claims = plan_claims if kind == "plan" else elevation_claims
            return OpeningEvidence(potentially_observable_claims=claims, negative_evidence_capable_claims=claims,
                coverage=Coverage(frame="plan_floor_region" if kind == "plan" else "elevation_local_along",
                                  region="full_floor" if kind == "plan" else "full_facade", completeness_assertion_id="complete"),
                completeness_assertion=CompletenessAssertion(assertion_id="complete", source_ref=UserSourceRef(source="user", content_sha256="1" * 64)))
        return OpeningEvidence(potentially_observable_claims=plan_claims if kind == "plan" else elevation_claims)
    plan_meta = dict(declared_direction_token=None, direction_source="standard_assumption", direction_semantics="building_axis", semantics_source="case_metadata", azimuth_deg=None, building_view_direction=None)
    entries = [RequiredViewEntry(input_id="plan-F1", source_image="case_data/p1.png", image_sha256=H, view_type="plan", floor_ref=1, dimensioned=True, expected_output_id="plan-F1", opening_evidence=evidence("plan", complete_plan), **plan_meta),
        RequiredViewEntry(input_id="plan-F2", source_image="case_data/p2.png", image_sha256=H, view_type="plan", floor_ref=2, dimensioned=True, expected_output_id="plan-F2", opening_evidence=evidence("plan"), **plan_meta)]
    elevation_inputs = [("elev-N", "North"), ("elev-N-detail", "North"), ("elev-S", "South")]
    if negative_only_elevation:
        # Reviewed manifest/binding source with completeness but no GT opening
        # source ref: it is the real §8.6.1 item-2 absence-witness fixture.
        elevation_inputs.append(("elev-N-absence", "North"))
    for ident, family in elevation_inputs:
        entries.append(RequiredViewEntry(input_id=ident, source_image="case_data/%s.png" % ident, image_sha256=H, view_type="elevation", floor_ref=None, declared_direction_token=family, direction_source="standard_assumption", direction_semantics="building_axis", semantics_source="case_metadata", azimuth_deg=None, building_view_direction=family, dimensioned=True, expected_output_id=ident, opening_evidence=evidence("elevation", complete_elevation)))
    entries.sort(key=lambda item: item.input_id)
    payload = {"view_manifest_schema_version":"1", "claims_vocab_version":"1", "generator_version":"1", "completeness_ruleset_version":"1", "case_id":gt.case, "case_metadata_sha256":H, "entries":[item.model_dump(mode="json") for item in entries]}
    manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))
    segments = {segment.id:segment for floor in gt.floors for segment in floor.boundary_segments}
    bindings = [PlanScoreViewBindingV1(kind="plan", input_id="plan-F1", floor_id="F1", gt_source_view_ids=("plan-F1",)), PlanScoreViewBindingV1(kind="plan", input_id="plan-F2", floor_id="F2", gt_source_view_ids=("plan-F2",))]
    for ident, family in elevation_inputs:
        span = [segment.world_along_interval for segment in segments.values() if segment.facade_family == family]
        sign = -1 if family == "North" else 1
        proto = ElevationScoreViewBindingV1(kind="elevation", input_id=ident, floor_ids=("F1", "F2"), facade_family=family, gt_source_view_ids=(ident,), resolved_building_direction=family, resolution_source="manifest_building_axis", orientation_output_hash=None, adapter_version=None, source_footprint_fingerprint=gt.floors[0].footprint_fingerprint, world_axis="x", sign=sign, along_origin=max(x.hi for x in span) if sign == -1 else min(x.lo for x in span), mirrored=False, local_x_positive="image_left_to_right", frame_transform_sha256="0" * 64)
        bindings.append(proto.model_copy(update={"frame_transform_sha256":frame_transform_sha256(proto)}))
    raw = {"schema_version":"1", "case_id":gt.case, "gt_content_sha256":gt.content_sha256, "case_metadata_sha256":H, "base_view_manifest_sha256":manifest.content_sha256, "bindings":[item.model_dump(mode="json") for item in bindings]}
    score_bindings = JudgeScoreViewBindingsV1(schema_version="1", case_id=gt.case, gt_content_sha256=gt.content_sha256, case_metadata_sha256=H, base_view_manifest_sha256=manifest.content_sha256, bindings=tuple(bindings), content_sha256=canonical_sha256(raw))
    return gt, manifest, score_bindings


def correction_two_zone(*, window_room="C1", window_span=(.5, 1.5)):
    """Actual typed correction geometry with one exterior host and shared wall."""
    from src.agent.correction.facade_visibility import VisibilityTolerances, materialize_all_facade_segments
    from src.agent.correction.schema import CorrectedGeometryV3
    raw = {"schema_version":"3", "footprint_x":[0.,4.], "footprint_y":[0.,2.], "floors":[{"id":"F1","name":"F1","z_floor":0.,"ceiling_height":3.,"footprint":{"vertices":[[0.,0.],[4.,0.],[4.,2.],[0.,2.]]},"cells":[{"id":"C1","role":"office","x":[0.,2.],"y":[0.,2.],"polygon":[[0.,0.],[2.,0.],[2.,2.],[0.,2.]]},{"id":"C2","role":"office","x":[2.,4.],"y":[0.,2.],"polygon":[[2.,0.],[4.,0.],[4.,2.],[2.,2.]]}]}],"windows":[{"id":"W1","floor":"F1","floor_id":"F1","facade":"North","span":list(window_span),"z":[1.,2.],"room":window_room,"facade_segment_id":None}],"facade_segments":[],"corrections":[],"conflicts":[],"unsupported":[],"notes":None}
    geometry = CorrectedGeometryV3.model_validate(raw)
    segments = materialize_all_facade_segments(geometry, tolerances=VisibilityTolerances(1e-9, 1e-9))
    return geometry.model_copy(update={"facade_segments":list(segments)})


@pytest.mark.parametrize("ring,minimum", [
    ([(0,0),(4,0),(4,1),(1,1),(1,4),(0,4)], 6),       # L
    ([(0,0),(4,0),(4,4),(3,4),(3,1),(1,1),(1,4),(0,4)], 8),  # U
])
def test_b4b_b1_actual_concave_segments_are_not_bbox_or_fixed_four_sides(ring, minimum):
    """B4B-B1: a fake typed floor preserves every L/U edge, including reflex runs."""
    floor = SimpleNamespace(id="F", footprint=SimpleNamespace(exterior=SimpleNamespace(vertices=ring)), boundary_segments=[], zones=[SimpleNamespace(id="Z", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=ring)))])
    gt = SimpleNamespace(floors=[floor])
    segments = extract_gt_plan_segments(gt)  # extraction only consumes typed polygon attributes
    # no exterior declarations here; the absence of synthesized bbox walls is the point
    assert not segments
    # Actual correction-like observations retain all six/eight topology edges.
    actual = [seg(str(i), ring[i], ring[(i+1) % len(ring)]) for i in range(len(ring))]
    assert len(actual) >= minimum and {(s.p1, s.p2) for s in actual} != {((0,0),(4,0)), ((4,0),(4,4)), ((4,4),(0,4)), ((0,4),(0,0))}


def test_b4b_b1_gt_fixture_contains_multiple_same_family_and_short_return_segments():
    gt = make_b4b_gt_document()
    segments = extract_gt_plan_segments(gt)
    north = [item for item in segments if item.floor_id == "F1" and item.exterior and item.p1[1] == item.p2[1]]
    assert len(north) > 2
    assert min(item.length for item in north) < max(item.length for item in north)


def test_b4b_r1_correction_extraction_and_reading_adapter_are_real_typed_paths():
    geometry = correction_two_zone()
    extracted = extract_correction_plan_segments(geometry)
    interior = [item for item in extracted if not item.exterior]
    assert len([item for item in extracted if item.exterior]) == 4
    assert len(interior) == 1 and interior[0].zone_ids == ("C1", "C2") and {interior[0].p1, interior[0].p2} == {(2.,0.), (2.,2.)}
    reading = coerce_plan_observations(({"id":"read-1","floor_id":"F1","p1":[0.,2.],"p2":[2.,2.],"source_ids":["plan-F1"]},))
    assert reading[0].key == "read-1" and reading[0].source_ids == ("plan-F1",)
    with pytest.raises(ScoreContractError, match="score_product_identity_invalid"):
        coerce_plan_observations(({"id":"bad"},))


def test_b4b_r1_gt_interior_pairing_and_invariant_raises():
    geometry = correction_two_zone()
    floor = SimpleNamespace(id="F1", footprint=SimpleNamespace(exterior=SimpleNamespace(vertices=[(0.,0.),(4.,0.),(4.,2.),(0.,2.)])), boundary_segments=[], zones=[SimpleNamespace(id="Z1", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=[(0.,0.),(2.,0.),(2.,2.),(0.,2.)]))), SimpleNamespace(id="Z2", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=[(2.,0.),(4.,0.),(4.,2.),(2.,2.)])) )])
    interior = extract_gt_plan_segments(SimpleNamespace(floors=[floor]))
    assert len(interior) == 1 and interior[0].zone_ids == ("Z1", "Z2")
    bad = SimpleNamespace(id="F", footprint=SimpleNamespace(exterior=SimpleNamespace(vertices=[(0.,0.),(2.,0.),(2.,2.),(0.,2.)])), boundary_segments=[], zones=[SimpleNamespace(id="Z", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=[(0.,0.),(1.,0.),(1.,1.),(0.,1.)])) )])
    with pytest.raises(ScoreContractError) as invalid:
        extract_gt_plan_segments(SimpleNamespace(floors=[bad]))
    assert invalid.value.context["reason"] == "invalid_interior_edge_pair"
    conflict = SimpleNamespace(id="F", footprint=SimpleNamespace(exterior=SimpleNamespace(vertices=[(0.,0.),(2.,0.),(2.,2.),(0.,2.)])), boundary_segments=[], zones=[SimpleNamespace(id="A", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=[(0.,0.),(2.,0.),(2.,1.),(0.,1.)]))), SimpleNamespace(id="B", polygon=SimpleNamespace(exterior=SimpleNamespace(vertices=[(2.,0.),(0.,0.),(0.,-1.),(2.,-1.)])) )])
    with pytest.raises(ScoreContractError) as exterior:
        extract_gt_plan_segments(SimpleNamespace(floors=[conflict]))
    assert exterior.value.context["reason"] == "exterior_interior_topology_conflict"


def test_b4b_b2_assignment_is_order_and_id_rename_invariant():
    targets = (seg("t2", (2,0), (3,0)), seg("t1", (0,0), (1,0)))
    first = (seg("a", (0,0), (1,0)), seg("b", (2,0), (3,0)))
    second = tuple(reversed((seg("renamed-b", (2,0), (3,0)), seg("renamed-a", (0,0), (1,0)))))
    one = assign_plan_segments(targets=targets, observations=first, config=config())
    two = assign_plan_segments(targets=reversed(targets), observations=second, config=config())
    assert [(a.p1, b.p1) for a, b in one.matched] == [(a.p1, b.p1) for a, b in two.matched]


def test_b4b_b2_exact_tie_is_rejected_without_id_tiebreak():
    with pytest.raises(ScoreContractError, match="score_match_ambiguous"):
        assign_plan_segments(targets=(seg("t", (0,0), (1,0)),), observations=(seg("a", (0,0), (1,0)), seg("z", (0,0), (1,0))), config=config())


def test_b4b_b2_segment_states_include_complete_within_miss_extra_and_extent():
    rows = score_plan_segments(targets=(seg("a", (0,0), (1,0)), seg("b", (2,0), (3,0)), seg("miss", (8,0), (9,0))),
        observations=(seg("exact", (0,0), (1,0)), seg("long", (2,0), (3.2,0)), seg("extra", (5,0), (6,0))), config=config())
    assert {row.status for row in rows} == {"complete", "within_tolerance", "miss", "extra"}
    assert next(row for row in rows if row.observation and row.observation.key == "long").extent_symmetric_difference_m == pytest.approx(.2)


def test_b4b_b2_opening_tie_and_duplicate_target_id_are_rejected():
    target = SimpleNamespace(id="T", floor_id="F", kind="window", boundary_segment_id="S", world_along_interval=SimpleNamespace(lo=0., hi=1.))
    observations = (OpeningObservation("a", "F", "window", "S", (0., 1.), "plan"), OpeningObservation("z", "F", "window", "S", (0., 1.), "plan"))
    with pytest.raises(ScoreContractError, match="score_match_ambiguous"):
        assign_openings(targets=(target,), observations=observations, config=config(), product_to_gt_segment={"S":"S"})


def test_b4b_b2_missing_and_ambiguous_correction_segment_binding_fail_closed():
    from src.agent.correction.schema import FacadeSegment, WorldInterval
    H = "a" * 64
    def facade(id):
        return FacadeSegment(id=id, floor_id="F", facade_family="North", p1=(0., 1.), p2=(2., 1.), outward_normal=(0, 1),
            world_along_interval=WorldInterval(lo=0., hi=2.), depth=0., visible_intervals=[], source_footprint_fingerprint=H)
    window = SimpleNamespace(id="W", floor_id="F", facade="North", span=(.5, 1.5), facade_segment_id=None)
    with pytest.raises(ScoreContractError, match="score_product_segment_unresolved"):
        bind_correction_window_segment(window=window, segments=(facade("a"), facade("b")))
    with pytest.raises(ScoreContractError, match="score_product_segment_unresolved"):
        bind_correction_window_segment(window=window, segments=())


def test_b4b_r1_real_correction_host_resolver_scores_and_rejects_zero_multi_adjacency():
    from src.agent.judge.opening_claim_score import bind_correction_window_segment, resolve_correction_window_host
    gt, manifest, bindings = real_va_context(); target = next(item for item in gt.openings if item.kind == "window")
    geometry = correction_two_zone(window_span=(target.world_along_interval.lo, target.world_along_interval.hi)); reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    window = geometry.windows[0]; product_segment, mode = bind_correction_window_segment(window=window, segments=geometry.facade_segments)
    mapping = {product_segment.id:target.boundary_segment_id}; resolver = build_correction_host_resolver(geometry=geometry, product_to_gt_segment=mapping, product_to_gt_zone={"C1":target.host_zone_id})
    observation = OpeningObservation("W1", "F1", "window", product_segment.id, tuple(window.span), "plan-F1")
    assignment = assign_openings(targets=(target,), observations=(observation,), config=config(), product_to_gt_segment=mapping)
    rows = score_plan_claims(gt=gt, ledger=reference, assignment=assignment, config=config(), host_resolver=resolver)
    assert mode == "temporary_unique_span_binding" and next(row for row in rows if row.target_id == target.id and row.claim == "host").result == "complete"
    with pytest.raises(ScoreContractError, match="score_product_segment_unresolved"):
        resolve_correction_window_host(geometry=geometry, window=window.model_copy(update={"span":[4.1,4.2]}), product_segment=product_segment, gt_segment_id=target.boundary_segment_id, gt_zone_id=target.host_zone_id, product_to_gt_segment=mapping, product_to_gt_zone={"C1":target.host_zone_id})
    with pytest.raises(ScoreContractError, match="score_product_segment_unresolved"):
        resolve_correction_window_host(geometry=geometry, window=window.model_copy(update={"span":[1.9,2.1]}), product_segment=product_segment, gt_segment_id=target.boundary_segment_id, gt_zone_id=target.host_zone_id, product_to_gt_segment=mapping, product_to_gt_zone={"C1":target.host_zone_id})


@pytest.mark.parametrize("ratio", [.1, .5, .9])
def test_b4b_b4_partial_denominator_is_exact_geometric_ratio_not_half(ratio):
    units, reason, parts = eligible_units(claim=claim(intervals=((0., ratio),)), target_kind="window")
    assert reason is None and units == ratio and parts == ((0., ratio),)


def test_b4b_b4_na_zero_miss_are_disjoint_and_summary_conserves_units():
    partial, _, _ = eligible_units(claim=claim(intervals=((0., .1), (.5, .9))), target_kind="window")
    na, reason, _ = eligible_units(claim=claim(name="appearance", intervals=((0., 1.),)), target_kind="window")
    assert partial == pytest.approx(.5) and (na, reason) == (0., "reference_value_unavailable")
    # This is the denominator invariant consumed by the sidecar summary: NA has no units.
    assert partial + na == pytest.approx(.5)


def test_b4b_b4_real_reference_va_rows_and_summary_conserve_na_zero_miss():
    gt, manifest, bindings = real_va_context()
    reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(item for item in gt.openings if item.kind == "window")
    observation = OpeningObservation("observed", "F1", "window", target.boundary_segment_id,
        (target.world_along_interval.lo, target.world_along_interval.hi), "plan-F1")
    assignment = assign_openings(targets=(target,), observations=(observation,), config=config(), product_to_gt_segment={target.boundary_segment_id:target.boundary_segment_id})
    rows = score_plan_claims(gt=gt, ledger=reference, assignment=assignment, config=config(), host_results={target.id:"complete"})
    summaries = summarize_claim_rows(rows)
    assert sum(row.eligible_units for row in rows if row.result != "not_applicable") == pytest.approx(sum(item.denominator_units for item in summaries))
    assert any(row.result == "not_applicable" for row in rows) and any(row.result == "complete" for row in rows)


def test_b4b_real_multisource_fusion_is_scored_without_dropping_evidence():
    gt, manifest, bindings = real_va_context(complete_plan=True)
    reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(item for item in gt.openings if item.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    observations = (OpeningObservation("plan-good", "F1", "window", target.boundary_segment_id, span, "plan-F1"),
        OpeningObservation("elev-bad", "F1", "window", target.boundary_segment_id, (span[0], span[0] + (span[1]-span[0])*.2), "elev-N"))
    assigned = assign_openings(targets=(target,), observations=observations, config=config(), product_to_gt_segment={target.boundary_segment_id:target.boundary_segment_id})
    rows = score_plan_claims(gt=gt, ledger=reference, assignment=assigned, config=config(), host_results={target.id:"complete"})
    along = next(row for row in rows if row.target_id == target.id and row.claim == "along")
    assert len(along.matched_observation_ids) == 2 and along.result == "complete"


def test_b4b_phase_b_twin_redundant_gt_positive_sources_do_not_make_correct_plan_conflict():
    """MAJOR-1 twin probe: Phase-B must exclude GT-positive negative intervals."""
    gt, manifest, bindings = real_va_context(complete_plan=True, complete_elevation=True)
    reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(item for item in gt.openings if item.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    observation = OpeningObservation("plan-only", "F1", "window", target.boundary_segment_id, span, "plan-F1")
    assigned = assign_openings(targets=(target,), observations=(observation,), config=config(),
                               product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    along = next(row for row in score_plan_claims(gt=gt, ledger=reference, assignment=assigned,
                                                   config=config(), host_results={target.id: "complete"})
                 if row.target_id == target.id and row.claim == "along")
    assert along.result == "complete"


def test_b4b_phase_b_gt_positive_source_is_not_treated_as_trusted_negative_conflict():
    gt, manifest, bindings = real_va_context(complete_plan=True)
    reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(item for item in gt.openings if item.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    observation = OpeningObservation("elev-only", "F1", "window", target.boundary_segment_id, span, "elev-N")
    assigned = assign_openings(targets=(target,), observations=(observation,), config=config(), product_to_gt_segment={target.boundary_segment_id:target.boundary_segment_id})
    rows = score_plan_claims(gt=gt, ledger=reference, assignment=assigned, config=config(), host_results={target.id:"complete"})
    assert next(row for row in rows if row.target_id == target.id and row.claim == "along").result == "complete"


def test_b4b_r2_source_view_id_is_distinct_from_manifest_input_id():
    gt, manifest, bindings = real_va_context(); reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(item for item in gt.openings if item.kind == "window")
    observation = OpeningObservation("alias", "F1", "window", target.boundary_segment_id, (target.world_along_interval.lo, target.world_along_interval.hi), "gt-plan-view")
    assignment = OpeningAssignment(matched=((target, observation),), unmatched_targets=(), unmatched_observations=())
    rows = score_plan_claims(gt=gt, ledger=reference, assignment=assignment, config=config(), host_results={target.id:"complete"}, source_view_to_input={"gt-plan-view":"plan-F1"})
    assert next(row for row in rows if row.target_id == target.id and row.claim == "host").result == "complete"


def test_b4b_r2_product_declaration_deletion_repushes_reference_ledger_and_changes_only_product():
    gt, manifest, bindings = real_va_context(); visibility = gt_to_va_visibility(gt)
    views = materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest)
    declared = gt_openings_to_va_claims(gt=gt, bindings=bindings, effective_manifest=manifest)
    reference_before = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    product_before = derive_product_ledger(visibility=visibility, manifest=manifest, elevation_views=views, openings=declared)
    deleted = tuple(row.model_copy(update={"claims":tuple(item.model_copy(update={"positive_evidence":()}) for item in row.claims)}) for row in declared)
    product_after = derive_product_ledger(visibility=visibility, manifest=manifest, elevation_views=views, openings=deleted)
    reference_after = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    units = lambda ledger: tuple((item.opening_id, claim.claim, eligible_units(claim=claim, target_kind="window" if item.opening_id == "O1" else "door")[0]) for item in ledger.openings for claim in item.claims)
    assert reference_before.content_sha256 == reference_after.content_sha256 and units(reference_before) == units(reference_after)
    assert product_before.content_sha256 != product_after.content_sha256


def test_b4b_b3_gt_to_va_uses_public_vg_and_preserves_concave_multisegment_fixture():
    gt = make_b4b_gt_document()
    ledger = gt_to_va_visibility(gt)
    assert ledger.source_kind == "judge_gt"
    assert ledger.facade_segments_sha256
    assert len(ledger.floors[0].segments) > 4


def test_b4b_b3_va_rejects_duplicate_opening_dangling_segment_and_eighth_claim():
    # These are public Va rejection paths: B4b neither forks nor bypasses them.
    from test_c2_va_applicability import fixture, invoke, opening
    vm, visibility, elevation = fixture()
    good = opening()
    duplicate = good.model_copy(update={"opening_id": good.opening_id})
    with pytest.raises(Exception, match="va_opening_segment_invalid"):
        invoke(vm, visibility, (elevation,), (good, duplicate))
    with pytest.raises(Exception, match="va_opening_segment_invalid"):
        invoke(vm, visibility, (elevation,), (good.model_copy(update={"facade_segment_id": "dangling"}),))
    with pytest.raises(Exception, match="va_claim_ledger_invalid"):
        invoke(vm, visibility, (elevation,), (good.model_copy(update={"claims": good.claims + (good.claims[-1],)}),))


def test_b4b_b5_unmatched_opening_without_completeness_is_not_automatically_extra():
    gt, manifest, bindings = real_va_context(complete_plan=False)
    target = next(item for item in gt.openings if item.kind == "window"); observation = OpeningObservation("extra-1", "F1", "window", target.boundary_segment_id, (target.world_along_interval.lo, target.world_along_interval.hi), "plan-F1")
    visibility = gt_to_va_visibility(gt); floors = {floor.id:i + 1 for i, floor in enumerate(gt.floors)}
    families = {segment.id:segment.facade_family for floor in gt.floors for segment in floor.boundary_segments}
    queries = build_absence_opening_claims(observations=(observation,), floor_refs=floors, segment_families=families, output_sha256="b" * 64, product_to_gt_segment={target.boundary_segment_id:target.boundary_segment_id}, trusted_source_views={target.boundary_segment_id:("plan-F1",)})
    ledger = derive_absence_ledger(visibility=visibility, manifest=manifest, elevation_views=materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest), openings=queries)
    assert classify_extra_observation(observation=observation, absence_ledger=ledger, output_sha256="b" * 64, gt_segment_id=target.boundary_segment_id) == "not_applicable"


def test_b4b_b5_complete_trusted_negative_coverage_is_extra():
    gt, manifest, bindings = real_va_context(complete_plan=True)
    target = next(item for item in gt.openings if item.kind == "window"); observation = OpeningObservation("extra-2", "F1", "window", target.boundary_segment_id, (target.world_along_interval.lo, target.world_along_interval.hi), "plan-F1")
    visibility = gt_to_va_visibility(gt); floors = {floor.id:i + 1 for i, floor in enumerate(gt.floors)}
    families = {segment.id:segment.facade_family for floor in gt.floors for segment in floor.boundary_segments}
    queries = build_absence_opening_claims(observations=(observation,), floor_refs=floors, segment_families=families, output_sha256="c" * 64, product_to_gt_segment={target.boundary_segment_id:target.boundary_segment_id}, trusted_source_views={target.boundary_segment_id:("plan-F1",)})
    ledger = derive_absence_ledger(visibility=visibility, manifest=manifest, elevation_views=materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest), openings=queries)
    assert classify_extra_observation(observation=observation, absence_ledger=ledger, output_sha256="c" * 64, gt_segment_id=target.boundary_segment_id) == "extra"


def test_b4b_fusion_and_trusted_negative_are_judge_only_va_consumers():
    from src.agent.judge.opening_claim_score import split_applicable_by_trusted_negative
    decision = SimpleNamespace(negative_evidence_intervals=(SimpleNamespace(lo=.2, hi=.6),))
    row = SimpleNamespace(source_evidence=(decision,))
    assert split_applicable_by_trusted_negative(applicable=((0., 1.),), claim=row) == (((0., .2), False), ((.2, .6), True), ((.6, 1.), False))
    assert fuse_source_results(("within_tolerance", "complete")) == "complete"
    assert fuse_source_results(("complete", "conflict")) == "conflict"
    assert fuse_source_results(("not_applicable",)) == "not_applicable"


def test_b4b_judge_only_source_scan_and_seven_claim_contract():
    import pathlib
    forbidden = ("src.agent.judge.opening_claim_score", "src.agent.judge.segment_score")
    for root in (pathlib.Path("src/agent/correction"), pathlib.Path("src/agent/reading"), pathlib.Path("src/agent/pipeline.py")):
        paths = root.rglob("*.py") if root.is_dir() else (root,)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            assert not any(token in text for token in forbidden)
    assert len(CLAIM_ORDER) == 7
