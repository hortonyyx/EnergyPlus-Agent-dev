"""P1 algorithm-body tests for the Tianzheng->GT v3 converter (S0-S4).

Scope (dispatch §1, P1 exit gate):
  * sm24 real-drawing end-to-end — the exit gate numbers are INDEPENDENTLY derived
    by running this implementation (never copied from probes/ as an unverified
    expectation).  They are then cross-checked against the probe targets; a
    mismatch would have stopped the work (brief §2 hard-discipline #7).
  * a synthetic green fixture (one room, one window) closes topology cleanly.
  * a RED fixture for every fail branch wired in P1 (S0/S1/S3/S4), each asserting
    the exact diagnostic code fires (no false-green — discipline #5).
  * determinism (same bytes -> same product).
  * the report contract exercises end-to-end (PASS/BLOCKED, round-trip).

P1 wires these fail branches: tarch_source_proxy_present, tarch_units_undeclared,
tarch_view_frame_missing, tarch_view_frame_ambiguous, tarch_entity_unsupported,
tarch_wall_nonorthogonal, tarch_quantization_conflict, tarch_opening_block_unresolved,
tarch_opening_block_ambiguous, tarch_opening_kind_ambiguous, tarch_wall_free_end,
tarch_topology_residual.  (S2 ribbon-accounting rigor and the S3 geometric-
continuation witness codes are P2 — see delivery note.)
"""
from __future__ import annotations

import dataclasses
import hashlib
import math
import shutil
from pathlib import Path
from types import SimpleNamespace

import ezdxf
import pytest

from src.agent.judge import tarch_normalize as tn
from src.agent.judge.tarch_converter_schema import (
    PlanViewIntentV1, TarchConversionRequestV1, TarchDialectRulesV1,
    TarchEntitySelectorV1, ZoneIntentEntryV1, ZoneIntentSpecV1,
    ConversionReportV1, ConversionDiagnosticV1, DiagnosticSeverity,
    compute_request_sha256, resolve_converter_tooling)

REPO = Path(__file__).resolve().parents[1]
GT_CONFIG = REPO / "src/configs/judge_gt.yaml"
VG_CONFIG = REPO / "src/configs/correction.yaml"
SM24_SOURCE = REPO / "case_tests/test_baseline/gt_sources/sm24_anchor/source.dxf"

WINDOW_BLOCK = "$TCHSYS$WIN2D"
DOOR_BLOCK = "$DorLib2D$00000001"


# --------------------------------------------------------------------------- #
# synthetic-DXF builder (one room, one window on the north wall) + failure knobs
# --------------------------------------------------------------------------- #
def _make_dxf(path: Path, *, window_block: str = WINDOW_BLOCK,
              no_caps: bool = False, ambiguous: bool = False, unknown_block: bool = False,
              diagonal: bool = False, circle_in_wall: bool = False, free_end: bool = False,
              extra_title: bool = False, no_title: bool = False,
              insunits: int = 0) -> None:
    """Write a minimal Tianzheng-style DXF.  Default = clean green (1 window)."""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    W = "WALL"
    # outer skin (1000,1000)-(5000,7000), inner (1240,1240)-(4760,6760), thickness 240
    msp.add_line((1000, 7000), (2000, 7000), dxfattribs={"layer": W})   # north outer (gap at window)
    msp.add_line((3000, 7000), (5000, 7000), dxfattribs={"layer": W})
    msp.add_line((1240, 6760), (2000, 6760), dxfattribs={"layer": W})   # north inner
    msp.add_line((3000, 6760), (4760, 6760), dxfattribs={"layer": W})
    msp.add_line((1000, 1000), (5000, 1000), dxfattribs={"layer": W})   # south
    msp.add_line((1240, 1240), (4760, 1240), dxfattribs={"layer": W})
    msp.add_line((5000, 1000), (5000, 7000), dxfattribs={"layer": W})   # east
    msp.add_line((4760, 1240), (4760, 6760), dxfattribs={"layer": W})
    msp.add_line((1000, 1000), (1000, 7000), dxfattribs={"layer": W})   # west
    msp.add_line((1240, 1240), (1240, 6760), dxfattribs={"layer": W})
    if not no_caps:
        msp.add_line((2000, 6760), (2000, 7000), dxfattribs={"layer": W})  # jamb caps
        msp.add_line((3000, 6760), (3000, 7000), dxfattribs={"layer": W})
    if ambiguous:
        # TWO stacked horizontal wall bands (y 3000..3240 and y 4000..4240), each
        # with caps at x=2000 and x=3000.  The block's normal range overlaps both
        # => two candidate jamb-cap pairs => opening_block_ambiguous.
        for ylo, yhi in ((3000, 3240), (4000, 4240)):
            msp.add_line((2000, ylo), (2000, yhi), dxfattribs={"layer": W})
            msp.add_line((3000, ylo), (3000, yhi), dxfattribs={"layer": W})
            msp.add_line((2000, ylo), (3000, ylo), dxfattribs={"layer": W})
            msp.add_line((2000, yhi), (3000, yhi), dxfattribs={"layer": W})
    if diagonal:
        msp.add_line((2000, 3000), (3000, 4000), dxfattribs={"layer": W})  # non-axis-parallel
    if circle_in_wall:
        msp.add_circle((3000, 3000), radius=500, dxfattribs={"layer": W})
    if free_end:
        msp.add_line((2000, 3000), (2000, 4000), dxfattribs={"layer": W})  # stub -> dangle
    # opening block
    if ambiguous:
        name, geom, insert = window_block, [(0, 0), (1000, 1240)], (2000, 3000)  # spans both bands
    elif unknown_block:
        name, geom, insert = "$Furniture$0001", [(0, 0), (1000, 240)], (2000, 6760)
    else:
        name, geom, insert = window_block, [(0, 0), (1000, 240)], (2000, 6760)
    if name not in doc.blocks:
        blk = doc.blocks.new(name=name)
        blk.add_line(geom[0], geom[1])
    msp.add_blockref(name, insert=insert, dxfattribs={"layer": "WINDOW"})
    # edge frame + title
    msp.add_lwpolyline([(200, 200), (5800, 200), (5800, 7800), (200, 7800)],
                       dxfattribs={"layer": "edge"}, close=True)
    if not no_title:
        msp.add_text("test1f", dxfattribs={"layer": "0", "insert": (3000, 4000), "height": 200})
    if extra_title:
        msp.add_text("dup", dxfattribs={"layer": "0", "insert": (3500, 4500), "height": 200})
    doc.saveas(str(path))


def _request(case: str, sha: str, clip: dict, frame_title: str = "test1f",
             native_units: str = "unitless", metres_per_unit: float = 0.001,
             expected_count: int = 1) -> tuple[TarchConversionRequestV1, PlanViewIntentV1]:
    # dxf_native -> world_metre, so the linear part IS the declared native scale.
    # Derived rather than hard-coded at 0.001 because one caller below declares
    # metres_per_unit=0.01: the affine two-end magnitude gate (B4-(2)a) rejects a
    # request whose coefficients contradict its own metres_per_unit, and that
    # caller's intended defect is a units *label* mismatch, not a bad affine.
    aff = {"m00": metres_per_unit, "m01": 0.0, "m02": -1.0,
           "m10": 0.0, "m11": metres_per_unit, "m12": -1.0}
    pv = PlanViewIntentV1(
        id="plan-F1", floor_id="F1", frame_title=frame_title, clip_box_dxf=clip,
        world_from_source_m=aff,
        wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
        opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
        dialect_rules=TarchDialectRulesV1(window_block_names=[WINDOW_BLOCK],
                                          door_block_prefixes=["$DorLib2D$"], classifier_version="v1"),
        zone_intent=ZoneIntentSpecV1(
            mode="intent_file", expected_count=expected_count,
            entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified")
                     for i in range(expected_count)]))
    req = TarchConversionRequestV1(
        request_version=1, case=case, source_dxf_label="src.dxf", source_dxf_sha256=sha,
        normalized_source_id=f"{case}-norm", target_geometry_profile="c2_simple_orthogonal_no_holes",
        native_units=native_units, metres_per_unit=metres_per_unit,
        floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
        plan_views=[pv], request_sha256="0" * 64)
    req = req.model_copy(update={"request_sha256": compute_request_sha256(req)})
    return req, pv


def _run(path: Path, **req_kw):
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    req, pv = _request("case", sha, clip={"xmin": 200, "ymin": 200, "xmax": 5800, "ymax": 7800}, **req_kw)
    return tn.run_p1_plan_view(path, req, pv, tooling), req, pv, tooling, sha


def _codes(res) -> set[str]:
    return {d.code for d in res.diagnostics}


