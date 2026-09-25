"""Select the source spaces and openings physically present on one floor.

Some source spaces span several storeys and belong to a separate floor group.
Each storey explicitly names those spaces in ``spanning_space_ids``. Views and
reviews must use that membership, then limit openings to the storey's height.
"""
from __future__ import annotations

_Z_EPS = 1e-7  # Display membership only; source validation owns geometry tolerances.


def _vertical_interval(row):
    if "z_floor" not in row or "height" not in row:
        return None
    bottom = float(row["z_floor"])
    return bottom, bottom + float(row["height"])


def select_source_floor(source: dict, floor_id: str) -> tuple[dict, list[dict]]:
    """Return the floor and its local plus explicitly referenced spanning spaces."""
    floor = next((row for row in source["floors"] if row["id"] == floor_id), None)
    if floor is None:
        raise ValueError("unknown source floor_id")
    local_ids = {row["id"] for row in source["spaces"] if row["floor_id"] == floor_id}
    spanning_ids = set(floor.get("spanning_space_ids", []))
    selected_ids = local_ids | spanning_ids
    floor_interval = _vertical_interval(floor)
    spaces = []
    for row in source["spaces"]:
        if row["id"] not in selected_ids:
            continue
        interval = _vertical_interval(row)
        if floor_interval is not None and interval is not None:
            if min(floor_interval[1], interval[1]) - max(floor_interval[0], interval[0]) <= _Z_EPS:
                continue
        spaces.append(row)
    missing = selected_ids - {row["id"] for row in spaces}
    if missing:
        raise ValueError(f"floor {floor_id} references missing or nonoverlapping spaces: {sorted(missing)}")
    return floor, spaces


def select_source_floor_openings(source: dict, floor: dict, spaces: list[dict]) -> list[dict]:
    """Return openings fully owned by selected spaces and intersecting this floor's z span."""
    ids = {row["id"] for row in spaces}
    floor_interval = _vertical_interval(floor)
    selected = []
    for opening in source["openings"]:
        owners = opening["space_ids"]
        if not owners or not set(owners).issubset(ids):
            continue
        if floor_interval is not None:
            heights = [float(vertex[2]) for vertex in opening["vertices"]]
            if min(floor_interval[1], max(heights)) - max(floor_interval[0], min(heights)) <= _Z_EPS:
                continue
        selected.append(opening)
    return selected
