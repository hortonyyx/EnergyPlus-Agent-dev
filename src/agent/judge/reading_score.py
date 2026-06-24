"""Coordinate-level reading↔gt scorer — the AUTHORITATIVE reading-quality metric.

User directive (2026-06-24): a reading is judged good/bad ONLY by matching its
**coordinates** against the ground-truth coordinates (walls + windows), element by
element, reporting hit / miss / extra + actual offset. Looking at the rendered
image is auxiliary only and never the basis for a verdict; visual adjudication
belongs to the user. This module institutionalizes that standard so we stop
eyeballing renders to call a reading "clean".

Judge-side only: it reads gt (via `gt.load_gt`), so — like the rest of
`src/agent/judge/` — it must never be imported by gate① checks or stage
executors (enforced by `tests/test_gt_discipline.py`).

What it does, per plan floor image:
  * derives the gt INTERIOR wall lines (vertical x-lines + horizontal y-lines)
    from the gt zone rectangles (an edge is interior iff it is not on the
    footprint boundary), and the gt window spans per facade;
  * extracts the same from a reading JSON's strokes;
  * greedily matches within a tolerance and returns hits/misses/extras + the
    signed coordinate offsets so the precision is visible, not just the count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json

from .gt import load_gt

# A wall counts as "found" if a read line sits within this many metres of the
# gt line (readers legitimately trace the inner face, ~0.12 m off centreline).
DEFAULT_WALL_TOL_M = 0.30
# A window counts as "found" if its centre sits within this of the gt centre.
DEFAULT_WIN_CENTRE_TOL_M = 0.40
# How close to 0 / W / D a coordinate must be to count as "on the boundary".
_BOUNDARY_EPS_M = 0.30
_COLINEAR_EPS_M = 0.05


@dataclass
class LineMatch:
    truth: float
    read: float | None          # matched read value, or None if missed
    delta: float | None         # read - truth (signed), or None


@dataclass
class WinMatch:
    truth: tuple[float, float]
    read: tuple[float, float] | None
    centre_delta: float | None


@dataclass
class FloorScore:
    floor: str
    vwalls: list[LineMatch] = field(default_factory=list)
    hwalls: list[LineMatch] = field(default_factory=list)
    extra_vwalls: list[float] = field(default_factory=list)
    extra_hwalls: list[float] = field(default_factory=list)
    windows: dict[str, list[WinMatch]] = field(default_factory=dict)
    extra_windows: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    def wall_hits(self) -> tuple[int, int]:
        ms = self.vwalls + self.hwalls
        return sum(1 for m in ms if m.read is not None), len(ms)

    def window_hits(self) -> tuple[int, int]:
        hit = tot = 0
        for ms in self.windows.values():
            hit += sum(1 for m in ms if m.read is not None)
            tot += len(ms)
        return hit, tot

    def max_wall_offset(self) -> float:
        ds = [abs(m.delta) for m in self.vwalls + self.hwalls if m.delta is not None]
        return round(max(ds), 3) if ds else 0.0


# ---------------------------------------------------------------- gt derivation

def derive_gt_walls(zones: list[dict], W: float, D: float) -> tuple[list[float], list[float]]:
    """Interior vertical x-lines and horizontal y-lines from zone rects.

    Each zone rect is [x0, y0, x1, y1]. A rect edge that does not lie on the
    footprint boundary (x∈{0,W}, y∈{0,D}) is an interior partition line.
    """
    vx: set[float] = set()
    hy: set[float] = set()
    for z in zones:
        x0, y0, x1, y1 = z["rect_m"]
        for x in (x0, x1):
            if _BOUNDARY_EPS_M < x < W - _BOUNDARY_EPS_M:
                vx.add(round(x, 2))
        for y in (y0, y1):
            if _BOUNDARY_EPS_M < y < D - _BOUNDARY_EPS_M:
                hy.add(round(y, 2))
    return sorted(vx), sorted(hy)


def derive_gt_windows(gt: dict, floor_name: str) -> dict[str, list[tuple[float, float]]]:
    """Per-facade window spans for one floor: (start, start+width) along the facade.

    For N/S the span is in world x; for E/W it is the along-facade coordinate
    (world y) exactly as gt stores `x_m`.
    """
    out: dict[str, list[tuple[float, float]]] = {"N": [], "S": [], "E": [], "W": []}
    fac = {"North": "N", "South": "S", "East": "E", "West": "W"}
    for entry in gt.get("windows", []):
        if entry.get("floor") != floor_name:
            continue
        f = fac.get(entry.get("facade"))
        if not f:
            continue
        for op in entry.get("openings", []):
            x = op.get("x_m")
            w = op.get("width_m")
            if x is None or w is None:
                continue
            out[f].append((round(x, 2), round(x + w, 2)))
    return out


# ----------------------------------------------------------- reading extraction

def _strokes(reading: dict) -> list[dict]:
    def find(o):
        if isinstance(o, dict):
            if isinstance(o.get("strokes"), list):
                return o["strokes"]
            for v in o.values():
                r = find(v)
                if r is not None:
                    return r
        if isinstance(o, list):
            for v in o:
                r = find(v)
                if r is not None:
                    return r
        return None
    return find(reading) or []


def _dedupe(vals: list[float], tol: float = 0.20) -> list[float]:
    out: list[float] = []
    for v in sorted(vals):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def extract_reading_walls(reading: dict, W: float, D: float) -> tuple[list[float], list[float]]:
    vx: list[float] = []
    hy: list[float] = []
    for s in _strokes(reading):
        if s.get("pen") != "wall":
            continue
        g = s.get("geometry", {})
        p1, p2 = g.get("p1"), g.get("p2")
        if not p1 or not p2:
            continue
        x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
        if abs(x1 - x2) < _COLINEAR_EPS_M and _BOUNDARY_EPS_M < x1 < W - _BOUNDARY_EPS_M:
            vx.append(round(x1, 2))
        elif abs(y1 - y2) < _COLINEAR_EPS_M and _BOUNDARY_EPS_M < y1 < D - _BOUNDARY_EPS_M:
            hy.append(round(y1, 2))
    return _dedupe(vx), _dedupe(hy)


def extract_reading_windows(reading: dict, W: float, D: float) -> dict[str, list[tuple[float, float]]]:
    out: dict[str, list[tuple[float, float]]] = {"N": [], "S": [], "E": [], "W": []}
    for s in _strokes(reading):
        if s.get("pen") != "window":
            continue
        g = s.get("geometry", {})
        p1, p2 = g.get("p1"), g.get("p2")
        if not p1 or not p2:
            continue
        x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
        horiz = abs(y1 - y2) < _COLINEAR_EPS_M
        vert = abs(x1 - x2) < _COLINEAR_EPS_M
        if horiz and y1 > D - 1.0:
            out["N"].append((round(min(x1, x2), 2), round(max(x1, x2), 2)))
        elif horiz and y1 < 1.0:
            out["S"].append((round(min(x1, x2), 2), round(max(x1, x2), 2)))
        elif vert and x1 > W - 1.0:
            out["E"].append((round(min(y1, y2), 2), round(max(y1, y2), 2)))
        elif vert and x1 < 1.0:
            out["W"].append((round(min(y1, y2), 2), round(max(y1, y2), 2)))
    return out


# ---------------------------------------------------------------------- matching

def _match_lines(read: list[float], truth: list[float], tol: float) -> tuple[list[LineMatch], list[float]]:
    pool = list(read)
    matches: list[LineMatch] = []
    for t in truth:
        cands = [r for r in pool if abs(r - t) <= tol]
        if cands:
            b = min(cands, key=lambda r: abs(r - t))
            matches.append(LineMatch(t, b, round(b - t, 2)))
            pool.remove(b)
        else:
            matches.append(LineMatch(t, None, None))
    return matches, pool


def _match_windows(read: list[tuple[float, float]], truth: list[tuple[float, float]], tolc: float):
    pool = list(read)
    matches: list[WinMatch] = []
    for ts, te in truth:
        tc = (ts + te) / 2
        cands = [(rs, re) for rs, re in pool if abs((rs + re) / 2 - tc) <= tolc]
        if cands:
            b = min(cands, key=lambda x: abs((x[0] + x[1]) / 2 - tc))
            matches.append(WinMatch((ts, te), b, round((b[0] + b[1]) / 2 - tc, 2)))
            pool.remove(b)
        else:
            matches.append(WinMatch((ts, te), None, None))
    return matches, pool


def score_floor(
    reading: dict,
    gt: dict,
    floor_name: str,
    *,
    wall_tol: float = DEFAULT_WALL_TOL_M,
    win_tol: float = DEFAULT_WIN_CENTRE_TOL_M,
) -> FloorScore:
    fp = gt["footprint"]
    W, D = float(fp["W_m"]), float(fp["D_m"])
    floor = next(f for f in gt["floors"] if f["name"] == floor_name)

    gvx, ghy = derive_gt_walls(floor["zones"], W, D)
    gwin = derive_gt_windows(gt, floor_name)
    rvx, rhy = extract_reading_walls(reading, W, D)
    rwin = extract_reading_windows(reading, W, D)

    sc = FloorScore(floor=floor_name)
    sc.vwalls, sc.extra_vwalls = _match_lines(rvx, gvx, wall_tol)
    sc.hwalls, sc.extra_hwalls = _match_lines(rhy, ghy, wall_tol)
    for f in ("N", "S", "E", "W"):
        ms, extra = _match_windows(rwin[f], gwin[f], win_tol)
        sc.windows[f] = ms
        sc.extra_windows[f] = extra
    return sc


def floor_name_for_image(stem: str, gt: dict) -> str | None:
    """Map a reading image stem (e.g. '1f_view') to a gt floor name."""
    digit = "".join(ch for ch in stem if ch.isdigit())[:1]
    if digit:
        idx = int(digit) - 1
        floors = gt.get("floors", [])
        if 0 <= idx < len(floors):
            return floors[idx]["name"]
    return None


def score_reading_dir(
    reading_dir: Path | str,
    case: str,
    *,
    gt_dir: Path | str | None = None,
    wall_tol: float = DEFAULT_WALL_TOL_M,
    win_tol: float = DEFAULT_WIN_CENTRE_TOL_M,
) -> dict[str, FloorScore]:
    """Score every plan `*_view.json` in a dir against the case gt."""
    gt = load_gt(case, gt_dir=gt_dir) if gt_dir else load_gt(case)
    if gt is None:
        raise FileNotFoundError(f"no gt for case {case!r}")
    out: dict[str, FloorScore] = {}
    for p in sorted(Path(reading_dir).glob("*_view.json")):
        reading = json.loads(p.read_text(encoding="utf-8"))
        if reading.get("image_kind") not in (None, "plan"):
            continue
        fname = floor_name_for_image(p.stem, gt)
        if fname is None:
            continue
        out[p.stem] = score_floor(reading, gt, fname, wall_tol=wall_tol, win_tol=win_tol)
    return out
