import copy
import json
from pathlib import Path

from src.agent.geometry.bim_delivery import summarize_delivery
from src.agent.geometry.opening_review import facade_inventory, review_openings
from tests.test_opening_review import _digest, _facade_review, _images, _source


RUN06 = Path(__file__).resolve().parents[1] / "AI_agent/logs/experiments/2026-09-10_bim_agent_sm21_run06"


def _json(relative):
    return json.loads((RUN06 / relative).read_text())


def _scope(summary, floor_id, kind):
    return next(row for row in summary["opening_review_scopes"]
                if row["floor_id"] == floor_id and row["kind"] == kind)


def test_run06_candidate02_reports_two_follow_up_reviews_and_unreviewed_windows():
    source = _json("candidate_02/source_model.json")
    reviews = [_json("opening_reviews/review_001.json"), _json("opening_reviews/review_002.json")]

    summary = summarize_delivery(source, reviews)

    assert summary["source_validation"] == source["validation"]
    assert summary["counts"] == {"spaces": 14, "boundaries": 84, "openings": 28,
                                 "connections": 14, "unbuilt_openings": 0, "unsupported": 0}
    assert summary["generation"]["unresolved"] == source["generation"]["unresolved"]
    assert [row["review_ref"] for row in summary["current_reviews"]] == [
        "opening_reviews/review_001.json", "opening_reviews/review_002.json"]
    assert summary["stale_reviews"] == []
    assert _scope(summary, "F1", "door")["review_status"] == "observations_require_follow_up"
    assert _scope(summary, "F2", "door")["review_status"] == "observations_require_follow_up"
    assert _scope(summary, "F1", "window")["review_status"] == "not_reviewed"
    assert summary["drawing_fidelity"] == "not_evaluated"


def test_run06_candidate03_does_not_inherit_candidate02_reviews_after_notes_change():
    source = _json("candidate_03/source_model.json")
    reviews = [_json("opening_reviews/review_001.json"), _json("opening_reviews/review_002.json")]

    summary = summarize_delivery(source, reviews)

    assert summary["current_reviews"] == []
    assert [row["stale_reason"] for row in summary["stale_reviews"]] == [
        "source_model_sha256_mismatch", "source_model_sha256_mismatch"]
    assert all(row["review_status"] == "not_reviewed" for row in summary["opening_review_scopes"])


def test_partial_or_uncertain_evidence_cannot_become_a_consistency_pass():
    source = _json("candidate_02/source_model.json")
    source_hash = source["source_model_sha256"]
    partial = {
        "source_model_sha256": source_hash,
        "review_file": "partial.json",
        "review_scope": {"floor_id": "F1", "kind": "window", "coverage": "partial"},
        "image": {"name": "detail.png", "sha256": "a" * 64},
        "conclusion": "consistent_with_supplied_observations",
        "findings": [],
    }
    uncertain = {
        "source_model_sha256": source_hash,
        "review_file": "uncertain.json",
        "review_scope": {"floor_id": "F2", "kind": "window", "coverage": "complete"},
        "image": {"name": "f2.png", "sha256": "b" * 64},
        "conclusion": "consistent_with_supplied_observations",
        "findings": [{"code": "observation_pending"}],
    }

    summary = summarize_delivery(source, [partial, uncertain])

    assert _scope(summary, "F1", "window")["review_status"] == "partial"
    assert _scope(summary, "F2", "window")["review_status"] == "observations_require_follow_up"


def test_later_complete_same_image_replaces_old_risk_but_other_image_risk_remains():
    source = _json("candidate_02/source_model.json")
    source_hash = source["source_model_sha256"]
    base = {
        "source_model_sha256": source_hash,
        "review_scope": {"floor_id": "F1", "kind": "window", "coverage": "complete"},
    }
    old = {**base, "review_file": "old.json", "image": {"name": "f1.png", "sha256": "a" * 64},
           "conclusion": "observations_require_follow_up", "findings": [{"code": "observation_pending"}]}
    replacement = {**base, "review_file": "replacement.json", "image": {"name": "f1.png", "sha256": "a" * 64},
                   "conclusion": "consistent_with_supplied_observations", "findings": []}
    other_image = {**base, "review_file": "other.json", "image": {"name": "elevation.png", "sha256": "b" * 64},
                   "conclusion": "observations_require_follow_up", "findings": [{"code": "wrong_connection"}]}

    summary = summarize_delivery(source, [old, replacement, other_image])
    scope = _scope(summary, "F1", "window")

    assert scope["effective_complete_review_refs"] == ["replacement.json", "other.json"]
    assert scope["superseded_review_refs"] == ["old.json"]
    assert scope["finding_codes"] == ["wrong_connection"]
    assert scope["review_status"] == "observations_require_follow_up"


