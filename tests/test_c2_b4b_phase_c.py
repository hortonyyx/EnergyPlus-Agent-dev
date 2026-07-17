"""B4b Phase-C contract probes: every C1..C5 exit has a named assertion."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.agent.correction.facade_applicability import (
    ApplicabilityIntervalV1, ElevationViewBindingV1, derive_opening_claim_applicability,
)
from src.agent.judge.elevation_score import (
    TypedElevationObservation, project_typed_elevation_observation, score_typed_elevation_floor_lines,
)
from src.agent.judge.opening_claim_score import (
    OpeningObservation, assign_openings, bind_correction_window_segment, compute_facade_segments_sha256,
    derive_product_ledger, eligible_units, gt_openings_to_va_claims, gt_to_va_visibility,
    resolve_correction_window_host, score_opening_claims_v3,
)
from src.agent.judge.score_inputs import materialize_va_elevation_bindings
from src.agent.judge.score_policy import c2_v3_score_policy
from src.agent.judge.score_schema import ScoreContractError, decide_score_capability
from tests.test_c2_b4b_phase_b import config, correction_two_zone, real_va_context


def _binding(*, sign: int, mirrored: bool, local_x_positive: str) -> ElevationViewBindingV1:
    return ElevationViewBindingV1(
        input_id="elev-N", resolved_building_direction="North", resolution_source="manifest_building_axis",
        view_manifest_sha256="a" * 64, orientation_output_hash=None, adapter_version=None,
        source_footprint_fingerprint="b" * 64, world_axis="x", sign=sign,
        along_origin=10.0 if sign == -1 else 0.0, mirrored=mirrored,
        local_x_positive=local_x_positive, frame_transform_sha256="c" * 64,
    )


def _product_ledger_with_only_plan_declaration(*, gt, manifest, bindings):
    """Real product-Va ledger: plan declares positive, other sources absent."""
    claims = gt_openings_to_va_claims(gt=gt, bindings=bindings, effective_manifest=manifest)
    declarations = tuple(row.model_copy(update={"claims": tuple(
        claim.model_copy(update={"positive_evidence": tuple(
            evidence for evidence in claim.positive_evidence if evidence.source_input_id == "plan-F1"
        )}) for claim in row.claims
    )}) for row in claims)
    visibility = gt_to_va_visibility(gt)
    return derive_product_ledger(visibility=visibility, manifest=manifest,
                                 elevation_views=materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest),
                                 openings=declarations)


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("mirrored", (False, True))
@pytest.mark.parametrize("local", ("image_left_to_right", "image_right_to_left"))
def test_b4b_c1_frame_trust_forward_inverse_restores_world_target(sign, mirrored, local):
    """B4B-C1: sign/mirror/local-x variants use only reviewed binding frame."""
    binding = _binding(sign=sign, mirrored=mirrored, local_x_positive=local)
    target = (2.0, 4.0)
    local_target = tuple((value - binding.along_origin) / binding.sign for value in target)
    projected = project_typed_elevation_observation(
        observation=TypedElevationObservation("e", "elev-N", "F1", "window", "North",
                                              (min(local_target), max(local_target)), (1.0, 2.0)),
        binding=binding,
    )
    assert projected.world_along_interval == target


@pytest.mark.parametrize("semantics", ("true_azimuth", "unknown"))
def test_b4b_c1_frame_trust_true_or_unknown_without_resolver_rejects_whole_view(semantics):
    with pytest.raises(ScoreContractError, match="score_direction_unresolved"):
        project_typed_elevation_observation(
            observation=TypedElevationObservation("e", "elev-N", "F1", "window", "North", (2., 4.), (1., 2.)),
            binding=_binding(sign=1, mirrored=False, local_x_positive="image_left_to_right"),
            direction_semantics=semantics,
        )


def test_b4b_c1_frame_trust_shorter_visible_intervals_only_shrink_va_output():
    """B4B-C1: evidence stays maximal; only Va's public channel narrows it."""
    gt, manifest, bindings = real_va_context()
    visibility = gt_to_va_visibility(gt)
    claims = gt_openings_to_va_claims(gt=gt, bindings=bindings, effective_manifest=manifest)
    evidence_before = tuple((item.source_input_id, item.local_interval.lo, item.local_interval.hi)
                            for row in claims for claim in row.claims if claim.claim == "sill"
                            for item in claim.positive_evidence)
    target = next(item for item in gt.openings if item.kind == "window")
    floor = next(item for item in visibility.floors if item.floor_id == target.floor_id)
    segment = next(item for item in floor.segments if item.id == target.boundary_segment_id)
    midpoint = (target.world_along_interval.lo + target.world_along_interval.hi) / 2
    shortened_segment = segment.model_copy(update={"visible_intervals": [
        ApplicabilityIntervalV1(lo=target.world_along_interval.lo, hi=midpoint),
    ]})
    shortened_floor = floor.model_copy(update={"segments": tuple(shortened_segment if item.id == segment.id else item for item in floor.segments)})
    shortened_floors = tuple(shortened_floor if item.floor_id == floor.floor_id else item for item in visibility.floors)
    all_segments = tuple(item for item_floor in shortened_floors for item in item_floor.segments)
    shortened_visibility = visibility.model_copy(update={"floors": shortened_floors,
                                                           "facade_segments_sha256": compute_facade_segments_sha256(all_segments)})
    va_bindings = materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest)
    full = derive_opening_claim_applicability(visibility=visibility, manifest=manifest, elevation_views=va_bindings, openings=claims)
    short = derive_opening_claim_applicability(visibility=shortened_visibility, manifest=manifest, elevation_views=va_bindings, openings=claims)
    full_sill = next(claim for entry in full.openings if entry.opening_id == target.id for claim in entry.claims if claim.claim == "sill")
    short_sill = next(claim for entry in short.openings if entry.opening_id == target.id for claim in entry.claims if claim.claim == "sill")
    assert full_sill.applicable_intervals != short_sill.applicable_intervals
    assert sum(item.hi - item.lo for item in short_sill.applicable_intervals) < sum(item.hi - item.lo for item in full_sill.applicable_intervals)
    assert tuple((item.source_input_id, item.local_interval.lo, item.local_interval.hi)
                 for row in claims for claim in row.claims if claim.claim == "sill"
                 for item in claim.positive_evidence) == evidence_before


