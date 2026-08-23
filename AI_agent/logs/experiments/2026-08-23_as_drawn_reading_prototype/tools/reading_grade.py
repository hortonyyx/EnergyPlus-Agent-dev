"""⭐ reading grade — 线段对线段, against the machine-defined denominator.

This is the D step: the reading judge the batch guide asked for.  It scores the
as-drawn product against ``denominator.py``'s targets, in BOTH directions, with
one criterion per failure mode the third cross-family review named:

  C1 POSITION   is the drawn face line where the answer's face line is?
  C2 COVERAGE   is the answer's run actually drawn over its whole length?
                (少画 — the failure a "does it look right" glance never sees)
  C3 SEGMENTATION  do the reading's run ENDS land on the answer's run ends?
                (错切 — one stroke drawn straight through a doorway is C1+C2
                 perfect and still wrong; the gt-free ledger says so itself:
                 "it cannot judge whether a stroke should have been split")
  C4 EXTRA      length the reading claims as wall that no target explains
                (多画 — ⭐ the direction a gt-only ruler REWARDS: claiming a
                 line runs edge-to-edge raised the old reconstruct score above
                 the honest product's)

⭐ Only face lines PERCEPTION positively called walls are graded.  A face line it
declared ``non_wall`` / ``ambiguous`` is not silently forgiven either: it is
counted in the abstention ledger, and any TARGET left uncovered because of it
still scores as missing.  So abstaining cannot buy points -- it only moves the
loss from C4 to C2.

⛔ Tolerances are declared, reported and swept; ⛔ none of them is invented to
make a number look good.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

POS_TOL_M = 0.08      # same band the reconstruction uses: half the thinnest wall
SPAN_MIN = 0.80       # a target counts as drawn when this much of it is covered
END_TOL_M = 0.30      # how close a run end must be to the answer's run end
EXTRA_MIN_M = 0.10    # ignore slivers shorter than this when counting 多画


def _union(spans):
    out = []
    for lo, hi in sorted([min(a, b), max(a, b)] for a, b in spans):
        if out and lo <= out[-1][1] + 1e-9:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def _covered(spans, lo, hi):
    return sum(max(0.0, min(b, hi) - max(a, lo)) for a, b in spans)


def grade(doc: dict, den: dict, *, pos_tol: float = POS_TOL_M,
          span_min: float = SPAN_MIN, end_tol: float = END_TOL_M,
          extra_min: float = EXTRA_MIN_M) -> dict:
    hyp = doc["hypotheses"]
    graded_ids = ({x for p in (hyp.get("pairs") or []) for x in (p["face_a"], p["face_b"])}
                  | set(hyp.get("solid_band_walls") or {})
                  | set(hyp.get("unpaired_wall_faces") or {}))
    abstained = {"non_wall": len(hyp.get("non_wall_face_lines") or {}),
                 "ambiguous": len(hyp.get("ambiguous_face_lines") or {})}

    lines = []
    for f in doc["observations"]["face_lines"]:
        if f["id"] not in graded_ids:
            continue
        axis = "x" if f["constant_world_axis"] == "x" else "y"
        lines.append({"id": f["id"], "axis": axis, "const": float(f["pos_m"]),
                      "runs": _union([tuple(r) for r in f["runs_m"]])})

    rows, used_len = [], {ln["id"]: 0.0 for ln in lines}
    for t in den["targets"]:
        cands = [ln for ln in lines
                 if ln["axis"] == t["axis"] and abs(ln["const"] - t["const_m"]) <= pos_tol]
        lo, hi = t["lo_m"], t["hi_m"]
        best = None
        for ln in cands:
            cov = _covered(ln["runs"], lo, hi)
            if best is None or cov > best[0]:
                best = (cov, ln)
        row = {"axis": t["axis"], "const_m": t["const_m"], "span": [lo, hi],
               "length_m": t["length_m"]}
        if best is None or best[0] <= 0:
            row.update({"verdict": "MISSING", "matched": None, "coverage": 0.0})
            rows.append(row)
            continue
        cov, ln = best
        frac = cov / max(1e-9, hi - lo)
        used_len[ln["id"]] += cov
        # C3: does a drawn end sit near each answer end?
        ends = [e for r in ln["runs"] for e in r]
        end_err = [min((abs(e - x) for e in ends), default=9.9) for x in (lo, hi)]
        row.update({"matched": ln["id"], "coverage": round(frac, 4),
                    "const_err_m": round(abs(ln["const"] - t["const_m"]), 4),
                    "end_err_m": [round(e, 3) for e in end_err],
                    "verdict": ("OK" if frac >= span_min and max(end_err) <= end_tol
                                else "SHORT" if frac < span_min else "BAD_SPLIT")})
        rows.append(row)

    extras = []
    for ln in lines:
        drawn = sum(b - a for a, b in ln["runs"])
        # length of this line that no target on its axis+const can explain
        tgt = _union([(t["lo_m"], t["hi_m"]) for t in den["targets"]
                      if t["axis"] == ln["axis"] and abs(t["const_m"] - ln["const"]) <= pos_tol])
        unexplained = drawn - sum(_covered(tgt, a, b) for a, b in ln["runs"])
        if unexplained >= extra_min:
            extras.append({"face": ln["id"], "axis": ln["axis"],
                           "const_m": round(ln["const"], 4),
                           "unexplained_m": round(unexplained, 3),
                           "drawn_m": round(drawn, 3)})

    n = len(rows)
    ok = sum(1 for r in rows if r["verdict"] == "OK")
    tot_len = sum(r["length_m"] for r in rows)
    cov_len = sum(r["length_m"] * r["coverage"] for r in rows)
    extra_len = sum(e["unexplained_m"] for e in extras)
    return {
        "grade_version": "reading_grade_v1",
        "denominator": {"rule": den["rule_version"], "view": den["view_id"],
                        "targets": n, "length_m": round(tot_len, 3)},
        "params": {"pos_tol_m": pos_tol, "span_min": span_min,
                   "end_tol_m": end_tol, "extra_min_m": extra_min},
        "scores": {
            "C1_C2_targets_drawn_pct": round(100.0 * ok / max(1, n), 1),
            "C2_length_coverage_pct": round(100.0 * cov_len / max(1e-9, tot_len), 1),
            "C3_bad_split": sum(1 for r in rows if r["verdict"] == "BAD_SPLIT"),
            "C4_extra_length_m": round(extra_len, 3),
            "C4_extra_pct_of_answer": round(100.0 * extra_len / max(1e-9, tot_len), 1),
        },
        "by_verdict": {v: sum(1 for r in rows if r["verdict"] == v)
                       for v in ("OK", "SHORT", "BAD_SPLIT", "MISSING")},
        "perception": {"face_lines_graded": len(lines), "abstained": abstained,
                       "note": "⛔ abstaining does not forgive a target: an answer run "
                               "left uncovered still scores as MISSING/SHORT."},
        "worst_targets": sorted([r for r in rows if r["verdict"] != "OK"],
                                key=lambda r: -r["length_m"])[:12],
        "extras": sorted(extras, key=lambda e: -e["unexplained_m"])[:12],
    }


def main(doc_path: str, den_path: str, out_path: str, **kw) -> int:
    g = grade(json.loads(Path(doc_path).read_text()),
              json.loads(Path(den_path).read_text()), **kw)
    Path(out_path).write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"view": g["denominator"]["view"], **g["scores"],
                      **g["by_verdict"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    kw = {}
    for i, name in enumerate(("pos_tol", "span_min", "end_tol", "extra_min"), start=4):
        if len(sys.argv) > i:
            kw[{"pos_tol": "pos_tol", "span_min": "span_min",
                "end_tol": "end_tol", "extra_min": "extra_min"}[name]
               + ("_m" if name != "span_min" else "")] = float(sys.argv[i])
    raise SystemExit(main(sys.argv[1], sys.argv[2], sys.argv[3], **kw))
