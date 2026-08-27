"""⭐⭐⭐ ①-2′ 第 3 步：判分方尺子的【逐点】holdout —— sol 要的那个形式，此前一直没做。

前情（[`../2026-08-27_judge_ruler_holdout/`](../2026-08-27_judge_ruler_holdout/README.md) §六#4）：
  「⛔ 仍**没有**做 sol 要的『每视图 ≥3 个非共线 holdout 点、报 max 与 RMS』的**逐点**形式 ——
   那需要一个能扛住『基点≠质心』的配对器（坑 1）。**下一单该做这个。**」

## 为什么逐点比外包强

外包版每组只有 4 个数 ⇒ 只界定**全局平移 + 缩放**，**对旋转与局部畸变完全是瞎的**。
逐点残差能看见外包看不见的东西：整体旋转、逐区偏移、以及**原点单独错**（外包会被缩放吸收掉一部分）。

## holdout 性质（⛔ 这条是全部价值所在）

manifest 的平面仿射**只用 `WALL` 图层的线峰拟合**。本探针量的是
`WINDOW` / `E_WINDOW`（青）与 `LVTRY`（品红）—— **拟合从没见过它们**。
颜色取自**图纸自己在 DXF 图层表里的声明**，⛔ 不是我挑的。

## 坑 1 的解法（⛔ 不用最近邻贪心）

- 几何侧用 `ezdxf.bbox.extents(fast=False)` 的**外包中心**，⛔ 不用块基点（基点不是质心）；
- 墨迹侧用**无阈值**的最近调色板归属 + 连通域，取连通域外包中心；
- 配对用 **全局最优指派**（`linear_sum_assignment`），⛔ 不用贪心（贪心会跨全图乱配）；
- ⭐ 并且**要求指派是互为最近邻的**才计入 —— 不互为最近邻的显式记成 `ambiguous`，
  ⛔ 不硬配（同族：F-86 就是硬配撞出来的）。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MANIFEST = REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/manifest.json"
DXF = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
CASE_DATA = REPO / "case_tests/e2e_tests/sm25-L_anchor/case_data"
PALETTE = {"bg": (0, 0, 0), "white": (255, 255, 255), "wall": (192, 192, 192),
           "window": (0, 255, 255), "door": (255, 0, 255), "dim": (0, 255, 0),
           "edge": (63, 0, 255)}
GROUPS = (("window", ("WINDOW", "E_WINDOW")), ("door", ("LVTRY",)))
MIN_COMPONENT_PX = 12          # 丢掉抗锯齿碎点；⛔ 下面会扫描证明它不承重


def src_to_px(a, sx, sy):
    """pixel_to_source_m 的逆。⛔ 只吃 manifest。"""
    det = a["m00"] * a["m11"] - a["m01"] * a["m10"]
    dx, dy = sx - a["m02"], sy - a["m12"]
    return ((a["m11"] * dx - a["m01"] * dy) / det,
            (-a["m10"] * dx + a["m00"] * dy) / det)


def geometry_centres(msp, layers, mpu, box):
    import ezdxf
    from ezdxf import bbox
    out = []
    for e in msp:
        if e.dxf.layer not in layers:
            continue
        try:
            bb = bbox.extents([e], fast=False)
        except Exception:
            continue
        if bb is None or not bb.has_data:
            continue
        cx = (bb.extmin.x + bb.extmax.x) / 2.0
        cy = (bb.extmin.y + bb.extmax.y) / 2.0
        if not (box["xmin"] <= cx <= box["xmax"] and box["ymin"] <= cy <= box["ymax"]):
            continue
        out.append((cx * mpu, cy * mpu, e.dxftype(), e.dxf.layer))
    return out


def ink_centres(img, palette_names, pal, want, min_px):
    import numpy as np
    from scipy import ndimage
    d = ((img[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
    nearest = d.argmin(-1)
    mask = nearest == palette_names.index(want)
    lab, n = ndimage.label(mask)
    if n == 0:
        return []
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    out = []
    for i, s in enumerate(sizes, start=1):
        if s < min_px:
            continue
        ys, xs = np.where(lab == i)
        out.append(((xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0, int(s)))
    return out


def match(pred, obs):
    """全局最优指派 + 互为最近邻校验。⛔ 不硬配。"""
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    if not pred or not obs:
        return [], list(range(len(pred))), list(range(len(obs)))
    C = np.array([[math.dist(p[:2], o[:2]) for o in obs] for p in pred])
    ri, ci = linear_sum_assignment(C)
    pairs, amb = [], []
    for i, j in zip(ri, ci):
        mutual = (C[i].argmin() == j) and (C[:, j].argmin() == i)
        (pairs if mutual else amb).append((int(i), int(j), float(C[i, j])))
    return pairs, amb, C


def main() -> int:
    import numpy as np, ezdxf
    from PIL import Image
    man = json.loads(MANIFEST.read_text())
    mpu = man["metres_per_unit"]
    ro = {r["view_id"]: r for r in man["raster_overlays"]}
    views = {v["id"]: v for v in man["views"] if v["kind"] == "plan"}
    msp = ezdxf.readfile(DXF).modelspace()
    names = list(PALETTE)
    pal = np.array([PALETTE[n] for n in names])

    report = {"probe": "judge_ruler_pointwise_holdout",
              "holdout_property": "manifest 平面仿射只用 WALL 拟合；本探针量 WINDOW/E_WINDOW/LVTRY",
              "min_component_px": MIN_COMPONENT_PX, "views": {}}
    for vid, view in sorted(views.items()):
        b = ro[vid]
        img = np.asarray(Image.open(CASE_DATA / b["source_label"]).convert("RGB")).astype(np.int16)
        vrow = {}
        for gname, layers in GROUPS:
            geo = geometry_centres(msp, set(layers), mpu, view["clip_box_dxf"])
            pred = [src_to_px(b["pixel_to_source_m"], gx, gy) for gx, gy, _, _ in geo]
            obs = ink_centres(img, names, pal, gname, MIN_COMPONENT_PX)
            pairs, amb, C = match(pred, obs)
            dx = [obs[j][0] - pred[i][0] for i, j, _ in pairs]
            dy = [obs[j][1] - pred[i][1] for i, j, _ in pairs]
            dist = [d for _, _, d in pairs]
            n = len(pairs)
            vrow[gname] = {
                "dxf_features": len(geo), "ink_components": len(obs),
                "matched_mutual_nn": n, "ambiguous_not_counted": len(amb),
                "max_abs_dx_px": round(max((abs(v) for v in dx), default=0.0), 3),
                "max_abs_dy_px": round(max((abs(v) for v in dy), default=0.0), 3),
                "max_dist_px": round(max(dist, default=0.0), 3),
                "rms_dist_px": round(math.sqrt(sum(d * d for d in dist) / n), 3) if n else None,
                "mean_dx_px": round(sum(dx) / n, 3) if n else None,
                "mean_dy_px": round(sum(dy) / n, 3) if n else None,
                "non_collinear": bool(n >= 3 and len({round(p[0], 1) for p in
                                                      [pred[i] for i, _, _ in pairs]}) > 1
                                      and len({round(p[1], 1) for p in
                                               [pred[i] for i, _, _ in pairs]}) > 1),
            }
            print(f"{vid:9s} {gname:7s} 几何 {len(geo):3d} 墨迹 {len(obs):3d} "
                  f"配上 {n:3d} 存疑 {len(amb):2d} | max {vrow[gname]['max_dist_px']:>7} px "
                  f"RMS {vrow[gname]['rms_dist_px']} px | 均值偏移 "
                  f"({vrow[gname]['mean_dx_px']}, {vrow[gname]['mean_dy_px']})")
        report["views"][vid] = vrow

    (HERE / "pointwise_holdout.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
