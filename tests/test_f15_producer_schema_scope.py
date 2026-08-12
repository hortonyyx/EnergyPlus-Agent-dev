"""F-15 (2026-08-07 dispatch): the correction draw's PROMPT schema handed the
model the deterministic core's own audit-trail fields (top-level
``facade_segments``, each window's ``facade_segment_id``) as if they were
ordinary optional fields worth filling — nothing in the schema or the prompt
said otherwise (B1). A real run then burned all 3 inner-retry attempts on the
IDENTICAL ``producer_segment_ref_prefilled`` rejection, because the F-4a
retry-guidance channel — although fully wired into the loop that raises it —
only recognised ``pydantic.ValidationError``, and ``WindowResolverInputError``
is a plain ``ValueError`` subclass, so guidance fell through to blind retry
every time (B2). See ``correction_raw.txt`` in
``run_2026-08-07_f9_root_fix_verify/1_correction/`` (the real crash this
locks against, copied byte-for-byte into
``tests/fixtures/f15_producer_schema_scope/real_crash_draw.json`` — NOT a
hand-crafted "just barely triggers" fixture).

Two independent fixes, both locked here:

* **B1 fix** — ``vocab.producer_facing_json_schema`` strips any field the
  schema itself marks ``schema.CORRECTION_DRAW_FORBIDDEN``
  (``json_schema_extra``) from the JSON Schema dumped into the correction
  system prompt, and prunes any ``$defs`` entry that becomes unreachable as a
  result. ``_producer_preflight`` (window_sources.py) is UNCHANGED and
  UNWEAKENED — it remains the authoritative door; this fix only changes what
  the model is shown, never what the core accepts.
* **B2 fix** — ``retry_guidance_for_correction`` now also translates the two
  named ``model_draw_error``-category ``WindowResolverInputError`` codes into
  format-only, code-keyed corrective guidance (``_MODEL_DRAW_ERROR_GUIDANCE``)
  — while an ``input_integrity_error``-category instance (an upstream/
  environment fault resampling cannot fix) still retries blind, preserving
  F-4a's existing discipline.

Neuter self-check performed by hand during construction (not re-encoded as a
test toggle, per this project's convention): reverting the ``schema.py``
markers, the ``vocab.py`` stripping function, and the ``_guide`` isinstance
branch each independently turned the corresponding lock(s) below red with no
unrelated collateral, then were restored byte-for-byte.

FOLLOW-UP (same day, orchestrator A3): the first pass above marked only
``facade_segments`` + ``facade_segment_id`` forbidden. A second real run then
filled ``north_axis`` instead (same shape of field: core-only, populated
downstream by the SEPARATE, non-LLM ``e4_orientation`` enrichment phase in
``orientation.py`` — never the draw) and was rejected, but BLINDLY: the b2
draw-contract gate in ``parse.py`` had its own, independently hardcoded
``facade_segments``/``north_axis`` name check (predating F-15), so marking
only ``schema.py``'s side left the two doors' name lists free to drift — and
they had already drifted (the gate enforced ``north_axis``; the marker/prompt
did not).

The follow-up fix is a genuine SINGLE SOURCE OF TRUTH, not just "add the
missing mark": ``schema.draw_forbidden_field_names(model_cls)`` mechanically
reads the marker off ``model_cls.model_fields``, and BOTH
``vocab.producer_facing_json_schema`` (already marker-driven from the first
pass) AND ``parse.py``'s b2 gate (refactored here to call
``draw_forbidden_field_names`` instead of hardcoding names) now read the same
function. Group E below is the drift lock: it does not just assert the
current field set (that would be self-referential — reading the
implementation's own list and checking it equals itself) — it PROVES the
coupling is live by mutating the marker on an arbitrary field at runtime and
observing the REAL ``parse_correction_draw`` gate's accept/reject behaviour
change as an independent, externally observable effect, in both directions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from src.agent import pipeline
from src.agent.correction.parse import correction_target, parse_correction_draw
from src.agent.correction.schema import (
    CORRECTION_DRAW_FORBIDDEN,
    CorrectedGeometry,
    CorrectedGeometryV3,
    draw_forbidden_field_names,
)
from src.agent.correction.vocab import (
    _MODEL_DRAW_ERROR_GUIDANCE,
    producer_facing_json_schema,
    retry_guidance_for_correction,
)
from src.agent.correction.window_sources import WindowResolverInputError

_FIXTURE = Path(__file__).parent / "fixtures" / "f15_producer_schema_scope" / "real_crash_draw.json"
_FIXTURE_NORTH_AXIS_ONLY = (
    Path(__file__).parent / "fixtures" / "f15_producer_schema_scope"
    / "real_crash_draw_north_axis_only.json"
)
V3 = correction_target("orthogonal_polygon")
V1 = correction_target("rectangular")

SECTION = {"api_key": "x", "model_name": "m"}


def _real_crash_draw() -> dict:
    """The actual model output that crashed ``run_2026-08-07_f9_root_fix_verify``
    (F-15 A1/A2) — 2 floors, 15 windows, 8 fabricated ``facade_segments``
    (including a 64-``a`` placeholder ``source_footprint_fingerprint``), and
    every window carrying a prefilled ``facade_segment_id``. Loaded fresh per
    call so tests that mutate a copy never cross-contaminate."""
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _real_crash_draw_north_axis_only() -> dict:
    """The SAME real crash draw as `_real_crash_draw()`, with `facade_segments`
    and every window's `facade_segment_id` programmatically stripped (the
    door the FIRST F-15 pass already closed) — but its real,
    model-generated `north_axis` block (`{"value_deg": 0.0, "provenance":
    "assumed", ..., "method": "north_from_layout_orientation"}`) left
    untouched. This is a faithful reconstruction of what
    `run_2026-08-07_f15_producer_schema_verify`'s SECOND verification run
    actually produced on attempts 1-2 (confirmed by that run's own retry log:
    both attempts rejected with the identical `b2 draw contract requires
    empty facade_segments and null north_axis` message) — not a
    hand-invented payload; the base file predates and is independent of the
    north_axis follow-up fix.

    F-16 follow-up (2026-08-08, §6 摊一 Step 2): each window's `floor`
    string is ALSO now programmatically stripped from this on-disk fixture
    — it was a legitimately required field when this real draw was
    produced (predates F-16), but `floor` is now `CORRECTION_DRAW_DERIVED`
    and any populated value is rejected on its own, orthogonal door
    (`producer_window_floor_populated`) BEFORE `parse_correction_draw` ever
    reaches the north_axis check this fixture exists to isolate. Left as-is
    the fixture would fail this test for the wrong reason (floor, not
    north_axis) — stripping it keeps the isolation this fixture's docstring
    promises, same reasoning as the pre-existing facade_segments/
    facade_segment_id strip above."""
    return json.loads(_FIXTURE_NORTH_AXIS_ONLY.read_text(encoding="utf-8"))


def _valid_v3_payload() -> dict:
    return {
        "schema_version": "3",
        "footprint_x": [0.0, 4.0],
        "footprint_y": [0.0, 3.0],
        "floors": [
            {
                "name": "F1",
                "id": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "footprint": {"vertices": [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]},
                "cells": [{"id": "A", "x": [0.0, 4.0], "y": [0.0, 3.0]}],
            }
        ],
        "windows": [],
    }


# =========================================================================== #
# Group A — producer_facing_json_schema: structural exclusion (B1 fix)
# =========================================================================== #

def test_producer_schema_excludes_facade_segments_and_segment_id():
    full = CorrectedGeometryV3.model_json_schema()
    # sanity: the full schema DOES carry both fields (else this test would be
    # vacuous — proves we're testing against the real defect surface).
    assert "facade_segments" in full["properties"]
    assert "north_axis" in full["properties"]
    window_def_name = next(k for k in full["$defs"] if k == "WindowV3")
    assert "facade_segment_id" in full["$defs"][window_def_name]["properties"]

    stripped = producer_facing_json_schema(CorrectedGeometryV3)
    assert "facade_segments" not in stripped["properties"]
    assert "north_axis" not in stripped["properties"]
    assert "facade_segment_id" not in stripped["$defs"][window_def_name]["properties"]
    # required lists must not still name a field that was removed
    assert "facade_segments" not in stripped.get("required", [])
    assert "north_axis" not in stripped.get("required", [])
    win_required = stripped["$defs"][window_def_name].get("required", [])
    assert "facade_segment_id" not in win_required


def test_producer_schema_prunes_orphaned_defs():
    """Removing `facade_segments` (type FacadeSegment, which itself uses
    WorldInterval) and `north_axis` (type NorthAxisEvidence) must not leave
    any of the three sitting in `$defs` unreferenced by anything — that would
    still visually re-offer the model the exact shape it must not fill."""
    full = CorrectedGeometryV3.model_json_schema()
    assert "FacadeSegment" in full["$defs"]
    assert "WorldInterval" in full["$defs"]
    assert "NorthAxisEvidence" in full["$defs"]

    stripped = producer_facing_json_schema(CorrectedGeometryV3)
    assert "FacadeSegment" not in stripped["$defs"]
    assert "WorldInterval" not in stripped["$defs"]
    assert "NorthAxisEvidence" not in stripped["$defs"]
    # and the textual dump — what the model actually reads — carries neither
    # type name anywhere at all.
    dumped = json.dumps(stripped)
    assert "FacadeSegment" not in dumped
    assert "WorldInterval" not in dumped
    assert "NorthAxisEvidence" not in dumped


def test_producer_schema_preserves_everything_else_byte_identical():
    """Every OTHER top-level property and every OTHER $defs entry is
    byte-identical to the untouched schema — this fix removes exactly the
    marked fields and nothing else.

    F-22 BLOCKER-1 (2026-08-12): `deterministic_core_stamp` joins the marked
    set here too (schema.py, `CorrectedGeometryV3`) — same
    CORRECTION_DRAW_FORBIDDEN marker, same reason (a core-only provenance
    fact, illegal draw input), stripped by the SAME generic marker scan with
    zero changes needed to `producer_facing_json_schema` itself.
    """
    full = CorrectedGeometryV3.model_json_schema()
    stripped = producer_facing_json_schema(CorrectedGeometryV3)

    kept_top = set(full["properties"]) - {"facade_segments", "north_axis", "deterministic_core_stamp"}
    assert set(stripped["properties"]) == kept_top
    for name in kept_top:
        assert stripped["properties"][name] == full["properties"][name], name

    kept_defs = set(full["$defs"]) - {"FacadeSegment", "WorldInterval", "NorthAxisEvidence", "DeterministicCoreStampV1"}
    assert set(stripped["$defs"]) == kept_defs
    for name in kept_defs:
        if name == "WindowV3":
            continue  # this one entry is intentionally modified, checked above
        assert stripped["$defs"][name] == full["$defs"][name], name


def test_producer_schema_v1_target_is_completely_unmodified():
    """v1 (rectangular, `CorrectedGeometry`) carries no
    CORRECTION_DRAW_FORBIDDEN-marked field at all, so the stripped schema must
    be byte-identical (as JSON text) to the untouched one — no accidental
    touch of the v1 path."""
    full = CorrectedGeometry.model_json_schema()
    stripped = producer_facing_json_schema(CorrectedGeometry)
    assert json.dumps(stripped, sort_keys=True) == json.dumps(full, sort_keys=True)


def test_schema_forbidden_marker_present_on_exactly_the_four_fields():
    """Pins the marker itself at the schema source (schema.py) — if someone
    removes `json_schema_extra` from any of the four, or adds it somewhere
    it doesn't belong, this test names exactly which field changed.

    Three, not two: the original F-15 pass only marked `facade_segments` +
    `facade_segment_id`; `north_axis` is the follow-up (orchestrator A3) —
    same shape of core-only field (populated only by the separate
    `e4_orientation` enrichment phase, never the draw), just missed the first
    time because the real crash that surfaced it (a filled `north_axis`) only
    happened on the SECOND verification run, after the first door closed.

    Four, not three (2026-08-12, F-22 BLOCKER-1): `deterministic_core_stamp`
    joins the set — same shape again (a core-only provenance fact a draw
    must never pre-fill), this time because a schema-v3-shaped draw claiming
    a core-verified identity it never earned is exactly what let a pre-F-17
    real production run score five-for-five `pass` while 0.12 m off on
    every side (see correction_score.py's `_is_trusted_output_convention`).
    """
    full = CorrectedGeometryV3.model_json_schema()
    assert full["properties"]["facade_segments"].get(CORRECTION_DRAW_FORBIDDEN) is True
    assert full["properties"]["north_axis"].get(CORRECTION_DRAW_FORBIDDEN) is True
    assert full["properties"]["deterministic_core_stamp"].get(CORRECTION_DRAW_FORBIDDEN) is True
    window_def = full["$defs"]["WindowV3"]
    assert window_def["properties"]["facade_segment_id"].get(CORRECTION_DRAW_FORBIDDEN) is True
    # nothing else on CorrectedGeometryV3's own top-level carries the marker
    other_top = {
        k: v for k, v in full["properties"].items()
        if k not in ("facade_segments", "north_axis", "deterministic_core_stamp")
    }
    assert not any(isinstance(v, dict) and v.get(CORRECTION_DRAW_FORBIDDEN) for v in other_top.values())


# =========================================================================== #
# Group B — the real prompt-builder (_build_correction_messages) is wired to
# the stripped schema, and carries the audit-row note (B1 fix, production path)
# =========================================================================== #

def _schema_block(system_prompt: str) -> str:
    return system_prompt.split(
        "===== BEGIN CorrectedGeometry JSON SCHEMA =====\n", 1
    )[1].split("\n===== END CorrectedGeometry JSON SCHEMA =====", 1)[0]


def test_v3_prompt_schema_block_excludes_forbidden_fields(tmp_path):
    (tmp_path / "reading_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "1f_view.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    system, _ = pipeline._build_correction_messages(tmp_path, "{}", target=V3)
    block = _schema_block(system)
    assert "facade_segments" not in block
    assert "facade_segment_id" not in block
    assert "FacadeSegment" not in block
    # sanity: the block is not empty / didn't strip everything
    assert "footprint_x" in block
    assert "windows" in block


def test_v3_prompt_warns_against_window_host_resolution_audit_rows(tmp_path):
    (tmp_path / "reading_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "1f_view.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    system, _ = pipeline._build_correction_messages(tmp_path, "{}", target=V3)
    assert "window_host_resolution" in system
    assert "deterministic core produces downstream" in system


def test_v1_prompt_schema_block_is_byte_identical_to_full_schema(tmp_path):
    """v1 has no forbidden-marked field, so its schema block must be the
    UNSTRIPPED, full model_json_schema() dump verbatim — proves the fix
    changed nothing about the v1 path."""
    (tmp_path / "reading_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "1f_view.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    system, _ = pipeline._build_correction_messages(tmp_path, "{}", target=V1)
    block = _schema_block(system).strip("\n")
    expected = json.dumps(V1.schema_model.model_json_schema(), indent=2, ensure_ascii=False)
    assert block == expected
    assert "window_host_resolution" not in system  # v3-only note


# =========================================================================== #
# Group C — retry_guidance_for_correction: WindowResolverInputError handling
# (B2 fix)
# =========================================================================== #

def test_retry_guidance_translates_producer_segment_ref_prefilled():
    guide = retry_guidance_for_correction(V3)
    exc = WindowResolverInputError("producer_segment_ref_prefilled", category="model_draw_error")
    msg = guide(exc)
    assert msg is not None
    assert "facade_segments" in msg
    assert "facade_segment_id" in msg
    assert "deterministic-core-only" in msg


def test_retry_guidance_translates_producer_resolver_audit_prefilled():
    guide = retry_guidance_for_correction(V3)
    exc = WindowResolverInputError("producer_resolver_audit_prefilled", category="model_draw_error")
    msg = guide(exc)
    assert msg is not None
    assert "window_host_resolution" in msg


def test_retry_guidance_translates_producer_b2_forbidden_field_populated():
    """Follow-up (orchestrator A3): the b2 gate's rejection (facade_segments
    and/or north_axis populated) now uses the same typed exception/category
    as the other two doors, so it gets the same guidance treatment — a real
    run burned 2 of its 3 attempts blind on this exact rejection before this
    fix (facade_segments was already clean; north_axis was the new door)."""
    guide = retry_guidance_for_correction(V3)
    exc = WindowResolverInputError(
        "producer_b2_forbidden_field_populated",
        {"message": "b2 draw contract requires empty facade_segments and null north_axis", "fields": ["north_axis"]},
        category="model_draw_error",
    )
    msg = guide(exc)
    assert msg is not None
    assert "north_axis" in msg
    assert "facade_segments" in msg


def test_retry_guidance_input_integrity_error_still_retries_blind():
    """An upstream/environment fault (resampling cannot fix it) must NOT get
    resample guidance — preserves F-4a's existing 'blind unless it's a
    drawing/format mistake' discipline."""
    guide = retry_guidance_for_correction(V3)
    exc = WindowResolverInputError("source_identity_invalid", category="input_integrity_error")
    assert guide(exc) is None


