"""Deterministic geometry build + split-pairing (shapely, polygon-native).

Input  : CorrectedGeometry (room cells per floor, polygon or x/y rect, + windows)
Output : BuildingGeometry (zones + fully-resolved surfaces + windows)

Surfaces carry vertices (CCW from outside), OBC (Outdoors/Ground/Surface), and for
interzone faces a reciprocal `obc_obj`. Split-pairing:
  - vertical interior walls: per same-floor cell pair, the shared boundary segment
    becomes a reciprocal wall pair; the rest of each cell edge is exterior (Outdoors)
  - horizontal floor/ceiling: a cell's ceiling ∩ each stacked upper-floor cell's
    footprint becomes a reciprocal ceiling/floor pair; uncovered ceiling -> roof
    (Outdoors); bottom floor -> Ground

Geometry only — no physics. Tolerances reuse the InterZone gate's thresholds so a
clean build passes the gate by construction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import unary_union

from src.agent.correction.schema import Cell, CorrectedGeometry, Floor

_MIN_EDGE = 0.10      # m — below this a face is a degenerate sliver (gate floor)
_Z_TOL = 0.02         # m — floors stack when |lower ceiling z - upper floor z| <= this
_AREA_MIN = 0.05      # m^2 — ignore overlaps/segments smaller than this


@dataclass
class Surface:
    name: str
    zone: str
    stype: str              # Wall | Floor | Ceiling | Roof
    verts: list[tuple[float, float, float]]   # CCW from outside
    obc: str                # Outdoors | Ground | Surface | Adiabatic
    obc_obj: str = ""       # reciprocal target surface name (Surface only)


@dataclass
class Window:
    name: str
    parent: str             # parent wall surface name
    verts: list[tuple[float, float, float]]


@dataclass
class BuildingGeometry:
    zones: list[str] = field(default_factory=list)
    surfaces: list[Surface] = field(default_factory=list)
    windows: list[Window] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _safe(name: str) -> str:
    """EnergyPlus-safe identifier: letters/digits/_ only."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(name))


def _cell_polygon(c: Cell) -> Polygon:
    """Cell -> CCW shapely Polygon. Prefer an explicit `polygon`; else x/y rect."""
    poly = getattr(c, "polygon", None) or (
        c.__pydantic_extra__ or {}
    ).get("polygon")
    if poly:
        ring = [(float(p[0]), float(p[1])) for p in poly]
    else:
        x0, x1 = float(c.x[0]), float(c.x[1])
        y0, y1 = float(c.y[0]), float(c.y[1])
        ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    p = Polygon(ring)
    if not p.is_valid:
        p = p.buffer(0)
    # normalize to CCW exterior
    if p.exterior is not None and not _is_ccw(list(p.exterior.coords)):
        p = Polygon(list(p.exterior.coords)[::-1])
    return p


def _is_ccw(coords: list) -> bool:
    s = 0.0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i][0], coords[i][1]
        x2, y2 = coords[i + 1][0], coords[i + 1][1]
        s += (x2 - x1) * (y2 + y1)
    return s < 0  # shoelace: negative sum => CCW


def _newell(verts: list[tuple[float, float, float]]) -> np.ndarray:
    pts = np.asarray(verts, float)
    n = np.zeros(3)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    m = np.linalg.norm(n)
    return n / m if m > 1e-12 else n


def _orient(verts: list, desired: np.ndarray) -> list:
    """Reverse vertex order if the polygon normal opposes `desired`."""
    if float(np.dot(_newell(verts), desired)) < 0:
        return verts[::-1]
    return verts


def _iter_segments(geom):
    """Yield straight ((x1,y1),(x2,y2)) segments from a Line/MultiLineString."""
    if geom is None or geom.is_empty:
        return
    lines = []
    if isinstance(geom, LineString):
        lines = [geom]
    elif isinstance(geom, MultiLineString):
        lines = list(geom.geoms)
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            if isinstance(g, (LineString, MultiLineString)):
                yield from _iter_segments(g)
        return
    for ln in lines:
        cs = list(ln.coords)
        for i in range(len(cs) - 1):
            p1, p2 = cs[i], cs[i + 1]
            if LineString([p1, p2]).length >= _MIN_EDGE:
                yield (float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1]))


def _wall_verts(p1, p2, zf, zt, interior_pt) -> list:
    """Vertical wall rectangle, oriented so the outward normal points away from
    `interior_pt` (the owning zone's centroid)."""
    v = [
        (p1[0], p1[1], zt),
        (p2[0], p2[1], zt),
        (p2[0], p2[1], zf),
        (p1[0], p1[1], zf),
    ]
    # outward horizontal direction: perpendicular to (p2-p1), away from interior
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    nrm = np.array([dy, -dx, 0.0])  # one perpendicular
    inward = np.array([interior_pt[0] - mx, interior_pt[1] - my, 0.0])
    if float(np.dot(nrm, inward)) > 0:  # points toward interior -> flip desired
        nrm = -nrm
    return _orient(v, nrm)


