"""Project a source-BIM plan back onto an explicitly calibrated original image.

This is a review aid.  It does not inspect drawing pixels, infer calibration,
or decide whether the source BIM matches the drawing.
"""
from __future__ import annotations

import copy
import math

from PIL import Image, ImageDraw

from src.agent.geometry.source_model import _digest
from src.agent.reading.cv_toolbox.tools import _load_rgb, px_m_calibrator


_MAGENTA = (255, 0, 255)
_ORANGE = (255, 165, 0)
_LIME = (0, 255, 0)


def _number(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _axis_anchors(
    anchors: list[list[float]], *, axis: str, size: int,
) -> tuple[float, float, list[list[float]]]:
    """Return world-per-pixel slope and intercept for one image axis."""
    if not isinstance(anchors, list) or len(anchors) != 2:
        raise ValueError(f"{axis}_anchors requires exactly two [pixel, world_m] anchors")
    parsed: list[list[float]] = []
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, list) or len(anchor) != 2:
            raise ValueError(f"{axis}_anchors[{index}] must be [pixel, world_m]")
        pixel = _number(anchor[0], name=f"{axis}_anchors[{index}][0]")
        world = _number(anchor[1], name=f"{axis}_anchors[{index}][1]")
        if not 0 <= pixel < size:
            raise ValueError(f"{axis}_anchors[{index}] pixel is outside original image bounds")
        parsed.append([pixel, world])
    (p0, w0), (p1, w1) = parsed
    if p0 == p1 or w0 == w1:
        raise ValueError(f"{axis}_anchors require distinct pixel and world values")
    slope = (w1 - w0) / (p1 - p0)
    return slope, w0 - slope * p0, parsed


def _source_hash(source: dict) -> str:
    if not isinstance(source, dict):
        raise TypeError("source must be a source_model.json object")
    declared = source.get("source_model_sha256")
    if not isinstance(declared, str) or not declared:
        raise ValueError("source requires source_model_sha256")
    actual = _digest({key: value for key, value in source.items() if key != "source_model_sha256"})
    if declared != actual:
        raise ValueError("source_model_sha256 does not match source content")
    return actual


def _plan_points(vertices: object, *, name: str) -> list[tuple[float, float]]:
    if not isinstance(vertices, list) or len(vertices) < 2:
        raise ValueError(f"{name} requires at least two plan vertices")
    points = []
    for index, vertex in enumerate(vertices):
        if not isinstance(vertex, (list, tuple)) or len(vertex) < 2:
            raise ValueError(f"{name}[{index}] must contain x and y")
        points.append((_number(vertex[0], name=f"{name}[{index}][0]"),
                       _number(vertex[1], name=f"{name}[{index}][1]")))
    return points


