"""As-drawn plan transcription — prototype for the "reading only traces" shape.

⭐ Why this file exists (2026-08-23, user ratified the thorough version):
the previous shape collapsed each wall to ONE centreline with a ``thickness_m``
and took its along-extent as ``[rows.min(), rows.max()+1]``.  Both steps are
judgements, and both produced real errors on sm25 1f:

  * the min/max extent drew a wall straight across a corridor that has no wall
    (measured: grey-ink column coverage 100% / **2.0%** / 98.8% across the three
    stretches) -- a 2.1 m phantom wall that no gate could see;
  * collapsing to a centreline destroys the fact that a wall's two faces can
    have DIFFERENT lengths (exactly what happens at the Z-notch corner), so the
    exterior/interior distinction became underivable downstream.

This module therefore emits, per wall, the two face lines **as drawn**: each
keeps its own continuous runs, and the pair keeps its measured spacing.  It
writes no centreline, no thickness, and no exterior/interior call -- those are
derivations and belong to 1_correction.

⛔ Deliberately NOT here: modulus snapping of the spacing.  The declared values
(240/120) come from the drawing's own callouts, which are an OCR product; the
snap is a conversion and belongs downstream with the rest of them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import (  # noqa: E402
    Axis, collect_ticks, dialect_report, dump, face_lines, fit_chain,
    ink_families, load_rgb, vertical_runs_mask, witness_ticks,
)

# The one threshold in this file, and it is NOT new: 0.60 m is the project's
# already-signed domain lower bound for an opening (the NARROW-OPENING process
# gate, F-73).  A blank stretch at least this long is a real break in the wall;
# anything shorter is recorded as a hairline gap and kept in the ledger rather
# than silently merged away.  Measured gap histogram on sm25 1f shows a clean
# valley here: 5 gaps <= 15 px, 2 in 16..30 px, 34 in 31..60 px.
OPENING_MIN_M = 0.60


def _runs(flags: np.ndarray, *, break_gap_px: float) -> tuple[list[list[int]], list[dict[str, Any]]]:
    """Continuous runs of True, plus every blank gap between them.

    Gaps shorter than ``break_gap_px`` do not split a run (they are anti-alias
    dropouts or another line crossing this one), but they are still reported so
    the choice stays auditable instead of becoming an invisible default.
    """
    idx = np.flatnonzero(flags)
    if idx.size == 0:
        return [], []
    edges = np.flatnonzero(np.diff(idx) > 1)
    raw = []
    start = idx[0]
    for e in edges:
        raw.append([int(start), int(idx[e]) + 1])
        start = idx[e + 1]
    raw.append([int(start), int(idx[-1]) + 1])

    runs: list[list[int]] = []
    gaps: list[dict[str, Any]] = []
    for span in raw:
        if runs:
            gap = span[0] - runs[-1][1]
            gaps.append({"lo_px": runs[-1][1], "hi_px": span[0], "len_px": int(gap),
                         "class": "break" if gap >= break_gap_px else "hairline"})
            if gap < break_gap_px:
                runs[-1][1] = span[1]
                continue
        runs.append(list(span))
    return runs, gaps


# A position along a line counts as inked when at least this fraction of the
# line group's own columns carry ink there. For a two-face-line dialect a group
# is 1-3 px wide, so this is indistinguishable from "any column"; for a solid
# filled band (sm24) a group is ~9 px wide and "any column" would call the band
# present wherever only its edge is drawn -- which is how the first sm24 run
# produced runs that the reverse ledger then measured at 15% ink coverage.
FILL_RATIO = 0.5


def face_line_runs(mask_structure: np.ndarray, *, axis: Axis, min_run_px: int,
                   min_support: int, break_gap_px: float) -> list[dict[str, Any]]:
    """Like ``plan_ink.face_lines`` but keeps each line's ACTUAL runs.

    ``face_lines`` reports ``extent_px = [rows.min(), rows.max()+1]``.  That one
    line is the phantom-wall bug: a face line that stops at a corridor and
    resumes on the far side is reported as one unbroken stretch.
    """
    m = mask_structure if axis == "col" else mask_structure.T
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
        along = keep[:, g].mean(1) >= FILL_RATIO
        runs, gaps = _runs(along, break_gap_px=break_gap_px)
        if not runs:
            continue
        out.append({
            "pos_px": round(float(np.average(g, weights=support[g])), 2),
            "cols_px": [g[0], g[-1] + 1],
            "runs_px": runs,
            "gaps": gaps,
            "covered_px": int(sum(b - a for a, b in runs)),
            "support_px": int(support[g].sum()),
        })
    return out


def opening_runs(fenestration: np.ndarray, *, axis: Axis, cols: tuple[int, int],
                 limit: tuple[int, int], break_gap_px: float) -> list[dict[str, Any]]:
    """Where the fenestration colour layer crosses this wall band.

    ⭐ This is the other half of an as-drawn wall: the face lines stop at an
    opening, and the opening itself is a block of ink on a SEPARATE colour layer
    (F-69: these drawings put doors and windows on their own layer, and the
    project's only mask was blind to it -- measured cyan pixel count 0).
    Transcribing both means a wall's full extent is (drawn runs) U (openings),
    with no healing and no guess about which kind of opening it is.

    ⛔ No door/window call is made here. The evidence that separates them (ink
    reaching beyond the band = a swing arc) is recorded per run so the call can
    be made downstream from data rather than from a threshold buried here.
    """
    c0, c1 = cols
    if axis == "col":
        strip = fenestration[:, c0:c1]
        wide = fenestration[:, max(0, c0 - 12):c1 + 12]
    else:
        strip = fenestration[c0:c1, :].T
        wide = fenestration[max(0, c0 - 12):c1 + 12, :].T
    along = strip.any(1)
    runs, _gaps = _runs(along, break_gap_px=break_gap_px)
    lo_lim, hi_lim = limit
    out = []
    for a, b in runs:
        if b <= lo_lim or a >= hi_lim:
            continue
        inside = int(strip[a:b].sum())
        outside = int(wide[a:b].sum()) - inside
        out.append({"run_px": [a, b], "fen_px_in_band": inside,
                    "fen_px_beyond_band": outside,
                    "beyond_ratio": round(outside / max(1, inside), 3)})
    return out


def _overlap(runs_a: list[list[int]], runs_b: list[list[int]]) -> list[list[int]]:
    out = []
    for a0, a1 in runs_a:
        for b0, b1 in runs_b:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi > lo:
                out.append([lo, hi])
    return sorted(out)


def _tol(t: float, tol_px: float) -> float:
    """Same rule as plan_ink._thickness_tol: scale with the declared value so a
    240 mm wall drawn 8.7 px wide (sm24) and 11 px wide (sm25) share one rule."""
    return max(tol_px, 0.30 * t)


def pair_bands_as_drawn(lines: list[dict[str, Any]], thickness_px: list[float],
                        *, tol_px: float = 2.0, min_overlap_px: int = 10) -> tuple[list[dict], list[int]]:
    """Pair face lines into wall bands, keeping BOTH faces' runs intact."""
    bands: list[dict[str, Any]] = []
    used: set[int] = set()

    # Dialect 2 (sm24): a wall drawn as one solid filled band. The group's own
    # width IS the spacing; there is no second face line to keep.
    for i, a in enumerate(lines):
        w = a["cols_px"][1] - a["cols_px"][0]
        hit = [t for t in thickness_px if abs(w - t) <= _tol(t, tol_px)]
        if hit:
            bands.append({"representation": "solid_fill", "faces": [a],
                          "spacing_px": float(w), "overlap_runs_px": list(a["runs_px"])})
            used.add(i)

    for i, a in enumerate(lines):
        if i in used:
            continue
        for j in range(i + 1, len(lines)):
            if j in used:
                continue
            b = lines[j]
            d = b["pos_px"] - a["pos_px"]
            if d > max(thickness_px) + _tol(max(thickness_px), tol_px):
                break
            if not any(abs(d - t) <= _tol(t, tol_px) for t in thickness_px):
                continue
            ov = _overlap(a["runs_px"], b["runs_px"])
            if sum(hi - lo for lo, hi in ov) < min_overlap_px:
                continue
            bands.append({"representation": "two_face_lines", "faces": [a, b],
                          "spacing_px": round(d, 2), "overlap_runs_px": ov})
            used.update({i, j})
            break
    return bands, [i for i in range(len(lines)) if i not in used]


def build_as_drawn(cfg: dict) -> dict:
    """Transcribe one plan drawing into the as-drawn shape."""
    a = load_rgb(cfg["image"])
    fams = ink_families(a)
    st = fams["structure"].copy()
    r0, r1, c0, c1 = cfg["drawing_box"]
    st[:r0, :] = False
    st[r1:, :] = False
    st[:, :c0] = False
    st[:, c1:] = False

    chains = cfg["chains"]
    fits: dict[str, Any] = {}
    tick_map: dict[str, dict[str, float]] = {"x": {}, "y": {}}
    for cid, c in chains.items():
        f = fit_chain(witness_ticks(fams["annotation"], axis=c["axis"], strip=tuple(c["strip"])),
                      c["values_mm"], axis=c["axis"], overall_mm=sum(c["values_mm"]))
        fits[cid] = f
        world = "x" if c["axis"] == "row" else "y"
        for px, cum in zip(f.matched_px, f.cum_mm):
            if px != px:                                   # NaN = unmatched division
                continue
            tick_map[world][str(round(px, 1))] = c["world_start_mm"] + c["direction"] * cum
    fitx = fits[cfg["primary_x_chain"]]
    fity = fits[cfg["primary_y_chain"]]
    mmpx = (fitx.mm_per_px + fity.mm_per_px) / 2.0
    x_zero, y_zero = cfg["world_zero_px"]

    def to_x(px: float) -> float:
        return round((px - x_zero) * fitx.mm_per_px / 1000.0, 4)

    def to_y(px: float) -> float:
        return round((y_zero - px) * fity.mm_per_px / 1000.0, 4)

    break_gap_px = OPENING_MIN_M * 1000.0 / mmpx
    thick_px = [t / mmpx for t in cfg["declared_thickness_mm"]]

    wall_bands: list[dict[str, Any]] = []
    unpaired: list[dict[str, Any]] = []
    for axis in ("col", "row"):
        # axis="col": vertical face lines, constant world x, running along y.
        pos_to_world = to_x if axis == "col" else to_y
        along_to_world = to_y if axis == "col" else to_x
        lines = face_line_runs(st, axis=axis, min_run_px=cfg.get("min_run_px", 14),
                               min_support=cfg.get("min_support", 10),
                               break_gap_px=break_gap_px)
        bands, loose = pair_bands_as_drawn(lines, thick_px, tol_px=cfg.get("thickness_tol_px", 2.0))
        for b in bands:
            # A solid filled band (sm24 dialect) is detected as ONE group, but the
            # thing the drawing shows is still a wall with two faces -- they are
            # the group's own edges. Synthesising them here keeps one downstream
            # shape for both dialects; without it the outer face of every sm24
            # exterior wall simply has no coordinate (measured: gt's x=0 / y=0
            # outline segments came back NO_LINE_AT_COORDINATE).
            if b["representation"] == "solid_fill":
                src = b["faces"][0]
                c0, c1 = src["cols_px"]
                # pos_px = where the face IS; cols_px = the ink that EVIDENCES it.
                # For two thin face lines the two coincide; for a solid band the
                # evidence is the whole band, so keep it -- sampling a 1 px sliver
                # at the band edge measured 0.0 coverage on ink that is solid.
                b["faces"] = [dict(src, pos_px=float(c0), cols_px=[c0, c1]),
                              dict(src, pos_px=float(c1), cols_px=[c0, c1])]
            faces = []
            for k, f in enumerate(b["faces"]):
                runs_m = [sorted((along_to_world(lo), along_to_world(hi))) for lo, hi in f["runs_px"]]
                faces.append({
                    "role": "a" if k == 0 else "b",
                    "pos_px": f["pos_px"],
                    "cols_px": f["cols_px"],
                    "pos_m": pos_to_world(f["pos_px"]),
                    "runs_px": f["runs_px"],
                    "runs_m": [[round(x, 4) for x in r] for r in runs_m],
                    "gaps": f["gaps"],
                    "covered_px": f["covered_px"],
                })
            band_cols = (min(f["cols_px"][0] for f in b["faces"]),
                         max(f["cols_px"][1] for f in b["faces"]))
            all_runs = [r for f in b["faces"] for r in f["runs_px"]]
            limit = (min(r[0] for r in all_runs), max(r[1] for r in all_runs))
            ops = opening_runs(fams["fenestration"], axis=axis, cols=band_cols,
                               limit=limit, break_gap_px=break_gap_px)
            for o in ops:
                a0, a1 = o["run_px"]
                o["run_m"] = [round(v, 4) for v in sorted((along_to_world(a0), along_to_world(a1)))]
            wall_bands.append({
                "id": f"B{len(wall_bands) + 1:02d}",
                "axis": axis,
                "constant_world_axis": "x" if axis == "col" else "y",
                "representation": b["representation"],
                "faces": faces,
                "spacing_px": b["spacing_px"],
                "spacing_m": round(b["spacing_px"] * mmpx / 1000.0, 4),
                "declared_thickness_candidates_mm": cfg["declared_thickness_mm"],
                "overlap_runs_m": [[round(v, 4) for v in sorted((along_to_world(lo), along_to_world(hi)))]
                                   for lo, hi in b["overlap_runs_px"]],
                "opening_runs": ops,
            })
        unpaired += [{"axis": axis, "pos_px": lines[i]["pos_px"], "pos_m": pos_to_world(lines[i]["pos_px"]),
                      "cols_px": lines[i]["cols_px"], "runs_px": lines[i]["runs_px"],
                      "runs_m": [[round(v, 4) for v in sorted((along_to_world(lo), along_to_world(hi)))]
                                 for lo, hi in lines[i]["runs_px"]],
                      "covered_px": lines[i]["covered_px"]} for i in loose]

    return {
        "schema": "as_drawn_plan_v0",
        "image": cfg["image"],
        "image_label": cfg.get("image_label"),
        "dialect": dialect_report(a),
        "calibration": {
            "x": fitx.as_dict(), "y": fity.as_dict(),
            "mm_per_px": round(mmpx, 6),
            "cross_axis_relative_deviation": round(abs(fitx.mm_per_px - fity.mm_per_px) / mmpx, 6),
            "world_zero_px": [x_zero, y_zero],
            "break_gap_px": round(break_gap_px, 2),
            "break_gap_basis": f"OPENING_MIN_M={OPENING_MIN_M} (signed domain bound, F-73)",
        },
        # Witness ticks are carried as EVIDENCE, not applied. Snapping a face-line
        # end or an opening edge onto a chain tick is a conversion, so it belongs
        # to 1_correction together with modulus snapping -- but correction cannot
        # do it without the witnesses, so the as-drawn layer hands them over.
        "dimension_witnesses": tick_map,
        "wall_bands": wall_bands,
        "unpaired_face_lines": unpaired,
        "ledger": {
            "wall_band_count": len(wall_bands),
            "face_line_count": sum(len(b["faces"]) for b in wall_bands) + len(unpaired),
            "unpaired_count": len(unpaired),
            "break_gap_count": sum(sum(1 for g in f["gaps"] if g["class"] == "break")
                                   for b in wall_bands for f in b["faces"]),
            "opening_run_count": sum(len(b["opening_runs"]) for b in wall_bands),
            "hairline_gap_count": sum(sum(1 for g in f["gaps"] if g["class"] == "hairline")
                                      for b in wall_bands for f in b["faces"]),
        },
    }


if __name__ == "__main__":
    cfg = json.loads(Path(sys.argv[1]).read_text())
    res = build_as_drawn(cfg)
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    dump(res, out)
    led = res["ledger"]
    print(json.dumps({"out": str(out), **led,
                      "cross_axis_dev": res["calibration"]["cross_axis_relative_deviation"],
                      "break_gap_px": res["calibration"]["break_gap_px"]}, ensure_ascii=False))
