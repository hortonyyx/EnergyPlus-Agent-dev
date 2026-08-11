"""B4b Phase A: strict wire, identity, sidecar and A0 registration."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.correction.schema import FacadeSegment, WorldInterval
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import ViewManifest
from src.agent.judge.score_config import judge_score_config_sha256, load_judge_score_config
from src.agent.judge.score_schema import (
    C2ToleranceIdentityV8, CapabilityDecisionV8, GtIdentityV8, HelperIdentityV8,
    ManifestIdentityV8, NotApplicablePayloadV8, ProductIdentityV8, ScoreIdentityV8,
    ScoreSidecarV8, build_phase_a_sidecar, canonical_sha256, compute_facade_segments_sha256,
    decide_score_capability, load_cached_score,
)

H = "a" * 64


def identity():
    config = load_judge_score_config("src/configs/judge_score.yaml")
    return ScoreIdentityV8(
        gt=GtIdentityV8(path_id="gt.json", file_sha256=H, content_sha256="b" * 64, schema_version=3,
            profile="c2_simple_orthogonal_no_holes", coordinate_frame="building_axis_world_m",
            verification_status="human_verified", loader_helper_version="gt_typed_loader_v1"),
        product=ProductIdentityV8(stage="reading", attempt=0, output_sha256="c" * 64, output_schema="3",
            accepted=False, accepted_stage_record_sha256=None, source="attempt_output"),
        manifest=ManifestIdentityV8(base_view_manifest_sha256="d" * 64, effective_view_manifest_sha256="d" * 64,
            case_metadata_sha256="e" * 64, completeness_ruleset="1", completeness_overlay_sha256=None,
            score_view_bindings_sha256=None),
        helpers=HelperIdentityV8(scorer_schema="8", segment_scorer="b4b_segment_score_v3_ic1",
            gt_to_va_adapter="b4b_gt_to_va_v1", denominator_helper="b4b_denominator_v1",
            grade_renderer="b4b_grade_png_v1", va_helper="facade_applicability_v1",
            vg_helper="facade_visibility_v1", claims_contract="1"),
        capability=CapabilityDecisionV8(path="not_applicable", capability_key=("3", "c2", "reading", "3", "1", "1", "1", "c2"),
            reason="unsupported_view_contract", gate_id="scoring.capability"),
        tolerances=C2ToleranceIdentityV8(profile_kind="judge_score_config_v1", values=config,
            content_sha256=canonical_sha256(config.model_dump(mode="json"))),
        reference_applicability_sha256=None, product_applicability_sha256=None, absence_applicability_sha256=None,
    )


def test_strict_wire_rejects_extra_missing_type_and_nonfinite():
    config = load_judge_score_config("src/configs/judge_score.yaml")
    raw = config.model_dump()
    with pytest.raises(ValidationError):
        type(config).model_validate({**raw, "extra": 1})
    with pytest.raises(ValidationError):
        type(config).model_validate({key: value for key, value in raw.items() if key != "head_claim_tol_m"})
    with pytest.raises(ValidationError):
        type(config).model_validate({**raw, "head_claim_tol_m": "0.3"})
    with pytest.raises(ValidationError):
        type(config).model_validate({**raw, "head_claim_tol_m": float("nan")})
    with pytest.raises(ValidationError):
        type(config).model_validate({**raw, "head_claim_tol_m": float("inf")})


def test_config_hash_relationships_and_a0_registration():
    config = load_judge_score_config("src/configs/judge_score.yaml")
    assert judge_score_config_sha256(config) == "ac2c14705bbfc285b489f7eeb593baf712cdc46de57a5457317103f36a3c4a06"
    assert judge_score_config_sha256(config) in Path("skills/intake_pipeline/1_correction/A0_contract.md").read_text(encoding="utf-8")
    with pytest.raises(ValidationError):
        type(config).model_validate({**config.model_dump(), "opening_assignment_tie_epsilon": 0.4})


def test_non_utf8_config_is_a_score_contract_error(tmp_path):
    from src.agent.judge.score_schema import ScoreContractError
    bad = tmp_path / "judge_score.yaml"
    bad.write_bytes(b"\xff\xfe")
    with pytest.raises(ScoreContractError) as caught:
        load_judge_score_config(bad)
    assert caught.value.code == "score_gt_identity_invalid"


def test_schema7_is_not_a_v8_cache_hit(tmp_path):
    old = tmp_path / "score_vs_gt.json"
    old.write_text(json.dumps({"scorer_schema": "7"}), encoding="utf-8")
    assert load_cached_score(old, grade_path=tmp_path / "grade.png", expected_identity=identity()) is None


def test_v8_sidecar_has_identity_and_empty_ledger_skeleton(tmp_path):
    grade = tmp_path / "grade.png"
    grade.write_bytes(b"phase-a-board")
    sidecar = build_phase_a_sidecar(identity=identity(), payload=NotApplicablePayloadV8(
        kind="not_applicable", reason="unsupported_view_contract", detail="missing reviewed bindings"),
        grade_png_sha256=hashlib.sha256(grade.read_bytes()).hexdigest())
    parsed = ScoreSidecarV8.model_validate_json(sidecar.model_dump_json())
    assert parsed.schema_version == "8"
    path = tmp_path / "score_vs_gt.json"
    path.write_text(parsed.model_dump_json(), encoding="utf-8")
    assert load_cached_score(path, grade_path=grade, expected_identity=identity()) == parsed
    grade.write_bytes(b"changed")
    assert load_cached_score(path, grade_path=grade, expected_identity=identity()) is None


def test_helper_identity_literals_are_required_without_contract_defaults():
    with pytest.raises(ValidationError):
        HelperIdentityV8(va_helper="facade_applicability_v1", vg_helper="facade_visibility_v1", claims_contract="1")


def test_legacy_scorer_schema_is_independent_of_typed_v8_contract_label():
    """The legacy (run_stage) and typed (score_schema) scorer-schema constants
    are INDEPENDENT cache keys. MAJOR-1 bumped the legacy constant from "8" to
    "9" because commit 4a11097 (F-1a/F-1b) changed legacy scoring semantics, so
    any v8 sidecar must be recomputed; the typed v3 path was untouched and stays
    "8". This lock pins both values so a future bump to either side is conscious
    (and is the lock the MAJOR-1 fix changed — the old form asserted both == "8",
    which hid the divergence this fix introduced on purpose).

    F-22 (2026-08-11) bumped the legacy constant again, "9" -> "10": the
    correction-boundary scoring SEMANTICS changed (deleted a double
    wall-thickness expansion that was double-counting post-F-17 outer-skin
    products) and the sidecar SHAPE changed (`boundary` entries gained a
    `status` field), so any v9-or-earlier sidecar must be recomputed. The
    typed v3 path is still untouched and stays "8"."""
    import scripts.tool_scripts.run_stage as run_stage
    from src.agent.judge.score_schema import SCORER_SCHEMA
    assert run_stage.SCORER_SCHEMA == "10"
    assert SCORER_SCHEMA == "8"


def test_facade_hash_is_full_sorted_a0_preimage():
    segment = FacadeSegment(id="z", floor_id="f1", facade_family="South", p1=(0.0, 0.0), p2=(2.0, 0.0),
        outward_normal=(0, -1), world_along_interval=WorldInterval(lo=0.0, hi=2.0), depth=0.0,
        visible_intervals=[WorldInterval(lo=0.0, hi=2.0)], source_footprint_fingerprint=H)
    expected = canonical_sha256([segment.model_dump(mode="json")])
    assert compute_facade_segments_sha256((segment,)) == expected
    changed = segment.model_copy(update={"id": "a"})
    assert compute_facade_segments_sha256((changed,)) != expected


def test_typed_capability_dispatch_never_downgrades_v3_to_legacy():
    gt = identity().gt
    payload = {"view_manifest_schema_version": "1", "claims_vocab_version": "1", "generator_version": "1",
        "completeness_ruleset_version": "1", "case_id": "case", "case_metadata_sha256": H, "entries": []}
    view_manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))
    reading = decide_score_capability(
        gt_identity=gt,
        stage="reading",
        product_schema="3",
        view_manifest=view_manifest,
    )
    assert reading.path == "not_applicable"
    assert reading.reason == "unsupported_reading_contract"
    assert decide_score_capability(gt_identity=gt, stage="correction", product_schema="2", view_manifest=view_manifest).path == "not_applicable"
    assert "load_gt(" not in Path("src/agent/judge/score_schema.py").read_text(encoding="utf-8")
