from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.correction.feature_state import FeatureStateClaimsV1, artifact_feature_state, derive_feature_state_claims
from src.agent.correction.finalize import FinalizeResult
from src.agent.correction.finalize import finalize_correction_draw
from src.agent.correction.footprint import floor_footprint, floor_footprint_fingerprint, footprint_bbox
from src.agent.correction.parse import correction_target, ensure_corrected_geometry, parse_correction_draw, validate_final_corrected_geometry
from src.agent.correction.schema import CorrectedGeometry
from src.agent.correction.config import load_core_tolerances
from src.agent.correction.deterministic import _apply_envelope_reconcile, apply_deterministic_core
from src.agent.correction.envelope import AuthoritativeEnvelope, EnvelopeAxisResolution
from src.agent.execution.evidence_preflight import EvidenceDebt, EvidenceDebtItem
from src.agent.execution.manifest import RunInputs, RunManifestV2
from src.agent.execution.stage_runner import StageRunner
from src.validator.checks.correction import check_correction, check_evidence_debt_coverage
from src.validator.checks.schema import CheckReport


def _payload(*, ring=None):
    ring = ring or [[0, 0], [10, 0], [10, 8], [0, 8]]
    return {
        "schema_version": "3", "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"id": "f1", "name": "1F", "z_floor": 0, "ceiling_height": 3,
                    "footprint": {"vertices": ring},
                    "cells": [{"id": "room", "x": [0, 10], "y": [0, 8]}]}],
    }


def test_v3_is_strict_and_final_ring_is_canonical():
    with pytest.raises(Exception):
        ensure_corrected_geometry({**_payload(), "unknown": 1})
    target = correction_target("orthogonal_polygon")
    draw = parse_correction_draw(_payload(ring=[[0, 0], [0, 8], [10, 8], [10, 0], [0, 0]]), target)
    with pytest.raises(ValueError, match="must not repeat"):
        validate_final_corrected_geometry(draw)


def test_v3_footprint_is_floor_owned_and_helper_uses_it():
    geom = ensure_corrected_geometry(_payload())
    assert floor_footprint(geom, geom.floors[0]) == [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]
    assert footprint_bbox(geom) == ((0.0, 10.0), (0.0, 8.0))
    broken = _payload()
    del broken["floors"][0]["footprint"]
    with pytest.raises(Exception):
        ensure_corrected_geometry(broken)


def test_correction_writer_emits_b2_contract(tmp_path: Path):
    geom = validate_final_corrected_geometry(ensure_corrected_geometry(_payload()))
    target = correction_target("orthogonal_polygon")
    result = FinalizeResult(
        geom=geom,
        audit_payload={"corrections": [], "conflicts": [], "unsupported": []},
        feature_state_claims=derive_feature_state_claims(target, geom),
    )
    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    rec = StageRunner(tmp_path, manifest).record(stage="1_correction", stage_dir=tmp_path / "1_correction", output_obj=result, report=report)
    assert rec.accepted
    stage = manifest.accepted("1_correction")
    assert stage.artifact_contract == "correction_b2_v1"
    assert stage.stage_version == "2"
    assert set(stage.artifact_hashes) == {"output", "checks", "audit", "feature_states"}
    assert artifact_feature_state(tmp_path / "1_correction" / "attempts" / "001", stage, "per_floor_footprint") == "populated"
    output = json.loads((tmp_path / "1_correction" / "attempts" / "001" / "output.json").read_text())
    assert output["floors"][0]["id"] == "f1"


