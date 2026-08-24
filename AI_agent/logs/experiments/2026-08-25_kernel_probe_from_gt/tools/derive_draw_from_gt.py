"""Derive a 1_correction-shaped CorrectedGeometryV3 *draw* straight from a gt.

⛔ EXPLORATORY / DIAGNOSTIC ONLY — the answer is in the INPUT, so nothing this
produces may ever be recorded as a score (CLAUDE.md §0.2 reverse-iron-rule).
Its only purpose: hand the geometry kernel an input whose correctness is not in
question, so a defect observed downstream is the kernel's, not correction's.

Basis note (guide §四之二): gt zones/footprints are "exterior wall = outer skin,
interior wall = axis"; a CorrectedGeometry is centerline throughout.  With
`--basis centerline` the outer skin is pulled in by t/2 (the one conversion the
real correction stage still owes); `--basis outer` leaves gt untouched so the
two runs bracket exactly how much that single conversion is worth.

Window provenance/citation blocks are transplanted from a real correction draw:
a v3 window must cite reading observations, and gt carries no such citations.
Geometry (span / z / host) still comes from gt.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

ROLE_DEFAULT = "office"


def _ring(poly_obj: dict) -> list[list[float]]:
    return [list(map(float, p)) for p in poly_obj["exterior"]["vertices"]]


def _shrink(ring: list[list[float]], inset: float) -> list[list[float]]:
    if inset <= 0:
        return ring
    shrunk = Polygon(ring).buffer(-inset, join_style=2, mitre_limit=100.0)
    if shrunk.is_empty or shrunk.geom_type != "Polygon":
        raise SystemExit(f"footprint shrink by {inset} produced {shrunk.geom_type}")
    return _clean_ring(shrunk.exterior.coords, tag="footprint")


def _clean_ring(coords, *, tag: str) -> list[list[float]]:
    """Drop duplicate and collinear vertices, then force CCW.

    Both are REQUIRED, not cosmetic: pulling the outer skin in to the wall axis
    routinely lands a room corner exactly on the building's re-entrant corner,
    and shapely reports that zero-area touch as a repeated vertex / spike.
    Leaving it in produces a ring the correction core rejects as
    self-intersecting — the true fix is to normalize the ring, not to widen a
    tolerance until the spike is tolerated.
    """
    pts = [(round(float(x), 9), round(float(y), 9)) for x, y in coords]
    if pts and pts[0] == pts[-1]:
        pts = pts[:-1]
    dedup: list[tuple[float, float]] = []
    for pt in pts:
        if not dedup or abs(pt[0] - dedup[-1][0]) > 1e-9 or abs(pt[1] - dedup[-1][1]) > 1e-9:
            dedup.append(pt)
    while len(dedup) > 1 and dedup[0] == dedup[-1]:
        dedup.pop()
    out: list[tuple[float, float]] = []
    n = len(dedup)
    for i in range(n):
        a, b, c = dedup[i - 1], dedup[i], dedup[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) > 1e-9:
            out.append(b)
    if len(out) < 3:
        raise SystemExit(f"{tag}: ring degenerated to {len(out)} vertices")
    poly = Polygon(out)
    if not poly.is_valid:
        raise SystemExit(f"{tag}: normalized ring is still invalid")
    if not poly.exterior.is_ccw:
        out = out[::-1]
    return [[round(x, 6), round(y, 6)] for x, y in out]


def _clip(ring: list[list[float]], clip_poly: Polygon, zid: str) -> list[list[float]]:
    inter = Polygon(ring).intersection(clip_poly)
    if inter.geom_type == "MultiPolygon":
        inter = max(inter.geoms, key=lambda g: g.area)
    if inter.is_empty or inter.geom_type != "Polygon":
        raise SystemExit(f"zone {zid}: clip produced {inter.geom_type}")
    return _clean_ring(inter.exterior.coords, tag=f"zone {zid}")


def _facade_of(gt: dict, floor_id: str, segment_id: str) -> tuple[str, dict]:
    for fl in gt["floors"]:
        if fl["id"] != floor_id:
            continue
        for bs in fl["boundary_segments"]:
            if bs["id"] == segment_id:
                return bs["facade_family"], bs
    raise SystemExit(f"boundary segment {segment_id} not found on {floor_id}")


def _load_donor_windows(donor_path: Path) -> list[dict]:
    return json.loads(donor_path.read_text(encoding="utf-8"))["windows"]


def _match_donor(donor: list[dict], *, floor_name: str, facade: str,
                 span: list[float]) -> dict | None:
    mid = (span[0] + span[1]) / 2.0
    pool = [w for w in donor if w["facade"] == facade and w.get("floor") == floor_name]
    if not pool:
        pool = [w for w in donor if w["facade"] == facade]
    if not pool:
        return None
    return min(pool, key=lambda w: abs((w["span"][0] + w["span"][1]) / 2.0 - mid))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("gt", type=Path)
    ap.add_argument("donor_draw", type=Path,
                    help="a real 1_correction pre-core draw (window citations donor)")
    ap.add_argument("out", type=Path)
    ap.add_argument("--basis", choices=("centerline", "outer"), default="centerline")
    args = ap.parse_args()

    gt = json.loads(args.gt.read_text(encoding="utf-8"))
    donor = json.loads(args.donor_draw.read_text(encoding="utf-8"))
    donor_windows = donor["windows"]
    # gt floor id -> the donor's floor id/name, matched on z (never on ordinal).
    donor_by_z = {round(float(fl["z_floor"]), 3): fl for fl in donor["floors"]}

    floors, clip_polys, floor_map = [], {}, {}
    for fl in gt["floors"]:
        t = {bs.get("wall_thickness_m") for bs in fl["boundary_segments"]}
        if len(t) != 1 or None in t:
            raise SystemExit(f"{fl['id']}: non-uniform exterior thickness {t}")
        inset = (float(t.pop()) / 2.0) if args.basis == "centerline" else 0.0
        fp = _shrink(_ring(fl["footprint"]), inset)
        clip = Polygon(fp)
        clip_polys[fl["id"]] = clip
        dz = donor_by_z.get(round(float(fl["z_floor_m"]), 3))
        if dz is None:
            raise SystemExit(f"no donor floor at z={fl['z_floor_m']}")
        floor_map[fl["id"]] = (dz["id"], dz["name"])
        cells = []
        for z in sorted(fl["zones"], key=lambda r: r["id"]):
            ring = _clip(_ring(z["polygon"]), clip, z["id"])
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            cells.append({
                "id": z["id"], "role": ROLE_DEFAULT,
                "x": [min(xs), max(xs)], "y": [min(ys), max(ys)],
                "polygon": ring,
            })
        floors.append({
            "id": dz["id"], "name": dz["name"],
            "z_floor": float(fl["z_floor_m"]),
            "ceiling_height": float(fl["ceiling_height_m"]),
            "footprint": {"vertices": fp},
            "cells": cells,
        })

    union = unary_union(list(clip_polys.values()))
    minx, miny, maxx, maxy = union.bounds

    windows, unmatched = [], []
    for op in gt["openings"]:
        if op["kind"] != "window":
            continue
        facade, _bs = _facade_of(gt, op["floor_id"], op["boundary_segment_id"])
        fid, fname = floor_map[op["floor_id"]]
        span = [float(op["world_along_interval"]["lo"]), float(op["world_along_interval"]["hi"])]
        zint = [float(op["z_interval"]["lo"]), float(op["z_interval"]["hi"])]
        donor_w = _match_donor(donor_windows, floor_name=fname, facade=facade, span=span)
        if donor_w is None:
            unmatched.append(op["id"])
            continue
        windows.append({
            "id": f"gt_{op['id']}", "floor_id": fid, "facade": facade,
            "span": [round(v, 6) for v in span], "z": [round(v, 6) for v in zint],
            "room": op["host_zone_id"],
            "provenance": donor_w.get("provenance"),
        })

    draw = {
        "schema_version": "3",
        "footprint_x": [round(minx, 6), round(maxx, 6)],
        "footprint_y": [round(miny, 6), round(maxy, 6)],
        "floors": floors,
        "windows": windows,
        "corrections": [], "conflicts": [], "unsupported": [],
        "notes": (f"DIAGNOSTIC draw derived mechanically from {args.gt.name} "
                  f"(basis={args.basis}); NEVER a score."),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(draw, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out}  basis={args.basis}")
    print(f"  floors={len(floors)} cells={sum(len(f['cells']) for f in floors)} "
          f"windows={len(windows)} unmatched={unmatched}")
    print(f"  footprint_x={draw['footprint_x']} footprint_y={draw['footprint_y']}")


if __name__ == "__main__":
    main()
