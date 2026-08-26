"""⭐⭐ Parameter-FREE holdout for the judge-side raster affine (the authoritative run).

Same claim as ``probe_extent_holdout.py``, but with the free parameter removed.

⚠️ Why that mattered: the threshold version's answer MOVES with the threshold
(max|Δ| = 2.38 px at tol=40, 0.66 px at tol=90, nonsense at tol=10).  Picking the
tolerance that gives the prettiest number is exactly
[[acceptance-bar-must-not-be-written-from-the-result]].  So this version has no
threshold at all: every pixel is assigned to the NEAREST colour in a palette that
the DRAWING ITSELF declares (the DXF layer table) plus black background.

Holdout property (sol 2026-08-27 §C): the manifest's plan affine was fitted from
``WALL``-layer line peaks only.  The features measured here are on
``WINDOW`` / ``E_WINDOW`` / ``LVTRY`` — never seen by that fit.

⛔ What it still does NOT measure:
  * EXTENTS only (4 numbers per group) -> bounds a global translation+scale error,
    blind to local distortion;
  * ink extent vs geometric extent differ by ~half a line width, which is the SAME
    ORDER as the residual -> this method cannot resolve below ~0.5 px.  Read the
    result as "indistinguishable from perfect at this method's resolution", ⛔ not
    as "the affine is accurate to 0.66 px".
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/manifest.json"
DXF = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
CASE_DATA = REPO / "case_tests/e2e_tests/sm25-L_anchor/case_data"
# every colour the DXF layer table declares, + the black page. ⛔ nothing invented.
PALETTE = {"bg": (0, 0, 0), "white": (255, 255, 255), "wall": (192, 192, 192),
           "window": (0, 255, 255), "door": (255, 0, 255), "dim": (0, 255, 0),
           "edge": (63, 0, 255)}
GROUPS = (("window", ("WINDOW", "E_WINDOW")), ("door", ("LVTRY",)))


def inv(a, x, y):
    det = a["m00"] * a["m11"] - a["m01"] * a["m10"]
    dx, dy = x - a["m02"], y - a["m12"]
    return ((a["m11"] * dx - a["m01"] * dy) / det,
            (-a["m10"] * dx + a["m00"] * dy) / det)


def main() -> int:
    import numpy as np, ezdxf
    from ezdxf import bbox
    from PIL import Image
    man = json.loads(MANIFEST.read_text())
    mpu = man["metres_per_unit"]
    ro = {r["view_id"]: r for r in man["raster_overlays"]}
    views = {v["id"]: v for v in man["views"] if v["kind"] == "plan"}
    msp = ezdxf.readfile(DXF).modelspace()
    names = list(PALETTE)
    pal = np.array([PALETTE[n] for n in names])
    rows = []
    for vid, view in views.items():
        b, box = ro[vid], view["clip_box_dxf"]
        im = np.asarray(Image.open(CASE_DATA / b["source_label"]).convert("RGB")).astype(np.int16)
        label = ((im[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1).argmin(-1)
        mpp = abs(b["pixel_to_source_m"]["m00"]) * 1000
        for group, layers in GROUPS:
            mask = label == names.index(group)
            ys, xs = np.nonzero(mask)
            ents = [e for e in msp.query("INSERT") if e.dxf.layer in layers
                    and box["xmin"] <= float(e.dxf.insert.x) <= box["xmax"]
                    and box["ymin"] <= float(e.dxf.insert.y) <= box["ymax"]]
            ex = bbox.extents(ents, cache=bbox.Cache(), fast=False)
            c = [inv(b["pixel_to_source_m"], X * mpu, Y * mpu)
                 for X, Y in ((ex.extmin.x, ex.extmin.y), (ex.extmax.x, ex.extmax.y))]
            px0, px1 = sorted([c[0][0], c[1][0]]); py0, py1 = sorted([c[0][1], c[1][1]])
            delta = {"L": round(float(xs.min() - px0), 2), "R": round(float(xs.max() - px1), 2),
                     "T": round(float(ys.min() - py0), 2), "B": round(float(ys.max() - py1), 2)}
            m = max(abs(v) for v in delta.values())
            rows.append({"view": vid, "group": group, "n_blocks": len(ents),
                         "classified_px": int(mask.sum()), "mm_per_px": round(mpp, 2),
                         "delta_px": delta, "max_abs_delta_px": round(m, 2),
                         "max_abs_delta_mm": round(m * mpp, 1)})
            print(json.dumps(rows[-1], ensure_ascii=False))
    Path(__file__).with_name("palette_holdout.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
