"""Single judge-side dispatch seam used by run-stage and score CLI.

The module intentionally owns dispatch/normalization only.  Legacy policy
continues to be supplied by the preserved legacy scorer, while v3 elevation
observations are projected exclusively through reviewed score bindings.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable, Literal

from src.agent.judge.elevation_score import (
    ProjectedElevationObservation,
    TypedElevationObservation,
    project_typed_elevation_observation,
)
from src.agent.judge.score_schema import (
    C2ScoredPayloadV8, C2ToleranceIdentityV8, ExtraObservationV8,
    HelperIdentityV8, ManifestIdentityV8, ProductIdentityV8, ScoreContractError,
    ScoreIdentityV8, SegmentExtraV8, SegmentScoreRowV8, canonical_sha256,
    decide_score_capability, finalize_score_sidecar,
)
from src.agent.judge.score_schema import ElevationScoreViewBindingV1


def normalize_typed_elevation_observations(*, payload: object, score_bindings: object) -> tuple[ProjectedElevationObservation, ...]:
    """Normalize the CLI/product boundary before scoring (never trust product mirror)."""
    if not isinstance(payload, dict):
        raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity",
                                 context={"reason": "elevation_payload_not_object"})
    raw_items = payload.get("elevation_observations", ())
    if not isinstance(raw_items, list):
        raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity",
                                 context={"reason": "elevation_observations_not_list"})
    bindings = getattr(score_bindings, "bindings", ())
    by_input = {item.input_id: item for item in bindings if isinstance(item, ElevationScoreViewBindingV1)}
    projected: list[ProjectedElevationObservation] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity")
        try:
            local = raw["local_x_interval"]
            z = raw.get("z_interval")
            observation = TypedElevationObservation(
                observation_id=str(raw["observation_id"]), source_input_id=str(raw["source_input_id"]),
                floor_id=str(raw["floor_id"]), kind=raw["kind"], facade_family=raw["facade_family"],
                local_x_interval=(float(local[0]), float(local[1])),
                z_interval=None if z is None else (float(z[0]), float(z[1])),
            )
            binding = by_input[observation.source_input_id]
        except (KeyError, TypeError, ValueError) as exc:
            raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity",
                                     context={"reason": "invalid_typed_elevation_observation"}) from exc
        projected.append(project_typed_elevation_observation(
            observation=observation, binding=binding,
            direction_semantics=raw.get("direction_semantics", "building_axis"),
        ))
    return tuple(projected)


@dataclass(frozen=True)
class TypedScoreResult:
    identity: ScoreIdentityV8
    payload: C2ScoredPayloadV8
    sidecar: object
    grade_png: bytes


def _opening_observations(*, payload: dict, score_bindings: object):
    """Normalize plan world observations plus reviewed-frame elevation inputs."""
    from src.agent.judge.opening_claim_score import OpeningObservation
    values: list[OpeningObservation] = []
    for raw in payload.get("openings", ()):
        if not isinstance(raw, dict):
            raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity")
        try:
            span = raw["world_along_interval"]
            z = raw.get("z_interval")
            values.append(OpeningObservation(
                id=str(raw["observation_id"]), floor_id=str(raw["floor_id"]), kind=raw["kind"],
                facade_segment_id=str(raw["facade_segment_id"]),
                world_along_interval=(float(span[0]), float(span[1])), source_view_id=str(raw["source_input_id"]),
                room_id=raw.get("declared_room_id"), z_interval=None if z is None else (float(z[0]), float(z[1])),
                channel=raw.get("channel", "plan"),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity",
                                     context={"reason": "invalid_opening_observation"}) from exc
    for projected in normalize_typed_elevation_observations(payload=payload, score_bindings=score_bindings):
        # C2 input carries a declared product segment; the projection helper
        # owns coordinates only and intentionally does not infer a host.
        raw = next(item for item in payload["elevation_observations"]
                   if item.get("observation_id") == projected.observation_id)
        values.append(OpeningObservation(
            id=projected.observation_id, floor_id=projected.floor_id, kind=projected.kind,
            facade_segment_id=str(raw["facade_segment_id"]), world_along_interval=projected.world_along_interval,
            source_view_id=projected.source_input_id, room_id=raw.get("declared_room_id"),
            z_interval=projected.z_interval, channel="elevation",
        ))
    return tuple(values)


def score_typed_attempt(*, gt_identity, gt, stage: Literal["reading", "correction"],
                        product_payload: dict, product_identity: ProductIdentityV8,
                        base_view_manifest, score_bindings, completeness_overlay, c2_config,
                        window_host_proof=None) -> TypedScoreResult:
    """Assemble the Phase A/B/C engines into the one real C2 score service."""
    from src.agent.correction.facade_applicability import FACADE_APPLICABILITY_HELPER_VERSION
    from src.agent.correction.claims import CLAIMS_VOCAB_VERSION
    from src.agent.judge.opening_claim_score import (
        OpeningObservation, assign_openings, bind_correction_window_segment,
        build_absence_opening_claims, derive_absence_ledger, derive_product_ledger,
        derive_reference_ledger, gt_openings_to_va_claims, gt_to_va_visibility, score_opening_claims_v3,
        summarize_claim_rows,
    )
    from src.agent.judge.score_inputs import build_effective_view_manifest, materialize_va_elevation_bindings
    from src.agent.judge.score_policy import c2_v3_score_policy
    from src.agent.judge.segment_score import (assign_plan_segments, coerce_plan_observations,
                                               extract_correction_plan_segments, extract_gt_plan_segments,
                                               score_plan_segments)

    if gt is None:
        raise ScoreContractError("score_gt_identity_invalid", "scoring.input_identity")
    effective = build_effective_view_manifest(base=base_view_manifest, overlay=completeness_overlay)
    capability = decide_score_capability(gt_identity=gt_identity, stage=stage,
                                          product_schema=product_identity.output_schema,
                                          view_manifest=effective,
                                          product_artifact_contract=product_identity.artifact_contract)
    if capability.path != "c2_v3":
        raise ScoreContractError("score_unsupported_combination", "scoring.capability",
                                 context={"reason": capability.reason or capability.path})
    tolerance = C2ToleranceIdentityV8(profile_kind="judge_score_config_v1", values=c2_config,
                                      content_sha256=canonical_sha256(c2_config.model_dump(mode="json")))
    manifest_identity = ManifestIdentityV8(
        base_view_manifest_sha256=base_view_manifest.content_sha256,
        effective_view_manifest_sha256=effective.content_sha256,
        case_metadata_sha256=base_view_manifest.case_metadata_sha256,
        completeness_ruleset=effective.completeness_ruleset_version,
        completeness_overlay_sha256=None if completeness_overlay is None else completeness_overlay.content_sha256,
        score_view_bindings_sha256=score_bindings.content_sha256,
    )
    helpers = HelperIdentityV8(
        scorer_schema="8", segment_scorer="b4b_segment_score_v1", gt_to_va_adapter="b4b_gt_to_va_v1",
        denominator_helper="b4b_denominator_v1", grade_renderer="b4b_grade_png_v1",
        va_helper=FACADE_APPLICABILITY_HELPER_VERSION, vg_helper="facade_visibility_v1",
        claims_contract=CLAIMS_VOCAB_VERSION,
    )

    gt_segments = extract_gt_plan_segments(gt)
    geometry = None
    if stage == "correction":
        from src.agent.correction.schema import CorrectedGeometryV3
        from src.agent.geometry.build import (
            VerifiedWindowHostProof,
            _reverify_window_host_proof,
        )
        if not product_identity.accepted or not isinstance(
            window_host_proof, VerifiedWindowHostProof,
        ):
            raise ScoreContractError(
                "score_product_identity_invalid",
                "scoring.input_identity",
                context={"reason": "official_b5_requires_verified_six_artifact_input"},
            )
        try:
            verified_proof = _reverify_window_host_proof(window_host_proof)
        except ValueError as exc:
            raise ScoreContractError(
                "score_product_identity_invalid",
                "scoring.input_identity",
                context={"reason": "b5_window_host_proof_invalid"},
            ) from exc
        if hashlib.sha256(verified_proof.raw_output_bytes).hexdigest() != product_identity.output_sha256:
            raise ScoreContractError(
                "score_product_identity_invalid",
                "scoring.input_identity",
                context={"reason": "b5_output_hash_mismatch"},
            )
        geometry = CorrectedGeometryV3.model_validate_json(verified_proof.raw_output_bytes)
        if geometry.model_dump(mode="json") != CorrectedGeometryV3.model_validate(product_payload).model_dump(mode="json"):
            raise ScoreContractError(
                "score_product_identity_invalid",
                "scoring.input_identity",
                context={"reason": "b5_product_payload_differs_from_verified_output"},
            )
        plan_observations = extract_correction_plan_segments(geometry)
    else:
        plan_observations = coerce_plan_observations(product_payload.get("segments", ()))
    segment_assignment = assign_plan_segments(targets=gt_segments, observations=plan_observations, config=c2_config)
    segment_rows = score_plan_segments(targets=gt_segments, observations=plan_observations, config=c2_config)
    product_to_gt = {observation.key: target.key for target, observation in segment_assignment.matched}
    product_to_gt.update({item.key: item.key for item in plan_observations if item.key in {target.key for target in gt_segments}})
    if geometry is not None:
        # Correction facade ids are product-local.  Bind them only where one
        # real GT facade span contains the product span; ambiguity is a hard
        # scorer error, never an id/name heuristic.
        gt_facades = tuple(segment for floor in gt.floors for segment in floor.boundary_segments)
        for product_segment in geometry.facade_segments:
            candidates = tuple(target for target in gt_facades
                if target.floor_id == product_segment.floor_id
                and target.facade_family == product_segment.facade_family
                and target.world_along_interval.lo <= product_segment.world_along_interval.lo
                and product_segment.world_along_interval.hi <= target.world_along_interval.hi)
            if len(candidates) == 1:
                product_to_gt[product_segment.id] = candidates[0].id

    if geometry is None:
        observations = _opening_observations(payload=product_payload, score_bindings=score_bindings)
    else:
        plan_sources = {item.floor_id: item.input_id for item in score_bindings.bindings
                        if getattr(item, "kind", None) == "plan"}
        converted: list[OpeningObservation] = []
        for window in geometry.windows:
            segment, _method = bind_correction_window_segment(
                window=window,
                segments=geometry.facade_segments,
                allow_temporary_binding=False,
            )
            source = plan_sources.get(window.floor_id)
            if source is None:
                raise ScoreContractError("score_view_binding_invalid", "scoring.view_bindings",
                                         context={"floor_id": window.floor_id})
            converted.append(OpeningObservation(id=window.id, floor_id=window.floor_id, kind="window",
                facade_segment_id=segment.id, world_along_interval=tuple(window.span), source_view_id=source,
                room_id=window.room, z_interval=None if window.z is None else tuple(window.z), channel="plan"))
        observations = tuple(converted)
    opening_assignment = assign_openings(targets=tuple(gt.openings), observations=observations,
                                         config=c2_config, product_to_gt_segment=product_to_gt)
    visibility = gt_to_va_visibility(gt)
    reference = derive_reference_ledger(gt=gt, bindings=score_bindings, effective_manifest=effective)
    # Product declarations are deliberately derived separately.  A source only
    # remains positive when this attempt actually supplied an observation from
    # that reviewed input; reference denominator data never consults this.
    source_ids = {item.source_view_id for item in observations}
    reference_claims = gt_openings_to_va_claims(gt=gt, bindings=score_bindings, effective_manifest=effective)
    product_claims = tuple(row.model_copy(update={"claims": tuple(claim.model_copy(update={
        "positive_evidence": tuple(item for item in claim.positive_evidence if item.source_input_id in source_ids)
    }) for claim in row.claims)}) for row in reference_claims)
    va_bindings = materialize_va_elevation_bindings(score_bindings=score_bindings, effective_manifest=effective)
    product = derive_product_ledger(visibility=visibility, manifest=effective, elevation_views=va_bindings, openings=product_claims)
    host_resolver = None
    if geometry is not None:
        from src.agent.judge.opening_claim_score import (
            build_correction_host_resolver,
            map_product_cells_to_gt_zones,
        )
        host_resolver = build_correction_host_resolver(
            geometry=geometry,
            product_to_gt_segment=product_to_gt,
            product_to_gt_zone=map_product_cells_to_gt_zones(geometry=geometry, gt=gt),
            allow_temporary_binding=False,
        )
    rows = score_opening_claims_v3(gt=gt, reference_ledger=reference, product_ledger=product,
                                   assignment=opening_assignment, config=c2_config,
                                   host_resolver=host_resolver)
    summaries = summarize_claim_rows(rows)

    floors = {floor.id: index + 1 for index, floor in enumerate(gt.floors)}
    families = {segment.id: segment.facade_family for floor in gt.floors for segment in floor.boundary_segments}
    unmatched = opening_assignment.unmatched_observations
    absence = None
    extras: tuple[ExtraObservationV8, ...] = ()
    if unmatched:
        from src.agent.judge.opening_claim_score import classify_extra_observation
        queries = build_absence_opening_claims(observations=unmatched, floor_refs=floors, segment_families=families,
            output_sha256=product_identity.output_sha256, product_to_gt_segment=product_to_gt,
            trusted_source_views={item.facade_segment_id: (item.source_view_id,) for item in unmatched})
        absence = derive_absence_ledger(visibility=visibility, manifest=effective, elevation_views=va_bindings, openings=queries)
        extras = tuple(ExtraObservationV8(observation_id=item.id,
            result=classify_extra_observation(observation=item, absence_ledger=absence,
                output_sha256=product_identity.output_sha256, gt_segment_id=product_to_gt.get(item.facade_segment_id, item.facade_segment_id)),
            reason=None) for item in unmatched)
    policy = c2_v3_score_policy(claim_rows=rows, segment_rows=segment_rows)
    identity = ScoreIdentityV8(gt=gt_identity, product=product_identity, manifest=manifest_identity,
        helpers=helpers, capability=capability, tolerances=tolerance,
        reference_applicability_sha256=reference.content_sha256, product_applicability_sha256=product.content_sha256,
        absence_applicability_sha256=None if absence is None else absence.content_sha256)
    serial_segments = tuple(SegmentScoreRowV8(
        target_id=None if row.target is None else row.target.key, observation_id=None if row.observation is None else row.observation.key,
        floor_id=(row.target or row.observation).floor_id, exterior=(row.target or row.observation).exterior,
        status=row.status, axis_alignment_error_m=row.axis_alignment_error_m, position_error_m=row.position_error_m,
        extent_symmetric_difference_m=row.extent_symmetric_difference_m) for row in segment_rows)
    payload = C2ScoredPayloadV8(kind="c2_scored", segment_rows=serial_segments, segment_extras=(),
        claim_rows=rows, claim_summaries=summaries, extras=extras,
        score_criteria=tuple(item.model_dump(mode="json") for item in policy.criteria),
        reference_ledger_sha256=reference.content_sha256, product_ledger_sha256=product.content_sha256,
        absence_ledger_sha256=None if absence is None else absence.content_sha256)
    # The renderer is a judge-side script and consumes the typed document; no
    # legacy bbox transform is reachable on this branch.
    import sys
    from pathlib import Path
    scripts = str(Path(__file__).resolve().parents[3] / "scripts" / "tool_scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from render_grade import render_score_grade_png
    png = render_score_grade_png(gt=gt, identity=identity, payload=payload)
    sidecar = finalize_score_sidecar(identity=identity, payload=payload, grade_png=png,
        ledger_counts=(len(reference.openings), len(product.openings), 0 if absence is None else len(absence.openings)))
    return TypedScoreResult(identity=identity, payload=payload, sidecar=sidecar, grade_png=png)


def score_attempt_service(*, stage: Literal["0_reading", "1_correction"] | None = None, output: dict | None = None,
                          gt: dict | None = None, grade: object | None = None,
                          legacy_evaluator: Callable[..., dict] | None = None,
                          typed_request: dict | None = None):
    """The one service dispatch for legacy attempt scoring.

    The evaluator is injected so this seam neither copies nor subtly changes
    legacy policy.  v3 callers use the typed normalizer above before entering
    the C2 scorer; no raw-dict fallback is available there.
    """
    if typed_request is not None:
        return score_typed_attempt(**typed_request)
    if legacy_evaluator is None or stage is None or output is None or gt is None:
        raise ValueError("score service requires either typed_request or legacy evaluator inputs")
    return legacy_evaluator(stage, output, gt, grade=grade)
