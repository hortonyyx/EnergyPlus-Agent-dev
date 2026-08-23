"""As-drawn ELEVATION transcription — the facade half of the as-drawn shape.

⭐ Why this file exists (2026-08-23, P-6): the plan side got the as-drawn
treatment first because that is where the damage was (three real errors, all
from collapsing two face lines into one centreline).  The elevation side was
never tried, and plan.md §五 recorded that it needs three changes.  All three
are here, and each removes a JUDGEMENT from reading rather than adding a
capability:

  1. **No snapping.**  ``assemble_elevation.py`` snaps every opening edge onto
     the nearest dimension witness tick and emits only the snapped number.
     Snapping is a conversion, so it belongs to 1_correction -- but correction
     cannot do it without the witnesses, so both the raw pixel measurement and
     the tick evidence (which tick, how far, which dimension ids meet there)
     are handed over.
  2. **No door/window call.**  ``assemble_elevation.py`` carries
     ``DOOR_MAX_SILL_M = 0.50`` and decides.  On sm25 that call was RIGHT and
     still cost three doors, because the reading schema has no ``door`` pen so
     the three correctly-measured doors went into ``uncaptured``.  Here every
     opening is an ``opening``; the measurements that separate the two kinds
     (sill height, whether the ink reaches the structure line below it) are
     recorded per opening so the call is made downstream from data.
  3. **Outline / storey line / depth step line are first class.**  They were
     ``uncaptured`` prose.  They are ordinary structure lines, so they are
     scanned by the SAME code the plan side uses for wall faces, keeping each
     line's real continuous runs.  ⛔ They are NOT named here -- "this one is
     the ground line" is a judgement; their coordinates are not.

Image-local by contract: x runs along the facade from the drawing's own x=0
witness, z is height above the drawn ground line.  No world axis, no sign, no
mirroring call -- 1_correction's job, exactly as on the plan side.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import (  # noqa: E402
    dialect_report, dump, fenestration_boxes, fit_chain, ink_families,
    load_rgb, witness_ticks,
)
from as_drawn import OPENING_MIN_M, face_line_runs  # noqa: E402

# A structure line has to carry this much ink before it is a line rather than an
# arrowhead or a tick that leaked into the structural colour.  Measured on the
# four sm25 elevations: the real lines (outline, storey, ground, depth step)
# carry 470-1480 px; the leaked marks carry 20-54.  The floor sits in that gap
# and is reported in the ledger so a drawing whose lines are shorter than this
# is visible rather than silently empty.
MIN_LINE_PX = 120


def _chain_zero_px(fit, chain: dict) -> float:
    """Pixel where this chain's world coordinate is 0. See as_drawn.build_as_drawn."""
    return fit.origin_px - chain["world_start_mm"] / (chain["direction"] * fit.mm_per_px)


def _nearest(ticks: list[float], px: float) -> tuple[float | None, float]:
    if not ticks:
        return None, float("inf")
    t = min(ticks, key=lambda v: abs(v - px))
    return t, abs(t - px)