def _ring_verts(poly: Polygon, z: float, up: bool) -> list:
    coords = list(poly.exterior.coords)[:-1]
    v = [(float(x), float(y), z) for x, y in coords]
    return _orient(v, np.array([0.0, 0.0, 1.0 if up else -1.0]))


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def build_geometry(geom: CorrectedGeometry) -> BuildingGeometry:
    out = BuildingGeometry()
    floors: list[Floor] = list(geom.floors)

    # cell id -> (floor index, polygon, zf, zt, zone name)
    polys: dict[str, Polygon] = {}
    meta: dict[str, dict] = {}
    for fi, fl in enumerate(floors):
        zf = float(fl.z_floor)
        zt = zf + float(fl.ceiling_height)
        for c in fl.cells:
            zone = _safe(c.id)
            polys[c.id] = _cell_polygon(c)
            meta[c.id] = {"fi": fi, "zf": zf, "zt": zt, "zone": zone}
            out.zones.append(zone)

    # tiling guard: same-floor cells must not overlap (a phase2a defect — e.g. a
    # corridor placed over the rooms it should sit between). Flag, don't paper over:
    # overlapping cells produce same-side walls the gate rejects as non-opposite.
    _floor_cells: dict[int, list[str]] = {}
    for cid, m in meta.items():
        _floor_cells.setdefault(m["fi"], []).append(cid)
    for fi, cids in _floor_cells.items():
        for i in range(len(cids)):
            for j in range(i + 1, len(cids)):
                ov = polys[cids[i]].intersection(polys[cids[j]]).area
                if ov > _AREA_MIN:
                    out.notes.append(
                        f"OVERLAP: cells '{cids[i]}' and '{cids[j]}' on floor "
                        f"{floors[fi].name} overlap by {ov:.2f} m^2 — cells must tile, "
                        f"not overlap (upstream phase2a/correction defect)"
                    )

    # name registry to keep surface names unique
    used: set[str] = set()

    def uname(base: str) -> str:
        nm = _safe(base)
        i = 1
        cand = nm
        while cand in used:
            i += 1
            cand = f"{nm}_{i}"
        used.add(cand)
        return cand

    surf_index: dict[str, Surface] = {}

    def add(zone, stype, verts, obc, obc_obj="") -> Surface:
        s = Surface(uname(f"{zone}_{stype}"), zone, stype, verts, obc, obc_obj)
        out.surfaces.append(s)
        surf_index[s.name] = s
        return s

    # ---- 1. vertical walls + same-floor interzone pairing ----
    by_floor: dict[int, list[str]] = {}
    for cid, m in meta.items():
        by_floor.setdefault(m["fi"], []).append(cid)

    # shared boundary per cell (accumulate to subtract for exterior)
    shared_acc: dict[str, list] = {cid: [] for cid in meta}

    for fi, cids in by_floor.items():
        for ai in range(len(cids)):
            for bi in range(ai + 1, len(cids)):
                A, B = cids[ai], cids[bi]
                inter = polys[A].boundary.intersection(polys[B].boundary)
                for p1, p2 in _iter_segments(inter):
                    zf, zt = meta[A]["zf"], meta[A]["zt"]
                    wa = _wall_verts(p1, p2, zf, zt, polys[A].representative_point().coords[0])
                    wb = _wall_verts(p1, p2, zf, zt, polys[B].representative_point().coords[0])
                    sa = add(meta[A]["zone"], "Wall", wa, "Surface")
                    sb = add(meta[B]["zone"], "Wall", wb, "Surface")
                    sa.obc_obj, sb.obc_obj = sb.name, sa.name
                    shared_acc[A].append(LineString([p1, p2]))
                    shared_acc[B].append(LineString([p1, p2]))

    # exterior wall segments = cell boundary minus all shared segments
    for cid, m in meta.items():
        boundary = polys[cid].boundary
        if shared_acc[cid]:
            ext = boundary.difference(unary_union(shared_acc[cid]).buffer(1e-6))
        else:
            ext = boundary
        for p1, p2 in _iter_segments(ext):
            wv = _wall_verts(p1, p2, m["zf"], m["zt"], polys[cid].representative_point().coords[0])
            add(m["zone"], "Wall", wv, "Outdoors")

    # ---- 2. horizontal floor/ceiling + cross-floor pairing ----
    fi_to_z = {}
    for cid, m in meta.items():
        fi_to_z.setdefault(m["fi"], (m["zf"], m["zt"]))

    for cid, m in meta.items():
        fi, zf, zt, zone = m["fi"], m["zf"], m["zt"], m["zone"]
        poly = polys[cid]

        # FLOOR
        if fi == 0:
            add(zone, "Floor", _ring_verts(poly, zf, up=False), "Ground")
        else:
            lower = [c for c in by_floor.get(fi - 1, []) if abs(meta[c]["zt"] - zf) <= _Z_TOL]
            covered = []
            for L in lower:
                ov = poly.intersection(polys[L])
                for piece in _polys(ov):
                    if piece.area < _AREA_MIN:
                        continue
                    fs = add(zone, "Floor", _ring_verts(piece, zf, up=False), "Surface")
                    cs = add(meta[L]["zone"], "Ceiling", _ring_verts(piece, zf, up=True), "Surface")
                    fs.obc_obj, cs.obc_obj = cs.name, fs.name
                    covered.append(piece)
            rem = poly.difference(unary_union(covered)) if covered else poly
            for piece in _polys(rem):
                if piece.area >= _AREA_MIN:
                    add(zone, "Floor", _ring_verts(piece, zf, up=False), "Outdoors")  # exposed underside

        # CEILING / ROOF (paired ceilings already created above from the lower side;
        # here handle the uncovered remainder of THIS cell's ceiling = roof)
        upper = [c for c in by_floor.get(fi + 1, []) if abs(meta[c]["zf"] - zt) <= _Z_TOL]
        covered_top = []
        for U in upper:
            ov = poly.intersection(polys[U])
            for piece in _polys(ov):
                if piece.area >= _AREA_MIN:
                    covered_top.append(piece)
        rem_top = poly.difference(unary_union(covered_top)) if covered_top else (
            None if not upper else poly
        )
        if not upper:
            add(zone, "Roof", _ring_verts(poly, zt, up=True), "Outdoors")
        elif rem_top is not None:
            for piece in _polys(rem_top):
                if piece.area >= _AREA_MIN:
                    add(zone, "Roof", _ring_verts(piece, zt, up=True), "Outdoors")

    # ---- 3. windows -> sub-surface on the room's exterior wall on that facade ----
    for w in geom.windows:
        if w.room not in meta:
            out.notes.append(f"window {w.id}: room '{w.room}' not found; skipped")
            continue
        m = meta[w.room]
        parent = _find_parent_wall(out, m["zone"], w, surf_index)
        if parent is None:
            out.notes.append(f"window {w.id}: no exterior wall on {w.facade} for {w.room}")
            continue
        verts = _window_verts(w, parent)
        if verts:
            out.windows.append(Window(uname(f"{m['zone']}_Win"), parent.name, verts))

    return out


