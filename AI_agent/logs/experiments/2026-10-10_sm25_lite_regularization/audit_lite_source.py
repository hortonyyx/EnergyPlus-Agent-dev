"""Offline audit for a finalized Lite BIM source model.

The grid check is intentionally schema-aware.  It checks adopted geometric XYZ
values only: floor footprints and levels, space polygons and levels, source
boundary/opening vertices, and boundary-relation region vertices.  It excludes
areas, normals, hashes, tolerances, evidence boxes, raw observations, reports,
and other numeric metadata.

An optional same-run pre-regularization source model can be supplied as a
baseline.  The comparison reports inventory/topology preservation and movement
statistics by stable object/path identity.  A 2026-10-09 result must not be used
as reader context or silently treated as the same-run baseline.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


AXES = ("x", "y", "z")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"source model must be a JSON object: {path}")
    return value


def point_records(path: str, point: Any, axes: tuple[str, ...],
                  category: str) -> Iterable[dict[str, Any]]:
    if not isinstance(point, list) or len(point) != len(axes):
        raise ValueError(f"{path} must be a {len(axes)}-coordinate point")
    for index, (axis, value) in enumerate(zip(axes, point, strict=True)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{path}[{index}] must be a finite numeric {axis} coordinate")
        yield {"path": f"{path}[{index}]", "axis": axis, "category": category,
               "value_m": float(value)}


def row_id(row: dict[str, Any], collection: str, index: int) -> str:
    value = row.get("id")
    if not isinstance(value, str) or not value:
        raise ValueError(f"{collection}[{index}].id must be nonempty text")
    return value


def geometry_records(model: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only final adopted coordinate values, never arbitrary JSON numbers."""
    records: list[dict[str, Any]] = []
    for index, floor in enumerate(model.get("floors", [])):
        identity = row_id(floor, "floors", index)
        for point_index, point in enumerate(floor.get("footprint", [])):
            records.extend(point_records(f"floors[{identity}].footprint[{point_index}]", point,
                                         ("x", "y"), "floor_footprint"))
        z_floor = floor.get("z_floor")
        height = floor.get("height")
        if isinstance(z_floor, (int, float)) and not isinstance(z_floor, bool):
            records.append({"path": f"floors[{identity}].z_floor", "axis": "z",
                            "category": "z_lower_extents", "value_m": float(z_floor)})
            if isinstance(height, (int, float)) and not isinstance(height, bool):
                records.append({"path": f"floors[{identity}].z_ceiling_derived", "axis": "z",
                                "category": "z_upper_extents",
                                "value_m": float(z_floor) + float(height)})

    for index, space in enumerate(model.get("spaces", [])):
        identity = row_id(space, "spaces", index)
        for point_index, point in enumerate(space.get("polygon", [])):
            records.extend(point_records(f"spaces[{identity}].polygon[{point_index}]", point,
                                         ("x", "y"), "space_polygon"))
        z_floor = space.get("z_floor")
        height = space.get("height")
        if isinstance(z_floor, (int, float)) and not isinstance(z_floor, bool):
            records.append({"path": f"spaces[{identity}].z_floor", "axis": "z",
                            "category": "z_lower_extents", "value_m": float(z_floor)})
            if isinstance(height, (int, float)) and not isinstance(height, bool):
                records.append({"path": f"spaces[{identity}].z_ceiling_derived", "axis": "z",
                                "category": "z_upper_extents",
                                "value_m": float(z_floor) + float(height)})

    for collection in ("boundaries", "openings"):
        for index, row in enumerate(model.get(collection, [])):
            identity = row_id(row, collection, index)
            for point_index, point in enumerate(row.get("vertices", [])):
                records.extend(point_records(
                    f"{collection}[{identity}].vertices[{point_index}]", point, AXES,
                    "boundary_vertices" if collection == "boundaries" else "opening_vertices"))

    for relation_index, relation in enumerate(model.get("boundary_relations", [])):
        for region_index, region in enumerate(relation.get("regions", [])):
            for point_index, point in enumerate(region.get("vertices", [])):
                records.extend(point_records(
                    f"boundary_relations[{relation_index}].regions[{region_index}].vertices[{point_index}]",
                    point, AXES, "boundary_relation_vertices"))
            for hole_index, hole in enumerate(region.get("holes", [])):
                for point_index, point in enumerate(hole):
                    records.extend(point_records(
                        f"boundary_relations[{relation_index}].regions[{region_index}].holes[{hole_index}][{point_index}]",
                        point, AXES, "boundary_relation_vertices"))
    return records