def test_complete_consistency_is_not_downgraded_by_partial_coverage_notice_alone():
    source = _json("candidate_02/source_model.json")
    source_hash = source["source_model_sha256"]
    complete = {
        "source_model_sha256": source_hash,
        "review_file": "complete.json",
        "review_scope": {"floor_id": "F1", "kind": "window", "coverage": "complete"},
        "image": {"name": "plan.png", "sha256": "a" * 64},
        "conclusion": "consistent_with_supplied_observations",
        "findings": [],
    }
    partial = {
        "source_model_sha256": source_hash,
        "review_file": "detail.json",
        "review_scope": {"floor_id": "F1", "kind": "window", "coverage": "partial"},
        "image": {"name": "detail.png", "sha256": "b" * 64},
        "conclusion": "observations_require_follow_up",
        "findings": [{"code": "partial_review_not_complete"}],
    }

    summary = summarize_delivery(source, [complete, partial])
    scope = _scope(summary, "F1", "window")

    assert scope["partial_review_refs"] == ["detail.json"]
    assert scope["finding_codes"] == ["partial_review_not_complete"]
    assert scope["review_status"] == "consistent_with_supplied_observations"


def _facade_reports(source, kind):
    ids = {"window": {"South": "W1"}, "door": {"West": "DOUT"}}[kind]
    reports = []
    for facade in ("North", "South", "East", "West"):
        opening_id = ids.get(facade)
        marks = [] if opening_id is None else [{
            "mark_id": f"{facade}-{kind}", "box": [1, 2, 10, 12], "opening_ids": [opening_id],
            "space_ids": ["A"], "basis": "visible", "note": f"{facade} facade",
        }]
        report = review_openings(source, _facade_review(facade, kind=kind, marks=marks), _images())
        report["review_file"] = f"{facade}-{kind}.json"
        reports.append(report)
    return reports


def test_facade_delivery_requires_each_exterior_direction_including_empty_facades():
    source = _source()
    reports = _facade_reports(source, "window")

    incomplete = summarize_delivery(source, reports[:-1])
    assert _scope(incomplete, "F1", "window")["review_status"] == "partial"
    west = next(row for row in incomplete["facade_review_scopes"]
                if row["floor_id"] == "F1" and row["kind"] == "window" and row["facade"] == "West")
    assert west["built_count"] == 0
    assert west["review_status"] == "not_reviewed"

    merged = summarize_delivery(source, reports)
    assert _scope(merged, "F1", "window")["review_status"] == "consistent_with_supplied_observations"
    assert [row["facade"] for row in merged["facade_review_scopes"]
            if row["floor_id"] == "F1" and row["kind"] == "window"] == ["North", "South", "East", "West"]


def test_facade_delivery_does_not_silently_pass_interior_openings():
    source = _source()
    summary = summarize_delivery(source, _facade_reports(source, "door"))
    scope = _scope(summary, "F1", "door")

    assert scope["review_status"] == "partial"
    assert scope["facade_coverage"]["non_facade_openings"] == [{
        "opening_id": "D1", "kind": "door", "floor_id": "F1", "facade": None, "reason": "not_exterior",
    }]


def test_unsupported_zero_opening_exterior_wall_blocks_facade_only_whole_floor_pass():
    source = _source()
    # This is a source-model fixture, not a request to add diagonal geometry
    # support.  The changed wall is exterior and has no opening, so old
    # opening-only enumeration would have omitted it entirely.
    boundary = next(row for row in source["boundaries"] if row["id"] == "space/A/wall/2")
    boundary["vertices"] = [[2.0, 2.0, 0.0], [0.5, 2.5, 0.0],
                            [0.5, 2.5, 3.0], [2.0, 2.0, 3.0]]
    source["source_model_sha256"] = _digest({key: value for key, value in source.items()
                                              if key != "source_model_sha256"})

    facade_data = facade_inventory(source)
    assert facade_data["floors"][0]["unsupported_exterior_boundaries"] == [{
        "boundary_id": "space/A/wall/2", "reason": "host_direction_unsupported",
    }]
    facade_only = summarize_delivery(source, _facade_reports(source, "window"))
    scope = _scope(facade_only, "F1", "window")
    assert scope["review_status"] == "partial"
    assert scope["facade_coverage"]["unsupported_exterior_boundaries"] == [{
        "boundary_id": "space/A/wall/2", "reason": "host_direction_unsupported",
    }]

    # An old whole-floor plan review is intentionally unchanged: it does not
    # claim a facade-only aggregation and retains its established semantics.
    plan = review_openings(source, {
        "floor_id": "F1", "kind": "window", "image": "plan.png", "coverage": "complete",
        "marks": [{"mark_id": "window", "box": [1, 2, 10, 12], "opening_ids": ["W1"],
                   "space_ids": ["A"], "basis": "visible", "note": "plan window"}],
    }, _images())
    plan["review_file"] = "plan.json"
    assert _scope(summarize_delivery(source, [plan]), "F1", "window")["review_status"] == (
        "consistent_with_supplied_observations")