def _polys(geom):
    """Yield Polygon parts from a possibly-Multi/GeometryCollection result."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            if isinstance(g, Polygon) and not g.is_empty:
                yield g


def _facade_axis(facade: str) -> str:
    return "x" if facade.lower().startswith(("e", "w")) else "y"


def _find_parent_wall(out: BuildingGeometry, zone: str, w, surf_index) -> Surface | None:
    """Pick the zone's exterior wall on window facade whose XY span covers the window."""
    span = sorted(float(s) for s in w.span)
    axis = _facade_axis(w.facade)
    best = None
    for s in out.surfaces:
        if s.zone != zone or s.stype != "Wall" or s.obc != "Outdoors":
            continue
        xs = [v[0] for v in s.verts]
        ys = [v[1] for v in s.verts]
        # wall must be (near) constant in the facade-normal axis and span the window
        if axis == "y":  # N/S facade: wall runs along x, ~constant y
            if max(ys) - min(ys) > 0.05:
                continue
            if min(xs) - 0.05 <= span[0] and max(xs) + 0.05 >= span[1]:
                best = s
        else:            # E/W facade: wall runs along y, ~constant x
            if max(xs) - min(xs) > 0.05:
                continue
            if min(ys) - 0.05 <= span[0] and max(ys) + 0.05 >= span[1]:
                best = s
    return best


def _window_verts(w, parent: Surface) -> list:
    """Window rectangle on the parent wall's plane, CCW from outside."""
    span = sorted(float(s) for s in w.span)
    z0, z1 = sorted(float(z) for z in w.z)
    axis = _facade_axis(w.facade)
    if axis == "y":  # N/S: plane y=const
        y = parent.verts[0][1]
        v = [(span[0], y, z0), (span[1], y, z0), (span[1], y, z1), (span[0], y, z1)]
    else:            # E/W: plane x=const
        x = parent.verts[0][0]
        v = [(x, span[0], z0), (x, span[1], z0), (x, span[1], z1), (x, span[0], z1)]
    # orient to match the parent wall's outward normal
    return _orient(v, _newell(parent.verts))
