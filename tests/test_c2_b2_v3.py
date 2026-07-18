from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.correction.feature_state import (
    FeatureStateClaimsV1,
    artifact_feature_state,
    correction_stage_version,
    derive_feature_state_claims,
)
from src.agent.correction.finalize import FinalizeResult, _identity_snapshot
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
    # Vg is mandatory for every v3 finalize now: route through the real
    # finalize pipeline (not a bare ensure_corrected_geometry) so
    # facade_segments is actually populated before the writer records it.
    target = correction_target("orthogonal_polygon")
    result = finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)
    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    rec = StageRunner(tmp_path, manifest).record(stage="1_correction", stage_dir=tmp_path / "1_correction", output_obj=result, report=report)
    assert rec.accepted
    stage = manifest.accepted("1_correction")
    assert stage.artifact_contract == "correction_b2_v1"
    assert stage.stage_version == "3"
    assert set(stage.artifact_hashes) == {"output", "checks", "audit", "feature_states"}
    assert artifact_feature_state(tmp_path / "1_correction" / "attempts" / "001", stage, "per_floor_footprint") == "populated"
    assert artifact_feature_state(tmp_path / "1_correction" / "attempts" / "001", stage, "facade_segments") == "populated"
    output = json.loads((tmp_path / "1_correction" / "attempts" / "001" / "output.json").read_text())
    assert output["floors"][0]["id"] == "f1"
    assert len(output["facade_segments"]) == 4  # one North/South/East/West segment for a plain rectangle


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
    out = _apply_envelope_reconcile(geom, load_core_tolerances(), _accepted_x_envelope())
    assert (out.footprint_x, out.footprint_y) == ([0.0, 10.0], [0.0, 8.0])
    assert out.unsupported[0]["reason"] == (
        "authoritative envelope reconcile for polygon cells is not implemented in schema v2 B1; "
        "refusing to move bbox-only cell edges without moving polygon vertices"
    )


def test_f1_v3_nonrectangular_ring_blanket_rejection_is_removed():
    geom = ensure_corrected_geometry(_payload(ring=[[0, 0], [10, 0], [10, 3], [4, 3], [4, 8], [0, 8]]))
    out = apply_deterministic_core(geom, load_core_tolerances(), authoritative_envelope=_accepted_x_envelope(), capability_profile="orthogonal_polygon")
    assert not any("vertex-level deformation belongs to B2b" in row.get("reason", "") for row in out.unsupported)


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

    target = correction_target("orthogonal_polygon")
    result = finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)
    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    rec = StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction",
        output_obj=result,
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


def _populated_v3_claims() -> FeatureStateClaimsV1:
    # Hand-built valid post-Vg claims — decoupled from finalize/Vg plumbing so
    # this test stays focused on FeatureStateClaimsV1's own wire validation.
    return FeatureStateClaimsV1(
        target_schema_version="3", phase_contract="b2",
        helper_versions=("floor_footprint_v1", "facade_visibility_v1"),
        cell_polygon="populated", per_floor_footprint="populated",
        facade_segments="populated", typed_north_axis="declared_unpopulated",
    )


def test_f3_feature_state_wire_rejects_unknown_keys_and_states():
    wire = _populated_v3_claims().model_dump()
    wire["cell_polygon"] = "invented"
    with pytest.raises(ValueError):
        FeatureStateClaimsV1.model_validate(wire)
    wire = _populated_v3_claims().model_dump()
    wire["unknown_feature"] = "populated"
    with pytest.raises(ValueError):
        FeatureStateClaimsV1.model_validate(wire)


# --------------------------------------------------------------------------- #
# C2 Vg batch (proposals/c2_vg_detail_spec.md §12.3): finalize identity
# timing, producer permissions, dual-path parity, stage-version release map,
# and legacy zero-regression.
# --------------------------------------------------------------------------- #
def test_v3_producer_prefilled_facade_segments_still_rejected():
    raw = _payload()
    geom = ensure_corrected_geometry(_payload())
    digest = floor_footprint_fingerprint(geom, geom.floors[0])
    raw["facade_segments"] = [{
        "id": "north-1", "floor_id": "f1", "facade_family": "North",
        "p1": [0, 8], "p2": [10, 8], "outward_normal": [0, 1],
        "world_along_interval": {"lo": 0, "hi": 10}, "depth": 0,
        "source_footprint_fingerprint": digest,
    }]
    target = correction_target("orthogonal_polygon")
    with pytest.raises(ValueError, match="b2 draw contract requires empty facade_segments"):
        parse_correction_draw(raw, target)


