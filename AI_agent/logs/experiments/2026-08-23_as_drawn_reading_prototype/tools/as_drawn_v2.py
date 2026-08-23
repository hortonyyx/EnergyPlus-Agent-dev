"""As-drawn plan transcription, **v2 schema** — three layers, no domain classification.

⭐ Why this file exists (2026-08-23): two cross-family reviews rejected the v1
prototype, and the second one's headline was that the DESIGN DOCUMENT described
a shape the CODE did not implement -- so every number quoted in support of it
had actually been produced by the v1 shape.  This module is that shape, for
real, so the numbers can be re-measured on the thing being proposed.

The product is split into three layers, and the split is the whole point:

  ``observations``   what a ruler measured on pixels.  ⭐ The only scorable
                     layer, and the only one a downstream consumer may treat
                     as fact.
  ``declarations``   what the drawing or its config ASSERTS, transcribed
                     verbatim.  Compared by text, never by meaning.
  ``hypotheses``     everything derived from the first two.  ⛔ Not scored and
                     droppable in one piece.

The property that makes the split worth having: **``observations`` +
``declarations`` must be enough to re-derive every hypothesis.**  A field that
fails that test is smuggling a judgement.

What changed from v1, and why each one was forced:

  * **No bridging.**  v1 merged blank stretches shorter than 0.60 m into the
    run and labelled the rest ``break``.  The first review showed the same
    0.60 m does opposite work on the two ink layers (closing dropouts in wall
    lines, swallowing piers between windows).  Runs here are RAW maximal
    continuous stretches and every blank is reported.
  * **No ``class`` on a gap.**  A gap carries measurements; naming it is
    1_correction's job.
  * **Re-computable opening evidence.**  v1 emitted two aggregate cyan-pixel
    counts at one fixed window, and a consumer who disliked the window could
    not recompute.  Worse, the check built on it could be satisfied by ONE
    pixel.  Each gap now carries a distance PROFILE plus the along-gap span
    that actually has opening ink, and the components themselves are emitted.
  * **Pairing is a hypothesis with every admissible partner listed.**  v1 took
    the first admissible partner and broke.  (Measured: that greedy order was
    not what mis-paired sm24 -- 0 of its 98 lines had more than one admissible
    partner -- but enumerating costs nothing and removes the question.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import (  # noqa: E402
    Axis, dialect_report, dump, fit_chain, ink_families, load_rgb,
    vertical_runs_mask, witness_ticks,
)

SCHEMA = "as_drawn_plan_v2"

# Distance bins (px) for the per-gap opening-ink profile. A profile, not a
# single windowed count, is what makes the evidence re-computable: a consumer
# who wants a 0.10 m window sums the near bins, one who wants 0.30 m sums more.
PROFILE_BINS_PX = (2, 5, 10, 15, 25)

# A position along a line counts as inked when at least this fraction of the
# group's own columns carry ink there. Same value and same reason as v1: a
# solid band is ~9 px wide and "any column" would call it present wherever only
# its edge is drawn.
FILL_RATIO = 0.5


def _raw_runs(flags: np.ndarray) -> tuple[list[list[int]], list[list[int]]]:
    """Maximal continuous runs of True, and every blank between them.

    ⛔ No bridging, no threshold, no classification -- that is the v2 change.
    """
    idx = np.flatnonzero(flags)
    if idx.size == 0:
        return [], []
    edges = np.flatnonzero(np.diff(idx) > 1)
    runs, start = [], idx[0]
    for e in edges:
        runs.append([int(start), int(idx[e]) + 1])
        start = idx[e + 1]
    runs.append([int(start), int(idx[-1]) + 1])
    gaps = [[a[1], b[0]] for a, b in zip(runs, runs[1:])]
    return runs, gaps


def _profile(mask: np.ndarray, lo: int, hi: int, c0: int, c1: int) -> dict[str, Any]:
    """Distance profile of one ink family across a blank stretch of a line.

    ``on_line`` is the group's own columns; each further bin adds a ring of
    columns at that distance.  ``span_ratio`` is the fraction of the stretch's
    LENGTH that has any such ink within the widest bin -- the quantity a single
    stray pixel cannot move, which is exactly what the v1 evidence lacked.
    """
    if hi <= lo:
        return {"on_line": 0, "by_distance_px": {}, "span_ratio": 0.0, "nearest_px": None}
    out: dict[str, int] = {}
    prev_lo, prev_hi = c0, c1
    for d in PROFILE_BINS_PX:
        w_lo, w_hi = max(0, c0 - d), c1 + d
        ring = int(mask[lo:hi, w_lo:w_hi].sum()) - int(mask[lo:hi, prev_lo:prev_hi].sum())
        out[str(d)] = ring
        prev_lo, prev_hi = w_lo, w_hi
    on_line = int(mask[lo:hi, c0:c1].sum())
    widest = slice(max(0, c0 - PROFILE_BINS_PX[-1]), c1 + PROFILE_BINS_PX[-1])
    rows = mask[lo:hi, widest].any(axis=1)
    nearest = None
    for d in (0,) + PROFILE_BINS_PX:
        if int(mask[lo:hi, max(0, c0 - d):c1 + d].sum()) > 0:
            nearest = d
            break
    return {"on_line": on_line, "by_distance_px": out,
            "span_ratio": round(float(rows.mean()), 4), "nearest_px": nearest}


def _ink_groups(structure: np.ndarray, fenestration: np.ndarray, *, axis: Axis,
                min_run_px: int, min_support: int) -> list[dict[str, Any]]:
    """Every column group of structural ink that behaves like a drawn line.

    ⛔ This is an OBSERVATION, not a wall face: a group may be one thin line or
    a whole solid band.  Which it is, and whether two of them are one wall, is
    decided in ``hypotheses``.
    """
    m = structure if axis == "col" else structure.T
    f = fenestration if axis == "col" else fenestration.T
    keep = vertical_runs_mask(m, min_run_px)
    support = keep.sum(0)
    cols = np.flatnonzero(support >= min_support)
    groups: list[list[int]] = []
    for c in cols:
        if groups and c - groups[-1][-1] <= 1:
            groups[-1].append(int(c))
        else:
            groups.append([int(c)])

    out = []
    for g in groups:
        c0, c1 = g[0], g[-1] + 1
        along = keep[:, g].mean(1) >= FILL_RATIO
        runs, gaps = _raw_runs(along)
        if not runs:
            continue
        per_run = []
        for a, b in runs:
            strip = m[a:b, max(0, c0 - 1):c1 + 1]
            per_run.append(round(float(strip.any(axis=1).mean()), 4))
        gap_rows = []
        for lo, hi in gaps:
            gap_rows.append({
                "lo_px": lo, "hi_px": hi, "len_px": int(hi - lo),
                # ⛔ no class. Three measured families of evidence instead.
                "opening_ink": _profile(f, lo, hi, c0, c1),
                "structure_ink": _profile(m, lo, hi, c0, c1),
            })
        out.append({
            "pos_px": round(float(np.average(g, weights=support[g])), 2),
            "support_cols_px": [c0, c1],
            "width_px": int(c1 - c0),
            "runs_px": runs,
            "gaps": gap_rows,
            "ink_coverage_per_run": per_run,
            "covered_px": int(sum(b - a for a, b in runs)),
            "support_px": int(support[g].sum()),
        })
    return out


def _components(mask: np.ndarray, min_area_px: int) -> list[dict[str, Any]]:
    """Opening-colour connected components, emitted so any window is re-computable."""
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    if n == 0:
        return []
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        area = int((lab[sl] == i).sum())
        if area < min_area_px:
            continue
        out.append({"bbox_px": [int(sl[1].start), int(sl[0].start),
                                int(sl[1].stop), int(sl[0].stop)],
                    "area_px": area})
    out.sort(key=lambda d: -d["area_px"])
    return out


def _chain_zero_px(fit, chain: dict) -> float:
    return fit.origin_px - chain["world_start_mm"] / (chain["direction"] * fit.mm_per_px)


def build(cfg: dict) -> dict:
    a = load_rgb(cfg["image"])
    fams = ink_families(a)
    st = fams["structure"].copy()
    r0, r1, c0, c1 = cfg["drawing_box"]
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    chains = cfg["chains"]
    fits, tick_map = {}, {"x": {}, "y": {}}
    for cid, c in chains.items():
        f = fit_chain(witness_ticks(fams["annotation"], axis=c["axis"], strip=tuple(c["strip"])),
                      c["values_mm"], axis=c["axis"], overall_mm=sum(c["values_mm"]))
        fits[cid] = f
        world = "x" if c["axis"] == "row" else "y"
        for px, cum in zip(f.matched_px, f.cum_mm):
            if px != px:
                continue
            tick_map[world][str(round(px, 1))] = c["world_start_mm"] + c["direction"] * cum
    fx, fy = fits[cfg["primary_x_chain"]], fits[cfg["primary_y_chain"]]
    mmpx = (fx.mm_per_px + fy.mm_per_px) / 2.0
    x_zero = _chain_zero_px(fx, chains[cfg["primary_x_chain"]])
    y_zero = _chain_zero_px(fy, chains[cfg["primary_y_chain"]])

    def to_x(px: float) -> float:
        return round((px - x_zero) * fx.mm_per_px / 1000.0, 4)

    def to_y(px: float) -> float:
        return round((y_zero - px) * fy.mm_per_px / 1000.0, 4)

    face_lines: list[dict[str, Any]] = []
    for axis in ("col", "row"):
        pos_w = to_x if axis == "col" else to_y
        along_w = to_y if axis == "col" else to_x
        for grp in _ink_groups(st, fams["fenestration"], axis=axis,
                               min_run_px=cfg.get("min_run_px", 14),
                               min_support=cfg.get("min_support", 10)):
            for gap in grp["gaps"]:
                lo, hi = sorted((along_w(gap["lo_px"]), along_w(gap["hi_px"])))
                gap["span_m"] = [round(lo, 4), round(hi, 4)]
                gap["len_m"] = round(hi - lo, 4)
            face_lines.append({
                "id": f"L{len(face_lines) + 1:03d}",
                "axis": axis,
                "constant_world_axis": "x" if axis == "col" else "y",
                "pos_px": grp["pos_px"], "pos_m": pos_w(grp["pos_px"]),
                "support_cols_px": grp["support_cols_px"],
                # ⭐ The group's own two edges, in world units. Pure measurement:
                # it is where the ink starts and stops across the line. For a
                # thin stroke the two edges are 1-3 px apart; for a solid filled
                # band (the sm24 dialect) they ARE the wall's two faces. ⛔ Saying
                # which of those it is would be a judgement, so it is not said
                # here -- but withholding the numbers would lose the sm24 wall
                # entirely, which is what "observations must stand alone" means.
                "edges_m": sorted((pos_w(float(grp["support_cols_px"][0])),
                                   pos_w(float(grp["support_cols_px"][1])))),
                "support_width_m": round(grp["width_px"] * mmpx / 1000.0, 4),
                "runs_px": grp["runs_px"],
                "runs_m": [[round(v, 4) for v in sorted((along_w(lo), along_w(hi)))]
                           for lo, hi in grp["runs_px"]],
                "gaps": grp["gaps"],
                "ink_coverage_per_run": grp["ink_coverage_per_run"],
                "covered_px": grp["covered_px"], "support_px": grp["support_px"],
            })

    # ------------------------------------------------------- hypotheses ----
    # ⛔ Everything below is DERIVED and carries its basis. A consumer may drop
    # this whole block and rebuild it from observations + declarations.
    declared_px = [t / mmpx for t in cfg["declared_thickness_mm"]]
    tol_px = cfg.get("thickness_tol_px", 2.0)

    def _tol(t_px: float) -> float:
        return max(tol_px, 0.30 * t_px)

    pairs = []
    for i, A in enumerate(face_lines):
        for j in range(i + 1, len(face_lines)):
            B = face_lines[j]
            if A["axis"] != B["axis"]:
                continue
            d = abs(B["pos_px"] - A["pos_px"])
            hits = [t for t in declared_px if abs(d - t) <= _tol(t)]
            if not hits:
                continue
            # ⭐ distinct support: two readings of ONE stroke are not a wall.
            (a0, a1), (b0, b1) = A["support_cols_px"], B["support_cols_px"]
            if min(a1, b1) > max(a0, b0):
                continue
            ov = 0
            for p in A["runs_px"]:
                for q in B["runs_px"]:
                    ov += max(0, min(p[1], q[1]) - max(p[0], q[0]))
            if ov < cfg.get("min_overlap_px", 10):
                continue
            pairs.append({"face_a": A["id"], "face_b": B["id"],
                          "spacing_px": round(d, 2),
                          "spacing_m": round(d * mmpx / 1000.0, 4),
                          "matched_declared_mm": [round(t * mmpx) for t in hits],
                          "overlap_px": int(ov),
                          "basis": "declared thickness +/- max(2px, 30%), "
                                   "disjoint support columns, overlapping runs"})
    # ⭐ every admissible partner, ⛔ no first-match-and-break
    by_face: dict[str, list[str]] = {}
    for p in pairs:
        by_face.setdefault(p["face_a"], []).append(p["face_b"])
        by_face.setdefault(p["face_b"], []).append(p["face_a"])
    for p in pairs:
        p["admissible_alternatives"] = sorted(
            set(by_face.get(p["face_a"], []) + by_face.get(p["face_b"], []))
            - {p["face_a"], p["face_b"]})

    return {
        "schema": SCHEMA,
        "image": cfg["image"],
        "image_label": cfg.get("image_label"),
        "observations": {
            "calibration": {
                "x": fx.as_dict(), "y": fy.as_dict(),
                "mm_per_px": round(mmpx, 6),
                "cross_axis_relative_deviation":
                    round(abs(fx.mm_per_px - fy.mm_per_px) / mmpx, 6),
                "world_zero_px": [round(x_zero, 3), round(y_zero, 3)],
                "world_zero_source": "chain_fit",
                "profile_bins_px": list(PROFILE_BINS_PX),
                "fill_ratio": FILL_RATIO,
            },
            "ink_dialect": dialect_report(a),
            "face_lines": face_lines,
            "opening_components": _components(fams["fenestration"],
                                              cfg.get("min_area_px", 40)),
            "dimension_witnesses": tick_map,
        },
        "declarations": {
            "thickness_callouts_mm": cfg["declared_thickness_mm"],
            "thickness_callout_note": "from the drawing's own callouts (an OCR product); "
                                      "⛔ compared verbatim, never treated as a measurement",
            "world_zero_px_declared": cfg.get("world_zero_px"),
            "chains": {cid: {k: c[k] for k in ("axis", "values_mm", "world_start_mm",
                                               "direction", "ref_coord_m") if k in c}
                       for cid, c in chains.items()},
            "drawing_box_px": cfg["drawing_box"],
        },
        "hypotheses": {
            "pairs": pairs,
            "note": "⛔ derived, not scored. Rebuildable from observations + declarations: "
                    "pairs = face-line spacings matching a declared callout within "
                    "max(2px,30%), with disjoint support columns and overlapping runs.",
        },
        "ledger": {
            "face_lines": len(face_lines),
            "runs_total": sum(len(f["runs_px"]) for f in face_lines),
            "gaps_total": sum(len(f["gaps"]) for f in face_lines),
            "pairs": len(pairs),
            "faces_in_a_pair": len({x for p in pairs for x in (p["face_a"], p["face_b"])}),
            "opening_components": len(_components(fams["fenestration"],
                                                  cfg.get("min_area_px", 40))),
            "bridging_applied": False,
            "gap_classified": False,
            "pairing_in_observations": False,
        },
    }


def main(cfg_path: str, out_path: str) -> int:
    doc = build(json.loads(Path(cfg_path).read_text()))
    dump(doc, out_path)
    L = doc["ledger"]
    print(f"{Path(cfg_path).stem:16s} face_lines={L['face_lines']:3d} runs={L['runs_total']:4d} "
          f"gaps={L['gaps_total']:4d} pairs={L['pairs']:3d} "
          f"paired_faces={L['faces_in_a_pair']:3d} components={L['opening_components']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
