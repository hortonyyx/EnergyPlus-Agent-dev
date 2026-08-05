"""B5 Phase-A gates: source trust, strict wires, bindings, and draw rejects."""
from __future__ import annotations

import hashlib
import importlib
import json

import pytest
from pydantic import ValidationError

from src.agent.correction.config import CoreTolerances, load_core_tolerances
from src.agent.correction.facade_applicability import _validate_bindings
from src.agent.correction.facade_visibility import VisibilityTolerances, materialize_all_facade_segments
from src.agent.correction.footprint import floor_footprint_fingerprint
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.schema import CorrectedGeometryV3, FieldProvenance
from src.agent.correction.window_host import (
    WindowHostConflictV1, WindowHostResolutionAuditV1, map_direction_binding_error, resolve_window_hosts,
)
from src.agent.correction.window_sources import (
    ElevationDirectionFactV1, PlanSourceWindowV1, WindowClaimSourceLinkV1, WindowResolverInputError,
    WindowDirectionBindingError, WindowResolverInputsV1, build_verified_window_resolver_inputs,
    build_window_source_offer, canonical_sha256,
    materialize_current_ring_va_elevation_bindings, source_locator, verify_window_resolver_inputs,
)
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry, ViewManifest

H = "a" * 64


def _entry(input_id: str, kind: str, *, floor_ref: int | None = None, claims=None, direction="South"):
    claims = claims or (["existence", "host", "along", "width"] if kind == "plan" else ["existence", "along", "width", "sill", "head", "appearance"])
    return RequiredViewEntry(input_id=input_id, source_image=f"case_data/{input_id}.png", image_sha256=H,
        view_type=kind, floor_ref=floor_ref, declared_direction_token=direction if kind == "elevation" else None,
        direction_source="standard_assumption", direction_semantics="building_axis", semantics_source="case_metadata",
        building_view_direction=direction if kind == "elevation" else None, dimensioned=True,
        expected_output_id=input_id, opening_evidence=OpeningEvidence(potentially_observable_claims=claims))


def _manifest(*entries):
    payload = {"view_manifest_schema_version": "1", "claims_vocab_version": "1", "generator_version": "1",
        "completeness_ruleset_version": "1", "case_id": "case", "case_metadata_sha256": H,
        "entries": [entry.model_dump(mode="json") for entry in sorted(entries, key=lambda entry: entry.input_id)]}
    model = ViewManifest(**payload, content_sha256=hash_obj(payload))
    return model, model.model_dump_json().encode()


def _reading(*strokes):
    return json.dumps({"image_kind": "plan", "strokes": list(strokes), "uncaptured": []}, separators=(",", ":")).encode()


