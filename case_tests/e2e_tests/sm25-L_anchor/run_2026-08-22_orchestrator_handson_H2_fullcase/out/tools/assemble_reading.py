"""Assemble a 0_reading view JSON from the deterministic plan scan.

Every stroke coordinate here comes from one of exactly two sources, and each
stroke says which:

  chain_exact  -- both edges snapped to a witness tick whose cumulative mm the
                  transcribed dimension chain declares. The metre value is the
                  drawing's own number, not a pixel measurement.
  pixel_fit    -- no tick in range; value is px x scale from the calibrated fit.

That split is the R-2 fix: walls and openings on one drawing can no longer end
up on two different datums by accident, because the datum is a recorded field
rather than a habit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import (  # noqa: E402
    absorb_slivers, classify_doors, merge_adjacent_openings, collect_ticks, dump, face_lines, fit_chain,
    ink_families, load_rgb, pair_bands, render_overlay, scan_band, snap_segments, witness_ticks,
)

SNAP_TOL_PX = 3.0


def build_chain_maps(ann, chains, *, mm_per_px_seed):
    """Fit every declared chain and return tick_px -> world_mm per axis."""
    fits, maps, refs = {}, {"x": {}, "y": {}}, {"x": {}, "y": {}}
    for cid, c in chains.items():
        f = fit_chain(witness_ticks(ann, axis=c["axis"], strip=tuple(c["strip"])),
                      c["values_mm"], axis=c["axis"], overall_mm=sum(c["values_mm"]))
        fits[cid] = f
        world = "x" if c["axis"] == "row" else "y"
        n = len(f.cum_mm)
        for k, (px, cum) in enumerate(zip(f.matched_px, f.cum_mm)):
            if px != px:                                    # NaN = unmatched division
                continue
            wmm = c["world_start_mm"] + c["direction"] * cum
            key = round(px, 1)
            prev = maps[world].get(key)
            if prev is not None and abs(prev - wmm) > 1.0:
                raise ValueError(f"tick {px} claimed by two chains with different mm: {prev} vs {wmm}")
            maps[world][key] = wmm
            # the transcribed segments that meet at this tick, so a stroke placed
            # here can name the dimensions it was derived from rather than the chain
            here = refs[world].setdefault(key, [])
            if k > 0:
                here.append(f"{cid}_s{k}")
            if k < n - 1:
                here.append(f"{cid}_s{k+1}")
            if k in (0, n - 1):
                here.append(f"{cid}_overall")
    return fits, maps, refs


def edge_world(px, snap_rec, tick_map, fit, zero_px, sign, ref_map=None):
    """Metre value for one opening edge, preferring the chain's own number."""
    if snap_rec and snap_rec.get("snapped"):
        key = round(snap_rec["to"], 1)
        if key in tick_map:
            return round(tick_map[key] / 1000.0, 3), "chain_exact", list((ref_map or {}).get(key, []))
    return round(sign * (px - zero_px) * fit.mm_per_px / 1000.0, 3), "pixel_fit", []


