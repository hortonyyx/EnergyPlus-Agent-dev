"""Conservative ink-line alignment for elevation opening observations.

The reader's legacy ``bbox`` is an evidence crop, not an opening boundary.
This module therefore uses it only as a sampling region for left/right edges.
Opening geometry comes from an explicit ``opening_bbox`` when present, or from
legacy ``x_px`` plus ``sill_m``/``head_m`` when a vertical calibration proves
the pixel-to-height conversion.

The public function returns an alignment envelope and never mutates the input
artifact.  Callers preserve the envelope beside the reader artifact, then apply
``aligned_values`` before Lite-grid adoption. Marked dimensions and mixed
evidence are never replaced by image ink; the later regularization report keeps
these pre-grid readings beside the adopted values.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


INK_ALIGNMENT_SCHEMA_VERSION = "elevation_ink_alignment_v2"
DEFAULT_SEARCH_DISTANCE_M = 0.30
DEFAULT_MIN_SUPPORT_RATIO = 0.55
DEFAULT_MIN_MEAN_INK = 0.30

_EDGES = ("left", "top", "right", "bottom")


def align_elevation_artifact(
    image: str | Path | Image.Image | np.ndarray,
    artifact: Mapping[str, Any],
    *,
    search_distance_m: float = DEFAULT_SEARCH_DISTANCE_M,
    min_support_ratio: float = DEFAULT_MIN_SUPPORT_RATIO,
    min_mean_ink: float = DEFAULT_MIN_MEAN_INK,
) -> dict[str, Any]:
    """Align approximate opening rectangles to nearby strong facade ink.

    The search radius is ``search_distance_m * pixels_per_metre`` on each
    calibrated axis.  A candidate must cover ``min_support_ratio`` of the
    corresponding opening span and meet ``min_mean_ink``.  Weak or absent
    evidence leaves that edge unchanged and records why.

    Minimal forward contract:

    * ``opening.opening_bbox`` is ``[left, top, right, bottom]`` in original
      image pixels and means the approximate *opening* rectangle.
    * ``artifact.z_calibration`` mirrors ``x_calibration`` with
      ``pixel_start``, ``pixel_end``, ``world_start_m`` and ``world_end_m``.
      Image Y must increase while world Z decreases.

    Legacy artifacts remain useful horizontally through ``x_px``.  Their
    vertical bounds are derived from ``sill_m`` and ``head_m`` only when the
    explicit Z calibration is valid; otherwise top/bottom are not invented.
    """

    if not isinstance(artifact, Mapping):
        raise TypeError("artifact must be a mapping")
    if not math.isfinite(search_distance_m) or search_distance_m <= 0:
        raise ValueError("search_distance_m must be a positive finite number")
    if not 0 < min_support_ratio <= 1:
        raise ValueError("min_support_ratio must be in (0, 1]")
    if not 0 < min_mean_ink <= 1:
        raise ValueError("min_mean_ink must be in (0, 1]")

    gray = _grayscale(image)
    height, width = gray.shape
    x_calibration, x_problem = _calibration(
        artifact.get("x_calibration"), require_descending_world=False
    )
    z_calibration, z_problem = _calibration(
        artifact.get("z_calibration"), require_descending_world=True
    )
    x_radius = _search_radius(x_calibration, search_distance_m)
    z_radius = _search_radius(z_calibration, search_distance_m)

    opening_results = []
    for index, original_opening in enumerate(artifact.get("openings", ())):
        if not isinstance(original_opening, Mapping):
            raise TypeError(f"openings[{index}] must be a mapping")
        opening_results.append(
            _align_opening(
                gray,
                original_opening,
                index=index,
                x_calibration=x_calibration,
                z_calibration=z_calibration,
                x_problem=x_problem,
                z_problem=z_problem,
                x_radius=x_radius,
                z_radius=z_radius,
                levels=artifact.get("elevations", ()),
                min_support_ratio=min_support_ratio,
                min_mean_ink=min_mean_ink,
            )
        )

    opening_statuses = Counter(item["status"] for item in opening_results)
    edge_statuses = Counter(
        edge["status"]
        for item in opening_results
        for edge in item["edges"].values()
    )
    return {
        "schema_version": INK_ALIGNMENT_SCHEMA_VERSION,
        "image_size_px": [width, height],
        "search_distance_m": float(search_distance_m),
        "search_radius_px": {"x": x_radius, "z": z_radius},
        "calibration": {
            "x": "available" if x_calibration is not None else x_problem,
            "z": "available" if z_calibration is not None else z_problem,
        },
        "openings": opening_results,
        "summary": {
            "opening_count": len(opening_results),
            "opening_status_counts": dict(sorted(opening_statuses.items())),
            "edge_status_counts": dict(sorted(edge_statuses.items())),
            "candidate_moved_edge_count": edge_statuses["aligned"],
            "moved_edge_count": sum(row["edges"][edge]["status"] == "aligned" and field in row["applied_fields"]
                for row in opening_results for edge, field in (("left", "x_px"), ("right", "x_px"),
                                                               ("top", "head_m"), ("bottom", "sill_m"))),
            "applied_field_count": sum(len(row["applied_fields"]) for row in opening_results),
            "inconsistency_count": sum(len(row["inconsistencies"]) for row in opening_results),
        },
    }


def _align_opening(
    gray: np.ndarray,
    opening: Mapping[str, Any],
    *,
    index: int,
    x_calibration: dict[str, float] | None,
    z_calibration: dict[str, float] | None,
    x_problem: str,
    z_problem: str,
    x_radius: int | None,
    z_radius: int | None,
    levels: Sequence[Mapping[str, Any]],
    min_support_ratio: float,
    min_mean_ink: float,
) -> dict[str, Any]:
    opening_id = str(opening.get("id", f"opening-{index + 1}"))
    submitted = {
        field: copy.deepcopy(opening.get(field))
        for field in ("x_px", "width_m", "sill_m", "head_m")
    }
    explicit_box = _box_or_none(opening.get("opening_bbox"))
    x_pair = _pair_or_none(opening.get("x_px"))
    if explicit_box is not None:
        left, top, right, bottom = explicit_box
        geometry_source = "opening_bbox"
    else:
        left, right = x_pair if x_pair is not None else (None, None)
        top = _world_to_pixel(z_calibration, opening.get("head_m"))
        bottom = _world_to_pixel(z_calibration, opening.get("sill_m"))
        geometry_source = "legacy_x_px_and_calibrated_heights"

    original_box: list[float | None] = [left, top, right, bottom]
    if opening.get("evidence_type") == "pixels":
        if submitted["x_px"] is None and left is not None and right is not None:
            submitted["x_px"] = [left, right]
        if submitted["width_m"] is None and x_calibration and left is not None and right is not None:
            submitted["width_m"] = abs((right - left) * x_calibration["world_per_pixel"])
        for field, pixel in (("head_m", top), ("sill_m", bottom)):
            if submitted[field] is None and z_calibration and pixel is not None:
                submitted[field] = _pixel_to_world(z_calibration, pixel)
    aligned_box = list(original_box)
    evidence_box = _box_or_none(opening.get("bbox"))
    sampling_top, sampling_bottom = _sampling_vertical_span(
        top, bottom, evidence_box, gray.shape[0]
    )

    edges: dict[str, dict[str, Any]] = {}
    for edge_name in _EDGES:
        coordinate = original_box[_EDGES.index(edge_name)]
        calibration = x_calibration if edge_name in {"left", "right"} else z_calibration
        calibration_problem = x_problem if edge_name in {"left", "right"} else z_problem
        radius = x_radius if edge_name in {"left", "right"} else z_radius
        if coordinate is None or calibration is None or radius is None:
            edges[edge_name] = _unmoved_edge(
                coordinate, "missing_calibration", calibration_problem
            )
            continue

        if edge_name in {"left", "right"}:
            span = (sampling_top, sampling_bottom)
            axis_length = gray.shape[1]
        else:
            if left is None or right is None:
                edges[edge_name] = _unmoved_edge(
                    coordinate, "missing_geometry", "horizontal opening span is unavailable"
                )
                continue
            span = _trimmed_span(left, right, gray.shape[1])
            axis_length = gray.shape[0]

        candidates = _supported_lines(
            gray,
            coordinate=coordinate,
            radius=radius,
            span=span,
            vertical=edge_name in {"left", "right"},
            min_support_ratio=min_support_ratio,
            min_mean_ink=min_mean_ink,
        )
        if len(candidates) != 1:
            edges[edge_name] = _unmoved_edge(
                coordinate, "ambiguous_lines" if candidates else "no_strong_line",
                "multiple supported ink strokes" if candidates else "no supported ink line in the calibrated search range"
            )
            edges[edge_name]["candidates"] = candidates
            continue
        candidate = candidates[0]
        candidate_px, support_ratio, mean_ink = candidate["pixel"], candidate["support_ratio"], candidate["mean_ink"]
        candidate_px = float(max(0, min(axis_length - 1, candidate_px)))
        # Sub-pixel stroke centroids are not meaningful BIM changes.  Treat a
        # line within one source pixel as confirmation and retain the reader's
        # coordinate, avoiding tiny drift on thick or antialiased ink.
        if math.isclose(candidate_px, coordinate, abs_tol=1.0):
            candidate_px = float(coordinate)
            status = "confirmed"
        else:
            status = "aligned"
        edges[edge_name] = {
            "status": status,
            "original_px": float(coordinate),
            "aligned_px": candidate_px,
            "shift_px": candidate_px - float(coordinate),
            "support_ratio": support_ratio,
            "mean_ink": mean_ink,
            "search_radius_px": radius,
            "candidates": candidates,
        }
        aligned_box[_EDGES.index(edge_name)] = candidate_px

    _reject_inverted_pair(edges, aligned_box, "left", "right")
    _reject_inverted_pair(edges, aligned_box, "top", "bottom")

    policy = _apply_evidence_policy(opening, submitted, aligned_box, edges,
                                    x_calibration, z_calibration, levels)

    statuses = [edge["status"] for edge in edges.values()]
    moved = statuses.count("aligned")
    supported = moved + statuses.count("confirmed")
    if supported == 4:
        status = "aligned" if moved else "confirmed"
    elif supported:
        status = "partial"
    else:
        status = "unchanged"

    return {
        "id": opening_id,
        "status": "aligned" if policy["applied_fields"] else "inconsistent" if policy["inconsistencies"]
                  else "confirmed" if supported == 4 else "partial" if supported else "unchanged",
        "candidate_status": status,
        "geometry_source": geometry_source,
        "original_bbox_px": original_box,
        "candidate_bbox_px": aligned_box,
        "aligned_bbox_px": policy["effective_bbox_px"],
        "original_values": submitted,
        **policy,
        "edges": edges,
    }


def _apply_evidence_policy(opening, submitted, candidate_box, edges, xcal, zcal, levels):
    """An opening-level basis cannot authorize field-level mixed-source edits."""
    basis = opening.get("evidence_type", "unspecified")
    pure_pixels = basis == "pixels"
    values = copy.deepcopy(submitted)
    ink_values, inconsistencies, applied, decisions = {}, [], [], {}
    tolerances = {axis: max(0.05, 2 * abs(cal["world_per_pixel"])) if cal else None
                  for axis, cal in (("x", xcal), ("z", zcal))}
    unique = {name: edge["status"] in {"aligned", "confirmed"} for name, edge in edges.items()}
    if unique["left"] and unique["right"]:
        ink_values["x_px"] = [candidate_box[0], candidate_box[2]]
        ink_values["width_m"] = abs((candidate_box[2] - candidate_box[0]) * xcal["world_per_pixel"])
    for edge, field, index in (("top", "head_m", 1), ("bottom", "sill_m", 3)):
        if unique[edge]:
            ink_values[field] = _pixel_to_world(zcal, candidate_box[index])

    # Ground is not assumed to be Z=0 and a raised threshold is not flattened.
    # Only an observed same-floor/ground level already touching the submitted
    # sill (at most one pixel and 5 cm) establishes this protection.
    floor_contact = []
    sill = submitted.get("sill_m")
    if opening.get("kind") == "door" and zcal and isinstance(sill, (int, float)):
        contact_tolerance = min(0.05, abs(zcal["world_per_pixel"]))
        for level in levels:
            if (level.get("evidence_type") not in {"annotation", "annotation_and_pixels", "pixels"}
                    or level.get("kind") not in {"ground", "floor"}
                    or (level.get("floor_id") is not None and level["floor_id"] != opening.get("floor_id"))):
                continue
            z = level.get("value_m")
            if isinstance(z, (int, float)) and abs(sill - z) <= contact_tolerance + 1e-9:
                floor_contact.append({"id": level.get("id"), "value_m": z, "bbox": level.get("bbox"),
                                      "evidence_type": level["evidence_type"]})

    required_edges = {"x_px": ("left", "right"), "width_m": ("left", "right"),
                      "head_m": ("top",), "sill_m": ("bottom",)}
    for field, names in required_edges.items():
        original, ink = submitted.get(field), ink_values.get(field)
        axis = "x" if field in {"x_px", "width_m"} else "z"
        reason = "retained_non_pixel_basis" if not pure_pixels else "no_unique_ink"
        if ink is not None and original is not None:
            delta = (max(abs(a - b) * abs(xcal["world_per_pixel"])
                         for a, b in zip(ink, original)) if field == "x_px" else abs(ink - original))
            if delta > tolerances[axis] + 1e-9:
                inconsistencies.append({"field": field, "reader_value": copy.deepcopy(original),
                    "ink_value": copy.deepcopy(ink), "difference_m": delta,
                    "tolerance_m": tolerances[axis], "evidence_type": basis,
                    "reason": "reader_value_disagrees_with_unique_ink"})
            if pure_pixels:
                if field == "sill_m" and floor_contact:
                    reason = "retained_floor_contact"
                elif any(edges[name]["status"] == "aligned" for name in names):
                    values[field] = copy.deepcopy(ink)
                    applied.append(field)
                    reason = "replaced_unique_pixels"
                else:
                    # A line confirming the existing pixel edge does not
                    # justify re-rounding an independently submitted number.
                    reason = "confirmed_no_movement"
        decisions[field] = reason
    # Actual pixel corrections are recorded as corrections, not unresolved
    # disagreements. All retained numeric/ink disagreements remain reviewable.
    inconsistencies = [row for row in inconsistencies if row["field"] not in applied]
    effective = [None, None, None, None]
    if values["x_px"] is not None:
        effective[0], effective[2] = values["x_px"]
    effective[1] = _world_to_pixel(zcal, values["head_m"])
    effective[3] = _world_to_pixel(zcal, values["sill_m"])
    values["world_span_m"] = ([_pixel_to_world(xcal, x) for x in values["x_px"]]
                              if xcal and values["x_px"] is not None else None)
    for name, edge in edges.items():
        edge["effective_px"] = effective[_EDGES.index(name)]
    return {"aligned_values": values, "effective_bbox_px": effective,
            "ink_values": ink_values, "evidence_type": basis,
            "replacement_policy": "only_pixels_with_unique_ink; all_mixed_or_unspecified_values_retained",
            "tolerance_m": tolerances, "floor_contact": floor_contact,
            "field_decisions": decisions, "applied_fields": applied,
            "inconsistencies": inconsistencies}


def _grayscale(image: str | Path | Image.Image | np.ndarray) -> np.ndarray:
    if isinstance(image, np.ndarray):
        array = np.asarray(image)
        if array.ndim == 2:
            gray = array
        elif array.ndim == 3 and array.shape[2] in {3, 4}:
            pil = Image.fromarray(array.astype(np.uint8, copy=False))
            gray = np.asarray(_pil_grayscale(pil))
        else:
            raise ValueError("image array must be grayscale, RGB, or RGBA")
    else:
        pil = image if isinstance(image, Image.Image) else Image.open(image)
        gray = np.asarray(_pil_grayscale(pil))
    if gray.ndim != 2 or min(gray.shape) < 2:
        raise ValueError("image must contain at least 2 x 2 pixels")
    return gray.astype(np.float32, copy=False)


def _pil_grayscale(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image = Image.alpha_composite(white, rgba)
    return image.convert("L")


def _calibration(
    value: Any, *, require_descending_world: bool
) -> tuple[dict[str, float] | None, str]:
    if not isinstance(value, Mapping):
        return None, "missing_calibration"
    required = ("pixel_start", "pixel_end", "world_start_m", "world_end_m")
    try:
        numbers = {name: float(value[name]) for name in required}
    except (KeyError, TypeError, ValueError):
        return None, "invalid_calibration"
    if not all(math.isfinite(number) for number in numbers.values()):
        return None, "invalid_calibration"
    pixel_delta = numbers["pixel_end"] - numbers["pixel_start"]
    world_delta = numbers["world_end_m"] - numbers["world_start_m"]
    if pixel_delta == 0 or world_delta == 0:
        return None, "invalid_calibration"
    if require_descending_world and pixel_delta * world_delta >= 0:
        return None, "invalid_vertical_direction"
    numbers["world_per_pixel"] = world_delta / pixel_delta
    numbers["pixels_per_metre"] = abs(pixel_delta / world_delta)
    return numbers, "available"


def _search_radius(calibration: dict[str, float] | None, distance_m: float) -> int | None:
    if calibration is None:
        return None
    return max(2, int(math.ceil(calibration["pixels_per_metre"] * distance_m)))


def _pixel_to_world(calibration: dict[str, float], pixel: float) -> float:
    return calibration["world_start_m"] + (
        float(pixel) - calibration["pixel_start"]
    ) * calibration["world_per_pixel"]


def _world_to_pixel(calibration: dict[str, float] | None, world: Any) -> float | None:
    if calibration is None:
        return None
    try:
        value = float(world)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return calibration["pixel_start"] + (
        value - calibration["world_start_m"]
    ) / calibration["world_per_pixel"]


def _pair_or_none(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        return None
    try:
        first, second = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (first, second)) or first >= second:
        return None
    return first, second


def _box_or_none(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 4:
        return None
    try:
        left, top, right, bottom = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in (left, top, right, bottom)):
        return None
    if left >= right or top >= bottom:
        return None
    return left, top, right, bottom


def _sampling_vertical_span(
    top: float | None,
    bottom: float | None,
    evidence_box: tuple[float, float, float, float] | None,
    image_height: int,
) -> tuple[int, int]:
    if top is not None and bottom is not None and top < bottom:
        return _trimmed_span(top, bottom, image_height)
    if evidence_box is not None:
        # Legacy bbox is safe as a trace sampling region, never as geometry.
        return _trimmed_span(evidence_box[1], evidence_box[3], image_height)
    return 0, image_height


def _trimmed_span(start: float, end: float, limit: int) -> tuple[int, int]:
    low, high = sorted((float(start), float(end)))
    trim = min((high - low) * 0.10, 4.0)
    low = max(0, int(math.floor(low + trim)))
    high = min(limit, int(math.ceil(high - trim)) + 1)
    if high - low < 3:
        low = max(0, int(math.floor(min(start, end))))
        high = min(limit, int(math.ceil(max(start, end))) + 1)
    return low, max(low + 1, high)


def _supported_lines(
    gray: np.ndarray,
    *,
    coordinate: float,
    radius: int,
    span: tuple[int, int],
    vertical: bool,
    min_support_ratio: float,
    min_mean_ink: float,
) -> list[dict[str, float]]:
    axis_length = gray.shape[1] if vertical else gray.shape[0]
    lower = max(0, int(math.floor(coordinate)) - radius)
    upper = min(axis_length - 1, int(math.ceil(coordinate)) + radius)
    supported: list[tuple[int, float, float]] = []
    for candidate in range(lower, upper + 1):
        pixels = (
            gray[span[0] : span[1], candidate]
            if vertical
            else gray[candidate, span[0] : span[1]]
        )
        if pixels.size == 0:
            continue
        ink = 1.0 - np.clip(pixels, 0.0, 255.0) / 255.0
        support = float(np.mean(ink >= min_mean_ink))
        mean_ink = float(np.mean(ink))
        mask = ink >= min_mean_ink
        changes = np.diff(np.r_[False, mask, False].astype(np.int8))
        longest = max((np.flatnonzero(changes == -1) - np.flatnonzero(changes == 1)), default=0) / len(mask)
        if support >= min_support_ratio and longest >= min_support_ratio and mean_ink >= min_mean_ink:
            supported.append((candidate, support, mean_ink))
    if not supported:
        return []

    runs: list[list[tuple[int, float, float]]] = []
    for item in supported:
        if not runs or item[0] != runs[-1][-1][0] + 1:
            runs.append([item])
        else:
            runs[-1].append(item)
    output = []
    for run in runs:
        weights = np.asarray([item[2] for item in run], dtype=float)
        positions = np.asarray([item[0] for item in run], dtype=float)
        output.append({"pixel": float(np.average(positions, weights=weights)),
                       "support_ratio": max(item[1] for item in run),
                       "mean_ink": max(item[2] for item in run)})
    return output


def _unmoved_edge(coordinate: float | None, status: str, reason: str) -> dict[str, Any]:
    value = None if coordinate is None else float(coordinate)
    return {
        "status": status,
        "original_px": value,
        "aligned_px": value,
        "shift_px": 0.0,
        "reason": reason,
    }


def _reject_inverted_pair(
    edges: dict[str, dict[str, Any]],
    aligned_box: list[float | None],
    first_name: str,
    second_name: str,
) -> None:
    first_index, second_index = _EDGES.index(first_name), _EDGES.index(second_name)
    first, second = aligned_box[first_index], aligned_box[second_index]
    if first is None or second is None or first < second:
        return
    for name, index in ((first_name, first_index), (second_name, second_index)):
        edge = edges[name]
        if edge["status"] == "aligned":
            aligned_box[index] = edge["original_px"]
            edge.update(
                status="rejected_geometry",
                aligned_px=edge["original_px"],
                shift_px=0.0,
                reason="aligned edges would invert or collapse the opening",
            )