# --------------------------------------------------------------------------- #
# sm24 real-drawing end-to-end — THE P1 EXIT GATE (independently derived)
# --------------------------------------------------------------------------- #
def _sm24_request(sha: str):
    aff = {"m00": 0.001, "m01": 0.0, "m02": -23.0576, "m10": 0.0, "m11": 0.001, "m12": -26.5652}
    clip = {"xmin": 12276.94, "ymin": 18802.14, "xmax": 41994.33, "ymax": 51678.57}
    pv = PlanViewIntentV1(
        id="plan-F1", floor_id="F1", frame_title="1f平面图", clip_box_dxf=clip, world_from_source_m=aff,
        wall_selector=TarchEntitySelectorV1(entity_types=["LINE"], layers=["WALL"]),
        opening_selector=TarchEntitySelectorV1(entity_types=["INSERT"], layers=["WINDOW"]),
        dialect_rules=TarchDialectRulesV1(window_block_names=[WINDOW_BLOCK],
                                          door_block_prefixes=["$DorLib2D$"], classifier_version="tarch-dialect-v1"),
        zone_intent=ZoneIntentSpecV1(
            mode="intent_file", expected_count=8,
            entries=[ZoneIntentEntryV1(zone_id=f"z{i}", name=f"r{i}", role="unspecified") for i in range(8)]))
    req = TarchConversionRequestV1(
        request_version=1, case="sm24_anchor", source_dxf_label="sm24_source.dxf", source_dxf_sha256=sha,
        normalized_source_id="sm24-anchor-normalized",
        target_geometry_profile="c2_simple_orthogonal_no_holes", native_units="unitless",
        metres_per_unit=0.001, floors=[{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": 4.5}],
        plan_views=[pv], request_sha256="0" * 64)
    return req.model_copy(update={"request_sha256": compute_request_sha256(req)}), pv


def test_sm24_exit_gate_openings_21_and_topology_clean(tmp_path):
    """P1 exit gate (brief §2): sm24 openings 21/21 + dangles/cuts/invalid=0 +
    sum_area == footprint.  Numbers below are THIS implementation's independent
    output, cross-checked against the probe targets (brief #7)."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p1_plan_view(dst, req, pv, tooling)

    # --- S1/S2 independently derived counts (cross-checked vs probes 0/132, 34/39) ---
    assert res.degenerate_line_count == 0
    assert len(res.wall_lines) == 132
    assert sum(len(v) for v in res.jamb_caps_v.values()) == 34
    assert sum(len(v) for v in res.jamb_caps_h.values()) == 39

    # --- S3: 21/21 openings resolved (11 windows + 10 doors), zero unresolved ---
    assert len(res.openings) == 21
    kinds = {o.kind for o in res.openings}
    assert sum(1 for o in res.openings if o.kind == "window") == 11
    assert sum(1 for o in res.openings if o.kind == "door") == 10
    assert not any(c.startswith("tarch_opening_block_unresolved") for c in _codes(res))
    assert not any(c.startswith("tarch_opening_block_ambiguous") for c in _codes(res))

    # --- D5 split: 14 exterior + 7 interior (cross-checked vs probes/SURVEY) ---
    exterior = sum(1 for o in res.openings if o.classification == "exterior")
    interior = sum(1 for o in res.openings if o.classification == "interior_excluded")
    assert exterior == 14 and interior == 7

    # --- S4: three-zero residual + area conservation (cross-checked: 51 faces, 200.0 m²) ---
    assert res.dangles == 0 and res.cuts == 0 and res.invalid == 0
    assert len(res.faces) == 51
    assert res.sum_area_m2 == pytest.approx(200.0, abs=1e-6)
    assert res.footprint_area_m2 == pytest.approx(200.0, abs=1e-6)
    assert abs(res.sum_area_m2 - res.footprint_area_m2) <= 1e-6

    # --- all P1 gates green, no BLOCK diagnostic, PASS report ---
    assert all(g.passed for g in res.gates)
    assert not res.has_block
    report = tn.build_p1_report(res, req, pv, tooling, sha)
    assert report.status == "PASS"
    assert len(report.openings) == 21


def test_sm24_door_opening_excludes_swing_arc(tmp_path):
    """D2: a door block bbox contains the swing arc and overflows the wall; the
    resolved rect must be the wall-cross-section rectangle, NOT the block bbox."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    res = tn.run_p1_plan_view(dst, req, pv, tooling)
    ac3 = next(o for o in res.openings if o.handle == "AC3")   # north exterior door
    # rect must lie within the 240-thick north wall (y in [46325.2, 46565.2]),
    # never the block's 780-mm-tall swing bbox (which reaches y=47225.2).
    x0, y0, x1, y1 = ac3.rect_dxf_mm
    assert 46325.2 - 1 <= y0 and y1 <= 46565.2 + 1
    assert (y1 - y0) == pytest.approx(240.0, abs=1)
    assert y1 < 47225.2


def test_sm24_deterministic(tmp_path):
    """Same bytes -> identical openings (sorted) and diagnostic set."""
    dst = tmp_path / "source.dxf"
    shutil.copyfile(SM24_SOURCE, dst)
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    req, pv = _sm24_request(sha)
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    r1 = tn.run_p1_plan_view(dst, req, pv, tooling)
    r2 = tn.run_p1_plan_view(dst, req, pv, tooling)
    a = [(o.handle, o.kind, o.rect_dxf_mm, o.classification) for o in r1.openings]
    b = [(o.handle, o.kind, o.rect_dxf_mm, o.classification) for o in r2.openings]
    assert a == b
    assert _codes(r1) == _codes(r2)
    assert [g.evidence for g in r1.gates] == [g.evidence for g in r2.gates]


# --------------------------------------------------------------------------- #
# synthetic green fixture
# --------------------------------------------------------------------------- #
def test_synthetic_green_one_window_closes(tmp_path):
    path = tmp_path / "green.dxf"
    _make_dxf(path)
    res, *_ = _run(path)
    assert len(res.openings) == 1
    assert res.openings[0].rect_dxf_mm == (2000.0, 6760.0, 3000.0, 7000.0)
    assert res.openings[0].kind == "window"
    assert res.dangles == 0 and res.cuts == 0 and res.invalid == 0
    assert res.sum_area_m2 == pytest.approx(24.0, abs=1e-6)     # 4000x6000 mm building
    assert all(g.passed for g in res.gates)
    assert not res.has_block


# --------------------------------------------------------------------------- #
# S0 red fixtures
# --------------------------------------------------------------------------- #
def test_s0_view_frame_ambiguous_two_titles(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, extra_title=True)
    res, *_ = _run(path)
    assert "tarch_view_frame_ambiguous" in _codes(res)
    assert res.has_block


def test_s0_view_frame_ambiguous_zero_titles(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, no_title=True)
    res, *_ = _run(path)
    assert "tarch_view_frame_ambiguous" in _codes(res)
    assert res.has_block


def test_s0_view_frame_missing(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path)
    # request a clip box that matches NO closed frame polyline
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    req, pv = _request("c", sha, clip={"xmin": 90000, "ymin": 90000, "xmax": 95000, "ymax": 95000})
    res = tn.run_p1_plan_view(path, req, pv, tooling)
    assert "tarch_view_frame_missing" in _codes(res)
    assert res.has_block


def test_s0_entity_unsupported_circle_in_wall(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, circle_in_wall=True)
    res, *_ = _run(path)
    assert "tarch_entity_unsupported" in _codes(res)


def test_s0_units_undeclared_on_scale_mismatch(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, insunits=4)   # 4 = mm, non-unitless header
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    # request declares mm but gives a cm scale -> mismatch
    req, pv = _request("c", sha, clip={"xmin": 200, "ymin": 200, "xmax": 5800, "ymax": 7800},
                       native_units="mm", metres_per_unit=0.01)
    res = tn.run_p1_plan_view(path, req, pv, tooling)
    assert "tarch_units_undeclared" in _codes(res)


def test_s0_proxy_count_predicate():
    class _E:
        def __init__(self, t): self._t = t
        def dxftype(self): return self._t
    assert tn._proxy_count([_E("LINE"), _E("CIRCLE")]) == 0
    assert tn._proxy_count([_E("LINE"), _E("ACAD_PROXY_ENTITY")]) == 1


# --------------------------------------------------------------------------- #
# S1 red fixtures
# --------------------------------------------------------------------------- #
def test_s1_wall_nonorthogonal_rejected(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, diagonal=True)
    res, *_ = _run(path)
    assert "tarch_wall_nonorthogonal" in _codes(res)


def test_s1_quantization_conflict_unit():
    """G2 guard: two coords > tau_node apart must not collapse to one grid point.
    q = tau_node/10 makes this impossible for sane drawings; this asserts the
    guard fires when handed an abnormal (synthetic) source table."""
    collect = tn._WallCollect(
        wall_lines=[], degenerate=0, caps_v={}, caps_h={},
        cap_handles_v={}, cap_handles_h={}, all_handles=set(),
        source_x={0.0: [0.0, 2.0]}, source_y={})    # 2mm gap collapsed to grid 0.0
    diags: list[ConversionDiagnosticV1] = []
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    tols = tn._tols_from(tooling, 0.001)
    ok = tn._g2_conservation(collect, tols, diags)
    assert not ok
    assert any(d.code == "tarch_quantization_conflict" for d in diags)


def test_s1_degenerate_line_is_info_not_block(tmp_path):
    """A zero-length wall line is bookkept INFO (D3), never a BLOCK."""
    path = tmp_path / "a.dxf"; _make_dxf(path)
    # inject a zero-length line on the WALL layer
    doc = ezdxf.readfile(str(path)); msp = doc.modelspace()
    msp.add_line((2500, 2500), (2500, 2500), dxfattribs={"layer": "WALL"})
    doc.saveas(str(path))
    res, *_ = _run(path)
    deg = [d for d in res.diagnostics if d.code == "tarch_wall_degenerate_line"]
    assert len(deg) == 1
    assert deg[0].severity == DiagnosticSeverity.INFO


# --------------------------------------------------------------------------- #
# S3 red fixtures
# --------------------------------------------------------------------------- #
def test_s3_opening_unresolved_no_caps(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, no_caps=True)
    res, *_ = _run(path)
    assert "tarch_opening_block_unresolved" in _codes(res)


def test_s3_opening_ambiguous_two_bands(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, ambiguous=True)
    res, *_ = _run(path)
    assert "tarch_opening_block_ambiguous" in _codes(res)


def test_s3_opening_kind_ambiguous_unknown_block(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, unknown_block=True)
    res, *_ = _run(path)
    assert "tarch_opening_kind_ambiguous" in _codes(res)


# --------------------------------------------------------------------------- #
# S4 red fixtures
# --------------------------------------------------------------------------- #
def test_s4_wall_free_end_dangle(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, free_end=True)
    res, *_ = _run(path)
    assert res.dangles > 0
    assert "tarch_wall_free_end" in _codes(res)
    assert any(g.id == "G5" and not g.passed for g in res.gates)


def test_s4_topology_residual_area_mismatch_unit():
    """The area-mismatch branch of tarch_topology_residual (a guard: a clean
    polygonize cannot mismatch, so exercise it with a crafted residual)."""
    diags: list[ConversionDiagnosticV1] = []
    tooling = resolve_converter_tooling(GT_CONFIG, VG_CONFIG)
    tols = tn._tols_from(tooling, 0.001)
    from shapely.geometry import Polygon
    s4 = {"faces": [], "dangles": [], "cuts": [], "invalid": [],
          "n_dangles": 0, "n_cuts": 0, "n_invalid": 0,
          "sum_area_m2": 200.0, "footprint_area_m2": 100.0,
          "footprint": Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])}
    tn._emit_s4_diagnostics(s4, tols, diags)
    assert any(d.code == "tarch_topology_residual" and d.context.get("delta_m2", 0) > 1.0
               for d in diags)


