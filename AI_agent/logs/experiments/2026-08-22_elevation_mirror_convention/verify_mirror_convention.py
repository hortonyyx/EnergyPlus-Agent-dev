"""Verify the elevation local-x convention against gt, on every available case.

The question this answers: a reading records elevation openings in IMAGE-LOCAL
coordinates ("x metres from the image's left edge") because the reading contract
forbids it from declaring a world axis. To score such a product the judge needs
the missing half of the translation -- in particular whether the image's left
edge is the LOW or the HIGH end of the world axis that facade runs along.

Getting that backwards is the nastiest failure mode available here: the opening
count, every width and every spacing stay correct, and only the positions flip
end-for-end. On a symmetric facade it is invisible.

Method (no free parameters): for each facade family, take the openings gt places
on it (`world_along_interval`) and the openings the reading places on it
(image-local `x_range_m`), and test two hypotheses -- direct (local == world)
and mirrored (local == L - world, L = the building's extent on that axis). The
proposed rule is then checked against each facade's OUTWARD NORMAL, which gt
carries independently on every boundary segment.

Run:  python AI_agent/logs/experiments/2026-08-22_elevation_mirror_convention/verify_mirror_convention.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
TOL = 0.05  # metres; readings snap to dimension ticks, gt carries drafting residue

CASES = [
    # (case, gt path, reading dir, who produced the reading)
    ("sm25-L_anchor",
     "case_tests/test_baseline/gt/sm25-L_anchor/gt.json",
     "case_tests/e2e_tests/sm25-L_anchor/run_2026-08-22_orchestrator_handson_H2_fullcase/0_reading",
     "orchestrator hands-on 2026-08-22"),
    ("sm24_anchor",
     "case_tests/test_baseline/gt/sm24_anchor/gt.json",
     "case_tests/e2e_tests/sm24_anchor/run_2026-07-07_haiku_cv_probe/0_reading",
     "07-07 haiku (INDEPENDENT: not produced by this round)"),
]


def facade_geometry(gt: dict) -> tuple[dict, dict, tuple[float, float]]:
    """Per facade family: outward normal, the world axis it runs along; plus the
    building's overall bbox, whose max on an axis is the mirror constant."""
    normals, axes = defaultdict(set), defaultdict(set)
    xs, ys = [], []
    for floor in gt.get("floors", []):
        for seg in floor.get("boundary_segments", []):
            fam = seg["facade_family"]
            normals[fam].add(tuple(seg["outward_normal"]))
            horizontal = abs(seg["p1"][1] - seg["p2"][1]) < 1e-9
            axes[fam].add("x" if horizontal else "y")
            for p in (seg["p1"], seg["p2"]):
                xs.append(p[0])
                ys.append(p[1])
    return normals, axes, (max(xs), max(ys))


def predicted_sign(normal: tuple[float, float], axis: str) -> int:
    """Local +x direction = (-outward_normal) x z_hat.

    That is exactly "the facade is drawn as seen from outside the building":
    stand outside looking at the wall, and the viewer's right-hand direction is
    the direction the drawing's x increases in.
    """
    dx, dy = -normal[0], -normal[1]
    right = (dy, -dx)                      # (d, 0) x (0, 0, 1)
    return int(right[0] if axis == "x" else right[1])


def openings_by_facade(gt: dict) -> dict[str, list[tuple[float, float]]]:
    seg_family = {}
    for floor in gt.get("floors", []):
        for seg in floor.get("boundary_segments", []):
            seg_family[seg["id"]] = seg["facade_family"]
    out = defaultdict(list)
    for op in gt.get("openings", []):
        fam = seg_family.get(op["boundary_segment_id"])
        if fam and op["kind"] == "window":
            iv = op["world_along_interval"]
            out[fam].append((round(iv["lo"], 2), round(iv["hi"], 2)))
    return {k: sorted(v) for k, v in out.items()}


def reading_openings(path: Path) -> list[tuple[float, float]]:
    view = json.loads(path.read_text(encoding="utf-8"))
    return sorted((round(s["geometry"]["x_range_m"][0], 2), round(s["geometry"]["x_range_m"][1], 2))
                  for s in view.get("strokes", []) if s.get("pen") == "window")


def matches(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> bool:
    return len(a) == len(b) and all(abs(p[0] - q[0]) <= TOL and abs(p[1] - q[1]) <= TOL
                                    for p, q in zip(sorted(a), sorted(b)))


def main() -> int:
    rows, failures = [], 0
    for case, gt_rel, read_rel, provenance in CASES:
        gt_path, read_dir = REPO / gt_rel, REPO / read_rel
        if not gt_path.exists() or not read_dir.exists():
            print(f"{case}: skipped (missing gt or reading)")
            continue
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        normals, axes, (max_x, max_y) = facade_geometry(gt)
        gt_ops = openings_by_facade(gt)
        print(f"\n===== {case}   reading = {provenance}")
        print(f"      building bbox max: x={max_x:.2f} y={max_y:.2f}")
        for fam in ("East", "North", "South", "West"):
            view = read_dir / f"{fam}_view.json"
            if not view.exists() or fam not in gt_ops:
                continue
            (normal,) = normals[fam]
            (axis,) = axes[fam]
            mine, theirs = reading_openings(view), gt_ops[fam]
            span = max_x if axis == "x" else max_y
            direct = matches(mine, theirs)
            mirrored = matches([(round(span - hi, 2), round(span - lo, 2)) for lo, hi in mine], theirs)
            observed = +1 if direct else (-1 if mirrored else 0)
            pred = predicted_sign(normal, axis)
            ok = observed == pred and observed != 0
            failures += not ok
            rows.append((case, fam, normal, axis, pred, observed, len(mine), ok))
            print(f"   {fam:6s} n={str(normal):8s} axis={axis}  n_windows={len(mine):2d}  "
                  f"predicted={pred:+d}  observed={observed:+d}  {'OK' if ok else 'MISMATCH'}"
                  f"{'' if observed else '   (neither hypothesis fit -- see raw lists)'}")
            if not ok:
                print(f"        reading local x: {mine}")
                print(f"        gt world along : {theirs}")

    total = len(rows)
    print(f"\n=== rule: local +x = (-outward_normal) x z_hat  ('drawn as seen from outside') ===")
    print(f"=== {total - failures}/{total} facades agree across {len({r[0] for r in rows})} buildings ===")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
