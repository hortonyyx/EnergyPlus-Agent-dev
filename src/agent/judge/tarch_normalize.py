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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import ezdxf
from ezdxf import bbox as ezdxf_bbox
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize_full, unary_union

from .tarch_converter_schema import (
    Affine2D, ClipBoxDxf, ConversionDiagnosticV1, ConversionReportV1,
    DiagnosticSeverity, GateResultV1, OpeningReportV1, PlanViewIntentV1,
    Point2, StableId, TARCH_DIAGNOSTIC_REGISTRY, TarchConversionRequestV1,
    TarchDialectRulesV1, ThicknessEvidenceV1, WallReportV1,
    WallRibbonSegmentV1, assert_staging_input, derive_quantization_step,
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


def _tols_from(tooling, metres_per_unit: float) -> _Tols:
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
    if name in dialect.window_block_names:
        return "window"
    for pref in dialect.door_block_prefixes:
        if name.startswith(pref):
            return "door"
    return None


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
    walls = [
        WallReportV1(
            band_id=b.band_id, floor_id=result.floor_id, axis=b.axis,
            coord_mm=b.coord_mm, span_mm=[b.along_min_mm, b.along_max_mm],
            segments=[WallRibbonSegmentV1(
                segment_id=b.band_id + "_s0", axis=b.axis, coord_m=b.coord_mm / 1000.0,
                span_m=[b.along_min_mm / 1000.0, b.along_max_mm / 1000.0],
                thickness_evidence=ThicknessEvidenceV1(
                    source_kind="wall_cap_or_opening_jamb",
                    value_m=b.thickness_mm / 1000.0,
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


__all__ = [
    "run_p1_plan_view", "build_p1_report", "converter_sha256",
    "P1PlanViewGeometry", "ResolvedOpening", "WallBand",
]