def test_b4b_c1_projection_to_v3_scorer_ignores_product_frame_self_report():
    """B4B-C1: typed local-x projection reaches the scorer; product flags do not."""
    gt, manifest, bindings = real_va_context(complete_plan=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(item for item in gt.openings if item.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    binding = next(item for item in materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest)
                   if item.input_id == "elev-N")
    local = tuple((value - binding.along_origin) / binding.sign for value in span)
    def rows(raw):
        projected = project_typed_elevation_observation(
            observation=TypedElevationObservation("elev", "elev-N", "F1", "window", "North",
                                                  raw["local_x_interval"], (1., 2.)), binding=binding,
        )
        observations = (
            OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1"),
            OpeningObservation(projected.observation_id, projected.floor_id, projected.kind,
                               target.boundary_segment_id, projected.world_along_interval, "elev-N",
                               z_interval=projected.z_interval, channel="elevation"),
        )
        assigned = assign_openings(targets=(target,), observations=observations, config=config(),
                                   product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
        return tuple(row for row in score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config())
                     if row.target_id == target.id)
    first = rows({"local_x_interval": (min(local), max(local)), "mirrored": False, "local_x_positive": "image_left_to_right"})
    flipped = rows({"local_x_interval": (min(local), max(local)), "mirrored": True, "local_x_positive": "image_right_to_left"})
    assert next(row for row in first if row.claim == "along").result == "complete"
    assert tuple(row.model_dump_json() for row in first) == tuple(row.model_dump_json() for row in flipped)


def test_b4b_c2_elevation_claims_score_actual_projection_and_na_overrides():
    """B4B-C2: elevation z values score, while appearance remains real NA."""
    gt, manifest, bindings = real_va_context(complete_plan=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    evidence = (
        OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1", channel="plan"),
        OpeningObservation("elev", "F1", "window", target.boundary_segment_id, span, "elev-N", z_interval=(1., 2.), channel="elevation"),
    )
    assigned = assign_openings(targets=(target,), observations=evidence, config=config(),
                               product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    rows = score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config())
    by_claim = {row.claim: row for row in rows if row.target_id == target.id}
    assert by_claim["existence"].result == "complete"
    assert by_claim["appearance"].result == "not_applicable"
    assert by_claim["appearance"].na_reason == "reference_value_unavailable"
    assert by_claim["appearance"].eligible_units == 0.0


def test_b4b_c2_elevation_partial_scalars_are_binary_and_floor_lines_use_actual_z():
    """B4B-C2: partial sill/head are binary; z-null is NA before coverage."""
    partial_sill = SimpleNamespace(claim="sill", target_world_interval=SimpleNamespace(lo=0., hi=1.),
                                   applicable_intervals=(SimpleNamespace(lo=.2, hi=.3),), status="partially_applicable")
    assert eligible_units(claim=partial_sill, target_kind="window", has_reference_value=True)[0] == 1.0
    assert eligible_units(claim=partial_sill, target_kind="window", has_reference_value=False)[:2] == (0.0, "reference_value_unavailable")
    score = score_typed_elevation_floor_lines(binding=_binding(sign=1, mirrored=False, local_x_positive="image_left_to_right"),
                                              gt_floor_zs=(0., 3., 6.), product_zs=(0., 3.1, 6.), tolerance_m=.3)
    assert [item.status for item in score.matches] == ["complete", "within_tol", "complete"]


def test_b4b_c2_multiple_same_family_elevation_sources_fuse_without_id_shortcut():
    """B4B-C2: North full/detail sources independently corroborate one target."""
    gt, manifest, bindings = real_va_context(complete_plan=True, complete_elevation=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    observations = (
        OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1"),
        OpeningObservation("north-full", "F1", "window", target.boundary_segment_id, span, "elev-N", z_interval=(1., 2.), channel="elevation"),
        OpeningObservation("north-detail", "F1", "window", target.boundary_segment_id, span, "elev-N-detail", z_interval=(1., 2.), channel="elevation"),
    )
    assigned = assign_openings(targets=(target,), observations=observations, config=config(), product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    along = next(row for row in score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config()) if row.target_id == target.id and row.claim == "along")
    assert along.result == "complete" and {"north-full", "north-detail"}.issubset(along.matched_observation_ids)


def test_b4b_c2_host_correct_wrong_and_ambiguous_stay_judge_only():
    """B4B-C2: host is score-only and covers complete, miss, and ambiguity."""
    gt, manifest, bindings = real_va_context(complete_plan=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    assigned = assign_openings(targets=(target,), observations=(OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1"),), config=config(), product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    complete = score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config(), host_resolver=lambda _target, _obs: "complete")
    wrong = score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config(), host_resolver=lambda _target, _obs: "miss")
    assert next(row for row in complete if row.target_id == target.id and row.claim == "host").result == "complete"
    assert next(row for row in wrong if row.target_id == target.id and row.claim == "host").result == "miss"
    geometry = correction_two_zone()
    window = geometry.windows[0]
    product_segment, _method = bind_correction_window_segment(window=window, segments=geometry.facade_segments)
    with pytest.raises(ScoreContractError, match="score_product_segment_unresolved"):
        resolve_correction_window_host(geometry=geometry, window=window.model_copy(update={"span": [4.1, 4.2]}),
                                       product_segment=product_segment, gt_segment_id=target.boundary_segment_id,
                                       gt_zone_id=target.host_zone_id or "ZF1",
                                       product_to_gt_segment={product_segment.id: target.boundary_segment_id},
                                       product_to_gt_zone={"C1": target.host_zone_id or "ZF1"})


def test_b4b_c3_fusion_totality_conflict_and_exact_partial_denominator():
    """B4B-C3: conflicting independent sources fail units; no fixed half unit."""
    gt, manifest, bindings = real_va_context(complete_plan=True, complete_elevation=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    evidence = (
        OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1", channel="plan"),
        OpeningObservation("elev-bad", "F1", "window", target.boundary_segment_id,
                           (span[0] - .5, span[1] + .5), "elev-N", z_interval=(1., 2.), channel="elevation"),
    )
    assigned = assign_openings(targets=(target,), observations=evidence, config=config(),
                               product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    rows = score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config())
    along = next(row for row in rows if row.target_id == target.id and row.claim == "along")
    assert along.result == "conflict" and sum(piece.units for piece in along.outcome_slices) == along.eligible_units
    claim = SimpleNamespace(claim="along", target_world_interval=SimpleNamespace(lo=0., hi=1.),
                            applicable_intervals=(SimpleNamespace(lo=0., hi=.1),), status="partially_applicable")
    assert eligible_units(claim=claim, target_kind="window")[0] == .1


def test_b4b_c3_correct_single_plan_observation_is_not_reference_negative_conflict():
    """B4B-C3: redundant GT-positive complete sources cannot punish a correct plan."""
    gt, manifest, bindings = real_va_context(complete_plan=True, complete_elevation=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    assigned = assign_openings(targets=(target,), observations=(OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1"),), config=config(), product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    along = next(row for row in score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config()) if row.target_id == target.id and row.claim == "along")
    assert along.result == "complete" and sum(piece.units for piece in along.outcome_slices) == along.eligible_units


def test_b4b_c3_explicit_product_absence_in_non_gt_source_conflicts_with_positive():
    """B4B-C3: real §8.6.1 item-2 conflict needs product-Va absence declaration."""
    gt, manifest, bindings = real_va_context(complete_plan=True, complete_elevation=True, negative_only_elevation=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    reference = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    product = _product_ledger_with_only_plan_declaration(gt=gt, manifest=manifest, bindings=bindings)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    reference_along = next(claim for entry in reference.openings if entry.opening_id == target.id for claim in entry.claims if claim.claim == "along")
    product_along = next(claim for entry in product.openings if entry.opening_id == target.id for claim in entry.claims if claim.claim == "along")
    assert next(item for item in reference_along.source_evidence if item.source_input_id == "elev-N-absence").positive_evidence_declared is False
    assert next(item for item in product_along.source_evidence if item.source_input_id == "elev-N-absence").positive_evidence_declared is False
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    assigned = assign_openings(targets=(target,), observations=(OpeningObservation("plan", "F1", "window", target.boundary_segment_id, span, "plan-F1"),), config=config(), product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    along = next(row for row in score_opening_claims_v3(gt=gt, reference_ledger=reference, product_ledger=product, assignment=assigned, config=config()) if row.target_id == target.id and row.claim == "along")
    assert along.result == "conflict" and sum(piece.units for piece in along.outcome_slices) == along.eligible_units


def test_b4b_c4_na_machine_surface_unsupported_combination_and_door():
    """B4B-C4: v3 unsupported inputs retain a machine-readable NA surface."""
    gt, manifest, _ = real_va_context()
    from src.agent.judge.score_schema import GtIdentityV8
    decision = decide_score_capability(
        gt_identity=GtIdentityV8(path_id="typed", file_sha256="a" * 64, content_sha256=gt.content_sha256,
                                  schema_version=3, profile="c2_simple_orthogonal_no_holes",
                                  coordinate_frame="building_axis_world_m", verification_status="candidate",
                                  loader_helper_version="gt_typed_loader_v1"),
        stage="correction", product_schema="2", view_manifest=manifest,
    )
    assert decision.path == "not_applicable" and decision.reason == "unsupported_product_schema"
    door_claim = SimpleNamespace(claim="existence", target_world_interval=SimpleNamespace(lo=0., hi=1.),
                                 applicable_intervals=(), status="not_applicable")
    assert eligible_units(claim=door_claim, target_kind="door")[:2] == (0.0, "unsupported_target_kind")


def test_b4b_c5_policy_conservation_and_top_level_na_or_rejected():
    """B4B-C5: miss/conflict are failing units, all-NA is NA, invalid is rejected."""
    gt, manifest, bindings = real_va_context(complete_plan=True)
    from src.agent.judge.opening_claim_score import derive_reference_ledger
    ledger = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    target = next(opening for opening in gt.openings if opening.kind == "window")
    span = (target.world_along_interval.lo, target.world_along_interval.hi)
    assigned = assign_openings(targets=(target,), observations=(OpeningObservation("miss", "F1", "window", target.boundary_segment_id, (span[0], span[0] + .01), "plan-F1"),), config=config(), product_to_gt_segment={target.boundary_segment_id: target.boundary_segment_id})
    rows = score_opening_claims_v3(gt=gt, reference_ledger=ledger, assignment=assigned, config=config())
    policy = c2_v3_score_policy(claim_rows=rows)
    assert policy.verdict == "fail"
    assert all(item.passing_units + item.failing_units == item.denominator_units for item in policy.criteria)
    assert c2_v3_score_policy(claim_rows=()).verdict == "not_applicable"
    assert c2_v3_score_policy(claim_rows=rows, totality_valid=False).verdict == "rejected"
    segmented = c2_v3_score_policy(claim_rows=(), segment_rows=(
        SimpleNamespace(target=SimpleNamespace(exterior=False), status="complete"),
        SimpleNamespace(target=SimpleNamespace(exterior=True), status="miss"),
    ))
    by_id = {item.criterion_id: item for item in segmented.criteria}
    assert (by_id["walls_complete"].denominator_units, by_id["walls_complete"].verdict) == (1.0, "pass")
    assert (by_id["boundary_complete"].denominator_units, by_id["boundary_complete"].verdict) == (1.0, "fail")
