"""E4-output-contract spec v2 §10.4 (accepted identity / sidecar / release map)
+ the §10.6 integrated-vs-manifest coordinate-semantic parity subset."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from src.agent._share import ensure_schema_initialized
from src.agent.correction.feature_state import (
    HELPER_NORTH_AXIS_ORIENTATION_V1,
    FeatureStateClaimsV1,
    FeatureStatesArtifactV1,
    correction_stage_version,
)
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.orientation import (
    OrientationEvidenceSetV1,
    OrientationRunConfigV1,
    build_orientation_resolution_input,
    finalize_orientation_enrichment,
    verify_orientation_resolution,
)
from src.agent.correction.parse import correction_target
from src.agent.execution.manifest import RunInputs, RunManifestV2, hash_bytes, new_run_id
from src.agent.execution.stage_runner import StageRunner
from src.agent.intakeoutput import MepOutput
from src.agent.output_coordinates import (
    AssemblyE4Write,
    build_assembly_coordinate_audit,
    build_output_coordinate_snapshot,
    canonical_json_bytes,
    coordinate_semantic_projection,
    derive_output_coordinate_contract,
    load_intake_bundle,
    load_verified_accepted_correction,
    sha256_bytes,
    verify_integrated_gate1_correction,
)
from src.validator import BuildingSchema, SiteLocationSchema
from src.validator.checks.schema import CheckLayer, CheckReport

_REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _init_schema():
    ensure_schema_initialized()


# --------------------------------------------------------------------------- #
# release map lock (§10.4 first block)
# --------------------------------------------------------------------------- #
def _claims(schema, helpers, cp, pf, fs, na, phase="b2"):
    return FeatureStateClaimsV1(
        target_schema_version=schema, phase_contract=phase, helper_versions=helpers,
        cell_polygon=cp, per_floor_footprint=pf, facade_segments=fs, typed_north_axis=na,
    )


def test_release_map_three_exact_tuples():
    assert correction_stage_version(_claims(
        "3", ("floor_footprint_v1",),
        "populated", "populated", "declared_unpopulated", "declared_unpopulated")) == "2"
    assert correction_stage_version(_claims(
        "3", ("floor_footprint_v1", "facade_visibility_v1"),
        "populated", "populated", "populated", "declared_unpopulated")) == "3"
    assert correction_stage_version(_claims(
        "3", ("floor_footprint_v1", "facade_visibility_v1", HELPER_NORTH_AXIS_ORIENTATION_V1),
        "populated", "populated", "populated", "populated",
        phase="e4_orientation")) == "4"


def test_release_map_wrong_order_is_invariant():
    with pytest.raises(ValueError, match="INVARIANT"):
        correction_stage_version(_claims(
            "3", (HELPER_NORTH_AXIS_ORIENTATION_V1, "floor_footprint_v1", "facade_visibility_v1"),
            "populated", "populated", "populated", "populated", phase="e4_orientation"))


def test_release_map_missing_helper_is_invariant():
    with pytest.raises(ValueError, match="INVARIANT"):
        correction_stage_version(_claims(
            "3", ("floor_footprint_v1", HELPER_NORTH_AXIS_ORIENTATION_V1),
            "populated", "populated", "populated", "populated", phase="e4_orientation"))


def test_release_map_phase_mismatch_is_invariant():
    with pytest.raises(ValueError, match="phase_contract"):
        correction_stage_version(_claims(
            "3", ("floor_footprint_v1", "facade_visibility_v1", HELPER_NORTH_AXIS_ORIENTATION_V1),
            "populated", "populated", "populated", "populated", phase="b2"))


def test_release_map_unpopulated_north_with_e4_tuple_is_invariant():
    with pytest.raises(ValueError, match="INVARIANT|populated"):
        correction_stage_version(_claims(
            "3", ("floor_footprint_v1", "facade_visibility_v1", HELPER_NORTH_AXIS_ORIENTATION_V1),
            "populated", "populated", "populated", "declared_unpopulated",
            phase="e4_orientation"))


def test_release_map_unknown_combination_is_invariant():
    with pytest.raises(ValueError, match="INVARIANT"):
        correction_stage_version(_claims(
            "3", ("some_future_helper_v9",),
            "populated", "populated", "populated", "populated"))


def test_no_stage_version_four_literal_outside_release_map():
    """The wire value \"4\" for the correction release may exist as a literal
    ONLY in the central release map (feature_state.py). `stage_runner.py` and
    `orientation.py` must derive it."""
    pattern = re.compile(r'["\']4["\']')
    for rel in ("src/agent/execution/stage_runner.py", "src/agent/correction/orientation.py"):
        text = (_REPO / rel).read_text(encoding="utf-8")
        assert not pattern.search(text), f"bare '4' literal found in {rel}"


# --------------------------------------------------------------------------- #
# stepwise accepted-identity fixture
# --------------------------------------------------------------------------- #
def _v3_finalized():
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
            payload, vector_dir=Path(td), target=correction_target("orthogonal_polygon"))


def _clean_report(stage="1_correction"):
    rep = CheckReport(stage=stage, capability_profile="orthogonal_polygon")
    rep.add_pass("x", CheckLayer.INVARIANT)
    return rep


def _mep_model():
    return MepOutput(
        building=BuildingSchema(name="T"),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
        material_specs="m", construction_specs="c", schedule_specs="s",
        hvac_specs="h", people_specs="p", lights_specs="l",
    )


def _stepwise_e4_run(run_dir: Path):
    """Build a complete stepwise E4 run: accepted Vg correction attempt →
    accepted orientation-enrichment attempt (release \"4\") → accepted
    assembly_e4_v1 S5 attempt. Returns (manifest, contract, intake)."""
    from src.agent.geometry import build_geometry
    from src.agent.geometry.specs import serialize_geometry
    from src.agent.output_coordinates import assemble_intake_artifacts

    manifest = RunManifestV2(
        case=run_dir.name, run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256="f" * 64),
    )
    runner = StageRunner(run_dir, manifest)

    finalized = _v3_finalized()
    runner.record(
        stage="1_correction", stage_dir=run_dir / "1_correction",
        output_obj=finalized, report=_clean_report(),
    )

    base = load_verified_accepted_correction(run_dir=run_dir, manifest=manifest)
    resolution_input, evidence_bytes = build_orientation_resolution_input(
        base_correction_sha256=base.ref.output_sha256,
        evidence_set=OrientationEvidenceSetV1(), completion_mode="prior_fill",
    )
    resolution_bytes = resolution_input.model_dump_json(indent=2).encode("utf-8")
    run_config_bytes = OrientationRunConfigV1(
        completion_mode="prior_fill").model_dump_json(indent=2).encode("utf-8")
    # evidence set is a content-addressed artifact under 1_correction/
    es_dir = run_dir / "1_correction" / "orientation_evidence_sets"
    es_dir.mkdir(parents=True, exist_ok=True)
    (es_dir / f"{sha256_bytes(evidence_bytes)}.json").write_bytes(evidence_bytes)
    resolution = verify_orientation_resolution(
        raw_resolution_input_bytes=resolution_bytes,
        raw_evidence_set_bytes=evidence_bytes,
        raw_run_config_bytes=run_config_bytes,
    )
    enrichment = finalize_orientation_enrichment(base, resolution)
    runner.record(
        stage="1_correction", stage_dir=run_dir / "1_correction",
        output_obj=enrichment, report=_clean_report(),
        input_hashes={
            "base_correction": base.ref.output_sha256,
            "orientation_evidence_set": sha256_bytes(evidence_bytes),
            "orientation_resolution": sha256_bytes(resolution_bytes),
            "run_config": sha256_bytes(run_config_bytes),
        },
        stage_version="9",  # deliberately wrong: the writer must derive "4"
    )

    verified = load_verified_accepted_correction(run_dir=run_dir, manifest=manifest)
    bg = build_geometry(enrichment.geom, capability_profile="orthogonal_polygon")
    zone_specs, surface_specs, fen_specs, _used = serialize_geometry(
        bg, frame_label="building_axis")
    snapshot = build_output_coordinate_snapshot(bg)
    bundle = assemble_intake_artifacts(
        zone_specs=zone_specs, surface_specs=surface_specs,
        fenestration_specs=fen_specs, mep=_mep_model(),
        correction=verified, coordinate_snapshot=snapshot,
    )
    audit = build_assembly_coordinate_audit(
        verified=verified, contract=bundle.output_coordinates,
        snapshot_bytes=canonical_json_bytes(snapshot),
        mep_placeholder_north_axis=0.0,
        final_building_north_axis=bundle.intake.building.north_axis,
    )
    runner.record(
        stage="5_intakeoutput", stage_dir=run_dir / "5_intakeoutput",
        output_obj=AssemblyE4Write(
            intake=bundle.intake, contract=bundle.output_coordinates,
            snapshot=snapshot, audit=audit,
        ),
        report=_clean_report("5_intakeoutput"),
        input_hashes={
            "1_correction": verified.ref.output_sha256,
            "4_mep": "0" * 64,
            "geometry_specs": hash_bytes(zone_specs.encode("utf-8")),
        },
    )
    manifest.save(run_dir)
    # root convenience copy of the final intake (what the CLI points at)
    (run_dir / "5_intakeoutput" / "intake_output.json").write_text(
        bundle.intake.model_dump_json(indent=2), encoding="utf-8")
    return manifest, bundle, enrichment


@pytest.mark.xfail(strict=True, reason="B5 Phase C 令 build_geometry v3 强制 VerifiedWindowHostProof (spec §8.1)；E4 stepwise→build→loader→assembly 的 proof 接线在 Phase D 落地 (gate B5-D3 e4-rebind + MINOR-2 pipeline/check_kernel proof)。Phase D 须重写本测试以构造/传 proof，届时 strict xfail 会 XPASS 提醒清除标记。")
def test_stepwise_enrichment_and_assembly_identity(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, bundle, _enrichment = _stepwise_e4_run(run_dir)

    corr = manifest.accepted("1_correction")
    assert corr.artifact_contract == "correction_e4_orientation_v1"
    assert corr.stage_version == "4"  # derived, not the caller's bogus "9"
    assert set(corr.artifact_hashes) == {"output", "checks", "audit", "feature_states"}
    assert set(corr.input_hashes) == {
        "base_correction", "orientation_evidence_set", "orientation_resolution", "run_config",
    }

    s5 = manifest.accepted("5_intakeoutput")
    assert s5.artifact_contract == "assembly_e4_v1"
    assert set(s5.artifact_hashes) == {
        "output", "checks", "audit", "output_coordinate_contract", "output_coordinate_snapshot",
    }
    assert s5.artifact_hashes["output"] == s5.output_hash

    # every artifact hash matches the on-disk attempt bytes
    attempt = run_dir / "5_intakeoutput" / "attempts" / f"{s5.accepted_attempt:03d}"
    for key, filename in (
        ("output", "output.json"), ("checks", "checks.json"), ("audit", "audit.json"),
        ("output_coordinate_contract", "output_coordinate_contract.json"),
        ("output_coordinate_snapshot", "output_coordinate_snapshot.json"),
    ):
        assert s5.artifact_hashes[key] == hash_bytes((attempt / filename).read_bytes())


@pytest.mark.xfail(strict=True, reason="B5 Phase C 令 build_geometry v3 强制 VerifiedWindowHostProof (spec §8.1)；E4 stepwise→build→loader→assembly 的 proof 接线在 Phase D 落地 (gate B5-D3 e4-rebind + MINOR-2 pipeline/check_kernel proof)。Phase D 须重写本测试以构造/传 proof，届时 strict xfail 会 XPASS 提醒清除标记。")
def test_loader_reads_accepted_attempt_and_round_trips(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, bundle, _ = _stepwise_e4_run(run_dir)
    loaded = load_intake_bundle(
        run_dir / "5_intakeoutput" / "intake_output.json", run_dir=run_dir)
    assert loaded.output_coordinates.mode == "relative_north_axis"
    assert loaded.output_coordinates.north_axis_deg == 0.0
    assert loaded.output_coordinates == bundle.output_coordinates
    assert loaded.coordinate_snapshot == bundle.coordinate_snapshot
    assert loaded.intake.building.north_axis == 0.0


@pytest.mark.xfail(strict=True, reason="B5 Phase C 令 build_geometry v3 强制 VerifiedWindowHostProof (spec §8.1)；E4 stepwise→build→loader→assembly 的 proof 接线在 Phase D 落地 (gate B5-D3 e4-rebind + MINOR-2 pipeline/check_kernel proof)。Phase D 须重写本测试以构造/传 proof，届时 strict xfail 会 XPASS 提醒清除标记。")
def test_loader_ignores_blocked_later_attempt(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, bundle, enrichment = _stepwise_e4_run(run_dir)
    accepted_before = manifest.accepted("5_intakeoutput").accepted_attempt

    # a later BLOCKED S5 attempt (bad report, accept=False) must not move the pointer
    snapshot = bundle.coordinate_snapshot
    audit = build_assembly_coordinate_audit(
        verified=load_verified_accepted_correction(run_dir=run_dir, manifest=manifest),
        contract=bundle.output_coordinates,
        snapshot_bytes=canonical_json_bytes(snapshot),
        mep_placeholder_north_axis=0.0, final_building_north_axis=0.0,
    )
    StageRunner(run_dir, manifest).record(
        stage="5_intakeoutput", stage_dir=run_dir / "5_intakeoutput",
        output_obj=AssemblyE4Write(
            intake=bundle.intake, contract=bundle.output_coordinates,
            snapshot=snapshot, audit=audit),
        report=_clean_report("5_intakeoutput"), accept=False,
    )
    manifest.save(run_dir)
    assert manifest.accepted("5_intakeoutput").accepted_attempt == accepted_before
    loaded = load_intake_bundle(
        run_dir / "5_intakeoutput" / "intake_output.json", run_dir=run_dir)
    assert loaded.output_coordinates == bundle.output_coordinates


@pytest.mark.xfail(strict=True, reason="B5 Phase C 令 build_geometry v3 强制 VerifiedWindowHostProof (spec §8.1)；E4 stepwise→build→loader→assembly 的 proof 接线在 Phase D 落地 (gate B5-D3 e4-rebind + MINOR-2 pipeline/check_kernel proof)。Phase D 须重写本测试以构造/传 proof，届时 strict xfail 会 XPASS 提醒清除标记。")
def test_tampered_contract_sidecar_breaks_the_chain(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, bundle, _ = _stepwise_e4_run(run_dir)
    s5 = manifest.accepted("5_intakeoutput")
    attempt = run_dir / "5_intakeoutput" / "attempts" / f"{s5.accepted_attempt:03d}"
    sidecar = attempt / "output_coordinate_contract.json"
    sidecar.write_text(sidecar.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_intake_bundle(run_dir / "5_intakeoutput" / "intake_output.json", run_dir=run_dir)


@pytest.mark.xfail(strict=True, reason="B5 Phase C 令 build_geometry v3 强制 VerifiedWindowHostProof (spec §8.1)；E4 stepwise→build→loader→assembly 的 proof 接线在 Phase D 落地 (gate B5-D3 e4-rebind + MINOR-2 pipeline/check_kernel proof)。Phase D 须重写本测试以构造/传 proof，届时 strict xfail 会 XPASS 提醒清除标记。")
def test_tampered_correction_output_breaks_the_chain(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, _, _ = _stepwise_e4_run(run_dir)
    corr = manifest.accepted("1_correction")
    output = run_dir / "1_correction" / "attempts" / f"{corr.accepted_attempt:03d}" / "output.json"
    output.write_text(output.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        load_verified_accepted_correction(run_dir=run_dir, manifest=manifest)


def test_v3_run_without_e4_sidecar_refuses_legacy(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest = RunManifestV2(
        case="run", run_id=new_run_id(),
        run_inputs=RunInputs(view_manifest_sha256="f" * 64))
    runner = StageRunner(run_dir, manifest)
    finalized = _v3_finalized()
    runner.record(stage="1_correction", stage_dir=run_dir / "1_correction",
                  output_obj=finalized, report=_clean_report())
    # a pre-E4-style S5 record (plain dict output => base_v2)
    intake_dict = {"note": "not a real intake"}
    runner.record(stage="5_intakeoutput", stage_dir=run_dir / "5_intakeoutput",
                  output_obj=intake_dict, report=_clean_report("5_intakeoutput"))
    manifest.save(run_dir)
    intake_path = run_dir / "5_intakeoutput" / "intake_output.json"
    from src.agent.state import IntakeOutput

    intake_path.write_text(IntakeOutput(
        building=BuildingSchema(name="B"),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
        zone_specs="z", material_specs="m", schedule_specs="s", construction_specs="c",
        surface_specs="su", fenestration_specs="f", hvac_specs="h",
        people_specs="p", lights_specs="l",
    ).model_dump_json(indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="assembly_e4_v1"):
        load_intake_bundle(intake_path, run_dir=run_dir)


def test_pure_historical_file_gets_legacy_contract(tmp_path):
    from src.agent.state import IntakeOutput

    intake_path = tmp_path / "intake_output.json"
    intake_path.write_text(IntakeOutput(
        building=BuildingSchema(name="B"),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
        zone_specs="z", material_specs="m", schedule_specs="s", construction_specs="c",
        surface_specs="su", fenestration_specs="f", hvac_specs="h",
        people_specs="p", lights_specs="l",
    ).model_dump_json(indent=2), encoding="utf-8")
    bundle = load_intake_bundle(intake_path)
    assert bundle.output_coordinates.mode == "world_legacy"
    assert bundle.output_coordinates.source.binding_kind == "legacy_standalone_intake"
    assert bundle.output_coordinates.source.intake_output_sha256 == sha256_bytes(
        intake_path.read_bytes())
    assert bundle.coordinate_snapshot is None


def test_partial_sidecar_pair_is_never_valid(tmp_path):
    from src.agent.state import IntakeOutput

    intake_path = tmp_path / "intake_output.json"
    intake_path.write_text(IntakeOutput(
        building=BuildingSchema(name="B"),
        site_location=SiteLocationSchema(
            name="S", latitude=22.5, longitude=114.0, time_zone=8.0, elevation=5.0),
        zone_specs="z", material_specs="m", schedule_specs="s", construction_specs="c",
        surface_specs="su", fenestration_specs="f", hvac_specs="h",
        people_specs="p", lights_specs="l",
    ).model_dump_json(indent=2), encoding="utf-8")
    (tmp_path / "output_coordinate_contract.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="partial sidecar"):
        load_intake_bundle(intake_path)


# --------------------------------------------------------------------------- #
# §10.6 subset — integrated vs manifest coordinate-semantic parity
# --------------------------------------------------------------------------- #
@pytest.mark.xfail(strict=True, reason="B5 Phase C 令 build_geometry v3 强制 VerifiedWindowHostProof (spec §8.1)；E4 stepwise→build→loader→assembly 的 proof 接线在 Phase D 落地 (gate B5-D3 e4-rebind + MINOR-2 pipeline/check_kernel proof)。Phase D 须重写本测试以构造/传 proof，届时 strict xfail 会 XPASS 提醒清除标记。")
def test_integrated_and_manifest_refs_project_identically(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest, bundle, enrichment = _stepwise_e4_run(run_dir)
    manifest_verified = load_verified_accepted_correction(run_dir=run_dir, manifest=manifest)

    raw = enrichment.geom.model_dump_json(indent=2).encode("utf-8")
    fs = FeatureStatesArtifactV1(
        output_sha256=sha256_bytes(raw), claims=enrichment.feature_state_claims)
    integrated_verified = verify_integrated_gate1_correction(
        raw_output_bytes=raw, correction_report=_clean_report(), feature_states=fs)

    snap_hash = bundle.output_coordinates.geometry_snapshot_sha256
    manifest_contract = derive_output_coordinate_contract(
        manifest_verified, geometry_snapshot_sha256=snap_hash)
    integrated_contract = derive_output_coordinate_contract(
        integrated_verified, geometry_snapshot_sha256=snap_hash)

    # identity envelopes legitimately differ...
    assert manifest_contract.source.acceptance == "manifest"
    assert integrated_contract.source.acceptance == "integrated_gate1"
    assert manifest_contract.source.run_id is not None
    # ...but the coordinate semantics must be field-for-field identical
    assert coordinate_semantic_projection(manifest_contract) == \
        coordinate_semantic_projection(integrated_contract)
