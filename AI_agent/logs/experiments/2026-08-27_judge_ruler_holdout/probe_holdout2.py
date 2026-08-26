"""Step 2 of the judge-ruler holdout: detect the SAME features in the raster,
independently of anything the reading product says, and measure the residual.

Why this is a genuine holdout (sol 2026-08-27 §C):
  * the manifest's plan affine was fitted from ``WALL`` layer line peaks only
    (2026-08-20 build_request.py, RANSAC);
  * the features used here live on ``WINDOW`` / ``E_WINDOW`` / ``LVTRY``, whose
    colours are DECLARED BY THE DRAWING ITSELF in the DXF layer table
    (cyan 0,255,255 for both window layers; magenta 255,0,255 for doors)
    -> detection needs no product input, no gt coordinate, and no fitting.

Method per plan view:
  1. every INSERT on those layers inside the view's clip box -> explode to
     virtual entities -> bounding-box centre in DXF NATIVE units;
  2. native (m) -> pixel via the manifest affine (taken as given, ⛔ not fitted);
  3. in the PNG, keep pixels within ``TOL`` of the declared layer colour, label
     8-connected components, drop specks -> detected blob centroids;
  4. greedy nearest one-to-one assignment, and report residuals.
     ⛔ no free parameter is tuned to the answer: TOL and MIN_PX are declared
     here and swept in the report.
"""
from __future__ import annotations
import json, math
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/manifest.json"
DXF = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor/sm25-L_t3.dxf"
CASE_DATA = REPO / "case_tests/e2e_tests/sm25-L_anchor/case_data"

COLOURS = {"WINDOW": (0, 255, 255), "E_WINDOW": (0, 255, 255), "LVTRY": (255, 0, 255)}
TOL = 40          # per-channel tolerance when matching the declared layer colour
MIN_PX = 25       # ignore components smaller than this (anti-aliasing specks)


def inv_affine(a, x, y):
    det = a["m00"] * a["m11"] - a["m01"] * a["m10"]
    dx, dy = x - a["m02"], y - a["m12"]
    return ((a["m11"] * dx - a["m01"] * dy) / det,
            (-a["m10"] * dx + a["m00"] * dy) / det)


def components(mask, min_px):
    """8-connected components -> list of (centroid_x, centroid_y, size)."""
    import numpy as np
    H, W = mask.shape
    lab = np.zeros((H, W), dtype=np.int32)
    out = []
    cur = 0
    ys, xs = np.nonzero(mask)
    seen = set()
    stack = []
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if lab[y0, x0]:
            continue
        cur += 1
        stack.append((y0, x0))
        lab[y0, x0] = cur
        sx = sy = n = 0
        while stack:
            y, x = stack.pop()
            sx += x; sy += y; n += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = cur
                        stack.append((ny, nx))
        if n >= min_px:
            out.append((sx / n, sy / n, n))
    return out


def main() -> int:
    import ezdxf, numpy as np
    from PIL import Image
    from ezdxf.math import Matrix44

    man = json.loads(MANIFEST.read_text())
    mpu = man["metres_per_unit"]
    ro = {r["view_id"]: r for r in man["raster_overlays"]}
    views = {v["id"]: v for v in man["views"] if v["kind"] == "plan"}
    doc = ezdxf.readfile(DXF)
    msp = doc.modelspace()

    report = {"tol": TOL, "min_px": MIN_PX, "views": {}}
    for vid, view in views.items():
        b = ro[vid]; box = view["clip_box_dxf"]
        im = np.asarray(Image.open(CASE_DATA / b["source_label"]).convert("RGB")).astype(int)
        H, W, _ = im.shape

        for group, layers in (("window", ("WINDOW", "E_WINDOW")), ("door", ("LVTRY",))):
            rgb = COLOURS[layers[0]]
            preds = []
            for e in msp.query("INSERT"):
                if e.dxf.layer not in layers:
                    continue
                x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
                if not (box["xmin"] <= x <= box["xmax"] and box["ymin"] <= y <= box["ymax"]):
                    continue
                xs, ys = [], []
                try:
                    for sub in e.virtual_entities():
                        try:
                            bb = sub.bbox() if hasattr(sub, "bbox") else None
                        except Exception:
                            bb = None
                        pts = []
                        if hasattr(sub, "vertices"):
                            try: pts = [(p[0], p[1]) for p in sub.vertices()]
                            except Exception: pts = []
                        if not pts:
                            for attr in ("start", "end", "center", "insert"):
                                v = getattr(sub.dxf, attr, None)
                                if v is not None:
                                    pts.append((float(v.x), float(v.y)))
                        for px_, py_ in pts:
                            xs.append(px_); ys.append(py_)
                except Exception:
                    pass
                cx = (min(xs) + max(xs)) / 2 if xs else x
                cy = (min(ys) + max(ys)) / 2 if ys else y
                preds.append(inv_affine(b["pixel_to_source_m"], cx * mpu, cy * mpu))

            d = np.abs(im - np.array(rgb)).max(axis=2)
            mask = d <= TOL
            blobs = components(mask, MIN_PX)

            # greedy nearest one-to-one
            used, pairs = set(), []
            for i, (px_, py_) in enumerate(preds):
                best, bd = None, 1e18
                for j, (bx, by, n) in enumerate(blobs):
                    if j in used:
                        continue
                    dd = (bx - px_) ** 2 + (by - py_) ** 2
                    if dd < bd:
                        bd, best = dd, j
                if best is not None:
                    used.add(best); pairs.append((i, best, math.sqrt(bd)))
            res = sorted(p[2] for p in pairs)
            mpp = abs(b["pixel_to_source_m"]["m00"])
            def stat(v):
                return {"n": len(v),
                        "median_px": round(v[len(v)//2], 3) if v else None,
                        "p90_px": round(v[int(len(v)*0.9)], 3) if v else None,
                        "max_px": round(v[-1], 3) if v else None,
                        "rms_px": round(math.sqrt(sum(x*x for x in v)/len(v)), 3) if v else None,
                        "median_mm": round(v[len(v)//2]*mpp*1000, 1) if v else None,
                        "rms_mm": round(math.sqrt(sum(x*x for x in v)/len(v))*mpp*1000, 1) if v else None}
            report["views"].setdefault(vid, {})[group] = {
                "png": b["source_label"], "declared_rgb": list(rgb),
                "n_inserts": len(preds), "n_blobs": len(blobs),
                "mask_px": int(mask.sum()), "residual": stat(res)}
            print(f"{vid} {group:7s} inserts={len(preds):3d} blobs={len(blobs):3d} "
                  f"maskpx={int(mask.sum()):6d} -> {report['views'][vid][group]['residual']}")

    Path(__file__).with_name("holdout_residuals.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