def test_retry_guidance_unmapped_model_draw_error_code_is_safe_none():
    guide = retry_guidance_for_correction(V3)
    exc = WindowResolverInputError("some_future_code_not_yet_mapped", category="model_draw_error")
    assert guide(exc) is None


def test_guidance_map_covers_exactly_the_three_known_model_draw_error_codes():
    """Pins the guidance map's key set directly against the codes the
    real doors raise: `_producer_preflight` (window_sources.py, 2 codes) +
    the b2 gate (parse.py, 2 codes: `producer_b2_forbidden_field_populated`
    for top-level fields, and `producer_window_floor_populated` — F-16,
    2026-08-08 §6 摊一 Step 2 — for the nested, CORRECTION_DRAW_DERIVED
    `WindowV3.floor`). If a new door is added at either site without a
    matching guidance entry, this test names the gap."""
    assert set(_MODEL_DRAW_ERROR_GUIDANCE) == {
        "producer_segment_ref_prefilled",
        "producer_resolver_audit_prefilled",
        "producer_b2_forbidden_field_populated",
        "producer_window_floor_populated",
    }


# =========================================================================== #
# Group D — end-to-end: the REAL crash draw through the REAL validator +
# retry-guidance chain (mirrors test_correction_blind_retry_r3.py's style)
# =========================================================================== #