def test_nonconvex_footprint_classifies_reentrant_outer_opening_locally():
    """An exterior opening on a concave arm cannot use one global interior point."""
    footprint = tn.Polygon([
        (0, 0), (10000, 0), (10000, 4000), (4000, 4000),
        (4000, 8000), (10000, 8000), (10000, 12000), (0, 12000),
    ])
    opening = tn.ResolvedOpening(
        handle="15D9", block_name="$TCHSYS$WIN2D", kind="window",
        rect_dxf_mm=(6000, 3760, 8000, 4000), axis="x",
        cross_section_mm=(3760, 4000), jamb_handles=["J1", "J2"])
    rep = footprint.representative_point()
    assert rep.y > 4000  # old global-point rule chooses the wrong (lower) face
    assert footprint.exterior.distance(tn.Point(7000, 3760)) == pytest.approx(240.0)
    assert footprint.exterior.distance(tn.Point(7000, 4000)) == pytest.approx(0.0)

    diags = []
    tn._classify_openings(
        [opening], footprint, tn._tols_from(resolve_converter_tooling(GT_CONFIG, VG_CONFIG), 0.001), diags)
    assert opening.classification == "exterior"
    assert not diags


# --------------------------------------------------------------------------- #
# report contract
# --------------------------------------------------------------------------- #
def test_report_pass_on_green_and_round_trip(tmp_path):
    path = tmp_path / "green.dxf"; _make_dxf(path)
    res, req, pv, tooling, sha = _run(path)
    report = tn.build_p1_report(res, req, pv, tooling, sha)
    assert report.status == "PASS"
    assert report.normalized_dxf_sha256 == sha   # source-bound until P2 (disclosed)
    reloaded = ConversionReportV1.model_validate_json(report.model_dump_json())
    assert reloaded == report
    # every wall band carries cap-derived thickness evidence (kind #2)
    for w in report.walls:
        assert w.segments[0].thickness_evidence.source_kind == "wall_cap_or_opening_jamb"
    # openings carry their jamb-cap proof handles
    for o in report.openings:
        assert o.jamb_handles


def test_report_wall_units_follow_declared_metres_per_unit(tmp_path):
    """HC-02: P1 report ribbons follow native-unit scale, not a baked-in mm scale."""
    path = tmp_path / "green.dxf"; _make_dxf(path)
    res, req, pv, tooling, sha = _run(path)
    mm_report = tn.build_p1_report(res, req, pv, tooling, sha)
    native_m_req = req.model_copy(update={"metres_per_unit": 1.0})
    native_m_req = native_m_req.model_copy(
        update={"request_sha256": compute_request_sha256(native_m_req)})
    native_m_report = tn.build_p1_report(res, native_m_req, pv, tooling, sha)
    for mm_wall, m_wall in zip(mm_report.walls, native_m_report.walls):
        mm_seg, m_seg = mm_wall.segments[0], m_wall.segments[0]
        assert m_seg.coord_m == pytest.approx(mm_seg.coord_m * 1000.0)
        assert m_seg.span_m == pytest.approx([v * 1000.0 for v in mm_seg.span_m])
        assert m_seg.thickness_evidence.value_m == pytest.approx(
            mm_seg.thickness_evidence.value_m * 1000.0)


def test_report_blocked_on_red_and_round_trip(tmp_path):
    path = tmp_path / "a.dxf"; _make_dxf(path, no_caps=True)
    res, req, pv, tooling, sha = _run(path)
    report = tn.build_p1_report(res, req, pv, tooling, sha)
    assert report.status == "BLOCKED"
    assert report.normalized_dxf_sha256 is None
    assert any(d.code == "tarch_opening_block_unresolved" for d in report.diagnostics)
    reloaded = ConversionReportV1.model_validate_json(report.model_dump_json())
    assert reloaded == report


def test_staging_discipline_rejects_protected_source():
    """A convert/build input inside a protected root is refused (§0.1 方案A)."""
    with pytest.raises(ValueError, match="tarch_staging_input_protected_path"):
        tn.run_p1_plan_view(SM24_SOURCE, *_sm24_request("0" * 64),
                            resolve_converter_tooling(GT_CONFIG, VG_CONFIG))


# =========================================================================== #
# ⭐⭐⭐ G-c (2026-09-07) -- THE FOUR-TIER LADDER replaces the two ANDed gates.
#
# What the user defined, verbatim:
#   "这种正交吸附和按毫米分辨率吸附我理解是不用签字的，直接修正就可以，
#    需要签字的是像之前上下墙体出现对齐错误的这类真『画错』问题"
#   "长度越长容差应该越大一些…最大定到 5 度吧"   (长度 = the stroke's own length)
#   "按阶梯定一个方案，综合长度和角度；超出的才升级到需要人签字的仲裁"
#   "10mm作废吧，就都按现在的推进就行"
#
#   tier 0  deviation <= q (0.1 mm)               never enters the branch
#   tier 1  deviation <= min(len·tan5°, CAP)      flattened about the ANCHOR END
#   tier 2  inside 5° but over CAP, or the        refused AND itemised for a
#           anchor end is undecidable-and-        HUMAN (arbitration)
#           visible
#   tier 3  angle > 5°                            a real diagonal, refused
#
# ⛔ THE 10 mm CEILING (``AXIS_SNAP_MAX_DEVIATION_M``) IS RETIRED.  Its job is
# now done by ``CAP`` = half the REQUEST'S OWN thinnest declared wall, derived
# per request -- so the tests below move it by declaring a different
# ``wall_thickness_range_m``, which exercises the derivation as well as the
# comparison.  ⛔ Nothing here monkeypatches ``tn.AXIS_SNAP_MAX_ANGLE_DEG``:
# ``from X import Y`` binds via the parent package attribute, not
# ``sys.modules``, and patching the wrong object has already manufactured a
# band of false-red in this repo.  ``_Tols``/``_tols_from`` expose the angle as
# a keyword; that is the injection port.
#
# ⭐ Unit-level, not through the full DXF/S0/S3/S4 pipeline: ``_collect_walls``
# is what implements the decision and its inputs are cheap to build directly.
# =========================================================================== #
def _one_line_msp(dx_mm: float, dy_mm: float, *, x0: float = 1000.0, y0: float = 1000.0):
    """A bare ezdxf modelspace holding exactly one WALL line, endpoints
    ``(x0, y0)`` -> ``(x0+dx_mm, y0+dy_mm)``.  ⛔ No frame/title/other walls --
    ``_collect_walls`` needs none of them, only S0 preflight does."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((x0, y0), (x0 + dx_mm, y0 + dy_mm), dxfattribs={"layer": "WALL"})
    return msp


def _two_line_msp(specs, *, layer: str = "WALL"):
    """A bare modelspace holding one WALL line per ``(x0, y0, x1, y1)`` spec."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for x0, y0, x1, y1 in specs:
        msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": layer})
    return msp


#: ⭐ The declared thickness range whose CAP is 30 mm -- the value BOTH real
#: in-corpus requests derive today (``wall_thickness_range_m[0] = 0.06``).
#: ⛔ It is a fixture INPUT here, never an expectation: ``_cap_mm`` recomputes
#: it from the same declaration the production code reads.
CORPUS_THICKNESS_M = (0.06, 0.50)


def _cap_mm(thickness_range_m) -> float:
    """CAP as the production code derives it, ⛔ not as a literal."""
    return thickness_range_m[0] * 1000.0 / 2.0


def _collect_lines(specs, *, thickness_range_m=CORPUS_THICKNESS_M,
                   axis_snap_max_angle_deg: float = tn.AXIS_SNAP_MAX_ANGLE_DEG,
                   tau_axis_m: float = 0.001, node_join_m: float = 0.001):
    """``_collect_walls`` on N hand-built lines, with the request's declared
    thickness (⇒ CAP) and the angle envelope both controlled.

    Defaults are the PRODUCTION angle and the CORPUS thickness declaration, so
    a test that overrides exactly one keyword is measuring exactly one thing.
    ``metres_per_unit=0.001`` ⇒ the native unit is the millimetre, so every
    number in these fixtures reads directly as mm.
    """
    plan_view = SimpleNamespace(wall_selector=TarchEntitySelectorV1(
        entity_types=["LINE"], layers=["WALL"]))
    request = SimpleNamespace(wall_thickness_range_m=list(thickness_range_m))
    tols = tn._Tols(metres_per_unit=0.001, node_join_m=node_join_m,
                    axis_align_m=tau_axis_m, topo_area_m2=1e-6,
                    axis_snap_max_angle_deg=axis_snap_max_angle_deg)
    msp = _two_line_msp(specs)
    diags: list = []
    xs = [c for s in specs for c in (s[0], s[2])]
    ys = [c for s in specs for c in (s[1], s[3])]
    clip = (min(xs) - 10.0, min(ys) - 10.0, max(xs) + 10.0, max(ys) + 10.0)
    collect = tn._collect_walls(msp, plan_view, request, clip, tols, diags)
    return collect, diags


