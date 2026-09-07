#!/usr/bin/env python3
"""把「不完全正交」的笔画全体量出来 —— 去掉那道入口卡会多出多少条？

⭐ 背景：现行代码在这条路上有**三个**判据，而只有后两个是用户签过字的：

  ① **入口卡**（⛔ **没有为这个用途签过字**）：`dx > tau_axis AND dy > tau_axis`，
     `tau_axis = dxf_axis_alignment_tolerance_m = 1 mm`
  ② 偏移门（**已签**，2026-08-30）：`minor_leg <= AXIS_SNAP_MAX_DEVIATION_M`（10 mm）
  ③ 角度门（**已签**，同上，用户原话「签，角度调到 1 度吧」）：`angle <= 1°`

用户 2026-09-07 口径：「**用歪线的长度 + 偏移的角度一起来定**」⇒ 由 ②③ 定，
⛔ 不要那个只看 minor_leg 绝对值的入口卡 —— 它正是 13AF 掉进去的那条缝。

⚠️ **但入口卡还兼着第二份工：挡住浮点噪声。** 本脚本就是量这件事的：
噪声有多少条、真歪斜有多少条、分界在哪。

⭐ **量化步长 `q = tau_node / 10 = 0.1 mm`**（`judge_gt.yaml`：`dxf_node_join_tolerance_m
= 0.001`）—— 它才是真正的噪声地板：比 q 小的偏差，后面那步量化本来就会抹平。

跑法： python AI_agent/logs/experiments/2026-09-06d_Ga_machine_half/sweep_skew_population.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from collections import Counter

import ezdxf

REPO = pathlib.Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.agent.judge.tarch_normalize import (  # noqa: E402
    AXIS_SNAP_MAX_ANGLE_DEG, AXIS_SNAP_MAX_DEVIATION_M)

SOURCES = REPO / "case_tests/test_baseline/gt_sources"

TAU_AXIS_MM = 1.0     # 现行入口卡（dxf_axis_alignment_tolerance_m）
QUANT_MM = 0.1        # q = tau_node / 10 —— 真正的噪声地板
DEV_MAX_MM = AXIS_SNAP_MAX_DEVIATION_M * 1000.0

BUCKETS = ("精确正交", "浮点噪声 <1e-6mm", "1e-6 ~ q(0.1mm)",
           "⭐ q ~ tau_axis(1mm) 缝里", "tau_axis ~ 10mm 今天就吸附", "真斜线 >10mm 或 >1°")


def _resolve_by_hash(anchor: pathlib.Path, want_sha256: str) -> pathlib.Path | None:
    """按 request 声明的 sha256 在 anchor 目录里认出源图。

    ⛔ 不按文件名猜：``source_dxf_label`` 是标签，与盘上的文件名不保证一致
    （sm24 实测：标签 ``sm24_source.dxf`` vs 盘上 ``source.dxf``）。
    """
    import hashlib
    for candidate in sorted(anchor.glob("*.dxf")):
        if hashlib.sha256(candidate.read_bytes()).hexdigest() == want_sha256:
            return candidate
    return None


def _in_box(point, box) -> bool:
    return (box["xmin"] <= point[0] <= box["xmax"]
            and box["ymin"] <= point[1] <= box["ymax"])


def _classify(dx: float, dy: float) -> tuple[str, float, float, float]:
    minor, major = min(dx, dy), max(dx, dy)
    angle = math.degrees(math.atan2(minor, major)) if major else 0.0
    if minor == 0.0:
        return "精确正交", major, minor, angle
    if minor > DEV_MAX_MM or angle > AXIS_SNAP_MAX_ANGLE_DEG:
        return "真斜线 >10mm 或 >1°", major, minor, angle
    if minor < 1e-6:
        return "浮点噪声 <1e-6mm", major, minor, angle
    if minor <= QUANT_MM:
        return "1e-6 ~ q(0.1mm)", major, minor, angle
    if minor <= TAU_AXIS_MM:
        return "⭐ q ~ tau_axis(1mm) 缝里", major, minor, angle
    return "tau_axis ~ 10mm 今天就吸附", major, minor, angle


def main() -> None:
    print(f"已签的两道门: 偏移 <= {DEV_MAX_MM:.0f} mm 且 角度 <= {AXIS_SNAP_MAX_ANGLE_DEG:.0f}°")
    print(f"没为此用途签过字的入口卡: 两条腿都 > tau_axis = {TAU_AXIS_MM} mm")
    print(f"真正的噪声地板（量化步长）: q = {QUANT_MM} mm\n")
    grand: Counter[str] = Counter()
    for case in sorted(p.name for p in SOURCES.iterdir() if p.is_dir()):
        anchor = SOURCES / case
        req_path = (anchor / "request_as_measured.json"
                    if (anchor / "request_as_measured.json").is_file()
                    else anchor / "request.json")
        if not req_path.is_file():
            continue
        req = json.loads(req_path.read_text(encoding="utf-8"))
        # ⚠️ ``source_dxf_label`` 是【标签】不是文件名（sm24 的标签 = "sm24_source.dxf"，
        # 盘上却叫 "source.dxf"）⇒ 找不到就按 request 声明的 sha256 在同目录里认。
        dxf = anchor / req["source_dxf_label"]
        if not dxf.is_file():
            dxf = _resolve_by_hash(anchor, req["source_dxf_sha256"])
        if dxf is None:
            print(f"=== {case}: 认不出 {req['source_dxf_label']}（哈希也没匹配上），跳过\n")
            continue
        doc = ezdxf.readfile(dxf)
        print(f"=== {case}  ({req['source_dxf_label']}) ===")
        for view in req.get("plan_views", []):
            sel, box = view["wall_selector"], view["clip_box_dxf"]
            layers, types = set(sel.get("layers") or []), set(sel.get("entity_types") or [])
            hist: Counter[str] = Counter()
            interesting: list[tuple[str, str, float, float, float]] = []
            total = 0
            for e in doc.modelspace():
                if (types and e.dxftype() not in types) or (layers and e.dxf.layer not in layers):
                    continue
                if not hasattr(e.dxf, "start"):
                    continue
                s, t = e.dxf.start, e.dxf.end
                # ⭐ 按该视图自己的裁剪框筛，⛔ 否则每张图都会看到整个 modelspace
                if not (_in_box(s, box) and _in_box(t, box)):
                    continue
                total += 1
                bucket, major, minor, angle = _classify(abs(t[0] - s[0]), abs(t[1] - s[1]))
                hist[bucket] += 1
                if minor > 1e-6:
                    interesting.append((bucket, e.dxf.handle, major, minor, angle))
            print(f"  {view['id']}: 框内笔画 {total} 条")
            for bucket in BUCKETS:
                if hist[bucket]:
                    print(f"     {hist[bucket]:4d}  {bucket}")
            for bucket, handle, major, minor, angle in sorted(interesting, key=lambda r: -r[3]):
                print(f"        {handle}: 长 {major:9.3f} mm  偏移 {minor:.6f} mm"
                      f"  角度 {angle:.4f}°   [{bucket}]")
            grand.update(hist)
        print()
    print("=" * 74)
    for bucket in BUCKETS:
        if grand[bucket]:
            print(f"  {grand[bucket]:4d}  {bucket}")
    today = grand["tau_axis ~ 10mm 今天就吸附"]
    gap = grand["⭐ q ~ tau_axis(1mm) 缝里"]
    noise = grand["浮点噪声 <1e-6mm"] + grand["1e-6 ~ q(0.1mm)"]
    print()
    print(f"⇒ 入口卡改成 q(0.1mm) 后：吸附名单 {today} → {today + gap} 条（+{gap}）；")
    print(f"   而 {noise} 条噪声仍然不进分支（量化本来就会抹平它们）。")
    print(f"⇒ 若入口卡改成「只要不为零」：吸附名单会变成 {today + gap + noise} 条 "
          f"⇒ ⛔ 人签名单被噪声淹没。")


if __name__ == "__main__":
    main()
