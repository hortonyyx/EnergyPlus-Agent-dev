"""Locks for the F-6 dispatch (commit following 0256060): the correction LLM
emitted ``provenance`` VALUES outside the schema's enum
(``'transcribed_dimension'`` / ``'inferred_topology'``) and burned the whole
retry budget, because F-4's mechanically-derived vocabulary covered only the
``provenance`` dict KEYS (the opening-claim names) and the ``north_axis`` field
set — NOT the observed/derived/assumed VALUE enum on each claim.

F-6 folds that VALUE enum into the SAME F-4 mechanism (single source in
``correction/vocab.py``): derived from the schema's own ``Literal`` annotations,
never hand-copied, never widening the schema. Two lock families:

* **derivation = schema** — the exported kind list and the system-prompt block
  are element-equal to ``FieldProvenance.provenance`` / ``NorthAxisEvidence
  .provenance`` (so a schema change propagates to the prompt with no manual
  sync, and a hand-copied stale list reds the moment it disagrees);
* **two-cell retry** — a draw with an illegal VALUE gets a corrective message
  carrying the legal enum (cell A); a draw with a different shape of error
  (a bad KEY, a north_axis extra field) does NOT (cell B), proving the value
  guidance is targeted, not unconditionally injected.
"""

from __future__ import annotations

import json
from typing import get_args

import pytest
from pydantic import ValidationError

from src.agent import pipeline
from src.agent.correction.parse import correction_target
from src.agent.correction.schema import CorrectedGeometryV3, FieldProvenance, NorthAxisEvidence
from src.agent.correction.vocab import (
    provenance_kind_vocabulary,
    retry_guidance_for_correction,
)

V3 = correction_target("orthogonal_polygon")
VALUE_GUIDANCE_PHRASE = "legal `provenance` value"


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


def _window(claim_payload: dict) -> dict:
    """A minimal window whose ``provenance`` dict is ``claim_payload`` (used to
    build a schema-valid-except-for-provenance draw)."""
    base = _valid_v3_payload()
    base["windows"] = [
        {
            "id": "W1",
            "floor": "F1",
            "floor_id": "F1",
            "facade": "South",
            "span": [1.0, 2.0],
            "z": [0.5, 2.5],
            "room": "A",
            "provenance": claim_payload,
        }
    ]
    return base


def _validate_error(payload: dict) -> ValidationError:
    """Return the real ValidationError from the v3 schema (not a hand-built one),
    so the loc shape the retry guidance sees is exactly production's."""
    try:
        CorrectedGeometryV3.model_validate(payload)
        raise AssertionError("expected a ValidationError")
    except ValidationError as exc:
        return exc


def _tokens_after_last_colon(line: str) -> set[str]:
    return {t.strip() for t in line.rsplit(":", 1)[-1].split(",") if t.strip()}


# =========================================================================== #
# derivation == schema enum (single source; a hand-copied list reds on drift)
# =========================================================================== #
def test_f6_provenance_kinds_derived_from_schema_enum():
    """The exported kind list is the schema's own Literal args, not a hand-copied
    constant: element-equal to BOTH ``FieldProvenance.provenance`` (the claim
    enum the model got wrong) and ``NorthAxisEvidence.provenance``. The helper
    itself asserts the two Literal declarations agree, so adding a fourth kind to
    one but not the other reds here (drift guard)."""
    field_kinds = set(get_args(FieldProvenance.model_fields["provenance"].annotation))
    north_kinds = set(get_args(NorthAxisEvidence.model_fields["provenance"].annotation))

    kinds = set(provenance_kind_vocabulary())

    assert kinds == field_kinds == north_kinds
    # the live enum today (anchors the test to a known shape)
    assert kinds == {"observed", "derived", "assumed"}


def test_f6_prompt_carries_schema_provenance_kinds(tmp_path):
    """The v3 system prompt's ALLOWED VOCABULARY block lists the provenance VALUE
    enum, and that listed set is EXACTLY the schema-derived kind set — compared
    against the schema's Literal args, not the prompt's own helper, so a stale or
    divergent hand-copied list in the prompt reds the moment it disagrees."""
    (tmp_path / "reading_summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "1f_view.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    system, _ = pipeline._build_correction_messages(tmp_path, "{}", target=V3)

    assert "BEGIN ALLOWED VOCABULARY" in system
    block = system.split("BEGIN ALLOWED VOCABULARY", 1)[1].split("END ALLOWED VOCABULARY", 1)[0]
    value_line = next(
        line for line in block.splitlines() if "provenance" in line and "VALUE" in line
    )

    schema_kinds = set(get_args(FieldProvenance.model_fields["provenance"].annotation))
    assert _tokens_after_last_colon(value_line) == schema_kinds == set(provenance_kind_vocabulary())


# =========================================================================== #
# two-cell retry guidance (cell A: illegal VALUE -> carries the legal enum)
# =========================================================================== #
def test_f6_retry_guidance_carries_kinds_on_illegal_value():
    """Cell A (the F-6 bug shape): a window claim with ``provenance`` =
    ``'transcribed_dimension'`` (the exact off-vocabulary value that burned the
    retry budget) yields a corrective message carrying the field PATH and the
    schema's legal value enum. Proves the channel opens on a provenance-VALUE
    rejection and carries the enum, not just 'a guidance message appeared'."""
    exc = _validate_error(
        _window({"existence": {"provenance": "transcribed_dimension", "source_ids": ["src:00"]}})
    )
    msg = retry_guidance_for_correction(V3)(exc)
    assert msg is not None
    # the field path points at the claim's provenance value ...
    assert "field path: windows.0.provenance.existence.provenance" in msg
    # ... and the schema's mechanically-derived legal value enum is attached.
    assert VALUE_GUIDANCE_PHRASE in msg
    for kind in ("observed", "derived", "assumed"):
        assert kind in msg
    # FORMAT-only: never echoes the rejected draw's coordinates.
    assert "[0.0, 4.0]" not in msg


def test_f6_retry_guidance_kinds_targeted_to_value_errors():
    """Cell B (discriminating negative): the value enum is NOT injected for
    errors that are not a provenance-VALUE rejection. A bad KEY (an unknown
    opening-claim name) is guided to the KEY vocabulary, and a north_axis extra
    field is guided to the field set — neither carries the value-enum phrase.
    Catches a regression where the value guidance is made unconditional."""
    guide = retry_guidance_for_correction(V3)

    # bad KEY: an opening-claim name outside the vocabulary -> KEY guidance.
    key_exc = _validate_error(
        _window(
            {
                "existence": {"provenance": "observed", "source_ids": ["src:00"]},
                "bogus_claim": {"provenance": "observed"},
            }
        )
    )
    key_msg = guide(key_exc)
    assert key_msg is not None
    assert "opening-claim vocabulary" in key_msg
    assert VALUE_GUIDANCE_PHRASE not in key_msg

    # north_axis extra field -> field-set guidance, not the value enum.
    na_payload = _valid_v3_payload()
    na_payload["north_axis"] = {
        "value_deg": 0.0,
        "provenance": "observed",
        "source_ids": ["s1"],
        "note": "extra key not in the schema",
    }
    na_msg = guide(_validate_error(na_payload))
    assert na_msg is not None
    assert "value_deg" in na_msg  # a north_axis allowed field
    assert VALUE_GUIDANCE_PHRASE not in na_msg

    # non-schema failures stay blind (the inner retry owns ONLY schema/format).
    assert guide(ValueError("0 windows")) is None
