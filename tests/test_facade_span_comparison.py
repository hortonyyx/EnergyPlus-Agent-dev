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
    assert not compare(raw)["direction_separation"]["direction_distinguishable"]
    raw["elevation"]["openings"].append({"id": "extra", "pixels": [350, 360]})
    result = compare(raw)
    assert not result["direction_separation"]["direction_distinguishable"]
    assert len(result["directions"]["elevation_forward"]["unpaired_elevation"]) == 1
    raw["plan"]["openings"] = raw["elevation"]["openings"] = []
    assert not compare(raw)["direction_separation"]["direction_distinguishable"]


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
