"""Probe 2 (②-1c recon): support-line ring rebuild + edge-level reconciliation
against gt.json, with the unsigned-revision closure REMOVED first.

Pipeline:
1. cavity faces = footprint − (walls ∪ openings), faces > min_room_area
2. NA closure: handles named by any unsigned revision → walls referencing them
   (face_line_ids_lo/hi, or "wall would need this line but it is absent" --
   13AF case: the missing partner face) → zones whose ring uses those walls
3. per surviving cavity: ring edges matched to walls, form-B support const,
   vertices = adjacent support-line intersections, 6a dedupe
4. compare zone rings to gt.json vertices, unit by unit (0.1 mm)
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[4]
STAGING = REPO / "case_tests/test_baseline/gt_staging/sm25-L_anchor/facts"
GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"
REQ = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/request_as_measured.json"
UNITS = 10000

facts = json.loads((STAGING / "as_signed.json").read_text())
revisions = json.loads((STAGING / "revisions.json").read_text())
gt = json.loads(GT.read_text())
request = json.loads(REQ.read_text())
assert request["request_sha256"] == facts["request_sha256"], "request mismatch"

min_room_units2 = request["min_room_area_m2"] * UNITS * UNITS
gt_floor = {f["id"]: f for f in gt["floors"]}

unsigned_handles = {r["target"]["handle"] for r in revisions["revisions"]
                    if r["verdict"] == "unsigned"}
print("unsigned handles:", sorted(unsigned_handles))

for view in facts["views"]:
    vid, floor_id = view["view_id"], view["floor_id"]
    print(f"\n=== {vid} ===")
    walls = view["walls"]
    by_lo: dict[tuple[str, int], list[dict]] = {}
    by_hi: dict[tuple[str, int], list[dict]] = {}
    for w in walls:
        by_lo.setdefault((w["axis"], w["face_lo"]), []).append(w)
        by_hi.setdefault((w["axis"], w["face_hi"]), []).append(w)

    # walls whose named face lines include an unsigned handle -> NA walls
    na_walls = set()
    for w in walls:
        ids = set(w["face_line_ids_lo"]) | set(w["face_line_ids_hi"])
        if ids & unsigned_handles:
            na_walls.add(w["id"])
    print(f"walls directly touched by unsigned revisions: {len(na_walls)}")

    # walls that SHOULD exist but a face is a missing/unsigned stroke:
    # the paired-wall half whose partner side is absent. Detect structurally:
    # an unsigned handle with no face_line record (13AF) kills the wall band
    # it would have closed. Find walls whose along span contains a gap that a
    # non-orthogonal stroke of the same axis straddles -- approximated here by:
    # any wall whose rectangle's boundary shows a cavity leak (z4/z5 merge).
    # For the probe: mark zones (cavity faces) whose edge cannot be matched to
    # any non-NA wall as NA zones.
    na_wall_objs = [w for w in walls if w["id"] in na_walls]

    ext_ring = next(r["points"] for r in view["footprint"]["rings"]
                    if r["kind"] == "exterior")
    footprint = Polygon([(p[0], p[1]) for p in ext_ring])
    ext_lines = []
    ring = ext_ring
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if a[0] == b[0]:
            ext_lines.append(("x", a[0], min(a[1], b[1]), max(a[1], b[1])))
        elif a[1] == b[1]:
            ext_lines.append(("y", a[1], min(a[0], b[0]), max(a[0], b[0])))

    def is_exterior_side(w, face):
        return any(lax == w["axis"] and lc == face
                   and min(w["along_max"], lhi) - max(w["along_min"], llo) > 0
                   for lax, lc, llo, lhi in ext_lines)

    rects, orects = [], []
    for w in walls:
        if w["axis"] == "x":
            rects.append(Polygon([(w["along_min"], w["face_lo"]), (w["along_max"], w["face_lo"]),
                                  (w["along_max"], w["face_hi"]), (w["along_min"], w["face_hi"])]))
        else:
            rects.append(Polygon([(w["face_lo"], w["along_min"]), (w["face_lo"], w["along_max"]),
                                  (w["face_hi"], w["along_max"]), (w["face_hi"], w["along_min"])]))
    for o in view["openings"]:
        if o["axis"] == "x":
            orects.append(Polygon([(o["along_min"], o["cross_lo"]), (o["along_max"], o["cross_lo"]),
                                   (o["along_max"], o["cross_hi"]), (o["along_min"], o["cross_hi"])]))
        else:
            orects.append(Polygon([(o["cross_lo"], o["along_min"]), (o["cross_lo"], o["along_max"]),
                                   (o["cross_hi"], o["along_max"]), (o["cross_hi"], o["along_min"])]))
    solid = unary_union(rects + orects)
    cav = footprint.difference(solid)
    faces = list(cav.geoms) if cav.geom_type == "MultiPolygon" else [cav]
    faces = [f for f in faces if f.area > min_room_units2]

    # per-face: match every ring edge to a non-NA wall; form-B support const
    rebuilt = []
    for f in faces:
        ring_pts = list(f.exterior.coords)
        support = []          # per directed edge: (axis, out_const, wall_id)
        ok = True
        reasons = []
        for a, b in zip(ring_pts, ring_pts[1:]):
            if a[0] == b[0]:
                axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
            else:
                axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
            # wall whose face matches this cavity edge (const, axis, overlap)
            cands = [w for w in by_lo.get((axis, const), []) + by_hi.get((axis, const), [])
                     if min(w["along_max"], hi) - max(w["along_min"], lo) > 0]
            if not cands:
                ok = False
                reasons.append(f"edge {axis}@{const}[{lo},{hi}] no wall")
                support.append(None)
                continue
            if len(cands) > 1:
                # split span across multiple collinear walls: take the one covering
                # the midpoint, probe-level approximation
                mid = (lo + hi) // 2
                cands = [w for w in cands
                         if w["along_min"] <= mid <= w["along_max"]] or cands
            w = cands[0]
            if w["id"] in na_walls:
                ok = False
                reasons.append(f"edge {axis}@{const} wall {w['id']} NA")
                support.append(None)
                continue
            if (w["face_hi"] - w["face_lo"]) % 2 != 0:
                ok = False
                reasons.append(f"odd thickness {w['id']}")
                support.append(None)
                continue
            mid_axis = w["face_lo"] + (w["face_hi"] - w["face_lo"]) // 2
            if is_exterior_side(w, w["face_lo"]):
                out = w["face_lo"]
            elif is_exterior_side(w, w["face_hi"]):
                out = w["face_hi"]
            else:
                out = mid_axis
            support.append((axis, out, w["id"]))
        rebuilt.append({"face": f, "support": support, "ok": ok, "reasons": reasons})

    # vertices from adjacent support-line intersections (+ 6a dedupe)
    for item in rebuilt:
        sup = item["support"]
        if not item["ok"]:
            item["verts"] = None
            continue
        verts = []
        n = len(sup)
        for i in range(n):
            a, b = sup[i - 1], sup[i]
            if a[0] == "y":      # a: const is an x coordinate
                vx, vy = a[1], b[1]
            else:
                vx, vy = b[1], a[1]
            verts.append((vx, vy))
        ded = []
        for v in verts:
            if not ded or v != ded[-1]:
                ded.append(v)
        if len(ded) > 1 and ded[0] == ded[-1]:
            ded.pop()
        item["verts"] = ded

    gt_zones = gt_floor[floor_id]["zones"]
    print(f"rebuilt faces: {len(rebuilt)} (NA: {sum(1 for r in rebuilt if not r['ok'])})")
    for item in rebuilt:
        if not item["ok"]:
            print("  NA zone:", item["reasons"][:3], "…")
            continue
        verts = item["verts"]
        poly = Polygon(verts)
        rep = poly.representative_point()
        matches = [z for z in gt_zones
                   if Polygon([(v[0] * UNITS, v[1] * UNITS)
                               for v in z["polygon"]["exterior"]["vertices"]]).contains(rep)]
        if not matches:
            print(f"  zone {poly.area/UNITS/UNITS:.2f} m2: no gt match (vertices {len(verts)})")
            continue
        z = matches[0]
        gv = [(round(v[0] * UNITS), round(v[1] * UNITS))
              for v in z["polygon"]["exterior"]["vertices"]]
        same_set = sorted(verts) == sorted(set(gv)) and sorted(map(tuple, verts)) == sorted(set(map(tuple, gv)))
        exact = sorted(verts) == sorted(set(map(tuple, gv)))
        if not exact:
            only_ours = set(map(tuple, verts)) - set(map(tuple, gv))
            only_gt = set(map(tuple, gv)) - set(map(tuple, verts))
            print(f"  {z['id']}: DIFF  ours-only={sorted(only_ours)[:6]} gt-only={sorted(only_gt)[:6]}")
        else:
            print(f"  {z['id']}: EXACT ({len(verts)} verts)")
