"""Deterministic correction core: canonical axis snapping + sliver guard.

Runs on `CorrectedGeometry` (phase2a output) before phase2b modeling. Builds a
GLOBAL canonical axis set across all floors and snaps every cell / window /
footprint boundary onto it, so:

  1. the same wall on different floors becomes byte-identical (cross-floor jitter
     gone), and
  2. no two canonical axes are closer than MIN_EDGE_LENGTH, so the interzone
     floor/ceiling split cannot produce a degenerate sub-tolerance sliver — the
     EnergyPlus input-processing segfault class is made structurally impossible.

This kills the CRASH. It does NOT guarantee CORRECTNESS: if phase2a mis-placed a
partition, snapping removes the crack but keeps the wrong layout. Geometric
correctness is the judgment layer's job (phase2a, A3 arbitration). "No crash" and
"is correct" are deliberately separate concerns.

Constants come from the A0 tolerance registry
(skills/energyplus_mcp_twostep/phase2/PartA-correction/A0_contract.md §4).
"""

from __future__ import annotations

from src.agent.correction.schema import CorrectedGeometry

AXIS_JITTER_TOL = 0.050  # m — within this (and same intended axis), one canonical
MIN_EDGE_LENGTH = 0.100  # m — degenerate-sliver floor; no two canonicals closer
OUTPUT_PRECISION = 0.010  # m — log a correction only when a move exceeds this


def _build_axis_map(
    values: list[float],
    jitter_tol: float = AXIS_JITTER_TOL,
    min_edge: float = MIN_EDGE_LENGTH,
) -> dict[float, float]:
    """Map each input coordinate to a canonical axis value.

    Step 1: cluster coordinates within `jitter_tol` (same intended axis).
    Step 2: merge clusters whose representatives are closer than `min_edge`
            (sliver guard — guarantees the resulting break set has no gap that
            would split into a sub-tolerance strip).
    """
    pts = sorted({round(float(v), 6) for v in values})
    if not pts:
        return {}

    clusters: list[list[float]] = [[pts[0]]]
    for v in pts[1:]:
        if v - clusters[-1][-1] <= jitter_tol:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    reps = [sum(c) / len(c) for c in clusters]

    groups: list[list[int]] = [[0]]
    canon: list[float] = [reps[0]]
    for i in range(1, len(reps)):
        if reps[i] - canon[-1] < min_edge:
            groups[-1].append(i)
            canon[-1] = sum(reps[j] for j in groups[-1]) / len(groups[-1])
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


def apply_deterministic_core(geom: CorrectedGeometry) -> CorrectedGeometry:
    """Snap all geometry onto a global canonical axis set; append audit entries.

    Mutates and returns `geom` (corrections / unsupported appended).
    """
    xs: list[float] = [*geom.footprint_x]
    ys: list[float] = [*geom.footprint_y]
    for fl in geom.floors:
        for c in fl.cells:
            xs += [c.x[0], c.x[1]]
            ys += [c.y[0], c.y[1]]
    for w in geom.windows:
        if w.facade.lower().startswith(("n", "s")):
            xs += [w.span[0], w.span[1]]
        else:
            ys += [w.span[0], w.span[1]]

    xmap = _build_axis_map(xs)
    ymap = _build_axis_map(ys)

    corrections = list(geom.corrections)
    unsupported = list(geom.unsupported)

    def log(target: str, axis: str, before: float, after: float) -> None:
        if abs(after - before) > OUTPUT_PRECISION:
            corrections.append(
                {
                    "rule_id": "deterministic_core.snap",
                    "stage": "core",
                    "target": target,
                    "axis": axis,
                    "original_value": round(before, 4),
                    "resolved_value": round(after, 4),
                    "delta": round(after - before, 4),
                    "tolerance_name": "AXIS_JITTER_TOL+MIN_EDGE_LENGTH",
                }
            )

    fx = [_snap(geom.footprint_x[0], xmap), _snap(geom.footprint_x[1], xmap)]
    fy = [_snap(geom.footprint_y[0], ymap), _snap(geom.footprint_y[1], ymap)]
    geom.footprint_x, geom.footprint_y = fx, fy

    for fl in geom.floors:
        for c in fl.cells:
            x0, x1 = _snap(c.x[0], xmap), _snap(c.x[1], xmap)
            y0, y1 = _snap(c.y[0], ymap), _snap(c.y[1], ymap)
            log(f"{c.id}.x[0]", "x", c.x[0], x0)
            log(f"{c.id}.x[1]", "x", c.x[1], x1)
            log(f"{c.id}.y[0]", "y", c.y[0], y0)
            log(f"{c.id}.y[1]", "y", c.y[1], y1)
            if (x1 - x0) < MIN_EDGE_LENGTH or (y1 - y0) < MIN_EDGE_LENGTH:
                unsupported.append(
                    {
                        "target": c.id,
                        "reason": "cell collapsed below MIN_EDGE_LENGTH after snap",
                        "regime_assumption_violated": "non-degenerate room cell",
                    }
                )
            c.x, c.y = [x0, x1], [y0, y1]

    for w in geom.windows:
        if w.facade.lower().startswith(("n", "s")):
            w.span = [_snap(w.span[0], xmap), _snap(w.span[1], xmap)]
        else:
            w.span = [_snap(w.span[0], ymap), _snap(w.span[1], ymap)]

    geom.corrections = corrections
    geom.unsupported = unsupported
    return geom
