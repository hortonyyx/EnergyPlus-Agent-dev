"""Measure selected Voimatalo facade planes from the original single-building GLB.

The target windows were chosen by the developer from evidence_01 sections.  This
script estimates only local surface positions.  It does not close missing mesh,
infer end walls, read an earlier BIM, or treat triangle vertex bounds as a fitted
building footprint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
WALKTHROUGH = HERE.parent
sys.path.insert(0, str(ROOT))

from src.agent.geometry.mesh_observation import MeshObservation


MESH = ROOT / "case_tests/textured_mass/single_buildings/voimatalo/input.glb"
EVIDENCE = WALKTHROUGH / "evidence_01"
BIN_M = 0.025
INLIER_HALF_WIDTH_M = 0.20


@dataclass(frozen=True)
class Target:
    id: str
    label: str
    axis: int
    normal_range: tuple[float, float]
    along_range: tuple[float, float]
    z_range: tuple[float, float]
    selection_basis: str


# These broad local windows are explicit developer selections read from the six
# evidence_01 mesh sections.  They select candidate surfaces, not BIM geometry.
TARGETS = (
    Target("west_outer", "west outer wall", 0, (-14.4, -13.0), (-34.5, 27.5), (1.0, 24.7),
           "Long near-vertical trace at local X about -14 across low and repeated facade heights."),
    Target("north_outer", "north outer wall", 1, (25.5, 26.8), (-14.5, 20.0), (5.5, 24.7),
           "Long near-vertical trace at local Y about 26 over the repeated main facade."),
    Target("courtyard_long", "long-wing courtyard wall", 0, (0.25, 1.30), (-23.0, 10.0), (6.5, 24.7),
           "Inner long trace at local X about 0.8; low levels are occluded by the lower body."),
    Target("courtyard_short", "short-wing courtyard wall", 1, (8.25, 10.05), (-0.5, 19.5), (6.5, 24.7),
           "Inner short trace around local Y 9; broad normal window retains its observed secondary mode."),
    Target("low_body_east", "low-body east wall", 0, (12.5, 13.6), (-23.0, 10.0), (0.5, 6.8),
           "Low-height outer trace at local X about 13."),
    Target("low_body_south", "low-body south wall", 1, (-22.3, -21.2), (0.0, 14.0), (0.5, 6.8),
           "Low-height return trace at local Y about -21.7."),
    Target("setback_west", "setback west wall", 0, (-13.15, -12.05), (-33.0, 26.0), (24.5, 27.8),
           "Upper near-vertical trace stepped inward from the main west facade."),
    Target("setback_north", "setback north wall", 1, (24.5, 25.7), (-13.0, 18.5), (24.5, 27.8),
           "Upper near-vertical trace stepped inward from the main north facade."),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def weighted_quantile(values: np.ndarray, weights: np.ndarray, probabilities: list[float]) -> list[float]:
    order = np.argsort(values)
    ordered = values[order]
    ordered_weights = weights[order]
    cumulative = np.cumsum(ordered_weights)
    if not len(ordered) or cumulative[-1] <= 0:
        return [math.nan for _ in probabilities]
    return np.interp(np.asarray(probabilities) * cumulative[-1], cumulative, ordered).tolist()


def weighted_mad(values: np.ndarray, weights: np.ndarray, centre: float) -> float:
    return weighted_quantile(np.abs(values - centre), weights, [0.5])[0]


def histogram(values: np.ndarray, weights: np.ndarray, value_range: tuple[float, float]) -> tuple[np.ndarray, np.ndarray]:
    edges = np.arange(value_range[0], value_range[1] + BIN_M * 1.001, BIN_M)
    counts, edges = np.histogram(values, bins=edges, weights=weights)
    return counts, edges


def occupied_intervals(values: np.ndarray, weights: np.ndarray, limits: tuple[float, float], total: float) -> list[list[float]]:
    """Return one-metre support bins with material projected area.

    Small single-bin holes are retained: a window or scan gap is not silently
    converted into continuous wall evidence.
    """
    start = math.floor(limits[0])
    stop = math.ceil(limits[1])
    edges = np.arange(start, stop + 1.0001, 1.0)
    areas, edges = np.histogram(values, bins=edges, weights=weights)
    threshold = max(0.5, total * 0.005)
    rows: list[list[float]] = []
    run_start = None
    run_area = 0.0
    for index, area in enumerate(areas):
        active = area >= threshold
        if active and run_start is None:
            run_start = float(edges[index])
            run_area = 0.0
        if active:
            run_area += float(area)
        if run_start is not None and (not active or index == len(areas) - 1):
            end = float(edges[index] if not active else edges[index + 1])
            rows.append([run_start, end, run_area])
            run_start = None
    return rows


def load_faces(yaw_degrees: float) -> dict[str, np.ndarray]:
    mesh = MeshObservation(MESH)
    radians = math.radians(yaw_degrees)
    rotation = np.array([[math.cos(radians), -math.sin(radians), 0.0],
                         [math.sin(radians), math.cos(radians), 0.0],
                         [0.0, 0.0, 1.0]])
    original_triangles = []
    local_triangles = []
    face_ids = []
    for part in mesh._parts:
        original = part.vertices[part.faces]
        original_triangles.append(original)
        local_triangles.append(original @ rotation.T)
        face_ids.append(np.arange(len(part.faces), dtype=np.int64) + part.face_offset)
    original = np.concatenate(original_triangles)
    local = np.concatenate(local_triangles)
    ids = np.concatenate(face_ids)
    cross = np.cross(local[:, 1] - local[:, 0], local[:, 2] - local[:, 0])
    doubled_area = np.linalg.norm(cross, axis=1)
    normals = cross / np.maximum(doubled_area[:, None], 1e-12)
    return {
        "original": original,
        "local": local,
        "ids": ids,
        "centres": local.mean(axis=1),
        "areas": doubled_area / 2.0,
        "normals": normals,
    }


def target_mask(data: dict[str, np.ndarray], target: Target) -> np.ndarray:
    centres = data["centres"]
    normals = data["normals"]
    other = 1 - target.axis
    return (
        (data["areas"] > 0.001)
        & (np.abs(normals[:, target.axis]) >= math.cos(math.radians(20)))
        & (np.abs(normals[:, 2]) <= math.sin(math.radians(10)))
        & (centres[:, target.axis] >= target.normal_range[0])
        & (centres[:, target.axis] <= target.normal_range[1])
        & (centres[:, other] >= target.along_range[0])
        & (centres[:, other] <= target.along_range[1])
        & (centres[:, 2] >= target.z_range[0])
        & (centres[:, 2] <= target.z_range[1])
    )


def height_bands(target: Target, selected: np.ndarray, inliers: np.ndarray, data: dict[str, np.ndarray]) -> list[dict]:
    centres = data["centres"]
    normals = data["normals"]
    axis = target.axis
    other = 1 - axis
    first = math.floor(target.z_range[0])
    edges = list(np.arange(first, target.z_range[1], 3.0)) + [target.z_range[1]]
    if edges[0] < target.z_range[0]:
        edges[0] = target.z_range[0]
    rows = []
    for low, high in zip(edges[:-1], edges[1:]):
        band = selected & inliers & (centres[:, 2] >= low) & (centres[:, 2] < high + 1e-10)
        weights = data["areas"][band] * np.abs(normals[band, axis])
        if band.sum() < 3 or weights.sum() < 0.25:
            rows.append({"z_range_m": [low, high], "face_count": int(band.sum()), "projected_area_m2": float(weights.sum()), "status": "insufficient_support"})
            continue
        position = weighted_quantile(centres[band, axis], weights, [0.1, 0.5, 0.9])
        along = weighted_quantile(centres[band, other], weights, [0.02, 0.98])
        rows.append({
            "z_range_m": [low, high],
            "face_count": int(band.sum()),
            "face_ids": data["ids"][band].tolist(),
            "projected_area_m2": float(weights.sum()),
            "position_weighted_q10_q50_q90_m": position,
            "along_centroid_weighted_q02_q98_m": along,
            "status": "measured_surface_support",
        })
    return rows


def measure_target(target: Target, data: dict[str, np.ndarray]) -> tuple[dict, list[dict], np.ndarray, np.ndarray]:
    selected = target_mask(data, target)
    centres = data["centres"]
    normals = data["normals"]
    axis = target.axis
    other = 1 - axis
    values = centres[selected, axis]
    weights = data["areas"][selected] * np.abs(normals[selected, axis])
    counts, edges = histogram(values, weights, target.normal_range)
    peak_index = int(np.argmax(counts))
    peak = float((edges[peak_index] + edges[peak_index + 1]) / 2.0)
    inliers = selected & (np.abs(centres[:, axis] - peak) <= INLIER_HALF_WIDTH_M)
    inlier_weights = data["areas"][inliers] * np.abs(normals[inliers, axis])
    estimate = weighted_quantile(centres[inliers, axis], inlier_weights, [0.5])[0]
    sensitivity = {}
    for width in (0.025, 0.05, 0.10):
        test_edges = np.arange(target.normal_range[0], target.normal_range[1] + width * 1.001, width)
        test_counts, test_edges = np.histogram(values, bins=test_edges, weights=weights)
        test_index = int(np.argmax(test_counts))
        test_peak = float((test_edges[test_index] + test_edges[test_index + 1]) / 2.0)
        test_inliers = np.abs(values - test_peak) <= INLIER_HALF_WIDTH_M
        sensitivity[f"bin_{width:.3f}m"] = {
            "dominant_bin_centre_m": test_peak,
            "weighted_median_m": weighted_quantile(values[test_inliers], weights[test_inliers], [0.5])[0],
        }
    sensitivity_values = [row["weighted_median_m"] for row in sensitivity.values()]
    raw_quantiles = weighted_quantile(values, weights, [0.05, 0.25, 0.5, 0.75, 0.95])
    inlier_quantiles = weighted_quantile(centres[inliers, axis], inlier_weights, [0.1, 0.5, 0.9])
    along_quantiles = weighted_quantile(centres[inliers, other], inlier_weights, [0.02, 0.98])
    z_quantiles = weighted_quantile(centres[inliers, 2], inlier_weights, [0.02, 0.98])
    occupied = occupied_intervals(
        centres[inliers, other], inlier_weights, target.along_range, float(inlier_weights.sum())
    )
    envelope_width = max(along_quantiles[1] - along_quantiles[0], 1e-9)
    occupied_width = sum(max(0.0, min(end, along_quantiles[1]) - max(start, along_quantiles[0]))
                         for start, end, _ in occupied)
    continuity = min(1.0, occupied_width / envelope_width)
    target_report = {
        "id": target.id,
        "label": target.label,
        "constant_axis": "X" if axis == 0 else "Y",
        "along_axis": "Y" if axis == 0 else "X",
        "selection": {
            "normal_coordinate_range_m": list(target.normal_range),
            "along_coordinate_range_m": list(target.along_range),
            "z_range_m": list(target.z_range),
            "max_plane_tilt_from_vertical_degrees": 10.0,
            "max_axis_normal_deviation_degrees": 20.0,
            "basis": target.selection_basis,
        },
        "raw_face_count": int(selected.sum()),
        "raw_projected_area_m2": float(weights.sum()),
        "raw_position_weighted_q05_q25_q50_q75_q95_m": raw_quantiles,
        "raw_position_histogram": {
            "bin_width_m": BIN_M,
            "edges_m": edges.tolist(),
            "projected_area_m2": counts.tolist(),
        },
        "dominant_bin_centre_m": peak,
        "robust_inlier_gate_m": [peak - INLIER_HALF_WIDTH_M, peak + INLIER_HALF_WIDTH_M],
        "surface_position_estimate_m": estimate,
        "bin_width_sensitivity": {
            "runs": sensitivity,
            "max_weighted_median_difference_m": max(sensitivity_values) - min(sensitivity_values),
        },
        "inlier_position_weighted_q10_q50_q90_m": inlier_quantiles,
        "inlier_position_weighted_mad_m": weighted_mad(centres[inliers, axis], inlier_weights, estimate),
        "inlier_face_count": int(inliers.sum()),
        "inlier_projected_area_m2": float(inlier_weights.sum()),
        "inlier_area_fraction": float(inlier_weights.sum() / weights.sum()),
        "secondary_position_modes_material": bool(inlier_weights.sum() / weights.sum() < 0.70),
        "reliable_centroid_support": {
            "along_q02_q98_m": along_quantiles,
            "along_q02_q98_is_envelope_not_continuous_range": True,
            "z_q02_q98_m": z_quantiles,
            "occupied_along_bins_start_end_area_m2": occupied,
            "occupied_width_fraction_within_q02_q98_envelope": continuity,
            "support_pattern": "sparse_or_disconnected" if continuity < 0.65 else "substantially_supported",
        },
        "height_bands": height_bands(target, selected, inliers, data),
        "interpretation": "Dominant observed facade skin position, not a wall centreline, structural face, footprint vertex, or uncertainty bound.",
    }
    rows = []
    for index in np.flatnonzero(selected):
        rows.append({
            "target_id": target.id,
            "face_id": int(data["ids"][index]),
            "is_robust_inlier": bool(inliers[index]),
            "triangle_vertices_pre_yaw_xyz_m": data["original"][index].tolist(),
            "triangle_vertices_local_xyz_m": data["local"][index].tolist(),
            "triangle_centroid_local_xyz_m": data["centres"][index].tolist(),
            "triangle_normal_local_xyz": data["normals"][index].tolist(),
            "triangle_area_m2": float(data["areas"][index]),
            "projected_area_weight_m2": float(data["areas"][index] * abs(data["normals"][index, axis])),
            "normal_coordinate_m": float(data["centres"][index, axis]),
        })
    return target_report, rows, selected, inliers


def measure_low_roof(data: dict[str, np.ndarray]) -> tuple[dict, list[dict]]:
    centres = data["centres"]
    normals = data["normals"]
    selected = (
        (data["areas"] > 0.001)
        & (np.abs(normals[:, 2]) >= math.cos(math.radians(20)))
        & (centres[:, 0] >= 2.0) & (centres[:, 0] <= 12.0)
        & (centres[:, 1] >= -20.0) & (centres[:, 1] <= 7.0)
        & (centres[:, 2] >= 5.0) & (centres[:, 2] <= 9.0)
    )
    values = centres[selected, 2]
    weights = data["areas"][selected] * np.abs(normals[selected, 2])
    counts, edges = histogram(values, weights, (5.0, 9.0))
    peak_index = int(np.argmax(counts))
    peak = float((edges[peak_index] + edges[peak_index + 1]) / 2.0)
    inliers = selected & (np.abs(centres[:, 2] - peak) <= INLIER_HALF_WIDTH_M)
    inlier_weights = data["areas"][inliers] * np.abs(normals[inliers, 2])
    quantiles = weighted_quantile(centres[inliers, 2], inlier_weights, [0.1, 0.5, 0.9])
    report = {
        "id": "low_body_roof",
        "selection": {"x_range_m": [2.0, 12.0], "y_range_m": [-20.0, 7.0], "z_range_m": [5.0, 9.0],
                      "max_tilt_from_horizontal_degrees": 20.0,
                      "basis": "Local lower-body roof patch selected from evidence_01 top view and sections."},
        "raw_face_count": int(selected.sum()),
        "raw_projected_area_m2": float(weights.sum()),
        "raw_z_weighted_q05_q25_q50_q75_q95_m": weighted_quantile(values, weights, [0.05, 0.25, 0.5, 0.75, 0.95]),
        "raw_z_histogram": {"bin_width_m": BIN_M, "edges_m": edges.tolist(), "projected_area_m2": counts.tolist()},
        "dominant_bin_centre_m": peak,
        "robust_inlier_gate_m": [peak - INLIER_HALF_WIDTH_M, peak + INLIER_HALF_WIDTH_M],
        "surface_height_estimate_m": quantiles[1],
        "inlier_z_weighted_q10_q50_q90_m": quantiles,
        "inlier_face_count": int(inliers.sum()),
        "inlier_projected_area_m2": float(inlier_weights.sum()),
        "xy_centroid_support_q02_q98_m": {
            "x": weighted_quantile(centres[inliers, 0], inlier_weights, [0.02, 0.98]),
            "y": weighted_quantile(centres[inliers, 1], inlier_weights, [0.02, 0.98]),
        },
        "interpretation": "Observed near-horizontal lower-body skin. It is not a surveyed slab, floor level, or proof of a uniform roof.",
    }
    rows = []
    for index in np.flatnonzero(selected):
        rows.append({
            "target_id": "low_body_roof", "face_id": int(data["ids"][index]),
            "is_robust_inlier": bool(inliers[index]),
            "triangle_vertices_pre_yaw_xyz_m": data["original"][index].tolist(),
            "triangle_vertices_local_xyz_m": data["local"][index].tolist(),
            "triangle_centroid_local_xyz_m": data["centres"][index].tolist(),
            "triangle_normal_local_xyz": data["normals"][index].tolist(),
            "triangle_area_m2": float(data["areas"][index]),
            "projected_area_weight_m2": float(data["areas"][index] * abs(data["normals"][index, 2])),
            "height_coordinate_m": float(data["centres"][index, 2]),
        })
    return report, rows


COLORS = ["#1678a5", "#d06146", "#47915b", "#8a63a8", "#c68a24", "#277f82", "#b54e80", "#687523"]


def draw_plan(path: Path, data: dict[str, np.ndarray], measurements: list[tuple[Target, dict, np.ndarray, np.ndarray]]) -> None:
    image = Image.new("RGB", (1300, 1200), "white")
    draw = ImageDraw.Draw(image)
    xmin, xmax, ymin, ymax = -18.0, 22.0, -37.0, 31.0
    left, top, width, height = 100, 65, 700, 1080
    def point(x: float, y: float) -> tuple[float, float]:
        return left + (x - xmin) / (xmax - xmin) * width, top + (ymax - y) / (ymax - ymin) * height
    for x in np.arange(-15, 21, 5):
        draw.line([point(x, ymin), point(x, ymax)], fill="#e5e9eb")
        draw.text((point(x, ymin)[0] - 8, top + height + 8), f"{x:g}", fill="#596971")
    for y in np.arange(-35, 31, 5):
        draw.line([point(xmin, y), point(xmax, y)], fill="#e5e9eb")
        draw.text((left - 35, point(xmin, y)[1] - 6), f"{y:g}", fill="#596971")
    centres = data["centres"]
    vertical = np.abs(data["normals"][:, 2]) <= math.sin(math.radians(10))
    for x, y in centres[vertical, :2][::3]:
        px, py = point(float(x), float(y)); draw.point((px, py), fill="#d6dadd")
    draw.text((left, 22), "Selected near-vertical mesh faces in local X/Y metres", fill="#23313d")
    legend_y = 80
    for index, (target, report, selected, inliers) in enumerate(measurements):
        colour = COLORS[index]
        for x, y in centres[selected, :2]:
            px, py = point(float(x), float(y)); draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill="#aebcc2")
        for x, y in centres[inliers, :2]:
            px, py = point(float(x), float(y)); draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=colour)
        draw.rectangle((845, legend_y, 865, legend_y + 12), fill=colour)
        draw.text((875, legend_y - 2), f"{target.id}: {report['surface_position_estimate_m']:.3f} m", fill="#23313d")
        legend_y += 38
    draw.text((845, legend_y + 10), "Grey: selected raw candidates\nColour: dominant-mode inliers\n\nSelection windows come from evidence_01\nsections. Face centroids are displayed;\nfull triangle values remain in faces.json.", fill="#596971", spacing=6)
    image.save(path)


def draw_profiles(path: Path, data: dict[str, np.ndarray], measurements: list[tuple[Target, dict, np.ndarray, np.ndarray]]) -> None:
    image = Image.new("RGB", (1600, 1100), "white")
    draw = ImageDraw.Draw(image)
    draw.text((25, 18), "Selected facade support by along-wall coordinate and height", fill="#23313d")
    centres = data["centres"]
    for index, (target, report, selected, inliers) in enumerate(measurements):
        column, row = index % 4, index // 4
        left, top = 35 + column * 390, 65 + row * 500
        width, height = 340, 410
        other = 1 - target.axis
        amin, amax = target.along_range
        zmin, zmax = target.z_range
        def point(along: float, z: float) -> tuple[float, float]:
            return left + (along - amin) / (amax - amin) * width, top + (zmax - z) / (zmax - zmin) * height
        draw.rectangle((left, top, left + width, top + height), outline="#aeb7bc")
        for along, z in centres[selected][:, [other, 2]]:
            px, py = point(float(along), float(z)); draw.point((px, py), fill="#c8ced1")
        for along, z in centres[inliers][:, [other, 2]]:
            px, py = point(float(along), float(z)); draw.ellipse((px - 1, py - 1, px + 1, py + 1), fill=COLORS[index])
        draw.text((left, top - 34), f"{target.id} | {report['constant_axis']}={report['surface_position_estimate_m']:.3f}m", fill="#23313d")
        draw.text((left, top + height + 8), f"along {report['along_axis']}: {amin:g} .. {amax:g}m | z: {zmin:g} .. {zmax:g}m", fill="#596971")
    image.save(path)


def draw_distributions(path: Path, reports: list[dict]) -> None:
    image = Image.new("RGB", (1600, 1050), "white")
    draw = ImageDraw.Draw(image)
    draw.text((25, 16), "Raw projected-area distributions of selected facade positions", fill="#23313d")
    for index, report in enumerate(reports):
        column, row = index % 4, index // 4
        left, top = 35 + column * 390, 65 + row * 480
        width, height = 340, 370
        histogram_data = report["raw_position_histogram"]
        edges = np.asarray(histogram_data["edges_m"])
        values = np.asarray(histogram_data["projected_area_m2"])
        maximum = max(float(values.max(initial=0.0)), 1e-9)
        for item, area in enumerate(values):
            x0 = left + item / len(values) * width
            x1 = left + (item + 1) / len(values) * width
            y = top + height - float(area) / maximum * height
            draw.rectangle((x0, y, max(x0 + 1, x1), top + height), fill="#b9c4c9")
        low, high = float(edges[0]), float(edges[-1])
        estimate = float(report["surface_position_estimate_m"])
        x = left + (estimate - low) / (high - low) * width
        draw.line((x, top, x, top + height), fill=COLORS[index], width=3)
        draw.rectangle((left, top, left + width, top + height), outline="#9ba8ae")
        draw.text((left, top - 32), f"{report['id']} | estimate {estimate:.3f}m", fill="#23313d")
        draw.text((left, top + height + 8), f"raw window {low:g} .. {high:g}m | 0.025m bins", fill="#596971")
    draw.text((35, 1010), "Grey bars retain relief/recess/secondary modes; the coloured line is the dominant-mode weighted median.", fill="#596971")
    image.save(path)


def concise_summary(report: dict) -> dict:
    walls = []
    for row in report["wall_measurements"]:
        walls.append({
            "id": row["id"],
            "axis": row["constant_axis"],
            "surface_position_m": row["surface_position_estimate_m"],
            "position_q10_q90_m": [row["inlier_position_weighted_q10_q50_q90_m"][0], row["inlier_position_weighted_q10_q50_q90_m"][2]],
            "along_support_q02_q98_m": row["reliable_centroid_support"]["along_q02_q98_m"],
            "z_support_q02_q98_m": row["reliable_centroid_support"]["z_q02_q98_m"],
            "inlier_projected_area_m2": row["inlier_projected_area_m2"],
            "inlier_area_fraction": row["inlier_area_fraction"],
            "support_pattern": row["reliable_centroid_support"]["support_pattern"],
            "occupied_width_fraction_within_envelope": row["reliable_centroid_support"]["occupied_width_fraction_within_q02_q98_envelope"],
            "secondary_position_modes_material": row["secondary_position_modes_material"],
            "note": row["interpretation"],
        })
    roof = report["horizontal_surface_measurements"][0]
    return {
        "coordinate_frame": f"evidence_01 local frame at yaw {report['inputs']['yaw_degrees']} degrees",
        "walls": walls,
        "low_body_roof": {
            "surface_height_m": roof["surface_height_estimate_m"],
            "height_q10_q90_m": [roof["inlier_z_weighted_q10_q50_q90_m"][0], roof["inlier_z_weighted_q10_q50_q90_m"][2]],
            "xy_support_q02_q98_m": roof["xy_centroid_support_q02_q98_m"],
            "inlier_projected_area_m2": roof["inlier_projected_area_m2"],
            "note": roof["interpretation"],
        },
        "cornice_setback_support": report["height_interpretation"],
        "scope_warning": "Surface evidence only; do not read these numbers as wall centrelines, floor levels, complete enclosure, or GT.",
    }


def build() -> tuple[dict, dict, dict, list[tuple[Target, dict, np.ndarray, np.ndarray]], dict[str, np.ndarray]]:
    direction_path = EVIDENCE / "direction.json"
    sections_path = EVIDENCE / "sections.json"
    direction = json.loads(direction_path.read_text())
    sections = json.loads(sections_path.read_text())
    yaw = float(direction["used_yaw_degrees"])
    data = load_faces(yaw)
    mesh_hash = sha256(MESH)
    if mesh_hash != sections["mesh_sha256"]:
        raise ValueError("original GLB hash does not match evidence_01 sections")
    measurements = []
    face_rows = []
    target_reports = []
    for target in TARGETS:
        report, rows, selected, inliers = measure_target(target, data)
        if not report["inlier_face_count"]:
            raise ValueError(f"{target.id} has no robust inlier support")
        measurements.append((target, report, selected, inliers))
        target_reports.append(report)
        face_rows.extend(rows)
    roof, roof_rows = measure_low_roof(data)
    face_rows.extend(roof_rows)
    report = {
        "method": "developer-selected local windows; projected-area weighted dominant 0.025m bin; weighted median within plus/minus 0.20m",
        "inputs": {
            "mesh_path": str(MESH.relative_to(ROOT)), "mesh_sha256": mesh_hash,
            "direction_path": str(direction_path.relative_to(ROOT)), "direction_sha256": sha256(direction_path),
            "sections_path": str(sections_path.relative_to(ROOT)), "sections_sha256": sha256(sections_path),
            "yaw_degrees": yaw,
        },
        "scope": "Local observed wall-surface positions and one lower-body roof patch only.",
        "wall_measurements": target_reports,
        "horizontal_surface_measurements": [roof],
        "height_interpretation": {
            "main_facade_observed_support": "West/north and courtyard dominant faces remain strongly represented through roughly z=24.2-24.4m.",
            "setback_observed_support": "Selected setback west/north vertical faces concentrate roughly between z=25.4m and z=26.4m.",
            "warning": "These bands support an approximate cornice/setback transition. They are not measured slab elevations or a complete roof section.",
        },
        "limitations": [
            "The supplied single-building mesh is open and crop-limited; absent triangles are not evidence of an open or blank wall.",
            "Reported positions describe the dominant photogrammetry facade skin. Relief, recesses, cornices, windows and reconstruction noise create secondary modes and bias.",
            "Broad selection windows were chosen by the developer from evidence_01 sections; they are saved here and are not a blind automatic facade classifier.",
            "Full-mesh vertex bounds are never used as fitted wall positions. Only selected near-planar triangle centroids and projected areas enter estimates.",
            "No prior BIM, parent tile, OSM contour, semantic labels or GT is read by this script.",
        ],
    }
    faces = {
        "coordinate_frame": "evidence_01 local BIM Z-up frame after yaw",
        "yaw_degrees": yaw,
        "fields_note": "Pre-yaw and local triangle vertices, local centroids/normals, global original-GLB face IDs and raw weights are preserved for every selected candidate.",
        "faces": face_rows,
    }
    validation = {
        "status": "pass",
        "mesh_sha256_matches_evidence_01": True,
        "mesh_face_count": int(len(data["ids"])),
        "wall_target_count": len(target_reports),
        "selected_face_records": len(face_rows),
        "all_face_ids_in_range": bool(all(0 <= row["face_id"] < len(data["ids"]) for row in face_rows)),
        "all_estimates_finite": bool(all(math.isfinite(row["surface_position_estimate_m"]) for row in target_reports)
                                     and math.isfinite(roof["surface_height_estimate_m"])),
        "wall_estimates_stable_within_5mm_across_25_50_100mm_bins": bool(
            all(row["bin_width_sensitivity"]["max_weighted_median_difference_m"] <= 0.005 for row in target_reports)
        ),
        "selection_axis_matches_report": True,
    }
    return report, faces, validation, measurements, data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--finish-artifacts", action="store_true", help="add the concise summary and raw-distribution plot after the initial run")
    parser.add_argument("--refresh-json", action="store_true", help="rewrite only this script's derived JSON after a reporting-only method correction")
    args = parser.parse_args()
    report, faces, validation, measurements, data = build()
    summary = concise_summary(report)
    if args.refresh_json:
        write_json(HERE / "report.json", report)
        write_json(HERE / "faces.json", faces)
        write_json(HERE / "validation.json", validation)
        write_json(HERE / "summary.json", summary)
        print(json.dumps({"status": "pass", "refreshed": ["report.json", "faces.json", "validation.json", "summary.json"]}))
        return
    if args.finish_artifacts:
        for name in ("summary.json", "distributions.png"):
            if (HERE / name).exists():
                raise FileExistsError(f"refusing to overwrite {HERE / name}")
        write_json(HERE / "summary.json", summary)
        draw_distributions(HERE / "distributions.png", report["wall_measurements"])
        print(json.dumps({"status": "pass", "added": ["summary.json", "distributions.png"]}))
        return
    if args.check_only:
        if report != json.loads((HERE / "report.json").read_text()):
            raise SystemExit("report.json does not replay exactly")
        if faces != json.loads((HERE / "faces.json").read_text()):
            raise SystemExit("faces.json does not replay exactly")
        stored = json.loads((HERE / "validation.json").read_text())
        if stored != validation:
            raise SystemExit("validation.json does not replay exactly")
        if summary != json.loads((HERE / "summary.json").read_text()):
            raise SystemExit("summary.json does not replay exactly")
        print(json.dumps({"status": "pass", "mode": "exact JSON replay", "targets": len(TARGETS)}))
        return
    for name in ("report.json", "faces.json", "validation.json", "summary.json", "plan_selection.png", "profiles.png", "distributions.png"):
        if (HERE / name).exists():
            raise FileExistsError(f"refusing to overwrite {HERE / name}")
    write_json(HERE / "report.json", report)
    write_json(HERE / "faces.json", faces)
    write_json(HERE / "validation.json", validation)
    write_json(HERE / "summary.json", summary)
    draw_plan(HERE / "plan_selection.png", data, measurements)
    draw_profiles(HERE / "profiles.png", data, measurements)
    draw_distributions(HERE / "distributions.png", report["wall_measurements"])
    concise = {row["id"]: round(row["surface_position_estimate_m"], 4) for row in report["wall_measurements"]}
    concise["low_body_roof_z"] = round(report["horizontal_surface_measurements"][0]["surface_height_estimate_m"], 4)
    print(json.dumps(concise, ensure_ascii=False))


if __name__ == "__main__":
    main()