def _geom(*, provenance=True):
    source = source_locator(input_id="plan", observation_id="W-01", output_sha256=hashlib.sha256(_reading({"id": "W-01", "pen": "window", "geometry": {"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 1.0]}})).hexdigest())
    return CorrectedGeometryV3.model_validate({"schema_version": "3", "footprint_x": [0.0, 4.0], "footprint_y": [0.0, 3.0],
        "floors": [{"id": "f1", "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
                    "footprint": {"vertices": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]},
                    "cells": [{"id": "r1", "x": [0.0, 4.0], "y": [0.0, 3.0]}]}],
        "windows": [{"id": "w1", "floor": "F1", "floor_id": "f1", "facade": "South", "span": [1.0, 2.0], "z": [1.0, 2.0], "room": "r1",
                     "provenance": {"existence": {"provenance": "observed", "source_ids": [source]}} if provenance else None}],
        "facade_segments": []})


def _base():
    manifest, raw_manifest = _manifest(_entry("plan", "plan", floor_ref=1), _entry("south", "elevation"))
    plan = _reading({"id": "W-01", "pen": "window", "geometry": {"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 1.0]}})
    elevation = json.dumps({"image_kind": "elevation", "strokes": [], "uncaptured": [],
        "facade": {"mirrored": False, "local_x_positive": "image_left_to_right"}}, separators=(",", ":")).encode()
    fact = ElevationDirectionFactV1(input_id="south", resolved_building_direction="South", resolution_source="manifest_building_axis",
        mirrored=False, local_x_positive="image_left_to_right", orientation_output_hash=None, adapter_version=None,
        view_manifest_sha256=manifest.content_sha256)
    return manifest, raw_manifest, {"plan": plan, "south": elevation}, fact


def _provenance(rows):
    return {claim: FieldProvenance.model_validate(value) for claim, value in rows.items()}


def _rehash_inputs(inputs):
    payload = inputs.model_dump(mode="json")
    payload.pop("content_sha256")
    return inputs.model_copy(update={"content_sha256": canonical_sha256(payload)})


def _audit_payload():
    return {
        "kind": "window_host_resolution", "rule_id": "deterministic_core.window_host_resolver_v1",
        "stage": "core", "claim_type": "topology_identity", "window_id": "w1", "floor_id": "f1",
        "original_room_id": "r1", "resolved_room_id": "r1", "original_facade_segment_id": None,
        "resolved_facade_segment_id": "f1:facade:1", "original_span": {"lo": 1.0, "hi": 2.0},
        "resolved_span": {"lo": 1.0, "hi": 2.0}, "source_ids": ("src:" + H,), "branch": "plan",
        "resolution_sha256": H,
        "tolerance_names": (
            "WINDOW_SEGMENT_ENDPOINT_CLAMP_TOL", "WINDOW_HOST_SPAN_EPSILON", "WINDOW_HOST_PLANE_EPSILON",
        ),
        "changes_topology": True,
    }


def test_b5_a1_source_identity_locator_vector_and_catalog():
    # Handwritten preimage/vector: do not call the production hash helper.
    assert source_locator(input_id="plan-1", observation_id="W-01", output_sha256="a" * 64) == "src:d4e4d28c48522a4852047b9c7f257b9370692c9c186a85c884c2774f2fa9d2e2"
    _, raw_manifest, artifacts, _ = _base()
    offer = build_window_source_offer(raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts)
    assert len(offer.source_windows) == 1
    assert offer.source_windows[0].channel == "plan"


def test_b5_a2_wire_strict_and_conflict_shape():
    with pytest.raises(ValidationError):
        PlanSourceWindowV1(channel="plan", source_locator="src:" + H, source_input_id="p", source_output_sha256=H,
            observation_id="w", floor_ref=True, world_x_interval={"lo": 0.0, "hi": 1.0},
            world_y_interval={"lo": 0.0, "hi": 1.0}, positive_claims=("existence",))
    with pytest.raises(ValidationError):
        WindowHostConflictV1(kind="window_host_conflict", conflict_schema_version="1", window_id="w", floor_id="f",
            branch="unresolved", reason_code="direction_binding_invalid", raw_span=None, source_input_ids=(), candidate_segment_ids=(),
            candidate_room_ids=(), crossed_segment_ids=(), trusted_negative=(), upstream_error_code="direction_binding_ring_invalid",
            failed_gate_id="correction.window_host_resolution", fallback_action="needs_input_no_geometry_commit", blocking=True)
    payload = _geom().model_dump(mode="json"); payload["corrections"] = [{"kind": "window_host_resolution"}]
    with pytest.raises(ValidationError):
        CorrectedGeometryV3.model_validate(payload)


def test_b5pa_01_audit_tolerance_names_are_fixed_ordered_triplet():
    audit = WindowHostResolutionAuditV1(**_audit_payload())
    assert audit.tolerance_names == (
        "WINDOW_SEGMENT_ENDPOINT_CLAMP_TOL", "WINDOW_HOST_SPAN_EPSILON", "WINDOW_HOST_PLANE_EPSILON",
    )
    with pytest.raises(ValidationError):
        WindowHostResolutionAuditV1(**{**_audit_payload(), "tolerance_names": ()})
    with pytest.raises(ValidationError):
        WindowHostResolutionAuditV1(**{**_audit_payload(), "tolerance_names": (
            "WINDOW_HOST_SPAN_EPSILON", "WINDOW_SEGMENT_ENDPOINT_CLAMP_TOL", "WINDOW_HOST_PLANE_EPSILON",
        )})


def test_b5_a3_config_a0_required_and_relations():
    tol = load_core_tolerances()
    assert (tol.window_segment_endpoint_clamp_tol_m, tol.window_host_span_epsilon_m, tol.window_host_plane_epsilon_m) == (0.01, 1e-9, 1e-9)
    base = tol.__dict__.copy(); base.pop("window_host_plane_epsilon_m")
    with pytest.raises(TypeError):
        CoreTolerances(**base)
    with pytest.raises(ValueError):
        CoreTolerances(**{**tol.__dict__, "window_host_span_epsilon_m": 0.02}).validate()


def test_b5_a4_va_type_import_and_direction_fact_tamper_rejected():
    manifest, raw_manifest, artifacts, fact = _base()
    marker = build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))
    assert marker.inputs.elevation_direction_facts[0].resolved_building_direction == "South"
    bad = fact.model_copy(update={"mirrored": True})
    with pytest.raises(WindowResolverInputError, match="direction_fact_invalid"):
        build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(bad,))


def test_bind_1_direction_family_tamper_rejected():
    _, raw_manifest, artifacts, fact = _base()
    with pytest.raises(WindowResolverInputError, match="direction_fact_invalid"):
        build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact.model_copy(update={"resolved_building_direction": "North"}),))


def test_bind_1_orientation_hash_tamper_rejected():
    _, raw_manifest, artifacts, fact = _base()
    with pytest.raises(WindowResolverInputError, match="direction_fact_invalid"):
        build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact.model_copy(update={"orientation_output_hash": "b" * 64}),))