def test_v3_finalize_vg_uses_post_core_ring_not_producer_ring(tmp_path: Path):
    # 10.003 is off the default 0.01m structural snap grid; the deterministic
    # core snaps it to 10.0 before Vg ever runs, so a facade segment reading
    # the PRE-core producer ring would see 10.003, not 10.0.
    raw = _payload(ring=[[0, 0], [10.003, 0], [10.003, 8], [0, 8]])
    target = correction_target("orthogonal_polygon")
    result = finalize_correction_draw(raw, vector_dir=tmp_path, target=target)
    floor = result.geom.floors[0]
    assert floor_footprint(result.geom, floor) == [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]]
    east = next(s for s in result.geom.facade_segments if s.facade_family == "East")
    assert east.p1[0] == 10.0 and east.p2[0] == 10.0
    assert (east.world_along_interval.lo, east.world_along_interval.hi) == (0.0, 8.0)


def test_identity_snapshot_includes_segment_component_even_though_b2_draws_start_empty():
    # b2 draw contract normally forces facade_segments=[] on entry (tested
    # above); bypass that producer-parser gate directly so the segment
    # component of `_identity_snapshot`'s 3-tuple is exercised even though
    # the real end-to-end pipeline never observes a non-empty pre-materialize
    # segment list.
    geom_for_fp = ensure_corrected_geometry(_payload())
    digest = floor_footprint_fingerprint(geom_for_fp, geom_for_fp.floors[0])
    raw = _payload()
    raw["facade_segments"] = [{
        "id": "north-1", "floor_id": "f1", "facade_family": "North",
        "p1": [0, 8], "p2": [10, 8], "outward_normal": [0, 1],
        "world_along_interval": {"lo": 0, "hi": 10}, "depth": 0,
        "source_footprint_fingerprint": digest,
    }]
    geom = ensure_corrected_geometry(raw)  # bypasses parse_correction_draw's b2 gate
    before = _identity_snapshot(geom)
    assert before[2] == (("north-1", "f1"),)
    tampered_segment = geom.facade_segments[0].model_copy(update={"id": "north-2"})
    mutated = geom.model_copy(update={"facade_segments": [tampered_segment]})
    after = _identity_snapshot(mutated)
    assert before != after


def test_finalize_raises_if_core_mutates_floor_identity(tmp_path, monkeypatch):
    import src.agent.correction.finalize as finalize_module

    def _tamper_core(geom, tol=None, *, authoritative_envelope=None, capability_profile="rectangular",
                     verified_window_inputs=None):
        object.__setattr__(geom.floors[0], "id", "tampered")
        return geom

    monkeypatch.setattr(finalize_module, "apply_deterministic_core", _tamper_core)
    target = correction_target("orthogonal_polygon")
    with pytest.raises(ValueError, match="finalize invariant"):
        finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)


def test_finalize_raises_if_core_mutates_window_floor_reference(tmp_path, monkeypatch):
    import src.agent.correction.finalize as finalize_module

    raw = _payload()
    raw["windows"] = [{"id": "w1", "floor": "1F", "floor_id": "f1", "facade": "South", "span": [1, 2], "z": [1, 2]}]

    def _tamper_core(geom, tol=None, *, authoritative_envelope=None, capability_profile="rectangular",
                     verified_window_inputs=None):
        geom.windows[0].floor_id = "tampered"
        return geom

    monkeypatch.setattr(finalize_module, "apply_deterministic_core", _tamper_core)
    target = correction_target("orthogonal_polygon")
    # B5 now rejects v3 windows without a verified source marker before core;
    # floor-reference mutation remains covered by the marker-backed Phase-B
    # resolver tests.
    with pytest.raises(ValueError, match="source_identity_invalid"):
        finalize_correction_draw(raw, vector_dir=tmp_path, target=target)


def test_v3_finalize_parity_dict_vs_parsed_geom_and_feature_state(tmp_path: Path):
    """Integrated (producer dict payload) vs stepwise (pre-parsed geom object)
    entry conventions both delegate to the one shared `finalize_correction_draw`
    (spec §12.3 item 15): same fixture must produce byte-identical geometry
    and feature-state claims regardless of entry convention."""
    target = correction_target("orthogonal_polygon")
    payload = _payload()
    result_from_dict = finalize_correction_draw(payload, vector_dir=tmp_path, target=target)
    parsed = parse_correction_draw(payload, target)
    result_from_geom = finalize_correction_draw(parsed, vector_dir=tmp_path, target=target)
    assert result_from_dict.geom.model_dump_json() == result_from_geom.geom.model_dump_json()
    assert result_from_dict.feature_state_claims == result_from_geom.feature_state_claims
    assert result_from_dict.feature_state_claims.facade_segments == "populated"
    assert result_from_dict.feature_state_claims.helper_versions == ("floor_footprint_v1", "facade_visibility_v1")


