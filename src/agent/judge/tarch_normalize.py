"""Tianzheng (天正) real-building DXF -> GT v3: P1 algorithm body (S0-S4).

Built strictly on top of the P0-frozen contracts in
:mod:`tarch_converter_schema`.  This module implements the **geometry stages
only**:

  S0  input preflight   proxy=0 / units explicit / view frame + unique title /
                        non-axis-parallel rejected
  S1  coordinate quantize   ``q = tau_node/10`` (a derived value); G2 conservation
                        (quantize may denoise but never merge two coords > tau_node
                        apart); zero-length (degenerate) lines bookkept as INFO
  S2  wall collect + jamb-cap identification  the short cross-section lines are
                        thickness evidence kind #2 (``wall_cap_or_opening_jamb``);
                        the legal thickness *range* is a sanity bound only, never
                        the *source* of a thickness (plan §2.1)
  S3  opening dual-evidence resolution   block bbox gives the along-wall span,
                        the wall's own jamb caps give the normal interval; the
                        bbox's normal extent must overlap the wall band (this is
                        what excludes a door's swing arc — D2).  Exactly one
                        solution fills; 0/many fail (plan §4 S3).
  S4  topology closure   ``polygonize_full`` over (all walls + all opening fills);
                        ``dangles/cuts/invalid`` all empty AND ``sum(face areas) ==
                        footprint area`` (plan §4 S4 / G5).

It does **not** do S5-S9 (cavities / intent binding / per-edge expand / gates
G6-G9 / persist) — that is P2.  No DXF is augmented or promoted in P1 (§0.1
方案A: convert+build always run in staging); the normalization lives in the IR.

Hard disciplines enforced here (dispatch §2 / plan §2):

  1. fail-closed — every ambiguous branch raises a BLOCK diagnostic and stops;
     there is no warn-then-continue path (the report status contract makes a
     PASS-with-BLOCK-diagnostic impossible).
  2. no baked thickness assumption — thickness comes ONLY from a measured jamb
     cap (evidence kind #2); the [t_min, t_max] range is a sanity filter, not a
     source.  No ``DEFAULT_WALL_THICKNESS`` / ``MAX_WALL_PAIR_DISTANCE`` constant.
  3. non-exact-orthogonal — axis-ness is decided by ``|dx|,|dy| <= tau_axis``,
     never by float ``==`` (D: walls deviate up to 1.31e-10 mm).
  4. no fabricated tolerance — every threshold is read from ``judge_gt.yaml`` via
     :func:`resolve_converter_tooling`; the quantization step is derived
     (``tau_node/10``), not a config key.
  5. gt isolation — this module is judge-side.  Tianzheng layer names, block-name
     prefixes and the view-frame convention are read ONLY from the request's
     :class:`TarchDialectRulesV1` / selectors, never from a module constant.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import ezdxf
from ezdxf import bbox as ezdxf_bbox
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import polygonize_full, unary_union

from .tarch_converter_schema import (
    Affine2D, CavityIRV1, CavityReportV1, ClipBoxDxf, ConversionDiagnosticV1,
    DatumBoundNamedElevationViewIntentV3, ElevationDoorBlockRuleV1,
    ConversionReportV1, DiagnosticSeverity, EdgeBasis, GateResultV1, HumanReviewAckV1,
    OpeningReportV1, PlanViewIntentV1, Point2, PolygonIRV1, RingV1, StableId,
    SourceEntityRefV1, SourceMapEntryV1, SourceMapV1, TARCH_DIAGNOSTIC_REGISTRY,
    TarchConversionRequestV1, TarchDialectRulesV1, ThicknessEvidenceV1,
    WallReportV1, WallRibbonSegmentV1, ZoneEdgeReportV1, ZoneReportV1,
    assert_staging_input, assert_staging_work_dir, compute_request_sha256,
    compute_source_map_sha256, derive_quantization_step,
    diagnostic_spec)

# --------------------------------------------------------------------------- #
# Tolerance bundle — the only thresholds, all from judge_gt.yaml
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _Tols:
    """All seven judge tolerances (in metres) + derived helpers, none invented."""
    metres_per_unit: float
    node_join_m: float           # tau_node   (quantize base, node merge)
    axis_align_m: float          # tau_axis   (orthogonality)
    topo_area_m2: float          # tau_area   (area conservation)
    @property
    def node_join_native(self) -> float:
        return self.node_join_m / self.metres_per_unit

    @property
    def axis_align_native(self) -> float:
        return self.axis_align_m / self.metres_per_unit

    @property
    def quant_native(self) -> float:
        # q = tau_node / 10, expressed in the DXF native unit (mm for sm24).
        return self.node_join_native / 10.0

def _tols_from(tooling, metres_per_unit: float, _legacy_unused: float | None = None) -> _Tols:
    t = tooling.tolerances
    return _Tols(metres_per_unit=metres_per_unit,
                 node_join_m=t.dxf_node_join_tolerance_m,
                 axis_align_m=t.dxf_axis_alignment_tolerance_m,
                 topo_area_m2=t.dxf_topology_area_tolerance_m2)


# --------------------------------------------------------------------------- #
# Small geometry helpers (work in DXF native units; convert to world at the edge)
# --------------------------------------------------------------------------- #
def _quantize(value: float, q: float) -> float:
    """Snap ``value`` to the ``q`` grid.  Deterministic (no banker's-rounding surprise
    on wall coords, which never sit on a .5 boundary at q = tau_node/10)."""
    return round(value / q) * q


def _overlap(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> float:
    """Positive-overlap length of two [lo,hi] intervals (0 if disjoint/touching)."""
    return min(hi_a, hi_b) - max(lo_a, lo_b)


def _to_world(point_xy: tuple[float, float], affine: Affine2D) -> Point2:
    """Apply the request's source->world affine to a DXF-native (mm) point."""
    x, y = point_xy
    return [affine.m00 * x + affine.m01 * y + affine.m02,
            affine.m10 * x + affine.m11 * y + affine.m12]


# --------------------------------------------------------------------------- #
# Diagnostic helper
# --------------------------------------------------------------------------- #
def _diag(code: str, *, handles: list[str] | None = None,
          points_dxf_mm: list[tuple[float, float]] | None = None,
          context: dict[str, Any] | None = None) -> ConversionDiagnosticV1:
    spec = diagnostic_spec(code)
    return ConversionDiagnosticV1(
        code=code, severity=spec.severity, stage=spec.stage,
        source_entity_handles=list(handles or []),
        source_points_dxf_mm=[list(p) for p in (points_dxf_mm or [])],
        context=dict(context or {}),
        action_code=spec.code)


def _add(diags: list[ConversionDiagnosticV1], d: ConversionDiagnosticV1) -> None:
    diags.append(d)


def _apply_test_neuter(gates: list[GateResultV1]) -> list[GateResultV1]:
    """Fresh-process mutation seam used only by the canonical gate suite."""
    target = os.environ.get("TARCH_NEUTER_GATE")
    return [gate.model_copy(update={"passed": True}) if gate.id == target else gate for gate in gates]


# --------------------------------------------------------------------------- #
# P1 result (the geometry artefacts of S0-S4 for one plan view)
# --------------------------------------------------------------------------- #
@dataclass
class ResolvedOpening:
    """One opening resolved by S3 dual evidence."""
    handle: str
    block_name: str
    kind: Literal["window", "door"]
    rect_dxf_mm: tuple[float, float, float, float]   # (x0, y0, x1, y1)
    axis: Literal["x", "y"]                          # along-wall axis
    cross_section_mm: tuple[float, float]            # normal interval [c1, c2]
    jamb_handles: list[str]
    classification: Literal["exterior", "interior_excluded"] = "exterior"

    def fill_edges(self) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        x0, y0, x1, y1 = self.rect_dxf_mm
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return [(corners[i], corners[(i + 1) % 4]) for i in range(4)]


@dataclass
class WallBand:
    """One thickness-homogeneous wall band, grouped from its jamb caps (S2).

    coord_mm is the band's midline representative (mean of its two face coords);
    the two real face coords are encoded in band_id and recoverable from
    thickness + cross-section.  P2 refines bands into full ribbons (both face
    tracks + joints); at P1 the cap-grouped band is the honest S2 output.
    """
    axis: Literal["x", "y"]            # along-wall (running) axis
    face_lo_mm: float                  # the two real wall-face coords (normal axis)
    face_hi_mm: float
    along_min_mm: float                # extent of the band along the running axis
    along_max_mm: float
    thickness_mm: float
    cap_handles: list[str]

    @property
    def coord_mm(self) -> float:
        return (self.face_lo_mm + self.face_hi_mm) / 2.0

    @property
    def band_id(self) -> str:
        return f"w_{self.axis}_{self.face_lo_mm:.4f}_{self.face_hi_mm:.4f}"


@dataclass
class P1PlanViewGeometry:
    """All S0-S4 outputs for one plan view, plus diagnostics and gate results."""
    view_id: str
    floor_id: str
    quant_step_native: float
    wall_lines: list[tuple[str, float, float, float, float]]   # (handle,x0,y0,x1,y1) quantized, non-degenerate
    degenerate_line_count: int
    jamb_caps_v: dict[float, set[tuple[float, float]]]         # const-x -> {(ylo,yhi)}
    jamb_caps_h: dict[float, set[tuple[float, float]]]         # const-y -> {(xlo,xhi)}
    cap_handles_v: dict[float, dict[tuple[float, float], list[str]]]
    cap_handles_h: dict[float, dict[tuple[float, float], list[str]]]
    wall_bands: list[WallBand]
    openings: list[ResolvedOpening]
    opening_fills: list[tuple[tuple[float, float], tuple[float, float]]]
    faces: list[Any]                  # shapely Polygons (native units)
    dangles: int
    cuts: int
    invalid: int
    sum_area_m2: float
    footprint_area_m2: float
    footprint_polygon: Any            # unary_union of faces (native units)
    diagnostics: list[ConversionDiagnosticV1] = field(default_factory=list)
    gates: list[GateResultV1] = field(default_factory=list)
    consumed_wall_handles: set[str] = field(default_factory=set)
    all_wall_handles: set[str] = field(default_factory=set)

    @property
    def has_block(self) -> bool:
        return any(d.severity == DiagnosticSeverity.BLOCK for d in self.diagnostics)


# --------------------------------------------------------------------------- #
# S0 — input preflight
# --------------------------------------------------------------------------- #
def _frame_bbox(poly) -> tuple[float, float, float, float]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (min(xs), min(ys), max(xs), max(ys))


def _point_strictly_inside(px: float, py: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] < px < box[2] and box[1] < py < box[3]


def _proxy_count(msp) -> int:
    """Count proprietary proxy entities (user did not run 'graphics export').

    Extracted so the predicate is unit-testable with duck-typed fake entities
    (ezdxf cannot synthesize a real ACAD_PROXY_ENTITY in a test)."""
    return sum(1 for e in msp if "PROXY" in e.dxftype().upper())


def s0_preflight(doc, msp, plan_view: PlanViewIntentV1, request: TarchConversionRequestV1,
                 tols: _Tols, diags: list[ConversionDiagnosticV1]) -> tuple[bool, set[str]]:
    """S0: proxy / units / view frame + unique title.  Returns (ok, wall_layer_names)."""
    ok = True
    cb = plan_view.clip_box_dxf
    clip = (float(cb.xmin), float(cb.ymin), float(cb.xmax), float(cb.ymax))
    # 1. proxy entities (user did not run 'graphics export')
    proxy_handles = [e.dxf.handle for e in msp if "PROXY" in e.dxftype().upper()]
    if proxy_handles:
        _add(diags, _diag("tarch_source_proxy_present",
                          handles=[proxy_handles[0]],
                          points_dxf_mm=[(clip[0], clip[1])],
                          context={"proxy_entity_count": len(proxy_handles)}))
        ok = False

    # 2. units: unitless source MUST carry an explicit metres_per_unit (no guessing)
    try:
        insunits = int(doc.header.get("$INSUNITS", 0))
    except Exception:  # pragma: no cover - defensive
        insunits = 0
    unit_scale = {"m": 1.0, "mm": 0.001, "cm": 0.01, "in": 0.0254, "ft": 0.3048}
    units_bad = False
    if insunits == 0 and request.native_units == "unitless":
        if request.metres_per_unit <= 0:   # guarded by PositiveFiniteFloat; future-proof
            units_bad = True
    if insunits != 0 and request.native_units != "unitless":
        declared = unit_scale.get(request.native_units)
        if declared is not None and abs(declared - request.metres_per_unit) > 1e-12:
            units_bad = True
    if units_bad:
        _add(diags, _diag("tarch_units_undeclared",
                          points_dxf_mm=[(clip[0], clip[1])],
                          context={"native_units": request.native_units,
                                   "metres_per_unit": request.metres_per_unit,
                                   "header_insunits": insunits}))
        ok = False

    # 3. view frame: the request's clip_box IS the frame (human-declared).  Verify
    #    a closed polyline frame exists at it and exactly one title sits inside.
    tau = tols.node_join_native
    frames = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.closed:
            fb = _frame_bbox(list(e.get_points()))
            if (abs(fb[0] - clip[0]) <= tau and abs(fb[1] - clip[1]) <= tau
                    and abs(fb[2] - clip[2]) <= tau and abs(fb[3] - clip[3]) <= tau):
                frames.append((e.dxf.handle, fb))
    if not frames:
        _add(diags, _diag("tarch_view_frame_missing",
                          points_dxf_mm=[(clip[0], clip[1]), (clip[2], clip[3])]))
        ok = False
    titles_inside: list[tuple[str, str]] = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            ip = e.dxf.insert
            text = e.dxf.text if e.dxftype() == "TEXT" else e.text
            if _point_strictly_inside(float(ip.x), float(ip.y), clip):
                titles_inside.append((e.dxf.handle, text))
    if len(titles_inside) != 1:
        _add(diags, _diag("tarch_view_frame_ambiguous",
                          handles=[h for h, _ in titles_inside],
                          points_dxf_mm=[(clip[0], clip[1]), (clip[2], clip[3])],
                          context={"title_count": len(titles_inside),
                                   "frame_title": plan_view.frame_title}))
        ok = False
    return ok, titles_inside


# --------------------------------------------------------------------------- #
# S1 + S2 — quantize, collect walls, identify jamb caps, check orthogonality
# --------------------------------------------------------------------------- #
@dataclass
class _WallCollect:
    wall_lines: list[tuple[str, float, float, float, float]]
    degenerate: int
    caps_v: dict[float, set[tuple[float, float]]]
    caps_h: dict[float, set[tuple[float, float]]]
    cap_handles_v: dict[float, dict[tuple[float, float], list[str]]]
    cap_handles_h: dict[float, dict[tuple[float, float], list[str]]]
    all_handles: set[str]
    # G2 conservation: source coord -> set of pre-quantize source coords (per axis)
    source_x: dict[float, list[float]]
    source_y: dict[float, list[float]]


