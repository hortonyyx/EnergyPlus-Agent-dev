#!/usr/bin/env python3
"""Render replayable close views for Voimatalo opening completion.

This development aid reads only the original single-building GLB plus the
frozen 2026-09-15 observation metadata.  It does not edit either input.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageOps


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT / "AI_agent/logs/experiments/2026-09-15_voimatalo_developer_walkthrough"
sys.path.insert(0, str(ROOT))

from src.agent.geometry.mesh_observation import MeshObservation


MESH = ROOT / "case_tests/textured_mass/single_buildings/voimatalo/input.glb"

# Pixel intervals are developer readings of visible mullion/bay edges in the
# new close west view.  They are converted to metres from the saved camera,
# rather than being typed as metric coordinates.
GROUND_WEST_WINDOWS = [
    ("GW01", 91, 170),
    ("GW02", 184, 267),
    ("GW03", 281, 365),
    ("GW04", 379, 462),
    ("GW05", 478, 560),
    ("GW06", 575, 658),
    ("GW07", 674, 756),
    ("GW08", 771, 850),
    ("GW09", 867, 965),
    ("GW10", 1055, 1135),
    ("GW11", 1148, 1233),
    ("GW12", 1247, 1335),
]


def camera_box_interval(metadata: dict, box: list[int], axis: int) -> tuple[list[float], list[float]]:
    """Convert exclusive pixel-box edges to metric horizontal and Z intervals."""
    mapping = metadata["pixel_center_mapping"]
    origin = mapping["top_left_pixel_center_plane_xyz"]
    dx = mapping["column_step_world_xyz"]
    dy = mapping["row_step_world_xyz"]
    left, top, right, bottom = box
    a = [origin[i] + (left - 0.5) * dx[i] + (top - 0.5) * dy[i] for i in range(3)]
    b = [origin[i] + (right - 0.5) * dx[i] + (bottom - 0.5) * dy[i] for i in range(3)]
    return sorted([round(a[axis], 5), round(b[axis], 5)]), sorted(
        [round(a[2], 5), round(b[2], 5)]
    )


def annotate_ground() -> None:
    image = Image.open(HERE / "ground_west_bright.png").convert("RGB")
    draw = ImageDraw.Draw(image)
    for opening_id, left, right in GROUND_WEST_WINDOWS:
        draw.rectangle((left, 97, right, 369), outline=(40, 230, 80), width=3)
        draw.text((left + 2, 101), opening_id, fill=(40, 230, 80))
    draw.rectangle((1009, 232, 1045, 389), outline=(30, 220, 240), width=4)
    draw.text((1011, 234), "D_entry_west", fill=(30, 220, 240))
    draw.rectangle((1352, 97, 1435, 369), outline=(255, 165, 0), width=4)
    draw.text((1354, 101), "unknown bay", fill=(255, 165, 0))
    image.save(HERE / "ground_west_annotated.png")


def annotate_exception_views(unresolved: list[dict], row_boxes: dict[str, dict[str, list[int]]]) -> None:
    colors = {
        "add": (40, 230, 80),
        "infer": (30, 220, 240),
        "exclude": (235, 50, 50),
        "unknown": (255, 165, 0),
    }
    dispositions = {
        "west_corner_large": "add",
        "north_right_large_01": "add",
        "north_right_large_02": "add",
        "court_long_right_partial": "add",
        "court_long_back_wall_exposure": "exclude",
        "court_long_middle_dark_recess": "unknown",
        "court_short_back_wall_exposure": "exclude",
        "court_short_R05_G03_partial": "infer",
        "court_short_R06_G03_partial": "infer",
    }
    by_view: dict[str, list[dict]] = {}
    for item in unresolved:
        by_view.setdefault(item["view"], []).append(item)
    for view, items in by_view.items():
        image = Image.open(OLD / "evidence_01" / f"{view}.png").convert("RGB")
        draw = ImageDraw.Draw(image)
        for item in items:
            boxes = row_boxes.get(item["id"], {"observed": item["pixel_box"]})
            color = colors[dispositions[item["id"]]]
            for row_id, box in boxes.items():
                left, top, right, bottom = box
                draw.rectangle((left, top, right, bottom), outline=color, width=3)
                draw.text((left + 2, top + 2), f"{item['id']}:{row_id}", fill=color)
        image.save(HERE / f"exceptions_{view}.png")
    details = {
        "west": (970, 165, 1140, 525),
        "north": (790, 280, 1045, 850),
        "court_long": (130, 270, 1135, 735),
        "court_short": (430, 520, 710, 940),
    }
    for view, crop in details.items():
        source = Image.open(OLD / "evidence_01" / f"{view}.png").convert("RGB")
        detail = source.crop(crop)
        scale = min(4.0, 1500 / detail.width)
        detail.resize((round(detail.width * scale), round(detail.height * scale))).save(
            HERE / f"exception_detail_{view}.png"
        )


def main() -> None:
    mesh = MeshObservation(MESH)
    yaw = json.loads((OLD / "evidence_01/direction.json").read_text())["used_yaw_degrees"]
    operations = [
        {
            "name": "ground_west",
            "eye": [-100, -3, 3.2],
            "target": [0, -3, 3.2],
            "width_m": 66,
            "height_m": 7.5,
            "width_px": 1500,
            "height_px": 420,
            "bounds": [[-16, -36, -1], [-10, 27, 7]],
        },
        {
            "name": "ground_north",
            "eye": [2, 100, 3.2],
            "target": [2, 0, 3.2],
            "width_m": 40,
            "height_m": 7.5,
            "width_px": 1500,
            "height_px": 420,
            "bounds": [[-16, 23, -1], [21, 29, 7]],
        },
        {
            "name": "ground_court_long",
            "eye": [100, -12, 3.2],
            "target": [0, -12, 3.2],
            "width_m": 47,
            "height_m": 7.5,
            "width_px": 1500,
            "height_px": 420,
            "bounds": [[-2, -36, -1], [3, 10.5, 7]],
        },
        {
            "name": "ground_court_short",
            "eye": [10, -100, 3.2],
            "target": [10, 10, 3.2],
            "width_m": 25,
            "height_m": 7.5,
            "width_px": 1400,
            "height_px": 420,
            "bounds": [[0, 6, -1], [21, 12, 7]],
        },
    ]
    summaries = []
    for operation in operations:
        args = {key: value for key, value in operation.items() if key != "name"}
        _, metadata = mesh.render(HERE / operation["name"], yaw_degrees=yaw, **args)
        if operation["name"] == "ground_west":
            raw = ImageOps.autocontrast(_, cutoff=0.5)
            bright = ImageEnhance.Brightness(raw).enhance(1.45)
            bright.save(HERE / "ground_west_bright.png")
            for index, (left, right) in enumerate(((60, 560), (500, 1050), (980, 1480)), 1):
                bright.crop((left, 35, right, 385)).resize((1200, 840)).save(
                    HERE / f"ground_west_detail_{index}.png"
                )
        summaries.append(
            {
                "name": operation["name"],
                "camera": metadata["camera"],
                "view_span_m": metadata["view_span_m"],
                "resolution_px": metadata["resolution_px"],
                "selection_bounds": metadata["selection_bounds"],
                "visible_pixel_count": metadata["rasterizer"]["visible_pixel_count"],
            }
        )
    (HERE / "operations.json").write_text(
        json.dumps(
            {
                "mode": "development_assistant_opening_completion",
                "mesh_sha256": mesh.mesh_sha256,
                "yaw_degrees": yaw,
                "operations": operations,
                "summaries": summaries,
                "caveat": (
                    "Bounds select triangle centroids to isolate a facade. Missing or clipped "
                    "pixels are not evidence that the physical wall or opening is absent."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    ground_meta = json.loads((HERE / "ground_west.json").read_text())
    old_meta = {
        view: json.loads((OLD / "evidence_01" / f"{view}.json").read_text())
        for view in ("west", "north", "court_long", "court_short")
    }
    unresolved = json.loads(
        (OLD / "aperture_observations/unresolved_observations.json").read_text()
    )
    unresolved_by_id = {item["id"]: item for item in unresolved}
    old_assembly = json.loads((OLD / "assembly_observations.json").read_text())["openings"]
    old_assembly_by_id = {item["id"]: item for item in old_assembly}
    source = json.loads((OLD / "candidate_02/source_model.json").read_text())
    source_openings = {item["id"]: item for item in source["openings"]}

    # Use the already accepted row bands for Z.  Only the horizontal exception
    # span is newly interpreted, which avoids allowing a warped texture box to
    # cross the estimated slab levels.
    row_boxes: dict[str, dict[str, list[int]]] = {
        "west_corner_large": {},
        "north_right_large_01": {},
        "north_right_large_02": {},
        "court_long_right_partial": {},
        "court_short_R05_G03_partial": {
            "R05": unresolved_by_id["court_short_R05_G03_partial"]["pixel_box"]
        },
        "court_short_R06_G03_partial": {
            "R06": unresolved_by_id["court_short_R06_G03_partial"]["pixel_box"]
        },
    }
    reference_group = {
        "west_corner_large": ("west", "G15"),
        "north_right_large_01": ("north", "G08"),
        "north_right_large_02": ("north", "G08"),
        "court_long_right_partial": ("court_long", "G08"),
    }
    true_vertical_boxes = {
        # Translate the original exception box itself by the visible row pitch.
        # Do not shrink these nonstandard windows to the standard-window height.
        "west_corner_large": {
            "R01": [189, 239], "R02": [243, 293], "R03": [297, 347],
            "R04": [351, 401], "R05": [405, 455], "R06": [459, 509],
        },
        "north_right_large_01": {
            "R01": [314, 379], "R02": [403, 468], "R03": [492, 557],
            "R04": [580, 645], "R05": [668, 733], "R06": [756, 821],
        },
        "north_right_large_02": {
            "R01": [314, 379], "R02": [403, 468], "R03": [492, 557],
            "R04": [580, 645], "R05": [668, 733], "R06": [756, 821],
        },
    }
    for exception_id, (view, group) in reference_group.items():
        horizontal = unresolved_by_id[exception_id]["pixel_box"]
        for row_id in ("R01", "R02", "R03", "R04", "R05", "R06"):
            reference = old_assembly_by_id[f"{view}_{row_id}_{group}"]
            vertical = true_vertical_boxes.get(exception_id, {}).get(
                row_id, reference["pixel_box"][1:4:2]
            )
            row_boxes[exception_id][row_id] = [
                horizontal[0],
                vertical[0],
                horizontal[2],
                vertical[1],
            ]

    additions: list[dict] = []

    def add_repeated_exception(
        exception_id: str,
        view: str,
        group: str,
        suffix: str,
        evidence_status: str,
    ) -> None:
        axis = {"west": 1, "north": 0, "court_long": 1}[view]
        for row_id, box in row_boxes[exception_id].items():
            reference_id = f"{view}_{row_id}_{group}"
            reference = old_assembly_by_id[reference_id]
            host = source_openings[reference_id]
            span, observed_z = camera_box_interval(old_meta[view], box, axis)
            points = [
                [(box[0] + box[2]) // 2, (box[1] + box[3]) // 2],
                [box[0] + 3, (box[1] + box[3]) // 2],
                [box[2] - 4, (box[1] + box[3]) // 2],
            ]
            query = mesh.pixel_query(OLD / "evidence_01" / view, points)
            additions.append(
                {
                    "id": f"{view}_{row_id}_{suffix}",
                    "operation": "add",
                    "kind": "window",
                    "view": view,
                    "plane_key": view,
                    "observation_row": row_id,
                    "source_group": suffix,
                    "pixel_box": box,
                    "pixel_box_convention": "left/top inclusive; right/bottom exclusive",
                    "span_m": span,
                    "z_m": observed_z,
                    "basis": (
                        "开发辅助：例外组在原纹理中逐层重复；水平边缘与完整高度均按例外框，"
                        "米制坐标由冻结相机换算，不按标准窗或假设楼板裁短。"
                    ),
                    "notes": unresolved_by_id[exception_id]["notes"],
                    "visibility": "partial" if reference.get("visibility") == "partial" else evidence_status,
                    "source_exception_id": exception_id,
                    "source_refs": [
                        f"../2026-09-15_voimatalo_developer_walkthrough/evidence_01/{view}.png",
                        f"exceptions_{view}.png",
                    ],
                    "space_id": host["space_ids"][0],
                    "host_boundary_id": host["host_boundary_id"],
                    "face_hit_query": query,
                }
            )

    add_repeated_exception("west_corner_large", "west", "G15", "corner_large", "clear_nonstandard")
    add_repeated_exception("north_right_large_01", "north", "G08", "right_large_01", "clear_nonstandard")
    add_repeated_exception("north_right_large_02", "north", "G08", "right_large_02", "clear_nonstandard")
    add_repeated_exception("court_long_right_partial", "court_long", "G08", "right_partial", "edge_partial")

    # The two court-short fragments align exactly with the complete G03 groups
    # above and with neighbouring G01/G02 rows.  Complete their width as an
    # explicitly inferred rectangle.  R06 also infers its missing lower edge
    # from the complete vertical pitch and retains observed/inferred subranges.
    for row_id in ("R05", "R06"):
        exception_id = f"court_short_{row_id}_G03_partial"
        reference_id = f"court_short_{row_id}_G02"
        reference = old_assembly_by_id[reference_id]
        host = source_openings[reference_id]
        box = unresolved_by_id[exception_id]["pixel_box"]
        span, _ = camera_box_interval(old_meta["court_short"], box, 0)
        query = mesh.pixel_query(
            OLD / "evidence_01/court_short",
            [[(box[0] + box[2]) // 2, (box[1] + box[3]) // 2], [box[0] + 3, (box[1] + box[3]) // 2], [box[2] - 4, (box[1] + box[3]) // 2]],
        )
        opening_suffix = "G03_completed" if row_id == "R05" else "G03_inferred_complete"
        observed_z = list(reference["z_m"])
        assembly_z = list(observed_z)
        inferred_extension = None
        if row_id == "R06":
            assembly_z[0] = round(9.875 - 3.166667, 6)
            inferred_extension = [assembly_z[0], observed_z[0]]
        additions.append(
            {
                "id": f"court_short_{row_id}_{opening_suffix}",
                "operation": "add",
                "kind": "window",
                "view": "court_short",
                "plane_key": "court_short",
                "observation_row": row_id,
                "source_group": opening_suffix,
                "pixel_box": box,
                "pixel_box_convention": "left/top inclusive; right/bottom exclusive",
                "span_m": span,
                "z_m": assembly_z,
                "observed_visible_z_m": observed_z,
                "inferred_vertical_extension_z_m": inferred_extension,
                "basis": (
                    "部分推理：原网格保留左侧窗片；G03在上四排完整，且本排G01/G02保持同一节奏。"
                    "补全缺面后的G03宽度；R05高度完整。R06下沿按R05下沿减同列完整排距"
                    "3.166667m推到6.708333m，可见段与推断延伸分别保留。"
                ),
                "notes": unresolved_by_id[exception_id]["notes"],
                "visibility": (
                    "inferred_full_width_from_visible_fragment_and_vertical_repetition"
                    if row_id == "R05"
                    else "inferred_full_width_and_lower_extent_from_vertical_repetition"
                ),
                "source_exception_id": exception_id,
                "source_refs": [
                    "../2026-09-15_voimatalo_developer_walkthrough/evidence_01/court_short.png",
                    "exceptions_court_short.png",
                ],
                "space_id": host["space_ids"][0],
                "host_boundary_id": host["host_boundary_id"],
                "face_hit_query": query,
            }
        )

    # Ground-floor west storefront: record only clear glazed bays.  The far
    # right bay remains semantically unresolved and is deliberately omitted.
    for opening_id, left, right in GROUND_WEST_WINDOWS:
        span, observed_z = camera_box_interval(ground_meta, [left, 97, right, 369], 1)
        query_points = [
            [(left + right) // 2, 150],
            [(left + right) // 2, 240],
            [left + 3, 205],
            [right - 4, 205],
        ]
        additions.append(
            {
                "id": f"ground_west_{opening_id}",
                "operation": "add",
                "kind": "window",
                "opening_type": "storefront_glazing_group",
                "view": "west",
                "plane_key": "west",
                "observation_row": "GROUND",
                "source_group": opening_id,
                "pixel_box": [left, 97, right, 369],
                "pixel_box_convention": "left/top inclusive; right/bottom exclusive",
                "span_m": span,
                "observed_visible_z_band_m": observed_z,
                "z_m": [0.35, 5.2],
                "basis": (
                    "开发辅助：新首层近视图可见连续店面玻璃及竖梃；按清楚的主竖梃分组，"
                    "不细拆窗扇。高度在估计F1层内保守规整，地面坡度和门槛仍未知。"
                ),
                "notes": "原纹理支持玻璃店面组；不据模糊反射判断窗扇或商业单元边界。",
                "visibility": "clear_storefront_glazing_simplified",
                "source_refs": ["ground_west.png", "ground_west_annotated.png"],
                "space_id": "F1_open",
                "host_boundary_id": "space/F1_open/wall/13",
                "face_hit_query": mesh.pixel_query(HERE / "ground_west", query_points),
            }
        )

    door_query = mesh.pixel_query(
        HERE / "ground_west", [[1027, 255], [1027, 320], [1013, 285], [1040, 285]]
    )
    door_action = {
        "id": "D_entry_west",
        "operation": "replace_metadata_keep_geometry",
        "kind": "door",
        "opening_type": "probable_glazed_storefront_door",
        "space_id": "F1_open",
        "host_boundary_id": "space/F1_open/wall/13",
        "plane_key": "west",
        "span_m": [-16.0, -14.4],
        "z_m": [0.0, 2.8],
        "decision": (
            "保留原几何。该跨度落在独立窄门扇/把手样竖带，不再只写无图假设；"
            "门的开启方式、准确门槛和是否为主入口仍未知。"
        ),
        "source_refs": ["ground_west.png", "ground_west_annotated.png"],
        "face_hit_query": door_query,
    }

    disposition_by_id = {
        "west_corner_large": "build_as_six_repeated_nonstandard_windows",
        "north_right_large_01": "build_as_six_repeated_nonstandard_windows",
        "north_right_large_02": "build_as_six_repeated_nonstandard_windows",
        "court_long_right_partial": "build_visible_corner_span_for_six_rows_without_width_extension",
        "court_long_back_wall_exposure": "exclude_not_on_host_facade",
        "court_long_middle_dark_recess": "remain_unknown_recess_or_opening_no_window_class",
        "court_short_back_wall_exposure": "exclude_not_on_host_facade",
        "court_short_R05_G03_partial": "build_full_width_by_explicit_vertical_repetition_inference",
        "court_short_R06_G03_partial": "build_full_width_and_lower_extent_by_explicit_vertical_repetition_inference",
    }
    decisions = []
    for item in unresolved:
        decisions.append(
            {
                **item,
                "decision": disposition_by_id[item["id"]],
                "generated_opening_ids": [
                    row["id"] for row in additions if row.get("source_exception_id") == item["id"]
                ],
                "reason": {
                    "court_long_back_wall_exposure": "五点均命中X约-13.4m后墙，与宿主X=0.8m相差约14m。",
                    "court_short_back_wall_exposure": "五点均命中Y约25.9m北墙，与宿主Y=8.8m相差约17m。",
                    "court_long_middle_dark_recess": "命中近侧表面但形态为跨层暗槽，原图不能区分凹槽、开敞或玻璃。",
                }.get(item["id"], "原纹理重复关系、邻组节奏与面命中共同支持所列处理；推断项另有显式标记。"),
            }
        )

    annotate_ground()
    annotate_exception_views(unresolved, row_boxes)
    (HERE / "assembly_windows.json").write_text(
        json.dumps(
            {
                "schema": "voimatalo_opening_additions_v1",
                "openings": additions,
                "count": len(additions),
                "count_interpretation": {
                    "complete_rectangles": len(additions),
                    "with_explicit_vertical_inference": 1,
                    "vertically_inferred_id": "court_short_R06_G03_inferred_complete",
                },
                "candidate_base": "2026-09-15 developer candidate_02",
                "note": (
                    "Append to frozen assembly observations only after replacing the estimated storey levels as recorded "
                    "in validation.json; true west exception heights intentionally fail the old level hosts."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    (HERE / "opening_actions.json").write_text(
        json.dumps(
            {
                "schema": "voimatalo_opening_completion_actions_v1",
                "mesh_sha256": mesh.mesh_sha256,
                "window_additions_file": "assembly_windows.json",
                "door_actions": [door_action],
                "original_nine_exception_decisions": decisions,
                "remaining_unknowns": [
                    {
                        "id": "court_short_R06_G01_G02_old_partial_lower_extents",
                        "host_boundary_id": "space/F2_open/wall/10",
                        "known_existing_fragments": [
                            "court_short_R06_G01, Z[7.025,8.545]m",
                            "court_short_R06_G02, Z[7.025,8.545]m"
                        ],
                        "reason": "本轮只为新增G03显式推断完整下沿；旧G01/G02仍是可见高度，未统一延伸，不能宣传该排或全楼窗完整。",
                    },
                    {
                        "id": "ground_west_far_right_bay",
                        "host_boundary_id": "space/F1_open/wall/13",
                        "approx_span_m": [-33.16, -29.49],
                        "reason": "深色大面与上部亮牌并存，原纹理不足以区分橱窗、车库门或实墙饰面。",
                    },
                    {
                        "id": "ground_north_and_courtyard",
                        "reason": "新近视图在Z<约6.7m主要为裁剪空洞、后墙或低体遮挡，没有足够宿主面支持首层窗门。",
                    },
                    {
                        "id": "ground_thresholds_and_door_classes",
                        "reason": "街面地面锯齿且纹理模糊；除D_entry_west外，不强行把竖梃间玻璃分类为门。",
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
