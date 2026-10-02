"""Render a saved source floor, without drawing calibration or a fidelity verdict."""
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

from src.agent.geometry.source_floor_selection import select_source_floor, select_source_floor_openings
from src.agent.geometry.source_image_overlay import _source_hash


def render_source_plan(source: dict, floor_id: str):
    source_hash = _source_hash(source)
    floor, rooms = select_source_floor(source, floor_id)
    if not rooms:
        raise ValueError("unknown floor_id")
    points = [point for space in rooms for point in space["polygon"]]
    x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
    y0, y1 = min(p[1] for p in points), max(p[1] for p in points)
    scale = min(1000 / (x1 - x0), 700 / (y1 - y0))
    convert = lambda p: (40 + (p[0] - x0) * scale, 40 + (y1 - p[1]) * scale)
    pic = Image.new("RGB", (1080, 800), "white")
    draw = ImageDraw.Draw(pic)
    draw.text((40, 12), f"SOURCE BIM / {floor_id} / not drawing evidence", fill="black")
    draw.text((1040, 15), "+Y / N", fill="black", anchor="rt")
    draw.line([(1050, 70), (1050, 30)], fill="black", width=3)
    draw.polygon([(1050, 25), (1045, 35), (1055, 35)], fill="black")
    for index, space in enumerate(rooms):
        ring = [convert(point) for point in space["polygon"]]
        draw.polygon(ring, fill=(220 + (index * 11) % 30, 225, 235), outline="black", width=3)
        point = Polygon(space["polygon"]).representative_point()
        draw.text(convert((point.x, point.y)), space["id"], fill="black", anchor="mm")
    openings = select_source_floor_openings(source, floor, rooms)
    for opening in openings:
        points = list(dict.fromkeys(tuple(vertex[:2]) for vertex in opening["vertices"]))
        draw.line([convert(point) for point in points],
                  fill="blue" if opening["kind"] == "window" else "red", width=6)
    draw.text((40, 765), f"x: {x0:g}..{x1:g} m; y: {y0:g}..{y1:g} m; blue: windows; red: doors/passages", fill="black")
    return pic, {
        "source_model_sha256": source_hash,
        "floor_id": floor_id,
        "space_ids": [space["id"] for space in rooms],
        "opening_ids": [opening["id"] for opening in openings],
        "world_bounds_m": {"x": [x0, x1], "y": [y0, y1]},
        "scope": "actual saved source plan; no original calibration, height verification or drawing-fidelity verdict",
    }