def _collect_walls(msp, plan_view: PlanViewIntentV1, request: TarchConversionRequestV1,
                   clip: tuple[float, float, float, float], tols: _Tols,
                   diags: list[ConversionDiagnosticV1]) -> _WallCollect:
    q = tols.quant_native
    tau_axis = tols.axis_align_native
    wall_layers = set(plan_view.wall_selector.layers)
    wall_types = set(plan_view.wall_selector.entity_types)
    # wall thickness sanity range (native units); a FILTER, never a thickness source.
    t_min = request.wall_thickness_range_m[0] / tols.metres_per_unit
    t_max = request.wall_thickness_range_m[1] / tols.metres_per_unit

    wall_lines: list[tuple[str, float, float, float, float]] = []
    degenerate = 0
    caps_v: dict[float, set[tuple[float, float]]] = {}
    caps_h: dict[float, set[tuple[float, float]]] = {}
    cap_handles_v: dict[float, dict[tuple[float, float], list[str]]] = {}
    cap_handles_h: dict[float, dict[tuple[float, float], list[str]]] = {}
    all_handles: set[str] = set()
    source_x: dict[float, list[float]] = {}
    source_y: dict[float, list[float]] = {}

    for e in msp:
        if e.dxf.layer not in wall_layers:
            continue
        if e.dxftype() not in wall_types:
            # S0 entity gate: only the selector's wall primitive type (LINE) is a
            # wall this round.  Any other entity on a wall layer (arc/circle/
            # lwpolyline/proxy) is rejected, not approximated — no slope/curve.
            _add(diags, _diag("tarch_entity_unsupported",
                              handles=[e.dxf.handle],
                              context={"dxftype": e.dxftype(), "role": "wall"}))
            continue
        sx0, sy0 = float(e.dxf.start.x), float(e.dxf.start.y)
        sx1, sy1 = float(e.dxf.end.x), float(e.dxf.end.y)
        # restrict to the plan frame (both endpoints strictly inside)
        if not (_point_strictly_inside(sx0, sy0, clip) and _point_strictly_inside(sx1, sy1, clip)):
            continue
        all_handles.add(e.dxf.handle)
        # S1 orthogonality (non-exact): reject if both legs exceed tau_axis.
        if abs(sx1 - sx0) > tau_axis and abs(sy1 - sy0) > tau_axis:
            _add(diags, _diag("tarch_wall_nonorthogonal",
                              handles=[e.dxf.handle],
                              points_dxf_mm=[(sx0, sy0), (sx1, sy1)]))
            continue
        x0, y0 = _quantize(sx0, q), _quantize(sy0, q)
        x1, y1 = _quantize(sx1, q), _quantize(sy1, q)
        # G2 conservation bookkeeping (per axis, pre vs post quantize)
        for src, snap in ((sx0, x0), (sx1, x1)):
            source_x.setdefault(snap, []).append(src)
        for src, snap in ((sy0, y0), (sy1, y1)):
            source_y.setdefault(snap, []).append(src)
        # degenerate (zero-length after quantize) -> INFO, drop
        if x0 == x1 and y0 == y1:
            degenerate += 1
            _add(diags, _diag("tarch_wall_degenerate_line",
                              handles=[e.dxf.handle],
                              points_dxf_mm=[(x0, y0)]))
            continue
        wall_lines.append((e.dxf.handle, x0, y0, x1, y1))
        # S2 jamb-cap identification: short cross-section line within the sanity range.
        if x0 == x1:  # vertical segment -> cap of a horizontal wall band (normal = y)
            length = abs(y1 - y0)
            if t_min <= length <= t_max:
                span = (min(y0, y1), max(y0, y1))
                caps_v.setdefault(x0, set()).add(span)
                cap_handles_v.setdefault(x0, {}).setdefault(span, []).append(e.dxf.handle)
        elif y0 == y1:  # horizontal segment -> cap of a vertical wall band (normal = x)
            length = abs(x1 - x0)
            if t_min <= length <= t_max:
                span = (min(x0, x1), max(x0, x1))
                caps_h.setdefault(y0, set()).add(span)
                cap_handles_h.setdefault(y0, {}).setdefault(span, []).append(e.dxf.handle)

    return _WallCollect(wall_lines, degenerate, caps_v, caps_h,
                        cap_handles_v, cap_handles_h, all_handles, source_x, source_y)


def _g2_conservation(collect: _WallCollect, tols: _Tols,
                     diags: list[ConversionDiagnosticV1]) -> bool:
    """G2: quantize may denoise but must not merge two coords > tau_node apart."""
    ok = True
    tau = tols.node_join_native
    for axis_name, table in (("x", collect.source_x), ("y", collect.source_y)):
        for snap, sources in table.items():
            if len(sources) < 2:
                continue
            lo, hi = min(sources), max(sources)
            if hi - lo > tau:
                _add(diags, _diag("tarch_quantization_conflict",
                                  points_dxf_mm=[(snap, snap)] if axis_name == "x" else [(snap, snap)],
                                  context={"axis": axis_name, "snap": snap,
                                           "min_source": lo, "max_source": hi,
                                           "gap": hi - lo}))
                ok = False
    return ok


def _build_wall_bands(collect: _WallCollect) -> list[WallBand]:
    """Group jamb caps into wall bands (one per unique cross-section)."""
    bands: list[WallBand] = []
    # horizontal-wall bands: caps_v groups by y cross-section; run along x.
    by_cs_v: dict[tuple[float, float], list[tuple[float, list[str]]]] = {}
    for xcoord, spans in collect.caps_v.items():
        for span in spans:
            by_cs_v.setdefault(span, []).append((xcoord, collect.cap_handles_v[xcoord][span]))
    for (ylo, yhi), members in sorted(by_cs_v.items()):
        xs = [m[0] for m in members]
        handles = sorted({h for _, hs in members for h in hs})
        bands.append(WallBand(axis="x", face_lo_mm=ylo, face_hi_mm=yhi,
                              along_min_mm=min(xs), along_max_mm=max(xs),
                              thickness_mm=yhi - ylo, cap_handles=handles))
    # vertical-wall bands: caps_h groups by x cross-section; run along y.
    by_cs_h: dict[tuple[float, float], list[tuple[float, list[str]]]] = {}
    for ycoord, spans in collect.caps_h.items():
        for span in spans:
            by_cs_h.setdefault(span, []).append((ycoord, collect.cap_handles_h[ycoord][span]))
    for (xlo, xhi), members in sorted(by_cs_h.items()):
        ys = [m[0] for m in members]
        handles = sorted({h for _, hs in members for h in hs})
        bands.append(WallBand(axis="y", face_lo_mm=xlo, face_hi_mm=xhi,
                              along_min_mm=min(ys), along_max_mm=max(ys),
                              thickness_mm=xhi - xlo, cap_handles=handles))
    bands.sort(key=lambda b: b.band_id)
    return bands


# --------------------------------------------------------------------------- #
# S3 — opening dual-evidence resolution
# --------------------------------------------------------------------------- #
def _classify_block(name: str, dialect: TarchDialectRulesV1) -> Literal["window", "door"] | None:
    is_window = name in dialect.window_block_names
    is_door = any(name.startswith(pref) for pref in dialect.door_block_prefixes)
    if is_window == is_door:  # both true is ambiguous; both false is unresolved
        return None
    return "window" if is_window else "door"


def _resolve_one(ext_x0: float, ext_y0: float, ext_x1: float, ext_y1: float,
                 caps_v: dict[float, set[tuple[float, float]]],
                 caps_h: dict[float, set[tuple[float, float]]]) -> list[tuple[Literal["x", "y"], float, float, float, float]]:
    """Dual evidence: try both axes; a solution = a jamb-cap pair at (lo,hi) with an
    identical cross-section [c1,c2] that the bbox's normal extent overlaps."""
    solutions: list[tuple[Literal["x", "y"], float, float, float, float]] = []
    # axis = x : opening spans x[lo,hi]; caps are vertical (caps_v) at x=lo and x=hi,
    #            cross-section is a y-interval; bbox normal extent is its y-range.
    for axis, lo, hi, caps, normal_lo, normal_hi in (
            ("x", ext_x0, ext_x1, caps_v, ext_y0, ext_y1),
            ("y", ext_y0, ext_y1, caps_h, ext_x0, ext_x1)):
        a_set = caps.get(lo, set())
        b_set = caps.get(hi, set())
        for a in a_set:
            for b in b_set:
                if a == b:  # identical cross-section => same wall band both ends
                    c1, c2 = a
                    if _overlap(c1, c2, normal_lo, normal_hi) > 0:
                        solutions.append((axis, lo, hi, c1, c2))
    return solutions


def s3_resolve_openings(msp, plan_view: PlanViewIntentV1, request: TarchConversionRequestV1,
                        clip: tuple[float, float, float, float], tols: _Tols,
                        collect: _WallCollect,
                        diags: list[ConversionDiagnosticV1]) -> tuple[list[ResolvedOpening], list[tuple[tuple[float, float], tuple[float, float]]]]:
    q = tols.quant_native
    opening_layers = set(plan_view.opening_selector.layers)
    opening_types = set(plan_view.opening_selector.entity_types)
    dialect = plan_view.dialect_rules

    openings: list[ResolvedOpening] = []
    fills: list[tuple[tuple[float, float], tuple[float, float]]] = []
    raw = []
    for e in msp:
        if e.dxf.layer not in opening_layers:
            continue
        if e.dxftype() not in opening_types:
            _add(diags, _diag("tarch_entity_unsupported",
                              handles=[e.dxf.handle],
                              context={"dxftype": e.dxftype(), "role": "opening"}))
            continue
        raw.append(e)
    raw.sort(key=lambda e: e.dxf.handle)

    for e in raw:
        ext = ezdxf_bbox.extents([e])
        sx0, sy0 = float(ext.extmin.x), float(ext.extmin.y)
        sx1, sy1 = float(ext.extmax.x), float(ext.extmax.y)
        cx, cy = (sx0 + sx1) / 2.0, (sy0 + sy1) / 2.0
        if not _point_strictly_inside(cx, cy, clip):
            continue
        x0, y0 = _quantize(sx0, q), _quantize(sy0, q)
        x1, y1 = _quantize(sx1, q), _quantize(sy1, q)
        kind = _classify_block(e.dxf.name, dialect)
        if kind is None:
            _add(diags, _diag("tarch_opening_kind_ambiguous",
                              handles=[e.dxf.handle],
                              context={"block_name": e.dxf.name}))
            continue
        sols = _resolve_one(x0, y0, x1, y1, collect.caps_v, collect.caps_h)
        if len(sols) == 0:
            _add(diags, _diag("tarch_opening_block_unresolved",
                              handles=[e.dxf.handle],
                              points_dxf_mm=[(x0, y0), (x1, y1)],
                              context={"block_name": e.dxf.name, "kind": kind}))
            continue
        if len(sols) > 1:
            _add(diags, _diag("tarch_opening_block_ambiguous",
                              handles=[e.dxf.handle],
                              points_dxf_mm=[(x0, y0), (x1, y1)],
                              context={"block_name": e.dxf.name, "kind": kind,
                                       "candidate_count": len(sols)}))
            continue
        axis, lo, hi, c1, c2 = sols[0]
        if axis == "x":
            rect = (lo, c1, hi, c2)
            cross = (c1, c2)
        else:
            rect = (c1, lo, c2, hi)
            cross = (c1, c2)
        jamb_handles: list[str] = []
        caps_table = collect.cap_handles_v if axis == "x" else collect.cap_handles_h
        for coord in (lo, hi):
            hs = caps_table.get(coord, {}).get(cross, [])
            jamb_handles.extend(hs)
        jamb_handles = sorted(set(jamb_handles))
        op = ResolvedOpening(handle=e.dxf.handle, block_name=e.dxf.name, kind=kind,
                             rect_dxf_mm=rect, axis=axis, cross_section_mm=cross,
                             jamb_handles=jamb_handles)
        openings.append(op)
        fills.extend(op.fill_edges())
    openings.sort(key=lambda o: o.handle)
    return openings, fills


# --------------------------------------------------------------------------- #
# S4 — topology closure + area conservation (G5)
# --------------------------------------------------------------------------- #
def s4_close_topology(wall_lines: list[tuple[str, float, float, float, float]],
                      fills: list[tuple[tuple[float, float], tuple[float, float]]],
                      tols: _Tols):
    mpu = tols.metres_per_unit
    segs: list[LineString] = []
    for _, x0, y0, x1, y1 in wall_lines:
        segs.append(LineString([(x0, y0), (x1, y1)]))
    for a, b in fills:
        segs.append(LineString([a, b]))
    polygons, cuts, dangles, invalid = polygonize_full(unary_union(segs))
    faces = list(polygons.geoms)
    dangle_geoms = list(dangles.geoms)
    cut_geoms = list(cuts.geoms)
    invalid_geoms = list(invalid.geoms)
    footprint = unary_union(faces) if faces else Polygon()
    sum_area_native = sum(g.area for g in faces)
    footprint_area_native = footprint.area
    return {"faces": faces, "dangles": dangle_geoms, "cuts": cut_geoms,
            "invalid": invalid_geoms, "n_dangles": len(dangle_geoms),
            "n_cuts": len(cut_geoms), "n_invalid": len(invalid_geoms),
            "sum_area_m2": sum_area_native * mpu * mpu,
            "footprint_area_m2": footprint_area_native * mpu * mpu,
            "footprint": footprint}


# --------------------------------------------------------------------------- #
# exterior / interior classification (D5) — needs the S4 footprint
# --------------------------------------------------------------------------- #
def _classify_openings(openings: list[ResolvedOpening], footprint: Any,
                       tols: _Tols, diags: list[ConversionDiagnosticV1]) -> None:
    """An opening is EXTERIOR iff its outward wall face lies on the footprint
    exterior boundary (within tau_node).  Interior openings are INFO-excluded.

    Robust to a non-clean topology (a red fixture may leave a MultiPolygon): we
    classify against the largest constituent polygon.  Classification is moot
    when topology is broken (the report is BLOCKED anyway), but it must not crash.
    """
    from shapely.geometry import MultiPolygon, Polygon as _Poly
    if footprint.is_empty:
        return
    poly = footprint
    if isinstance(footprint, MultiPolygon):
        poly = max(footprint.geoms, key=lambda g: g.area)
    if not isinstance(poly, _Poly):
        return
    tau = tols.node_join_native
    skin = poly.exterior
    rep = poly.representative_point()
    for op in openings:
        x0, y0, x1, y1 = op.rect_dxf_mm
        c1, c2 = op.cross_section_mm
        # outward face = the cross-section coord farther from the footprint interior
        if op.axis == "x":  # wall runs along x; cross-section is y; sample at mid-x
            mid_along = (x0 + x1) / 2.0
            outward = c2 if abs(c2 - rep.y) >= abs(c1 - rep.y) else c1
            probe = (mid_along, outward)
        else:  # wall runs along y; cross-section is x; sample at mid-y
            mid_along = (y0 + y1) / 2.0
            outward = c2 if abs(c2 - rep.x) >= abs(c1 - rep.x) else c1
            probe = (outward, mid_along)
        on_skin = skin.distance(Point(probe)) <= tau
        op.classification = "exterior" if on_skin else "interior_excluded"
        if op.classification == "interior_excluded":
            _add(diags, _diag("tarch_interior_opening_excluded",
                              handles=[op.handle],
                              points_dxf_mm=[probe],
                              context={"kind": op.kind, "rect": list(op.rect_dxf_mm)}))


# --------------------------------------------------------------------------- #
# S4 diagnostics — emit fail-closed codes for topology residuals (G5)
# --------------------------------------------------------------------------- #
def _emit_s4_diagnostics(s4: dict, tols: _Tols, diags: list[ConversionDiagnosticV1]) -> None:
    """Turn topology residuals into localizable BLOCK diagnostics.

    Dangling segments => a free-end / unfilled gap (``tarch_wall_free_end``); the
    converter never auto-extends (that would slice a corridor — Q5).  Non-zero
    cuts/invalid or an area mismatch => ``tarch_topology_residual``.  Each is
    localized on a real residual endpoint (never a placeholder).
    """
    if s4["n_dangles"] > 0:
        first = s4["dangles"][0]
        pt = tuple(c[:2] for c in first.coords)[0]
        _add(diags, _diag("tarch_wall_free_end",
                          points_dxf_mm=[pt],
                          context={"dangle_count": s4["n_dangles"]}))
    if s4["n_cuts"] > 0 or s4["n_invalid"] > 0:
        geoms = s4["cuts"] or s4["invalid"]
        pt = tuple(c[:2] for c in geoms[0].coords)[0] if geoms else (0.0, 0.0)
        _add(diags, _diag("tarch_topology_residual",
                          points_dxf_mm=[pt],
                          context={"cuts": s4["n_cuts"], "invalid": s4["n_invalid"]}))
    if abs(s4["sum_area_m2"] - s4["footprint_area_m2"]) > tols.topo_area_m2:
        fp = s4["footprint"]
        pt = (fp.centroid.x, fp.centroid.y) if not fp.is_empty else (0.0, 0.0)
        _add(diags, _diag("tarch_topology_residual",
                          points_dxf_mm=[pt],
                          context={"sum_area_m2": s4["sum_area_m2"],
                                   "footprint_area_m2": s4["footprint_area_m2"],
                                   "delta_m2": abs(s4["sum_area_m2"] - s4["footprint_area_m2"])}))


