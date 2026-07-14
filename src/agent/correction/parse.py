"""Correction trust boundary and the separate draw/final ring contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.agent.correction.cell_geometry import normalized_ccw_polygon, validate_cell_polygon
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.schema import CorrectedGeometry, CorrectedGeometryV3

# E4-output-contract spec v2 §3.2bis writer contract: the frozen phase
# vocabulary. `b2` = draw/Vg finalize (north_axis must stay None);
# `e4_orientation` = the deterministic orientation-enrichment augment
# (BO-CR10: narrowed from bare `str` to the contract Literal).
PhaseContract = Literal["b2", "e4_orientation"]


@dataclass(frozen=True)
class CorrectionTarget:
    schema_version: str
    schema_model: type[CorrectedGeometry]
    capability_profile: str
    phase_contract: PhaseContract = "b2"

    def __post_init__(self) -> None:
        if self.phase_contract not in ("b2", "e4_orientation"):
            raise ValueError(
                f"unknown correction phase_contract {self.phase_contract!r}; "
                "frozen vocabulary is 'b2' | 'e4_orientation'"
            )


def correction_target(capability_profile: str) -> CorrectionTarget:
    if capability_profile == "rectangular":
        return CorrectionTarget("1", CorrectedGeometry, capability_profile)
    if capability_profile == "orthogonal_polygon":
        return CorrectionTarget("3", CorrectedGeometryV3, capability_profile)
    raise ValueError(f"unknown correction capability profile {capability_profile!r}")


def ensure_corrected_geometry(value: dict | CorrectedGeometry) -> CorrectedGeometry:
    # Capability's registry is deliberately consulted at runtime so test/feature
    # profiles can register a future read-only legacy schema while still keeping
    # genuinely unknown versions fail-closed.
    from src.agent.geometry.capability import SUPPORTED_SCHEMA_VERSIONS
    if isinstance(value, dict):
        version = str(value.get("schema_version", "1"))
        if version == "3":
            return CorrectedGeometryV3.model_validate(value)
        if version in SUPPORTED_SCHEMA_VERSIONS:
            return CorrectedGeometry.model_validate(value)
        raise ValueError(f"unsupported correction schema_version {version!r}")
    version = str(getattr(value, "schema_version", "1"))
    if version == "3":
        return CorrectedGeometryV3.model_validate(value.model_dump())
    if version in SUPPORTED_SCHEMA_VERSIONS:
        return value
    raise ValueError(f"unsupported correction schema_version {version!r}")


def _ring_checks(geom: CorrectedGeometry, *, canonical: bool) -> None:
    if geom.schema_version != "3":
        return
    tol = load_core_tolerances()
    for floor in geom.floors:
        ring = floor.footprint.vertices
        # Reuse the established robust orthogonal/simple/min-edge checker via a
        # temporary cell-shaped object; its input contract is identical.
        class _Ring:
            polygon = [list(p) for p in ring]
            x = [min(p[0] for p in ring), max(p[0] for p in ring)]
            y = [min(p[1] for p in ring), max(p[1] for p in ring)]
            id = "floor_footprint"
        validate_cell_polygon(_Ring(), min_edge_length_m=tol.min_edge_length_m,
                              require_bbox_match=False, allow_cw=not canonical,
                              allow_closed=not canonical)


def parse_correction_draw(payload: dict, target: CorrectionTarget) -> CorrectedGeometry:
    geom = ensure_corrected_geometry(payload)
    if geom.schema_version != target.schema_version:
        raise ValueError("correction draw schema_version does not match selected target")
    if target.phase_contract == "b2" and geom.schema_version == "3":
        assert isinstance(geom, CorrectedGeometryV3)
        if geom.facade_segments or geom.north_axis is not None:
            raise ValueError("b2 draw contract requires empty facade_segments and null north_axis")
    _ring_checks(geom, canonical=False)
    return geom


def validate_final_corrected_geometry(geom: CorrectedGeometry) -> CorrectedGeometry:
    result = ensure_corrected_geometry(geom)
    _ring_checks(result, canonical=True)
    return result
