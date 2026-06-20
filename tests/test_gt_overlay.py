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

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_gt_overlay as ov  # noqa: E402

_CD = Path("case_tests/e2e_tests/sm21_anchor/case_data")
_HAS = (_CD / "1f_view.png").exists() and (ov.GT_DIR / "sm21_anchor" / "gt.json").exists()
pytestmark = pytest.mark.skipif(not _HAS, reason="sm21_anchor case_data / gt not present")


def _scale_err(name, w_m, h_m):
    im = np.asarray(Image.open(_CD / f"{name}.png").convert("RGB"))
    x0, x1, yt, yb = ov._calibrate(im, w_m, h_m)
    sx, sy = (x1 - x0) / w_m, (yb - yt) / h_m
    return abs(sx - sy) / max(sx, sy)


def test_plan_calibration_axes_agree():
    for name in ("1f_view", "2f_view"):
        assert _scale_err(name, 15.0, 8.0) < 0.05, name


def test_elevation_calibration_axes_agree():
    # the dual detector (gray ∪ white) must find a consistent box for every facade
    for name in ("South_view", "North_view", "East_view", "West_view"):
        fw = 15.0 if name in ("South_view", "North_view") else 8.0
        assert _scale_err(name, fw, 6.6) < 0.05, name


def test_overlays_render():
    gt, cd = ov._load("sm21_anchor")
    assert ov.overlay_plan("sm21_anchor", gt, cd, "Floor 1").mode == "RGB"
    assert ov.overlay_elev("sm21_anchor", gt, cd, "South").mode == "RGB"
