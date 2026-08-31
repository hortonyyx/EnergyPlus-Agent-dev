"""F-153 独立复现探针（主控 orchestrator 自量，⛔ 不转引复核方数字）。

问题：生产阈值 5.0 下存在的 cavity 里，有哪些被 derive_boundary_edges 静默丢掉
（ring_is_logical=False 或 merged<3），它们各自面积多大、边界贴墙率多少。
"""
import json, sys
from pathlib import Path

from shapely.geometry import Point

from src.agent.judge.as_measured import (
    AsMeasuredViewV1, UNITS_PER_METRE,
    _boundary_footprint, _boundary_wall_region, _boundary_wall_groups,
    _boundary_owners, _boundary_cavity_id, _BoundarySpan,
    _classify_boundary_fact, _merge_boundary_spans,
)

FACTS = Path("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json")
MIN_ROOM_AREA_M2 = 5.0          # 生产阈值，来自 request_as_measured.json
ADJ_TOL_M = 0.04                # 复核方用的 4 cm
N_SAMPLES = 400


def classify_cavity(view, cavity, footprint, ring_records, wall_region,
                    cavities, cavity_ids, groups, face_by_id):
    """复刻 derive_boundary_edges 的 per-cavity 判定，返回 (状态, 细节)。"""
    ring = [(int(round(x)), int(round(y)))
            for x, y in list(cavity.exterior.coords)[:-1]]
    rep = cavity.representative_point()
    spans = []
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if a[0] == b[0] and a[1] != b[1]:
            axis, const, lo, hi = "y", a[0], min(a[1], b[1]), max(a[1], b[1])
            side = -1 if rep.x < const else 1
        elif a[1] == b[1] and a[0] != b[0]:
            axis, const, lo, hi = "x", a[1], min(a[0], b[0]), max(a[0], b[0])
            side = -1 if rep.y < const else 1
        else:
            return "non_axis_segment", {"seg": (a, b)}
        owners = _boundary_owners(groups, axis, const, lo, hi)
        if len(owners) != 1:
            return "owner_count_%d" % len(owners), {"axis": axis, "const": const,
                                                    "lo": lo, "hi": hi}
        group = owners[0]
        near = "lo" if side < 0 else "hi"
        far = "hi" if near == "lo" else "lo"
        raw_near = round(sum(face_by_id[h].const for h in group.handles(near))
                         / len(group.handles(near)))
        raw_far = round(sum(face_by_id[h].const for h in group.handles(far))
                        / len(group.handles(far)))
        cand = _BoundarySpan(axis=axis, cavity_const=const, lo=lo, hi=hi,
                             side=side, p1=a, p2=b, group=group,
                             boundary_condition="unknown")
        cond, _ev, logical = _classify_boundary_fact(
            cand, raw_near, raw_far, footprint, ring_records, wall_region,
            cavities, cavity_ids)
        if not logical:
            return "classify_illogical", {"axis": axis, "const": const,
                                          "lo": lo, "hi": hi}
        cand.boundary_condition = cond
        spans.append(cand)
    merged = _merge_boundary_spans(spans)
    if len(merged) < 3:
        return "merged_lt_3", {"merged": len(merged)}
    return "ok", {"merged": len(merged)}


def adjacency(cavity, wall_region, n=N_SAMPLES, tol_m=ADJ_TOL_M):
    ring = cavity.exterior
    tol_u = tol_m * UNITS_PER_METRE
    hits = 0
    dists = []
    for i in range(n):
        pt = ring.interpolate(ring.length * i / n)
        d = wall_region.distance(Point(pt.x, pt.y))
        dists.append(d)
        if d <= tol_u:
            hits += 1
    return hits, n, max(dists) / UNITS_PER_METRE


def main():
    doc = json.loads(FACTS.read_text(encoding="utf-8"))
    total_excluded = 0
    for raw_view in doc["views"]:
        view = AsMeasuredViewV1.model_validate(raw_view)
        footprint, ring_records = _boundary_footprint(view)
        wall_region = _boundary_wall_region(view)
        geometry = footprint.difference(wall_region)
        thr = MIN_ROOM_AREA_M2 * UNITS_PER_METRE * UNITS_PER_METRE
        parts = [p for p in getattr(geometry, "geoms", [geometry])
                 if p.geom_type == "Polygon" and not p.is_empty]
        cavities = [p for p in parts if p.area > thr]
        cavities.sort(key=lambda c: tuple(round(v, 6) for v in c.bounds))
        cavity_ids = {id(c): _boundary_cavity_id(view.view_id, c) for c in cavities}
        groups = _boundary_wall_groups(view)
        face_by_id = {f.id: f for f in view.face_lines}

        print(f"\n=== {view.view_id} ===")
        print(f"  difference 出的多边形共 {len(parts)} 个；"
              f"过 {MIN_ROOM_AREA_M2} m2 阈值的 cavity = {len(cavities)} 个；"
              f"落库 boundary_edges 覆盖 cavity = "
              f"{len({e.cavity_id for e in view.boundary_edges})} 个")
        sub = sorted((p.area / UNITS_PER_METRE**2 for p in parts if p.area <= thr),
                     reverse=True)[:5]
        print(f"  未过阈值的碎片面积 top5 (m2) = {[round(a,4) for a in sub]}")
        for cav in cavities:
            state, detail = classify_cavity(view, cav, footprint, ring_records,
                                            wall_region, cavities, cavity_ids,
                                            groups, face_by_id)
            if state == "ok":
                continue
            total_excluded += 1
            hits, n, worst = adjacency(cav, wall_region)
            area = cav.area / UNITS_PER_METRE**2
            print(f"  ⛔ EXCLUDED {cavity_ids[id(cav)]}  area={area:.2f} m2  "
                  f"reason={state} {detail}  贴墙 {hits}/{n} (≤{ADJ_TOL_M} m)  "
                  f"最远采样点距墙带 {worst:.3f} m")
    print(f"\n合计被排除的过阈值 cavity = {total_excluded}")


if __name__ == "__main__":
    main()
