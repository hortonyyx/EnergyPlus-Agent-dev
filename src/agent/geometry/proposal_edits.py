"""Deterministic, auditable local edits for direct legacy geometry proposals."""
from __future__ import annotations

import copy
import math

from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.correction.schema import Window


_PROPOSAL_FIELDS = {"geometry", "assumptions", "unresolved", "enclosure_declaration"}
_WINDOW_FIELDS = {"facade", "span", "z", "room", "floor", "assumptions"}
_OPENING_FIELDS = {"space_id", "other_space_id", "p1", "p2", "z", "state", "assumptions"}
_FACADE_REFLECTIONS = {
    "x": {"East": "West", "West": "East", "North": "North", "South": "South"},
    "y": {"North": "South", "South": "North", "East": "East", "West": "West"},
}
_DIRECTION_NOTICE = (
    "Existing assumptions may contain direction language and require review; "
    "use set_notes to replace them."
)


def _require_fields(row: dict, allowed: set[str], *, operation: str) -> None:
    unknown = set(row) - allowed
    if unknown:
        raise ValueError(f"{operation}: unknown fields {sorted(unknown)}")


def _nonblank_string(value: object, *, field: str, operation: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{operation}: {field} must be a nonblank string")
    return value


def _source_refs(value: object, *, operation: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(row, str) or not row.strip() for row in value):
        raise ValueError(f"{operation}: source_refs must be a nonempty list of nonblank strings")
    return list(value)


def _notes(value: object, *, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(row, str) for row in value):
        raise ValueError(f"set_notes: {field} must be a list of strings")
    return list(value)


def _validate_proposal(proposal: dict) -> dict:
    if not isinstance(proposal, dict):
        raise TypeError("proposal must be an object")
    _require_fields(proposal, _PROPOSAL_FIELDS, operation="proposal")
    missing = {"geometry", "assumptions", "unresolved"} - set(proposal)
    if missing:
        raise ValueError(f"proposal: missing fields {sorted(missing)}")
    geometry = proposal["geometry"]
    if not isinstance(geometry, dict):
        raise TypeError("proposal.geometry must be an object")
    version = str(geometry.get("schema_version", "1"))
    if version not in {"1", "2"}:
        raise ValueError("proposal geometry must use legacy schema_version 1 or 2")
    _notes(proposal["assumptions"], field="assumptions")
    _notes(proposal["unresolved"], field="unresolved")
    enclosure = proposal.get("enclosure_declaration")
    if enclosure is not None and not isinstance(enclosure, dict):
        raise TypeError("proposal.enclosure_declaration must be an object")
    ensure_corrected_geometry(geometry)
    return geometry


def _unique_ids(geometry: dict) -> None:
    identities = []
    for floor in geometry.get("floors", []):
        identities.extend(("space", row.get("id")) for row in floor.get("cells", []))
    identities.extend(("opening", row.get("id")) for row in geometry.get("windows", []))
    identities.extend(("opening", row.get("id")) for row in geometry.get("openings", []))
    seen = set()
    for kind, identity in identities:
        if not isinstance(identity, str) or not identity:
            raise ValueError(f"{kind} identity must be a nonempty string")
        if (kind, identity) in seen:
            raise ValueError(f"duplicate {kind} id: {identity}")
        seen.add((kind, identity))


def _interval_reflected(interval: list[float], midpoint: float) -> list[float]:
    if not isinstance(interval, list) or len(interval) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in interval):
        raise ValueError("reflection requires finite two-value coordinate intervals")
    return [2 * midpoint - interval[1], 2 * midpoint - interval[0]]


def _reflect_point(point: list[float], *, axis: str, midpoint: float) -> list[float]:
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError("reflection requires two-dimensional points")
    x, y = point
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (x, y)):
        raise ValueError("reflection requires finite point coordinates")
    return [2 * midpoint - x, y] if axis == "x" else [x, 2 * midpoint - y]


