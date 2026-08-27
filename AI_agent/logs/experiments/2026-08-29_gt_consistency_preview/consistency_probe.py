"""⭐ gt 一致性检查原型 —— 「按一个真正的建筑来把问题筛出来」（用户 2026-08-29）

⛔ 探索档诊断工具，**产物不作成绩**。事实层（as_measured）尚未落库，本原型暂从
判分器现算的面线取数；事实层落地后须重接。

设计口径（用户 2026-08-29 定 + orchestrator 当日三次实证）：
  ⛔ **不设差值阈值**。取代阈值的是【结构上的唯一匹配】= 互为最近邻。
     实证：面线比面线 = 625 条噪声；墙比墙但「重叠即配」= 仍爆炸；
     墙比墙 + 互为最近邻 = **1 条**（那处真的 60 mm）。
  ⭐ 排序不是阈值：全列出来，人从大到小看。

⛔ 渲染器只照搬不推导：墙带的两条边【就是】量到的那两条面线，
   ⛔ 不许「取中轴再 ±半个厚度」重画 —— 那会把错误抹平。
"""
from __future__ import annotations
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from src.agent.judge.as_drawn.denominator import denominator   # noqa: E402

MODULE_MM = 1.0          # 用户 2026-08-29 定：给 pipeline 的分辨率默认 1 mm


def walls(d):
    """把面线两两配成墙。⛔ 无厚度阈值：同轴 + 沿墙重叠 + 取最近的一条作对面。
    ⭐ 保留【两条面线各自的位置】，⛔ 不塌成中轴（渲染器要照搬它们）。"""
    ts, used, out = d["targets"], set(), []
    for i, a in enumerate(ts):
        if i in used:
            continue
        best = None
        for j, b in enumerate(ts):
            if j <= i or j in used or a["axis"] != b["axis"]:
                continue
            ov = min(a["hi_m"], b["hi_m"]) - max(a["lo_m"], b["lo_m"])
            gap = abs(a["const_m"] - b["const_m"])
            if ov <= 0 or gap < 1e-9:
                continue
            if best is None or gap < best[0]:
                best = (gap, j, b, ov)
        if best:
            gap, j, b, ov = best
            used |= {i, j}
            f0, f1 = sorted((a["const_m"], b["const_m"]))
            out.append({"axis": a["axis"], "f0": f0, "f1": f1,
                        "mid": round((f0 + f1) / 2, 4), "t": round(gap, 4),
                        "lo": max(a["lo_m"], b["lo_m"]), "hi": min(a["hi_m"], b["hi_m"])})
    unpaired = [ts[i] for i in range(len(ts)) if i not in used]
    return _to_wall_lines(out), unpaired


def _to_wall_lines(segs):
    """⭐ 把【墙段】合并成【墙线】—— 匹配单位必须是墙线。

    ⛔ 实证（2026-08-29 第 4 次迭代）：按墙【段】做互为最近邻，会产生 24 条假的
    「这堵墙在另一层找不到对应」—— 因为同一堵物理墙在两层被切成的段数不同
    （洞口位置不同 ⇒ 切法不同），1 对 1 匹配下配不上的那些就被判成「另一层没有」。
    同族 [[proxy-mistaken-for-the-thing]]：拿「墙段」当了「墙」的代理量。
    """
    g = {}
    for s in segs:
        k = (s["axis"], round(s["f0"], 4), round(s["f1"], 4))
        e = g.setdefault(k, {"axis": s["axis"], "f0": s["f0"], "f1": s["f1"],
                             "mid": s["mid"], "t": s["t"],
                             "lo": s["lo"], "hi": s["hi"], "segs": []})
        e["lo"] = min(e["lo"], s["lo"]); e["hi"] = max(e["hi"], s["hi"])
        e["segs"].append([round(s["lo"], 3), round(s["hi"], 3)])
    return list(g.values())


