"""Independent, read-only opening audit for the saved sm24 developer candidate.

The typed GT enters only here, through the judge loader. This script does not
participate in candidate generation or alter its inputs and source model.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import LineString, Polygon

from src.agent.judge.gt import load_gt_document
from src.agent.judge.gt_schema import GroundTruthV3


RUN = Path(__file__).resolve().parent
GT_CASE = "sm24_anchor"


def read(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def round6(value: float) -> float:
    return round(float(value), 6)


def source_row(opening: dict) -> dict:
    xyz = opening["vertices"]
    xy = sorted({(float(v[0]), float(v[1])) for v in xyz})
    if len(xy) != 2:
        raise ValueError(f"{opening['id']}: expected two plan endpoints")
    z = sorted({float(v[2]) for v in xyz})
    if len(z) != 2:
        raise ValueError(f"{opening['id']}: expected two heights")
    a, b = xy
    if math.isclose(a[1], b[1], abs_tol=1e-7):
        axis, along = "x", [a[0], b[0]]
        facade = "North" if math.isclose(a[1], 20.0, abs_tol=1e-7) else "South" if math.isclose(a[1], 0.0, abs_tol=1e-7) else None
        plane = a[1]
    elif math.isclose(a[0], b[0], abs_tol=1e-7):
        axis, along = "y", [a[1], b[1]]
        facade = "East" if math.isclose(a[0], 10.0, abs_tol=1e-7) else "West" if math.isclose(a[0], 0.0, abs_tol=1e-7) else None
        plane = a[0]
    else:
        raise ValueError(f"{opening['id']}: non-orthogonal opening")
    return {"id": opening["id"], "kind": opening["kind"], "exterior": opening["exterior"],
            "spaces": opening["space_ids"], "host_boundary_id": opening["host_boundary_id"],
            "line": LineString([a, b]), "axis": axis, "plane": plane, "facade": facade,
            "along": sorted(along), "z": z, "source_refs": opening["source_refs"]}


def distance_to_line_ends(line: LineString, target) -> float:
    return max(target.distance(LineString([p, p])) for p in line.coords)


def wall_plan_line(boundary: dict) -> LineString:
    xy = sorted({(float(v[0]), float(v[1])) for v in boundary["vertices"]})
    if len(xy) != 2:
        raise ValueError(f"{boundary['id']}: wall lacks two plan endpoints")
    return LineString(xy)


def main() -> None:
    gt = load_gt_document(GT_CASE)
    if not isinstance(gt, GroundTruthV3) or gt.verification.status != "human_verified":
        raise ValueError("Expected verified typed_v3 GT")
    source = read("candidate_01/source_model.json")
    proposal = read("candidate_01/proposal.json")["geometry"]
    proposal_openings = {o["id"]: o for o in proposal["windows"] + proposal["openings"]}
    partition = read("evaluation_final/candidate_01_partition.json")
    mapping = {m["reference_id"]: m["candidate_id"] for m in partition["comparison"]["matches"]}
    reverse = {v: k for k, v in mapping.items()}
    if len(mapping) != len(reverse):
        raise ValueError("Partition mapping is not one-to-one")
    rows = [source_row(o) for o in source["openings"]]
    connections = {c["opening_id"]: c for c in source["connections"]}
    boundaries = {b["id"]: b for b in source["boundaries"]}
    hosts = source["opening_hosts"]
    zone_polygons = {z.id: Polygon(z.polygon.exterior.vertices)
                     for floor in gt.floors for z in floor.zones}
    segments = {s.id: s for floor in gt.floors for s in floor.boundary_segments}

    target_rows = []
    for o in gt.openings:
        segment = segments[o.boundary_segment_id]
        target_rows.append({"id": o.id, "kind": o.kind, "facade": segment.facade_family,
                            "host_zone_id": o.host_zone_id,
                            "along": [o.world_along_interval.lo, o.world_along_interval.hi],
                            "z": None if o.z_interval is None else [o.z_interval.lo, o.z_interval.hi],
                            "segment": segment,
                            "source_ref_roles": sorted({r.role for r in o.source_refs})})

    candidates = [r for r in rows if r["exterior"]]
    pair_options = []
    for ti, target in enumerate(target_rows):
        for ci, candidate in enumerate(candidates):
            if (target["kind"], target["facade"]) != (candidate["kind"], candidate["facade"]):
                continue
            overlap = min(target["along"][1], candidate["along"][1]) - max(target["along"][0], candidate["along"][0])
            if overlap > 0:
                pair_options.append((-overlap, ti, ci))
    used_t, used_c, matches = set(), set(), []
    for _, ti, ci in sorted(pair_options):
        if ti in used_t or ci in used_c:
            continue
        used_t.add(ti)
        used_c.add(ci)
        target, candidate = target_rows[ti], candidates[ci]
        seg = target["segment"]
        plane = seg.p1[1] if candidate["axis"] == "x" else seg.p1[0]
        dz = None if target["z"] is None else [candidate["z"][i] - target["z"][i] for i in (0, 1)]
        da = [candidate["along"][i] - target["along"][i] for i in (0, 1)]
        expected_space = mapping[target["host_zone_id"]]
        matches.append({"gt_id": target["id"], "source_id": candidate["id"], "kind": candidate["kind"],
                        "facade": candidate["facade"], "gt_zone_id": target["host_zone_id"],
                        "expected_source_space_id": expected_space, "source_space_ids": candidate["spaces"],
                        "host_correct": candidate["spaces"] == [expected_space],
                        "reference_along_m": [round6(x) for x in target["along"]],
                        "source_along_m": candidate["along"],
                        "endpoint_delta_m": [round6(x) for x in da],
                        "center_abs_error_m": round6(abs(sum(da) / 2)),
                        "width_error_m": round6((candidate["along"][1] - candidate["along"][0]) - (target["along"][1] - target["along"][0])),
                        "reference_z_m": None if target["z"] is None else [round6(x) for x in target["z"]],
                        "source_z_m": candidate["z"],
                        "z_endpoint_delta_m": None if dz is None else [round6(x) for x in dz],
                        "height_error_m": None if dz is None else round6(dz[1] - dz[0]),
                        "reference_plane_m": round6(plane), "source_plane_m": candidate["plane"],
                        "reference_plane_abs_error_m": round6(abs(plane - candidate["plane"])),
                        "source_ref_roles": target["source_ref_roles"],
                        "source_model_refs": candidate["source_refs"],
                        "proposal_refs": proposal_openings[candidate["id"]]["source_refs"]})

    host_checks = []
    for row in rows:
        listed = hosts.get(row["id"], [])
        actual_host = boundaries.get(row["host_boundary_id"])
        proposal_refs = proposal_openings[row["id"]]["source_refs"]
        bound_ok = actual_host is not None and actual_host["space_id"] in row["spaces"]
        declared_host_spaces = {boundaries[h]["space_id"] for h in listed if h in boundaries}
        max_host_gap = max((distance_to_line_ends(row["line"], wall_plan_line(boundaries[h]))
                            for h in listed if h in boundaries), default=float("inf"))
        host_checks.append({"source_id": row["id"], "declared_boundary_ids": listed,
                            "primary_boundary_id": row["host_boundary_id"],
                            "primary_boundary_space_correct": bound_ok,
                            "declared_host_count_correct": len(listed) == (1 if row["exterior"] else 2),
                            "declared_hosts_exist": all(h in boundaries for h in listed),
                            "declared_host_spaces_correct": declared_host_spaces == set(row["spaces"]),
                            "source_model_refs": row["source_refs"], "proposal_refs": proposal_refs,
                            "source_refs_present": bool(row["source_refs"]) and bool(proposal_refs),
                            "plan_ref_present": any("1f_view.png" in ref for ref in proposal_refs),
                            "elevation_ref_present": any(("view.png" in ref and "1f_view.png" not in ref) or "Original corresponding elevation" in ref for ref in proposal_refs),
                            "max_declared_host_wall_gap_m": None if not listed else round6(max_host_gap)})

    internal = []
    for row in rows:
        if row["exterior"]:
            continue
        if len(row["spaces"]) != 2:
            raise ValueError(f"{row['id']}: internal door does not name two spaces")
        gt_zone_ids = [reverse[s] for s in row["spaces"]]
        shared = zone_polygons[gt_zone_ids[0]].boundary.intersection(zone_polygons[gt_zone_ids[1]].boundary)
        internal.append({"source_id": row["id"], "source_spaces": row["spaces"],
                         "gt_adjacent_zones": gt_zone_ids, "gt_shared_boundary_length_m": round6(shared.length),
                         "source_to_gt_shared_plane_max_m": round6(distance_to_line_ends(row["line"], shared)),
                         "source_width_m": round6(row["along"][1] - row["along"][0]),
                         "source_z_m": row["z"], "height_basis": "explicit_source_assumption_2.1m_not_GT_measured",
                         "source_model_refs": row["source_refs"],
                         "proposal_refs": proposal_openings[row["id"]]["source_refs"]})

    connection_checks = []
    for row in rows:
        if row["kind"] != "door":
            continue
        connection = connections.get(row["id"])
        connection_checks.append({"source_id": row["id"], "source_spaces": row["spaces"],
                                  "connection_spaces": None if connection is None else connection["space_ids"],
                                  "connection_exterior": None if connection is None else connection["exterior"],
                                  "matches_opening": connection is not None
                                  and set(connection["space_ids"]) == set(row["spaces"])
                                  and connection["exterior"] == row["exterior"]
                                  and connection["kind"] == "door"})

    result = {"mode": "post_generation_read_only", "gt_case": GT_CASE,
              "gt_schema_version": gt.schema_version, "gt_verification": gt.verification.status,
              "gt_content_sha256": gt.content_sha256,
              "source_model_sha256": source["source_model_sha256"],
              "comparison_basis": "same world-m coordinates; kind, facade and positive along-overlap one-to-one pairing; no fitted shift or scale",
              "scope": {"source_windows": sum(r["kind"] == "window" for r in rows),
                        "source_exterior_doors": sum(r["kind"] == "door" and r["exterior"] for r in rows),
                        "source_internal_doors": len(internal), "gt_windows": sum(r["kind"] == "window" for r in target_rows),
                        "gt_exterior_doors": sum(r["kind"] == "door" for r in target_rows),
                        "gt_internal_door_records": 0},
              "reference_matches": sorted(matches, key=lambda m: (m["kind"], m["facade"], m["reference_along_m"])),
              "missing_reference_openings": [target_rows[i]["id"] for i in range(len(target_rows)) if i not in used_t],
              "extra_source_exterior_openings": [candidates[i]["id"] for i in range(len(candidates)) if i not in used_c],
              "source_host_checks": host_checks, "door_connection_checks": connection_checks,
              "internal_doors": internal,
              "reference_plane_note": "GT uses nominal external 0/10/20 m planes and interior partition planes; source external planes coincide, interior representative planes differ within the recorded distances.",
              "source_provenance_note": "Compiled source windows retain correction:window pointers; full original-plan/elevation references remain on the saved proposal, linked by stable opening ID. Doors retain direct source refs.",
              "limits": ["GT typed_v3 has no internal door targets, so their position, width, height and presence cannot be independently scored against GT.",
                         "Source plan/elevation refs show traceability, not independent proof that the raster was interpreted correctly.",
                         "Exterior z values use the facade-outline base; finished-floor datum is unresolved. Internal door height 2.1 m is an assumption."]}
    result["summary"] = {"matched_reference_openings": len(matches),
                         "wrong_exterior_hosts": [m["source_id"] for m in matches if not m["host_correct"]],
                         "max_center_abs_error_m": round6(max(m["center_abs_error_m"] for m in matches)),
                         "max_width_abs_error_m": round6(max(abs(m["width_error_m"]) for m in matches)),
                         "max_z_endpoint_abs_error_m": round6(max(abs(x) for m in matches for x in m["z_endpoint_delta_m"])),
                         "max_internal_to_gt_shared_plane_m": round6(max(x["source_to_gt_shared_plane_max_m"] for x in internal)),
                         "door_connection_failures": [x["source_id"] for x in connection_checks if not x["matches_opening"]],
                         "source_host_check_failures": [x["source_id"] for x in host_checks if not all((x["primary_boundary_space_correct"], x["declared_host_count_correct"], x["declared_hosts_exist"], x["declared_host_spaces_correct"], x["source_refs_present"], x["plan_ref_present"])) or (x["max_declared_host_wall_gap_m"] is not None and x["max_declared_host_wall_gap_m"] > 0.001)]}
    (RUN / "opening_evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