def _collect_one(dx_mm: float, dy_mm: float, **kwargs):
    """ONE line from (1000, 1000), with ⛔ NO neighbour at either end.

    ⭐ Read the consequence before using this: with no neighbour, the anchor
    rule cannot resolve, so a visible deviation lands on TIER 2 by design
    ("锚端定不了且该选择在产物里看得出来").  That is the right fixture for the
    tier-2c and tier-3 cases and the WRONG one for anything that should be
    auto-flattened -- use :func:`_collect_anchored` for those.
    """
    return _collect_lines([(1000.0, 1000.0, 1000.0 + dx_mm, 1000.0 + dy_mm)],
                          **kwargs)


def _collect_anchored(dx_mm: float, dy_mm: float, *, post: float = 200.0,
                      **kwargs):
    """A skew face PLUS an already-straight post sharing its FAR endpoint.

    ⭐ This is the corpus' own shape (13AD's east end is held by the straight
    13AC), and it is what lets the anchor rule resolve to ``p1`` -- so these
    fixtures exercise the tier-1 path the real drawing takes.  The post is
    exactly vertical, so it never enters the ladder itself and contributes no
    diagnostic of its own.
    """
    x1, y1 = 1000.0 + dx_mm, 1000.0 + dy_mm
    return _collect_lines([(1000.0, 1000.0, x1, y1), (x1, y1, x1, y1 - post)],
                          **kwargs)


def _face_lines_of(collect, post: float = 200.0):
    """The staged strokes that are NOT the anchoring post."""
    return [row for row in collect.wall_lines
            if not (row[1] == row[3] and abs(row[4] - row[2]) == pytest.approx(
                post, abs=0.5))]


def _refusal(diags):
    """The single ``tarch_wall_nonorthogonal`` diagnostic's context."""
    refusals = [d for d in diags if d.code == "tarch_wall_nonorthogonal"]
    assert len(refusals) == 1, [d.code for d in diags]
    return refusals[0].context


def _admission(diags):
    """The single ``tarch_wall_axis_snapped`` diagnostic's context."""
    snaps = [d for d in diags if d.code == "tarch_wall_axis_snapped"]
    assert len(snaps) == 1, [d.code for d in diags]
    return snaps[0].context


# --------------------------------------------------------------------------- #
# LOCK 1 (was ``test_axis_snap_admits_a_line_within_the_threshold_and_itemises_it``)
#   pinned: "minor leg inside the ceiling ⇒ admitted, short leg zeroed, long
#            leg untouched, itemised once"
#   now pins: the SAME outcome, plus the ladder tier that produced it and the
#            fact that the ceiling it was measured against is the DERIVED CAP.
# --------------------------------------------------------------------------- #
def test_gc_lock1_tier1_admits_and_itemises_with_the_derived_ceiling():
    """3 mm out over a 2000 mm run = 0.086°: inside the 5° envelope and inside
    the 30 mm CAP the corpus thickness declaration derives ⇒ tier 1."""
    collect, diags = _collect_anchored(2000.0, 3.0)
    codes = [d.code for d in diags]
    assert "tarch_wall_nonorthogonal" not in codes
    assert codes.count("tarch_wall_axis_snapped") == 1
    faces = _face_lines_of(collect)
    assert len(faces) == 1
    _handle, x0, y0, x1, y1 = faces[0]
    # ⭐ the short leg (y) is zeroed -- the line is now EXACTLY axis-aligned
    assert y0 == y1
    # ⭐ the long leg (x) endpoints are the fixed design constraint: untouched
    assert (x0, x1) == (pytest.approx(1000.0), pytest.approx(3000.0))
    ctx = _admission(diags)
    assert ctx["ladder_tier"] == 1
    assert ctx["snapped_axis"] == "y"
    assert ctx["minor_leg_mm"] == pytest.approx(3.0)
    # ⭐ the ceiling it was compared against is the request's own CAP, ⛔ not a
    # module constant: this stroke is long enough that CAP is the binding limb.
    assert ctx["cap_mm"] == pytest.approx(_cap_mm(CORPUS_THICKNESS_M))
    assert ctx["deviation_limit_mm"] == pytest.approx(ctx["cap_mm"])
    # ⭐ before_p0/before_p1's LONG-leg coordinate equals the raw input exactly
    assert ctx["before_p0"][0] == pytest.approx(1000.0)
    assert ctx["before_p1"][0] == pytest.approx(3000.0)


# --------------------------------------------------------------------------- #
# LOCK 2 (was ``test_axis_snap_still_refuses_a_genuine_diagonal_beyond_the_threshold``)
#   pinned: "beyond the millimetre ceiling ⇒ still refused, still absent from
#            wall_lines" -- i.e. the pre-②-1b-S outcome survives.
#   now pins: that outcome survives AND is no longer anonymous -- a stroke
#            refused for being over CAP is TIER 2 (a human decides), which is a
#            different finding from tier 3, and the record says which.
# --------------------------------------------------------------------------- #
def test_gc_lock2_over_cap_is_still_refused_and_is_named_arbitration():
    """20 mm out over 2000 mm = 0.573°: the ANGLE says yes (0.573 < 5), so the
    only thing that can refuse it is CAP.  With a 12 mm thinnest wall declared,
    CAP = 6 mm and 20 mm is over it ⇒ refused, dropped, and itemised as tier 2
    -- ⛔ NOT silently discarded and ⛔ not mislabelled a diagonal."""
    collect, diags = _collect_one(2000.0, 20.0, thickness_range_m=(0.012, 0.50))
    codes = [d.code for d in diags]
    assert codes.count("tarch_wall_nonorthogonal") == 1
    assert "tarch_wall_axis_snapped" not in codes
    assert collect.wall_lines == []
    ctx = _refusal(diags)
    assert ctx["ladder_tier"] == 2
    assert ctx["refused_by"] == ["deviation_over_cap"]
    assert ctx["angle_deg"] == pytest.approx(0.5729, abs=1e-3)
    # ⭐ the load-bearing half: the ENVELOPE said yes.
    assert ctx["angle_deg"] <= ctx["axis_snap_max_angle_deg"]
    assert ctx["cap_mm"] == pytest.approx(6.0)


# --------------------------------------------------------------------------- #
# LOCK 3 (was ``test_axis_snap_threshold_is_a_real_parameter_not_hardcoded``)
#   pinned: "the same 20 mm stroke flips between two hand-passed threshold
#            values ⇒ the comparison reads a parameter, not a baked number."
#   now pins: strictly more -- the same stroke flips between two REQUESTS that
#            differ only in ``wall_thickness_range_m``, so the DERIVATION is
#            exercised too, ⛔ not just the comparison.  This is the executable
#            form of "⛔ CAP must not be a module constant" (invariant #6).
# --------------------------------------------------------------------------- #
def test_gc_lock3_cap_is_derived_per_request_not_baked_in():
    spec_dx, spec_dy = 2000.0, 20.0        # 0.573°, well inside the envelope
    refused, diags_thin = _collect_anchored(spec_dx, spec_dy,
                                            thickness_range_m=(0.012, 0.50))
    assert _face_lines_of(refused) == []
    assert _refusal(diags_thin)["refused_by"] == ["deviation_over_cap"]

    admitted, diags_thick = _collect_anchored(spec_dx, spec_dy,
                                              thickness_range_m=(0.060, 0.50))
    assert len(_face_lines_of(admitted)) == 1
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags_thick)
    assert _admission(diags_thick)["ladder_tier"] == 1
    # ⭐ and the two CAPs the two requests derived are the two halves:
    assert _cap_mm((0.012, 0.50)) == 6.0 and _cap_mm((0.060, 0.50)) == 30.0
    assert not hasattr(tn, "AXIS_SNAP_MAX_DEVIATION_M"), (
        "the 10 mm module ceiling is retired (user 2026-09-07); reintroducing "
        "it would put an absolute millimetre number back in front of a "
        "per-request derivation")


# =========================================================================== #
# The real drawing.  ⭐ Not synthetic: handles 13AD/13AE/13AF on the as-received
# sm25 drawing are the ONLY off-axis strokes anywhere in the corpus (measured:
# 1 degenerate / 262 exact / 314 float-noise / 3 skew / 0 real slants across
# all three plan views of both cases).
# =========================================================================== #
SM25_AS_RECEIVED = (REPO /
    "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3_as_received.dxf")
SM25_AS_MEASURED_REQUEST = (REPO /
    "case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json")


