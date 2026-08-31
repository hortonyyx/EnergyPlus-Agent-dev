import json
from pathlib import Path
from shapely.geometry import Point
from src.agent.judge.as_measured import (
    AsMeasuredViewV1, UNITS_PER_METRE,
    _boundary_footprint, _boundary_wall_region, _boundary_band_rectangle,
    _boundary_wall_groups)

FACTS = Path("case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json")
M = UNITS_PER_METRE
doc = json.loads(FACTS.read_text(encoding="utf-8"))
views = {v["view_id"]: AsMeasuredViewV1.model_validate(v) for v in doc["views"]}

print("=========== 形态 A：出口射线 1 单位(0.1mm) 落进邻墙 ===========")
for vid in ("plan-F1", "plan-F2"):
    view = views[vid]
    pt = Point(50000, 161201)
    print(f"\n--- {vid} 覆盖 exit_point (5.0000 m, 16.1201 m) 的墙/洞口 ---")
    for w in view.walls:
        r = _boundary_band_rectangle(w.axis, w.face_lo, w.face_hi, w.along_min, w.along_max)
        if r.covers(pt):
            print(f"  WALL {w.id} axis={w.axis} face=[{w.face_lo},{w.face_hi}]"
                  f" ({(w.face_hi-w.face_lo)/M*1000:.0f} mm) along=[{w.along_min},{w.along_max}]"
                  f" = y[{w.face_lo/M},{w.face_hi/M}] m")
    for o in view.openings:
        r = _boundary_band_rectangle(o.axis, o.cross_lo, o.cross_hi, o.along_min, o.along_max)
        if r.covers(pt):
            print(f"  OPENING {o.id} axis={o.axis} cross=[{o.cross_lo},{o.cross_hi}]"
                  f" along=[{o.along_min},{o.along_max}]")
    # 该点向上再走，多远才出墙
    for step in (1, 2, 5, 10, 50, 100, 200, 400, 800, 1200, 2400):
        p = Point(50000, 161200 + step)
        wr = _boundary_wall_region(view)
        if not wr.covers(p):
            print(f"  ⇒ 从 far face y=161200 起，向外走 {step} 单位 ({step/10:.1f} mm) 才离开墙体并集")
            break

print("\n=========== 形态 B：cavity 环顶点比墙面 const 大 1 单位(0.1mm) ===========")
view = views["plan-F1"]
footprint, _ = _boundary_footprint(view)
wall_region = _boundary_wall_region(view)
geom = footprint.difference(wall_region)
THR = 5.0 * M * M
cavs = [p for p in getattr(geom, "geoms", [geom])
        if p.geom_type == "Polygon" and not p.is_empty and p.area > THR]
cavs.sort(key=lambda c: tuple(round(v, 6) for v in c.bounds))
target = [c for c in cavs if abs(c.area / M / M - 28.68) < 0.05][0]
rep = target.representative_point()
print(f"  cavity area={target.area/M/M:.4f} m2  bounds={target.bounds}")
print(f"  representative_point = ({rep.x:.6f}, {rep.y:.6f})  centroid=({target.centroid.x:.3f},{target.centroid.y:.3f})")
print("  环上 x 在 52395..52410 的原始(未取整)顶点：")
for x, y in list(target.exterior.coords):
    if 52390 <= x <= 52415:
        print(f"    raw=({x!r}, {y!r})  -> int=({int(round(x))},{int(round(y))})")
