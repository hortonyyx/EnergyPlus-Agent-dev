"""The one correction finalization transaction shared by pipeline and flow."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.agent.correction.config import CoreTolerances, load_core_tolerances
from src.agent.correction.deterministic import apply_deterministic_core
from src.agent.correction.envelope import extract_authoritative_envelope
from src.agent.correction.feature_state import FeatureStateClaimsV1, derive_feature_state_claims
from src.agent.correction.parse import CorrectionTarget, ensure_corrected_geometry, parse_correction_draw, validate_final_corrected_geometry
from src.agent.correction.schema import CorrectedGeometry


@dataclass(frozen=True)
class FinalizeResult:
    geom: CorrectedGeometry
    audit_payload: dict
    feature_state_claims: FeatureStateClaimsV1


def _identity_snapshot(geom: CorrectedGeometry):
    if geom.schema_version != "3":
        return None
    return (
        tuple(floor.id for floor in geom.floors),
        tuple((window.id, window.floor_id, window.facade_segment_id) for window in geom.windows),
        tuple((segment.id, segment.floor_id) for segment in geom.facade_segments),
    )


def finalize_correction_draw(
    geom_or_payload,
    *,
    vector_dir: Path,
    tol: CoreTolerances | None = None,
    target: CorrectionTarget,
) -> FinalizeResult:
    """Parse/ensure → identity snapshot → envelope/core → final strict artifact.

    The function intentionally has no attempt-directory I/O: the common writer
    owns archive, hashes, and accepted-pointer promotion.
    """
    geom = (parse_correction_draw(geom_or_payload, target)
            if isinstance(geom_or_payload, dict) else ensure_corrected_geometry(geom_or_payload))
    if geom.schema_version != target.schema_version:
        raise ValueError("finalize input does not match correction target")
    before = _identity_snapshot(geom)
    tol = tol or load_core_tolerances()
    envelope = extract_authoritative_envelope(
        Path(vector_dir), footprint=geom, footprint_tolerance_m=tol.envelope_reconcile_tol_m,
    )
    geom = apply_deterministic_core(
        geom, tol, authoritative_envelope=envelope, capability_profile=target.capability_profile,
    )
    if before != _identity_snapshot(geom):
        raise ValueError("finalize invariant: v3 floor/reference identities changed during core")
    geom = validate_final_corrected_geometry(geom)
    return FinalizeResult(
        geom=geom,
        audit_payload={"corrections": geom.corrections, "conflicts": geom.conflicts, "unsupported": geom.unsupported},
        feature_state_claims=derive_feature_state_claims(target, geom),
    )
