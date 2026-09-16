"""Package a Voimatalo source candidate for offline visual review.

The package uses the candidate's recorded mesh frame.  It never fits or moves
the source model during packaging.  Observation directories are parameters so
the frozen 09-15 facade evidence and the new 09-16 roof observations can be
reviewed together without copying either input.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import runpy
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OLD = HERE.parent / "2026-09-15_voimatalo_developer_walkthrough"
DEFAULT_RAW_VIEWER = (
    ROOT / "case_tests/textured_mass/single_buildings/voimatalo/viewer.html"
)
sys.path.insert(0, str(ROOT))

from scripts.tool_scripts.render_geometry_viewer import build_viewer_html
from src.agent.geometry.mesh_bim_frame import render_mesh_bim_overlay


DEFAULT_VIEWS = [
    "top:F4", "street", "courtyard", "west:F4", "north:F6",
    "court_long", "court_short",
]
DEFAULT_ROOF_VIEWS = ["west", "north", "court_short", "south_box", "top"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_view(value: str) -> tuple[str, str | None]:
    name, separator, floor = value.partition(":")
    if not name or (separator and not floor):
        raise argparse.ArgumentTypeError("view must be NAME or NAME:FLOOR")
    return name, floor or None


def relative_href(target: Path, page_dir: Path) -> str:
    return Path(os.path.relpath(target.resolve(), page_dir.resolve())).as_posix()


def observation_card(
    *,
    source: dict,
    observation_dir: Path,
    name: str,
    floor_id: str | None,
    output_dir: Path,
    output_stem: str,
    caption_prefix: str,
) -> str:
    metadata_path = observation_dir / f"{name}.json"
    image_path = observation_dir / f"{name}.png"
    if not metadata_path.is_file() or not image_path.is_file():
        raise FileNotFoundError(
            f"observation pair missing for {name}: {metadata_path}, {image_path}"
        )
    observation = read_json(metadata_path)
    picture = Image.open(image_path)
    result, metadata = render_mesh_bim_overlay(
        picture, observation, source, floor_id=floor_id
    )
    result.save(output_dir / f"{output_stem}.png")
    (output_dir / f"{output_stem}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    floor_text = floor_id or "全部空间"
    caption = html.escape(f"{caption_prefix}{name} · {floor_text}")
    return (
        f'<figure><figcaption>{caption}</figcaption>'
        f'<a href="feedback/{output_stem}.png">'
        f'<img src="feedback/{output_stem}.png"></a></figure>'
    )


def source_section(source: dict, z: float, output_dir: Path) -> str:
    active = [
        space for space in source["spaces"]
        if float(space["z_floor"]) <= z
        < float(space["z_floor"]) + float(space["height"])
    ]
    all_points = np.asarray(
        [point for space in source["spaces"] for point in space["polygon"]], dtype=float
    )
    low = all_points.min(axis=0)
    high = all_points.max(axis=0)
    width, height = 900, 900
    margin = 70
    scale = min(
        (width - 2 * margin) / max(high[0] - low[0], 1e-9),
        (height - 2 * margin) / max(high[1] - low[1], 1e-9),
    )

    def point(value):
        return (
            margin + (float(value[0]) - low[0]) * scale,
            height - margin - (float(value[1]) - low[1]) * scale,
        )

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (25, 20),
        f"Actual source section z={z:g}m; continuous cores included; interior hypothesis",
        fill="black",
    )
    for space in active:
        role = str(space.get("role", ""))
        color = "#e0e9f0"
        if "vertical_circulation" in role or "CORE" in space["id"]:
            color = "#ddc7a7"
        elif "service" in role:
            color = "#c6d6b7"
        elif "annex" in role:
            color = "#ccd2e6"
        elif "roof" in role:
            color = "#d9cfdf"
        draw.polygon(
            [point(value) for value in space["polygon"]],
            fill=color,
            outline="#32495a",
            width=2,
        )
        label = Polygon(space["polygon"]).representative_point()
        draw.text(point([label.x, label.y]), space["id"], fill="black", anchor="mm")
    for opening in source["openings"]:
        vertices = np.asarray(opening["vertices"], dtype=float)
        if vertices[:, 2].min() <= z <= vertices[:, 2].max():
            endpoints = np.unique(np.round(vertices[:, :2], 10), axis=0)
            if len(endpoints) == 2:
                color = "#159066" if opening["kind"] == "window" else "#d46823"
                draw.line([point(value) for value in endpoints], fill=color, width=4)
    stem = f"section_{z:g}"
    image.save(output_dir / f"{stem}.png")
    (output_dir / f"{stem}.json").write_text(
        json.dumps(
            {
                "source_model_sha256": source["source_model_sha256"],
                "z_m": z,
                "space_ids": [space["id"] for space in active],
                "scope": (
                    "Derived section of actual source volumes; no added floor/slab objects; "
                    "not original-plan evidence"
                ),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return (
        f'<figure><figcaption>源模型水平剖切 z={z:g}m，包含实际相交的跨层空间</figcaption>'
        f'<a href="feedback/{stem}.png"><img src="feedback/{stem}.png"></a></figure>'
    )


def default_section_heights(source: dict) -> list[float]:
    heights = [2.8, 10.4, 26.3]
    roof_midpoints = []
    for space in source["spaces"]:
        role = str(space.get("role", "")).lower()
        if "roof" in role or str(space.get("floor_id", "")).upper().startswith("ROOF"):
            roof_midpoints.append(
                float(space["z_floor"]) + float(space["height"]) / 2
            )
    heights.extend(sorted(set(round(value, 6) for value in roof_midpoints)))
    return list(dict.fromkeys(heights))


def build_overlay_viewer(source: dict, display: dict, raw_viewer: Path) -> str:
    frame = source["mesh_frame"]
    extension_path = (
        ROOT
        / "AI_agent/logs/experiments/2026-09-14_voimatalo_transfer_setup/package_result.py"
    )
    extension = runpy.run_path(str(extension_path))["EXTENSION"]
    extension = extension.replace(
        "Math.PI/12", f'Math.PI*({frame["yaw_degrees"]})/180'
    )
    tx, ty, tz = frame["translation_m"]
    extension = extension.replace(
        "aligned[i]=ca*rp[i]+sa*rp[i+2]",
        f"aligned[i]=ca*rp[i]+sa*rp[i+2]+({tx})",
    ).replace(
        "aligned[i+1]=sa*rp[i]-ca*rp[i+2]",
        f"aligned[i+1]=sa*rp[i]-ca*rp[i+2]+({ty})",
    ).replace(
        "aligned[i+2]=rp[i+1]", f"aligned[i+2]=rp[i+1]+({tz})"
    )
    original = raw_viewer.read_text(encoding="utf-8")
    raw = json.loads(original.split("const data=", 1)[1].split(";\nfunction bytes", 1)[0])
    page = build_viewer_html(
        display, title="Voimatalo · 开发示范修订（内部为假设）"
    )
    anchor = (
        "  (function loop(){ requestAnimationFrame(loop); controls.update(); "
        "renderer.render(scene,camera); })();"
    )
    if page.count(anchor) != 1:
        raise ValueError("viewer animation anchor changed")
    page = page.replace(
        anchor, extension.replace("__RAW__", json.dumps(raw, separators=(",", ":"))) + anchor
    )
    buttons = (
        '<aside style="position:fixed;left:33%;top:10px;z-index:200;'
        'background:#fffe;padding:9px">'
        + "".join(
            f'<button data-transfer-mode="{key}">{label}</button>'
            for key, label in [
                ("bim", "实际BIM"),
                ("input", "原始纹理"),
                ("overlay", "按记录坐标叠合"),
            ]
        )
        + "</aside>"
    )
    return (
        page.replace("row('floors',BASES.length)", "row('基准标高组',BASES.length)")
        .replace("<body>", "<body>" + buttons, 1)
        .replace("label('N','#d32f2f'", "label('y (local)','#d32f2f'")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=HERE / "candidate_03")
    parser.add_argument("--out", type=Path, default=HERE / "result_03")
    parser.add_argument(
        "--observations", type=Path, default=OLD / "evidence_01",
        help="directory containing the frozen primary NAME.json/NAME.png pairs",
    )
    parser.add_argument(
        "--view", action="append", type=parse_view,
        help="primary observation NAME or NAME:FLOOR; repeat to replace defaults",
    )
    parser.add_argument(
        "--roof-observations", type=Path, default=HERE / "roof",
        help="directory containing new roof NAME.json/NAME.png pairs and sections.png",
    )
    parser.add_argument(
        "--roof-view", action="append",
        help="roof observation name; repeat to replace defaults",
    )
    parser.add_argument(
        "--section-z", action="append", type=float,
        help="source-model section height; repeat to replace automatic set",
    )
    parser.add_argument("--raw-viewer", type=Path, default=DEFAULT_RAW_VIEWER)
    args = parser.parse_args()

    candidate = args.candidate.resolve()
    output = args.out.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    for filename in ["source_model.json", "display_geometry.json", "report.json"]:
        if not (candidate / filename).is_file():
            raise FileNotFoundError(candidate / filename)
    output.mkdir(parents=True)
    feedback = output / "feedback"
    feedback.mkdir()

    source = read_json(candidate / "source_model.json")
    display = read_json(candidate / "display_geometry.json")
    primary_views = args.view or [parse_view(value) for value in DEFAULT_VIEWS]
    roof_views = args.roof_view or DEFAULT_ROOF_VIEWS
    cards = []
    for name, floor_id in primary_views:
        cards.append(
            observation_card(
                source=source,
                observation_dir=args.observations.resolve(),
                name=name,
                floor_id=floor_id,
                output_dir=feedback,
                output_stem=f"primary_{name}",
                caption_prefix="原主观察 · ",
            )
        )
    for name in roof_views:
        cards.append(
            observation_card(
                source=source,
                observation_dir=args.roof_observations.resolve(),
                name=name,
                floor_id=None,
                output_dir=feedback,
                output_stem=f"roof_{name}",
                caption_prefix="新屋顶观察 · ",
            )
        )

    raw_roof_cards = []
    roof_sections = args.roof_observations.resolve() / "sections.png"
    if roof_sections.is_file():
        shutil.copy2(roof_sections, feedback / "roof_raw_sections.png")
        raw_roof_cards.append(
            '<figure><figcaption>原网格屋顶六高度剖切（诊断切片，不是楼板）</figcaption>'
            '<a href="feedback/roof_raw_sections.png">'
            '<img src="feedback/roof_raw_sections.png"></a></figure>'
        )

    section_heights = args.section_z or default_section_heights(source)
    section_cards = [source_section(source, z, feedback) for z in section_heights]
    (output / "overlay.html").write_text(
        build_overlay_viewer(source, display, args.raw_viewer.resolve()), encoding="utf-8"
    )

    style = (
        "<style>body{font:16px/1.6 system-ui;margin:24px;color:#233b4c}"
        "a{color:#116b7a}main{display:grid;grid-template-columns:"
        "repeat(auto-fit,minmax(360px,1fr));gap:16px}figure{margin:0;"
        "border:1px solid #cdd5dc;padding:10px}img{width:100%}iframe{width:100%;"
        "height:800px;border:1px solid #cdd5dc}</style>"
    )
    (output / "observations.html").write_text(
        '<!doctype html><html lang="zh"><meta charset="utf-8">'
        "<title>开发助手实际源反馈</title>" + style
        + "<h1>原网格上的实际源叠图</h1>"
        + "<p>紫色为源墙边，绿色为窗，橙色为门。源线穿透显示；扫描缺面不代表真实透空。"
        + "这些是开发生成后的检查，不是工作模型收到的答案。</p><main>"
        + "".join(cards) + "</main><h2>屋顶原网格高度证据</h2><main>"
        + "".join(raw_roof_cards)
        + "</main><h2>候选源模型水平剖切</h2>"
        + "<p>内部为假设；跨层核心按实际空间相交显示，没有添加中间楼板。</p><main>"
        + "".join(section_cards) + "</main></html>",
        encoding="utf-8",
    )

    counts = {
        "spaces": len(source["spaces"]),
        "windows": sum(row["kind"] == "window" for row in source["openings"]),
        "doors": sum(row["kind"] == "door" for row in source["openings"]),
        "connections": len(source["connections"]),
    }
    notes = "".join(
        "<li>" + html.escape(note) + "</li>"
        for note in source.get("generation", {}).get("unresolved", [])
    )
    source_href = relative_href(candidate / "source_model.json", output)
    report_href = relative_href(candidate / "report.json", output)
    experiment_href = relative_href(HERE / "README.md", output)
    main_storeys = sum(
        floor["id"].startswith("F") and floor["id"][1:].isdigit()
        for floor in source["floors"]
    )
    (output / "index.html").write_text(
        f'<!doctype html><html lang="zh"><meta charset="utf-8">'
        f"<title>Voimatalo 开发示范修订</title>{style}"
        "<h1>Voimatalo · 开发助手的部分推理修订</h1>"
        "<p>原单体网格＋建筑声明，经开发助手观察、量测和确定性装配。"
        "这不是工作模型成绩；内部布局和门仍是方案假设。</p>"
        f"<p>{main_storeys}个主楼楼层 · {counts['spaces']}个空间体 · "
        f"{counts['windows']}组窗 · {counts['doors']}处门。</p>"
        '<p><a href="overlay.html">打开旋转查看</a> · '
        '<a href="observations.html">原网格叠图与水平剖切</a> · '
        f'<a href="{html.escape(source_href)}">源BIM</a> · '
        f'<a href="{html.escape(report_href)}">源检查</a> · '
        f'<a href="{html.escape(experiment_href)}">方法和范围</a></p>'
        '<iframe src="overlay.html" title="原网格/BIM/叠合"></iframe>'
        f"<h2>仍需说明的范围</h2><ul>{notes}</ul></html>",
        encoding="utf-8",
    )
    packaging = {
        "schema": "voimatalo_candidate_package_v2",
        "candidate": str(candidate),
        "source_model_sha256": source["source_model_sha256"],
        "mesh_frame": source["mesh_frame"],
        "source_mutated": False,
        "fitted_during_packaging": False,
        "counts": counts,
        "inputs": {
            "primary_observations": str(args.observations.resolve()),
            "roof_observations": str(args.roof_observations.resolve()),
            "raw_viewer": str(args.raw_viewer.resolve()),
        },
        "primary_views": [
            {"name": name, "floor_id": floor_id} for name, floor_id in primary_views
        ],
        "roof_views": roof_views,
        "raster_overlays": len(cards),
        "raw_roof_section_images": len(raw_roof_cards),
        "height_sections": section_heights,
        "links": {
            "source_model": source_href,
            "report": report_href,
            "experiment_readme": experiment_href,
        },
    }
    (output / "packaging.json").write_text(
        json.dumps(packaging, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
