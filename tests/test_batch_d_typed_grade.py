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


# --------------------------------------------------------------------------- #
# L-D4 (MINOR, r3 batchC dispatch §3): internal plan-panel labels — content
# and layout. sol's 2026-08-04 review §S-4 found two independent defects here
# that L-D1/L-D2/L-D3 above never touch (they only check panel titles/legend/
# placeholders): segment/polygon/opening labels were sliced to their last
# 10/14/12 characters (real ids like "F1:boundary:North:0" truncate to
# unreadable fragments), and the claim rail's rows — one per opening, stacked
# upward from the panel's bottom edge — could land inside the plan geometry's
# own interior region once a floor had enough openings (a synthetic
# four-facade fixture put rows for openings 1-3 on top of the South boundary
# and its label). N-16 of that review's mutation table proved the OLD tests
# had zero binding to this: deleting all five internal-label draw calls left
# every existing Batch D test green.
# --------------------------------------------------------------------------- #

def test_L_D4_segment_polygon_opening_labels_are_full_untruncated_text():
    """Every segment/polygon/opening id this fixture produces is longer than
    the old truncation slices (segment ids are 18-20 chars vs the old
    ``[-10:]``, polygon ids vs ``[-14:]``, opening ids like "O-North" are
    short enough to survive ``[-12:]`` by coincidence — so this also proves
    the fixture actually exercises the truncating case for segments/polygons,
    not just a case too short to matter).

    Neuter: reintroduce ``segment.id[-10:]`` / ``polygon.id[-14:]`` in
    render_typed_grade's per-floor loop (or make ``_fit_label_font`` slice
    ``text`` instead of shrinking the font) ⇒ this lock reds — the audit
    ledger's ``label:segment:*`` / ``label:polygon:*`` values stop matching
    the full ids asserted below."""
    doc = make_four_facade_gt_document()
    payload = _all_claims_payload(doc)
    image, audit = render_grade.render_typed_grade(gt_document=doc, payload=payload)

    from src.agent.judge.gt_render_model import gt_to_render_model
    model = gt_to_render_model(doc)
    f1 = model.floors[0]
    assert f1.floor_id == "F1"

    segment_ids = [segment.id for segment in f1.boundary_segments]
    assert segment_ids, "fixture must have at least one boundary segment"
    assert any(len(sid) > 10 for sid in segment_ids), "fixture must exercise the truncating case"
    for sid in segment_ids:
        assert audit[f"label:segment:{sid}"] == sid

    polygon_ids = [polygon.id for polygon in f1.zone_polygons]
    assert polygon_ids, "fixture must have at least one zone polygon"
    for pid in polygon_ids:
        assert audit[f"label:polygon:{pid}"] == pid

    opening_ids = [o.id for o in doc.openings if o.floor_id == "F1"]
    assert opening_ids, "fixture must have at least one F1 opening"
    for oid in opening_ids:
        assert audit[f"label:opening:{oid}"] == oid

    # Batch D §3 companion: a concrete, non-color panel count assertion — the
    # exact number of polygons this floor rendered, not just "some pixel
    # somewhere is non-background".
    assert audit[f"label:floor_polygon_count:{f1.floor_id}"] == str(len(f1.zone_polygons))
    assert image  # sanity: render did not raise


def test_L_D4_claim_rail_reserved_band_stays_free_of_plan_geometry():
    """The exact adversarial shape from sol's review: F1 has one opening per
    facade (4 openings) — the claim rail needs 4 stacked rows. The reserved
    band at the bottom of the plan panel (sized from the ACTUAL opening
    count, ``_TYPED_RAIL_ROW_H``/``_TYPED_RAIL_RESERVE_PAD``) must contain NO
    GT wall/outline/fill colour (TRUTH / GT_FILL / GT_EDGE / REFERENCE) —
    those colours are painted ONLY by the plan geometry (walls, zone-polygon
    fills, the footprint outline), never by the claim rail itself (which only
    ever paints GREEN/ORANGE/RED or the not-applicable hatch), so if any of
    them appear in the reserved band, the geometry's own scale was not
    actually constrained to stay out of rail territory.

    Neuter: drop the ``- rail_reserved`` term from the scale computation in
    render_typed_grade's per-floor loop (reverting to
    ``(height - 2 * margin) / max(max_y - min_y, .1)``) ⇒ this lock reds —
    the plan geometry (walls/fills) is scaled large enough to paint into the
    band this test asserts must stay clear."""
    doc = make_four_facade_gt_document()
    payload = _all_claims_payload(doc)
    image, _audit = render_grade.render_typed_grade(gt_document=doc, payload=payload)

    from src.agent.judge.gt_render_model import gt_to_render_model
    model = gt_to_render_model(doc)
    f1 = model.floors[0]
    num_openings_f1 = sum(1 for o in doc.openings if o.floor_id == "F1")
    assert num_openings_f1 == 4, "fixture must exercise the multi-opening adversarial shape"

    width, height = render_grade._TYPED_PLAN_PANEL_W, render_grade._TYPED_PLAN_PANEL_H
    oy = render_grade._TYPED_FLOOR_TOP
    rail_reserved = num_openings_f1 * render_grade._TYPED_RAIL_ROW_H + render_grade._TYPED_RAIL_RESERVE_PAD
    band_top = int(oy + height - rail_reserved)
    band_box = (0, band_top, width, oy + height)

    for color in (render_grade.TRUTH, render_grade.GT_FILL, render_grade.GT_EDGE, render_grade.REFERENCE):
        assert not _region_has_color(image, band_box, color, tol=4), color
    assert len(f1.zone_polygons) >= 1  # sanity: the floor actually has geometry to have collided
