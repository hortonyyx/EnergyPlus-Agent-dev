"""F-156 v3 · probe A: what does the support-line cycle actually look like?

Answers, for every above-threshold sm25 cavity:
  * how many raw ring segments, how many merged SUPPORT LINES (axis+const),
  * how each line's spans split into faced / endcap / ambiguous,
  * whether a single support line ever mixes faced and endcap spans,
  * whether adjacent support lines are always perpendicular,
  * whether the production merge key (group+condition) ever splits one line
    into more than one edge record.
Read-only; consumes src.agent.judge.as_measured helpers, writes nothing.
"""
import json
import sys
from pathlib import Path

REPO = Path("/workspaces/EnergyPlus-Agent-dev")
sys.path.insert(0, str(REPO))
from src.agent.judge import as_measured as am  # noqa: E402

SRC = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
REQ = SRC / "request_as_measured.json"
MIN = float(json.loads(REQ.read_text())["min_room_area_m2"])
U = am.UNITS_PER_METRE


def endcap_candidates(groups, axis, const, lo, hi):
    out = []
    for g in groups.values():
        if g.axis == axis:
            continue
        for w in g.runs:
            if const in (w.along_min, w.along_max) and min(hi, w.face_hi) - max(lo, w.face_lo) > 0:
                out.append(g)
                break
    return sorted(out, key=lambda g: (g.key, g.wall_ids))


def parallel_faces_global(groups, axis, const):
    return [g.key for g in groups.values()
            if g.axis == axis and const in (g.face_lo, g.face_hi)]


def parallel_faces_overlapping(groups, axis, const, lo, hi):
    out = []
    for g in groups.values():
        if g.axis != axis or const not in (g.face_lo, g.face_hi):
            continue
        if any(min(hi, e) - max(lo, s) > 0 for s, e in g.coverage()):
            out.append(g.key)
    return out


doc = am.build_as_measured(SRC / "sm25-L_t3_as_received.dxf", REQ)
for view in doc.views:
    groups = am._boundary_wall_groups(view)
    footprint, ring_records = am._boundary_footprint(view)
    wall_region = am._boundary_wall_region(view)
    geometry = footprint.difference(wall_region)
    thr = MIN * U * U
    cavities = [p for p in getattr(geometry, "geoms", [geometry])
                if p.geom_type == "Polygon" and not p.is_empty and p.area > thr]
    cavities.sort(key=lambda c: tuple(round(v, 6) for v in c.bounds))
    for cav in cavities:
        cid = am._boundary_cavity_id(view.view_id, cav)
        ring = [(int(round(x)), int(round(y))) for x, y in list(cav.exterior.coords)[:-1]]
        rp = cav.representative_point()
        segs = []
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a[0] == b[0]:
                axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
                side = -1 if rp.x < const else 1
            else:
                axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
                side = -1 if rp.y < const else 1
            ow = am._boundary_owners(groups, axis, const, lo, hi)
            ec = endcap_candidates(groups, axis, const, lo, hi)
            if len(ow) == 1:
                kind, key = "faced", ow[0].key
            elif not ow and len(ec) == 1:
                kind, key = "endcap", ec[0].key
            else:
                kind, key = f"AMBIG(ow={len(ow)},ec={len(ec)})", None
            segs.append(dict(axis=axis, const=const, lo=lo, hi=hi, side=side,
                             kind=kind, key=key, p1=a, p2=b))
        # rotate so index 0 starts a new (axis, const) line
        start = 0
        for i, s in enumerate(segs):
            if (segs[i - 1]["axis"], segs[i - 1]["const"]) != (s["axis"], s["const"]):
                start = i
                break
        rot = segs[start:] + segs[:start]
        lines = []
        for s in rot:
            if lines and (lines[-1]["axis"], lines[-1]["const"]) == (s["axis"], s["const"]):
                lines[-1]["segs"].append(s)
            else:
                lines.append(dict(axis=s["axis"], const=s["const"], segs=[s]))
        mixed = [(ln["axis"], ln["const"], sorted({q["kind"] for q in ln["segs"]}))
                 for ln in lines if len({q["kind"] for q in ln["segs"]}) > 1]
        # production merge key inside one line: (kind, key, side)
        multi_record = []
        for ln in lines:
            runs = []
            for s in ln["segs"]:
                sig = (s["kind"], s["key"], s["side"])
                if not runs or runs[-1] != sig:
                    runs.append(sig)
            if len(runs) > 1:
                multi_record.append((ln["axis"], ln["const"], len(runs)))
        par = [(lines[i - 1]["axis"], lines[i]["axis"])
               for i in range(len(lines)) if lines[i - 1]["axis"] == lines[i]["axis"]]
        kinds = [max({q["kind"] for q in ln["segs"]}, key=lambda k: k) for ln in lines]
        n_faced = sum(1 for ln in lines if all(q["kind"] == "faced" for q in ln["segs"]))
        n_end = sum(1 for ln in lines if all(q["kind"] == "endcap" for q in ln["segs"]))
        n_amb = len(lines) - n_faced - n_end - len(mixed)
        bad_g = [(ln["axis"], ln["const"]) for ln in lines
                 if all(q["kind"] == "endcap" for q in ln["segs"])
                 and not parallel_faces_global(groups, ln["axis"], ln["const"])]
        bad_o = [(ln["axis"], ln["const"]) for ln in lines
                 if all(q["kind"] == "endcap" for q in ln["segs"])
                 and not parallel_faces_overlapping(
                     groups, ln["axis"], ln["const"],
                     min(q["lo"] for q in ln["segs"]), max(q["hi"] for q in ln["segs"]))]
        print(f"{view.view_id} {cid} area={cav.area/U/U:8.3f} segs={len(segs)} "
              f"lines={len(lines)} faced_lines={n_faced} endcap_lines={n_end} "
              f"other={n_amb} mixed_lines={len(mixed)} multi_record_lines={len(multi_record)} "
              f"adjacent_parallel={len(par)} "
              f"BAD_ENDCAP_global={bad_g} BAD_ENDCAP_overlap={bad_o}")
        if mixed:
            print(f"    MIXED {mixed}")
        if multi_record:
            print(f"    MULTI {multi_record}")
        amb = [(s["axis"], s["const"], s["lo"], s["hi"], s["kind"])
               for s in segs if s["kind"].startswith("AMBIG")]
        if amb:
            print(f"    AMBIG {amb}")
