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
    """L-51 companion (O-4): a STRUCTURAL canvas whose side genuinely exceeds
    MAX_STRUCTURAL_SIDE_M (a >8 km side, even at 1 px/m) is REFUSED (raises
    ``CanvasBudgetExceeded``) — never silently clamped, because clamping would
    hide a broken extent instead of surfacing it. Here the structure itself
    spans an enormous footprint (no annotation involved) so the refusal is the
    structural METRE-side guard, not the annotation-exclusion guard.

    X-3 (r2 batchC dispatch §3): this docstring previously claimed the
    refusal was "the pixel budget" — it is not. The fixture's 20000 m side is
    what trips MAX_STRUCTURAL_SIDE_M (a metre cap: N-3's absurd-structure gate
    in render(), checked BEFORE any px/m scale is chosen); it never reaches
    MAX_CANVAS_PIXELS (a pixel-count cap consumed only inside
    ``_fit_scale``, once a structure has already passed the metre gate) —
    see ``test_L51_total_pixel_budget_binds_for_large_square_structure`` below
    for a fixture that actually exercises that cap ("声称在守其实没守" — the
    docstring said one thing and a different check fired)."""
    huge = {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [20000, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 20000]}},
        ],
    }
    with pytest.raises(rv.CanvasBudgetExceeded):
        rv.render(huge)


def test_L51_total_pixel_budget_binds_for_large_square_structure():
    """X-3 (r2 batchC dispatch §3 MINOR): ``_fit_scale``'s ``total_fit`` term
    (the ``MAX_CANVAS_PIXELS`` / area constraint) had ZERO lock — every
    existing fixture is a thin bar (e.g. 200x20 m) where ``side_fit`` alone
    already keeps the canvas under the total pixel budget, so ``total_fit`` is
    never the binding term and dropping it changes nothing observable
    (cross-review neuter x1: dropping ``total_fit`` left the whole affected
    subset green).

    A large near-SQUARE structure (unlike a bar) hits ``total_fit`` BEFORE
    ``side_fit``: at ``side_fit`` alone a 503x503 m extent (500 m building +
    margin) would scale to ~8190x8190 px ≈ 67M px — OVER the 50M budget — so
    ``total_fit`` must shrink the scale further for the render to stay in
    budget at all.

    Neuter: drop ``total_fit`` from ``_fit_scale`` (``return
    min(SCALE_PX_PER_M, side_fit)``) ⇒ the canvas grows to ~8190x8190 ≈ 67M px
    ⇒ over ``MAX_CANVAS_PIXELS`` ⇒ this lock reds."""
    data = {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [500, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 500]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [500, 0], "p2": [500, 500]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 500], "p2": [500, 500]}},
        ],
    }
    img = rv.render(data)  # must NOT raise
    # the actual proof: side_fit ALONE would put this ~67M px, over budget —
    # total_fit is what keeps it under.
    assert img.size[0] * img.size[1] <= rv.MAX_CANVAS_PIXELS
    # sanity: total_fit is genuinely binding here, not a no-op — side_fit alone
    # would have used ~8190 px/side (near MAX_CANVAS_SIDE_PX); total_fit pulls
    # it down further.
    side_fit_only_side = int(503 * (rv.MAX_CANVAS_SIDE_PX / 503))
    assert side_fit_only_side * side_fit_only_side > rv.MAX_CANVAS_PIXELS  # confirms side_fit alone overshoots
    assert img.size[0] < side_fit_only_side  # total_fit pulled the scale down further


def test_pixel_side_cap_widening_does_not_loosen_structural_refusal_threshold(monkeypatch):
    """NIT (r2 batchC dispatch §3 / cross-review P-8 §1, GLM r2 WIP): before this
    fix ``MAX_CANVAS_SIDE_PX`` was reused as BOTH a pixel-per-side render cap
    (consumed by ``_fit_scale``) AND the metre threshold for the
    genuinely-too-large-structure refusal in ``render()`` — a unit pun. Now the
    refusal uses a SEPARATE ``MAX_STRUCTURAL_SIDE_M`` constant. Widening the
    pixel cap alone must NOT loosen the structural (metre) refusal threshold.

    Neuter: collapse the two constants back to one shared ``MAX_CANVAS_SIDE_PX``
    (i.e. make the structural refusal compare against the pixel cap again) ⇒
    widening ``MAX_CANVAS_SIDE_PX`` here would ALSO raise the metre threshold,
    and the 9000 m structure would no longer be refused ⇒ this lock reds."""
    monkeypatch.setattr(rv, "MAX_CANVAS_SIDE_PX", 20000)  # widen the PIXEL cap only
    huge = {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [9000, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 9000]}},
        ],
    }
    # 9000 m is still > MAX_STRUCTURAL_SIDE_M (8192, unmoved) — must still refuse.
    with pytest.raises(rv.CanvasBudgetExceeded):
        rv.render(huge)


def test_pixel_side_cap_shrinking_does_not_trip_structural_refusal(monkeypatch):
    """NIT companion: shrinking the PIXEL cap alone must not move the METRE
    threshold either. A legitimate 200 m building (well under the unmoved
    MAX_STRUCTURAL_SIDE_M=8192 m) must still render via adaptive downscale, not
    be refused — even with an absurdly small pixel cap forcing heavy downscale.

    Neuter: collapse the two constants back to one ⇒ shrinking
    ``MAX_CANVAS_SIDE_PX`` here would ALSO shrink the metre gate to 100 ⇒ the
    200 m structure (> 100) would be refused ⇒ this lock reds."""
    monkeypatch.setattr(rv, "MAX_CANVAS_SIDE_PX", 100)  # shrink the PIXEL cap only
    data = {
        "image_kind": "plan",
        "strokes": [
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [200, 0]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 0], "p2": [0, 20]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [200, 0], "p2": [200, 20]}},
            {"pen": "wall", "geometry": {"kind": "line", "p1": [0, 20], "p2": [200, 20]}},
        ],
    }
    img = rv.render(data)  # must NOT raise despite the tiny pixel cap
    assert img.size[0] <= 100  # honors the shrunk pixel cap via adaptive downscale


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
