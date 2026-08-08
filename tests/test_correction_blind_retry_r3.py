"""Locks for the correction blind-retry r3 dispatch (F-4a / F-4b), commit
following fb78e74.

The defect: ``_call_json_llm``'s inner retry was *blind* — a schema rejection
wrote the error to disk and re-issued the verbatim prompt, so a systematic
schema misunderstanding (an unknown ``north_axis`` key; an off-vocabulary
window ``provenance`` key) repeated identically until the retry budget was
gone and then crashed the flow. Two fixes:

* **F-4a** — when a retry follows a *schema* rejection (we got a model
  response, then validation failed), append a machine-generated, FORMAT-ONLY
  corrective message (pydantic field path + reason + the schema's legal
  vocabulary/field-set) to the next attempt's messages. Transport errors and
  semantic ValueErrors retry blind.
* **F-4b** — the legal vocabulary (window ``provenance`` opening-claim keys,
  ``north_axis`` allowed fields) is mechanically derived from the schema and
  placed in the system prompt up front, so the model knows the vocabulary
  before guessing — derived, never hand-copied (a second list is a second ruler).

Discriminating-power locks (08-04 lesson: a red neuter only proves the
implementation was called). The F-4a judgment is a discrete two-path split, so
each path is locked with the negative direction proven by neuter:

* schema-failure cell  ⇒ guidance IS appended (carries the field path);
* transport-failure    ⇒ guidance is NOT appended;
* semantic-ValueError  ⇒ guidance is NOT appended (content present, but
  retry_guidance returns None — the inner retry owns ONLY schema/format).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.agent import pipeline
from src.agent.correction.parse import correction_target
from src.agent.correction.vocab import (
    north_axis_allowed_fields,
    retry_guidance_for_correction,
    window_provenance_vocabulary,
)

SECTION = {"api_key": "x", "model_name": "m"}


# --------------------------------------------------------------------------- #
# fakes
# --------------------------------------------------------------------------- #

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
    """Queues one outcome per ``create()`` call (a response object returned, or
    an Exception raised) and records the exact messages each call received, so
    the F-4a locks can assert what the retry actually sent."""

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


# --------------------------------------------------------------------------- #
# structurally-complete v3 payloads (real CorrectedGeometryV3 shape, b2 contract)
# --------------------------------------------------------------------------- #

def _valid_v3_payload() -> dict:
    """Minimal payload that passes CorrectedGeometryV3.model_validate + the b2
    draw contract (footprint ring, floor id, no facade_segments/north_axis)."""
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


def _v3_with_extra_north_axis_key() -> dict:
    """Schema-violating draw: an unknown ``north_axis.note`` key triggers
    pydantic extra_forbidden — the exact 'attempt 3' failure from the dispatch."""
    return {
        **_valid_v3_payload(),
        "north_axis": {
            "value_deg": 0.0,
            "provenance": "observed",
            "source_ids": ["s1"],
            "note": "extra key not in the schema",
        },
    }


def _v3_with_window() -> dict:
    # F-16 (2026-08-08, §6 摊一 Step 2): `floor` is CORRECTION_DRAW_DERIVED —
    # a legal draw never supplies it (it is derived from `floor_id`) — so it
    # is intentionally omitted here, not just left matching `floor_id`'s
    # floor name as it used to.
    base = _valid_v3_payload()
    base["windows"] = [
        {
            "id": "W1",
            "floor_id": "F1",
            "facade": "South",
            "span": [1.0, 2.0],
            "z": [0.5, 2.5],
            "room": "A",
        }
    ]
    return base


V3 = correction_target("orthogonal_polygon")


# =========================================================================== #
# F-4a — schema failure appends a field-path corrective message (cell A)
# =========================================================================== #

def test_f4a_schema_failure_appends_field_path_guidance(monkeypatch):
    """Cell A: the first draw violates the schema (extra north_axis key); the
    retry MUST append a corrective message carrying the field path, and the
    model's second (valid) draw is returned. Proves the channel opens on schema
    rejection and carries the diagnostic, not just 'a third message appeared'."""
    fc = _patch_openai(
        monkeypatch,
        [_resp(json.dumps(_v3_with_extra_north_axis_key())), _resp(json.dumps(_valid_v3_payload()))],
    )
    validate = lambda parsed: pipeline._schema_only_correction_validator(parsed, V3)  # noqa: E731
    out = pipeline._call_json_llm(
        SECTION, "sys", "human", out_dir=None, prefix="t", attempts=3,
        validate=validate, retry_guidance=retry_guidance_for_correction(V3),
    )
    assert out["schema_version"] == "3" and out["windows"] == []
    # exactly two LLM calls; the second one carried the corrective message.
    assert len(fc.received_messages) == 2
    second = fc.received_messages[1]
    assert len(second) == 3, "schema failure must append a corrective third message"
    assert second[2]["role"] == "user"
    guidance = second[2]["content"]
    # carries the field PATH (the diagnostic that was missing before F-4a) ...
    assert "field path: north_axis.note" in guidance
    # ... and the schema's mechanically-derived legal field-set for that field.
    assert "value_deg" in guidance  # a north_axis allowed field
    # FORMAT-only: never echoes the rejected draw's geometry/coordinates.
    assert "[0.0, 4.0]" not in guidance
    assert "FORMAT error" in guidance


# =========================================================================== #
# F-4a — transport failure retries BLIND (no corrective message) (cell B)
# =========================================================================== #

def test_f4a_transport_failure_retries_blind(monkeypatch):
    """Cell B: the first call raises a transport exception (the create() raised
    before any response — content stays empty); the retry MUST NOT append a
    corrective message. retry_guidance is wired (same as cell A) yet stays
    silent here, proving the channel is gated on 'we got a model response', not
    on 'retry_guidance is non-None'.

    The spy pins the actual gate: a transport failure (empty content) must not
    even INVOKES retry_guidance. Without this, the len==2 assertion could be
    satisfied by 'invoke guidance but it returns None', hiding a broken
    content gate."""
    fc = _patch_openai(
        monkeypatch,
        [ConnectionError("simulated 5xx / timeout"), _resp(json.dumps(_valid_v3_payload()))],
    )
    validate = lambda parsed: pipeline._schema_only_correction_validator(parsed, V3)  # noqa: E731
    base_guide = retry_guidance_for_correction(V3)
    guidance_calls: list[BaseException] = []

    def spy(exc):
        guidance_calls.append(exc)
        return base_guide(exc)

    out = pipeline._call_json_llm(
        SECTION, "sys", "human", out_dir=None, prefix="t", attempts=3,
        validate=validate, retry_guidance=spy,
    )
    assert out["schema_version"] == "3"
    assert len(fc.received_messages) == 2
    # both calls carried only system + human — no corrective third message,
    # even though retry_guidance was wired identically to cell A.
    for msgs in fc.received_messages:
        assert len(msgs) == 2
    # AND retry_guidance was never consulted — the content gate kept the blind
    # retry blind at the call site, not just by returning None downstream.
    assert guidance_calls == [], "transport failure (empty content) must not invoke retry_guidance"


# =========================================================================== #
# F-4a — a semantic ValueError retries BLIND (content present, guidance None)
# =========================================================================== #

def test_f4a_semantic_valueerror_retries_blind(monkeypatch):
    """The third path: the draw parses and is schema-valid but fails a SEMANTIC
    check (0 windows emitted while reading had window strokes). content is
    non-empty, so the 'we got a response' gate is open — yet retry_guidance
    returns None because a semantic ValueError is not a schema ValidationError.
    The retry MUST stay blind: the inner retry owns ONLY schema/format, never
    semantic draw quality (that is gate①'s job)."""
    fc = _patch_openai(
        monkeypatch,
        [_resp(json.dumps(_valid_v3_payload())), _resp(json.dumps(_v3_with_window()))],
    )
    # Full composite validator: schema (pydantic) THEN semantic draw issues.
    validate = lambda parsed: pipeline._make_correction_validator(5, V3)(parsed)  # noqa: E731
    out = pipeline._call_json_llm(
        SECTION, "sys", "human", out_dir=None, prefix="t", attempts=3,
        validate=validate, retry_guidance=retry_guidance_for_correction(V3),
    )
    assert len(out["windows"]) == 1
    assert len(fc.received_messages) == 2
    second = fc.received_messages[1]
    assert len(second) == 2, "semantic ValueError must NOT append corrective guidance"


# =========================================================================== #
# F-4a — retry_guidance itself: schema ValidationError ⇒ guidance; others ⇒ None
# =========================================================================== #

def test_f4a_retry_guidance_is_schema_only():
    """Directly pins the predicate retry_guidance uses: a pydantic
    ValidationError yields a non-None guidance with field paths; a transport
    exception, a JSON syntax error, and a semantic ValueError all yield None."""
    guide = retry_guidance_for_correction(V3)

    # schema ValidationError (real, via the v3 model) -> guidance with paths
    from pydantic import ValidationError
    from src.agent.correction.schema import CorrectedGeometryV3
    try:
        CorrectedGeometryV3.model_validate(_v3_with_extra_north_axis_key())
        raise AssertionError("expected ValidationError")
    except ValidationError as exc:
        msg = guide(exc)
    assert msg is not None
    assert "field path: north_axis.note" in msg

    # everything else -> None (blind)
    assert guide(ConnectionError("net")) is None
    assert guide(ValueError("0 windows")) is None
    assert guide(json.JSONDecodeError("msg", "doc", 0)) is None


# =========================================================================== #
# F-4b — system prompt vocabulary is mechanically derived from the schema
#         (write a second, hand-copied list and this goes red)
# =========================================================================== #

def _tokens_after_last_colon(line: str) -> set[str]:
    return {t.strip() for t in line.rsplit(":", 1)[-1].split(",") if t.strip()}


def test_f4b_system_prompt_vocabulary_equals_schema_derivation(tmp_path):
    """The v3 correction system prompt carries an ALLOWED VOCABULARY block whose
    token sets are EXACTLY the schema's mechanically-derived sets — compared
    directly against the schema sources (WINDOW_CLAIMS / NorthAxisEvidence
    model_fields), not against the prompt's own helper, so hand-copying a stale
    or divergent list into the prompt goes red the moment it disagrees."""
    from src.agent.correction.claims import WINDOW_CLAIMS
    from src.agent.correction.schema import NorthAxisEvidence

    (tmp_path / "reading_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "1f_view.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    system, _ = pipeline._build_correction_messages(tmp_path, "{}", target=V3)

    assert "BEGIN ALLOWED VOCABULARY" in system and "END ALLOWED VOCABULARY" in system
    block = system.split("BEGIN ALLOWED VOCABULARY", 1)[1].split("END ALLOWED VOCABULARY", 1)[0]

    win_line = next(l for l in block.splitlines() if "opening-claim vocabulary" in l)
    na_line = next(l for l in block.splitlines() if "north_axis" in l and "allowed fields" in l)

    assert _tokens_after_last_colon(win_line) == set(sorted(WINDOW_CLAIMS))
    assert _tokens_after_last_colon(na_line) == set(sorted(NorthAxisEvidence.model_fields))


def test_f4b_v1_prompt_has_no_vocabulary_block(tmp_path):
    """v1 (rectangular) carries neither window provenance nor north_axis, so its
    prompt is byte-identical to before — no ALLOWED VOCABULARY block appears."""
    rect = correction_target("rectangular")
    (tmp_path / "reading_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "1f_view.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    system, _ = pipeline._build_correction_messages(tmp_path, "{}", target=rect)
    assert "ALLOWED VOCABULARY" not in system
    assert "opening-claim vocabulary" not in system


def test_f4b_vocab_helpers_derive_from_schema_sources():
    """The vocab helpers themselves read the schema sources (not a hand-copied
    constant): window keys == sorted(WINDOW_CLAIMS), north_axis fields == sorted
    NorthAxisEvidence.model_fields. If someone replaces the derivation with a
    literal list, this reds as soon as the schema source disagrees with it."""
    from src.agent.correction.claims import WINDOW_CLAIMS
    from src.agent.correction.schema import NorthAxisEvidence

    assert window_provenance_vocabulary() == sorted(WINDOW_CLAIMS)
    assert north_axis_allowed_fields() == sorted(NorthAxisEvidence.model_fields)
