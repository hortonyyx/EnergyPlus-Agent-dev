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
import copy
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .readers import ReaderTools
from .submission import ReaderSubmission, _bytes


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

ELEVATION_COORDINATES = (
    "opening_bbox and calibration pixel_start/pixel_end use original-image pixels. "
    "Give distance_start_m/distance_end_m measured from the building's LEFT edge in "
    "this image, increasing left to right, and facade_length_m from the overall "
    "dimension chain. The two pixels locate those distances. The task fixes the facade; "
    "the domain tool derives exterior viewing direction and world axis. "
    "z_calibration maps image top/bottom to absolute Z metres. Preserve annotated numeric readings; only pixels evidence permits unique-ink corrections."
)


def elevation_submission_tool():
    """Facade-only adapter; the shared plan submission module stays untouched."""
    from .submission import ELEVATION_SCHEMA
    schema = copy.deepcopy(ELEVATION_SCHEMA)
    for name in ("orientation", "view_direction"):
        schema["properties"].pop(name)
        schema["required"].remove(name)
    numbers = {name: {"type": "number"} for name in (
        "pixel_start", "pixel_end", "distance_start_m", "distance_end_m",
        "facade_length_m")}
    schema["properties"]["x_calibration"] = {
        "type": "object", "additionalProperties": False, "properties": numbers,
        "required": ["pixel_start", "pixel_end", "distance_start_m",
                     "distance_end_m", "facade_length_m"],
    }
    schema["properties"]["z_calibration"] = {
        "type": "object", "additionalProperties": False,
        "properties": {name: {"type": "number"} for name in
                       ("pixel_start", "pixel_end", "world_start_m", "world_end_m")},
        "required": ["pixel_start", "pixel_end", "world_start_m", "world_end_m"],
    }
    opening = schema["properties"]["openings"]["items"]
    opening["properties"]["opening_bbox"] = {
        "type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}
    opening["required"] = ["id", "floor_id", "kind", "evidence_type"]
    opening["anyOf"] = [
        {"required": ["opening_bbox"]},
        {"required": ["x_px", "width_m", "sill_m", "head_m", "bbox"]},
    ]
    return {"name": "submit_elevation_reading", "description":
        "Submit the assigned facade: horizontal and vertical calibration plus a rough opening_bbox for each opening; "
        "Only pixels evidence allows unique-ink corrections; other evidence needs explicit x_px/width_m/sill_m/head_m, which are retained and checked. "
        "Direction/axis come from task.target. "
        "Counts, locations and the immutable submission are checked.", "inputSchema": schema}


def expand_elevation_submission(arguments, target):
    from .submission import parse_target
    orientation, _ = parse_target("elevation_reader", target)
    if orientation is None:
        raise ValueError("an assigned facade target is required")
    row = copy.deepcopy(_mapping(arguments, "arguments"))
    calibration = _mapping(row.get("x_calibration"), "x_calibration")
    view = {"North": "South", "South": "North", "East": "West", "West": "East"}[orientation]
    if "world_start_m" in calibration:
        # Historical recorded calls contain the expanded internal contract,
        # which is intentionally absent from the current model-facing schema.
        if row.get("orientation", orientation) != orientation:
            raise ValueError("historical elevation orientation conflicts with task.target")
        if row.get("view_direction", view) != view:
            raise ValueError("historical elevation view_direction conflicts with task.target")
        calibration.setdefault("world_axis", _world_axis(orientation))
        row.update(orientation=orientation, view_direction=view, x_calibration=calibration)
        return row
    import jsonschema
    jsonschema.validate(row, elevation_submission_tool()["inputSchema"])
    low = _number(calibration["distance_start_m"], "distance_start_m", minimum=0)
    high = _number(calibration["distance_end_m"], "distance_end_m", minimum=0)
    length = _number(calibration["facade_length_m"], "facade_length_m", minimum=0)
    if not low < high <= length:
        raise ValueError("calibration needs 0 <= distance_start_m < distance_end_m <= facade_length_m")
    start, end = (low, high) if _expected_world_sign(orientation, view) > 0 else (length - low, length - high)
    row.update(orientation=orientation, view_direction=view,
               x_calibration={"pixel_start": calibration["pixel_start"], "pixel_end": calibration["pixel_end"],
                              "world_start_m": start, "world_end_m": end,
                              "world_axis": _world_axis(orientation)})
    return row


class ElevationReaderSubmission(ReaderSubmission):
    """Role-local durable submission that binds deterministic ink alignment."""

    def __init__(self, *args, admitted_image_sha256=None, **kwargs):
        self.admitted_image_sha256 = admitted_image_sha256
        super().__init__(*args, **kwargs)

    def _verified_image(self):
        path = self.directory / "images" / self.image_name if self.directory else None
        if path is None or not path.is_file():
            raise ValueError("admitted elevation image is missing")
        if self.admitted_image_sha256 is None:
            raise ValueError("elevation image is not admitted by the input manifest")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != self.admitted_image_sha256:
            raise ValueError("elevation image changed since reader admission")
        return path, digest

    def read(self):
        value = super().read()
        if value is None or "ink_alignment" not in value.get("artifact", {}):
            return value
        alignment = value["artifact"]["ink_alignment"]
        validation = value.get("validation", {})
        if _canonical_hash(alignment) != validation.get("ink_alignment_sha256"):
            raise ValueError("saved elevation ink alignment hash mismatch")
        path, digest = self._verified_image()
        if path is None or digest != validation.get("image_sha256"):
            raise ValueError("saved elevation ink alignment image changed")
        return value

    def _submit(self, arguments):
        from .height_evidence import derive_z_calibration
        from .elevation_ink import align_elevation_artifact
        from .plan_review import box

        artifact = validate_elevation_artifact(arguments, image_name=self.image_name)
        if self.target_identity is not None and artifact["orientation"] != self.target_identity:
            raise ValueError(f"orientation must match task.target {self.target_identity}")
        floors = {row["floor_id"] for key in ("openings", "elevations", "counts")
                  for row in artifact[key] if row.get("floor_id") is not None}
        if self.target_floors and (not floors <= self.target_floors or
                {row["floor_id"] for row in artifact["counts"]} != self.target_floors):
            raise ValueError(
                f"floor_id/counts must cover exactly task.target floors {sorted(self.target_floors)}"
            )
        for evidence_box in [row["bbox"] for row in artifact["elevations"] + artifact["openings"]]:
            box(evidence_box, self.image_size)
        for opening in artifact["openings"]:
            if opening.get("opening_bbox") is not None:
                box(opening["opening_bbox"], self.image_size)

        z_evidence = derive_z_calibration(artifact["elevations"])
        if artifact.get("z_calibration") is None and z_evidence.get("calibration") is not None:
            artifact = copy.deepcopy(artifact)
            artifact.pop("artifact_sha256", None)
            artifact["z_calibration"] = z_evidence["calibration"]
            artifact = validate_elevation_artifact(artifact, image_name=self.image_name)

        image_path, image_sha256 = self._verified_image()
        validation = {
            "validation_passed": True,
            "image_sha256": image_sha256,
            "z_calibration_evidence": z_evidence,
        }
        alignment = align_elevation_artifact(image_path, artifact)
        artifact = copy.deepcopy(artifact)
        artifact.pop("artifact_sha256", None)
        by_id = {row["id"]: row for row in alignment["openings"]}
        for opening in artifact["openings"]:
            aligned = by_id[opening["id"]]["aligned_values"]
            for field in ("x_px", "width_m", "sill_m", "head_m"):
                if aligned.get(field) is not None:
                    opening[field] = copy.deepcopy(aligned[field])
        artifact["ink_alignment"] = alignment
        artifact = validate_elevation_artifact(artifact, image_name=self.image_name)
        validation["ink_alignment_sha256"] = _canonical_hash(alignment)

        value = {
            "role_id": self.role_id,
            "image": self.image_name,
            "target": self.target,
            "artifact": artifact,
            "artifact_sha256": hashlib.sha256(_bytes(artifact)).hexdigest(),
            "validation": validation,
        }
        previous = self.read()
        if previous is not None and previous != value:
            raise ValueError("this task already has an accepted submission; rework uses a new task_id")
        if previous is None and self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_bytes(_bytes(value))
            temporary.replace(self.path)
        self.value = value
        return {
            "status": "accepted",
            "artifact_sha256": value["artifact_sha256"],
            "plan_sha256": None,
            "unresolved": artifact["unresolved"],
            "next_action": "Submission saved. End your turn with a short acknowledgement; do not repeat the artifact.",
        }


class ElevationReaderTools(ReaderTools):
    """Expose a smaller facade contract, then use the existing durable validator."""

    def __init__(self, frozen, *, role_id, image_name, trial=None, target=None):
        super().__init__(
            frozen, role_id=role_id, image_name=image_name, trial=trial, target=target
        )
        self.submission = ElevationReaderSubmission(
            role_id=role_id,
            image_name=image_name,
            directory=self._scope_directory,
            trial=trial,
            target=target,
            admitted_image_sha256=self._image_sha256,
        )

    async def list_tools(self):
        tools = await super().list_tools()
        tools = [elevation_submission_tool() if tool["name"] == "submit_elevation_reading" else tool
                 for tool in tools]
        self._catalog = {tool["name"]: tool for tool in tools}
        return tools

    async def call_tool(self, name, arguments):
        if name != "submit_elevation_reading":
            return await super().call_tool(name, arguments)
        from .parameters import normalize_stringified_parameters
        from .session import envelope
        import jsonschema
        try:
            arguments = normalize_stringified_parameters(arguments, elevation_submission_tool()["inputSchema"])
            expanded = expand_elevation_submission(arguments, self.submission.target)
            result = await super().call_tool(name, expanded)
            if not result.get("isError"):
                return result
            reason = result["structuredContent"]["reason"].split(". Minimum correct example:", 1)[0]
        except (ValueError, KeyError, TypeError, jsonschema.ValidationError) as error:
            reason = error.message if isinstance(error, jsonschema.ValidationError) else str(error)
        from .guidance import COMPACT_ELEVATION_EXAMPLE
        return envelope({"status": "rejected", "reason": reason,
                         "example": COMPACT_ELEVATION_EXAMPLE}, error=True)


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


def _normalize_z_calibration(value: Any) -> dict[str, float]:
    row = _mapping(value, "z_calibration")
    allowed = {"pixel_start", "pixel_end", "world_start_m", "world_end_m"}
    _allowed(row, allowed, "z_calibration")
    _required(row, allowed, "z_calibration")
    pixel_start = _number(row["pixel_start"], "z_calibration.pixel_start", minimum=0.0)
    pixel_end = _number(row["pixel_end"], "z_calibration.pixel_end", minimum=0.0)
    world_start = _number(row["world_start_m"], "z_calibration.world_start_m")
    world_end = _number(row["world_end_m"], "z_calibration.world_end_m")
    if pixel_start >= pixel_end:
        raise ValueError("z_calibration pixel_start must be less than pixel_end")
    if world_start <= world_end:
        raise ValueError(
            "z_calibration must map image top toward higher absolute building Z"
        )
    return {
        "pixel_start": pixel_start,
        "pixel_end": pixel_end,
        "world_start_m": world_start,
        "world_end_m": world_end,
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


def _normalize_opening(
    value: Any,
    index: int,
    *,
    x_calibration: Mapping[str, Any],
    z_calibration: Mapping[str, Any] | None,
    preserve_aligned: bool,
) -> dict[str, Any]:
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
        "opening_bbox",
    }
    required = {"id", "floor_id", "kind", "evidence_type"}
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
    opening_bbox = (
        _bbox(row["opening_bbox"], f"{path}.opening_bbox")
        if row.get("opening_bbox") is not None else None
    )
    fields = {"x_px", "width_m", "sill_m", "head_m"}
    if opening_bbox is not None and not fields <= set(row):
        if evidence_type != "pixels":
            raise ValueError(f"{path}: non-pixel evidence requires explicit x_px/width_m/sill_m/head_m; a rough box is not an annotation")
        if z_calibration is None:
            raise ValueError(
                f"{path}.opening_bbox requires z_calibration so sill/head are not invented"
            )
        row.setdefault("x_px", [opening_bbox[0], opening_bbox[2]])
        row.setdefault("width_m", abs(_pixel_to_world(x_calibration, row["x_px"][1])
                                      - _pixel_to_world(x_calibration, row["x_px"][0])))
        row.setdefault("head_m", _pixel_to_world(z_calibration, opening_bbox[1]))
        row.setdefault("sill_m", _pixel_to_world(z_calibration, opening_bbox[3]))
    _required(row, fields, path)
    x_px = _pair(row["x_px"], f"{path}.x_px", positive_span=True)
    width = _number(row["width_m"], f"{path}.width_m", minimum=1e-12)
    sill = _number(row["sill_m"], f"{path}.sill_m")
    head = _number(row["head_m"], f"{path}.head_m")
    if head <= sill:
        raise ValueError(
            f"{path}.head_m must exceed sill_m; both are absolute building Z"
        )
    result = {
        "id": _string(row["id"], f"{path}.id"),
        "floor_id": _string(row["floor_id"], f"{path}.floor_id"),
        "kind": kind,
        "x_px": x_px,
        "width_m": width,
        "sill_m": sill,
        "head_m": head,
        "evidence_type": evidence_type,
        "bbox": _bbox(row.get("bbox", opening_bbox), f"{path}.bbox"),
    }
    if opening_bbox is not None:
        result["opening_bbox"] = opening_bbox
    return result


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
        "z_calibration",
        "elevations",
        "openings",
        "counts",
        "unresolved",
        "artifact_sha256",
        "ink_alignment",
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
    z_calibration = (
        _normalize_z_calibration(row["z_calibration"])
        if row.get("z_calibration") is not None else None
    )
    elevations = [
        _normalize_elevation(item, index)
        for index, item in enumerate(_sequence(row["elevations"], "elevations"))
    ]
    if not elevations:
        raise ValueError("elevations must contain at least one located level")
    openings = [
        _normalize_opening(
            item,
            index,
            x_calibration=calibration,
            z_calibration=z_calibration,
            preserve_aligned=row.get("ink_alignment") is not None,
        )
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
    if z_calibration is not None:
        normalized["z_calibration"] = z_calibration
    if row.get("ink_alignment") is not None:
        alignment = _mapping(row["ink_alignment"], "ink_alignment")
        if alignment.get("schema_version") not in {"elevation_ink_alignment_v1", "elevation_ink_alignment_v2"}:
            raise ValueError("ink_alignment has an unsupported schema_version")
        aligned_rows = _sequence(alignment.get("openings"), "ink_alignment.openings")
        if [item.get("id") for item in aligned_rows if isinstance(item, Mapping)] != opening_ids:
            raise ValueError("ink_alignment openings do not match artifact openings")
        normalized["ink_alignment"] = copy.deepcopy(alignment)
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
                "world_span_m": sorted(point[axis_index] for point in unique_planar),
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


def _horizontal_fit(elevation, source, *, position_tolerance_m, width_tolerance_m):
    """Fit a complete, uniquely ordered group, never a selected subset.

    Three points leave a residual check (two always fit perfectly). Widths stay
    independent observations; neither a count match nor a fit can waive them.
    These conservative limits cover the measured 2.4% drift in sm24 run7.
    """
    if len(elevation) != len(source) or len(elevation) < 3:
        return None
    x = [row["world_coordinate_m"] for row in elevation]
    y = [row["world_coordinate_m"] for row in source]
    residual_limit = min(0.10, position_tolerance_m)
    if (max(x) - min(x) < 1.4 or max(y) - min(y) < 1.4
            or any(abs(b - a) <= 2 * residual_limit for values in (x, y)
                   for a, b in zip(values, values[1:]))):
        return None
    if any(abs(left["width_m"] - right["width_m"]) > width_tolerance_m
           for left, right in zip(elevation, source, strict=True)):
        return None
    mean_x, mean_y = sum(x) / len(x), sum(y) / len(y)
    scale = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True)) / sum(
        (a - mean_x) ** 2 for a in x)
    offset = mean_y - scale * mean_x
    residual = max(abs(scale * a + offset - b) for a, b in zip(x, y, strict=True))
    if not (0.90 <= scale <= 1.10 and abs(offset) <= position_tolerance_m
            and residual <= residual_limit):
        return None
    if any(abs(scale * left["calibrated_width_m"] - left["width_m"]) > width_tolerance_m
           for left in elevation):
        return None
    return {"scale": scale, "offset_m": offset, "max_residual_m": residual,
            "residual_tolerance_m": residual_limit, "opening_count": len(x),
            "method": "complete_ordered_group_least_squares"}


