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
from shapely.geometry import Point
from shapely.geometry import LineString, MultiLineString, Polygon

from src.agent.correction.cell_geometry import (
    cell_has_polygon,
    cell_polygon as _validated_cell_polygon,
)
from src.agent.correction.schema import Cell, CorrectedGeometry
from src.agent.correction.footprint import footprint_bbox
from src.agent.geometry.capability import FEATURE_CELL_POLYGON, require_supported_geometry_contract, schema_supports

# Shared tolerances (single source; split_pairing imports these).
_MIN_EDGE = 0.10      # m — below this a face is a degenerate sliver (gate floor)
_Z_TOL = 0.02         # m — floors stack when |lower ceiling z - upper floor z| <= this
_AREA_MIN = 0.05      # m^2 — ignore overlaps/segments smaller than this
_NAME_QUANT = 6       # shared precision for deterministic public-name keys


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
    role: str = "office"    # semantic role (for zone_specs serialization)
    handle: str = ""        # short deterministic public handle, e.g. Z01


@dataclass
class BuildingGeometry:
    zones: list[str] = field(default_factory=list)
    surfaces: list[Surface] = field(default_factory=list)
    windows: list[Window] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    zone_volumes: list[ZoneVolume] = field(default_factory=list)  # for serialization


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


def _q(value: float) -> float:
    return round(float(value), _NAME_QUANT)


def _qpt(pt) -> tuple[float, float]:
    return (_q(pt[0]), _q(pt[1]))


def _role_token(role: str | None) -> str:
    raw = str(role or "").strip()
    if not raw:
        raw = "office"
    parts = re.findall(r"[A-Za-z0-9]+", raw)
    titled = "_".join(part[:1].upper() + part[1:].lower() for part in parts)
    token = re.sub(r"_+", "_", _safe(titled)).strip("_")
    return token or "Office"


def _canonical_ring(poly: Polygon) -> tuple[tuple[float, float], ...]:
    coords = [_qpt(p) for p in list(poly.exterior.coords)[:-1]]
    if len(coords) < 3:
        return tuple(coords)
    if not _is_ccw(coords + [coords[0]]):
        coords = list(reversed(coords))
    start = min(range(len(coords)), key=lambda i: (coords[i][1], coords[i][0]))
    return tuple(coords[start:] + coords[:start])


def _geometry_fingerprint(poly: Polygon) -> tuple:
    minx, miny, maxx, maxy = poly.bounds
    return (
        (_q(minx), _q(miny), _q(maxx), _q(maxy)),
        _q(poly.area),
        _canonical_ring(poly),
    )


def _zone_centroid_key(poly: Polygon) -> tuple[float, float]:
    c = poly.centroid
    return (_q(-c.y), _q(c.x))


def _zone_quadrant(poly: Polygon, footprint_x: list[float], footprint_y: list[float]) -> str:
    cx = (float(footprint_x[0]) + float(footprint_x[1])) / 2.0
    cy = (float(footprint_y[0]) + float(footprint_y[1])) / 2.0
    half_w = max(abs(float(footprint_x[1]) - float(footprint_x[0])) / 2.0, 1e-9)
    half_h = max(abs(float(footprint_y[1]) - float(footprint_y[0])) / 2.0, 1e-9)
    p = poly.centroid
    dx, dy = p.x - cx, p.y - cy
    tol_x = min(half_w * 0.05, 0.5) + 1e-6
    tol_y = min(half_h * 0.05, 0.5) + 1e-6
    near_x = abs(dx) <= tol_x
    near_y = abs(dy) <= tol_y
    if near_x and near_y:
        return "C"
    ns = "" if near_y else ("N" if dy > 0 else "S")
    ew = "" if near_x else ("E" if dx > 0 else "W")
    return ns + ew


