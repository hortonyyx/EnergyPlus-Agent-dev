import pytest

from src.agent.geometry.dimension_chain import map_dimension_chain


def test_observed_sm24_south_chain_locates_right_window_without_manual_sum():
    result = map_dimension_chain([540, 1500, 2500, 900, 2520, 1500, 540], expected_total=10000)
    assert result["segments"][5]["span_m"] == [7.96, 9.46]
    assert result["closure_error_m"] == 0
    assert "not_independently_verified" in result["evidence_status"]


def test_reverse_facade_keeps_world_spans_ordered_and_exposes_transcription_gap():
    result = map_dimension_chain([540, 4800, 2500, 1600, 540], origin_m=10,
                                 direction=-1, expected_total=10000)
    assert result["segments"][1]["span_m"] == [4.66, 9.46]
    assert result["closure_error_m"] == -0.02
    assert result["end_m"] == 0.02


@pytest.mark.parametrize("kwargs", [
    {"lengths": []}, {"lengths": [-1]}, {"lengths": [float("nan")]},
    {"lengths": [1], "origin_m": float("inf")},
    {"lengths": [1], "direction": 0}, {"lengths": [1], "unit": "cm"},
])
def test_invalid_measurements_are_not_silently_turned_into_coordinates(kwargs):
    with pytest.raises(ValueError):
        map_dimension_chain(**kwargs)