def _mutual_nearest(A, B):
    """⭐ 结构唯一匹配，⛔ 不是阈值。"""
    def near(x, others):
        c = [o for o in others if o["axis"] == x["axis"]
             and min(x["hi"], o["hi"]) - max(x["lo"], o["lo"]) > 0]
        return min(c, key=lambda o: abs(o["mid"] - x["mid"])) if c else None
    return [(a, b) for a in A if (b := near(a, B)) is not None and near(b, A) is a]


def check(floors, declared_t_mm):
    """floors: {floor_id: (walls, unpaired)}。返回 findings 清单，⛔ 无阈值、按幅度排序。"""
    F = []
    ids = list(floors)

    # ── 类型二：本该一致的不一致（跨层）──────────────────────────────
    for i in range(len(ids) - 1):
        lo_id, hi_id = ids[i], ids[i + 1]
        A, B = floors[lo_id][0], floors[hi_id][0]
        pairs = _mutual_nearest(A, B)
        for a, b in pairs:
            dm = abs(a["mid"] - b["mid"]) * 1000
            dt = abs(a["t"] - b["t"]) * 1000
            if dm > 1e-6:
                F.append({"kind": "cross_floor_axis_offset", "mm": round(dm, 3),
                          "where": f"{lo_id}↔{hi_id}", "axis": a["axis"],
                          "detail": f"{lo_id} 中轴 {a['mid']:.4f} vs {hi_id} {b['mid']:.4f}",
                          "span": [round(max(a['lo'], b['lo']), 3), round(min(a['hi'], b['hi']), 3)],
                          "floor": lo_id, "wall": a})
            if dt > 1e-6:
                F.append({"kind": "cross_floor_thickness", "mm": round(dt, 3),
                          "where": f"{lo_id}↔{hi_id}", "axis": a["axis"],
                          "detail": f"{lo_id} t={a['t']:.4f} vs {hi_id} t={b['t']:.4f}",
                          "span": [round(max(a['lo'], b['lo']), 3), round(min(a['hi'], b['hi']), 3)],
                          "floor": lo_id, "wall": a})
        # 只在一层出现、另一层无对应的墙
        # ⭐ 落单的也要报【最近对手 + 距离】。
        # ⛔ 只说「找不到对应」会把两种完全不同的情况压成一句话（[[absence-conflates-causes-in-observables]]）：
        #    ① 那一层根本没有这堵墙（真的没有）
        #    ② 有，但整体挪了一点 ⇒ 于是成了另一条墙线、配不上
        # 实证：sm25 那处 60 mm 错位正是 ②，只说「找不到对应」会把「偏 60 mm」这个数弄丢。
        for lbl, other_lbl, X, Y, P in ((lo_id, hi_id, A, B, {id(a) for a, _ in pairs}),
                                        (hi_id, lo_id, B, A, {id(b) for _, b in pairs})):
            for w in X:
                if id(w) in P:
                    continue
                cand = [o for o in Y if o["axis"] == w["axis"]
                        and min(w["hi"], o["hi"]) - max(w["lo"], o["lo"]) > 0]
                if cand:
                    n = min(cand, key=lambda o: abs(o["mid"] - w["mid"]))
                    dm = abs(n["mid"] - w["mid"]) * 1000
                    # ⭐⭐ 结构性判据，⛔ 零发明阈值：两堵墙的中轴差【小于它们自己的厚度】
                    # ⇒ 两条墙带在物理上重叠 ⇒ 不可能是两堵有意为之的墙
                    # ⇒ 必然是【同一堵墙没对齐】。
                    # 比较的尺子是墙【自己量出来的厚度】（事实），⛔ 不是谁挑的参数。
                    # 实测 sm25：60 mm vs (120+120)/2 = 120 ⇒ 重叠 ⇒ 判为错位 ✓
                    #            3910 / 1880 mm vs 120 / 180 ⇒ 不重叠 ⇒ 两层布局本就不同 ✓
                    overlap = dm < (w["t"] + n["t"]) * 1000 / 2.0
                    kind = "cross_floor_misaligned" if overlap else "cross_floor_layout_differs"
                    F.append({"kind": kind, "mm": round(dm, 3), "suspicious": overlap,
                              "band_mm": round((w["t"] + n["t"]) * 1000 / 2.0, 1),
                              "where": f"{lbl}↔{other_lbl}", "axis": w["axis"],
                              "detail": (f"{lbl} 中轴 {w['mid']:.4f} 这堵墙，在 {other_lbl} 上最近的同位墙是 "
                                         f"{n['mid']:.4f}（差 {dm:.3f} mm）⇒ 配不成同一条墙线"),
                              "span": [round(w["lo"], 3), round(w["hi"], 3)], "floor": lbl, "wall": w})
                else:
                    F.append({"kind": "cross_floor_absent", "mm": round(w["t"] * 1000, 1),
                              "where": f"{lbl}↔{other_lbl}", "axis": w["axis"],
                              "detail": (f"{lbl} 中轴 {w['mid']:.4f} 这堵墙，在 {other_lbl} 上"
                                         f"【沿墙方向完全没有】同位墙（长 {w['hi']-w['lo']:.3f} m）"),
                              "span": [round(w["lo"], 3), round(w["hi"], 3)], "floor": lbl, "wall": w})

    # ── 同层 ────────────────────────────────────────────────────────
    for fid, (W, unpaired) in floors.items():
        for w in W:
            t_mm = w["t"] * 1000
            if not any(abs(t_mm - d) < 1e-6 for d in declared_t_mm):
                F.append({"kind": "thickness_not_declared", "mm": round(t_mm, 3),
                          "where": fid, "axis": w["axis"],
                          "detail": f"墙厚 {t_mm:.3f} mm 不在声明集合 {declared_t_mm} 内",
                          "span": [round(w["lo"], 3), round(w["hi"], 3)], "floor": fid, "wall": w})
        for u in unpaired:
            F.append({"kind": "unpaired_face_line", "mm": round((u["hi_m"] - u["lo_m"]) * 1000, 1),
                      "where": fid, "axis": u["axis"],
                      "detail": f"面线没有配到对面（{u['axis']}={u['const_m']:.4f}，长 {u['length_m']:.3f} m）",
                      "span": [round(u["lo_m"], 3), round(u["hi_m"], 3)], "floor": fid, "wall": None})

    # ── 类型一：值不在声明模数上 ─────────────────────────────────────
    for fid, (W, _) in floors.items():
        for w in W:
            for nm, v in (("f0", w["f0"]), ("f1", w["f1"]), ("lo", w["lo"]), ("hi", w["hi"])):
                off = abs(v * 1000 / MODULE_MM - round(v * 1000 / MODULE_MM)) * MODULE_MM
                if off > 1e-6:
                    F.append({"kind": "off_module", "mm": round(off, 4), "where": fid,
                              "axis": w["axis"], "detail": f"{nm}={v:.6f} m 偏离 {MODULE_MM} mm 模数 {off:.4f} mm",
                              "span": [round(w["lo"], 3), round(w["hi"], 3)], "floor": fid, "wall": w})
    # ⭐ 排序 ≠ 过滤：全部条目都在清单上。
    # 只是把【结构上可疑的】排到前面 —— 可疑 = 两条墙带物理重叠却没对齐。
    F.sort(key=lambda f: (not f.get("suspicious", True), -f["mm"]))
    return F


