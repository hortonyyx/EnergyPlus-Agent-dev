"""Deterministic correction core: canonical axis snapping + sliver guard.

Runs on `CorrectedGeometry` (correction stage output) before the modeling/MEP stages modeling. Builds a
GLOBAL canonical axis set across all floors and snaps every cell / window /
footprint boundary onto it, so:

  1. the same wall on different floors becomes byte-identical (cross-floor jitter
     gone), and
  2. no two canonical axes are closer than `min_edge_length_m`, so the interzone
     floor/ceiling split cannot produce a degenerate sub-tolerance sliver — the
     EnergyPlus input-processing segfault class is made structurally impossible.

This kills the CRASH. It does NOT guarantee CORRECTNESS: if correction stage mis-placed a
partition, snapping removes the crack but keeps the wrong layout. Geometric
correctness is the judgment layer's job (correction stage, A3 arbitration). "No crash" and
"is correct" are deliberately separate concerns.

Pipeline per axis (structural x/y): cluster (identity) -> snap representative to
grid (regularize) -> sliver-merge (min-edge safety). Then a CONNECTIVITY pass pulls
any cell edge falling within `gap_close_threshold_m` inside a footprint boundary
out onto it, so an internal wall that stops short of the exterior seals the
enclosure (an unclosed enclosure forms no EnergyPlus zone). Connectivity is a
coarser, distinct operation from axis identity (A0 §4) — bigger threshold,
directional, footprint-only for now. Windows are tiered finer and are NOT placed
on the structural grid (no cross-floor identity / sliver role); they snap to
`window_snap_grid_m` and clamp into their parent cell/floor.

All tolerances come from `src/configs/correction.yaml` (basis: A0_contract.md §4),
loaded via `src.agent.correction.config` — not hardcoded here, so there is one
place to tune granularity and no A0-doc vs Python-constant drift.
"""

from __future__ import annotations

from src.agent.correction.config import CoreTolerances, load_core_tolerances
from src.agent.correction.schema import CorrectedGeometry


def _snap_to_grid(v: float, grid: float) -> float:
    """Round `v` to the nearest multiple of `grid` (grid > 0)."""
    return round(round(v / grid) * grid, 6)


def _build_axis_map(values: list[float], tol: CoreTolerances) -> dict[float, float]:
    """Map each input coordinate to a canonical axis value.

    1. cluster coordinates within `axis_jitter_tol_m` (same intended axis);
    2. snap each cluster representative (mean) onto `structural_snap_grid_m`;
    3. merge snapped representatives still closer than `min_edge_length_m`
       (sliver guard — the resulting break set has no gap that would split into
       a sub-tolerance strip).
    """
    grid = tol.structural_snap_grid_m
    pts = sorted({round(float(v), 6) for v in values})
    if not pts:
        return {}

    # 1. identity clustering
    clusters: list[list[float]] = [[pts[0]]]
    for v in pts[1:]:
        if v - clusters[-1][-1] <= tol.axis_jitter_tol_m:
            clusters[-1].append(v)
        else:
            clusters.append([v])

    # 2. snap each representative onto the structural grid
    reps = [_snap_to_grid(sum(c) / len(c), grid) for c in clusters]

    # 3. sliver guard against the running canonical value
    groups: list[list[int]] = [[0]]
    canon: list[float] = [reps[0]]
    for i in range(1, len(reps)):
        if reps[i] - canon[-1] < tol.min_edge_length_m:
            groups[-1].append(i)
            merged = sum(reps[j] for j in groups[-1]) / len(groups[-1])
            canon[-1] = _snap_to_grid(merged, grid)
        else:
            groups.append([i])
            canon.append(reps[i])

    mapping: dict[float, float] = {}
    for gi, grp in enumerate(groups):
        cval = round(canon[gi], 6)
        for ci in grp:
            for v in clusters[ci]:
                mapping[v] = cval
    return mapping


def _snap(v: float, mapping: dict[float, float]) -> float:
    return mapping.get(round(float(v), 6), float(v))


def _clamp(v: float, lo: float, hi: float) -> float:
    return min(max(v, lo), hi)


def _close_to_boundary(v: float, lo: float, hi: float, thr: float) -> float:
    """Connectivity: pull a cell edge that falls just inside a footprint boundary
    out onto it (so the enclosure seals), within `thr`. Directional — only edges
    short of `lo`/`hi` by ≤ thr move; interior partitions are untouched."""
    if 0 < v - lo <= thr:
        return lo
    if 0 < hi - v <= thr:
        return hi
    return v


