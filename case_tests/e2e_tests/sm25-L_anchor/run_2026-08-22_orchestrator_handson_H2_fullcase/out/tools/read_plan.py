"""Driver: run the whole plan-reading SOP over one drawing, deterministically."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from plan_ink import *   # noqa


def read_plan(cfg: dict) -> dict:
    a = load_rgb(cfg["image"])
    F = ink_families(a)
    st = F["structure"].copy()
    (r0, r1, c0, c1) = cfg["drawing_box"]
    st[:r0, :] = False; st[r1:, :] = False; st[:, :c0] = False; st[:, c1:] = False

    dialect = dialect_report(a)
    fitx = fit_chain(witness_ticks(F["annotation"], axis="row", strip=tuple(cfg["x_chain"]["strip"])),
                     cfg["x_chain"]["values_mm"], axis="row", overall_mm=cfg["x_chain"]["overall_mm"])
    fity = fit_chain(witness_ticks(F["annotation"], axis="col", strip=tuple(cfg["y_chain"]["strip"])),
                     cfg["y_chain"]["values_mm"], axis="col", overall_mm=cfg["y_chain"]["overall_mm"])
    ticks_x = collect_ticks(F["annotation"], [("row", tuple(s)) for s in cfg["x_tick_strips"]])
    ticks_y = collect_ticks(F["annotation"], [("col", tuple(s)) for s in cfg["y_tick_strips"]])
    mmpx = (fitx.mm_per_px + fity.mm_per_px) / 2.0
    x_zero, y_zero = cfg["world_zero_px"]        # px of world x=0 and y=0
    to_x = lambda px: round((px - x_zero) * fitx.mm_per_px / 1000.0, 4)
    to_y = lambda px: round((y_zero - px) * fity.mm_per_px / 1000.0, 4)

    thick_px = [t / mmpx for t in cfg["declared_thickness_mm"]]
    findings, unpaired = [], []
    for axis, ticks in (("col", ticks_y), ("row", ticks_x)):
        lines = face_lines(st, axis=axis, min_run_px=cfg.get("min_run_px", 14),
                           min_support=cfg.get("min_support", 10))
        bands = pair_bands(lines, thickness_px=thick_px, tol_px=cfg.get("thickness_tol_px", 2.0))
        paired_pos = {p for b in bands for p in b["band_px"]}
        unpaired += [{"axis": axis, **l} for l in lines if l["pos_px"] not in paired_pos]
        for b in bands:
            lo, hi = b["overlap_extent_px"]
            if hi - lo < cfg.get("min_band_extent_px", 25):
                continue
            sc = scan_band(a, axis=axis, band_px=tuple(b["band_px"]), along_range=(lo, hi))
            sc = classify_doors(a, sc, mm_per_px=mmpx)
            sc["segments"] = snap_segments(sc["segments"], ticks, tol_px=cfg.get("snap_tol_px", 3.0))
            sc = absorb_slivers(sc, mm_per_px=mmpx)
            sc["band_thickness_mm"] = round(b["width_px"] * mmpx, 1)
            findings.append(sc)

    return {
        "image": cfg["image"], "dialect": dialect,
        "calibration": {"x": fitx.as_dict(), "y": fity.as_dict(),
                        "cross_axis_relative_deviation": round(abs(fitx.mm_per_px - fity.mm_per_px) / mmpx, 6),
                        "world_zero_px": [x_zero, y_zero]},
        "tick_counts": {"x": len(ticks_x), "y": len(ticks_y)},
        "findings": findings, "unpaired_face_lines": unpaired,
        "_to_x": to_x, "_to_y": to_y,
    }


if __name__ == "__main__":
    cfg = json.loads(Path(sys.argv[1]).read_text())
    res = read_plan(cfg)
    a = load_rgb(cfg["image"])
    out = Path(cfg["out_dir"])
    render_overlay(a, res["findings"], out / "openings_overlay.png")
    tox, toy = res.pop("_to_x"), res.pop("_to_y")
    dump(res, out / "plan_scan.json")
    W = D = 0
    for f in res["findings"]:
        conv = toy if f["axis"] == "col" else tox
        pos = tox(f["band_px"][0]) if f["axis"] == "col" else toy(f["band_px"][0])
        ops = [s for s in f["segments"] if s["kind"] in ("window", "door")]
        if not ops:
            continue
        print(f"\n{f['axis']} band {'x' if f['axis']=='col' else 'y'}={pos:7.3f}  {f['band_thickness_mm']:5.1f}mm")
        for s in ops:
            c = sorted((conv(s["start_px"]), conv(s["end_px"])))
            sn = s.get("snap", {})
            mk = "".join("S" if sn.get(e, {}).get("snapped") else "." for e in ("start_px", "end_px"))
            print(f"   {s['kind']:6s} {c[0]:8.3f} .. {c[1]:8.3f}  len {c[1]-c[0]:6.3f}  snap[{mk}]  fen={s['fen_px']:4d}")
            W += s["kind"] == "window"; D += s["kind"] == "door"
    print(f"\nTOTAL windows={W} doors={D}   unpaired face lines={len(res['unpaired_face_lines'])}")
