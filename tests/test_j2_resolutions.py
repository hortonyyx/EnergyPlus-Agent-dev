"""J-2 locks: two grid resolutions, each declared once, each consumed, never equal.

MEASURED before writing these locks (2026-09-06): the rule "gt 1 mm / pipeline
10 mm, each declared and each consumed, ⛔ not required equal" existed only in
guide §15.11 prose — no code declared either number as a resolution and no
grader read a declaration.  These locks hold the shape the dispatch asked for:

  * a declaration that changes moves the grader's inputs (no dead reading),
  * a missing gt declaration fails LOUDLY (never a silent default),
  * the two sides' defaults stay deliberately UNEQUAL — collapsing them is the
    exact "unify to one grid" ruling §15.11 exists to forbid.

Every lock here has a concrete way to go red, named in its own comment.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.judge.as_drawn.resolutions import (
    GT_RESOLUTION_M,
    GT_DECLARATION_POINTER,
    PIPELINE_OUTPUT_RESOLUTION_M,
    ResolutionDeclarationMissing,
    quantization_band_m,
    read_gt_resolution,
    read_product_resolution,
    snap_to_resolution,
)

REAL_GT = (Path(__file__).resolve().parents[1]
           / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json")


def _gt_with_tolerance(value: float | None) -> dict:
    """A minimal gt-shaped document whose declaration says ``value``.

    Same pointer shape as the real answer root
    (``generator.tolerances.dxf_axis_alignment_tolerance_m``), so the reader is
    exercised against the contract, not against a convenient key.
    """
    doc: dict = {"generator": {"tolerances": {}}}
    if value is not None:
        doc["generator"]["tolerances"]["dxf_axis_alignment_tolerance_m"] = value
    return doc


# ---------------------------------------------------------------- declaration
def test_gt_declaration_is_read_from_the_answer_root_itself():
    """The declaration point is real, not aspirational: sm25's shipped gt.json
    declares 0.001 at the pointer this module reads.

    Goes red if the reader drifts off the pointer (reads a different field) or
    if the gt bundle stops carrying the declaration.
    """
    declaration = read_gt_resolution(json.loads(REAL_GT.read_text()))
    assert declaration.value_m == pytest.approx(0.001)
    assert declaration.declared is True
    assert declaration.source == "/" + "/".join(GT_DECLARATION_POINTER)


def test_a_different_gt_declaration_moves_the_readout():
    """J-2's core demand on the gt side: feed a gt declaring 2 mm, the reader
    hands back 2 mm.  Goes red the moment the reader hard-codes the default.
    """
    assert read_gt_resolution(_gt_with_tolerance(0.002)).value_m == pytest.approx(0.002)


def test_missing_gt_declaration_fails_loudly():
    """A gt with no grid declaration is a different contract — loud, not defaulted.

    Goes red if anyone "fixes" the loud path into a silent fallback to
    GT_RESOLUTION_M (the failure F-126 closed on the denominator side).
    """
    with pytest.raises(ResolutionDeclarationMissing):
        read_gt_resolution(_gt_with_tolerance(None))


def test_non_positive_gt_declaration_is_not_a_grid():
    """0 / negative / non-numeric declarations carry no grid and must not be
    graded against.  Goes red if validation is dropped from the reader.
    """
    for bad in (0, -0.001, "coarse"):
        with pytest.raises(ResolutionDeclarationMissing):
            read_gt_resolution(_gt_with_tolerance(bad))


# ------------------------------------------------------------------ product side
def test_product_declaration_is_read_and_flagged_as_declared():
    """A product carrying its own ``resolution_m`` is followed verbatim and the
    report can see it was the product's number.  Goes red if the reader ignores
    the field (the dispatch's J-2 lock: the grade must FOLLOW the declaration).
    """
    declaration = read_product_resolution({"resolution_m": 0.05})
    assert declaration.value_m == pytest.approx(0.05)
    assert declaration.declared is True


def test_product_without_declaration_uses_the_named_pipeline_default():
    """Today's v0 elevation products carry no grid field: the signed 10 mm
    pipeline-output grid stands in, NAMED as a default (declared=False), so a
    report never launders a default into the product's own claim.
    """
    declaration = read_product_resolution({})
    assert declaration.value_m == pytest.approx(PIPELINE_OUTPUT_RESOLUTION_M)
    assert declaration.declared is False
    assert "default" in declaration.source


def test_malformed_product_declaration_falls_back_loudly_flagged():
    """A corrupt declaration is not silently consumed: the named default stands
    in and ``declared`` stays False.  Goes red if a corrupt value reaches the
    grader as a grid (e.g. float("5 mm") crashing or "0" zeroing).
    """
    declaration = read_product_resolution({"resolution_m": "5 mm"})
    assert declaration.value_m == pytest.approx(PIPELINE_OUTPUT_RESOLUTION_M)
    assert declaration.declared is False


# --------------------------------------------------------------------- the rule
def test_the_two_defaults_are_deliberately_unequal():
    """§15.11: the two grids are INTENTIONALLY different values; "unify them"
    was ruled out because it would misfire on every comparison.  This lock goes
    red the day someone collapses the two constants onto one number — the exact
    regression the 2026-09-04 ruling was written to stop.
    """
    assert GT_RESOLUTION_M != PIPELINE_OUTPUT_RESOLUTION_M


def test_band_is_half_a_cell_from_each_side():
    """The mechanisation of J-1's "max half a cell" arithmetic.  Goes red if the
    band stops tracking both declarations (e.g. only the product's half-cell).
    """
    assert quantization_band_m(0.001, 0.010) == pytest.approx(0.0055)
    assert quantization_band_m(0.001, 0.5) == pytest.approx(0.2505)


def test_snap_consumes_the_declaration_mechanically():
    """Consumption is a real snap, not a report line: coordinates move onto the
    declared grid.  Goes red if snapping stops moving values (identity) — and
    the second assertion pins the DIRECTION: a coarser declaration moves the
    same coordinate further, so a grader cannot ignore it and stay green here.
    """
    fine = snap_to_resolution(15.3405, 0.001)
    coarse = snap_to_resolution(15.3405, 0.5)
    assert fine == pytest.approx(15.34)      # measured: round(15340.5) is 15340
    assert coarse == pytest.approx(15.5)
    assert abs(coarse - 15.3405) > abs(fine - 15.3405)


def test_non_positive_grid_leaves_the_value_untouched():
    """A malformed grid must not zero out the coordinate system; the boundary
    guard returns the value.  Goes red if the guard is dropped (division by 0).
    """
    assert snap_to_resolution(2.718, 0.0) == pytest.approx(2.718)