# --------------------------------------------------------------------------- #
# Orchestrator — run S0-S4 for one plan view
# --------------------------------------------------------------------------- #
def run_p1_plan_view(dxf_path: Path, request: TarchConversionRequestV1,
                     plan_view: PlanViewIntentV1, tooling) -> P1PlanViewGeometry:
    """Run S0-S4 on one plan view.  Pure: reads the DXF, returns geometry + diags.

    The DXF path MUST be a staging path (not a protected answer/source root);
    the staging discipline is enforced structurally (§0.1 方案A).
    """
    assert_staging_input(Path(dxf_path))
    tols = _tols_from(tooling, request.metres_per_unit)
    diags: list[ConversionDiagnosticV1] = []
    actual_sha = hashlib.sha256(Path(dxf_path).read_bytes()).hexdigest()
    request_hash_ok = request.request_sha256 == compute_request_sha256(request)
    ownership_ok = (plan_view.id in {v.id for v in request.plan_views}
                    and any(f.id == plan_view.floor_id for f in request.floors)
                    and any(v.id == plan_view.id and v.floor_id == plan_view.floor_id
                            for v in request.plan_views))
    if actual_sha != request.source_dxf_sha256 or not request_hash_ok or not ownership_ok:
        _add(diags, _diag("tarch_input_source_hash_mismatch", points_dxf_mm=[(0.0, 0.0)], context={
            "actual_source_sha256": actual_sha, "declared_source_sha256": request.source_dxf_sha256,
            "request_hash_ok": request_hash_ok, "plan_view_id": plan_view.id,
            "floor_id": plan_view.floor_id, "ownership_ok": ownership_ok}))
        empty = P1PlanViewGeometry(plan_view.id, plan_view.floor_id, tols.quant_native,
            [], 0, {}, {}, {}, {}, [], [], [], [], 0, 0, 0, 0.0, 0.0, Polygon(), diags)
        _assemble_gates(empty, False, False, tols)
        return empty
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    cb = plan_view.clip_box_dxf
    clip = (float(cb.xmin), float(cb.ymin), float(cb.xmax), float(cb.ymax))

    s0_ok, _titles = s0_preflight(doc, msp, plan_view, request, tols, diags)

    collect = _collect_walls(msp, plan_view, request, clip, tols, diags)
    g2_ok = _g2_conservation(collect, tols, diags)
    bands = _build_wall_bands(collect)

    openings, fills = s3_resolve_openings(msp, plan_view, request, clip, tols, collect, diags)

    s4 = s4_close_topology(collect.wall_lines, fills, tols)
    _emit_s4_diagnostics(s4, tols, diags)
    _classify_openings(openings, s4["footprint"], tols, diags)

    result = P1PlanViewGeometry(
        view_id=plan_view.id, floor_id=plan_view.floor_id,
        quant_step_native=tols.quant_native,
        wall_lines=collect.wall_lines, degenerate_line_count=collect.degenerate,
        jamb_caps_v=collect.caps_v, jamb_caps_h=collect.caps_h,
        cap_handles_v=collect.cap_handles_v, cap_handles_h=collect.cap_handles_h,
        wall_bands=bands, openings=openings, opening_fills=fills,
        faces=s4["faces"], dangles=s4["n_dangles"], cuts=s4["n_cuts"], invalid=s4["n_invalid"],
        sum_area_m2=s4["sum_area_m2"], footprint_area_m2=s4["footprint_area_m2"],
        footprint_polygon=s4["footprint"],
        diagnostics=diags, all_wall_handles=collect.all_handles)

    _assemble_gates(result, s0_ok, g2_ok, tols)
    return result


def _assemble_gates(result: P1PlanViewGeometry, s0_ok: bool, g2_ok: bool, tols: _Tols) -> None:
    """Emit the P1 gates.  G1/G2/G3/G5 are real pass/fail gates here; G4 (the
    14==14 outer-skin gap conservation) is an S7 check and is NOT emitted at P1
    (the exterior/interior CLASSIFICATION is done, as INFO diagnostics, but the
    conservation gate lands in P2 — emitting a stub G4=pass would be a false-lock)."""
    # G1 input preflight
    g1 = all(d.code != "tarch_source_proxy_present"
             and d.code != "tarch_units_undeclared"
             and d.code != "tarch_view_frame_missing"
             and d.code != "tarch_view_frame_ambiguous"
             and d.code != "tarch_entity_unsupported"
             and d.code != "tarch_wall_nonorthogonal" for d in result.diagnostics) and s0_ok
    result.gates.append(GateResultV1(
        id="G1", name="input preflight", passed=g1,
        evidence={"proxy_present": any(d.code == "tarch_source_proxy_present" for d in result.diagnostics),
                  "frame_ok": not any(d.code in ("tarch_view_frame_missing", "tarch_view_frame_ambiguous") for d in result.diagnostics)}))
    # G2 quantization conservation (the thickness-evidence coverage rigor — every
    # wall band fully evidenced — is P2 ribbon work; G2 at P1 is the conservation guard).
    result.gates.append(GateResultV1(
        id="G2", name="quantization conservation", passed=g2_ok,
        evidence={"quantization_conflict": any(d.code == "tarch_quantization_conflict" for d in result.diagnostics),
                  "jamb_caps_v": sum(len(v) for v in result.jamb_caps_v.values()),
                  "jamb_caps_h": sum(len(v) for v in result.jamb_caps_h.values()),
                  "wall_bands_evidenced": len(result.wall_bands)}))
    # G3 opening dual evidence
    unresolved = sum(1 for d in result.diagnostics if d.code in
                     ("tarch_opening_block_unresolved", "tarch_opening_block_ambiguous",
                      "tarch_opening_kind_ambiguous"))
    g3 = unresolved == 0
    result.gates.append(GateResultV1(
        id="G3", name="opening dual evidence", passed=g3,
        evidence={"resolved": len(result.openings), "unresolved_or_ambiguous": unresolved,
                  "exterior": sum(1 for o in result.openings if o.classification == "exterior"),
                  "interior_excluded": sum(1 for o in result.openings if o.classification == "interior_excluded")}))
    # G5 topology closure + area conservation
    area_ok = abs(result.sum_area_m2 - result.footprint_area_m2) <= tols.topo_area_m2
    g5 = result.dangles == 0 and result.cuts == 0 and result.invalid == 0 and area_ok
    result.gates.append(GateResultV1(
        id="G5", name="topology closure + area conservation", passed=g5,
        evidence={"faces": len(result.faces), "dangles": result.dangles,
                  "cuts": result.cuts, "invalid": result.invalid,
                  "sum_area_m2": result.sum_area_m2,
                  "footprint_area_m2": result.footprint_area_m2}))
    result.gates = _apply_test_neuter(result.gates)


# --------------------------------------------------------------------------- #
# Report builder — exercise the P0 contract with the P1 geometry
# --------------------------------------------------------------------------- #
def converter_sha256() -> str:
    """sha256 of this module's source (the converter implementation fingerprint)."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def build_p1_report(result: P1PlanViewGeometry, request: TarchConversionRequestV1,
                    plan_view: PlanViewIntentV1, tooling,
                    source_dxf_sha256: str) -> ConversionReportV1:
    """Build a ConversionReportV1 from the P1 geometry.

    P1 does not write an augmented normalized DXF (that is P2 S9); the
    normalization (quantization + opening fills) lives in the IR and is verified
    by gates G1-G5.  ``normalized_dxf_sha256`` is therefore bound to the *source*
    bytes at this stage and rebound to the augmented normalized.dxf in P2.
    """
    # WallBand field names retain the historical ``*_mm`` spelling, but P1 IR is
    # always in request-native units.  Reports must use the declared conversion,
    # not assume native DXF units are millimetres.
    mpu = request.metres_per_unit
    walls = [
        WallReportV1(
            band_id=b.band_id, floor_id=result.floor_id, axis=b.axis,
            coord_mm=b.coord_mm, span_mm=[b.along_min_mm, b.along_max_mm],
            segments=[WallRibbonSegmentV1(
                segment_id=b.band_id + "_s0", axis=b.axis, coord_m=b.coord_mm * mpu,
                span_m=[b.along_min_mm * mpu, b.along_max_mm * mpu],
                thickness_evidence=ThicknessEvidenceV1(
                    source_kind="wall_cap_or_opening_jamb",
                    value_m=b.thickness_mm * mpu,
                    proof_handles=b.cap_handles))],
            source_handles=b.cap_handles)
        for b in result.wall_bands]
    openings_report = [
        OpeningReportV1(
            opening_id=f"op_{o.handle.lower()}", kind=o.kind,
            classification=o.classification,
            rect_mm=list(o.rect_dxf_mm), block_handle=o.handle, block_name=o.block_name,
            jamb_handles=o.jamb_handles, geometric_witness=True)
        for o in result.openings]
    has_block = result.has_block
    status: Literal["PASS", "BLOCKED"] = "BLOCKED" if has_block else "PASS"
    return ConversionReportV1(
        report_version=1, status=status, case=request.case,
        source_dxf_sha256=source_dxf_sha256,
        normalized_dxf_sha256=(source_dxf_sha256 if status == "PASS" else None),
        request_sha256=request.request_sha256,
        judge_config_sha256=tooling.judge_config_sha256,
        vg_config_sha256=tooling.vg_config_sha256,
        converter_sha256=converter_sha256(),
        profile_version=1, quantization_step_m=derive_quantization_step(tooling),
        walls=walls, openings=openings_report,
        gates=result.gates, diagnostics=result.diagnostics,
        wall_proof_coverage={"wall_lines": len(result.wall_lines),
                             "wall_bands_evidenced": len(result.wall_bands),
                             "degenerate_lines": result.degenerate_line_count})


# =========================================================================== #
# P2 — S5..S9 (cavity -> intent -> per-edge expand -> nine gates -> persist)
#
# Geometry is carried in DXF *native* units (mm for sm24) and converted to
# world metres only at the report/manifest/overlay/seed boundary via _to_world.
#
# G8 (the reconstruction gate) is the highest-risk piece of this batch (plan §1
# G8 reinforcement, dispatch §2 #5).  It is implemented as an INDEPENDENT
# inverse: from the OUTPUT zone polygon + each edge's recorded basis+thickness
# it rebuilds the wall region and compares it to the S5-measured wall region.
# It NEVER reads S5's WallRegion or anything derived from it — rebuilding from
# ∪zones − ∪(reverse-shrunk zones), where the shrink uses only the zone output
# + recorded per-edge offsets, would otherwise collapse to the
# Footprint − Σzones tautology = a permanent false-green (plan §1).
# =========================================================================== #


@dataclass
class _ZoneEdgeRec:
    """One emitted zone-boundary edge (between consecutive zone vertices).

    ``basis`` is ``None`` for a thickness-change *step* edge (offset 0, no basis);
    wall edges carry their basis + measured thickness + outward offset.
    """
    nx: float            # outward normal x component (out of the zone)
    ny: float
    basis: EdgeBasis | None
    thickness_native: float | None
    offset_native: float   # t (outer_skin) | t/2 (wall_axis) | 0 (step)
    p1: tuple[float, float] | None = None
    p2: tuple[float, float] | None = None
    thickness_evidence: ThicknessEvidenceV1 | None = None
    # DXF handles of the SOURCE wall lines this edge derives from (the inner-face
    # wall line(s) the cavity edge lies on).  Carried so the report's source_handles
    # and the per-edge source_map ancestry are REAL handles, not a layer label.
    source_handles: list[str] = field(default_factory=list)


@dataclass
class ZoneExpansion:
    """S7 output for one zone: its polygon (native) + per-edge records + cavity."""
    cavity_id: str
    polygon: Any                # shapely Polygon (native units)
    vertices: list[tuple[float, float]]   # zone polygon verts (native, ordered, CCW)
    edges: list[_ZoneEdgeRec]   # parallel: edge vertices[i] -> vertices[i+1]
    seed_native: tuple[float, float]
    area_m2: float


@dataclass
class P2ConversionResult:
    """Everything P2 derives for one plan view: zones, gates, report, persist artefacts."""
    p1: P1PlanViewGeometry
    cavities: list[Any]              # shapely Polygons (native), area > A_room
    wall_region: Any                 # unary_union of wall-material faces (native)
    footprint: Any                   # unary_union of all faces (native)
    near_threshold_faces: list[dict] # [{area_m2, centroid_world_m}] in [0.5*A_room, 2*A_room]
    zones: list[ZoneExpansion]
    claims: list[dict]               # parallel to zones: intent binding per zone
    gates: list[GateResultV1]
    diagnostics: list[ConversionDiagnosticV1]
    manifest: Any = None             # GtExtractionManifestV1 (built in S9)
    augmented_dxf_path: Path | None = None
    conversion_report: ConversionReportV1 | None = None
    source_map: Any = None           # SourceMapV1
    overlay_path: Path | None = None
    gtv3_handles: dict | None = None                    # {layer: [handles]}
    gtv3_zone_edge_handles: dict | None = None          # {(zone_idx, edge_idx): handle}
    elevation_records: list[_ElevationRecord] = field(default_factory=list)
    elevation_audit_rows: list[dict] = field(default_factory=list)

    @property
    def has_block(self) -> bool:
        return any(d.severity == DiagnosticSeverity.BLOCK for d in self.diagnostics)


def _clean_collinear(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Remove collinear vertices (plan §4 S7: degenerate-redundant removal)."""
    c = list(coords)
    changed = True
    while changed:
        changed = False
        for i in range(len(c)):
            a, b, d = c[i - 1], c[i], c[(i + 1) % len(c)]
            if (a[0] == b[0] == d[0]) or (a[1] == b[1] == d[1]):
                c.pop(i); changed = True; break
    return c