def test_b5_a5_hash_vectors_are_literal_and_change_sensitive():
    assert hashlib.sha256(b"[]").hexdigest() == "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    literal = b'{"input_id":"plan-1","observation_id":"W-01","output_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","schema":"window_source_locator_v1"}'
    assert hashlib.sha256(literal).hexdigest() == "d4e4d28c48522a4852047b9c7f257b9370692c9c186a85c884c2774f2fa9d2e2"
    assert hashlib.sha256(literal[:-1] + b" ").hexdigest() != "d4e4d28c48522a4852047b9c7f257b9370692c9c186a85c884c2774f2fa9d2e2"


def test_b5_a6_current_ring_binding_parity_and_ring_free_rejection():
    manifest, raw_manifest, artifacts, fact = _base()
    geom = _geom()
    segments = materialize_all_facade_segments(geom, tolerances=VisibilityTolerances(1e-9, 1e-9))
    geom = geom.model_copy(update={"facade_segments": list(segments)})
    bindings = materialize_current_ring_va_elevation_bindings(geom=geom, manifest=manifest, direction_facts=(fact,),
        visibility_tolerances=VisibilityTolerances(1e-9, 1e-9))
    _validate_bindings(manifest, bindings)
    # Frozen judge-compatible South frame vector: no production helper result is used as expected.
    assert bindings[0].frame_transform_sha256 == "b0051aa21fe1a5532df46986f31f7461a767b172a4aab0d280f1554ea6082a86"
    # Judge is parity oracle only; production source remains judge-blind.
    from src.agent.judge.score_inputs import materialize_va_elevation_bindings
    from src.agent.judge.score_schema import ElevationScoreViewBindingV1, JudgeScoreViewBindingsV1, PlanScoreViewBindingV1, canonical_sha256 as judge_hash
    judge_rows = (
        PlanScoreViewBindingV1(kind="plan", input_id="plan", floor_id="f1", gt_source_view_ids=("gt-plan",)),
        ElevationScoreViewBindingV1(kind="elevation", input_id="south", floor_ids=("f1",), facade_family="South",
            gt_source_view_ids=("gt-south",), resolved_building_direction="South", resolution_source="manifest_building_axis",
            orientation_output_hash=None, adapter_version=None, source_footprint_fingerprint=floor_footprint_fingerprint(geom, geom.floors[0]),
            world_axis="x", sign=1, along_origin=0.0, mirrored=False, local_x_positive="image_left_to_right",
            frame_transform_sha256="b0051aa21fe1a5532df46986f31f7461a767b172a4aab0d280f1554ea6082a86"),
    )
    judge_payload = {"schema_version": "1", "case_id": "case", "gt_content_sha256": "b" * 64,
        "case_metadata_sha256": H, "base_view_manifest_sha256": manifest.content_sha256,
        "bindings": [row.model_dump(mode="json") for row in judge_rows]}
    judge_bindings = JudgeScoreViewBindingsV1(schema_version="1", case_id="case", gt_content_sha256="b" * 64,
        case_metadata_sha256=H, base_view_manifest_sha256=manifest.content_sha256, bindings=judge_rows,
        content_sha256=judge_hash(judge_payload))
    assert tuple(row.model_dump(mode="json") for row in bindings) == tuple(row.model_dump(mode="json") for row in materialize_va_elevation_bindings(score_bindings=judge_bindings, effective_manifest=manifest))
    bad = geom.model_copy(update={"facade_segments": []})
    with pytest.raises(Exception, match="direction_binding_ring_invalid"):
        materialize_current_ring_va_elevation_bindings(geom=bad, manifest=manifest, direction_facts=(fact,),
            visibility_tolerances=VisibilityTolerances(1e-9, 1e-9))


