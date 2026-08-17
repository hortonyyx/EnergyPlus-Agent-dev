"""M1: reading-view schema migration (P1a dimension chain + P1b facade image-local)."""

from __future__ import annotations

import re
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


def test_plan_scale_origin_is_an_optional_not_mandatory_reader_instruction_contract():
    """scale_origin (2026-08-17, 707-prereq): supersedes this test's own
    former name and body
    (``test_plan_scale_origin_is_a_locked_reader_instruction_contract``).

    OLD semantics (a short-lived state, introduced sometime after the
    07-07/07-08 good window and never present in either successful run from
    that window -- see AI_agent/logs/experiments/2026-08-16_707_repro/
    behavioral_change_inventory.md §A1): ``guide.md`` §1 said "Every plan view
    **must** declare `scale_origin`", where the required value was **the SW
    INNER corner of the overall projected maximum building boundary** --
    i.e. every plan-view reading required the reader to (1) determine the
    whole building's CROSS-FLOOR projected maximum footprint, (2) judge that
    boundary's INNER edge (⇒ requires judging wall thickness / inner vs.
    outer skin -- this project's "dimension/wall-thickness/derive-footprint"
    workstream is explicitly UNSOLVED), and (3) place the result in world
    coordinates. All three are exactly the kind of "world placement" the same
    document's §1 opening line explicitly forbids the reading stage from
    doing ("the reading stage does NO world placement") -- the old
    requirement contradicted the document's own governing rule, was never
    exercised by either known-good run, and was never actually a documented
    rule before 2026-08-16 despite reading like a long-settled one. This old
    literal sentence is what the previous version of this test locked
    (byte-for-byte, including its embedded newline).

    NEW semantics: ``scale_origin`` is OPTIONAL for every plan (never
    required), and when given, its reference point is a per-image datum only
    -- "an easily-seen reference point drawn in THIS SAME image", explicitly
    NEVER the result of cross-floor footprint or wall-thickness reasoning.
    Leaving it ``null`` when not cheaply confident is legal and is explicitly
    NOT a self-check failure. This restores consistency with §1's "no world
    placement" rule rather than carving out a silent exception to it.

    Why this test locks SEMANTICS (optional-not-mandatory, same-image-only
    scoping) rather than the new sentences' literal wording: the old test's
    actual defect was never "it used substring/exact-text checks against doc
    prose" (that technique is this codebase's normal way of contract-locking
    a skill doc -- see e.g. tests/test_substrate_fix_tools.py's F-53
    section). The defect was locking the WRONG CONTENT -- one specific
    sentence's exact phrasing, which happened to encode a requirement that
    was itself wrong and that a future editorial rewrite (e.g. rewording
    "SHOULD" to "may" for style) could trivially break EVEN THOUGH the
    underlying contract had not changed, while conversely a regression back
    to "must" + cross-floor reasoning phrased in ANY new sentence would sail
    right past a check that only ever looked for one old exact string. Each
    assertion below is therefore a short, semantically load-bearing marker
    (present-tense: proves the new invariant holds; absent-tense: proves the
    old wrong invariant has not silently crept back), not a full-sentence
    verbatim pin -- picked so a future copy-edit that PRESERVES the contract
    keeps passing, while an edit that REGRESSES the contract (mandatory
    again, or cross-floor/wall-thickness reasoning again, in any phrasing)
    fails. Also widened to session_kickoff.md, the third of the three files
    this same commit touched (the previous version of this test covered only
    guide.md + pen_library.md) -- in scope because it is literally part of
    what item ② of this porting task changed, not scope creep. Two of the old
    test's assertions (the literal ``"world_x_m": 0.00`` / ``"world_y_m":
    0.00`` example strings) are deliberately NOT carried forward: they pin an
    illustrative worked example, not a promise -- they were never evidence of
    mandatoriness one way or the other, so locking them taught nothing about
    THIS contract.
    """

    guide = Path("skills/intake_pipeline/0_reading/guide.md").read_text(encoding="utf-8")
    pens = Path("skills/intake_pipeline/0_reading/pen_library.md").read_text(encoding="utf-8")
    kickoff = Path("skills/intake_pipeline/0_reading/session_kickoff.md").read_text(encoding="utf-8")

    # --- scale_origin is still a documented, legal field (not deleted) ---
    assert '"scale_origin"' in guide
    assert "world_x_m" in guide and "world_y_m" in guide and "world_z_m" in guide

    # --- NEW: explicitly optional, in both the prose rule and the schema ---
    assert "scale_origin: OPTIONAL for every plan" in guide
    assert re.search(r"plan view SHOULD\s+also declare `scale_origin`", guide), (
        "expected a SHOULD (not MUST) instruction to declare scale_origin"
    )
    assert "leave `scale_origin` `null` rather than guess" in guide
    assert "omitting it is not itself a self-check failure" in guide
    assert "optional container action" in pens
    assert "never guess the field — omit it" in pens
    assert "is not an exception to that" in kickoff
    assert "a plan MAY state" in kickoff

    # --- NEW: reference point is per-image / same-drawing only ---
    assert "drawn in THIS SAME image" in guide
    assert "drawn in THIS SAME image" in pens
    assert re.search(r"never a cross-image or\s+cross-floor judgment", kickoff), kickoff
    assert "never guessed, never a cross-floor judgment" in kickoff

    # --- OLD wrong requirement must not have silently crept back ---
    assert "must** declare `scale_origin`" not in guide
    assert "mandatory container action" not in pens
    assert "overall projected maximum building boundary" not in guide
    assert "SW inner corner" not in guide
    assert "all floors share that datum" not in pens


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