def grid_audit(records: list[dict[str, Any]], grid_m: Decimal,
               abs_tol_m: Decimal) -> dict[str, Any]:
    failures = []
    by_axis = Counter()
    by_category = Counter()
    failures_by_category = Counter()
    samples_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unique = defaultdict(set)
    reused = defaultdict(Counter)
    maximum = Decimal("0")
    for record in records:
        value = Decimal(str(record["value_m"]))
        multiple = (value / grid_m).to_integral_value(rounding=ROUND_HALF_UP)
        adopted = multiple * grid_m
        residual = abs(value - adopted)
        maximum = max(maximum, residual)
        by_axis[record["axis"]] += 1
        by_category[record["category"]] += 1
        unique[record["axis"]].add(value)
        reused[record["axis"]][value] += 1
        if residual > abs_tol_m:
            failure = {
                **record,
                "nearest_grid_m": float(adopted),
                "absolute_residual_m": float(residual),
            }
            failures.append(failure)
            failures_by_category[record["category"]] += 1
            if len(samples_by_category[record["category"]]) < 20:
                samples_by_category[record["category"]].append(failure)
    categories = sorted(by_category)
    return {
        "status": "pass" if not failures else "fail",
        "grid_m": float(grid_m),
        "absolute_tolerance_m": float(abs_tol_m),
        "checked_coordinate_values": len(records),
        "checked_by_axis": dict(sorted(by_axis.items())),
        "checked_by_category": {category: by_category[category] for category in categories},
        "off_grid_by_category": {
            category: failures_by_category[category] for category in categories
        },
        "off_grid_samples_by_category": {
            category: samples_by_category[category] for category in categories
        },
        "unique_values_by_axis": {axis: len(values) for axis, values in sorted(unique.items())},
        "shared_values_by_axis": {
            axis: sum(1 for count in counts.values() if count > 1)
            for axis, counts in sorted(reused.items())
        },
        "maximum_absolute_residual_m": float(maximum),
        "off_grid_count": len(failures),
        "off_grid": failures[:200],
        "off_grid_truncated": len(failures) > 200,
        "excluded_numeric_fields": [
            "areas and lengths not represented as adopted XYZ coordinates",
            "normals, tolerances, confidence, scores, hashes and counters",
            "evidence/image bounding boxes and raw observations",
            "regularization audit metadata and movement reports",
        ],
    }


def id_map(model: dict[str, Any], collection: str) -> dict[str, dict[str, Any]]:
    result = {}
    for index, row in enumerate(model.get(collection, [])):
        identity = row_id(row, collection, index)
        if identity in result:
            raise ValueError(f"duplicate {collection} id: {identity}")
        result[identity] = row
    return result


def canonical_vertices(vertices: Any, digits: int) -> tuple[tuple[float, ...], ...]:
    if not isinstance(vertices, list):
        return ()
    return tuple(sorted(tuple(round(float(value), digits) for value in point) for point in vertices))


