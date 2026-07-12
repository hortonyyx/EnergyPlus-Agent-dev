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
        return FeatureStateClaimsV1(
            target_schema_version="3", phase_contract=target.phase_contract,
            helper_versions=("floor_footprint_v1",),
            cell_polygon="populated", per_floor_footprint="populated",
            facade_segments="declared_unpopulated", typed_north_axis="declared_unpopulated",
        )
    return FeatureStateClaimsV1(
        target_schema_version="1", phase_contract=target.phase_contract,
        cell_polygon="not_declared", per_floor_footprint="not_declared",
        facade_segments="not_declared", typed_north_axis="not_declared",
    )


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
