"""Offline discriminating-power fixture for F-95 — no gt, no LLM, no run.

Why this file exists: the repo ALREADY has a concave-room lock
(`tests/test_geometry_kernel.py::test_lshape_polygon_clean`) and it is green,
because the single-reflex L it uses is exactly the concave shape angle-sort
happens to preserve. A fix for F-95 must therefore be judged against shapes
that DO break before the fix — otherwise "the lock is green" proves only that
the lock never looked.

Before F-95: rectangle/L/Z are preserved; U/comb/sm25 corridor are corrupted.
After F-95: every ordered-simple row is preserved and the bowtie is rejected.

Run from the repo root (keeps this worktree first on ``sys.path``):
    python -m AI_agent.logs.experiments.2026-08-25_kernel_probe_from_gt.tools.concave_canonicalization_matrix
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import src.validator.data_model as data_model  # noqa: E402
from src.validator.data_model import canonicalize_ring_vertices  # noqa: E402

if not Path(data_model.__file__).resolve().is_relative_to(REPO_ROOT):
    raise RuntimeError(
        "concave matrix imported src outside its worktree: "
        f"repo_root={REPO_ROOT} imported={data_model.__file__}"
    )

DOWN = np.array([0.0, 0.0, -1.0])

CASES: dict[str, list[list[float]]] = {
    # the shape the existing lock uses — preserved even today, so it can never
    # be the only case a fix is measured against
    "rect_control": [[0, 0], [10, 0], [10, 8], [0, 8]],
    "L_single_reflex": [[0, 0], [10, 0], [10, 6], [6, 6], [6, 10], [0, 10]],
    "U_two_reflex": [[0, 0], [10, 0], [10, 10], [7, 10], [7, 4], [3, 4], [3, 10], [0, 10]],
    "Z_two_reflex": [[0, 0], [6, 0], [6, 4], [10, 4], [10, 10], [4, 10], [4, 6], [0, 6]],
    "comb_three_reflex": [[0, 0], [12, 0], [12, 8], [10, 8], [10, 3], [7, 3],
                          [7, 8], [5, 8], [5, 3], [2, 3], [2, 8], [0, 8]],
}

BOWTIE = [[0, 0], [2, 2], [0, 2], [2, 0]]


def _vertex_set(points: np.ndarray) -> set[tuple[float, float, float]]:
    return {tuple(float(value) for value in point) for point in points}


def _edge_set(
    points: np.ndarray,
) -> set[frozenset[tuple[float, float, float]]]:
    vertices = [tuple(float(value) for value in point) for point in points]
    return {
        frozenset((vertices[index], vertices[(index + 1) % len(vertices)]))
        for index in range(len(vertices))
    }


def _angles_monotonic(ring: list[list[float]]) -> bool:
    """Whether ordered vertices move one way around their arithmetic centroid."""
    points = np.asarray(ring, dtype=float)
    centroid = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - centroid[1], points[:, 0] - centroid[0])
    steps = (np.roll(angles, -1) - angles + np.pi) % (2 * np.pi) - np.pi
    return bool(np.all(steps >= -1e-12) or np.all(steps <= 1e-12))


def _load_sm25_corridor() -> list[list[float]] | None:
    """The real 14-vertex corridor, if the probe output is still on disk."""
    import json
    p = (Path(__file__).resolve().parent.parent
         / "out" / "kernel_gap020" / "correction_snapped.json")
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    for floor in doc["floors"]:
        for cell in floor["cells"]:
            if cell["id"] == "F1-z0":
                return cell["polygon"]
    return None


def main() -> int:
    cases = dict(CASES)
    u_ring = CASES["U_two_reflex"]
    cases["U_reverse_winding"] = list(reversed(u_ring))
    cases["U_different_start"] = u_ring[3:] + u_ring[:3]
    corridor = _load_sm25_corridor()
    if corridor is not None:
        cases["sm25_corridor_14v"] = corridor
    else:
        print("(sm25 corridor fixture not on disk — synthetic cases only)")

    failures = []
    print(f"src={Path(data_model.__file__).resolve()}")
    for name, ring in cases.items():
        pts = np.array([[float(x), float(y), 0.0] for x, y in ring])
        got = canonicalize_ring_vertices(pts, DOWN)
        before = Polygon(ring).area
        after = Polygon([(p[0], p[1]) for p in got]).area
        same_vertices = _vertex_set(pts) == _vertex_set(got)
        same_edges = _edge_set(pts) == _edge_set(got)
        ok = abs(before - after) < 1e-6 and same_vertices and same_edges
        if not ok:
            failures.append(name)
        print(
            f"{name:24s} nv={len(ring):3d} in={before:9.3f} out={after:9.3f} "
            f"vertices={'same' if same_vertices else 'CHANGED':7s} "
            f"edges={'same' if same_edges else 'CHANGED':7s} "
            f"angle_mono={str(_angles_monotonic(ring)):5s} "
            f"{'OK' if ok else 'CORRUPTED'}"
        )

    # Z is the explicit "concave but angle-monotonic" control. It proves
    # reflex vertices alone do not discriminate F-95.
    z_ring = CASES["Z_two_reflex"]
    if not _angles_monotonic(z_ring):
        failures.append("Z_expected_angle_monotonic")

    bowtie = np.array([[float(x), float(y), 0.0] for x, y in BOWTIE])
    try:
        canonicalize_ring_vertices(bowtie, DOWN)
    except ValueError as exc:
        rejected = "canonicalize_ring_vertices.non_simple_ring" in str(exc)
        print(
            f"{'bowtie_non_simple':24s} nv={len(bowtie):3d} "
            f"expected=REJECT got={'REJECT' if rejected else 'WRONG_ERROR'} "
            f"{'OK' if rejected else 'FAILED'} error={exc}"
        )
        if not rejected:
            failures.append("bowtie_non_simple_wrong_error")
    else:
        print(
            f"{'bowtie_non_simple':24s} nv={len(bowtie):3d} "
            "expected=REJECT got=ACCEPT FAILED"
        )
        failures.append("bowtie_non_simple_accepted")

    print()
    if failures:
        print(f"{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("all ordered simple rings preserved; non-simple ring rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
