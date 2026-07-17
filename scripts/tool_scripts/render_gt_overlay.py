"""Overlay the DXF-built gt onto the ORIGINAL drawing PNGs — cross-source validation.

The original case_data drawings and the source.dxf are two INDEPENDENT data sources for
the same building. Overlaying gt (built from the DXF) onto the original PNG cross-checks
that the two sources agree: if the gt zones/windows land on the drawing's real
walls/openings, the sources are consistent; if not, there is a real DATA problem (the
DXF and the drawing disagree, or one is wrong). This is the strong human-QA gate — unlike
gt-over-DXF, which (for a deterministic dxf→gt) only re-confirms the code.

Calibration is automatic: the footprint / facade-envelope pixel box is found from
wall-line pixel density per column/row, cross-checked by px-per-metre agreement between
the two axes (a mismatch flags a contaminated edge, corrected from the cleaner axis).

Usage:
    python scripts/tool_scripts/render_gt_overlay.py sm21_anchor
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Mapping

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from src.agent.judge.gt import load_gt_file
from src.agent.judge.gt_manifest import (ElevationViewBindingV1, GtExtractionManifestV1,
                                          PlanViewBindingV1)
from src.agent.judge.gt_render_model import gt_to_render_model
from src.agent.judge.gt_schema import GroundTruthV3

DIM = 0.38     # original drawing dimmed to this brightness so the gt overlay stands out

GT_DIR = Path("case_tests/test_baseline/gt")
CASE_DATA = Path("case_tests/e2e_tests/{case}/case_data")

ROLE = {"office": (90, 140, 220), "meeting": (70, 175, 90), "corridor": (220, 170, 40)}
WIN = (0, 200, 255)
DOOR = (255, 120, 0)
# elevation x runs west→east for S, south→north for E; N & W are viewed mirrored.
_MIRRORED = {"North", "West"}
_FACADE_PNG = {"South": "South_view", "North": "North_view",
               "East": "East_view", "West": "West_view"}
_FLOOR_PNG = {"Floor 1": "1f_view", "Floor 2": "2f_view"}


def _font(sz):
    return ImageFont.load_default(size=sz)


def _density_box(mask):
    cden, rden = mask.sum(0), mask.sum(1)
    if mask.sum() < 100:
        return None
    cols = np.where(cden > cden.max() * 0.38)[0]
    rows = np.where(rden > rden.max() * 0.38)[0]
    return int(cols.min()), int(cols.max()), int(rows.min()), int(rows.max())


def _box_gray(im):
    r, g, b = im[:, :, 0].astype(int), im[:, :, 1].astype(int), im[:, :, 2].astype(int)
    return _density_box((abs(r - g) < 25) & (abs(g - b) < 25) & (r > 60) & (r < 210))


def _box_white(im):
    r, g, b = im[:, :, 0].astype(int), im[:, :, 1].astype(int), im[:, :, 2].astype(int)
    return _density_box((r > 170) & (g > 170) & (b > 170))


def _calibrate(im, w_m, h_m):
    """Footprint / envelope pixel box. Try the gray-wall and white-envelope detectors;
    use whichever gives px-per-metre AGREEMENT between the two axes (the consistent one
    is the clean calibration — a contaminated edge inflates one axis). The two detectors
    are complementary across views, so one of them is almost always clean."""
    best = None
    for box in (_box_gray(im), _box_white(im)):
        if not box:
            continue
        x0, x1, yt, yb = box
        if x1 <= x0 or yb <= yt:
            continue
        sx, sy = (x1 - x0) / w_m, (yb - yt) / h_m
        err = abs(sx - sy) / max(sx, sy)
        if err < 0.05:
            return box
        if best is None or err < best[0]:
            best = (err, box)
    # fallback: anchor x on the gray box centre, width from the (reliable) y-scale
    x0, x1, yt, yb = best[1] if best else _box_gray(im)
    sy = (yb - yt) / h_m
    cx, half = (x0 + x1) / 2, sy * w_m / 2
    return round(cx - half), round(cx + half), yt, yb


def _load(case):
    gt = json.loads((GT_DIR / case / "gt.json").read_text(encoding="utf-8"))
    cd = Path(str(CASE_DATA).format(case=case))
    return gt, cd


def overlay_plan(case, gt, cd, floor):
    png = cd / f"{_FLOOR_PNG[floor]}.png"
    base = Image.open(png).convert("RGBA")
    im = np.asarray(base.convert("RGB"))               # calibrate on the full-brightness original
    dim = ImageEnhance.Brightness(base.convert("RGB")).enhance(DIM).convert("RGBA")
    W, D = gt["footprint"]["W_m"], gt["footprint"]["D_m"]
    x0, x1, yt, yb = _calibrate(im, W, D)

    def PX(gx):
        return x0 + gx / W * (x1 - x0)

    def PY(gy):
        return yb - gy / D * (yb - yt)         # gy=0 (south) at bottom

    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    fl = next(f for f in gt["floors"] if f["name"] == floor)
    for z in fl["zones"]:
        a, c, e, f = z["rect_m"]
        col = ROLE.get(z["role"], (150, 150, 150))
        d.rectangle([PX(a), PY(f), PX(e), PY(c)], fill=col + (70,), outline=col + (255,), width=3)
        d.text((PX(a) + 5, PY(f) + 4), f"{z['id']} {z['role']}", font=_font(20), fill=col + (255,))
    for w in gt["windows"]:
        if w["floor"] != floor:
            continue
        for o in w.get("openings", []):
            p, q = o["x_m"], o["x_m"] + o["width_m"]
            if w["facade"] in ("North", "South"):
                yy = PY(D) if w["facade"] == "North" else PY(0)
                d.line([(PX(p), yy), (PX(q), yy)], fill=WIN + (255,), width=9)
            else:
                xx = PX(W) if w["facade"] == "East" else PX(0)
                yA = yb - p / D * (yb - yt); yB = yb - q / D * (yb - yt)
                d.line([(xx, yA), (xx, yB)], fill=WIN + (255,), width=9)
    for dr in gt["doors"]:
        if dr["floor"] != floor:
            continue
        a, w = dr.get("x_m", 0.0), dr.get("width_m", 0.9)
        if dr["facade"] in ("North", "South"):           # facade-local x = world x
            yy = PY(D) if dr["facade"] == "North" else PY(0)
            d.line([(PX(a), yy), (PX(a + w), yy)], fill=DOOR + (255,), width=10)
        else:                                            # E/W facade-local = world y
            xx = PX(W) if dr["facade"] == "East" else PX(0)
            yA = yb - a / D * (yb - yt); yB = yb - (a + w) / D * (yb - yt)
            d.line([(xx, yA), (xx, yB)], fill=DOOR + (255,), width=10)
    d.text((10, 8), f"TYPE 2  {floor}:  gt over dimmed original  (is gt faithful to the drawing?)",
           font=_font(22), fill=(255, 255, 255, 255))
    out = Image.alpha_composite(dim, ov).convert("RGB")
    return out


def overlay_elev(case, gt, cd, facade):
    png = cd / f"{_FACADE_PNG[facade]}.png"
    base = Image.open(png).convert("RGBA")
    im = np.asarray(base.convert("RGB"))
    dim = ImageEnhance.Brightness(base.convert("RGB")).enhance(DIM).convert("RGBA")
    fw = gt["footprint"]["W_m"] if facade in ("North", "South") else gt["footprint"]["D_m"]
    ht = max(f["z_floor"] + f["ceiling_height"] for f in gt["floors"])
    x0, x1, yt, yb = _calibrate(im, fw, ht)
    mir = facade in _MIRRORED

    def PX(fx):
        t = (fw - fx) / fw if mir else fx / fw
        return x0 + t * (x1 - x0)

    def PZ(z):
        return yb - z / ht * (yb - yt)

    ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for w in gt["windows"]:
        if w["facade"] != facade:
            continue
        for o in w.get("openings", []):
            if "sill_m" not in o:
                continue
            xa, xb = PX(o["x_m"]), PX(o["x_m"] + o["width_m"])
            d.rectangle([min(xa, xb), PZ(o["head_m"]), max(xa, xb), PZ(o["sill_m"])],
                        outline=WIN + (255,), width=4)
    for dr in gt["doors"]:
        if dr["facade"] != facade:
            continue
        xa, xb = PX(dr["x_m"]), PX(dr["x_m"] + dr["width_m"])
        d.rectangle([min(xa, xb), PZ(dr.get("head_m", 2.1)), max(xa, xb), PZ(dr.get("sill_m", 0))],
                    outline=DOOR + (255,), width=4)
    d.text((10, 8), f"TYPE 2  {facade} elevation:  gt over dimmed original  "
           "(do gt windows match the drawing?)", font=_font(20), fill=(255, 255, 255, 255))
    out = Image.alpha_composite(dim, ov).convert("RGB")
    return out


def _inverse_affine(transform, x: float, y: float) -> tuple[float, float]:
    determinant = transform.m00 * transform.m11 - transform.m01 * transform.m10
    if determinant == 0:
        raise ValueError("gt_overlay_singular_affine")
    dx, dy = x - transform.m02, y - transform.m12
    return ((transform.m11 * dx - transform.m01 * dy) / determinant,
            (-transform.m10 * dx + transform.m00 * dy) / determinant)


def _apply_affine(transform, x: float, y: float) -> tuple[float, float]:
    return (transform.m00 * x + transform.m01 * y + transform.m02,
            transform.m10 * x + transform.m11 * y + transform.m12)


def _pixel_for_world_plan(view: PlanViewBindingV1, binding, world: tuple[float, float]) -> tuple[float, float]:
    source = _inverse_affine(view.world_from_source_m, *world)
    return _inverse_affine(binding.pixel_to_source_m, *source)


def _pixel_for_world_elevation(view: ElevationViewBindingV1, binding, along: float, z: float) -> tuple[float, float]:
    source = {view.world_along_from_source_m.source_axis: (along - view.world_along_from_source_m.offset) / view.world_along_from_source_m.scale,
              view.world_z_from_source_m.source_axis: (z - view.world_z_from_source_m.offset) / view.world_z_from_source_m.scale}
    return _inverse_affine(binding.pixel_to_source_m, source["x"], source["y"])


def _along_extent(segment) -> tuple[float, float]:
    axis = 0 if segment.facade_family in {"North", "South"} else 1
    return tuple(sorted((segment.p1[axis], segment.p2[axis])))


def _safe_raster(raster_root: Path, label: str) -> Path:
    if Path(label).name != label or ".." in Path(label).parts:
        raise ValueError("gt_overlay_raster_label_invalid")
    root = raster_root.resolve()
    raw_candidate = root / label
    candidate = raw_candidate.resolve()
    if not candidate.is_relative_to(root) or raw_candidate.is_symlink() or not candidate.is_file():
        raise ValueError("gt_overlay_raster_escape")
    return candidate


def _within(image: Image.Image, point: tuple[float, float], epsilon: float = 1e-6) -> None:
    if not (-epsilon <= point[0] <= image.width - 1 + epsilon and -epsilon <= point[1] <= image.height - 1 + epsilon):
        raise ValueError("gt_overlay_projection_out_of_bounds")


def _candidate_stamp(image: Image.Image, document: GroundTruthV3) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, image.height - 28, image.width, image.height), fill=(80, 0, 0, 255))
    draw.text((8, image.height - 24), f"CANDIDATE — NOT BASELINE  {document.content_sha256[:12]}", fill=(255,255,255,255), font=_font(15))


def _sanitized_view_id(view_id: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "-", view_id).strip(".-")
    if not result:
        raise ValueError("gt_overlay_view_id_unsanitisable")
    return result


def build_gt_overlay_images_v3(
    doc: GroundTruthV3,
    manifest: GtExtractionManifestV1,
    *,
    raster_root: Path,
) -> Mapping[str, Image.Image]:
    """Project typed v3 geometry via the manifest's declared affine bindings."""
    if doc.case != manifest.case:
        raise ValueError("gt_overlay_case_mismatch")
    if doc.generator.manifest_sha256 != manifest.manifest_sha256:
        raise ValueError("gt_overlay_manifest_hash_mismatch")
    model = gt_to_render_model(doc)
    overlays = sorted(manifest.raster_overlays, key=lambda item: (item.view_id, item.id))
    if len({item.view_id for item in overlays}) != len(overlays):
        raise ValueError("gt_overlay_competing_bindings")
    views = {view.id: view for view in manifest.views}
    floors = {floor.floor_id: floor for floor in model.floors}
    images: dict[str, Image.Image] = {}
    for binding in overlays:
        raster = _safe_raster(Path(raster_root), binding.source_label)
        if hashlib.sha256(raster.read_bytes()).hexdigest() != binding.source_sha256:
            raise ValueError("gt_overlay_raster_hash_mismatch")
        view = views.get(binding.view_id)
        if view is None:
            raise ValueError("gt_overlay_view_missing")
        base = Image.open(raster).convert("RGBA")
        image = ImageEnhance.Brightness(base.convert("RGB")).enhance(DIM).convert("RGBA")
        draw = ImageDraw.Draw(image)
        if isinstance(view, PlanViewBindingV1):
            floor = floors.get(view.floor_id)
            if floor is None:
                raise ValueError("gt_overlay_floor_missing")
            for polygon, colour in [(floor.footprint_exterior, (20,20,20,255)), *( (zone.exterior, ROLE.get(zone.role, (150,150,150)) + (255,)) for zone in floor.zone_polygons )]:
                points = [_pixel_for_world_plan(view, binding, point) for point in polygon]
                for point in points: _within(image, point)
                draw.line(points + [points[0]], fill=colour, width=3)
            segments = {segment.id: segment for segment in floor.boundary_segments}
            for opening in floor.openings:
                segment = segments[opening.segment_id]
                a,b = opening.world_along_interval
                def locate(value):
                    return (value, segment.p1[1]) if segment.facade_family in {"North", "South"} else (segment.p1[0], value)
                points = [_pixel_for_world_plan(view,binding,locate(a)), _pixel_for_world_plan(view,binding,locate(b))]
                for point in points: _within(image, point)
                draw.line(points, fill=WIN + (255,) if opening.kind == "window" else DOOR + (255,), width=7)
        elif isinstance(view, ElevationViewBindingV1):
            surface = next((item for item in model.elevation_surfaces if item.key == view.projection_surface_key), None)
            if surface is None:
                raise ValueError("gt_overlay_surface_missing")
            for segment in surface.segments:
                low, high = _along_extent(segment)
                z_floor = next(item.z_floor_m for item in model.floors if item.floor_id == segment.floor_id)
                for step in range(0, 13, 2):
                    a, b = low+(high-low)*step/12, low+(high-low)*min(1., (step+1)/12)
                    points = [_pixel_for_world_elevation(view,binding,a,z_floor), _pixel_for_world_elevation(view,binding,b,z_floor)]
                    for point in points: _within(image, point)
                    draw.line(points, fill=(150,0,0,255), width=1)
                for visible_low, visible_high in segment.visible_intervals:
                    points = [_pixel_for_world_elevation(view,binding,visible_low,z_floor), _pixel_for_world_elevation(view,binding,visible_high,z_floor)]
                    for point in points: _within(image, point)
                    draw.line(points, fill=(20,20,20,255), width=3)
            for opening in surface.openings:
                if opening.z_interval is None: continue
                a,b = opening.world_along_interval; z0,z1 = opening.z_interval
                corners = [_pixel_for_world_elevation(view,binding,a,z0), _pixel_for_world_elevation(view,binding,b,z1)]
                for point in corners: _within(image, point)
                draw.rectangle((corners[0], corners[1]), outline=WIN + (255,) if opening.kind == "window" else DOOR + (255,), width=3)
        else:  # pragma: no cover - strict manifest union protects this.
            raise ValueError("gt_overlay_view_kind_invalid")
        if doc.verification.status == "candidate": _candidate_stamp(image, doc)
        images[binding.view_id] = image.convert("RGB")
    return dict(sorted(images.items()))


