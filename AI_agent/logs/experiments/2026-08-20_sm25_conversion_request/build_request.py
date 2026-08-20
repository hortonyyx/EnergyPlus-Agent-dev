#!/usr/bin/env python3
"""确定性地生成 sm25-L 的天正转换请求（request_v3.json）。

⭐ 一切可从 DXF 机械导出的东西都在这里算，⛔ 不手抄坐标。
唯一需要「看图」的是六张光栅图的像素标定，本脚本用
「白色线投影峰值 <-> DXF 线位」自动对齐求解，并打印内点数/残差自证。
"""
from __future__ import annotations
import hashlib, itertools, json, sys
from pathlib import Path

import ezdxf
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from src.agent.judge.tarch_converter_schema import (          # noqa: E402
    TarchConversionRequestV1, compute_request_sha256)

DXF = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
CASE = REPO / "case_tests/e2e_tests/sm25-L_anchor/case_data"
MPU = 0.001
FLOOR_H = 3.6

FRAMES = {"plan-F1": "37B", "plan-F2": "380",
          "West_view": "382", "South_view": "384",
          "North_view": "386", "East_view": "388"}
PLAN_RASTER = {"plan-F1": "1f_view.png", "plan-F2": "2f_view.png"}
# 立面：(facade, 图名, F1 地坪线句柄, F2 楼层线句柄, 屋顶线句柄, 图名 TEXT 句柄, 沿墙 lo 端点)
ELEV = {
    "West_view":  ("West",  "西立面", "346", "345", "343", "383", "end"),
    "South_view": ("South", "南立面", "30A", "30C", "30D", "385", "start"),
    "North_view": ("North", "北立面", "324", "325", "326", "387", "start"),
    "East_view":  ("East",  "东立面", "331", "333", "335", "389", "start"),
}
ELEV_TITLE_MAP = {"东立面": "East", "北立面": "North", "南立面": "South", "西立面": "West"}
ZONE_COUNT = {"plan-F1": 14, "plan-F2": 15}   # 用户 2026-08-20 填的 testdata_prompt.json

WIN_BLOCK, DOOR_BLOCK = "$EWDLib$00000533", "$EWDLib$00000621"
WIN_OUTLINE = {"316", "317", "319", "31B"}     # 块内外框 4 条 LINE = 洞口
DOOR_OUTLINE = {"35E", "35F", "360", "361"}

doc = ezdxf.readfile(str(DXF))
msp = doc.modelspace()
ent = {e.dxf.handle: e for e in msp}


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frame_box(handle):
    pts = [tuple(p)[:2] for p in ent[handle].get_points()]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def wall_bbox(box):
    xs, ys = [], []
    for e in msp:
        if e.dxf.layer != "WALL" or e.dxftype() != "LINE":
            continue
        s, t = tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]
        if box[0] <= s[0] <= box[2] and box[1] <= s[1] <= box[3]:
            xs += [s[0], t[0]]; ys += [s[1], t[1]]
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------- #
# 像素标定
# --------------------------------------------------------------------------- #
def white_profile(png):
    a = np.array(Image.open(png).convert("RGB")).astype(int)
    mx, mn = a.max(2), a.min(2)
    white = (mx > 60) & ((mx - mn) < 50)
    return white


def peaks(prof, frac, min_abs=25):
    thr = max(min_abs, prof.max() * frac)
    idx = np.where(prof >= thr)[0]
    groups = []
    for i in idx:
        if groups and i - groups[-1][-1] <= 2:
            groups[-1].append(i)
        else:
            groups.append([i])
    return [float(np.average(g, weights=prof[g])) for g in groups]


def dxf_line_positions(box, layers, min_len=400.0):
    xs, ys = [], []
    for e in msp:
        if e.dxf.layer not in layers or e.dxftype() != "LINE":
            continue
        s, t = tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]
        if not (box[0] <= s[0] <= box[2] and box[1] <= s[1] <= box[3]):
            continue
        dx, dy = t[0] - s[0], t[1] - s[1]
        if abs(dx) < 1e-6 and abs(dy) >= min_len:
            xs.append(round(s[0], 2))
        elif abs(dy) < 1e-6 and abs(dx) >= min_len:
            ys.append(round(s[1], 2))
    return sorted(set(xs)), sorted(set(ys))


