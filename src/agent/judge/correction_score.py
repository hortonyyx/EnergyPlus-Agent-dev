"""Correction-stage gt scorer.

Judge-side adapter for accepted ``CorrectedGeometry`` attempt outputs.  It
extracts the same wall/window primitives used by ``reading_score`` and reuses
the shared gt derivation + matchers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from src.agent.correction.cell_geometry import cell_bbox, cell_polygon
from src.agent.correction.schema import CorrectedGeometry

from .reading_score import (
    DEFAULT_COMPLETE_EPS_M,
    DEFAULT_EXTENT_TOL_M,
    DEFAULT_POSITION_TOL_M,
    DEFAULT_WALL_TOL_M,
    DEFAULT_WIN_CENTRE_TOL_M,
    FloorScore,
    WallSegment,
    _dedupe,
    _dedupe_segments,
    _match_lines,
    _match_wall_segments,
    _match_window_segments,
    derive_gt_walls,
    derive_gt_wall_segments,
    derive_gt_windows,
    match_boundary,
)
from .elevation_score import (
    DEFAULT_ELEVATION_ALONG_TOL_M,
    DEFAULT_FLOOR_LINE_TOL_M,
    DEFAULT_OVERLAP_ACCEPT,
    DEFAULT_OVERLAP_COMPLETE,
    DEFAULT_HEAD_TOL_M,
    DEFAULT_SILL_TOL_M,
    DEFAULT_WIDTH_TOL_M,
    ElevationScoreResult,
    score_correction_elevation_windows,
)

_BOUNDARY_EPS_M = 0.30


@dataclass
class CorrectionScoreResult:
    scores: dict[str, FloorScore]
    evidence: list[dict] = field(default_factory=list)
    floor_map: dict[str, str] = field(default_factory=dict)
    elevation: ElevationScoreResult | None = None


def _floor_number(name: str) -> int | None:
    m = re.search(r"(?<!\d)(\d+)(?!\d)", name or "")
    return int(m.group(1)) if m else None


def _map_floors(geom: CorrectedGeometry, gt: dict) -> tuple[dict[str, str], list[dict]]:
    gt_floors = list(gt.get("floors", []))
    gt_by_name = {str(f.get("name")): f for f in gt_floors}
    used: set[str] = set()
    mapping: dict[str, str] = {}
    evidence: list[dict] = []

    # 1. exact name
    for fl in geom.floors:
        if fl.name in gt_by_name:
            mapping[fl.name] = fl.name
            used.add(fl.name)

    # 2. numeric floor ordinal: F1 / 1F / Floor 1 -> gt floor #1
    for fl in geom.floors:
        if fl.name in mapping:
            continue
        n = _floor_number(fl.name)
        if n is None:
            continue
        idx = n - 1
        if 0 <= idx < len(gt_floors):
            candidate = str(gt_floors[idx].get("name"))
            if candidate not in used:
                mapping[fl.name] = candidate
                used.add(candidate)

    # 3. z-floor first, then list order for any remaining unique slot.
    remaining_gt = [f for f in gt_floors if str(f.get("name")) not in used]
    for fl in sorted((f for f in geom.floors if f.name not in mapping), key=lambda f: f.z_floor):
        z_matches = [
            f for f in remaining_gt
            if f.get("z_floor") is not None and abs(float(f["z_floor"]) - float(fl.z_floor)) <= 0.45
        ]
        chosen = z_matches[0] if z_matches else (remaining_gt[0] if remaining_gt else None)
        if chosen is None:
            evidence.append(
                {
                    "type": "unmatched_floor",
                    "floor": fl.name,
                    "z_floor": fl.z_floor,
                    "reason": "no remaining gt floor",
                }
            )
            continue
        gt_name = str(chosen.get("name"))
        mapping[fl.name] = gt_name
        used.add(gt_name)
        remaining_gt = [f for f in remaining_gt if str(f.get("name")) != gt_name]

    for fl in geom.floors:
        if fl.name not in mapping:
            evidence.append(
                {
                    "type": "unmatched_floor",
                    "floor": fl.name,
                    "z_floor": fl.z_floor,
                    "reason": "could not map by exact name, ordinal, z_floor, or order",
                }
            )
    return mapping, evidence


def _expand_boundary_span(
    lo: float,
    hi: float,
    bounds: tuple[float, float],
    *,
    wall_thickness_m: float | None,
) -> tuple[float, float]:
    if wall_thickness_m is None or wall_thickness_m <= 0:
        return lo, hi
    half = float(wall_thickness_m) / 2.0
    blo, bhi = bounds
    if abs(lo - blo) <= _BOUNDARY_EPS_M:
        lo = lo - half
    if abs(hi - bhi) <= _BOUNDARY_EPS_M:
        hi = hi + half
    return lo, hi


def _extract_correction_wall_segments(
    floor,
    W: float,
    D: float,
    *,
    boundary_bounds: tuple[tuple[float, float], tuple[float, float]] | None = None,
    wall_thickness_m: float | None = None,
) -> tuple[list[WallSegment], list[WallSegment]]:
    vx: list[WallSegment] = []
    hy: list[WallSegment] = []
    if boundary_bounds is None:
        boundary_bounds = _floor_cells_bbox(floor)
    for cell in floor.cells:
        try:
            coords = list(cell_polygon(cell).exterior.coords)
        except ValueError:
            continue
        for a, b in zip(coords, coords[1:]):
            x0, y0 = float(a[0]), float(a[1])
            x1, y1 = float(b[0]), float(b[1])
            if abs(x0 - x1) <= 1e-6:
                x = round(x0, 2)
                if _BOUNDARY_EPS_M < x0 < W - _BOUNDARY_EPS_M:
                    lo, hi = sorted((y0, y1))
                    if boundary_bounds is not None:
                        lo, hi = _expand_boundary_span(
                            lo,
                            hi,
                            boundary_bounds[1],
                            wall_thickness_m=wall_thickness_m,
                        )
                    vx.append(WallSegment("v", x, round(lo, 2), round(hi, 2)))
            elif abs(y0 - y1) <= 1e-6:
                y = round(y0, 2)
                if _BOUNDARY_EPS_M < y0 < D - _BOUNDARY_EPS_M:
                    lo, hi = sorted((x0, x1))
                    if boundary_bounds is not None:
                        lo, hi = _expand_boundary_span(
                            lo,
                            hi,
                            boundary_bounds[0],
                            wall_thickness_m=wall_thickness_m,
                        )
                    hy.append(WallSegment("h", y, round(lo, 2), round(hi, 2)))
    return _dedupe_segments(vx), _dedupe_segments(hy)


def _extract_correction_walls(floor, W: float, D: float) -> tuple[list[float], list[float]]:
    vx, hy = _extract_correction_wall_segments(floor, W, D)
    return [s.coord for s in vx], [s.coord for s in hy]


def _valid_pair(vals) -> tuple[float, float] | None:
    if vals is None or len(vals) != 2:
        return None
    try:
        a, b = float(vals[0]), float(vals[1])
    except (TypeError, ValueError):
        return None
    return min(a, b), max(a, b)


def _floor_cells_bbox(floor) -> tuple[tuple[float, float], tuple[float, float]] | None:
    xs: list[float] = []
    ys: list[float] = []
    for cell in floor.cells:
        try:
            minx, miny, maxx, maxy = cell_bbox(cell)
        except ValueError:
            continue
        xs.extend([minx, maxx])
        ys.extend([miny, maxy])
    if not xs or not ys:
        return None
    return (min(xs), max(xs)), (min(ys), max(ys))


def _fallback_footprint_from_raw_cells(data: dict) -> tuple[tuple[float, float], tuple[float, float]] | None:
    xs: list[float] = []
    ys: list[float] = []
    for floor in data.get("floors") or []:
        for cell in floor.get("cells") or []:
            x = cell.get("x") or []
            y = cell.get("y") or []
            if len(x) == 2:
                xs.extend([float(x[0]), float(x[1])])
            if len(y) == 2:
                ys.extend([float(y[0]), float(y[1])])
    if not xs or not ys:
        return None
    return (min(xs), max(xs)), (min(ys), max(ys))


def _normalise_raw_geom_for_scoring(data: dict) -> dict:
    fx = _valid_pair(data.get("footprint_x"))
    fy = _valid_pair(data.get("footprint_y"))
    if fx is not None and fy is not None:
        return data
    bbox = _fallback_footprint_from_raw_cells(data)
    if bbox is None:
        return data
    out = dict(data)
    if fx is None:
        out["footprint_x"] = [bbox[0][0], bbox[0][1]]
    if fy is None:
        out["footprint_y"] = [bbox[1][0], bbox[1][1]]
    return out


def _boundary_centerline_to_outer(
    boundary: dict[str, float], wall_thickness_m: float | None
) -> dict[str, float]:
    if wall_thickness_m is None or wall_thickness_m <= 0:
        return boundary
    half = float(wall_thickness_m) / 2.0
    return {
        "S": boundary["S"] - half,
        "N": boundary["N"] + half,
        "W": boundary["W"] - half,
        "E": boundary["E"] + half,
    }


def _extract_correction_boundary(
    geom: CorrectedGeometry,
    floor,
    *,
    wall_thickness_m: float | None = None,
) -> dict[str, float] | None:
    from src.agent.correction.footprint import footprint_bbox
    try:
        fx, fy = footprint_bbox(geom, floor)
    except ValueError:
        bbox = _floor_cells_bbox(floor)
        if bbox is None:
            return None
        fx, fy = bbox
    return _boundary_centerline_to_outer(
        {"S": fy[0], "N": fy[1], "W": fx[0], "E": fx[1]},
        wall_thickness_m,
    )


def _gt_floor_for_label(label: str, gt: dict, floor_map: dict[str, str]) -> str | None:
    if label in floor_map:
        return floor_map[label]
    gt_floors = list(gt.get("floors", []))
    gt_names = {str(f.get("name")) for f in gt_floors}
    if label in gt_names:
        return label
    n = _floor_number(label)
    if n is not None and 0 <= n - 1 < len(gt_floors):
        return str(gt_floors[n - 1].get("name"))
    return None


def _extract_correction_windows(
    geom: CorrectedGeometry,
    gt_floor_name: str,
    gt: dict,
    floor_map: dict[str, str],
) -> dict[str, list[tuple[float, float]]]:
    out: dict[str, list[tuple[float, float]]] = {"N": [], "S": [], "E": [], "W": []}
    facade_code = {"North": "N", "South": "S", "East": "E", "West": "W"}
    for win in geom.windows:
        if _gt_floor_for_label(win.floor, gt, floor_map) != gt_floor_name:
            continue
        code = facade_code.get(win.facade)
        if not code or len(win.span) != 2:
            continue
        out[code].append((round(min(win.span), 2), round(max(win.span), 2)))
    return out


def score_correction_geometry(
    geom_data: CorrectedGeometry | dict,
    gt: dict,
    *,
    wall_tol: float = DEFAULT_WALL_TOL_M,
    win_tol: float = DEFAULT_WIN_CENTRE_TOL_M,
    position_tol: float | None = None,
    extent_tol: float = DEFAULT_EXTENT_TOL_M,
    complete_eps: float = DEFAULT_COMPLETE_EPS_M,
    elevation_along_tol_m: float = DEFAULT_ELEVATION_ALONG_TOL_M,
    sill_tol_m: float = DEFAULT_SILL_TOL_M,
    head_tol_m: float = DEFAULT_HEAD_TOL_M,
    width_tol_m: float = DEFAULT_WIDTH_TOL_M,
    overlap_accept: float = DEFAULT_OVERLAP_ACCEPT,
    overlap_complete: float = DEFAULT_OVERLAP_COMPLETE,
    floor_line_tol_m: float = DEFAULT_FLOOR_LINE_TOL_M,
) -> CorrectionScoreResult:
    from src.agent.correction.parse import ensure_corrected_geometry
    geom = ensure_corrected_geometry(
        geom_data if isinstance(geom_data, CorrectedGeometry)
        else _normalise_raw_geom_for_scoring(geom_data)
    )
    fp = gt["footprint"]
    W, D = float(fp["W_m"]), float(fp["D_m"])
    wall_thickness_m = gt.get("wall_thickness_m")
    try:
        wall_thickness_m = float(wall_thickness_m) if wall_thickness_m is not None else None
    except (TypeError, ValueError):
        wall_thickness_m = None
    gt_floor_by_name = {str(f["name"]): f for f in gt.get("floors", [])}
    floor_map, evidence = _map_floors(geom, gt)
    scores: dict[str, FloorScore] = {}

    for fl in geom.floors:
        gt_name = floor_map.get(fl.name)
        if gt_name is None:
            continue
        gt_floor = gt_floor_by_name.get(gt_name)
        if gt_floor is None:
            evidence.append(
                {"type": "unmatched_floor", "floor": fl.name, "mapped_gt_floor": gt_name}
            )
            continue
        position_tol = wall_tol if position_tol is None else position_tol
        gvx, ghy = derive_gt_wall_segments(gt_floor["zones"], W, D)
        gwin = derive_gt_windows(gt, gt_name)
        centerline_bounds = _floor_cells_bbox(fl)
        rvx, rhy = _extract_correction_wall_segments(
            fl,
            W,
            D,
            boundary_bounds=centerline_bounds,
            wall_thickness_m=wall_thickness_m,
        )
        rwin = _extract_correction_windows(geom, gt_name, gt, floor_map)
        rbnd = _extract_correction_boundary(
            geom,
            fl,
            wall_thickness_m=wall_thickness_m,
        )

        sc = FloorScore(floor=gt_name)
        sc.vwalls, sc.extra_vwalls = _match_wall_segments(
            rvx,
            gvx,
            position_tol=position_tol,
            extent_tol=extent_tol,
            complete_eps=complete_eps,
        )
        sc.hwalls, sc.extra_hwalls = _match_wall_segments(
            rhy,
            ghy,
            position_tol=position_tol,
            extent_tol=extent_tol,
            complete_eps=complete_eps,
        )
        sc.boundary = match_boundary(rbnd, W, D, wall_tol)
        for facade in ("N", "S", "E", "W"):
            ms, extra = _match_window_segments(
                facade,
                rwin[facade],
                gwin[facade],
                extent_tol=extent_tol,
                complete_eps=complete_eps,
            )
            sc.windows[facade] = ms
            sc.extra_windows[facade] = extra
        scores[fl.name] = sc

    window_floor_names = {w.floor for w in geom.windows}
    known_floor_names = {f.name for f in geom.floors}
    for floor_name in sorted(window_floor_names - known_floor_names):
        if _gt_floor_for_label(floor_name, gt, floor_map) is not None:
            continue
        evidence.append(
            {
                "type": "unmatched_window_floor",
                "floor": floor_name,
                "reason": "window floor not present in CorrectedGeometry.floors",
            }
        )
    elevation_evidence: list[dict] = []
    elevation = score_correction_elevation_windows(
        geom,
        gt,
        floor_map=floor_map,
        evidence=elevation_evidence,
        elevation_along_tol_m=elevation_along_tol_m,
        sill_tol_m=sill_tol_m,
        head_tol_m=head_tol_m,
        width_tol_m=width_tol_m,
        overlap_accept=overlap_accept,
        overlap_complete=overlap_complete,
        floor_line_tol_m=floor_line_tol_m,
    )
    return CorrectionScoreResult(
        scores=scores,
        evidence=evidence,
        floor_map=floor_map,
        elevation=elevation,
    )