def _ensure_ccw(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not Polygon(coords).exterior.is_ccw:
        return coords[::-1]
    return coords


def _outward_normal(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Outward (right-hand) normal of a directed CCW orthogonal edge a->b."""
    if a[1] == b[1]:          # horizontal edge
        return (0.0, -1.0) if b[0] > a[0] else (0.0, 1.0)
    return (1.0, 0.0) if b[1] > a[1] else (-1.0, 0.0)


def _ray_thickness(mid: tuple[float, float], nx: float, ny: float,
                   wall_region: Any, footprint: Any, tols: _Tols) -> tuple[float, bool] | None:
    """Exact ray/boundary intersection; no native-unit march or range-derived pad."""
    minx, miny, maxx, maxy = unary_union([wall_region, footprint]).bounds
    reach = max(maxx - minx, maxy - miny) * 2.0 + tols.node_join_native
    ray = LineString([mid, (mid[0] + nx * reach, mid[1] + ny * reach)])
    hit = ray.intersection(wall_region.boundary)
    pts = []
    if hit.geom_type == "Point":
        pts = [hit]
    elif hasattr(hit, "geoms"):
        pts = [g for g in hit.geoms if g.geom_type == "Point"]
    eps = tols.node_join_native
    ds = sorted((p.x - mid[0]) * nx + (p.y - mid[1]) * ny for p in pts)
    ds = [d for d in ds if d > eps]
    if not ds:
        return None
    thickness = ds[0]
    exit_pt = Point(mid[0] + nx * thickness, mid[1] + ny * thickness)
    return thickness, footprint.exterior.distance(exit_pt) <= tols.node_join_native


def _thickness_profile(a: tuple[float, float], b: tuple[float, float],
                       nx: float, ny: float, wall_region: Any, footprint: Any,
                       tols: _Tols) -> list[tuple[tuple[float, float], tuple[float, float], float, EdgeBasis]]:
    """Per-segment thickness along edge a->b, split where thickness or basis
    changes (plan §4 S7-3).

    Returns ordered [(sub_start, sub_end, thickness, basis)] in native units.
    Uniform edges -> one segment (every sm24 edge).  A wall whose thickness
    changes mid-span -> multiple segments, each with its own measured thickness
    (real wall-pier step geometry).

    Event coordinates are projections of WallRegion boundary vertices onto the
    cavity edge.  Each open event interval is measured once at its midpoint, so
    a thickness change is located at the actual CAD coordinate, not a sample pad.
    """
    ax, ay = a
    bx, by = b

    def measure(f: float) -> tuple[float, EdgeBasis] | None:
        x, y = ax + (bx - ax) * f, ay + (by - ay) * f
        hit = _ray_thickness((x, y), nx, ny, wall_region, footprint, tols)
        if hit is None:
            return None
        t, ext = hit
        return (t, "outer_skin" if ext else "wall_axis")

    def same(p: tuple[float, EdgeBasis], q: tuple[float, EdgeBasis]) -> bool:
        return abs(p[0] - q[0]) <= tols.axis_align_native and p[1] == q[1]
    length = abs(bx - ax) if ay == by else abs(by - ay)
    events = {0.0, 1.0}
    for geom in getattr(wall_region.boundary, "geoms", [wall_region.boundary]):
        for x, y in getattr(geom, "coords", []):
            f = ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / (length * length)
            if tols.node_join_native / length < f < 1.0 - tols.node_join_native / length:
                # Only vertices in the normal wall slab can split this ray profile.
                px, py = ax + (bx - ax) * f, ay + (by - ay) * f
                if abs((x - px) * nx + (y - py) * ny) >= -tols.node_join_native:
                    events.add(round(f, 12))
    fs = sorted(events)
    out: list[tuple[tuple[float, float], tuple[float, float], float, EdgeBasis]] = []
    for f0, f1 in zip(fs, fs[1:]):
        m = measure((f0 + f1) / 2.0)
        if m is None:
            continue
        seg = ((ax + (bx - ax) * f0, ay + (by - ay) * f0),
               (ax + (bx - ax) * f1, ay + (by - ay) * f1), m[0], m[1])
        if out and same((out[-1][2], out[-1][3]), m):
            out[-1] = (out[-1][0], seg[1], out[-1][2], out[-1][3])
        else:
            out.append(seg)
    return out


def _offset_for(basis: EdgeBasis, thickness: float) -> float:
    return thickness if basis == "outer_skin" else thickness / 2.0


def _shift(pt: tuple[float, float], nx: float, ny: float, off: float) -> tuple[float, float]:
    return (pt[0] + nx * off, pt[1] + ny * off)


def _corner(v: tuple[float, float], n1: tuple[float, float], off1: float,
            n2: tuple[float, float], off2: float) -> tuple[float, float]:
    """Vertex = cavity vertex shifted by off1 along n1 and off2 along n2 (perpendicular)."""
    return (v[0] + n1[0] * off1 + n2[0] * off2, v[1] + n1[1] * off1 + n2[1] * off2)


def _edge_source_handles(a: tuple[float, float], b: tuple[float, float],
                         wall_lines, tols: _Tols) -> list[str]:
    """DXF handles of the SOURCE wall LINEs whose line the axis-aligned cavity edge
    a->b lies on.  A cavity boundary edge IS a (sub-span of a) source wall line — the
    inner face of the wall bounding that cavity — so matching axis+coord+span-overlap
    recovers the real source handle(s).  Used for honest per-edge ancestry (report
    ``source_handles`` + source_map); never a criterion.

    Wall LINEs may be drawn in either direction (x1<x0), so their span is taken as
    min/max — a segment fully inside the cavity edge is still a valid source."""
    ta = tols.axis_align_native
    out: list[str] = []
    if a[1] == b[1]:                       # horizontal cavity edge at y == a[1]
        yc, lo, hi = a[1], min(a[0], b[0]), max(a[0], b[0])
        for h, x0, y0, x1, y1 in wall_lines:
            if abs(y0 - yc) <= ta and abs(y1 - yc) <= ta:
                wlo, whi = min(x0, x1), max(x0, x1)
                if whi > lo + ta and wlo < hi - ta:        # spans overlap (non-trivial)
                    out.append(h)
    else:                                   # vertical cavity edge at x == a[0]
        xc, lo, hi = a[0], min(a[1], b[1]), max(a[1], b[1])
        for h, x0, y0, x1, y1 in wall_lines:
            if abs(x0 - xc) <= ta and abs(x1 - xc) <= ta:
                wlo, whi = min(y0, y1), max(y0, y1)
                if whi > lo + ta and wlo < hi - ta:
                    out.append(h)
    return out


# --------------------------------------------------------------------------- #
# S5 — cavity identification (area bisection) + wall region + outer skin
# --------------------------------------------------------------------------- #
def s5_identify_cavities(p1: P1PlanViewGeometry, request: TarchConversionRequestV1,
                         tols: _Tols, diags: list[ConversionDiagnosticV1],
                         affine: Affine2D) -> tuple[list[Any], Any, Any, list[dict]]:
    """Area bisection: faces > A_room are cavities; the rest union to the wall region.

    A_room is a DOMAIN PARAMETER (proposal only, never a criterion — plan §2.2);
    the criterion is the human-declared room count (G6).  Multiple disjoint exterior
    rings -> ``tarch_footprint_multiple`` (no 'take largest'); an interior ring ->
    ``tarch_profile_hole_unsupported``.  The near-threshold face list
    [0.5*A_room, 2*A_room] is computed unconditionally (承重 gate evidence, §2.2 C4).
    """
    mpu = tols.metres_per_unit
    a_room_mm2 = request.min_room_area_m2 / (mpu * mpu)
    faces = p1.faces
    cavities = [g for g in faces if g.area > a_room_mm2]
    wall_faces = [g for g in faces if g.area <= a_room_mm2]
    wall_region = unary_union(wall_faces) if wall_faces else Polygon()
    footprint = unary_union(faces) if faces else Polygon()

    # Outer-skin shape checks (plan §2.3): the simple-connected, no-hole cases S7
    # runs in are exactly those where unary_union == unbounded flood-fill outer skin
    # (plan §7b C2); the inequivalent cases (multipolygon / holes) are blocked here.
    if footprint.geom_type == "MultiPolygon" or (
            footprint.geom_type == "Polygon" and footprint.interiors):
        # localise on the first offending ring's representative point
        if footprint.geom_type == "MultiPolygon":
            rep = max(footprint.geoms, key=lambda g: g.area).representative_point()
            _add(diags, _diag("tarch_footprint_multiple",
                              points_dxf_mm=[(rep.x, rep.y)],
                              context={"component_count": len(footprint.geoms)}))
        else:
            ir = footprint.interiors[0]
            _add(diags, _diag("tarch_profile_hole_unsupported",
                              points_dxf_mm=[(ir.centroid.x, ir.centroid.y)],
                              context={"interior_ring_count": len(footprint.interiors)}))

    # Near-threshold承重 face list (always computed, not only on failure).
    lo, hi = 0.5 * a_room_mm2, 2.0 * a_room_mm2
    near: list[dict] = []
    for g in faces:
        if lo <= g.area <= hi:
            wpt = _to_world((g.centroid.x, g.centroid.y), affine)
            near.append({"area_m2": g.area * mpu * mpu, "centroid_world_m": wpt,
                         "is_cavity": g.area > a_room_mm2})
    near.sort(key=lambda d: d["area_m2"])
    return cavities, wall_region, footprint, near


# --------------------------------------------------------------------------- #
# S6 — intent binding (cavities <-> human-declared ZoneIntentSpecV1)
# --------------------------------------------------------------------------- #
def s6_bind_intent(cavities: list[Any], plan_view: PlanViewIntentV1,
                   tols: _Tols, diags: list[ConversionDiagnosticV1],
                   affine: Affine2D) -> list[dict]:
    """Bind cavities to the human-declared room list.  Coordinates come from the
    machine (cavity representative point); count+name come from the human
    (plan §4 S6 / §5.5 — the single non-mechanical step).  No auto-A_room."""
    intent = plan_view.zone_intent
    # canonical order: (minx, miny) of cavity bounds (plan §5.5)
    ordered = sorted(enumerate(cavities),
                     key=lambda kv: (round(kv[1].bounds[0], 6), round(kv[1].bounds[1], 6)))
    expected = intent.expected_count
    if len(cavities) != expected:
        reps = [_to_world((g.representative_point().x, g.representative_point().y), affine)
                for _, g in ordered]
        _add(diags, _diag("tarch_cavity_count_mismatch",
                          points_dxf_mm=[(g.representative_point().x, g.representative_point().y)
                                         for _, g in ordered[:8]],
                          context={"cavity_count": len(cavities), "expected_count": expected,
                                   "cavity_centroids_world_m": reps}))
        return []
    # void declarations remove a cavity from the zone set (no voids on sm24)
    void_pts = [(v.point_world_m[0], v.point_world_m[1]) for v in plan_view.void_intent]
    claims: list[dict] = []
    for idx, (orig_i, g) in enumerate(ordered):
        entry = intent.entries[idx]
        is_void = any(g.contains(Point(*_world_to_native(wp, affine))) for wp in void_pts)
        if is_void:
            continue
        seed_native = (g.representative_point().x, g.representative_point().y)
        claims.append({"cavity": g, "cavity_index": orig_i,
                       "zone_id": entry.zone_id, "name": entry.name or entry.zone_id,
                       "role": entry.role, "seed_native": seed_native})
    # any cavity unclaimed (no entry) would already have failed the count gate
    if intent.mode == "intent_file" and not claims:
        _add(diags, _diag("tarch_cavity_unclaimed",
                          points_dxf_mm=[(c.representative_point().x, c.representative_point().y)
                                         for c in cavities[:8]]))
    return claims


def _world_to_native(world_xy: list[float], affine: Affine2D) -> tuple[float, float]:
    """Inverse of _to_world (seed world -> native), used only for void containment."""
    # affine is source->world; for a pure scale+offset sm24 affine the inverse is exact.
    a, b, c, d, e, f = affine.m00, affine.m01, affine.m02, affine.m10, affine.m11, affine.m12
    det = a * e - b * d
    wx, wy = world_xy
    return ((e * (wx - c) - b * (wy - f)) / det, (-d * (wx - c) + a * (wy - f)) / det)


# --------------------------------------------------------------------------- #
# S7 — per-edge expand to the mixed basis box (outer skin / wall axis)
# --------------------------------------------------------------------------- #
def _thickness_evidence_for(thickness_native: float, bands: list[WallBand],
                            tols: _Tols) -> ThicknessEvidenceV1 | None:
    """Resolve S7's measured value to an independent S2 cap/jamb proof."""
    for band in bands:
        if abs(band.thickness_mm - thickness_native) <= tols.axis_align_native and band.cap_handles:
            return ThicknessEvidenceV1(source_kind="wall_cap_or_opening_jamb",
                                       value_m=thickness_native * tols.metres_per_unit,
                                       proof_handles=band.cap_handles)
    return None


def s7_expand_zones(claims: list[dict], wall_region: Any, footprint: Any,
                    tols: _Tols, diags: list[ConversionDiagnosticV1],
                    wall_lines, wall_bands: list[WallBand] | None = None) -> list[ZoneExpansion]:
    """For each claimed cavity: clean+CCW, per-edge measure thickness + far-side
    classify (outer_skin -> offset t; wall_axis -> offset t/2), split edges on
    thickness change, rebuild the zone polygon from offset support-line corners +
    thickness-change steps (plan §4 S7).  L/T/cross/re-entrant joints need no
    special-case code; free-ends never reach here (S4 dangle gate).

    ``vertices`` and ``edges`` are parallel lists: ``edges[k]`` is the edge from
    ``vertices[k]`` to ``vertices[(k+1) % m]``.  This parallelism is what lets G8
    reverse-shrink the zone by subtracting each edge's recorded offset (the exact
    algebraic inverse of the expansion below).
    """
    mpu = tols.metres_per_unit
    zones: list[ZoneExpansion] = []
    for k, claim in enumerate(claims):
        g = claim["cavity"]
        c = _ensure_ccw(_clean_collinear([(p[0], p[1]) for p in list(g.exterior.coords)[:-1]]))
        n = len(c)
        subs_per_edge: list[list[tuple[tuple, tuple, float, EdgeBasis]]] = []
        normals: list[tuple[float, float]] = []
        edge_sources: list[list[str]] = []
        for i in range(n):
            a, b = c[i], c[(i + 1) % n]
            nx, ny = _outward_normal(a, b)
            normals.append((nx, ny))
            raw_profile = _thickness_profile(a, b, nx, ny, wall_region, footprint, tols)
            # A perpendicular T/cross wall can create a short ray interval through
            # the junction material.  It is not a thickness event unless it has an
            # independent S2 proof.  Collapse only such unproven junction runs into
            # their proven continuation; a genuine change must carry its own proof.
            proven = [_thickness_evidence_for(s[2], wall_bands or [], tols) is not None
                      for s in raw_profile]
            profile = list(raw_profile)
            for j, ok in enumerate(proven):
                if ok:
                    continue
                left = next((q for q in range(j - 1, -1, -1) if proven[q]), None)
                right = next((q for q in range(j + 1, len(profile)) if proven[q]), None)
                donor = left if right is None else right if left is None else (
                    left if profile[left][2:] == profile[right][2:] else None)
                if donor is None:
                    _add(diags, _diag("tarch_wall_thickness_unevidenced", points_dxf_mm=[profile[j][0], profile[j][1]],
                                      context={"thickness_native": profile[j][2], "reason": "event_interval_unproven"}))
                    continue
                profile[j] = (profile[j][0], profile[j][1], profile[donor][2], profile[donor][3])
                proven[j] = True
            merged: list[tuple[tuple, tuple, float, EdgeBasis]] = []
            for sub in profile:
                if merged and merged[-1][2:] == sub[2:]:
                    merged[-1] = (merged[-1][0], sub[1], sub[2], sub[3])
                else:
                    merged.append(sub)
            subs_per_edge.append(merged)
            # per-cavity-edge source ancestry (same for every sub of this cavity edge)
            edge_sources.append(_edge_source_handles(a, b, wall_lines, tols))
        offsets_per_edge = [[_offset_for(s[3], s[2]) for s in subs] for subs in subs_per_edge]

        zone_verts: list[tuple[float, float]] = []
        edges: list[_ZoneEdgeRec] = []
        for i in range(n):
            subs = subs_per_edge[i]
            offs = offsets_per_edge[i]
            nx, ny = normals[i]
            # corner_i (start of this edge's boundary); appended once (as corner_0),
            # thereafter it is the previous edge's appended end corner.
            if i == 0:
                zone_verts.append(_corner(c[0], normals[n - 1], offsets_per_edge[n - 1][-1],
                                          (nx, ny), offs[0]))
            # interior thickness-change splits -> wall sub-edge + step edge
            src = edge_sources[i]
            for j in range(len(subs) - 1):
                split_a = subs[j][1]
                proof = _thickness_evidence_for(subs[j][2], wall_bands or [], tols)
                if proof is None:
                    _add(diags, _diag("tarch_wall_thickness_unevidenced", handles=list(src),
                                      points_dxf_mm=[split_a],
                                      context={"thickness_native": subs[j][2]}))
                edges.append(_ZoneEdgeRec(nx, ny, subs[j][3], subs[j][2], offs[j],
                                          thickness_evidence=proof, source_handles=list(src)))
                zone_verts.append(_shift(split_a, nx, ny, offs[j]))
                edges.append(_ZoneEdgeRec(-ny, nx, None, None, 0.0))   # step, offset 0
                zone_verts.append(_shift(split_a, nx, ny, offs[j + 1]))
            # last sub -> end corner (start of next cavity edge)
            ni = (i + 1) % n
            end = _corner(c[ni], (nx, ny), offs[-1], normals[ni], offsets_per_edge[ni][0])
            proof = _thickness_evidence_for(subs[-1][2], wall_bands or [], tols)
            if proof is None:
                _add(diags, _diag("tarch_wall_thickness_unevidenced", handles=list(src),
                                  points_dxf_mm=[a, b],
                                  context={"thickness_native": subs[-1][2]}))
            edges.append(_ZoneEdgeRec(nx, ny, subs[-1][3], subs[-1][2], offs[-1],
                                      thickness_evidence=proof, source_handles=list(src)))
            if i != n - 1:
                zone_verts.append(end)
        zone_verts = [(round(vx, 6), round(vy, 6)) for vx, vy in zone_verts]
        poly = Polygon(zone_verts)
        if not poly.is_valid or poly.geom_type != "Polygon":
            _add(diags, _diag("tarch_edge_thickness_inconsistent", points_dxf_mm=zone_verts,
                              context={"reason": "expanded_polygon_invalid"}))
            continue
        for i, edge in enumerate(edges):
            edge.p1 = zone_verts[i]
            edge.p2 = zone_verts[(i + 1) % len(zone_verts)]
        zones.append(ZoneExpansion(
            cavity_id=f"c_{k:02d}", polygon=poly, vertices=zone_verts, edges=edges,
            seed_native=claim["seed_native"], area_m2=poly.area * mpu * mpu))
    return zones


# --------------------------------------------------------------------------- #
# G8 — INDEPENDENT reconstruction gate (the主保险)
# --------------------------------------------------------------------------- #
def g8_reconstruct_wall_region(zones: list[ZoneExpansion]) -> Any:
    """Rebuild the wall region from the OUTPUT zones + each edge's recorded basis+
    thickness ONLY (plan §1 G8 reinforcement, dispatch §2 #5).  Never reads S5's
    WallRegion or its derivatives.

    The normal is recomputed from persisted output ``p1 -> p2`` and offset from
    ``basis + thickness``.  In particular this function intentionally does not
    read ``nx``, ``ny`` or ``offset_native``: those are forward-pass caches and
    using either turns G8 into a tautological inverse.
    """
    zone_union = unary_union([z.polygon for z in zones]) if zones else Polygon()
    cav_recon: list[Any] = []
    for z in zones:
        e = z.edges
        m = len(e)
        if not m or any(edge.p1 is None or edge.p2 is None for edge in e):
            continue
        normals = [_outward_normal(edge.p1, edge.p2) for edge in e]
        offsets = [(_offset_for(edge.basis, edge.thickness_native)
                    if edge.basis is not None and edge.thickness_native is not None else 0.0)
                   for edge in e]
        cverts = []
        for i in range(m):
            vx, vy = e[i].p1
            pn, cn = normals[i - 1], normals[i]
            vx -= pn[0] * offsets[i - 1] + cn[0] * offsets[i]
            vy -= pn[1] * offsets[i - 1] + cn[1] * offsets[i]
            cverts.append((round(vx, 6), round(vy, 6)))
        poly = Polygon(cverts)
        if poly.is_valid and poly.geom_type == "Polygon" and not poly.is_empty:
            cav_recon.append(poly)
    cav_union = unary_union(cav_recon) if cav_recon else Polygon()
    return zone_union.difference(cav_union)


def _same_wall_consistency(zones: list[ZoneExpansion], tols: _Tols) -> tuple[bool, list[dict]]:
    """Pair back-to-back output edges by *overlap subinterval*, never whole edge.

    A long edge may face several shorter neighbour edges at T/cross junctions;
    every positive collinear overlap becomes its own evidence item.
    """
    records = []
    for zi, zone in enumerate(zones):
        for ei, edge in enumerate(zone.edges):
            if edge.basis is None or edge.thickness_native is None or edge.p1 is None or edge.p2 is None:
                continue
            nx, ny = _outward_normal(edge.p1, edge.p2)
            axis = "x" if edge.p1[1] == edge.p2[1] else "y"
            coord = edge.p1[1] if axis == "x" else edge.p1[0]
            span = sorted((edge.p1[0], edge.p2[0])) if axis == "x" else sorted((edge.p1[1], edge.p2[1]))
            records.append((zi, ei, edge, nx, ny, axis, coord, span))
    pairs: list[dict] = []
    for i, left in enumerate(records):
        for right in records[i + 1:]:
            zi, ei, e, nx, ny, axis, coord, span = left
            zj, ej, f, fx, fy, faxis, fcoord, fspan = right
            if zi == zj or axis != faxis or abs(coord - fcoord) > tols.axis_align_native:
                continue
            if abs(nx + fx) > 1e-12 or abs(ny + fy) > 1e-12:
                continue
            lo, hi = max(span[0], fspan[0]), min(span[1], fspan[1])
            if hi - lo <= tols.node_join_native:
                continue
            ok = e.basis == f.basis and abs(e.thickness_native - f.thickness_native) <= tols.axis_align_native
            pairs.append({"left": {"zone": zi, "edge": ei, "basis": e.basis, "thickness_native": e.thickness_native},
                          "right": {"zone": zj, "edge": ej, "basis": f.basis, "thickness_native": f.thickness_native},
                          "axis": axis, "coord_native": coord, "overlap_native": [lo, hi], "consistent": ok})
    return all(p["consistent"] for p in pairs), pairs


# --------------------------------------------------------------------------- #
# G4 — outer-skin gap conservation (exterior openings == outer-skin gaps)
# --------------------------------------------------------------------------- #
def _outer_skin_gap_count(p1: P1PlanViewGeometry, footprint: Any) -> int:
    """Count gaps in the RAW (unfilled) outer-skin wall lines along each exterior
    ring edge.  Each exterior opening breaks the outer skin once; the count must
    equal the exterior opening count (plan §5.2 G4 / SURVEY §3.2: 14==14)."""
    if footprint.is_empty or footprint.geom_type != "Polygon":
        return -1
    raw = list(footprint.exterior.coords)
    # The polygonized outer-skin ring carries a redundant collinear vertex at every
    # opening jamb: S4's opening fills close the wall gaps, so unary_union's exterior
    # boundary runs straight through each jamb with an extra vertex.  Counting gaps
    # per raw sub-edge would split each building side into many pieces and miscount
    # (sm24 west wall alone: 1 true edge -> ~10 jamb sub-edges -> ~10 false gaps).
    # Collapse to the true corner set first (sm24: 32 -> 4), then iterate sides.
    if raw and raw[0] == raw[-1]:
        raw = raw[:-1]
    ring = _clean_collinear([(p[0], p[1]) for p in raw])
    gaps = 0
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if a[0] != b[0] and a[1] != b[1]:
            continue  # profile only supports orthogonal rings
        if a[1] == b[1]:  # horizontal ring edge at y
            yc, lo, hi = a[1], min(a[0], b[0]), max(a[0], b[0])
            segs = sorted((min(x0, x1), max(x0, x1)) for _, x0, y0, x1, y1 in p1.wall_lines
                          if y0 == yc and y1 == yc
                          and not (max(x0, x1) <= lo or min(x0, x1) >= hi))
        else:            # vertical ring edge at x
            xc, lo, hi = a[0], min(a[1], b[1]), max(a[1], b[1])
            segs = sorted((min(y0, y1), max(y0, y1)) for _, x0, y0, x1, y1 in p1.wall_lines
                          if x0 == xc and x1 == xc
                          and not (max(y0, y1) <= lo or min(y0, y1) >= hi))
        # merge spans, count uncovered gaps strictly inside (lo, hi)
        merged = []
        for s in segs:
            if merged and s[0] <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], s[1]))
            else:
                merged.append(list(s))
        cursor = lo
        for s0, s1 in merged:
            if s0 - cursor > 1.0:
                gaps += 1
            cursor = max(cursor, s1)
        if hi - cursor > 1.0:
            gaps += 1
    return gaps