def _reflect(geometry: dict, *, axis: str, reason: str) -> dict:
    if axis not in {"x", "y"}:
        raise ValueError("reflect: axis must be x or y")
    interval_name = f"footprint_{axis}"
    interval = geometry.get(interval_name)
    if not isinstance(interval, list) or len(interval) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in interval):
        raise ValueError(f"reflect: {interval_name} must contain two finite coordinates")
    midpoint = (interval[0] + interval[1]) / 2
    geometry[interval_name] = _interval_reflected(interval, midpoint)
    for floor in geometry.get("floors", []):
        if floor.get("footprint"):
            raise ValueError("reflect: nonempty floor.footprint requires an explicit per-floor footprint edit")
        for cell in floor.get("cells", []):
            cell[axis] = _interval_reflected(cell[axis], midpoint)
            polygon = cell.get("polygon")
            if polygon is not None:
                reflected = [_reflect_point(point, axis=axis, midpoint=midpoint) for point in polygon]
                # A reflection reverses winding. Keep the original ring orientation
                # and its first vertex's identity stable for downstream references.
                cell["polygon"] = reflected[:1] + list(reversed(reflected[1:]))
    for window in geometry.get("windows", []):
        facade = Window.model_validate(window).facade
        if (axis == "x" and facade in {"North", "South"}) or (axis == "y" and facade in {"East", "West"}):
            window["span"] = _interval_reflected(window["span"], midpoint)
        window["facade"] = _FACADE_REFLECTIONS[axis][facade]
    for opening in geometry.get("openings", []):
        opening["p1"] = _reflect_point(opening["p1"], axis=axis, midpoint=midpoint)
        opening["p2"] = _reflect_point(opening["p2"], axis=axis, midpoint=midpoint)
    return {
        "operation": "reflect",
        "reason": reason,
        "transform": {"axis": axis, "about_world_coordinate": midpoint},
        "notice": _DIRECTION_NOTICE,
    }


def _find(rows: list[dict], identity: str, *, operation: str) -> dict:
    matches = [row for row in rows if row.get("id") == identity]
    if len(matches) != 1:
        raise ValueError(f"{operation}: expected exactly one existing id {identity!r}, found {len(matches)}")
    return matches[0]


def _update(geometry: dict, operation: dict, *, target: str) -> dict:
    name = operation["op"]
    _require_fields(operation, {"op", "id", "changes", "reason", "source_refs"}, operation=name)
    identity = _nonblank_string(operation.get("id"), field="id", operation=name)
    reason = _nonblank_string(operation.get("reason"), field="reason", operation=name)
    refs = _source_refs(operation.get("source_refs"), operation=name)
    changes = operation.get("changes")
    allowed = _WINDOW_FIELDS if target == "window" else _OPENING_FIELDS
    if not isinstance(changes, dict) or not changes:
        raise ValueError(f"{name}: changes must be a nonempty object")
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"{name}: unsupported changes {sorted(unknown)}")
    if "assumptions" in changes:
        _notes(changes["assumptions"], field="changes.assumptions")
    row = _find(geometry[f"{target}s"], identity, operation=name)
    before = copy.deepcopy(row)
    row.update(copy.deepcopy(changes))
    # New sources replace the edited object's active basis. The complete prior
    # record, including old sources, stays in the append-only audit below.
    row["source_refs"] = refs
    return {"operation": name, "id": identity, "reason": reason, "source_refs": refs,
            "before": before, "after": copy.deepcopy(row)}


def _remove_opening(geometry: dict, operation: dict) -> dict:
    name = "remove_opening"
    _require_fields(operation, {"op", "id", "reason", "source_refs"}, operation=name)
    identity = _nonblank_string(operation.get("id"), field="id", operation=name)
    reason = _nonblank_string(operation.get("reason"), field="reason", operation=name)
    refs = _source_refs(operation.get("source_refs"), operation=name)
    row = _find(geometry["openings"], identity, operation=name)
    before = copy.deepcopy(row)
    geometry["openings"].remove(row)
    return {"operation": name, "id": identity, "reason": reason, "source_refs": refs,
            "before": before, "after": None}