def compare_opening_positions(plan_span, elevation_span, *, tolerance_m=0.10):
    """Compare independent world endpoints, never fitted coordinates or an average."""
    plan = _pair(plan_span, "plan_span", positive_span=True)
    elevation = _pair(elevation_span, "elevation_span", positive_span=True)
    differences = {"left": elevation[0] - plan[0], "right": elevation[1] - plan[1],
                   "width": (elevation[1] - elevation[0]) - (plan[1] - plan[0])}
    maximum = max(abs(value) for value in differences.values())
    return {"plan_span_m": plan, "elevation_span_m": elevation,
            "plan_width_m": plan[1] - plan[0], "elevation_width_m": elevation[1] - elevation[0],
            "differences_m": differences, "max_difference_m": maximum,
            "status": "keep_plan" if maximum <= tolerance_m + 1e-9 else "pending",
            "bucket": "le_10cm" if maximum <= tolerance_m + 1e-9 else (
                "10_30cm" if maximum <= 0.30 + 1e-9 else "gt_30cm"),
            "requires_both_views": maximum > 0.30 + 1e-9}


def attach_ink_review(comparison, inconsistencies):
    """Keep the independent numeric comparison; add unresolved image evidence."""
    comparison["ink_inconsistencies"] = copy.deepcopy(inconsistencies)
    maximum = max((row["difference_m"] for row in inconsistencies), default=0.0)
    comparison["ink_max_difference_m"] = maximum
    width_conflict = comparison.get("width_span_conflict")
    if width_conflict:
        maximum = max(maximum, width_conflict["difference_m"])
    comparison["evidence_max_difference_m"] = maximum
    if inconsistencies or width_conflict:
        if comparison["status"] == "keep_plan":
            comparison["status"] = "pending"
        comparison["requires_both_views"] |= maximum > 0.30 + 1e-9
    return comparison


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
    horizontal_fits = []
    position_comparisons = []
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
        fit = None
        if (not ambiguous and not only_left and not only_right
                and any(abs(left[i]["world_coordinate_m"] - right[j]["world_coordinate_m"])
                        > position_tolerance_m for i, j in pairs)):
            fit = _horizontal_fit(left, right, position_tolerance_m=position_tolerance_m,
                                  width_tolerance_m=width_tolerance_m)
            if fit:
                horizontal_fits.append({"floor_id": floor_id, "kind": kind, **fit})
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
            aligned = (fit["scale"] * observed["world_coordinate_m"] + fit["offset_m"]
                       if fit else observed["world_coordinate_m"])
            position_difference = aligned - actual["world_coordinate_m"]
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
            if fit:
                match.update(horizontal_fit=fit, aligned_world_coordinate_m=aligned,
                             raw_position_difference_m=observed["world_coordinate_m"] - actual["world_coordinate_m"])
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
            if not ambiguous:
                independent = compare_opening_positions(actual["world_span_m"], sorted(
                    _pixel_to_world(calibration, x) for x in observed["x_px"]))
                alignment = next((r for r in normalized.get("ink_alignment", {}).get("openings", [])
                                  if r["id"] == observed["id"]), None)
                span_width = independent["elevation_width_m"]
                width_tolerance = max(0.05, 2 * abs((calibration["world_end_m"] - calibration["world_start_m"])
                                                   / (calibration["pixel_end"] - calibration["pixel_start"])))
                independent.update(reader_width_m=observed["width_m"], width_span_conflict=None)
                if observed["evidence_type"] != "pixels" and abs(observed["width_m"] - span_width) > width_tolerance + 1e-9:
                    independent["width_span_conflict"] = {"reader_width_m": observed["width_m"],
                        "pixel_span_width_m": span_width, "difference_m": abs(observed["width_m"] - span_width),
                        "tolerance_m": width_tolerance,
                        "reason": "retained_numeric_width_disagrees_with_pixel_interval; reread_before_using_elevation"}
                attach_ink_review(independent, (alignment or {}).get("inconsistencies", []))
                evidence_box = list(observed["bbox"])
                for box in (() if not alignment else (alignment["aligned_bbox_px"], alignment.get("candidate_bbox_px", []))):
                    if len(box) == 4 and all(isinstance(v, (int, float)) for v in box):
                        evidence_box = [min(evidence_box[0], box[0]), min(evidence_box[1], box[1]),
                                        max(evidence_box[2], box[2]), max(evidence_box[3], box[3])]
                position_comparisons.append({**independent,
                    "source_opening_id": actual["source_id"], "artifact_opening_id": observed["id"],
                    "floor_id": floor_id, "kind": kind, "identity_matched": safe,
                    "orientation": normalized["orientation"], "world_axis": calibration["world_axis"],
                    "elevation_evidence": {"image": normalized["image"], "bbox": evidence_box,
                        "evidence_type": observed["evidence_type"], "x_px": observed["x_px"],
                        "reader_values": {key: observed[key] for key in ("width_m", "sill_m", "head_m")},
                        "x_calibration": calibration, "ink_alignment": alignment},
                    "identity_fit": fit})
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
        "horizontal_fits": horizontal_fits,
        "position_comparisons": position_comparisons,
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
