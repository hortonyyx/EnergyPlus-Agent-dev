"""B6 reading vocabulary: line-style/visibility and non-rectangular envelopes."""

from __future__ import annotations

from src.agent.reading import ReadingView, Stroke, parse_reading_view
from src.validator.checks.reading import check_reading_view
from src.validator.checks.schema import CheckLayer, CheckStatus


def _elevation_view(strokes: list[dict]) -> ReadingView:
    return ReadingView.model_validate(
        {
            "image_kind": "elevation",
            "facade": {"view_facade": "South"},
            "uncaptured": [],
            "strokes": strokes,
        }
    )


def _window_stroke(stroke_id: str, *, line_style: str, visibility: str) -> dict:
    return {
        "id": stroke_id,
        "pen": "window",
        "geometry": {"kind": "rect", "x_range_m": [1.0, 2.0], "y_range_m": [1.0, 2.0]},
        "provenance": "seen",
        "confidence": "high",
        "line_style": line_style,
        "visibility": visibility,
    }


def _assert_gate_invariants_pass(view: ReadingView) -> None:
    report = check_reading_view(view)
    failed_invariants = [
        result.check_id
        for result in report.results
        if result.layer == CheckLayer.INVARIANT and result.status == CheckStatus.FAIL
    ]
    assert report.passed, [result.message for result in report.blocking()]
    assert failed_invariants == []


def test_solid_visible_window_is_a_normal_visible_observation():
    view = _elevation_view([_window_stroke("W-visible", line_style="solid", visibility="visible")])

    stroke = view.strokes[0]
    assert stroke.line_style == "solid"
    assert stroke.visibility == "visible"
    _assert_gate_invariants_pass(view)


def test_dashed_hidden_window_is_retained_as_hidden_observation():
    view = _elevation_view([_window_stroke("W-hidden", line_style="dashed", visibility="hidden")])

    stroke = view.strokes[0]
    assert stroke.line_style == "dashed"
    assert stroke.visibility == "hidden"
    restored = ReadingView.model_validate_json(view.model_dump_json())
    assert restored.strokes[0].line_style == "dashed"
    assert restored.strokes[0].visibility == "hidden"
    _assert_gate_invariants_pass(view)


def test_dashed_window_style_is_not_silently_coerced_to_solid():
    source = _window_stroke("W-dashed", line_style="dashed", visibility="hidden")

    stroke = Stroke.model_validate(source)
    restored = Stroke.model_validate_json(stroke.model_dump_json())
    assert restored.line_style == "dashed"
    assert restored.line_style != "solid"
    assert restored.visibility == "hidden"


def test_overlapping_solid_and_dashed_windows_remain_independent_strokes():
    view = _elevation_view(
        [
            _window_stroke("W-solid", line_style="solid", visibility="visible"),
            _window_stroke("W-dashed", line_style="dashed", visibility="hidden"),
        ]
    )

    assert [stroke.id for stroke in view.strokes] == ["W-solid", "W-dashed"]
    assert len({stroke.id for stroke in view.strokes}) == 2
    assert [(stroke.line_style, stroke.visibility) for stroke in view.strokes] == [
        ("solid", "visible"),
        ("dashed", "hidden"),
    ]
    _assert_gate_invariants_pass(view)


def test_line_style_and_visibility_schema_round_trip():
    stroke = Stroke(
        id="S1",
        pen="wall",
        geometry={"kind": "line", "p1": [0.0, 0.0], "p2": [3.0, 0.0]},
        line_style="dash_dot",
        visibility="hidden",
    )

    restored = Stroke.model_validate_json(stroke.model_dump_json())
    assert restored.line_style == "dash_dot"
    assert restored.visibility == "hidden"


def test_legacy_view_without_new_fields_loads_and_serializes_strokes_unchanged():
    raw = {
        "image_kind": "plan",
        "strokes": [
            {
                "id": "S1",
                "pen": "wall",
                "geometry": {"kind": "line", "p1": [0.0, 0.0], "p2": [4.0, 0.0]},
            }
        ],
        "dimensions": [{"id": "D1", "text": "4.00"}],
    }

    view = parse_reading_view(raw)
    assert view.migrated_from_legacy is True
    assert view.strokes[0].line_style is None
    assert view.strokes[0].visibility is None
    serialized = view.model_dump(exclude_none=True, exclude_defaults=True)
    assert serialized["strokes"] == raw["strokes"]


def test_concave_outer_envelope_polyline_passes_reading_gate():
    view = ReadingView.model_validate(
        {
            "image_kind": "plan",
            "uncaptured": [],
            "strokes": [
                {
                    "id": "outer-envelope",
                    "pen": "wall",
                    "geometry": {
                        "kind": "polyline",
                        "points": [[0, 0], [6, 0], [6, 2], [2, 2], [2, 5], [0, 5], [0, 0]],
                    },
                    "provenance": "seen",
                    "confidence": "high",
                }
            ],
        }
    )

    assert [2, 2] in view.strokes[0].geometry["points"]
    _assert_gate_invariants_pass(view)