def _sm25_as_received_geometry(tmp_path):
    request = TarchConversionRequestV1.model_validate_json(
        SM25_AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    view = next(v for v in request.plan_views if v.id == "plan-F1")
    staged = tmp_path / SM25_AS_RECEIVED.name
    shutil.copy2(SM25_AS_RECEIVED, staged)
    return tn.run_p1_plan_view(staged, request, view,
                               resolve_converter_tooling(GT_CONFIG, VG_CONFIG))


# --------------------------------------------------------------------------- #
# LOCK 4 (was ``test_f147_acceptance_1_real_tremor_13ad_is_admitted_by_both_gates``)
#   pinned: "13AD/13AE are admitted and the diagnostic carries BOTH signed
#            readings" -- the two-gate decision is auditable.
#   now pins: the LADDER's decision is auditable -- tier, both readings, AND
#            (new, load-bearing) WHICH END it was anchored about.  ⭐ 13AF joins
#            the list: it used to fall between ``tau_axis`` and exact equality
#            and vanish from every table.
# --------------------------------------------------------------------------- #
def test_gc_lock4_real_tremor_all_three_strokes_are_tier1_and_auditable(tmp_path):
    geo = _sm25_as_received_geometry(tmp_path)
    snapped = {d.source_entity_handles[0]: d.context for d in geo.diagnostics
               if d.code == "tarch_wall_axis_snapped"}
    assert set(snapped) == {"13AD", "13AE", "13AF"}, sorted(snapped)
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in geo.diagnostics)

    for handle in ("13AD", "13AE", "13AF"):
        ctx = snapped[handle]
        assert ctx["ladder_tier"] == 1
        # one rigid-body rotation: all three read the SAME angle
        assert ctx["angle_deg"] == pytest.approx(0.0914, abs=5e-4)
        assert ctx["minor_leg_mm"] <= ctx["deviation_limit_mm"]

    # ⭐ the long faces: the anchor rule found the end shared with an
    # already-straight neighbour (13AC / 160A), ⛔ not the midpoint.
    for handle in ("13AD", "13AE"):
        assert snapped[handle]["anchor_end"] == "p1"
        assert snapped[handle]["anchor_reason"] == (
            "p1_shares_a_point_with_an_already_axial_stroke")
        assert snapped[handle]["minor_leg_mm"] == pytest.approx(5.8084, abs=5e-4)
    # ⭐ the 120 mm end cap: BOTH its neighbours are crooked, so no end anchors
    # it -- and the three candidate answers collapse to ONE stored value, so
    # the choice is not representable and ⛔ must not cost a human anything.
    cap_ctx = snapped["13AF"]
    assert cap_ctx["anchor_end"] == "mid"
    assert cap_ctx["anchor_reason"] == "anchor_choice_not_representable"
    assert len(set(cap_ctx["anchor_candidates_stored"])) == 1
    assert cap_ctx["minor_leg_mm"] == pytest.approx(0.1915, abs=5e-4)
    # ⭐ and the short stroke is where the ANGLE limb binds, not CAP:
    assert cap_ctx["deviation_limit_mm"] == pytest.approx(10.4986, abs=1e-3)
    assert cap_ctx["deviation_limit_mm"] < cap_ctx["cap_mm"]


def test_gc_lock4b_the_anchor_rule_closes_the_joints_the_midpoint_split(tmp_path):
    """⭐⭐ THE VARIABILITY PROOF for lock 4, and the acceptance G-c-1 asks for:
    flip the anchor back to the midpoint and the joints re-open by exactly the
    3.0 mm the ledger used to carry.  ⛔ This is measured on the real drawing
    through the real ``_collect_walls``, not asserted from the docstring.
    """
    geo = _sm25_as_received_geometry(tmp_path)
    lines = {h: (x0, y0, x1, y1) for h, x0, y0, x1, y1 in geo.wall_lines}
    # 13AD is horizontal at const y; 13AC is vertical and ends on it.
    assert lines["13AD"][1] == lines["13AD"][3]           # flattened
    assert lines["13AD"][1] == min(lines["13AC"][1], lines["13AC"][3])
    assert lines["13AE"][1] == max(lines["160A"][1], lines["160A"][3])
    # the west end cap followed the ends that moved -- ⛔ no torn corner:
    assert sorted((lines["13AF"][1], lines["13AF"][3])) == sorted(
        (lines["13AE"][1], lines["13AD"][1]))

    # ⇒ the counterfactual: the midpoint answer, recomputed from the SAME raw
    # endpoints the converter recorded, is 2.90 mm away from the anchored one.
    ctx = next(d.context for d in geo.diagnostics
               if d.code == "tarch_wall_axis_snapped"
               and d.source_entity_handles[0] == "13AD")
    raw_anchor = ctx["before_p1"][1]                 # the end the rule chose
    midpoint_const = (ctx["before_p0"][1] + ctx["before_p1"][1]) / 2.0
    assert abs(midpoint_const - raw_anchor) == pytest.approx(
        ctx["minor_leg_mm"] / 2.0)                   # half the skew, by definition
    assert abs(midpoint_const - raw_anchor) == pytest.approx(2.9042, abs=1e-3)
    # ⭐ and on the 1 mm ingest grid that half-skew becomes exactly the 3.0 mm
    # (``const -30``) the revisions ledger used to ask a human to sign off.
    # sm25's native unit IS the millimetre, so these two steps are the same
    # chain a real coordinate walks.
    tols_sm25 = tn._Tols(metres_per_unit=0.001, node_join_m=0.001,
                         axis_align_m=0.001, topo_area_m2=1e-6)
    stored = lambda v: tn._quantize(tn._quantize(v, tols_sm25.quant_native),
                                    tols_sm25.ingest_grid_native)
    assert abs(stored(midpoint_const) - stored(raw_anchor)) == pytest.approx(3.0)


# --------------------------------------------------------------------------- #
# LOCK 5 (was ``test_f147_acceptance_1b_the_signed_10mm_deviation_value_has_teeth``)
#   pinned: "the SIGNED 10 mm value itself has teeth" -- an 8 mm stroke is
#            admitted under 10 mm and refused under the old 6 mm placeholder.
#   ⛔ THAT PREMISE IS GONE: the user retired the 10 mm value on 2026-09-07, so
#            there is no longer a signed millimetre number for this test to
#            defend.  ⭐ The QUESTION it existed to answer survives intact --
#            "is the deviation ceiling load-bearing, or is it decorative?" --
#            and the answer is now measured against CAP.  The fixture is kept
#            in the same band (8 mm on a 2000 mm run) because that band still
#            has no real specimen in the corpus, which is why the original test
#            had to supply one.
# --------------------------------------------------------------------------- #
def test_gc_lock5_the_deviation_ceiling_still_has_teeth_now_as_cap():
    """2000 mm run, 8 mm out = 0.229°.  The ENVELOPE says yes either way, so
    this stroke's verdict is decided by the deviation ceiling ALONE."""
    spec_dx, spec_dy = 2000.0, 8.0
    admitted, diags = _collect_anchored(spec_dx, spec_dy)   # corpus CAP = 30 mm
    ctx = _admission(diags)
    assert len(_face_lines_of(admitted)) == 1
    assert ctx["ladder_tier"] == 1
    assert ctx["minor_leg_mm"] == pytest.approx(8.0)
    assert ctx["angle_deg"] == pytest.approx(0.2292, abs=1e-3)

    # a request that declares a 12 mm thinnest wall derives CAP = 6 mm, and
    # refuses exactly this stroke -- on the ceiling, ⛔ not on the angle:
    refused, diags_thin = _collect_anchored(spec_dx, spec_dy,
                                            thickness_range_m=(0.012, 0.50))
    assert _face_lines_of(refused) == []
    thin_ctx = _refusal(diags_thin)
    assert thin_ctx["refused_by"] == ["deviation_over_cap"]
    assert thin_ctx["angle_deg"] <= thin_ctx["axis_snap_max_angle_deg"]


def test_gc_lock5b_the_retired_10mm_ceiling_is_not_silently_still_in_force():
    """⭐ The other half of lock 5's retirement: prove the 10 mm number is not
    merely deleted from sight but actually out of the decision.  A 12 mm
    deviation is REFUSED by the old ceiling and ADMITTED by today's ladder on
    the corpus declaration (12 <= CAP 30, 0.34° <= 5°)."""
    admitted, diags = _collect_anchored(2000.0, 12.0)
    assert len(_face_lines_of(admitted)) == 1
    ctx = _admission(diags)
    assert ctx["minor_leg_mm"] == pytest.approx(12.0)
    assert ctx["minor_leg_mm"] > 10.0        # ⛔ the retired ceiling would refuse
    assert ctx["ladder_tier"] == 1


# --------------------------------------------------------------------------- #
# LOCK 6 (was ``test_f147_acceptance_2_short_slant_passes_the_mm_gate_and_the
#          _angle_gate_stops_it``)
#   pinned: "60 mm long, 5 mm out = 4.764°: the millimetre gate SAID YES, and
#            the stroke is refused ONLY because the 1.0° angle gate exists."
#   ⛔ ITS PREMISE MOVED with 1.0° -> 5.0°: 4.764° is now INSIDE the envelope
#            and this fixture is admitted.  ⭐ What the test was really pinning
#            -- "on a short stroke the deviation ceiling is blind and only the
#            angle can refuse" -- is unchanged and is pinned here at the NEW
#            envelope, with the fixture moved to straddle 5.0° instead of 1.0°.
#            ⛔ Both sides are kept: just-inside AND just-outside.
# --------------------------------------------------------------------------- #
def test_gc_lock6_on_a_short_stroke_only_the_angle_can_refuse():
    """60 mm long.  5.00 mm out = 4.764° (inside) and 5.30 mm out = 5.046°
    (outside).  ⭐ In BOTH cases the deviation is far under the 30 mm CAP, so
    CAP is structurally incapable of separating them -- exactly the dimension
    an absolute millimetre ceiling cannot see, and the reason the envelope is
    an angle."""
    admitted, diags_in = _collect_anchored(60.0, 5.0)
    in_ctx = _admission(diags_in)
    assert len(_face_lines_of(admitted)) == 1
    assert in_ctx["ladder_tier"] == 1
    assert in_ctx["angle_deg"] == pytest.approx(4.7636, abs=1e-3)
    assert in_ctx["angle_deg"] <= tn.AXIS_SNAP_MAX_ANGLE_DEG

    refused, diags_out = _collect_anchored(60.0, 5.3)
    out_ctx = _refusal(diags_out)
    assert _face_lines_of(refused) == []
    assert not any(d.code == "tarch_wall_axis_snapped" for d in diags_out)
    assert out_ctx["angle_deg"] == pytest.approx(5.0480, abs=1e-3)
    assert out_ctx["ladder_tier"] == 3
    assert out_ctx["refused_by"] == ["angle_beyond_envelope"]
    # ⭐⭐ the load-bearing half, unchanged in spirit: the DEVIATION ceiling
    # said yes to the refused one.  ⇒ the ONLY thing that refused it is the
    # angle envelope.
    assert out_ctx["minor_leg_mm"] == pytest.approx(5.3)
    assert out_ctx["minor_leg_mm"] <= out_ctx["cap_mm"]


