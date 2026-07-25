"""Smoke tests for render_gt_overlay.py (gt-over-original-PNG cross-source validation).

Pixel alignment needs a human to confirm; these guard that auto-calibration yields a
px-per-metre that AGREES between the two axes (the consistency self-check the overlay
relies on) on every real view, and that both overlay views render without crashing."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw
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


@pytest.mark.skipif(not _HAS, reason="sm21_anchor case_data / gt not present")
def test_sm21_legacy_overlay_pipeline_is_unchanged():
    """R-01: the sm21 legacy overlays are LOCKED baseline assets — pixel-identical.

    ``DIM``, ``_calibrate``, ``overlay_plan`` and ``overlay_elev`` are shared history.
    The v3 review path deliberately grew its own greyscale base, proportional stroke
    weights and role annotations; this lock is what makes "v3 only" a checkable claim
    rather than a promise.  Compared against the committed renders themselves, so any
    drift in the legacy dimming / calibration / draw order fails here immediately.
    """
    gt, cd = ov._load("sm21_anchor")
    renders = ov.GT_DIR / "sm21_anchor" / "renders"
    produced = {f"overlay_{ov._FLOOR_PNG[floor]}.png": ov.overlay_plan("sm21_anchor", gt, cd, floor)
                for floor in ("Floor 1", "Floor 2")}
    produced.update({f"overlay_{ov._FACADE_PNG[facade]}.png": ov.overlay_elev("sm21_anchor", gt, cd, facade)
                     for facade in ("South", "North", "East", "West")})
    for name, image in produced.items():
        reference = np.asarray(Image.open(renders / name).convert("RGB"))
        fresh = np.asarray(image.convert("RGB"))
        assert fresh.shape == reference.shape, name
        assert int((fresh != reference).any(-1).sum()) == 0, name


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


def test_sm24_v3_plan_and_elevation_overlays_normalise_y_down_rectangle_corners(tmp_path, monkeypatch):
    """Real y-down CAD screenshots make z0 map below z1; all four must render.

    This is intentionally the production v3 builder path: before the narrow
    PIL-corner ordering repair it raised ``y1 must be >= y0`` at the first
    elevation opening despite correct calibration/projection math.
    """
    from src.agent.judge.tarch_converter_schema import TarchConversionRequestV1, resolve_converter_tooling
    from src.agent.judge.tarch_normalize import run_p2_conversion
    from src.agent.judge.gt_extraction import ExtractionInputs, extract_gt_v3
    from src.agent.judge.gt_schema import REPO_ROOT, compute_gt_implementation_hashes
    root = Path("logs/experiments/2026-07-24_sm24_gt_review")
    request = TarchConversionRequestV1.model_validate_json((root / "request_v3_calibrated.json").read_text())
    tooling = resolve_converter_tooling(Path("src/configs/judge_gt.yaml"), Path("src/configs/correction.yaml"))
    conversion = run_p2_conversion(root / "source.dxf", request, request.plan_views[0], tooling, tmp_path)
    document = extract_gt_v3(ExtractionInputs(conversion.augmented_dxf_path, conversion.manifest, tooling,
                                               compute_gt_implementation_hashes(REPO_ROOT)))
    lines = []
    events = []
    original_line = ImageDraw.ImageDraw.line
    original_polygon = ImageDraw.ImageDraw.polygon
    original_text = ImageDraw.ImageDraw.text
    def capture_line(self, xy, *args, **kwargs):
        lines.append((xy, kwargs)); events.append("line")
        return original_line(self, xy, *args, **kwargs)
    def capture_polygon(self, xy, *args, **kwargs):
        events.append("polygon")
        return original_polygon(self, xy, *args, **kwargs)
    def capture_text(self, xy, *args, **kwargs):
        events.append("text")
        return original_text(self, xy, *args, **kwargs)
    monkeypatch.setattr(ImageDraw.ImageDraw, "line", capture_line)
    monkeypatch.setattr(ImageDraw.ImageDraw, "polygon", capture_polygon)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture_text)
    images = ov.build_gt_overlay_images_v3(document, conversion.manifest,
                                            raster_root=Path("case_tests/e2e_tests/sm24_anchor/case_data"))
    assert list(images) == ["East_view", "North_view", "South_view", "West_view", "plan-F1"]
    assert all(image.mode == "RGB" and image.width > 0 and image.height > 0 for image in images.values())
    # Each of the four facade envelopes is drawn as FOUR explicit equal-width edges
    # (PIL's rectangle renders a 1 px bottom edge), so the envelope colour must appear
    # 4x4 times plus one closed footprint ring on the plan.  This still proves the
    # y-down corner-ordering repair: every corner projects and renders without raising.
    envelope_edges = [xy for xy, kwargs in lines if kwargs.get("fill") == ov._ENVELOPE + (255,)]
    assert len(envelope_edges) == 4 * 4 + 1

    # FIX-1 (draw order): on the plan, EVERY zone fill must be laid down before ANY
    # zone label, otherwise a later zone's translucent fill buries an earlier zone's
    # name — which is exactly how z4 lost its label in the 07-25 bundle.
    # plan-F1 sorts last and is the only view that fills polygons, so the plan segment
    # of the event log starts at the first polygon.
    plan_events = events[events.index("polygon"):]
    first_text = plan_events.index("text")
    last_polygon = len(plan_events) - 1 - plan_events[::-1].index("polygon")
    assert last_polygon < first_text, (last_polygon, first_text)
    assert plan_events.count("polygon") == 8            # eight sm24 zone fills
    assert plan_events.count("text") == 8 + 1           # eight zone labels + candidate stamp


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


# --------------------------------------------------------------------------- #
# WI-5 — v3 review-render quality (07-24 bundle was unreviewable: hairline strokes
# on elevations, fat strokes on the small plan, and gt drawn in the same cyan as the
# drawing's own opening ink over a base dimmed to 0.38).
# --------------------------------------------------------------------------- #
_SM24_CD = Path("case_tests/e2e_tests/sm24_anchor/case_data")


def test_v3_review_base_keeps_drawing_ink_readable_and_hue_free():
    """Quantified criterion: ink luma retention >= 0.6 (legacy multiply gave 0.38),
    and the base carries no hue at all, so every saturated pixel in the finished
    overlay provably belongs to gt rather than to the drawing."""
    base = Image.open(_SM24_CD / "South_view.png").convert("RGB")
    source = np.asarray(base).astype(float)
    result = np.asarray(ov._review_base(base).convert("RGB")).astype(float)
    luma = source @ np.array([0.299, 0.587, 0.114])
    ink = luma > 40                     # non-background pixels of the drawing
    retention = (result[..., 0][ink]).mean() / luma[ink].mean()
    assert retention >= 0.6, retention
    assert retention / ov.DIM >= 1.9, retention   # ~2x the legacy 0.38 multiply
    assert (result[..., 0] == result[..., 1]).all() and (result[..., 1] == result[..., 2]).all()


def test_v3_stroke_weights_scale_with_raster_instead_of_being_absolute():
    """The 07-24 defect: one absolute constant is a hairline on a 2434 px elevation
    and a wall-burying slab on a 790 px plan."""
    small = ov._weights(Image.new("RGB", (790, 1111)))
    large = ov._weights(Image.new("RGB", (2434, 1457)))
    assert large["bar"] > small["bar"] and large["box"] > small["box"]
    assert large["font"] > small["font"]
    assert all(value >= 2 for value in small.values())
    # proportionally equal (that is the whole point), within integer rounding
    assert abs(large["bar"] / 2434 - small["bar"] / 790) < 0.002


def test_v3_outline_edges_are_equal_width_and_dashing_leaves_gaps():
    """WI-5c/WI-5e.

    Honest scope note: the review premise "PIL's rectangle bottom edge is only 1 px"
    was CHECKED and does not hold on Pillow 12.2 (all four edges render at full width),
    so the equal-width half of this test is a behavioural lock on ``_outline``, not
    proof of a fixed PIL bug.  The load-bearing half is DASHING: a solid box hides the
    drawing's own opening frame — the very evidence the reviewer compares against —
    and ``ImageDraw.rectangle`` cannot dash at all.
    """
    def edges(dash):
        image = Image.new("RGBA", (60, 40), (0, 0, 0, 255))
        ov._outline(ImageDraw.Draw(image), (10, 10, 50, 30), (255, 0, 0, 255), 4, dash=dash)
        pixels = np.asarray(image.convert("RGB"))
        return (pixels[..., 0] > 200) & (pixels[..., 1] < 60)

    solid = edges(0)
    assert solid[8:14, 20:40].sum(0).max() == solid[26:34, 20:40].sum(0).max() == 4
    # every column across the top edge is inked when solid ...
    assert solid[8:16, 12:48].any(0).all()
    dashed = edges(6)
    # ... and provably NOT when dashed, which is what lets the drawing show through
    assert not dashed[8:16, 12:48].any(0).all()
    assert 0 < dashed[8:16, 12:48].any(0).sum() < solid[8:16, 12:48].any(0).sum()


def test_v3_review_annotations_are_review_only_and_never_guess(tmp_path):
    """The zone-role annotation tints and labels; it may not touch the GT, and any
    zone it does not name stays neutral grey rather than being guessed."""
    doc, manifest, _ = _v3_plan_inputs(tmp_path)
    before = doc.model_dump_json()
    zone_id = doc.floors[0].zones[0].id
    annotated = ov.build_gt_overlay_images_v3(doc, manifest, raster_root=tmp_path,
                                              review_annotations={zone_id: "meeting"})
    plain = ov.build_gt_overlay_images_v3(doc, manifest, raster_root=tmp_path)
    assert doc.model_dump_json() == before                      # GT untouched
    assert np.asarray(annotated["plan-F1"]).shape == np.asarray(plain["plan-F1"]).shape
    assert (np.asarray(annotated["plan-F1"]) != np.asarray(plain["plan-F1"])).any()
    # A zone nobody annotated and whose GT role is unspecified falls back to neutral
    # grey — the renderer must never invent a role colour.
    assert ov._V3_ROLE["unspecified"] == ov._NEUTRAL_ROLE
    assert ov._V3_ROLE.get("no_such_role", ov._NEUTRAL_ROLE) == ov._NEUTRAL_ROLE