def _resp(content: str, finish_reason: str = "stop"):
    class _Obj:
        pass

    msg = _Obj()
    msg.content = content
    msg.reasoning_content = None
    choice = _Obj()
    choice.message = msg
    choice.finish_reason = finish_reason
    usage = _Obj()
    usage.prompt_tokens = 1
    usage.completion_tokens = 1
    resp = _Obj()
    resp.choices = [choice]
    resp.usage = usage
    return resp


class _RecordingClient:
    def __init__(self, outcomes: list[Any]):
        self._outcomes = list(outcomes)
        self.received_messages: list[list[dict]] = []
        self.chat = self
        self.completions = self

    def create(self, **kw):
        self.received_messages.append([dict(m) for m in kw.get("messages", [])])
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _patch_openai(monkeypatch, outcomes):
    fc = _RecordingClient(outcomes)
    monkeypatch.setattr(pipeline, "OpenAI", lambda **_kw: fc)
    return fc


def test_e2e_real_crash_draw_gets_guided_then_recovers(monkeypatch):
    """Attempt 1 = the byte-for-byte real crash draw (facade_segments +
    15x facade_segment_id). It must be rejected by the REAL production
    validator chain (`_make_correction_validator` -> `parse_correction_draw`
    -> the parse.py:101 early-exit raise) with the exact named code, receive
    non-blind corrective guidance, and attempt 2 (a clean re-draw) must
    succeed — proving the inner retry recovers in ONE guided step instead of
    burning all 3 attempts on the identical mistake (F-15 A1)."""
    outcomes = [_resp(json.dumps(_real_crash_draw())), _resp(json.dumps(_valid_v3_payload()))]
    fc = _patch_openai(monkeypatch, outcomes)
    validate = pipeline._make_correction_validator(0, V3)
    out = pipeline._call_json_llm(
        SECTION, "sys", "human", out_dir=None, prefix="t", attempts=3,
        validate=validate, retry_guidance=retry_guidance_for_correction(V3),
    )
    assert out["windows"] == []
    assert len(fc.received_messages) == 2, "must recover on attempt 2, not burn all 3 (F-15 A1)"

    second = fc.received_messages[1]
    assert len(second) == 3, "a model_draw_error rejection must append corrective guidance"
    guidance = second[2]["content"]
    assert "facade_segments" in guidance
    assert "facade_segment_id" in guidance
    # format-only: never echoes the rejected draw's actual geometry
    assert "14.88" not in guidance  # a real footprint_x value from the fixture
    assert "1F_North" not in guidance  # a real facade_segment id from the fixture