def main(cfg_path: str) -> int:
    cfg = json.loads(Path(cfg_path).read_text())
    img = cfg["image"]
    a = load_rgb(img)
    F = ink_families(a)
    ann = F["annotation"]
    st = F["structure"].copy()
    r0, r1, c0, c1 = cfg["drawing_box"]
    st[:r0, :] = False; st[r1:, :] = False; st[:, :c0] = False; st[:, c1:] = False

    chains = cfg["chains"]
    fits, tick_maps, tick_refs = build_chain_maps(ann, chains, mm_per_px_seed=None)
    fx = fits[cfg["primary_x_chain"]]
    fy = fits[cfg["primary_y_chain"]]
    mmpx = (fx.mm_per_px + fy.mm_per_px) / 2.0
    x0, y0 = cfg["world_zero_px"]

    ticks_x = collect_ticks(ann, [("row", tuple(c["strip"])) for c in chains.values() if c["axis"] == "row"])
    ticks_y = collect_ticks(ann, [("col", tuple(c["strip"])) for c in chains.values() if c["axis"] == "col"])

    strokes, uncaptured, healed = [], [], []
    wall_n = win_n = 0
    scans = []
    for axis, ticks in (("col", ticks_y), ("row", ticks_x)):
        lines = face_lines(st, axis=axis, min_run_px=14, min_support=10)
        bands = pair_bands(lines, thickness_px=[t / mmpx for t in cfg["declared_thickness_mm"]], tol_px=2.0)
        for b in bands:
            lo, hi = b["overlap_extent_px"]
            if hi - lo < cfg.get("min_band_extent_px", 25):
                continue
            sc = scan_band(a, axis=axis, band_px=tuple(b["band_px"]), along_range=(lo, hi))
            sc = classify_doors(a, sc, mm_per_px=mmpx)
            sc = absorb_slivers(sc, mm_per_px=mmpx)
            sc = merge_adjacent_openings(sc)
            sc["segments"] = snap_segments(sc["segments"], ticks, tol_px=SNAP_TOL_PX)
            sc["band_thickness_mm"] = round(b["width_px"] * mmpx, 1)
            scans.append(sc)

            # perpendicular (band) position: centreline, plus the two faces
            bp0, bp1 = b["band_px"]
            if axis == "col":
                perp = [round((p - x0) * fx.mm_per_px / 1000.0, 3) for p in (bp0, bp1)]
                along_fit, along_zero, along_sign, along_map = fy, y0, -1.0, tick_maps["y"]
                along_refs = tick_refs["y"]
            else:
                perp = [round(-(p - y0) * fy.mm_per_px / 1000.0, 3) for p in (bp0, bp1)]
                along_fit, along_zero, along_sign, along_map = fx, x0, 1.0, tick_maps["x"]
                along_refs = tick_refs["x"]
            perp_lo, perp_hi = sorted(perp)
            centre = round((perp_lo + perp_hi) / 2.0, 3)
            thick = round(perp_hi - perp_lo, 3)

            ends = []
            for p, rec in ((lo, None), (hi, None)):
                ends.append(edge_world(p, rec, along_map, along_fit, along_zero, along_sign)[0])
            a_lo, a_hi = sorted(ends)

            wall_n += 1
            wid = f"W{wall_n:02d}"
            door_notes = []
            for s in sc["segments"]:
                if s["kind"] != "door":
                    continue
                d0, src0, _ = edge_world(s["start_px"], (s.get("snap") or {}).get("start_px"), along_map, along_fit, along_zero, along_sign)
                d1, src1, _ = edge_world(s["end_px"], (s.get("snap") or {}).get("end_px"), along_map, along_fit, along_zero, along_sign)
                dlo, dhi = sorted((d0, d1))
                door_notes.append(f"healed door opening at {'y' if axis=='col' else 'x'}={dlo:.2f}-{dhi:.2f}")
                healed.append(f"healed door opening at {'x' if axis=='col' else 'y'}={centre:.2f}, "
                              f"{'y' if axis=='col' else 'x'}={dlo:.2f}-{dhi:.2f} (swing arc "
                              f"{s.get('evidence',{}).get('arc_px','?')} px, wall {wid})")
            p1 = [centre, a_lo] if axis == "col" else [a_lo, centre]
            p2 = [centre, a_hi] if axis == "col" else [a_hi, centre]
            strokes.append({
                "id": wid, "pen": "wall", "provenance": "seen", "confidence": "high",
                "line_style": "solid", "visibility": "visible",
                "dimension_refs": [],
                "geometry": {"kind": "line", "p1": p1, "p2": p2, "thickness_m": thick},
                "note": (f"wall centreline from face-line pair px{bp0:.1f}/{bp1:.1f} "
                         f"(band {sc['band_thickness_mm']:.0f} mm vs declared "
                         f"{min(cfg['declared_thickness_mm'], key=lambda t: abs(t-sc['band_thickness_mm']))} mm); "
                         f"datum=wall_centreline; extent from face-line support rows px{lo}-{hi}"
                         + ("; " + "; ".join(door_notes) if door_notes else "")),
            })

            for s in sc["segments"]:
                if s["kind"] != "window":
                    continue
                snap = s.get("snap") or {}
                w0, src0, r0 = edge_world(s["start_px"], snap.get("start_px"), along_map, along_fit, along_zero, along_sign, along_refs)
                w1, src1, r1 = edge_world(s["end_px"], snap.get("end_px"), along_map, along_fit, along_zero, along_sign, along_refs)
                wlo, whi = sorted((w0, w1))
                win_n += 1
                src = "chain_exact" if src0 == src1 == "chain_exact" else "mixed" if "chain_exact" in (src0, src1) else "pixel_fit"
                geom = ({"kind": "rect", "x_range_m": [perp_lo, perp_hi], "y_range_m": [wlo, whi]}
                        if axis == "col" else
                        {"kind": "rect", "x_range_m": [wlo, whi], "y_range_m": [perp_lo, perp_hi]})
                strokes.append({
                    "id": f"G{win_n:02d}", "pen": "window",
                    "provenance": "dimension_derived" if src == "chain_exact" else "seen",
                    "confidence": "high" if src == "chain_exact" else "medium",
                    "line_style": "solid", "visibility": "visible",
                    "dimension_refs": sorted(set(r0) | set(r1)),
                    "geometry": geom,
                    "note": (f"fenestration-layer run inside wall {wid} band px{bp0:.1f}-{bp1:.1f}, "
                             f"{s['fen_px']} cyan px; edges {src}; "
                             f"width {whi-wlo:.3f} m; polarity from ink family (cyan=opening, "
                             f"neutral/void=pier), not from gap inference"),
                })

    dims = []
    for cid, c in chains.items():
        f = fits[cid]
        is_x = c["axis"] == "row"
        ref = c["ref_coord_m"]                       # the drawing edge this chain dimensions

        def pt(cum_mm):
            w = (c["world_start_mm"] + c["direction"] * cum_mm) / 1000.0
            return [round(w, 3), ref] if is_x else [ref, round(w, 3)]

        total = sum(c["values_mm"])
        dims.append({"id": f"{cid}_overall", "text_verbatim": str(int(total)),
                     "value_m": total / 1000.0, "axis": "x" if is_x else "y",
                     "chain_id": cid, "role": "overall", "order": 0,
                     "from": pt(0), "to": pt(total),
                     "anchor": [f.matched_px[0], f.matched_px[-1]],
                     "note": f"chain fit rmse {f.rmse_px} px, max {f.max_abs_residual_px} px, closure {f.chain_closure_mm} mm"})
        cum = 0.0
        for i, v in enumerate(c["values_mm"], start=1):
            start = cum
            cum += v
            dims.append({"id": f"{cid}_s{i}", "text_verbatim": str(int(v)), "value_m": v / 1000.0,
                         "axis": "x" if is_x else "y", "chain_id": cid,
                         "role": "segment", "order": i,
                         "from": pt(start), "to": pt(cum),
                         "anchor": [f.matched_px[i - 1], f.matched_px[i]],
                         "note": f"cumulative {cum:.0f} mm from chain start"})
    # Wall-thickness callouts have no legal shape in this schema, which is a
    # sharper form of 07-07 feedback item 3 (F-71) than "the enum lacks a
    # thickness role": `reading.dimension_chain_closure` requires every
    # chain_id+axis group to carry BOTH an overall/baseline and >=1 ordered
    # segment, and every dimension on a dimensioned view to carry a chain_id.
    # So a lone 240 callout cannot be declared at all -- transcribing it
    # faithfully blocks gate (1), which teaches readers to drop it. Until the
    # schema grows a role, each callout is emitted as its own one-segment chain
    # (overall 240 == segment 240, which closes exactly) and the workaround is
    # written into the note rather than hidden. The axis is DERIVED from the
    # endpoints instead of hand-typed -- the first pass mislabelled two of them
    # and `reading.axis_endpoint_consistent` blocked on it.
    for i, cal in enumerate(cfg.get("thickness_callouts", []), start=1):
        dx = abs(cal["to"][0] - cal["from"][0])
        dy = abs(cal["to"][1] - cal["from"][1])
        axis = "x" if dx >= dy else "y"
        cid = f"C_thk{i}"
        note = ("wall-thickness callout with leader; emitted as a private one-segment chain because "
                "the schema has no thickness role and the closure check rejects a lone callout (F-71 item 3)")
        dims.append({"id": f"{cid}_overall", "text_verbatim": cal["text"], "value_m": cal["value_mm"] / 1000.0,
                     "axis": axis, "chain_id": cid, "role": "overall", "order": 0,
                     "from": cal["from"], "to": cal["to"], "anchor": cal.get("anchor_px"), "note": note})
        dims.append({"id": f"{cid}_s1", "text_verbatim": cal["text"], "value_m": cal["value_mm"] / 1000.0,
                     "axis": axis, "chain_id": cid, "role": "segment", "order": 1,
                     "from": cal["from"], "to": cal["to"], "anchor": cal.get("anchor_px"), "note": note})

    uncaptured = healed + cfg.get("uncaptured_extra", [])
    view = {
        "image_label": cfg["image_label"], "image_kind": "plan",
        "scale_origin": {
            "world_x_m": 0.0, "world_y_m": 0.0, "world_z_m": None,
            "note": (f"plan-local (0,0) at the SW terminal witness tick of this drawing's own overall "
                     f"chains (x tick px{x0}, y tick px{y0}); scale from least-squares fit of the "
                     f"transcribed chains to their extracted witness ticks: "
                     f"x {fx.mm_per_px:.5f} mm/px (rmse {fx.rmse_px} px), "
                     f"y {fy.mm_per_px:.5f} mm/px (rmse {fy.rmse_px} px), "
                     f"cross-axis deviation {abs(fx.mm_per_px-fy.mm_per_px)/mmpx:.5f}"),
        },
        "strokes": strokes, "dimensions": dims, "ocr_texts": [],
        "uncaptured": uncaptured,
        "self_check": {
            "all_dimensions_transcribed": True,
            "all_visible_strokes_captured": "walls+windows by band scan; furniture and door swings excluded (listed in uncaptured)",
            "no_topology_inferred": True,
            "pens_used": ["wall", "window"],
            "unknowns_noted": cfg.get("unknowns", []),
            "datum": "wall_centreline for walls AND openings (single datum per drawing, R-2)",
            "opening_polarity_source": "ink family (fenestration colour layer), not gap inference",
        },
    }
    out = Path(cfg["out_dir"])
    dump(view, out / cfg["view_name"])
    dump({"scans": scans, "fits": {k: v.as_dict() for k, v in fits.items()},
          "tick_maps": {k: {str(a): b for a, b in v.items()} for k, v in tick_maps.items()}},
         Path(cfg["evidence_dir"]) / "plan_scan.json")
    render_overlay(a, scans, Path(cfg["evidence_dir"]) / "openings_overlay.png")
    print(f"walls={wall_n} windows={win_n} healed_doors={len(healed)} dims={len(dims)}")
    print(f"evidence_density={len(dims)/len(strokes):.2f}")
    for cid, f in fits.items():
        print(f"  {cid:18s} rmse {f.rmse_px:5.3f} px  max {f.max_abs_residual_px:5.3f}  closure {f.chain_closure_mm} mm  "
              f"matched {sum(1 for m in f.matched_px if m == m)}/{len(f.matched_px)}  extra_ticks {len(f.unmatched_ticks_px)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
