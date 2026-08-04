"""O-4 (batch C) locks for ``render_vector_to_png.py``.

Root cause these lock: an OCR/annotation anchor is fully untyped in the reading
schema (``ocr_texts: list``), so a PIXEL anchor like ``[360, 450]`` read as
metric expanded the rendered canvas extent to ~360 x 450 m -> ~3.3e8 px (a PNG
nothing can open). The renderer must derive its canvas extent from STRUCTURAL
geometry (strokes + dimension endpoints) ONLY, never from annotation anchors,
and enforce a hard pixel budget before ``Image.new`` (refuse, never clamp).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_vector_to_png as rv  # noqa: E402


def _plan_with_structure_and_ocr(ocr_anchor):
    """A ~10 x 20 m plan (walls spanning [0,10] x [0,20]) carrying one OCR text
    whose anchor is either a legal metric point or a pixel point (the O-4 root
    cause). The structure is identical across both — only the OCR anchor moves."""
    return {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [10, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 20]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [10, 0], "p2": [10, 20]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 20], "p2": [10, 20]}},
        ],
        "ocr_texts": [{"text": "3600", "anchor": ocr_anchor}],
    }


def test_L51_pixel_ocr_anchor_does_not_blow_up_canvas():
    """L-51 (O-4): a ~10 x 20 m structure with an OCR anchor of ``[360, 450]``
    (a pixel point that, read as metric, was the 3.3e8-px root cause) must render
    within the pixel budget. The canvas extent comes from structural strokes ONLY
    — the OCR anchor never expands it — and the budget is enforced before
    ``Image.new``. Neuter: re-add OCR anchors to ``_collect_points`` ⇒ the
    ``[360, 450]`` anchor expands the extent to ~360 x 450 m ⇒ canvas ~3.3e8 px ⇒
    ``CanvasBudgetExceeded`` raised by the pre-``Image.new`` budget check ⇒ this
    lock reds (render no longer succeeds)."""
    data = _plan_with_structure_and_ocr([360, 450])
    img = rv.render(data)  # must NOT raise
    # canvas bounded by the ~10x20 m structure (+ margin), nowhere near the budget
    assert img.size[0] * img.size[1] < rv.MAX_CANVAS_PIXELS
    assert img.size[0] <= rv.MAX_CANVAS_SIDE_PX
    assert img.size[1] <= rv.MAX_CANVAS_SIDE_PX
    # sanity: structural extent ~13 m wide (10 + 2*1.5 margin) at 45 px/m ≈ 585 px
    assert img.size[0] < 2000, img.size


def test_L52_pixel_vs_metric_ocr_anchor_canvas_unchanged():
    """L-52 (O-4): the same OCR text carrying a pixel anchor (``[60, 80]``) vs a
    legal metric anchor inside the structure (``[5, 10]``) must produce the SAME
    metric canvas — the OCR anchor never participates in the canvas extent, so a
    pixel anchor cannot change it; the metric anchor is drawn against the trusted
    structural bounds. Neuter: re-add OCR anchors to ``_collect_points`` ⇒ the
    pixel ``[60, 80]`` expands the extent (but stays under the budget) while the
    metric ``[5, 10]`` does not ⇒ the two canvas sizes diverge ⇒ this lock reds."""
    pixel_img = rv.render(_plan_with_structure_and_ocr([60, 80]))
    metric_img = rv.render(_plan_with_structure_and_ocr([5, 10]))
    assert pixel_img.size == metric_img.size
    # and both are the structural extent, not blown up by either anchor
    assert pixel_img.size[0] < 2000, pixel_img.size


def test_L51_over_budget_structural_canvas_is_refused_not_clamped():
    """L-51 companion (O-4): a STRUCTURAL canvas that genuinely exceeds the pixel
    budget is REFUSED (raises ``CanvasBudgetExceeded``) — never silently clamped,
    because clamping would hide a broken extent instead of surfacing it. Here the
    structure itself spans an enormous footprint (no annotation involved) so the
    refusal is the structural budget guard, not the annotation-exclusion guard."""
    huge = {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [20000, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 20000]}},
        ],
    }
    with pytest.raises(rv.CanvasBudgetExceeded):
        rv.render(huge)


def test_L53_large_legit_building_renders_via_adaptive_scale():
    """N-3 (invariant #6): a legitimate but large building (here 200 x 20 m — a
    real bar building using only ~1/5 of the total pixel budget) must RENDER,
    not be refused. The old fixed SCALE_PX_PER_M=45 made any single side over
    ~182 m (8192/45) unrenderable, baking in a 'no building over ~182 m'
    assumption that blocks future complexity (long bars, setbacks unfolded into
    elevations, atrium sections, site plans). The fix ADAPTIVELY scales px/m to
    the structural extent — this is NOT clamping (the metric geometry is
    preserved; only the pixel resolution adapts) — and refuses only a genuinely
    absurd structure (>8 km side, pinned by test_L51_over_budget...). A bad OCR
    anchor is still never clamped: O-4 keeps it out of the extent and gate①
    (reading.ocr_anchors_in_bounds) surfaces it.

    Neuter: revert to the fixed SCALE_PX_PER_M (drop the adaptive _fit_scale, so
    the 200 m side maps to 200*45=9000 px) ⇒ 9000 > MAX_CANVAS_SIDE_PX ⇒
    CanvasBudgetExceeded ⇒ this lock reds (the legit building is refused
    again)."""
    data = {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [200, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 20]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [200, 0], "p2": [200, 20]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 20], "p2": [200, 20]}},
        ],
    }
    img = rv.render(data)  # must NOT raise — a legit 200 m bar renders
    # canvas fits BOTH budgets (adaptive scale chose a lower px/m, not a refusal)
    assert img.size[0] <= rv.MAX_CANVAS_SIDE_PX
    assert img.size[1] <= rv.MAX_CANVAS_SIDE_PX
    assert img.size[0] * img.size[1] <= rv.MAX_CANVAS_PIXELS
    # the 200 m side was DOWNSCALED to fit — at the fixed 45 px/m it would be
    # 9000 px (> MAX_CANVAS_SIDE_PX, refused); adaptive keeps it under the cap,
    # proving the resolution adapted rather than the building being refused
    assert img.size[0] < 200 * rv.SCALE_PX_PER_M
    # the canvas is still legible (not degenerated to a sliver) and keeps the
    # long bar's aspect ratio (uniform adaptive scaling, not a per-side clamp)
    assert img.size[0] > 100 and img.size[1] > 100
    assert img.size[0] / img.size[1] > 5