def test_e2e_real_crash_draw_without_the_fix_would_burn_all_3_attempts(monkeypatch):
    """Neuter-style control: confirms the OLD behaviour (retry_guidance that
    only recognises ValidationError, i.e. `lambda exc: None` for this error)
    on the SAME real crash draw repeated 3 times still fails after exhausting
    the budget — pinning what B2 actually fixed, via the real validator chain
    (not a synthetic exception)."""
    outcomes = [_resp(json.dumps(_real_crash_draw()))] * 3
    fc = _patch_openai(monkeypatch, outcomes)
    validate = pipeline._make_correction_validator(0, V3)
    with pytest.raises(RuntimeError, match="failed after 3 attempt"):
        pipeline._call_json_llm(
            SECTION, "sys", "human", out_dir=None, prefix="t", attempts=3,
            validate=validate, retry_guidance=lambda exc: None,
        )
    assert len(fc.received_messages) == 3
    for msgs in fc.received_messages:
        assert len(msgs) == 2, "blind retry never appends a corrective 3rd message"


def test_e2e_real_crash_north_axis_only_draw_gets_guided_then_recovers(monkeypatch):
    """Follow-up e2e (orchestrator A3): attempt 1 = the real crash draw with
    `facade_segments`/`facade_segment_id` already clean (the door the FIRST
    F-15 pass closed) but `north_axis` still populated with its REAL
    model-generated content — a faithful reconstruction of what
    `run_2026-08-07_f15_producer_schema_verify`'s SECOND verification run
    actually produced (that run's own retry log shows attempts 1 and 2 both
    rejected with the identical `b2 draw contract requires empty
    facade_segments and null north_axis` message, un-guided, before this
    fix). Must now be rejected via the SAME typed exception/category as the
    other two doors, receive corrective guidance naming `north_axis`, and
    recover on attempt 2 instead of repeating blind."""
    outcomes = [
        _resp(json.dumps(_real_crash_draw_north_axis_only())),
        _resp(json.dumps(_valid_v3_payload())),
    ]
    fc = _patch_openai(monkeypatch, outcomes)
    validate = pipeline._make_correction_validator(0, V3)
    out = pipeline._call_json_llm(
        SECTION, "sys", "human", out_dir=None, prefix="t", attempts=3,
        validate=validate, retry_guidance=retry_guidance_for_correction(V3),
    )
    assert out["windows"] == []
    assert len(fc.received_messages) == 2, "must recover on attempt 2, not repeat blind"

    second = fc.received_messages[1]
    assert len(second) == 3, "a model_draw_error rejection must append corrective guidance"
    guidance = second[2]["content"]
    assert "north_axis" in guidance
    assert "facade_segments" in guidance
    assert "deterministic core" in guidance
    # format-only: never echoes the rejected draw's actual geometry
    assert "14.88" not in guidance


