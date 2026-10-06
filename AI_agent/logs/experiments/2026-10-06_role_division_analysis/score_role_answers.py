"""Convert/score role answers with the project's existing evaluation tolerances.

Accepted answer schema is the same plan_questions/elevation_questions subset as
role_reference_v1.  ``--source-model`` converts a delivered source_model.json
without using GT to alter its geometry.  ``--score`` compares an answer with a
reference and emits an auditable JSON report.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import LineString, MultiLineString, Polygon, shape, mapping
from shapely.ops import unary_union


def floor_number(value: str) -> int:
    match = re.search(r"(\d+)", value)
    if not match:
        raise ValueError(f"floor identity is not explicit: {value}")
    return int(match.group(1))


def normalize_floor(value: str) -> str:
    return f"F{floor_number(value)}"


def line_geojson(geometry) -> dict:
    if geometry.is_empty:
        return mapping(MultiLineString([]))
    return mapping(geometry)


def facade_from_boundary(vertices: list[list[float]]) -> str:
    (x0, y0, *_), (x1, y1, *_) = vertices[:2]
    # Source space rings are counter-clockwise; the exterior is to the right.
    nx, ny = y1 - y0, -(x1 - x0)
    if abs(nx) > abs(ny):
        return "East" if nx > 0 else "West"
    return "North" if ny > 0 else "South"


def source_answer(source: dict, case: str | None = None) -> dict:
    floors = {normalize_floor(f["id"]): f for f in source["floors"]}
    plan = []
    for fid, floor in sorted(floors.items(), key=lambda row: floor_number(row[0])):
        rooms = [{"id": s["id"], "name": source.get("public_names", {}).get(s["id"]),
                  "role": s.get("role"), "polygon_m": s["polygon"]}
                 for s in source["spaces"] if normalize_floor(s["floor_id"]) == fid]
        footprint = Polygon(floor["footprint"])
        boundaries = unary_union([Polygon(r["polygon_m"]).boundary for r in rooms])
        row = {
            "floor_id": fid, "z_floor_m": floor["z_floor"], "ceiling_height_m": floor["height"],
            "exterior_m": floor["footprint"], "partitions_m": line_geojson(
                boundaries.difference(footprint.boundary.buffer(1e-8))), "rooms": rooms, "openings": [],
        }
        plan.append(row)
    plan_by_floor = {row["floor_id"]: row for row in plan}
    boundaries = {row["id"]: row for row in source["boundaries"]}
    elevation_rows = []
    for opening in source["openings"]:
        if opening["kind"] not in {"door", "window"}:
            continue
        floor_ids = {normalize_floor(s["floor_id"]) for s in source["spaces"]
                     if s["id"] in opening["space_ids"]}
        if len(floor_ids) != 1:
            continue
        fid = next(iter(floor_ids))
        xyz = np.asarray(opening["vertices"], dtype=float)
        dim = int(np.argmax(np.ptp(xyz[:, :2], axis=0)))
        span = [float(xyz[:, dim].min()), float(xyz[:, dim].max())]
        cross = float(xyz[:, 1 - dim].mean())
        plan_by_floor[fid]["openings"].append({
            "id": opening["id"], "floor_id": fid, "kind": opening["kind"],
            "axis": "xy"[dim], "span_m": span, "cross_m": cross,
            "width_m": span[1] - span[0], "host_room_ids": opening["space_ids"],
            "exterior": opening["exterior"],
        })
        if opening["exterior"] and opening.get("host_boundary_id") in boundaries:
            facade = facade_from_boundary(boundaries[opening["host_boundary_id"]]["vertices"])
            elevation_rows.append({
                "id": opening["id"], "facade": facade, "floor_id": fid, "kind": opening["kind"],
                "span_m": span, "width_m": span[1] - span[0],
                "sill_m": float(xyz[:, 2].min()), "head_m": float(xyz[:, 2].max()),
                "host_room_id": opening["space_ids"][0] if opening["space_ids"] else None,
            })
    facades = []
    for name in sorted({row["facade"] for row in elevation_rows}):
        openings = sorted((row for row in elevation_rows if row["facade"] == name),
                          key=lambda row: (floor_number(row["floor_id"]), row["span_m"][0], row["kind"]))
        facades.append({"facade": name, "openings": openings,
                        "counts": {kind: sum(row["kind"] == kind for row in openings)
                                   for kind in ("door", "window")}})
    return {"schema_version": "role_answer_v1", "case": case,
            "coordinate_frame": "building_axis_world_m",
            "plan_questions": plan, "elevation_questions": facades}


def boundary_metric(reference, candidate, tolerance: float) -> dict:
    missing = reference.difference(candidate.buffer(tolerance + 1e-9)).length
    extra = candidate.difference(reference.buffer(tolerance + 1e-9)).length
    return {"status": "pass" if max(missing, extra) <= 2 * tolerance + 1e-9 else "severe",
            "tolerance_m": tolerance, "missing_length_m": missing, "extra_length_m": extra}


def score_rooms(reference: list[dict], candidate: list[dict], fid: str, z: float, height: float) -> dict:
    from src.agent.judge.source_partition import compare_partitions
    def rows(values):
        return [{"id": item["id"], "floor_id": fid, "polygon": item["polygon_m"],
                 "z_floor": z, "height": height} for item in values]
    return compare_partitions(rows(reference), rows(candidate), tolerance_m=0.02)


def score_plan_openings(reference: list[dict], candidate: list[dict]) -> dict:
    costs = np.full((len(reference), len(candidate)), 1e6)
    metrics = {}
    for i, ref in enumerate(reference):
        for j, item in enumerate(candidate):
            if (ref["kind"], ref["axis"]) != (item["kind"], item["axis"]):
                continue
            along = max(abs(a - b) for a, b in zip(ref["span_m"], item["span_m"]))
            across = abs(ref["cross_m"] - item["cross_m"])
            costs[i, j] = along + across
            metrics[i, j] = along, across
    comparisons, used_r, used_c = [], set(), set()
    for i, j in zip(*linear_sum_assignment(costs)):
        if costs[i, j] >= 1e6:
            continue
        i, j = int(i), int(j)
        used_r.add(i); used_c.add(j)
        ref, item = reference[i], candidate[j]
        along, across = metrics[i, j]
        tol = ref["tolerance_m"]
        cross_limit = tol["external_cross_m" if ref["exterior"] else "internal_cross_m"]
        comparisons.append({
            "reference_id": ref["id"], "answer_id": item["id"], "kind": ref["kind"],
            "max_endpoint_error_m": along, "perpendicular_error_m": across,
            "along_tolerance_m": tol["along_m"], "cross_tolerance_m": cross_limit,
            "position_match": along <= tol["along_m"] and across <= cross_limit,
        })
    missing = [row["id"] for i, row in enumerate(reference) if i not in used_r]
    extra = [row["id"] for i, row in enumerate(candidate) if i not in used_c]
    good = sum(row["position_match"] for row in comparisons)
    return {"status": "pass" if good == len(reference) and not extra else "severe",
            "reference_count": len(reference), "matched": len(comparisons), "positions": good,
            "comparisons": comparisons, "unmatched_reference": missing, "unmatched_answer": extra}


def score_elevations(reference: list[dict], candidate: list[dict]) -> dict:
    # Same current judge tolerances: centre association 0.4 m; along/width
    # 0.4 m; sill/head 0.3 m. Global assignment prevents double use.
    costs = np.full((len(reference), len(candidate)), 1e6)
    metrics = {}
    for i, ref in enumerate(reference):
        for j, item in enumerate(candidate):
            if (ref["floor_id"], ref["facade"], ref["kind"]) != (
                    item["floor_id"], item["facade"], item["kind"]):
                continue
            center = abs(sum(ref["span_m"]) / 2 - sum(item["span_m"]) / 2)
            width = abs(ref["width_m"] - item["width_m"])
            sill = abs(ref["sill_m"] - item["sill_m"])
            head = abs(ref["head_m"] - item["head_m"])
            costs[i, j] = center + width + sill + head
            metrics[i, j] = center, width, sill, head
    rows, used_r, used_c = [], set(), set()
    for i, j in zip(*linear_sum_assignment(costs)):
        if costs[i, j] >= 1e6:
            continue
        i, j = int(i), int(j)
        used_r.add(i); used_c.add(j)
        center, width, sill, head = metrics[i, j]
        passed = center <= .4 and width <= .4 and sill <= .3 and head <= .3
        rows.append({"reference_id": reference[i]["id"], "answer_id": candidate[j]["id"],
                     "facade": reference[i]["facade"], "floor_id": reference[i]["floor_id"],
                     "kind": reference[i]["kind"], "center_error_m": center,
                     "width_error_m": width, "sill_error_m": sill, "head_error_m": head,
                     "match": passed})
    missing = [row["id"] for i, row in enumerate(reference) if i not in used_r]
    extra = [row["id"] for i, row in enumerate(candidate) if i not in used_c]
    good = sum(row["match"] for row in rows)
    return {"status": "pass" if good == len(reference) and not extra else "severe",
            "reference_count": len(reference), "matched": len(rows), "within_tolerance": good,
            "comparisons": rows, "unmatched_reference": missing, "unmatched_answer": extra,
            "tolerances_m": {"center": .4, "width": .4, "sill": .3, "head": .3}}


def score(reference: dict, answer: dict) -> dict:
    ref_floors = {row["floor_id"]: row for row in reference["plan_questions"]}
    ans_floors = {row["floor_id"]: row for row in answer["plan_questions"]}
    floor_rows = []
    for fid, ref in ref_floors.items():
        item = ans_floors.get(fid)
        if item is None:
            floor_rows.append({"floor_id": fid, "status": "missing"})
            continue
        exterior = boundary_metric(Polygon(ref["exterior_m"]).boundary,
                                   Polygon(item["exterior_m"]).boundary, .02)
        partitions = boundary_metric(shape(ref["partitions_m"]), shape(item["partitions_m"]), .02)
        rooms = score_rooms(ref["rooms"], item["rooms"], fid, ref["z_floor_m"], ref["ceiling_height_m"])
        openings = score_plan_openings(ref.get("openings", []), item.get("openings", []))
        statuses = {exterior["status"], partitions["status"], rooms["status"], openings["status"]}
        floor_rows.append({"floor_id": fid, "status": "severe" if "severe" in statuses else "pass",
                           "exterior": exterior, "partitions": partitions,
                           "rooms": rooms, "openings": openings})
    ref_elev = [row for facade in reference["elevation_questions"] for row in facade["openings"]]
    ans_elev = [row for facade in answer["elevation_questions"] for row in facade["openings"]]
    elevations = score_elevations(ref_elev, ans_elev)
    status = "pass" if elevations["status"] == "pass" and all(
        row["status"] == "pass" for row in floor_rows) and set(ans_floors) == set(ref_floors) else "severe"
    return {"schema_version": "role_score_v1", "case": reference["case"], "status": status,
            "floors": floor_rows, "extra_floors": sorted(set(ans_floors) - set(ref_floors)),
            "elevations": elevations,
            "limits": ["Scoring is evaluation-only and does not infer correctness outside the listed questions.",
                       "Room IDs/names are not identity keys; one-to-one geometry is matched globally."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--source-model", type=Path)
    action.add_argument("--score", type=Path, metavar="ANSWER_JSON")
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.source_model:
        result = source_answer(json.loads(args.source_model.read_bytes()), args.case)
    else:
        if not args.reference:
            parser.error("--score requires --reference")
        result = score(json.loads(args.reference.read_bytes()), json.loads(args.score.read_bytes()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: result.get(key) for key in ("schema_version", "case", "status")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
