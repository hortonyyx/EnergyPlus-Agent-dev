"""Judge-only adapter contracts for aggregate reading-stage products."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from src.agent.judge.score_schema import (
    READING_DENOMINATOR_VERSION,
    READING_PRODUCT_CONTRACT,
    ElevationScoreViewBindingV1,
    PlanScoreViewBindingV1,
    ReadingDenominatorAtomV1,
    ReadingDenominatorBasisV1,
    ReadingFilteredComponentBasisV1,
    canonical_sha256,
)


READING_CONTRACT_DETECTOR_VERSION = "reading_contract_detector_v1"


@dataclass(frozen=True)
class ReadingContractDecision:
    contract_id: Literal["reading_views_v1", "unrecognized"]
    reason: str | None


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
