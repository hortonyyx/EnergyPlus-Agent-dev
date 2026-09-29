"""Project an actual source elevation onto a caller-calibrated original image."""
from __future__ import annotations

from PIL import Image, ImageDraw

from src.agent.geometry.source_elevation_view import render_source_elevation
from src.agent.geometry.source_image_overlay import _axis_anchors, _label, _overlay_font


def render_elevation_overlay(source, original, *, facade, horizontal_anchors, z_anchors, basis):
    """Use two original-pixel/world-metre anchors per axis; never fit source geometry.

    Horizontal metres are world x on North/South and world y on East/West,
    without a second sign reversal. Vertical metres are absolute source z.
    Only axis-aligned drawings are supported. Calibration is caller evidence,
    not a correspondence or fidelity verdict.
    """
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("basis must describe the observed horizontal and absolute-z references")
    image = original.convert("RGB").copy()
    hs, ho, horizontal = _axis_anchors(horizontal_anchors, axis="horizontal", size=image.width)
    zs, zo, vertical = _axis_anchors(z_anchors, axis="z", size=image.height)
    _, view = render_source_elevation(source, facade)
    axis = 0 if view["horizontal_axis"] == "x" else 1
    draw = ImageDraw.Draw(image)
    font = _overlay_font(image)

    def project(h, z):
        return [(h - ho) / hs, (z - zo) / zs]

    def record(row, points):
        return {**row, "pixel_vertices": [[round(v, 6) for v in p] for p in points],
                "out_of_image": any(not (0 <= x < image.width and 0 <= y < image.height)
                                    for x, y in points)}

    walls, openings, floors = [], [], []
    for row in view["projected_exterior_walls"]:
        points = [project(p[axis], p[2]) for p in row["world_vertices"]]
        draw.line(points + [points[0]], fill=(160, 160, 160), width=1)
        walls.append(record(row, points))
    for row in view["projected_floor_lines"]:
        points = [project(h, z) for h, z in row["world_vertices"]]
        draw.line(points, fill=(180, 180, 180), width=1)
        floors.append(record(row, points))
    for row in view["projected_openings"]:
        points = [project(p[axis], p[2]) for p in row["world_vertices"]]
        colour = (255, 145, 0) if row["kind"] == "window" else (0, 190, 90)
        draw.line(points + [points[0]], fill=colour, width=2)
        if any(0 <= x < image.width and 0 <= y < image.height for x, y in points):
            _label(draw, (min(p[0] for p in points), min(p[1] for p in points)), row["id"],
                   colour=colour, font=font, offset=(3, -20))
        openings.append(record(row, points))

    warnings = []
    if abs(abs(hs / zs) - 1) > 0.05:
        warnings.append("Horizontal and vertical scales differ by more than 5%; inspect the anchor references.")
    return image, {
        "mode": "source_elevation_overlay",
        "source_model_sha256": view["source_model_sha256"],
        "facade": facade,
        "horizontal_axis": view["horizontal_axis"],
        "direction": ("+" if hs > 0 else "-") + view["horizontal_axis"],
        "image_size": list(image.size),
        "anchors": {"horizontal": horizontal, "absolute_z": vertical},
        "basis": basis.strip(),
        "calibration_unverified": True,
        "transform": {"horizontal_metres_per_pixel": hs, "horizontal_offset_m": ho,
                      "z_metres_per_pixel": zs, "z_offset_m": zo},
        "calibration_warnings": warnings,
        "projected_exterior_walls": walls,
        "projected_openings": openings,
        "projected_floor_lines": floors,
        "opening_heights": view["opening_heights"],
        "drawing_fidelity": "not_evaluated",
        "view_status": "not_visually_verified",
        "limits": [
            "Caller selects the image/facade and original-pixel/world-metre references; neither is independently verified.",
            "Horizontal values are world x/y, not distance from the facade's left edge; z is absolute, not above-floor height.",
            "Only axis-aligned drawings are supported; no rotation, perspective or automatic pixel matching.",
            "All same-facing exterior hosts are projected; recess-depth occlusion is not resolved.",
            "No source geometry is changed. Repeat with the same observed anchors after revision; do not fit anchors to generated openings.",
        ],
    }
