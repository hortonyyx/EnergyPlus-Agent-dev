"""建模·几何 — geometry realization vocabulary (no topology decisions).

This module owns the *primitives* for turning corrected room cells into oriented
geometry: the output dataclasses, the per-cell zone volumes, and the functions
that synthesize a face's vertices (walls, floor/ceiling rings, window rects) with
correct outward orientation. It makes **no** decision about which faces exist or
how they correspond — that topology lives in `split_pairing` (which imports from
here, never the reverse).

Polygon-native (shapely): a rectangle is the simple case, so non-orthogonal /
L-shaped rooms need no rewrite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LineString, MultiLineString, Polygon

from src.agent.correction.schema import Cell, CorrectedGeometry

# Shared tolerances (single source; split_pairing imports these).
_MIN_EDGE = 0.10      # m — below this a face is a degenerate sliver (gate floor)
_Z_TOL = 0.02         # m — floors stack when |lower ceiling z - upper floor z| <= this
_AREA_MIN = 0.05      # m^2 — ignore overlaps/segments smaller than this


# --------------------------------------------------------------------------- #
# output dataclasses (re-exported by build.py for back-compat)
# --------------------------------------------------------------------------- #
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


@dataclass
class ZoneVolume:
    """One zone's volume: footprint polygon + z range. The leg-agnostic unit
    `split_pairing` consumes — any zonification (faithful rooms / re-topologized
    thermal blocks) produces these; only the count/granularity differs."""

    zone: str               # EP-safe zone name
    cell_id: str            # original cell id (for window room lookup)
    polygon: Polygon
    zf: float
    zt: float
    fi: int                 # floor membership (every zonification has floors);
                            # actual face pairing is z + polygon driven, not fi


class NameRegistry:
    """Hands out unique EP-safe surface/window names across the whole build."""

    def __init__(self) -> None:
        self.used: set[str] = set()

    def uname(self, base: str) -> str:
        nm = _safe(base)
        i = 1
        cand = nm
        while cand in self.used:
            i += 1
            cand = f"{nm}_{i}"
        self.used.add(cand)
        return cand


# --------------------------------------------------------------------------- #
# low-level primitives (all geometric helpers live here; one-way dep)
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


# --------------------------------------------------------------------------- #
# face vertex synthesis
# --------------------------------------------------------------------------- #
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


def _facade_axis(facade: str) -> str:
    return "x" if facade.lower().startswith(("e", "w")) else "y"


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


def _find_parent_wall(surfaces: list[Surface], zone: str, w) -> Surface | None:
    """Pick the zone's exterior wall on the window facade whose XY span covers it."""
    span = sorted(float(s) for s in w.span)
    axis = _facade_axis(w.facade)
    best = None
    for s in surfaces:
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


# --------------------------------------------------------------------------- #
# zone volumes + window attachment (geometry realization, not topology)
# --------------------------------------------------------------------------- #
def build_zone_volumes(geom: CorrectedGeometry) -> tuple[list[ZoneVolume], list[str]]:
    """Cells -> zone volumes, in floor-major / cell order. Also returns tiling
    guard notes: same-floor cells must not overlap (a phase2a defect — e.g. a
    corridor placed over the rooms it should sit between produces same-side walls
    the gate rejects). Flag, don't paper over."""
    zvs: list[ZoneVolume] = []
    notes: list[str] = []
    for fi, fl in enumerate(geom.floors):
        zf = float(fl.z_floor)
        zt = zf + float(fl.ceiling_height)
        for c in fl.cells:
            zvs.append(
                ZoneVolume(_safe(c.id), c.id, _cell_polygon(c), zf, zt, fi)
            )

    by_fi: dict[int, list[ZoneVolume]] = {}
    for zv in zvs:
        by_fi.setdefault(zv.fi, []).append(zv)
    for fi, group in by_fi.items():
        fname = geom.floors[fi].name
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                ov = group[i].polygon.intersection(group[j].polygon).area
                if ov > _AREA_MIN:
                    notes.append(
                        f"OVERLAP: cells '{group[i].cell_id}' and "
                        f"'{group[j].cell_id}' on floor {fname} overlap by "
                        f"{ov:.2f} m^2 — cells must tile, not overlap "
                        f"(upstream phase2a/correction defect)"
                    )
    return zvs, notes


def attach_windows(
    geom: CorrectedGeometry,
    surfaces: list[Surface],
    zv_by_cell: dict[str, ZoneVolume],
    registry: NameRegistry,
) -> tuple[list[Window], list[str]]:
    """Attach each window to its room's exterior wall on that facade. Runs after
    all walls exist so `_find_parent_wall` sees the finished exterior-wall set."""
    windows: list[Window] = []
    notes: list[str] = []
    for w in geom.windows:
        if w.room not in zv_by_cell:
            notes.append(f"window {w.id}: room '{w.room}' not found; skipped")
            continue
        zone = zv_by_cell[w.room].zone
        parent = _find_parent_wall(surfaces, zone, w)
        if parent is None:
            notes.append(f"window {w.id}: no exterior wall on {w.facade} for {w.room}")
            continue
        verts = _window_verts(w, parent)
        if verts:
            windows.append(Window(registry.uname(f"{zone}_Win"), parent.name, verts))
    return windows, notes
