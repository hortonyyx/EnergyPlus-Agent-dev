"""Build evaluation-only, format-neutral references for plan/elevation roles.

The references combine verified GT geometry with the frozen original-image plan
inventories already used by the current evaluator.  They are never generator
inputs.  Run from the worktree root after scripts/activate_windows.ps1.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from shapely.geometry import LineString, MultiLineString, Polygon, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
POLICIES = ROOT / "src/agent/judge/convention_policies.json"
CASES = ("sm21_anchor", "sm24_anchor", "sm25-L_anchor")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def floor_number(value: str) -> int:
    match = re.search(r"(\d+)", value)
    if not match:
        raise ValueError(f"floor identity is not explicit: {value}")
    return int(match.group(1))


def coordinate(calibration: dict, value: float, axis: str) -> float:
    (p0, v0), (p1, v1) = calibration[f"{axis}_anchors"]
    return v0 + (value - p0) * (v1 - v0) / (p1 - p0)


def line_geojson(geometry) -> dict:
    if geometry.is_empty:
        return mapping(MultiLineString([]))
    if isinstance(geometry, (LineString, MultiLineString)):
        return mapping(geometry)
    lines = [item for item in getattr(geometry, "geoms", ())
             if isinstance(item, (LineString, MultiLineString))]
    return mapping(unary_union(lines))


def typed_floors(gt: dict) -> list[dict]:
    result = []
    for floor in gt["floors"]:
        exterior = floor["footprint"]["exterior"]["vertices"]
        holes = [ring["vertices"] for ring in floor["footprint"].get("interior_rings", [])]
        footprint = Polygon(exterior, holes)
        rooms = [{"id": z["id"], "name": z.get("name"), "role": z.get("role"),
                  "polygon_m": z["polygon"]["exterior"]["vertices"]} for z in floor["zones"]]
        room_boundaries = unary_union([Polygon(r["polygon_m"]).boundary for r in rooms])
        partitions = room_boundaries.difference(footprint.boundary.buffer(1e-8))
        result.append({
            "floor_id": floor["id"], "z_floor_m": floor["z_floor_m"],
            "ceiling_height_m": floor["ceiling_height_m"],
            "exterior_m": exterior, "interior_rings_m": holes,
            "partitions_m": line_geojson(partitions),
            "rooms": rooms,
        })
    return result


def legacy_floors(gt: dict) -> list[dict]:
    width, depth = gt["footprint"]["W_m"], gt["footprint"]["D_m"]
    exterior = [[0.0, 0.0], [width, 0.0], [width, depth], [0.0, depth]]
    result = []
    for index, floor in enumerate(gt["floors"], 1):
        rooms = []
        for zone in floor["zones"]:
            x0, y0, x1, y1 = zone["rect_m"]
            rooms.append({"id": zone["id"], "name": None, "role": zone.get("role"),
                          "polygon_m": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]})
        footprint = Polygon(exterior)
        room_boundaries = unary_union([Polygon(r["polygon_m"]).boundary for r in rooms])
        result.append({
            "floor_id": f"F{index}", "z_floor_m": floor["z_floor"],
            "ceiling_height_m": floor["ceiling_height"], "exterior_m": exterior,
            "partitions_m": line_geojson(room_boundaries.difference(footprint.boundary.buffer(1e-8))),
            "rooms": rooms,
        })
    return result


def plan_openings(policy: dict) -> tuple[list[dict], list[dict]]:
    rows, sources = [], []
    for entry in policy["plan_observations"]:
        path = ROOT / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise RuntimeError(f"frozen observation hash changed: {path}")
        data = json.loads(path.read_bytes())
        sources.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                        "authority": "frozen_original_image_inventory"})
        for obs in data.get("floors", [data]):
            floor_id = f"F{floor_number(Path(obs['source_image']).stem)}"
            cal = obs["calibration"]
            for opening in obs["apertures"]:
                axis = opening["axis"]
                span = sorted(coordinate(cal, value, axis) for value in opening["span_pixels"])
                cross_axis = "y" if axis == "x" else "x"
                cross = coordinate(cal, opening["cross_pixel"], cross_axis)
                rows.append({
                    "id": opening["id"], "floor_id": floor_id, "kind": opening["kind"],
                    "axis": axis, "span_m": span, "cross_m": cross,
                    "width_m": span[1] - span[0], "host_labels": opening["hosts"],
                    "exterior": len(opening["hosts"]) == 1,
                    "tolerance_m": obs["tolerance"],
                    "source_image": obs["source_image"], "source_sha256": obs["source_sha256"],
                })
            image = ROOT / obs["source_image"]
            if sha256(image) != obs["source_sha256"]:
                raise RuntimeError(f"original image hash changed: {image}")
            sources.append({"path": image.relative_to(ROOT).as_posix(), "sha256": sha256(image),
                            "authority": "original_image"})
    return rows, sources


def typed_elevations(gt: dict) -> list[dict]:
    segments = {segment["id"]: segment for floor in gt["floors"]
                for segment in floor["boundary_segments"]}
    rows = []
    for opening in gt["openings"]:
        segment = segments[opening["boundary_segment_id"]]
        span, z = opening["world_along_interval"], opening["z_interval"]
        rows.append({
            "id": opening["id"], "facade": segment["facade_family"],
            "floor_id": opening["floor_id"], "kind": opening["kind"],
            "span_m": [span["lo"], span["hi"]], "width_m": span["hi"] - span["lo"],
            "sill_m": z["lo"], "head_m": z["hi"], "host_room_id": opening["host_zone_id"],
        })
    return rows


def legacy_elevations(gt: dict) -> list[dict]:
    rows = []
    for group_index, group in enumerate(gt["windows"]):
        for item_index, opening in enumerate(group["openings"]):
            rows.append({
                "id": f"window_group_{group_index}_item_{item_index}", "facade": group["facade"],
                "floor_id": f"F{floor_number(group['floor'])}", "kind": "window",
                "span_m": [opening["x_m"], opening["x_m"] + opening["width_m"]],
                "width_m": opening["width_m"], "sill_m": opening["sill_m"],
                "head_m": opening["head_m"], "host_room_id": None,
            })
    for index, opening in enumerate(gt["doors"]):
        rows.append({
            "id": f"door_{index}", "facade": opening["facade"],
            "floor_id": f"F{floor_number(opening['floor'])}",
            "kind": "door", "span_m": [opening["x_m"], opening["x_m"] + opening["width_m"]],
            "width_m": opening["width_m"], "sill_m": opening["sill_m"],
            "head_m": opening["head_m"], "host_room_id": None,
        })
    return rows


def build(case: str, policies: dict) -> dict:
    gt_path = ROOT / "case_tests/test_baseline/gt" / case / "gt.json"
    gt = json.loads(gt_path.read_bytes())
    typed = int(gt["schema_version"]) == 3
    plans = typed_floors(gt) if typed else legacy_floors(gt)
    openings, sources = plan_openings(policies[case])
    elevations = typed_elevations(gt) if typed else legacy_elevations(gt)
    by_floor = {floor["floor_id"]: floor for floor in plans}
    for opening in openings:
        by_floor[opening["floor_id"]].setdefault("openings", []).append(opening)
    by_facade: dict[str, dict] = {}
    for opening in elevations:
        key = opening["facade"]
        by_facade.setdefault(key, {"facade": key, "openings": []})["openings"].append(opening)
    for facade in by_facade.values():
        facade["openings"].sort(key=lambda row: (floor_number(row["floor_id"]), row["span_m"][0], row["kind"]))
        facade["counts"] = {
            key: sum(row["kind"] == key for row in facade["openings"])
            for key in ("door", "window")
        }
    return {
        "schema_version": "role_reference_v1", "case": case,
        "purpose": "evaluation_only_never_generator_input",
        "coordinate_frame": "building_axis_world_m",
        "tolerances": {
            "room_and_partition_boundary_m": 0.02,
            "plan_openings": "per-floor frozen original-image inventory; see each opening.tolerance_m",
            "elevation_along_m": 0.4, "elevation_width_m": 0.4,
            "elevation_sill_m": 0.3, "elevation_head_m": 0.3,
        },
        "sources": [{"path": gt_path.relative_to(ROOT).as_posix(), "sha256": sha256(gt_path),
                     "authority": "verified_gt"}, *sources],
        "plan_questions": list(by_floor.values()),
        "elevation_questions": [by_facade[key] for key in sorted(by_facade)],
        "limits": [
            "Plan openings come from frozen original-image inventories; room and envelope geometry comes from verified GT.",
            "Elevation openings come from verified GT and use the current judge tolerances.",
            "Room role/name is descriptive; geometry, opening kind, position, width and height are scored independently.",
        ],
    }


def main() -> None:
    policies = json.loads(POLICIES.read_bytes())
    output = HERE / "references"
    output.mkdir(exist_ok=True)
    manifest = {"schema_version": "role_reference_manifest_v1", "references": []}
    for case in CASES:
        target = output / f"{case}.json"
        target.write_text(json.dumps(build(case, policies), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        manifest["references"].append({"case": case, "path": target.name, "sha256": sha256(target)})
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
