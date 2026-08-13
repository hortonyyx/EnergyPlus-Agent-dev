"""A5 vertex comparison for 摊 I acceptance runs.

Compares `2_modelling/building_geometry.json` between a candidate run and the
reference `run_2026-08-11_continuous_e2e`, vertex-by-vertex, same order — NOT
via `geometry_checkpoint_digest` (that digest hashes a kernel report with
room names baked in; a room-name-only diff changes the digest while leaving
every vertex identical, per CLAUDE.md memory 2026-08-13).

Usage: python vertex_compare.py <candidate_run_dir>
"""

import json
import sys
from pathlib import Path

REF = Path(
    "case_tests/e2e_tests/sm21_anchor/run_2026-08-11_continuous_e2e/"
    "2_modelling/building_geometry.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def compare(ref: dict, cand: dict) -> None:
    ref_surfaces = ref["surfaces"]
    cand_surfaces = cand["surfaces"]
    ref_windows = ref["windows"]
    cand_windows = cand["windows"]

    print(f"surfaces: ref={len(ref_surfaces)} cand={len(cand_surfaces)}")
    print(f"windows:  ref={len(ref_windows)} cand={len(cand_windows)}")

    assert len(ref_surfaces) == len(cand_surfaces), "surface count differs"
    assert len(ref_windows) == len(cand_windows), "window count differs"

    surf_vert_mismatches = []
    for i, (rs, cs) in enumerate(zip(ref_surfaces, cand_surfaces)):
        rv, cv = rs["verts"], cs["verts"]
        if rv != cv:
            surf_vert_mismatches.append((i, rs.get("name"), cs.get("name")))

    win_vert_mismatches = []
    for i, (rw, cw) in enumerate(zip(ref_windows, cand_windows)):
        rv, cv = rw["verts"], cw["verts"]
        if rv != cv:
            win_vert_mismatches.append((i, rw.get("name"), cw.get("name")))

    ref_surf_vertex_count = sum(len(s["verts"]) for s in ref_surfaces)
    cand_surf_vertex_count = sum(len(s["verts"]) for s in cand_surfaces)
    ref_win_vertex_count = sum(len(w["verts"]) for w in ref_windows)
    cand_win_vertex_count = sum(len(w["verts"]) for w in cand_windows)

    print(
        f"surface vertex-triple count: ref={ref_surf_vertex_count} "
        f"cand={cand_surf_vertex_count}"
    )
    print(
        f"window vertex-triple count:  ref={ref_win_vertex_count} "
        f"cand={cand_win_vertex_count}"
    )
    print(f"surface vertex mismatches: {len(surf_vert_mismatches)}")
    print(f"window vertex mismatches:  {len(win_vert_mismatches)}")

    if surf_vert_mismatches:
        print("FIRST surface mismatches:", surf_vert_mismatches[:5])
    if win_vert_mismatches:
        print("FIRST window mismatches:", win_vert_mismatches[:5])

    # Also report non-vertex diffs (room names etc.) for context — not part
    # of the pass/fail geometry criterion, purely informational.
    name_diffs = [
        (i, rs.get("zone"), cs.get("zone"))
        for i, (rs, cs) in enumerate(zip(ref_surfaces, cand_surfaces))
        if rs.get("zone") != cs.get("zone")
    ]
    if name_diffs:
        print(f"INFO: {len(name_diffs)} surface zone-label diffs (non-geometry):")
        print(name_diffs[:10])

    ok = not surf_vert_mismatches and not win_vert_mismatches
    print("RESULT:", "PASS — vertices identical, same order" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    cand_path = Path(sys.argv[1]) / "2_modelling" / "building_geometry.json"
    compare(load(REF), load(cand_path))
