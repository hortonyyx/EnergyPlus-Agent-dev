"""Bounded validation for the developer-built Voimatalo source candidate.

This verifies replay and internal consistency, then reports a one-way mesh-
surface-to-candidate-perimeter diagnostic.  The diagnostic is not ground truth,
does not test candidate completeness, and cannot validate missing end faces or
the inferred interior layout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


HERE = Path(__file__).resolve().parent
WALKTHROUGH = HERE.parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from src.agent.execution.source_proposal import export_source_proposal
from src.agent.geometry.mesh_bim_frame import observation_to_source
from src.agent.geometry.mesh_observation import MeshObservation
from src.agent.geometry.source_model import _digest


DEFAULT_BASELINE = (
    ROOT / "AI_agent/logs/experiments/2026-09-15_voimatalo_frame_run02/candidate_03"
)
DEFAULT_MESH = ROOT / "case_tests/textured_mass/single_buildings/voimatalo/input.glb"
TOLERANCE_M = 1e-7
TOLERANCE_M2 = 1e-6


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def candidate_paths(value: Path) -> tuple[Path, Path]:
    value = value.resolve()
    directory = value if value.is_dir() else value.parent
    source_path = directory / "source_model.json" if value.is_dir() else value
    if not source_path.is_file():
        raise FileNotFoundError(f"candidate source_model.json not found: {source_path}")
    return directory, source_path


def polygon_for_space(space: dict) -> Polygon:
    polygon = Polygon(space["polygon"])
    if polygon.is_empty or not polygon.is_valid or polygon.area <= TOLERANCE_M2:
        raise ValueError(f"invalid source-space polygon: {space.get('id')}")
    return polygon


def weighted_quantiles(values: np.ndarray, weights: np.ndarray, ps=(0.5, 0.9, 0.95)) -> dict:
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cumulative = np.cumsum(weights)
    if not len(values) or cumulative[-1] <= 0:
        return {f"q{round(p * 100):02d}": None for p in ps}
    result = np.interp(np.asarray(ps) * cumulative[-1], cumulative, values)
    return {f"q{round(p * 100):02d}": float(v) for p, v in zip(ps, result)}


def expected_outline(plan: dict, number: int) -> Polygon:
    shell = plan["shell"]
    attic = number == 8
    west = shell["attic_west"] if attic else shell["west"]
    east = shell["attic_east_end"] if attic else shell["east_end"]
    south = shell["attic_south_end"] if attic else shell["south_end"]
    north = shell["attic_north"] if attic else shell["north"]
    inner = shell["attic_court_long"] if attic else shell["court_long"]
    step = shell["court_step_x"]
    court = shell["court_short"]
    corner = shell["court_corner_y"]
    return Polygon([
        [west, south], [inner, south], [inner, corner], [step, corner],
        [step, court], [east, court], [east, north], [west, north],
    ])


def check_replay(candidate_dir: Path, source_path: Path, source: dict) -> dict:
    proposal_path = candidate_dir / "proposal.json"
    report_path = candidate_dir / "report.json"
    if not proposal_path.is_file() or not report_path.is_file():
        return {"status": "fail", "error": "proposal.json or report.json missing"}
    proposal = read_json(proposal_path)
    candidate_report = read_json(report_path)
    provenance = candidate_report.get("provenance")
    stored_digest = source.get("source_model_sha256")
    calculated_digest = _digest({k: v for k, v in source.items() if k != "source_model_sha256"})
    with tempfile.TemporaryDirectory(prefix="voimatalo-source-replay-") as tmp:
        replay_dir = Path(tmp) / "candidate"
        replay_report = export_source_proposal(proposal, replay_dir, provenance=provenance)
        replay_source_path = replay_dir / "source_model.json"
        if not replay_source_path.is_file():
            return {
                "status": "fail", "error": replay_report.get("error", "replay source missing"),
                "stored_digest": stored_digest, "calculated_digest": calculated_digest,
            }
        replay_source = read_json(replay_source_path)
        replay_digest = replay_source.get("source_model_sha256")
        exact_bytes = source_path.read_bytes() == replay_source_path.read_bytes()
        exact_json = source == replay_source
        result = {
            "status": "pass" if (
                stored_digest == calculated_digest == replay_digest and exact_json and exact_bytes
            ) else "fail",
            "stored_digest": stored_digest,
            "calculated_digest": calculated_digest,
            "replayed_digest": replay_digest,
            "exact_json": exact_json,
            "exact_source_model_bytes": exact_bytes,
            "source_file_sha256": sha256(source_path),
            "replayed_source_file_sha256": sha256(replay_source_path),
            "temporary_directory_removed_after_check": True,
        }
    return result


def check_no_same_height_overlap(source: dict) -> dict:
    rows = []
    spaces = source["spaces"]
    polygons = {s["id"]: polygon_for_space(s) for s in spaces}
    for i, a in enumerate(spaces):
        a_top = float(a["z_floor"]) + float(a["height"])
        for b in spaces[i + 1:]:
            b_top = float(b["z_floor"]) + float(b["height"])
            overlap_z = min(a_top, b_top) - max(float(a["z_floor"]), float(b["z_floor"]))
            if overlap_z <= TOLERANCE_M:
                continue
            area = polygons[a["id"]].intersection(polygons[b["id"]]).area
            if area > TOLERANCE_M2:
                rows.append({
                    "space_ids": [a["id"], b["id"]],
                    "vertical_overlap_m": float(overlap_z),
                    "plan_overlap_m2": float(area),
                })
    return {"status": "pass" if not rows else "fail", "overlaps": rows}


def check_storey_coverage(source: dict, plan: dict) -> dict:
    by_id = {s["id"]: s for s in source["spaces"]}
    floors = {f["id"]: f for f in source["floors"]}
    core_ids = [f"{name}_continuous" for name in plan["inferred_core_rectangles"]]
    levels = plan["storey_levels_m"]
    rows = []
    for number, (low, high) in enumerate(zip(levels, levels[1:]), 1):
        midpoint = (low + high) / 2
        floor_id = f"F{number}"
        floor_record = floors.get(floor_id, {})
        spanning_ids = floor_record.get("spanning_space_ids", [])
        spanning_refs_ok = (
            set(spanning_ids) == set(core_ids)
            and all(sid in by_id for sid in spanning_ids)
            and all(
                float(by_id[sid]["z_floor"]) <= low + TOLERANCE_M
                and float(by_id[sid]["z_floor"]) + float(by_id[sid]["height"])
                >= high - TOLERANCE_M
                for sid in spanning_ids
            )
        )
        selected = [
            s for s in source["spaces"]
            if s.get("floor_id") == floor_id or s["id"] in spanning_ids
        ]
        selected = [
            s for s in selected
            if float(s["z_floor"]) + TOLERANCE_M < midpoint
            < float(s["z_floor"]) + float(s["height"]) - TOLERANCE_M
        ]
        actual = unary_union([polygon_for_space(s) for s in selected])
        expected = expected_outline(plan, number)
        symmetric = expected.symmetric_difference(actual).area
        outside = actual.difference(expected).area
        missing = expected.difference(actual).area
        rows.append({
            "storey": floor_id, "z_mid_m": midpoint,
            "space_ids": sorted(s["id"] for s in selected),
            "spanning_space_ids": spanning_ids,
            "expected_spanning_space_ids": core_ids,
            "spanning_references_exist_and_cover_full_storey_height": spanning_refs_ok,
            "expected_area_m2": float(expected.area), "actual_union_area_m2": float(actual.area),
            "missing_area_m2": float(missing), "outside_area_m2": float(outside),
            "symmetric_difference_m2": float(symmetric),
            "status": "pass" if symmetric <= TOLERANCE_M2 and spanning_refs_ok else "fail",
            "expected_basis": (
                "case_plan shell using attic_court_long" if number == 8
                else "case_plan main shell using court_long"
            ),
        })
    return {
        "status": "pass" if all(r["status"] == "pass" for r in rows) else "fail",
        "scope": "candidate assembly against its own case_plan; not mesh truth or fidelity",
        "storeys": rows,
    }


def check_cores(source: dict, plan: dict) -> dict:
    spaces = {s["id"]: s for s in source["spaces"]}
    levels = plan["storey_levels_m"]
    doors = [o for o in source["openings"] if o.get("kind") == "door"]
    rows = []
    for core_name in plan["inferred_core_rectangles"]:
        core_id = f"{core_name}_continuous"
        space = spaces.get(core_id)
        horizontal = [
            b for b in source["boundaries"]
            if b["space_id"] == core_id and b["geometry_type"] in {"floor", "ceiling"}
        ]
        zs = sorted({round(float(v[2]), 8) for b in horizontal for v in b["vertices"]})
        per_floor = []
        for number, low in enumerate(levels[:-1], 1):
            open_id = f"F{number}_open"
            matches = [
                o["id"] for o in doors
                if set(o.get("space_ids", [])) == {open_id, core_id}
            ]
            per_floor.append({"storey": f"F{number}", "opening_ids": matches,
                              "status": "pass" if matches else "fail"})
        span_ok = bool(space) and abs(float(space["z_floor"]) - levels[0]) <= TOLERANCE_M and abs(
            float(space["z_floor"]) + float(space["height"]) - levels[-1]
        ) <= TOLERANCE_M
        horizontal_ok = len(horizontal) == 2 and zs == [round(levels[0], 8), round(levels[-1], 8)]
        rows.append({
            "core_space_id": core_id, "z_span_m": (
                [space["z_floor"], space["z_floor"] + space["height"]] if space else None
            ),
            "horizontal_boundary_ids": [b["id"] for b in horizontal],
            "horizontal_boundary_z_values_m": zs,
            "only_bottom_and_top_horizontal_boundaries": horizontal_ok,
            "storey_connection_doors": per_floor,
            "status": "pass" if span_ok and horizontal_ok and all(
                r["status"] == "pass" for r in per_floor
            ) else "fail",
        })
    return {"status": "pass" if all(r["status"] == "pass" for r in rows) else "fail", "cores": rows}


def check_door_graph(source: dict) -> dict:
    roof_ids = sorted(
        s["id"] for s in source["spaces"] if str(s.get("role", "")).startswith("roof_")
    )
    usable = sorted(s["id"] for s in source["spaces"] if s["id"] not in roof_ids)
    outside = "__EXTERIOR__"
    graph: dict[str, set[str]] = {s["id"]: set() for s in source["spaces"]}
    graph[outside] = set()
    used_doors = []
    for opening in source["openings"]:
        if opening.get("kind") != "door":
            continue
        ids = list(opening.get("space_ids", []))
        if opening.get("exterior") and len(ids) == 1:
            a, b = ids[0], outside
        elif len(ids) == 2:
            a, b = ids
        else:
            continue
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
        used_doors.append(opening["id"])
    reachable = {outside}
    pending = [outside]
    while pending:
        node = pending.pop()
        for adjacent in graph.get(node, ()):
            if adjacent not in reachable:
                reachable.add(adjacent)
                pending.append(adjacent)
    unreachable = sorted(set(usable) - reachable)
    return {
        "status": "pass" if not unreachable else "fail",
        "door_opening_ids_used": sorted(used_doors),
        "usable_space_ids": usable,
        "unreachable_usable_space_ids": unreachable,
        "roof_enclosure_space_ids_listed_separately": roof_ids,
        "interpretation": "Reachability in the declared door graph only; inferred doors do not establish the real interior circulation.",
    }


def check_openings(candidate_dir: Path, source: dict, proposal: dict, plan: dict, apertures_path: Path) -> dict:
    declared_windows = proposal["geometry"].get("windows", [])
    declared_other = proposal["geometry"].get("openings", [])
    built = source.get("openings", [])
    unbuilt = source.get("unbuilt_openings", [])
    mapping_path = candidate_dir / "opening_mapping.json"
    mappings = read_json(mapping_path) if mapping_path.is_file() else []
    observed = read_json(apertures_path)
    if isinstance(observed, dict):
        observed = observed["openings"]
    expected_observation_ids = {r["id"] for r in observed} | {
        r["id"] for r in plan.get("additional_openings", [])
    }
    mapping_ids = {r["id"] for r in mappings}
    declared_window_ids = {r["id"] for r in declared_windows}
    built_ids = {r["id"] for r in built}
    declared_ids = declared_window_ids | {r["id"] for r in declared_other}
    return {
        "status": "pass" if (
            not unbuilt
            and len(built) == len(declared_windows) + len(declared_other)
            and declared_ids == built_ids
            and expected_observation_ids == mapping_ids == declared_window_ids
            and all(r.get("owner") for r in mappings)
        ) else "fail",
        "counts": {
            "input_aperture_observations": len(observed),
            "case_plan_additional_openings": len(plan.get("additional_openings", [])),
            "opening_mapping_rows": len(mappings),
            "proposal_windows": len(declared_windows),
            "proposal_other_openings": len(declared_other),
            "source_built_openings": len(built),
            "source_unbuilt_openings": len(unbuilt),
        },
        "missing_mapping_ids": sorted(expected_observation_ids - mapping_ids),
        "unexpected_mapping_ids": sorted(mapping_ids - expected_observation_ids),
        "mapped_but_not_declared_window_ids": sorted(mapping_ids - declared_window_ids),
        "declared_window_but_not_mapped_ids": sorted(declared_window_ids - mapping_ids),
        "declared_but_not_built_ids": sorted(declared_ids - built_ids),
        "built_but_not_declared_ids": sorted(built_ids - declared_ids),
        "unbuilt_openings": unbuilt,
    }


def load_fixed_mesh_faces(mesh_path: Path, direction_path: Path) -> tuple[dict, dict]:
    direction = read_json(direction_path)
    mesh = MeshObservation(mesh_path)
    triangles, ids = [], []
    for part in mesh._parts:
        triangles.append(part.vertices[part.faces])
        ids.append(np.arange(len(part.faces), dtype=np.int64) + part.face_offset)
    triangles = np.concatenate(triangles)
    ids = np.concatenate(ids)
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    twice_area = np.linalg.norm(cross, axis=1)
    normals = cross / np.maximum(twice_area[:, None], 1e-15)
    centres = triangles.mean(axis=1)
    z0, z1 = direction["original_z_band_m"]
    tilt = direction["max_tilt_from_vertical_degrees"]
    mask = (
        (twice_area > 1e-10)
        & (np.abs(normals[:, 2]) <= math.sin(math.radians(tilt)))
        & (centres[:, 2] >= z0) & (centres[:, 2] <= z1)
    )
    recomputed_ids = ids[mask].tolist()
    if recomputed_ids != direction["face_ids"] or len(recomputed_ids) != 2090:
        raise ValueError("fixed mesh-face recomputation differs from evidence_01/direction.json")
    if mesh.mesh_sha256 != direction.get("mesh_sha256", mesh.mesh_sha256):
        raise ValueError("direction evidence and mesh digest differ")
    return {
        "triangles": triangles[mask], "centres": centres[mask], "normals": normals[mask],
        "areas": twice_area[mask] / 2.0, "ids": ids[mask], "mesh_sha256": mesh.mesh_sha256,
    }, direction


def polygon_exterior_segments(geometry) -> np.ndarray:
    polygons = []
    if geometry.geom_type == "Polygon":
        polygons = [geometry]
    elif geometry.geom_type == "MultiPolygon":
        polygons = list(geometry.geoms)
    elif geometry.geom_type == "GeometryCollection":
        polygons = [g for g in geometry.geoms if g.geom_type == "Polygon"]
    segments = []
    for polygon in polygons:
        points = np.asarray(polygon.exterior.coords, dtype=float)
        segments.extend(np.stack([points[:-1], points[1:]], axis=1))
    if not segments:
        raise ValueError("active source-space union has no exterior perimeter")
    return np.asarray(segments)


def nearest_segment(point: np.ndarray, segments: np.ndarray) -> tuple[float, np.ndarray]:
    starts = segments[:, 0]
    vectors = segments[:, 1] - starts
    lengths2 = np.einsum("ij,ij->i", vectors, vectors)
    t = np.clip(np.einsum("ij,ij->i", point - starts, vectors) / lengths2, 0.0, 1.0)
    closest = starts + t[:, None] * vectors
    distances = np.linalg.norm(closest - point, axis=1)
    index = int(np.argmin(distances))
    return float(distances[index]), vectors[index] / math.sqrt(lengths2[index])


def mesh_to_candidate_metric(source_path: Path, mesh_data: dict, direction: dict) -> tuple[dict, list[dict]]:
    source = read_json(source_path)
    frame = source.get("mesh_frame")
    if not frame or frame.get("mesh_sha256") != mesh_data["mesh_sha256"]:
        raise ValueError(f"candidate mesh_frame does not identify fixed GLB: {source_path}")
    source_centres = observation_to_source(mesh_data["centres"], frame, observation_yaw=0.0)
    source_triangles = observation_to_source(
        mesh_data["triangles"].reshape(-1, 3), frame, observation_yaw=0.0
    ).reshape(-1, 3, 3)
    cross = np.cross(source_triangles[:, 1] - source_triangles[:, 0],
                     source_triangles[:, 2] - source_triangles[:, 0])
    normals = cross / np.maximum(np.linalg.norm(cross, axis=1)[:, None], 1e-15)
    polygons = {s["id"]: polygon_for_space(s) for s in source["spaces"]}
    perimeter_cache = {}
    distances, angle_deltas, rows = [], [], []
    for face_id, point3, normal, area in zip(
        mesh_data["ids"], source_centres, normals, mesh_data["areas"]
    ):
        active_ids = tuple(sorted(
            s["id"] for s in source["spaces"]
            if float(s["z_floor"]) - TOLERANCE_M <= point3[2]
            <= float(s["z_floor"]) + float(s["height"]) + TOLERANCE_M
        ))
        if not active_ids:
            raise ValueError(f"no active candidate spaces at mesh face {face_id}, z={point3[2]}")
        if active_ids not in perimeter_cache:
            perimeter_cache[active_ids] = polygon_exterior_segments(
                unary_union([polygons[sid] for sid in active_ids])
            )
        distance, segment_axis = nearest_segment(point3[:2], perimeter_cache[active_ids])
        trace_axis = np.array([-normal[1], normal[0]])
        trace_axis /= np.linalg.norm(trace_axis)
        cosine = float(np.clip(abs(np.dot(trace_axis, segment_axis)), 0.0, 1.0))
        delta = math.degrees(math.acos(cosine))
        distances.append(distance)
        angle_deltas.append(delta)
        rows.append({
            "face_id": int(face_id), "surface_area_m2": float(area),
            "mesh_centroid_in_candidate_frame_xyz_m": point3.tolist(),
            "active_space_ids": list(active_ids),
            "one_way_distance_to_union_exterior_m": distance,
            "axis_difference_degrees": delta,
        })
    distances = np.asarray(distances)
    angles = np.asarray(angle_deltas)
    weights = mesh_data["areas"]
    summary = {
        "candidate": str(source_path.parent),
        "source_model_sha256": source.get("source_model_sha256"),
        "mesh_frame": frame,
        "fixed_face_count": len(rows),
        "fixed_surface_area_m2": float(weights.sum()),
        "one_way_area_weighted_distance_m": {
            "mean": float(np.average(distances, weights=weights)),
            **weighted_quantiles(distances, weights),
            "maximum": float(distances.max()),
        },
        "area_weighted_axis_difference_degrees": {
            "mean": float(np.average(angles, weights=weights)),
            **weighted_quantiles(angles, weights),
            "maximum": float(angles.max()),
        },
    }
    return summary, rows


def markdown_report(report: dict) -> str:
    checks = report["candidate_self_consistency"]
    comparison = report["mesh_comparison"]
    lines = [
        "# Voimatalo developer candidate validation", "",
        f"Overall self-consistency: **{report['overall_self_consistency']}**", "",
        "## Replay and declared-plan checks", "",
        "| Check | Status |", "|---|---|",
    ]
    labels = {
        "source_export_replay": "Source digest and exact export replay",
        "baseline_export_replay_compatibility": "Old candidate exact replay compatibility",
        "same_height_non_overlap": "No same-height source-space overlap",
        "case_plan_storey_coverage": "F1–F8 union covers declared case_plan outline",
        "continuous_cores": "Two continuous cores and per-storey declared doors",
        "declared_door_graph": "Usable spaces reach exterior in declared door graph",
        "opening_mapping": "Opening count and mapping retention",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {checks[key]['status']} |")
    lines += ["", "## One-way mesh diagnostic", ""]
    for item in comparison["candidates"]:
        d = item["one_way_area_weighted_distance_m"]
        a = item["area_weighted_axis_difference_degrees"]
        lines.append(
            f"- `{Path(item['candidate']).name}`: distance mean {d['mean']:.3f} m, "
            f"q50 {d['q50']:.3f} m, q90 {d['q90']:.3f} m; axis difference "
            f"mean {a['mean']:.2f}°, q90 {a['q90']:.2f}°."
        )
    lines += [
        "", "## Interpretation limits", "",
        "- Storey coverage only proves consistency with `case_plan.json`; it is not a truth or fidelity test.",
        "- The mesh metric samples the fixed 2,090 original near-vertical faces at z=8–22 m and measures mesh → candidate exterior only. Extra or missing candidate perimeter is not penalised.",
        "- Missing/cropped end faces and internal partitions cannot be verified by this metric. Relief and slanted facade triangles can bias distance and axis difference.",
        "- Door reachability follows declared, partly inferred doors. It does not establish the real circulation layout.",
        "- The U-shaped service/lobby spaces, their core subtraction and the north-service wall position are case-plan hypotheses, not measurements.",
        "- No exterior classification uses the presence of any adjacent host; perimeters come from same-height source-space unions.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True,
                        help="candidate directory or its source_model.json")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--plan", type=Path, default=WALKTHROUGH / "case_plan.json")
    parser.add_argument("--apertures", type=Path,
                        default=WALKTHROUGH / "assembly_observations.json")
    parser.add_argument("--mesh", type=Path, default=DEFAULT_MESH)
    parser.add_argument("--direction", type=Path, default=WALKTHROUGH / "evidence_01/direction.json")
    parser.add_argument("--report", type=Path,
                        help="JSON output path; must remain inside this validation directory")
    args = parser.parse_args()

    candidate_dir, source_path = candidate_paths(args.candidate)
    baseline_dir, baseline_source_path = candidate_paths(args.baseline)
    report_path = (args.report or HERE / f"{candidate_dir.name}_validation.json").resolve()
    if HERE.resolve() not in report_path.parents:
        raise ValueError("validation reports must be written inside the validation directory")
    detail_path = report_path.with_name(report_path.stem + "_mesh_faces.json")
    markdown_path = report_path.with_suffix(".md")

    source = read_json(source_path)
    proposal = read_json(candidate_dir / "proposal.json")
    plan = read_json(args.plan)
    baseline_source = read_json(baseline_source_path)
    checks = {
        "source_export_replay": check_replay(candidate_dir, source_path, source),
        "baseline_export_replay_compatibility": check_replay(
            baseline_dir, baseline_source_path, baseline_source
        ),
        "same_height_non_overlap": check_no_same_height_overlap(source),
        "case_plan_storey_coverage": check_storey_coverage(source, plan),
        "continuous_cores": check_cores(source, plan),
        "declared_door_graph": check_door_graph(source),
        "opening_mapping": check_openings(candidate_dir, source, proposal, plan, args.apertures),
    }
    overall = "pass" if all(row["status"] == "pass" for row in checks.values()) else "fail"

    mesh_data, direction = load_fixed_mesh_faces(args.mesh, args.direction)
    baseline_metric, baseline_faces = mesh_to_candidate_metric(baseline_source_path, mesh_data, direction)
    candidate_metric, candidate_faces = mesh_to_candidate_metric(source_path, mesh_data, direction)
    mesh_comparison = {
        "interpretation": "one-way area-weighted diagnostic, original mesh faces to each candidate's declared same-height source-space-union exterior",
        "not_ground_truth": True,
        "not_completeness_metric": True,
        "fixed_selection": {
            "source": str(args.direction.resolve()),
            "mesh": str(args.mesh.resolve()),
            "mesh_sha256": mesh_data["mesh_sha256"],
            "z_band_m": direction["original_z_band_m"],
            "max_tilt_from_vertical_degrees": direction["max_tilt_from_vertical_degrees"],
            "face_count": len(mesh_data["ids"]),
            "surface_area_m2": float(mesh_data["areas"].sum()),
            "face_ids_sha256": hashlib.sha256(
                json.dumps(mesh_data["ids"].tolist(), separators=(",", ":")).encode()
            ).hexdigest(),
        },
        "candidates": [baseline_metric, candidate_metric],
        "limitations": [
            "Candidate perimeters with no selected mesh surface are unpenalised.",
            "Unknown/cropped end faces and internal partitions cannot be verified.",
            "Relief, facade ornament and slanted triangles can bias point distance and local axis difference.",
            "Each candidate's declared mesh_frame is part of the comparison; the baseline and new candidate may use different yaw values.",
        ],
    }
    report = {
        "schema": "voimatalo_developer_candidate_validation_v1",
        "candidate": str(candidate_dir), "baseline_evaluation_only": str(baseline_dir),
        "overall_self_consistency": overall,
        "candidate_self_consistency": checks,
        "mesh_comparison": mesh_comparison,
        "claims": {
            "case_plan_coverage_is_self_consistency_not_truth": True,
            "interior_scheme_is_inferred_not_measured": True,
            "service_and_lobby_shapes_are_case_plan_hypotheses_not_measurements": True,
            "old_candidate_was_read_only_for_evaluation_and_not_generation": True,
            "fidelity_pass_claimed": False,
        },
    }
    details = {
        "fixed_face_ids": mesh_data["ids"].tolist(),
        "baseline": baseline_faces,
        "candidate": candidate_faces,
    }
    detail_path.write_text(json.dumps(details, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    report["mesh_comparison"]["face_detail_artifact"] = {
        "path": str(detail_path), "sha256": sha256(detail_path),
        "contents": "fixed face IDs plus per-candidate centroid, active union, distance and axis difference",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    markdown_path.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({
        "status": overall, "report": str(report_path), "mesh_details": str(detail_path),
        "baseline_distance_mean_m": baseline_metric["one_way_area_weighted_distance_m"]["mean"],
        "candidate_distance_mean_m": candidate_metric["one_way_area_weighted_distance_m"]["mean"],
    }, ensure_ascii=False))
    if overall != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
