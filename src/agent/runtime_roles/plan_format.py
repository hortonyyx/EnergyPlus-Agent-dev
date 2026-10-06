"""Collect plan-reader format errors without changing the shared compiler."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping

from jsonschema import Draft202012Validator, validators

from scripts.tool_scripts.bim_agent_guidance import REFERENCES
from src.agent.geometry.plan_partition import (
    _OPENING_FIELDS, _PARTITION_FIELDS, _PLAN_FIELDS, _REQUIRED_PLAN_FIELDS, _SEED_FIELDS,
)
from src.agent.roles import ROOM_TYPES, normalize


# Use the actual reference example, so guidance and repair feedback cannot drift.
_REFERENCE = REFERENCES["plan_partition"]
PLAN_EXAMPLE, _ = json.JSONDecoder().raw_decode(_REFERENCE[_REFERENCE.index('{"floor_id"'):])


def _reader_example(example):
    """The same plan at image scale. The shared example's single-digit pixels read
    like metres, and a reader copied that into world-metre points (10-06 probe)."""
    def pixel(value, offset):
        value = offset + 40 * value
        return int(value) if float(value).is_integer() else value

    def point(row):
        return [pixel(row[0], 100), pixel(row[1], 80)]

    value = copy.deepcopy(example)
    value["x_anchors"] = [[pixel(px, 100), metres] for px, metres in value["x_anchors"]]
    value["y_anchors"] = [[pixel(px, 80), metres] for px, metres in value["y_anchors"]]
    value["footprint_pixels"] = [point(row) for row in value["footprint_pixels"]]
    for row in value["partitions"]:
        row["points"] = [point(item) for item in row["points"]]
    for row in value["openings"]:
        row["p1"], row["p2"] = point(row["p1"]), point(row["p2"])
    for row in value["space_seeds"]:
        row["point"] = point(row["point"])
    return value


READER_PLAN_EXAMPLE = _reader_example(PLAN_EXAMPLE)
COMMON_ROOM_TYPES = ("office", "conference/meeting/multipurpose", "corridor", "lobby",
                     "storage", "restroom", "stairwell")
assert set(COMMON_ROOM_TYPES) <= set(ROOM_TYPES)


def _object(properties, required):
    return {"type": "object", "properties": properties,
            "required": sorted(required), "additionalProperties": False}


def _array(items, minimum=0, maximum=None):
    return {"type": "array", "items": items, "minItems": minimum,
            **({"maxItems": maximum} if maximum is not None else {})}


TEXT = {"type": "string", "pattern": r"\S"}
NUMBER = {"type": "number"}
STRINGS = _array(TEXT)
REFS = _array(TEXT, 1)
PROFILE = _object({"profile": {"type": "string", "pattern": r"^profile_[0-9]{3,}$"},
                   "candidate": TEXT, "at": {"enum": ["peak", "start", "end"]}},
                  {"profile", "candidate"})
PIXEL = {"anyOf": [NUMBER, PROFILE, _object({"midpoint": _array(PROFILE, 2, 2)}, {"midpoint"})]}
LENGTH = {"anyOf": [NUMBER, _object({"value": NUMBER, "unit": {"enum": ["m", "cm", "mm"]}},
                                   {"value", "unit"})]}
POINT = _array(PIXEL, 2, 2)
ANCHOR = {"type": "array", "prefixItems": [PIXEL, LENGTH], "items": False,
          "minItems": 2, "maxItems": 2}
PARTITION = _object({"id": TEXT, "points": _array(POINT, 2), "source_refs": REFS}, _PARTITION_FIELDS)
SEED = _object({"id": TEXT, "point": POINT, "role": TEXT, "source_refs": STRINGS}, {"id", "point"})
OPENING = _object({"id": TEXT, "kind": {"enum": ["window", "door", "open"]},
                   "p1": POINT, "p2": POINT, "z": _array(LENGTH, 2, 2), "source_refs": REFS,
                   "state": {"enum": [None, "unknown", "open", "closed"]}, "assumptions": STRINGS},
                  {"id", "kind", "p1", "p2", "z", "source_refs"})
PLAN_FORMAT = _object({
    "floor_id": TEXT, "z_floor": LENGTH, "ceiling_height": LENGTH, "basis": TEXT,
    "x_anchors": _array(ANCHOR, 2, 2), "y_anchors": _array(ANCHOR, 2, 2),
    "footprint_pixels": _array(POINT, 4), "partitions": _array(PARTITION),
    "space_seeds": _array(SEED), "openings": _array(OPENING),
    "assumptions": STRINGS, "unresolved": STRINGS,
}, _REQUIRED_PLAN_FIELDS)
assert set(PLAN_FORMAT["properties"]) == _PLAN_FIELDS
assert set(OPENING["properties"]) == _OPENING_FIELDS
assert set(SEED["properties"]) == _SEED_FIELDS

_Validator = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    "number", lambda checker, value: isinstance(value, (int, float))
    and not isinstance(value, bool) and math.isfinite(value)))


def _path(parts):
    return "plan" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts)


def plan_format_errors(plan):
    """Check every entry and alias; never infer missing fields or repair geometry."""
    value = copy.deepcopy(plan)
    errors = []
    if isinstance(value, Mapping):
        for collection, field in (("partitions", "points"), ("space_seeds", "point")):
            rows = value.get(collection, [])
            for index, row in enumerate(rows if isinstance(rows, list) else []):
                if isinstance(row, dict) and "pixels" in row:
                    if field in row:
                        errors.append({"path": f"plan.{collection}[{index}]",
                                       "message": f"both pixels and {field} supplied; use only {field}"})
                        row.pop("pixels")
                    else:
                        row[field] = row.pop("pixels")
    for error in _Validator(PLAN_FORMAT).iter_errors(value):
        errors.append({"path": _path(error.absolute_path), "message": error.message})
    if isinstance(value, Mapping):
        for collection in ("partitions", "openings", "space_seeds"):
            seen = set()
            rows = value.get(collection, [])
            for index, row in enumerate(rows if isinstance(rows, list) else []):
                if not isinstance(row, Mapping):
                    continue
                identity = row.get("id")
                if isinstance(identity, str):
                    if identity in seen:
                        errors.append({"path": f"plan.{collection}[{index}].id", "message": f"duplicate id {identity!r}"})
                    seen.add(identity)
                if collection == "openings" and row.get("state") is not None:
                    if row.get("kind") == "window" or (row.get("kind") == "open" and row["state"] != "open"):
                        errors.append({"path": f"plan.openings[{index}].state",
                                       "message": "window state must be omitted; open passage state must be open or omitted"})
                role = row.get("role") if collection == "space_seeds" else None
                if isinstance(role, str) and (normalize(role) or "unknown") not in ROOM_TYPES:
                    errors.append({"path": f"plan.space_seeds[{index}].role",
                                   "message": f"{role!r} is not a room_types code; omit role or use one such as "
                                              + ", ".join(COMMON_ROOM_TYPES) + " (full list: get_bim_reference('room_types'))"})
        errors.extend(_points_outside_footprint(value))
    return errors


def _pixel_point(value):
    return (isinstance(value, list) and len(value) == 2 and all(
        isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item) for item in value))


def _points_outside_footprint(plan):
    """Name objects whose numeric points fall clearly outside the footprint's pixel box.

    Plan points are original pixels; a divider written in world metres lands near the
    image origin. Profile references are not resolved here and are skipped.
    """
    ring = plan.get("footprint_pixels")
    if not isinstance(ring, list) or len(ring) < 3 or not all(_pixel_point(row) for row in ring):
        return []
    xs, ys = [row[0] for row in ring], [row[1] for row in ring]
    margin = 0.05 * max(max(xs) - min(xs), max(ys) - min(ys), 1)
    left, top, right, bottom = min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin
    found = []
    for collection, fields in (("partitions", ("points",)), ("openings", ("p1", "p2")), ("space_seeds", ("point",))):
        rows = plan.get(collection)
        for index, row in enumerate(rows if isinstance(rows, list) else []):
            if not isinstance(row, Mapping):
                continue
            points = []
            for field in fields:
                value = row.get(field)
                points.extend(value if field == "points" and isinstance(value, list) else [value])
            outside = [point for point in points if _pixel_point(point)
                       and not (left <= point[0] <= right and top <= point[1] <= bottom)]
            if outside:
                found.append({"path": f"plan.{collection}[{index}]",
                              "message": f"points {outside[:2]} lie outside the footprint pixels "
                                         f"(x {min(xs):g}-{max(xs):g}, y {min(ys):g}-{max(ys):g}); plan points are "
                                         "original-image pixels, never world metres"})
    return found


def format_failure(errors):
    return {"status": "failed", "source_geometry_ready": False, "error_type": "plan_format",
            "format_errors": errors, "reason": f"{len(errors)} plan format problems; correct all listed fields",
            "repair_hint": {"example": copy.deepcopy(READER_PLAN_EXAMPLE),
                            "note": "Complete minimum format (plan_partition example at image scale); synthetic values are not observations."}}