# --------------------------------------------------------------------------- #
# LOCK 7 (was ``test_f147_acceptance_3_forty_five_degrees_is_refused_by_both_gates``)
#   pinned: "a 45° line is refused, and the record shows BOTH gates said no --
#            'refused' must never be confused with 'refused for the reason I
#            assumed'."
#   now pins: the same discrimination, one tier up -- a 45° line is TIER 3 and
#            ⛔ explicitly NOT arbitration.  ⭐ That distinction is new and is
#            the one that matters: tier 2 costs a human's time, tier 3 must not.
# --------------------------------------------------------------------------- #
def test_gc_lock7_forty_five_degrees_is_tier3_and_never_reaches_a_human():
    collect, diags = _collect_one(1000.0, 1000.0)
    ctx = _refusal(diags)
    assert collect.wall_lines == []
    assert ctx["angle_deg"] == pytest.approx(45.0)
    assert ctx["minor_leg_mm"] == pytest.approx(1000.0)
    assert ctx["ladder_tier"] == 3
    assert ctx["refused_by"] == ["angle_beyond_envelope"]
    # ⭐ it is over CAP too (1000 mm >> 30 mm) -- and the ladder still calls it
    # tier 3, ⛔ not tier 2: the envelope is tested FIRST on purpose, because a
    # genuine diagonal is not a suspected drafting error.
    assert ctx["minor_leg_mm"] > ctx["cap_mm"]


# --------------------------------------------------------------------------- #
# LOCK 8 (was ``test_f147_signed_1deg_admits_the_0p39deg_slanted_wall_KNOWN_
#          SIGNED_RISK``)
#   pinned: ⛔⛔ A COST THE USER KNOWINGLY ACCEPTED at 1.0°, ⛔ not a
#            correctness expectation: a real 0.394° slanted wall is admitted,
#            both faces snap to their own midlines, and the pairing step
#            MANUFACTURES a wall that is not on the drawing.
#   now pins: THE SAME COST, at the wider 5.0° envelope -- ⛔ the change did not
#            reduce it -- plus what does and does not bound it now.  ⭐ Kept as
#            a PRICE tag, ⛔ still not a verified behaviour.
# --------------------------------------------------------------------------- #
def test_gc_lock8_five_degrees_still_admits_the_0p39deg_slanted_wall_KNOWN_RISK():
    """⛔⛔ THIS TEST PINS A COST, ⛔ NOT A CORRECTNESS CLAIM.

    The cross-reviewer's negative sample: two faces 800 mm long, each 5.5 mm
    out (0.394°), 120 mm apart.  Under 1.0° both were admitted, each snapped to
    its own midline, the pair stayed exactly 120 mm apart and looked like an
    ordinary orthogonal wall to everything downstream -- on the real drawing
    that took walls 55 -> 56, ⛔ a wall that is not on the drawing.  ⭐ 5.0°
    admits a strictly WIDER angular band, so ⛔ the 2026-09-07 change does not
    reduce this cost by itself.

    ⭐⭐ MEASURED HERE, and it is the part a reader should not miss: the ladder
    narrows the sample in a way the angle never could.  This sample as the
    cross-reviewer built it -- two faces with NOTHING attached to either end --
    no longer reaches the fabrication at all: with no anchor end and a visibly
    different answer, both faces are refused to a HUMAN (tier 2).  ⛔ The cost
    is NOT gone: attach a straight stroke to one end of each face (the shape
    the real corpus has) and the anchor rule resolves, both are flattened, and
    the phantom 120 mm wall is back.  BOTH halves are pinned below so nobody
    can read either one as the whole story.
    """
    faces = [(1000.0, 1000.0, 1800.0, 1005.5),      # 800 mm run, 5.5 mm out
             (1000.0, 1120.0, 1800.0, 1125.5)]      # its partner, 120 mm away

    # --- half 1: the sample AS BUILT is now caught, ⛔ not fabricated --------
    isolated, diags_isolated = _collect_lines(faces)
    assert isolated.wall_lines == []
    caught = [d for d in diags_isolated if d.code == "tarch_wall_nonorthogonal"]
    assert len(caught) == 2
    for d in caught:
        assert d.context["ladder_tier"] == 2
        assert d.context["refused_by"] == ["anchor_undecidable_and_observable"]
        assert d.context["angle_deg"] == pytest.approx(0.3939, abs=1e-3)
        assert d.context["angle_deg"] <= tn.AXIS_SNAP_MAX_ANGLE_DEG

    # --- half 2: ⛔ THE COST, still there, on the shape the corpus has -------
    anchored = faces + [(1800.0, 1005.5, 1800.0, 1105.5),
                        (1800.0, 1125.5, 1800.0, 1225.5)]
    collect, diags = _collect_lines(anchored)
    snaps = [d for d in diags if d.code == "tarch_wall_axis_snapped"]
    assert len(snaps) == 2, [d.code for d in diags]
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags)
    for d in snaps:
        assert d.context["angle_deg"] == pytest.approx(0.3939, abs=1e-3)
        assert d.context["ladder_tier"] == 1
        assert d.context["anchor_end"] == "p1"

    # ⛔ the actual harm, made visible: two snapped faces, still 120 mm apart
    # -- i.e. indistinguishable from a genuine 120 mm wall.
    ys = sorted({round(y0, 6) for _h, _x0, y0, _x1, y1 in collect.wall_lines
                 if y0 == y1})
    assert len(ys) == 2 and ys[1] - ys[0] == pytest.approx(120.0, abs=0.05)

    # ⭐ and the OTHER bound the ladder adds, measured: declare a 10 mm thinnest
    # wall (CAP = 5 mm) and the same anchored pair goes to a human instead.
    refused, diags_thin = _collect_lines(anchored, thickness_range_m=(0.010, 0.50))
    tier2 = [d for d in diags_thin if d.code == "tarch_wall_nonorthogonal"]
    assert len(tier2) == 2
    assert all(d.context["ladder_tier"] == 2 for d in tier2)
    assert all(d.context["refused_by"] == ["deviation_over_cap"] for d in tier2)


# --------------------------------------------------------------------------- #
# LOCK 9 (was ``test_f147_acceptance_5a_widening_only_the_angle_gate_flips_a_case``)
#   pinned: "ONLY the angle knob moves and the verdict moves with it ⇒ the
#            angle gate is load-bearing by itself."
#   now pins: the same, unchanged in shape -- the angle is still one of the
#            ladder's two limits and it is still independently load-bearing.
#            ⭐ The flip points are re-measured for the ladder (a stroke the 1°
#            envelope refuses is tier 3; the 10° envelope makes it tier 1).
# --------------------------------------------------------------------------- #
def test_gc_lock9_moving_only_the_angle_envelope_flips_a_case():
    """Same 60 mm / 5 mm stroke as lock 6.  ⛔ The request's declared thickness
    (⇒ CAP) is left at the corpus value throughout -- ONLY the envelope moves."""
    refused, diags_lo = _collect_anchored(60.0, 5.0, axis_snap_max_angle_deg=1.0)
    assert _face_lines_of(refused) == []
    lo_ctx = _refusal(diags_lo)
    assert lo_ctx["refused_by"] == ["angle_beyond_envelope"]
    assert lo_ctx["ladder_tier"] == 3
    assert lo_ctx["cap_mm"] == pytest.approx(_cap_mm(CORPUS_THICKNESS_M))

    admitted, diags_hi = _collect_anchored(60.0, 5.0, axis_snap_max_angle_deg=10.0)
    assert len(_face_lines_of(admitted)) == 1
    hi_ctx = _admission(diags_hi)
    assert hi_ctx["angle_deg"] == pytest.approx(4.7636, abs=1e-3)
    assert hi_ctx["ladder_tier"] == 1
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags_hi)


