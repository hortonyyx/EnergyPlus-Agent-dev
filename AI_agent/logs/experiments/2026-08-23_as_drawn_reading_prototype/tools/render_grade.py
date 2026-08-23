"""Human-review grade panel for an as-drawn reading.

The machine checks need no picture; a human reviewing or overruling them does.
This renders, ON THE ORIGINAL DRAWING, three things a reviewer has to be able to
see at a glance:

  1. what the reading CLAIMED   -- every transcribed face-line run;
  2. what the answer WANTED     -- every gt target, coloured by whether the
     reading can still reconstruct it;
  3. where the reading claimed ink that is not there -- the multi-draw case,
     which is invisible in any "does it look about right" eyeball check because
     a phantom stroke lies along the same axis as real walls.

⛔ It is a VIEW, never a source of score. Every number printed here comes from
the two JSON reports; nothing is recomputed for the picture.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

DIM = 0.34                      # background drawing, dimmed so overlays read
C_OK = (60, 220, 120)           # gt target the reading can reconstruct
C_MISS = (255, 70, 70)          # gt target it cannot
C_CLAIM = (90, 190, 255)        # a transcribed face-line run
C_PHANTOM = (255, 0, 220)       # a run whose ink coverage failed the ledger
C_OPEN = (255, 210, 40)         # transcribed opening ink
C_GAP = (255, 140, 0)           # a break gap (doorway / opening in the wall)


def _px_of(doc: dict):
    """world metres -> pixel, inverting the document's own calibration."""
    cal = doc["calibration"]
    x0, y0 = cal["world_zero_px"]
    mmx = cal["x"]["mm_per_px"]
    mmy = cal["y"]["mm_per_px"]
    return (lambda xm: x0 + xm * 1000.0 / mmx,
            lambda ym: y0 - ym * 1000.0 / mmy)


def render(doc_path: str, checks_path: str, recon_path: str, floor: str, out_path: str) -> dict:
    doc = json.loads(Path(doc_path).read_text())
    checks = json.loads(Path(checks_path).read_text())
    recon = json.loads(Path(recon_path).read_text()) if recon_path != "-" else None

    base = Image.open(doc["image"]).convert("RGB")
    dark = Image.eval(base, lambda v: int(v * DIM))
    im = dark.convert("RGB")
    d = ImageDraw.Draw(im)
    to_x, to_y = _px_of(doc)

    bad = {(v["band"], v["face"], tuple(v["run_px"]))
           for v in checks["checks"][0].get("violations", [])}

    # --- layer 1: what the reading claimed -------------------------------
    claimed = phantom = gaps = opens = 0
    for band in doc["wall_bands"]:
        vertical = band["axis"] == "col"
        for face in band["faces"]:
            p = face["pos_px"]
            for run in face["runs_px"]:
                key = (band["id"], face["role"], tuple(run))
                col = C_PHANTOM if key in bad else C_CLAIM
                phantom += key in bad
                claimed += 1
                if vertical:
                    d.line([(p, run[0]), (p, run[1])], fill=col, width=2)
                else:
                    d.line([(run[0], p), (run[1], p)], fill=col, width=2)
            for g in face["gaps"]:
                if g["class"] != "break":
                    continue
                gaps += 1
                if vertical:
                    d.line([(p, g["lo_px"]), (p, g["hi_px"])], fill=C_GAP, width=2)
                else:
                    d.line([(g["lo_px"], p), (g["hi_px"], p)], fill=C_GAP, width=2)
        lo = min(f["cols_px"][0] for f in band["faces"])
        hi = max(f["cols_px"][1] for f in band["faces"])
        for o in band["opening_runs"]:
            a, b = o["run_px"]
            opens += 1
            box = [(lo, a), (hi, b)] if band["axis"] == "col" else [(a, lo), (b, hi)]
            d.rectangle([min(box[0][0], box[1][0]), min(box[0][1], box[1][1]),
                         max(box[0][0], box[1][0]), max(box[0][1], box[1][1])],
                        outline=C_OPEN, width=2)

    # --- layer 2: what the answer wanted ---------------------------------
    ok = miss = 0
    if recon:
        for row in recon["rows"]:
            if row["floor"] != floor:
                continue
            good = row["verdict"] == "OK"
            ok += good
            miss += not good
            col = C_OK if good else C_MISS
            const, (lo, hi) = row["const"], row["span"]
            if not row["horizontal"]:      # constant x, spans world y
                x = to_x(const)
                d.line([(x, to_y(lo)), (x, to_y(hi))], fill=col, width=5)
            else:
                y = to_y(const)
                d.line([(to_x(lo), y), (to_x(hi), y)], fill=col, width=5)

    # --- caption ---------------------------------------------------------
    lines = [
        f"AS-DRAWN GRADE  {Path(doc['image']).name}   floor {floor}",
        f"reading claimed: {claimed} face-line runs   openings {opens}   break gaps {gaps}",
        f"phantom runs (ink ledger red): {phantom}",
    ]
    for c in checks["checks"]:
        lines.append(f"  [{c['status']:>8}] {c['check']}"
                     + (f"  worst_cov={c['worst_coverage']}" if "worst_coverage" in c else "")
                     + (f"  unclaimed={c['unclaimed_pct']}%" if "unclaimed_pct" in c else ""))
    if recon:
        lines.append(f"gt targets on this floor: {ok} reconstructible / {miss} not")
    pad = 16 * len(lines) + 14
    canvas = Image.new("RGB", (im.width, im.height + pad), (16, 16, 20))
    canvas.paste(im, (0, 0))
    dd = ImageDraw.Draw(canvas)
    for i, t in enumerate(lines):
        dd.text((10, im.height + 6 + 16 * i), t, fill=(235, 235, 235))
    key = [("gt OK", C_OK), ("gt MISS", C_MISS), ("claimed", C_CLAIM),
           ("PHANTOM", C_PHANTOM), ("opening", C_OPEN), ("break gap", C_GAP)]
    x = im.width - 110
    for i, (lab, col) in enumerate(key):
        dd.rectangle([x, 8 + 16 * i, x + 12, 20 + 16 * i], fill=col)
        dd.text((x + 18, 8 + 16 * i), lab, fill=(235, 235, 235))
    canvas.save(out_path)
    return {"out": out_path, "claimed_runs": claimed, "phantom_runs": phantom,
            "openings": opens, "break_gaps": gaps, "gt_ok": ok, "gt_miss": miss}


if __name__ == "__main__":
    print(json.dumps(render(*sys.argv[1:6]), ensure_ascii=False))
