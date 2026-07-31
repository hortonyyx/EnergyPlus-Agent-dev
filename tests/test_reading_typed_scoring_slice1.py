"""Slice 1 locks for reading contract, V9 wire, and total results."""

from __future__ import annotations

import json
import shutil
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
    wrong_adapter = decide_score_capability(
        gt_identity=gt_identity,
        stage="reading",
        product_schema="reading_views_v1",
        view_manifest=manifest,
        reading_adapter_version="reading_typed_adapter_v0",
    )
    wrong_detector = decide_score_capability(
        gt_identity=gt_identity,
        stage="reading",
        product_schema="reading_views_v1",
        view_manifest=manifest,
        reading_contract_detector_version="reading_contract_detector_v0",
    )
    assert accepted.path == "c2_v3"
    assert rejected.path == "not_applicable"
    assert rejected.reason == "unsupported_reading_contract"
    assert (wrong_adapter.path, wrong_adapter.reason) == (
        "not_applicable",
        "unsupported_reading_contract",
    )
    assert (wrong_detector.path, wrong_detector.reason) == (
        "not_applicable",
        "unsupported_reading_contract",
    )


@pytest.mark.parametrize(
    ("raw", "contract_id", "reason"),
    [
        ([], "unrecognized", "reading_output_not_object"),
        ({}, "unrecognized", "reading_views_missing"),
        ({"views": []}, "unrecognized", "reading_views_not_object"),
        ({"views": {1: {}}}, "unrecognized", "reading_view_id_invalid"),
        (
            {
                "schema_version": "3",
                "segments": [],
                "openings": [],
                "elevation_observations": [],
            },
            "unrecognized",
            "reading_views_missing",
        ),
        ({"views": {"plan": None}}, "reading_views_v1", None),
    ],
)
def test_detector_is_total_and_leaves_per_view_shape_to_adapter(
    raw, contract_id, reason
):
    from src.agent.judge.reading_typed_adapter import identify_reading_contract

    decision = identify_reading_contract(raw)
    assert decision.contract_id == contract_id
    assert decision.reason == reason


def test_non_object_reading_product_still_gets_total_na_artifacts(tmp_path):
    sidecar, artifacts = _grade_payload(
        tmp_path,
        [],
        name="non_object_reading",
    )
    assert sidecar["payload"]["kind"] == "not_applicable"
    assert sidecar["payload"]["reason"] == "unsupported_reading_contract"
    assert Path(artifacts["grade"]).read_bytes().startswith(b"\x89PNG")


def test_reading_score_error_does_not_abort_later_attempts_in_exploratory(
    tmp_path, monkeypatch
):
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from src.agent.judge.score_schema import load_score_gt_identity
    import src.agent.judge.score_service as service

    run = tmp_path / "attempt_totality"
    meta = run / "_run"
    meta.mkdir(parents=True)
    for filename in ("view_manifest.json", "judge_score_bindings.json"):
        shutil.copyfile(REAL_RUN / "_run" / filename, meta / filename)
    payload = _real_payload()
    for attempt in (1, 2):
        attempt_dir = run / f"0_reading/attempts/{attempt:03d}"
        attempt_dir.mkdir(parents=True)
        (attempt_dir / "output.json").write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )

    original = service.score_typed_attempt

    def fail_first_attempt(**request):
        if request["product_identity"].attempt == 1:
            raise RuntimeError("test-only first-attempt fault")
        return original(**request)

    monkeypatch.setattr(service, "score_typed_attempt", fail_first_attempt)
    _identity, document = load_score_gt_identity(GT_FILE)
    assert document is not None
    with pytest.warns(RuntimeWarning, match="internal failure"):
        results = run_stage._render_all_typed_attempt_grades(
            "0_reading",
            document.case,
            run,
            document,
            manifest=RunManifest(case=document.case),
            grade=run_stage.GradeConfig(),
            gt_file=GT_FILE,
            run_profile="exploratory",
        )

    assert tuple(results) == (1, 2)
    first = json.loads(
        Path(results[1]["score_vs_gt"]).read_text(encoding="utf-8")
    )
    second = json.loads(
        Path(results[2]["score_vs_gt"]).read_text(encoding="utf-8")
    )
    assert first["payload"]["reason"] == "scorer_internal_failure"
    assert second["payload"]["kind"] == "c2_scored"
    assert second["certificates"]["reading_normalization"] is not None
    assert second["certificates"]["source_applicability"] is not None
    assert Path(results[2]["grade"]).read_bytes().startswith(b"\x89PNG")


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