def relationship_audit(model: dict[str, Any], abs_tol_m: float) -> dict[str, Any]:
    floors = id_map(model, "floors")
    spaces = id_map(model, "spaces")
    boundaries = id_map(model, "boundaries")
    openings = id_map(model, "openings")
    errors: list[dict[str, Any]] = []
    counterpart_pairs = set()
    one_to_one_equal = 0
    one_to_one_compared = 0
    digits = max(0, int(math.ceil(-math.log10(abs_tol_m)))) if abs_tol_m < 1 else 0

    for identity, space in spaces.items():
        floor_id = space.get("floor_id")
        if floor_id not in floors:
            errors.append({"type": "space_missing_floor", "space_id": identity,
                           "floor_id": floor_id})

    for identity, boundary in boundaries.items():
        space_id = boundary.get("space_id")
        if space_id not in spaces:
            errors.append({"type": "boundary_missing_space", "boundary_id": identity,
                           "space_id": space_id})
        adjacent_space_ids = boundary.get("adjacent_space_ids", [])
        if not isinstance(adjacent_space_ids, list):
            errors.append({"type": "invalid_adjacent_space_ids", "boundary_id": identity})
        else:
            for adjacent_space_id in adjacent_space_ids:
                if adjacent_space_id not in spaces:
                    errors.append({"type": "boundary_missing_adjacent_space",
                                   "boundary_id": identity,
                                   "space_id": adjacent_space_id})
        counterparts = boundary.get("counterpart_ids", [])
        if not isinstance(counterparts, list):
            errors.append({"type": "invalid_counterpart_ids", "boundary_id": identity})
            continue
        for counterpart in counterparts:
            if counterpart not in boundaries:
                errors.append({"type": "missing_counterpart", "boundary_id": identity,
                               "counterpart_id": counterpart})
                continue
            pair = tuple(sorted((identity, counterpart)))
            counterpart_pairs.add(pair)
            reverse = boundaries[counterpart].get("counterpart_ids", [])
            if identity not in reverse:
                errors.append({"type": "nonreciprocal_counterpart", "boundary_id": identity,
                               "counterpart_id": counterpart})
            if len(counterparts) == 1 and len(reverse) == 1:
                one_to_one_compared += 1
                if canonical_vertices(boundary.get("vertices"), digits) == canonical_vertices(
                        boundaries[counterpart].get("vertices"), digits):
                    one_to_one_equal += 1

    relation_refs = 0
    for index, relation in enumerate(model.get("boundary_relations", [])):
        for identity in relation.get("boundary_ids", []):
            relation_refs += 1
            if identity not in boundaries:
                errors.append({"type": "relation_missing_boundary", "relation": index,
                               "boundary_id": identity})
        for identity in relation.get("space_ids", []):
            if identity not in spaces:
                errors.append({"type": "relation_missing_space", "relation": index,
                               "space_id": identity})

    hosts = model.get("opening_hosts", {})
    if not isinstance(hosts, dict):
        errors.append({"type": "invalid_opening_hosts"})
        hosts = {}
    for opening_id, opening in openings.items():
        opening_space_ids = opening.get("space_ids", [])
        if not isinstance(opening_space_ids, list):
            errors.append({"type": "invalid_opening_space_ids", "opening_id": opening_id})
        else:
            for space_id in opening_space_ids:
                if space_id not in spaces:
                    errors.append({"type": "opening_missing_space", "opening_id": opening_id,
                                   "space_id": space_id})
        mapped = hosts.get(opening_id, [])
        if not isinstance(mapped, list):
            errors.append({"type": "invalid_opening_host_list", "opening_id": opening_id})
            mapped = []
        for boundary_id in mapped:
            if boundary_id not in boundaries:
                errors.append({"type": "opening_missing_host_boundary", "opening_id": opening_id,
                               "boundary_id": boundary_id})
        primary = opening.get("host_boundary_id")
        if primary not in boundaries:
            errors.append({"type": "opening_missing_primary_host", "opening_id": opening_id,
                           "boundary_id": primary})
        if isinstance(primary, str) and primary not in mapped:
            errors.append({"type": "primary_host_not_in_host_map", "opening_id": opening_id,
                           "boundary_id": primary})
    for opening_id in hosts:
        if opening_id not in openings:
            errors.append({"type": "host_map_missing_opening", "opening_id": opening_id})

    connection_count = 0
    for index, connection in enumerate(model.get("connections", [])):
        connection_count += 1
        opening_id = connection.get("opening_id")
        if opening_id not in openings:
            errors.append({"type": "connection_missing_opening", "connection": index,
                           "opening_id": opening_id})
            continue
        connection_spaces = set(connection.get("space_ids", []))
        opening_spaces = set(openings[opening_id].get("space_ids", []))
        if connection_spaces != opening_spaces:
            errors.append({"type": "connection_space_mismatch", "opening_id": opening_id,
                           "connection_space_ids": sorted(connection_spaces),
                           "opening_space_ids": sorted(opening_spaces)})
        for space_id in connection_spaces:
            if space_id not in spaces:
                errors.append({"type": "connection_missing_space", "opening_id": opening_id,
                               "space_id": space_id})

    validation = model.get("validation", {})
    if not isinstance(validation, dict) or validation.get("status") != "pass":
        errors.append({"type": "source_validation_not_pass", "value": validation})
    return {
        "status": "pass" if not errors else "fail",
        "inventory": {
            "floors": len(floors),
            "spaces": len(spaces),
            "boundaries": len(boundaries),
            "openings": len(openings),
            "connections": connection_count,
            "boundary_relations": len(model.get("boundary_relations", [])),
        },
        "counterpart_pairs": len(counterpart_pairs),
        "one_to_one_counterpart_geometry_compared": one_to_one_compared,
        "one_to_one_counterpart_geometry_equal": one_to_one_equal,
        "boundary_relation_references": relation_refs,
        "opening_host_mappings": sum(len(value) for value in hosts.values() if isinstance(value, list)),
        "source_validation_status": validation.get("status") if isinstance(validation, dict) else None,
        "errors": errors[:200],
        "errors_truncated": len(errors) > 200,
    }


