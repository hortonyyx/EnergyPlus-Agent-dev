"""B2 machine-readable feature population state (separate from schema support)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.agent.geometry.capability import (
    FEATURE_CELL_POLYGON, FEATURE_FACADE_SEGMENTS, FEATURE_PER_FLOOR_FOOTPRINT,
    FEATURE_TYPED_NORTH_AXIS,
)

FeatureState = Literal["not_declared", "declared_unpopulated", "populated"]


class FeatureStateClaimsV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    target_schema_version: Literal["1", "3"]
    phase_contract: str
    helper_versions: tuple[str, ...] = ()
    cell_polygon: FeatureState
    per_floor_footprint: FeatureState
    facade_segments: FeatureState
    typed_north_axis: FeatureState

    def state_for(self, feature: str) -> FeatureState:
        return {
            FEATURE_CELL_POLYGON: self.cell_polygon,
            FEATURE_PER_FLOOR_FOOTPRINT: self.per_floor_footprint,
            FEATURE_FACADE_SEGMENTS: self.facade_segments,
            FEATURE_TYPED_NORTH_AXIS: self.typed_north_axis,
        }[feature]


class FeatureStatesArtifactV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1"] = "1"
    output_sha256: str
    claims: FeatureStateClaimsV1


def derive_feature_state_claims(target, geom) -> FeatureStateClaimsV1:
    if geom.schema_version == "3":
        # Vg (C2 §9.2) is now mandatory inside `finalize_correction_draw` for
        # every v3 draw, so by the time this is called the geom must already
        # carry a populated, per-floor-complete facade segment list — an empty
        # or partial list here is a Vg/finalize-ordering defect, not a
        # legitimate "not yet populated" declaration.
        if not geom.facade_segments:
            raise ValueError(
                "INVARIANT: v3 facade_segments must be populated by Vg before feature-state derivation"
            )
        floor_ids = {fl.id for fl in geom.floors}
        segment_floor_ids = {seg.floor_id for seg in geom.facade_segments}
        if segment_floor_ids != floor_ids:
            raise ValueError("INVARIANT: facade segments do not cover every v3 floor")
        return FeatureStateClaimsV1(
            target_schema_version="3", phase_contract=target.phase_contract,
            helper_versions=("floor_footprint_v1", "facade_visibility_v1"),
            cell_polygon="populated", per_floor_footprint="populated",
            facade_segments="populated", typed_north_axis="declared_unpopulated",
        )
    return FeatureStateClaimsV1(
        target_schema_version="1", phase_contract=target.phase_contract,
        cell_polygon="not_declared", per_floor_footprint="not_declared",
        facade_segments="not_declared", typed_north_axis="not_declared",
    )


# --------------------------------------------------------------------------- #
# Correction stage-version release map (C2 Vg rework CR2, spec v3 §9.2).
# `stage_version` is a wire protocol label the writer must be able to derive
# without trusting the caller; every FULL claims-state combination the writer
# can legitimately emit — schema + helper_versions + all four feature states
# — must be registered here explicitly before it is ever written. Keying on
# the complete state (not just `helper_versions`) is what lets the legacy-v1
# lineage (`helper_versions=()`, all features `not_declared`) coexist in the
# same table as the B2 v3 lineage without a post-hoc "version 2 must mean
# declared_unpopulated" side-check that would wrongly reject legacy claims —
# every combination stands on its own registered row.
# --------------------------------------------------------------------------- #
ReleaseKey = tuple[
    str,                    # target_schema_version
    tuple[str, ...],        # helper_versions, canonical dependency order
    FeatureState,           # cell_polygon
    FeatureState,           # per_floor_footprint
    FeatureState,           # facade_segments
    FeatureState,           # typed_north_axis
]

_CORRECTION_STAGE_VERSION_BY_RELEASE: dict[ReleaseKey, str] = {
    # legacy v1 lineage: no v3 feature/helper is declared
    ("1", (),
     "not_declared", "not_declared", "not_declared", "not_declared"): "2",

    # B2 v3 lineage: footprint features populated; facade/north only declared
    ("3", ("floor_footprint_v1",),
     "populated", "populated", "declared_unpopulated", "declared_unpopulated"): "2",

    # Vg v3 lineage: facade visibility is now populated; north remains pending
    ("3", ("floor_footprint_v1", "facade_visibility_v1"),
     "populated", "populated", "populated", "declared_unpopulated"): "3",
}


def correction_stage_version(claims: FeatureStateClaimsV1) -> str:
    key: ReleaseKey = (
        claims.target_schema_version,
        claims.helper_versions,
        claims.cell_polygon,
        claims.per_floor_footprint,
        claims.facade_segments,
        claims.typed_north_axis,
    )
    try:
        return _CORRECTION_STAGE_VERSION_BY_RELEASE[key]
    except KeyError as exc:
        raise ValueError("INVARIANT: unknown correction helper/state release") from exc


def artifact_feature_state(attempt_dir, record, feature: str) -> FeatureState:
    """Read a populated-state claim only after its accepted bundle verifies."""
    from pathlib import Path
    from src.agent.execution.manifest import hash_file

    path = Path(attempt_dir)
    if getattr(record, "artifact_contract", None) != "correction_b2_v1":
        raise ValueError("feature state requires a correction_b2_v1 accepted record")
    output = path / "output.json"
    sidecar = path / "feature_states.json"
    hashes = getattr(record, "artifact_hashes", {})
    if (not output.is_file() or not sidecar.is_file()
            or hashes.get("output") != hash_file(output)
            or hashes.get("feature_states") != hash_file(sidecar)):
        raise ValueError("feature-state artifact hash chain is invalid")
    artifact = FeatureStatesArtifactV1.model_validate_json(sidecar.read_text(encoding="utf-8"))
    if artifact.output_sha256 != hash_file(output):
        raise ValueError("feature-state sidecar does not bind this output")
    try:
        return artifact.claims.state_for(feature)
    except KeyError as exc:
        raise ValueError(f"unknown correction feature {feature!r}") from exc
