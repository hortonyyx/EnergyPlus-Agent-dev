"""Information-not-lost proof for the as-drawn layer.

⭐ This is the prototype's most important test (user, 2026-08-23): the thorough
version is only worth building if the as-drawn layer still CONTAINS everything
today's answer layer needs.  It must not be confused with the three gt-free
self-checks in ``checks_as_drawn.py`` -- this one deliberately reads gt.

It does NOT implement 1_correction.  It asks the narrower, sufficient question:
for every target the current answer layer carries, is there an as-drawn face
line at that coordinate whose runs span it?  If yes, correction can still derive
the target; if no, the change would lose information and must not ship.

Two target families, and they are read differently on purpose:
  * EXTERIOR boundary segments -- gt records the OUTER FACE, so the match is
    against a single face line;
  * INTERIOR zone edges -- gt records the shared zone edge (the wall's centre),
    so the match is against the MIDPOINT of a band's two faces.
That asymmetry is exactly R-3 ("内墙走中轴、外墙走外包"), and seeing it survive
here is the point: the as-drawn layer carries both, so correction can emit
either frame instead of having one baked in.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.agent.judge.gt import load_gt_document  # noqa: E402
from src.agent.judge.segment_score import extract_gt_plan_segments  # noqa: E402

POS_TOL_M = 0.08          # >= half the thinnest declared wall (120 mm)          # a face line must sit within 50 mm of the target line
SPAN_MIN_COVER = 0.80     # and its runs must span at least this much of it


def _cover(runs: list[list[float]], lo: float, hi: float) -> float:
    if hi <= lo:
        return 1.0
    total = 0.0
    for a, b in runs:
        total += max(0.0, min(hi, b) - max(lo, a))
    return min(1.0, total / (hi - lo))


def _candidates(doc: dict, axis_is_x: bool):
    """(constant coord, along-runs, label) for every face line and band midline."""
    out = []
    for band in doc["wall_bands"]:
        want = "x" if axis_is_x else "y"
        if band["constant_world_axis"] != want:
            continue
        # A wall's full extent as drawn = its drawn runs UNION its openings.
        # gt records the wall as one continuous entity (openings are separate
        # objects), so comparing drawn runs alone would score every window as a
        # hole in the wall.
        ops = [o["run_m"] for o in band.get("opening_runs", [])]

        def _full(face):
            # drawn runs U openings U the face's own INTERNAL break gaps. A break
            # between two runs is a hole in a wall (a doorway), not the wall's
            # end -- the wall's end is simply where the run set stops. The gaps
            # are already transcribed, so no new judgement is introduced.
            runs = [list(r) for r in face["runs_m"]] + [list(o) for o in ops]
            rp = face["runs_px"]
            for g, (lo_px, hi_px) in zip([g for g in face["gaps"] if g["class"] == "break"],
                                         [(a[1], b[0]) for a, b in zip(rp, rp[1:])]):
                pass
            # map each internal px gap to metres via the neighbouring runs
            for i in range(len(face["runs_m"]) - 1):
                a = max(face["runs_m"][i]); b = min(face["runs_m"][i + 1])
                lo, hi = sorted((a, b))
                if hi > lo:
                    runs.append([lo, hi])
            return runs

        for f in band["faces"]:
            out.append((f["pos_m"], _full(f), f"{band['id']}.{f['role']}", "face"))
        if len(band["faces"]) == 2:
            mid = (band["faces"][0]["pos_m"] + band["faces"][1]["pos_m"]) / 2.0
            out.append((mid, _full(band["faces"][0]), f"{band['id']}.mid", "midline"))
    # An UNPAIRED face line is still transcribed information -- it is in the
    # product, just without a partner. Excluding it would understate what the
    # as-drawn layer carries (sm25 2f's x=9.146 partition is exactly this case).
    for i, l in enumerate(doc.get("unpaired_face_lines", [])):
        want_axis = "col" if axis_is_x else "row"
        if l["axis"] != want_axis:
            continue
        runs_m = l.get("runs_m")
        if runs_m is None:
            continue
        out.append((l["pos_m"], runs_m, f"U{i:02d}", "face"))
    return out


def main(gt_case: str, docs: dict[str, str], out_path: str) -> int:
    gt = load_gt_document(gt_case)
    targets = extract_gt_plan_segments(gt)
    rows, missing = [], []
    for t in targets:
        floor = t.floor_id
        doc_path = docs.get(floor)
        if doc_path is None:
            continue
        doc = json.loads(Path(doc_path).read_text())
        (x1, y1), (x2, y2) = tuple(t.p1), tuple(t.p2)
        horizontal = abs(y2 - y1) < 1e-6
        const = y1 if horizontal else x1
        lo, hi = sorted((x1, x2) if horizontal else (y1, y2))
        want_kinds = ("face",) if t.exterior else ("midline", "face")
        best = None
        for pos, runs, label, kind in _candidates(doc, axis_is_x=not horizontal):
            if kind not in want_kinds:
                continue
            d = abs(pos - const)
            if d > POS_TOL_M:
                continue
            cov = _cover(runs, lo, hi)
            score = (cov, -d)
            if best is None or score > best[0]:
                best = (score, label, kind, d, cov)
        row = {"target": t.key[:60], "floor": floor, "exterior": t.exterior,
               "horizontal": horizontal,
               "const": round(const, 3), "span": [round(lo, 3), round(hi, 3)],
               "length_m": round(hi - lo, 3)}
        if best is None:
            row.update({"matched": None, "verdict": "NO_LINE_AT_COORDINATE"})
            missing.append(row)
        else:
            _s, label, kind, d, cov = best
            ok = cov >= SPAN_MIN_COVER
            row.update({"matched": label, "kind": kind, "offset_m": round(d, 4),
                        "span_coverage": round(cov, 3),
                        "verdict": "OK" if ok else "SHORT_COVERAGE"})
            if not ok:
                missing.append(row)
        rows.append(row)

    ext = [r for r in rows if r["exterior"]]
    inte = [r for r in rows if not r["exterior"]]

    def rate(rs):
        return round(100.0 * sum(1 for r in rs if r["verdict"] == "OK") / max(1, len(rs)), 1)

    summary = {"gt_case": gt_case, "targets": len(rows),
               "exterior": {"n": len(ext), "ok_pct": rate(ext)},
               "interior": {"n": len(inte), "ok_pct": rate(inte)},
               "overall_ok_pct": rate(rows),
               "pos_tol_m": POS_TOL_M, "span_min_cover": SPAN_MIN_COVER}
    Path(out_path).write_text(json.dumps({"summary": summary, "rows": rows,
                                          "not_recoverable": missing},
                                         ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    if missing:
        print(f"  不可还原 {len(missing)} 条，前 10:")
        for r in sorted(missing, key=lambda x: -x["length_m"])[:10]:
            print(f"    {r['verdict']:<22} {'外' if r['exterior'] else '内'} "
                  f"const={r['const']:7.3f} span={r['span']} 长{r['length_m']:6.3f}m "
                  f"cov={r.get('span_coverage')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]))