def test_b5_a6_production_source_is_judge_blind():
    source = open(importlib.import_module("src.agent.correction.window_sources").__file__, encoding="utf-8").read()
    assert "src.agent.judge" not in source


def test_b5_b1_plan_source_resolves_hidden_segment_without_center_guess():
    manifest, raw_manifest = _manifest(_entry("plan", "plan", floor_ref=1), _entry("east", "elevation", direction="East"))
    plan = _reading({"id": "W-01", "pen": "window", "geometry": {"x_range_m":[2.9, 3.1], "y_range_m":[4.0, 5.0]}})
    elevation = json.dumps({"image_kind": "elevation", "strokes": [], "uncaptured": [],
        "facade": {"view_facade": "East", "mirrored": False, "local_x_positive": "image_left_to_right"}}, separators=(",", ":")).encode()
    artifacts = {"plan": plan, "east": elevation}
    locator = source_locator(input_id="plan", observation_id="W-01", output_sha256=hashlib.sha256(plan).hexdigest())
    ring = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [7.0, 8.0], [7.0, 3.0], [3.0, 3.0], [3.0, 8.0], [0.0, 8.0]]
    geom = CorrectedGeometryV3.model_validate({"schema_version": "3", "footprint_x": [0.0, 10.0], "footprint_y": [0.0, 8.0],
        "floors": [{"id": "f1", "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
                    "footprint": {"vertices": ring}, "cells": [{"id": "r1", "x": [0.0, 10.0], "y": [0.0, 8.0], "polygon": ring}]}],
        "windows": [{"id": "w1", "floor": "F1", "floor_id": "f1", "facade": "East", "span": [4.0, 5.0], "z": [1.0, 2.0], "room": "r1",
                     "provenance": {"existence": {"provenance": "observed", "source_ids": [locator]}}}], "facade_segments": []})
    fact = ElevationDirectionFactV1(input_id="east", resolved_building_direction="East", resolution_source="manifest_building_axis",
        mirrored=False, local_x_positive="image_left_to_right", orientation_output_hash=None, adapter_version=None,
        view_manifest_sha256=manifest.content_sha256)
    verified = build_verified_window_resolver_inputs(producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))
    segments = list(materialize_all_facade_segments(geom, tolerances=VisibilityTolerances(1e-9, 1e-9)))
    hidden = next(segment for segment in segments if segment.facade_family == "East" and segment.p1[0] == 3.0)
    assert hidden.visible_intervals == []
    geom = geom.model_copy(update={"facade_segments": segments})
    claims = resolve_window_hosts(geom, verified_inputs=verified, tolerances=load_core_tolerances())
    row = claims.resolutions[0]
    assert (row.branch, row.room_id, row.facade_segment_id, row.visible_overlap_intervals) == ("plan", "r1", hidden.id, ())


