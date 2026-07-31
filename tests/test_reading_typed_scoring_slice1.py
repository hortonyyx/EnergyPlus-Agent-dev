"""Slice 1 locks for reading contract, V9 wire, and total results."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.test_reading_typed_scoring_slice0 import (
    GT_FILE,
    REAL_RUN,
    _grade_payload,
    _real_payload,
)


def _trusted_request(payload: dict) -> dict:
    from src.agent.execution.manifest import hash_text
    from src.agent.execution.view_manifest import ViewManifest
    from src.agent.judge.reading_typed_adapter import identify_reading_contract
    from src.agent.judge.score_config import load_judge_score_config
    from src.agent.judge.score_inputs import (
        load_completeness_overlay,
        load_score_view_bindings,
    )
    from src.agent.judge.score_schema import (
        build_product_identity,
        load_score_gt_identity,
    )

    gt_identity, gt = load_score_gt_identity(GT_FILE)
    assert gt is not None
    base = ViewManifest.model_validate_json(
        (REAL_RUN / "_run/view_manifest.json").read_text(encoding="utf-8")
    )
    bindings = load_score_view_bindings(
        REAL_RUN / "_run/judge_score_bindings.json",
        expected_case_id=gt.case,
        expected_gt_content_sha256=gt_identity.content_sha256,
        expected_case_metadata_sha256=base.case_metadata_sha256,
        expected_base_view_manifest_sha256=base.content_sha256,
    )
    overlay = load_completeness_overlay(
        None,
        expected_case_id=gt.case,
        expected_gt_content_sha256=gt_identity.content_sha256,
        expected_base_view_manifest_sha256=base.content_sha256,
    )
    text = json.dumps(payload, sort_keys=True)
    product = build_product_identity(
        stage="reading",
        attempt=3,
        output_sha256=hash_text(text),
        output_schema=identify_reading_contract(payload).contract_id,
        source="attempt_output",
        accepted_stage_record=None,
    )
    return {
        "gt_identity": gt_identity,
        "gt": gt,
        "stage": "reading",
        "product_payload": payload,
        "product_identity": product,
        "base_view_manifest": base,
        "score_bindings": bindings,
        "completeness_overlay": overlay,
        "c2_config": load_judge_score_config(
            "src/configs/judge_score.yaml"
        ),
        "window_host_proof": None,
    }


def test_detector_and_capability_use_reading_views_contract_not_schema_default():
    from src.agent.judge.reading_typed_adapter import identify_reading_contract
    from src.agent.judge.score_schema import decide_score_capability

    request = _trusted_request(_real_payload())
    manifest = request["base_view_manifest"]
    gt_identity = request["gt_identity"]
    assert identify_reading_contract(_real_payload()).contract_id == (
        "reading_views_v1"
    )
    accepted = decide_score_capability(
        gt_identity=gt_identity,
        stage="reading",
        product_schema="reading_views_v1",
        view_manifest=manifest,
    )
    rejected = decide_score_capability(
        gt_identity=gt_identity,
        stage="reading",
        product_schema="3",
        view_manifest=manifest,
    )
    assert accepted.path == "c2_v3"
    assert rejected.path == "not_applicable"
    assert rejected.reason == "unsupported_reading_contract"


def test_component_applicability_separates_status_from_denominator_disposition():
    from src.agent.judge.score_schema import ReadingComponentApplicabilityV1

    applicable = ReadingComponentApplicabilityV1(
        source_input_id="plan",
        channel="plan",
        component="plan_segments",
        floor_ids=("F1",),
        status="applicable",
        reasons=(),
        cause_class="none",
        denominator_disposition="score",
        observation_count=0,
        transform_sha256=None,
    )
    assert applicable.observation_count == 0
    frame_na = ReadingComponentApplicabilityV1(
        source_input_id="elev",
        channel="elevation",
        component="elevation_opening_xy",
        floor_ids=("F1",),
        status="not_applicable",
        reasons=("elevation_local_x_sense_disagreement",),
        cause_class="trusted_frame",
        denominator_disposition="retain_as_miss",
        observation_count=0,
        transform_sha256=None,
    )
    assert frame_na.denominator_disposition == "retain_as_miss"
    with pytest.raises(ValidationError):
        frame_na.model_copy(
            update={"denominator_disposition": "filter"}
        ).__class__.model_validate(
            {
                **frame_na.model_dump(mode="json"),
                "denominator_disposition": "filter",
            }
        )


def test_denominator_constructor_accepts_only_canonical_trusted_exclusions():
    from src.agent.judge.reading_typed_adapter import (
        derive_reading_denominator_v1,
    )
    from src.agent.judge.score_schema import ReadingFilteredComponentBasisV1

    request = _trusted_request(_real_payload())
    first = ReadingFilteredComponentBasisV1(
        source_input_id="1f_view",
        component="plan_openings",
        floor_ids=("F1",),
        cause_class="trusted_input",
        reasons=("trusted_plan_capability_unavailable",),
    )
    second = ReadingFilteredComponentBasisV1(
        source_input_id="East_view",
        component="elevation_opening_z",
        floor_ids=("F1",),
        cause_class="trusted_input",
        reasons=("trusted_vertical_capability_unavailable",),
    )
    left = derive_reading_denominator_v1(
        request["gt"],
        request["base_view_manifest"],
        request["score_bindings"],
        (first, second),
    )
    right = derive_reading_denominator_v1(
        request["gt"],
        request["base_view_manifest"],
        request["score_bindings"],
        (second, first),
    )
    assert left == right
    basis, atoms, basis_sha, denominator_sha = left
    assert atoms
    assert basis.content_sha256 == basis_sha
    assert len(denominator_sha) == 64
    with pytest.raises(ValidationError):
        ReadingFilteredComponentBasisV1.model_validate(
            {
                **first.model_dump(mode="json"),
                "cause_class": "trusted_frame",
            }
        )


def test_v9_cache_hits_exact_identity_and_treats_v8_as_miss(tmp_path):
    from scripts.tool_scripts import run_stage
    from src.agent.judge.score_schema import load_cached_score
    from tests.test_c2_b4b_phase_d import (
        _correction_v3_runstage_fixture,
        _identity,
        _sidecar,
    )

    gt, run, manifest, gt_file = _correction_v3_runstage_fixture(tmp_path)
    accepted = manifest.accepted("1_correction")
    attempt = (
        run / "1_correction/attempts" / f"{accepted.accepted_attempt:03d}"
    )
    artifacts = run_stage._grade_typed_attempt_artifacts(
        "1_correction",
        gt.case,
        attempt,
        gt,
        gt_file=gt_file,
        manifest=manifest,
        grade=run_stage.GradeConfig(),
    )
    score = Path(artifacts["score_vs_gt"])
    grade = Path(artifacts["grade"])
    raw = json.loads(score.read_text(encoding="utf-8"))
    from src.agent.judge.score_schema import ScoreSidecarV9

    sidecar = ScoreSidecarV9.model_validate(raw)
    assert load_cached_score(
        score, grade_path=grade, expected_identity=sidecar.identity
    ) == sidecar
    changed = sidecar.identity.model_copy(
        update={
            "score_manifest_sha256": (
                "0" * 64
                if sidecar.identity.score_manifest_sha256 != "0" * 64
                else "1" * 64
            )
        }
    )
    assert (
        load_cached_score(score, grade_path=grade, expected_identity=changed)
        is None
    )
    v8 = _sidecar(_identity(), grade.read_bytes())
    score.write_text(v8.model_dump_json(), encoding="utf-8")
    assert (
        load_cached_score(
            score, grade_path=grade, expected_identity=sidecar.identity
        )
        is None
    )


def test_totalizer_emits_internal_na_and_trusted_rejected(monkeypatch):
    import src.agent.judge.score_service as service
    from src.agent.judge.score_schema import ScoreContractError

    request = _trusted_request(_real_payload())

    def explode_internal(**_kwargs):
        raise RuntimeError("test-only internal detail must not enter wire")

    monkeypatch.setattr(service, "score_typed_attempt", explode_internal)
    with pytest.warns(RuntimeWarning, match="internal failure"):
        internal = service.score_attempt_service(
            typed_request={**request, "run_profile": "exploratory"}
        )
    assert internal.payload.kind == "not_applicable"
    assert internal.payload.reason == "scorer_internal_failure"
    assert internal.payload.visibility_counts.scorer_internal_failures == 1
    assert "test-only" not in internal.sidecar.model_dump_json()
    assert internal.grade_png.startswith(b"\x89PNG")

    def explode_trusted(**_kwargs):
        raise ScoreContractError(
            "score_view_binding_invalid",
            "scoring.view_bindings",
        )

    monkeypatch.setattr(service, "score_typed_attempt", explode_trusted)
    rejected = service.score_attempt_service(typed_request=request)
    assert rejected.payload.kind == "rejected"
    assert rejected.payload.error_code == "score_view_binding_invalid"
    assert rejected.grade_png.startswith(b"\x89PNG")


@pytest.mark.parametrize("run_profile", ["golden", "regression"])
def test_strict_profile_commits_top_level_na_before_raising(
    tmp_path, run_profile
):
    from src.agent.judge.score_service import TopLevelNotApplicableError

    with pytest.raises(TopLevelNotApplicableError):
        _grade_payload(
            tmp_path,
            {
                "schema_version": "3",
                "segments": [],
                "openings": [],
                "elevation_observations": [],
            },
            name=f"strict_{run_profile}",
            run_profile=run_profile,
        )
    attempt = (
        tmp_path
        / f"strict_{run_profile}/0_reading/attempts/003"
    )
    assert (attempt / "score_vs_gt.json").exists()
    assert (attempt / "grade.png").read_bytes().startswith(b"\x89PNG")


def test_exploratory_na_returns_artifacts_and_empty_criteria(tmp_path):
    sidecar, artifacts = _grade_payload(
        tmp_path,
        {
            "schema_version": "3",
            "segments": [],
            "openings": [],
            "elevation_observations": [],
        },
        name="exploratory_na",
    )
    assert sidecar["schema_version"] == "9"
    assert sidecar["payload"]["kind"] == "not_applicable"
    assert sidecar["payload"]["reason"] == "unsupported_reading_contract"
    assert artifacts["score_criteria"] == []