# --------------------------------------------------------------------------- #
# LOCK 10 (was ``test_f147_acceptance_5b_widening_only_the_deviation_gate_flips
#           _a_different_case``)
#   pinned: "ONLY the millimetre knob moves and a DIFFERENT case flips ⇒ the
#            two gates are not redundant; neither could be deleted."
#   now pins: the identical claim with CAP in the millimetre gate's place --
#            and ⭐ the non-redundancy is now demonstrable in BOTH directions in
#            one function, which the original could only do across two files'
#            worth of fixtures.
# --------------------------------------------------------------------------- #
def test_gc_lock10_the_envelope_and_the_cap_are_not_redundant():
    """Two strokes, each refused by exactly one of the two limits, ⛔ with the
    OTHER limit saying yes in each case.

      long  = 2000 mm run, 20 mm out = 0.573°  -> the envelope says YES,
                                                  CAP(6 mm) says no
      short =   60 mm run,  5.3 mm out = 5.046° -> CAP says YES,
                                                  the envelope says no

    ⇒ deleting either limit would let one of these through, so neither is
    redundant.  ⭐ And they land on DIFFERENT tiers, which is itself the point:
    over-CAP is a question for a person, over-envelope is not.
    """
    long_refused, long_diags = _collect_anchored(2000.0, 20.0,
                                                 thickness_range_m=(0.012, 0.50))
    long_ctx = _refusal(long_diags)
    assert _face_lines_of(long_refused) == []
    assert long_ctx["refused_by"] == ["deviation_over_cap"]
    assert long_ctx["ladder_tier"] == 2
    assert long_ctx["angle_deg"] <= long_ctx["axis_snap_max_angle_deg"]

    short_refused, short_diags = _collect_anchored(60.0, 5.3,
                                                   thickness_range_m=(0.012, 0.50))
    short_ctx = _refusal(short_diags)
    assert _face_lines_of(short_refused) == []
    assert short_ctx["refused_by"] == ["angle_beyond_envelope"]
    assert short_ctx["ladder_tier"] == 3
    assert short_ctx["minor_leg_mm"] <= short_ctx["cap_mm"]

    # and each is ADMITTED once its own refusing limit is moved, ⛔ with the
    # other left at the value it already had:
    long_ok, _ = _collect_anchored(2000.0, 20.0, thickness_range_m=(0.060, 0.50))
    assert len(_face_lines_of(long_ok)) == 1
    short_ok, _ = _collect_anchored(60.0, 5.3, thickness_range_m=(0.012, 0.50),
                                    axis_snap_max_angle_deg=10.0)
    assert len(_face_lines_of(short_ok)) == 1


# --------------------------------------------------------------------------- #
# LOCK 11 (was ``test_axis_snap_along_axis_endpoints_survive_bit_for_bit
#           _through_quantize``)
#   pinned: "the snap contributes ZERO extra movement on the along axis."
#   now pins: the SAME invariant for the snap itself, ⛔ but no longer as an
#            unconditional property of the stage -- because G-c added a
#            mechanism that DOES move along-axis endpoints (a node relocation,
#            when the stroke shares a point another stroke's flattening moved).
#            ⭐ So the lock is split: unchanged when nothing shares the node,
#            and the companion below proves the exception is real, ⛔ not a
#            loophole nobody measured.
# --------------------------------------------------------------------------- #
def test_gc_lock11_the_snap_alone_never_moves_an_along_axis_endpoint():
    tols_ref = tn._Tols(metres_per_unit=0.001, node_join_m=0.001, axis_align_m=0.001,
                        topo_area_m2=1e-6)
    collect, _ = _collect_anchored(2000.0, 3.0)
    _, x0, _, x1, _ = _face_lines_of(collect)[0]
    assert x0 == tn._quantize(1000.0, tols_ref.quant_native)
    assert x1 == tn._quantize(3000.0, tols_ref.quant_native)


def test_gc_lock11b_an_along_axis_endpoint_DOES_follow_a_relocated_node():
    """⭐⭐ The exception, on a fixture that reproduces the corpus' west corner
    in miniature: a long face flattened about its RIGHT end drops its LEFT end,
    and the end cap sharing that left point comes with it.

    ⛔ Without this the two would tear apart -- measured on the real drawing as
    a 6.0 mm gap, i.e. twice the 3.0 mm this unit set out to close.

    ⭐ The cap is drawn 0.19 mm out of plumb ON PURPOSE, exactly as 13AF is:
    a perfectly straight cap would ANCHOR the face's left end too, the face
    would have two anchors, and the fixture would be measuring tier 2 instead.
    """
    face = (1000.0, 1000.0, 3000.0, 1003.0)      # 2000 mm run, 3 mm out
    cap = (1000.0, 1000.0, 1000.19, 880.0)       # 120 mm cap, 0.19 mm out
    post = (3000.0, 1003.0, 3000.0, 1503.0)      # straight: anchors the face
    collect, diags = _collect_lines([face, cap, post])
    lines = {h: (x0, y0, x1, y1) for h, x0, y0, x1, y1 in collect.wall_lines}
    snapped = {d.source_entity_handles[0]: d.context for d in diags
               if d.code == "tarch_wall_axis_snapped"}
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags)
    assert len(snapped) == 2                      # the face and the cap

    face_handle = next(h for h, c in snapped.items() if c["snapped_axis"] == "y")
    cap_handle = next(h for h, c in snapped.items() if c["snapped_axis"] == "x")
    assert snapped[face_handle]["anchor_end"] == "p1"
    assert snapped[cap_handle]["anchor_reason"] == "anchor_choice_not_representable"

    # the face was anchored about its RIGHT end -> its const is the right y
    face_line = lines[face_handle]
    assert face_line[1] == face_line[3] == pytest.approx(1003.0)
    # ⭐ and the cap's shared (top) endpoint FOLLOWED it, ⛔ instead of staying
    # at the pre-flattening 1000.0 -- i.e. the corner closes at 0.
    cap_line = lines[cap_handle]
    assert max(cap_line[1], cap_line[3]) == pytest.approx(1003.0)
    assert max(cap_line[1], cap_line[3]) == face_line[1]


# =========================================================================== #
# ⭐⭐⭐ G-c-6 -- ONE FIXTURE PER TIER, each with BOTH sides of its boundary.
#
# ⛔ WHY THIS SECTION IS THE HEAVIEST PART OF THE UNIT: the corpus contains
# ZERO real slants (measured sweep: 1 degenerate / 262 exact / 314 float-noise /
# 3 skew / 0 slants).  ⇒ tiers 2 and 3 -- the REFUSING directions -- have no
# natural specimen at all, so without synthetic fixtures the new ladder would
# be toothless in precisely the direction that matters.
# =========================================================================== #
def _tier_of(diags) -> int:
    """0 = nothing recorded; else the ladder tier the record names."""
    for d in diags:
        if d.code in ("tarch_wall_axis_snapped", "tarch_wall_nonorthogonal"):
            return int(d.context["ladder_tier"])
    return 0


def test_gc6_tier0_boundary_at_q_noise_is_not_recorded_at_all():
    """⭐ Both sides of ``q`` = 0.1 mm.  ⛔ Under it there must be NO record of
    any kind: quantization erases the deviation anyway, and a 314-entry noise
    list would drown the one entry a human should look at."""
    #   just inside the noise floor: 0.09 mm out over 2000 mm  (q = 0.1)
    quiet, diags_quiet = _collect_anchored(2000.0, 0.09)
    assert _tier_of(diags_quiet) == 0
    assert [d.code for d in diags_quiet] == []
    assert len(_face_lines_of(quiet)) == 1
    #   just outside it: 0.11 mm -- now it is a tier-1 admission WITH a record
    loud, diags_loud = _collect_anchored(2000.0, 0.11)
    assert _tier_of(diags_loud) == 1
    assert _admission(diags_loud)["minor_leg_mm"] == pytest.approx(0.11)
    assert len(_face_lines_of(loud)) == 1


def test_gc6_tier1_boundary_is_cap_on_a_long_stroke():
    """⭐ Both sides of the tier-1 ceiling where CAP binds.  2000 mm run,
    corpus CAP = 30 mm."""
    cap = _cap_mm(CORPUS_THICKNESS_M)
    inside, diags_in = _collect_anchored(2000.0, cap)          # exactly at CAP
    assert _tier_of(diags_in) == 1
    assert len(_face_lines_of(inside)) == 1
    assert _admission(diags_in)["deviation_limit_mm"] == pytest.approx(cap)
    outside, diags_out = _collect_anchored(2000.0, cap + 0.1)   # one q past it
    assert _tier_of(diags_out) == 2
    assert _face_lines_of(outside) == []
    assert _refusal(diags_out)["refused_by"] == ["deviation_over_cap"]


def test_gc6_tier1_boundary_is_the_angle_on_a_short_stroke():
    """⭐ Both sides of the tier-1 ceiling where the ANGLE binds instead --
    the other side of the crossing at ``CAP / tan5°`` = 343 mm.  100 mm run:
    the ceiling is 100·tan5° = 8.75 mm, far under the 30 mm CAP."""
    limit = tn._axis_snap_deviation_limit(100.0, _cap_mm(CORPUS_THICKNESS_M),
                                          tn.AXIS_SNAP_MAX_ANGLE_DEG)
    assert limit == pytest.approx(8.7489, abs=1e-3)          # ⇒ the angle binds
    inside, diags_in = _collect_anchored(100.0, 8.7)          # 4.9722°
    assert _tier_of(diags_in) == 1 and len(_face_lines_of(inside)) == 1
    outside, diags_out = _collect_anchored(100.0, 8.8)        # 5.0291°
    assert _tier_of(diags_out) == 3 and _face_lines_of(outside) == []


def test_gc6_tier2a_long_stroke_inside_the_envelope_but_over_cap():
    """⭐⭐ THE RISK FACE OF THE 5° CHANGE, and the格 the dispatch calls out:
    a stroke can be well inside 5° and still be asked to move a very long way,
    because 5° of a long run is a lot of millimetres.  10 m run at 4° is
    699 mm -- 23 CAPs.  ⛔ That must reach a human, not be flattened."""
    over, diags_over = _collect_anchored(10_000.0, 699.0)
    ctx = _refusal(diags_over)
    assert _face_lines_of(over) == []
    assert ctx["ladder_tier"] == 2
    assert ctx["refused_by"] == ["deviation_over_cap"]
    assert ctx["angle_deg"] == pytest.approx(3.9985, abs=1e-3)
    assert ctx["angle_deg"] < tn.AXIS_SNAP_MAX_ANGLE_DEG     # ⭐ envelope said yes
    assert ctx["deviation_limit_mm"] == pytest.approx(_cap_mm(CORPUS_THICKNESS_M))
    # the just-passing side of the SAME boundary, same stroke length:
    under, diags_under = _collect_anchored(10_000.0, 30.0)
    assert _tier_of(diags_under) == 1 and len(_face_lines_of(under)) == 1


