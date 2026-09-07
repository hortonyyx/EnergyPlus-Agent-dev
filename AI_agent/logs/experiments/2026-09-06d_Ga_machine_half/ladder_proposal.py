#!/usr/bin/env python3
"""正交吸附的【阶梯】方案 —— 综合线长与角度，超出阶梯才升级人签仲裁。

⭐ 用户 2026-09-07 口径（三句连起来才是完整意思）：
  1. 「**这种正交吸附和按毫米分辨率吸附不用签字，直接修正就可以；
     需要签字的是像上下墙体出现对齐错误的这类真『画错』问题**」
  2. 「**长度越长容差应该越大一些，因为越长越容易歪了看不出来。最大定到 5 度吧**」
     （并确认：「长度」= **歪线自己的总长**，⛔ 不是偏离距离）
  3. 「**按阶梯定一个方案，综合长度和角度；超出的才升级到需要人签字的仲裁，
     确定是不是真画错了**」

⇒ 阶梯把「机器自己修」与「人签仲裁」分在同一条线的两侧。

════════════════════════════════════════════════════════════════════════
阶梯（四档，⭐ **除用户给的 5° 外，零新常数**）
────────────────────────────────────────────────────────────────────────
 档 0  噪声      偏移 ≤ q                     ⇒ 量化本来就抹平，⛔ 不记录
 档 1  自动拉平  偏移 ≤ min(线长·tan5°, CAP)   ⇒ 机器绕「好的那一端」转平，
       （且结构判据能给出唯一锚端）              记一行审计，⛔ 不用人签
 档 2  人签仲裁  角度 ≤ 5° 但偏移 > CAP，       ⇒ 进 revisions 台账，人判
       或结构判据判不出唯一锚端                  「真画错 / 就该这样」
 档 3  真斜线    角度 > 5°                     ⇒ 照旧诊断，⛔ 不拉平也不进台账
════════════════════════════════════════════════════════════════════════

**两个数都不是新发明的**：

  q   = tau_node / 10 = **0.1 mm**  —— 量化步长，派生值
        (``judge_gt.yaml: dxf_node_join_tolerance_m = 0.001``)
  CAP = 最薄墙厚 / 2 = **30 mm**    —— 由 **request 自己声明的**
        ``wall_thickness_range_m[0] = 0.06`` 派生
        ⭐ 语义：位移一旦超过半个最薄墙厚，一个面就可能被推过墙心、
        改变「这条线属于哪堵墙」—— 那已经不是「拉直」而是「改设计」，
        ⇒ 该由人来签。

**⭐ 这个阶梯同时满足用户的两句话**（它们看似矛盾，其实不）：

  · 「长度越长容差越大」 ⇒ 短线区里 偏移上限 = 线长·tan5°，**随长度线性增长** ✓
  · 「长线上小角度就已经很显眼」 ⇒ 长线区里上限封顶在 CAP，
     **等效角度上限 = arctan(CAP/线长) 自动收紧** ✓
  两区的分界 = CAP / tan5° = **343 mm**。

跑法： python AI_agent/logs/experiments/2026-09-06d_Ga_machine_half/ladder_proposal.py
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

import ezdxf

REPO = pathlib.Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SOURCES = REPO / "case_tests/test_baseline/gt_sources"

MAX_ANGLE_DEG = 5.0          # ⭐ 用户 2026-09-07 定
QUANT_MM = 0.1               # q = tau_node/10（派生）
COINCIDENT_MM = 1e-6


def _cap_mm(req: dict) -> float:
    """CAP = 最薄墙厚 / 2，由 request 自己声明的 wall_thickness_range_m 派生。"""
    return req["wall_thickness_range_m"][0] * 1000.0 / 2.0


def _resolve(anchor: pathlib.Path, req: dict) -> pathlib.Path | None:
    named = anchor / req["source_dxf_label"]
    if named.is_file():
        return named
    for candidate in sorted(anchor.glob("*.dxf")):
        if hashlib.sha256(candidate.read_bytes()).hexdigest() == req["source_dxf_sha256"]:
            return candidate
    return None


def _collect(doc, view: dict) -> dict[str, tuple[tuple, tuple, bool]]:
    sel, box = view["wall_selector"], view["clip_box_dxf"]
    layers, types = set(sel.get("layers") or []), set(sel.get("entity_types") or [])
    out: dict[str, tuple[tuple, tuple, bool]] = {}
    for e in doc.modelspace():
        if (types and e.dxftype() not in types) or (layers and e.dxf.layer not in layers):
            continue
        if not hasattr(e.dxf, "start"):
            continue
        s, t = e.dxf.start, e.dxf.end
        if not all(box["xmin"] <= p[0] <= box["xmax"] and box["ymin"] <= p[1] <= box["ymax"]
                   for p in (s, t)):
            continue
        dx, dy = abs(t[0] - s[0]), abs(t[1] - s[1])
        skewed = math.hypot(dx, dy) >= QUANT_MM and min(dx, dy) > COINCIDENT_MM
        out[e.dxf.handle] = ((s[0], s[1]), (t[0], t[1]), skewed)
    return out


def _anchorable_ends(handle: str, strokes: dict) -> list[bool]:
    """每一端能不能锚：与它共端点的邻居里，有没有【本身已正交】的。"""
    p0, p1, _ = strokes[handle]
    result = []
    for point in (p0, p1):
        straight = any(
            not other_skew
            and any(abs(q[0] - point[0]) < COINCIDENT_MM and abs(q[1] - point[1]) < COINCIDENT_MM
                    for q in (other_p0, other_p1))
            for other, (other_p0, other_p1, other_skew) in strokes.items()
            if other != handle)
        result.append(straight)
    return result


#: A-11 的入库网格（1 mm）—— 产物里存得下的最小分辨率。
INGEST_GRID_MM = 1.0


def _stored(value_mm: float) -> int:
    """这个坐标最终会以什么形态存进 as_measured（A-11 的 1 mm 入库网格）。"""
    return round(value_mm / INGEST_GRID_MM)


def _anchor_choice_is_observable(p0, p1, along_is_x: bool) -> bool:
    """⭐ 零阈值判据：锚哪一端【在产物里看得出来吗】？

    候选答案 = 锚端A（取端A 的次坐标）· 锚端B · 取中点。
    三者按入库网格取整后若**完全相同**，这个选择在产物里**不可观测**
    ⇒ ⛔ 没有理由为它惊动一个人（[[proxy-mistaken-for-the-thing]] 的反面用法：
    别把一个观测不到的差别升级成需要签字的决定）。
    """
    minor_index = 1 if along_is_x else 0
    a, b = p0[minor_index], p1[minor_index]
    return len({_stored(a), _stored(b), _stored((a + b) / 2.0)}) > 1


def _tier(minor_mm: float, length_mm: float, anchors: list[bool], cap_mm: float,
          p0=None, p1=None, along_is_x: bool = True) -> tuple[str, float]:
    angle_cap_mm = length_mm * math.tan(math.radians(MAX_ANGLE_DEG))
    tier1_cap = min(angle_cap_mm, cap_mm)
    if minor_mm <= QUANT_MM:
        return "档0 噪声（量化抹平，不记录）", tier1_cap
    if minor_mm > angle_cap_mm:
        return "档3 真斜线（角度 > 5°，照旧诊断）", tier1_cap
    if minor_mm > cap_mm:
        return "档2 人签仲裁（角度合格但位移超 CAP）", tier1_cap
    if sum(anchors) == 1:
        return f"档1 自动拉平（锚{'端A' if anchors[0] else '端B'}）", tier1_cap
    # 锚端不唯一 —— 先问「这个选择在产物里看得出来吗」，⛔ 别急着惊动人
    if p0 is not None and not _anchor_choice_is_observable(p0, p1, along_is_x):
        return "档1 自动拉平（⭐ 锚端选择在入库网格上不可观测，取中点即可）", tier1_cap
    why = "两端都锚得住 ⇒ 疑似真斜线" if sum(anchors) == 2 else "两端都锚不住 ⇒ 须按连通组解"
    return f"档2 人签仲裁（{why}，且该选择在产物里看得出来）", tier1_cap


def main() -> None:
    print(f"角度上限 = {MAX_ANGLE_DEG}°（用户定） · q = {QUANT_MM} mm（派生）")
    print("CAP = 最薄墙厚/2（由 request 的 wall_thickness_range_m 派生）\n")
    print("① 阶梯长什么样（偏移上限 vs 线长）")
    print(f"   {'线长':>10}{'档1 上限(mm)':>16}{'等效角度上限':>16}{'哪一区':>12}")
    cap = 30.0
    for length_mm in (120, 240, 343, 500, 1000, 3640, 10000):
        angle_cap = length_mm * math.tan(math.radians(MAX_ANGLE_DEG))
        tier1 = min(angle_cap, cap)
        eff = math.degrees(math.atan2(tier1, length_mm))
        zone = "短线区(角度当家)" if angle_cap <= cap else "长线区(CAP 当家)"
        print(f"   {length_mm/1000:8.3f} m{tier1:14.1f}{eff:15.3f}°{zone:>16}")
    print()
    print("② 语料里每条歪线落在哪一档")
    for case in sorted(p.name for p in SOURCES.iterdir() if p.is_dir()):
        anchor = SOURCES / case
        req_path = (anchor / "request_as_measured.json"
                    if (anchor / "request_as_measured.json").is_file()
                    else anchor / "request.json")
        if not req_path.is_file():
            continue
        req = json.loads(req_path.read_text(encoding="utf-8"))
        dxf = _resolve(anchor, req)
        if dxf is None:
            continue
        cap_mm = _cap_mm(req)
        doc = ezdxf.readfile(dxf)
        for view in req.get("plan_views", []):
            strokes = _collect(doc, view)
            skewed = sorted(h for h, v in strokes.items() if v[2])
            if not skewed:
                continue
            print(f"   === {case} / {view['id']}  (CAP = {cap_mm:.0f} mm) ===")
            for handle in skewed:
                p0, p1, _ = strokes[handle]
                dx, dy = abs(p1[0] - p0[0]), abs(p1[1] - p0[1])
                minor, length = min(dx, dy), math.hypot(dx, dy)
                angle = math.degrees(math.atan2(minor, max(dx, dy)))
                tier, tier1_cap = _tier(minor, length, _anchorable_ends(handle, strokes),
                                        cap_mm, p0, p1, along_is_x=dx >= dy)
                print(f"     {handle}: 长 {length/1000:6.3f} m  偏移 {minor:8.4f} mm"
                      f"  角度 {angle:.4f}°  档1上限 {tier1_cap:6.1f} mm")
                print(f"        ⇒ {tier}")


if __name__ == "__main__":
    main()