def apply_deterministic_core(
    geom: CorrectedGeometry, tol: CoreTolerances | None = None
) -> CorrectedGeometry:
    """Snap all geometry onto a global canonical axis set; append audit entries.

    Mutates and returns `geom` (corrections / unsupported appended). `tol`
    defaults to the active `correction.yaml` (overridable for testing).
    """
    if tol is None:
        tol = load_core_tolerances()

    # ---- structural axes: room / wall / footprint x,y only (NOT windows) ----
    xs: list[float] = [*geom.footprint_x]
    ys: list[float] = [*geom.footprint_y]
    for fl in geom.floors:
        for c in fl.cells:
            xs += [c.x[0], c.x[1]]
            ys += [c.y[0], c.y[1]]

    xmap = _build_axis_map(xs, tol)
    ymap = _build_axis_map(ys, tol)

    corrections = list(geom.corrections)
    unsupported = list(geom.unsupported)

    def log(target: str, axis: str, before: float, after: float, rule: str) -> None:
        if abs(after - before) > tol.output_precision_m:
            corrections.append(
                {
                    "rule_id": rule,
                    "stage": "core",
                    "target": target,
                    "axis": axis,
                    "original_value": round(before, 4),
                    "resolved_value": round(after, 4),
                    "delta": round(after - before, 4),
                    "tolerance_name": "AXIS_JITTER_TOL+SNAP_GRID+MIN_EDGE_LENGTH",
                }
            )

    fx = [_snap(geom.footprint_x[0], xmap), _snap(geom.footprint_x[1], xmap)]
    fy = [_snap(geom.footprint_y[0], ymap), _snap(geom.footprint_y[1], ymap)]
    geom.footprint_x, geom.footprint_y = fx, fy
    gthr = tol.gap_close_threshold_m

    def axis_then_reach(cid, label, orig, amap, lo, hi):
        """Axis-identity snap, then connectivity-close to a footprint boundary."""
        snapped = _snap(orig, amap)
        reached = _close_to_boundary(snapped, lo, hi, gthr)
        log(f"{cid}.{label}", label[0], orig, snapped, "deterministic_core.snap")
        log(f"{cid}.{label}", label[0], snapped, reached, "deterministic_core.gap_close")
        return reached

    for fl in geom.floors:
        for c in fl.cells:
            x0 = axis_then_reach(c.id, "x[0]", c.x[0], xmap, fx[0], fx[1])
            x1 = axis_then_reach(c.id, "x[1]", c.x[1], xmap, fx[0], fx[1])
            y0 = axis_then_reach(c.id, "y[0]", c.y[0], ymap, fy[0], fy[1])
            y1 = axis_then_reach(c.id, "y[1]", c.y[1], ymap, fy[0], fy[1])
            if (x1 - x0) < tol.min_edge_length_m or (y1 - y0) < tol.min_edge_length_m:
                unsupported.append(
                    {
                        "target": c.id,
                        "reason": "cell collapsed below min_edge_length after snap",
                        "regime_assumption_violated": "non-degenerate room cell",
                    }
                )
            c.x, c.y = [x0, x1], [y0, y1]

    # ---- windows: finer grid + clamp into parent cell/floor (no structural grid) ----
    wgrid = tol.window_snap_grid_m
    cell_by_id = {c.id: (fl, c) for fl in geom.floors for c in fl.cells}
    for w in geom.windows:
        s0, s1 = _snap_to_grid(w.span[0], wgrid), _snap_to_grid(w.span[1], wgrid)
        z0, z1 = _snap_to_grid(w.z[0], wgrid), _snap_to_grid(w.z[1], wgrid)
        if tol.window_clamp_to_parent and w.room in cell_by_id:
            fl, c = cell_by_id[w.room]
            lo, hi = (c.x[0], c.x[1]) if w.facade.lower().startswith(("n", "s")) else (c.y[0], c.y[1])
            s0, s1 = _clamp(s0, lo, hi), _clamp(s1, lo, hi)
            zlo, zhi = fl.z_floor, fl.z_floor + fl.ceiling_height
            z0, z1 = _clamp(z0, zlo, zhi), _clamp(z1, zlo, zhi)
        log(f"{w.id}.span[0]", "span", w.span[0], s0, "deterministic_core.window")
        log(f"{w.id}.span[1]", "span", w.span[1], s1, "deterministic_core.window")
        log(f"{w.id}.z[0]", "z", w.z[0], z0, "deterministic_core.window")
        log(f"{w.id}.z[1]", "z", w.z[1], z1, "deterministic_core.window")
        w.span, w.z = [s0, s1], [z0, z1]

    geom.corrections = corrections
    geom.unsupported = unsupported
    return geom
