"""Mechanically-derived correction schema vocabulary — the SINGLE source both
the correction system prompt (F-4b) and the inner-retry corrective message
(F-4a) read from.

Why this module exists: the correction LLM draw is single-shot, and its only
feedback on a schema rejection used to be a *blind* re-issue of the same
prompt — ``_call_json_llm`` wrote the validation error to disk and retried
verbatim, so a systematic schema misunderstanding (e.g. an unknown
``north_axis`` key, or a non-vocabulary window ``provenance`` key) burned the
whole retry budget on the same mistake and then crashed the flow. The fix tells
the model *which field* broke and *what the legal tokens are* — but the legal
tokens MUST come from the schema itself (``WINDOW_CLAIMS`` /
``NorthAxisEvidence.model_fields``), never from a hand-copied second list. A
second list is a second ruler, and this project has been bitten by that before.

These helpers derive the vocabulary mechanically, so a schema change propagates
to both the prompt and the retry message with no manual sync step to forget.
They carry ONLY format / word-list information — never geometry, upstream
reading content, gt, or numeric values from a rejected draw.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, get_args


def window_provenance_vocabulary() -> list[str]:
    """Legal keys for ``WindowV3.provenance`` — the opening-claim vocabulary.

    Derived from ``WINDOW_CLAIMS`` (the schema's authoritative word list in
    ``claims.py``), not hand-copied."""
    from src.agent.correction.claims import WINDOW_CLAIMS

    return sorted(WINDOW_CLAIMS)


def provenance_kind_vocabulary() -> list[str]:
    """Legal VALUES for a claim's ``provenance`` field — observed / derived /
    assumed (the VALUE enum, distinct from :func:`window_provenance_vocabulary`
    which is the claim-name KEY set).

    Derived mechanically from ``FieldProvenance.provenance``'s own ``Literal``
    annotation (the schema's authoritative enum), not hand-copied, and asserted
    element-equal to ``NorthAxisEvidence.provenance`` so the two Literal
    declarations cannot drift. A schema change (a fourth kind added to either)
    propagates to both the system prompt and the retry message automatically."""
    from src.agent.correction.schema import FieldProvenance, NorthAxisEvidence

    field_kinds = get_args(FieldProvenance.model_fields["provenance"].annotation)
    north_kinds = get_args(NorthAxisEvidence.model_fields["provenance"].annotation)
    if set(field_kinds) != set(north_kinds):
        raise AssertionError(
            "FieldProvenance.provenance and NorthAxisEvidence.provenance enums "
            f"drifted: {field_kinds} vs {north_kinds}"
        )
    return sorted(field_kinds)


def north_axis_allowed_fields() -> list[str]:
    """Legal top-level fields on ``NorthAxisEvidence`` (``extra='forbid'``).

    Derived from the pydantic model's own field declarations, not hand-copied."""
    from src.agent.correction.schema import NorthAxisEvidence

    return sorted(NorthAxisEvidence.model_fields)


def _is_v3_target(target: Any) -> bool:
    schema_model = getattr(target, "schema_model", None)
    try:
        from src.agent.correction.schema import CorrectedGeometryV3

        return isinstance(schema_model, type) and issubclass(schema_model, CorrectedGeometryV3)
    except Exception:  # noqa: BLE001 — a malformed target is simply "not v3"
        return False


def _provenance_value_break(loc: tuple) -> bool:
    """True when a ``ValidationError`` loc targets a claim's ``provenance`` VALUE
    (the observed/derived/assumed ``Literal`` on ``FieldProvenance`` /
    ``NorthAxisEvidence``) — as opposed to the window ``provenance`` dict KEY set.

    Both shapes end in ``'provenance'``: a window claim's value error is
    ``('windows', i, 'provenance', <claim>, 'provenance')`` and north_axis's is
    ``('north_axis', 'provenance')``, whereas the window key-set rejection is
    exactly ``('windows', i, 'provenance')`` (the dict field itself). The key-set
    case is the one shape to exclude so it is guided to the KEY vocabulary, not
    the value enum."""
    if not loc or str(loc[-1]) != "provenance":
        return False
    if str(loc[0]) == "windows" and len(loc) == 3:
        return False
    return True


def correction_schema_vocabulary(target: Any) -> dict[str, list[str]]:
    """Map of stable label -> sorted legal tokens for the target schema.

    Only v3 (``CorrectedGeometryV3``) carries ``WindowV3.provenance`` and
    ``north_axis``; v1 (rectangular) has neither, so its vocabulary map is
    empty and the prompt/retry path adds nothing — legacy behaviour unchanged."""
    if not _is_v3_target(target):
        return {}
    return {
        "window_provenance_keys": window_provenance_vocabulary(),
        "provenance_kinds": provenance_kind_vocabulary(),
        "north_axis_fields": north_axis_allowed_fields(),
    }


def format_correction_system_vocabulary(target: Any) -> str:
    """The allowed-vocabulary block for the correction system prompt (F-4b).

    Empty string for targets that carry no constrained vocabulary (v1), so the
    v1 prompt is byte-identical to before the change."""
    vocab = correction_schema_vocabulary(target)
    if not vocab:
        return ""
    lines = [
        "===== BEGIN ALLOWED VOCABULARY (mechanically derived from the schema; "
        "if the schema changes this block changes with it — never invent tokens "
        "outside it) =====",
    ]
    if "window_provenance_keys" in vocab:
        lines.append(
            "window `provenance` keys — the opening-claim vocabulary (use ONLY "
            "these; any other key is rejected): "
            + ", ".join(vocab["window_provenance_keys"])
        )
    if "provenance_kinds" in vocab:
        lines.append(
            "each claim's `provenance` VALUE — observed/derived/assumed (the value "
            "of every opening-claim AND north_axis; any other string is rejected): "
            + ", ".join(vocab["provenance_kinds"])
        )
    if "north_axis_fields" in vocab:
        lines.append(
            "`north_axis` allowed fields (the schema rejects any extra key): "
            + ", ".join(vocab["north_axis_fields"])
        )
    lines.append("===== END ALLOWED VOCABULARY =====")
    return "\n".join(lines) + "\n\n"


def retry_guidance_for_correction(target: Any) -> Callable[[BaseException], str | None]:
    """Build the inner-retry corrective-message callable for ``_call_json_llm`` (F-4a).

    Returns a machine-generated, FORMAT-ONLY correction when the failure is a
    Pydantic schema ``ValidationError``: each error's field path + the
    validator's own reason + the schema's mechanically-derived legal vocabulary
    / field-set for that field. Returns ``None`` for any other failure
    (transport, JSON syntax, a semantic ``ValueError`` from
    ``correction_draw_issues``) so those retry blind — the inner retry owns
    ONLY schema/format robustness, never geometry, upstream content, gt, or
    numeric values (run_stage.py:320 "Inner retry handles ONLY schema/format
    robustness").

    The message never echoes the rejected draw's coordinates or numbers: only
    field paths, the validator's reason text, and the schema's legal tokens.
    """
    from pydantic import ValidationError

    # Vocab is fixed at build time; the schema model is immutable for a run, so
    # this is a cache, not a staleness risk.
    vocab = correction_schema_vocabulary(target)

    def _guide(exc: BaseException) -> str | None:
        if not isinstance(exc, ValidationError):
            return None
        lines = [
            "Your previous output was rejected by the schema validator. This is a "
            "FORMAT error only — correct the fields named below and re-emit the "
            "SAME geometry. Do NOT change any coordinate or numeric value, any "
            "room/window placement, or any upstream reading content that already "
            "passed; fix only the schema-format mistakes.",
        ]
        for err in exc.errors():
            loc = err.get("loc", ())
            path = ".".join(str(part) for part in loc)
            reason = err.get("msg", "")
            lines.append(f"- field path: {path}  reason: {reason}")
            if _provenance_value_break(loc) and "provenance_kinds" in vocab:
                lines.append(
                    "  legal `provenance` value (observed/derived/assumed): "
                    + ", ".join(vocab["provenance_kinds"])
                )
            elif "windows" in loc and "provenance" in loc and "window_provenance_keys" in vocab:
                lines.append(
                    "  legal window `provenance` keys (opening-claim vocabulary): "
                    + ", ".join(vocab["window_provenance_keys"])
                )
            elif loc and str(loc[0]) == "north_axis" and "north_axis_fields" in vocab:
                lines.append(
                    "  legal `north_axis` fields: " + ", ".join(vocab["north_axis_fields"])
                )
        return "\n".join(lines)

    return _guide