def _lstsq_uniform(pairs_x, pairs_y):
    """解 col = x*s + ox ; row = -y*s + oy （统一尺度 s）。"""
    A, b = [], []
    for d, p in pairs_x:
        A.append([d, 1.0, 0.0]); b.append(p)
    for d, p in pairs_y:
        A.append([-d, 0.0, 1.0]); b.append(p)
    sol, *_ = np.linalg.lstsq(np.array(A, float), np.array(b, float), rcond=None)
    s, ox, oy = sol
    resid = ([abs(d * s + ox - p) for d, p in pairs_x]
             + [abs(-d * s + oy - p) for d, p in pairs_y])
    return float(s), float(ox), float(oy), resid


def calibrate_plan(view_id, box):
    """平面：墙线多，用 RANSAC 粗对齐再统一尺度精修。"""
    white = white_profile(CASE / PLAN_RASTER[view_id])
    cols, rows = peaks(white.sum(0), 0.06), peaks(white.sum(1), 0.06)
    xs, ys = dxf_line_positions(box, {"WALL"})

    def ransac(dv, pv, positive, tol=2.0):
        best = (0, None, None); pa = np.array(sorted(pv))
        for d0, d1 in itertools.combinations(sorted(dv), 2):
            if abs(d1 - d0) < 1500:
                continue
            for p0, p1 in itertools.combinations(sorted(pv), 2):
                if abs(p1 - p0) < 50:
                    continue
                scale = (p1 - p0) / (d1 - d0) if positive else (p0 - p1) / (d1 - d0)
                off = (p0 - d0 * scale) if positive else (p1 - d0 * scale)
                if not (0.01 <= abs(scale) <= 0.25):
                    continue
                if (scale < 0) if positive else (scale > 0):
                    continue
                pred = np.array(sorted(dv)) * scale + off
                inl = int(sum(1 for q in pred if np.min(np.abs(pa - q)) <= tol))
                if inl > best[0]:
                    best = (inl, scale, off)
        return best

    _, sx, ox = ransac(xs, cols, True)
    _, sy, oy = ransac(ys, rows, False)
    ca, ra = np.array(sorted(cols)), np.array(sorted(rows))
    px = [(d, float(ca[np.argmin(abs(ca - (d * sx + ox)))])) for d in xs
          if abs(ca[np.argmin(abs(ca - (d * sx + ox)))] - (d * sx + ox)) <= 2.5]
    py = [(d, float(ra[np.argmin(abs(ra - (d * sy + oy)))])) for d in ys
          if abs(ra[np.argmin(abs(ra - (d * sy + oy)))] - (d * sy + oy)) <= 2.5]
    s, ox2, oy2, resid = _lstsq_uniform(px, py)
    return s, ox2, oy2, len(px) + len(py), max(resid), white.shape


def calibrate_elevation(view_id, box):
    """立面：轮廓/楼层线是全高全宽的强峰，恰好 3 竖 3 横，按序对齐。"""
    white = white_profile(CASE / f"{view_id}.png")
    cols, rows = peaks(white.sum(0), 0.5), peaks(white.sum(1), 0.5)
    xs, ys = dxf_line_positions(box, {"AXIS_TEXT"})
    if len(cols) != len(xs) or len(rows) != len(ys):
        raise SystemExit(f"{view_id}: 强峰数 {len(cols)}/{len(rows)} 与 DXF 线数 "
                         f"{len(xs)}/{len(ys)} 不符，标定假设不成立")
    pairs_x = list(zip(sorted(xs), sorted(cols)))              # x 增大 -> 列增大
    pairs_y = list(zip(sorted(ys), sorted(rows, reverse=True)))  # y 增大 -> 行减小
    s, ox, oy, resid = _lstsq_uniform(pairs_x, pairs_y)
    return s, ox, oy, len(pairs_x) + len(pairs_y), max(resid), white.shape


def raster_overlay(view_id, calib, controls):
    s, ox, oy = calib[0], calib[1], calib[2]
    return {
        "id": f"raster_{view_id}",
        "source_label": PLAN_RASTER.get(view_id, f"{view_id}.png"),
        "source_sha256": sha256(CASE / PLAN_RASTER.get(view_id, f"{view_id}.png")),
        "view_id": view_id,
        "pixel_to_source_m": {"m00": MPU / s, "m01": 0.0, "m02": -ox * MPU / s,
                              "m10": 0.0, "m11": -MPU / s, "m12": oy * MPU / s},
        "calibration_controls": controls,
    }


