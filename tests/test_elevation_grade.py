"""Elevation-grade locks — the facade dimension of the as-drawn reading judge.

Fixtures are REAL, not synthetic: gt is the shipped sm25-L_anchor answer root
and the products are the four shipped ``as_drawn_elevation_v0`` documents the
2026-08-23 prototype produced.  MEASURED before writing any lock (J §三):

  * gt puts 34 openings on the four facades (East 13 / North 8 / South 7 /
    West 6), every facade's list spanning BOTH floors (all views declare
    floor_ids == ["F1", "F2"]);
  * product and answer coordinates share one axis frame — East's 13 product
    openings line up with gt's 13 answer openings one-to-one with centre
    deviations of 3–23 mm (that spread is WHY J-1 demands a band).

The one lock the dispatch names explicitly (§2.2): a facade that spans two
floors MUST grade whole — ⛔ never "one sheet dropped because it crosses
storeys" (F-89's shape).  Every sm25 facade crosses storeys, so the fixture
inventory for that defect is maximal, not marginal.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.judge.as_drawn.elevation_grade import (
    ElevationTargetsUnavailable,
    ToleranceBelowQuantizationBand,
    elevation_targets,
    grade,
)

REPO = Path(__file__).resolve().parents[1]
GT = json.loads((REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json").read_text())
PROTOTYPE = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"

VIEWS = {"East_view": 13, "North_view": 8, "South_view": 7, "West_view": 6}


def _product(view_id: str) -> dict:
    stem = view_id.removesuffix("_view").lower()
    return json.loads((PROTOTYPE / f"sm25_{stem}_as_drawn.json").read_text())


# ═══════════════════════ the F-89 lock (dispatch §2.2, hard ban) ═════════════
@pytest.mark.parametrize("view_id,expected", sorted(VIEWS.items()))
def test_a_two_storey_facade_grades_whole(view_id: str, expected: int):
    """Every sm25 facade spans F1+F2 and MUST produce a score over its WHOLE
    opening list.

    Goes red in exactly the F-89 shape: any per-floor filter in the targets
    (or the grade) halves the denominator, so ``openings == expected`` fails;
    and ``floors == ["F1", "F2"]`` fails the moment a grader narrows the view
    to one storey.  North is the tightest case for the storey split: its 8
    openings are 4 + 4 across the two floors — a filter on EITHER floor alone
    drops it to 4 and this lock goes red.
    """
    targets = elevation_targets(GT, view_id)
    assert targets["floor_ids"] == ["F1", "F2"]
    assert len(targets["openings"]) == expected
    by_floor = targets["ledger"]["openings_by_floor"]
    assert sum(by_floor.values()) == expected
    assert all(count > 0 for count in by_floor.values()), (
        "a view declared to span two floors graded with an empty one")

    result = grade(_product(view_id), targets, gt=GT)
    assert result["denominator"]["floors"] == ["F1", "F2"]
    assert result["denominator"]["openings"] == expected
    assert len(result["detail"]["openings"]) == expected


def test_north_storeys_both_carry_openings():
    """The storey split itself, pinned: North is 4 (F1) + 4 (F2).  If the
    answer's own view/floor wiring ever silently collapses to one storey this
    names WHICH half vanished, not just that a number changed.
    """
    by_floor = elevation_targets(GT, "North_view")["ledger"]["openings_by_floor"]
    assert by_floor == {"F1": 4, "F2": 4}


# ═══════════════════════ J-1: band, never bitwise ═════════════════════════════
# MEASURED axis facts (2026-09-06, before any tolerance was chosen): under its
# correct along-axis hypothesis EVERY facade's product lines up with gt
# one-to-one to 2–23 mm; the prototype's East/South products share gt's axis
# direction and North/West are mirrored about the facade extent.
AXIS_OF_VIEW = {"East_view": "identity", "South_view": "identity",
                "North_view": "mirror", "West_view": "mirror"}


@pytest.mark.parametrize("view_id", sorted(VIEWS))
def test_honest_products_score_ok_within_the_band(view_id: str):
    """The prototype products deviate from gt by 3–23 mm (measured).  A bitwise
    comparison (``==``) would score them all NOT_FOUND; the band must place
    essentially all of them — under the axis hypothesis the grader reports.
    Goes red if a tolerance collapses to zero / an equality creeps into the
    matcher / the axis picker stops finding the measured direction.
    """
    result = grade(_product(view_id), elevation_targets(GT, view_id), gt=GT)
    assert result["along_axis"]["assumed"] == AXIS_OF_VIEW[view_id]
    scores = result["scores"]
    assert scores["E1_openings_found_pct"] >= 85.0, scores
    assert scores["E1_openings_placed_and_sized_pct"] >= 85.0, scores


def test_the_axis_hypothesis_is_reported_not_smuggled():
    """North's product axis is MIRRORED; the grade says so out loud with both
    hypotheses' placement counts.  A direction problem must be VISIBLE in the
    report, never hidden inside a low score that reads as "the product is bad"
    — and never silently flipped either.  Goes red if the axis report loses
    its counts or its assumed value.
    """
    result = grade(_product("North_view"), elevation_targets(GT, "North_view"), gt=GT)
    report = result["along_axis"]
    assert report["assumed"] == "mirror"
    assert report["explicit"] is False
    assert report["identity_placed"] <= report["mirror_placed"] - 2
    assert report["mirror_placed"] == 8


def test_a_shifted_product_is_not_laundered_by_a_marginal_axis_flip():
    """AXIS_SWITCH_MARGIN earns its keep: shift every East product opening by
    +0.5 m — a REAL misplacement.  Under identity it scores honestly low; the
    mirror hypothesis cannot place it either, so no marginal win flips the
    axis and launders the error.  Goes red if the margin is dropped (a 1-hit
    coincidence would flip) or if the grader starts fitting shifts.
    """
    product = json.loads(json.dumps(_product("East_view")))
    for o in product["openings"]:
        o["x_range_m"] = [v + 0.5 for v in o["x_range_m"]]
    result = grade(product, elevation_targets(GT, "East_view"), gt=GT)
    assert result["along_axis"]["assumed"] == "identity"
    assert result["scores"]["E1_openings_placed_and_sized_pct"] < 100.0


def test_east_grades_thirteen_for_thirteen():
    """East's one-to-one alignment measured in J §三, asserted where it bites:
    13 answer openings, all found, none extra.  Goes red if the greedy pairing
    lets one product opening answer two targets or drops a target.
    """
    result = grade(_product("East_view"), elevation_targets(GT, "East_view"), gt=GT)
    assert result["by_verdict"]["NOT_FOUND"] == 0
    assert result["scores"]["E2_extra_openings"] == 0
    assert result["by_verdict"]["OK"] + result["by_verdict"]["WRONG_SIZE"] == 13


def test_a_missing_opening_scores_not_found():
    """Delete one product opening (North) → exactly that answer opening is
    NOT_FOUND and nothing else changes verdict.  Goes red if the grader
    forgives a miss (the failure a glance never sees) — the lock has teeth in
    the direction the fixture now carries inventory for.
    """
    product = _product("North_view")
    targets = elevation_targets(GT, "North_view")
    honest = grade(product, targets, gt=GT)
    victim_id = honest["detail"]["openings"][0]["matched"]
    product = json.loads(json.dumps(product))      # work on a copy
    product["openings"] = [o for o in product["openings"] if o["id"] != victim_id]
    robbed = grade(product, targets, gt=GT)
    assert robbed["by_verdict"]["NOT_FOUND"] == honest["by_verdict"]["NOT_FOUND"] + 1
    assert robbed["scores"]["E1_openings_found_pct"] < honest["scores"]["E1_openings_found_pct"]


def test_an_invented_opening_bills_as_extra():
    """A product opening no answer explains must be billed (E2) — 多画 in the
    direction a plan-only ruler used to REWARD.  Goes red if E2 goes blind.
    """
    product = json.loads(json.dumps(_product("East_view")))
    product["openings"].append({
        "id": "OFABRICATED", "x_range_m": [30.5, 31.5], "z_range_m": [1.0, 2.0]})
    result = grade(product, elevation_targets(GT, "East_view"), gt=GT)
    assert result["scores"]["E2_extra_openings"] == 1
    assert result["detail"]["extras"][0]["id"] == "OFABRICATED"


# ═══════════════════════ J-2: the grade FOLLOWS the declarations ═════════════
def test_params_report_both_grids_as_consumed():
    """Both declarations ride out with provenance — the default is named as a
    default (v0 products carry no ``resolution_m``).  Goes red if the report
    ever launders the default into the product's own claim.
    """
    result = grade(_product("East_view"), elevation_targets(GT, "East_view"), gt=GT)
    params = result["params"]
    assert params["gt_resolution_m"] == pytest.approx(0.001)
    assert params["gt_resolution_source"].endswith("dxf_axis_alignment_tolerance_m")
    assert params["product_resolution_m"] == pytest.approx(0.010)
    assert params["product_resolution_declared"] is False
    assert params["quantization_band_m"] == pytest.approx(0.0055)


def test_a_coarser_product_declaration_moves_the_grade():
    """THE J-2 lock: same product, one field changed — ``resolution_m`` 0.6 —
    and the grade must follow.  A 0.6 m grid makes the two-sided quantization
    band (0.3005 m) exceed the semantic along band (0.30 m), so the grader
    REFUSES loudly instead of quietly scoring against a band no product could
    meet.  Goes red if the declaration is read but not consumed (report-only),
    or if the refusal is downgraded to a pass.
    """
    product = json.loads(json.dumps(_product("East_view")))
    product["resolution_m"] = 0.6
    with pytest.raises(ToleranceBelowQuantizationBand) as caught:
        grade(product, elevation_targets(GT, "East_view"), gt=GT)
    assert caught.value.band_m == pytest.approx(0.3005)


def test_a_finer_product_declaration_is_consumed_mechanically():
    """A declaration INSIDE the bands is consumed by the snap: a 0.35 m grid
    (band 0.1755 m, under the 0.20 m z tolerance) moves product coordinates
    onto that grid, which visibly changes the reported centre errors.  Goes
    red if snapping becomes identity — the reported errors would be identical.
    """
    targets = elevation_targets(GT, "East_view")
    fine = grade(_product("East_view"), targets, gt=GT)
    coarse = grade(json.loads(json.dumps({**_product("East_view"),
                                          "resolution_m": 0.35})), targets, gt=GT)
    assert coarse["params"]["product_resolution_m"] == pytest.approx(0.35)
    assert coarse["params"]["quantization_band_m"] == pytest.approx(0.1755)
    fine_errs = [r.get("along_centre_err_m") for r in fine["detail"]["openings"]]
    coarse_errs = [r.get("along_centre_err_m") for r in coarse["detail"]["openings"]]
    assert fine_errs != coarse_errs, "declaration consumed as a report line only"


def test_a_coarser_gt_declaration_is_read_not_assumed():
    """The gt side of J-2: a gt declaring 2 mm moves the gt-grid snap and the
    reported band — with the product at its 10 mm default, 0.5*0.002+0.5*0.010.
    Goes red if the gt declaration is hardcoded to the constant.
    """
    gt2 = json.loads(json.dumps(GT))
    gt2["generator"]["tolerances"]["dxf_axis_alignment_tolerance_m"] = 0.002
    result = grade(_product("East_view"), elevation_targets(gt2, "East_view"), gt=gt2)
    assert result["params"]["gt_resolution_m"] == pytest.approx(0.002)
    assert result["params"]["quantization_band_m"] == pytest.approx(0.006)


# ═══════════════════════ structure lines & the empty-denominator guard ══════
def test_structure_lines_grade_and_the_divider_is_ledgered_not_billed():
    """Floor lines (z=0/3.6/7.2) and both end lines must be found; the REAL
    mid-facade divider stroke (East x=6, a chain segment line the drawing
    has) has no answer target, so it is LEDGERED — ⛔ never billed as 多画.
    Goes red if E3 goes blind or if the grader starts scoring against an
    answer it does not own (the two-rulers mistake).
    """
    result = grade(_product("East_view"), elevation_targets(GT, "East_view"), gt=GT)
    assert result["scores"]["E3_structure_lines_pct"] == 100.0
    ledger = result["structure_unexplained"]
    assert "S02" in ledger, ledger        # East's divider at x≈6.0, a real stroke
    assert set(ledger) <= {"S02"}, ledger  # S01/S03 are end lines, S04-S06 floor lines


def test_unknown_view_is_a_loud_failure():
    """A view id gt does not carry fails loudly — an empty denominator is never
    a denominator (F-126's shape, elevation side).  Goes red on silent ``[]``.
    """
    with pytest.raises(ElevationTargetsUnavailable):
        elevation_targets(GT, "Northwest_view")


def test_gt_side_kind_is_reported_not_scored_for_undeclaring_products():
    """v0 products do not declare door/window (``door_window_classified``
    false in their ledger) ⇒ E5 is null, an honest gap — ⛔ not a zero that
    reads as "all wrong" and ⛔ not a fabricated score.  Goes red if someone
    makes E5 guess (score a number with no declaration behind it).
    """
    result = grade(_product("East_view"), elevation_targets(GT, "East_view"), gt=GT)
    assert result["scores"]["E5_opening_kind_pct"] is None
    # but the answer's OWN kinds ride out on every row, so the gap is visible
    assert {row["kind"] for row in result["detail"]["openings"]} == {"door", "window"}
