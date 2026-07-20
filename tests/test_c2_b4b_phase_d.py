"""B4b Phase D closure: cache, artifact pair, typed grade, and boundaries."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest
from PIL import Image

from src.agent.judge.score_config import load_judge_score_config
from src.agent.judge.score_schema import (
    C2ToleranceIdentityV8, CapabilityDecisionV8, GtIdentityV8,
    HelperIdentityV8, ManifestIdentityV8, NotApplicablePayloadV8,
    ProductIdentityV8, ScoreContractError, ScoreIdentityV8,
    build_phase_a_sidecar, canonical_sha256, commit_score_artifacts,
    load_cached_score,
)

H = "a" * 64


def _identity() -> ScoreIdentityV8:
    config = load_judge_score_config("src/configs/judge_score.yaml")
    return ScoreIdentityV8(
        gt=GtIdentityV8(path_id="gt.json", file_sha256=H, content_sha256="b" * 64, schema_version=3,
            profile="c2_simple_orthogonal_no_holes", coordinate_frame="building_axis_world_m",
            verification_status="human_verified", loader_helper_version="gt_typed_loader_v1"),
        product=ProductIdentityV8(stage="reading", attempt=1, output_sha256="c" * 64, output_schema="3",
            accepted=False, accepted_stage_record_sha256=None, source="attempt_output"),
        manifest=ManifestIdentityV8(base_view_manifest_sha256="d" * 64, effective_view_manifest_sha256="e" * 64,
            case_metadata_sha256="f" * 64, completeness_ruleset="1", completeness_overlay_sha256="1" * 64,
            score_view_bindings_sha256="2" * 64),
        helpers=HelperIdentityV8(scorer_schema="8", segment_scorer="b4b_segment_score_v1",
            gt_to_va_adapter="b4b_gt_to_va_v1", denominator_helper="b4b_denominator_v1",
            grade_renderer="b4b_grade_png_v1", va_helper="va-1", vg_helper="vg-1", claims_contract="1"),
        capability=CapabilityDecisionV8(path="c2_v3", capability_key=("3", "c2", "reading", "3", "1", "1", "1", "c2"),
            reason=None, gate_id="scoring.capability"),
        tolerances=C2ToleranceIdentityV8(profile_kind="judge_score_config_v1", values=config,
            content_sha256=canonical_sha256(config.model_dump(mode="json"))),
        reference_applicability_sha256="3" * 64, product_applicability_sha256="4" * 64,
        absence_applicability_sha256="5" * 64,
    )


def _png_bytes(color=(255, 255, 255)) -> bytes:
    from io import BytesIO
    image = Image.new("RGB", (8, 8), color); result = BytesIO(); image.save(result, "PNG")
    return result.getvalue()


def _sidecar(identity: ScoreIdentityV8, png: bytes):
    return build_phase_a_sidecar(identity=identity, payload=NotApplicablePayloadV8(
        kind="not_applicable", reason="unsupported_view_contract", detail="fixture"),
        grade_png_sha256=hashlib.sha256(png).hexdigest())


def test_d1_every_identity_component_is_strict_cache_miss(tmp_path):
    identity, png = _identity(), _png_bytes()
    sidecar, score, grade = _sidecar(identity, png), tmp_path / "score_vs_gt.json", tmp_path / "grade.png"
    score.write_text(sidecar.model_dump_json(), encoding="utf-8"); grade.write_bytes(png)
    assert load_cached_score(score, grade_path=grade, expected_identity=identity) == sidecar
    changed = (
        identity.model_copy(update={"gt": identity.gt.model_copy(update={"file_sha256": "0" * 64})}),
        identity.model_copy(update={"gt": identity.gt.model_copy(update={"schema_version": 2})}),
        identity.model_copy(update={"capability": identity.capability.model_copy(update={"capability_key": ("changed",)})}),
        identity.model_copy(update={"tolerances": C2ToleranceIdentityV8(
            profile_kind="judge_score_config_v1",
            values=identity.tolerances.values.model_copy(update={"along_claim_tol_m": 0.31}),
            content_sha256=canonical_sha256(identity.tolerances.values.model_copy(update={"along_claim_tol_m": 0.31}).model_dump(mode="json")),
        )}),
        identity.model_copy(update={"manifest": identity.manifest.model_copy(update={"base_view_manifest_sha256": "6" * 64})}),
        identity.model_copy(update={"manifest": identity.manifest.model_copy(update={"effective_view_manifest_sha256": "7" * 64})}),
        identity.model_copy(update={"manifest": identity.manifest.model_copy(update={"completeness_overlay_sha256": None})}),
        identity.model_copy(update={"manifest": identity.manifest.model_copy(update={"score_view_bindings_sha256": None})}),
        identity.model_copy(update={"helpers": identity.helpers.model_copy(update={"va_helper": "va-2"})}),
        identity.model_copy(update={"helpers": identity.helpers.model_copy(update={"vg_helper": "vg-2"})}),
        identity.model_copy(update={"helpers": identity.helpers.model_copy(update={"claims_contract": "2"})}),
        identity.model_copy(update={"product": identity.product.model_copy(update={"output_sha256": "8" * 64})}),
        identity.model_copy(update={"product": identity.product.model_copy(update={"accepted": True, "accepted_stage_record_sha256": "9" * 64})}),
        identity.model_copy(update={"reference_applicability_sha256": "0" * 64}),
    )
    assert all(load_cached_score(score, grade_path=grade, expected_identity=item) is None for item in changed)


def test_d1_schema_zero_to_seven_are_not_v8_cache_hits(tmp_path):
    grade = tmp_path / "grade.png"; grade.write_bytes(_png_bytes())
    for schema in range(8):
        path = tmp_path / f"{schema}.json"; path.write_text(json.dumps({"schema_version": str(schema)}), encoding="utf-8")
        assert load_cached_score(path, grade_path=grade, expected_identity=_identity()) is None


def test_d2_fault_injected_second_replace_restores_complete_old_pair(tmp_path, monkeypatch):
    import src.agent.judge.score_schema as schema
    old_png, new_png = _png_bytes((1, 2, 3)), _png_bytes((4, 5, 6))
    old, new = _sidecar(_identity(), old_png), _sidecar(_identity(), new_png)
    score, grade = tmp_path / "score_vs_gt.json", tmp_path / "grade.png"
    score.write_text(old.model_dump_json(), encoding="utf-8"); grade.write_bytes(old_png)
    original_replace, tripped = schema.os.replace, {"value": False}
    def fail_sidecar_once(src, dst):
        if Path(dst) == score and not tripped["value"]:
            tripped["value"] = True; raise OSError("injected")
        return original_replace(src, dst)
    monkeypatch.setattr(schema.os, "replace", fail_sidecar_once)
    with pytest.raises(ScoreContractError, match="score_atomic_write_failed"):
        commit_score_artifacts(sidecar_path=score, grade_path=grade, sidecar=new, grade_png=new_png)
    assert score.read_bytes() == old.model_dump_json().encode("utf-8")
    assert grade.read_bytes() == old_png
    assert load_cached_score(score, grade_path=grade, expected_identity=_identity()) == old


def test_d3_typed_polygon_hatch_audit_and_unknown_target_rejection():
    import sys
    sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
    import render_grade
    from tests.b4b_contract_fixture import make_b4b_gt_document
    doc = make_b4b_gt_document()
    payload = {"kind": "c2_scored", "claim_rows": [{"target_id": "O1", "claim": "appearance",
               "result": "not_applicable", "na_reason": "reference_value_unavailable"}]}
    image, audit = render_grade.render_typed_grade(gt_document=doc, payload=payload)
    assert image.size[0] > 0 and audit["O1:appearance"].startswith("rail:")
    bad = {"kind": "c2_scored", "claim_rows": [{"target_id": "not-a-target", "claim": "host"}]}
    with pytest.raises(ScoreContractError, match="scoring.render_totality"):
        render_grade.render_typed_grade(gt_document=doc, payload=bad)


def test_d4_legacy_v2_renderer_pixel_hash_and_samples_are_locked():
    import sys
    from io import BytesIO
    sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
    import render_grade
    from tests.test_render_grade import _gt, _sidecar
    image = render_grade.render_grade("0_reading", _sidecar(), _gt())
    encoded = BytesIO(); image.save(encoded, format="PNG")
    assert hashlib.sha256(encoded.getvalue()).hexdigest() == "c44204353979bd390112b47b1d60317adb0d809a1002816126d954c8b7c36a30"
    assert image.getpixel((300, 300)) == (238, 238, 234)
    assert image.getpixel((50, 900)) == (150, 150, 145)


def test_projection_normalizer_uses_reviewed_binding_not_product_mirror_flags():
    from types import SimpleNamespace
    from src.agent.judge.score_schema import ElevationScoreViewBindingV1
    from src.agent.judge.score_service import normalize_typed_elevation_observations
    binding = ElevationScoreViewBindingV1(
        kind="elevation", input_id="elev", floor_ids=("F1",), facade_family="North",
        gt_source_view_ids=("source",), resolved_building_direction="North",
        resolution_source="manifest_building_axis", orientation_output_hash=None, adapter_version=None,
        source_footprint_fingerprint=H, world_axis="x", sign=-1, along_origin=10.0,
        mirrored=False, local_x_positive="image_left_to_right", frame_transform_sha256="b" * 64,
    )
    payload = {"elevation_observations": [{"observation_id": "o", "source_input_id": "elev", "floor_id": "F1",
                "kind": "window", "facade_family": "North", "local_x_interval": [2.0, 4.0],
                "z_interval": [1.0, 2.0], "mirrored": True, "local_x_positive": "image_right_to_left"}]}
    result = normalize_typed_elevation_observations(payload=payload, score_bindings=SimpleNamespace(bindings=(binding,)))
    assert result[0].world_along_interval == (6.0, 8.0)


def _typed_attempt_payload(gt, bindings):
    target = next(item for item in gt.openings if item.id == "O1")
    elevation = next(item for item in bindings.bindings if getattr(item, "input_id", "") == "elev-N")
    local = sorted((value - elevation.along_origin) / elevation.sign
                   for value in (target.world_along_interval.lo, target.world_along_interval.hi))
    return {
        "schema_version": "3",
        "segments": [{"id": segment.id, "floor_id": segment.floor_id, "p1": list(segment.p1),
                      "p2": list(segment.p2), "source_ids": ["plan-F1"]}
                     for floor in gt.floors for segment in floor.boundary_segments],
        "openings": [{"observation_id": "plan-O1", "floor_id": "F1", "kind": "window",
                      "facade_segment_id": target.boundary_segment_id,
                      "world_along_interval": [target.world_along_interval.lo, target.world_along_interval.hi],
                      "source_input_id": "plan-F1"}],
        "elevation_observations": [{"observation_id": "elev-O1", "source_input_id": "elev-N", "floor_id": "F1",
                      "kind": "window", "facade_family": "North", "facade_segment_id": target.boundary_segment_id,
                      "local_x_interval": local, "z_interval": [1.0, 2.0], "mirrored": True}],
    }


def test_d1_d2_d3_runstage_and_cli_share_real_v3_service_byte_for_byte(tmp_path):
    """E2E: run-stage emits v8+typed grade and CLI emits identical artifacts."""
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from tests.test_c2_b4b_phase_b import config, real_va_context
    gt, base, bindings = real_va_context(complete_plan=True, complete_elevation=True)
    run = tmp_path / "run"; attempt = run / "0_reading" / "attempts" / "001"; attempt.mkdir(parents=True)
    meta = run / "_run"; meta.mkdir()
    gt_file = tmp_path / "gt.json"; gt_file.write_text(gt.model_dump_json(), encoding="utf-8")
    (meta / "view_manifest.json").write_text(base.model_dump_json(), encoding="utf-8")
    (meta / "judge_score_bindings.json").write_text(bindings.model_dump_json(), encoding="utf-8")
    payload = _typed_attempt_payload(gt, bindings); payload_text = json.dumps(payload, sort_keys=True)
    (attempt / "output.json").write_text(payload_text, encoding="utf-8")
    artifacts = run_stage._grade_typed_attempt_artifacts("0_reading", gt.case, attempt, gt,
        gt_file=gt_file, manifest=RunManifest(case=gt.case), grade=run_stage.GradeConfig())
    sidecar = json.loads(Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar["schema_version"] == "8" and sidecar["payload"]["kind"] == "c2_scored"
    assert Path(artifacts["grade"]).read_bytes().startswith(b"\x89PNG")
    cli_out = tmp_path / "cli"
    completed = subprocess.run([
        "python", "scripts/tool_scripts/score_reading_vs_gt.py", str(attempt / "output.json"), "--case", gt.case,
        "--typed-elevation-json", str(attempt / "output.json"), "--gt-file", str(gt_file),
        "--view-manifest", str(meta / "view_manifest.json"), "--bindings", str(meta / "judge_score_bindings.json"),
        "--attempt", "1", "--out-dir", str(cli_out),
    ], check=True, capture_output=True, text=True)
    assert completed.returncode == 0
    assert (cli_out / "score_vs_gt.json").read_bytes() == (attempt / "score_vs_gt.json").read_bytes()
    assert (cli_out / "grade.png").read_bytes() == (attempt / "grade.png").read_bytes()


def _correction_v3_runstage_fixture(tmp_path):
    from src.agent._share import ensure_schema_initialized
    from src.agent.execution.view_manifest import ViewManifest
    from src.agent.judge.score_schema import (
        JudgeScoreViewBindingsV1,
        PlanScoreViewBindingV1,
        canonical_sha256,
    )
    from tests.b4b_contract_fixture import make_b4b_gt_document
    from tests.test_output_coordinate_identity import _stepwise_e4_run

    ensure_schema_initialized()
    gt = make_b4b_gt_document(observed_elevation=False)
    run = tmp_path / "run"
    run.mkdir()
    manifest, _bundle, _enrichment = _stepwise_e4_run(run)
    accepted = manifest.accepted("1_correction")
    attempt = run / "1_correction" / "attempts" / f"{accepted.accepted_attempt:03d}"
    meta = run / "_run"
    base = ViewManifest.model_validate_json(
        (meta / "view_manifest.json").read_text(encoding="utf-8")
    )
    gt_file = tmp_path / "gt.json"
    gt_file.write_text(gt.model_dump_json(), encoding="utf-8")
    binding = PlanScoreViewBindingV1(
        kind="plan", input_id="plan", floor_id="F1", gt_source_view_ids=("plan-F1",)
    )
    raw_bindings = {
        "schema_version": "1",
        "case_id": gt.case,
        "gt_content_sha256": gt.content_sha256,
        "case_metadata_sha256": base.case_metadata_sha256,
        "base_view_manifest_sha256": base.content_sha256,
        "bindings": [binding.model_dump(mode="json")],
    }
    bindings = JudgeScoreViewBindingsV1(
        schema_version="1",
        case_id=gt.case,
        gt_content_sha256=gt.content_sha256,
        case_metadata_sha256=base.case_metadata_sha256,
        base_view_manifest_sha256=base.content_sha256,
        bindings=(binding,),
        content_sha256=canonical_sha256(raw_bindings),
    )
    (meta / "judge_score_bindings.json").write_text(
        bindings.model_dump_json(), encoding="utf-8"
    )
    return gt, run, manifest, gt_file


def test_correction_v3_runstage_scoring_e2e_emits_real_grade(tmp_path):
    """B4b MINOR-1: correction is a real typed scoring producer, not just reading."""
    from scripts.tool_scripts import run_stage

    gt, run, manifest, gt_file = _correction_v3_runstage_fixture(tmp_path)
    accepted = manifest.accepted("1_correction")
    attempt = run / "1_correction" / "attempts" / f"{accepted.accepted_attempt:03d}"

    artifacts = run_stage._grade_typed_attempt_artifacts(
        "1_correction", gt.case, attempt, gt, gt_file=gt_file,
        manifest=manifest, grade=run_stage.GradeConfig(),
    )

    assert artifacts["score_vs_gt"] is not None
    assert artifacts["grade"] is not None
    sidecar = json.loads(Path(artifacts["score_vs_gt"]).read_text(encoding="utf-8"))
    assert sidecar["payload"]["kind"] == "c2_scored"
    assert sidecar["identity"]["product"]["stage"] == "correction"
    assert Path(artifacts["grade"]).read_bytes().startswith(b"\x89PNG")


def test_correction_v3_grade_loop_skips_nonaccepted_attempt_and_scores_accepted(tmp_path):
    """F-R1/P7x: base 001 is unscored; accepted enrichment 002 gets a real score."""
    from scripts.tool_scripts import run_stage

    gt, run, manifest, gt_file = _correction_v3_runstage_fixture(tmp_path)
    accepted = manifest.accepted("1_correction")
    assert accepted.accepted_attempt == 2
    assert sorted(path.name for path in (run / "1_correction" / "attempts").iterdir()) == [
        "001", "002"
    ]

    artifacts = run_stage._render_all_typed_attempt_grades(
        "1_correction",
        gt.case,
        run,
        gt,
        manifest=manifest,
        grade=run_stage.GradeConfig(),
        gt_file=gt_file,
    )

    assert artifacts[1] == {
        "score_vs_gt": None,
        "grade": None,
        "score_criteria": [],
    }
    assert artifacts[2]["score_vs_gt"] is not None
    assert artifacts[2]["grade"] is not None
    assert Path(artifacts[2]["grade"]).read_bytes().startswith(b"\x89PNG")


@pytest.mark.parametrize("run_profile", ["exploratory", "dev"])
def test_v3_gt_missing_bindings_warns_loudly_in_non_strict_profiles(tmp_path, run_profile):
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from tests.test_c2_b4b_phase_b import real_va_context

    gt, base, bindings = real_va_context()
    run = tmp_path / "run"
    attempt = run / "0_reading" / "attempts" / "001"
    attempt.mkdir(parents=True)
    meta = run / "_run"
    meta.mkdir()
    gt_file = tmp_path / "gt.json"
    gt_file.write_text(gt.model_dump_json(), encoding="utf-8")
    (meta / "view_manifest.json").write_text(base.model_dump_json(), encoding="utf-8")
    (attempt / "output.json").write_text(json.dumps(_typed_attempt_payload(gt, bindings)), encoding="utf-8")

    with pytest.warns(RuntimeWarning, match="v3 GT.*judge sidecar.*missing"):
        artifacts = run_stage._grade_typed_attempt_artifacts(
            "0_reading", gt.case, attempt, gt, gt_file=gt_file,
            manifest=RunManifest(case=gt.case), grade=run_stage.GradeConfig(),
            run_profile=run_profile,
        )

    assert artifacts == {"score_vs_gt": None, "grade": None, "score_criteria": []}


@pytest.mark.parametrize("run_profile", ["golden", "regression"])
def test_v3_gt_missing_bindings_fails_closed_in_strict_profiles(tmp_path, run_profile):
    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from tests.test_c2_b4b_phase_b import real_va_context

    gt, base, bindings = real_va_context()
    run = tmp_path / "run"
    attempt = run / "0_reading" / "attempts" / "001"
    attempt.mkdir(parents=True)
    meta = run / "_run"
    meta.mkdir()
    gt_file = tmp_path / "gt.json"
    gt_file.write_text(gt.model_dump_json(), encoding="utf-8")
    (meta / "view_manifest.json").write_text(base.model_dump_json(), encoding="utf-8")
    (attempt / "output.json").write_text(json.dumps(_typed_attempt_payload(gt, bindings)), encoding="utf-8")

    with pytest.raises(RuntimeError, match=f"run_profile={run_profile}"):
        run_stage._grade_typed_attempt_artifacts(
            "0_reading", gt.case, attempt, gt, gt_file=gt_file,
            manifest=RunManifest(case=gt.case), grade=run_stage.GradeConfig(),
            run_profile=run_profile,
        )


def test_missing_bindings_remains_silent_when_gt_is_not_v3(tmp_path, monkeypatch):
    import warnings

    from scripts.tool_scripts import run_stage
    from src.agent.execution.manifest import RunManifest
    from tests.test_c2_b4b_phase_b import real_va_context

    gt, _base, bindings = real_va_context()
    run = tmp_path / "run"
    attempt = run / "0_reading" / "attempts" / "001"
    attempt.mkdir(parents=True)
    gt_file = tmp_path / "gt.json"
    gt_file.write_text("{}", encoding="utf-8")
    (attempt / "output.json").write_text(json.dumps(_typed_attempt_payload(gt, bindings)), encoding="utf-8")
    monkeypatch.setattr(
        "src.agent.judge.score_schema.load_score_gt_identity", lambda path: (None, None)
    )

    with warnings.catch_warnings(record=True) as caught:
        artifacts = run_stage._grade_typed_attempt_artifacts(
            "0_reading", gt.case, attempt, gt, gt_file=gt_file,
            manifest=RunManifest(case=gt.case), grade=run_stage.GradeConfig(),
            run_profile="golden",
        )

    assert caught == []
    assert artifacts == {"score_vs_gt": None, "grade": None, "score_criteria": []}


def test_d2_persisted_sigkill_half_pair_is_never_a_cache_hit(tmp_path):
    """Reader-side digest check rejects the deliberate PNG-new/JSON-old state."""
    old_png, new_png = _png_bytes((1, 2, 3)), _png_bytes((4, 5, 6))
    sidecar = _sidecar(_identity(), old_png)
    score, grade = tmp_path / "score_vs_gt.json", tmp_path / "grade.png"
    score.write_text(sidecar.model_dump_json(), encoding="utf-8")
    grade.write_bytes(new_png)  # SIGKILL after PNG replace, before JSON marker.
    assert load_cached_score(score, grade_path=grade, expected_identity=_identity()) is None


def test_d5_va_c7_six_debts_are_exercised_through_public_va_and_b4b_seams():
    """VA-C7: eighth/duplicate/dangling, deletion, concave, hidden-negative, scan."""
    from src.agent.judge.opening_claim_score import (derive_product_ledger, derive_reference_ledger,
                                                      gt_openings_to_va_claims, gt_to_va_visibility)
    from src.agent.judge.score_inputs import materialize_va_elevation_bindings
    from tests.test_c2_b4b_phase_b import real_va_context
    from tests.b4b_contract_fixture import make_b4b_gt_document
    import test_c2_va_applicability as va_tests
    vm, visibility, elevation = va_tests.fixture(); good = va_tests.opening()
    with pytest.raises(Exception, match="va_claim_ledger_invalid"):
        va_tests.invoke(vm, visibility, (elevation,), (good.model_copy(update={"claims": good.claims + (good.claims[-1],)}),))
    with pytest.raises(Exception, match="va_opening_segment_invalid"):
        va_tests.invoke(vm, visibility, (elevation,), (good, good))
    with pytest.raises(Exception, match="va_opening_segment_invalid"):
        va_tests.invoke(vm, visibility, (elevation,), (good.model_copy(update={"facade_segment_id": "dangling"}),))
    rows = list(good.claims)
    rows[0] = rows[0].model_copy(update={"positive_evidence": (
        va_tests.PlanClaimEvidenceV1(source_input_id="dangling-source", world_interval=va_tests.interval()),
    )})
    with pytest.raises(Exception, match="va_claim_ledger_invalid"):
        va_tests.invoke(vm, visibility, (elevation,), (good.model_copy(update={"claims": tuple(rows)}),))
    concave = gt_to_va_visibility(make_b4b_gt_document())
    assert len(concave.floors[0].segments) > 4  # actual multi-segment concave Vg fixture
    gt, manifest, bindings = real_va_context(complete_plan=True, complete_elevation=False, negative_only_elevation=True)
    first = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    second = derive_reference_ledger(gt=gt, bindings=bindings, effective_manifest=manifest)
    declared = gt_openings_to_va_claims(gt=gt, bindings=bindings, effective_manifest=manifest)
    deleted = tuple(row.model_copy(update={"claims": tuple(claim.model_copy(update={"positive_evidence": ()})
                                                        for claim in row.claims)}) for row in declared)
    views = materialize_va_elevation_bindings(score_bindings=bindings, effective_manifest=manifest)
    product_before = derive_product_ledger(visibility=gt_to_va_visibility(gt), manifest=manifest,
                                           elevation_views=views, openings=declared)
    product_after = derive_product_ledger(visibility=gt_to_va_visibility(gt), manifest=manifest,
                                          elevation_views=views, openings=deleted)
    assert first.content_sha256 == second.content_sha256 and product_before.content_sha256 != product_after.content_sha256
    # The untrusted/hidden source cannot fabricate a negative witness row.
    assert all(item.source_input_id != "elev-N-absence"
               for opening in first.openings for claim in opening.claims for item in claim.source_evidence)


def test_d5_va_source_has_no_tautological_noop_assertion_and_d6_new_judge_modules_stay_judge_only():
    source = Path("src/agent/correction/facade_applicability.py").read_text(encoding="utf-8")
    assert "assert flip == flip" not in source and "assert result == result" not in source
    production = [*Path("src/agent/execution").glob("*.py"), *Path("src/agent/correction").glob("*.py"),
                  *Path("src/agent/reading").glob("*.py"), Path("src/agent/pipeline.py")]
    forbidden = ("score_schema", "score_config", "score_inputs", "segment_score", "opening_claim_score", "score_policy", "elevation_score", "score_service")
    assert all(not any(f"src.agent.judge.{name}" in path.read_text(encoding="utf-8") for name in forbidden)
               for path in production if path.exists())
    protected = subprocess.run(
        ["git", "diff", "--name-only", "--", "case_tests"], check=True,
        capture_output=True, text=True,
    )
    assert protected.stdout.strip() == ""
