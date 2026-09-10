import copy

import pytest

from src.agent.correction.schema import CorrectedGeometry
from src.agent.geometry.opening_review import opening_inventory, review_openings
from src.agent.geometry.source_bim import build_source_bim
from src.agent.geometry.source_model import _digest


def _source():
    geom = CorrectedGeometry.model_validate({
        "footprint_x": [0, 4], "footprint_y": [0, 2],
        "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3, "cells": [
            {"id": "A", "x": [0, 2], "y": [0, 2]},
            {"id": "B", "x": [2, 4], "y": [0, 2]},
        ]}],
        "windows": [{"id": "W1", "floor": "F1", "facade": "South", "span": [0.4, 1.2], "z": [1, 2], "room": "A"}],
        "openings": [
            {"id": "D1", "kind": "door", "space_id": "A", "other_space_id": "B", "p1": [2, 0.4], "p2": [2, 1.2], "z": [0, 2], "source_refs": ["test:door"]},
            {"id": "DOUT", "kind": "door", "space_id": "A", "other_space_id": None, "p1": [0, 0.4], "p2": [0, 1.2], "z": [0, 2], "source_refs": ["test:outside"]},
        ],
    })
    return build_source_bim(geom)


def _images():
    return {"plan.png": {"size": [100, 80], "sha256": "a" * 64}}


def _review(*, kind="door", coverage="complete", marks=None):
    return {"floor_id": "F1", "kind": kind, "image": "plan.png", "coverage": coverage,
            "marks": marks if marks is not None else [{
                "mark_id": "m1", "box": [1, 2, 10, 12], "opening_ids": ["D1"],
                "space_ids": ["A", "B"], "basis": "visible", "note": "internal door",
            }, {"mark_id": "m2", "box": [20, 2, 30, 12], "opening_ids": ["DOUT"],
                "space_ids": ["A"], "basis": "visible", "note": "outside door"}]}


def test_inventory_exposes_actual_openings_by_floor_and_space_without_mutating_source():
    source = _source()
    before = copy.deepcopy(source)
    inventory = opening_inventory(source)
    floor = inventory["floors"][0]
    assert floor["opening_ids"] == ["D1", "DOUT", "W1"]
    assert floor["counts"] == {"door": 2, "passage": 0, "window": 1}
    assert next(row for row in inventory["spaces"] if row["space_id"] == "A")["opening_ids"] == ["D1", "DOUT", "W1"]
    assert "openings" not in next(row for row in inventory["spaces"] if row["space_id"] == "A")
    assert next(row for row in floor["openings"] if row["id"] == "DOUT")["space_ids"] == ["A"]
    assert source == before


def test_complete_review_flags_extra_model_door_and_reports_per_room_missing_ids():
    report = review_openings(_source(), _review(marks=[_review()["marks"][0]]), _images())
    assert {row["code"] for row in report["findings"]} == {"unaccounted_model_opening"}
    assert report["room_coverage"] == [
        {"space_id": "A", "actual_opening_ids": ["D1", "DOUT"], "actual_opening_count": 2,
         "matched_opening_ids": ["D1"], "matched_opening_count": 1, "missing_opening_ids": ["DOUT"]},
        {"space_id": "B", "actual_opening_ids": ["D1"], "actual_opening_count": 1,
         "matched_opening_ids": ["D1"], "matched_opening_count": 1, "missing_opening_ids": []},
    ]
    assert report["drawing_fidelity"] == "not_evaluated"


def test_unmodeled_observation_and_multiple_or_reused_ids_are_findings():
    marks = [
    {"mark_id": "seen", "box": [1, 2, 10, 12], "opening_ids": [], "space_ids": ["A", "B"], "basis": "visible", "note": "door arc"},
        {"mark_id": "many", "box": [20, 2, 30, 12], "opening_ids": ["D1", "DOUT"], "space_ids": ["A", "B"], "basis": "visible", "note": "bad grouping"},
        {"mark_id": "again", "box": [40, 2, 50, 12], "opening_ids": ["D1"], "space_ids": ["A", "B"], "basis": "visible", "note": "duplicate"},
    ]
    codes = {row["code"] for row in review_openings(_source(), _review(marks=marks), _images())["findings"]}
    assert {"unmodeled_observed_mark", "mark_multiple_opening_ids", "opening_id_reused", "unaccounted_model_opening"} <= codes


def test_unmodeled_uncertain_mark_is_still_pending_and_inventory_names_unbuilt_scope():
    source = _source()
    source["unbuilt_openings"] = [{"id": "not-built"}]
    source["unsupported"] = [{"id": "ambiguous"}]
    source["source_model_sha256"] = _digest({key: value for key, value in source.items() if key != "source_model_sha256"})
    report = review_openings(source, _review(marks=[{
        "mark_id": "seen", "box": [1, 2, 10, 12], "opening_ids": [], "space_ids": ["A"],
        "basis": "uncertain", "note": "possible opening",
    }]), _images())
    assert {"unmodeled_observed_mark", "observation_pending", "unaccounted_model_opening"} <= {row["code"] for row in report["findings"]}
    inventory = opening_inventory(source)
    assert inventory["scope"]["unbuilt_opening_ids"] == ["not-built"]
    assert inventory["scope"]["unsupported_observation_count"] == 1


def test_wrong_connection_and_pending_basis_are_explicit_not_a_fidelity_pass():
    review = _review(marks=[{**_review()["marks"][0], "space_ids": ["A"], "basis": "inferred"}])
    report = review_openings(_source(), review, _images())
    assert {row["code"] for row in report["findings"]} >= {"mark_space_ids_mismatch", "observation_pending", "unaccounted_model_opening"}
    assert report["conclusion"] == "observations_require_follow_up"


def test_partial_review_never_claims_complete_coverage_or_consistency():
    review = _review(coverage="partial", marks=[_review()["marks"][0]])
    report = review_openings(_source(), review, _images())
    assert [row["code"] for row in report["findings"]] == ["partial_review_not_complete"]
    assert report["conclusion"] != "consistent_with_supplied_observations"


@pytest.mark.parametrize("mutate", [
    lambda review: review.update(image="missing.png"),
    lambda review: review["marks"][0].update(box=[1, 2, float("nan"), 12]),
    lambda review: review["marks"][1].update(mark_id="m1"),
    lambda review: review.update(extra=True),
])
def test_invalid_pixels_or_schema_are_rejected_and_source_is_unchanged(mutate):
    source = _source()
    before = copy.deepcopy(source)
    review = _review()
    mutate(review)
    with pytest.raises(ValueError, match="invalid opening review"):
        review_openings(source, review, _images())
    assert source == before


def test_duplicate_box_and_unknown_floor_are_findings_not_rejections():
    duplicate = _review()
    duplicate["marks"][1]["box"] = [1, 2, 10, 12]
    assert "duplicate_mark_box" in {row["code"] for row in review_openings(_source(), duplicate, _images())["findings"]}
    unknown = _review()
    unknown["floor_id"] = "F404"
    assert "unknown_floor" in {row["code"] for row in review_openings(_source(), unknown, _images())["findings"]}
