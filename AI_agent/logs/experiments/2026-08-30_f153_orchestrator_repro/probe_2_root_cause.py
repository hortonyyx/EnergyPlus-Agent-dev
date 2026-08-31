"""F-153 根因定位（主控自量）：把两个失败形态各自拆到 file:line 级别。"""
import json
from pathlib import Path
from shapely.geometry import Point

from src.agent.judge.as_measured import (
    AsMeasuredViewV1, UNITS_PER_METRE,
    _boundary_footprint, _boundary_wall_region, _boundary_wall_groups,
    _boundary_owners, _boundary_cavity_id, _BoundarySpan,
    _classify_boundary_fact,
)

FACTS = Path("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json")
THR = 5.0 * UNITS_PER_METRE ** 2
M = UNITS_PER_METRE


def m(v):
    return round(v / M, 4)


doc = json.loads(FACTS.read_text(encoding="utf-8"))
for raw in doc["views"]:
    view = AsMeasuredViewV1.model_validate(raw)
    footprint, ring_records = _boundary_footprint(view)
    wall_region = _boundary_wall_region(view)
    geom = footprint.difference(wall_region)
    cavities = [p for p in getattr(geom, "geoms", [geom])
                if p.geom_type == "Polygon" and not p.is_empty and p.area > THR]
    cavities.sort(key=lambda c: tuple(round(v, 6) for v in c.bounds))
    cav_ids = {id(c): _boundary_cavity_id(view.view_id, c) for c in cavities}
    groups = _boundary_wall_groups(view)
    face_by_id = {f.id: f for f in view.face_lines}

    for cav in cavities:
        ring = [(int(round(x)), int(round(y)))
                for x, y in list(cav.exterior.coords)[:-1]]
        rep = cav.representative_point()
        bad = None
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a[0] == b[0] and a[1] != b[1]:
                axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
                side = -1 if rep.x < const else 1
            elif a[1] == b[1] and a[0] != b[0]:
                axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
                side = -1 if rep.y < const else 1
            else:
                bad = ("non_axis", a, b, None); break
            owners = _boundary_owners(groups, axis, const, lo, hi)
            if len(owners) != 1:
                bad = ("owners=%d" % len(owners), (axis, const, lo, hi), side, None)
                break
            g = owners[0]
            near = "lo" if side < 0 else "hi"
            far = "hi" if near == "lo" else "lo"
            rn = round(sum(face_by_id[h].const for h in g.handles(near)) / len(g.handles(near)))
            rf = round(sum(face_by_id[h].const for h in g.handles(far)) / len(g.handles(far)))
            cand = _BoundarySpan(axis=axis, cavity_const=const, lo=lo, hi=hi,
                                 side=side, p1=a, p2=b, group=g,
                                 boundary_condition="unknown")
            cond, ev, logical = _classify_boundary_fact(
                cand, rn, rf, footprint, ring_records, wall_region, cavities, cav_ids)
            if not logical:
                bad = ("illogical", (axis, const, lo, hi), side,
                       dict(group_key=g.key, raw_near=rn, raw_far=rf,
                            exit_point=ev.exit_point,
                            wall_covers=wall_region.covers(Point(ev.exit_point)),
                            fp_covers=footprint.covers(Point(ev.exit_point)),
                            in_cavity=[cav_ids[id(c)] for c in cavities
                                       if c.covers(Point(ev.exit_point))]))
                break
        if bad is None:
            continue
        print(f"\n### {view.view_id} {cav_ids[id(cav)]} area={m(cav.area)/1:.6g}"
              f" -> {cav.area/M**2:.2f} m2  bounds(m)={[m(v) for v in cav.bounds]}")
        print(f"    failure = {bad[0]}  span={bad[1]}  side={bad[2]}")
        if bad[3]:
            for k, v in bad[3].items():
                print(f"      {k} = {v}")
        # 附近的墙面 const（找 off-by-N）
        axis, const, lo, hi = bad[1] if bad[0] != "non_axis" else (None,)*4
        if axis:
            near_consts = sorted({c for (ax, fl, fh) in groups
                                  for c in (fl, fh) if ax == axis
                                  and abs(c - const) <= 30})
            print(f"      同轴 |Δ|≤30 单位(3mm) 的墙面 const = {near_consts}"
                  f"  (cavity const = {const})")
            # 该 const 上有没有覆盖重叠的组，只是 const 差一点
            cands = [(g.key, g.coverage()) for g in groups.values()
                     if g.axis == axis and min(abs(g.face_lo-const), abs(g.face_hi-const)) <= 30]
            for key, cov in cands:
                ov = [(s, e) for s, e in cov if min(hi, e) - max(lo, s) > 0]
                print(f"      near-miss group {key} overlap={ov}")
