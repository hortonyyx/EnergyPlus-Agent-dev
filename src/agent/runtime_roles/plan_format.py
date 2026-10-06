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


# Use the actual reference example, so guidance and repair feedback cannot drift.
_REFERENCE = REFERENCES["plan_partition"]
PLAN_EXAMPLE, _ = json.JSONDecoder().raw_decode(_REFERENCE[_REFERENCE.index('{"floor_id"'):])


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
    return errors


def format_failure(errors):
    return {"status": "failed", "source_geometry_ready": False, "error_type": "plan_format",
            "format_errors": errors, "reason": f"{len(errors)} plan format problems; correct all listed fields",
            "repair_hint": {"example": copy.deepcopy(PLAN_EXAMPLE),
                            "note": "Complete minimum format from plan_partition; synthetic values are not observations."}}
