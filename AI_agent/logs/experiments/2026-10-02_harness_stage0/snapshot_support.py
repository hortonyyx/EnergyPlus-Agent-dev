"""Deterministically extract contract snapshots from persisted source BIM files.

The caller selects dimensions to expose, but never supplies semantic inventory,
opening geometry, hosts, or connectivity.  Those values are rebuilt from the
saved ``source_bim_v1`` artifact and its own cross-references.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from pydantic import model_validator

from src.agent.contracts import (
    BuildingObjectRef,
    ConnectivityState,
    DimensionState,
    OpeningSemanticState,
    SavedModelSnapshot,
    SemanticSnapshot,
)
from src.agent.contracts._base import ContractModel, NonEmptyStr


_HOST_TOLERANCE_M = 2e-5


class SnapshotDimensionSource(ContractModel):
    """One numeric value copied from the saved artifact by JSON Pointer."""

    object_ref: BuildingObjectRef
    field_path: NonEmptyStr
    source_pointer: NonEmptyStr

    @model_validator(mode="after")
    def validate_paths(self) -> "SnapshotDimensionSource":
        if not self.field_path.startswith("/") or not self.source_pointer.startswith("/"):
            raise ValueError("snapshot dimension paths must be absolute JSON Pointers")
        return self


def snapshot_source_bim(
    source_bim_path: str | Path,
    *,
    model_version_id: str,
    dimensions: Sequence[SnapshotDimensionSource] = (),
) -> SavedModelSnapshot:
    """Read one persisted source BIM and return an artifact-bound snapshot.

    Only the path, version label, and dimension selectors are accepted.  This
    deliberately provides no argument through which a caller can inject a
    semantic snapshot or stale opening coordinates.
    """

    path = Path(source_bim_path)
    raw = path.read_bytes()
    artifact_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        source = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"saved source BIM is not valid UTF-8 JSON: {path}") from exc
    if not isinstance(source, dict) or source.get("schema_version") not in {
        "source_bim_v1",
        "source_bim_v2",
    }:
        raise ValueError("semantic snapshots support persisted source_bim_v1/v2 artifacts only")
    _verify_internal_digest(source)
    semantics = _semantic_snapshot(source)
    extracted = tuple(_dimension(source, selector) for selector in dimensions)
    return SavedModelSnapshot(
        model_version_id=model_version_id,
        artifact_sha256=artifact_sha256,
        semantics=semantics,
        dimensions=extracted,
    )


def _semantic_snapshot(source: Mapping[str, Any]) -> SemanticSnapshot:
    spaces = _objects(source, "spaces")
    boundaries = _objects(source, "boundaries")
    openings = _objects(source, "openings")
    connections = source.get("connections")
    if not isinstance(connections, list):
        raise ValueError("source BIM connections must be a list")

    space_by_id = _unique_index(spaces, "space")
    boundary_by_id = _unique_index(boundaries, "boundary")
    opening_by_id = _unique_index(openings, "opening")

    floor_ids: set[str] = set()
    for space_id, space in space_by_id.items():
        floor_id = space.get("floor_id")
        if not isinstance(floor_id, str) or not floor_id:
            raise ValueError(f"space {space_id!r} has no valid floor_id")
        floor_ids.add(floor_id)

    wall_ids = {
        boundary_id
        for boundary_id, boundary in boundary_by_id.items()
        if boundary.get("geometry_type") == "wall"
    }
    semantic_openings: list[OpeningSemanticState] = []
    derived_connections: dict[str, tuple[str, str]] = {}
    for opening_id, opening in opening_by_id.items():
        kind = opening.get("kind")
        if kind not in {"window", "door", "open"}:
            raise ValueError(f"opening {opening_id!r} has unsupported kind {kind!r}")
        host_id = opening.get("host_boundary_id")
        if not isinstance(host_id, str) or host_id not in boundary_by_id:
            raise ValueError(f"opening {opening_id!r} references an unknown host boundary")
        host = boundary_by_id[host_id]
        if host.get("geometry_type") != "wall":
            raise ValueError(f"opening {opening_id!r} host is not a wall")
        space_ids = opening.get("space_ids")
        if (
            not isinstance(space_ids, list)
            or not space_ids
            or any(not isinstance(value, str) or value not in space_by_id for value in space_ids)
            or len(space_ids) != len(set(space_ids))
        ):
            raise ValueError(f"opening {opening_id!r} has invalid source-space references")
        if host.get("space_id") not in space_ids:
            raise ValueError(f"opening {opening_id!r} host does not belong to a connected space")
        if len(space_ids) > 2:
            raise ValueError(f"opening {opening_id!r} connects more than two source spaces")

        p1, p2, z_range = _opening_geometry(opening_id, opening.get("vertices"))
        _assert_opening_on_host(opening_id, p1, p2, z_range, host.get("vertices"))
        semantic_openings.append(
            OpeningSemanticState(
                object_kind="window" if kind == "window" else "opening",
                opening_id=opening_id,
                host_ids=(host_id,),
                p1=p1,
                p2=p2,
                z_range=z_range,
            )
        )
        if kind != "window":
            exterior = opening.get("exterior")
            expected_exterior = len(space_ids) == 1
            if not isinstance(exterior, bool) or exterior != expected_exterior:
                raise ValueError(f"opening {opening_id!r} has inconsistent exterior/connectivity state")
            pair = (
                (space_ids[0], "exterior")
                if expected_exterior
                else tuple(sorted(space_ids))
            )
            derived_connections[opening_id] = pair

    declared_connections: dict[str, tuple[str, str]] = {}
    for row in connections:
        if not isinstance(row, dict):
            raise ValueError("source BIM connection entries must be objects")
        opening_id = row.get("opening_id")
        if not isinstance(opening_id, str) or opening_id in declared_connections:
            raise ValueError("source BIM connection opening IDs must be unique strings")
        if opening_id not in derived_connections:
            raise ValueError(f"connection {opening_id!r} has no door/open source object")
        space_ids = row.get("space_ids")
        exterior = row.get("exterior")
        if not isinstance(space_ids, list) or not isinstance(exterior, bool):
            raise ValueError(f"connection {opening_id!r} has invalid space/exterior fields")
        pair = (
            (space_ids[0], "exterior")
            if exterior and len(space_ids) == 1
            else tuple(sorted(space_ids)) if not exterior and len(space_ids) == 2
            else None
        )
        if pair is None or pair != derived_connections[opening_id]:
            raise ValueError(f"connection {opening_id!r} disagrees with its saved opening")
        declared_connections[opening_id] = pair
    if declared_connections != derived_connections:
        missing = sorted(set(derived_connections) - set(declared_connections))
        raise ValueError(f"source BIM omits opening connectivity rows: {missing}")

    return SemanticSnapshot(
        floor_ids=tuple(sorted(floor_ids)),
        wall_ids=tuple(sorted(wall_ids)),
        room_ids=tuple(sorted(space_by_id)),
        openings=tuple(sorted(semantic_openings, key=lambda row: row.opening_id)),
        connectivity=tuple(
            ConnectivityState(connection_id=opening_id, object_ids=pair)
            for opening_id, pair in sorted(derived_connections.items())
        ),
    )


def _objects(source: Mapping[str, Any], field: str) -> list[dict[str, Any]]:
    value = source.get(field)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"source BIM {field} must be a list of objects")
    return value


def _unique_index(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        identity = row.get("id")
        if not isinstance(identity, str) or not identity or identity in result:
            raise ValueError(f"source BIM {label} IDs must be unique non-empty strings")
        result[identity] = row
    return result


def _opening_geometry(
    opening_id: str, vertices: Any
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    if not isinstance(vertices, list) or len(vertices) < 4:
        raise ValueError(f"opening {opening_id!r} needs at least four saved vertices")
    parsed = [_point3(value, f"opening {opening_id!r} vertex") for value in vertices]
    low, high = min(p[2] for p in parsed), max(p[2] for p in parsed)
    if high - low <= _HOST_TOLERANCE_M:
        raise ValueError(f"opening {opening_id!r} has no positive saved height")
    lower_xy = sorted({(p[0], p[1]) for p in parsed if abs(p[2] - low) <= _HOST_TOLERANCE_M})
    all_xy = sorted({(p[0], p[1]) for p in parsed})
    if len(lower_xy) != 2 or all_xy != lower_xy or lower_xy[0] == lower_xy[1]:
        raise ValueError(f"opening {opening_id!r} vertices do not form one vertical planar span")
    return lower_xy[0], lower_xy[1], (low, high)


def _assert_opening_on_host(
    opening_id: str,
    p1: tuple[float, float],
    p2: tuple[float, float],
    z_range: tuple[float, float],
    host_vertices: Any,
) -> None:
    if not isinstance(host_vertices, list) or len(host_vertices) < 4:
        raise ValueError(f"opening {opening_id!r} host has invalid vertices")
    host = [_point3(value, f"opening {opening_id!r} host vertex") for value in host_vertices]
    low_z, high_z = min(p[2] for p in host), max(p[2] for p in host)
    if z_range[0] < low_z - _HOST_TOLERANCE_M or z_range[1] > high_z + _HOST_TOLERANCE_M:
        raise ValueError(f"opening {opening_id!r} lies outside its host's vertical range")
    low_points = [(p[0], p[1]) for p in host if abs(p[2] - low_z) <= _HOST_TOLERANCE_M]
    unique_low = list(dict.fromkeys(low_points))
    if len(unique_low) != 2:
        raise ValueError(f"opening {opening_id!r} host is not one vertical wall segment")
    a, b = unique_low
    for point in (p1, p2):
        if not _point_on_segment(point, a, b, _HOST_TOLERANCE_M):
            raise ValueError(f"opening {opening_id!r} vertices do not lie on the saved host wall")


def _point_on_segment(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
    tolerance: float,
) -> bool:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 <= tolerance * tolerance:
        return False
    cross = abs((point[0] - a[0]) * dy - (point[1] - a[1]) * dx)
    if cross / math.sqrt(length2) > tolerance:
        return False
    projection = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2
    margin = tolerance / math.sqrt(length2)
    return -margin <= projection <= 1 + margin


def _point3(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must contain x, y, z")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value):
        raise ValueError(f"{label} coordinates must be numbers")
    result = tuple(float(v) for v in value)
    if not all(math.isfinite(v) for v in result):
        raise ValueError(f"{label} coordinates must be finite")
    return result


def _dimension(source: Mapping[str, Any], selector: SnapshotDimensionSource) -> DimensionState:
    value = _resolve_pointer(source, selector.source_pointer)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"dimension source {selector.source_pointer!r} is not a finite number")
    return DimensionState(
        object_ref=selector.object_ref,
        field_path=selector.field_path,
        value_m=float(value),
    )


def _resolve_pointer(value: Any, pointer: str) -> Any:
    current = value
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not part.isdigit() or int(part) >= len(current):
                raise ValueError(f"dimension source pointer does not exist: {pointer}")
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError(f"dimension source pointer does not exist: {pointer}")
    return current


def _verify_internal_digest(source: Mapping[str, Any]) -> None:
    claimed = source.get("source_model_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("source BIM has no valid source_model_sha256")
    payload = dict(source)
    payload.pop("source_model_sha256", None)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    actual = hashlib.sha256(encoded).hexdigest()
    if actual != claimed:
        raise ValueError("source BIM internal content hash does not match its saved content")


__all__ = ["SnapshotDimensionSource", "snapshot_source_bim"]
