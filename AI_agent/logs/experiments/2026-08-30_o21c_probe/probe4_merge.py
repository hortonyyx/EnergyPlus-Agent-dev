"""Probe 4 (②-1c recon): merged-edge model + full printout of every zone.

Fixes vs probe 3, each from a measured failure:
a) cavity ring edges are MERGED per physical-wall group first (a group's runs
   plus its opening stretches form ONE support segment); vertices are computed
   only at junctions between merged edges -- kills the (c,c) fake vertices
   where two collinear segments met.
b) a group's exterior test uses the union coverage of its runs AND the
   openings that bridge them (a window wall's outer face may only ever be
   touched by opening stretches).
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

for view in facts["views"]:
    vid, floor_id = view["view_id"], view["floor_id"]
    print(f"\n================ {vid} ================")
    walls, openings = view["walls"], view["openings"]

    groups: dict[tuple, dict] = {}
    for w in walls:
        key = (w["axis"], w["face_lo"], w["face_hi"])
        groups.setdefault(key, {"runs": [], "handles": set()})
        groups[key]["runs"].append(w)
        groups[key]["handles"] |= set(w["face_line_ids_lo"]) | set(w["face_line_ids_hi"])
    by_id = {w["id"]: w for w in walls}
    for o in openings:
        for wid in o["carrier_wall_ids"]:
            w = by_id.get(wid)
            if w is None:
                continue
            key = (w["axis"], w["face_lo"], w["face_hi"])
            groups.setdefault(key, {"runs": [], "handles": set()})
            groups[key].setdefault("openings", []).append(o)

    na_groups = {k for k, g in groups.items() if g["handles"] & unsigned}

    ext_ring = next(r["points"] for r in view["footprint"]["rings"]
                    if r["kind"] == "exterior")
    ext_lines = []
    for a, b in zip(ext_ring, ext_ring[1:] + ext_ring[:1]):
        if a[0] == b[0]:      # vertical edge RUNS ALONG y -- as_measured convention
            ext_lines.append(("y", a[0], min(a[1], b[1]), max(a[1], b[1])))
        elif a[1] == b[1]:    # horizontal edge runs along x
            ext_lines.append(("x", a[1], min(a[0], b[0]), max(a[0], b[0])))

    face_by_id = {f["id"]: f for f in view["face_lines"]}

    def group_coverage(key):
        cov = [(w["along_min"], w["along_max"]) for w in groups[key]["runs"]]
        cov += [(o["along_min"], o["along_max"]) for o in groups[key].get("openings", [])]
        return cov

    def _all_handles(g, side):
        out = []
        for w in g["runs"]:
            out.extend(w[f"face_line_ids_{side}"])
        return out

    def group_support(key):
        axis, lo, hi = key
        g = groups[key]
        loh = _all_handles(g, "lo")
        hih = _all_handles(g, "hi")
        lo_avg = round(sum(face_by_id[h]["const"] for h in loh) / len(loh))
        hi_avg = round(sum(face_by_id[h]["const"] for h in hih) / len(hih))
        if (lo_avg + hi_avg) % 2:
            return None, "half_unit_midline"
        mid = (lo_avg + hi_avg) // 2
        cov = group_coverage(key)
        for face in (lo_avg, hi_avg):
            for lax, lc, llo, lhi in ext_lines:
                if lax != axis or lc != face:
                    continue
                if any(min(c_hi, lhi) - max(c_lo, llo) > 0 for c_lo, c_hi in cov):
                    return (face, "exterior", ("ring", lc)), None
        return (mid, "interior", None), None

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

    # build the per-face merged support list
    results = []
    for f in faces:
        ring_pts = list(f.exterior.coords)
        raw = []
        for a, b in zip(ring_pts, ring_pts[1:]):
            if a[0] == b[0]:
                axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
            else:
                axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
            cands = [k for k in groups if k[0] == axis and const in (k[1], k[2])
                     and any(min(c1, hi) - max(c0, lo) > 0 for c0, c1 in group_coverage(k))]
            if not cands:
                raw.append(None)
                continue
            key = cands[0]
            raw.append((key, group_support(key)))
        # merge collinear consecutive segments belonging to the same group,
        # INCLUDING the ring wrap-around (the ring may start mid-wall)
        seq = raw + [raw[0] if raw else None]
        # rotate so that a None or a group-change sits at the boundary
        start = 0
        for i in range(len(raw)):
            prev = raw[i - 1]
            if prev is None or raw[i] is None or prev[0] != raw[i][0]:
                start = i
                break
        rot = raw[start:] + raw[:start]
        merged = []
        for seg in rot:
            if seg is None:
                merged.append(None)
                continue
            key, sup = seg
            if merged and merged[-1] is not None and merged[-1][0] == key:
                continue
            merged.append(seg)
        ok = all(m is not None and m[1][0] is not None for m in merged)
        why = [f"{m[0]}:{m[1][1]}" for m in merged if m is not None and m[1][0] is None]
        why += ["no_group" for m in merged if m is None]
        verts = None
        if ok:
            sup = [m[1][0] for m in merged]
            axes = [m[0][0] for m in merged]
            verts = []
            for i in range(len(sup)):
                pa, pb = sup[i - 1], sup[i]
                if axes[i - 1] == "y":      # const is an x coordinate
                    verts.append((pa[0], pb[0]))
                else:
                    verts.append((pb[0], pa[0]))
            ded = []
            for v in verts:
                if not ded or v != ded[-1]:
                    ded.append(v)
            if len(ded) > 1 and ded[0] == ded[-1]:
                ded.pop()
            verts = ded
        results.append({"face": f, "merged": merged, "verts": verts,
                        "ok": ok, "why": why})

    for item in results:
        if not item["ok"]:
            print("  NA:", sorted(set(item["why"]))[:4])
            continue
        verts = item["verts"]
        poly = Polygon(verts)
        rep = poly.representative_point()
        gt_zones = gt_floor[floor_id]["zones"]
        # match: gt zone whose polygon contains the cavity's representative point
        frep = item["face"].representative_point()
        matches = [z for z in gt_zones
                   if Polygon([(v[0] * UNITS, v[1] * UNITS)
                               for v in z["polygon"]["exterior"]["vertices"]]).contains(frep)]
        if not matches:
            print(f"  rebuilt {poly.area/1e8:.2f} m2 (cavity {item['face'].area/1e8:.2f}): no gt zone")
            continue
        z = matches[0]
        gv = sorted({(round(v[0] * UNITS), round(v[1] * UNITS))
                     for v in z["polygon"]["exterior"]["vertices"]})
        ours = sorted(set(verts))
        tag = "EXACT" if ours == gv else "DIFF"
        print(f"  {z['id']}: {tag} ({len(ours)} ours / {len(gv)} gt)")
        if tag == "DIFF":
            print(f"     ours-only: {sorted(set(ours) - set(gv))}")
            print(f"     gt-only : {sorted(set(gv) - set(ours))}")
            print(f"     ours seq: {verts}")
            print(f"     gt  seq : {[(round(v[0]*UNITS), round(v[1]*UNITS)) for v in z['polygon']['exterior']['vertices']]}")