# =========================================================================== #
# Group E — drift lock (orchestrator A3/B1 follow-up): proves the b2 gate's
# forbidden-field set and the prompt-schema stripper are a genuine SINGLE
# SOURCE OF TRUTH (schema.draw_forbidden_field_names), not two independently
# hardcoded lists that can silently re-diverge (which is exactly what
# happened: the gate hardcoded `facade_segments`/`north_axis`; the marker —
# and therefore the prompt stripper — only had `facade_segments`).
#
# NOT self-referential: instead of asserting the implementation's own
# derived list equals itself, these mutate the marker on the REAL schema
# class at runtime (via monkeypatch, auto-reverted) and observe the REAL
# `parse_correction_draw` gate's accept/reject behaviour change as an
# independent, externally observable effect — in BOTH directions. This is
# what proves "mark a field once, both consumers see it" is actually true,
# not just true today by coincidence of two lists agreeing.
# =========================================================================== #

def test_marking_a_previously_ordinary_field_makes_the_b2_gate_reject_it_live(monkeypatch):
    """`notes` is an ordinary, currently-unmarked `str | None` field — nothing
    anywhere hardcodes it as forbidden. Mark it forbidden on the REAL
    `CorrectedGeometryV3` model at runtime (zero change to parse.py) and the
    REAL gate must start rejecting a draw that populates it. This is the
    'future new door, mark it once, enforcement is automatic' half of the
    proof — the inverse of what actually went wrong with `north_axis`."""
    payload = _valid_v3_payload()
    payload["notes"] = "some note"

    # control: BEFORE marking, a populated `notes` is unremarkable.
    geom = parse_correction_draw(payload, V3)
    assert geom.notes == "some note"
    assert "notes" not in draw_forbidden_field_names(CorrectedGeometryV3)

    field_info = CorrectedGeometryV3.model_fields["notes"]
    monkeypatch.setattr(field_info, "json_schema_extra", {CORRECTION_DRAW_FORBIDDEN: True})
    assert "notes" in draw_forbidden_field_names(CorrectedGeometryV3)

    with pytest.raises(WindowResolverInputError) as exc_info:
        parse_correction_draw(payload, V3)
    assert exc_info.value.code == "producer_b2_forbidden_field_populated"
    assert "notes" in exc_info.value.context["fields"]


