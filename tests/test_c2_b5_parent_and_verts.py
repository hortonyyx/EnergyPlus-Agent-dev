"""B5 Phase-C gates: directed line geometry, parent binding and four-way sync."""
from __future__ import annotations

import hashlib
import inspect
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.geometry_validator import check_window_host_resolution
from src.agent.correction.parse import correction_target
from src.agent.correction.schema import (
    CorrectedGeometry,
    CorrectedGeometryV3,
    FacadeSegment,
    WorldInterval,
)
from src.agent.correction.window_host import (
    WindowEvidenceLedgerV1,
    WindowHostClaimsV1,
    WindowHostResolutionV1,
    WindowHostsArtifactV1,
)
from src.agent.correction.window_sources import (
    build_verified_window_resolver_inputs,
    canonical_sha256,
    derive_manifest_direction_facts,
    serialize_window_resolver_inputs_artifact,
    source_locator,
)
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import (
    OpeningEvidence,
    RequiredViewEntry,
    ViewManifest,
)
from src.agent.geometry.build import (
    _issue_verified_window_host_proof,
    build_geometry,
)
from src.agent.geometry.modelling import (
    BuildingGeometry,
    NameRegistry,
    SegmentLine2D,
    Surface,
    Window,
    WindowParentBindingError,
    _newell,
    attach_windows_v3,
    window_verts_on_line,
)
from src.agent.geometry.specs import (
    building_geometry_dict,
    building_geometry_json,
    check_geometry_specs_consistency,
    geometry_specs_markdown,
    serialize_geometry,
)
from src.agent.judge.opening_claim_score import (
    bind_correction_window_segment,
    resolve_correction_window_host,
)
from src.agent.judge.score_schema import (
    GtIdentityV8,
    JudgeScoreViewBindingsV1,
    PlanScoreViewBindingV1,
    ProductIdentityV8,
    ScoreContractError,
    canonical_sha256,
    decide_score_capability,
)
from src.agent.judge.score_config import load_judge_score_config
from src.agent.judge.score_service import score_typed_attempt
from src.validator.checks.kernel import _window_parent_binding, check_kernel
from src.validator.checks.schema import CheckReport


H = "a" * 64
RING = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]
SOUTH_SEGMENT_ID = "f1:facade:c7548828ff8ea141abc4467ff1c4c3e20b54949eb08b3690b1218675986efe76"
SOUTH_RESOLUTION_SHA256 = "2e3e3683c5493c6c4939053489b100689bd1812478aa1869fcf1d7a28d72e2cb"


def _manifest(*, include_elevation: bool = False) -> tuple[ViewManifest, bytes]:
    entry = RequiredViewEntry(
        input_id="plan",
        source_image="case_data/plan.png",
        image_sha256=H,
        view_type="plan",
        floor_ref=1,
        declared_direction_token=None,
        direction_source="standard_assumption",
        direction_semantics="building_axis",
        semantics_source="case_metadata",
        building_view_direction=None,
        dimensioned=True,
        expected_output_id="plan",
        opening_evidence=OpeningEvidence(
            potentially_observable_claims=["existence", "host", "along", "width"],
        ),
    )
    entries = [entry]
    if include_elevation:
        entries.append(RequiredViewEntry(
            input_id="south",
            source_image="case_data/south.png",
            image_sha256=H,
            view_type="elevation",
            floor_ref=None,
            declared_direction_token="South",
            direction_source="standard_assumption",
            direction_semantics="building_axis",
            semantics_source="case_metadata",
            building_view_direction="South",
            dimensioned=True,
            expected_output_id="south",
            opening_evidence=OpeningEvidence(
                potentially_observable_claims=[
                    "existence", "along", "width", "sill", "head", "appearance",
                ],
            ),
        ))
    payload = {
        "view_manifest_schema_version": "1",
        "claims_vocab_version": "1",
        "generator_version": "1",
        "completeness_ruleset_version": "1",
        "case_id": "phase-c",
        "case_metadata_sha256": H,
        "entries": [row.model_dump(mode="json") for row in entries],
    }
    manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))
    return manifest, manifest.model_dump_json().encode("utf-8")


def _plan_geometry(facade: str) -> dict[str, list[float]]:
    return {
        "South": {"x_range": [1.0, 3.0], "y_range": [0.0, 0.1]},
        "North": {"x_range": [1.0, 3.0], "y_range": [3.9, 4.0]},
        "East": {"x_range": [3.9, 4.0], "y_range": [1.0, 3.0]},
        "West": {"x_range": [0.0, 0.1], "y_range": [1.0, 3.0]},
    }[facade]


