"""Batch D: typed (v3) grade board restores the six-panel layout (two plan
floors + four facade elevations North/South/East/West) plus a shared legend.

See AI_agent/logs/reviews/request/2026-08-04_batchD_and_R4a_dispatch.md §1.

Locks:
  - L-D1: a GT with two floors + all four elevations + a payload ⇒ the
    rendered image contains all 6 panel titles (asserted as concrete pixel
    regions, not merely "an Image came back") and the canvas is exactly the
    formula-derived size needed to hold them.
  - L-D2: a facade absent from GT ⇒ an explicit "no such elevation" hatched
    placeholder panel, occupying the SAME grid cell a real panel would (not
    a shrunk layout that silently drops it).
  - L-D3: the legend lists every judgement tier (complete / within-tolerance
    / miss / not-applicable) plus the gt-truth line style.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path("scripts/tool_scripts").resolve()))
import render_grade  # noqa: E402

from tests.b4b_contract_fixture import make_b4b_gt_document  # noqa: E402
from tests.batch_d_four_facade_fixture import make_four_facade_gt_document  # noqa: E402


def _region_has_nonbackground_pixel(image: Image.Image, box: tuple[int, int, int, int]) -> bool:
    """True if any pixel in ``box`` differs materially from the page
    background — i.e. something (text, a line, a fill) was actually drawn
    there, not left blank."""
    x0, y0, x1, y1 = box
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(image.width, x1), min(image.height, y1)
    if x1 <= x0 or y1 <= y0:
        return False
    region = image.convert("RGB").crop((x0, y0, x1, y1))
    bg = render_grade.BG
    for px in region.getdata():
        if any(abs(px[i] - bg[i]) > 8 for i in range(3)):
            return True
    return False


def _region_has_color(image: Image.Image, box: tuple[int, int, int, int], color, tol: int = 10) -> bool:
    x0, y0, x1, y1 = box
    region = image.convert("RGB").crop((x0, y0, x1, y1))
    for px in region.getdata():
        if all(abs(px[i] - color[i]) <= tol for i in range(3)):
            return True
    return False


def _floor_title_box(index: int) -> tuple[int, int, int, int]:
    ox = index * (render_grade._TYPED_PLAN_PANEL_W + render_grade._TYPED_PLAN_GAP)
    oy = render_grade._TYPED_FLOOR_TOP
    return (ox + 10, oy - 24, ox + 200, oy - 4)


def _elev_title_box(idx: int) -> tuple[int, int, int, int]:
    col = idx % render_grade._TYPED_ELEV_COLUMNS
    row = idx // render_grade._TYPED_ELEV_COLUMNS
    ox = col * (render_grade._TYPED_ELEV_PANEL_W + render_grade._TYPED_ELEV_GAP)
    oy = (render_grade._TYPED_ELEV_TOP
          + row * (render_grade._TYPED_ELEV_CELL_H + render_grade._TYPED_ELEV_GAP)
          + render_grade.LABEL_H)
    return (ox, oy - render_grade.LABEL_H, ox + 200, oy - 2)


def _elev_panel_box(idx: int) -> tuple[int, int, int, int]:
    col = idx % render_grade._TYPED_ELEV_COLUMNS
    row = idx // render_grade._TYPED_ELEV_COLUMNS
    ox = col * (render_grade._TYPED_ELEV_PANEL_W + render_grade._TYPED_ELEV_GAP)
    oy = (render_grade._TYPED_ELEV_TOP
          + row * (render_grade._TYPED_ELEV_CELL_H + render_grade._TYPED_ELEV_GAP)
          + render_grade.LABEL_H)
    return (ox, oy, ox + render_grade._TYPED_ELEV_PANEL_W, oy + render_grade._TYPED_ELEV_PANEL_H)


def _expected_image_size(num_floors: int) -> tuple[int, int]:
    elev_grid_w = (render_grade._TYPED_ELEV_COLUMNS * render_grade._TYPED_ELEV_PANEL_W
                   + (render_grade._TYPED_ELEV_COLUMNS - 1) * render_grade._TYPED_ELEV_GAP)
    elev_grid_h = (render_grade._TYPED_ELEV_ROWS * render_grade._TYPED_ELEV_CELL_H
                   + (render_grade._TYPED_ELEV_ROWS - 1) * render_grade._TYPED_ELEV_GAP)
    content_bottom = render_grade._TYPED_ELEV_TOP + elev_grid_h
    width = max(
        500,
        num_floors * (render_grade._TYPED_PLAN_PANEL_W + render_grade._TYPED_PLAN_GAP),
        elev_grid_w,
    )
    return width, content_bottom + 20


def _all_claims_payload(doc) -> dict:
    rows = []
    for opening in doc.openings:
        for claim in ("existence", "along", "width", "sill", "head"):
            rows.append({"target_id": opening.id, "claim": claim, "result": "complete"})
    return {"kind": "c2_scored", "claim_rows": rows}


# --------------------------------------------------------------------------- #
# L-D1
# --------------------------------------------------------------------------- #

def test_L_D1_six_panels_render_with_titles_and_exact_canvas_size():
    """A GT with two floors + all four elevations ⇒ the image contains all 6
    panel titles (2 plan + 4 elevation, each asserted via a concrete pixel
    region) and the canvas is EXACTLY the formula-derived size that fits them
    — not merely "big enough" by luck.

    Neuter: comment out the elevation-panel drawing loop in
    render_typed_grade (scripts/tool_scripts/render_grade.py) — the 4
    elevation title-region assertions below go red (their regions become
    pure background) while the 2 floor-title assertions stay green, proving
    this lock is pinned to the elevation panels specifically.
    """
    doc = make_four_facade_gt_document()
    payload = _all_claims_payload(doc)
    image, audit = render_grade.render_typed_grade(gt_document=doc, payload=payload)

    assert image.size == _expected_image_size(num_floors=2)

    # 2 plan panel titles
    for index in range(2):
        assert _region_has_nonbackground_pixel(image, _floor_title_box(index)), (
            f"floor panel {index} title region is blank"
        )
    # 4 elevation panel titles (N, S, E, W in FACADE_CODES order)
    for idx in range(4):
        assert _region_has_nonbackground_pixel(image, _elev_title_box(idx)), (
            f"elevation panel {idx} ({render_grade.FACADE_CODES[idx]}) title region is blank"
        )
    # every opening got a real (non-placeholder) claim colour on its own facade
    for idx, facade in enumerate(render_grade.FACADE_CODES):
        panel_box = _elev_panel_box(idx)
        assert _region_has_color(image, panel_box, render_grade.GREEN), (
            f"{facade} elevation panel has no green (complete) opening box"
        )


def test_L_D1_does_not_read_product_mirror_or_local_x_declarations():
    """§1 requirement 4: the typed elevation renderer must not consume any
    product-declared mirror/local-x field. A payload that carries one (with
    a value that, if honoured, would visibly flip which panel gets coloured)
    must render IDENTICALLY to the same payload without it."""
    doc = make_four_facade_gt_document()
    payload = _all_claims_payload(doc)
    payload_with_mirror_claim = {
        **payload,
        "mirrored": True,
        "local_x_positive": "right_to_left",
    }
    image_a, _ = render_grade.render_typed_grade(gt_document=doc, payload=payload)
    image_b, _ = render_grade.render_typed_grade(gt_document=doc, payload=payload_with_mirror_claim)
    assert list(image_a.getdata()) == list(image_b.getdata())


# --------------------------------------------------------------------------- #
# L-D2
# --------------------------------------------------------------------------- #

def test_L_D2_missing_facade_renders_explicit_placeholder_not_omission():
    """The b4b fixture only declares North/South elevations. East/West must
    still occupy their full grid cell as an explicit hatched "no such
    elevation" placeholder — never a silently skipped panel (which would
    look, to a human, like "nothing to report" instead of "not measured").

    Neuter: in _draw_typed_elevation_panel, change the `if not surfaces:`
    branch to `return` immediately (no hatch, no text) instead of drawing the
    placeholder — the hatch-fill and NA-message assertions below go red,
    while the image-size assertion (proving the cell is still reserved,
    not omitted) stays green — showing the two are independent checks.
    """
    doc = make_b4b_gt_document()
    payload = {"kind": "c2_scored", "claim_rows": []}
    image, _audit = render_grade.render_typed_grade(gt_document=doc, payload=payload)

    # the grid cell for East/West is still fully reserved (idx 2, 3 in
    # FACADE_CODES = ("N","S","E","W"))
    assert image.size == _expected_image_size(num_floors=2)
    for idx in (2, 3):
        facade = render_grade.FACADE_CODES[idx]
        panel_box = _elev_panel_box(idx)
        # explicit red "NO SUCH ELEVATION" label is present in the panel
        assert _region_has_color(image, panel_box, render_grade.RED), (
            f"{facade} elevation panel has no explicit NO-SUCH-ELEVATION marker"
        )
        # and the panel is hatched (not just an empty outline) — sample
        # several pixels down the panel's diagonal for the NA hatch stroke
        # colour used by _typed_hatch.
        na_line = (107, 114, 128)
        assert _region_has_color(image, panel_box, na_line, tol=20), (
            f"{facade} elevation panel is missing the NA hatch pattern"
        )
    # the two facades GT DOES declare still render real content (not also
    # hatched by some over-broad neuter)
    for idx in (0, 1):
        panel_box = _elev_panel_box(idx)
        assert _region_has_nonbackground_pixel(image, panel_box)


def test_L_D2_missing_facade_does_not_shrink_the_grid():
    """A GT with only 2/4 facades declared still reserves all 4 grid cells —
    proves 'no such elevation' does not silently compact the layout down to
    however many elevations happen to exist (which would look identical to a
    correctly-drawn two-facade building from a glance at the image size)."""
    two_facade_size = render_grade.render_typed_grade(
        gt_document=make_b4b_gt_document(), payload={"kind": "c2_scored", "claim_rows": []},
    )[0].size
    four_facade_size = render_grade.render_typed_grade(
        gt_document=make_four_facade_gt_document(),
        payload=_all_claims_payload(make_four_facade_gt_document()),
    )[0].size
    assert two_facade_size == four_facade_size == _expected_image_size(num_floors=2)


# --------------------------------------------------------------------------- #
# L-D3
# --------------------------------------------------------------------------- #

def test_L_D3_legend_lists_every_judgement_tier():
    """The legend row must contain all four judgement-tier swatches (green
    complete / orange within-tolerance / red miss / hatched not-applicable)
    plus the gt-truth line style — the vocabulary batch D requires be
    restored to the v3 typed path.

    Neuter: replace the body of _typed_legend with `pass` — every colour
    assertion below goes red simultaneously (the legend row becomes pure
    background), with zero effect on any panel-content test above (which
    read pixels well below the legend's y range).
    """
    doc = make_four_facade_gt_document()
    payload = _all_claims_payload(doc)
    image, _audit = render_grade.render_typed_grade(gt_document=doc, payload=payload)

    legend_box = (0, render_grade._TYPED_LEGEND_Y - 4, image.width, render_grade._TYPED_LEGEND_Y + 16)
    assert _region_has_color(image, legend_box, render_grade.GREEN)
    assert _region_has_color(image, legend_box, render_grade.ORANGE)
    assert _region_has_color(image, legend_box, render_grade.RED)
    # not-applicable swatch: light gray fill with a dark diagonal stroke
    assert _region_has_color(image, legend_box, (224, 224, 224), tol=4)
    assert _region_has_color(image, legend_box, (107, 114, 128), tol=15)
    # gt truth line swatch
    assert _region_has_color(image, legend_box, render_grade.TRUTH, tol=4)
