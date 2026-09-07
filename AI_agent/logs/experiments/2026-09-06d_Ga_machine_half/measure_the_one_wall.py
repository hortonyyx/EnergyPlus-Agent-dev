#!/usr/bin/env python3
"""G-a 机器那半：把 sm25-L 那份 revisions 清单上的 3 条记录量到底。

⭐ 本脚本只【量】，不改任何产物 —— 结论全部写在 README.md，这里只负责让每个数字
   可以被重新跑出来（[[verify-the-number-before-writing-it-into-a-load-bearing-place]]）。

跑法：  python AI_agent/logs/experiments/2026-09-07a_Ga_machine_half/measure_the_one_wall.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import ezdxf

REPO = pathlib.Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ANCHOR = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
FACTS = REPO / "case_tests/test_baseline/gt_staging/sm25-L_anchor/facts"

#: The worklist the 09-01 builder script was handed.  ⚠️ 5 handles, but only 3
#: still produce a candidate after A-11's 1 mm ingest grid (13AC / 160A fell
#: below it) -- that is why plan.md's "那 5 条线" is stale.
WORKLIST = ("13AD", "13AC", "13AF", "160A", "13AE")
#: The one wall those records are really about.
THE_WALL = ("13AD", "13AE", "13AF")


def _load(dxf: str, request: str):
    doc = ezdxf.readfile(ANCHOR / dxf)
    req = json.loads((ANCHOR / request).read_text(encoding="utf-8"))
    return doc, req["plan_views"][0]["world_from_source_m"]


def _world_units(m: dict, point) -> tuple[float, float]:
    """source -> world metres -> 0.1 mm units, WITHOUT any quantisation."""
    x = m["m00"] * point[0] + m["m01"] * point[1] + m["m02"]
    y = m["m10"] * point[0] + m["m11"] * point[1] + m["m12"]
    return x * 10000.0, y * 10000.0


def _endpoints(doc, m, handle):
    entity = doc.entitydb.get(handle)
    if entity is None or not hasattr(entity.dxf, "start"):
        return None
    return _world_units(m, entity.dxf.start), _world_units(m, entity.dxf.end)


def main() -> None:
    received, m_recv = _load("sm25-L_t3_as_received.dxf", "request_as_measured.json")
    signed, m_sign = _load("sm25-L_t3.dxf", "request.json")

    print("=" * 78)
    print("① 两份图上，清单里的 5 个 handle 各自长什么样（0.1 mm 世界单位，未量化）")
    print("=" * 78)
    for label, doc, m in (("as_received", received, m_recv), ("signed(t3)  ", signed, m_sign)):
        print(f"--- {label} ---")
        for handle in WORKLIST:
            pts = _endpoints(doc, m, handle)
            if pts is None:
                print(f"  {handle}: absent / non-LINE")
                continue
            (x0, y0), (x1, y1) = pts
            print(f"  {handle}: ({x0:10.3f},{y0:10.3f}) -> ({x1:10.3f},{y1:10.3f})"
                  f"   |dx|={abs(x1 - x0):9.3f}u  |dy|={abs(y1 - y0):9.3f}u")

    print()
    print("=" * 78)
    print("② 这 3 条是不是【同一次刚体旋转】—— 逐条量它偏离最近坐标轴多少")
    print("=" * 78)
    angles = {}
    for handle in THE_WALL:
        (x0, y0), (x1, y1) = _endpoints(received, m_recv, handle)
        theta = math.atan2(y1 - y0, x1 - x0)
        residual = min(abs(theta - k * math.pi / 2) for k in range(-2, 3))
        angles[handle] = residual
        print(f"  {handle}: {residual:.9e} rad = {math.degrees(residual) * 3600:8.2f} 角秒")
    spread = max(angles.values()) - min(angles.values())
    print(f"  ⇒ 三条之间的最大差 = {spread:.3e} rad "
          f"({'一次刚体旋转' if spread < 1e-8 else '⛔ 不是同一个角'})")

    print()
    print("=" * 78)
    print("③ 旋转中心在哪 —— 用 as_received→signed 的 Δy 对 x 做直线，求 Δy=0 的 x")
    print("=" * 78)
    (wx, wy), (ex, ey) = _endpoints(received, m_recv, "13AD")
    (swx, swy), (sex, sey) = _endpoints(signed, m_sign, "13AD")
    dy_west, dy_east = swy - wy, sey - ey
    slope = (dy_east - dy_west) / (ex - wx)
    cx = wx - dy_west / slope
    print(f"  13AD 西头 Δy = {dy_west:8.3f}u   东头 Δy = {dy_east:8.3f}u")
    print(f"  ⇒ 旋转角 = {slope:.9e} rad = {math.degrees(slope) * 3600:.2f} 角秒")
    print(f"  ⇒ Δy=0 的 x = {cx:.3f}u")
    neighbours = {h: _endpoints(received, m_recv, h) for h in ("13AA", "160C")}
    for handle, pts in neighbours.items():
        (nx0, ny0), (nx1, ny1) = pts
        print(f"  隔壁 {handle}: x={nx0:.3f}u   端点 y = {ny0:.3f} / {ny1:.3f}")
    jx = neighbours["13AA"][0][0]
    print(f"  ⇒ 旋转中心 x 与隔壁墙 13AA/160C 的 x 差 {abs(cx - jx):.3f}u "
          f"({abs(cx - jx) / 10:.4f} mm)")

    print()
    print("=" * 78)
    print("④ 落库后 13AF 的证据还在不在（A-11 1 mm 入库规整的作用面）")
    print("=" * 78)
    stored = json.loads((FACTS / "as_measured.json").read_text(encoding="utf-8"))
    for view in stored["views"]:
        for row in view["converter_readouts"].get("non_orthogonal_lines", []):
            print(f"  view {view['view_id']}  {row['id']}: p0={row['p0']} p1={row['p1']}"
                  f"   ⇒ dx={abs(row['p1'][0] - row['p0'][0])}u")
    (rx0, _), (rx1, _) = _endpoints(received, m_recv, "13AF")
    print(f"  裸 ezdxf 量的原值: x {rx0:.3f} -> {rx1:.3f}  (dx={abs(rx1 - rx0):.3f}u "
          f"= {abs(rx1 - rx0) / 10:.4f} mm)")
    print("  ⇒ 存进去的两个端点 x 相同 = 一条【完全垂直】的线，被登记在 non_orthogonal_lines 里")


if __name__ == "__main__":
    main()


# --------------------------------------------------------------------------- #
# ⭐ 2026-09-07 追加：题面翻转那一轮的两处实测（接头对账 + 阈值缝）
# 跑法： python …/measure_the_one_wall.py --reframe
# --------------------------------------------------------------------------- #
def reframe() -> None:
    stored = json.loads((FACTS / "as_measured.json").read_text(encoding="utf-8"))
    view = stored["views"][0]
    by_id = {f["id"]: f for f in view["face_lines"]}

    print("=" * 78)
    print("⑤ 接头对账 —— 光看 as_measured 自己，这堵墙和邻墙对得上吗")
    print("=" * 78)
    for wall_face, neighbour in (("13AD", "13AC"), ("13AE", "160A")):
        f, g = by_id.get(wall_face), by_id.get(neighbour)
        if f is None or g is None:
            print(f"  {wall_face}/{neighbour}: 有一条不在 face_lines 里")
            continue
        gap = min(abs(f["const"] - g["along_min"]), abs(f["const"] - g["along_max"]))
        # ⭐ 接头是否成立 = 这条水平面线的 const 落不落在竖线的【端点】上，
        # ⛔ 不是「两条线在 x 上有没有重叠」（那只说明它们相交，不说明接得上）。
        at_end = f["const"] in (g["along_min"], g["along_max"])
        inside = g["along_min"] < f["const"] < g["along_max"]
        shape = ("✅ 正好在端点" if at_end
                 else "⛔ 穿过去了(端点变成了 T 形交叉)" if inside
                 else "⛔ 够不着(留了个缝)")
        print(f"  {neighbour}: along=[{g['along_min']},{g['along_max']}] const={g['const']}")
        print(f"  {wall_face}: const={f['const']}"
              f"  ⇒ 距 {neighbour} 最近端点 {gap} 单位 = {gap / 10:.1f} mm   {shape}")

    print()
    print("=" * 78)
    print("⑥ 13AF 掉进的那条缝：两个阈值在 (0, 1mm) 上互相不认")
    print("=" * 78)
    from src.agent.judge import tarch_normalize as tn
    (rx0, _), (rx1, _) = _endpoints(*_load("sm25-L_t3_as_received.dxf",
                                           "request_as_measured.json"), "13AF")
    skew_mm = abs(rx1 - rx0) / 10.0
    print(f"  13AF 实际歪斜            = {skew_mm:.4f} mm")
    print(f"  吸附分支进入条件         = 两条腿都 > tau_axis (= 1 mm)"
          f"   ⇒ {skew_mm:.4f} <= 1 ⇒ 【不进分支】")
    # ⚠️ 09-06 那一轮的两道门 = 10 mm / 1.0°；两者在 09-07 都已被 G-c 阶梯取代
    # （10 mm 作废，角度 1.0°→5.0°）⇒ 这里写死当时的值，⛔ 不从生产模块读，
    # 否则本脚本复现不出 09-06 的读数。
    print(f"  两道吸附门（进了才用得上）= <= 10 mm"
          f" 且 <= 1°  （13AF 两项都合格，但根本没走到）")
    print("  面线分类判据             = x0 == x1 【精确相等、零容差】 ⇒ 【不算面线】")
    discarded = view["converter_readouts"]["s1_nonorthogonal_discarded_handles"]
    print(f"  佐证 s1_nonorthogonal_discarded_handles = {len(discarded)} 条 {discarded}"
          "  ⇒ 从来没有任何一条被吸附门拒绝过")


if __name__ == "__main__" and "--reframe" in sys.argv:
    reframe()