def to_pixel(calib, x, y):
    s, ox, oy = calib[0], calib[1], calib[2]
    return [x * s + ox, -y * s + oy]


# --------------------------------------------------------------------------- #
def main() -> int:
    boxes = {vid: frame_box(h) for vid, h in FRAMES.items()}
    calib, overlays = {}, []
    print("=== 像素标定（内点数 / 最大残差 即自证）===")
    for vid in FRAMES:
        if vid.startswith("plan"):
            calib[vid] = calibrate_plan(vid, boxes[vid])
        else:
            calib[vid] = calibrate_elevation(vid, boxes[vid])
        s, ox, oy, n, mr, shape = calib[vid]
        print(f"  {vid:11s} s={s:.6f} px/mm  ox={ox:9.3f} oy={oy:8.3f}  "
              f"用点 {n:2d}  最大残差 {mr:5.2f}px  (1px≈{1/s:.1f}mm)  img {shape[1]}x{shape[0]}")

    dialect = {
        "window_block_names": ["$TCHSYS$WIN2D"],
        "door_block_prefixes": ["$DorLib2D$"],
        "classifier_version": "tarch-dialect-v1",
        "elevation_title_map": ELEV_TITLE_MAP,
        "elevation_door_block_rules": [],
    }

    plan_views = []
    for vid, floor_id in (("plan-F1", "F1"), ("plan-F2", "F2")):
        box = boxes[vid]
        wx0, wy0, wx1, wy1 = wall_bbox(box)
        n = ZONE_COUNT[vid]
        plan_views.append({
            "id": vid, "floor_id": floor_id,
            "frame_title": "1f平面图" if floor_id == "F1" else "2f平面图",
            "clip_box_dxf": {"xmin": box[0], "ymin": box[1], "xmax": box[2], "ymax": box[3]},
            "world_from_source_m": {"m00": MPU, "m01": 0.0, "m02": -wx0 * MPU,
                                    "m10": 0.0, "m11": MPU, "m12": -wy0 * MPU},
            "wall_selector": {"entity_types": ["LINE"], "layers": ["WALL"]},
            "opening_selector": {"entity_types": ["INSERT"], "layers": ["WINDOW"]},
            "room_label_selector": None,
            "dialect_rules": dialect,
            "zone_intent": {"mode": "intent_file", "expected_count": n,
                            "entries": [{"zone_id": f"z{i}", "name": f"r{i}",
                                         "role": "unspecified"} for i in range(n)]},
            "void_intent": [],
        })
        # 平面光栅控制点 = footprint 外包框三角
        pts = {"footprint_sw": (wx0, wy0), "footprint_se": (wx1, wy0), "footprint_nw": (wx0, wy1)}
        overlays.append(raster_overlay(vid, calib[vid], [
            {"entity_handle": FRAMES[vid], "source_point_dxf": [px, py],
             "pixel_point": to_pixel(calib[vid], px, py), "role": role}
            for role, (px, py) in pts.items()]))

    elevation_views = []
    for vid, (facade, title, d1, d2, roof, title_h, lo_end) in ELEV.items():
        box = boxes[vid]
        line = ent[d1]
        a0 = tuple(line.dxf.start)[:2]; a1 = tuple(line.dxf.end)[:2]
        lo_pt, hi_pt = (a0, a1) if lo_end == "start" else (a1, a0)
        span = 25.0 if facade in ("North", "South") else 20.0
        scale = span / ((hi_pt[0] - lo_pt[0]))      # 沿墙：源 x -> 世界 [0, span]
        offset = -lo_pt[0] * scale
        z_scale = MPU
        z_offset = 0.0 - tuple(line.dxf.start)[1] * z_scale
        elevation_views.append({
            "intent_version": 3, "intent_kind": "named_datum_bound", "id": vid,
            "binding_source": "named_title", "frame_title": title,
            "frame_entity_handle": FRAMES[vid], "title_entity_handle": title_h,
            "floor_ids": ["F1", "F2"], "facade_family": facade,
            "clip_box_dxf": {"xmin": box[0], "ymin": box[1], "xmax": box[2], "ymax": box[3]},
            "world_along_from_source_m": {"source_axis": "x", "scale": scale, "offset": offset},
            "world_z_from_source_m": {"source_axis": "y", "scale": z_scale, "offset": z_offset},
            "floor_datums": [
                {"floor_id": "F1", "entity_handle": d1, "datum_kind": "floor_line",
                 "world_along_lo_source_endpoint": lo_end},
                {"floor_id": "F2", "entity_handle": d2, "datum_kind": "floor_line",
                 "world_along_lo_source_endpoint": lo_end}],
            "window_selector": {"entity_types": ["INSERT", "LWPOLYLINE"], "layers": ["E_WINDOW"]},
            "door_selector": {"entity_types": ["INSERT"], "layers": ["E_WINDOW"]},
            "view_kind": "full", "segment_scope_mode": "all_family_segments",
        })
        roof_line = ent[roof]
        off_pt = tuple(roof_line.dxf.start)[:2]
        overlays.append(raster_overlay(vid, calib[vid], [
            {"entity_handle": d1, "source_point_dxf": list(lo_pt),
             "pixel_point": to_pixel(calib[vid], *lo_pt), "role": "datum_lo"},
            {"entity_handle": d1, "source_point_dxf": list(hi_pt),
             "pixel_point": to_pixel(calib[vid], *hi_pt), "role": "datum_hi"},
            {"entity_handle": roof, "source_point_dxf": list(off_pt),
             "pixel_point": to_pixel(calib[vid], *off_pt), "role": "off_datum"}]))

    def block_roles(all_handles, outline):
        return [{"entity_handle": h,
                 "role": "structural_outline" if h in outline else "nonstructural_detail"}
                for h in all_handles]

    win_handles = [e.dxf.handle for e in doc.blocks.get(WIN_BLOCK)]
    door_handles = [e.dxf.handle for e in doc.blocks.get(DOOR_BLOCK)]
    from src.agent.judge.tarch_normalize import elevation_block_definition_sha256
    carriers = [
        {"carrier_id": "sm25.window.polyline", "opening_kind": "window",
         "match": {"entity_type": "LWPOLYLINE", "layers": ["E_WINDOW"]},
         "outline": {"kind": "closed_polyline_rect"}},
        {"carrier_id": "sm25.window.block", "opening_kind": "window",
         "match": {"entity_type": "INSERT", "layers": ["E_WINDOW"],
                   "block_name_exact": WIN_BLOCK,
                   "block_definition_sha256": elevation_block_definition_sha256(doc, WIN_BLOCK)},
         "outline": {"kind": "block_entity_rect",
                     "block_entity_roles": block_roles(win_handles, WIN_OUTLINE)}},
        {"carrier_id": "sm25.door.block", "opening_kind": "door",
         "match": {"entity_type": "INSERT", "layers": ["E_WINDOW"],
                   "block_name_exact": DOOR_BLOCK,
                   "block_definition_sha256": elevation_block_definition_sha256(doc, DOOR_BLOCK)},
         "outline": {"kind": "block_entity_rect",
                     "block_entity_roles": block_roles(door_handles, DOOR_OUTLINE)},
         "module_union_strategy": "touching_rect_union",
         "module_union_min_gap_m": 0.5},
    ]

    payload = {
        "request_version": 3, "case": "sm25-L_anchor",
        "source_dxf_label": "sm25-L_t3.dxf", "source_dxf_sha256": sha256(DXF),
        "normalized_source_id": "sm25-l-anchor-normalized",
        "target_geometry_profile": "c2_simple_orthogonal_no_holes",
        "native_units": "unitless", "metres_per_unit": MPU,
        "wall_thickness_range_m": [0.06, 0.5], "min_room_area_m2": 2.0,
        "floors": [{"id": "F1", "name": "1F", "z_floor_m": 0.0, "ceiling_height_m": FLOOR_H},
                   {"id": "F2", "name": "2F", "z_floor_m": FLOOR_H, "ceiling_height_m": FLOOR_H}],
        "plan_views": plan_views,
        "elevation_views": elevation_views,
        "opening_carrier_rules": carriers,
        "ignore_selector": [],
        "north_axis": None,
        "raster_overlays": overlays,
        "label_role_map": {},
        "overrides": [],
        "critical_dimensions": [],
        "request_sha256": "0" * 64,
    }
    request = TarchConversionRequestV1.model_validate(payload)
    payload["request_sha256"] = compute_request_sha256(request)
    request = TarchConversionRequestV1.model_validate(payload)

    out = Path(__file__).with_name("request_v3.json")
    out.write_text(json.dumps(request.model_dump(mode="json"), indent=1,
                              ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\n✅ schema 通过；request_sha256={request.request_sha256}")
    print(f"   写出 {out.relative_to(REPO)}  ({out.stat().st_size} 字节)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
