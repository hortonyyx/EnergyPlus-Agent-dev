"""⭐ 逐点 holdout v2 —— ⛔ v1 又踩了「拿整个块去配它的一个碎片」这个坑。

v1 读数：31 扇窗 ↔ **49** 个墨块、13 樘门 ↔ **155** 个墨块 ⇒ 一个门窗符号在图上
本来就是**若干条分离的线**，把「整块的几何中心」去配「某一个碎片的中心」，
残差自然是 8–15 px，而**均值偏移接近零**（0.6 / −1.5）恰恰说明尺子没偏、是我配错了。
同族 [[proxy-mistaken-for-the-thing]]（这是本项目第 N 次栽在同一个形状上）。

## v2 的做法：**先预测框、再就地取墨**，⛔ 不做全局配对

对每个 DXF 特征：几何外包 → 用 manifest 仿射映射成像素框 → **把框按 f 膨胀** →
在框内取该颜色的墨 → 算墨的**质心**与**外包中心** → 与预测中心比。

⭐ **为什么这不是循环论证**：框是**膨胀过的**（默认 f=1.8，窗约 46 px ⇒ 余量 ~18 px 每边），
远大于待测残差；仿射若真错了 >18 px，框里会**取不到墨或只取到半边**，
⇒ 报出来的 `ink_capture` 与「墨是否居中」会直接把它暴露。
⛔ 并且 f 会被**扫描**，证明结论不随它走（本项目硬纪律 §五#3）。

⛔ **仍然量不到的**：墨迹外包/质心 ≠ 几何外包，差约半个线宽 ⇒ 本方法分辨率仍在 ~0.5 px。
正确读法是「**在本方法分辨率下与完美无法区分**」。
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
DILATIONS = (1.4, 1.8, 2.4, 3.0)      # ⭐ 采样窗，扫描证明它不承重
ISO_F = 3.0                           # 隔离半径，**固定**：一次只动一个变量


def src_to_px(a, sx, sy):
    det = a["m00"] * a["m11"] - a["m01"] * a["m10"]
    dx, dy = sx - a["m02"], sy - a["m12"]
    return ((a["m11"] * dx - a["m01"] * dy) / det,
            (-a["m10"] * dx + a["m00"] * dy) / det)


def feature_boxes(msp, layers, mpu, box, aff):
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
        if not (box["xmin"] <= (bb.extmin.x + bb.extmax.x) / 2 <= box["xmax"]
                and box["ymin"] <= (bb.extmin.y + bb.extmax.y) / 2 <= box["ymax"]):
            continue
        c = [src_to_px(aff, bb.extmin.x * mpu, bb.extmin.y * mpu),
             src_to_px(aff, bb.extmax.x * mpu, bb.extmax.y * mpu)]
        x0, x1 = sorted((c[0][0], c[1][0]))
        y0, y1 = sorted((c[0][1], c[1][1]))
        out.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1,
                    "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2, "type": e.dxftype()})
    return out


def main() -> int:
    import numpy as np, ezdxf
    from PIL import Image
    man = json.loads(MANIFEST.read_text())
    mpu = man["metres_per_unit"]
    ro = {r["view_id"]: r for r in man["raster_overlays"]}
    views = {v["id"]: v for v in man["views"] if v["kind"] == "plan"}
    msp = ezdxf.readfile(DXF).modelspace()
    names, pal = list(PALETTE), np.array(list(PALETTE.values()))

    report = {"probe": "judge_ruler_pointwise_holdout_v2",
              "holdout_property": "manifest 平面仿射只用 WALL 拟合；量的是 WINDOW/E_WINDOW/LVTRY",
              "resolution_floor_note": "墨迹中心 ≠ 几何中心，差约半线宽 ⇒ 分辨率 ~0.5 px",
              "dilation_sweep": {}, "views": {}}
    masks_cache = {}
    for vid, view in sorted(views.items()):
        b = ro[vid]
        img = np.asarray(Image.open(CASE_DATA / b["source_label"]).convert("RGB")).astype(np.int16)
        nearest = ((img[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1).argmin(-1)
        masks_cache[vid] = {g: (nearest == names.index(g)) for g, _ in GROUPS}
        H, W = nearest.shape
        vrow = {}
        for gname, layers in GROUPS:
            boxes = feature_boxes(msp, set(layers), mpu, view["clip_box_dxf"],
                                  b["pixel_to_source_m"])
            mask = masks_cache[vid][gname]
            per_f = {}
            for f in DILATIONS:
                ds, empty = [], 0
                dxs, dys, caps, pts, edge_err = [], [], [], [], []
                # ⭐ 隔离筛：只量「邻域里没有别的同色特征」的点。
                # ⛔ 不筛的话，沿墙密排的窗会把邻居的墨吃进框里 —— 那量的是拥挤程度，不是尺子。
                # ⚠️ **隔离半径固定为 ISO_F，⛔ 不跟着 f 走** —— 第一版让两者同用 f，
                #    于是每个 f 下入选集合都不同 = 一次动了两个变量，扫描读数因此不可比
                #    （f=1.8 那行 max 33 px、而 1.4/2.4/3.0 都 ≤0.97 px，正是这么来的）。
                kept = []
                for bx in boxes:
                    hw = max((bx["x1"] - bx["x0"]) / 2 * ISO_F, 6.0)
                    hh = max((bx["y1"] - bx["y0"]) / 2 * ISO_F, 6.0)
                    clash = any(o is not bx
                                and o["x0"] <= bx["cx"] + hw and o["x1"] >= bx["cx"] - hw
                                and o["y0"] <= bx["cy"] + hh and o["y1"] >= bx["cy"] - hh
                                for o in boxes)
                    if not clash:
                        kept.append(bx)
                for bx in kept:
                    hw = max((bx["x1"] - bx["x0"]) / 2 * f, 6.0)
                    hh = max((bx["y1"] - bx["y0"]) / 2 * f, 6.0)
                    c0, c1 = int(max(0, bx["cx"] - hw)), int(min(W, bx["cx"] + hw + 1))
                    r0, r1 = int(max(0, bx["cy"] - hh)), int(min(H, bx["cy"] + hh + 1))
                    sub = mask[r0:r1, c0:c1]
                    tot = int(sub.sum())
                    if tot < 8:
                        empty += 1
                        continue
                    ys, xs = np.nonzero(sub)
                    # ⭐⭐ 比【外包对外包】，⛔ 不比质心：门的弧线 symbol 墨偏在一侧，
                    # 「几何外包中心 vs 墨迹质心」是两个不同的量，比它们量的是符号形状不是尺子。
                    # （这正是外包法当初能到 0.66 px、而我的质心版到 5 px 的原因。）
                    il, ir = xs.min() + c0, xs.max() + c0
                    it, ib = ys.min() + r0, ys.max() + r0
                    e = [il - bx["x0"], ir - bx["x1"], it - bx["y0"], ib - bx["y1"]]
                    edge_err.extend(e)
                    dx, dy = (e[0] + e[1]) / 2, (e[2] + e[3]) / 2
                    ds.append(math.hypot(dx, dy)); dxs.append(dx); dys.append(dy)
                    caps.append(tot); pts.append((round(bx["cx"], 1), round(bx["cy"], 1),
                                                  round(dx, 3), round(dy, 3)))
                n = len(ds)
                per_f[str(f)] = {
                    "features": len(boxes), "isolated": len(kept), "measured": n,
                    "no_ink_in_box": empty,
                    "points_cx_cy_dx_dy": pts if f == DILATIONS[1] else None,
                    "max_dist_px": round(max(ds, default=0.0), 3),
                    "rms_dist_px": round(math.sqrt(sum(d * d for d in ds) / n), 3) if n else None,
                    "mean_dx_px": round(sum(dxs) / n, 3) if n else None,
                    "mean_dy_px": round(sum(dys) / n, 3) if n else None,
                    "median_ink_px_in_box": int(np.median(caps)) if caps else 0,
                    # ⭐ 逐特征、逐边的残差（每个特征 4 条边）—— 这才是同类比同类
                    "edges_n": len(edge_err),
                    "edge_max_abs_px": round(max((abs(v) for v in edge_err), default=0.0), 3),
                    "edge_rms_px": (round(math.sqrt(sum(v * v for v in edge_err) / len(edge_err)), 3)
                                    if edge_err else None),
                    "edge_mean_px": (round(sum(edge_err) / len(edge_err), 3)
                                     if edge_err else None),
                }
            vrow[gname] = per_f
            base = per_f[str(DILATIONS[1])]
            print(f"{vid:9s} {gname:7s} 特征 {base['features']:3d} 隔离 {base['isolated']:3d} 量到 {base['measured']:3d} "
                  f"| ⭐逐边 n={base['edges_n']:3d} max {base['edge_max_abs_px']:>6} px  "
                  f"RMS {base['edge_rms_px']:>6} px  偏置 {base['edge_mean_px']:>6} px")
        report["views"][vid] = vrow

    # ⭐ 扫描对账：结论随不随膨胀系数走
    sweep = {}
    for f in DILATIONS:
        allmax = [report["views"][v][g][str(f)]["edge_max_abs_px"]
                  for v in report["views"] for g, _ in GROUPS]
        allrms = [report["views"][v][g][str(f)]["edge_rms_px"]
                  for v in report["views"] for g, _ in GROUPS
                  if report["views"][v][g][str(f)]["edge_rms_px"] is not None]
        sweep[str(f)] = {"max_over_all_groups_px": round(max(allmax), 3),
                         "worst_rms_px": round(max(allrms), 3)}
    report["dilation_sweep"] = sweep
    print("\n=== 膨胀系数扫描（证明它不承重）===")
    for f, s in sweep.items():
        print(f"  f={f:4s}  全组 max {s['max_over_all_groups_px']:>6} px   最差 RMS {s['worst_rms_px']:>6} px")
    (HERE / "pointwise_holdout_v2.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
