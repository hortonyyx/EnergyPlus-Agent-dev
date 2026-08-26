"""⭐ HOLDOUT for the judge-side raster affine — extent form (the one that worked).

Claim under test (sol 2026-08-27 §C): ``GtExtractionManifestV1.raster_overlays[]
.pixel_to_source_m`` is a ruler the JUDGE owns, independent of the reading product.

Why the features here are a real holdout: the manifest's plan affine was fitted from
``WALL``-layer line peaks only (2026-08-20 build_request.py, RANSAC).  These features
live on ``WINDOW`` / ``E_WINDOW`` / ``LVTRY``, and their colours are declared BY THE
DRAWING ITSELF in the DXF layer table (cyan 0,255,255 / magenta 255,0,255) — so
detecting them needs no product input, no gt coordinate, and no fitting.

⛔ What this does NOT measure: it compares EXTENTS (4 numbers per group), which bounds
a global translation+scale error but is blind to local distortion.  A per-feature
residual needs a matcher that survives "block base point != ink centroid" — the first
attempt (``probe_holdout2.py``) died exactly there; see README.
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/manifest.json"
DXF = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
CASE_DATA = REPO / "case_tests/e2e_tests/sm25-L_anchor/case_data"
GROUPS = (("window", ("WINDOW", "E_WINDOW"), (0, 255, 255)),
          ("door", ("LVTRY",), (255, 0, 255)))
TOL = 40   # declared per-channel colour tolerance; swept in the README


def inv(a, x, y):
    det = a["m00"] * a["m11"] - a["m01"] * a["m10"]
    dx, dy = x - a["m02"], y - a["m12"]
    return ((a["m11"] * dx - a["m01"] * dy) / det,
            (-a["m10"] * dx + a["m00"] * dy) / det)


def main(tol: int = TOL) -> int:
    import numpy as np, ezdxf
    from ezdxf import bbox
    from PIL import Image
    man = json.loads(MANIFEST.read_text())
    mpu = man["metres_per_unit"]
    ro = {r["view_id"]: r for r in man["raster_overlays"]}
    views = {v["id"]: v for v in man["views"] if v["kind"] == "plan"}
    msp = ezdxf.readfile(DXF).modelspace()
    rows = []
    for vid, view in views.items():
        b, box = ro[vid], view["clip_box_dxf"]
        im = np.asarray(Image.open(CASE_DATA / b["source_label"]).convert("RGB")).astype(int)
        mpp = abs(b["pixel_to_source_m"]["m00"]) * 1000
        for label, layers, rgb in GROUPS:
            mask = np.abs(im - np.array(rgb)).max(axis=2) <= tol
            ys, xs = np.nonzero(mask)
            ents = [e for e in msp.query("INSERT") if e.dxf.layer in layers
                    and box["xmin"] <= float(e.dxf.insert.x) <= box["xmax"]
                    and box["ymin"] <= float(e.dxf.insert.y) <= box["ymax"]]
            ex = bbox.extents(ents, cache=bbox.Cache(), fast=False)
            c = [inv(b["pixel_to_source_m"], X * mpu, Y * mpu)
                 for X, Y in ((ex.extmin.x, ex.extmin.y), (ex.extmax.x, ex.extmax.y))]
            px0, px1 = sorted([c[0][0], c[1][0]]); py0, py1 = sorted([c[0][1], c[1][1]])
            row = {"view": vid, "group": label, "tol": tol, "n_blocks": len(ents),
                   "mm_per_px": round(mpp, 2),
                   "ink_px": [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
                   "dxf_pred_px": [round(px0, 2), round(px1, 2), round(py0, 2), round(py1, 2)],
                   "delta_px": {"L": round(xs.min() - px0, 2), "R": round(xs.max() - px1, 2),
                                "T": round(ys.min() - py0, 2), "B": round(ys.max() - py1, 2)}}
            row["max_abs_delta_px"] = round(max(abs(v) for v in row["delta_px"].values()), 2)
            row["max_abs_delta_mm"] = round(row["max_abs_delta_px"] * mpp, 1)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False))
    Path(__file__).with_name(f"extent_holdout_tol{tol}.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else TOL))
