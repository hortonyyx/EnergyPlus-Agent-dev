"""E4-output-contract spec v2 §10.1 — strict contract types, explicit
dispatch, derive matrix, and the §3.2bis orientation-resolution four-table."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.correction.feature_state import FeatureStatesArtifactV1
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.orientation import (
    NorthAxisAssumptionAuditV1,
    OrientationConflictV1,
    OrientationEvidenceSetV1,
    OrientationNeedsInputError,
    OrientationRunConfigV1,
    build_orientation_resolution_input,
    finalize_orientation_enrichment,
    verify_orientation_resolution,
)
from src.agent.correction.parse import correction_target
from src.agent.correction.schema import NorthAxisEvidence
from src.agent.output_coordinates import (
    AcceptedCorrectionRef,
    LegacyStandaloneIntakeRef,
    OutputCoordinateContract,
    VerifiedAcceptedCorrection,
    derive_output_coordinate_contract,
    legacy_contract_for_unversioned_intake,
    sha256_bytes,
    verify_integrated_gate1_correction,
)
from src.validator.checks.schema import CheckLayer, CheckReport

HEX64 = "a" * 64


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _clean_report() -> CheckReport:
    rep = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    rep.add_pass("x", CheckLayer.INVARIANT)
    return rep


def _v3_vg_finalized():
    """A real Vg-release v3 finalize result (facade segments materialized by
    the one real writer; north_axis still None)."""
    payload = {
        "schema_version": "3",
        "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{
            "id": "F1", "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": [[0, 0], [10, 0], [10, 8], [0, 8]]},
            "cells": [{"id": "F1_A", "x": [0, 10], "y": [0, 8]}],
        }],
        "windows": [],
    }
    with tempfile.TemporaryDirectory() as td:
        return finalize_correction_draw(
            payload, vector_dir=Path(td), target=correction_target("orthogonal_polygon")
        )


def _verified_base(finalized) -> VerifiedAcceptedCorrection:
    raw = finalized.geom.model_dump_json(indent=2).encode("utf-8")
    fs = FeatureStatesArtifactV1(
        output_sha256=sha256_bytes(raw), claims=finalized.feature_state_claims
    )
    return verify_integrated_gate1_correction(
        raw_output_bytes=raw, correction_report=_clean_report(), feature_states=fs
    )


def _resolve(base_hash: str, evidence_set: OrientationEvidenceSetV1, mode: str):
    resolution_input, evidence_bytes = build_orientation_resolution_input(
        base_correction_sha256=base_hash, evidence_set=evidence_set, completion_mode=mode
    )
    run_config_bytes = (
        OrientationRunConfigV1(completion_mode=mode).model_dump_json(indent=2).encode("utf-8")
    )
    return verify_orientation_resolution(
        raw_resolution_input_bytes=resolution_input.model_dump_json(indent=2).encode("utf-8"),
        raw_evidence_set_bytes=evidence_bytes,
        raw_run_config_bytes=run_config_bytes,
    )


def _enriched_verified(mode="prior_fill", evidence_set=None) -> VerifiedAcceptedCorrection:
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(base.ref.output_sha256, evidence_set or OrientationEvidenceSetV1(), mode)
    enriched = finalize_orientation_enrichment(base, resolution)
    raw = enriched.geom.model_dump_json(indent=2).encode("utf-8")
    fs = FeatureStatesArtifactV1(
        output_sha256=sha256_bytes(raw), claims=enriched.feature_state_claims
    )
    return verify_integrated_gate1_correction(
        raw_output_bytes=raw, correction_report=_clean_report(), feature_states=fs
    )


def _relative_kwargs(**overrides):
    kwargs = dict(
        mode="relative_north_axis",
        source=AcceptedCorrectionRef(
            schema_version="3", output_sha256=HEX64, acceptance="integrated_gate1",
            artifact_contract="correction_e4_orientation_v1",
        ),
        geometry_frame="building_axis_absolute_values",
        global_geometry_coordinate_system="Relative",
        daylighting_reference_point_coordinate_system="Relative",
        rectangular_surface_coordinate_system="Relative",
        zone_origin_policy="all_zero", zone_direction_policy="all_zero",
        north_axis_owner="accepted_correction_orientation",
        north_axis_deg=90.0, orientation_provenance="observed",
        orientation_source_ids=("s1",), geometry_snapshot_sha256="b" * 64,
    )
    kwargs.update(overrides)
    return kwargs


# --------------------------------------------------------------------------- #
# §10.1 strict wire
# --------------------------------------------------------------------------- #
def test_contract_rejects_extra_field():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(**_relative_kwargs(), bogus_extra="x")


def test_contract_rejects_bad_digest():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(**_relative_kwargs(geometry_snapshot_sha256="not-hex"))


@pytest.mark.parametrize("theta", [float("nan"), float("inf"), 360.0, -1.0])
def test_contract_rejects_bad_theta(theta):
    with pytest.raises(ValidationError):
        OutputCoordinateContract(**_relative_kwargs(north_axis_deg=theta))


def test_contract_is_frozen_including_nested_ref():
    contract = OutputCoordinateContract(**_relative_kwargs())
    with pytest.raises(ValidationError):
        contract.north_axis_deg = 0.0
    with pytest.raises(ValidationError):
        contract.source.output_sha256 = "c" * 64


# --------------------------------------------------------------------------- #
# §10.1 mode combination matrix
# --------------------------------------------------------------------------- #
def test_relative_plus_v1_source_rejected():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(**_relative_kwargs(
            source=AcceptedCorrectionRef(
                schema_version="1", output_sha256=HEX64,
                acceptance="integrated_gate1", artifact_contract="base_v2",
            ),
        ))


def test_world_plus_v3_source_rejected():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(
            mode="world_legacy",
            source=AcceptedCorrectionRef(
                schema_version="3", output_sha256=HEX64,
                acceptance="integrated_gate1",
                artifact_contract="correction_e4_orientation_v1",
            ),
            geometry_frame="building_axis_absolute_values",
            global_geometry_coordinate_system="World",
            daylighting_reference_point_coordinate_system="Relative",
            rectangular_surface_coordinate_system="Relative",
            zone_origin_policy="preserve_legacy", zone_direction_policy="preserve_legacy",
            north_axis_owner="legacy_mep_placeholder", north_axis_deg=0.0,
            geometry_snapshot_sha256="b" * 64,
        )


def test_relative_plus_preserve_origins_rejected():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(**_relative_kwargs(zone_origin_policy="preserve_legacy"))


def test_legacy_with_orientation_metadata_rejected():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(
            mode="world_legacy",
            source=LegacyStandaloneIntakeRef(intake_output_sha256=HEX64),
            geometry_frame="building_axis_absolute_values",
            global_geometry_coordinate_system="World",
            daylighting_reference_point_coordinate_system="Relative",
            rectangular_surface_coordinate_system="Relative",
            zone_origin_policy="preserve_legacy", zone_direction_policy="preserve_legacy",
            north_axis_owner="legacy_mep_placeholder", north_axis_deg=0.0,
            orientation_provenance="assumed",
        )


def test_b2_artifact_cannot_claim_relative():
    with pytest.raises(ValidationError):
        OutputCoordinateContract(**_relative_kwargs(
            source=AcceptedCorrectionRef(
                schema_version="3", output_sha256=HEX64,
                acceptance="integrated_gate1", artifact_contract="correction_b2_v1",
            ),
        ))


def test_manifest_acceptance_requires_run_identity():
    with pytest.raises(ValidationError):
        AcceptedCorrectionRef(
            schema_version="3", output_sha256=HEX64, acceptance="manifest",
            artifact_contract="correction_e4_orientation_v1",
        )
    with pytest.raises(ValidationError):
        AcceptedCorrectionRef(
            schema_version="3", output_sha256=HEX64, acceptance="integrated_gate1",
            run_id="0" * 32, accepted_attempt=1,
            artifact_contract="correction_e4_orientation_v1",
        )


# --------------------------------------------------------------------------- #
# §10.1 derive matrix
# --------------------------------------------------------------------------- #
def test_prior_fill_derives_relative_with_assumed_zero():
    verified = _enriched_verified("prior_fill")
    contract = derive_output_coordinate_contract(verified, geometry_snapshot_sha256="b" * 64)
    assert contract.mode == "relative_north_axis"
    assert contract.north_axis_deg == 0.0
    assert contract.orientation_provenance == "assumed"
    assert contract.orientation_method == "prior_fill_default_zero_v1"
    assert contract.global_geometry_coordinate_system == "Relative"
    assert contract.zone_origin_policy == "all_zero"


def test_observed_zero_also_derives_relative_and_stays_distinguishable():
    ev = OrientationEvidenceSetV1(accepted_candidates=(
        NorthAxisEvidence(value_deg=0.0, provenance="observed", source_ids=["site_plan"]),
    ))
    verified = _enriched_verified("prior_fill", evidence_set=ev)
    contract = derive_output_coordinate_contract(verified, geometry_snapshot_sha256="b" * 64)
    assert contract.mode == "relative_north_axis"
    assert contract.north_axis_deg == 0.0
    assert contract.orientation_provenance == "observed"  # NOT assumed
    assert contract.orientation_source_ids == ("site_plan",)


def test_theta_zero_and_ninety_take_the_same_mode_branch():
    """Dispatch sentinel: theta==0.0 and theta==90.0 both produce Relative —
    proof there is no `if theta` truthiness branch anywhere in the derive."""
    ev90 = OrientationEvidenceSetV1(accepted_candidates=(
        NorthAxisEvidence(value_deg=90.0, provenance="observed", source_ids=["s"]),
    ))
    c0 = derive_output_coordinate_contract(
        _enriched_verified("prior_fill"), geometry_snapshot_sha256="b" * 64)
    c90 = derive_output_coordinate_contract(
        _enriched_verified("prior_fill", evidence_set=ev90), geometry_snapshot_sha256="b" * 64)
    assert c0.mode == c90.mode == "relative_north_axis"
    assert (c0.north_axis_deg, c90.north_axis_deg) == (0.0, 90.0)


def test_v1_derives_world_legacy_and_ignores_legacy_extra_north_axis():
    # legacy v1 payload carrying a rogue extra `north_axis` field (the
    # permissive V1 schema allows extras) — derive must NOT read it.
    raw = (
        b'{"schema_version": "1", "footprint_x": [0, 5], "footprint_y": [0, 4],'
        b' "floors": [{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,'
        b' "cells": [{"id": "A", "x": [0, 5], "y": [0, 4]}]}],'
        b' "north_axis": 270.0}'
    )
    from src.agent.correction.feature_state import FeatureStateClaimsV1
    claims = FeatureStateClaimsV1(
        target_schema_version="1", phase_contract="b2",
        cell_polygon="not_declared", per_floor_footprint="not_declared",
        facade_segments="not_declared", typed_north_axis="not_declared",
    )
    fs = FeatureStatesArtifactV1(output_sha256=sha256_bytes(raw), claims=claims)
    verified = verify_integrated_gate1_correction(
        raw_output_bytes=raw, correction_report=_clean_report(), feature_states=fs
    )
    contract = derive_output_coordinate_contract(verified, geometry_snapshot_sha256="b" * 64)
    assert contract.mode == "world_legacy"
    assert contract.north_axis_deg == 0.0
    assert contract.global_geometry_coordinate_system == "World"
    # legacy keeps A4/A5 at their true current defaults, NOT flipped to World
    assert contract.daylighting_reference_point_coordinate_system == "Relative"
    assert contract.rectangular_surface_coordinate_system == "Relative"


def test_v3_b2_artifact_without_enrichment_blocks_not_falls_back():
    finalized = _v3_vg_finalized()
    verified = _verified_base(finalized)  # correction_b2_v1, north_axis None
    with pytest.raises(ValueError, match="masquerade|correction_e4_orientation_v1"):
        derive_output_coordinate_contract(verified, geometry_snapshot_sha256="b" * 64)


def test_digest_drift_rejected_by_derive():
    verified = _enriched_verified("prior_fill")
    tampered = VerifiedAcceptedCorrection(
        ref=verified.ref,
        raw_output_bytes=verified.raw_output_bytes + b" ",
        raw_feature_states_bytes=verified.raw_feature_states_bytes,
    )
    with pytest.raises(ValueError, match="output_sha256"):
        derive_output_coordinate_contract(tampered, geometry_snapshot_sha256="b" * 64)


def test_forged_populated_north_claims_cannot_upgrade_relative():
    """BO-CR4 attack negative: a caller cannot promote a B2 claim by merely
    changing strings to e4/populated. The verifier must fresh-derive the
    helper tuple and every feature state from correction bytes."""
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(base.ref.output_sha256, OrientationEvidenceSetV1(), "prior_fill")
    enriched = finalize_orientation_enrichment(base, resolution)
    raw = enriched.geom.model_dump_json(indent=2).encode("utf-8")
    from src.agent.correction.feature_state import FeatureStateClaimsV1

    forged = FeatureStateClaimsV1(
        target_schema_version="3", phase_contract="e4_orientation",
        helper_versions=(), cell_polygon="not_declared",
        per_floor_footprint="not_declared", facade_segments="not_declared",
        typed_north_axis="populated",
    )
    with pytest.raises(ValueError, match="fresh re-derivation|forged"):
        verify_integrated_gate1_correction(
            raw_output_bytes=raw, correction_report=_clean_report(),
            feature_states=FeatureStatesArtifactV1(
                output_sha256=sha256_bytes(raw), claims=forged,
            ),
        )


def test_legacy_standalone_factory_shape():
    c = legacy_contract_for_unversioned_intake(intake_output_sha256=HEX64)
    assert c.mode == "world_legacy"
    assert isinstance(c.source, LegacyStandaloneIntakeRef)
    assert c.geometry_snapshot_sha256 is None
    assert c.north_axis_deg == 0.0


# --------------------------------------------------------------------------- #
# §3.2bis orientation resolution four-table
# --------------------------------------------------------------------------- #
def test_zero_evidence_prior_fill_generates_exact_assumed_zero():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(base.ref.output_sha256, OrientationEvidenceSetV1(), "prior_fill")
    result = finalize_orientation_enrichment(base, resolution)
    ev = result.geom.north_axis
    assert ev.value_deg == 0.0
    assert ev.provenance == "assumed"
    assert ev.source_ids == []
    assert ev.uncertainty_deg is None
    assert ev.method == "prior_fill_default_zero_v1"
    assert ev.frame_transform_hash is None
    assert result.feature_state_claims.typed_north_axis == "populated"
    assert result.feature_state_claims.phase_contract == "e4_orientation"


def test_zero_evidence_interactive_is_needs_input_not_default():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(base.ref.output_sha256, OrientationEvidenceSetV1(), "interactive")
    with pytest.raises(OrientationNeedsInputError):
        finalize_orientation_enrichment(base, resolution)


def test_conflict_blocks_never_degrades_to_assumed_zero():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    ev = OrientationEvidenceSetV1(conflicts=(
        OrientationConflictV1(conflict_id="c" * 64, reason="two arrows disagree", source_ids=("a", "b")),
    ))
    resolution = _resolve(base.ref.output_sha256, ev, "prior_fill")
    with pytest.raises(ValueError, match="conflict"):
        finalize_orientation_enrichment(base, resolution)


def test_multiple_accepted_candidates_block():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    ev = OrientationEvidenceSetV1(accepted_candidates=(
        NorthAxisEvidence(value_deg=10.0, provenance="observed", source_ids=["a"]),
        NorthAxisEvidence(value_deg=200.0, provenance="observed", source_ids=["b"]),
    ))
    resolution = _resolve(base.ref.output_sha256, ev, "prior_fill")
    with pytest.raises(ValueError, match="multiple|2 accepted"):
        finalize_orientation_enrichment(base, resolution)


def test_evidence_hash_drift_cannot_impersonate_zero_evidence():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution_input, evidence_bytes = build_orientation_resolution_input(
        base_correction_sha256=base.ref.output_sha256,
        evidence_set=OrientationEvidenceSetV1(), completion_mode="prior_fill",
    )
    run_config_bytes = OrientationRunConfigV1(
        completion_mode="prior_fill").model_dump_json(indent=2).encode("utf-8")
    with pytest.raises(ValueError, match="evidence"):
        verify_orientation_resolution(
            raw_resolution_input_bytes=resolution_input.model_dump_json(indent=2).encode("utf-8"),
            raw_evidence_set_bytes=evidence_bytes + b" ",  # drifted artifact
            raw_run_config_bytes=run_config_bytes,
        )


def test_completion_mode_mismatch_with_run_config_rejected():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution_input, evidence_bytes = build_orientation_resolution_input(
        base_correction_sha256=base.ref.output_sha256,
        evidence_set=OrientationEvidenceSetV1(), completion_mode="prior_fill",
    )
    interactive_cfg = OrientationRunConfigV1(
        completion_mode="interactive").model_dump_json(indent=2).encode("utf-8")
    with pytest.raises(ValueError, match="completion_mode"):
        verify_orientation_resolution(
            raw_resolution_input_bytes=resolution_input.model_dump_json(indent=2).encode("utf-8"),
            raw_evidence_set_bytes=evidence_bytes,
            raw_run_config_bytes=interactive_cfg,
        )


def test_enrichment_changes_only_north_axis_and_audit():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(base.ref.output_sha256, OrientationEvidenceSetV1(), "prior_fill")
    result = finalize_orientation_enrichment(base, resolution)
    before = finalized.geom.model_dump(exclude={"north_axis"})
    after = result.geom.model_dump(exclude={"north_axis"})
    assert before == after
    assert finalized.geom.north_axis is None and result.geom.north_axis is not None


def test_enrichment_requires_unpopulated_vg_base():
    verified_enriched = _enriched_verified("prior_fill")
    # feed an ALREADY-enriched correction back in as base: must refuse
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(
        verified_enriched.ref.output_sha256, OrientationEvidenceSetV1(), "prior_fill")
    with pytest.raises(ValueError):
        # resolution is bound to the enriched hash, base is the Vg draw — mismatch
        finalize_orientation_enrichment(base, resolution)


# --------------------------------------------------------------------------- #
# assumed-0 audit wire (§3.2bis / §10.1)
# --------------------------------------------------------------------------- #
def test_assumption_audit_wire_is_exact():
    audit = NorthAxisAssumptionAuditV1(value_deg=0.0)
    assert audit.policy_ref == "c2_e4.north_axis.default_zero.v1"
    assert audit.knowledge_ref is None
    assert audit.knowledge_ref_na_reason == "policy_default_not_knowledge_lookup"
    assert audit.evidence_candidate_count == 0
    with pytest.raises(ValidationError):
        NorthAxisAssumptionAuditV1(value_deg=0.5)


def test_assumption_audit_lands_in_enrichment_audit_payload():
    finalized = _v3_vg_finalized()
    base = _verified_base(finalized)
    resolution = _resolve(base.ref.output_sha256, OrientationEvidenceSetV1(), "prior_fill")
    result = finalize_orientation_enrichment(base, resolution)
    orientation = result.audit_payload["orientation"]
    assert orientation["resolution_kind"] == "prior_fill_assumed_zero"
    audit = orientation["assumption_audit"]
    assert audit["policy_ref"] == "c2_e4.north_axis.default_zero.v1"
    assert audit["knowledge_ref"] is None
    assert audit["knowledge_ref_na_reason"] == "policy_default_not_knowledge_lookup"
