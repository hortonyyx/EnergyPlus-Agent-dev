#!/usr/bin/env python3
"""Replay developer-assisted standard-window observations for Voimatalo.

Only the four frozen PNG/JSON/NPZ observation triplets in evidence_01 are read.
Horizontal groups and visible row bands are developer visual judgements. Metric
conversion, local contrast, pixel hits, face IDs and wall-depth checks are code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent / "evidence_01"

# Boxes are [left, top, right, bottom], right/bottom exclusive. R01 is the
# highest visible standard row, not an asserted building floor number.
ROWS: dict[str, list[dict[str, Any]]] = {
    "west": [
        {"id": "R01", "vertical": [198, 230]},
        {"id": "R02", "vertical": [252, 284]},
        {"id": "R03", "vertical": [306, 339]},
        {"id": "R04", "vertical": [360, 394], "representative": True},
        {"id": "R05", "vertical": [414, 447]},
        {"id": "R06", "vertical": [468, 501]},
    ],
    "north": [
        {"id": "R01", "vertical": [323, 375]},
        {"id": "R02", "vertical": [412, 464], "representative": True},
        {"id": "R03", "vertical": [501, 554]},
        {"id": "R04", "vertical": [589, 642]},
        {"id": "R05", "vertical": [677, 730]},
        {"id": "R06", "vertical": [765, 798], "partial": True,
         "note": "下沿网格开始破碎；只保留仍命中北墙的可见部分，不外推完整窗高。"},
    ],
    "court_long": [
        {"id": "R01", "vertical": [299, 342]},
        {"id": "R02", "vertical": [379, 423]},
        {"id": "R03", "vertical": [459, 503]},
        {"id": "R04", "vertical": [539, 583], "representative": True},
        {"id": "R05", "vertical": [619, 664]},
        {"id": "R06", "vertical": [699, 720], "partial": True,
         "note": "长墙下排被前方低体屋面遮住下沿；只记录遮挡前仍可见的窗纹理。"},
    ],
    "court_short": [
        {"id": "R01", "vertical": [367, 425]},
        {"id": "R02", "vertical": [467, 525]},
        {"id": "R03", "vertical": [567, 625], "representative": True},
        {"id": "R04", "vertical": [667, 725]},
        {"id": "R05", "vertical": [767, 825]},
        {"id": "R06", "vertical": [867, 915], "partial": True,
         "note": "最下排靠近破碎网格边缘；可见高度短于上五排，不补画缺失下沿。"},
    ],
}

GROUPS: dict[str, list[dict[str, Any]]] = {
    "west": [
        {"id": "G01", "horizontal": [118, 162]},
        {"id": "G02", "horizontal": [174, 215]},
        {"id": "G03", "horizontal": [228, 269]},
        {"id": "G04", "horizontal": [282, 321]},
        {"id": "G05", "horizontal": [337, 374]},
        {"id": "G06", "horizontal": [389, 428]},
        {"id": "G07", "horizontal": [443, 481]},
        {"id": "G08", "horizontal": [496, 534]},
        {"id": "G09", "horizontal": [548, 589]},
        {"id": "G10", "horizontal": [602, 642]},
        {"id": "G11", "horizontal": [654, 694]},
        {"id": "G12", "horizontal": [709, 747]},
        {"id": "G13", "horizontal": [762, 802]},
        {"id": "G14", "horizontal": [817, 856]},
        {"id": "G15", "horizontal": [871, 911]},
    ],
    "north": [
        {"id": "G01", "horizontal": [140, 204]},
        {"id": "G02", "horizontal": [227, 292]},
        {"id": "G03", "horizontal": [315, 381]},
        {"id": "G04", "horizontal": [404, 471]},
        {"id": "G05", "horizontal": [492, 560]},
        {"id": "G06", "horizontal": [580, 648]},
        {"id": "G07", "horizontal": [668, 736]},
        {"id": "G08", "horizontal": [756, 824]},
    ],
    "court_long": [
        {"id": "S01", "horizontal": [39, 94],
         "plane_key": "court_long_south_segment",
         "note": "同向但与主长墙不连续的南端墙片。"},
        {"id": "S02", "horizontal": [108, 141],
         "plane_key": "court_long_south_segment",
         "note": "较窄窗组；右侧约x=169起的暗带是后墙透出，不是第三组窗。"},
        {"id": "G01", "horizontal": [425, 490]},
        {"id": "G02", "horizontal": [502, 567]},
        {"id": "G03", "horizontal": [579, 645]},
        {"id": "G04", "horizontal": [658, 724]},
        {"id": "G05", "horizontal": [737, 804]},
        {"id": "G06", "horizontal": [817, 882]},
        {"id": "G07", "horizontal": [895, 961]},
        {"id": "G08", "horizontal": [974, 1039]},
    ],
    "court_short": [
        {"id": "C01", "horizontal": [111, 173],
         "plane_key": "court_corner_y",
         "note": "左侧台阶墙窗组；墙深约y=9.6m，与右侧主短墙约y=8.9m分开。"},
        {"id": "G01", "horizontal": [274, 352]},
        {"id": "G02", "horizontal": [372, 450]},
        {"id": "G03", "horizontal": [469, 551], "exclude_rows": ["R05", "R06"],
         "note": "R05/R06右缘网格缺失并露出后墙，两排残窗另列未决观察。"},
    ],
}

DEFAULT_PLANE = {"west": "west_main", "north": "north_main",
                 "court_long": "court_long_main", "court_short": "court_short_main"}

# Medians of representative-row visible-surface hits, with enough tolerance for
# mesh wobble but far less than the >10 m gap to accidentally exposed back walls.
PLANE_DEPTH = {
    "west_main": {"axis": "x", "expected_m": -13.69, "tolerance_m": 0.45},
    "north_main": {"axis": "y", "expected_m": 26.12, "tolerance_m": 0.55},
    "court_long_main": {"axis": "x", "expected_m": 0.72, "tolerance_m": 0.45},
    "court_long_south_segment": {"axis": "x", "expected_m": 0.76, "tolerance_m": 0.45},
    "court_short_main": {"axis": "y", "expected_m": 8.91, "tolerance_m": 0.45},
    "court_corner_y": {"axis": "y", "expected_m": 9.63, "tolerance_m": 0.45},
}

UNRESOLVED = [
    {"id": "west_corner_large", "view": "west", "plane_key": "west_corner_warped",
     "pixel_box": [1028, 351, 1103, 401], "status": "visible_nonstandard_unresolved",
     "notes": "右端逐层大暗窗/凹槽清楚可见，但代表排更高更宽且表面中心比主墙前移约0.5m；不套用15组标准窗。",
     "repeat_rows": ["R01", "R02", "R03", "R04", "R05", "R06"]},
    {"id": "north_right_large_01", "view": "north", "plane_key": "north_main_warped_texture",
     "pixel_box": [838, 403, 906, 468], "status": "visible_nonstandard_unresolved",
     "notes": "右端较大且纹理扭曲的窗区；中心仍命中北墙深度，但边界不足以按标准组建模。",
     "repeat_rows": ["R01", "R02", "R03", "R04", "R05", "R06"]},
    {"id": "north_right_large_02", "view": "north", "plane_key": "north_main_warped_texture",
     "pixel_box": [908, 403, 996, 468], "status": "visible_nonstandard_unresolved",
     "notes": "最右大窗区；可见且命中北墙，但组间边界/宽度受扭曲影响，暂不规则化。",
     "repeat_rows": ["R01", "R02", "R03", "R04", "R05", "R06"]},
    {"id": "court_long_right_partial", "view": "court_long", "plane_key": "court_long_main",
     "pixel_box": [1054, 539, 1106, 583], "status": "visible_edge_partial_unresolved",
     "notes": "主长墙右端还能看到一组窗，但观察裁边/缺面截掉右缘；不据残宽推完整宽度。",
     "repeat_rows": ["R01", "R02", "R03", "R04", "R05", "R06"]},
    {"id": "court_long_back_wall_exposure", "view": "court_long", "plane_key": "different_back_wall",
     "pixel_box": [169, 536, 321, 584], "status": "excluded_visible_back_wall",
     "notes": "暗带中心深度约x=-13.4m，而当前长墙约x=0.7m；这是缺面后露出的另一墙，不能当窗。"},
    {"id": "court_long_middle_dark_recess", "view": "court_long", "plane_key": "court_long_recess",
     "pixel_box": [321, 536, 407, 584], "status": "visible_nonstandard_unresolved",
     "notes": "中部竖向暗槽命中约x=0.7–1.0m的近侧表面，与左边透出的后墙不同；形态像凹槽/大开口，不按标准窗处理。",
     "repeat_rows": ["R01", "R02", "R03", "R04", "R05", "R06"]},
    {"id": "court_short_back_wall_exposure", "view": "court_short", "plane_key": "different_back_wall",
     "pixel_box": [575, 565, 685, 625], "status": "excluded_visible_back_wall",
     "notes": "主短墙右缘缺失后露出约y=25.9m的北墙，当前主墙约y=8.9m；暗区不是短墙大窗。"},
    {"id": "court_short_R05_G03_partial", "view": "court_short", "plane_key": "court_short_main",
     "pixel_box": [469, 767, 551, 825], "status": "visible_mesh_cut_partial_unresolved",
     "notes": "第五排第三组窗可见，但右侧及下侧缺面穿透到y约26.1m的后墙；不把矩形框全算作当前墙窗。"},
    {"id": "court_short_R06_G03_partial", "view": "court_short", "plane_key": "court_short_main",
     "pixel_box": [469, 867, 551, 915], "status": "visible_mesh_cut_partial_unresolved",
     "notes": "最下排第三组窗可见残片，右缘锯齿缺面穿透后墙；不推断完整矩形。"},
]


class PixelBuffer:
    def __init__(self, prefix: Path) -> None:
        self.meta = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
        with np.load(prefix.with_suffix(".npz"), allow_pickle=False) as data:
            self.shape = tuple(int(value) for value in data["image_shape"])
            self.indices = np.asarray(data["pixel_indices"], dtype=np.int64)
            self.points = np.asarray(data["world_points"], dtype=np.float64)
            self.faces = np.asarray(data["face_ids"], dtype=np.int64)
            mesh_sha256 = str(data["mesh_sha256"].item())
        if mesh_sha256 != self.meta["mesh_sha256"]:
            raise ValueError(f"mesh identity mismatch for {prefix}")

    def query(self, x: int, y: int) -> dict[str, Any]:
        height, width = self.shape
        if not (0 <= x < width and 0 <= y < height):
            return {"pixel": [x, y], "hit": False, "reason": "outside_image"}
        flat = y * width + x
        position = int(np.searchsorted(self.indices, flat))
        if position >= len(self.indices) or int(self.indices[position]) != flat:
            return {"pixel": [x, y], "hit": False, "reason": "background"}
        return {"pixel": [x, y], "hit": True,
                "world_xyz": self.points[position].tolist(),
                "face_id": int(self.faces[position])}


def box_samples(box: list[int]) -> list[list[int]]:
    left, top, right, bottom = box
    px = min(3, max(1, (right - left) // 8)); py = min(3, max(1, (bottom - top) // 8))
    return [[(left + right - 1) // 2, (top + bottom - 1) // 2],
            [left + px, (top + bottom - 1) // 2],
            [right - 1 - px, (top + bottom - 1) // 2],
            [(left + right - 1) // 2, top + py],
            [(left + right - 1) // 2, bottom - 1 - py]]


def metric_box(meta: dict[str, Any], box: list[int]) -> tuple[float, list[float]]:
    mapping = meta["pixel_center_mapping"]
    top_z = float(mapping["top_left_pixel_center_plane_xyz"][2])
    dz = float(mapping["row_step_world_xyz"][2])
    left, top, right, bottom = box
    za = top_z + (top - 0.5) * dz; zb = top_z + (bottom - 0.5) * dz
    return (right - left) * float(mapping["pixel_width_m"]), sorted([za, zb])


def hit_check(buffer: PixelBuffer, box: list[int], plane_key: str) -> dict[str, Any]:
    target = PLANE_DEPTH[plane_key]; axis_index = "xyz".index(target["axis"])
    queried = [buffer.query(x, y) for x, y in box_samples(box)]
    hits = [item for item in queried if item["hit"]]
    depths = [float(item["world_xyz"][axis_index]) for item in hits]
    deviation = max((abs(value - target["expected_m"]) for value in depths), default=None)
    return {"sample_pixels": [item["pixel"] for item in queried],
            "hit_count": len(hits), "sample_count": len(queried),
            "all_hit": len(hits) == len(queried), "depth_axis": target["axis"],
            "expected_wall_depth_m": target["expected_m"],
            "accepted_deviation_m": target["tolerance_m"],
            "depth_range_m": None if not depths else [min(depths), max(depths)],
            "max_abs_deviation_m": deviation,
            "target_wall_depth_pass": bool(len(hits) == len(queried) and deviation is not None
                                           and deviation <= target["tolerance_m"]),
            "face_ids": sorted({int(item["face_id"]) for item in hits})}


def contrast(rgb: np.ndarray, box: list[int]) -> dict[str, Any]:
    left, top, right, bottom = box
    grey = rgb[..., 0] * .2126 + rgb[..., 1] * .7152 + rgb[..., 2] * .0722
    ix = min(4, max(1, (right-left)//6)); iy = min(4, max(1, (bottom-top)//6))
    inside = grey[top+iy:bottom-iy, left+ix:right-ix]
    bands = [grey[max(0, top-5):top, left:right], grey[bottom:min(grey.shape[0], bottom+5), left:right]]
    around = np.concatenate([part.reshape(-1) for part in bands if part.size])
    inner = float(np.median(inside)); outer = float(np.median(around))
    return {"inside_luma_median": inner,
            "adjacent_horizontal_band_luma_median": outer,
            "surround_minus_inside_luma": outer-inner,
            "interpretation": "辅助局部对比值，不是把所有暗条判作窗的阈值。"}


def build(out_dir: Path) -> None:
    openings: list[dict[str, Any]] = []; summaries: dict[str, Any] = {}; annotated = {}
    font = ImageFont.load_default()
    for view in ROWS:
        prefix = EVIDENCE / view; buffer = PixelBuffer(prefix)
        source = Image.open(prefix.with_suffix(".png")).convert("RGB"); rgb = np.asarray(source)
        canvas = source.copy(); draw = ImageDraw.Draw(canvas)
        representative = next(row for row in ROWS[view] if row.get("representative"))
        row_summary = []
        for row in ROWS[view]:
            top, bottom = row["vertical"]; _, zm = metric_box(buffer.meta, [0, top, 1, bottom])
            row_summary.append({**row, "z_m": [round(v, 4) for v in zm]})
            colour = (255, 165, 0) if row.get("partial") else (80, 220, 255)
            draw.line((0, top, source.width-1, top), fill=colour, width=1)
            draw.line((0, bottom-1, source.width-1, bottom-1), fill=colour, width=1)
            draw.text((4, top+2), f"{row['id']} z={zm[0]:.2f}..{zm[1]:.2f}", fill=colour, font=font)
        for group in GROUPS[view]:
            plane = group.get("plane_key", DEFAULT_PLANE[view]); left, right = group["horizontal"]
            for row in ROWS[view]:
                if row["id"] in group.get("exclude_rows", []):
                    continue
                top, bottom = row["vertical"]; box = [left, top, right, bottom]
                span, zm = metric_box(buffer.meta, box)
                basis = ("开发辅助：原纹理代表排直接判读窗组边缘；像素缓冲确定性换算并核墙面深度。"
                         if row.get("representative") else
                         "开发辅助：该排视觉上重复代表排水平分组；垂直可见带逐排判读，像素缓冲确定性核验。")
                if row.get("partial"): basis += " 本排只记可见残段，不补全缺失窗高。"
                openings.append({"id": f"{view}_{row['id']}_{group['id']}", "view": view,
                    "plane_key": plane, "observation_row": row["id"], "source_group": group["id"],
                    "pixel_box": box, "pixel_box_convention": "left/top inclusive; right/bottom exclusive",
                    "span_m": round(span, 4), "z_m": [round(v, 4) for v in zm], "basis": basis,
                    "notes": " ".join(x for x in (group.get("note", ""), row.get("note", "")) if x),
                    "visibility": "partial" if row.get("partial") else "clear_standard",
                    "hit_check": hit_check(buffer, box, plane), "local_contrast": contrast(rgb, box)})
            top, bottom = representative["vertical"]
            colour = (20, 220, 255) if group.get("plane_key") else (60, 255, 60)
            draw.rectangle((left, top, right-1, bottom-1), outline=colour, width=2)
            draw.text((left+2, top+2), group["id"], fill=colour, font=font)
        summaries[view] = {"resolution_px": buffer.meta["resolution_px"],
            "pixel_center_mapping": buffer.meta["pixel_center_mapping"],
            "representative_row": representative["id"], "rows": row_summary,
            "groups": GROUPS[view],
            "opening_count": sum(item["view"] == view for item in openings)}
        annotated[view] = canvas

    unresolved = []
    for item in UNRESOLVED:
        view = item["view"]; buffer = PixelBuffer(EVIDENCE/view); box = item["pixel_box"]
        samples = [buffer.query(x, y) for x, y in box_samples(box)]; hits = [x for x in samples if x["hit"]]
        span, zm = metric_box(buffer.meta, box)
        unresolved.append({**item, "span_m": round(span, 4), "z_m": [round(v, 4) for v in zm],
            "hit_check": {"sample_pixels": [x["pixel"] for x in samples], "hit_count": len(hits),
                          "sample_count": len(samples), "world_xyz": [x.get("world_xyz") for x in samples],
                          "face_ids": [x.get("face_id") for x in samples]}})
        draw = ImageDraw.Draw(annotated[view]); left, top, right, bottom = box
        colour = (255,70,70) if item["status"].startswith("excluded") else (255,165,0)
        draw.rectangle((left,top,right-1,bottom-1), outline=colour, width=3)
        draw.text((left+2,top+2), item["id"], fill=colour, font=font)

    failures = [x["id"] for x in openings if not x["hit_check"]["target_wall_depth_pass"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir/"openings.json").write_text(json.dumps(openings,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out_dir/"observations.json").write_text(json.dumps({
        "scope":"four facade standard-row window groups only",
        "source_files":[f"evidence_01/{v}.{s}" for v in ROWS for s in ("png","json","npz")],
        "judgement":"horizontal groups and visible vertical bands are developer-assisted visual readings",
        "deterministic_support":"camera mapping, metric spans/Z, local luma contrast, pixel hit/face/depth checks",
        "box_convention":"[left, top, right, bottom], right/bottom exclusive", "views":summaries,
        "total_openings":len(openings), "depth_check_failures":failures,
        "caveat":"No ground-floor doors, roof windows, fine mullions or inferred completion of missing surfaces is included."
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out_dir/"unresolved_observations.json").write_text(json.dumps(unresolved,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for view,image in annotated.items(): image.save(out_dir/f"{view}_apertures.png")
    (out_dir/"verification.json").write_text(json.dumps({"opening_count":len(openings),
        "all_standard_samples_hit_expected_wall_depth":not failures,"failure_ids":failures,
        "unresolved_count":len(unresolved)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if failures: raise SystemExit(f"{len(failures)} opening depth checks failed; see verification.json")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--out",type=Path,default=HERE)
    build(parser.parse_args().out.resolve())


if __name__ == "__main__": main()