def test_correction_stage_version_from_helper_versions():
    """C2 Vg rework CR2 (§9.2 central release map): the map is now keyed on
    the FULL claims state (schema + helper_versions + all four feature
    states), covering all three legitimate lineages — legacy v1, B2 v3, and
    Vg v3 — plus a fail-closed rejection for anything unregistered."""
    legacy_claims = FeatureStateClaimsV1(
        target_schema_version="1", phase_contract="b2",
        helper_versions=(),
        cell_polygon="not_declared", per_floor_footprint="not_declared",
        facade_segments="not_declared", typed_north_axis="not_declared",
    )
    assert correction_stage_version(legacy_claims) == "2"

    b2_claims = FeatureStateClaimsV1(
        target_schema_version="3", phase_contract="b2",
        helper_versions=("floor_footprint_v1",),
        cell_polygon="populated", per_floor_footprint="populated",
        facade_segments="declared_unpopulated", typed_north_axis="declared_unpopulated",
    )
    assert correction_stage_version(b2_claims) == "2"

    vg_claims = _populated_v3_claims()
    assert correction_stage_version(vg_claims) == "3"

    unknown_claims = FeatureStateClaimsV1(
        target_schema_version="3", phase_contract="b2",
        helper_versions=("floor_footprint_v1", "some_future_helper_v1"),
        cell_polygon="populated", per_floor_footprint="populated",
        facade_segments="populated", typed_north_axis="declared_unpopulated",
    )
    with pytest.raises(ValueError, match="unknown correction helper/state release"):
        correction_stage_version(unknown_claims)

    # A claims combination whose helper_versions matches a registered B2 row
    # but whose facade_segments state does not (an inconsistent/tampered
    # state) is a DIFFERENT, unregistered full key — still rejected, now
    # purely by table lookup (no separate post-hoc state check needed).
    mismatched_claims = FeatureStateClaimsV1(
        target_schema_version="3", phase_contract="b2",
        helper_versions=("floor_footprint_v1",),
        cell_polygon="populated", per_floor_footprint="populated",
        facade_segments="populated", typed_north_axis="declared_unpopulated",
    )
    with pytest.raises(ValueError, match="unknown correction helper/state release"):
        correction_stage_version(mismatched_claims)

    mismatched_vg_claims = FeatureStateClaimsV1(
        target_schema_version="3", phase_contract="b2",
        helper_versions=("floor_footprint_v1", "facade_visibility_v1"),
        cell_polygon="populated", per_floor_footprint="populated",
        facade_segments="declared_unpopulated", typed_north_axis="declared_unpopulated",
    )
    with pytest.raises(ValueError, match="unknown correction helper/state release"):
        correction_stage_version(mismatched_vg_claims)


def test_vg_attempt_uses_derived_stage_version(tmp_path: Path):
    target = correction_target("orthogonal_polygon")
    result = finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)
    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    rec = StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction",
        output_obj=result, report=report, stage_version="9",
    )
    assert rec.accepted
    # writer derives it from the re-derived claims; a caller-supplied
    # stage_version ("9" here) must never leak through.
    assert manifest.accepted("1_correction").stage_version == "3"

    import inspect
    import re

    from src.agent.execution import stage_runner as stage_runner_module
    source = inspect.getsource(stage_runner_module)
    # `geom.schema_version == "3"` is a legitimate, necessary read of the
    # correction schema version; what must never appear is a hardcoded
    # `stage_version = "3"` / `stage_version="3"` assignment.
    assert not re.search(r'stage_version\s*=\s*"3"', source), (
        "stage_runner.py must not hardcode a correction stage_version literal"
    )


