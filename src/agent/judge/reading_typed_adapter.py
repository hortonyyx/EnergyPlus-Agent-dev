"""Judge-only adapter contracts for aggregate reading-stage products."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from src.agent.execution.view_manifest import RequiredViewEntry
from src.agent.judge.elevation_score import (
    TypedElevationObservation,
    project_typed_elevation_observation,
)
from src.agent.judge.score_schema import (
    READING_ADAPTER_VERSION,
    READING_DENOMINATOR_VERSION,
    READING_PRODUCT_CONTRACT,
    READING_CONTRACT_DETECTOR_VERSION,
    ClosedIntervalV1,
    ElevationFrameDisagreementWitnessV1,
    ElevationScoreViewBindingV1,
    PlanScoreViewBindingV1,
    ReadingComponentApplicabilityV1,
    ReadingDenominatorAtomV1,
    ReadingDenominatorBasisV1,
    ReadingElevationOpeningAuditV1,
    ReadingFilteredComponentBasisV1,
    ReadingMetadataFindingV1,
    ReadingNormalizationCertificateV1,
    UnmeasurableObservationWitnessV1,
    VerticalDatumCertificateV1,
    canonical_sha256,
)
from src.agent.reading import ReadingView


READING_CONTRACT_DETECTOR_VERSION = "reading_contract_detector_v1"


@dataclass(frozen=True)
class ReadingContractDecision:
    contract_id: Literal["reading_views_v1", "unrecognized"]
    reason: str | None


@dataclass(frozen=True)
class ReadingNormalizationOutcome:
    certificate: ReadingNormalizationCertificateV1
    trusted_capability_dispositions: tuple[
        ReadingFilteredComponentBasisV1, ...
    ]


def identify_reading_contract(raw: object) -> ReadingContractDecision:
    """Recognize the aggregate reading envelope without inventing a schema."""
    if not isinstance(raw, dict):
        return ReadingContractDecision("unrecognized", "reading_output_not_object")
    if "views" not in raw:
        return ReadingContractDecision("unrecognized", "reading_views_missing")
    views = raw["views"]
    if not isinstance(views, dict):
        return ReadingContractDecision("unrecognized", "reading_views_not_object")
    if any(not isinstance(key, str) or not key for key in views):
        return ReadingContractDecision("unrecognized", "reading_view_id_invalid")
    return ReadingContractDecision(READING_PRODUCT_CONTRACT, None)


_ELEVATION_COMPONENTS = (
    "elevation_opening_xy",
    "elevation_opening_z",
)
_PLAN_COMPONENTS = ("plan_segments", "plan_openings")
_MISSING = object()


def _strict_finite(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("strict finite number required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("strict finite number required")
    return result


def _strict_point(value: object) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("point requires two coordinates")
    return _strict_finite(value[0]), _strict_finite(value[1])


def _audit_sha(value: object) -> str:
    try:
        return canonical_sha256(value)
    except (TypeError, ValueError):
        return canonical_sha256(
            {
                "unsupported_json_value": type(value).__name__,
            }
        )


def _component(
    *,
    source_input_id: str,
    channel: Literal["plan", "elevation"],
    component: str,
    floor_ids: tuple[str, ...],
    status: Literal["applicable", "not_applicable"],
    reasons: tuple[str, ...] = (),
    cause_class: str = "none",
    denominator_disposition: str = "score",
    observation_count: int = 0,
    transform_sha256: str | None = None,
) -> ReadingComponentApplicabilityV1:
    return ReadingComponentApplicabilityV1(
        source_input_id=source_input_id,
        channel=channel,
        component=component,
        floor_ids=tuple(sorted(floor_ids)),
        status=status,
        reasons=tuple(sorted(reasons)),
        cause_class=cause_class,
        denominator_disposition=denominator_disposition,
        observation_count=observation_count,
        transform_sha256=transform_sha256,
    )


def _na_components(
    *,
    source_input_id: str,
    channel: Literal["plan", "elevation"],
    components: tuple[str, ...],
    floor_ids: tuple[str, ...],
    reason: str,
    cause_class: str,
    denominator_disposition: str,
) -> tuple[ReadingComponentApplicabilityV1, ...]:
    return tuple(
        _component(
            source_input_id=source_input_id,
            channel=channel,
            component=component,
            floor_ids=floor_ids,
            status="not_applicable",
            reasons=(reason,),
            cause_class=cause_class,
            denominator_disposition=denominator_disposition,
        )
        for component in components
    )


def _normalized_observation_id(
    *,
    output_sha256: str,
    input_id: str,
    stroke_id: str,
    component: str,
    primitive_index: int,
) -> str:
    return "reading:" + canonical_sha256(
        (
            output_sha256,
            input_id,
            stroke_id,
            component,
            primitive_index,
        )
    )


def _vertical_datum(
    *,
    input_id: str,
    floor_ids: tuple[str, ...],
    source: Literal[
        "product_declared",
        "project_convention_2026_07_25",
        "multi_floor_unavailable",
    ],
    z_origin: float | None,
) -> VerticalDatumCertificateV1:
    if source == "multi_floor_unavailable":
        raw = {
            "input_id": input_id,
            "floor_ids": tuple(sorted(floor_ids)),
            "status": "not_applicable",
            "source": source,
            "units": "metre",
            "local_axis": "drawing_up",
            "z_sign": None,
            "z_origin": None,
            "authority": "reviewed_binding_multiple_floors",
            "reason": "elevation_floor_partition_unresolved",
        }
    else:
        raw = {
            "input_id": input_id,
            "floor_ids": tuple(sorted(floor_ids)),
            "status": "applicable",
            "source": source,
            "units": "metre",
            "local_axis": "drawing_up",
            "z_sign": 1,
            "z_origin": z_origin,
            "authority": (
                "reading_scale_origin_world_z_m"
                if source == "product_declared"
                else "user_ruling_grade_line_equals_interior_floor_zero"
            ),
            "reason": None,
        }
    return VerticalDatumCertificateV1(
        **raw,
        preimage_sha256=canonical_sha256(raw),
    )


def _facade_sense(
    raw_view: dict,
) -> tuple[
    object,
    Literal["image_left_to_right", "image_right_to_left"] | None,
    object,
    bool | None,
    object,
]:
    facade = raw_view.get("facade", "missing")
    if not isinstance(facade, dict):
        return "missing", None, "missing", None, facade
    raw_local = facade.get("local_x_positive", "missing")
    effective_local = (
        "image_left_to_right"
        if raw_local == "missing"
        else raw_local
    )
    raw_mirrored = facade.get("mirrored", "missing")
    effective_mirrored = {
        True: True,
        False: False,
        "true": True,
        "false": False,
        "unknown": None,
        "missing": None,
    }.get(raw_mirrored)
    return (
        raw_local,
        effective_local,
        raw_mirrored,
        effective_mirrored,
        facade,
    )


def _elevation_bounds(
    geometry: object,
) -> tuple[str, tuple[float, float], tuple[float, float]]:
    if not isinstance(geometry, dict):
        raise ValueError("geometry must be an object")
    kind = geometry.get("kind")
    if kind == "rect":
        raw_x = geometry.get("x_range_m")
        raw_y = geometry.get("y_range_m")
        if (
            not isinstance(raw_x, list)
            or len(raw_x) != 2
            or not isinstance(raw_y, list)
            or len(raw_y) != 2
        ):
            raise ValueError("rect ranges invalid")
        xs = (_strict_finite(raw_x[0]), _strict_finite(raw_x[1]))
        ys = (_strict_finite(raw_y[0]), _strict_finite(raw_y[1]))
    elif kind == "line":
        points = (_strict_point(geometry.get("p1")), _strict_point(geometry.get("p2")))
        xs = tuple(point[0] for point in points)
        ys = tuple(point[1] for point in points)
    elif kind == "polyline":
        raw_points = geometry.get("points")
        if not isinstance(raw_points, list) or not raw_points:
            raise ValueError("polyline points invalid")
        points = tuple(_strict_point(point) for point in raw_points)
        xs = tuple(point[0] for point in points)
        ys = tuple(point[1] for point in points)
    else:
        raise ValueError("unsupported elevation geometry")
    return str(kind), (min(xs), max(xs)), (min(ys), max(ys))


def _metadata_hash(value: object) -> str:
    return canonical_sha256("missing" if value is _MISSING else value)


def _elevation_result(
    *,
    entry: RequiredViewEntry,
    binding: ElevationScoreViewBindingV1,
    raw_view: object,
    source_output_sha256: str,
) -> tuple[
    tuple[ReadingComponentApplicabilityV1, ...],
    tuple[ReadingElevationOpeningAuditV1, ...],
    tuple[VerticalDatumCertificateV1, ...],
    tuple[UnmeasurableObservationWitnessV1, ...],
    tuple[ElevationFrameDisagreementWitnessV1, ...],
    tuple[ReadingMetadataFindingV1, ...],
    tuple[ReadingFilteredComponentBasisV1, ...],
]:
    floor_ids = tuple(binding.floor_ids)
    if len(floor_ids) != 1:
        datum = _vertical_datum(
            input_id=binding.input_id,
            floor_ids=floor_ids,
            source="multi_floor_unavailable",
            z_origin=None,
        )
        components = _na_components(
            source_input_id=binding.input_id,
            channel="elevation",
            components=_ELEVATION_COMPONENTS,
            floor_ids=floor_ids,
            reason="elevation_floor_partition_unresolved",
            cause_class="trusted_input",
            denominator_disposition="filter",
        )
        exclusions = tuple(
            ReadingFilteredComponentBasisV1(
                source_input_id=binding.input_id,
                component=component,
                floor_ids=tuple(sorted(floor_ids)),
                cause_class="trusted_input",
                reasons=("elevation_floor_partition_unresolved",),
            )
            for component in _ELEVATION_COMPONENTS
        )
        return components, (), (datum,), (), (), (), exclusions
    if raw_view is _MISSING:
        return (
            _na_components(
                source_input_id=binding.input_id,
                channel="elevation",
                components=_ELEVATION_COMPONENTS,
                floor_ids=floor_ids,
                reason="reading_view_missing",
                cause_class="product_content",
                denominator_disposition="retain_as_miss",
            ),
            (),
            (),
            (),
            (),
            (),
            (),
        )
    if not isinstance(raw_view, dict):
        return (
            _na_components(
                source_input_id=binding.input_id,
                channel="elevation",
                components=_ELEVATION_COMPONENTS,
                floor_ids=floor_ids,
                reason="reading_view_schema_unsupported",
                cause_class="product_content",
                denominator_disposition="retain_as_miss",
            ),
            (),
            (),
            (),
            (),
            (),
            (),
        )
    try:
        parsed = ReadingView.model_validate(raw_view)
    except ValidationError:
        return (
            _na_components(
                source_input_id=binding.input_id,
                channel="elevation",
                components=_ELEVATION_COMPONENTS,
                floor_ids=floor_ids,
                reason="reading_view_schema_unsupported",
                cause_class="product_content",
                denominator_disposition="retain_as_miss",
            ),
            (),
            (),
            (),
            (),
            (),
            (),
        )

    findings: list[ReadingMetadataFindingV1] = []
    if raw_view.get("image_kind", "missing") != "elevation":
        findings.append(
            ReadingMetadataFindingV1(
                source_input_id=binding.input_id,
                code="image_kind_declaration_mismatch",
                declared_sha256=_metadata_hash(
                    raw_view.get("image_kind", "missing")
                ),
                trusted_sha256=_metadata_hash("elevation"),
            )
        )
    raw_facade = raw_view.get("facade")
    if (
        isinstance(raw_facade, dict)
        and raw_facade.get("view_facade", "missing")
        != binding.facade_family
    ):
        findings.append(
            ReadingMetadataFindingV1(
                source_input_id=binding.input_id,
                code="orientation_declaration_mismatch",
                declared_sha256=_metadata_hash(
                    raw_facade.get("view_facade", "missing")
                ),
                trusted_sha256=_metadata_hash(binding.facade_family),
            )
        )

    scale_origin = raw_view.get("scale_origin")
    raw_z = (
        scale_origin.get("world_z_m", _MISSING)
        if isinstance(scale_origin, dict)
        else _MISSING
    )
    datum: VerticalDatumCertificateV1 | None
    z_origin: float | None
    invalid_z = False
    if raw_z is _MISSING or raw_z is None:
        z_origin = 0.0
        datum = _vertical_datum(
            input_id=binding.input_id,
            floor_ids=floor_ids,
            source="project_convention_2026_07_25",
            z_origin=z_origin,
        )
    else:
        try:
            z_origin = _strict_finite(raw_z)
        except ValueError:
            invalid_z = True
            z_origin = None
            datum = None
        else:
            datum = _vertical_datum(
                input_id=binding.input_id,
                floor_ids=floor_ids,
                source="product_declared",
                z_origin=z_origin,
            )

    (
        raw_local,
        effective_local,
        raw_mirrored,
        effective_mirrored,
        facade_for_hash,
    ) = _facade_sense(raw_view)
    if (
        effective_local != binding.local_x_positive
        or effective_mirrored != binding.mirrored
    ):
        witness = ElevationFrameDisagreementWitnessV1(
            source_input_id=binding.input_id,
            binding_local_x_positive=binding.local_x_positive,
            product_local_x_positive_raw=raw_local,
            product_local_x_positive_effective=effective_local,
            binding_mirrored=binding.mirrored,
            product_mirrored_raw=raw_mirrored,
            product_mirrored_effective=effective_mirrored,
            binding_frame_transform_sha256=binding.frame_transform_sha256,
            product_facade_sha256=_audit_sha(facade_for_hash),
            reason="elevation_local_x_sense_disagreement",
        )
        return (
            _na_components(
                source_input_id=binding.input_id,
                channel="elevation",
                components=_ELEVATION_COMPONENTS,
                floor_ids=floor_ids,
                reason="elevation_local_x_sense_disagreement",
                cause_class="trusted_frame",
                denominator_disposition="retain_as_miss",
            ),
            (),
            () if datum is None else (datum,),
            (),
            (witness,),
            tuple(findings),
            (),
        )

    raw_strokes = raw_view.get("strokes")
    if not isinstance(raw_strokes, list):
        return (
            _na_components(
                source_input_id=binding.input_id,
                channel="elevation",
                components=_ELEVATION_COMPONENTS,
                floor_ids=floor_ids,
                reason="reading_view_schema_unsupported",
                cause_class="product_content",
                denominator_disposition="retain_as_miss",
            ),
            (),
            () if datum is None else (datum,),
            (),
            (),
            tuple(findings),
            (),
        )
    observations: list[ReadingElevationOpeningAuditV1] = []
    witnesses: list[UnmeasurableObservationWitnessV1] = []
    malformed = False
    direction_semantics = entry.direction_semantics
    for raw_stroke in raw_strokes:
        if not isinstance(raw_stroke, dict) or raw_stroke.get("pen") != "window":
            continue
        if raw_stroke.get("visibility") == "hidden" or raw_stroke.get(
            "line_style"
        ) in {"dashed", "dash_dot"}:
            continue
        stroke_id = raw_stroke.get("id")
        if not isinstance(stroke_id, str) or not stroke_id:
            malformed = True
            stroke_id = "invalid-stroke-id"
        geometry = raw_stroke.get("geometry", "missing")
        try:
            geometry_kind, local_x, local_y = _elevation_bounds(geometry)
        except ValueError:
            malformed = True
            witnesses.append(
                UnmeasurableObservationWitnessV1(
                    source_input_id=binding.input_id,
                    source_stroke_id=stroke_id,
                    component="elevation_opening_xy",
                    reason="consumed_geometry_malformed",
                    cause_class="product_content",
                    source_geometry_sha256=_audit_sha(geometry),
                )
            )
            continue
        observation_id = _normalized_observation_id(
            output_sha256=source_output_sha256,
            input_id=binding.input_id,
            stroke_id=stroke_id,
            component="elevation_opening_xy",
            primitive_index=0,
        )
        projected = project_typed_elevation_observation(
            observation=TypedElevationObservation(
                observation_id=observation_id,
                source_input_id=binding.input_id,
                floor_id=floor_ids[0],
                kind="window",
                facade_family=binding.facade_family,
                local_x_interval=local_x,
                z_interval=(
                    None
                    if invalid_z
                    else (
                        local_y[0] + z_origin,
                        local_y[1] + z_origin,
                    )
                ),
            ),
            binding=binding,
            direction_semantics=direction_semantics,
        )
        observations.append(
            ReadingElevationOpeningAuditV1(
                kind="elevation_opening",
                observation_id=observation_id,
                source_input_id=binding.input_id,
                source_stroke_id=stroke_id,
                floor_id=floor_ids[0],
                facade_family=binding.facade_family,
                geometry_kind=geometry_kind,
                local_x_interval=ClosedIntervalV1(
                    lo=local_x[0],
                    hi=local_x[1],
                ),
                local_y_interval=ClosedIntervalV1(
                    lo=local_y[0],
                    hi=local_y[1],
                ),
                world_along_interval=ClosedIntervalV1(
                    lo=projected.world_along_interval[0],
                    hi=projected.world_along_interval[1],
                ),
                z_interval=(
                    None
                    if projected.z_interval is None
                    else ClosedIntervalV1(
                        lo=projected.z_interval[0],
                        hi=projected.z_interval[1],
                    )
                ),
                source_geometry_sha256=_audit_sha(geometry),
                horizontal_transform_sha256=binding.frame_transform_sha256,
                vertical_transform_sha256=(
                    None if datum is None else datum.preimage_sha256
                ),
            )
        )
    if malformed:
        return (
            _na_components(
                source_input_id=binding.input_id,
                channel="elevation",
                components=_ELEVATION_COMPONENTS,
                floor_ids=floor_ids,
                reason="elevation_opening_geometry_unsupported",
                cause_class="product_content",
                denominator_disposition="retain_as_miss",
            ),
            (),
            () if datum is None else (datum,),
            tuple(witnesses),
            (),
            tuple(findings),
            (),
        )
    xy = _component(
        source_input_id=binding.input_id,
        channel="elevation",
        component="elevation_opening_xy",
        floor_ids=floor_ids,
        status="applicable",
        observation_count=len(observations),
        transform_sha256=binding.frame_transform_sha256,
    )
    if invalid_z:
        z = _component(
            source_input_id=binding.input_id,
            channel="elevation",
            component="elevation_opening_z",
            floor_ids=floor_ids,
            status="not_applicable",
            reasons=("elevation_vertical_datum_unsupported",),
            cause_class="product_content",
            denominator_disposition="retain_as_miss",
        )
    else:
        assert datum is not None
        z = _component(
            source_input_id=binding.input_id,
            channel="elevation",
            component="elevation_opening_z",
            floor_ids=floor_ids,
            status="applicable",
            observation_count=len(observations),
            transform_sha256=datum.preimage_sha256,
        )
    return (
        (xy, z),
        tuple(observations),
        () if datum is None else (datum,),
        tuple(witnesses),
        (),
        tuple(findings),
        (),
    )


def normalize_reading_attempt(
    *,
    raw: object,
    source_output_sha256: str,
    base_manifest,
    score_bindings,
) -> ReadingNormalizationOutcome:
    """Normalize product evidence through trusted manifest/binding frames."""
    decision = identify_reading_contract(raw)
    if decision.contract_id != READING_PRODUCT_CONTRACT:
        raise ValueError("normalize_reading_attempt requires reading_views_v1")
    assert isinstance(raw, dict)
    views = raw["views"]
    assert isinstance(views, dict)
    entries = {
        item.input_id: item
        for item in base_manifest.required_entries()
        if item.view_type in {"plan", "elevation"}
    }
    bindings = {item.input_id: item for item in score_bindings.bindings}
    component_rows: list[ReadingComponentApplicabilityV1] = []
    elevation_observations: list[ReadingElevationOpeningAuditV1] = []
    vertical_datums: list[VerticalDatumCertificateV1] = []
    unmeasurable: list[UnmeasurableObservationWitnessV1] = []
    disagreements: list[ElevationFrameDisagreementWitnessV1] = []
    findings: list[ReadingMetadataFindingV1] = []
    exclusions: list[ReadingFilteredComponentBasisV1] = []

    for input_id, entry in sorted(entries.items()):
        binding = bindings.get(input_id)
        raw_view = views.get(entry.expected_output_id, _MISSING)
        if entry.view_type == "elevation" and isinstance(
            binding, ElevationScoreViewBindingV1
        ):
            (
                components,
                observations,
                datums,
                witnesses,
                frame_witnesses,
                metadata,
                trusted_exclusions,
            ) = _elevation_result(
                entry=entry,
                binding=binding,
                raw_view=raw_view,
                source_output_sha256=source_output_sha256,
            )
            component_rows.extend(components)
            elevation_observations.extend(observations)
            vertical_datums.extend(datums)
            unmeasurable.extend(witnesses)
            disagreements.extend(frame_witnesses)
            findings.extend(metadata)
            exclusions.extend(trusted_exclusions)
            continue
        if entry.view_type == "plan" and isinstance(
            binding, PlanScoreViewBindingV1
        ):
            component_rows.extend(
                _na_components(
                    source_input_id=input_id,
                    channel="plan",
                    components=_PLAN_COMPONENTS,
                    floor_ids=(binding.floor_id,),
                    reason="plan_geometry_unsupported",
                    cause_class="product_content",
                    denominator_disposition="retain_as_miss",
                )
            )
            continue
        floor_ids = (
            (binding.floor_id,)
            if isinstance(binding, PlanScoreViewBindingV1)
            else tuple(getattr(binding, "floor_ids", ()))
        )
        components = (
            _PLAN_COMPONENTS
            if entry.view_type == "plan"
            else _ELEVATION_COMPONENTS
        )
        component_rows.extend(
            _na_components(
                source_input_id=input_id,
                channel=entry.view_type,
                components=components,
                floor_ids=floor_ids,
                reason="reading_view_schema_unsupported",
                cause_class="trusted_input",
                denominator_disposition="filter",
            )
        )
        exclusions.extend(
            ReadingFilteredComponentBasisV1(
                source_input_id=input_id,
                component=component,
                floor_ids=tuple(sorted(floor_ids)),
                cause_class="trusted_input",
                reasons=("reading_view_schema_unsupported",),
            )
            for component in components
        )

    expected_output_ids = {
        entry.expected_output_id for entry in entries.values()
    }
    for output_id in sorted(set(views) - expected_output_ids):
        findings.append(
            ReadingMetadataFindingV1(
                source_input_id=output_id,
                code="unbound_reading_view",
                declared_sha256=_audit_sha(views[output_id]),
                trusted_sha256=canonical_sha256("unbound"),
            )
        )

    component_rows.sort(
        key=lambda item: (
            item.source_input_id,
            item.component,
            item.floor_ids,
        )
    )
    observations = tuple(
        sorted(
            elevation_observations,
            key=lambda item: (
                item.source_input_id,
                item.source_stroke_id,
                item.kind,
                0,
            ),
        )
    )
    vertical_datums.sort(key=lambda item: (item.input_id, item.floor_ids))
    unmeasurable.sort(
        key=lambda item: (
            item.source_input_id,
            item.source_stroke_id,
            item.component,
        )
    )
    disagreements.sort(key=lambda item: item.source_input_id)
    findings.sort(key=lambda item: (item.source_input_id, item.code))
    exclusions.sort(
        key=lambda item: (
            item.source_input_id,
            item.component,
            item.floor_ids,
            item.reasons,
        )
    )
    certificate_raw = {
        "schema_version": "1",
        "helper_version": READING_ADAPTER_VERSION,
        "contract_detector_version": READING_CONTRACT_DETECTOR_VERSION,
        "source_output_sha256": source_output_sha256,
        "product_contract": READING_PRODUCT_CONTRACT,
        "base_view_manifest_sha256": base_manifest.content_sha256,
        "score_view_bindings_sha256": score_bindings.content_sha256,
        "plan_frames": (),
        "vertical_datums": tuple(
            item.model_dump(mode="json") for item in vertical_datums
        ),
        "component_applicability": tuple(
            item.model_dump(mode="json") for item in component_rows
        ),
        "observations": tuple(
            item.model_dump(mode="json") for item in observations
        ),
        "unmeasurable_observation_witnesses": tuple(
            item.model_dump(mode="json") for item in unmeasurable
        ),
        "elevation_frame_disagreements": tuple(
            item.model_dump(mode="json") for item in disagreements
        ),
        "metadata_findings": tuple(
            item.model_dump(mode="json") for item in findings
        ),
    }
    certificate = ReadingNormalizationCertificateV1(
        schema_version="1",
        helper_version=READING_ADAPTER_VERSION,
        contract_detector_version=READING_CONTRACT_DETECTOR_VERSION,
        source_output_sha256=source_output_sha256,
        product_contract=READING_PRODUCT_CONTRACT,
        base_view_manifest_sha256=base_manifest.content_sha256,
        score_view_bindings_sha256=score_bindings.content_sha256,
        plan_frames=(),
        vertical_datums=tuple(vertical_datums),
        component_applicability=tuple(component_rows),
        observations=observations,
        unmeasurable_observation_witnesses=tuple(unmeasurable),
        elevation_frame_disagreements=tuple(disagreements),
        metadata_findings=tuple(findings),
        content_sha256=canonical_sha256(certificate_raw),
    )
    return ReadingNormalizationOutcome(
        certificate=certificate,
        trusted_capability_dispositions=tuple(exclusions),
    )


def _filtered(
    exclusions: tuple[ReadingFilteredComponentBasisV1, ...],
    *,
    source_input_id: str,
    component: str,
    floor_id: str,
) -> bool:
    return any(
        item.source_input_id == source_input_id
        and item.component == component
        and floor_id in item.floor_ids
        for item in exclusions
    )


def _atom(
    *,
    target_id: str,
    target_kind: Literal["plan_segment", "window"],
    component: str,
    claim: str | None,
    floor_id: str,
    source_input_ids: tuple[str, ...],
    eligible_units: float,
) -> ReadingDenominatorAtomV1:
    raw = {
        "target_id": target_id,
        "target_kind": target_kind,
        "component": component,
        "claim": claim,
        "floor_id": floor_id,
        "source_input_ids": source_input_ids,
        "eligible_units": eligible_units,
    }
    return ReadingDenominatorAtomV1(
        atom_id=f"reading-denominator:{canonical_sha256(raw)}",
        **raw,
    )


def derive_reading_denominator_v1(
    gt,
    base_manifest,
    bindings,
    trusted_capability_dispositions,
) -> tuple[
    ReadingDenominatorBasisV1,
    tuple[ReadingDenominatorAtomV1, ...],
    str,
    str,
]:
    """Derive answer atoms from trusted inputs only.

    The signature deliberately has no product parameter.  The fourth argument
    validates through a wire whose cause literal is only ``trusted_input``.
    """
    exclusions = tuple(
        item
        if isinstance(item, ReadingFilteredComponentBasisV1)
        else ReadingFilteredComponentBasisV1.model_validate(item)
        for item in trusted_capability_dispositions
    )
    exclusions = tuple(
        sorted(
            exclusions,
            key=lambda item: (
                item.source_input_id,
                item.component,
                item.floor_ids,
                item.reasons,
            ),
        )
    )
    basis_preimage = {
        "helper_version": READING_DENOMINATOR_VERSION,
        "gt_content_sha256": gt.content_sha256,
        "base_view_manifest_sha256": base_manifest.content_sha256,
        "score_view_bindings_sha256": bindings.content_sha256,
        "filtered_components": tuple(
            item.model_dump(mode="json") for item in exclusions
        ),
    }
    basis = ReadingDenominatorBasisV1(
        helper_version=READING_DENOMINATOR_VERSION,
        gt_content_sha256=gt.content_sha256,
        base_view_manifest_sha256=base_manifest.content_sha256,
        score_view_bindings_sha256=bindings.content_sha256,
        filtered_components=exclusions,
        content_sha256=canonical_sha256(basis_preimage),
    )

    plan_bindings = tuple(
        item
        for item in bindings.bindings
        if isinstance(item, PlanScoreViewBindingV1)
    )
    elevation_bindings = tuple(
        item
        for item in bindings.bindings
        if isinstance(item, ElevationScoreViewBindingV1)
    )
    atoms: list[ReadingDenominatorAtomV1] = []
    for floor in gt.floors:
        for segment in floor.boundary_segments:
            source_views = {item.view_id for item in segment.source_refs}
            source_ids = tuple(
                sorted(
                    item.input_id
                    for item in plan_bindings
                    if item.floor_id == floor.id
                    and source_views.intersection(item.gt_source_view_ids)
                    and not _filtered(
                        exclusions,
                        source_input_id=item.input_id,
                        component="plan_segments",
                        floor_id=floor.id,
                    )
                )
            )
            if not source_ids:
                continue
            atoms.append(
                _atom(
                    target_id=segment.id,
                    target_kind="plan_segment",
                    component="plan_segments",
                    claim=None,
                    floor_id=floor.id,
                    source_input_ids=source_ids,
                    eligible_units=math.hypot(
                        segment.p2[0] - segment.p1[0],
                        segment.p2[1] - segment.p1[1],
                    ),
                )
            )

    component_claims = {
        "plan_openings": ("existence", "along", "width"),
        "elevation_opening_xy": ("existence", "along", "width"),
        "elevation_opening_z": ("sill", "head"),
    }
    for opening in gt.openings:
        if opening.kind != "window":
            continue
        source_views = {item.view_id for item in opening.source_refs}
        for component, claims in component_claims.items():
            candidates = plan_bindings if component == "plan_openings" else elevation_bindings
            source_ids = tuple(
                sorted(
                    item.input_id
                    for item in candidates
                    if (
                        (
                            item.floor_id == opening.floor_id
                            if isinstance(item, PlanScoreViewBindingV1)
                            else opening.floor_id in item.floor_ids
                        )
                        and source_views.intersection(item.gt_source_view_ids)
                        and not _filtered(
                            exclusions,
                            source_input_id=item.input_id,
                            component=component,
                            floor_id=opening.floor_id,
                        )
                    )
                )
            )
            if not source_ids:
                continue
            for claim in claims:
                if claim in {"sill", "head"} and opening.z_interval is None:
                    continue
                atoms.append(
                    _atom(
                        target_id=opening.id,
                        target_kind="window",
                        component=component,
                        claim=claim,
                        floor_id=opening.floor_id,
                        source_input_ids=source_ids,
                        eligible_units=1.0,
                    )
                )

    ordered = tuple(
        sorted(
            atoms,
            key=lambda item: (
                item.target_id,
                item.component,
                item.claim or "",
                item.source_input_ids,
            ),
        )
    )
    denominator_sha256 = canonical_sha256(
        [item.model_dump(mode="json") for item in ordered]
    )
    return basis, ordered, basis.content_sha256, denominator_sha256
