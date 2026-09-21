"""Direction evidence must preserve ambiguity and independently measured spans."""
import copy

import pytest

from src.agent.geometry.facade_span_comparison import compare


def observations():
    return {
        "plan": {"axis_anchors": [[0, 0], [100, 10]],
                 "openings": [{"id": "p", "pixels": [10, 30]}]},
        "elevation": {"axis_anchors": [[200, 0], [400, 10]],
                      "openings": [{"id": "e", "pixels": [340, 380]}]},
    }


def test_reverse_and_reversed_pixel_anchor_order():
    raw = observations()
    before = copy.deepcopy(raw)
    result = compare(raw)
    assert raw == before
    assert result["direction_separation"]["lower_residual_direction"] == "elevation_reverse"
    assert result["directions"]["elevation_reverse"]["max_abs_endpoint_residual_m"] == 0
    raw["elevation"]["axis_anchors"] = [[400, 0], [200, 10]]
    assert compare(raw)["direction_separation"]["lower_residual_direction"] == "elevation_forward"


def test_symmetric_empty_and_missing_openings_do_not_establish_direction():
    raw = observations()
    raw["plan"]["openings"][0]["pixels"] = [40, 60]
    raw["elevation"]["openings"][0]["pixels"] = [280, 320]
    assert not compare(raw)["direction_separation"]["relative_error_separated"]
    raw["elevation"]["openings"].append({"id": "extra", "pixels": [350, 360]})
    result = compare(raw)
    assert not result["direction_separation"]["relative_error_separated"]
    forward = result["directions"]["elevation_forward"]
    assert forward["pairs_by_centre"] == []
    assert forward["mean_abs_endpoint_residual_m"] is None
    assert len(forward["unpaired_plan"]) == 1
    assert len(forward["unpaired_elevation"]) == 2
    raw["plan"]["openings"] = raw["elevation"]["openings"] = []
    assert not compare(raw)["direction_separation"]["relative_error_separated"]


@pytest.mark.parametrize("extra_pixels", [[1, 5], [45, 50]])
def test_count_mismatch_does_not_claim_pairs_or_drop_early_and_middle_extras(extra_pixels):
    raw = {
        "plan": {"axis_anchors": [[0, 0], [100, 10]],
                 "openings": [{"id": "p1", "pixels": [20, 30]},
                              {"id": "p2", "pixels": [70, 80]}]},
        "elevation": {"axis_anchors": [[0, 0], [100, 10]],
                      "openings": [{"id": "e1", "pixels": [20, 30]},
                                   {"id": "e2", "pixels": [70, 80]},
                                   {"id": "extra", "pixels": extra_pixels}]},
    }
    result = compare(raw)
    assert result["schema_version"] == "facade_span_direction_probe_v2"
    assert not result["direction_separation"]["relative_error_separated"]
    for direction in result["directions"].values():
        assert direction["pairs_by_centre"] == []
        assert direction["mean_abs_endpoint_residual_m"] is None
        assert {row["id"] for row in direction["unpaired_plan"]} == {"p1", "p2"}
        assert {row["id"] for row in direction["unpaired_elevation"]} == {"e1", "e2", "extra"}


def test_relative_separation_does_not_claim_absolute_fit():
    raw = {
        "plan": {"axis_anchors": [[0, 0], [100, 10]],
                 "openings": [{"id": "p", "pixels": [0, 10]}]},
        "elevation": {"axis_anchors": [[0, 0], [100, 10]],
                      "openings": [{"id": "e", "pixels": [40, 50]}]},
    }
    result = compare(raw)
    assert result["directions"]["elevation_forward"]["mean_abs_endpoint_residual_m"] == 4
    assert result["directions"]["elevation_reverse"]["mean_abs_endpoint_residual_m"] == 5
    assert result["direction_separation"]["relative_error_separated"]
    assert result["direction_separation"]["absolute_fit_status"] == "not_evaluated"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 1e999])
def test_nonfinite_nested_evidence_is_rejected(value):
    raw = observations()
    raw["plan"]["openings"][0]["evidence"] = {"confidence": value}
    with pytest.raises(ValueError, match="finite"):
        compare(raw)


@pytest.mark.parametrize("pixels", [[-1, 30], [10, float("nan")], [10, 10], [True, 30]])
def test_invalid_observations_are_rejected(pixels):
    raw = observations()
    raw["plan"]["openings"][0]["pixels"] = pixels
    with pytest.raises(ValueError):
        compare(raw)


def test_unequal_axis_lengths_and_boolean_tolerance_are_rejected():
    raw = observations()
    with pytest.raises(ValueError):
        compare(raw, True)
    raw["elevation"]["axis_anchors"][1][1] = 20
    with pytest.raises(ValueError, match="same L"):
        compare(raw)
