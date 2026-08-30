"""Probe 5 (②-1c recon): wall-region exterior-ring basis test.

MEASURED on probe 4: "face lies on the footprint ring" has FALSE POSITIVES on
the as-received drawing -- the footprint ring dips along INTERIOR wall faces
wherever polygonize could not close a region (the z0 hall area), so interior
walls (z6 south wall 57600/60000, F2 z4 north wall 140000/142400) were called
exterior and emitted their face instead of the midline.

New basis test, computed ENTIRELY from facts-layer geometry:
  wall_region = unary_union(wall rectangles + opening fill rectangles)
  a wall face is EXTERIOR iff its (axis, const, span) is collinear-and-
  overlapping with the EXTERIOR ring of wall_region -- i.e. the face is on
  the boundary of the solid wall mass facing open space, not facing another
  cavity.  Faces bounding a hole (interior ring) are interior walls (a hole
  here is a room, not a courtyard -- stated limitation for no-holes profile).
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
min_room_units2 = request["min_room_area_m2"] * UNITS * UNITS
gt_floor = {f["id"]: f for f in gt["floors"]}
unsigned = {r["target"]["handle"] for r in revisions["revisions"]
            if r["verdict"] == "unsigned"}

summary = {"F1": [], "F2": []}
for view in facts["views"]:
    vid, floor_id = view["view_id"], view["floor_id"]
    print(f"\n================ {vid} ================")
    walls, openings = view["walls"], view["openings"]
    face_by_id = {f["id"]: f for f in view["face_lines"]}

    groups: dict[tuple, dict] = {}
    for w in walls:
        key = (w["axis"], w["face_lo"], w["face_hi"])
        groups.setdefault(key, {"runs": []})
        groups[key]["runs"].append(w)
    by_id = {w["id"]: w for w in walls}
    for o in openings:
        for wid in o["carrier_wall_ids"]:
            w = by_id.get(wid)
            if w is not None:
                groups[(w["axis"], w["face_lo"], w["face_hi"])].setdefault(
                    "openings", []).append(o)
    na_groups = set()
    for key, g in groups.items():
        hs = set()
        for w in g["runs"]:
            hs |= set(w["face_line_ids_lo"]) | set(w["face_line_ids_hi"])
        g["handles"] = hs
        if hs & unsigned:
            na_groups.add(key)

    rects = []
    for w in walls:
        if w["axis"] == "x":
            rects.append(Polygon([(w["along_min"], w["face_lo"]), (w["along_max"], w["face_lo"]),
                                  (w["along_max"], w["face_hi"]), (w["along_min"], w["face_hi"])]))
        else:
            rects.append(Polygon([(w["face_lo"], w["along_min"]), (w["face_lo"], w["along_max"]),
                                  (w["face_hi"], w["along_max"]), (w["face_hi"], w["along_min"])]))
    for o in openings:
        if o["axis"] == "x":
            rects.append(Polygon([(o["along_min"], o["cross_lo"]), (o["along_max"], o["cross_lo"]),
                                  (o["along_max"], o["cross_hi"]), (o["along_min"], o["cross_hi"])]))
        else:
            rects.append(Polygon([(o["cross_lo"], o["along_min"]), (o["cross_lo"], o["along_max"]),
                                   (o["cross_hi"], o["along_max"]), (o["cross_hi"], o["along_min"])]))
    wall_region = unary_union(rects)
    print(f"wall_region: {wall_region.geom_type}")

    ext_ring = next(r["points"] for r in view["footprint"]["rings"]
                    if r["kind"] == "exterior")
    footprint = Polygon([(p[0], p[1]) for p in ext_ring])

    from shapely.geometry import Point

    def support(key):
        axis, lo, hi = key
        g = groups[key]
        loh = sorted({face_by_id[h]["const"] for w in g["runs"] for h in w["face_line_ids_lo"]})
        hih = sorted({face_by_id[h]["const"] for w in g["runs"] for h in w["face_line_ids_hi"]})
        lo_avg, hi_avg = round(sum(loh) / len(loh)), round(sum(hih) / len(hih))
        if (lo_avg + hi_avg) % 2:
            return None, "half_unit_midline"
        mid = (lo_avg + hi_avg) // 2
        return {"lo": lo_avg, "hi": hi_avg, "mid": mid}, None

    def edge_support(key, sup, const, lo, hi, cavity_side):
        """S7 basis test recomputed from facts: exit through the wall band.
        cavity_side: -1 cavity lies at smaller const than the edge, +1 larger.
        The face the cavity touches is named by its RAW face-line mean, not the
        D3 group coordinate (160596 vs 160600 -- the 0.4 mm the partition line
        actually shows in gt)."""
        axis = key[0]
        t = sup["hi"] - sup["lo"]
        outward = -cavity_side
        face = sup["lo"] if cavity_side < 0 else sup["hi"]
        mid_along = (lo + hi) // 2
        exit_const = face + outward * (t + 1)
        q = Point(exit_const, mid_along) if axis == "y" else Point(mid_along, exit_const)
        exterior = not footprint.contains(q) and not wall_region.contains(q)
        off = t if exterior else t // 2
        return face + outward * off, ("exterior" if exterior else "interior")

    def coverage(key):
        g = groups[key]
        cov = [(w["along_min"], w["along_max"]) for w in g["runs"]]
        cov += [(o["along_min"], o["along_max"]) for o in g.get("openings", [])]
        return cov

    cav = footprint.difference(wall_region)
    faces = list(cav.geoms) if cav.geom_type == "MultiPolygon" else [cav]
    faces = [f for f in faces if f.area > min_room_units2]
    expected = next(pv["zone_intent"]["expected_count"] for pv in request["plan_views"]
                    if pv["id"] == vid)
    print(f"cavities {len(faces)} vs expected {expected}")

    for f in faces:
        ring_pts = list(f.exterior.coords)
        raw = []
        ok, why = True, []
        for a, b in zip(ring_pts, ring_pts[1:]):
            if a[0] == b[0]:
                axis, const, lo, hi = "y", int(a[0]), int(min(a[1], b[1])), int(max(a[1], b[1]))
            else:
                axis, const, lo, hi = "x", int(a[1]), int(min(a[0], b[0])), int(max(a[0], b[0]))
            cands = [k for k in groups if k[0] == axis and const in (k[1], k[2])
                     and any(min(c1, hi) - max(c0, lo) > 0 for c0, c1 in coverage(k))]
            if not cands:
                cands = [k for k in groups if k[0] == axis and any(
                    const in (o["cross_lo"], o["cross_hi"])
                    and min(o["along_max"], hi) - max(o["along_min"], lo) > 0
                    for o in groups[k].get("openings", []))]
            if not cands:
                ok = False
                why.append(f"no_group:{axis}@{const}[{lo},{hi}]")
                raw.append(None)
                continue
            key = cands[0]
            if key in na_groups:
                ok = False
                why.append(f"na_group:{axis}@{const}")
                raw.append(None)
                continue
            sup, err = support(key)
            if sup is None:
                ok = False
                why.append(f"{err}:{key}")
                raw.append(None)
                continue
            rep = f.representative_point()
            if axis == "y":
                cavity_side = -1 if rep.x < const else 1
            else:
                cavity_side = -1 if rep.y < const else 1
            out_const, basis = edge_support(key, sup, const, lo, hi, cavity_side)
            raw.append((key, (out_const, basis)))
        if not ok:
            print("  NA face:", sorted(set(why))[:3], " area", round(f.area / 1e8, 2))
            continue
        start_i = 0
        for i in range(len(raw)):
            prev = raw[i - 1]
            if prev is None or raw[i] is None or prev[0] != raw[i][0]:
                start_i = i
                break
        rot = raw[start_i:] + raw[:start_i]
        merged = []
        for seg in rot:
            if merged and merged[-1][0] == seg[0]:
                continue
            merged.append(seg)
        sup_c = [m[1][0] for m in merged]
        axes = [m[0][0] for m in merged]
        verts = []
        for i in range(len(sup_c)):
            pa, pb = sup_c[i - 1], sup_c[i]
            verts.append((pa, pb) if axes[i - 1] == "y" else (pb, pa))
        ded = []
        for v in verts:
            if not ded or v != ded[-1]:
                ded.append(v)
        if len(ded) > 1 and ded[0] == ded[-1]:
            ded.pop()
        poly = Polygon(ded)
        frep = f.representative_point()
        gt_zones = gt_floor[floor_id]["zones"]
        matches = [z for z in gt_zones
                   if Polygon([(v[0] * UNITS, v[1] * UNITS)
                               for v in z["polygon"]["exterior"]["vertices"]]).contains(frep)]
        if not matches:
            print(f"  rebuilt {poly.area/1e8:.2f} m2, {len(ded)} verts: NO GT ZONE for cavity rep")
            summary[floor_id].append(("no_gt", round(f.area / 1e8, 2)))
            continue
        z = matches[0]
        gv = sorted({(round(v[0] * UNITS), round(v[1] * UNITS))
                     for v in z["polygon"]["exterior"]["vertices"]})
        tag = "EXACT" if sorted(set(ded)) == gv else "DIFF"
        summary[floor_id].append((z["id"], tag))
        if tag == "DIFF":
            print(f"  {z['id']}: DIFF")
            print(f"     ours: {ded}")
            print(f"     gt  : {[(round(v[0]*UNITS), round(v[1]*UNITS)) for v in z['polygon']['exterior']['vertices']]}")
        else:
            print(f"  {z['id']}: EXACT ({len(ded)} verts)")

print()
for fl, rows in summary.items():
    n_exact = sum(1 for _, t in rows if t == "EXACT")
    print(f"{fl}: {n_exact} EXACT, "
          f"{sum(1 for _, t in rows if t == 'DIFF')} DIFF, "
          f"{sum(1 for r in rows if r[1] not in ('EXACT','DIFF'))} NA/no-gt  -> {rows}")