def test_v9_row_contracts_reject_incoherent_na_and_target_shapes():
    from src.agent.judge.score_schema import (
        OpeningSourceScoreRowV1,
        ReadingSegmentScoreRowV1,
    )

    segment = {
        "row_contract": "reading_segment_v1",
        "target_id": "wall-1",
        "observation_id": None,
        "floor_id": "F1",
        "target_exterior": True,
        "status": "miss",
        "eligible_units": 1.0,
        "axis_alignment_error_m": None,
        "position_error_m": None,
        "extent_symmetric_difference_m": None,
        "na_reason": None,
    }
    ReadingSegmentScoreRowV1.model_validate(segment)
    with pytest.raises(ValidationError):
        ReadingSegmentScoreRowV1.model_validate(
            {
                **segment,
                "status": "not_applicable",
                "eligible_units": 1.0,
                "na_reason": "plan_frame_unavailable",
            }
        )
    with pytest.raises(ValidationError):
        ReadingSegmentScoreRowV1.model_validate(
            {
                **segment,
                "target_id": None,
                "target_exterior": True,
            }
        )

    source_row = {
        "target_id": "window-1",
        "target_kind": "window",
        "claim": "existence",
        "source_input_id": "elev",
        "channel": "elevation",
        "eligible_units": 0.0,
        "result": "not_applicable",
        "na_reason": "elevation_local_x_sense_disagreement",
        "matched_observation_ids": (),
        "expected_intervals": (),
        "observed_interval": None,
        "expected_scalar": None,
        "observed_scalar": None,
        "error_metric": "not_applicable",
        "error_value": None,
        "tolerance": None,
        "source_applicability_sha256": "a" * 64,
    }
    OpeningSourceScoreRowV1.model_validate(source_row)
    with pytest.raises(ValidationError):
        OpeningSourceScoreRowV1.model_validate(
            {
                **source_row,
                "eligible_units": 1.0,
            }
        )
    with pytest.raises(ValidationError):
        OpeningSourceScoreRowV1.model_validate(
            {
                **source_row,
                "result": "miss",
                "na_reason": None,
            }
        )


def test_v9_rejection_and_absent_certificate_payloads_cross_validate(tmp_path):
    from scripts.tool_scripts import run_stage
    from src.agent.judge.score_schema import (
        RejectedPayloadV9,
        ScoreSidecarV9,
        canonical_sha256,
    )
    from tests.test_c2_b4b_phase_d import _correction_v3_runstage_fixture

    with pytest.raises(ValidationError):
        RejectedPayloadV9(
            kind="rejected",
            error_code="invented_error",
            cause_code=None,
            gate_id="invented_gate",
            detail="invented_error",
            channel_applicability=(),
            unmeasurable_observations=0,
            visibility_counts={
                "nonzero_plan_origins": 0,
                "project_convention_vertical_datums": 0,
                "multiple_plan_view_floor_components": 0,
                "elevation_local_x_sense_disagreements": 0,
                "scorer_internal_failures": 0,
            },
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
    raw = json.loads(
        Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8")
    )
    raw["payload"]["unmeasurable_observations"] = 1
    raw["content_sha256"] = canonical_sha256(
        {key: value for key, value in raw.items() if key != "content_sha256"}
    )
    with pytest.raises(ValidationError):
        ScoreSidecarV9.model_validate_json(json.dumps(raw))


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
    from src.agent.judge.score_schema import ScoreSidecarV9

    sidecar = ScoreSidecarV9.model_validate_json(
        score.read_text(encoding="utf-8")
    )
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
    from src.agent.judge.score_schema import ScoreContractError, ScoreSidecarV9

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
    assert (
        ScoreSidecarV9.model_validate_json(internal.sidecar.model_dump_json())
        == internal.sidecar
    )

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
    assert (
        ScoreSidecarV9.model_validate_json(rejected.sidecar.model_dump_json())
        == rejected.sidecar
    )

    def explode_unmapped_contract(**_kwargs):
        raise ScoreContractError(
            "score_identity_chain_bridge",
            "scoring.input_identity",
        )

    monkeypatch.setattr(
        service,
        "score_typed_attempt",
        explode_unmapped_contract,
    )
    with pytest.warns(RuntimeWarning, match="internal failure"):
        unmapped = service.score_attempt_service(
            typed_request={**request, "run_profile": "dev"}
        )
    assert unmapped.payload.kind == "not_applicable"
    assert unmapped.payload.reason == "scorer_internal_failure"
    assert unmapped.payload.visibility_counts.scorer_internal_failures == 1


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
