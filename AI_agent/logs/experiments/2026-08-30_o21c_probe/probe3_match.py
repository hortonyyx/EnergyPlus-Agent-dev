"""Probe 3 (②-1c recon): physical-wall grouping + full edge reconciliation.

Model corrections vs probe 2, each learned from measured data:
- A physical wall = one (axis, face_lo, face_hi) pair covering several wall
  RUNS (split by openings -- D4 refuses to merge across them) joined by the
  openings whose carrier_wall_ids name those runs.
- A cavity edge may run along a wall run OR across an opening stretch of the
  same physical wall (its cross edges sit exactly on the wall faces).
- The 28.68 m2 merged face (z4+z5) is the 13AF consequence: its dividing wall
  never got a face pair. Expected count 14 != 13 -> those zones go NA loudly.
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

intent = {}
for pv in request["plan_views"]:
    if pv["id"] in {v["view_id"] for v in facts["views"]}:
        for e in pv["zone_intent"]["entries"]:
            intent[(pv["id"], e["zone_id"])] = e["name"]

for view in facts["views"]:
    vid, floor_id = view["view_id"], view["floor_id"]
    print(f"\n================ {vid} ================")
    walls = view["walls"]
    openings = view["openings"]

    # physical wall groups: key (axis, face_lo, face_hi) -> run list
    groups: dict[tuple, list[dict]] = {}
    for w in walls:
        groups.setdefault((w["axis"], w["face_lo"], w["face_hi"]), []).append(w)
    # NA groups: any member run names an unsigned handle
    na_groups = set()
    for key, runs in groups.items():
        for w in runs:
            if (set(w["face_line_ids_lo"]) | set(w["face_line_ids_hi"])) & unsigned:
                na_groups.add(key)

    ext_ring = next(r["points"] for r in view["footprint"]["rings"]
                    if r["kind"] == "exterior")
    ext_lines = []
    for a, b in zip(ext_ring, ext_ring[1:] + ext_ring[:1]):
        if a[0] == b[0]:
            ext_lines.append(("x", a[0], min(a[1], b[1]), max(a[1], b[1])))
        elif a[1] == b[1]:
            ext_lines.append(("y", a[1], min(a[0], b[0]), max(a[0], b[0])))

    def group_support(key):
        axis, lo, hi = key
        if (hi - lo) % 2:
            return None, "odd_thickness"
        mid = lo + (hi - lo) // 2
        runs = groups[key]
        for face in (lo, hi):
            for lax, lc, llo, lhi in ext_lines:
                if lax != axis or lc != face:
                    continue
                if any(min(w["along_max"], lhi) - max(w["along_min"], llo) > 0
                       for w in runs):
                    return (face, "exterior"), None     # form-B: outer skin
        return (mid, "interior"), None

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
    footprint = Polygon([(p[0], p[1]) for p in ext_ring])
    cav = footprint.difference(unary_union(rects))
    faces = list(cav.geoms) if cav.geom_type == "MultiPolygon" else [cav]
    faces = [f for f in faces if f.area > min_room_units2]

    expected = next(pv["zone_intent"]["expected_count"] for pv in request["plan_views"]
                    if pv["id"] == vid)
    print(f"cavities {len(faces)} vs expected {expected}")

    rebuilt = []
    for f in faces:
        ring_pts = list(f.exterior.coords)
        sup, ok, why = [], True, []
        for a, b in zip(ring_pts, ring_pts[1:]):
            if a[0] == b[0]:
                axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
            else:
                axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
            cands = [k for k in groups if k[0] == axis and const in (k[1], k[2])
                     and any(min(w["along_max"], hi) - max(w["along_min"], lo) > 0
                             for w in groups[k])]
            if not cands:
                # opening stretch? any group whose runs sit around this span
                cands = [k for k in groups if k[0] == axis and const in (k[1], k[2])
                         and any(min(o["along_max"], hi) - max(o["along_min"], lo) > 0
                                 and const in (o["cross_lo"], o["cross_hi"])
                                 for o in openings
                                 if any(wid in {x["id"] for x in groups[k]}
                                        for wid in o["carrier_wall_ids"])
                                 and o["axis"] == axis)]
            if not cands:
                ok = False
                why.append(f"{axis}@{int(const)}[{int(lo)},{int(hi)}] no group")
                sup.append(None)
                continue
            key = cands[0]
            if key in na_groups:
                ok = False
                why.append(f"{axis}@{int(const)} group NA ({key[1]}..{key[2]})")
                sup.append(None)
                continue
            support, err = group_support(key)
            if support is None:
                ok = False
                why.append(f"group {key} {err}")
                sup.append(None)
                continue
            sup.append((axis, support[0], key, support[1]))
        rebuilt.append({"face": f, "sup": sup, "ok": ok, "why": why})

    for item in rebuilt:
        if not item["ok"]:
            item["verts"] = None
            continue
        sup = item["sup"]
        verts = []
        for i in range(len(sup)):
            a, b = sup[i - 1], sup[i]
            verts.append((a[1], b[1]) if a[0] == "y" else (b[1], a[1]))
        ded = []
        for v in verts:
            if not ded or v != ded[-1]:
                ded.append(v)
        if len(ded) > 1 and ded[0] == ded[-1]:
            ded.pop()
        item["verts"] = ded

    gt_zones = gt_floor[floor_id]["zones"]
    for item in rebuilt:
        if not item["ok"]:
            print("  NA:", item["why"][:2], "…")
            continue
        verts = item["verts"]
        poly = Polygon(verts) if len(verts) >= 3 else None
        if poly is None:
            print("  degenerate rebuilt ring")
            continue
        rep = poly.representative_point()
        matches = [z for z in gt_zones
                   if Polygon([(v[0] * UNITS, v[1] * UNITS)
                               for v in z["polygon"]["exterior"]["vertices"]]).contains(rep)]
        if not matches:
            print(f"  rebuilt {poly.area/1e8:.2f} m2: no gt zone contains its rep point")
            continue
        z = matches[0]
        gv = sorted({(round(v[0] * UNITS), round(v[1] * UNITS))
                     for v in z["polygon"]["exterior"]["vertices"]})
        ours = sorted(set(verts))
        if ours == gv:
            print(f"  {z['id']} ({intent.get((vid, z['id']), '?')}): EXACT {len(ours)} verts")
        else:
            print(f"  {z['id']} ({intent.get((vid, z['id']), '?')}): DIFF")
            print(f"     ours-only: {sorted(set(ours) - set(gv))[:8]}")
            print(f"     gt-only : {sorted(set(gv) - set(ours))[:8]}")