def test_unmarking_a_real_forbidden_field_makes_the_b2_gate_stop_rejecting_it_live(monkeypatch):
    """Reverse direction: proves the gate is NOT ALSO secretly hardcoding
    `north_axis` by name anywhere in addition to reading the marker (i.e.
    the refactor genuinely removed the old hardcoded check, it didn't just
    add a second parallel one). Strip the marker from the REAL `north_axis`
    field at runtime and a draw that populates it must now pass the b2 gate
    cleanly."""
    payload = _valid_v3_payload()
    payload["north_axis"] = {"value_deg": 0.0, "provenance": "assumed", "source_ids": []}

    # control: BEFORE un-marking, it's rejected (this is the real, current
    # production behaviour this whole ticket is about).
    with pytest.raises(WindowResolverInputError):
        parse_correction_draw(payload, V3)

    field_info = CorrectedGeometryV3.model_fields["north_axis"]
    monkeypatch.setattr(field_info, "json_schema_extra", None)
    assert "north_axis" not in draw_forbidden_field_names(CorrectedGeometryV3)

    geom = parse_correction_draw(payload, V3)
    assert geom.north_axis is not None
    assert geom.north_axis.value_deg == 0.0


def test_prompt_stripper_and_b2_gate_agree_on_forbidden_set_after_a_live_marker_change():
    """Cross-consumer proof: mark a third field (`notes`) forbidden at
    runtime and BOTH consumers — the prompt-schema stripper
    (`producer_facing_json_schema`, JSON-schema-dict based) and the b2 gate's
    field-name source (`draw_forbidden_field_names`, pydantic-model based) —
    must agree it is now excluded/forbidden, with no code change to either.
    This is the actual 'single source' claim: two independently-shaped
    consumers, one derivation.

    NOT a `monkeypatch.setattr` here: pydantic caches `model_json_schema()`'s
    output separately from `model_fields`, so making
    `producer_facing_json_schema` observe a live marker change also requires
    `model_rebuild(force=True)` — a plain attribute revert on teardown would
    leave the class's cached schema stale for whichever test runs next in
    this worker, so the restore + re-rebuild is done by hand in `finally`,
    synchronously, before this test returns."""
    field_info = CorrectedGeometryV3.model_fields["notes"]
    original = field_info.json_schema_extra
    field_info.json_schema_extra = {CORRECTION_DRAW_FORBIDDEN: True}
    CorrectedGeometryV3.model_rebuild(force=True)
    try:
        stripped = producer_facing_json_schema(CorrectedGeometryV3)
        assert "notes" not in stripped["properties"]
        assert "notes" in draw_forbidden_field_names(CorrectedGeometryV3)
    finally:
        field_info.json_schema_extra = original
        CorrectedGeometryV3.model_rebuild(force=True)
        # prove the restore is real, not just hoped for: `notes` is back to
        # being an ordinary, PRESENT (not stripped) property.
        assert "notes" not in draw_forbidden_field_names(CorrectedGeometryV3)
        assert "notes" in producer_facing_json_schema(CorrectedGeometryV3)["properties"]
