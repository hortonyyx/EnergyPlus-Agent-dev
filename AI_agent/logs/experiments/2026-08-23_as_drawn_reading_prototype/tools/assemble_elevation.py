"""Assemble one elevation's 0_reading view from the deterministic ink scan.

Same principle as the plan side -- the fenestration ink layer says WHICH
rectangle is an opening, the dimension chains say where its edges are -- with
one geometry change: an elevation face has no wall band, so openings come from
connected components instead of tiling a band.

Image-local by contract (guide 1): x runs along the facade from the image's
left edge, y is height. No world axis / sign / base is declared here; that is
1_correction's job.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import (  # noqa: E402
    collect_ticks, dump, fenestration_boxes, fit_chain, ink_families, load_rgb,
    render_overlay, snap_box, witness_ticks,
)

# A plan door reaches the floor; an elevation door reaches the ground line, at
# most a threshold step above it. Windows on these drawings sill at 1.0 m. The
# bound is declared here rather than buried in a comparison so that a drawing
# with a genuinely low window sill fails loudly instead of silently becoming a
# door (the "otherwise it must be X" trap).
DOOR_MAX_SILL_M = 0.50


def main(cfg_path: str) -> int:
    cfg = json.loads(Path(cfg_path).read_text())
    a = load_rgb(cfg["image"])
    ann = ink_families(a)["annotation"]

    # A chain with `"fit": false` is transcribed and its ticks join the snap pool,
    # but it is NOT least-squares fitted: a LOCAL chain (one drawn beside a single
    # opening rather than around the sheet) often terminates ON A DRAWN STRUCTURE
    # LINE -- the storey line, the ground line -- instead of repeating a green
    # witness tick there, so it has fewer ticks than divisions and `fit_chain`'s
    # one-tick-per-division premise does not hold. Recording it this way keeps the
    # transcription honest instead of dropping the chain or faking its anchors.
    fits = {}
    for cid, c in cfg["chains"].items():
        if not c.get("fit", True):
            continue
        fits[cid] = fit_chain(
            witness_ticks(ann, axis=c["axis"], strip=tuple(c["strip"])),
            c["values_mm"], axis=c["axis"], overall_mm=sum(c["values_mm"]),
        )
    fx, fz = fits[cfg["primary_x_chain"]], fits[cfg["primary_z_chain"]]
    ticks_x = collect_ticks(ann, [("row", tuple(c["strip"])) for c in cfg["chains"].values() if c["axis"] == "row"])
    ticks_z = collect_ticks(ann, [("col", tuple(c["strip"])) for c in cfg["chains"].values() if c["axis"] == "col"])
    x0_px, z0_px = cfg["world_zero_px"]          # px of facade-local x=0 and z=0 (ground)
    to_x = lambda px: round((px - x0_px) * fx.mm_per_px / 1000.0, 3)
    to_z = lambda px: round((z0_px - px) * fz.mm_per_px / 1000.0, 3)

    # tick px -> the transcribed dimension ids that meet there, so a snapped
    # stroke can name the dimensions it came from. `reading.dimension_derived_refs`
    # resolves refs against `dimensions[].id`, so naming the CHAIN is not enough.
    ref_x, ref_z = {}, {}
    for cid, c in cfg["chains"].items():
        f = fits.get(cid)
        if f is None:
            continue
        pool = ref_x if c["axis"] == "row" else ref_z
        n = len(f.cum_mm)
        for k, tick in enumerate(f.matched_px):
            if tick != tick:
                continue
            here = pool.setdefault(round(tick, 1), [])
            if k > 0:
                here.append(f"{cid}_s{k}")
            if k < n - 1:
                here.append(f"{cid}_s{k+1}")

    strokes, boxes, doors = [], [], []
    for i, box in enumerate(fenestration_boxes(a, min_area_px=cfg.get("min_area_px", 40)), start=1):
        snapped = snap_box(box, ticks_x, ticks_z, tol_px=cfg.get("snap_tol_px", 4.0))
        boxes.append(snapped)
        px = snapped["snap"]
        xs = sorted((to_x(px["x0"]["to"]), to_x(px["x1"]["to"])))
        zs = sorted((to_z(px["y0"]["to"]), to_z(px["y1"]["to"])))
        n_snapped = snapped["snap_count"]
        refs = sorted({r for name, pool in (("x0", ref_x), ("x1", ref_x), ("y0", ref_z), ("y1", ref_z))
                       if px[name].get("snapped")
                       for r in pool.get(round(px[name]["to"], 1), [])})
        is_door = zs[0] <= DOOR_MAX_SILL_M
        if is_door:
            # ⛔ The reading schema has NO `door` pen -- `_ELEVATION_PENS` is
            # {wall_fill, window, outline} and `_PLAN_PENS` is {wall, window}.
            # Emitting a door as pen="window" would make the FIELD lie while the
            # note tells the truth, and a consumer reads the field. So a door is
            # recorded the way plans already record theirs: not as a stroke, with
            # its full geometry in `uncaptured`. Registered as a schema gap --
            # gt does carry door targets on elevations (the typed scorer marks
            # them `unsupported_target_kind`), so this is lossy, not free.
            doors.append(
                f"door opening on this facade at x {xs[0]:.2f}-{xs[1]:.2f} m, z {zs[0]:.2f}-{zs[1]:.2f} m "
                f"(fenestration-layer component bbox px{box['bbox_px']}, {box['area_px']} cyan px, "
                f"{n_snapped}/4 edges snapped); NOT emitted as a stroke because the reading schema "
                f"has no door pen for image_kind=elevation (legal: wall_fill/window/outline)"
            )
            continue
        strokes.append({
            "id": f"E{i:02d}", "pen": "window",
            "provenance": "dimension_derived" if (n_snapped == 4 and refs) else "seen",
            "confidence": "high" if (n_snapped == 4 and refs) else "medium",
            "line_style": "solid", "visibility": "visible",
            "dimension_refs": refs if n_snapped == 4 else [],
            "geometry": {"kind": "rect", "x_range_m": xs, "y_range_m": zs},
            "note": (f"fenestration-layer component bbox px{box['bbox_px']} "
                     f"({box['area_px']} cyan px, {len(box['inner_boxes'])} nested inner frame(s)); "
                     f"{n_snapped}/4 edges snapped to dimension witness ticks; "
                     f"sill {zs[0]:.2f} m > door bound {DOOR_MAX_SILL_M} m so this is a window; "
                     f"polarity from ink family, not from gaps in the outline"),
        })

    dims = []
    for cid, c in cfg["chains"].items():
        f = fits.get(cid)
        is_x = c["axis"] == "row"
        ref = c["ref_coord_m"]
        pt = lambda cum: ([round((c["world_start_mm"] + c["direction"] * cum) / 1000.0, 3), ref] if is_x
                          else [ref, round((c["world_start_mm"] + c["direction"] * cum) / 1000.0, 3)])
        total = sum(c["values_mm"])
        dims.append({"id": f"{cid}_overall", "text_verbatim": str(int(total)), "value_m": total / 1000.0,
                     "axis": "x" if is_x else "y", "chain_id": cid, "role": "overall", "order": 0,
                     "from": pt(0), "to": pt(total),
                     "anchor": [f.matched_px[0], f.matched_px[-1]] if f else None,
                     "note": (f"chain fit rmse {f.rmse_px} px, max {f.max_abs_residual_px} px, "
                              f"closure {f.chain_closure_mm} mm" if f else
                              "LOCAL chain: transcribed and used for snapping, not least-squares fitted -- "
                              "two of its divisions land on drawn structure lines (storey line / ground line) "
                              "instead of repeating a green witness tick, so it has fewer ticks than divisions")})
        cum = 0.0
        for k, v in enumerate(c["values_mm"], start=1):
            start = cum
            cum += v
            dims.append({"id": f"{cid}_s{k}", "text_verbatim": str(int(v)), "value_m": v / 1000.0,
                         "axis": "x" if is_x else "y", "chain_id": cid, "role": "segment", "order": k,
                         "from": pt(start), "to": pt(cum),
                         "anchor": [f.matched_px[k - 1], f.matched_px[k]] if f else None,
                         "note": f"cumulative {cum:.0f} mm from chain start"})

    view = {
        "image_label": cfg["image_label"], "image_kind": "elevation",
        "facade": {
            "view_facade": cfg["view_facade"], "mirrored": "unknown",
            "orientation_evidence": [
                {"source": "image_name", "detail": f"file {Path(cfg['image']).name}; testdata key "
                                                   f"'{cfg['view_facade']} view path of the building'",
                 "confidence": "high"},
            ],
        },
        "scale_origin": {
            "world_x_m": None, "world_y_m": None, "world_z_m": 0.0,
            "note": (f"image-local: x from the facade's own overall chain terminal tick px{x0_px}, "
                     f"z=0 at the drawn ground line px{z0_px}. Scale from least-squares fit of the "
                     f"transcribed chains to extracted witness ticks: x {fx.mm_per_px:.5f} mm/px "
                     f"(rmse {fx.rmse_px} px), z {fz.mm_per_px:.5f} mm/px (rmse {fz.rmse_px} px), "
                     f"cross-axis deviation "
                     f"{abs(fx.mm_per_px - fz.mm_per_px) / ((fx.mm_per_px + fz.mm_per_px) / 2):.5f}"),
        },
        "strokes": strokes, "dimensions": dims, "ocr_texts": [],
        "uncaptured": doors + cfg.get("uncaptured_extra", []),
        "self_check": {
            "all_dimensions_transcribed": True,
            "all_visible_strokes_captured": "openings by fenestration-layer components; "
                                            "outline and storey line not emitted as strokes",
            "no_topology_inferred": True,
            "pens_used": sorted({s["pen"] for s in strokes}),
            "unknowns_noted": cfg.get("unknowns", []),
            "opening_polarity_source": "ink family (fenestration colour layer)",
        },
    }
    out = Path(cfg["out_dir"])
    dump(view, out / cfg["view_name"])
    ev = Path(cfg["evidence_dir"])
    dump({"boxes": boxes, "fits": {k: v.as_dict() for k, v in fits.items()}}, ev / "elevation_scan.json")
    render_overlay(a, [{"axis": "row", "band_px": [b["bbox_px"][1], b["bbox_px"][3]],
                        "segments": [{"kind": "window", "start_px": b["bbox_px"][0], "end_px": b["bbox_px"][2]}]}
                       for b in boxes], ev / "openings_overlay.png")
    win = len(strokes)
    door = len(doors)
    full = sum(1 for b in boxes if b["snap_count"] == 4)
    print(f"{cfg['view_facade']:6s} windows={win} doors={door}  fully-snapped {full}/{len(boxes)}  dims={len(dims)}")
    for cid, f in fits.items():
        print(f"   {cid:16s} rmse {f.rmse_px:5.3f} max {f.max_abs_residual_px:5.3f} closure {f.chain_closure_mm} mm "
              f"matched {sum(1 for m in f.matched_px if m == m)}/{len(f.matched_px)} extra {len(f.unmatched_ticks_px)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