def build_as_drawn_elevation(cfg: dict) -> dict:
    a = load_rgb(cfg["image"])
    fams = ink_families(a)
    ann, st, fen = fams["annotation"], fams["structure"], fams["fenestration"]

    chains = cfg["chains"]
    fits: dict[str, Any] = {}
    tick_map: dict[str, dict[str, float]] = {"x": {}, "z": {}}
    refs: dict[str, dict[float, list[str]]] = {"x": {}, "z": {}}
    for cid, c in chains.items():
        if not c.get("fit", True):
            continue
        f = fit_chain(witness_ticks(ann, axis=c["axis"], strip=tuple(c["strip"])),
                      c["values_mm"], axis=c["axis"], overall_mm=sum(c["values_mm"]))
        fits[cid] = f
        world = "x" if c["axis"] == "row" else "z"
        n = len(f.cum_mm)
        for k, (px, cum) in enumerate(zip(f.matched_px, f.cum_mm)):
            if px != px:                                   # NaN = unmatched division
                continue
            tick_map[world][str(round(px, 1))] = c["world_start_mm"] + c["direction"] * cum
            here = refs[world].setdefault(round(px, 1), [])
            if k > 0:
                here.append(f"{cid}_s{k}")
            if k < n - 1:
                here.append(f"{cid}_s{k+1}")

    fitx, fitz = fits[cfg["primary_x_chain"]], fits[cfg["primary_z_chain"]]
    mmpx = (fitx.mm_per_px + fitz.mm_per_px) / 2.0
    x_zero = _chain_zero_px(fitx, chains[cfg["primary_x_chain"]])
    z_zero = _chain_zero_px(fitz, chains[cfg["primary_z_chain"]])
    declared = cfg.get("world_zero_px")
    crosscheck = None
    if declared is not None:
        crosscheck = {"declared_px": list(declared),
                      "derived_px": [round(x_zero, 3), round(z_zero, 3)],
                      "delta_px": [round(declared[0] - x_zero, 3),
                                   round(declared[1] - z_zero, 3)],
                      "delta_mm": [round((declared[0] - x_zero) * fitx.mm_per_px, 1),
                                   round((declared[1] - z_zero) * fitz.mm_per_px, 1)],
                      "source": "chain_fit"}

    def to_x(px: float) -> float:
        return round((px - x_zero) * fitx.mm_per_px / 1000.0, 4)

    def to_z(px: float) -> float:
        return round((z_zero - px) * fitz.mm_per_px / 1000.0, 4)

    ticks_x = sorted(float(k) for k in tick_map["x"])
    ticks_z = sorted(float(k) for k in tick_map["z"])
    break_gap_px = OPENING_MIN_M * 1000.0 / mmpx

    # ---- structure lines ---------------------------------------------------
    # The declared chain strips are annotation territory; excluding them keeps
    # arrowheads and tick serifs that bleed into the structural colour out of
    # the line scan.  This is a DECLARATION (the strips are already in the cfg),
    # not a new eyeballed window.
    scan = st.copy()
    for c in chains.values():
        lo, hi = c["strip"]
        if c["axis"] == "row":
            scan[lo:hi, :] = False
        else:
            scan[:, lo:hi] = False

    structure_lines = []
    for axis, pos_to_world, along_to_world in (("col", to_x, to_z), ("row", to_z, to_x)):
        found = face_line_runs(scan, axis=axis, min_run_px=cfg.get("min_run_px", 14),
                               min_support=cfg.get("min_support", 10),
                               break_gap_px=break_gap_px)
        kept = [l for l in found if l["covered_px"] >= MIN_LINE_PX]
        widest = max((l["covered_px"] for l in kept), default=1)
        for l in sorted(kept, key=lambda d: d["pos_px"]):
            runs_m = [sorted((along_to_world(lo), along_to_world(hi))) for lo, hi in l["runs_px"]]
            structure_lines.append({
                "id": f"S{len(structure_lines) + 1:02d}",
                "axis": axis,
                # ⛔ deliberately no name. "ground line" / "storey line" /
                # "depth step" are identifications, and identification is
                # 1_correction's job. What is measured is where it is and how
                # far it runs.
                "constant_quantity": "x" if axis == "col" else "z",
                "pos_px": l["pos_px"], "pos_m": pos_to_world(l["pos_px"]),
                "cols_px": l["cols_px"],
                "runs_px": l["runs_px"],
                "runs_m": [[round(v, 4) for v in r] for r in runs_m],
                "gaps": l["gaps"],
                "covered_px": l["covered_px"],
                "span_ratio": round(l["covered_px"] / widest, 3),
            })

    # ---- openings ----------------------------------------------------------
    lines_below = sorted((l for l in structure_lines if l["axis"] == "row"),
                         key=lambda d: d["pos_px"])
    openings = []
    for i, box in enumerate(fenestration_boxes(a, min_area_px=cfg.get("min_area_px", 40)), start=1):
        x0, y0, x1, y1 = box["bbox_px"]
        xs = sorted((to_x(x0), to_x(x1)))
        zs = sorted((to_z(y0), to_z(y1)))
        witness = {}
        for name, px, pool, tk, m in (("x0", x0, "x", ticks_x, fitx.mm_per_px),
                                      ("x1", x1, "x", ticks_x, fitx.mm_per_px),
                                      ("z_low", y1, "z", ticks_z, fitz.mm_per_px),
                                      ("z_high", y0, "z", ticks_z, fitz.mm_per_px)):
            t, d = _nearest(tk, px)
            witness[name] = {"measured_px": px, "nearest_tick_px": t,
                             "distance_px": round(d, 2) if t is not None else None,
                             "distance_mm": round(d * m, 1) if t is not None else None,
                             "dimension_refs": refs[pool].get(round(t, 1), []) if t is not None else []}
        # Door-vs-window EVIDENCE, not the call. On an elevation the thing that
        # separates them is that a door meets the line the building stands on;
        # measure the gap to the nearest horizontal structure line below the
        # opening and hand the number over.
        below = [l for l in lines_below if l["pos_px"] >= y1 - 1]
        gap_px = (below[0]["pos_px"] - y1) if below else None
        openings.append({
            "id": f"O{i:02d}",
            "bbox_px": box["bbox_px"], "area_px": box["area_px"],
            "inner_frames": len(box["inner_boxes"]),
            # ⭐ RAW measurement. Snapping to the witness ticks below is a
            # conversion and is NOT applied here (see module docstring).
            "x_range_m": xs, "z_range_m": zs,
            "width_m": round(xs[1] - xs[0], 4), "height_m": round(zs[1] - zs[0], 4),
            "edge_witnesses": witness,
            "line_below_px": below[0]["id"] if below else None,
            "gap_to_line_below_px": round(gap_px, 2) if gap_px is not None else None,
            "gap_to_line_below_m": round(gap_px * fitz.mm_per_px / 1000.0, 4) if gap_px is not None else None,
        })

    fen_pct = 100.0 * fen.sum() / max(1, fams["ink"].sum())
    return {
        "schema": "as_drawn_elevation_v0",
        "image": cfg["image"],
        "image_label": cfg.get("image_label"),
        "facade_label": cfg.get("view_facade"),
        "dialect": dialect_report(a),
        "calibration": {
            "x": fitx.as_dict(), "z": fitz.as_dict(),
            "mm_per_px": round(mmpx, 6),
            "cross_axis_relative_deviation": round(abs(fitx.mm_per_px - fitz.mm_per_px) / mmpx, 6),
            "world_zero_px": [round(x_zero, 3), round(z_zero, 3)],
            "world_zero_source": "chain_fit",
            "world_zero_crosscheck": crosscheck,
            "break_gap_px": round(break_gap_px, 2),
            "min_line_px": MIN_LINE_PX,
        },
        "dimension_witnesses": tick_map,
        "structure_lines": structure_lines,
        "openings": openings,
        "ledger": {
            "structure_lines": len(structure_lines),
            "openings": len(openings),
            "opening_polarity_source": "fenestration colour layer",
            # Same explicit-downgrade rule as F-69: a drawing with no separate
            # opening colour gets told so, not guessed at.
            "polarity_status": "measured" if fen_pct >= 1.0 else "polarity_ambiguous",
            "fenestration_pct_of_ink": round(fen_pct, 2),
            "snapping_applied": False,
            "door_window_classified": False,
            "chain_fits": {k: {"rmse_px": v.rmse_px, "max_abs_residual_px": v.max_abs_residual_px,
                               "chain_closure_mm": v.chain_closure_mm} for k, v in fits.items()},
        },
    }


def main(cfg_path: str, out_path: str) -> int:
    cfg = json.loads(Path(cfg_path).read_text())
    doc = build_as_drawn_elevation(cfg)
    dump(doc, out_path)
    led = doc["ledger"]
    cc = doc["calibration"]["world_zero_crosscheck"]
    print(f"{doc['facade_label']:6s} lines={led['structure_lines']:2d} openings={led['openings']:2d} "
          f"polarity={led['polarity_status']} zero_delta_px={cc['delta_px'] if cc else None}")
    for l in doc["structure_lines"]:
        if l["span_ratio"] >= 0.5:
            print(f"    {l['id']} {l['axis']} {l['constant_quantity']}={l['pos_m']:8.3f} m "
                  f"covered={l['covered_px']:5d} span_ratio={l['span_ratio']:.2f} runs={len(l['runs_px'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