def _assert_a6_frozen_judge_parity(*, input_id, family, mirrored, expected_axis, expected_sign, expected_origin, expected_hash):
    manifest, _ = _manifest(_entry("plan", "plan", floor_ref=1), _entry(input_id, "elevation", direction=family))
    geom = _geom()
    geom = geom.model_copy(update={"facade_segments": list(materialize_all_facade_segments(
        geom, tolerances=VisibilityTolerances(1e-9, 1e-9)))})
    fact = ElevationDirectionFactV1(input_id=input_id, resolved_building_direction=family,
        resolution_source="manifest_building_axis", mirrored=mirrored, local_x_positive="image_left_to_right",
        orientation_output_hash=None, adapter_version=None, view_manifest_sha256=manifest.content_sha256)
    binding = materialize_current_ring_va_elevation_bindings(geom=geom, manifest=manifest, direction_facts=(fact,),
        visibility_tolerances=VisibilityTolerances(1e-9, 1e-9))[0]
    assert (binding.world_axis, binding.sign, binding.along_origin, binding.frame_transform_sha256) == (
        expected_axis, expected_sign, expected_origin, expected_hash,
    )
    from src.agent.judge.score_inputs import materialize_va_elevation_bindings
    from src.agent.judge.score_schema import ElevationScoreViewBindingV1, JudgeScoreViewBindingsV1, PlanScoreViewBindingV1, canonical_sha256 as judge_hash
    rows = (
        PlanScoreViewBindingV1(kind="plan", input_id="plan", floor_id="f1", gt_source_view_ids=("gt-plan",)),
        ElevationScoreViewBindingV1(kind="elevation", input_id=input_id, floor_ids=("f1",), facade_family=family,
            gt_source_view_ids=("gt-" + input_id,), resolved_building_direction=family,
            resolution_source="manifest_building_axis", orientation_output_hash=None, adapter_version=None,
            source_footprint_fingerprint=floor_footprint_fingerprint(geom, geom.floors[0]), world_axis=expected_axis,
            sign=expected_sign, along_origin=expected_origin, mirrored=mirrored,
            local_x_positive="image_left_to_right", frame_transform_sha256=expected_hash),
    )
    payload = {"schema_version": "1", "case_id": "case", "gt_content_sha256": "b" * 64,
        "case_metadata_sha256": H, "base_view_manifest_sha256": manifest.content_sha256,
        "bindings": [row.model_dump(mode="json") for row in rows]}
    judge_bindings = JudgeScoreViewBindingsV1(schema_version="1", case_id="case", gt_content_sha256="b" * 64,
        case_metadata_sha256=H, base_view_manifest_sha256=manifest.content_sha256, bindings=rows,
        content_sha256=judge_hash(payload))
    assert binding.model_dump(mode="json") == materialize_va_elevation_bindings(
        score_bindings=judge_bindings, effective_manifest=manifest)[0].model_dump(mode="json")


def test_b5pa_04_a6_mirrored_flip_frozen_judge_parity():
    _assert_a6_frozen_judge_parity(input_id="south", family="South", mirrored=True,
        expected_axis="x", expected_sign=-1, expected_origin=4.0,
        expected_hash="400d1ac490c1b7a72fd66d206fae7c8827456e048cc7d7d48f73c243433190cd")


def test_b5pa_04_a6_axis_y_frozen_judge_parity():
    _assert_a6_frozen_judge_parity(input_id="east", family="East", mirrored=False,
        expected_axis="y", expected_sign=1, expected_origin=0.0,
        expected_hash="dac44f5623dc1d6dcb288a767573e760c4da6e52d034c4f688fa5aa022717f80")