def _cell_polygon(c: Cell) -> Polygon:
    """Cell -> validated CCW shapely Polygon. Prefer explicit polygon."""
    return _validated_cell_polygon(c, min_edge_length_m=_MIN_EDGE)


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
def _local_outward_normal(p1, p2, owner_poly: Polygon) -> np.ndarray | None:
    """Return the wall's local outward XY normal for a segment on owner_poly.

    A single zone centroid/representative point is not enough for concave cells:
    a boundary edge in one wing can have the global representative point on the
    other side of the edge. Probe both sides of the segment midpoint and pick
    the side outside the owning polygon.
    """
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = float(np.hypot(dx, dy))
    if length <= 1e-12:
        return None
    mid = np.array([(p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0], dtype=float)
    n1 = np.array([dy / length, -dx / length], dtype=float)
    eps = min(1e-4, max(length / 1000.0, 1e-7))
    inside1 = owner_poly.covers(Point(*(mid + n1 * eps)))
    inside2 = owner_poly.covers(Point(*(mid - n1 * eps)))
    if inside1 and not inside2:
        return np.array([-n1[0], -n1[1], 0.0])
    if inside2 and not inside1:
        return np.array([n1[0], n1[1], 0.0])
    return None


def _wall_verts(p1, p2, zf, zt, interior_pt, owner_poly: Polygon | None = None) -> list:
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
    nrm = _local_outward_normal(p1, p2, owner_poly) if owner_poly is not None else None
    if nrm is None:
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


# Outward normal (x, y) a wall must have to belong to a given facade.
_FACADE_NORMAL = {
    "north": (0.0, 1.0),
    "south": (0.0, -1.0),
    "east": (1.0, 0.0),
    "west": (-1.0, 0.0),
}


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
    """Pick the zone's exterior wall on the window facade whose XY span covers it.

    The wall's outward normal must point in the facade direction — a span/axis
    match alone is not enough (a full-depth room has constant-y exterior walls
    on BOTH north and south; without the normal check a South window would
    silently attach to whichever matching wall came last)."""
    span = sorted(float(s) for s in w.span)
    axis = _facade_axis(w.facade)
    want = _FACADE_NORMAL[w.facade.strip().lower()]
    matches: list[Surface] = []
    seam_hits: list[dict] = []
    for s in surfaces:
        if s.zone != zone or s.stype != "Wall" or s.obc != "Outdoors":
            continue
        n = _newell(s.verts)
        if float(n[0] * want[0] + n[1] * want[1]) < 0.9:
            continue  # wall does not face the window's facade
        xs = [v[0] for v in s.verts]
        ys = [v[1] for v in s.verts]
        # wall must be (near) constant in the facade-normal axis and span the window
        if axis == "y":  # N/S facade: wall runs along x, ~constant y
            if max(ys) - min(ys) > 0.05:
                continue
            seg = (min(xs), max(xs))
        else:            # E/W facade: wall runs along y, ~constant x
            if max(xs) - min(xs) > 0.05:
                continue
            seg = (min(ys), max(ys))
        on_lower_seam = abs(span[0] - seg[0]) <= 0.05 or abs(span[0] - seg[1]) <= 0.05
        on_upper_seam = abs(span[1] - seg[0]) <= 0.05 or abs(span[1] - seg[1]) <= 0.05
        if on_lower_seam or on_upper_seam:
            seam_hits.append({"surface": s.name, "segment_span": seg})
            continue
        if seg[0] + 0.05 < span[0] and span[1] < seg[1] - 0.05:
            matches.append(s)
    if seam_hits:
        raise ValueError(
            f"window {w.id}: ambiguous parent wall on {w.facade} for {w.room}; "
            f"window span {span} lands on wall segment seam(s): {seam_hits}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"window {w.id}: ambiguous parent wall on {w.facade} for {w.room}; "
            f"window span {span} falls inside {len(matches)} same-orientation "
            f"wall segment spans: {[s.name for s in matches]}"
        )
    return matches[0] if matches else None


# --------------------------------------------------------------------------- #
# zone volumes + window attachment (geometry realization, not topology)
# --------------------------------------------------------------------------- #
def build_zone_volumes(
    geom: CorrectedGeometry, *, capability_profile: str = "rectangular"
) -> tuple[list[ZoneVolume], list[str]]:
    """Cells -> zone volumes, returned in deterministic public-name order. Also returns tiling
    guard notes: same-floor cells must not overlap (a correction stage defect — e.g. a
    corridor placed over the rooms it should sit between produces same-side walls
    the gate rejects). Flag, don't paper over.

    Hard guards (raise, never silently corrupt — the InterZone gate is blind to
    both failure classes):
      - cell ids must be globally unique across floors (every id-keyed map in
        split_pairing / window attachment is last-wins on duplicates);
      - the z-stack must be contiguous: a gap/overlap beyond the pairing
        tolerance would silently model an internal floor interface as Roof +
        exposed Floor (mid-building outdoors) with zero gate issues.
    """
    require_supported_geometry_contract(geom, capability_profile)

    # ---- source-id uniqueness guard ----
    floor_of_id: dict[str, str] = {}
    for fl in geom.floors:
        for c in fl.cells:
            if cell_has_polygon(c) and not schema_supports(geom, FEATURE_CELL_POLYGON):
                raise ValueError(
                    f"cell {c.id}: polygon requires schema_version '2' or a schema version with feature '{FEATURE_CELL_POLYGON}'"
                )
            if c.id in floor_of_id:
                raise ValueError(
                    f"duplicate cell id '{c.id}' on floors '{floor_of_id[c.id]}' "
                    f"and '{fl.name}' — cell ids must be globally unique across "
                    f"floors (A0 id_uniqueness); duplicates silently merge zones "
                    f"and mis-pair surfaces"
                )
            floor_of_id[c.id] = fl.name

    # ---- z-stack continuity guard ----
    floors_by_z = sorted(enumerate(geom.floors), key=lambda item: float(item[1].z_floor))
    for prev, cur in zip(floors_by_z, floors_by_z[1:]):
        top = float(prev[1].z_floor) + float(prev[1].ceiling_height)
        gap = float(cur[1].z_floor) - top
        if abs(gap) > _Z_TOL:
            raise ValueError(
                f"broken z-stack: floor '{cur[1].name}' starts at z={cur[1].z_floor} "
                f"but floor '{prev[1].name}' tops out at z={top} (gap {gap:+.3f} m "
                f"> {_Z_TOL} m tolerance) — split-pairing would silently model "
                f"this interface as Roof + exposed Floor (mid-building outdoors); "
                f"fix the correction-stage z values"
            )

    zvs: list[ZoneVolume] = []
    notes: list[str] = []
    floor_name_by_rank: dict[int, str] = {}
    for rank, (_orig_i, fl) in enumerate(floors_by_z):
        floor_name_by_rank[rank] = fl.name
        zf = float(fl.z_floor)
        zt = zf + float(fl.ceiling_height)
        for c in fl.cells:
            zvs.append(
                ZoneVolume(
                    "", c.id, _cell_polygon(c), zf, zt, rank,
                    getattr(c, "role", "office") or "office",
                )
            )

    seen_fingerprint: dict[tuple[int, tuple], str] = {}
    for zv in zvs:
        fp = _geometry_fingerprint(zv.polygon)
        key = (zv.fi, fp)
        if key in seen_fingerprint:
            raise ValueError(
                f"duplicate same-floor zone geometry fingerprint for cell ids "
                f"'{seen_fingerprint[key]}' and '{zv.cell_id}' — deterministic "
                f"zone serials require unique geometry"
            )
        seen_fingerprint[key] = zv.cell_id

    zvs.sort(
        key=lambda zv: (
            zv.fi,
            *_zone_centroid_key(zv.polygon),
            _geometry_fingerprint(zv.polygon),
            _safe(zv.cell_id),
        )
    )
    width = max(2, len(str(len(zvs))))
    for idx, zv in enumerate(zvs, start=1):
        zv.handle = f"Z{idx:0{width}d}"
        role = _role_token(zv.role)
        (fx0, fx1), (fy0, fy1) = footprint_bbox(geom, geom.floors[zv.fi])
        quadrant = _zone_quadrant(zv.polygon, [fx0, fx1], [fy0, fy1])
        zv.zone = f"{zv.handle}_F{zv.fi + 1}_{role}_{quadrant}"

    by_fi: dict[int, list[ZoneVolume]] = {}
    for zv in zvs:
        by_fi.setdefault(zv.fi, []).append(zv)
    for fi, group in by_fi.items():
        fname = floor_name_by_rank.get(fi, f"F{fi + 1}")
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                ov = group[i].polygon.intersection(group[j].polygon).area
                if ov > _AREA_MIN:
                    notes.append(
                        f"OVERLAP: cells '{group[i].cell_id}' and "
                        f"'{group[j].cell_id}' on floor {fname} overlap by "
                        f"{ov:.2f} m^2 — cells must tile, not overlap "
                        f"(upstream correction stage/correction defect)"
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
    pending: list[tuple[Window, str]] = []
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
            win = Window("", parent.name, verts)
            windows.append(win)
            pending.append((win, str(w.id)))

    by_parent: dict[str, list[tuple[Window, str]]] = {}
    for win, src in pending:
        by_parent.setdefault(win.parent, []).append((win, str(src)))

    def win_key(item: tuple[Window, str]) -> tuple:
        win, src = item
        xs = [v[0] for v in win.verts]
        ys = [v[1] for v in win.verts]
        zs = [v[2] for v in win.verts]
        if max(xs) - min(xs) >= max(ys) - min(ys):
            a0, a1 = min(xs), max(xs)
        else:
            a0, a1 = min(ys), max(ys)
        return (_q(a0), _q(a1), _q(min(zs)), _q(max(zs)), _safe(src))

    named: list[Window] = []
    for parent in sorted(by_parent):
        items = sorted(by_parent[parent], key=win_key)
        for idx, (win, _src) in enumerate(items, start=1):
            win.name = f"{parent}_Win{idx}"
            named.append(win)
    return named, notes
