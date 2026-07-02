"""Correction-stage gt scorer.

Judge-side adapter for accepted ``CorrectedGeometry`` attempt outputs.  It
extracts the same wall/window primitives used by ``reading_score`` and reuses
the shared gt derivation + matchers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from src.agent.correction.schema import CorrectedGeometry

from .reading_score import (
    DEFAULT_WALL_TOL_M,
    DEFAULT_WIN_CENTRE_TOL_M,
    FloorScore,
    _dedupe,
    _match_lines,
    _match_windows,
    derive_gt_walls,
    derive_gt_windows,
)

_BOUNDARY_EPS_M = 0.30


@dataclass
class CorrectionScoreResult:
    scores: dict[str, FloorScore]
    evidence: list[dict] = field(default_factory=list)
    floor_map: dict[str, str] = field(default_factory=dict)


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


def _extract_correction_walls(floor, W: float, D: float) -> tuple[list[float], list[float]]:
    vx: list[float] = []
    hy: list[float] = []
    for cell in floor.cells:
        for x in cell.x:
            if _BOUNDARY_EPS_M < float(x) < W - _BOUNDARY_EPS_M:
                vx.append(round(float(x), 2))
        for y in cell.y:
            if _BOUNDARY_EPS_M < float(y) < D - _BOUNDARY_EPS_M:
                hy.append(round(float(y), 2))
    return _dedupe(vx), _dedupe(hy)


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
) -> CorrectionScoreResult:
    geom = (
        geom_data
        if isinstance(geom_data, CorrectedGeometry)
        else CorrectedGeometry.model_validate(geom_data)
    )
    fp = gt["footprint"]
    W, D = float(fp["W_m"]), float(fp["D_m"])
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
        gvx, ghy = derive_gt_walls(gt_floor["zones"], W, D)
        gwin = derive_gt_windows(gt, gt_name)
        rvx, rhy = _extract_correction_walls(fl, W, D)
        rwin = _extract_correction_windows(geom, gt_name, gt, floor_map)

        sc = FloorScore(floor=gt_name)
        sc.vwalls, sc.extra_vwalls = _match_lines(rvx, gvx, wall_tol)
        sc.hwalls, sc.extra_hwalls = _match_lines(rhy, ghy, wall_tol)
        for facade in ("N", "S", "E", "W"):
            ms, extra = _match_windows(rwin[facade], gwin[facade], win_tol)
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
    return CorrectionScoreResult(scores=scores, evidence=evidence, floor_map=floor_map)