# --------------------------------------------------------------------------- #
# P2 gate assembly (G4/G6/G7/G8/G9/G10) — G1/G2/G3/G5 come from P1
# --------------------------------------------------------------------------- #
def _zone_polygon_world(z: ZoneExpansion, affine: Affine2D) -> list[tuple[float, float]]:
    return [_to_world(v, affine) for v in z.vertices]


def _build_p2_gates(p1: P1PlanViewGeometry, cavities, wall_region, footprint,
                    zones: list[ZoneExpansion], claims: list[dict],
                    near_threshold: list[dict], request, plan_view, tols,
                    diags: list[ConversionDiagnosticV1]) -> list[GateResultV1]:
    gates: list[GateResultV1] = []
    affine = plan_view.world_from_source_m
    mpu = tols.metres_per_unit

    # carry P1 gates forward
    gates.extend(p1.gates)

    # G4 outer-skin gap conservation
    ext_openings = [o for o in p1.openings if o.classification == "exterior"]
    skin_gaps = _outer_skin_gap_count(p1, footprint)
    g4 = skin_gaps >= 0 and skin_gaps == len(ext_openings)
    if not g4 and skin_gaps >= 0:
        fp_pt = footprint.representative_point()
        _add(diags, _diag("tarch_opening_skin_gap_mismatch",
                          points_dxf_mm=[(fp_pt.x, fp_pt.y)],
                          context={"exterior_openings": len(ext_openings), "outer_skin_gaps": skin_gaps}))
    gates.append(GateResultV1(id="G4", name="outer-skin gap conservation", passed=g4,
        evidence={"exterior_openings": len(ext_openings), "outer_skin_gaps": skin_gaps}))

    # G6 cavity claim + count + near-threshold承重 list
    count_ok = len(cavities) == plan_view.zone_intent.expected_count
    unclaimed = len(cavities) - len(claims)
    near_pending = bool(near_threshold)
    g6 = count_ok and unclaimed <= 0 and not near_pending and not any(
        d.code == "tarch_cavity_count_mismatch" for d in diags)
    gates.append(GateResultV1(id="G6", name="cavity claim + count", passed=g6,
        evidence={"cavity_count": len(cavities),
                  "expected_count": plan_view.zone_intent.expected_count,
                  "claimed": len(claims),
                  "near_threshold_faces": near_threshold,
                  "human_confirmation_required": near_pending}))

    # G7 tiling: ∪zones ≡ footprint, no pairwise overlap (plan §4 S4/G7)
    zone_polys = [z.polygon for z in zones]
    zone_union = unary_union(zone_polys) if zone_polys else Polygon()
    symdiff_geom = zone_union.symmetric_difference(footprint)
    symdiff = symdiff_geom.area * mpu * mpu
    overlap = sum(zone_polys[i].intersection(zone_polys[j]).area
                  for i in range(len(zone_polys)) for j in range(i + 1, len(zone_polys))) * mpu * mpu
    g7 = symdiff <= tols.topo_area_m2 and overlap <= tols.topo_area_m2
    if not g7:
        loc = (symdiff_geom.representative_point() if not symdiff_geom.is_empty
               else footprint.representative_point())
        _add(diags, _diag("tarch_zone_tiling_residual",
                          points_dxf_mm=[(loc.x, loc.y)],
                          context={"symmetric_diff_m2": symdiff, "pairwise_overlap_m2": overlap}))
    gates.append(GateResultV1(id="G7", name="zone tiling", passed=g7,
        evidence={"zone_count": len(zones), "symmetric_diff_m2": symdiff,
                  "pairwise_overlap_m2": overlap}))

    # G8 INDEPENDENT reconstruction: rebuilt wall region vs measured wall region
    g8_passed = False
    g8_sd = None
    if zones and not wall_region.is_empty:
        recon = g8_reconstruct_wall_region(zones)
        g8_sd_geom = recon.symmetric_difference(wall_region)
        g8_sd = g8_sd_geom.area * mpu * mpu
        g8_passed = g8_sd <= tols.topo_area_m2
        if not g8_passed:
            loc = (g8_sd_geom.representative_point() if not g8_sd_geom.is_empty
                   else wall_region.representative_point())
            _add(diags, _diag("tarch_reconstruction_residual",
                              points_dxf_mm=[(loc.x, loc.y)],
                              context={"symmetric_diff_m2": g8_sd,
                                       "rebuilt_area_m2": recon.area * mpu * mpu,
                                       "measured_area_m2": wall_region.area * mpu * mpu}))
    walls_ok, wall_pairs = _same_wall_consistency(zones, tols)
    conflicts = [p for p in wall_pairs if not p["consistent"]]
    if conflicts:
        first = conflicts[0]
        _add(diags, _diag("tarch_edge_thickness_inconsistent",
                          context={"reason": "back_to_back_zone_edge_mismatch",
                                   "conflicts": conflicts},
                          points_dxf_mm=[(first["coord_native"], first["overlap_native"][0])]))
    g8_passed = g8_passed and walls_ok
    gates.append(GateResultV1(id="G8", name="independent wall-region reconstruction",
        passed=g8_passed, evidence={"symmetric_diff_m2": g8_sd,
                                    "same_wall_pairs": wall_pairs,
                                    "same_wall_conflict_count": len(conflicts)}))

    # G9 v3 preflight + G10 human-review overlay are emitted by the orchestrator
    # after S9 builds the augmented DXF / manifest / overlay (they need those artefacts).
    return _apply_test_neuter(gates)


# --------------------------------------------------------------------------- #
# S9 — persist: augmented DXF (appended GTV3_* layers) + manifest + report +
# source_map + human-review overlay.  §0.1 方案A: write into staging only.
# --------------------------------------------------------------------------- #
GTV3_FOOTPRINT_LAYER = "GTV3_FOOTPRINT"
GTV3_ZONE_LAYER = "GTV3_ZONE"
GTV3_OPENING_LAYER = "GTV3_OPENING"
GTV3_ELEV_OPENING_LAYER = "GTV3_ELEV_OPENING"


@dataclass(frozen=True)
class _ElevationRecord:
    view_id: str
    facade: str
    kind: Literal["window", "door"]
    rect: tuple[float, float, float, float]
    raw_handles: tuple[str, ...]
    structural_handles: tuple[str, ...]
    datum_handle: str
    datum_start: tuple[float, float]
    datum_end: tuple[float, float]
    declared_lo_endpoint: str
    generated_handle: str = ""


def elevation_block_definition_sha256(doc, name: str) -> str:
    """Canonical, order-independent fingerprint of all direct block entities.

    This deliberately includes non-structural entities: adding a CIRCLE/TEXT
    cannot bypass the request-bound exhaustive role list merely because it is
    excluded from structural extrema.
    """
    block = doc.blocks.get(name)
    def freeze(value):
        if hasattr(value, "x") and hasattr(value, "y"):
            return [float(value.x), float(value.y), float(getattr(value, "z", 0.0))]
        if isinstance(value, (list, tuple)):
            return [freeze(v) for v in value]
        if isinstance(value, dict):
            return {str(k): freeze(v) for k, v in sorted(value.items()) if k not in {"owner", "handle"}}
        return str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
    entities = []
    for entity in block:
        data = entity.dxfattribs()
        # ezdxf legitimately omits zero-valued optional defaults after a save;
        # canonicalize that container representation, not the geometry.
        if entity.dxftype() == "LWPOLYLINE":
            data.setdefault("const_width", 0.0)
        # dxfattribs omits polyline vertices; they are semantic geometry.
        if entity.dxftype() == "LWPOLYLINE":
            data["points"] = [list(map(float, p[:5])) for p in entity.get_points("xyseb")]
        entities.append({"handle": entity.dxf.handle, "type": entity.dxftype(),
                         "layer": entity.dxf.layer, "tags": freeze(data)})
    payload = {"name": name, "base_point": freeze(block.block.dxf.base_point),
               "entities": sorted(entities, key=lambda item: item["handle"])}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n").hexdigest()


def _entity_text(entity) -> str:
    return entity.plain_text() if entity.dxftype() == "MTEXT" else str(getattr(entity.dxf, "text", ""))


def _inside(entity, clip: ClipBoxDxf) -> bool:
    box = ezdxf_bbox.extents([entity], fast=True)
    cx, cy = (box.extmin.x + box.extmax.x) / 2, (box.extmin.y + box.extmax.y) / 2
    return clip.xmin < cx < clip.xmax and clip.ymin < cy < clip.ymax


def _rect_from_lines(lines, q: float) -> tuple[float, float, float, float] | None:
    """Strict four-edge rectangle check after the converter's q=tau_node/10 snap."""
    edges = []
    for line in lines:
        a = (_quantize(float(line.dxf.start.x), q), _quantize(float(line.dxf.start.y), q))
        b = (_quantize(float(line.dxf.end.x), q), _quantize(float(line.dxf.end.y), q))
        if a == b or (a[0] != b[0] and a[1] != b[1]):
            return None
        edges.append((a, b))
    if len(edges) != 4:
        return None
    degree: dict[tuple[float, float], int] = {}
    for a, b in edges:
        degree[a] = degree.get(a, 0) + 1; degree[b] = degree.get(b, 0) + 1
    if len(degree) != 4 or set(degree.values()) != {2}:
        return None
    xs, ys = [p[0] for p in degree], [p[1] for p in degree]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    expected = {tuple(sorted(((x0,y0),(x1,y0)))), tuple(sorted(((x1,y0),(x1,y1)))),
                tuple(sorted(((x0,y1),(x1,y1)))), tuple(sorted(((x0,y0),(x0,y1))))}
    return (x0, y0, x1, y1) if {tuple(sorted(edge)) for edge in edges} == expected and x0 < x1 and y0 < y1 else None


def _line_components(lines, q: float) -> list[list[Any]]:
    endpoints = [{(_quantize(float(e.dxf.start.x),q), _quantize(float(e.dxf.start.y),q)),
                  (_quantize(float(e.dxf.end.x),q), _quantize(float(e.dxf.end.y),q))} for e in lines]
    pending = set(range(len(lines))); groups = []
    while pending:
        todo = [pending.pop()]; group = []
        while todo:
            i = todo.pop(); group.append(lines[i]); neighbours = [j for j in pending if endpoints[i] & endpoints[j]]
            for j in neighbours: pending.remove(j); todo.append(j)
        groups.append(group)
    return groups


