"""Flat elevation-reader artifacts and conservative facade-to-BIM matching.

The reader reports absolute building Z for sill/head values.  Horizontal
calibration uses the fixed world axis: North/South facades use world X and
East/West facades use world Y.  ``view_direction`` determines whether image
left-to-right increases or decreases that world coordinate.

This module only prepares matches and existing ``claim_transaction`` input.
It never edits a candidate or treats a count match as geometric evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "elevation_reader_v1"
MATCH_SCHEMA_VERSION = "elevation_match_v1"
APPLICATION_SCHEMA_VERSION = "elevation_height_application_v1"

_CARDINALS = {"North", "South", "East", "West"}
_OPENING_KINDS = {"window", "door"}
_ELEVATION_KINDS = {"ground", "floor", "eave", "roof", "other"}
_EVIDENCE_TYPES = {
    "annotation",
    "pixels",
    "annotation_and_pixels",
    "visual_estimate",
    "assumption",
    "declared",
}


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return dict(value)


def _sequence(value: Any, path: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{path} must be an array")
    return list(value)


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a nonempty string")
    return value.strip()


def _number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{path} must be a finite number")
    if minimum is not None and result < minimum:
        raise ValueError(f"{path} must be at least {minimum}")
    return result


def _pair(value: Any, path: str, *, positive_span: bool = False) -> list[float]:
    items = _sequence(value, path)
    if len(items) != 2:
        raise ValueError(f"{path} must contain exactly two numbers")
    pair = [_number(item, f"{path}[{index}]") for index, item in enumerate(items)]
    if positive_span and pair[0] >= pair[1]:
        raise ValueError(f"{path} must be ordered [start, end] with start < end")
    return pair


def _bbox(value: Any, path: str) -> list[float]:
    items = _sequence(value, path)
    if len(items) != 4:
        raise ValueError(f"{path} must be [left, top, right, bottom]")
    box = [_number(item, f"{path}[{index}]", minimum=0.0) for index, item in enumerate(items)]
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError(f"{path} must have positive width and height")
    return box


def _allowed(row: Mapping[str, Any], allowed: set[str], path: str) -> None:
    if extras := sorted(set(row) - allowed):
        raise ValueError(f"{path} has unknown fields: {extras}")


def _required(row: Mapping[str, Any], required: set[str], path: str) -> None:
    if missing := sorted(required - set(row)):
        raise ValueError(f"{path} is missing required fields {missing}")


def _world_axis(orientation: str) -> str:
    return "x" if orientation in {"North", "South"} else "y"


def _expected_world_sign(orientation: str, view_direction: str) -> int:
    if orientation in {"North", "South"}:
        if view_direction not in {"North", "South"}:
            raise ValueError(
                "view_direction must be North or South for a North/South facade"
            )
        # A viewer looking South has East on the image's left, so world X
        # decreases from image left to right.  Looking North is the inverse.
        return -1 if view_direction == "South" else 1
    if view_direction not in {"East", "West"}:
        raise ValueError(
            "view_direction must be East or West for an East/West facade"
        )
    # A viewer looking West has South on the image's left, so world Y
    # increases from image left to right.  Looking East is the inverse.
    return 1 if view_direction == "West" else -1


def _normalize_calibration(
    value: Any, *, orientation: str, view_direction: str
) -> dict[str, Any]:
    row = _mapping(value, "x_calibration")
    allowed = {
        "pixel_start",
        "pixel_end",
        "world_start_m",
        "world_end_m",
        "world_axis",
    }
    required = {"pixel_start", "pixel_end", "world_start_m", "world_end_m"}
    _allowed(row, allowed, "x_calibration")
    _required(row, required, "x_calibration")
    pixel_start = _number(row["pixel_start"], "x_calibration.pixel_start", minimum=0.0)
    pixel_end = _number(row["pixel_end"], "x_calibration.pixel_end", minimum=0.0)
    world_start = _number(row["world_start_m"], "x_calibration.world_start_m")
    world_end = _number(row["world_end_m"], "x_calibration.world_end_m")
    if pixel_start >= pixel_end:
        raise ValueError("x_calibration pixel_start must be less than pixel_end")
    if world_start == world_end:
        raise ValueError("x_calibration world coordinates must span a nonzero distance")
    axis = _world_axis(orientation)
    if "world_axis" in row and row["world_axis"] != axis:
        raise ValueError(
            f"x_calibration.world_axis must be {axis!r} for {orientation} facade"
        )
    sign = 1 if world_end > world_start else -1
    expected = _expected_world_sign(orientation, view_direction)
    if sign != expected:
        raise ValueError(
            "x_calibration world direction contradicts view_direction; "
            f"image left-to-right must {'increase' if expected > 0 else 'decrease'} "
            f"world {axis.upper()}"
        )
    return {
        "pixel_start": pixel_start,
        "pixel_end": pixel_end,
        "world_start_m": world_start,
        "world_end_m": world_end,
        "world_axis": axis,
    }


def _normalize_elevation(value: Any, index: int) -> dict[str, Any]:
    path = f"elevations[{index}]"
    row = _mapping(value, path)
    allowed = {"id", "floor_id", "kind", "value_m", "evidence_type", "bbox"}
    required = {"id", "kind", "value_m", "evidence_type", "bbox"}
    _allowed(row, allowed, path)
    _required(row, required, path)
    kind = _string(row["kind"], f"{path}.kind")
    if kind not in _ELEVATION_KINDS:
        raise ValueError(f"{path}.kind must be one of {sorted(_ELEVATION_KINDS)}")
    evidence_type = _string(row["evidence_type"], f"{path}.evidence_type")
    if evidence_type not in _EVIDENCE_TYPES:
        raise ValueError(
            f"{path}.evidence_type must be one of {sorted(_EVIDENCE_TYPES)}"
        )
    result = {
        "id": _string(row["id"], f"{path}.id"),
        "floor_id": None,
        "kind": kind,
        "value_m": _number(row["value_m"], f"{path}.value_m"),
        "evidence_type": evidence_type,
        "bbox": _bbox(row["bbox"], f"{path}.bbox"),
    }
    if row.get("floor_id") is not None:
        result["floor_id"] = _string(row["floor_id"], f"{path}.floor_id")
    if kind == "floor" and result["floor_id"] is None:
        raise ValueError(f"{path}.floor_id is required for kind='floor'")
    return result


def _normalize_opening(value: Any, index: int) -> dict[str, Any]:
    path = f"openings[{index}]"
    row = _mapping(value, path)
    allowed = {
        "id",
        "floor_id",
        "kind",
        "x_px",
        "width_m",
        "sill_m",
        "head_m",
        "evidence_type",
        "bbox",
    }
    required = allowed
    _allowed(row, allowed, path)
    _required(row, required, path)
    kind = _string(row["kind"], f"{path}.kind")
    if kind not in _OPENING_KINDS:
        raise ValueError(f"{path}.kind must be 'window' or 'door'")
    evidence_type = _string(row["evidence_type"], f"{path}.evidence_type")
    if evidence_type not in _EVIDENCE_TYPES:
        raise ValueError(
            f"{path}.evidence_type must be one of {sorted(_EVIDENCE_TYPES)}"
        )
    sill = _number(row["sill_m"], f"{path}.sill_m")
    head = _number(row["head_m"], f"{path}.head_m")
    if head <= sill:
        raise ValueError(
            f"{path}.head_m must exceed sill_m; both are absolute building Z"
        )
    return {
        "id": _string(row["id"], f"{path}.id"),
        "floor_id": _string(row["floor_id"], f"{path}.floor_id"),
        "kind": kind,
        "x_px": _pair(row["x_px"], f"{path}.x_px", positive_span=True),
        "width_m": _number(row["width_m"], f"{path}.width_m", minimum=1e-12),
        "sill_m": sill,
        "head_m": head,
        "evidence_type": evidence_type,
        "bbox": _bbox(row["bbox"], f"{path}.bbox"),
    }


def _normalize_count(value: Any, index: int) -> dict[str, Any]:
    path = f"counts[{index}]"
    row = _mapping(value, path)
    allowed = {"floor_id", "window_count", "door_count"}
    _allowed(row, allowed, path)
    _required(row, allowed, path)
    result = {"floor_id": _string(row["floor_id"], f"{path}.floor_id")}
    for field in ("window_count", "door_count"):
        count = row[field]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{path}.{field} must be a nonnegative integer")
        result[field] = count
    return result


def validate_elevation_artifact(
    value: Any, *, image_name: str | None = None
) -> dict[str, Any]:
    """Validate and normalize one elevation reader's compact artifact.

    ``image_name`` supplies the assigned original when the model omits ``image``.
    ``schema_version`` and ``artifact_id`` also default, so models need not fill
    runtime identity fields.  Errors identify the exact item and field.
    """

    row = _mapping(value, "artifact")
    allowed = {
        "schema_version",
        "artifact_id",
        "image",
        "orientation",
        "view_direction",
        "x_calibration",
        "elevations",
        "openings",
        "counts",
        "unresolved",
        "artifact_sha256",
    }
    required = {
        "orientation",
        "view_direction",
        "x_calibration",
        "elevations",
        "openings",
        "counts",
    }
    _allowed(row, allowed, "artifact")
    _required(row, required, "artifact")
    schema_version = row.get("schema_version", SCHEMA_VERSION)
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}")
    orientation = _string(row["orientation"], "orientation")
    view_direction = _string(row["view_direction"], "view_direction")
    if orientation not in _CARDINALS:
        raise ValueError(f"orientation must be one of {sorted(_CARDINALS)}")
    if view_direction not in _CARDINALS:
        raise ValueError(f"view_direction must be one of {sorted(_CARDINALS)}")
    image = row.get("image", image_name)
    image = _string(image, "image (or image_name)")
    if image_name is not None and Path(image).name != Path(image_name).name:
        raise ValueError("artifact.image does not match the assigned image_name")
    calibration = _normalize_calibration(
        row["x_calibration"],
        orientation=orientation,
        view_direction=view_direction,
    )
    elevations = [
        _normalize_elevation(item, index)
        for index, item in enumerate(_sequence(row["elevations"], "elevations"))
    ]
    if not elevations:
        raise ValueError("elevations must contain at least one located level")
    openings = [
        _normalize_opening(item, index)
        for index, item in enumerate(_sequence(row["openings"], "openings"))
    ]
    counts = [
        _normalize_count(item, index)
        for index, item in enumerate(_sequence(row["counts"], "counts"))
    ]
    unresolved = [
        _string(item, f"unresolved[{index}]")
        for index, item in enumerate(_sequence(row.get("unresolved", []), "unresolved"))
    ]

    opening_ids = [item["id"] for item in openings]
    if len(opening_ids) != len(set(opening_ids)):
        raise ValueError("openings[*].id values must be unique")
    elevation_ids = [item["id"] for item in elevations]
    if len(elevation_ids) != len(set(elevation_ids)):
        raise ValueError("elevations[*].id values must be unique")
    count_floors = [item["floor_id"] for item in counts]
    if len(count_floors) != len(set(count_floors)):
        raise ValueError("counts[*].floor_id values must be unique")

    previous_by_floor: dict[str, float] = {}
    actual_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for index, opening in enumerate(openings):
        center = sum(opening["x_px"]) / 2.0
        previous = previous_by_floor.get(opening["floor_id"])
        if previous is not None and center <= previous:
            raise ValueError(
                f"openings[{index}] is not in left-to-right order within "
                f"floor {opening['floor_id']!r}"
            )
        previous_by_floor[opening["floor_id"]] = center
        actual_counts[opening["floor_id"]][opening["kind"]] += 1
    reported = {item["floor_id"]: item for item in counts}
    if missing := sorted(set(actual_counts) - set(reported)):
        raise ValueError(f"counts is missing floors present in openings: {missing}")
    for floor_id, item in reported.items():
        expected = actual_counts[floor_id]
        for kind, field in (("window", "window_count"), ("door", "door_count")):
            if item[field] != expected[kind]:
                raise ValueError(
                    f"counts for floor {floor_id!r} says {field}={item[field]}, "
                    f"but openings contains {expected[kind]}"
                )

    artifact_id = row.get("artifact_id")
    if artifact_id is None:
        artifact_id = f"elevation:{orientation}:{Path(image).stem}"
    artifact_id = _string(artifact_id, "artifact_id")
    normalized = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "image": image,
        "orientation": orientation,
        "view_direction": view_direction,
        "x_calibration": calibration,
        "elevations": elevations,
        "openings": openings,
        "counts": counts,
        "unresolved": unresolved,
    }
    normalized["artifact_sha256"] = _canonical_hash(normalized)
    if row.get("artifact_sha256") not in (None, normalized["artifact_sha256"]):
        raise ValueError("artifact_sha256 does not match normalized artifact content")
    return normalized


def _newell_normal(vertices: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    x = y = z = 0.0
    for first, second in zip(vertices, [*vertices[1:], vertices[0]], strict=True):
        x += (first[1] - second[1]) * (first[2] + second[2])
        y += (first[2] - second[2]) * (first[0] + second[0])
        z += (first[0] - second[0]) * (first[1] + second[1])
    return x, y, z


def _boundary_orientation(boundary: Mapping[str, Any]) -> str:
    vertices = _sequence(boundary.get("vertices"), "boundary.vertices")
    if len(vertices) < 3:
        raise ValueError("exterior host boundary has fewer than three vertices")
    normal = _newell_normal(vertices)
    if max(abs(normal[0]), abs(normal[1])) <= 1e-9:
        raise ValueError("exterior host boundary has no horizontal outward normal")
    if abs(normal[0]) > abs(normal[1]):
        return "East" if normal[0] > 0 else "West"
    return "North" if normal[1] > 0 else "South"


def _source_rows(source_bim: Mapping[str, Any], orientation: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    boundaries = {
        _string(row.get("id"), "boundaries[*].id"): row
        for row in (_mapping(item, "boundaries[*]") for item in _sequence(source_bim.get("boundaries"), "source_bim.boundaries"))
    }
    spaces = {
        _string(row.get("id"), "spaces[*].id"): row
        for row in (_mapping(item, "spaces[*]") for item in _sequence(source_bim.get("spaces"), "source_bim.spaces"))
    }
    rows: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    axis_index = 0 if _world_axis(orientation) == "x" else 1
    for raw in _sequence(source_bim.get("openings"), "source_bim.openings"):
        opening = _mapping(raw, "source_bim.openings[*]")
        if not opening.get("exterior", False):
            continue
        opening_id = _string(opening.get("id"), "source_bim.openings[*].id")
        host_id = opening.get("host_boundary_id")
        host = boundaries.get(host_id)
        if host is None:
            conflicts.append(
                {"type": "source_host_missing", "source_id": opening_id, "host_boundary_id": host_id}
            )
            continue
        try:
            facade = _boundary_orientation(host)
        except ValueError as error:
            conflicts.append(
                {"type": "source_orientation_unresolved", "source_id": opening_id, "detail": str(error)}
            )
            continue
        if facade != orientation:
            continue
        floor_ids = sorted(
            {
                spaces[space_id]["floor_id"]
                for space_id in opening.get("space_ids", [])
                if space_id in spaces and spaces[space_id].get("floor_id") is not None
            }
        )
        if len(floor_ids) != 1:
            conflicts.append(
                {"type": "source_floor_unresolved", "source_id": opening_id, "floor_ids": floor_ids}
            )
            continue
        vertices = _sequence(opening.get("vertices"), f"source opening {opening_id}.vertices")
        if len(vertices) < 2:
            conflicts.append({"type": "source_vertices_missing", "source_id": opening_id})
            continue
        try:
            points = [
                [_number(value, f"source opening {opening_id}.vertices") for value in vertex]
                for vertex in vertices
            ]
        except (TypeError, ValueError) as error:
            conflicts.append(
                {"type": "source_vertices_invalid", "source_id": opening_id, "detail": str(error)}
            )
            continue
        if any(len(point) < 3 for point in points):
            conflicts.append({"type": "source_vertices_invalid", "source_id": opening_id})
            continue
        kind = opening.get("kind")
        if kind not in _OPENING_KINDS:
            continue
        planar = [(point[0], point[1]) for point in points]
        unique_planar = list(dict.fromkeys(planar))
        if len(unique_planar) != 2:
            conflicts.append(
                {"type": "source_width_unresolved", "source_id": opening_id, "plan_points": unique_planar}
            )
            continue
        width = math.dist(unique_planar[0], unique_planar[1])
        coordinate = sum(point[axis_index] for point in unique_planar) / 2.0
        rows.append(
            {
                "source_id": opening_id,
                "floor_id": str(floor_ids[0]),
                "kind": kind,
                "world_coordinate_m": coordinate,
                "width_m": width,
                "absolute_z_m": [min(point[2] for point in points), max(point[2] for point in points)],
                "host_boundary_id": host_id,
            }
        )
    return rows, conflicts


def _pixel_to_world(calibration: Mapping[str, Any], pixel: float) -> float:
    fraction = (pixel - calibration["pixel_start"]) / (
        calibration["pixel_end"] - calibration["pixel_start"]
    )
    return calibration["world_start_m"] + fraction * (
        calibration["world_end_m"] - calibration["world_start_m"]
    )


def _ordered_assignment(
    elevation: list[dict[str, Any]],
    source: list[dict[str, Any]],
    *,
    position_tolerance_m: float,
    width_tolerance_m: float,
) -> tuple[list[tuple[int, int]], list[int], list[int], bool]:
    """Needleman-Wunsch assignment preserving facade order."""

    if len(elevation) == len(source):
        return list(zip(range(len(elevation)), range(len(source)), strict=True)), [], [], False
    gap = 3.0
    rows, columns = len(elevation) + 1, len(source) + 1
    costs = [[0.0] * columns for _ in range(rows)]
    paths = [[1] * columns for _ in range(rows)]
    actions: list[list[str | None]] = [[None] * columns for _ in range(rows)]
    for i in range(1, rows):
        costs[i][0] = i * gap
        actions[i][0] = "elevation_only"
    for j in range(1, columns):
        costs[0][j] = j * gap
        actions[0][j] = "source_only"
    epsilon = 1e-9
    for i in range(1, rows):
        for j in range(1, columns):
            left = elevation[i - 1]
            right = source[j - 1]
            match_cost = (
                abs(left["world_coordinate_m"] - right["world_coordinate_m"])
                / position_tolerance_m
                + abs(left["width_m"] - right["width_m"]) / width_tolerance_m
            )
            options = [
                (costs[i - 1][j - 1] + match_cost, "match", paths[i - 1][j - 1]),
                (costs[i - 1][j] + gap, "elevation_only", paths[i - 1][j]),
                (costs[i][j - 1] + gap, "source_only", paths[i][j - 1]),
            ]
            best = min(option[0] for option in options)
            winners = [option for option in options if abs(option[0] - best) <= epsilon]
            costs[i][j] = best
            paths[i][j] = min(2, sum(option[2] for option in winners))
            actions[i][j] = sorted(winners, key=lambda option: (option[1] != "match", option[1]))[0][1]
    pairs: list[tuple[int, int]] = []
    elevation_only: list[int] = []
    source_only: list[int] = []
    i, j = len(elevation), len(source)
    while i or j:
        action = actions[i][j]
        if action == "match":
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif action == "elevation_only":
            elevation_only.append(i - 1)
            i -= 1
        elif action == "source_only":
            source_only.append(j - 1)
            j -= 1
        else:
            raise AssertionError("assignment backtrace is incomplete")
    return (
        list(reversed(pairs)),
        list(reversed(elevation_only)),
        list(reversed(source_only)),
        paths[-1][-1] > 1,
    )


def match_elevation(
    source_bim: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    candidate: str | None = None,
    position_tolerance_m: float = 0.35,
    width_tolerance_m: float = 0.25,
) -> dict[str, Any]:
    """Match an elevation artifact to exterior source openings conservatively.

    The assignment is ordered independently within each floor and opening kind.
    Safe matches, both one-sided inventories, and conflicts are returned
    separately.  The result is bound to the source model and artifact hashes.
    """

    source = _mapping(source_bim, "source_bim")
    normalized = validate_elevation_artifact(artifact)
    position_tolerance_m = _number(
        position_tolerance_m, "position_tolerance_m", minimum=1e-12
    )
    width_tolerance_m = _number(
        width_tolerance_m, "width_tolerance_m", minimum=1e-12
    )
    source_hash = _string(source.get("source_model_sha256"), "source_model_sha256")
    rows, conflicts = _source_rows(source, normalized["orientation"])
    calibration = normalized["x_calibration"]
    elevation_rows = []
    for opening in normalized["openings"]:
        center_px = sum(opening["x_px"]) / 2.0
        elevation_rows.append(
            {
                **opening,
                "world_coordinate_m": _pixel_to_world(calibration, center_px),
                "calibrated_width_m": abs(
                    _pixel_to_world(calibration, opening["x_px"][1])
                    - _pixel_to_world(calibration, opening["x_px"][0])
                ),
            }
        )

    sign = _expected_world_sign(normalized["orientation"], normalized["view_direction"])
    by_group_elevation: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_group_source: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in elevation_rows:
        by_group_elevation[(row["floor_id"], row["kind"])].append(row)
    for row in rows:
        by_group_source[(row["floor_id"], row["kind"])].append(row)
    for group in by_group_elevation.values():
        group.sort(key=lambda item: sign * item["world_coordinate_m"])
    for group in by_group_source.values():
        group.sort(key=lambda item: sign * item["world_coordinate_m"])

    matches: list[dict[str, Any]] = []
    elevation_only: list[dict[str, Any]] = []
    source_only: list[dict[str, Any]] = []
    all_groups = sorted(set(by_group_elevation) | set(by_group_source))
    for floor_id, kind in all_groups:
        left = by_group_elevation[(floor_id, kind)]
        right = by_group_source[(floor_id, kind)]
        pairs, only_left, only_right, ambiguous = _ordered_assignment(
            left,
            right,
            position_tolerance_m=position_tolerance_m,
            width_tolerance_m=width_tolerance_m,
        )
        if ambiguous:
            conflicts.append(
                {
                    "type": "ambiguous_ordered_assignment",
                    "floor_id": floor_id,
                    "kind": kind,
                    "elevation_ids": [row["id"] for row in left],
                    "source_ids": [row["source_id"] for row in right],
                }
            )
        for left_index, right_index in pairs:
            observed = left[left_index]
            actual = right[right_index]
            position_difference = observed["world_coordinate_m"] - actual["world_coordinate_m"]
            width_difference = observed["width_m"] - actual["width_m"]
            match = {
                "artifact_opening_id": observed["id"],
                "source_opening_id": actual["source_id"],
                "floor_id": floor_id,
                "kind": kind,
                "artifact_world_coordinate_m": observed["world_coordinate_m"],
                "source_world_coordinate_m": actual["world_coordinate_m"],
                "position_difference_m": position_difference,
                "artifact_width_m": observed["width_m"],
                "source_width_m": actual["width_m"],
                "width_difference_m": width_difference,
                "sill_m": observed["sill_m"],
                "head_m": observed["head_m"],
                "evidence_type": observed["evidence_type"],
                "bbox": observed["bbox"],
                "ambiguous": ambiguous,
            }
            safe = (
                not ambiguous
                and abs(position_difference) <= position_tolerance_m
                and abs(width_difference) <= width_tolerance_m
            )
            if safe:
                match["status"] = "matched"
                matches.append(match)
            else:
                match["status"] = "conflict"
                match["type"] = "position_or_width_conflict"
                conflicts.append(match)
        for index in only_left:
            item = left[index]
            elevation_only.append(
                {
                    "artifact_opening_id": item["id"],
                    "floor_id": floor_id,
                    "kind": kind,
                    "world_coordinate_m": item["world_coordinate_m"],
                    "width_m": item["width_m"],
                }
            )
        for index in only_right:
            source_only.append(dict(right[index]))

    artifact_counts = {
        row["floor_id"]: {
            "window": row["window_count"],
            "door": row["door_count"],
        }
        for row in normalized["counts"]
    }
    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        source_counts[row["floor_id"]][row["kind"]] += 1
    count_comparison = []
    for floor_id in sorted(set(artifact_counts) | set(source_counts)):
        expected = artifact_counts.get(floor_id, {"window": 0, "door": 0})
        actual = source_counts[floor_id]
        count_comparison.append(
            {
                "floor_id": floor_id,
                "elevation": dict(expected),
                "source": {"window": actual["window"], "door": actual["door"]},
                "matches": all(expected[kind] == actual[kind] for kind in _OPENING_KINDS),
            }
        )

    result = {
        "schema_version": MATCH_SCHEMA_VERSION,
        "candidate": candidate,
        "source_model_sha256": source_hash,
        "artifact_id": normalized["artifact_id"],
        "artifact_sha256": normalized["artifact_sha256"],
        "orientation": normalized["orientation"],
        "view_direction": normalized["view_direction"],
        "world_axis": calibration["world_axis"],
        "tolerances_m": {
            "position": position_tolerance_m,
            "width": width_tolerance_m,
        },
        "matches": sorted(matches, key=lambda item: (item["floor_id"], item["kind"], sign * item["source_world_coordinate_m"])),
        "elevation_only": elevation_only,
        "source_only": source_only,
        "conflicts": conflicts,
        "counts": count_comparison,
        "can_apply": bool(matches),
        "stale": False,
    }
    result["match_id"] = "elevation_match:" + _canonical_hash(result)[:24]
    return result


def _claim_basis(evidence_type: str) -> str:
    return {
        "annotation": "annotation_and_pixels",
        "annotation_and_pixels": "annotation_and_pixels",
        "pixels": "pixels",
        "visual_estimate": "visual_estimate",
        "assumption": "inference",
        "declared": "declared",
    }[evidence_type]


def height_application(
    artifact: Mapping[str, Any],
    match_result: Mapping[str, Any],
    candidate: str | Mapping[str, Any],
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the current ``claim_transaction`` call for safe height matches.

    ``candidate`` may be a
    current source-model dict; in that form ``provenance={'candidate': 'C01'}``
    supplies its runtime name.  If ``candidate`` is a name, provenance must
    supply ``source_model_sha256``.  Any stale or ambiguous match is rejected.
    """

    normalized = validate_elevation_artifact(artifact)
    report = _mapping(match_result, "match_result")
    if report.get("schema_version") != MATCH_SCHEMA_VERSION:
        raise ValueError(f"match_result.schema_version must be {MATCH_SCHEMA_VERSION!r}")
    provenance = {} if provenance is None else _mapping(provenance, "provenance")
    if isinstance(candidate, Mapping):
        current_source_hash = _string(
            candidate.get("source_model_sha256"), "candidate.source_model_sha256"
        )
        candidate_name = provenance.get("candidate", report.get("candidate"))
    else:
        candidate_name = candidate
        current_source_hash = provenance.get("source_model_sha256")
    candidate_name = _string(candidate_name, "candidate name")
    current_source_hash = _string(current_source_hash, "current source_model_sha256")
    if report.get("stale"):
        raise ValueError("match_result is marked stale")
    if (report.get("source_model_sha256") != current_source_hash
            or report.get("candidate") not in (None, candidate_name)):
        from .lineage import opening_plan
        matched = provenance.get("matched_source_bim")
        current = candidate if isinstance(candidate, Mapping) else provenance.get("source_bim")
        if (not isinstance(matched, Mapping) or not isinstance(current, Mapping)
                or matched.get("source_model_sha256") != report.get("source_model_sha256")
                or current.get("source_model_sha256") != current_source_hash):
            raise ValueError("match_result is stale for the current source model")
        if opening_plan(matched) != opening_plan(current):
            raise ValueError("门窗平面位置或宿主已变化；请对当前稿重新对位 (match_result is stale)")
    if report.get("artifact_sha256") != normalized["artifact_sha256"]:
        raise ValueError("match_result was produced from a different elevation artifact")
    if not report.get("can_apply"):
        raise ValueError("match_result contains no safe height matches")

    by_id = {row["id"]: row for row in normalized["openings"]}
    entries = []
    used_artifact_ids: set[str] = set()
    used_source_ids: set[str] = set()
    for index, raw in enumerate(_sequence(report.get("matches"), "match_result.matches")):
        match = _mapping(raw, f"match_result.matches[{index}]")
        if match.get("status") != "matched" or match.get("ambiguous"):
            raise ValueError(f"match_result.matches[{index}] is not an unambiguous safe match")
        artifact_id = _string(
            match.get("artifact_opening_id"),
            f"match_result.matches[{index}].artifact_opening_id",
        )
        source_id = _string(
            match.get("source_opening_id"),
            f"match_result.matches[{index}].source_opening_id",
        )
        if artifact_id in used_artifact_ids or source_id in used_source_ids:
            raise ValueError("match_result matches must be one-to-one")
        used_artifact_ids.add(artifact_id)
        used_source_ids.add(source_id)
        opening = by_id.get(artifact_id)
        if opening is None:
            raise ValueError(f"match references unknown artifact opening {artifact_id!r}")
        if match.get("kind") != opening["kind"] or match.get("floor_id") != opening["floor_id"]:
            raise ValueError(f"match metadata disagrees with artifact opening {artifact_id!r}")
        basis = _claim_basis(opening["evidence_type"])
        unresolved = []
        if opening["evidence_type"] == "assumption":
            unresolved.append("Height is an explicit assumption, not a measured elevation value.")
        reason = (
            f"Elevation artifact {normalized['artifact_id']} opening {artifact_id}; "
            f"apply absolute building Z [{opening['sill_m']}, {opening['head_m']}] m "
            f"from original-image bbox {opening['bbox']}."
        )
        object_kind = "window" if opening["kind"] == "window" else "opening"
        operation = "update_window" if opening["kind"] == "window" else "update_opening"
        claim = {
            "candidate": candidate_name,
            "objects": [{"kind": object_kind, "id": source_id}],
            "basis": basis,
            "reason": reason,
            "sources": [{"image": normalized["image"], "box": opening["bbox"]}],
            "values": {
                "height": {
                    "type": "literal",
                    "value": [opening["sill_m"], opening["head_m"]],
                    "unit": "m",
                }
            },
            "observation_mode": (
                "candidate_review"
                if opening["evidence_type"] in {"assumption", "declared"}
                else "direct"
            ),
            "unresolved": unresolved,
        }
        entries.append(
            {
                "claim": claim,
                "action": "apply",
                "reason": reason,
                "operations": [
                    {
                        "op": operation,
                        "id": source_id,
                        "changes": {"z": {"claim": "$claim", "value": "height"}},
                        "reason": reason,
                    }
                ],
            }
        )
    if not entries:
        raise ValueError("match_result contains no safe height matches")
    from scripts.tool_scripts.bim_agent_role_heights import build_role_height_batch_entry

    batch = build_role_height_batch_entry(
        entries,
        evidence_types=[
            by_id[match["artifact_opening_id"]]["evidence_type"]
            for match in report["matches"]
        ],
    )
    return {
        "schema_version": APPLICATION_SCHEMA_VERSION,
        "candidate": candidate_name,
        "source_model_sha256": current_source_hash,
        "artifact_id": normalized["artifact_id"],
        "artifact_sha256": normalized["artifact_sha256"],
        "match_id": report.get("match_id"),
        "entries": entries,
        "entries_json": json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
        "batch_entry": batch["entry"],
        "batch_entries_json": batch["entries_json"],
        "batch_per_opening": batch["per_opening"],
        "unprocessed": {
            "elevation_only": report.get("elevation_only", []),
            "source_only": report.get("source_only", []),
            "conflicts": report.get("conflicts", []),
        },
    }


__all__ = [
    "APPLICATION_SCHEMA_VERSION",
    "MATCH_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "height_application",
    "match_elevation",
    "validate_elevation_artifact",
]