def _finite_coordinate(value: object, *, operation: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{operation}: coordinate_m must be a finite number")
    return float(value)


def _shared_rectangular_wall(left: dict, right: dict, *, operation: str) -> tuple[str, float, list[float], dict, dict]:
    """Return a complete common side, oriented from lower to higher coordinate."""
    if left.get("polygon") is not None or right.get("polygon") is not None:
        raise ValueError(f"{operation}: requires two rectangular cells without polygon")
    for cell in (left, right):
        for axis in ("x", "y"):
            interval = cell.get(axis)
            if (not isinstance(interval, list) or len(interval) != 2
                    or any(isinstance(value, bool) or not isinstance(value, (int, float))
                           or not math.isfinite(value) for value in interval)):
                raise ValueError(f"{operation}: rectangular cell {cell.get('id')!r} has invalid {axis} interval")

    # A local move is deliberately limited to one complete shared side.  Partial
    # contacts and polygon rings need a topology edit, rather than guessing which
    # vertices and neighbouring contacts should follow this wall.
    if left["y"] == right["y"]:
        if left["x"][1] == right["x"][0]:
            return "x", left["x"][1], list(left["y"]), left, right
        if right["x"][1] == left["x"][0]:
            return "x", right["x"][1], list(left["y"]), right, left
    if left["x"] == right["x"]:
        if left["y"][1] == right["y"][0]:
            return "y", left["y"][1], list(left["x"]), left, right
        if right["y"][1] == left["y"][0]:
            return "y", right["y"][1], list(left["x"]), right, left
    raise ValueError(f"{operation}: spaces must share one complete axis-aligned rectangular side")


def _opening_on_wall(opening: dict, *, axis: str, coordinate: float, span: list[float]) -> bool:
    points = [opening.get("p1"), opening.get("p2")]
    if any(not isinstance(point, (list, tuple)) or len(point) != 2 for point in points):
        return False
    normal = 0 if axis == "x" else 1
    along = 1 - normal
    try:
        return (all(point[normal] == coordinate for point in points)
                and all(span[0] <= point[along] <= span[1] for point in points))
    except TypeError:
        return False


def _move_shared_wall(proposal: dict, geometry: dict, operation: dict) -> dict:
    """Move one full rectangular interior side while preserving the source topology."""
    name = "move_shared_wall"
    _require_fields(operation, {"op", "space_ids", "coordinate_m", "reason", "source_refs"}, operation=name)
    if proposal.get("enclosure_declaration") is not None:
        raise ValueError("move_shared_wall: explicit enclosure_declaration requires an explicit enclosure edit")
    space_ids = operation.get("space_ids")
    if (not isinstance(space_ids, list) or len(space_ids) != 2
            or any(not isinstance(identity, str) or not identity.strip() for identity in space_ids)
            or space_ids[0] == space_ids[1]):
        raise ValueError("move_shared_wall: space_ids must contain two distinct nonblank space ids")
    reason = _nonblank_string(operation.get("reason"), field="reason", operation=name)
    refs = _source_refs(operation.get("source_refs"), operation=name)
    coordinate = _finite_coordinate(operation.get("coordinate_m"), operation=name)

    matches = []
    for floor in geometry.get("floors", []):
        cells = {cell.get("id"): cell for cell in floor.get("cells", [])}
        if all(identity in cells for identity in space_ids):
            matches.append((floor, cells[space_ids[0]], cells[space_ids[1]]))
    if len(matches) != 1:
        raise ValueError("move_shared_wall: spaces must occur together on exactly one floor")
    floor, first, second = matches[0]
    axis, old_coordinate, span, lower, higher = _shared_rectangular_wall(first, second, operation=name)
    interval_name = f"footprint_{axis}"
    footprint = geometry.get(interval_name)
    if (not isinstance(footprint, list) or len(footprint) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) for value in footprint)
            or not footprint[0] < old_coordinate < footprint[1]):
        raise ValueError(f"move_shared_wall: shared side is not an interior {axis} wall in the declared footprint")
    if not lower[axis][0] < coordinate < higher[axis][1]:
        raise ValueError("move_shared_wall: coordinate_m would collapse or invert a source space")

    before_cells = {cell["id"]: copy.deepcopy(cell) for cell in (lower, higher)}
    lower[axis][1] = coordinate
    higher[axis][0] = coordinate

    pair = set(space_ids)
    moved_openings = []
    for opening in geometry.get("openings", []):
        opening_pair = {opening.get("space_id"), opening.get("other_space_id")}
        on_old_wall = _opening_on_wall(opening, axis=axis, coordinate=old_coordinate, span=span)
        if opening_pair == pair:
            if not on_old_wall:
                raise ValueError(f"move_shared_wall: opening {opening.get('id')!r} between selected spaces is not fully hosted on their shared wall")
            before = copy.deepcopy(opening)
            normal = 0 if axis == "x" else 1
            opening["p1"][normal] = coordinate
            opening["p2"][normal] = coordinate
            moved_openings.append({"id": opening.get("id"), "before": before, "after": copy.deepcopy(opening)})
        elif on_old_wall:
            raise ValueError(f"move_shared_wall: opening {opening.get('id')!r} on the moved wall has different spaces")

    return {
        "operation": name,
        "space_ids": list(space_ids),
        "floor": floor.get("name"),
        "axis": axis,
        "from_coordinate_m": old_coordinate,
        "coordinate_m": coordinate,
        "shared_span_m": span,
        "reason": reason,
        "source_refs": refs,
        "before": {"cells": before_cells},
        "after": {"cells": {cell["id"]: copy.deepcopy(cell) for cell in (lower, higher)}},
        "moved_openings": moved_openings,
    }