def test_b5pa_03_map_direction_binding_error_is_canonical_and_blocking():
    manifest, raw_manifest, artifacts, fact = _base()
    verified = build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))
    payload = _geom().model_dump(mode="json")
    payload["floors"].append({**payload["floors"][0], "id": "f2", "name": "F2", "z_floor": 3.0,
        "cells": [{"id": "r2", "x": [0.0, 4.0], "y": [0.0, 3.0]}]})
    payload["windows"].append({**payload["windows"][0], "id": "w2", "floor": "F2", "floor_id": "f2", "room": "r2", "z": [4.0, 5.0]})
    geom = CorrectedGeometryV3.model_validate(payload)
    scoped = map_direction_binding_error(WindowDirectionBindingError("direction_binding_ring_invalid", {"floor_id": "f2"}),
        geom=geom, verified_inputs=verified, phase="final")
    global_rows = map_direction_binding_error(WindowDirectionBindingError("direction_binding_ring_incompatible", {}),
        geom=geom, verified_inputs=verified, phase="dry_pre_transform")
    assert [row.window_id for row in scoped] == ["w2"]
    assert [row.window_id for row in global_rows] == ["w1", "w2"]
    for row, code in ((scoped[0], "direction_binding_ring_invalid"), *[(row, "direction_binding_ring_incompatible") for row in global_rows]):
        assert (row.reason_code, row.upstream_error_code, row.fallback_action, row.blocking) == (
            "direction_binding_invalid", code, "invariant_no_geometry_commit", True,
        )


def test_src_c1_plan_sill_permission_rejected():
    _verify_invalid_channel_claim("plan", "sill")


def test_src_c2_elevation_host_permission_rejected():
    _verify_invalid_channel_claim("elevation", "host")


def _verify_invalid_channel_claim(channel, claim):
    _, raw_manifest, artifacts, fact = _base()
    marker = build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))
    row = marker.inputs.source_windows[0]
    if channel == "elevation":
        from src.agent.correction.window_sources import ElevationSourceWindowV1
        row = ElevationSourceWindowV1(channel="elevation", source_locator=row.source_locator, source_input_id="south",
            source_output_sha256=row.source_output_sha256, observation_id=row.observation_id,
            local_along_interval=row.world_x_interval, local_z_interval=None, positive_claims=("existence", "host"))
    else:
        row = row.model_copy(update={"positive_claims": ("existence", "sill")})
    inputs = _rehash_inputs(marker.inputs.model_copy(update={"source_windows": (row,),
        "claim_links": (WindowClaimSourceLinkV1(window_id="w1", claim=claim, source_locator=row.source_locator),)}))
    with pytest.raises(WindowResolverInputError, match="claim_permission_invalid"):
        verify_window_resolver_inputs(inputs)


def _reject_claim(channel, claim, code):
    manifest, raw_manifest, artifacts, fact = _base()
    if channel == "plan":
        raw = json.loads(artifacts["plan"]); raw["strokes"][0]["geometry"] = {"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 1.0]}; artifacts["plan"] = json.dumps(raw).encode()
        geom = _geom(); locator = source_locator(input_id="plan", observation_id="W-01", output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest())
    else:
        artifacts["south"] = _reading({"id": "E-01", "pen": "window", "geometry": {"x_range_m":[1.0, 2.0]}})
        geom = _geom(); locator = source_locator(input_id="south", observation_id="E-01", output_sha256=hashlib.sha256(artifacts["south"]).hexdigest())
    provenance = {"existence": {"provenance": "observed", "source_ids": [source_locator(input_id="plan", observation_id="W-01", output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest())]},
                  claim: {"provenance": "observed", "source_ids": [locator]}}
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={"provenance": _provenance(provenance)})]})
    with pytest.raises(WindowResolverInputError, match=code):
        build_verified_window_resolver_inputs(producer_draw=geom, raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))


def test_src_c3_producer_segment_ref_rejected():
    payload = _geom().model_dump(mode="json"); payload["windows"][0]["facade_segment_id"] = "fake"
    with pytest.raises(WindowResolverInputError, match="producer_segment_ref_prefilled"):
        parse_correction_draw(payload, correction_target("orthogonal_polygon"))


def test_src_c4_producer_resolver_audit_rejected():
    payload = _geom().model_dump(mode="json"); payload["corrections"] = [{"kind": "window_host_resolution"}]
    with pytest.raises(WindowResolverInputError, match="producer_resolver_audit_prefilled"):
        parse_correction_draw(payload, correction_target("orthogonal_polygon"))


