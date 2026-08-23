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
    so the match needs TWO face lines STRADDLING the target, and is scored on
    the stretch where both of them are drawn.
That asymmetry is exactly R-3 ("内墙走中轴、外墙走外包"), and seeing it survive
here is the point: the as-drawn layer carries both, so correction can emit
either frame instead of having one baked in.

⭐ G-1 (2026-08-23, raised by the first cross-family review): the interior rule
used to fall back to a LONE face line.  That made the check answer a much
weaker question than the one it claims to ask -- a single unpaired line, with
no thickness, no side and no partner, cannot yield a centreline.  Measured
under the old rule, all 16 of sm24's interior targets passed on a lone face and
15 of its 20 targets matched an UNPAIRED line, so its score said nothing about
whether correction could recover the answer.

The straddling pair is searched over ALL transcribed face lines, not over the
product's emitted bands: pairing is a HYPOTHESIS and this check deliberately
asks what the OBSERVATIONS alone can support.  The only bound is a domain one
(no wall in this building family is thicker than ``MAX_WALL_M``), and every
spacing actually used is reported so the bound cannot hide behind the score.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.agent.judge.gt import load_gt_document  # noqa: E402
from src.agent.judge.segment_score import extract_gt_plan_segments  # noqa: E402

POS_TOL_M = 0.08          # a face line must sit within half the thinnest declared wall (120 mm)
SPAN_MIN_COVER = 0.80     # and its runs must span at least this much of the target
MAX_WALL_M = 0.50         # domain bound for "these two faces could be one wall";
                          # every spacing actually used is reported, so a run
                          # that only passes via implausible 0.4 m "walls" is
                          # visible instead of hidden inside the percentage.


def _cover(runs: list[list[float]], lo: float, hi: float) -> float:
    """Fraction of [lo,hi] covered by the UNION of ``runs``.

    ⭐ 2026-08-23 cross-family review (sol): this used to sum the clipped
    intervals without merging them.  The interval set handed in here is runs U
    openings U bridged gaps, and those overlap by construction, so the sum
    double-counted.  Measured on the 240 candidate evaluations of sm24+sm25:
    47 were inflated, the worst by 0.291 -- more than the whole margin between
    a pass and a fail.
    """
    if hi <= lo:
        return 1.0
    clipped = sorted([max(lo, min(a, b)), min(hi, max(a, b))] for a, b in runs)
    total, cur = 0.0, None
    for a, b in clipped:
        if b <= a:
            continue
        if cur is not None and a <= cur[1]:
            cur[1] = max(cur[1], b)
        else:
            if cur is not None:
                total += cur[1] - cur[0]
            cur = [a, b]
    if cur is not None:
        total += cur[1] - cur[0]
    return min(1.0, total / (hi - lo))


def _full_extent(runs_m: list[list[float]],
                 openings: list[list[float]] | None = None,
                 gaps: list[dict] | None = None) -> list[list[float]]:
    """A line's full drawn extent = its runs U openings U its INTERNAL break gaps.

    A break between two consecutive runs is a hole in a wall (a doorway), not
    the wall's end -- the wall's end is simply where the run set stops.  Both
    the runs and the gaps are already transcribed, so nothing new is judged
    here.  Openings are the band's transcribed fenestration runs; a line with
    no band (an unpaired face line) has none, and gets the gap union only.

    ⭐ P-1 fix (2026-08-23): this used to be a closure applied to paired band
    faces only, while unpaired face lines were compared on their RAW runs.  The
    two are the same kind of object, so the asymmetry understated coverage
    wherever pairing failed -- measured on sm24, every SHORT_COVERAGE row was
    matched to an unpaired line (U09/U11/U57).

    ⭐⭐ 2026-08-23 cross-family review (sol) overturned the first version of
    this rule.  It bridged EVERY internal gap unconditionally, which made the
    whole check blind to the most realistic failure of all -- a face line whose
    MIDDLE was never read.  Measured: deleting the middle 20% of 153 (sm24) /
    198 (sm25) runs left the score at 100.0 / 94.7, bit for bit.

    A gap is now bridged only when the band's own transcribed fenestration ink
    overlaps it, i.e. only when the drawing says an opening is there.  That is
    the same data, read honestly: an unexplained hole in a face line is not
    evidence of a wall.  An UNPAIRED line has no opening evidence at all, so
    none of its gaps bridge -- which is why sm24 (69 unpaired lines) drops from
    an inflated 100.0% to 85.0% while sm25 does not move at all (94.7%).
    """
    ops = [list(o) for o in (openings or [])]
    runs = [list(r) for r in runs_m] + ops
    # The i-th run boundary is the i-th gap the scanner classed as a "break";
    # hairline gaps were absorbed into a run and are not boundaries.
    breaks = [g for g in (gaps or []) if g.get("class") == "break"]
    for i in range(len(runs_m) - 1):
        lo, hi = sorted((max(runs_m[i]), min(runs_m[i + 1])))
        if hi <= lo:
            continue
        # ⭐ Prefer the GAP's own fenestration measurement (design v2 §three).
        # Falling back to the band's opening list is what made this check blind
        # to an unpaired line's doorways: opening ink used to be measured per
        # band, so a line that never paired had gaps with no evidence at all.
        if i < len(breaks) and "fenestration_px_near" in breaks[i]:
            if breaks[i]["fenestration_px_near"] > 0:
                runs.append([lo, hi])
            continue
        if any(max(lo, min(a, b)) < min(hi, max(a, b)) for a, b in ops):
            runs.append([lo, hi])
    return runs