def _unique_endpoints(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    endpoints: list[tuple[float, float]] = []
    for point in points:
        if point not in endpoints:
            endpoints.append(point)
        if len(endpoints) == 2:
            break
    if len(endpoints) != 2:
        raise ValueError("source opening requires two distinct plan endpoints")
    return endpoints


def render_source_overlay(
    source: dict,
    image: Image.Image,
    *,
    floor_id: str,
    x_anchors: list[list[float]],
    y_anchors: list[list[float]],
    basis: str,
) -> tuple[Image.Image, dict]:
    """Draw one source floor over an original plan using a caller-supplied affine frame.

    ``x_anchors`` and ``y_anchors`` each contain exactly two ``[pixel, world_m]``
    pairs, matching the MCP ``map_pixels`` format.  The transform is axis-aligned
    only: rotation, perspective, and nonlinear scan distortion are unsupported.
    The returned metadata deliberately marks calibration and drawing fidelity as
    unverified; this function supplies a visual comparison, not an image verdict.
    """
    source_hash = _source_hash(source)
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL.Image.Image")
    if not isinstance(floor_id, str) or not floor_id:
        raise ValueError("floor_id must be a nonempty string")
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError("basis must be a nonempty calibration statement")

    x_slope, x_offset, parsed_x = _axis_anchors(x_anchors, axis="x", size=image.width)
    y_slope, y_offset, parsed_y = _axis_anchors(y_anchors, axis="y", size=image.height)
    calibration = px_m_calibrator([
        {"axis": "x", "px_a": parsed_x[0][0], "px_b": parsed_x[1][0],
         "value_m": abs(parsed_x[1][1] - parsed_x[0][1]), "dimension_ref": "caller_x_anchors"},
        {"axis": "y", "px_a": parsed_y[0][0], "px_b": parsed_y[1][0],
         "value_m": abs(parsed_y[1][1] - parsed_y[0][1]), "dimension_ref": "caller_y_anchors"},
    ])
    calibration_result = calibration["results"][0]

    floors = source.get("floors")
    spaces = source.get("spaces")
    openings = source.get("openings")
    if not isinstance(floors, list) or not isinstance(spaces, list) or not isinstance(openings, list):
        raise ValueError("source requires floors, spaces, and openings lists")
    floor_ids = {row.get("id") for row in floors if isinstance(row, dict)}
    if floor_id not in floor_ids:
        raise ValueError("unknown source floor_id")

    spaces_by_id: dict[str, dict] = {}
    selected_spaces: list[dict] = []
    for space in spaces:
        if not isinstance(space, dict) or not isinstance(space.get("id"), str) or not space["id"]:
            raise ValueError("source space requires a nonempty id")
        if space["id"] in spaces_by_id:
            raise ValueError("duplicate source space id")
        if space.get("floor_id") not in floor_ids:
            raise ValueError("source space references unknown floor")
        spaces_by_id[space["id"]] = space
        if space["floor_id"] == floor_id:
            selected_spaces.append(space)

    def project(point: tuple[float, float]) -> tuple[float, float]:
        return ((point[0] - x_offset) / x_slope, (point[1] - y_offset) / y_slope)

    def outside(point: tuple[float, float]) -> bool:
        return point[0] < 0 or point[0] >= image.width or point[1] < 0 or point[1] >= image.height

    overlay = _load_rgb(image)
    draw = ImageDraw.Draw(overlay)
    projected_spaces = []
    for space in selected_spaces:
        world_polygon = _plan_points(space.get("polygon"), name=f"space {space['id']} polygon")
        pixel_polygon = [project(point) for point in world_polygon]
        draw.line(pixel_polygon + [pixel_polygon[0]], fill=_MAGENTA, width=3, joint="curve")
        projected_spaces.append({
            "id": space["id"],
            "pixel_polygon": [[round(x, 6), round(y, 6)] for x, y in pixel_polygon],
            "out_of_image": any(outside(point) for point in pixel_polygon),
        })

    projected_openings = []
    projected_wall_faces = []
    for wall in source.get("wall_references", []):
        if wall["floor_id"] != floor_id:
            continue
        faces = wall.get("face_endpoints")
        pixels = [] if faces is None else [[project(tuple(p)) for p in face] for face in faces]
        for face in pixels:
            draw.line([(round(x), round(y)) for x, y in face], fill=(0, 160, 255), width=2)
        projected_wall_faces.append({
            "id": wall["id"], "boundary_ids": wall["boundary_ids"],
            "evidence_status": wall["evidence_status"], "offsets_m": wall.get("offsets_m"),
            "face_status": "unknown_offsets" if faces is None else "derived_from_declared_offsets",
            "pixel_faces": [[[round(x, 6), round(y, 6)] for x, y in face] for face in pixels],
            "out_of_image": any(outside(p) for face in pixels for p in face),
        })
    for opening in openings:
        if not isinstance(opening, dict) or not isinstance(opening.get("id"), str) or not opening["id"]:
            raise ValueError("source opening requires a nonempty id")
        space_ids = opening.get("space_ids")
        if not isinstance(space_ids, list) or not space_ids or any(sid not in spaces_by_id for sid in space_ids):
            raise ValueError(f"source opening {opening['id']} has invalid space_ids")
        opening_floors = {spaces_by_id[sid]["floor_id"] for sid in space_ids}
        if len(opening_floors) != 1:
            raise ValueError(f"source opening {opening['id']} spans multiple floors")
        if floor_id not in opening_floors:
            continue
        endpoints = [project(point) for point in _unique_endpoints(
            _plan_points(opening.get("vertices"), name=f"opening {opening['id']} vertices"))]
        kind = opening.get("kind")
        colour = _LIME if kind == "window" else _ORANGE
        draw.line(endpoints, fill=colour, width=3)
        projected_openings.append({
            "id": opening["id"],
            "kind": kind,
            "space_ids": list(space_ids),
            "pixel_endpoints": [[round(x, 6), round(y, 6)] for x, y in endpoints],
            "out_of_image": any(outside(point) for point in endpoints),
        })

    metadata = {
        "mode": "source_image_overlay",
        "source_model_sha256": source_hash,
        "floor_id": floor_id,
        "basis": basis,
        "calibration_basis": "caller_supplied_not_independently_verified",
        "calibration_unverified": True,
        "drawing_fidelity": "not_evaluated",
        "anchors": {"x": parsed_x, "y": parsed_y},
        "scale": {
            "world_metres_per_pixel": {"x": x_slope, "y": y_slope},
            "pixels_per_world_metre": {"x": 1.0 / x_slope, "y": 1.0 / y_slope},
            "axis_px_per_m": calibration_result["axis_px_per_m"],
            "warnings": copy.deepcopy(calibration_result["warnings"]),
        },
        "projected_spaces": projected_spaces,
        "projected_openings": projected_openings,
        "projected_wall_faces": projected_wall_faces,
        "legend": {"magenta": "source representative boundary", "blue": "declared wall faces; evidence status in metadata",
                   "green": "window", "orange": "door/open aperture"},
        "out_of_image": {
            "space_ids": [row["id"] for row in projected_spaces if row["out_of_image"]],
            "opening_ids": [row["id"] for row in projected_openings if row["out_of_image"]],
            "wall_reference_ids": [row["id"] for row in projected_wall_faces if row["out_of_image"]],
        },
        "unsupported": ["rotation", "perspective", "nonlinear_distortion"],
        "limits": [
            "Two caller-supplied anchors per axis define the transform but do not independently close a dimension chain.",
            "The overlay does not inspect original pixels or automatically decide positional error.",
        ],
    }
    return overlay, metadata
