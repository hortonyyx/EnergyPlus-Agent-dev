"""J wiring locks — flow's reading stage routes BY PRODUCT CONTRACT.

Measured before this file (dispatch J §一): ``reading_grade.grade`` and the
elevation dimension had ZERO production callers — flow scored every reading
run on the legacy stroke scorer.  These locks hold the wire in place:

  * the classifier deciding the route is vector_contract's, REUSED read-only
    (⛔ no second classifier, ⛔ no filename routing);
  * an as-drawn product, fed through flow's real typed entry, comes out as a
    graded ``score_vs_gt.json`` + per-view ``grade.png`` with NO hand-called
    API (the dispatch's target state, exercised end to end);
  * a legacy product is NOT hijacked — the branch returns None and today's
    typed/legacy path keeps it (⛔ the old path is not deleted);
  * a mixed run's non-as-drawn views are NAMED as leftovers, never dropped.

The fixtures are the real shipped gt bundle and the real prototype products.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.judge.as_drawn.flow_wiring import (
    AS_DRAWN_CONTRACTS,
    UnknownAsDrawnView,
    grade_as_drawn_attempt,
    resolve_elevation_view_id,
    resolve_plan_view_id,
    split_output_by_contract,
)

REPO = Path(__file__).resolve().parents[1]
GT = json.loads((REPO / "case_tests/test_baseline/gt/sm25-L_anchor/gt.json").read_text())
GT_SOURCES = REPO / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
PROTOTYPE = REPO / "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"


def _doc(name: str) -> dict:
    return json.loads((PROTOTYPE / f"{name}.json").read_text())


# ═══════════════════ the route is decided by the reused classifier ═══════════
def test_plan_product_is_routed_by_its_declared_contract():
    """sm25's real v2 plan product classifies as the as-drawn PLAN contract —
    the same answer 1_correction's ledger gives it (one classifier, two
    consumers).  Goes red if the wire keys on anything but the contract
    (e.g. a filename regex of its own).
    """
    decisions = split_output_by_contract({"1f_view": _doc("sm25_1f_v2")})
    assert decisions["1f_view"].contract_id in AS_DRAWN_CONTRACTS
    assert decisions["1f_view"].contract_id == "as_drawn_plan"


def test_elevation_product_is_routed_by_its_declared_contract():
    decisions = split_output_by_contract({"East_view": _doc("sm25_east_as_drawn")})
    assert decisions["East_view"].contract_id in AS_DRAWN_CONTRACTS
    assert decisions["East_view"].contract_id == "as_drawn_elevation_v0"


def test_a_legacy_reading_view_is_not_routed_to_the_as_drawn_judges():
    """The legacy stroke shape must NOT be hijacked: the route returns a
    non-as-drawn decision and the branch (next test) leaves it alone.  Goes
    red if the wire grows its own notion of "looks like a product" that
    swallows the legacy format.
    """
    legacy_view = {"schema_version": 1, "strokes": [
        {"pen": "wall", "coords": [[0, 0], [10, 0]]}]}
    decisions = split_output_by_contract({"1f_view": legacy_view})
    assert decisions["1f_view"].contract_id not in AS_DRAWN_CONTRACTS


def test_malformed_products_classify_never_raise():
    """Classifier discipline #6 (never raises) is the wire's inlet too: junk
    yields ``unknown``, which is named as a leftover — ⛔ not an exception out
    of the scoring path."""
    decisions = split_output_by_contract({"junk": {"hello": [1, 2, 3]},
                                          "notdict": 42})
    assert decisions["junk"].contract_id not in AS_DRAWN_CONTRACTS
    assert decisions["notdict"].contract_id not in AS_DRAWN_CONTRACTS


# ═══════════════════ view identity: declaration, then stem rules ═════════════
def test_plan_and_elevation_identities_resolve():
    assert resolve_plan_view_id(_doc("sm25_1f_v2"), GT) == "plan-F1"
    assert resolve_plan_view_id(_doc("sm25_2f_v2"), GT) == "plan-F2"
    assert resolve_elevation_view_id(_doc("sm25_east_as_drawn"), GT) == "East_view"


def test_unresolvable_identity_fails_loudly():
    """Grading against the WRONG view's answer launders one facade's answer
    onto another — an unresolvable identity stops the branch.  Goes red if
    anyone turns this into a default view / quiet skip.
    """
    with pytest.raises(UnknownAsDrawnView):
        resolve_elevation_view_id({"image": "case_data/Nope_view.png"}, GT)
    with pytest.raises(UnknownAsDrawnView):
        resolve_plan_view_id({"image": "case_data/basement_view.png"}, GT)


# ═══════════════════ the wire end to end, real gt and real products ══════════
def test_elevation_view_grades_through_the_wire(tmp_path):
    """Dispatch target state, exercised: one as-drawn elevation view goes in,
    the bundle + per-view grade json + png land in the attempt dir — no
    hand-called API.  Goes red if the wire stops writing any of the three.
    """
    bundle = grade_as_drawn_attempt({"East_view": _doc("sm25_east_as_drawn")},
                                    gt=GT, gt_sources_dir=GT_SOURCES,
                                    attempt_dir=tmp_path)
    assert bundle["schema"] == "as_drawn_grade_bundle_v1"
    (view,) = bundle["views"]
    assert view["grade_version"] == "elevation_grade_v1"
    assert view["denominator"]["floors"] == ["F1", "F2"]     # whole facade
    assert view["denominator"]["openings"] == 13
    assert Path(view["grade_json"]).exists()
    assert Path(view["grade_png"]).exists() and Path(view["grade_png"]).stat().st_size > 0
    assert (tmp_path / "score_vs_gt.json").exists()


def test_mixed_run_names_its_leftovers(tmp_path):
    """A run carrying an as-drawn view AND a junk file: the junk file is NAMED
    with its contract id, ⛔ never silently dropped (F-64's shape).  Goes red
    if leftovers stop being itemised.
    """
    bundle = grade_as_drawn_attempt(
        {"East_view": _doc("sm25_east_as_drawn"), "junk": {"hello": 1}},
        gt=GT, gt_sources_dir=GT_SOURCES, attempt_dir=tmp_path)
    assert [l["stem"] for l in bundle["leftover_views"]] == ["junk"]
    assert bundle["leftover_views"][0]["contract"] == "unknown"
    assert len(bundle["views"]) == 1


def test_plan_view_grades_through_the_wire(tmp_path):
    """The plan leg of the wire, on the real product: denominator derived live
    from the case's SIGNED DXF (hash-bound, 110 targets on plan-F1) and the
    UNTOUCHED plan grader's verdict rides out.  Goes red if the plan wire
    loses the signed-source binding (e.g. falls back to a filename glob).
    """
    bundle = grade_as_drawn_attempt({"1f_view": _doc("sm25_1f_v2")},
                                    gt=GT, gt_sources_dir=GT_SOURCES,
                                    attempt_dir=tmp_path)
    (view,) = bundle["views"]
    assert view["grade_version"] == "reading_grade_v1"
    assert view["denominator"]["view"] == "plan-F1"
    assert view["denominator"]["targets"] == 110          # measured on this fixture
    assert view["scores"]["C1_C2_targets_drawn_pct"] > 0.0


# ═══════════════ flow's typed entry: the branch engages, and ONLY for these ══
def test_flow_typed_entry_routes_as_drawn_output_to_the_branch(tmp_path,
                                                               monkeypatch):
    """The lock on the actual insertion point: ``_grade_typed_attempt_artifacts``
    with an as-drawn output.json must take the as-drawn branch (before any
    view-manifest/bindings requirement), and with a legacy output must NOT.
    Monkeypatched dispatcher so this lock isolates ROUTING, not grading.
    """
    import scripts.tool_scripts.run_stage as rs

    calls = []
    monkeypatch.setattr(
        "src.agent.judge.as_drawn.flow_wiring.grade_as_drawn_attempt",
        lambda *a, **k: calls.append(k) or {"schema": "as_drawn_grade_bundle_v1",
                                            "views": [], "leftover_views": []})

    document = type("D", (), {"model_dump_json": lambda self: json.dumps(GT)})()
    attempt = tmp_path / "001"
    attempt.mkdir()
    (attempt / "output.json").write_text(json.dumps(
        {"East_view": _doc("sm25_east_as_drawn")}))

    result = rs._grade_as_drawn_reading_branch(
        "sm25-L_anchor", attempt, document, json.loads((attempt / "output.json").read_text()))
    assert result is not None and calls, "as-drawn output did not take the branch"
    assert calls[0]["gt_sources_dir"].name == "sm25-L_anchor"

    # legacy output: the branch declines and today's path keeps the run
    legacy = {"1f_view": {"schema_version": 1, "strokes": []}}
    assert rs._grade_as_drawn_reading_branch(
        "sm25-L_anchor", attempt, document, legacy) is None


def test_branch_result_shape_matches_the_typed_contract(tmp_path):
    """What the branch returns must plug into the same slots the typed path
    fills (``score_vs_gt`` / ``grade`` / ``score_criteria``), so flow's
    downstream reporting never learns a second dialect.  Goes red if the
    branch invents its own keys for these.
    """
    import scripts.tool_scripts.run_stage as rs

    document = type("D", (), {"model_dump_json": lambda self: json.dumps(GT)})()
    attempt = tmp_path / "002"
    attempt.mkdir()
    (attempt / "output.json").write_text(json.dumps(
        {"East_view": _doc("sm25_east_as_drawn")}))
    result = rs._grade_as_drawn_reading_branch(
        "sm25-L_anchor", attempt, document,
        json.loads((attempt / "output.json").read_text()))
    assert set(result) >= {"score_vs_gt", "grade", "score_criteria"}
    assert Path(result["score_vs_gt"]).exists()
    assert result["score_criteria"], "no criterion was derived from the grades"
    assert all({"id", "name", "passed"} <= set(c) for c in result["score_criteria"])
