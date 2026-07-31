"""B4b Phase A score binding and completeness ownership probes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry, ViewManifest
from src.agent.judge.score_inputs import (
    build_effective_view_manifest, build_reading_score_manifest,
    frame_transform_preimage, frame_transform_sha256,
    frame_transform_sha256_from_preimage, load_completeness_overlay, materialize_va_elevation_bindings,
    resolve_dataset_declaration, validate_score_view_bindings,
    validate_score_view_bindings_against_gt,
)
from src.agent.judge.score_schema import (
    DatasetCompletenessDeclarationV1, DatasetDeclarationBodyV1, ElevationFullFacadeCoverageV1,
    ElevationScoreViewBindingV1, JudgeCompletenessOverlayV1, JudgeScoreViewBindingsV1,
    PlanFullFloorCoverageV1, PlanScoreViewBindingV1,
    ReadingFilteredComponentBasisV1, ScoreContractError, UserCompletenessDeclarationV1,
    UserDeclarationBodyV1, canonical_sha256,
)

H = "a" * 64
FRAME_VECTORS = {
    (False, "image_left_to_right"): "db2e25cf576ef104bb7cd39afc89026857f9860aba42bbdf2c6c52057e88dade",
    (True, "image_left_to_right"): "b2d733bed5cabbc2acdcaccfebeb177b79100425af8ad6a7a9608b436a20e970",
    (False, "image_right_to_left"): "741f28f3fa20a9231c71ea8ae0403f0e629bf7839aa67bc5d9234406021684c5",
    (True, "image_right_to_left"): "88c1c19d22be6d95750ae737bd26312f92733598d183ebc5f44a43331af81daf",
}


def entry(input_id, kind, *, semantics="building_axis"):
    return RequiredViewEntry(input_id=input_id, source_image=f"case_data/{input_id}.png", image_sha256=H,
        view_type=kind, floor_ref=1 if kind == "plan" else None,
        declared_direction_token="South" if kind == "elevation" else None,
        direction_source="standard_assumption", direction_semantics=semantics, semantics_source="case_metadata",
        azimuth_deg=90.0 if semantics == "true_azimuth" else None,
        building_view_direction="South" if kind == "elevation" and semantics == "building_axis" else None,
        dimensioned=True, expected_output_id=input_id,
        opening_evidence=OpeningEvidence(potentially_observable_claims=["existence", "host", "along", "width"] if kind == "plan" else ["existence", "along", "width", "sill", "head", "appearance"]))


def manifest(*entries):
    payload = {"view_manifest_schema_version": "1", "claims_vocab_version": "1", "generator_version": "1",
        "completeness_ruleset_version": "1", "case_id": "case", "case_metadata_sha256": H,
        "entries": [item.model_dump(mode="json") for item in sorted(entries, key=lambda item: item.input_id)]}
    return ViewManifest(**payload, content_sha256=hash_obj(payload))


def elevation_binding(*, semantics="manifest_building_axis", mirrored=False, local="image_left_to_right"):
    sign = -1 if mirrored ^ (local == "image_right_to_left") else 1
    raw = dict(kind="elevation", input_id="south", floor_ids=("f1",), facade_family="South", gt_source_view_ids=("gt-e",),
        resolved_building_direction="South", resolution_source=semantics,
        orientation_output_hash=None if semantics == "manifest_building_axis" else "b" * 64,
        adapter_version=None if semantics == "manifest_building_axis" else "resolver_v1", source_footprint_fingerprint=H,
        world_axis="x", sign=sign, along_origin=0.0, mirrored=mirrored, local_x_positive=local,
        frame_transform_sha256=FRAME_VECTORS[(mirrored, local)])
    return ElevationScoreViewBindingV1(**raw)


def bindings(base, elevation=None):
    elevation = elevation or elevation_binding()
    rows = (PlanScoreViewBindingV1(kind="plan", input_id="plan", floor_id="f1", gt_source_view_ids=("gt-p",)), elevation)
    raw = {"schema_version": "1", "case_id": "case", "gt_content_sha256": "b" * 64,
        "case_metadata_sha256": H, "base_view_manifest_sha256": base.content_sha256,
        "bindings": [item.model_dump(mode="json") for item in rows]}
    return JudgeScoreViewBindingsV1(schema_version="1", case_id="case", gt_content_sha256="b" * 64,
        case_metadata_sha256=H, base_view_manifest_sha256=base.content_sha256, bindings=rows,
        content_sha256=canonical_sha256(raw))


def user_declaration():
    body = UserDeclarationBodyV1(input_id="plan", assertion_id="user-1", negative_claims=("existence", "along"),
        coverage=PlanFullFloorCoverageV1(kind="full_floor", floor_id="f1"), asserted_by="reviewer", assertion_revision=1)
    return UserCompletenessDeclarationV1(source="user", body=body, body_sha256=canonical_sha256(body.model_dump(mode="json")))


def overlay(base, declaration):
    raw = {"schema_version": "1", "case_id": "case", "gt_content_sha256": "b" * 64,
        "base_view_manifest_sha256": base.content_sha256, "declarations": [declaration.model_dump(mode="json")]}
    return JudgeCompletenessOverlayV1(schema_version="1", case_id="case", gt_content_sha256="b" * 64,
        base_view_manifest_sha256=base.content_sha256, declarations=(declaration,), content_sha256=canonical_sha256(raw))


def test_standard_true_unknown_direction_and_product_cannot_drive_frame():
    standard = manifest(entry("plan", "plan"), entry("south", "elevation"))
    validate_score_view_bindings(bindings=bindings(standard), base=standard)
    true = manifest(entry("plan", "plan"), entry("south", "elevation", semantics="true_azimuth"))
    validate_score_view_bindings(bindings=bindings(true, elevation_binding(semantics="resolved_direction_sidecar")), base=true)
    unknown = manifest(entry("plan", "plan"), entry("south", "elevation", semantics="unknown"))
    validate_score_view_bindings(bindings=bindings(unknown, elevation_binding(semantics="resolved_direction_sidecar")), base=unknown)
    with pytest.raises(ScoreContractError):
        validate_score_view_bindings(bindings=bindings(true), base=true)
    assert "product" not in Path("src/agent/judge/score_inputs.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("mirrored,local", [(False, "image_left_to_right"), (True, "image_left_to_right"), (False, "image_right_to_left"), (True, "image_right_to_left")])
def test_frame_preimage_all_sign_mirror_localx_states(mirrored, local):
    binding = elevation_binding(mirrored=mirrored, local=local)
    assert binding.frame_transform_sha256 == FRAME_VECTORS[(mirrored, local)]
    assert frame_transform_sha256(binding) == FRAME_VECTORS[(mirrored, local)]
    assert FRAME_VECTORS[(mirrored, local)] in Path("skills/intake_pipeline/1_correction/A0_contract.md").read_text(encoding="utf-8")
    preimage = frame_transform_preimage(binding)
    for key in preimage:
        with pytest.raises(ScoreContractError):
            frame_transform_sha256_from_preimage({name: value for name, value in preimage.items() if name != key})
    with pytest.raises(ScoreContractError):
        frame_transform_sha256_from_preimage({**preimage, "extra": 1})


def test_effective_manifest_is_pure_and_base_conflict_or_idempotence_is_explicit():
    base = manifest(entry("plan", "plan"), entry("south", "elevation"))
    effective = build_effective_view_manifest(base=base, overlay=overlay(base, user_declaration()))
    assert effective.content_sha256 != base.content_sha256
    assert base.entry_by_input_id("plan").opening_evidence.completeness_assertion is None
    idempotent = build_effective_view_manifest(base=effective, overlay=overlay(effective, user_declaration()))
    assert idempotent == effective
    body = user_declaration().body.model_copy(update={"assertion_id": "other"})
    altered = UserCompletenessDeclarationV1(source="user", body=body,
        body_sha256=canonical_sha256(body.model_dump(mode="json")))
    with pytest.raises(ScoreContractError):
        build_effective_view_manifest(base=effective, overlay=overlay(effective, altered))


def test_user_and_dataset_builder_paths_and_overlay_loader(tmp_path):
    script = Path("scripts/tool_scripts/build_judge_score_inputs.py")
    user = tmp_path / "candidate" / "user.json"
    dataset = tmp_path / "candidate" / "dataset.json"
    common = [sys.executable, str(script), "--input-id", "plan", "--assertion-id", "a", "--negative-claim", "existence",
        "--coverage-kind", "full_floor", "--floor-id", "f1"]
    subprocess.run(common + ["--output", str(user), "--source", "user", "--asserted-by", "r", "--assertion-revision", "1"], check=True)
    subprocess.run(common + ["--output", str(dataset), "--source", "dataset_ref", "--dataset-id", "d", "--dataset-version", "1", "--contract-id", "c"], check=True)
    assert json.loads(user.read_text())["body_sha256"]
    assert json.loads(dataset.read_text())["body_sha256"]
    registry = tmp_path / "registry" / "d" / "1"
    registry.mkdir(parents=True)
    registry_entry = registry / "entry.json"
    registry_entry.write_text(dataset.read_text(), encoding="utf-8")
    resolved = DatasetCompletenessDeclarationV1.model_validate_json(dataset.read_text())
    assert resolve_dataset_declaration(declaration=resolved, registry_root=tmp_path / "registry") == registry_entry
    base = manifest(entry("plan", "plan"), entry("south", "elevation"))
    declaration = UserCompletenessDeclarationV1.model_validate_json(user.read_text())
    document = overlay(base, declaration)
    path = tmp_path / "overlay.json"
    path.write_text(document.model_dump_json(), encoding="utf-8")
    assert load_completeness_overlay(path, expected_case_id="case", expected_gt_content_sha256="b" * 64,
        expected_base_view_manifest_sha256=base.content_sha256) == document


def test_va_bindings_use_effective_manifest_identity():
    base = manifest(entry("plan", "plan"), entry("south", "elevation"))
    effective = build_effective_view_manifest(base=base, overlay=overlay(base, user_declaration()))
    va = materialize_va_elevation_bindings(score_bindings=bindings(base), effective_manifest=effective)
    assert va[0].view_manifest_sha256 == effective.content_sha256


def test_reading_trusted_filter_removes_positive_and_negative_va_evidence():
    from src.agent.judge.opening_claim_score import (
        derive_reference_ledger,
        gt_openings_to_va_claims,
    )
    from tests.test_c2_b4b_phase_b import real_va_context

    gt, base, reviewed = real_va_context(
        complete_plan=True,
        complete_elevation=True,
    )
    exclusion = ReadingFilteredComponentBasisV1(
        source_input_id="elev-N",
        component="elevation_opening_xy",
        floor_ids=("F1", "F2"),
        cause_class="trusted_input",
        reasons=("trusted_elevation_capability_unavailable",),
    )
    score_manifest = build_reading_score_manifest(
        effective=base,
        trusted_capability_dispositions=(exclusion,),
    )
    claims = gt_openings_to_va_claims(
        gt=gt,
        bindings=reviewed,
        effective_manifest=score_manifest,
    )
    filtered_claims = {"existence", "along", "width"}
    assert any(
        evidence.source_input_id == "elev-N"
        for opening in claims
        for claim in opening.claims
        if claim.claim == "sill"
        for evidence in claim.positive_evidence
    )
    assert not any(
        evidence.source_input_id == "elev-N"
        for opening in claims
        for claim in opening.claims
        if claim.claim in filtered_claims
        for evidence in claim.positive_evidence
    )
    ledger = derive_reference_ledger(
        gt=gt,
        bindings=reviewed,
        effective_manifest=score_manifest,
    )
    assert not any(
        decision.source_input_id == "elev-N"
        for opening in ledger.openings
        for claim in opening.claims
        if claim.claim in filtered_claims
        for decision in claim.source_evidence
    )


def test_gt_binding_cross_validation_checks_floor_facade_and_actual_source_refs():
    from test_gt_schema import _opening_payload
    from src.agent.judge.gt_schema import GroundTruthV3

    gt = GroundTruthV3.model_validate(_opening_payload(observed=True))
    base = manifest(entry("plan", "plan"), entry("south", "elevation"))
    proto = ElevationScoreViewBindingV1(kind="elevation", input_id="south", floor_ids=("F1",),
        facade_family="South", gt_source_view_ids=("elev-S",), resolved_building_direction="South",
        resolution_source="manifest_building_axis", orientation_output_hash=None, adapter_version=None,
        source_footprint_fingerprint=gt.floors[0].footprint_fingerprint, world_axis="x", sign=1,
        along_origin=0.0, mirrored=False, local_x_positive="image_left_to_right", frame_transform_sha256="0" * 64)
    elevation = proto.model_copy(update={"frame_transform_sha256": frame_transform_sha256(proto)})
    rows = (PlanScoreViewBindingV1(kind="plan", input_id="plan", floor_id="F1", gt_source_view_ids=("plan-F1",)), elevation)
    raw = {"schema_version": "1", "case_id": "case", "gt_content_sha256": gt.content_sha256,
        "case_metadata_sha256": H, "base_view_manifest_sha256": base.content_sha256,
        "bindings": [row.model_dump(mode="json") for row in rows]}
    reviewed = JudgeScoreViewBindingsV1(schema_version="1", case_id="case", gt_content_sha256=gt.content_sha256,
        case_metadata_sha256=H, base_view_manifest_sha256=base.content_sha256, bindings=rows,
        content_sha256=canonical_sha256(raw))
    validate_score_view_bindings_against_gt(bindings=reviewed, base=base, gt=gt)
    bad = rows[0].model_copy(update={"gt_source_view_ids": ("elev-S",)})
    raw["bindings"][0] = bad.model_dump(mode="json")
    invalid = JudgeScoreViewBindingsV1(schema_version="1", case_id="case", gt_content_sha256=gt.content_sha256,
        case_metadata_sha256=H, base_view_manifest_sha256=base.content_sha256, bindings=(bad, elevation),
        content_sha256=canonical_sha256(raw))
    with pytest.raises(ScoreContractError):
        validate_score_view_bindings_against_gt(bindings=invalid, base=base, gt=gt)
