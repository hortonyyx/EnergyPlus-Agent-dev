"""Information-not-lost proof against the **v2** as-drawn product.

Same question as the v1 checker, but consuming the three-layer schema, and with
the three false-greens the second cross-family review demonstrated closed:

  1. **One pixel could bridge a whole wall.**  v1 bridged a gap whenever the
     opening-ink count was ``> 0``; fabricating a single cyan pixel per gap
     took a product with its middles deleted from 30.0% back to 100.0%.  A gap
     now counts as an opening only when opening ink runs along at least
     ``OPENING_SPAN_MIN`` of the gap's LENGTH -- a quantity one stray pixel
     cannot move.
  2. **Two coincident lines could impersonate a wall.**  v1's interior rule had
     an upper spacing bound and nothing else, so two lines 0.2 mm apart scored
     1.0.  A pair now needs DISJOINT support columns and a spacing inside a
     stated domain band; and because v2 face lines come from disjoint column
     groups by construction, a real product cannot produce the twin at all.
  3. **A solid band had to be split into two synthetic faces.**  That split was
     a hypothesis living in the observation layer.  v2 emits the group's own
     ``edges_m`` instead, so a filled wall satisfies an interior target as ONE
     observation whose edges straddle it (case B below), with no invention.

⛔ Reads gt on purpose; the gt-free self-checks are elsewhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.agent.judge.gt import load_gt_document  # noqa: E402
from src.agent.judge.segment_score import extract_gt_plan_segments  # noqa: E402

POS_TOL_M = 0.08          # within half the thinnest declared wall (120 mm)
SPAN_MIN_COVER = 0.80     # and the drawn stretch must span this much of the target
MIN_WALL_M = 0.05         # domain band for "this could be one wall". Both ends
MAX_WALL_M = 0.50         # are swept in the README; neither is load-bearing.
# Fraction of a blank stretch's LENGTH that must carry opening ink before the
# stretch counts as an opening rather than as wall the reader failed to draw.
# ⭐ Chosen to be immune to single-pixel noise by construction, and swept.
OPENING_SPAN_MIN = 0.10


def _cover(runs, lo, hi) -> float:
    """Fraction of [lo,hi] covered by the UNION of runs."""
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


def _extent(face, *, opening_span_min: float, fen_family: str | None) -> list[list[float]]:
    """A face line's drawn stretches, plus the gaps the drawing calls openings.

    A wall continues through its own doorway, so a gap the drawing fills with
    opening ink counts.  A gap with no such ink is a stretch of wall the reader
    did not draw and must NOT count -- that is the whole difference between
    this check and one that cannot see a missing middle.

    ⭐ WHICH ink family is the opening layer is not decided here: it is read out
    of the product's own ``hypotheses.family_roles`` (a perception output).
    That is deliberate -- it makes the naming FALSIFIABLE.  Point the role at
    the wrong family and this check goes red, which is the whole reason the
    naming lives in the product instead of in this file.
    """
    out = [list(r) for r in face["runs_m"]]
    if fen_family is None:
        return out
    for g in face.get("gaps", []):
        prof = g.get("ink_by_family", {}).get(fen_family)
        if prof and prof.get("span_ratio", 0.0) >= opening_span_min:
            out.append(list(g["span_m"]))
    return out


def _intersect(a, b):
    return [[max(min(p), min(q)), min(max(p), max(q))]
            for p in a for q in b if min(max(p), max(q)) > max(min(p), min(q))]


def _axis_lines(doc, axis_is_x):
    want = "x" if axis_is_x else "y"
    return [f for f in doc["observations"]["face_lines"]
            if f["constant_world_axis"] == want]


def _best_exterior(lines, const, lo, hi, osm, m_per_px, fen):
    """gt records the OUTER FACE, so either a thin line or one edge of a band."""
    best = None
    for f in lines:
        half = (f["support_cols_px"][1] - f["support_cols_px"][0]) * m_per_px / 2.0
        cands = [("pos", f["pos_m"]), ("edge", f["pos_m"] - half), ("edge", f["pos_m"] + half)]
        for kind, v in cands:
            d = abs(v - const)
            if d > POS_TOL_M:
                continue
            cov = _cover(_extent(f, opening_span_min=osm, fen_family=fen), lo, hi)
            key = (cov, -d)
            if best is None or key > best[0]:
                best = (key, {"matched": f["id"], "kind": f"face_{kind}",
                              "offset_m": round(d, 4), "span_coverage": round(cov, 3)})
    return best


def _best_interior(lines, const, lo, hi, osm, m_per_px, fen):
    """Two things can put a wall CENTRE at the target, and both are measured."""
    best = None
    # case B -- one filled group whose own two edges straddle the target
    #
    # ⭐ The edges are RE-DERIVED from the group's support columns and the
    # calibration, ⛔ never taken from the product's own `edges_m`. A neuter
    # that simply rewrites `edges_m` to claim every thin stroke is a 0.24 m
    # filled band scored 94.7% -- HIGHER than the truthful product -- until
    # this was changed. A check that trusts a claim it could recompute is not
    # a check.
    for f in lines:
        c0, c1 = f["support_cols_px"]
        half = (c1 - c0) * m_per_px / 2.0
        e = [f["pos_m"] - half, f["pos_m"] + half]
        if not (min(e) < const < max(e)):
            continue
        w = max(e) - min(e)
        if not (MIN_WALL_M <= w <= MAX_WALL_M):
            continue
        d = abs((e[0] + e[1]) / 2.0 - const)
        if d > POS_TOL_M:
            continue
        cov = _cover(_extent(f, opening_span_min=osm, fen_family=fen), lo, hi)
        key = (cov, -d)
        if best is None or key > best[0]:
            best = (key, {"matched": f["id"], "kind": "filled_band",
                          "spacing_m": round(w, 4), "offset_m": round(d, 4),
                          "span_coverage": round(cov, 3)})
    # case A -- two DISTINCT groups straddling the target
    for i, A in enumerate(lines):
        for B in lines[i + 1:]:
            (a0, a1), (b0, b1) = A["support_cols_px"], B["support_cols_px"]
            if min(a1, b1) > max(a0, b0):       # ⭐ shared ink = one stroke read twice
                continue
            gap = abs(A["pos_m"] - B["pos_m"])
            if not (MIN_WALL_M <= gap <= MAX_WALL_M):
                continue
            if not min(A["pos_m"], B["pos_m"]) < const < max(A["pos_m"], B["pos_m"]):
                continue
            d = abs((A["pos_m"] + B["pos_m"]) / 2.0 - const)
            if d > POS_TOL_M:
                continue
            cov = _cover(_intersect(_extent(A, opening_span_min=osm, fen_family=fen),
                                    _extent(B, opening_span_min=osm, fen_family=fen)),
                         lo, hi)
            key = (cov, -d)
            if best is None or key > best[0]:
                best = (key, {"matched": f"{A['id']}+{B['id']}", "kind": "straddling_pair",
                              "spacing_m": round(gap, 4), "offset_m": round(d, 4),
                              "span_coverage": round(cov, 3)})
    return best


# ---------------------------------------------------------------- neuter ----
def _mutate(doc: dict, kind: str) -> str:
    fl = doc["observations"]["face_lines"]

    def punch(f):
        out = []
        for a, b in f["runs_m"]:
            lo, hi = sorted((a, b))
            if hi - lo > 0.5:
                out += [[lo, lo + 0.4 * (hi - lo)], [hi - 0.4 * (hi - lo), hi]]
            else:
                out.append([lo, hi])
        f["runs_m"] = out

    if kind == "punch_middle":
        for f in fl:
            punch(f)
        return "MUTATED: middle 20% of every run longer than 0.5 m deleted"
    if kind == "punch_middle_one_pixel":
        # ⭐ The exploit that beat v1 (sol, second review): claim the deleted
        # middles are openings on the strength of one stray pixel each.
        for f in fl:
            punch(f)
            # ⚠️ The fabricated gap must carry the REAL span between the two
            # runs it sits in, or the mutation silently bridges nothing and the
            # neuter passes for the wrong reason (I wrote it that way first).
            g = []
            for a, b in zip(f["runs_m"], f["runs_m"][1:]):
                lo, hi = sorted((max(a), min(b)))
                if hi <= lo:
                    continue
                length_px = max(1, int(round((hi - lo) / 0.0216)))
                # ⚠️ 2026-08-24, third cross-family review: this used to write a
                # key called ``opening_ink`` -- WHICH NOTHING READS.  The
                # consumer is ``ink_by_family[<the product's own opening
                # family>].span_ratio``.  So the 0.0 / 0.0 this neuter scored was
                # produced by the deleted middles alone; it never exercised the
                # bridge at all, and "one pixel cannot move the span judgement"
                # was an unearned claim.  Same shape as the discipline I wrote
                # down myself: "a mutation that did not run and a mutation with
                # no effect are indistinguishable in the artifact".
                fen = doc["hypotheses"]["family_roles"]["assignment"].get("fenestration")
                g.append({"span_m": [lo, hi], "len_px": length_px,
                          "ink_by_family": {fen: {"on_line": 1,
                                                  "span_ratio": round(1.0 / length_px, 6),
                                                  "nearest_px": 0,
                                                  "by_distance_px": {}}}})
            f["gaps"] = g
        # report how many fabricated gaps actually clear the bridge threshold,
        # so "immune" can never again mean "never reached the branch"
        hits = sum(1 for x in fl for gg in x["gaps"]
                   for pr in [list(gg["ink_by_family"].values())[0]]
                   if pr["span_ratio"] >= OPENING_SPAN_MIN)
        total = sum(len(x["gaps"]) for x in fl)
        return ("MUTATED: middles deleted, each new gap claimed as an opening on 1 px "
                f"in the CONSUMED schema; {hits}/{total} fabricated gaps clear "
                f"OPENING_SPAN_MIN={OPENING_SPAN_MIN}")
    if kind == "duplicate_face":
        # ⭐ The other exploit: a twin line 0.2 mm away, same runs.
        twins = []
        for f in fl:
            t = json.loads(json.dumps(f))
            t["id"] = f["id"] + "_TWIN"
            t["pos_m"] = round(f["pos_m"] + 0.0002, 6)
            twins.append(t)
        doc["observations"]["face_lines"] = fl + twins
        return f"MUTATED: {len(twins)} twin face lines added 0.2 mm away with identical runs"
    if kind == "shrink_runs":
        for f in fl:
            f["runs_m"] = [[min(r) + 0.25 * abs(r[1] - r[0]),
                            max(r) - 0.25 * abs(r[1] - r[0])] for r in f["runs_m"]]
        return "MUTATED: every run shortened 25% at each end"
    if kind == "keep_longest_run":
        for f in fl:
            if len(f["runs_m"]) > 1:
                f["runs_m"] = [max(f["runs_m"], key=lambda r: abs(r[1] - r[0]))]
        return "MUTATED: only the longest run kept per face line"
    if kind == "drop_one_of_each_pair":
        # ⭐ works off the SELECTION when the model has made one, else off the
        # code-enumerated candidates -- the neuter must not go quiet just
        # because nobody has chosen yet.
        src = (doc["hypotheses"].get("pairs")
               or doc["hypotheses"].get("pair_candidates") or [])
        drop = {p["face_b"] for p in src}
        doc["observations"]["face_lines"] = [f for f in fl if f["id"] not in drop]
        return f"MUTATED: {len(drop)} of the paired face lines removed"
    if kind == "misname_opening_family":
        # ⭐ The semantic neuter: point the opening role at the wrong family.
        # Nothing about the MEASUREMENTS changes -- only the naming -- so if
        # this does not go red, the naming was never load-bearing and the model
        # could have said anything.
        a = doc["hypotheses"]["family_roles"]["assignment"]
        fams = sorted({k for f in doc["observations"]["face_lines"]
                       for g in f.get("gaps", []) for k in g.get("ink_by_family", {})})
        wrong = next((x for x in fams if x != a.get("fenestration")), None)
        a["fenestration"] = wrong
        return f"MUTATED: opening role re-pointed from the drawing's own family to {wrong}"
    if kind == "drop_opening_role":
        doc["hypotheses"]["family_roles"]["assignment"].pop("fenestration", None)
        return "MUTATED: opening role removed entirely"
    if kind == "extend_runs_full":
        # ⭐ The cheat this gt-side check CANNOT see, kept here on purpose so the
        # pair of checks can be compared on one fixture: claim every face line is
        # drawn edge to edge.  Every target is then fully covered for free.  The
        # ⛔ gt-free reverse ledger (checks_as_drawn_v2.py) is what kills it --
        # it samples the ORIGINAL image under each claimed stretch.
        for axis in ("x", "y"):
            same = [f for f in fl if f["constant_world_axis"] == axis]
            if not same:
                continue
            lo = min(min(r) for f in same for r in f["runs_m"])
            hi = max(max(r) for f in same for r in f["runs_m"])
            for f in same:
                f["runs_m"] = [[lo, hi]]
        return "MUTATED: every face line claims to be drawn across the whole plan"
    if kind == "widen_all":
        for f in fl:
            c = f["pos_m"]
            f["edges_m"] = [c - 0.12, c + 0.12]
        return "MUTATED: every face line claims to be a 0.24 m filled band"
    raise SystemExit(f"unknown mutation {kind!r}")


def _admissibility(docs: dict[str, str], mutate: str | None) -> dict:
    """⛔ This score alone is NOT a grade.

    2026-08-24, third cross-family review: a product that really failed to read
    1.2 m of wall and then FABRICATED the gap evidence for that stretch scores
    the same 94.6 here as the honest product.  What catches it is the gt-free
    recompute gate (``checks_as_drawn_v2.py``), not this file -- this file has no
    image to check against.  So every report says out loud whether the product it
    scored was verified, instead of letting the number travel on its own.
    """
    state = []
    for fid, path in docs.items():
        name = Path(path).name
        cands = [Path(path).with_name(name.replace("_v2.json", "_checks_v2.json")),
                 Path(path).with_name(Path(path).stem + "_checks.json")]
        d, rep = None, None
        for c in cands:
            if not c.exists() or c == Path(path):
                continue
            try:
                cand = json.loads(c.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(cand.get("checks"), list):
                d, rep = cand, c
                break
        if mutate or d is None:
            state.append({"floor": fid, "verified_by": None})
            continue
        state.append({"floor": fid, "verified_by": str(rep),
                      "gates": {c["check"]: c["status"] for c in d["checks"]}})
    reds = sorted({g for s in state for g, v in (s.get("gates") or {}).items() if v == "red"})
    ok = all(s.get("gates") and all(v != "red" for v in s["gates"].values()) for s in state)
    return {"admissible_as_a_grade": bool(ok and not mutate),
            "red_gt_free_gates": reds,
            "why": ("every floor's product passed the gt-free recompute gates"
                    if ok and not mutate else
                    f"⛔ NOT a grade: red gt-free gates {reds}" if reds else
                    "⛔ NOT a grade: the scored product was mutated, or was not "
                    "verified by checks_as_drawn_v2.py. A fabricated gap profile "
                    "is invisible here by construction."),
            "per_floor": state}


def main(gt_case: str, docs: dict[str, str], out_path: str, *,
         mutate: str | None = None, opening_span_min: float = OPENING_SPAN_MIN) -> int:
    gt = load_gt_document(gt_case)
    loaded, note = {}, None
    for fid, path in docs.items():
        loaded[fid] = json.loads(Path(path).read_text())
        if mutate:
            note = _mutate(loaded[fid], mutate)
    rows, missing = [], []
    for t in extract_gt_plan_segments(gt):
        doc = loaded.get(t.floor_id)
        if doc is None:
            continue
        (x1, y1), (x2, y2) = tuple(t.p1), tuple(t.p2)
        horizontal = abs(y2 - y1) < 1e-6
        const = y1 if horizontal else x1
        lo, hi = sorted((x1, x2) if horizontal else (y1, y2))
        lines = _axis_lines(doc, axis_is_x=not horizontal)
        m_per_px = doc["observations"]["calibration"]["mm_per_px"] / 1000.0
        fen = doc["hypotheses"]["family_roles"]["assignment"].get("fenestration")
        best = (_best_exterior if t.exterior else _best_interior)(
            lines, const, lo, hi, opening_span_min, m_per_px, fen)
        row = {"target": t.key[:60], "floor": t.floor_id, "exterior": t.exterior,
               "const": round(const, 3), "span": [round(lo, 3), round(hi, 3)],
               "length_m": round(hi - lo, 3)}
        if best is None:
            row.update({"matched": None, "verdict": "NO_CANDIDATE"})
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

    used = sorted(r["spacing_m"] for r in rows if r["verdict"] == "OK" and "spacing_m" in r)
    kinds: dict[str, int] = {}
    for r in rows:
        if r["verdict"] == "OK":
            kinds[r.get("kind", "?")] = kinds.get(r.get("kind", "?"), 0) + 1
    summary = {"gt_case": gt_case, "schema": "as_drawn_plan_v2", "mutation": note,
               "targets": len(rows),
               "exterior": {"n": len(ext), "ok_pct": rate(ext)},
               "interior": {"n": len(inte), "ok_pct": rate(inte)},
               "overall_ok_pct": rate(rows),
               "matched_by_kind": dict(sorted(kinds.items())),
               "wall_spacing_used_m": ([used[0], used[len(used) // 2], used[-1]]
                                       if used else None),
               "pos_tol_m": POS_TOL_M, "span_min_cover": SPAN_MIN_COVER,
               "wall_band_m": [MIN_WALL_M, MAX_WALL_M],
               "opening_span_min": opening_span_min,
               "admissibility": _admissibility(docs, mutate)}
    Path(out_path).write_text(json.dumps({"summary": summary, "rows": rows,
                                          "not_recoverable": missing},
                                         ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], json.loads(sys.argv[2]), sys.argv[3],
                          mutate=sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None,
                          opening_span_min=(float(sys.argv[5]) if len(sys.argv) > 5
                                            else OPENING_SPAN_MIN)))