def _bundle(
    tmp_path: Path,
    *,
    facade: str = "South",
    include_window: bool = True,
    include_elevation: bool = False,
):
    manifest, raw_manifest = _manifest(include_elevation=include_elevation)
    reading = json.dumps(
        {
            "image_kind": "plan",
            "strokes": [{
                "id": "W-01",
                "pen": "window",
                "geometry": _plan_geometry(facade),
            }],
            "uncaptured": [],
        },
        separators=(",", ":"),
    ).encode("utf-8")
    locator = source_locator(
        input_id="plan",
        observation_id="W-01",
        output_sha256=hashlib.sha256(reading).hexdigest(),
    )
    geom = CorrectedGeometryV3.model_validate({
        "schema_version": "3",
        "footprint_x": [0.0, 4.0],
        "footprint_y": [0.0, 4.0],
        "floors": [{
            "id": "f1",
            "name": "F1",
            "z_floor": 0.0,
            "ceiling_height": 3.0,
            "footprint": {"vertices": RING},
            "cells": [{
                "id": "r1",
                "x": [0.0, 4.0],
                "y": [0.0, 4.0],
                "polygon": RING,
            }],
        }],
        "windows": ([{
            "id": "w1",
            "floor": "F1",
            "floor_id": "f1",
            "facade": facade,
            "span": [1.0, 3.0],
            "z": [1.0, 2.0],
            "room": "r1",
            "provenance": {"existence": {
                "provenance": "observed",
                "source_ids": [locator],
            }},
        }] if include_window else []),
        "facade_segments": [],
    })
    readings = {"plan": reading}
    if include_elevation:
        readings["south"] = json.dumps({
            "image_kind": "elevation",
            "strokes": [],
            "uncaptured": [],
            "facade": {
                "mirrored": False,
                "local_x_positive": "image_left_to_right",
            },
        }, separators=(",", ":")).encode("utf-8")
    facts = derive_manifest_direction_facts(
        raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=readings,
    )
    verified = build_verified_window_resolver_inputs(
        producer_draw=geom,
        raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=readings,
        elevation_direction_facts=facts,
    )
    result = finalize_correction_draw(
        geom,
        vector_dir=tmp_path,
        target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    artifact_payload = {
        "artifact_version": "window_hosts_v1",
        "output_sha256": result.prepared_candidate_identity.output_sha256,
        "claims": result.window_host_claims.model_dump(mode="json"),
        "evidence": result.window_evidence_ledger.model_dump(mode="json"),
    }
    artifact = WindowHostsArtifactV1(
        artifact_version="window_hosts_v1",
        output_sha256=artifact_payload["output_sha256"],
        claims=result.window_host_claims,
        evidence=result.window_evidence_ledger,
        content_sha256=canonical_sha256(artifact_payload),
    )
    proof = _issue_verified_window_host_proof(
        raw_resolver_inputs_bytes=serialize_window_resolver_inputs_artifact(verified),
        raw_window_hosts_bytes=artifact.model_dump_json(indent=2).encode("utf-8"),
        raw_output_bytes=result.prepared_candidate_identity.output_bytes,
    )
    bg = build_geometry(
        result.geom,
        capability_profile="orthogonal_polygon",
        window_host_proof=proof,
    )
    return SimpleNamespace(
        result=result,
        verified=verified,
        artifact=artifact,
        proof=proof,
        bg=bg,
        manifest=manifest,
    )


def _attach(bundle, surfaces: list[Surface]):
    return attach_windows_v3(
        bundle.result.geom,
        surfaces,
        {volume.cell_id: volume for volume in bundle.bg.zone_volumes},
        NameRegistry(),
        host_claims=bundle.result.window_host_claims,
        tolerances=load_core_tolerances(),
    )


def _parent(bundle) -> Surface:
    name = bundle.bg.windows[0].parent
    return next(surface for surface in bundle.bg.surfaces if surface.name == name)


def _resigned_claims(bundle, mutate) -> WindowHostClaimsV1:
    claims = bundle.result.window_host_claims.model_dump(mode="json")
    row = claims["resolutions"][0]
    mutate(row)
    unhashed = dict(row)
    unhashed.pop("resolution_sha256")
    row["resolution_sha256"] = canonical_sha256(unhashed)
    claims["aggregate_sha256"] = canonical_sha256([row["resolution_sha256"]])
    return WindowHostClaimsV1.model_validate_json(json.dumps(claims))


def _window_parent_gate(bg: BuildingGeometry, proof):
    report = CheckReport(stage="2_modelling", capability_profile="orthogonal_polygon")
    _window_parent_binding(report, bg, proof)
    assert len(report.results) == 1
    return report.results[0]


def _official_gt_identity() -> GtIdentityV8:
    return GtIdentityV8(
        path_id="gt.json",
        file_sha256=H,
        content_sha256="b" * 64,
        schema_version=3,
        profile="c2_simple_orthogonal_no_holes",
        coordinate_frame="building_axis_world_m",
        verification_status="human_verified",
        loader_helper_version="gt_typed_loader_v1",
    )


def _official_product_identity(bundle, *, output_sha256: str) -> ProductIdentityV8:
    return ProductIdentityV8(
        stage="correction",
        attempt=1,
        output_sha256=output_sha256,
        output_schema="3",
        accepted=True,
        accepted_stage_record_sha256="c" * 64,
        source="accepted_attempt",
        artifact_contract="correction_b5_v1",
    )


# B5-C2 / LINE-1, LINE-2, LINE-3, LINE-4
def test_line_1_directed_parameter_and_endpoints_are_literal():
    line = SegmentLine2D((0.0, 0.0), (4.0, 0.0))
    assert line.parameter_of((1.0, 0.0)) == 0.25
    assert line.parameter_of((3.0, 0.0)) == 0.75
    assert line.point_at(0.25) == (1.0, 0.0)
    assert line.point_at(0.75) == (3.0, 0.0)


def test_line_2_negative_x_record_preserves_p1_to_p2_order(tmp_path: Path):
    row = _bundle(tmp_path, facade="North").result.window_host_claims.resolutions[0]
    assert (row.segment_p1.x, row.segment_p1.y) == (4.0, 4.0)
    assert (row.segment_p2.x, row.segment_p2.y) == (0.0, 4.0)
    assert (row.segment_parameter_interval.lo, row.segment_parameter_interval.hi) == (0.25, 0.75)
    assert tuple((point.x, point.y) for point in row.clamped_plan_endpoints_p1_to_p2) == (
        (3.0, 4.0), (1.0, 4.0),
    )


def test_line_3_negative_y_record_preserves_p1_to_p2_order(tmp_path: Path):
    row = _bundle(tmp_path, facade="West").result.window_host_claims.resolutions[0]
    assert (row.segment_p1.x, row.segment_p1.y) == (0.0, 4.0)
    assert (row.segment_p2.x, row.segment_p2.y) == (0.0, 0.0)
    assert (row.segment_parameter_interval.lo, row.segment_parameter_interval.hi) == (0.25, 0.75)
    assert tuple((point.x, point.y) for point in row.clamped_plan_endpoints_p1_to_p2) == (
        (0.0, 3.0), (0.0, 1.0),
    )


def test_line_4_diagonal_helper_has_hand_written_vertices_and_normal():
    verts = window_verts_on_line(
        host_line=SegmentLine2D((0.0, 0.0), (3.0, 4.0)),
        parameter_interval=(0.2, 0.6),
        z_interval=(1.0, 2.0),
        outward_normal_xy=(0.8, -0.6),
    )
    assert [tuple(round(value, 12) for value in vertex) for vertex in verts] == [
        (0.6, 0.8, 1.0),
        (1.8, 2.4, 1.0),
        (1.8, 2.4, 2.0),
        (0.6, 0.8, 2.0),
    ]
    assert tuple(round(float(value), 12) for value in _newell(verts)) == (0.8, -0.6, 0.0)


# LINE-5 and LINE-6 are separate safety locks.
def test_line_5_diagonal_facade_segment_remains_out_of_c2():
    with pytest.raises(ValidationError, match="axis-aligned"):
        FacadeSegment(
            id="diag",
            floor_id="f1",
            facade_family="North",
            p1=(0.0, 0.0),
            p2=(3.0, 4.0),
            outward_normal=(0, 1),
            world_along_interval=WorldInterval(lo=0.0, hi=3.0),
            depth=0.0,
            visible_intervals=[],
            source_footprint_fingerprint=H,
        )


def test_line_6_zero_length_line_rejected():
    with pytest.raises(ValueError, match="positive length"):
        SegmentLine2D((1.0, 1.0), (1.0, 1.0))


def test_line_6_reverse_parameter_interval_rejected():
    with pytest.raises(ValueError, match="t0 < t1"):
        window_verts_on_line(
            host_line=SegmentLine2D((0.0, 0.0), (4.0, 0.0)),
            parameter_interval=(0.75, 0.25),
            z_interval=(1.0, 2.0),
            outward_normal_xy=(0.0, -1.0),
        )


def test_line_6_out_of_bounds_parameter_interval_rejected():
    with pytest.raises(ValueError, match="0 <= t0"):
        window_verts_on_line(
            host_line=SegmentLine2D((0.0, 0.0), (4.0, 0.0)),
            parameter_interval=(-0.01, 0.75),
            z_interval=(1.0, 2.0),
            outward_normal_xy=(0.0, -1.0),
        )


def test_line_6_parameter_interval_above_one_rejected():
    with pytest.raises(ValueError, match="t1 <= 1"):
        window_verts_on_line(
            host_line=SegmentLine2D((0.0, 0.0), (4.0, 0.0)),
            parameter_interval=(0.25, 1.01),
            z_interval=(1.0, 2.0),
            outward_normal_xy=(0.0, -1.0),
        )


# B5-C3 / LINE-7: world-sorted endpoint tamper is rejected by both audit and proof boundaries.
def test_line_7_negative_axis_world_sorted_endpoint_tamper_is_rejected(tmp_path: Path):
    bundle = _bundle(tmp_path, facade="North")
    tampered = _resigned_claims(
        bundle,
        lambda row: row.update({
            "clamped_plan_endpoints_p1_to_p2": [
                {"x": 1.0, "y": 4.0}, {"x": 3.0, "y": 4.0},
            ],
        }),
    )
    finding = check_window_host_resolution(
        bundle.result.geom,
        proof=tampered,
        evidence=bundle.result.window_evidence_ledger,
    )
    assert not finding.ok
    assert any(row["reason"] == "line_geometry" for row in finding.evidence["offenders"])

    payload = {
        "artifact_version": "window_hosts_v1",
        "output_sha256": bundle.artifact.output_sha256,
        "claims": tampered.model_dump(mode="json"),
        "evidence": bundle.result.window_evidence_ledger.model_dump(mode="json"),
    }
    tampered_artifact = WindowHostsArtifactV1(
        artifact_version="window_hosts_v1",
        output_sha256=bundle.artifact.output_sha256,
        claims=tampered,
        evidence=bundle.result.window_evidence_ledger,
        content_sha256=canonical_sha256(payload),
    )
    with pytest.raises(ValueError, match="claims disagree"):
        _issue_verified_window_host_proof(
            raw_resolver_inputs_bytes=serialize_window_resolver_inputs_artifact(
                bundle.verified
            ),
            raw_window_hosts_bytes=tampered_artifact.model_dump_json(indent=2).encode("utf-8"),
            raw_output_bytes=bundle.result.prepared_candidate_identity.output_bytes,
        )


# LINE-8 wire locks are deliberately independent.
def _wire_payload(bundle) -> dict:
    return bundle.result.window_host_claims.resolutions[0].model_dump(mode="json")


def test_line_8_non_unit_wire_normal_rejected(tmp_path: Path):
    payload = _wire_payload(_bundle(tmp_path))
    payload["segment_outward_normal"] = [1, 1]
    with pytest.raises(ValidationError, match="cardinal unit vector"):
        WindowHostResolutionV1.model_validate_json(json.dumps(payload))


def test_line_8_zero_wire_normal_rejected(tmp_path: Path):
    payload = _wire_payload(_bundle(tmp_path))
    payload["segment_outward_normal"] = [0, 0]
    with pytest.raises(ValidationError, match="cardinal unit vector"):
        WindowHostResolutionV1.model_validate_json(json.dumps(payload))


def test_line_8_plan_record_with_visible_overlap_rejected(tmp_path: Path):
    payload = _wire_payload(_bundle(tmp_path))
    payload["visible_overlap_intervals"] = [{"lo": 1.0, "hi": 2.0}]
    with pytest.raises(ValidationError, match="plan branch"):
        WindowHostResolutionV1.model_validate_json(json.dumps(payload))


def test_line_8_elevation_record_without_visible_overlap_rejected(tmp_path: Path):
    payload = _wire_payload(_bundle(tmp_path))
    payload["branch"] = "elevation"
    with pytest.raises(ValidationError, match="requires visible overlap"):
        WindowHostResolutionV1.model_validate_json(json.dumps(payload))


# B5-C1 / PARENT-1..5
def test_parent_1_same_normal_decoy_plane_does_not_steal_parent(tmp_path: Path):
    bundle = _bundle(tmp_path)
    parent = _parent(bundle)
    decoy = Surface(
        "decoy",
        parent.zone,
        "Wall",
        [(0.0, 4.0, 3.0), (4.0, 4.0, 3.0), (4.0, 4.0, 0.0), (0.0, 4.0, 0.0)],
        "Outdoors",
    )
    attached = _attach(bundle, [*bundle.bg.surfaces, decoy])
    assert len(attached) == 1
    assert attached[0].parent == parent.name


def test_proof_aware_build_requires_and_accepts_empty_v3_totality(tmp_path: Path):
    bundle = _bundle(tmp_path, include_window=False)
    assert bundle.bg.geometry_contract == "c2_b5_v1"
    assert bundle.bg.windows == []
    with pytest.raises(ValueError, match="requires VerifiedWindowHostProof"):
        build_geometry(
            bundle.result.geom,
            capability_profile="orthogonal_polygon",
        )


def test_parent_2_zero_parent_blocks_build_and_kernel(tmp_path: Path, monkeypatch):
    bundle = _bundle(tmp_path)
    parent = _parent(bundle)
    import src.agent.geometry.build as build_module

    original = build_module.pair_surfaces

    def without_parent(*args, **kwargs):
        return [surface for surface in original(*args, **kwargs) if surface.name != parent.name]

    monkeypatch.setattr(build_module, "pair_surfaces", without_parent)
    with pytest.raises(WindowParentBindingError) as exc:
        build_module.build_geometry(
            bundle.result.geom,
            capability_profile="orthogonal_polygon",
            window_host_proof=bundle.proof,
        )
    assert exc.value.code == "parent_wall_zero_candidates"

    broken = deepcopy(bundle.bg)
    broken.surfaces = [surface for surface in broken.surfaces if surface.name != parent.name]
    report = check_kernel(
        broken,
        window_host_proof=bundle.proof,
        capability_profile="orthogonal_polygon",
        interzone_issues=[],
    )
    gate = next(row for row in report.results if row.check_id == "kernel.window_parent_binding")
    assert gate.status.value == "fail"


def test_parent_3_two_complete_parents_block_multiple(tmp_path: Path):
    bundle = _bundle(tmp_path)
    duplicate = deepcopy(_parent(bundle))
    duplicate.name = "duplicate_parent"
    with pytest.raises(WindowParentBindingError) as exc:
        _attach(bundle, [*bundle.bg.surfaces, duplicate])
    assert exc.value.code == "parent_wall_multiple_candidates"


def test_parent_4_fragmented_half_span_parents_do_not_split_window(tmp_path: Path):
    bundle = _bundle(tmp_path)
    parent = _parent(bundle)
    fragments = [
        Surface(
            "half_a", parent.zone, "Wall",
            [(0.0, 0.0, 3.0), (2.0, 0.0, 3.0), (2.0, 0.0, 0.0), (0.0, 0.0, 0.0)],
            "Outdoors",
        ),
        Surface(
            "half_b", parent.zone, "Wall",
            [(2.0, 0.0, 3.0), (4.0, 0.0, 3.0), (4.0, 0.0, 0.0), (2.0, 0.0, 0.0)],
            "Outdoors",
        ),
    ]
    surfaces = [surface for surface in bundle.bg.surfaces if surface.name != parent.name]
    with pytest.raises(WindowParentBindingError) as exc:
        _attach(bundle, [*surfaces, *fragments])
    assert exc.value.code == "parent_wall_zero_candidates"


def test_parent_5_reverse_normal_parent_blocks(tmp_path: Path):
    bundle = _bundle(tmp_path)
    parent = _parent(bundle)
    reversed_parent = deepcopy(parent)
    reversed_parent.verts = list(reversed(reversed_parent.verts))
    surfaces = [
        reversed_parent if surface.name == parent.name else surface
        for surface in bundle.bg.surfaces
    ]
    with pytest.raises(WindowParentBindingError) as exc:
        _attach(bundle, surfaces)
    assert exc.value.code == "parent_wall_zero_candidates"


# B5-C4 / correction, kernel, built JSON and specs synchronisation.
def test_sync_1_output_built_json_and_specs_share_all_window_identity(tmp_path: Path):
    bundle = _bundle(tmp_path)
    row = building_geometry_dict(bundle.bg, geometry_contract="c2_b5_v1")["windows"][0]
    resolution = bundle.result.window_host_claims.resolutions[0]
    assert resolution.facade_segment_id == SOUTH_SEGMENT_ID
    assert resolution.resolution_sha256 == SOUTH_RESOLUTION_SHA256
    assert row == {
        "name": "Z01_W1_Win1",
        "parent": "Z01_W1",
        "verts": [[1.0, 0.0, 1.0], [3.0, 0.0, 1.0], [3.0, 0.0, 2.0], [1.0, 0.0, 2.0]],
        "source_window": "w1",
        "facade_segment": SOUTH_SEGMENT_ID,
        "host_resolution_sha256": SOUTH_RESOLUTION_SHA256,
    }
    zone, surface, fenestration, _used = serialize_geometry(
        bundle.bg,
        geometry_contract="c2_b5_v1",
    )
    assert "source_window=w1" in fenestration
    assert f"segment={SOUTH_SEGMENT_ID}" in fenestration
    assert f"host_proof={SOUTH_RESOLUTION_SHA256}" in fenestration
    specs = geometry_specs_markdown(
        zone,
        surface,
        fenestration,
        geometry_contract="c2_b5_v1",
    )
    check_geometry_specs_consistency(
        bundle.bg,
        building_geometry=building_geometry_dict(bundle.bg, geometry_contract="c2_b5_v1"),
        geometry_specs=specs,
        geometry_contract="c2_b5_v1",
    )


def test_sync_2_spec_parent_tamper_is_blocked(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = building_geometry_dict(bundle.bg, geometry_contract="c2_b5_v1")
    payload["windows"][0]["parent"] = "forged_parent"
    zone, surface, fenestration, _used = serialize_geometry(bundle.bg, geometry_contract="c2_b5_v1")
    specs = geometry_specs_markdown(zone, surface, fenestration, geometry_contract="c2_b5_v1")
    with pytest.raises(ValueError, match="building_geometry"):
        check_geometry_specs_consistency(
            bundle.bg,
            building_geometry=payload,
            geometry_specs=specs,
            geometry_contract="c2_b5_v1",
        )


def test_sync_2_spec_vertex_tamper_is_blocked(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = building_geometry_dict(bundle.bg, geometry_contract="c2_b5_v1")
    payload["windows"][0]["verts"][0][0] = 9.0
    zone, surface, fenestration, _used = serialize_geometry(bundle.bg, geometry_contract="c2_b5_v1")
    specs = geometry_specs_markdown(zone, surface, fenestration, geometry_contract="c2_b5_v1")
    with pytest.raises(ValueError, match="building_geometry"):
        check_geometry_specs_consistency(
            bundle.bg,
            building_geometry=payload,
            geometry_specs=specs,
            geometry_contract="c2_b5_v1",
        )


def test_correction_validator_fresh_recompute_passes_and_missing_proof_blocks(tmp_path: Path):
    bundle = _bundle(tmp_path)
    passed = check_window_host_resolution(
        bundle.result.geom,
        proof=bundle.proof,
        evidence=bundle.result.window_evidence_ledger,
    )
    missing = check_window_host_resolution(
        bundle.result.geom,
        proof=None,
        evidence=bundle.result.window_evidence_ledger,
    )
    assert passed.ok
    assert not missing.ok


# MAJOR-1: every promotion rejection is locked at its owning boundary.
def test_kernel_b5_contract_without_proof_fails_closed():
    gate = _window_parent_gate(
        BuildingGeometry(geometry_contract="c2_b5_v1"),
        None,
    )
    assert gate.status.value == "fail"
    assert gate.message == "B5 built geometry requires host proof"


def test_kernel_legacy_contract_with_b5_proof_fails_closed(tmp_path: Path):
    bundle = _bundle(tmp_path)
    gate = _window_parent_gate(BuildingGeometry(), bundle.proof)
    assert gate.status.value == "fail"
    assert gate.message == "legacy built geometry must not carry B5 proof"


def test_kernel_unknown_geometry_contract_fails_closed():
    bg = BuildingGeometry()
    bg.geometry_contract = "future_contract"
    gate = _window_parent_gate(bg, None)
    assert gate.status.value == "fail"
    assert gate.message == "unknown building geometry contract"


def test_kernel_invalid_b5_artifact_bytes_fail_closed(tmp_path: Path):
    bundle = _bundle(tmp_path)
    corrupt_proof = deepcopy(bundle.proof)
    object.__setattr__(corrupt_proof, "raw_window_hosts_bytes", b"not-json")
    gate = _window_parent_gate(bundle.bg, corrupt_proof)
    assert gate.status.value == "fail"
    assert gate.message == "B5 proof artifact is invalid"
    assert "Invalid JSON" in gate.evidence["reason"]


def test_kernel_unsupported_b5_proof_type_fails_closed():
    gate = _window_parent_gate(
        BuildingGeometry(geometry_contract="c2_b5_v1"),
        object(),
    )
    assert gate.status.value == "fail"
    assert gate.message == "unsupported B5 proof type"


def test_correction_validator_blocks_window_host_conflict_row(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = bundle.result.geom.model_dump(mode="json")
    payload["conflicts"] = [{
        "kind": "window_host_conflict",
        "window_id": "w1",
        "reason_code": "multiple_segment_candidates",
    }]
    conflicted = CorrectedGeometryV3.model_validate(payload)
    finding = check_window_host_resolution(
        conflicted,
        proof=bundle.proof,
        evidence=bundle.result.window_evidence_ledger,
    )
    assert not finding.ok
    assert finding.message == "v3 geometry contains blocking window-host conflicts"
    assert finding.evidence["conflicts"] == payload["conflicts"]


def test_correction_validator_rejects_wrong_evidence_wire_type(tmp_path: Path):
    bundle = _bundle(tmp_path)
    finding = check_window_host_resolution(
        bundle.result.geom,
        proof=bundle.proof,
        evidence=bundle.result.window_evidence_ledger.model_dump(mode="json"),
    )
    assert not finding.ok
    assert finding.message == "window evidence has the wrong wire type"


def test_correction_validator_rejects_evidence_different_from_proof_artifact(tmp_path: Path):
    bundle = _bundle(tmp_path)
    evidence_payload = bundle.result.window_evidence_ledger.model_dump(mode="json")
    evidence_payload["va_ledger_content_sha256"] = "0" * 64
    evidence_payload["content_sha256"] = canonical_sha256({
        key: value
        for key, value in evidence_payload.items()
        if key != "content_sha256"
    })
    different_evidence = WindowEvidenceLedgerV1.model_validate_json(
        json.dumps(evidence_payload)
    )
    finding = check_window_host_resolution(
        bundle.result.geom,
        proof=bundle.proof,
        evidence=different_evidence,
    )
    assert not finding.ok
    assert finding.message == "window evidence differs from verified proof artifact"


def test_kernel_fresh_recompute_rejects_built_vertex_tamper(tmp_path: Path):
    bundle = _bundle(tmp_path)
    broken = deepcopy(bundle.bg)
    broken.windows[0].verts[0] = (9.0, 9.0, 9.0)
    report = check_kernel(
        broken,
        window_host_proof=bundle.proof,
        capability_profile="orthogonal_polygon",
        interzone_issues=[],
    )
    gate = next(row for row in report.results if row.check_id == "kernel.window_parent_binding")
    assert gate.status.value == "fail"
    assert any(item["reason"] == "built_vertices" for item in gate.evidence["offenders"])


def test_build_rejects_runtime_geom_mutated_after_proof_issue(tmp_path: Path):
    bundle = _bundle(tmp_path)
    mutated = bundle.result.geom.model_copy(deep=True)
    mutated.windows[0].span = [1.25, 3.0]
    with pytest.raises(ValueError, match="mutated after verified output"):
        build_geometry(
            mutated,
            capability_profile="orthogonal_polygon",
            window_host_proof=bundle.proof,
        )


# MAJOR-2: serializer, build and proof-artifact identity rejection locks.
def test_serializer_rejects_contract_different_from_built_geometry():
    bg = BuildingGeometry(geometry_contract="c2_b5_v1")
    with pytest.raises(
        ValueError,
        match="serializer geometry_contract must match the built geometry contract",
    ):
        building_geometry_dict(bg, geometry_contract="legacy")


def test_building_geometry_dict_rejects_b5_window_without_three_identities():
    bg = BuildingGeometry(
        windows=[Window(
            name="W1",
            parent="S1",
            verts=[
                (1.0, 0.0, 1.0),
                (3.0, 0.0, 1.0),
                (3.0, 0.0, 2.0),
                (1.0, 0.0, 2.0),
            ],
        )],
        geometry_contract="c2_b5_v1",
    )
    with pytest.raises(
        ValueError,
        match="c2_b5_v1 windows require source/segment/host proof identity",
    ):
        building_geometry_dict(bg)


def test_serialize_geometry_rejects_b5_window_without_three_identities():
    bg = BuildingGeometry(
        windows=[Window(
            name="W1",
            parent="S1",
            verts=[
                (1.0, 0.0, 1.0),
                (3.0, 0.0, 1.0),
                (3.0, 0.0, 2.0),
                (1.0, 0.0, 2.0),
            ],
        )],
        geometry_contract="c2_b5_v1",
    )
    with pytest.raises(
        ValueError,
        match="c2_b5_v1 fenestration specs require proof identity",
    ):
        serialize_geometry(bg)


def test_build_geometry_rejects_legacy_input_with_b5_proof(tmp_path: Path):
    bundle = _bundle(tmp_path)
    legacy = CorrectedGeometry(
        schema_version="1",
        footprint_x=[0.0, 4.0],
        footprint_y=[0.0, 4.0],
        floors=[],
    )
    with pytest.raises(
        ValueError,
        match="legacy build must not receive B5 window host proof",
    ):
        build_geometry(legacy, window_host_proof=bundle.proof)


def test_window_hosts_artifact_rejects_output_identity_mismatch(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = bundle.artifact.model_dump(mode="json")
    payload["output_sha256"] = "0" * 64
    payload["content_sha256"] = canonical_sha256({
        key: value for key, value in payload.items() if key != "content_sha256"
    })
    with pytest.raises(
        ValidationError,
        match="window-host artifact output identity mismatch",
    ):
        WindowHostsArtifactV1.model_validate_json(json.dumps(payload))


def test_window_hosts_artifact_rejects_claim_evidence_window_id_mismatch(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = bundle.artifact.model_dump(mode="json")
    evidence = payload["evidence"]
    decision = evidence["decisions"][0]
    decision["window_id"] = "w-other"
    decision["evidence_sha256"] = canonical_sha256({
        key: value for key, value in decision.items() if key != "evidence_sha256"
    })
    evidence["aggregate_sha256"] = canonical_sha256([
        row["evidence_sha256"] for row in evidence["decisions"]
    ])
    evidence["content_sha256"] = canonical_sha256({
        key: value for key, value in evidence.items() if key != "content_sha256"
    })
    payload["content_sha256"] = canonical_sha256({
        key: value for key, value in payload.items() if key != "content_sha256"
    })
    with pytest.raises(
        ValidationError,
        match="host claims and evidence window ids must be exactly equal",
    ):
        WindowHostsArtifactV1.model_validate_json(json.dumps(payload))


def test_window_hosts_artifact_rejects_claim_evidence_identity_hash_mismatch(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = bundle.artifact.model_dump(mode="json")
    evidence = payload["evidence"]
    evidence["facade_segments_sha256"] = "0" * 64
    evidence["content_sha256"] = canonical_sha256({
        key: value for key, value in evidence.items() if key != "content_sha256"
    })
    payload["content_sha256"] = canonical_sha256({
        key: value for key, value in payload.items() if key != "content_sha256"
    })
    with pytest.raises(
        ValidationError,
        match="host claims and evidence identities disagree",
    ):
        WindowHostsArtifactV1.model_validate_json(json.dumps(payload))


def test_attach_windows_v3_rejects_source_resolution_totality_mismatch(tmp_path: Path):
    bundle = _bundle(tmp_path)
    claims_payload = bundle.result.window_host_claims.model_dump(mode="json")
    claims_payload["resolutions"] = []
    claims_payload["aggregate_sha256"] = canonical_sha256([])
    incomplete_claims = WindowHostClaimsV1.model_validate_json(
        json.dumps(claims_payload)
    )
    with pytest.raises(WindowParentBindingError) as exc:
        attach_windows_v3(
            bundle.result.geom,
            bundle.bg.surfaces,
            {volume.cell_id: volume for volume in bundle.bg.zone_volumes},
            NameRegistry(),
            host_claims=incomplete_claims,
            tolerances=load_core_tolerances(),
        )
    assert exc.value.code == "resolver_output_tampered"
    assert exc.value.context == {
        "source_window_ids": ["w1"],
        "resolution_ids": [],
    }


def test_legacy_version_gate_preserves_frozen_building_json_bytes():
    legacy = BuildingGeometry()
    expected = b'{\n  "zones": [],\n  "zone_meta": [],\n  "surfaces": [],\n  "windows": []\n}'
    assert building_geometry_json(legacy, geometry_contract="legacy").encode("utf-8") == expected
    assert "geometry_contract" not in building_geometry_dict(legacy, geometry_contract="legacy")
    zone, surface, fenestration, _used = serialize_geometry(
        legacy,
        geometry_contract="legacy",
    )
    expected_specs = (
        "# zone_specs\n\n"
        "Zones (world coordinates, meters, two decimals). Every zone name below is referenced literally by "
        "surface_specs / fenestration_specs / people_specs / lights_specs / hvac_specs.\n\n"
        "# surface_specs\n\n"
        "Surfaces (vertices CCW from outside, absolute world coordinates in meters). Construction names and "
        "adjacent zone names are authoritative — transcribe them verbatim. Interzone faces are pre-paired: the "
        "named adjacent surface is its reciprocal partner.\n\n"
        "# fenestration_specs\n\n"
        "This model has NO windows. The geometry contains zero fenestration surfaces. Do NOT create any "
        "FenestrationSurface:Detailed objects and do NOT invent windows on any facade.\n"
    ).encode("utf-8")
    assert geometry_specs_markdown(
        zone,
        surface,
        fenestration,
        geometry_contract="legacy",
    ).encode("utf-8") == expected_specs


# JUDGE-1/2/3: proof is a gate, but the score relation remains judge-only.
def test_judge_1_tampered_output_relation_fails_proof_before_scoring(tmp_path: Path):
    bundle = _bundle(tmp_path)
    output = bundle.result.geom.model_dump(mode="json")
    output["windows"][0]["room"] = "forged-room"
    tampered_bytes = CorrectedGeometryV3.model_validate(output).model_dump_json(indent=2).encode("utf-8")
    with pytest.raises(ValueError):
        _issue_verified_window_host_proof(
            raw_resolver_inputs_bytes=serialize_window_resolver_inputs_artifact(
                bundle.verified
            ),
            raw_window_hosts_bytes=bundle.artifact.model_dump_json(indent=2).encode("utf-8"),
            raw_output_bytes=tampered_bytes,
        )


def test_judge_2_official_binding_rejects_missing_explicit_segment_ref(tmp_path: Path):
    bundle = _bundle(tmp_path)
    window = bundle.result.geom.windows[0].model_copy(update={"facade_segment_id": None})
    with pytest.raises(ScoreContractError, match="score_product_segment_unresolved"):
        bind_correction_window_segment(
            window=window,
            segments=bundle.result.geom.facade_segments,
            allow_temporary_binding=False,
        )
    official_source = inspect.getsource(score_typed_attempt)
    assert "allow_temporary_binding=False" in official_source


def test_judge_3_pre_b5_correction_is_machine_na_but_official_b5_dispatches(tmp_path: Path):
    bundle = _bundle(tmp_path)
    gt_identity = GtIdentityV8(
        path_id="gt.json",
        file_sha256=H,
        content_sha256="b" * 64,
        schema_version=3,
        profile="c2_simple_orthogonal_no_holes",
        coordinate_frame="building_axis_world_m",
        verification_status="human_verified",
        loader_helper_version="gt_typed_loader_v1",
    )
    pre_b5 = decide_score_capability(
        gt_identity=gt_identity,
        stage="correction",
        product_schema="3",
        view_manifest=bundle.manifest,
    )
    official = decide_score_capability(
        gt_identity=gt_identity,
        stage="correction",
        product_schema="3",
        view_manifest=bundle.manifest,
        product_artifact_contract="correction_b5_v1",
    )
    assert (pre_b5.path, pre_b5.reason) == ("not_applicable", "unsupported_product_contract")
    assert official.path == "c2_v3"
    assert "correction_b5_v1" in official.capability_key


def test_judge_official_score_service_requires_verified_artifact_input(tmp_path: Path):
    bundle = _bundle(tmp_path)
    gt_identity = GtIdentityV8(
        path_id="gt.json",
        file_sha256=H,
        content_sha256="b" * 64,
        schema_version=3,
        profile="c2_simple_orthogonal_no_holes",
        coordinate_frame="building_axis_world_m",
        verification_status="human_verified",
        loader_helper_version="gt_typed_loader_v1",
    )
    product_identity = ProductIdentityV8(
        stage="correction",
        attempt=1,
        output_sha256=bundle.result.prepared_candidate_identity.output_sha256,
        output_schema="3",
        accepted=True,
        accepted_stage_record_sha256="c" * 64,
        source="accepted_attempt",
        artifact_contract="correction_b5_v1",
    )
    with pytest.raises(ScoreContractError) as exc:
        score_typed_attempt(
            gt_identity=gt_identity,
            gt=SimpleNamespace(floors=()),
            stage="correction",
            product_payload=bundle.result.geom.model_dump(mode="json"),
            product_identity=product_identity,
            base_view_manifest=bundle.manifest,
            score_bindings=SimpleNamespace(content_sha256="d" * 64),
            completeness_overlay=None,
            c2_config=load_judge_score_config("src/configs/judge_score.yaml"),
            window_host_proof=None,
        )
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.context == {
        "reason": "official_b5_requires_verified_six_artifact_input",
    }


def test_judge_rejects_verified_output_hash_different_from_product_identity(tmp_path: Path):
    bundle = _bundle(tmp_path)
    with pytest.raises(ScoreContractError) as exc:
        score_typed_attempt(
            gt_identity=_official_gt_identity(),
            gt=SimpleNamespace(floors=()),
            stage="correction",
            product_payload=bundle.result.geom.model_dump(mode="json"),
            product_identity=_official_product_identity(
                bundle,
                output_sha256="0" * 64,
            ),
            base_view_manifest=bundle.manifest,
            score_bindings=SimpleNamespace(content_sha256="d" * 64),
            completeness_overlay=None,
            c2_config=load_judge_score_config("src/configs/judge_score.yaml"),
            window_host_proof=bundle.proof,
        )
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.context == {"reason": "b5_output_hash_mismatch"}


def test_judge_rejects_payload_different_from_verified_output(tmp_path: Path):
    bundle = _bundle(tmp_path)
    payload = bundle.result.geom.model_dump(mode="json")
    payload["notes"] = "different candidate payload"
    with pytest.raises(ScoreContractError) as exc:
        score_typed_attempt(
            gt_identity=_official_gt_identity(),
            gt=SimpleNamespace(floors=()),
            stage="correction",
            product_payload=payload,
            product_identity=_official_product_identity(
                bundle,
                output_sha256=bundle.result.prepared_candidate_identity.output_sha256,
            ),
            base_view_manifest=bundle.manifest,
            score_bindings=SimpleNamespace(content_sha256="d" * 64),
            completeness_overlay=None,
            c2_config=load_judge_score_config("src/configs/judge_score.yaml"),
            window_host_proof=bundle.proof,
        )
    assert exc.value.code == "score_product_identity_invalid"
    assert exc.value.context == {
        "reason": "b5_product_payload_differs_from_verified_output",
    }


def test_judge_host_score_recomputes_boundary_segment_and_room_independently(tmp_path: Path):
    bundle = _bundle(tmp_path)
    window = bundle.result.geom.windows[0]
    segment, method = bind_correction_window_segment(
        window=window,
        segments=bundle.result.geom.facade_segments,
        allow_temporary_binding=False,
    )
    assert method == "declared_segment_binding"
    correct = resolve_correction_window_host(
        geometry=bundle.result.geom,
        window=window,
        product_segment=segment,
        gt_segment_id="gt-segment",
        gt_zone_id="gt-zone",
        product_to_gt_segment={segment.id: "gt-segment"},
        product_to_gt_zone={"r1": "gt-zone"},
    )
    wrong = resolve_correction_window_host(
        geometry=bundle.result.geom,
        window=window,
        product_segment=segment,
        gt_segment_id="gt-segment",
        gt_zone_id="gt-zone",
        product_to_gt_segment={segment.id: "gt-segment"},
        product_to_gt_zone={"r1": "different-zone"},
    )
    assert (correct, wrong) == ("complete", "miss")


# B5-C5 and the low-level branch ban.
def test_c5_production_correction_and_geometry_sources_import_no_judge():
    roots = [Path("src/agent/correction"), Path("src/agent/geometry")]
    offenders = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "src.agent.judge" in text or "from src.agent import judge" in text:
                offenders.append(str(path))
    assert offenders == []


def test_line_helper_body_has_no_facade_axis_or_xy_plane_branch():
    source = inspect.getsource(window_verts_on_line)
    assert "facade" not in source
    assert "_facade_axis" not in source
    assert "axis ==" not in source


# ---------------------------------------------------------------------------
# N-1 / §5-B exit 2: e2e window-host chain through score_service:230 (2026-07-27)
# ---------------------------------------------------------------------------
# The §5-B facade update at score_service:230 (_resolve_facade_product_to_gt) is
# the ONLY path that maps a product facade segment into product_to_gt; the
# downstream assign_openings consumes that map to route a real B5 correction
# window to its GT host.  The prior unit lock (test_b_facade_multi_span_straddle
# _fails_closed_not_first) calls the helper directly and never exercises :230, so
# neutering :230 left the whole suite green.  This lock drives a real
# VerifiedWindowHostProof six-artifact window through score_typed_attempt end to
# end, so neutering :230 makes a window fail closed (score_product_segment_
# unresolved) instead of silently mis-binding.


def _n1_gt(geom):
    """A GT structurally isomorphic to the bundle's corrected geometry: the same
    finalized vg-derived facade segments become boundary_segments (so the judge's
    own visibility adapter matches them exactly), one South opening sits on the
    South span, and the generator/tolerances/content_sha256 the judge helpers read
    are filled in."""
    south = next(segment for segment in geom.facade_segments if segment.facade_family == "South")

    def _wrap(segment):
        return SimpleNamespace(
            id=segment.id, floor_id=segment.floor_id, facade_family=segment.facade_family,
            p1=tuple(segment.p1), p2=tuple(segment.p2), outward_normal=tuple(segment.outward_normal),
            world_along_interval=segment.world_along_interval, depth=segment.depth,
            source_footprint_fingerprint=segment.source_footprint_fingerprint, source_refs=())

    floor = SimpleNamespace(
        id="f1",
        footprint=SimpleNamespace(exterior=SimpleNamespace(vertices=[[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]])),
        footprint_fingerprint=geom.facade_segments[0].source_footprint_fingerprint,
        zones=[SimpleNamespace(id="r1", polygon=SimpleNamespace(exterior=SimpleNamespace(
            vertices=[[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]])))],
        boundary_segments=[_wrap(segment) for segment in geom.facade_segments],
    )
    opening = SimpleNamespace(id="gt-w1", floor_id="f1", kind="window", boundary_segment_id=south.id,
        host_zone_id="r1", world_along_interval=SimpleNamespace(lo=1.0, hi=3.0),
        z_interval=SimpleNamespace(lo=1.0, hi=2.0), source_refs=())
    return SimpleNamespace(
        generator=SimpleNamespace(tolerances=SimpleNamespace(vg_depth_epsilon_m=0.3, vg_endpoint_epsilon_m=0.3)),
        content_sha256="e" * 64, floors=[floor], openings=[opening])


def _n1_bindings(bundle):
    plan_binding = PlanScoreViewBindingV1(kind="plan", input_id="plan", floor_id="f1", gt_source_view_ids=("gt-plan",))
    payload = {"schema_version": "1", "case_id": "case", "gt_content_sha256": "b" * 64,
               "case_metadata_sha256": H, "base_view_manifest_sha256": bundle.manifest.content_sha256,
               "bindings": [plan_binding.model_dump(mode="json")]}
    return JudgeScoreViewBindingsV1(schema_version="1", case_id="case", gt_content_sha256="b" * 64,
        case_metadata_sha256=H, base_view_manifest_sha256=bundle.manifest.content_sha256,
        bindings=(plan_binding,), content_sha256=canonical_sha256(payload))


def test_n1_facade_update_feeds_window_host_resolution_e2e(monkeypatch, tmp_path):
    bundle = _bundle(tmp_path)
    geom = bundle.result.geom
    common = dict(gt_identity=_official_gt_identity(), gt=_n1_gt(geom), stage="correction",
                  product_payload=geom.model_dump(mode="json"),
                  product_identity=_official_product_identity(
                      bundle, output_sha256=bundle.result.prepared_candidate_identity.output_sha256),
                  base_view_manifest=bundle.manifest, score_bindings=_n1_bindings(bundle),
                  completeness_overlay=None, c2_config=load_judge_score_config("src/configs/judge_score.yaml"),
                  window_host_proof=bundle.proof)
    # The grade PNG is a judge-side renderer; this lock pins the SCORING chain
    # (assign_openings / host_resolver), not the paint, so stub the renderer.
    import sys
    scripts_dir = str(Path(__file__).resolve().parents[1] / "scripts" / "tool_scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import render_grade
    monkeypatch.setattr(render_grade, "render_score_grade_png", lambda **kw: b"")
    # The window routes through :230's facade map and resolves matched.
    result = score_typed_attempt(**common)
    assert result.payload.extras == ()
    # NEUTER score_service:230 (the facade update feeds nothing) -> the window's
    # facade_segment_id is absent from product_to_gt -> assign_openings rejects it.
    monkeypatch.setattr("src.agent.judge.score_service._resolve_facade_product_to_gt", lambda **kw: {})
    with pytest.raises(ScoreContractError) as exc:
        score_typed_attempt(**common)
    assert exc.value.code == "score_product_segment_unresolved"
