"""Smoke tests for render_gt_overlay.py (gt-over-original-PNG cross-source validation).

Pixel alignment needs a human to confirm; these guard that auto-calibration yields a
px-per-metre that AGREES between the two axes (the consistency self-check the overlay
relies on) on every real view, and that both overlay views render without crashing."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
import hashlib

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_gt_overlay as ov  # noqa: E402
from src.agent.judge.gt_manifest import Affine2D, GtExtractionManifestV1, compute_manifest_sha256
from src.agent.judge.gt_schema import GroundTruthV3

_CD = Path("case_tests/e2e_tests/sm21_anchor/case_data")
_HAS = (_CD / "1f_view.png").exists() and (ov.GT_DIR / "sm21_anchor" / "gt.json").exists()


def _scale_err(name, w_m, h_m):
    im = np.asarray(Image.open(_CD / f"{name}.png").convert("RGB"))
    x0, x1, yt, yb = ov._calibrate(im, w_m, h_m)
    sx, sy = (x1 - x0) / w_m, (yb - yt) / h_m
    return abs(sx - sy) / max(sx, sy)


@pytest.mark.skipif(not _HAS, reason="sm21_anchor case_data / gt not present")
def test_plan_calibration_axes_agree():
    for name in ("1f_view", "2f_view"):
        assert _scale_err(name, 15.0, 8.0) < 0.05, name


@pytest.mark.skipif(not _HAS, reason="sm21_anchor case_data / gt not present")
def test_elevation_calibration_axes_agree():
    # the dual detector (gray ∪ white) must find a consistent box for every facade
    for name in ("South_view", "North_view", "East_view", "West_view"):
        fw = 15.0 if name in ("South_view", "North_view") else 8.0
        assert _scale_err(name, fw, 6.6) < 0.05, name


@pytest.mark.skipif(not _HAS, reason="sm21_anchor case_data / gt not present")
def test_overlays_render():
    gt, cd = ov._load("sm21_anchor")
    assert ov.overlay_plan("sm21_anchor", gt, cd, "Floor 1").mode == "RGB"
    assert ov.overlay_elev("sm21_anchor", gt, cd, "South").mode == "RGB"


def _v3_plan_inputs(tmp_path):
    from test_gt_schema import _opening_payload, _rehash
    raw = _opening_payload(observed=True)
    raw["case"] = "synthetic-L"
    raw["sources"][0]["views"][0]["projection_surface_key"] = "south-full"
    next(item for item in raw["floors"][0]["boundary_segments"] if item["facade_family"] == "South")["projection_surface_keys"] = ["south-full"]
    raster = tmp_path / "plan.png"; Image.new("RGB", (100, 100), "white").save(raster)
    from test_gt_from_dxf import _dxf, _manifest
    dxf = tmp_path / "source.dxf"; _dxf(dxf)
    manifest_raw = _manifest(dxf).model_dump(mode="json")
    manifest_raw["raster_overlays"] = [{"id": "plan-raster", "source_label": raster.name,
        "source_sha256": hashlib.sha256(raster.read_bytes()).hexdigest(), "view_id": "plan-F1",
        "pixel_to_source_m": {"m00": 0.1, "m01": 0.0, "m02": 0.0, "m10": 0.0, "m11": 0.1, "m12": 0.0}}]
    manifest_raw["manifest_sha256"] = "0" * 64
    manifest_raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**manifest_raw))
    manifest = GtExtractionManifestV1.model_validate(manifest_raw)
    raw["generator"]["manifest_sha256"] = manifest.manifest_sha256
    return GroundTruthV3.model_validate(_rehash(raw)), manifest, raster


def test_v3_overlay_affine_hash_watermark_and_atomic_output(tmp_path):
    doc, manifest, raster = _v3_plan_inputs(tmp_path)
    images = ov.build_gt_overlay_images_v3(doc, manifest, raster_root=tmp_path)
    assert list(images) == ["plan-F1"] and images["plan-F1"].getpixel((2, 98))[0] < 120
    binding = manifest.raster_overlays[0]; view = next(item for item in manifest.views if item.id == "plan-F1")
    point = (2.75, 1.25)
    pixel = ov._pixel_for_world_plan(view, binding, point)
    source = ov._apply_affine(binding.pixel_to_source_m, *pixel)
    world = ov._apply_affine(view.world_from_source_m, *source)
    assert world == pytest.approx(point, abs=1e-9) and pixel == pytest.approx((27.5, 12.5), abs=1e-9)
    out = tmp_path / "out"
    written = ov.write_gt_overlay_images_v3(images, out)
    assert [path.name for path in written] == ["overlay_plan-F1.png"] and written[0].is_file()
    with pytest.raises(FileExistsError): ov.write_gt_overlay_images_v3(images, out)


def test_v3_overlay_rejects_raster_hash_mismatch_and_sanitized_collision(tmp_path):
    doc, manifest, raster = _v3_plan_inputs(tmp_path)
    raster.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash_mismatch"):
        ov.build_gt_overlay_images_v3(doc, manifest, raster_root=tmp_path)
    images = {"A/B": Image.new("RGB", (2, 2)), "A-B": Image.new("RGB", (2, 2))}
    with pytest.raises(ValueError, match="collision"):
        ov.write_gt_overlay_images_v3(images, tmp_path / "collision")


def test_v3_overlay_rejects_document_manifest_binding_mismatch(tmp_path):
    doc, manifest, _ = _v3_plan_inputs(tmp_path)
    mismatched = doc.model_copy(update={"generator": doc.generator.model_copy(update={"manifest_sha256": "b" * 64})})
    with pytest.raises(ValueError, match="manifest_hash_mismatch"):
        ov.build_gt_overlay_images_v3(mismatched, manifest, raster_root=tmp_path)


def test_v3_elevation_overlay_uses_declared_floor_z_and_affine(tmp_path):
    doc, manifest, _ = _v3_plan_inputs(tmp_path)
    raster = tmp_path / "elev.png"; Image.new("RGB", (200, 100), "white").save(raster)
    raw = manifest.model_dump(mode="json")
    raw["raster_overlays"].append({"id":"elev-raster","source_label":raster.name,"source_sha256":hashlib.sha256(raster.read_bytes()).hexdigest(),"view_id":"elev-S","pixel_to_source_m":{"m00":.1,"m01":0.,"m02":0.,"m10":0.,"m11":.1,"m12":0.}})
    raw["manifest_sha256"] = "0" * 64
    raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    manifest = GtExtractionManifestV1.model_validate(raw)
    raised_floor = doc.floors[0].model_copy(update={"z_floor_m": 1.0})
    doc = doc.model_copy(update={"floors":[raised_floor], "generator":doc.generator.model_copy(update={"manifest_sha256":manifest.manifest_sha256})})
    image = ov.build_gt_overlay_images_v3(doc, manifest, raster_root=tmp_path)["elev-S"]
    # elevation source x=10+along and y=z; inverse pixel transform makes z=1 land at y=10 (≤1 px)
    assert image.getpixel((100, 10)) != (255, 255, 255)


@pytest.mark.parametrize("label", ["../outside.png", "/tmp/outside.png", "nested/raster.png"])
def test_v3_safe_raster_rejects_non_basename_paths(tmp_path, label):
    with pytest.raises(ValueError, match="raster_label_invalid"):
        ov._safe_raster(tmp_path, label)


def test_v3_safe_raster_rejects_symlink_escape_and_projection_out_of_bounds(tmp_path):
    outside = tmp_path.parent / "outside.png"; Image.new("RGB", (1, 1)).save(outside)
    link = tmp_path / "link.png"; link.symlink_to(outside)
    with pytest.raises(ValueError, match="raster_escape"):
        ov._safe_raster(tmp_path, link.name)
    with pytest.raises(ValueError, match="projection_out_of_bounds"):
        ov._within(Image.new("RGB", (2, 2)), (2.0, 0.0))


def test_v3_overlay_rejects_competing_binding_empty_view_id_and_singular_affine(tmp_path):
    doc, manifest, _ = _v3_plan_inputs(tmp_path)
    raw = manifest.model_dump(mode="json")
    duplicate = dict(raw["raster_overlays"][0]); duplicate["id"] = "plan-raster-2"; raw["raster_overlays"].append(duplicate)
    raw["manifest_sha256"] = "0" * 64
    raw["manifest_sha256"] = compute_manifest_sha256(GtExtractionManifestV1.model_construct(**raw))
    manifest = GtExtractionManifestV1.model_validate(raw)
    doc = doc.model_copy(update={"generator": doc.generator.model_copy(update={"manifest_sha256": manifest.manifest_sha256})})
    with pytest.raises(ValueError, match="gt_overlay_competing_bindings"):
        ov.build_gt_overlay_images_v3(doc, manifest, raster_root=tmp_path)
    with pytest.raises(ValueError, match="view_id_unsanitisable"):
        ov._sanitized_view_id("...")
    singular = Affine2D.model_construct(m00=1.0, m01=0.0, m02=0.0, m10=2.0, m11=0.0, m12=0.0)
    with pytest.raises(ValueError, match="singular_affine"):
        ov._inverse_affine(singular, 0.0, 0.0)
