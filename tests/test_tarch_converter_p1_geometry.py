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

import hashlib
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
# dispatch ②-1b-S R1 -- S1 "drop" -> "snap the short leg or still drop if
# genuinely diagonal".  ⭐ F-147 (2026-08-30) made the admission TWO gates
# ANDed (deviation ≤ 10 mm AND angle ≤ 1.0°), both USER-SIGNED.
#
# ⭐ Unit-level, not through the full DXF/S0/S3/S4 pipeline: ``_collect_walls``
# is what implements the decision, and its inputs (``plan_view.wall_selector``,
# ``request.wall_thickness_range_m``, a ``_Tols`` with a CONTROLLED
# ``axis_snap_max_m``) are cheap to build directly -- this is what lets test 3
# below prove the threshold is a real parameter and not a number baked into
# the ``if``.
# =========================================================================== #
def _one_line_msp(dx_mm: float, dy_mm: float, *, x0: float = 1000.0, y0: float = 1000.0):
    """A bare ezdxf modelspace holding exactly one WALL line, endpoints
    ``(x0, y0)`` -> ``(x0+dx_mm, y0+dy_mm)``.  ⛔ No frame/title/other walls --
    ``_collect_walls`` needs none of them, only S0 preflight does."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((x0, y0), (x0 + dx_mm, y0 + dy_mm), dxfattribs={"layer": "WALL"})
    return msp


def _collect_with_snap_threshold(dx_mm: float, dy_mm: float, *, axis_snap_max_m: float,
                                 tau_axis_m: float = 0.001):
    """Call ``tn._collect_walls`` directly with a hand-built, fully controlled
    ``_Tols`` -- ⭐ this is the "parameterized, not hardcoded in an if" proof:
    the SAME code path is exercised twice with two different threshold values
    below (test 3) and the admitted/refused outcome flips with it."""
    plan_view = SimpleNamespace(wall_selector=TarchEntitySelectorV1(
        entity_types=["LINE"], layers=["WALL"]))
    request = SimpleNamespace(wall_thickness_range_m=[0.06, 0.50])
    tols = tn._Tols(metres_per_unit=0.001, node_join_m=0.001, axis_align_m=tau_axis_m,
                    topo_area_m2=1e-6, axis_snap_max_m=axis_snap_max_m)
    msp = _one_line_msp(dx_mm, dy_mm)
    diags: list = []
    clip = (0.0, 0.0, 1000.0 + abs(dx_mm) + 10.0, 1000.0 + abs(dy_mm) + 10.0)
    collect = tn._collect_walls(msp, plan_view, request, clip, tols, diags)
    return collect, diags


def test_axis_snap_admits_a_line_within_the_threshold_and_itemises_it():
    """Minor leg 3 mm, major leg 2000 mm, threshold 6 mm (the ②-1b-S
    placeholder) -> ADMITTED: no ``tarch_wall_nonorthogonal``, one
    ``tarch_wall_axis_snapped``, and the line reaches ``wall_lines``."""
    collect, diags = _collect_with_snap_threshold(2000.0, 3.0, axis_snap_max_m=0.006)
    codes = [d.code for d in diags]
    assert "tarch_wall_nonorthogonal" not in codes
    assert codes.count("tarch_wall_axis_snapped") == 1
    assert len(collect.wall_lines) == 1
    handle, x0, y0, x1, y1 = collect.wall_lines[0]
    # ⭐ the short leg (y) is zeroed -- the line is now EXACTLY axis-aligned
    assert y0 == y1
    # ⭐ the long leg (x) endpoints are the dispatch's fixed design constraint:
    # untouched by the snap (⛔ not the pending-sign-off part)
    assert (x0, x1) == (pytest.approx(1000.0), pytest.approx(3000.0))
    snapped = next(d for d in diags if d.code == "tarch_wall_axis_snapped")
    assert snapped.context["snapped_axis"] == "y"
    assert snapped.context["minor_leg_mm"] == pytest.approx(3.0)
    # ⭐ before_p0/before_p1's LONG-leg coordinate equals the raw input exactly
    # -- the along-wall span is bit-for-bit unmoved by the snap
    assert snapped.context["before_p0"][0] == pytest.approx(1000.0)
    assert snapped.context["before_p1"][0] == pytest.approx(3000.0)


def test_axis_snap_still_refuses_a_genuine_diagonal_beyond_the_threshold():
    """Minor leg 20 mm, threshold 6 mm -> UNCHANGED behaviour: still refused,
    still ``tarch_wall_nonorthogonal``, still absent from ``wall_lines`` --
    the exact pre-②-1b-S outcome for anything beyond the admission line."""
    collect, diags = _collect_with_snap_threshold(2000.0, 20.0, axis_snap_max_m=0.006)
    codes = [d.code for d in diags]
    assert codes.count("tarch_wall_nonorthogonal") == 1
    assert "tarch_wall_axis_snapped" not in codes
    assert collect.wall_lines == []


def test_axis_snap_threshold_is_a_real_parameter_not_hardcoded():
    """⭐⭐ Acceptance 4's teeth: the SAME 20 mm-skew line is refused under one
    threshold value and admitted under another -- proving the comparison
    reads a passed-in value, not a number written into the ``if``."""
    refused, diags_lo = _collect_with_snap_threshold(2000.0, 20.0, axis_snap_max_m=0.006)
    assert refused.wall_lines == []
    assert any(d.code == "tarch_wall_nonorthogonal" for d in diags_lo)

    admitted, diags_hi = _collect_with_snap_threshold(2000.0, 20.0, axis_snap_max_m=0.030)
    assert len(admitted.wall_lines) == 1
    assert any(d.code == "tarch_wall_axis_snapped" for d in diags_hi)
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags_hi)


# =========================================================================== #
# F-147 (2026-08-30) -- the SECOND, ANGLE gate.  Acceptance ①..⑤.
#
# ⭐⭐⭐ Why an angle gate exists at all: the SAME millimetre number means a
# ~120x different angle depending on how long the stroke is.  6 mm on the real
# 3640 mm stroke 13AD is 0.094° (hand tremor); 6 mm on a 30 mm stroke is
# 11.310° (an unmistakable diagonal).  An absolute-millimetre threshold is
# therefore the wrong SHAPE for this decision, and no amount of tightening it
# recovers the dimension it cannot see.  ⛔ Hence a new gate, not a new number.
#
# ⛔ Every test below drives the thresholds through ``_Tols``/``_tols_from``
# keyword arguments -- the injection port the production code provides.
# ⛔ NOTHING here monkeypatches ``tn.AXIS_SNAP_MAX_*``: ``from X import Y``
# binds via the parent package attribute, not ``sys.modules``, and patching
# the wrong object has already manufactured a band of false-red in this repo.
# =========================================================================== #
SM25_AS_RECEIVED = (REPO /
    "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3_as_received.dxf")
SM25_AS_MEASURED_REQUEST = (REPO /
    "case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json")


def _two_line_msp(specs, *, layer: str = "WALL"):
    """A bare modelspace holding one WALL line per ``(x0, y0, x1, y1)`` spec."""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for x0, y0, x1, y1 in specs:
        msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": layer})
    return msp


def _collect_lines(specs, *, axis_snap_max_m: float = tn.AXIS_SNAP_MAX_DEVIATION_M,
                   axis_snap_max_angle_deg: float = tn.AXIS_SNAP_MAX_ANGLE_DEG,
                   tau_axis_m: float = 0.001):
    """``_collect_walls`` on N hand-built lines with BOTH gates controlled.

    Defaults are the PRODUCTION constants, so a test that overrides exactly one
    keyword is measuring exactly one gate.
    """
    plan_view = SimpleNamespace(wall_selector=TarchEntitySelectorV1(
        entity_types=["LINE"], layers=["WALL"]))
    request = SimpleNamespace(wall_thickness_range_m=[0.06, 0.50])
    tols = tn._Tols(metres_per_unit=0.001, node_join_m=0.001, axis_align_m=tau_axis_m,
                    topo_area_m2=1e-6, axis_snap_max_m=axis_snap_max_m,
                    axis_snap_max_angle_deg=axis_snap_max_angle_deg)
    msp = _two_line_msp(specs)
    diags: list = []
    xs = [c for s in specs for c in (s[0], s[2])]
    ys = [c for s in specs for c in (s[1], s[3])]
    clip = (min(xs) - 10.0, min(ys) - 10.0, max(xs) + 10.0, max(ys) + 10.0)
    collect = tn._collect_walls(msp, plan_view, request, clip, tols, diags)
    return collect, diags


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
# ① REAL hand tremor -- ⛔ not synthetic: handle 13AD on the as-received sm25
#    drawing, the only such stroke that exists anywhere in the corpus.
# --------------------------------------------------------------------------- #
def test_f147_acceptance_1_real_tremor_13ad_is_admitted_by_both_gates(tmp_path):
    """13AD: 5.8084 mm out over a 3639.9 mm run = 0.091°.  Inside BOTH signed
    gates, so it snaps -- and the diagnostic now carries BOTH readings, which
    is what makes the two-gate decision auditable by the human who signs the
    snap list.  ⭐ Real drawing, run through ``run_p1_plan_view``."""
    request = TarchConversionRequestV1.model_validate_json(
        SM25_AS_MEASURED_REQUEST.read_text(encoding="utf-8"))
    view = next(v for v in request.plan_views if v.id == "plan-F1")
    staged = tmp_path / SM25_AS_RECEIVED.name
    shutil.copy2(SM25_AS_RECEIVED, staged)
    geo = tn.run_p1_plan_view(staged, request, view,
                              resolve_converter_tooling(GT_CONFIG, VG_CONFIG))

    snapped = {d.source_entity_handles[0]: d.context for d in geo.diagnostics
               if d.code == "tarch_wall_axis_snapped"}
    assert set(snapped) == {"13AD", "13AE"}, sorted(snapped)
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in geo.diagnostics)

    ctx = snapped["13AD"]
    assert ctx["minor_leg_mm"] == pytest.approx(5.8084, abs=5e-4)
    # ⭐ R3: the angle reading, which did not exist before F-147
    assert ctx["angle_deg"] == pytest.approx(0.0914, abs=5e-4)
    assert ctx["angle_deg"] < tn.AXIS_SNAP_MAX_ANGLE_DEG
    assert ctx["minor_leg_mm"] < tn.AXIS_SNAP_MAX_DEVIATION_M * 1000.0
    # ⭐ and 13AD's own numbers prove the "same mm, 120x the angle" point that
    # motivated the gate: 5.81 mm reads as 0.09° ONLY because the run is long.
    assert snapped["13AE"]["angle_deg"] == pytest.approx(0.0914, abs=5e-4)


# --------------------------------------------------------------------------- #
# ①b The SIGNED 10 mm VALUE ITSELF has teeth.
#     ⭐ Added beyond the dispatch's five: the mutation matrix measured that
#     reverting 6 mm -> 10 mm left every other fixture GREEN, i.e. R1's value
#     change was landing unguarded.  The corpus has no stroke in the 6-10 mm
#     band, so the fixture has to supply one -- that absence is exactly why
#     nothing else could see this direction.
# --------------------------------------------------------------------------- #
def test_f147_acceptance_1b_the_signed_10mm_deviation_value_has_teeth():
    """2000 mm run, 8 mm out = 0.229°.  The ANGLE gate says yes either way, so
    this stroke's verdict is decided by the deviation value ALONE: admitted
    under the signed 10 mm, refused under the old unsigned 6 mm placeholder.

    ⛔ The main claim below runs on the PRODUCTION default (no keyword passed),
    so it goes red if anyone edits ``AXIS_SNAP_MAX_DEVIATION_M`` back down.
    """
    spec = [(1000.0, 1000.0, 3000.0, 1008.0)]
    admitted, diags = _collect_lines(spec)            # ⭐ production constants
    ctx = _admission(diags)
    assert len(admitted.wall_lines) == 1
    assert ctx["minor_leg_mm"] == pytest.approx(8.0)
    assert ctx["angle_deg"] == pytest.approx(0.2292, abs=1e-3)

    # the pre-F-147 placeholder refused exactly this, on the deviation gate:
    refused, diags_6mm = _collect_lines(spec, axis_snap_max_m=0.006)
    assert refused.wall_lines == []
    assert _refusal(diags_6mm)["refused_by"] == ["deviation_mm"]


# --------------------------------------------------------------------------- #
# ② SHORT slanted stroke -- the millimetre gate WOULD LET THIS THROUGH.
#    This single fixture is the whole reason the angle gate exists.
# --------------------------------------------------------------------------- #
def test_f147_acceptance_2_short_slant_passes_the_mm_gate_and_the_angle_gate_stops_it():
    """60 mm long, 5 mm out = 4.764°.  5 mm is comfortably inside the 10 mm
    signed deviation gate, so the PRE-F-147 code would have snapped this
    obvious little diagonal into an axis-aligned wall.  ⭐ It is refused only
    because the angle gate exists, and the refusal NAMES that gate."""
    collect, diags = _collect_lines([(1000.0, 1000.0, 1060.0, 1005.0)])
    ctx = _refusal(diags)
    assert collect.wall_lines == []
    assert not any(d.code == "tarch_wall_axis_snapped" for d in diags)
    assert ctx["angle_deg"] == pytest.approx(4.7636, abs=1e-3)
    # ⭐⭐ the load-bearing half: the millimetre gate SAID YES here.
    assert ctx["minor_leg_mm"] == pytest.approx(5.0)
    assert ctx["minor_leg_mm"] <= ctx["axis_snap_max_native"]
    # ⇒ so the ONLY reason it was refused is the angle gate:
    assert ctx["refused_by"] == ["angle_deg"]


# --------------------------------------------------------------------------- #
# ③ 45° control -- both gates refuse.
# --------------------------------------------------------------------------- #
def test_f147_acceptance_3_forty_five_degrees_is_refused_by_both_gates():
    """1000 mm x 1000 mm.  Not a subtle case; it is here so that "refused" is
    never confused with "refused for the reason I assumed" -- the record shows
    BOTH gates said no, which is a different observation from ② and from ⑤b."""
    collect, diags = _collect_lines([(1000.0, 1000.0, 2000.0, 2000.0)])
    ctx = _refusal(diags)
    assert collect.wall_lines == []
    assert ctx["angle_deg"] == pytest.approx(45.0)
    assert ctx["minor_leg_mm"] == pytest.approx(1000.0)
    assert ctx["refused_by"] == ["deviation_mm", "angle_deg"]


# --------------------------------------------------------------------------- #
# ④ ⛔⛔ KNOWN SIGNED RISK -- ⛔ NOT a correctness expectation.
# --------------------------------------------------------------------------- #
def test_f147_signed_1deg_admits_the_0p39deg_slanted_wall_KNOWN_SIGNED_RISK():
    """⛔⛔ THIS TEST PINS A COST THE USER KNOWINGLY ACCEPTED.  ⛔ It does NOT
    assert that the behaviour is correct, and ⛔ nobody should read it as
    evidence that this case was verified to be right.

    What it pins: the cross-reviewer's negative sample -- a REAL gently
    slanted wall, two faces 800 mm long, each 5.5 mm out (0.394°), 120 mm
    apart.  Under the signed 1.0° gate BOTH faces are admitted and each is
    snapped to its own midline; the pair therefore stays exactly 120 mm apart
    and looks like a perfectly ordinary orthogonal wall to everything
    downstream.  On the real as-received drawing this is what took walls
    55 -> 56: ⛔ a wall that is not on the drawing.  Same defect family as
    this project's 33 fabricated walls.

    ⭐ At 0.25° the same input is REFUSED (asserted below, so this test also
    records what the alternative would have bought).  The admissible interval
    was only (0.091°, 0.394°): one real tremor on one side, one synthetic
    slant on the other.  0.25°/0.3° were recommended.  The user was told the
    consequence, restated it, and chose 1.0° -- "签，角度调到 1 度吧"
    (2026-08-30, F-143).  This test exists so the next reader sees a PRICE,
    ⛔ not a verified behaviour.

    ⭐ The compensating control is the last gate, unchanged and outside this
    file: a human reads ``axis_snapped_lines`` line by line when signing
    ``revisions``.  Both faces below appear on that list, with their angles.
    """
    faces = [(1000.0, 1000.0, 1800.0, 1005.5),      # 800 mm run, 5.5 mm out
             (1000.0, 1120.0, 1800.0, 1125.5)]      # its partner, 120 mm away
    collect, diags = _collect_lines(faces)

    snaps = [d for d in diags if d.code == "tarch_wall_axis_snapped"]
    assert len(snaps) == 2, [d.code for d in diags]
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags)
    for d in snaps:
        assert d.context["angle_deg"] == pytest.approx(0.3939, abs=1e-3)
        assert d.context["angle_deg"] <= tn.AXIS_SNAP_MAX_ANGLE_DEG

    # ⛔ the actual harm, made visible: two snapped midlines, still 120 mm
    # apart -- i.e. indistinguishable from a genuine 120 mm wall.
    ys = sorted({round(y0, 6) for _h, _x0, y0, _x1, y1 in collect.wall_lines
                 if y0 == y1})
    assert len(ys) == 2 and ys[1] - ys[0] == pytest.approx(120.0, abs=0.05)

    # ⭐ and the counterfactual the user was shown before signing: 0.25° refuses it.
    refused, diags_025 = _collect_lines(faces, axis_snap_max_angle_deg=0.25)
    assert refused.wall_lines == []
    assert [d.code for d in diags_025].count("tarch_wall_nonorthogonal") == 2
    assert all(d.context["refused_by"] == ["angle_deg"]
               for d in diags_025 if d.code == "tarch_wall_nonorthogonal")


# --------------------------------------------------------------------------- #
# ⑤ Each gate has teeth ON ITS OWN.  ⛔ "both had to move" would not count.
# --------------------------------------------------------------------------- #
def test_f147_acceptance_5a_widening_only_the_angle_gate_flips_a_case():
    """Same 60 mm / 5 mm stroke as ②.  ⛔ The millimetre gate is left at the
    production value throughout -- ONLY ``axis_snap_max_angle_deg`` moves, and
    the verdict moves with it.  ⇒ the angle gate is load-bearing by itself."""
    refused, diags_lo = _collect_lines([(1000.0, 1000.0, 1060.0, 1005.0)],
                                       axis_snap_max_angle_deg=1.0)
    assert refused.wall_lines == []
    assert _refusal(diags_lo)["refused_by"] == ["angle_deg"]

    admitted, diags_hi = _collect_lines([(1000.0, 1000.0, 1060.0, 1005.0)],
                                        axis_snap_max_angle_deg=10.0)
    assert len(admitted.wall_lines) == 1
    assert _admission(diags_hi)["angle_deg"] == pytest.approx(4.7636, abs=1e-3)
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags_hi)


def test_f147_acceptance_5b_widening_only_the_deviation_gate_flips_a_different_case():
    """A LONG stroke: 2000 mm run, 20 mm out = 0.573°.  ⭐ The angle gate says
    YES to this one (0.573° < 1.0°) at the production value, which is left
    untouched here -- ONLY ``axis_snap_max_m`` moves.  ⇒ the millimetre gate
    is load-bearing by itself, and ⛔ the two gates are not redundant: ② and
    this case are refused by DIFFERENT gates, so neither gate could be deleted
    without letting one of them through."""
    spec = [(1000.0, 1000.0, 3000.0, 1020.0)]
    refused, diags_lo = _collect_lines(spec, axis_snap_max_m=0.010)
    assert refused.wall_lines == []
    ctx = _refusal(diags_lo)
    assert ctx["angle_deg"] == pytest.approx(0.5729, abs=1e-3)
    # ⭐ the angle gate SAID YES; only the millimetre gate refused.
    assert ctx["angle_deg"] <= ctx["axis_snap_max_angle_deg"]
    assert ctx["refused_by"] == ["deviation_mm"]

    admitted, diags_hi = _collect_lines(spec, axis_snap_max_m=0.030)
    assert len(admitted.wall_lines) == 1
    assert _admission(diags_hi)["minor_leg_mm"] == pytest.approx(20.0)
    assert not any(d.code == "tarch_wall_nonorthogonal" for d in diags_hi)


def test_axis_snap_along_axis_endpoints_survive_bit_for_bit_through_quantize():
    """⭐ Acceptance 3, at the unit level: the along-wall (major-axis)
    endpoints that end up in ``wall_lines`` are EXACTLY the same value
    quantizing the raw, un-snapped major-axis coordinates would have produced
    -- the snap contributes ZERO extra movement on that axis."""
    tols_ref = tn._Tols(metres_per_unit=0.001, node_join_m=0.001, axis_align_m=0.001,
                        topo_area_m2=1e-6)
    collect, _ = _collect_with_snap_threshold(2000.0, 3.0, axis_snap_max_m=0.006)
    _, x0, _, x1, _ = collect.wall_lines[0]
    assert x0 == tn._quantize(1000.0, tols_ref.quant_native)
    assert x1 == tn._quantize(3000.0, tols_ref.quant_native)
