"""Locks for the legacy (v2-GT) reading scoring envelope defect (2026-08-04).

Background: sm21 is a legacy case (GT ``schema_version=2``) scored through the
legacy branch of the judge.  Today's reading product is wrapped in a ReadingViews
v2 envelope ``{"views": {...}}``.  The legacy branch did not unwrap it, so every
view collapsed into a single bogus ``"views"`` stem, ZERO floors were scored,
yet the headline criteria still reported ``pass`` -- "no paper graded == perfect
score".  Two complementary fixes are locked here:

* F-1a -- ``_legacy_score_attempt_output`` unwraps the envelope exactly once, at
  the single seam that feeds BOTH legacy consumers (plan scorer
  ``_score_reading_attempt_output`` and ``score_reading_elevation_views``).
* F-1b -- ``reading_score_criteria`` treats empty ``scores`` as non-pass for all
  four headline criteria, while leaving the legitimate "GT has no windows"
  branch (non-empty scores, zero windows) untouched.

Fixtures use the REAL sm21 gt and the REAL 07-07 known-good reading artifact
(2 floors / 9:9 plan walls / 7:7 plan windows / 15:15 elevation windows) -- real
scale and real shape, per the project's "no degenerate 2x2 fixture" discipline.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.agent.execution.run_config import GradeConfig
from src.agent.judge.gt import load_gt
from src.agent.judge.reading_score import FloorScore
from src.agent.judge.reading_typed_adapter import identify_reading_contract
from src.agent.judge.score_policy import reading_score_criteria
from scripts.tool_scripts.run_stage import (
    _legacy_score_attempt_output,
    _unwrap_reading_views_envelope,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_ARTIFACT = (
    REPO_ROOT
    / "case_tests/e2e_tests/sm21_anchor/run_2026-07-07_haiku_cv_retest"
    / "0_reading/attempts/001/output.json"
)

# The four headline criteria that the empty-scores guard (F-1b) owns.
HEADLINE = ("walls_complete", "windows_placed", "boundary_complete", "no_oversplit")


pytestmark = pytest.mark.skipif(
    not GOOD_ARTIFACT.exists(),
    reason="real-scale 07-07 sm21 reading artifact is required for this lock",
)


def _criteria(result: dict) -> dict[str, str]:
    return {c["criterion"]: c["suggested_status"] for c in result["score_criteria"]}


def _shift_coordinate_pairs(node):
    """Recursively translate every ``[x, y]`` numeric pair by +1000 m.

    Used to build a realistic *bad* product: every wall/window stroke lands far
    outside any tolerance of the gt, so walls/windows are missed, yet the product
    keeps the same valid shape (same stroke count, same structure) -- a genuine
    mis-read, not a degenerate toy.
    """
    if isinstance(node, dict):
        for key in list(node.keys()):
            node[key] = _shift_coordinate_pairs(node[key])
        return node
    if isinstance(node, list):
        if len(node) == 2 and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in node):
            return [node[0] + 1000.0, node[1] + 1000.0]
        return [_shift_coordinate_pairs(x) for x in node]
    return node


def _bad_product(good: dict) -> dict:
    bad = copy.deepcopy(good)
    for view in bad.values():
        view["strokes"] = [_shift_coordinate_pairs(copy.deepcopy(s)) for s in view["strokes"]]
    return bad


@pytest.fixture(scope="module")
def good_product() -> dict:
    return json.loads(GOOD_ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gt() -> dict:
    return load_gt("sm21_anchor")


def test_good_product_is_real_scale(good_product, gt):
    """Guard against a degenerate fixture: this MUST be the 9/9, 7/7, 15/15 product."""
    result = _legacy_score_attempt_output("0_reading", good_product, gt, grade=GradeConfig())
    assert len(result["scores"]) == 2, "expected both sm21 floors (1f, 2f) scored"
    wall_hits = sum(sc.wall_hits()[0] for sc in result["scores"].values())
    wall_total = sum(sc.wall_hits()[1] for sc in result["scores"].values())
    win_hits = sum(sc.window_hits()[0] for sc in result["scores"].values())
    win_total = sum(sc.window_hits()[1] for sc in result["scores"].values())
    assert (wall_hits, wall_total) == (9, 9)
    assert (win_hits, win_total) == (7, 7)
    summary = result["elevation"].summary()
    assert (summary["gt_total"], summary["placed_hit_total"]) == (15, 15)


def test_envelope_unwrap_helper_is_single_point_and_idempotent():
    # Flat input (the historical contract) is returned unchanged.
    flat = {"1f_view": {"image_kind": "plan"}}
    assert _unwrap_reading_views_envelope(flat) is flat
    # A ReadingViews v2 envelope is flattened to its inner views mapping.
    inner = {"1f_view": {"image_kind": "plan"}, "north_view": {"image_kind": "elevation"}}
    assert _unwrap_reading_views_envelope({"views": inner}) == inner
    # Non-reading / unrecognized shapes are passed through (correction outputs).
    not_reading = {"schema_version": 3, "floors": []}
    assert _unwrap_reading_views_envelope(not_reading) is not_reading
    assert identify_reading_contract(not_reading).contract_id == "unrecognized"


def test_four_cell_matrix_envelope_consumed_in_both_directions(good_product, gt):
    """F-1a discriminating-power matrix (real-scale sm21).

    |            | good product | bad product |
    | envelope   | pass         | severe      |
    | flat       | pass         | severe      |

    The envelope column must equal the flat column in BOTH directions: that is
    the proof the legacy seam now consumes the ReadingViews v2 envelope.  And
    good->pass / bad->severe proves the scorer still discriminates (a neutered
    unwrap that produced empty scores for both would fail the bad->severe cell).
    """
    grade = GradeConfig()
    good_flat = good_product
    good_env = {"views": copy.deepcopy(good_product)}
    bad_flat = _bad_product(good_product)
    bad_env = {"views": _bad_product(good_product)}

    good_flat_r = _legacy_score_attempt_output("0_reading", good_flat, gt, grade=grade)
    good_env_r = _legacy_score_attempt_output("0_reading", good_env, gt, grade=grade)
    bad_flat_r = _legacy_score_attempt_output("0_reading", bad_flat, gt, grade=grade)
    bad_env_r = _legacy_score_attempt_output("0_reading", bad_env, gt, grade=grade)

    # F-1a: the envelope is consumed -- both floors scored in BOTH shapes.
    assert len(good_env_r["scores"]) == len(good_flat_r["scores"]) == 2
    assert len(bad_env_r["scores"]) == len(bad_flat_r["scores"]) == 2

    good_flat_c = _criteria(good_flat_r)
    good_env_c = _criteria(good_env_r)
    bad_flat_c = _criteria(bad_flat_r)
    bad_env_c = _criteria(bad_env_r)

    # good -> pass (all four headline), in BOTH shapes.
    for criterion in HEADLINE:
        assert good_flat_c[criterion] == "pass", criterion
        assert good_env_c[criterion] == "pass", criterion
    # Elevation consumer also received the unwrapped input (15:15 -> pass).
    assert good_flat_c["elevation_windows_placed"] == "pass"
    assert good_env_c["elevation_windows_placed"] == "pass"

    # bad -> failing (walls/windows/boundary severe), in BOTH shapes.  A shifted
    # product draws the same number of walls in wrong places, so no_oversplit
    # legitimately stays pass -- oversplit is about *extra* walls, not misplaced.
    for criterion in ("walls_complete", "windows_placed", "boundary_complete"):
        assert bad_flat_c[criterion] == "severe", criterion
        assert bad_env_c[criterion] == "severe", criterion
    assert bad_flat_c["elevation_windows_placed"] == "severe"
    assert bad_env_c["elevation_windows_placed"] == "severe"

    # Envelope must equal flat in both directions (the unwrap is transparent).
    for criterion in HEADLINE:
        assert good_env_c[criterion] == good_flat_c[criterion], criterion
        assert bad_env_c[criterion] == bad_flat_c[criterion], criterion


def test_empty_scores_makes_all_headline_criteria_non_pass():
    """F-1b 5th cell: empty scores -> all four headline criteria non-pass."""
    criteria = {c["criterion"]: c for c in reading_score_criteria({})}
    for criterion in HEADLINE:
        assert criteria[criterion]["suggested_status"] != "pass", criterion
        assert criteria[criterion]["suggested_status"] == "severe", criterion
        assert "no_data" in criteria[criterion]["evidence"], criterion


def test_empty_scores_guard_fires_end_to_end_through_legacy_seam(gt):
    """F-1b end-to-end: an envelope whose views map to no gt floor yields empty
    scores, and the headline criteria must come out non-pass (not the old false
    pass).  ``{"views": {}}`` is a recognized ReadingViews v2 envelope."""
    assert identify_reading_contract({"views": {}}).contract_id == "reading_views_v2"
    result = _legacy_score_attempt_output("0_reading", {"views": {}}, gt, grade=GradeConfig())
    assert result["scores"] == {}
    criteria = _criteria(result)
    for criterion in HEADLINE:
        assert criteria[criterion] != "pass", criterion


def test_empty_scores_guard_does_not_overfire_on_windowless_floor():
    """F-1b discrimination: a NON-empty scores mapping (a floor WAS scored) that
    legitimately has zero windows must keep ``windows_placed == pass`` -- this is
    the "GT has no windows" case, which is NOT what F-1b targets.  The guard keys
    only on the mechanical fact that ``scores`` is empty."""
    scored = FloorScore(
        floor="Floor 1",
        vwalls=[],
        hwalls=[],
        extra_vwalls=[],
        extra_hwalls=[],
        windows={},
        extra_windows={},
        boundary=None,
    )
    criteria = {c["criterion"]: c["suggested_status"] for c in reading_score_criteria({"1f_view": scored})}
    # Non-empty scores -> guard does not fire -> windows_placed stays pass.
    assert criteria["windows_placed"] == "pass"
