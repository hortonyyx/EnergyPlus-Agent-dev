"""切配·仿真 — split-pairing (which faces exist + 1:1 reciprocal correspondence).

Leg-agnostic: consumes a list of `ZoneVolume` (footprint polygon + z range) and
decides every face's existence and outside-boundary condition. Adjacent faces are
cut at the union of both sides' breaks so each interzone face corresponds 1:1 with
exactly one opposite face, with reciprocal `Outside Boundary Condition = Surface`.
The zonification regime (faithful rooms vs re-topologized thermal blocks) only
changes the input count, never this algorithm.

  - vertical interior walls: per same-floor cell pair, the shared boundary segment
    becomes a reciprocal wall pair; the rest of each cell edge is exterior (Outdoors)
  - horizontal floor/ceiling: a cell's ceiling ∩ each stacked upper-floor cell's
    footprint becomes a reciprocal ceiling/floor pair; uncovered ceiling -> roof
    (Outdoors); bottom floor -> Ground; exposed floor underside -> Outdoors

Tolerances reuse the InterZone gate's thresholds so a clean build passes by
construction. Imports geometry primitives from `modelling` only (one-way dep).
"""

from __future__ import annotations

from shapely.geometry import LineString
from shapely.ops import unary_union

from src.agent.geometry.modelling import (
    _AREA_MIN,
    _Z_TOL,
    NameRegistry,
    Surface,
    ZoneVolume,
    _iter_segments,
    _polys,
    _ring_verts,
    _wall_verts,
)


def pair_surfaces(zvs: list[ZoneVolume], registry: NameRegistry) -> list[Surface]:
    surfaces: list[Surface] = []

    def add(zone, stype, verts, obc, obc_obj="") -> Surface:
        s = Surface(registry.uname(f"{zone}_{stype}"), zone, stype, verts, obc, obc_obj)
        surfaces.append(s)
        return s

    zv_by_id: dict[str, ZoneVolume] = {zv.cell_id: zv for zv in zvs}
    by_floor: dict[int, list[str]] = {}
    for zv in zvs:
        by_floor.setdefault(zv.fi, []).append(zv.cell_id)

    # ---- 1. vertical walls + same-floor interzone pairing ----
    shared_acc: dict[str, list] = {zv.cell_id: [] for zv in zvs}

    for cids in by_floor.values():
        for ai in range(len(cids)):
            for bi in range(ai + 1, len(cids)):
                A, B = cids[ai], cids[bi]
                za, zb = zv_by_id[A], zv_by_id[B]
                inter = za.polygon.boundary.intersection(zb.polygon.boundary)
                for p1, p2 in _iter_segments(inter):
                    # same-floor cells share a z-range, but use each wall's own
                    # zone volume so the code stays correct if that ever changes
                    wa = _wall_verts(
                        p1, p2, za.zf, za.zt, za.polygon.representative_point().coords[0]
                    )
                    wb = _wall_verts(
                        p1, p2, zb.zf, zb.zt, zb.polygon.representative_point().coords[0]
                    )
                    sa = add(za.zone, "Wall", wa, "Surface")
                    sb = add(zb.zone, "Wall", wb, "Surface")
                    sa.obc_obj, sb.obc_obj = sb.name, sa.name
                    shared_acc[A].append(LineString([p1, p2]))
                    shared_acc[B].append(LineString([p1, p2]))

    # exterior wall segments = cell boundary minus all shared segments
    for zv in zvs:
        boundary = zv.polygon.boundary
        if shared_acc[zv.cell_id]:
            ext = boundary.difference(unary_union(shared_acc[zv.cell_id]).buffer(1e-6))
        else:
            ext = boundary
        for p1, p2 in _iter_segments(ext):
            wv = _wall_verts(
                p1, p2, zv.zf, zv.zt, zv.polygon.representative_point().coords[0]
            )
            add(zv.zone, "Wall", wv, "Outdoors")

    # ---- 2. horizontal floor/ceiling + cross-floor pairing ----
    for zv in zvs:
        fi, zf, zt, zone, poly = zv.fi, zv.zf, zv.zt, zv.zone, zv.polygon

        # FLOOR
        if fi == 0:
            add(zone, "Floor", _ring_verts(poly, zf, up=False), "Ground")
        else:
            lower = [
                zv_by_id[c]
                for c in by_floor.get(fi - 1, [])
                if abs(zv_by_id[c].zt - zf) <= _Z_TOL
            ]
            covered = []
            for L in lower:
                ov = poly.intersection(L.polygon)
                for piece in _polys(ov):
                    if piece.area < _AREA_MIN:
                        continue
                    fs = add(zone, "Floor", _ring_verts(piece, zf, up=False), "Surface")
                    cs = add(L.zone, "Ceiling", _ring_verts(piece, zf, up=True), "Surface")
                    fs.obc_obj, cs.obc_obj = cs.name, fs.name
                    covered.append(piece)
            rem = poly.difference(unary_union(covered)) if covered else poly
            for piece in _polys(rem):
                if piece.area >= _AREA_MIN:
                    add(zone, "Floor", _ring_verts(piece, zf, up=False), "Outdoors")

        # CEILING / ROOF (paired ceilings already created above from the lower side;
        # here handle the uncovered remainder of THIS cell's ceiling = roof)
        upper = [
            zv_by_id[c]
            for c in by_floor.get(fi + 1, [])
            if abs(zv_by_id[c].zf - zt) <= _Z_TOL
        ]
        covered_top = []
        for U in upper:
            ov = poly.intersection(U.polygon)
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

    return surfaces