def _set_notes(proposal: dict, operation: dict) -> dict:
    _require_fields(operation, {"op", "assumptions", "unresolved"}, operation="set_notes")
    assumptions = _notes(operation.get("assumptions"), field="assumptions")
    unresolved = _notes(operation.get("unresolved"), field="unresolved")
    before = {"assumptions": copy.deepcopy(proposal["assumptions"]), "unresolved": copy.deepcopy(proposal["unresolved"])}
    proposal["assumptions"] = assumptions
    proposal["unresolved"] = unresolved
    return {"operation": "set_notes", "before": before,
            "after": {"assumptions": copy.deepcopy(assumptions), "unresolved": copy.deepcopy(unresolved)}}


def apply_proposal_edits(proposal: dict, operations: list[dict]) -> dict:
    """Return an independently editable legacy proposal after explicit local edits.

    The input proposal is never changed.  This does not claim any edit is
    faithful to a drawing; it records the newly supplied reason/source evidence
    and leaves source-BIM validation to the normal deterministic builder.
    """
    _validate_proposal(proposal)
    if not isinstance(operations, list):
        raise TypeError("operations must be a list")
    result = copy.deepcopy(proposal)
    geometry = result["geometry"]
    _unique_ids(geometry)
    corrections = geometry.setdefault("corrections", [])
    if not isinstance(corrections, list):
        raise ValueError("geometry.corrections must be a list")
    for operation in operations:
        if not isinstance(operation, dict) or not isinstance(operation.get("op"), str):
            raise ValueError("each operation must be an object with an op")
        name = operation["op"]
        if name == "reflect":
            _require_fields(operation, {"op", "axis", "reason"}, operation=name)
            if result.get("enclosure_declaration"):
                raise ValueError("reflect: nonempty enclosure_declaration requires an explicit enclosure edit")
            if geometry.get("north_axis") is not None or geometry.get("facade_segments"):
                raise ValueError("reflect: explicit north_axis/facade_segments require an explicit directional metadata edit")
            audit = _reflect(geometry, axis=operation.get("axis"),
                             reason=_nonblank_string(operation.get("reason"), field="reason", operation=name))
            if _DIRECTION_NOTICE not in result["unresolved"]:
                result["unresolved"].append(_DIRECTION_NOTICE)
        elif name == "update_window":
            audit = _update(geometry, operation, target="window")
        elif name == "update_opening":
            audit = _update(geometry, operation, target="opening")
        elif name == "remove_opening":
            audit = _remove_opening(geometry, operation)
        elif name == "move_shared_wall":
            audit = _move_shared_wall(result, geometry, operation)
        elif name == "set_notes":
            audit = _set_notes(result, operation)
        else:
            raise ValueError(f"unknown proposal edit operation {name!r}")
        corrections.append(audit)
        _unique_ids(geometry)
    ensure_corrected_geometry(geometry)
    return result
