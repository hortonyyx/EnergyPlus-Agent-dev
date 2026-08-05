"""The one correction finalization transaction shared by pipeline and flow."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from src.agent.correction.artifact_serialization import (
    serialize_correction_output,
    serialize_feature_states,
)
from src.agent.correction.config import CoreTolerances, load_core_tolerances
from src.agent.correction.deterministic import apply_deterministic_core
from src.agent.correction.envelope import extract_authoritative_envelope
from src.agent.correction.facade_visibility import (
    VisibilityTolerances,
    materialize_all_facade_segments,
)
from src.agent.correction.feature_state import (
    FeatureStateClaimsV1,
    FeatureStatesArtifactV1,
    derive_feature_state_claims,
)
from src.agent.correction.parse import CorrectionTarget, ensure_corrected_geometry, parse_correction_draw, validate_final_corrected_geometry
from src.agent.correction.schema import CorrectedGeometry
from src.agent.correction.window_host import (
    WindowEvidenceLedgerV1,
    WindowHostClaimsV1,
    WindowHostResolutionError,
    apply_window_host_resolutions,
    derive_window_evidence_ledger,
    map_direction_binding_error,
    resolve_window_hosts,
)
from src.agent.correction.window_sources import (
    VerifiedWindowResolverInputs,
    WindowDirectionBindingError,
    WindowResolverInputError,
    canonical_json_bytes,
)


@dataclass(frozen=True)
class PreparedCandidateIdentity:
    output_bytes: bytes
    output_sha256: str
    feature_states_bytes: bytes
    feature_states_sha256: str

    def __post_init__(self) -> None:
        if hashlib.sha256(self.output_bytes).hexdigest() != self.output_sha256:
            raise ValueError("candidate_output_identity_drift")
        if hashlib.sha256(self.feature_states_bytes).hexdigest() != self.feature_states_sha256:
            raise ValueError("candidate_feature_states_identity_drift")
        artifact = FeatureStatesArtifactV1.model_validate_json(self.feature_states_bytes)
        if artifact.output_sha256 != self.output_sha256:
            raise ValueError("candidate_feature_states_output_identity_drift")


@dataclass(frozen=True)
class FinalizeResult:
    geom: CorrectedGeometry
    audit_payload: dict
    feature_state_claims: FeatureStateClaimsV1
    window_host_claims: WindowHostClaimsV1 | None = None
    window_evidence_ledger: WindowEvidenceLedgerV1 | None = None
    verified_window_resolver_inputs: VerifiedWindowResolverInputs | None = None
    prepared_candidate_identity: PreparedCandidateIdentity | None = None


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
    verified_window_inputs: VerifiedWindowResolverInputs | None = None,
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
    if geom.schema_version != "3" and verified_window_inputs is not None:
        raise ValueError("legacy v1/v2 finalize forbids verified_window_inputs")
    before = _identity_snapshot(geom)
    if geom.schema_version == "3" and verified_window_inputs is not None:
        producer_bytes = canonical_json_bytes(geom.model_dump(mode="json"))
        if producer_bytes != verified_window_inputs.producer_draw_canonical_bytes:
            # Caller-side wiring defect (finalize was handed a different geom
            # than the one `verified_window_inputs` was built from) — not a
            # model draw mistake, so no resample can help.
            raise WindowResolverInputError(
                "source_identity_invalid", {"artifact": "producer_draw_canonical_bytes"},
                category="input_integrity_error",
            )
    if geom.schema_version == "3" and verified_window_inputs is None:
        raise WindowResolverInputError(
            "source_identity_invalid", {"artifact": "verified_window_resolver_inputs"},
            category="input_integrity_error",
        )
    tol = tol or load_core_tolerances()
    envelope = extract_authoritative_envelope(
        Path(vector_dir), footprint=geom, footprint_tolerance_m=tol.envelope_reconcile_tol_m, tol=tol,
    )
    geom = apply_deterministic_core(
        geom, tol, authoritative_envelope=envelope, capability_profile=target.capability_profile,
        verified_window_inputs=verified_window_inputs,
    )
    if before != _identity_snapshot(geom):
        raise ValueError("finalize invariant: v3 floor/reference identities changed during core")
    if geom.schema_version == "3":
        # Vg (C2 §E1'/§9.1): the ONLY writer of `facade_segments`. Runs on the
        # core-final ring (not the producer's pre-core one) and strictly after
        # the identity snapshot compare above — an empty->populated facade
        # list here is the batch's intended write, not an identity drift.
        visibility_tol = VisibilityTolerances(
            depth_epsilon_m=tol.facade_visibility_depth_epsilon_m,
            endpoint_epsilon_m=tol.facade_visibility_endpoint_epsilon_m,
        )
        segments = materialize_all_facade_segments(geom, tolerances=visibility_tol)
        geom = geom.model_copy(update={"facade_segments": list(segments)})
        # The final-ring resolver is the typed validation boundary for every
        # v3 artifact, including an empty but verified window set.
    window_host_claims = None
    if geom.schema_version == "3" and verified_window_inputs is not None:
        try:
            window_host_claims = resolve_window_hosts(
                geom, verified_inputs=verified_window_inputs, tolerances=tol, commit=False,
            )
            geom = apply_window_host_resolutions(
                geom, claims=window_host_claims,
                verified_inputs=verified_window_inputs, tolerances=tol,
            )
        except WindowDirectionBindingError as exc:
            raise WindowHostResolutionError(
                map_direction_binding_error(
                    exc, geom=geom, verified_inputs=verified_window_inputs, phase="final",
                ),
                phase="final",
                context=exc.context,
            ) from exc
    geom = validate_final_corrected_geometry(geom)
    feature_state_claims = derive_feature_state_claims(target, geom)
    prepared_identity = None
    window_evidence = None
    if geom.schema_version == "3" and verified_window_inputs is not None:
        output_bytes = serialize_correction_output(geom)
        output_sha256 = hashlib.sha256(output_bytes).hexdigest()
        feature_states = FeatureStatesArtifactV1(
            output_sha256=output_sha256, claims=feature_state_claims,
        )
        feature_states_bytes = serialize_feature_states(feature_states)
        prepared_identity = PreparedCandidateIdentity(
            output_bytes=output_bytes,
            output_sha256=output_sha256,
            feature_states_bytes=feature_states_bytes,
            feature_states_sha256=hashlib.sha256(feature_states_bytes).hexdigest(),
        )
        try:
            window_evidence = derive_window_evidence_ledger(
                geom, host_claims=window_host_claims,
                verified_inputs=verified_window_inputs,
                candidate_identity=prepared_identity, tolerances=tol,
            )
        except WindowDirectionBindingError as exc:
            raise WindowHostResolutionError(
                map_direction_binding_error(
                    exc, geom=geom, verified_inputs=verified_window_inputs, phase="final",
                ),
                phase="final",
                context=exc.context,
            ) from exc
    return FinalizeResult(
        geom=geom,
        audit_payload={"corrections": geom.corrections, "conflicts": geom.conflicts, "unsupported": geom.unsupported},
        feature_state_claims=feature_state_claims,
        window_host_claims=window_host_claims,
        window_evidence_ledger=window_evidence,
        verified_window_resolver_inputs=verified_window_inputs,
        prepared_candidate_identity=prepared_identity,
    )
