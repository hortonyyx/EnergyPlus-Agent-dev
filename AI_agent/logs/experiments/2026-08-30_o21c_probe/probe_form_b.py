"""Probe (dispatch ②-1c, pre-implementation recon): rebuild form-B zone rings
from the staging facts layer (as_signed) and reconcile them, edge by edge,
against today's signed gt.json zones.

Questions this probe answers BEFORE the compiler is written:
1. Does "footprint − (wall rectangles ∪ opening rectangles)" reproduce the
   S5 cavity set (14 zones on F1)?
2. Does the support-line intersection (6c) rebuild the exact form-B rings?
3. What is the FULL difference set vs gt.json zones -- is it only the 5
   unsigned-revision lines, or does the GTV3_ZONE partition-line drift
   (4 edges, 0.1–0.4 mm, 2026-08-28 measurement) show up as a THIRD kind?

Pure recon: reads staging facts + gt.json + request, prints a table.
No repo state is modified.
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

REPO = Path(__file__).resolve().parents[4]
STAGING = REPO / "case_tests/test_baseline/gt_staging/sm25-L_anchor/facts"
GT = REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json"
UNITS = 10000  # 0.1 mm units per metre

facts = json.loads((STAGING / "as_signed.json").read_text())
revisions = json.loads((STAGING / "revisions.json").read_text())
gt = json.loads(GT.read_text())

# handles named by any revision (today: all five are unsigned)
rev_handles: dict[str, list[str]] = {}
for rev in revisions["revisions"]:
    rev_handles.setdefault(rev["verdict"], []).append(rev["target"]["handle"])
print("revision handles by verdict:", rev_handles)

gt_floor = {f["id"]: f for f in gt["floors"]}

for view in facts["views"]:
    vid = view["view_id"]
    floor_id = view["floor_id"]
    print(f"\n=== {vid} (floor {floor_id}) ===")
    walls = view["walls"]
    openings = view["openings"]
    fp = view["footprint"]
    ext_ring = next(r["points"] for r in fp["rings"] if r["kind"] == "exterior")
    footprint = Polygon([(p[0], p[1]) for p in ext_ring])
    print("footprint rings:", [(r["kind"], len(r["points"])) for r in fp["rings"]],
          "area m2:", round(footprint.area / UNITS / UNITS, 3))

    # wall rectangles in INTEGER 0.1mm units
    rects = []
    for w in walls:
        if w["axis"] == "x":     # runs along x, faces are y consts
            rect = Polygon([(w["along_min"], w["face_lo"]), (w["along_max"], w["face_lo"]),
                            (w["along_max"], w["face_hi"]), (w["along_min"], w["face_hi"])])
        else:
            rect = Polygon([(w["face_lo"], w["along_min"]), (w["face_lo"], w["along_max"]),
                            (w["face_hi"], w["along_max"]), (w["face_hi"], w["along_min"])])
        rects.append(rect)
    # opening rectangles (door/window fills -- S4 polygonizes over these too)
    orects = []
    for o in openings:
        if o["axis"] == "x":
            rect = Polygon([(o["along_min"], o["cross_lo"]), (o["along_max"], o["cross_lo"]),
                            (o["along_max"], o["cross_hi"]), (o["along_min"], o["cross_hi"])])
        else:
            rect = Polygon([(o["cross_lo"], o["along_min"]), (o["cross_lo"], o["along_max"]),
                            (o["cross_hi"], o["along_max"]), (o["cross_hi"], o["along_min"])])
        orects.append(rect)
    solid = unary_union(rects + orects)
    cavities_geom = footprint.difference(solid)
    faces = list(cavities_geom.geoms) if cavities_geom.geom_type == "MultiPolygon" else [cavities_geom]
    faces = [f for f in faces if not f.is_empty]
    print("cavity faces:", len(faces),
          "areas m2:", sorted(round(f.area / UNITS / UNITS, 2) for f in faces))

    gt_zones = gt_floor[floor_id]["zones"]
    print("gt zones:", len(gt_zones))

    # zone reconciliation by representative point (in units)
    unmatched_gt = []
    for z in gt_zones:
        verts = z["polygon"]["exterior"]["vertices"]
        poly = Polygon([(v[0] * UNITS, v[1] * UNITS) for v in verts])
        rep = poly.representative_point()
        hit = [f for f in faces if f.contains(rep)]
        area_gt = poly.area / UNITS / UNITS
        if not hit:
            unmatched_gt.append((z["id"], area_gt))
            continue
        f = hit[0]
        area_f = f.area / UNITS / UNITS
        print(f"  gt {z['id']}: area {area_gt:.3f} vs cavity {area_f:.3f} "
              f"(diff {area_f - area_gt:+.4f} m2)")
    print("  gt zones with no cavity:", unmatched_gt)

    # which walls' outer face touches the footprint exterior ring?
    ext_lines = set()
    ring = ext_ring
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if a[0] == b[0]:
            ext_lines.add(("x", a[0], min(a[1], b[1]), max(a[1], b[1])))
        elif a[1] == b[1]:
            ext_lines.add(("y", a[1], min(a[0], b[0]), max(a[0], b[0])))
    n_ext = 0
    for w in walls:
        for face, side in ((w["face_lo"], "lo"), (w["face_hi"], "hi")):
            for lax, lc, llo, lhi in ext_lines:
                if lax == w["axis"] and lc == face:
                    lo, hi = w["along_min"], w["along_max"]
                    if min(hi, lhi) - max(lo, llo) > 0:
                        n_ext += 1
                        break
    print(f"  wall faces touching the exterior ring: {n_ext} "
          f"(of {2 * len(walls)} faces; exterior-wall count below counts walls once)")
    ext_walls = []
    for w in walls:
        touch = any(
            lax == w["axis"] and lc in (w["face_lo"], w["face_hi"])
            and min(w["along_max"], lhi) - max(w["along_min"], llo) > 0
            for lax, lc, llo, lhi in ext_lines)
        if touch:
            ext_walls.append(w["id"])
    print(f"  exterior walls: {len(ext_walls)} of {len(walls)}")