def test_v3_finalize_derives_legacy_bbox_from_floor_footprint(tmp_path: Path):
    raw = _payload()
    raw["footprint_x"] = [-99, 99]
    raw["footprint_y"] = [-99, 99]
    result = finalize_correction_draw(raw, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"))
    assert result.geom.footprint_x == [0.0, 10.0]
    assert result.geom.footprint_y == [0.0, 8.0]
    assert any(row["rule_id"] == "deterministic_core.v3_bbox_projection" for row in result.geom.corrections)


def _accepted_x_envelope():
    return AuthoritativeEnvelope(axes={
        "x": EnvelopeAxisResolution(axis="x", status="accepted", bounds=(0.0, 10.0)),
    })


def test_f1_legacy_polygon_envelope_rejection_is_preserved():
    geom = CorrectedGeometry.model_validate({
        "schema_version": "2", "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "1F", "z_floor": 0, "ceiling_height": 3,
                    "cells": [{"id": "L", "x": [0, 10], "y": [0, 8],
                               "polygon": [[0, 0], [10, 0], [10, 3], [4, 3], [4, 8], [0, 8]]}]}],
    })
    unsupported: list[dict] = []
    fx, fy = _apply_envelope_reconcile(geom, load_core_tolerances(), _accepted_x_envelope(), [], unsupported, [])
    assert (fx, fy) == ([0.0, 10.0], [0.0, 8.0])
    assert unsupported[0]["reason"] == (
        "authoritative envelope reconcile for polygon cells is not implemented in schema v2 B1; "
        "refusing to move bbox-only cell edges without moving polygon vertices"
    )


def test_f1_v3_nonrectangular_ring_envelope_rejection_is_preserved():
    geom = ensure_corrected_geometry(_payload(ring=[[0, 0], [10, 0], [10, 3], [4, 3], [4, 8], [0, 8]]))
    unsupported: list[dict] = []
    _apply_envelope_reconcile(geom, load_core_tolerances(), _accepted_x_envelope(), [], unsupported, [])
    assert "non-rectangular v3 footprints is unsupported" in unsupported[0]["reason"]