def test_src_c5_duplicate_catalog_locator_rejected():
    manifest, raw_manifest, artifacts, fact = _base()
    marker = build_verified_window_resolver_inputs(producer_draw=_geom(), raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))
    duplicate = _rehash_inputs(marker.inputs.model_copy(update={"source_windows": marker.inputs.source_windows * 2}))
    with pytest.raises(WindowResolverInputError, match="duplicate_source_locator"):
        verify_window_resolver_inputs(duplicate)


def test_src_c6_duplicate_raw_observation_rejected():
    _, raw_manifest, artifacts, _ = _base(); row = {"id": "W-01", "pen": "window", "geometry": {"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 1.0]}}
    artifacts["plan"] = _reading(row, row)
    with pytest.raises(WindowResolverInputError, match="duplicate_source_observation"):
        build_window_source_offer(raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts)


def test_src_c7_non_contiguous_manifest_floor_ref_rejected():
    with pytest.raises(ValidationError, match="manifest_floor_ref_non_contiguous"):
        _manifest(_entry("p1", "plan", floor_ref=1), _entry("p3", "plan", floor_ref=3))


def test_src_c8_elevation_floor_mismatch_rejected():
    manifest, raw_manifest, artifacts, fact = _base()
    artifacts["south"] = _reading({"id": "E-01", "pen": "window", "geometry": {"x_range_m":[1.0, 2.0], "y_range_m":[4.0, 5.0]}})
    geom = _geom(); plan_locator = source_locator(input_id="plan", observation_id="W-01", output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest())
    elev_locator = source_locator(input_id="south", observation_id="E-01", output_sha256=hashlib.sha256(artifacts["south"]).hexdigest())
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={"provenance": _provenance({
        "existence": {"provenance": "observed", "source_ids": [plan_locator, elev_locator]}})})]})
    with pytest.raises(WindowResolverInputError, match="elevation_floor_mismatch"):
        build_verified_window_resolver_inputs(producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))


def test_src_c9_source_claim_undeclared_rejected():
    _reject_claim("plan", "sill", "source_claim_undeclared")


def test_src_c10_manifest_claim_not_observable_rejected():
    manifest, raw_manifest, artifacts, fact = _base()
    # The raw plan source supports host, while this trusted manifest explicitly does not.
    manifest, raw_manifest = _manifest(_entry("plan", "plan", floor_ref=1, claims=["existence"]), _entry("south", "elevation"))
    geom = _geom(); loc = source_locator(input_id="plan", observation_id="W-01", output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest())
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={"provenance": _provenance({"existence": {"provenance": "observed", "source_ids": [loc]}, "host": {"provenance": "observed", "source_ids": [loc]}})})]})
    fact = fact.model_copy(update={"view_manifest_sha256": manifest.content_sha256})
    with pytest.raises(WindowResolverInputError, match="manifest_claim_not_observable"):
        build_verified_window_resolver_inputs(producer_draw=geom, raw_view_manifest_bytes=raw_manifest, raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))


def test_source_dangling_locator_rejected_fail_closed():
    _, raw_manifest, artifacts, fact = _base()
    geom = _geom(); geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={"provenance": _provenance({
        "existence": {"provenance": "observed", "source_ids": ["src:" + "0" * 64]}})})]})
    with pytest.raises(WindowResolverInputError, match="source_identity_invalid"):
        build_verified_window_resolver_inputs(producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))


def test_source_assumed_existence_rejected_fail_closed():
    _, raw_manifest, artifacts, fact = _base()
    geom = _geom(); source = next(iter(geom.windows[0].provenance["existence"].source_ids))
    geom = geom.model_copy(update={"windows": [geom.windows[0].model_copy(update={"provenance": _provenance({
        "existence": {"provenance": "assumed", "source_ids": [source]}})})]})
    with pytest.raises(WindowResolverInputError, match="source_identity_invalid"):
        build_verified_window_resolver_inputs(producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
            raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,))