def check_openings(floors, openings):
    """⭐ 洞口类检查（2026-08-29 补）—— 此前「洞口一条没查」是最大的缺口。

    ⛔ 同样零阈值：判据全部来自【洞口自己/墙自己携带的量】。
    """
    F = []
    for fid, (W, _) in floors.items():
        for t in openings.get(fid, []):
            c0, c1 = t["const_range_m"]
            cmid = (c0 + c1) / 2.0
            # ── ① 洞口落在墙上吗 ──────────────────────────────
            # 结构判据：洞口的横向范围必须【落在某堵墙的两条面线之间】，
            # 且洞口沿墙方向要与那堵墙有重叠。⛔ 不设容差：面线就是墙的边界。
            # ⚠️ 2026-08-29 变异测试抓出：原来只验【中点】在墙里 ⇒ 洞口挪 1 mm
            # （一端捅出墙面）照样全绿。⭐ 改验【整个厚度方向范围被墙带包住】。
            # 这条改动是「M4 期望它报、它没报」逼出来的 —— ⭐ 写变异时那句"期望"
            # 本身就是信号：我以为它能查，其实不能。
            host, host_loose = None, None
            for w in W:
                if w["axis"] != t["axis"]:
                    continue
                if not (w["f0"] <= cmid <= w["f1"]):
                    continue
                if min(w["hi"], t["hi_m"]) - max(w["lo"], t["lo_m"]) > 0:
                    host_loose = w
                if not (w["f0"] - 1e-9 <= c0 and c1 <= w["f1"] + 1e-9):
                    continue
                if min(w["hi"], t["hi_m"]) - max(w["lo"], t["lo_m"]) <= 0:
                    continue
                host = w
                break
            if host is None and host_loose is not None:
                # 中点在墙里、但整个范围没被包住 ⇒ 洞口捅出了墙面
                out_mm = max(host_loose["f0"] - c0, c1 - host_loose["f1"]) * 1000
                F.append({"kind": "opening_pokes_out_of_wall", "mm": round(out_mm, 3),
                          "where": fid, "axis": t["axis"], "suspicious": True,
                          "detail": (f"{fid} 这个{t.get('kind','洞口')}的厚度方向范围 "
                                     f"[{c0:.4f},{c1:.4f}] 没有被承载墙 "
                                     f"[{host_loose['f0']:.4f},{host_loose['f1']:.4f}] 包住"
                                     f"（捅出 {out_mm:.1f} mm）"),
                          "span": [round(t["lo_m"], 3), round(t["hi_m"], 3)],
                          "floor": fid, "wall": host_loose})
                continue
            if host is None:
                F.append({"kind": "opening_not_on_a_wall",
                          "mm": round((t["hi_m"] - t["lo_m"]) * 1000, 1),
                          "where": fid, "axis": t["axis"], "suspicious": True,
                          "detail": (f"{fid} 这个{t.get('kind','洞口')}（{t['axis']}∈[{c0:.4f},{c1:.4f}]，"
                                     f"沿墙 [{t['lo_m']:.3f},{t['hi_m']:.3f}]）"
                                     f"**找不到承载它的墙**"),
                          "span": [round(t["lo_m"], 3), round(t["hi_m"], 3)],
                          "floor": fid, "wall": None})
                continue
            # ── ② 洞口宽度 vs 墙段长度：洞口不该比它所在的墙还长 ────────
            if t["hi_m"] - t["lo_m"] > host["hi"] - host["lo"] + 1e-9:
                F.append({"kind": "opening_wider_than_host",
                          "mm": round((t["hi_m"] - t["lo_m"] - (host["hi"] - host["lo"])) * 1000, 1),
                          "where": fid, "axis": t["axis"], "suspicious": True,
                          "detail": (f"{fid} 这个{t.get('kind','洞口')}宽 {t['hi_m']-t['lo_m']:.3f} m，"
                                     f"比承载它的墙（{host['hi']-host['lo']:.3f} m）还长"),
                          "span": [round(t["lo_m"], 3), round(t["hi_m"], 3)],
                          "floor": fid, "wall": host})
            # ── ③ 洞口厚度方向必须与墙厚一致（洞口是墙上挖的） ──────────
            dt = abs((c1 - c0) - host["t"]) * 1000
            if dt > 1e-6:
                F.append({"kind": "opening_depth_ne_wall_thickness", "mm": round(dt, 3),
                          "where": fid, "axis": t["axis"],
                          "suspicious": dt < host["t"] * 1000,   # 同一堵墙的量级 ⇒ 可疑
                          "detail": (f"{fid} 这个{t.get('kind','洞口')}的厚度方向跨度 {(c1-c0)*1000:.1f} mm，"
                                     f"与承载墙的厚度 {host['t']*1000:.1f} mm 不一致"),
                          "span": [round(t["lo_m"], 3), round(t["hi_m"], 3)],
                          "floor": fid, "wall": host})
    F.sort(key=lambda f: (not f.get("suspicious", True), -f["mm"]))
    return F
