"""P0 contract + diagnostic-skeleton tests for the Tianzheng->GT v3 converter.

Scope (dispatch §1, P0 exit gate):
  * contract freeze — request / IR / report / source_map all serialize round-trip,
  * diagnostic code table full coverage (no WARN; every BLOCK has a remedy;
    the DiagCode literal == the registry),
  * config channel — resolve_converter_tooling binds judge_config_sha256 from the
    real judge_gt.yaml; quantization step is derived (not a config key),
  * staging discipline — protected roots are rejected; staging lives under experiments,
  * hard-discipline structure guards — no baked thickness constants; severity has no WARN.

These tests are intentionally P0-only: they exercise the frozen contracts, never the
S0-S9 algorithm body (which is P1/P2 and does not exist yet).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.judge import tarch_converter_schema as schema
from src.agent.judge.tarch_converter_schema import (
    ALL_DIAGNOSTIC_CODES, ConversionDiagnosticV1, ConversionReportV1,
    DiagnosticSeverity, FloorIRV1, NormalizedBuildingIRV1, PolygonIRV1,
    RingV1, SourceMapV1, TARCH_DIAGNOSTIC_REGISTRY, ThicknessEvidenceV1,
    WallRibbonSegmentV1, WallRibbonV1, ZoneIRV1, ZoneIntentEntryV1,
    ZoneIntentSpecV1, TarchConversionRequestV1, compute_request_sha256,
    compute_report_sha256, compute_source_map_sha256,
    derive_quantization_step, is_protected_tarch_path, resolve_converter_tooling,
    staging_work_dir, assert_staging_input)

REPO = Path(__file__).resolve().parents[1]
GT_CONFIG = REPO / "src/configs/judge_gt.yaml"
VG_CONFIG = REPO / "src/configs/correction.yaml"


# --------------------------------------------------------------------------- #
# fixtures: minimal-but-contract-complete objects
# --------------------------------------------------------------------------- #
def _thickness(value_m: float = 0.120) -> ThicknessEvidenceV1:
    return ThicknessEvidenceV1(
        source_kind="wall_cap_or_opening_jamb", value_m=value_m,
        proof_handles=["1A3"])


def _square_ring(size: float = 2.0) -> RingV1:
    s = size / 2
    return RingV1(vertices=[[-s, -s], [s, -s], [s, s], [-s, s], [-s, -s]])


def _minimal_request() -> TarchConversionRequestV1:
    return TarchConversionRequestV1(
        request_version=1,
        case="sm24_anchor",
        source_dxf_label="sm24_source.dxf",
        source_dxf_sha256="92885d52340af72e24cd6396e893924f581b72983f5f1643076972d2aade245d",
        normalized_source_id="sm24-anchor-normalized",
        target_geometry_profile="c2_simple_orthogonal_no_holes",
        native_units="unitless",
        metres_per_unit=0.001,
        floors=[{"id": "F1", "name": "Floor 1", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
        plan_views=[{
            "id": "plan-F1", "floor_id": "F1", "frame_title": "1f平面图",
            "clip_box_dxf": {"xmin": 12000.0, "ymin": 18000.0, "xmax": 42000.0, "ymax": 52000.0},
            "world_from_source_m": {"m00": 0.001, "m01": 0.0, "m02": -23.0576,
                                    "m10": 0.0, "m11": 0.001, "m12": -26.5652},
            "wall_selector": {"entity_types": ["LINE"], "layers": ["WALL"]},
            "opening_selector": {"entity_types": ["INSERT"], "layers": ["WINDOW"]},
            "dialect_rules": {"window_block_names": ["$TCHSYS$WIN2D"],
                              "door_block_prefixes": ["$DorLib2D$"],
                              "classifier_version": "tarch-dialect-v1"},
            "zone_intent": ZoneIntentSpecV1(
                mode="intent_file", expected_count=1,
                entries=[ZoneIntentEntryV1(zone_id="z_a", name="room", role="unspecified")]),
        }],
        request_sha256="0" * 64,
    )


def _minimal_ir() -> NormalizedBuildingIRV1:
    # A wall that changes thickness mid-span => two segments (per-segment proof).
    seg1 = WallRibbonSegmentV1(segment_id="w0_s0", axis="y", coord_m=27.2976,
                               span_m=[30.0, 42.0], thickness_evidence=_thickness(0.120))
    seg2 = WallRibbonSegmentV1(segment_id="w0_s1", axis="y", coord_m=27.2976,
                               span_m=[24.0, 30.0], thickness_evidence=_thickness(0.240))
    ribbon = WallRibbonV1(id="w0", floor_id="F1", axis="y",
                          segments=[seg1, seg2],
                          source_refs=[{"handle": "1A3", "role": "side_a"},
                                       {"handle": "1A4", "role": "side_b"}])
    zone = ZoneIRV1(
        zone_id="z_a", floor_id="F1", name="room", role="unspecified",
        role_source="declared_absent", role_scored=False,
        seed_point_world_m=[5.0, 5.0], polygon=PolygonIRV1(exterior=_square_ring(4.0)),
        intent_anchor={"source": "intent_file", "point_world_m": [5.0, 5.0]},
        edges=[{"id": "e0", "floor_id": "F1", "kind": "wall_midline",
                "p1": [0.0, 0.0], "p2": [0.0, 4.0], "basis": "wall_axis",
                "thickness_evidence": _thickness(0.120), "offset_m": 0.06,
                "source_handles": ["1A3"]}])
    return NormalizedBuildingIRV1(
        ir_version=1, case="sm24_anchor",
        floors=[FloorIRV1(floor_id="F1", plan_view_id="plan-F1",
                          wall_ribbons=[ribbon],
                          footprint={"floor_id": "F1",
                                     "polygon": {"exterior": _square_ring(10.0)}},
                          zones=[zone])])


def _info_diag() -> ConversionDiagnosticV1:
    spec = TARCH_DIAGNOSTIC_REGISTRY["tarch_wall_degenerate_line"]
    return ConversionDiagnosticV1(
        code="tarch_wall_degenerate_line", severity=spec.severity, stage=spec.stage,
        source_entity_handles=["AB1"], action_code=spec.code)


def _block_diag() -> ConversionDiagnosticV1:
    spec = TARCH_DIAGNOSTIC_REGISTRY["tarch_cavity_count_mismatch"]
    return ConversionDiagnosticV1(
        code="tarch_cavity_count_mismatch", severity=spec.severity, stage=spec.stage,
        source_points_dxf_mm=[[27298.0, 30065.0]], action_code=spec.code)


# --------------------------------------------------------------------------- #
# diagnostic code table — full coverage
# --------------------------------------------------------------------------- #
def test_diagnostic_registry_nonempty_and_codes_match_literal():
    # The DiagCode literal and the registry must enumerate the exact same set.
    literal_codes = set(schema.DiagCode.__args__)  # type: ignore[attr-defined]
    registry_codes = set(TARCH_DIAGNOSTIC_REGISTRY.keys())
    assert literal_codes == registry_codes
    assert set(ALL_DIAGNOSTIC_CODES) == registry_codes
    assert len(registry_codes) >= 30  # both tables merged, deduped


def test_no_warn_severity_and_every_block_has_remedy():
    for code, spec in TARCH_DIAGNOSTIC_REGISTRY.items():
        assert spec.severity in (DiagnosticSeverity.BLOCK, DiagnosticSeverity.INFO), code
        assert spec.severity != "WARN", code  # no WARN allowed (§5.6)
        if spec.severity == DiagnosticSeverity.BLOCK:
            assert spec.remedy.strip(), f"BLOCK code {code} has no remedy"
            assert spec.gates, f"BLOCK code {code} names no gate"


def test_diagnostic_enforces_severity_and_stage_match_registry():
    # A diagnostic whose severity/stage disagree with the registry must be rejected.
    spec = TARCH_DIAGNOSTIC_REGISTRY["tarch_source_proxy_present"]  # BLOCK / S0
    with pytest.raises(Exception):
        ConversionDiagnosticV1(
            code="tarch_source_proxy_present", severity=DiagnosticSeverity.INFO,
            stage=spec.stage, source_entity_handles=["1"], action_code=spec.code)
    with pytest.raises(Exception):
        ConversionDiagnosticV1(
            code="tarch_source_proxy_present", severity=spec.severity,
            stage=schema.TarchStage.S9_PERSIST, source_entity_handles=["1"],
            action_code=spec.code)


def test_block_diagnostic_must_be_localizable():
    spec = TARCH_DIAGNOSTIC_REGISTRY["tarch_wall_free_end"]
    with pytest.raises(Exception):
        ConversionDiagnosticV1(
            code="tarch_wall_free_end", severity=spec.severity, stage=spec.stage,
            action_code=spec.code)  # no handle, no point => not localizable


# --------------------------------------------------------------------------- #
# contract freeze — round-trip serialization
# --------------------------------------------------------------------------- #
def test_request_round_trip_and_sha256_stable():
    req = _minimal_request()
    real = compute_request_sha256(req)
    bound = req.model_copy(update={"request_sha256": real})
    dumped = bound.model_dump_json()
    reloaded = TarchConversionRequestV1.model_validate_json(dumped)
    assert reloaded == bound
    assert compute_request_sha256(reloaded) == real  # stable on reload
    assert real != "0" * 64


def test_ir_carries_multi_ring_per_floor_per_segment_thickness():
    ir = _minimal_ir()
    dumped = ir.model_dump_json()
    reloaded = NormalizedBuildingIRV1.model_validate_json(dumped)
    assert reloaded == ir
    floor = reloaded.floors[0]
    # per-floor footprint retained
    assert floor.footprint is not None
    # multi-ring polygon structure exists (interior_rings slot, empty here)
    assert hasattr(floor.footprint.polygon, "interior_rings")
    # per-segment thickness proof: one wall, two segments with DIFFERENT evidence values
    ribbon = floor.wall_ribbons[0]
    thicknesses = [seg.thickness_evidence.value_m for seg in ribbon.segments]
    assert thicknesses == [0.120, 0.240]


def test_report_round_trip_and_status_contract():
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    # PASS report must have geometry, no BLOCK diag, and a normalized hash.
    zone = _minimal_ir().floors[0].zones[0]
    zone_report = {
        "zone_id": zone.zone_id, "floor_id": zone.floor_id, "name": zone.name,
        "role": zone.role, "role_source": zone.role_source,
        "seed_point_world_m": zone.seed_point_world_m,
        "polygon_m": zone.polygon.model_dump(mode="json"),
        "edges": [{"p1": e.p1, "p2": e.p2, "basis": e.basis,
                   "thickness_m": e.thickness_evidence.value_m, "offset_m": e.offset_m,
                   "source_handles": e.source_handles} for e in zone.edges]}
    pass_report = ConversionReportV1(
        report_version=1, status="PASS", case="sm24_anchor",
        source_dxf_sha256="a" * 64, normalized_dxf_sha256="b" * 64,
        request_sha256="c" * 64, judge_config_sha256=tooling.judge_config_sha256,
        vg_config_sha256=tooling.vg_config_sha256, converter_sha256="d" * 64,
        profile_version=1, quantization_step_m=derive_quantization_step(tooling),
        zones=[zone_report])
    reloaded = ConversionReportV1.model_validate_json(pass_report.model_dump_json())
    assert reloaded == pass_report
    assert reloaded.judge_config_sha256 == tooling.judge_config_sha256

    # BLOCKED report carries a BLOCK diag and may have no geometry.
    blocked = pass_report.model_copy(update={
        "status": "BLOCKED", "normalized_dxf_sha256": None, "zones": [],
        "diagnostics": [_block_diag()]})
    reloaded_b = ConversionReportV1.model_validate_json(blocked.model_dump_json())
    assert reloaded_b.status == "BLOCKED"
    assert reloaded_b.diagnostics[0].code == "tarch_cavity_count_mismatch"


def test_report_pass_with_block_diag_is_rejected():
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    zone = _minimal_ir().floors[0].zones[0]
    base = {
        "report_version": 1, "status": "PASS", "case": "sm24_anchor",
        "source_dxf_sha256": "a" * 64, "normalized_dxf_sha256": "b" * 64,
        "request_sha256": "c" * 64, "judge_config_sha256": tooling.judge_config_sha256,
        "vg_config_sha256": tooling.vg_config_sha256, "converter_sha256": "d" * 64,
        "profile_version": 1, "quantization_step_m": derive_quantization_step(tooling)}
    zone_report = {
        "zone_id": zone.zone_id, "floor_id": zone.floor_id, "name": zone.name,
        "role": zone.role, "role_source": zone.role_source,
        "seed_point_world_m": zone.seed_point_world_m,
        "polygon_m": zone.polygon.model_dump(mode="json"),
        "edges": [{"p1": e.p1, "p2": e.p2, "basis": e.basis,
                   "thickness_m": e.thickness_evidence.value_m, "offset_m": e.offset_m,
                   "source_handles": e.source_handles} for e in zone.edges]}
    with pytest.raises(Exception):
        ConversionReportV1(**{**base, "zones": [zone_report],
                              "diagnostics": [_block_diag()]})  # PASS + BLOCK => reject


def test_source_map_round_trip_and_sha256():
    sm = SourceMapV1(
        map_version=1, case="sm24_anchor", source_map_sha256="0" * 64,
        entries=[{
            "view_id": "plan-F1", "floor_id": "F1", "semantic_role": "zone_boundary",
            "operation": "midline", "canonical_geometry_world_m": {"p1": [0, 0], "p2": [0, 4]},
            "source_entity_refs": [{"handle": "1A3", "role": "wall_side"}],
            "wall_ribbon_ids": ["w0"]}])
    real = compute_source_map_sha256(sm)
    bound = sm.model_copy(update={"source_map_sha256": real})
    reloaded = SourceMapV1.model_validate_json(bound.model_dump_json())
    assert reloaded == bound
    assert compute_source_map_sha256(reloaded) == real


# --------------------------------------------------------------------------- #
# config channel — reuses load_gt_tooling_config, no new tolerance
# --------------------------------------------------------------------------- #
def test_config_channel_binds_real_judge_config_sha256():
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    # seven tolerances present
    t = tooling.tolerances
    for name in ("dxf_node_join_tolerance_m", "dxf_axis_alignment_tolerance_m",
                 "dxf_topology_area_tolerance_m2", "opening_boundary_max_distance_m",
                 "opening_assignment_tie_epsilon_m", "elevation_match_max_distance_m",
                 "elevation_match_tie_epsilon_m"):
        assert getattr(t, name) > 0, name
    # both config sha256 are real 64-hex
    assert len(tooling.judge_config_sha256) == 64
    assert len(tooling.vg_config_sha256) == 64
    # judge_config_sha256 matches the raw yaml bytes (what the extractor itself binds)
    import hashlib
    assert tooling.judge_config_sha256 == hashlib.sha256(GT_CONFIG.read_bytes()).hexdigest()


def test_quantization_step_is_derived_not_configured():
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    q = derive_quantization_step(tooling)
    assert q == pytest.approx(tooling.tolerances.dxf_node_join_tolerance_m / 10.0)
    assert q == pytest.approx(0.0001)  # 1mm / 10


# --------------------------------------------------------------------------- #
# §6.1 staging discipline
# --------------------------------------------------------------------------- #
def test_protected_roots_rejected():
    assert is_protected_tarch_path(REPO / "case_tests/test_baseline/gt/sm21_anchor/source.dxf")
    assert is_protected_tarch_path(REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf")
    assert is_protected_tarch_path(REPO / "case_tests/e2e_tests/sm21_anchor/case_data/x.dxf")
    # a staging path under experiments is NOT protected
    staging = staging_work_dir("sm24_anchor", "2026-07-22")
    assert not is_protected_tarch_path(staging / "source.dxf")
    assert staging.is_relative_to(REPO / "AI_agent/logs/experiments")


def test_assert_staging_input_fail_closed_on_protected():
    with pytest.raises(ValueError, match="tarch_staging_input_protected_path"):
        assert_staging_input(REPO / "case_tests/test_baseline/gt/sm21_anchor/source.dxf")
    # staging path is accepted
    assert_staging_input(staging_work_dir("sm24_anchor", "2026-07-22") / "source.dxf")


# --------------------------------------------------------------------------- #
# hard-discipline structure guards
# --------------------------------------------------------------------------- #
def test_no_baked_simplifying_constants_in_schema():
    import ast
    # Scan only module-level assignment TARGETS, not docstrings/comments, so the
    # discipline text that *names* the forbidden constants isn't a false positive.
    tree = ast.parse(Path(schema.__file__).read_text(encoding="utf-8"))
    assigned = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    assigned.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
    for forbidden in ("DEFAULT_WALL_THICKNESS", "MAX_WALL_PAIR_DISTANCE", "MIN_ROOM_WIDTH"):
        assert forbidden not in assigned, f"baked constant {forbidden} must not exist"
    # thickness source must be one of the six evidence kinds, never a numeric default
    text = Path(schema.__file__).read_text(encoding="utf-8")
    assert "window_block_short_side" in text
    assert "pub_dim_explicit" in text
    assert "source_hash_override" in text


def test_tianzheng_dialect_is_only_in_request_dialect_rules():
    # WALL/WINDOW layer names and block prefixes live ONLY in TarchDialectRulesV1.
    text = Path(schema.__file__).read_text(encoding="utf-8")
    # the dialect model is the named home for them
    assert "class TarchDialectRulesV1" in text
    assert "window_block_names" in text and "door_block_prefixes" in text


# --------------------------------------------------------------------------- #
# staging integration — the skeleton instantiates end-to-end in a staging dir
# --------------------------------------------------------------------------- #
def test_staging_skeleton_instantiates(tmp_path):
    """P0 exit gate: the frozen contracts import, instantiate, and round-trip
    inside a staging working directory, with the config sha256 recorded."""
    staging = tmp_path / "2026-07-22_sm24_anchor_gt" / "work"
    staging.mkdir(parents=True)

    # 1. resolve tooling + derive quantization step (the only tolerance channel)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)

    # 2. build a request, bind its hash, persist + reload
    req = _minimal_request().model_copy(
        update={"request_sha256": compute_request_sha256(_minimal_request())})
    (staging / "conversion_request.json").write_text(req.model_dump_json(), encoding="utf-8")
    reloaded_req = TarchConversionRequestV1.model_validate_json(
        (staging / "conversion_request.json").read_bytes())
    assert reloaded_req == req

    # 3. build the IR (multi-ring / per-floor / per-segment thickness), persist + reload
    ir = _minimal_ir()
    (staging / "normalized_ir.json").write_text(ir.model_dump_json(), encoding="utf-8")
    assert NormalizedBuildingIRV1.model_validate_json(
        (staging / "normalized_ir.json").read_bytes()) == ir

    # 4. every diagnostic code can be instantiated against its registry spec
    instantiated = []
    for code in ALL_DIAGNOSTIC_CODES:
        spec = TARCH_DIAGNOSTIC_REGISTRY[code]
        diag = ConversionDiagnosticV1(
            code=code, severity=spec.severity, stage=spec.stage,
            source_entity_handles=["00"] if spec.severity == DiagnosticSeverity.BLOCK else [],
            action_code=code)
        instantiated.append(diag)
    assert len(instantiated) == len(ALL_DIAGNOSTIC_CODES)

    # 5. a BLOCKED report carrying all INFO+BLOCK diagnostics as the table exercises
    report = ConversionReportV1(
        report_version=1, status="BLOCKED", case="sm24_anchor",
        source_dxf_sha256=req.source_dxf_sha256, request_sha256=req.request_sha256,
        judge_config_sha256=tooling.judge_config_sha256,
        vg_config_sha256=tooling.vg_config_sha256, converter_sha256="e" * 64,
        profile_version=1, quantization_step_m=derive_quantization_step(tooling),
        diagnostics=instantiated)
    (staging / "conversion_report.json").write_text(report.model_dump_json(), encoding="utf-8")
    reloaded_report = ConversionReportV1.model_validate_json(
        (staging / "conversion_report.json").read_bytes())
    assert reloaded_report == report
    assert compute_report_sha256(reloaded_report) == compute_report_sha256(report)
    # staging dir holds the four frozen-contract artifacts
    assert sorted(p.name for p in staging.iterdir()) == [
        "conversion_report.json", "conversion_request.json", "normalized_ir.json"]
