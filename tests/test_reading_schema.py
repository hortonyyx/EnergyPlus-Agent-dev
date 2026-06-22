"""M1: reading-view schema migration (P1a dimension chain + P1b facade image-local)."""

from __future__ import annotations

from pathlib import Path

from src.agent.reading import (
    Dimension,
    DimensionRole,
    ReadingView,
    RoomRoleObservation,
    Stroke,
    load_reading_view,
    migrate_view,
    parse_value_m,
)

_ANCHOR = Path("case_tests/e2e_tests/sm20_anchor/run_2026-06-15_baseline/0_reading")


def test_parse_value_m():
    assert parse_value_m("15.00") == 15.0
    assert parse_value_m("8") == 8.0
    assert parse_value_m("3.6 m") == 3.6
    assert parse_value_m("12,500") == 12500.0
    assert parse_value_m(None) is None
    assert parse_value_m("no number") is None


def test_legacy_plan_migration_backfills_dimensions():
    view = load_reading_view(_ANCHOR / "1f_view.json")
    assert view.migrated_from_legacy is True
    assert view.dimensions, "plan has dimensions"
    d0 = view.dimensions[0]
    # P1a back-fill: value_m parsed from legacy text, text_verbatim preserved.
    assert d0.value_m is not None
    assert d0.text_verbatim == d0.text
    assert any("value_m" in f for f in view.migration_flags)
    # uncaptured always present as a list (linter invariant precondition).
    assert isinstance(view.uncaptured, list)


def test_legacy_elevation_facade_is_image_local_only():
    view = load_reading_view(_ANCHOR / "East_view.json")
    assert view.facade is not None
    f = view.facade
    assert f.view_facade == "East"          # mined from label/note
    assert f.local_x_positive == "image_left_to_right"  # image-local, not east/west
    assert f.mirrored == "unknown"          # legacy never declared it
    # The world-flavoured legacy note is kept only as low-confidence evidence.
    assert any(e.source == "legacy_note" for e in f.orientation_evidence)
    assert any("world axis/sign must be re-derived" in flag for flag in view.migration_flags)


def test_canonical_view_loads_without_migration():
    canonical = {
        "image_label": "Floor 1",
        "image_kind": "plan",
        "strokes": [{"id": "S1", "pen": "wall", "geometry": {"kind": "line"}}],
        "dimensions": [
            {"id": "D1", "text_verbatim": "5.00", "value_m": 5.0,
             "chain_id": "c1", "role": "overall", "order": 0, "axis": "x"}
        ],
        "uncaptured": [],
    }
    v = ReadingView.model_validate(canonical)
    assert v.migrated_from_legacy is False
    assert v.dimensions[0].role == DimensionRole.OVERALL
    assert v.room_labels == []


def test_stroke_provenance_fields_default_and_round_trip():
    legacy = Stroke.model_validate({
        "id": "S1",
        "pen": "wall",
        "geometry": {"kind": "line", "p1": [0, 0], "p2": [5, 0]},
    })
    assert legacy.provenance is None
    assert legacy.confidence is None
    assert legacy.dimension_refs == []

    derived = Stroke.model_validate({
        "id": "S2",
        "pen": "wall",
        "provenance": "dimension_derived",
        "confidence": "medium",
        "dimension_refs": ["D1", "D2"],
        "geometry": {"kind": "line", "p1": [5, 0], "p2": [5, 3]},
    })
    dumped = derived.model_dump()
    assert dumped["provenance"] == "dimension_derived"
    assert dumped["confidence"] == "medium"
    assert dumped["dimension_refs"] == ["D1", "D2"]


def test_room_labels_round_trip():
    canonical = {
        "image_label": "Floor 2",
        "image_kind": "plan",
        "strokes": [],
        "dimensions": [],
        "uncaptured": [],
        "room_labels": [
            {
                "id": "RL1",
                "anchor": [4.2, 6.1],
                "role": "meeting",
                "label_text": "Meeting Room",
                "basis": "label",
                "confidence": 0.93,
            }
        ],
    }
    v = ReadingView.model_validate(canonical)
    assert v.room_labels == [
        RoomRoleObservation(
            id="RL1",
            anchor=[4.2, 6.1],
            role="meeting",
            label_text="Meeting Room",
            basis="label",
            confidence=0.93,
        )
    ]
    assert ReadingView.model_validate(v.model_dump()).room_labels[0].role == "meeting"


def test_legacy_room_labels_absent_defaults_empty_round_trip():
    legacy = {"image_label": "Floor 1", "image_kind": "plan", "uncaptured": []}
    v = ReadingView.model_validate(legacy)
    assert v.room_labels == []
    assert ReadingView.model_validate_json(v.model_dump_json()).room_labels == []


def test_dimension_from_alias():
    d = Dimension.model_validate({"id": "D1", "from": [0, 0], "to": [5, 0]})
    assert d.from_pt == [0, 0]
    # round-trips back under the alias for re-serialization
    assert d.model_dump(by_alias=True)["from"] == [0, 0]


def test_migrate_view_idempotent_on_canonical():
    """Migrating an already-canonical dict still yields a valid view (defensive)."""
    v = migrate_view({"image_kind": "plan", "dimensions": [], "strokes": []})
    assert isinstance(v, ReadingView)
    assert v.uncaptured == []