def _face_lines(doc: dict, axis_is_x: bool):
    """Every transcribed face line on this axis, banded or not.

    ⛔ Deliberately flat: a band is a pairing HYPOTHESIS, and this check asks
    what the observations support on their own.  Openings ride along with the
    band they were measured in, because a run's hole is only known to be an
    opening when the drawing put fenestration ink there.
    """
    out = []
    want = "x" if axis_is_x else "y"
    for band in doc["wall_bands"]:
        if band["constant_world_axis"] != want:
            continue
        ops = [o["run_m"] for o in band.get("opening_runs", [])]
        for f in band["faces"]:
            out.append({"pos": f["pos_m"],
                        "runs": _full_extent(f["runs_m"], ops, f.get("gaps")),
                        "label": f"{band['id']}.{f['role']}"})
    # An UNPAIRED face line is still transcribed information -- it is in the
    # product, just without a partner.
    for i, l in enumerate(doc.get("unpaired_face_lines", [])):
        if l["axis"] != ("col" if axis_is_x else "row"):
            continue
        if l.get("runs_m") is None:
            continue
        out.append({"pos": l["pos_m"],
                    "runs": _full_extent(l["runs_m"], None, l.get("gaps")),
                    "label": f"U{i:02d}"})
    return out


def _intersect(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Stretches where BOTH faces are drawn -- that is where the wall is."""
    out = []
    for p in a:
        for q in b:
            lo, hi = max(min(p), min(q)), min(max(p), max(q))
            if hi > lo:
                out.append([lo, hi])
    return out


def _best_exterior(lines, const, lo, hi):
    best = None
    for f in lines:
        d = abs(f["pos"] - const)
        if d > POS_TOL_M:
            continue
        cov = _cover(f["runs"], lo, hi)
        if best is None or (cov, -d) > best[0]:
            best = ((cov, -d), {"matched": f["label"], "kind": "face",
                                "offset_m": round(d, 4), "span_coverage": round(cov, 3)})
    return best


def _best_interior(lines, const, lo, hi):
    """Two face lines straddling the target, scored where both are drawn."""
    best = None
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            gap = abs(a["pos"] - b["pos"])
            if gap <= 0.0 or gap > MAX_WALL_M:
                continue
            if not (min(a["pos"], b["pos"]) < const < max(a["pos"], b["pos"])
                    or abs((a["pos"] + b["pos"]) / 2.0 - const) <= 1e-9):
                continue
            d = abs((a["pos"] + b["pos"]) / 2.0 - const)
            if d > POS_TOL_M:
                continue
            cov = _cover(_intersect(a["runs"], b["runs"]), lo, hi)
            if best is None or (cov, -d) > best[0]:
                best = ((cov, -d), {"matched": f"{a['label']}+{b['label']}",
                                    "kind": "straddling_pair",
                                    "spacing_m": round(gap, 4),
                                    "offset_m": round(d, 4),
                                    "span_coverage": round(cov, 3)})
    return best


# ---------------------------------------------------------------- neuter ----
# This check asks "is the information still THERE", so a neuter that proves it
# discriminates must REMOVE information.  ``checks_as_drawn.py``'s merge_runs
# mutation is the wrong direction here -- collapsing runs to [min,max] ADDS
# span, so it would make this check greener, not redder.

def _mutate(doc: dict, kind: str) -> str:
    lines = [f for band in doc["wall_bands"] for f in band["faces"]]
    loose = doc.get("unpaired_face_lines", [])
    if kind == "punch_middle":
        # ⭐ The mutation the first neuter set missed (sol, 2026-08-23): a face
        # line read at both ends but not in the middle. This is what a reader
        # that loses a stretch of wall actually produces.
        for f in lines + loose:
            out = []
            for a, b in f["runs_m"]:
                lo, hi = sorted((a, b))
                if hi - lo > 0.5:
                    out += [[lo, lo + 0.4 * (hi - lo)], [hi - 0.4 * (hi - lo), hi]]
                else:
                    out.append([lo, hi])
            f["runs_m"] = out
        return "MUTATED: middle 20% of every run longer than 0.5 m deleted"
    if kind == "shrink_runs":
        for f in lines + loose:
            out = []
            for a, b in f["runs_m"]:
                lo, hi = sorted((a, b))
                cut = (hi - lo) * 0.25
                out.append([lo + cut, hi - cut])
            f["runs_m"] = out
        return "MUTATED: every face-line run shortened 25% at each end"
    if kind == "keep_longest_run":
        for f in lines + loose:
            if len(f["runs_m"]) > 1:
                f["runs_m"] = [max(f["runs_m"], key=lambda r: abs(r[1] - r[0]))]
        return "MUTATED: only the longest run kept per face line"
    if kind == "drop_unpaired":
        n = len(loose)
        doc["unpaired_face_lines"] = []
        return f"MUTATED: all {n} unpaired face lines dropped"
    if kind == "drop_one_face":
        # ⭐ G-1's own neuter: keep only one face of every band. Under the old
        # lone-face interior rule this was invisible; a straddling-pair rule
        # must see it.
        n = 0
        for band in doc["wall_bands"]:
            if len(band["faces"]) == 2:
                band["faces"] = band["faces"][:1]
                n += 1
        return f"MUTATED: second face removed from {n} bands"
    raise SystemExit(f"unknown mutation {kind!r}")


def main(gt_case: str, docs: dict[str, str], out_path: str,
         *, mutate: str | None = None) -> int:
    gt = load_gt_document(gt_case)
    targets = extract_gt_plan_segments(gt)
    rows, missing = [], []
    loaded: dict[str, dict] = {}
    note = None
    for floor_id, path in docs.items():
        loaded[floor_id] = json.loads(Path(path).read_text())
        if mutate:
            note = _mutate(loaded[floor_id], mutate)
    for t in targets:
        floor = t.floor_id
        doc = loaded.get(floor)
        if doc is None:
            continue
        (x1, y1), (x2, y2) = tuple(t.p1), tuple(t.p2)
        horizontal = abs(y2 - y1) < 1e-6
        const = y1 if horizontal else x1
        lo, hi = sorted((x1, x2) if horizontal else (y1, y2))
        lines = _face_lines(doc, axis_is_x=not horizontal)
        best = (_best_exterior if t.exterior else _best_interior)(lines, const, lo, hi)
        row = {"target": t.key[:60], "floor": floor, "exterior": t.exterior,
               "horizontal": horizontal,
               "const": round(const, 3), "span": [round(lo, 3), round(hi, 3)],
               "length_m": round(hi - lo, 3)}
        if best is None:
            row.update({"matched": None,
                        "verdict": "NO_LINE_AT_COORDINATE" if t.exterior
                                   else "NO_STRADDLING_PAIR"})
            missing.append(row)
        else:
            row.update(best[1])
            ok = row["span_coverage"] >= SPAN_MIN_COVER
            row["verdict"] = "OK" if ok else "SHORT_COVERAGE"
            if not ok:
                missing.append(row)
        rows.append(row)

    ext = [r for r in rows if r["exterior"]]
    inte = [r for r in rows if not r["exterior"]]

    def rate(rs):
        return round(100.0 * sum(1 for r in rs if r["verdict"] == "OK") / max(1, len(rs)), 1)

    used_gaps = sorted(r["spacing_m"] for r in rows
                       if r["verdict"] == "OK" and "spacing_m" in r)
    summary = {"gt_case": gt_case, "mutation": note, "targets": len(rows),
               # ⭐ the bound cannot hide behind the score: every wall spacing
               # this run leaned on is reported.
               "interior_pair_spacing_m": ([used_gaps[0], used_gaps[len(used_gaps) // 2],
                                            used_gaps[-1]] if used_gaps else None),
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
    raise SystemExit(main(sys.argv[1], json.loads(sys.argv[2]), sys.argv[3],
                          mutate=sys.argv[4] if len(sys.argv) > 4 else None))