def test_f2_facade_segment_binds_floor_footprint_digest():
    raw = _payload()
    geom = ensure_corrected_geometry(raw)
    digest = floor_footprint_fingerprint(geom, geom.floors[0])
    raw["facade_segments"] = [{
        "id": "north-1", "floor_id": "f1", "facade_family": "North",
        "p1": [0, 8], "p2": [10, 8], "outward_normal": [0, 1],
        "world_along_interval": {"lo": 0, "hi": 10}, "depth": 0,
        "source_footprint_fingerprint": digest,
    }]
    assert ensure_corrected_geometry(raw).facade_segments[0].source_footprint_fingerprint == digest
    raw["facade_segments"][0]["source_footprint_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="source_footprint_fingerprint"):
        ensure_corrected_geometry(raw)


def _mismatched_bbox_geom():
    raw = _payload()
    raw["footprint_x"] = [-99, 99]
    raw["footprint_y"] = [-99, 99]
    return ensure_corrected_geometry(raw)


def test_f3_routes_r4_r5_r7_r8_use_floor_footprint():
    geom = _mismatched_bbox_geom()
    from src.agent.correction.envelope import _footprint_bounds as envelope_bounds
    from src.agent.judge.correction_score import _extract_correction_boundary
    from src.validator.checks.correction import _footprint_bounds as facade_bounds

    assert facade_bounds(geom) == ([0.0, 10.0], [0.0, 8.0])  # R4 facade frame
    assert envelope_bounds(geom) == {"x": (0.0, 10.0), "y": (0.0, 8.0)}  # R5
    rep = check_correction(geom, elevation_widths={"North": 10.0, "South": 10.0, "East": 8.0, "West": 8.0}, capability_profile="orthogonal_polygon")
    assert next(result for result in rep.results if result.check_id == "correction.cross_image_reconcile").status.value == "pass"  # R7
    assert _extract_correction_boundary(geom, geom.floors[0]) == {"S": 0.0, "N": 8.0, "W": 0.0, "E": 10.0}  # R8


def test_f3_routes_r6_r9_r10_use_floor_footprint():
    geom = _mismatched_bbox_geom()
    geom.floors[0].cells[0].x = [0, 4]
    geom.floors[0].cells[0].y = [0, 4]
    from src.agent.geometry.modelling import build_zone_volumes
    from scripts.tool_scripts.render_corrected_geometry import _floor_bounds
    from scripts.tool_scripts.render_elevation_windows import _along_extent

    zones, _ = build_zone_volumes(geom, capability_profile="orthogonal_polygon")
    assert zones[0].zone.endswith("_SW")  # R6 naming center
    floor = geom.model_dump()["floors"][0]
    data = geom.model_dump()
    assert _floor_bounds(data, floor) == (0.0, 0.0, 10.0, 8.0)  # R9
    assert _along_extent(data, "North") == (0.0, 10.0)  # R10


def test_f3_tampered_v3_and_feature_state_fail_closed(tmp_path: Path):
    loose = CorrectedGeometry.model_validate(_payload()).model_copy(update={"floors": [{"id": "f1"}]})
    assert loose.schema_version == "3"
    with pytest.raises(ValueError):
        apply_deterministic_core(loose, capability_profile="orthogonal_polygon")
    assert not check_correction(loose, capability_profile="orthogonal_polygon").passed

    geom = validate_final_corrected_geometry(ensure_corrected_geometry(_payload()))
    target = correction_target("orthogonal_polygon")
    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    rec = StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction",
        output_obj=FinalizeResult(geom, {"corrections": [], "conflicts": [], "unsupported": []}, derive_feature_state_claims(target, geom)),
        report=CheckReport(stage="1_correction", capability_profile="orthogonal_polygon"),
    )
    attempt = Path(rec.attempt_dir)
    (attempt / "output.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="hash chain"):
        artifact_feature_state(attempt, manifest.accepted("1_correction"), "per_floor_footprint")


def test_f3_v3_evidence_debt_requires_once_only_typed_resolution():
    debt = EvidenceDebt(debts=[EvidenceDebtItem(
        check_id="1f_view.reading.dimension_derived_refs", canonical_check_id="reading.dimension_derived_refs",
        status="fail", layer="cross_check", disposition="block", scope="element_local", offender_ids=["S1"],
    )])
    raw = _payload()
    raw["conflicts"] = [{"source_ids": ["S1"]}]
    geom = ensure_corrected_geometry(raw)
    assert not check_evidence_debt_coverage(geom, debt, capability_profile="orthogonal_polygon", run_profile="regression").passed
    raw["conflicts"] = [{"kind": "debt_resolution", "resolves_debt_id": debt.debts[0].debt_id, "rationale": "source checked", "source": "llm_correction"}]
    assert check_evidence_debt_coverage(ensure_corrected_geometry(raw), debt, capability_profile="orthogonal_polygon", run_profile="regression").passed
    raw["corrections"] = list(raw["conflicts"])
    assert not check_evidence_debt_coverage(ensure_corrected_geometry(raw), debt, capability_profile="orthogonal_polygon", run_profile="regression").passed
    raw["corrections"] = []
    raw["conflicts"] = [{"kind": "debt_resolution", "resolves_debt_id": "0" * 64, "rationale": "wrong debt", "source": "a3"}]
    assert not check_evidence_debt_coverage(ensure_corrected_geometry(raw), debt, capability_profile="orthogonal_polygon", run_profile="regression").passed


def test_f3_feature_state_wire_rejects_unknown_keys_and_states():
    wire = derive_feature_state_claims(correction_target("orthogonal_polygon"), ensure_corrected_geometry(_payload())).model_dump()
    wire["cell_polygon"] = "invented"
    with pytest.raises(ValueError):
        FeatureStateClaimsV1.model_validate(wire)
    wire = derive_feature_state_claims(correction_target("orthogonal_polygon"), ensure_corrected_geometry(_payload())).model_dump()
    wire["unknown_feature"] = "populated"
    with pytest.raises(ValueError):
        FeatureStateClaimsV1.model_validate(wire)
