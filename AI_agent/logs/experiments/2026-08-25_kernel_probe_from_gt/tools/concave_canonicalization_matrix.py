"""Offline discriminating-power fixture for F-95 — no gt, no LLM, no run.

Why this file exists: the repo ALREADY has a concave-room lock
(`tests/test_geometry_kernel.py::test_lshape_polygon_clean`) and it is green,
because the single-reflex L it uses is exactly the concave shape angle-sort
happens to preserve.  A fix for F-95 must therefore be judged against shapes
that DO break today — otherwise "the lock is green" proves only that the lock
never looked.

Expected TODAY (defect present):  L_single_reflex OK, everything else CORRUPTED.
Expected AFTER a fix:             every row OK.
Run: python <this file>            (exit code 1 while any row is CORRUPTED)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0, "/workspaces/EnergyPlus-Agent-dev")
from src.validator.data_model import canonicalize_ring_vertices  # noqa: E402

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
    corridor = _load_sm25_corridor()
    if corridor is not None:
        cases["sm25_corridor_14v"] = corridor
    else:
        print("(sm25 corridor fixture not on disk — synthetic cases only)")

    corrupted = []
    for name, ring in cases.items():
        pts = np.array([[float(x), float(y), 0.0] for x, y in ring])
        got = canonicalize_ring_vertices(pts, DOWN)
        before = Polygon(ring).area
        after = Polygon([(p[0], p[1]) for p in got]).area
        ok = abs(before - after) < 1e-6
        if not ok:
            corrupted.append(name)
        print(f"{name:24s} nv={len(ring):3d}  in={before:9.3f}  out={after:9.3f}  "
              f"{'OK' if ok else 'CORRUPTED'}")

    print()
    if corrupted:
        print(f"{len(corrupted)} shape(s) corrupted: {', '.join(corrupted)}")
        return 1
    print("all rings preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