def _v3_elevation_records(augmented_dxf: Path, request: TarchConversionRequestV1,
                          plan_gt, tols: _Tols) -> tuple[list[_ElevationRecord], list[ConversionDiagnosticV1]]:
    """E0--E4: validate named views/datum anchors and produce normalized evidence.

    It does not infer a datum or handedness: both are consumed only from the
    signed v3 request and verified against the plan projection before opening
    geometry is touched.
    """
    doc = ezdxf.readfile(str(augmented_dxf)); msp = doc.modelspace(); diags = []; records = []
    segment_by_id = {s.id: s for floor in plan_gt.floors for s in floor.boundary_segments}
    plan_openings = []
    for opening in plan_gt.openings:
        seg = segment_by_id[opening.boundary_segment_id]
        plan_openings.append((opening, seg.facade_family))
    for view in request.elevation_views:
        if not isinstance(view, DatumBoundNamedElevationViewIntentV3):
            continue
        frame = next((e for e in msp if e.dxf.handle == view.frame_entity_handle), None)
        title = next((e for e in msp if e.dxf.handle == view.title_entity_handle), None)
        mapped = request.plan_views[0].dialect_rules.elevation_title_map.get(view.frame_title)
        if frame is None or title is None or not _inside(title, view.clip_box_dxf) or _entity_text(title).strip() != view.frame_title or mapped != view.facade_family:
            _add(diags, _diag("tarch_elevation_title_mismatch", handles=[view.frame_entity_handle], context={"view_id": view.id})); continue
        facade_segments = [s for s in segment_by_id.values() if s.facade_family == view.facade_family and s.floor_id in view.floor_ids]
        if not facade_segments:
            _add(diags, _diag("tarch_elevation_datum_invalid", handles=[view.frame_entity_handle])); continue
        plan_lo, plan_hi = min(s.world_along_interval.lo for s in facade_segments), max(s.world_along_interval.hi for s in facade_segments)
        if abs(abs(view.world_along_from_source_m.scale) - request.metres_per_unit) != 0 or abs(abs(view.world_z_from_source_m.scale) - request.metres_per_unit) != 0:
            _add(diags, _diag("tarch_elevation_z_transform_mismatch", handles=[view.frame_entity_handle])); continue
        datum = view.floor_datums[0]
        ent = next((e for e in msp if e.dxf.handle == datum.entity_handle), None)
        if ent is None:
            _add(diags, _diag("tarch_elevation_datum_missing", handles=[datum.entity_handle])); continue
        if ent.dxftype() != "LINE":
            _add(diags, _diag("tarch_elevation_datum_invalid", handles=[datum.entity_handle])); continue
        start, end = (float(ent.dxf.start.x), float(ent.dxf.start.y)), (float(ent.dxf.end.x), float(ent.dxf.end.y))
        axis = view.world_along_from_source_m.source_axis; z_axis = view.world_z_from_source_m.source_axis
        a0, a1 = (start[0 if axis == "x" else 1], end[0 if axis == "x" else 1])
        z0, z1 = (start[0 if z_axis == "x" else 1], end[0 if z_axis == "x" else 1])
        transform_along = lambda value: value * view.world_along_from_source_m.scale + view.world_along_from_source_m.offset
        floor = next(f for f in request.floors if f.id == datum.floor_id)
        derived_offset = floor.z_floor_m - z0 * view.world_z_from_source_m.scale
        declared = a0 if datum.world_along_lo_source_endpoint == "start" else a1
        other = a1 if datum.world_along_lo_source_endpoint == "start" else a0
        endpoint_bad = abs(transform_along(declared) - plan_lo) > tols.node_join_m or abs(transform_along(other) - plan_hi) > tols.node_join_m
        if abs(z0 - z1) > tols.axis_align_native or abs(a0 - a1) <= tols.quant_native or abs(derived_offset - view.world_z_from_source_m.offset) > tols.node_join_m or endpoint_bad:
            _add(diags, _diag("tarch_elevation_along_direction_mismatch" if endpoint_bad else "tarch_elevation_z_transform_mismatch", handles=[datum.entity_handle])); continue
        lines = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer in view.window_selector.layers and _inside(e, view.clip_box_dxf)]
        for group in _line_components(lines, tols.quant_native):
            rect = _rect_from_lines(group, tols.quant_native)
            if rect is None:
                _add(diags, _diag("tarch_elevation_opening_component_invalid", handles=[group[0].dxf.handle])); continue
            records.append(_ElevationRecord(view.id, view.facade_family, "window", rect, tuple(sorted(e.dxf.handle for e in group)), tuple(sorted(e.dxf.handle for e in group)), datum.entity_handle, start, end, datum.world_along_lo_source_endpoint))
        if view.door_selector:
            rules = {r.block_name_exact: r for r in request.plan_views[0].dialect_rules.elevation_door_block_rules}
            modules = []
            for ins in [e for e in msp if e.dxftype() == "INSERT" and e.dxf.layer in view.door_selector.layers and _inside(e, view.clip_box_dxf)]:
                rule = rules.get(ins.dxf.name)
                if rule is None or elevation_block_definition_sha256(doc, ins.dxf.name) != (rule.block_definition_sha256 if rule else ""):
                    _add(diags, _diag("tarch_elevation_door_block_drift", handles=[ins.dxf.handle])); continue
                block_entities = list(doc.blocks.get(ins.dxf.name)); roles = {x.entity_handle: x.role for x in rule.entity_roles}
                if set(roles) != {x.dxf.handle for x in block_entities} or list(roles.values()).count("structural_outline") != 1:
                    _add(diags, _diag("tarch_elevation_door_block_drift", handles=[ins.dxf.handle])); continue
                index = next(i for i, x in enumerate(block_entities) if roles[x.dxf.handle] == "structural_outline")
                structural = block_entities[index]
                if structural.dxftype() != "LWPOLYLINE":
                    _add(diags, _diag("tarch_elevation_door_structure_invalid", handles=[ins.dxf.handle])); continue
                matrix = ins.matrix44()
                pts = []
                for point in structural.get_points("xyseb"):
                    world = matrix.transform((point[0], point[1], 0.0))
                    pts.append((world.x, world.y, point[2], point[3], point[4]))
                pseudo = []
                for i in range(len(pts)):
                    a, b = pts[i], pts[(i + 1) % len(pts)]
                    pseudo.append(type("L", (), {"dxf": type("D", (), {"start": type("P", (), {"x":a[0],"y":a[1]})(), "end": type("P", (), {"x":b[0],"y":b[1]})()})()})())
                rect = _rect_from_lines(pseudo, tols.quant_native)
                if rect is None:
                    _add(diags, _diag("tarch_elevation_door_structure_invalid", handles=[ins.dxf.handle])); continue
                modules.append((rect, ins.dxf.handle, block_entities[index].dxf.handle))
            # Modules sharing a sill/head band declare one structural-door union.
            # Do not silently split a gapped or overlapping pair into two doors:
            # its bounding union must tile exactly, otherwise the G3 structural
            # contract fails before pairing can hide the malformed geometry.
            pending = set(range(len(modules)))
            while pending:
                i = pending.pop(); cluster = [i]; changed = True
                while changed:
                    changed = False
                    for j in list(pending):
                        if any(
                            # Same z band is deliberately enough to join: a
                            # positive gap/overlap must be inspected as one
                            # claimed union rather than downgraded to doors.
                            (abs(modules[j][0][1]-modules[k][0][1]) <= tols.quant_native
                             and abs(modules[j][0][3]-modules[k][0][3]) <= tols.quant_native)
                            # Different-z touching/intersecting modules are a
                            # malformed T/step union and must share the check.
                            or (modules[j][0][0] <= modules[k][0][2] + tols.quant_native
                                and modules[j][0][2] + tols.quant_native >= modules[k][0][0]
                                and modules[j][0][1] <= modules[k][0][3] + tols.quant_native
                                and modules[j][0][3] + tols.quant_native >= modules[k][0][1])
                            for k in cluster):
                            pending.remove(j); cluster.append(j); changed = True
                rects = [modules[k][0] for k in cluster]; x0,y0,x1,y1 = min(r[0] for r in rects),min(r[1] for r in rects),max(r[2] for r in rects),max(r[3] for r in rects)
                if sum((r[2]-r[0])*(r[3]-r[1]) for r in rects) != (x1-x0)*(y1-y0):
                    _add(diags, _diag("tarch_elevation_door_structure_invalid", handles=[modules[cluster[0]][1]])); continue
                records.append(_ElevationRecord(view.id, view.facade_family, "door", (x0,y0,x1,y1), tuple(sorted(modules[k][1] for k in cluster)), tuple(sorted(modules[k][2] for k in cluster)), datum.entity_handle, start, end, datum.world_along_lo_source_endpoint))
    return records, diags


def _write_augmented_dxf(source_dxf: Path, dest: Path, footprint: Any,
                         zones: list[ZoneExpansion], exterior_openings: list[ResolvedOpening]
                         ) -> tuple[dict[str, list[str]], dict[tuple[int, int], str]]:
    """Append GTV3_* layers to a copy of the source DXF, preserving every original
    handle (plan §8.1).  Returns the generated-entity handles per layer AND a
    ``(zone_index, edge_index) -> handle`` map for the GTV3_ZONE lines, so each
    emitted zoning line ties back to the exact zone edge (and its source ancestry)
    that generated it."""
    doc = ezdxf.readfile(str(source_dxf))
    msp = doc.modelspace()
    for layer in (GTV3_FOOTPRINT_LAYER, GTV3_ZONE_LAYER, GTV3_OPENING_LAYER):
        if layer not in doc.layers:
            doc.layers.add(layer)
    handles: dict[str, list[str]] = {GTV3_FOOTPRINT_LAYER: [], GTV3_ZONE_LAYER: [], GTV3_OPENING_LAYER: []}

    # GTV3_FOOTPRINT: closed LWPOLYLINE = outer-skin exterior ring (native mm).
    # The polygonized outer-skin ring carries a redundant collinear vertex at every
    # opening jamb (S4 fills close the wall gaps, so the union exterior runs straight
    # through each jamb with a sub-mm extra vertex — see _outer_skin_gap_count).  Those
    # collapse to zero-length edges under v3's node-snap (dxf_short_edge), so drop them
    # first: only true corners remain, an identical polygon.
    if footprint.geom_type == "Polygon":
        raw = [(round(x, 6), round(y, 6)) for x, y in list(footprint.exterior.coords)[:-1]]
        ring = _clean_collinear(raw)
        e = msp.add_lwpolyline(ring, dxfattribs={"layer": GTV3_FOOTPRINT_LAYER}, close=True)
        handles[GTV3_FOOTPRINT_LAYER].append(e.dxf.handle)

    # GTV3_ZONE: one LINE per internal (wall_axis) zoning edge, deduped by canonical
    # coords (an internal wall is shared by two zones -> emitted once).  The handle is
    # recorded for BOTH zone edges so each zone report edge carries its derived handle.
    seen: dict[tuple[float, float, float, float], str] = {}
    zone_edge_handles: dict[tuple[int, int], str] = {}
    for z_idx, z in enumerate(zones):
        verts = z.vertices
        for i, edge in enumerate(z.edges):
            if edge.basis != "wall_axis":
                continue
            a, b = verts[i], verts[(i + 1) % len(verts)]
            key = (round(min(a[0], b[0]), 6), round(min(a[1], b[1]), 6),
                   round(max(a[0], b[0]), 6), round(max(a[1], b[1]), 6))
            if key in seen:
                zone_edge_handles[(z_idx, i)] = seen[key]
                continue
            e = msp.add_line((round(a[0], 6), round(a[1], 6)),
                             (round(b[0], 6), round(b[1], 6)),
                             dxfattribs={"layer": GTV3_ZONE_LAYER})
            seen[key] = e.dxf.handle
            handles[GTV3_ZONE_LAYER].append(e.dxf.handle)
            zone_edge_handles[(z_idx, i)] = e.dxf.handle

    # GTV3_OPENING: one closed LWPOLYLINE per EXTERIOR opening (clean rect, D2)
    for op in exterior_openings:
        x0, y0, x1, y1 = op.rect_dxf_mm
        e = msp.add_lwpolyline([(round(x0, 6), round(y0, 6)), (round(x1, 6), round(y0, 6)),
                                (round(x1, 6), round(y1, 6)), (round(x0, 6), round(y1, 6))],
                               dxfattribs={"layer": GTV3_OPENING_LAYER}, close=True)
        handles[GTV3_OPENING_LAYER].append(e.dxf.handle)

    doc.saveas(str(dest))
    return handles, zone_edge_handles


def _append_elevation_outlines(path: Path, records: list[_ElevationRecord], q: float) -> list[_ElevationRecord]:
    """E5: append only normalized structural rectangles, then reopen and verify."""
    doc = ezdxf.readfile(str(path)); msp = doc.modelspace()
    if GTV3_ELEV_OPENING_LAYER not in doc.layers:
        doc.layers.add(GTV3_ELEV_OPENING_LAYER)
    emitted = []
    for rec in records:
        x0, y0, x1, y1 = rec.rect
        entity = msp.add_lwpolyline([(x0,y0), (x1,y0), (x1,y1), (x0,y1)], close=True,
                                    dxfattribs={"layer": GTV3_ELEV_OPENING_LAYER})
        emitted.append(_ElevationRecord(**{**rec.__dict__, "generated_handle": entity.dxf.handle}))
    doc.saveas(str(path))
    reopened = ezdxf.readfile(str(path)); rmsp = reopened.modelspace()
    for rec in emitted:
        entity = next((e for e in rmsp if e.dxf.handle == rec.generated_handle), None)
        if entity is None or entity.dxftype() != "LWPOLYLINE":
            raise ValueError("tarch_elevation_normalized_outline_drift")
        pts = list(entity.get_points("xyseb"))
        if len(pts) != 4 or any(p[4] != 0 for p in pts):
            raise ValueError("tarch_elevation_normalized_outline_drift")
        if not entity.closed:
            raise ValueError("tarch_elevation_normalized_outline_drift")
    return emitted


def _validate_raster_intents(request: TarchConversionRequestV1, doc, tols: _Tols,
                             diags: list[ConversionDiagnosticV1]) -> None:
    """Validate signed v3 calibration facts; image bytes stay checked by overlay writer.

    ``pixel_to_source_m`` is source-metres (the manifest convention), whereas
    request control coordinates remain exact DXF-native values.  This boundary is
    explicit so a mm affine cannot silently be consumed as a metre affine.
    """
    if request.request_version != 3:
        return
    elevation_intents = {item.id: item for item in request.elevation_views if isinstance(item, DatumBoundNamedElevationViewIntentV3)}
    plan_intents = {item.id: item for item in request.plan_views}
    expected_view_ids = set(elevation_intents) | set(plan_intents)
    if {binding.view_id for binding in request.raster_overlays} != expected_view_ids or len(request.raster_overlays) != len(expected_view_ids):
        fallback = next(iter(elevation_intents.values())).frame_entity_handle if elevation_intents else request.plan_views[0].wall_selector.layers[0]
        _add(diags, _diag("tarch_raster_overlay_unbound", handles=[fallback])); return
    for binding in request.raster_overlays:
        elevation_intent = elevation_intents.get(binding.view_id)
        plan_intent = plan_intents.get(binding.view_id)
        if (elevation_intent is None and plan_intent is None) or Path(binding.source_label).name != binding.source_label:
            fallback = elevation_intent.frame_entity_handle if elevation_intent else next(iter(elevation_intents.values())).frame_entity_handle
            _add(diags, _diag("tarch_raster_overlay_unbound", handles=[fallback])); continue
        controls = {control.role: control for control in binding.calibration_controls}
        if len(controls) != len(binding.calibration_controls):
            _add(diags, _diag("tarch_raster_calibration_invalid", handles=[binding.calibration_controls[0].entity_handle])); continue
        if plan_intent is not None:
            footprint = next((item for item in doc.modelspace()
                              if item.dxftype() == "LWPOLYLINE" and item.dxf.layer == GTV3_FOOTPRINT_LAYER), None)
            if set(controls) != {"footprint_sw", "footprint_se", "footprint_nw"} or footprint is None:
                _add(diags, _diag("tarch_raster_calibration_invalid", handles=[binding.calibration_controls[0].entity_handle])); continue
            vertices = [(float(point[0]), float(point[1])) for point in footprint.get_points("xy")]
            min_x, max_x = min(point[0] for point in vertices), max(point[0] for point in vertices)
            min_y, max_y = min(point[1] for point in vertices), max(point[1] for point in vertices)
            expected = {"footprint_sw": (min_x, min_y), "footprint_se": (max_x, min_y), "footprint_nw": (min_x, max_y)}
            pix = [controls[key].pixel_point for key in ("footprint_sw", "footprint_se", "footprint_nw")]
            area2 = abs((pix[1][0]-pix[0][0])*(pix[2][1]-pix[0][1]) - (pix[1][1]-pix[0][1])*(pix[2][0]-pix[0][0]))
            def mapped(control):
                a = binding.pixel_to_source_m
                return (a.m00*control.pixel_point[0]+a.m01*control.pixel_point[1]+a.m02,
                        a.m10*control.pixel_point[0]+a.m11*control.pixel_point[1]+a.m12)
            residual_ok = all(max(abs(mapped(control)[0]-control.source_point_dxf[0]*request.metres_per_unit),
                                  abs(mapped(control)[1]-control.source_point_dxf[1]*request.metres_per_unit)) <= tols.node_join_m
                              for control in controls.values())
            def close_native(actual, expected_point): return max(abs(actual[0]-expected_point[0]), abs(actual[1]-expected_point[1])) <= tols.node_join_native
            if area2 == 0 or not residual_ok or not all(close_native(controls[role].source_point_dxf, point) for role, point in expected.items()):
                _add(diags, _diag("tarch_raster_calibration_invalid", handles=[binding.calibration_controls[0].entity_handle], context={"view_id": plan_intent.id})); continue
            continue
        intent = elevation_intent
        datum = intent.floor_datums[0]
        entity = next((item for item in doc.modelspace() if item.dxf.handle == datum.entity_handle), None)
        if set(controls) != {"datum_lo", "datum_hi", "off_datum"} or entity is None:
            _add(diags, _diag("tarch_raster_calibration_invalid", handles=[datum.entity_handle])); continue
        start, end = (float(entity.dxf.start.x), float(entity.dxf.start.y)), (float(entity.dxf.end.x), float(entity.dxf.end.y))
        expected_lo = start if datum.world_along_lo_source_endpoint == "start" else end
        expected_hi = end if datum.world_along_lo_source_endpoint == "start" else start
        def close_native(actual, expected): return max(abs(actual[0]-expected[0]), abs(actual[1]-expected[1])) <= tols.node_join_native
        pix = [controls[key].pixel_point for key in ("datum_lo", "datum_hi", "off_datum")]
        area2 = abs((pix[1][0]-pix[0][0])*(pix[2][1]-pix[0][1]) - (pix[1][1]-pix[0][1])*(pix[2][0]-pix[0][0]))
        def mapped(control):
            a = binding.pixel_to_source_m
            return (a.m00*control.pixel_point[0]+a.m01*control.pixel_point[1]+a.m02,
                    a.m10*control.pixel_point[0]+a.m11*control.pixel_point[1]+a.m12)
        residual_ok = all(max(abs(mapped(control)[0]-control.source_point_dxf[0]*request.metres_per_unit),
                              abs(mapped(control)[1]-control.source_point_dxf[1]*request.metres_per_unit)) <= tols.node_join_m
                          for control in controls.values())
        if (not close_native(controls["datum_lo"].source_point_dxf, expected_lo)
                or not close_native(controls["datum_hi"].source_point_dxf, expected_hi)
                or area2 == 0 or not residual_ok):
            _add(diags, _diag("tarch_raster_calibration_invalid", handles=[datum.entity_handle],
                              context={"view_id": intent.id, "declared_lo_endpoint": datum.world_along_lo_source_endpoint})); continue