def inventory_sets(model: dict[str, Any]) -> dict[str, set[str]]:
    return {name: set(id_map(model, name)) for name in ("floors", "spaces", "boundaries", "openings")}


def connection_signatures(model: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
    result = {}
    for row in model.get("connections", []):
        opening_id = row.get("opening_id")
        if isinstance(opening_id, str):
            result[opening_id] = (
                row.get("kind"), row.get("state"), bool(row.get("exterior")),
                tuple(sorted(row.get("space_ids", []))),
            )
    return result


def host_signatures(model: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    hosts = model.get("opening_hosts", {})
    if not isinstance(hosts, dict):
        return {}
    return {identity: tuple(sorted(value)) for identity, value in hosts.items() if isinstance(value, list)}


def changed_map(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    keys = sorted(set(before) | set(after))
    return [{"id": key, "before": before.get(key), "after": after.get(key)}
            for key in keys if before.get(key) != after.get(key)]


def baseline_audit(baseline: dict[str, Any], final: dict[str, Any],
                   abs_tol_m: float) -> dict[str, Any]:
    before_sets, after_sets = inventory_sets(baseline), inventory_sets(final)
    inventory = {}
    inventory_changed = False
    for collection in before_sets:
        removed = sorted(before_sets[collection] - after_sets[collection])
        added = sorted(after_sets[collection] - before_sets[collection])
        inventory[collection] = {"before": len(before_sets[collection]),
                                 "after": len(after_sets[collection]),
                                 "added": added, "removed": removed}
        inventory_changed = inventory_changed or bool(added or removed)
    host_changes = changed_map(host_signatures(baseline), host_signatures(final))
    connection_changes = changed_map(connection_signatures(baseline), connection_signatures(final))

    before_geometry = {row["path"]: row["value_m"] for row in geometry_records(baseline)}
    after_geometry = {row["path"]: row["value_m"] for row in geometry_records(final)}
    common = sorted(set(before_geometry) & set(after_geometry))
    movements = []
    for path in common:
        delta = after_geometry[path] - before_geometry[path]
        if abs(delta) > abs_tol_m:
            movements.append({"path": path, "before_m": before_geometry[path],
                              "after_m": after_geometry[path], "delta_m": delta})
    maximum = max((abs(row["delta_m"]) for row in movements), default=0.0)
    topology_preserved = not inventory_changed and not host_changes and not connection_changes
    return {
        "status": "pass" if topology_preserved else "fail",
        "scope": "Same-run stable-ID comparison; geometry movement is informational, inventory/hosts/connections are preservation gates.",
        "inventory": inventory,
        "host_changes": host_changes[:200],
        "connection_changes": connection_changes[:200],
        "geometry_paths_before": len(before_geometry),
        "geometry_paths_after": len(after_geometry),
        "geometry_paths_compared": len(common),
        "geometry_paths_moved": len(movements),
        "maximum_absolute_movement_m": maximum,
        "movement_sample": movements[:200],
        "movement_sample_truncated": len(movements) > 200,
    }


def regularization_sections(value: Any, path: str = "$") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}"
            lowered = key.casefold()
            if "regularization" in lowered or "lite_bim" in lowered:
                found.append(child)
            found.extend(regularization_sections(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(regularization_sections(item, f"{path}[{index}]"))
    return sorted(set(found))


def audit(model: dict[str, Any], *, grid_m: Decimal, abs_tol_m: Decimal,
          baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    records = geometry_records(model)
    grid = grid_audit(records, grid_m, abs_tol_m)
    relations = relationship_audit(model, float(abs_tol_m))
    baseline_report = (baseline_audit(baseline, model, float(abs_tol_m))
                       if baseline is not None else {"status": "not_supplied"})
    passed = (grid["status"] == "pass" and relations["status"] == "pass"
              and baseline_report["status"] in {"pass", "not_supplied"})
    return {
        "schema_version": "lite-source-grid-audit-v1",
        "status": "pass" if passed else "fail",
        "grid": grid,
        "source_relationships": relations,
        "same_run_baseline": baseline_report,
        "regularization_report_paths": regularization_sections(model),
        "limits": [
            "This audit proves numeric grid membership and referential preservation only.",
            "It does not prove drawing fidelity, correct space partitioning, complete inventory, or autonomous model stability.",
            "The common evaluator and visual review remain separate acceptance evidence.",
        ],
    }


def self_test() -> None:
    source = {
        "floors": [{"id": "F1", "footprint": [[0.0, 0.0], [1.0, 0.0],
                     [1.0, 1.0], [0.0, 1.0]], "z_floor": 0.0, "height": 3.0}],
        "spaces": [{"id": "S1", "floor_id": "F1", "polygon": [[0.0, 0.0], [1.0, 0.0],
                    [1.0, 1.0], [0.0, 1.0]], "z_floor": 0.0, "height": 3.0}],
        "boundaries": [{"id": "B1", "vertices": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                        [1.0, 0.0, 3.0], [0.0, 0.0, 3.0]], "space_id": "S1",
                        "adjacent_space_ids": [], "counterpart_ids": []}],
        "openings": [{"id": "D1", "host_boundary_id": "B1", "space_ids": ["S1"],
                      "vertices": [[0.2, 0.0, 0.0], [0.8, 0.0, 0.0],
                                   [0.8, 0.0, 2.1], [0.2, 0.0, 2.1]]}],
        "opening_hosts": {"D1": ["B1"]},
        "connections": [{"opening_id": "D1", "space_ids": ["S1"],
                         "kind": "door", "state": "unknown", "exterior": True}],
        "boundary_relations": [],
        "validation": {"status": "pass", "findings": []},
    }
    good = audit(source, grid_m=Decimal("0.1"), abs_tol_m=Decimal("1e-8"))
    assert good["status"] == "pass"
    bad = json.loads(json.dumps(source))
    bad["openings"][0]["vertices"][0][0] = 0.15
    failed = audit(bad, grid_m=Decimal("0.1"), abs_tol_m=Decimal("1e-8"))
    assert failed["status"] == "fail" and failed["grid"]["off_grid_count"] == 1
    changed = json.loads(json.dumps(source))
    changed["connections"] = []
    compared = audit(changed, grid_m=Decimal("0.1"), abs_tol_m=Decimal("1e-8"), baseline=source)
    assert compared["status"] == "fail" and compared["same_run_baseline"]["connection_changes"]
    print(json.dumps({"status": "passed", "network_requests": 0, "model_requests": 0,
                      "grid_failure_detected": True, "topology_change_detected": True},
                     ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_model", nargs="?", type=Path)
    parser.add_argument("--baseline", type=Path,
                        help="optional same-run pre-regularization source_model.json")
    parser.add_argument("--grid-m", default="0.1")
    parser.add_argument("--abs-tol-m", default="1e-8")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.source_model is None:
        parser.error("source_model is required unless --self-test is used")
    grid_m, abs_tol_m = Decimal(args.grid_m), Decimal(args.abs_tol_m)
    if not grid_m.is_finite() or grid_m <= 0:
        parser.error("--grid-m must be a positive finite decimal")
    if not abs_tol_m.is_finite() or abs_tol_m < 0 or abs_tol_m >= grid_m / 2:
        parser.error("--abs-tol-m must be nonnegative and less than half the grid")
    model = read_json(args.source_model.resolve())
    baseline = read_json(args.baseline.resolve()) if args.baseline else None
    result = audit(model, grid_m=grid_m, abs_tol_m=abs_tol_m, baseline=baseline)
    result["source_model"] = str(args.source_model.resolve())
    result["baseline"] = str(args.baseline.resolve()) if args.baseline else None
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(encoded, encoding="utf-8", newline="\n")
    sys.stdout.write(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