def test_legacy_v1_finalize_unaffected_by_vg(tmp_path: Path):
    """§12.3 item 17: legacy v1 finalize must not call Vg, gain new fields, or
    change its rectangle stage_version behavior."""
    raw = {
        "schema_version": "1", "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"name": "1F", "z_floor": 0, "ceiling_height": 3,
                    "cells": [{"id": "room", "x": [0, 10], "y": [0, 8]}]}],
    }
    target = correction_target("rectangular")
    result = finalize_correction_draw(raw, vector_dir=tmp_path, target=target)
    assert result.geom.schema_version == "1"
    assert not hasattr(result.geom, "facade_segments")
    assert result.feature_state_claims.facade_segments == "not_declared"
    assert result.feature_state_claims.helper_versions == ()

    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    report = CheckReport(stage="1_correction", capability_profile="rectangular")
    rec = StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction", output_obj=result, report=report,
    )
    assert rec.accepted
    assert manifest.accepted("1_correction").stage_version == "2"
    assert manifest.accepted("1_correction").artifact_contract == "correction_b2_v1"


# --------------------------------------------------------------------------- #
# C2 Vg rework r1 (2026-07-12 cross-review VG-CR1/CR4): writer fail-closed
# tamper rejection, promoted-artifact + feature-sidecar parity, identity-
# snapshot call-order spy, and append-only accepted/blocked attempts.
# --------------------------------------------------------------------------- #
def test_writer_rejects_tampered_facade_segment_wire(tmp_path: Path):
    """VG-CR1 (HIGH): a caller that bypasses `finalize_correction_draw`'s own
    internal `validate_materialized_facade_segments` call — by tampering a
    real result via `model_copy` and re-deriving claims from the tampered
    geom before constructing a fresh `FinalizeResult` — must still be
    rejected at the `StageRunner.record()` writer boundary. This is exactly
    the review's reproduction: `depth` on the first segment mutated to
    `99.0`; `derive_feature_state_claims` alone (shape-only: non-empty +
    full floor coverage) does not catch it, so the writer must independently
    recompute the whole per-floor wire from the authoritative ring."""
    target = correction_target("orthogonal_polygon")
    result = finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)
    tampered_segments = list(result.geom.facade_segments)
    tampered_segments[0] = tampered_segments[0].model_copy(update={"depth": 99.0})
    tampered_geom = result.geom.model_copy(update={"facade_segments": tampered_segments})
    tampered_claims = derive_feature_state_claims(target, tampered_geom)
    tampered_result = FinalizeResult(
        geom=tampered_geom, audit_payload=result.audit_payload, feature_state_claims=tampered_claims,
    )

    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    report = CheckReport(stage="1_correction", capability_profile="orthogonal_polygon")
    with pytest.raises(Exception, match="visibility_wire_mismatch"):
        StageRunner(tmp_path, manifest).record(
            stage="1_correction", stage_dir=tmp_path / "1_correction",
            output_obj=tampered_result, report=report,
        )
    assert manifest.accepted("1_correction") is None
    # no attempt was promoted to accepted, and no audit/feature-state
    # sidecar was written for the rejected attempt.
    assert not (tmp_path / "1_correction" / "attempts" / "001" / "feature_states.json").exists()


