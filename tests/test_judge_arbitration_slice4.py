"""Slice-4 release, cache, and public-wire locks."""
from __future__ import annotations

import hashlib
import json

import pytest

from src.agent.judge.identity_provenance import (
    IDENTITY_CONTRACT_VERSION,
    SEGMENT_SCORER_IDENTITY_RELEASE_MAP,
    identity_contract_for_segment_scorer,
)
from src.agent.judge.score_config import load_judge_score_config
from src.agent.judge.score_schema import (
    SEGMENT_SCORER_HELPER_VERSION,
    C2ToleranceIdentityV8,
    CapabilityDecisionV8,
    GtIdentityV8,
    HelperIdentityV8,
    ManifestIdentityV8,
    NotApplicablePayloadV8,
    ProductIdentityV8,
    ScoreIdentityV8,
    SegmentScoreRowV8,
    build_phase_a_sidecar,
    canonical_sha256,
    load_cached_score,
)

_H = "a" * 64


def _identity() -> ScoreIdentityV8:
    config = load_judge_score_config("src/configs/judge_score.yaml")
    return ScoreIdentityV8(
        gt=GtIdentityV8(
            path_id="gt.json",
            file_sha256=_H,
            content_sha256="b" * 64,
            schema_version=3,
            profile="c2_simple_orthogonal_no_holes",
            coordinate_frame="building_axis_world_m",
            verification_status="human_verified",
            loader_helper_version="gt_typed_loader_v1",
        ),
        product=ProductIdentityV8(
            stage="reading",
            attempt=0,
            output_sha256="c" * 64,
            output_schema="3",
            accepted=False,
            accepted_stage_record_sha256=None,
            source="attempt_output",
        ),
        manifest=ManifestIdentityV8(
            base_view_manifest_sha256="d" * 64,
            effective_view_manifest_sha256="d" * 64,
            case_metadata_sha256="e" * 64,
            completeness_ruleset="1",
            completeness_overlay_sha256=None,
            score_view_bindings_sha256=None,
        ),
        helpers=HelperIdentityV8(
            scorer_schema="8",
            segment_scorer=SEGMENT_SCORER_HELPER_VERSION,
            gt_to_va_adapter="b4b_gt_to_va_v1",
            denominator_helper="b4b_denominator_v1",
            grade_renderer="b4b_grade_png_v1",
            va_helper="facade_applicability_v1",
            vg_helper="facade_visibility_v1",
            claims_contract="1",
        ),
        capability=CapabilityDecisionV8(
            path="not_applicable",
            capability_key=("3", "c2", "reading", "3", "1", "1", "1", "c2"),
            reason="unsupported_view_contract",
            gate_id="scoring.capability",
        ),
        tolerances=C2ToleranceIdentityV8(
            profile_kind="judge_score_config_v1",
            values=config,
            content_sha256=canonical_sha256(config.model_dump(mode="json")),
        ),
        reference_applicability_sha256=None,
        product_applicability_sha256=None,
        absence_applicability_sha256=None,
    )


def test_helper_release_is_exactly_cross_verified_with_identity_contract() -> None:
    assert SEGMENT_SCORER_HELPER_VERSION == "b4b_segment_score_v3_ic1"
    assert IDENTITY_CONTRACT_VERSION == "1"
    assert dict(SEGMENT_SCORER_IDENTITY_RELEASE_MAP) == {
        "b4b_segment_score_v3_ic1": "1",
    }
    assert identity_contract_for_segment_scorer(
        SEGMENT_SCORER_HELPER_VERSION
    ) == IDENTITY_CONTRACT_VERSION
    with pytest.raises(ValueError, match="unknown segment scorer helper"):
        identity_contract_for_segment_scorer("b4b_segment_score_v2")


def test_old_v3_helper_sidecar_is_a_cache_miss(tmp_path) -> None:
    grade = tmp_path / "grade.png"
    grade.write_bytes(b"slice-4-cache-lock")
    identity = _identity()
    sidecar = build_phase_a_sidecar(
        identity=identity,
        payload=NotApplicablePayloadV8(
            kind="not_applicable",
            reason="unsupported_view_contract",
            detail="cache release lock",
        ),
        grade_png_sha256=hashlib.sha256(grade.read_bytes()).hexdigest(),
    )
    raw = sidecar.model_dump(mode="json")
    raw["identity"]["helpers"]["segment_scorer"] = "b4b_segment_score_v2"
    raw["content_sha256"] = canonical_sha256({
        key: value
        for key, value in raw.items()
        if key != "content_sha256"
    })
    path = tmp_path / "score_vs_gt.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_cached_score(
        path,
        grade_path=grade,
        expected_identity=identity,
    ) is None


def test_exact_audit_values_do_not_widen_public_segment_row_v8() -> None:
    assert tuple(SegmentScoreRowV8.model_fields) == (
        "target_id",
        "observation_id",
        "floor_id",
        "exterior",
        "status",
        "axis_alignment_error_m",
        "position_error_m",
        "extent_symmetric_difference_m",
    )
