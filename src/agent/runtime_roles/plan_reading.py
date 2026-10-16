"""Saved two-dimensional reading products; no source BIM or invented heights."""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString


def _bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def product_identity(receipt):
    """Both old BIM trials and current planar trials retain exact product hashes."""
    if receipt.get("reading_product_file"):
        return receipt["reading_product_file"], receipt["reading_product_sha256"]
    return f"{receipt['candidate']}/source_model.json", receipt.get("candidate_source_sha256")


def geometry_ready(receipt):
    return receipt.get("reading_geometry_ready", receipt.get("source_geometry_ready")) is True


def comparison_facts(product):
    """XY-only relation projection for the existing assembly fidelity comparison."""
    from shapely.geometry import Polygon
    metadata = product["mapping"]
    spaces = [{"id": row["space_id"], "floor_id": metadata["floor_id"], "polygon": row["world_polygon_m"]}
              for row in metadata["space_mapping"]]
    adjacency = []
    for i, first in enumerate(spaces):
        for second in spaces[i + 1:]:
            if Polygon(first["polygon"]).boundary.intersection(Polygon(second["polygon"]).boundary).length > 1e-7:
                adjacency.append({"space_ids": [first["id"], second["id"]]})
    return {"spaces": spaces, "boundary_relations": adjacency,
            "openings": [{"id": row["opening_id"], "kind": row["kind"], "space_ids": row["space_ids"],
                          "vertices": [row["p1_world_m"], row["p2_world_m"]], "exterior": row["exterior"]}
                         for row in metadata["opening_hosts"]]}


def _opening_overlaps(plan):
    rows = plan.get("openings", [])
    for index, first in enumerate(rows):
        a = LineString([first["p1"], first["p2"]])
        for second in rows[index + 1:]:
            if a.intersection(LineString([second["p1"], second["p2"]])).length > 1e-7:
                # A plan can explicitly describe vertically stacked apertures.
                az, bz = first.get("z"), second.get("z")
                if az and bz and min(az[1], bz[1]) <= max(az[0], bz[0]):
                    continue
                raise ValueError(f"overlapping plan openings {first['id']} and {second['id']}; "
                                 "resolve duplicate apertures or supply observed separate vertical intervals")


def _font(size=16):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _views(plan, metadata, original):
    """Render adopted coordinates through the original calibration, without refitting."""
    pictures = [original.convert("RGB"), Image.new("RGB", original.size, "white")]
    ring = plan["footprint_pixels"]
    for index, picture in enumerate(pictures):
        draw = ImageDraw.Draw(picture)
        wall = (15, 110, 195) if index == 0 else (42, 49, 61)
        def line(points, color, width):
            draw.line([tuple(p) for p in points], fill=color, width=width, joint="curve")
        line([*ring, ring[0]], wall, 3)
        for row in plan["partitions"]:
            line(row["points"], wall, 3)
        for row in plan["openings"]:
            color = (10, 167, 151) if row["kind"] == "window" else (214, 83, 32)
            line([row["p1"], row["p2"]], color, 5)
            if index:
                middle = [(a + b) / 2 for a, b in zip(row["p1"], row["p2"])]
                draw.text((middle[0] + 5, middle[1] + 4), row["id"], font=_font(13), fill=color)
        if index:
            for row in metadata["space_mapping"]:
                from shapely.geometry import Polygon
                p = Polygon(row["pixel_polygon"]).representative_point()
                draw.text((p.x, p.y), row["space_id"], font=_font(16), fill=(65, 65, 65), anchor="mm")
        # The anchor marker lies on its declared original pixel, never on a
        # freshly fitted ink bbox. This makes global calibration drift visible.
        for axis in ("x", "y"):
            for px, metres in plan[f"{axis}_anchors"]:
                if axis == "x":
                    draw.line([(px, 0), (px, picture.height)], fill=(205, 110, 180), width=1)
                    draw.text((px + 3, 12), f"x {px:g}px = {metres:g}m", font=_font(14), fill=(125, 30, 105))
                else:
                    draw.line([(0, px), (picture.width, px)], fill=(205, 110, 180), width=1)
                    draw.text((12, px + 3), f"y {px:g}px = {metres:g}m", font=_font(14), fill=(125, 30, 105))
    return pictures


def build_reading(plan, *, workspace, image_name, number):
    from src.agent.geometry.plan_partition import compile_plan_partition
    from src.agent.geometry.reader_wall_metadata import validate_wall_metadata
    workspace = Path(workspace)
    image_path = workspace / "images" / image_name
    raw_image = image_path.read_bytes()
    with Image.open(io.BytesIO(raw_image)) as image:
        original = image.convert("RGB")
    proposal, metadata = compile_plan_partition(plan, image_size=original.size, image_name=image_name)
    from src.agent.geometry.plan_drawing_differences import drawing_differences
    differences = drawing_differences(original, plan, image_name=image_name,
        image_sha256=hashlib.sha256(raw_image).hexdigest(), plan_sha256=hashlib.sha256(_bytes(plan)).hexdigest())
    _opening_overlaps(plan)
    walls = validate_wall_metadata(plan)
    product = {"schema": "plan_reading_v1", "image": image_name,
               "image_sha256": hashlib.sha256(raw_image).hexdigest(),
               "geometry": proposal["geometry"], "mapping": metadata, "walls": walls,
               "coverage": {"floor_id": plan["floor_id"], "mode": "complete_floor_plan",
                            "vertical_geometry": "assembly_pending"},
               "validation": {"topology": "pass", "opening_hosts": "pass", "overlapping_openings": "pass",
                              "drawing_fidelity": "reader_review_required"}}
    folder = workspace / f"reading_{number:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    product_path = folder / "reading.json"
    product_path.write_bytes(_bytes(product))
    plan_path = folder / "plan.json"
    plan_path.write_bytes(_bytes(plan))
    contents, views = [], []
    for label, picture in zip(("overlay", "plan"), _views(plan, metadata, original)):
        path = folder / f"{label}.png"
        picture.save(path, "PNG")
        raw = path.read_bytes()
        contents.append({"type": "image", "mimeType": "image/png", "data": base64.b64encode(raw).decode()})
        views.append({"file": path.relative_to(workspace).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()})
    result = {"status": "passed", "source_geometry_ready": False, "reading_geometry_ready": True,
              "candidate": folder.name,
              "reading_product_file": product_path.relative_to(workspace).as_posix(),
              "reading_product_sha256": hashlib.sha256(product_path.read_bytes()).hexdigest(),
              "plan_input": {"plan_file": plan_path.relative_to(workspace).as_posix(),
                             "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                             "submitted_plan_file": plan_path.relative_to(workspace).as_posix(),
                             "image": image_name, "image_sha256": product["image_sha256"]},
              "source_plan_views": views,
              "building_precision": {"status": "pass", "scope": "2D topology, hosts, grid; no height test",
                                     "counts": {"spaces": len(metadata["space_mapping"]),
                                                "openings": len(metadata["opening_hosts"])}},
              "drawing_differences": differences}
    # Match the JSON boundary of MCP results (e.g. report tuples become arrays)
    # so in-memory receipts and restored receipts have identical values.
    return {"content": contents, "structuredContent": json.loads(_bytes(result)), "isError": False}