def test_v3_finalize_parity_promoted_artifacts_and_feature_sidecar_hash(tmp_path: Path):
    """VG-CR4 (§12.3 item 15, promoted-artifact level): the integrated
    (producer dict payload) and stepwise (pre-parsed geom object) entry
    conventions must not just agree on the in-memory `FinalizeResult` (the
    pre-existing `test_v3_finalize_parity_dict_vs_parsed_geom_and_feature_state`
    above only checks that) — the bytes actually PROMOTED to each attempt's
    `output.json` / `feature_states.json` after `StageRunner.record()`, and
    the manifest's recorded artifact hashes for both, must match too."""
    target = correction_target("orthogonal_polygon")
    payload = _payload()

    dict_dir = tmp_path / "dict_path"
    geom_dir = tmp_path / "geom_path"
    dict_dir.mkdir()
    geom_dir.mkdir()

    result_from_dict = finalize_correction_draw(payload, vector_dir=dict_dir, target=target)
    parsed = parse_correction_draw(payload, target)
    result_from_geom = finalize_correction_draw(parsed, vector_dir=geom_dir, target=target)

    manifest_a = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    manifest_b = RunManifestV2(run_id="1" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    rec_a = StageRunner(dict_dir, manifest_a).record(
        stage="1_correction", stage_dir=dict_dir / "1_correction", output_obj=result_from_dict,
        report=CheckReport(stage="1_correction", capability_profile="orthogonal_polygon"),
    )
    rec_b = StageRunner(geom_dir, manifest_b).record(
        stage="1_correction", stage_dir=geom_dir / "1_correction", output_obj=result_from_geom,
        report=CheckReport(stage="1_correction", capability_profile="orthogonal_polygon"),
    )
    assert rec_a.accepted and rec_b.accepted

    attempt_a = Path(rec_a.attempt_dir)
    attempt_b = Path(rec_b.attempt_dir)
    assert (attempt_a / "output.json").read_text(encoding="utf-8") == (attempt_b / "output.json").read_text(encoding="utf-8")
    assert (attempt_a / "feature_states.json").read_text(encoding="utf-8") == (attempt_b / "feature_states.json").read_text(encoding="utf-8")

    stage_a = manifest_a.accepted("1_correction")
    stage_b = manifest_b.accepted("1_correction")
    assert stage_a.artifact_hashes["output"] == stage_b.artifact_hashes["output"]
    assert stage_a.artifact_hashes["feature_states"] == stage_b.artifact_hashes["feature_states"]
    assert stage_a.stage_version == stage_b.stage_version == "3"


def test_identity_snapshot_compare_happens_only_before_materialize_exactly_once(tmp_path: Path, monkeypatch):
    """VG-CR4 (§12.3 item 14, spy): §9.1's frozen ordering is
    snapshot -> core -> snapshot-compare -> materialize; this must hold as
    an observable fact, not just an absence of a post-materialize compare in
    the source. Spy on both `_identity_snapshot` and
    `materialize_all_facade_segments` and assert the call log is exactly
    ["snapshot", "snapshot", "materialize"] — two identity-snapshot calls
    (pre-core baseline + post-core compare), both strictly before the single
    materialize call, and none after."""
    import src.agent.correction.finalize as finalize_module

    call_log: list[str] = []
    real_snapshot = finalize_module._identity_snapshot
    real_materialize = finalize_module.materialize_all_facade_segments

    def _spy_snapshot(geom):
        call_log.append("snapshot")
        return real_snapshot(geom)

    def _spy_materialize(geom, *, tolerances):
        call_log.append("materialize")
        return real_materialize(geom, tolerances=tolerances)

    monkeypatch.setattr(finalize_module, "_identity_snapshot", _spy_snapshot)
    monkeypatch.setattr(finalize_module, "materialize_all_facade_segments", _spy_materialize)
    target = correction_target("orthogonal_polygon")
    finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)
    assert call_log == ["snapshot", "snapshot", "materialize"]


def test_append_only_second_attempt_blocked_downstream_still_bound_to_first(tmp_path: Path):
    """VG-CR4 (§12.3 item 16): a second, deliberately-blocked attempt must
    not overwrite or supersede the first accepted attempt — both attempt
    dirs persist (append-only), and the manifest's accepted pointer + output
    hash stay bound to attempt 001 throughout."""
    target = correction_target("orthogonal_polygon")
    result1 = finalize_correction_draw(_payload(), vector_dir=tmp_path, target=target)
    manifest = RunManifestV2(run_id="0" * 32, run_inputs=RunInputs(view_manifest_sha256="1" * 64))
    rec1 = StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction", output_obj=result1,
        report=CheckReport(stage="1_correction", capability_profile="orthogonal_polygon"),
    )
    assert rec1.accepted
    first_hash = manifest.accepted("1_correction").output_hash
    assert manifest.accepted("1_correction").accepted_attempt == 1

    result2 = finalize_correction_draw(
        _payload(ring=[[0, 0], [12, 0], [12, 8], [0, 8]]), vector_dir=tmp_path, target=target,
    )
    rec2 = StageRunner(tmp_path, manifest).record(
        stage="1_correction", stage_dir=tmp_path / "1_correction", output_obj=result2,
        report=CheckReport(stage="1_correction", capability_profile="orthogonal_polygon"),
        accept=False,
    )
    assert not rec2.accepted
    assert rec2.attempt_index == 2
    assert (tmp_path / "1_correction" / "attempts" / "001").is_dir()
    assert (tmp_path / "1_correction" / "attempts" / "002").is_dir()
    # append-only: attempt 001's own files are untouched by attempt 002.
    assert (tmp_path / "1_correction" / "attempts" / "001" / "output.json").read_text(encoding="utf-8") != \
        (tmp_path / "1_correction" / "attempts" / "002" / "output.json").read_text(encoding="utf-8")
    # downstream (the manifest's accepted pointer) is still bound to 001.
    accepted = manifest.accepted("1_correction")
    assert accepted.output_hash == first_hash
    assert accepted.accepted_attempt == 1
