#!/usr/bin/env python3
"""Describe and render one saved source-BIM candidate without modifying it."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import hashlib
import json
import math
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.geometry.source_elevation_view import render_source_elevation
from src.agent.geometry.source_floor_selection import select_source_floor, select_source_floor_openings
from src.agent.geometry.source_model import _digest
from src.agent.geometry.source_plan_view import render_source_plan


OPENING_KINDS = {"door", "passage", "open"}
SCOPE = (
    "Descriptive facts from this saved source_model.json and deterministic source views. "
    "Declared-opening reachability is not an egress, accessibility, code-compliance, "
    "drawing-fidelity, or architectural-acceptance result."
)


def _source_hash_status(source: dict) -> dict:
    declared = source.get("source_model_sha256")
    computed = _digest({key: value for key, value in source.items()
                        if key != "source_model_sha256"})
    return {"declared": declared, "computed": computed,
            "status": "valid" if declared == computed else "mismatch"}


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _space_size(space: dict) -> dict:
    row = {key: space.get(key) for key in ("id", "floor_id", "z_floor", "height", "role")}
    polygon = space.get("polygon")
    if (not isinstance(polygon, list) or len(polygon) < 3
            or any(not isinstance(point, list) or len(point) < 2
                   or not all(_finite(value) for value in point[:2]) for point in polygon)):
        return {**row, "geometry_status": "invalid_polygon_coordinates"}
    xs, ys = [point[0] for point in polygon], [point[1] for point in polygon]
    area = abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(polygon, polygon[1:] + polygon[:1]))) / 2
    return {**row, "geometry_status": "measured_from_saved_polygon",
            "bbox_m": {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)],
                       "width": max(xs) - min(xs), "depth": max(ys) - min(ys)},
            "footprint_area_m2": area}


def _window_distribution(spaces: list[dict], openings: list[dict]) -> dict:
    windows = defaultdict(list)
    for opening in openings:
        if opening.get("kind") == "window":
            for space_id in opening.get("space_ids", []):
                windows[space_id].append(opening.get("id"))
    rows = [{"space_id": space["id"], "window_count": len(windows[space["id"]]),
             "window_ids": sorted(windows[space["id"]])} for space in spaces]
    distribution = Counter(row["window_count"] for row in rows)
    return {"by_room": rows,
            "distribution": [{"window_count": count, "space_count": distribution[count]}
                             for count in sorted(distribution)]}


def _opening_graph(spaces: list[dict], openings: list[dict]) -> dict:
    space_ids = {space["id"] for space in spaces}
    adjacency = {space_id: set() for space_id in space_ids}
    edges, invalid_refs, entrance_openings, entrances = [], [], [], set()
    for opening in openings:
        if opening.get("kind") not in OPENING_KINDS:
            continue
        declared = list(dict.fromkeys(opening.get("space_ids", [])))
        valid = [space_id for space_id in declared if space_id in space_ids]
        missing = [space_id for space_id in declared if space_id not in space_ids]
        if missing:
            invalid_refs.append({"opening_id": opening.get("id"), "unknown_space_ids": missing})
        for index, first in enumerate(valid):
            for second in valid[index + 1:]:
                adjacency[first].add(second); adjacency[second].add(first)
                edges.append({"opening_id": opening.get("id"), "kind": opening.get("kind"),
                              "space_ids": [first, second],
                              "connectivity": opening.get("connectivity")})
        if opening.get("exterior") is True and valid:
            entrance_openings.append(opening.get("id")); entrances.update(valid)
    reachable, queue = set(entrances), deque(sorted(entrances))
    while queue:
        current = queue.popleft()
        for adjacent in sorted(adjacency[current] - reachable):
            reachable.add(adjacent); queue.append(adjacent)
    return {
        "scope": "Undirected graph of saved door/passage/open space_ids, seeded by exterior ones; operability is not inferred.",
        "exterior_entrance_opening_ids": sorted(entrance_openings),
        "exterior_entrance_space_ids": sorted(entrances),
        "reachable_space_ids": sorted(reachable),
        "unreachable_space_ids": sorted(space_ids - reachable),
        "declared_edges": edges, "unknown_space_references": invalid_refs,
    }


def _floor_rows(source: dict) -> list[dict]:
    spaces, openings = source.get("spaces", []), source.get("openings", [])
    rows = []
    for floor in source.get("floors", []):
        floor_id = floor.get("id")
        local_ids = sorted(space["id"] for space in spaces if space.get("floor_id") == floor_id)
        spanning_ids = sorted(floor.get("spanning_space_ids", []))
        row = {"floor_id": floor_id, "z_floor": floor.get("z_floor"),
               "height": floor.get("height"), "local_space_ids": local_ids,
               "spanning_space_ids": spanning_ids}
        try:
            selected_floor, selected_spaces = select_source_floor(source, floor_id)
            selected_openings = select_source_floor_openings(source, selected_floor, selected_spaces)
            row.update(
                selected_space_ids=sorted(space["id"] for space in selected_spaces),
                room_count=len(selected_spaces),
                window_count=sum(item.get("kind") == "window" for item in selected_openings),
                door_count=sum(item.get("kind") == "door" for item in selected_openings),
                passage_count=sum(item.get("kind") in {"passage", "open"}
                                  for item in selected_openings),
            )
        except Exception as error:
            row["selection_error"] = str(error)
        rows.append(row)
    return rows


def _safe_floor_name(floor_id: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9_.-]+", "_", floor_id).strip("._") or "floor"
    suffix = hashlib.sha256(floor_id.encode()).hexdigest()[:10]
    return f"floorplan_{readable}_{suffix}.png"


def _render_views(source: dict, output: Path) -> dict:
    plans, elevations, errors = [], [], []
    for floor in source.get("floors", []):
        floor_id = floor.get("id")
        try:
            image, metadata = render_source_plan(source, floor_id)
            filename = _safe_floor_name(floor_id)
            image.save(output / filename)
            plans.append({"floor_id": floor_id, "image": filename,
                          "space_ids": metadata["space_ids"],
                          "opening_ids": metadata["opening_ids"],
                          "world_bounds_m": metadata["world_bounds_m"],
                          "source_model_sha256": metadata["source_model_sha256"]})
        except Exception as error:
            errors.append({"view": "floorplan", "floor_id": floor_id, "error": str(error)})
    for facade in ("North", "South", "East", "West"):
        try:
            image, metadata = render_source_elevation(source, facade)
            filename = f"elevation_{facade.lower()}.png"
            image.save(output / filename)
            elevations.append({"facade": facade, "image": filename,
                               "horizontal_axis": metadata["horizontal_axis"],
                               "direction": metadata["direction"],
                               "world_view_extent_m": metadata["world_view_extent_m"],
                               "projected_wall_count": len(metadata["projected_exterior_walls"]),
                               "projected_opening_count": len(metadata["projected_openings"]),
                               "projected_floor_line_count": len(metadata["projected_floor_lines"]),
                               "source_model_sha256": metadata["source_model_sha256"]})
        except Exception as error:
            errors.append({"view": "elevation", "facade": facade, "error": str(error)})
    return {"floorplans": plans, "elevations": elevations, "errors": errors}


def inspect(candidate: Path, output: Path) -> dict:
    candidate, output = candidate.resolve(), output.resolve()
    if not candidate.is_dir() or not (candidate / "source_model.json").is_file():
        raise ValueError("candidate-dir must contain source_model.json")
    if output == candidate or candidate in output.parents:
        raise ValueError("output-dir must be outside the candidate directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output-dir must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    source = json.loads((candidate / "source_model.json").read_text())
    spaces, boundaries, openings = (source.get("spaces", []), source.get("boundaries", []),
                                    source.get("openings", []))
    hash_status = _source_hash_status(source)
    roles = defaultdict(list)
    for space in spaces:
        role = space.get("role") if isinstance(space.get("role"), str) else "<missing>"
        roles[role].append(space.get("id"))
    saved_validation = source.get("validation") if isinstance(source.get("validation"), dict) else {}
    result = {
        "schema_version": "partial_inference_postrun_inspection_v1", "scope": SCOPE,
        "candidate_dir": str(candidate), "source_file": str(candidate / "source_model.json"),
        "source_hash_validation": hash_status,
        "source_status": {"schema_version": source.get("schema_version"),
                          "saved_validation_status": saved_validation.get("status"),
                          "saved_validation_finding_count": len(saved_validation.get("findings", [])),
                          "hash_status": hash_status["status"],
                          "architectural_acceptance": "not_evaluated"},
        "counts": {"spaces": len(spaces), "boundaries": len(boundaries),
                   "openings": len(openings),
                   "windows": sum(row.get("kind") == "window" for row in openings),
                   "doors": sum(row.get("kind") == "door" for row in openings),
                   "passages": sum(row.get("kind") in {"passage", "open"} for row in openings)},
        "roles": {role: {"count": len(ids), "space_ids": sorted(ids)}
                  for role, ids in sorted(roles.items())},
        "floors": _floor_rows(source),
        "source_space_sizes": [_space_size(space) for space in spaces],
        "windows_by_room": _window_distribution(spaces, openings),
        "declared_opening_reachability": _opening_graph(spaces, openings),
        "source_views": _render_views(source, output),
    }
    (output / "inspection.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    result = inspect(args.candidate_dir, args.output_dir)
    print(json.dumps({"inspection": str(args.output_dir.resolve() / "inspection.json"),
                      "counts": result["counts"],
                      "rendered_floorplans": len(result["source_views"]["floorplans"]),
                      "rendered_elevations": len(result["source_views"]["elevations"]),
                      "view_error_count": len(result["source_views"]["errors"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