def _build_source_map(request: TarchConversionRequestV1, plan_view: PlanViewIntentV1,
                      zones: list[ZoneExpansion], exterior_openings: list[ResolvedOpening],
                      gtv3_handles: dict[str, list[str]],
                      zone_edge_handles: dict[tuple[int, int], str],
                      footprint: Any, p1: P1PlanViewGeometry, tols: _Tols
                      ) -> SourceMapV1:
    """Per-edge ancestry (plan §6.1 / §8.1): one SourceMapEntryV1 per GENERATED
    GTV3_* entity, each naming the SOURCE DXF handles it was derived from.

      * footprint_ring  <- the outer-skin wall LINEs on the footprint exterior
      * zone_edge       <- the inner-face wall LINE(s) the cavity edge lay on
      * opening_outline <- the opening block INSERT + its jamb-cap LINEs

    Generated handles come from ``_write_augmented_dxf``; source handles are the
    real tianzheng entity handles (never a layer label)."""
    affine = plan_view.world_from_source_m
    entries: list[SourceMapEntryV1] = []

    def world(pt): return list(_to_world(pt, affine))

    # footprint <- outer-skin wall lines on the footprint exterior ring
    if footprint.geom_type == "Polygon" and gtv3_handles.get(GTV3_FOOTPRINT_LAYER):
        ring = [(p[0], p[1]) for p in list(footprint.exterior.coords)[:-1]]
        src: list[str] = []
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a[0] == b[0] or a[1] == b[1]:
                src.extend(_edge_source_handles(a, b, p1.wall_lines, tols))
        entries.append(SourceMapEntryV1(
            generated_handle=gtv3_handles[GTV3_FOOTPRINT_LAYER][0],
            view_id=plan_view.id, floor_id=plan_view.floor_id,
            semantic_role="footprint", operation="footprint_ring",
            canonical_geometry_world_m={"ring_m": [world(p) for p in ring]},
            source_entity_refs=[SourceEntityRefV1(handle=h, role="wall_side") for h in dict.fromkeys(src)]))

    # zone edges <- inner-face wall lines; one entry per emitted GTV3_ZONE line
    handle_to_sources: dict[str, list[str]] = {}
    handle_to_geom: dict[str, list] = {}
    for (z_idx, e_idx), h in zone_edge_handles.items():
        z = zones[z_idx]
        edge = z.edges[e_idx]
        a = z.vertices[e_idx]
        b = z.vertices[(e_idx + 1) % len(z.vertices)]
        handle_to_sources.setdefault(h, []).extend(edge.source_handles)
        handle_to_geom[h] = [world(a), world(b)]
    for h, sources in handle_to_sources.items():
        refs = [SourceEntityRefV1(handle=s, role="wall_side") for s in dict.fromkeys(sources)]
        proof_ids = []
        for z_idx, e_idx in zone_edge_handles:
            if zone_edge_handles[(z_idx, e_idx)] == h:
                ev = zones[z_idx].edges[e_idx].thickness_evidence
                if ev is not None:
                    proof_ids.extend(ev.proof_handles)
        entries.append(SourceMapEntryV1(
            generated_handle=h, view_id=plan_view.id, floor_id=plan_view.floor_id,
            semantic_role="zone_boundary", operation="zone_edge",
            canonical_geometry_world_m={"segment_m": handle_to_geom[h]},
            source_entity_refs=refs, proof_ids=list(dict.fromkeys(proof_ids))))

    # openings <- block INSERT + jamb caps
    for op, h in zip(exterior_openings, gtv3_handles.get(GTV3_OPENING_LAYER, [])):
        refs = [SourceEntityRefV1(handle=op.handle, role="opening_block")]
        refs.extend(SourceEntityRefV1(handle=j, role="jamb") for j in op.jamb_handles)
        x0, y0, x1, y1 = op.rect_dxf_mm
        entries.append(SourceMapEntryV1(
            generated_handle=h, view_id=plan_view.id, floor_id=plan_view.floor_id,
            semantic_role="opening", operation="opening_outline",
            canonical_geometry_world_m={"rect_m": [world((x0, y0)), world((x1, y1))]},
            source_entity_refs=refs))

    sm = SourceMapV1(map_version=1, case=request.case, entries=entries, source_map_sha256="0" * 64)
    return sm.model_copy(update={"source_map_sha256": compute_source_map_sha256(sm)})


def _build_manifest(request: TarchConversionRequestV1, plan_view: PlanViewIntentV1,
                    zones: list[ZoneExpansion], claims: list[dict],
                    exterior_openings: list[ResolvedOpening], gtv3_handles: dict[str, list[str]],
                    augmented_dxf: Path, elevation_records: list[_ElevationRecord] | None = None):
    """Build a GtExtractionManifestV1 draft bound to the AUGMENTED DXF (plan §8.1) —
    that is the file v3 actually consumes.  Selectors pin the generated GTV3_*
    handles via only_listed (no 'layer has an extra line' silent answer drift)."""
    from .gt_manifest import (GtExtractionManifestV1, EntityLocatorV1,
                              PlanOpeningBindingV1, PlanViewBindingV1, ElevationViewBindingV1,
                              RasterOverlayBindingV1, ZoneSeedV1, compute_manifest_sha256)
    affine = plan_view.world_from_source_m          # native -> world (m00 = metres_per_unit)
    # v3's _transform pre-multiplies native by metres_per_unit, so the manifest
    # world_from_source_m maps source-METRES -> world (identity scale for a pure-scale
    # source) — NOT native -> world (which is what PlanViewIntentV1 carries).  Factor
    # the mpu scaling out of the linear part; the translation is already world-metres.
    # (Confirmed against the frozen v3 contract: tests/test_gt_extraction.py et al. use
    # m00=1.0 with metres_per_unit=0.001.)  Native->world affine is still used below for
    # the seed points, which are emitted directly in world metres.
    mpu = request.metres_per_unit
    manifest_affine = Affine2D(m00=affine.m00 / mpu, m01=affine.m01 / mpu, m02=affine.m02,
                               m10=affine.m10 / mpu, m11=affine.m11 / mpu, m12=affine.m12)
    floor = request.floors[0]
    fp_handles = sorted(gtv3_handles[GTV3_FOOTPRINT_LAYER])
    zo_handles = sorted(gtv3_handles[GTV3_ZONE_LAYER])
    # A single-zone building has no internal zoning lines -> no GTV3_ZONE handles.  The
    # selector contract requires only_listed to carry handles and all_matching to carry
    # none, so a handle-less zone set uses all_matching over the (empty) layer.
    zo_mode = "only_listed" if zo_handles else "all_matching"
    zo_min = 1 if zo_handles else 0
    seeds = []
    for z, claim in zip(zones, claims):
        wp = _to_world(z.seed_native, affine)
        seeds.append(ZoneSeedV1(zone_id=claim["zone_id"], name=claim["name"],
                                role=claim["role"], point_world_m=wp))
    plan_openings = []
    for op, h in zip(exterior_openings, sorted(gtv3_handles[GTV3_OPENING_LAYER])):
        plan_openings.append(PlanOpeningBindingV1(
            opening_id=f"op_{op.handle.lower()}", kind=op.kind,
            geometry_mode="closed_outline_bbox", span_world_axis=op.axis,
            entities=[EntityLocatorV1(handle=h)]))
    pv = {
        "kind": "plan", "id": plan_view.id, "floor_id": plan_view.floor_id,
        "clip_box_dxf": plan_view.clip_box_dxf, "world_from_source_m": manifest_affine,
        "footprint_boundary": {"entity_types": ["LWPOLYLINE"], "layers": [GTV3_FOOTPRINT_LAYER],
                               "handles": fp_handles, "handle_mode": "only_listed",
                               "min_count": 1, "max_count": 1},
        "zone_boundaries": {"entity_types": ["LINE"], "layers": [GTV3_ZONE_LAYER],
                            "handles": zo_handles, "handle_mode": zo_mode,
                            "min_count": zo_min, "max_count": None},
        "plan_openings": [p.model_dump(mode="python") for p in plan_openings],
        "zone_seeds": [s.model_dump(mode="python") for s in seeds],
        "boundary_reference": "outer_skin", "default_wall_thickness_m": None,
    }
    include_elevations = elevation_records is not None
    elevation_records = elevation_records or []
    elev_views = []
    for intent in sorted((x for x in request.elevation_views if isinstance(x, DatumBoundNamedElevationViewIntentV3)), key=lambda x: x.id) if include_elevations else []:
        evidence = []
        for rec in sorted((r for r in elevation_records if r.view_id == intent.id), key=lambda r: (r.kind, r.raw_handles)):
            evidence.append({"evidence_id": f"ev_{intent.id}_{min(rec.raw_handles).lower()}", "kind": rec.kind,
                             "geometry_mode": "closed_outline_bbox", "entities": [{"handle": rec.generated_handle}]})
        elev_views.append(ElevationViewBindingV1.model_validate({"kind": "elevation", "id": intent.id, "floor_ids": intent.floor_ids,
                           "projection_surface_key": f"ps_{intent.id}", "facade_family": intent.facade_family,
                           "view_kind": "full", "world_along_coverage": None, "direction_semantics": "building_axis", "azimuth_deg": None,
                           "clip_box_dxf": intent.clip_box_dxf,
                           "world_along_from_source_m": {"source_axis": intent.world_along_from_source_m.source_axis, "scale": intent.world_along_from_source_m.scale / mpu, "offset": intent.world_along_from_source_m.offset},
                           "world_z_from_source_m": {"source_axis": intent.world_z_from_source_m.source_axis, "scale": intent.world_z_from_source_m.scale / mpu, "offset": intent.world_z_from_source_m.offset},
                           "segment_scope_mode": "all_family_segments", "boundary_entities": [], "opening_entities": evidence}))
    rasters = []
    if request.request_version == 3 and include_elevations:
        for binding in request.raster_overlays:
            rasters.append(RasterOverlayBindingV1.model_validate({"id": binding.id, "source_label": binding.source_label, "source_sha256": binding.source_sha256,
                            "view_id": binding.view_id, "pixel_to_source_m": binding.pixel_to_source_m.model_dump(mode="python")}))
    raw = {"manifest_version": 1, "case": request.case, "source_id": request.normalized_source_id,
           "source_dxf_label": augmented_dxf.name,
           "source_dxf_sha256": hashlib.sha256(augmented_dxf.read_bytes()).hexdigest(),
           "native_units": request.native_units, "metres_per_unit": request.metres_per_unit,
           "geometry_profile": request.target_geometry_profile,
           "floors": [floor.model_dump(mode="python")], "views": [PlanViewBindingV1.model_validate(pv), *elev_views],
           "north_axis": None, "raster_overlays": rasters, "manifest_sha256": "0" * 64}
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    return GtExtractionManifestV1.model_validate(raw), seeds, plan_openings


def _run_g9_v3_preflight(augmented_dxf: Path, manifest, tooling) -> tuple[bool, str | None]:
    """G9: run the real v3 extractor (inspect + plan extraction) on the augmented
    DXF + manifest.  Any ExtractionError -> fail-closed (tarch_v3_precondition)."""
    from .gt_extraction import (ExtractionError, ExtractionInputs, InspectionInputs,
                                extract_gt_v3, inspect_extraction_inputs)
    from .gt_schema import REPO_ROOT, compute_gt_implementation_hashes
    try:
        hashes = compute_gt_implementation_hashes(REPO_ROOT)
        insp = inspect_extraction_inputs(InspectionInputs(augmented_dxf, manifest, tooling, hashes))
        if insp.status != "PASS":
            codes = ",".join(sorted({i.code for i in insp.issues}))
            return False, codes or insp.status
        extract_gt_v3(ExtractionInputs(augmented_dxf, manifest, tooling, hashes))
        return True, None
    except ExtractionError as exc:
        return False, str(exc)
    except Exception as exc:
        # validate_gt_v3 has its own typed validation error.  G9 is the outer
        # fail-closed conversion gate, so it must turn that final-stage failure
        # into a BLOCK result rather than leaking a green preflight or a crash.
        return False, str(exc)


def _write_overlay_svg(path: Path, p1: P1PlanViewGeometry, footprint: Any,
                       zones: list[ZoneExpansion], claims: list[dict],
                       exterior_openings: list[ResolvedOpening], affine: Affine2D) -> None:
    """Deterministic human-review overlay (G10): source wall lines + outer-skin ring
    + zone polygons (labelled, semi-transparent) + exterior opening rects.  SVG only
    (no matplotlib in this env); a PNG-composited overlay is a documented follow-up."""
    xs = [x for _, x0, y0, x1, y1 in p1.wall_lines for x in (x0, x1)]
    ys = [y for _, x0, y0, x1, y1 in p1.wall_lines for y in (y0, y1)]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W, H = 1600.0, 1200.0
    pad = 0.02 * max(maxx - minx, maxy - miny)
    lox, loy = minx - pad, miny - pad
    span = max(maxx - minx, maxy - miny) + 2 * pad
    sx = W / span
    sy = H / span
    s = min(sx, sy)

    def X(x): return (x - lox) * s
    def Y(y): return H - (y - loy) * s
    palette = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4",
               "#46f0f0", "#f032e6", "#bcf60c", "#fabebe"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="sans-serif" font-size="13">']
    parts.append(f'<rect width="{W:.0f}" height="{H:.0f}" fill="white"/>')
    # source wall lines
    for _, x0, y0, x1, y1 in p1.wall_lines:
        parts.append(f'<line x1="{X(x0):.1f}" y1="{Y(y0):.1f}" x2="{X(x1):.1f}" y2="{Y(y1):.1f}" '
                     f'stroke="#cccccc" stroke-width="0.8"/>')
    # zones
    for k, z in enumerate(zones):
        col = palette[k % len(palette)]
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in z.vertices)
        parts.append(f'<polygon points="{pts}" fill="{col}" fill-opacity="0.28" stroke="{col}" stroke-width="2"/>')
        label_pt = z.polygon.representative_point()
        cx, cy = label_pt.x, label_pt.y
        nm = claims[k]["name"] if k < len(claims) else z.cavity_id
        parts.append(f'<text x="{X(cx):.1f}" y="{Y(cy):.1f}" fill="black" text-anchor="middle" '
                     f'font-weight="bold">{nm}</text>')
    # outer-skin ring
    if footprint.geom_type == "Polygon":
        ring = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in footprint.exterior.coords)
        parts.append(f'<polygon points="{ring}" fill="none" stroke="black" stroke-width="2.5"/>')
    # exterior openings
    for op in exterior_openings:
        x0, y0, x1, y1 = op.rect_dxf_mm
        parts.append(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*s:.1f}" '
                     f'height="{(y1-y0)*s:.1f}" fill="none" stroke="#0066ff" stroke-width="1.5"/>')
    parts.append("</svg>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def _verify_human_review_ack(work_dir: Path, request: TarchConversionRequestV1,
                             source_dxf: Path, overlay: Path) -> tuple[bool, dict]:
    """G10 accepts only a hash-bound external acknowledgement.

    Legacy requests retain the plan-overlay hash.  v3 acknowledges the canonical
    review index, whose inventory binds GT, both renders, four overlays and the
    per-opening audit table without fixing the future number of view files.
    """
    ack_path = work_dir / "review_ack.json"
    if request.request_version == 3:
        index_path = work_dir / "review_index.json"
        evidence = {"review_index_asset": index_path.name, "verification_status": "candidate", "ack_path": ack_path.name}
        if not index_path.is_file():
            evidence["review_index_status"] = "missing"
            return False, evidence
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index_hash = index["inventory_sha256"]
        except Exception as exc:
            evidence["review_index_status"] = type(exc).__name__
            return False, evidence
        evidence["review_index_sha256"] = index_hash
        if not ack_path.is_file():
            return False, evidence
        try:
            ack = HumanReviewAckV1.model_validate_json(ack_path.read_text(encoding="utf-8"))
        except Exception as exc:
            evidence["ack_error"] = type(exc).__name__
            return False, evidence
        checks = {"source_hash": ack.source_dxf_sha256 == hashlib.sha256(source_dxf.read_bytes()).hexdigest(),
                  "request_hash": ack.request_sha256 == request.request_sha256,
                  "review_index_hash": ack.review_index_sha256 == index_hash}
        evidence.update({"verification_status": "signed" if all(checks.values()) else "hash_mismatch",
                         "reviewer": ack.reviewer, "signed_at": ack.signed_at, "ack_checks": checks,
                         "near_threshold_confirmed": ack.near_threshold_confirmed})
        return all(checks.values()), evidence
    overlay_rel = overlay.name
    evidence = {"overlay_asset": overlay_rel,
                "overlay_sha256": hashlib.sha256(overlay.read_bytes()).hexdigest(),
                "verification_status": "candidate", "ack_path": ack_path.name}
    if not ack_path.is_file():
        return False, evidence
    try:
        ack = HumanReviewAckV1.model_validate_json(ack_path.read_text(encoding="utf-8"))
    except Exception as exc:
        evidence["ack_error"] = type(exc).__name__
        return False, evidence
    checks = {"source_hash": ack.source_dxf_sha256 == hashlib.sha256(source_dxf.read_bytes()).hexdigest(),
              "request_hash": ack.request_sha256 == request.request_sha256,
              "overlay_hash": ack.overlay_sha256 == evidence["overlay_sha256"]}
    evidence.update({"verification_status": "signed" if all(checks.values()) else "hash_mismatch",
                     "reviewer": ack.reviewer, "signed_at": ack.signed_at, "ack_checks": checks})
    evidence["near_threshold_confirmed"] = ack.near_threshold_confirmed
    return all(checks.values()), evidence