def write_gt_overlay_images_v3(images: Mapping[str, Image.Image], out_dir: Path) -> tuple[Path, ...]:
    out_dir = Path(out_dir)
    if out_dir.exists():
        raise FileExistsError("gt_overlay_output_exists")
    names = [_sanitized_view_id(view_id) for view_id in images]
    if len(set(names)) != len(names):
        raise ValueError("gt_overlay_sanitized_name_collision")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.tmp-", dir=out_dir.parent))
    try:
        written: list[Path] = []
        for view_id, name in sorted(zip(images, names), key=lambda item: item[1]):
            path = temporary / f"overlay_{name}.png"; images[view_id].save(path); written.append(path)
        os.replace(temporary, out_dir)
        return tuple(out_dir / item.name for item in written)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main():
    ap = argparse.ArgumentParser(description="Overlay DXF-built gt onto the original drawing PNGs.")
    ap.add_argument("case", nargs="?", help="legacy v2 case")
    ap.add_argument("--gt-file")
    ap.add_argument("--manifest")
    ap.add_argument("--raster-root")
    ap.add_argument("--out-dir")
    args = ap.parse_args()
    v3 = any((args.gt_file, args.manifest, args.raster_root, args.out_dir))
    if v3:
        if args.case or not all((args.gt_file, args.manifest, args.raster_root, args.out_dir)):
            ap.error("v3 requires --gt-file --manifest --raster-root --out-dir and no positional case")
        document = load_gt_file(Path(args.gt_file), allow_legacy=False)
        if not isinstance(document, GroundTruthV3):
            ap.error("--gt-file must be schema v3")
        manifest = GtExtractionManifestV1.model_validate(json.loads(Path(args.manifest).read_text(encoding="utf-8")))
        for path in write_gt_overlay_images_v3(build_gt_overlay_images_v3(document, manifest, raster_root=Path(args.raster_root)), Path(args.out_dir)):
            print(f"wrote {path}")
        return
    if not args.case:
        ap.error("legacy positional case is required")
    gt, cd = _load(args.case)
    out_dir = GT_DIR / args.case / "renders"
    out_dir.mkdir(parents=True, exist_ok=True)
    for floor in ("Floor 1", "Floor 2"):
        p = out_dir / f"overlay_{_FLOOR_PNG[floor]}.png"
        overlay_plan(args.case, gt, cd, floor).save(p)
        print(f"wrote {p}")
    for facade in ("South", "North", "East", "West"):
        p = out_dir / f"overlay_{_FACADE_PNG[facade]}.png"
        overlay_elev(args.case, gt, cd, facade).save(p)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