def test_gc6_tier2b_both_ends_anchored_is_a_suspected_real_slant():
    """⭐⭐ The other tier-2 door, and the one the anchor rule opens: a skew
    stroke whose BOTH ends sit on already-straight strokes.  Then it is ⛔ not
    a slipped endpoint -- the drawing means it to run between two settled
    points -- so flattening it would be inventing geometry."""
    #   a 1000 mm skew face, 5 mm out, with a straight post at EACH end
    both = [(1000.0, 1000.0, 2000.0, 1005.0),
            (1000.0, 1000.0, 1000.0, 900.0),
            (2000.0, 1005.0, 2000.0, 905.0)]
    collect, diags = _collect_lines(both)
    refusals = [d for d in diags if d.code == "tarch_wall_nonorthogonal"]
    assert len(refusals) == 1
    ctx = refusals[0].context
    assert ctx["ladder_tier"] == 2
    assert ctx["refused_by"] == ["both_ends_anchored_suspected_true_slant"]
    assert ctx["angle_deg"] == pytest.approx(0.2865, abs=1e-3)
    assert ctx["minor_leg_mm"] <= ctx["cap_mm"]     # ⭐ neither limit refused it
    assert len(collect.wall_lines) == 2             # only the two straight posts

    # ⛔ THE OTHER SIDE, and the whole reason the rule says "a neighbour that is
    # ITSELF straight": drop ONE post and the very same skew face is tier 1,
    # anchored at the end that still has a straight neighbour.
    one = [both[0], both[1]]
    collect_one_post, diags_one = _collect_lines(one)
    assert _tier_of(diags_one) == 1
    assert _admission(diags_one)["anchor_end"] == "p0"
    assert len(collect_one_post.wall_lines) == 2


def test_gc6_tier2c_unanchored_and_visibly_different_goes_to_a_human():
    """⭐⭐ The zero-threshold observability rule, BOTH sides.

    Neither end anchored.  The question is only ever "do the three candidate
    answers land on the same STORED value" -- ⛔ never "are they closer than
    some number".

      visible  : a 2000 mm face 8 mm out -> anchor-p0 / anchor-p1 / midpoint
                 land 8 mm apart = 8 ingest cells ⇒ a person decides
      invisible: the same shape 0.2 mm out -> all three land on ONE cell
                 ⇒ ⛔ nobody is asked, the midpoint is taken, tier 1
    """
    visible, diags_visible = _collect_one(2000.0, 8.0, node_join_m=0.001)
    ctx = _refusal(diags_visible)
    assert visible.wall_lines == []
    assert ctx["ladder_tier"] == 2
    assert ctx["refused_by"] == ["anchor_undecidable_and_observable"]
    assert len(set(ctx["anchor_candidates_stored"])) > 1

    invisible, diags_invisible = _collect_one(2000.0, 0.2, node_join_m=0.001)
    inv_ctx = _admission(diags_invisible)
    assert len(invisible.wall_lines) == 1
    assert inv_ctx["ladder_tier"] == 1
    assert inv_ctx["anchor_end"] == "mid"
    assert inv_ctx["anchor_reason"] == "anchor_choice_not_representable"
    assert len(set(inv_ctx["anchor_candidates_stored"])) == 1


def test_gc6_tier3_boundary_is_the_signed_five_degrees():
    """⭐ Both sides of the user-signed envelope, on a stroke short enough that
    CAP cannot possibly be what decides it (⇒ the flip is attributable)."""
    inside, diags_in = _collect_anchored(200.0, 17.4)     # 4.9722°
    assert _tier_of(diags_in) == 1 and len(_face_lines_of(inside)) == 1
    assert _admission(diags_in)["angle_deg"] < tn.AXIS_SNAP_MAX_ANGLE_DEG

    outside, diags_out = _collect_anchored(200.0, 17.6)   # 5.0291°
    ctx = _refusal(diags_out)
    assert _face_lines_of(outside) == []
    assert ctx["ladder_tier"] == 3
    assert ctx["angle_deg"] > tn.AXIS_SNAP_MAX_ANGLE_DEG
    assert ctx["minor_leg_mm"] <= ctx["cap_mm"]      # ⭐ CAP said yes to both


# =========================================================================== #
# ⭐ The ladder's arithmetic, and the "no fourth threshold" invariant.
# =========================================================================== #
def test_gc_ladder_limit_table_matches_the_shape_the_user_asked_for():
    """⭐ "长度越长容差应该越大一些" AND "长线上小角度已经很显眼" are BOTH true,
    on opposite sides of the crossing at ``CAP / tan5°``.  ⛔ Measured from the
    production helper, not from a table copied into a docstring."""
    cap = _cap_mm(CORPUS_THICKNESS_M)
    limit = lambda length: tn._axis_snap_deviation_limit(
        length, cap, tn.AXIS_SNAP_MAX_ANGLE_DEG)
    # short-stroke region: the ceiling grows LINEARLY with length
    assert limit(120.0) == pytest.approx(10.4986, abs=1e-3)
    assert limit(240.0) == pytest.approx(20.9973, abs=1e-3)
    assert limit(240.0) == pytest.approx(2 * limit(120.0))
    # the crossing, and beyond it the ceiling is flat at CAP
    crossing = cap / math.tan(math.radians(tn.AXIS_SNAP_MAX_ANGLE_DEG))
    assert crossing == pytest.approx(342.9, abs=0.1)
    for length in (1000.0, 3640.0, 10_000.0):
        assert limit(length) == pytest.approx(cap)
    # ⇒ the EFFECTIVE angle therefore tightens automatically on long strokes
    assert math.degrees(math.asin(limit(3640.0) / 3640.0)) == pytest.approx(0.472, abs=1e-3)
    assert math.degrees(math.asin(limit(10_000.0) / 10_000.0)) == pytest.approx(0.172, abs=1e-3)


def test_gc_ladder_limit_first_limb_is_subsumed_by_the_angle_envelope():
    """⚠️ A MEASURED PROPERTY, recorded so nobody reads more into
    ``min(len·tan5°, CAP)`` than is there: the envelope is tested FIRST, and
    ``deviation = len·sin(angle)``, so any stroke that reaches the ceiling
    already satisfies the first limb.  ⇒ inside the envelope the binding limb
    is ALWAYS CAP.  The two formulations differ only on (5.0000°, 5.0191°]."""
    boundary = math.degrees(math.asin(math.tan(math.radians(
        tn.AXIS_SNAP_MAX_ANGLE_DEG))))
    assert boundary == pytest.approx(5.0191, abs=1e-3)
    for angle in (0.1, 1.0, 3.0, 4.999):
        length = 100.0
        deviation = length * math.sin(math.radians(angle))
        assert deviation < length * math.tan(math.radians(tn.AXIS_SNAP_MAX_ANGLE_DEG))


def test_gc_ingest_grid_is_tau_node_not_a_fourth_threshold():
    """⭐⭐⭐ THE "no fourth threshold" LOCK.  The observability rule rounds its
    three candidates onto the facts layer's 1 mm ingest grid, and the converter
    reaches that grid as ``tau_node`` -- ``q``'s own parent, ⛔ not a new
    number.  The two definitions live in two modules; this makes their equality
    a CHECKED invariant instead of a coincidence that silently rots.
    """
    from src.agent.judge.as_measured import (INGEST_RESOLUTION_UNITS,
                                             UNITS_PER_METRE)
    facts_grid_m = INGEST_RESOLUTION_UNITS / UNITS_PER_METRE
    tols = tn._Tols(metres_per_unit=0.001, node_join_m=0.001, axis_align_m=0.001,
                    topo_area_m2=1e-6)
    assert tols.ingest_grid_native == pytest.approx(facts_grid_m / 0.001)
    assert tols.ingest_grid_native == tols.node_join_native
    assert tols.quant_native == pytest.approx(tols.ingest_grid_native / 10.0)


def test_gc_the_ladder_holds_exactly_three_numbers():
    """⛔ The unit's hard constraint, made executable: ``q`` (derived), ``CAP``
    (derived per request) and ``5.0°`` (user-signed).  A fourth module-level
    threshold in this file's snap surface is the thing to catch."""
    assert tn.AXIS_SNAP_MAX_ANGLE_DEG == 5.0
    #: ⭐ PUBLIC module-level numbers only: a leading underscore marks the two
    #: unrelated internals (a DXF header epoch and a z-band equality guard),
    #: ⛔ neither of which the snap surface reads.
    module_numbers = {name for name, value in vars(tn).items()
                      if name.isupper() and not name.startswith("_")
                      and isinstance(value, (int, float))
                      and not isinstance(value, bool)}
    assert module_numbers == {"AXIS_SNAP_MAX_ANGLE_DEG"}, sorted(module_numbers)
    # ⭐ and CAP really is per-request, ⛔ not on the module or on ``_Tols``:
    assert not any("cap" in name.lower() for name in vars(tn) if name.isupper())
    assert "cap" not in " ".join(f.name for f in dataclasses.fields(tn._Tols)).lower()