def _write_diagnostic_overlay(path: Path, diagnostics: list[ConversionDiagnosticV1]) -> None:
    """Small deterministic BLOCK artefact: locations + stable diagnostic codes."""
    marks = []
    for d in diagnostics:
        for x, y in d.source_points_dxf_mm:
            marks.append((x, y, d.code))
    if marks:
        minx, maxx = min(x for x, _, _ in marks), max(x for x, _, _ in marks)
        miny, maxy = min(y for _, y, _ in marks), max(y for _, y, _ in marks)
    else:
        minx = miny = 0.0; maxx = maxy = 1.0
    span = max(maxx - minx, maxy - miny, 1.0)
    def X(x): return 40 + (x - minx) * 720 / span
    def Y(y): return 760 - (y - miny) * 720 / span
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800">',
             '<rect width="800" height="800" fill="white"/>']
    for x, y, code in marks:
        lines.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="7" fill="#d00"/>')
        lines.append(f'<text x="{X(x)+10:.1f}" y="{Y(y):.1f}" font-size="12">{code}</text>')
    if not marks:
        lines.append('<text x="20" y="40" font-size="14">BLOCK: no local geometry available</text>')
    lines.append('</svg>')
    path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# P2 orchestrator
# --------------------------------------------------------------------------- #
def run_p2_conversion(dxf_path: Path, request: TarchConversionRequestV1,
                      plan_view: PlanViewIntentV1, tooling,
                      work_dir: Path) -> P2ConversionResult:
    """Run S0-S9 end to end for one plan view.  Convert+build run in ``work_dir``
    (staging, §0.1 方案A); nothing is promoted into a protected answer root here."""
    assert_staging_input(Path(dxf_path))
    work_dir = Path(work_dir)
    assert_staging_work_dir(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    tols = _tols_from(tooling, request.metres_per_unit)
    affine = plan_view.world_from_source_m

    # S0-S4 (P1)
    p1 = run_p1_plan_view(dxf_path, request, plan_view, tooling)
    diags: list[ConversionDiagnosticV1] = list(p1.diagnostics)

    # A hash/ownership BLOCK is an entrance barrier: do not enter any geometry
    # stage (and therefore do not manufacture secondary topology diagnostics).
    if any(d.severity == DiagnosticSeverity.BLOCK for d in diags):
        cavities, wall_region, footprint, near, claims = [], Polygon(), Polygon(), [], []
    else:
        cavities, wall_region, footprint, near = s5_identify_cavities(p1, request, tols, diags, affine)
        claims = s6_bind_intent(cavities, plan_view, tols, diags, affine)
    # S7 expand (only if no BLOCK so far and cavities claimed)
    zones: list[ZoneExpansion] = []
    if claims and not any(d.severity == DiagnosticSeverity.BLOCK for d in diags):
        zones = s7_expand_zones(claims, wall_region, footprint, tols, diags,
                                p1.wall_lines, p1.wall_bands)

    result = P2ConversionResult(p1=p1, cavities=cavities, wall_region=wall_region,
                                footprint=footprint, near_threshold_faces=near, zones=zones,
                                claims=claims, gates=[], diagnostics=diags)

    # G4/G6/G7/G8 (G9/G10 need S9 artefacts)
    gates = _build_p2_gates(p1, cavities, wall_region, footprint, zones, claims, near,
                            request, plan_view, tols, diags)
    blocked = any(d.severity == DiagnosticSeverity.BLOCK for d in diags)

    augmented_path: Path | None = None
    manifest = None
    overlay_path: Path | None = None
    g9_code: str | None = None
    if zones and not blocked:
        # S9 persist (staging only)
        exterior_openings = [o for o in p1.openings if o.classification == "exterior"]
        augmented_path = work_dir / "normalized.dxf"
        gtv3_handles, zone_edge_handles = _write_augmented_dxf(Path(dxf_path), augmented_path, footprint,
                                            zones, exterior_openings)
        manifest, seeds, plan_openings = _build_manifest(
            request, plan_view, zones, claims, exterior_openings, gtv3_handles, augmented_path)
        # v3 elevation consumes the already-certified plan projection solely to
        # verify the signed datum endpoints and make the required global pairing;
        # it never derives datum height or handedness from openings.
        elevation_records: list[_ElevationRecord] = []
        if request.request_version == 3:
            from .gt_extraction import ExtractionInputs, extract_gt_v3
            from .gt_schema import REPO_ROOT, compute_gt_implementation_hashes
            plan_gt = extract_gt_v3(ExtractionInputs(augmented_path, manifest, tooling, compute_gt_implementation_hashes(REPO_ROOT)))
            elevation_records, elevation_diags = _v3_elevation_records(augmented_path, request, plan_gt, tols)
            diags.extend(elevation_diags)
            if not any(d.severity == DiagnosticSeverity.BLOCK for d in elevation_diags):
                try:
                    elevation_records = _append_elevation_outlines(augmented_path, elevation_records, tols.quant_native)
                except ValueError:
                    _add(diags, _diag("tarch_elevation_normalized_outline_drift", handles=[elevation_records[0].raw_handles[0]] if elevation_records else [plan_view.id]))
                else:
                    manifest, seeds, plan_openings = _build_manifest(request, plan_view, zones, claims, exterior_openings,
                                                                       gtv3_handles, augmented_path, elevation_records)
            result.elevation_records = elevation_records
        overlay_path = work_dir / "overlay_plan.svg"
        _write_overlay_svg(overlay_path, p1, footprint, zones, claims, exterior_openings, affine)
        # S9 per-edge ancestry (source_map)
        source_map = _build_source_map(request, plan_view, zones, exterior_openings, gtv3_handles,
                                       zone_edge_handles, footprint, p1, tols)
        _validate_raster_intents(request, ezdxf.readfile(str(augmented_path)), tols, diags)
        # G9 v3 preflight on the augmented bundle
        g9_ok, g9_code = _run_g9_v3_preflight(augmented_path, manifest, tooling)
        if not g9_ok:
            _add(diags, _diag("tarch_v3_precondition",
                              points_dxf_mm=[(p1.footprint_polygon.centroid.x,
                                              p1.footprint_polygon.centroid.y)],
                              context={"v3_code": g9_code}))
        gates.append(GateResultV1(id="G9", name="v3 extraction preflight", passed=g9_ok,
                                  evidence={"v3_code": g9_code}))
        # G10 is deliberately not a file-exists check: candidate != signed.
        g10_ok, g10_evidence = _verify_human_review_ack(work_dir, request, Path(dxf_path), overlay_path)
        gates.append(GateResultV1(id="G10", name="human-review overlay", passed=g10_ok,
                                  evidence=g10_evidence))
        # A signed overlay acknowledgement is also the explicit human decision for
        # the near-threshold face list.  It is the only path that may clear G6's
        # otherwise fail-closed pending-review subcondition.
        if g10_ok and g10_evidence.get("near_threshold_confirmed"):
            gates = [g.model_copy(update={"passed": True,
                                           "evidence": {**g.evidence, "human_confirmation": "signed"}})
                     if g.id == "G6" and g.evidence.get("human_confirmation_required") else g
                     for g in gates]
        result.manifest = manifest
        result.augmented_dxf_path = augmented_path
        result.overlay_path = overlay_path
        result.gtv3_handles = gtv3_handles
        result.gtv3_zone_edge_handles = zone_edge_handles
        result.source_map = source_map
    else:
        overlay_path = work_dir / "overlay_diagnostics.svg"
        _write_diagnostic_overlay(overlay_path, diags)
        gates.append(GateResultV1(id="G9", name="v3 extraction preflight", passed=False,
                                  evidence={"reason": "blocked upstream; no bundle built"}))
        gates.append(GateResultV1(id="G10", name="human-review overlay", passed=False,
                                  evidence={"reason": "blocked upstream", "overlay_asset": overlay_path.name,
                                            "verification_status": "blocked"}))
        result.overlay_path = overlay_path

    # Elevation E0--E4 diagnostics are emitted after the legacy plan gates were
    # assembled.  Fold their declared registry ownership back into those gates;
    # otherwise a malformed v3 intent could leave G1/G3 nominally green.
    blocked_gates = {gate for diag in diags if diag.severity == DiagnosticSeverity.BLOCK
                     for gate in diagnostic_spec(diag.code).gates}
    gates = [gate.model_copy(update={"passed": False,
                                     "evidence": {**gate.evidence, "elevation_block": True}})
             if gate.id in blocked_gates else gate for gate in gates]
    # deterministic gate ordering G1..G10
    order = {"G1": 0, "G2": 1, "G3": 2, "G4": 3, "G5": 4, "G6": 5, "G7": 6, "G8": 7, "G9": 8, "G10": 9}
    gates.sort(key=lambda g: order[g.id])
    # Test-only mutation seam: the canonical mutation suite starts a fresh
    # process for each value and permits exactly one final gate to be neutered.
    # It is intentionally opt-in and never set by normal conversion callers.
    gates = _apply_test_neuter(gates)
    result.gates = gates
    result.diagnostics = diags
    result.conversion_report = build_p2_report(result, request, plan_view, tooling,
                                               dxf_path, augmented_path)
    return result


def build_p2_report(result: P2ConversionResult, request: TarchConversionRequestV1,
                    plan_view: PlanViewIntentV1, tooling, source_dxf: Path,
                    augmented_dxf: Path | None) -> ConversionReportV1:
    """Build the full ConversionReportV1 (zones + cavities + all 10 gates)."""
    affine = plan_view.world_from_source_m
    mpu = request.metres_per_unit
    p1_report = build_p1_report(result.p1, request, plan_view, tooling,
                                hashlib.sha256(Path(source_dxf).read_bytes()).hexdigest())

    # cavities (claimed_by resolved against the parallel claims list)
    claimed_indices = {c["cavity_index"] for c in result.claims}
    cavities_r: list[CavityReportV1] = []
    # order cavities the same way S6 ordered them for stable cavity_id pairing
    ordered = sorted(enumerate(result.cavities),
                     key=lambda kv: (round(kv[1].bounds[0], 6), round(kv[1].bounds[1], 6)))
    claim_by_index = {c["cavity_index"]: c for c in result.claims}
    for k, (orig_i, g) in enumerate(ordered):
        claim = claim_by_index.get(orig_i)
        cavities_r.append(CavityReportV1(
            cavity_id=f"c_{k:02d}", floor_id=plan_view.floor_id,
            area_m2=g.area * mpu * mpu,
            vertices_m=[_to_world((x, y), affine) for x, y in list(g.exterior.coords)[:-1]],
            claimed_by=(claim["zone_id"] if claim else None),
            claim_source=("intent_file" if claim else "unclaimed")))

    # zones (edges carry their recorded basis + thickness — the D7/G8 compensation record;
    # source_handles = the real source wall-line handle(s) the cavity edge lay on; the
    # derived GTV3_ZONE handle is the zoning LINE emitted for wall_axis edges only)
    zeh = result.gtv3_zone_edge_handles or {}
    zones_r: list[ZoneReportV1] = []
    for k, (z, claim) in enumerate(zip(result.zones, result.claims)):
        edges_r: list[ZoneEdgeReportV1] = []
        verts = z.vertices
        m = len(verts)
        for i, edge in enumerate(z.edges):
            if edge.basis is None:
                continue  # thickness-change step (no wall-basis record)
            a, b = verts[i], verts[(i + 1) % m]
            edges_r.append(ZoneEdgeReportV1(
                p1=_to_world(a, affine), p2=_to_world(b, affine), basis=edge.basis,
                thickness_m=(edge.thickness_native or 0.0) * mpu,
                offset_m=edge.offset_native * mpu,
                derived_handle=zeh.get((k, i)),
                source_handles=edge.source_handles,
                thickness_evidence=edge.thickness_evidence))
        if not edges_r:
            continue
        zones_r.append(ZoneReportV1(
            zone_id=claim["zone_id"], floor_id=plan_view.floor_id, name=claim["name"],
            role=claim["role"],
            role_source=("declared_absent" if claim["role"] == "unspecified" else "intent_file"),
            seed_point_world_m=_to_world(z.seed_native, affine),
            polygon_m=PolygonIRV1(exterior=RingV1(vertices=[_to_world(v, affine) for v in verts])),
            edges=edges_r))

    all_gates_passed = {g.id for g in result.gates} == {f"G{i}" for i in range(1, 11)} and all(
        g.passed for g in result.gates)
    status = "PASS" if not result.has_block and all_gates_passed else "BLOCKED"
    norm_hash = None
    if status == "PASS":
        norm_hash = hashlib.sha256(Path(augmented_dxf).read_bytes()).hexdigest() \
            if augmented_dxf is not None \
            else hashlib.sha256(Path(source_dxf).read_bytes()).hexdigest()
    audit_rows = []
    intents = {v.id: v for v in request.elevation_views if isinstance(v, DatumBoundNamedElevationViewIntentV3)}
    for rec in sorted(result.elevation_records, key=lambda r: (r.view_id, r.kind, r.raw_handles)):
        intent = intents[rec.view_id]; axis = intent.world_along_from_source_m.source_axis; zaxis = intent.world_z_from_source_m.source_axis
        source_along = (rec.rect[0], rec.rect[2]) if axis == "x" else (rec.rect[1], rec.rect[3])
        source_z = (rec.rect[0], rec.rect[2]) if zaxis == "x" else (rec.rect[1], rec.rect[3])
        audit_rows.append({"evidence_id": f"ev_{rec.view_id}_{min(rec.raw_handles).lower()}", "view_id": rec.view_id,
                           "facade_family": rec.facade, "floor_id": intent.floor_ids[0], "kind": rec.kind,
                           "elevation_source_along_interval": list(source_along),
                           "world_along_interval": sorted([x * intent.world_along_from_source_m.scale + intent.world_along_from_source_m.offset for x in source_along]),
                           "z_interval": sorted([x * intent.world_z_from_source_m.scale + intent.world_z_from_source_m.offset for x in source_z]),
                           "datum_entity_handle": rec.datum_handle, "datum_source_start_point": list(rec.datum_start), "datum_source_end_point": list(rec.datum_end),
                           "declared_world_along_lo_source_endpoint": rec.declared_lo_endpoint,
                           "mapped_endpoint_pair": f"{rec.declared_lo_endpoint}->plan.lo", "raw_source_handles": list(rec.raw_handles), "structural_source_handles": list(rec.structural_handles)})
    return ConversionReportV1(
        report_version=1, status=status, case=request.case,
        source_dxf_sha256=hashlib.sha256(Path(source_dxf).read_bytes()).hexdigest(),
        normalized_dxf_sha256=norm_hash,
        request_sha256=request.request_sha256,
        judge_config_sha256=tooling.judge_config_sha256,
        vg_config_sha256=tooling.vg_config_sha256,
        converter_sha256=converter_sha256(),
        profile_version=1, quantization_step_m=derive_quantization_step(tooling),
        walls=p1_report.walls, openings=p1_report.openings, cavities=cavities_r, zones=zones_r,
        gates=result.gates, diagnostics=result.diagnostics,
        wall_proof_coverage=p1_report.wall_proof_coverage,
        zone_intent_coverage={"expected_count": plan_view.zone_intent.expected_count,
                              "cavity_count": len(result.cavities),
                              "near_threshold_faces": result.near_threshold_faces},
        elevation_audit_rows=audit_rows)


__all__ = [
    "run_p1_plan_view", "build_p1_report", "converter_sha256",
    "P1PlanViewGeometry", "ResolvedOpening", "WallBand",
    "run_p2_conversion", "build_p2_report", "P2ConversionResult", "ZoneExpansion",
    "g8_reconstruct_wall_region", "s5_identify_cavities", "s6_bind_intent",
    "s7_expand_zones", "GTV3_FOOTPRINT_LAYER", "GTV3_ZONE_LAYER", "GTV3_OPENING_LAYER", "GTV3_ELEV_OPENING_LAYER", "elevation_block_definition_sha256",
]
