from __future__ import annotations

from pathlib import Path

from src.agent.correction.envelope import (
    EnvelopeCandidate,
    extract_authoritative_envelope,
    extract_envelope_candidates_from_dir,
    extract_envelope_candidates_from_view,
    resolve_authoritative_envelope,
)
from src.agent.reading import load_reading_view


_SM21 = Path("case_tests/e2e_tests/sm21_anchor")
_SONNET = _SM21 / "run_2026-06-20_sonnet_reading" / "0_reading"
_GPT54 = _SM21 / "run_2026-06-20_gpt54_reading" / "0_reading"


def test_sonnet_south_d1_uses_endpoint_bounds_not_legacy_value_m():
    view = load_reading_view(_SONNET / "South_view.json")
    candidates = extract_envelope_candidates_from_view(view, view_name="South_view")
    d1 = next(c for c in candidates if c.view == "South" and c.source_id == "D1")
    assert d1.bounds == (0.0, 15.0)
    assert d1.span == 15.0
    assert d1.span != 15000.0
    assert "ignored inconsistent value_m=" in (d1.note or "")


def test_sonnet_all_facades_resolve_to_15_by_8_outer_envelope():
    env = extract_authoritative_envelope(
        _SONNET,
        footprint={"x": (0.12, 14.88), "y": (0.12, 7.88)},
        footprint_tolerance_m=0.30,
    )
    assert env.axis("x").status == "accepted"
    assert env.axis("x").bounds == (0.0, 15.0)
    assert env.axis("x").span == 15.0
    assert env.axis("y").status == "accepted"
    assert env.axis("y").bounds == (0.0, 8.0)
    assert env.axis("y").span == 8.0


def test_gpt54_empty_dimensions_extracts_outline_and_wall_fill():
    candidates = extract_envelope_candidates_from_dir(_GPT54)
    assert not [c for c in candidates if c.source_kind == "dimension"]
    assert any(c.axis == "x" and c.source_kind == "outline" and c.bounds == (0.0, 15.0) for c in candidates)
    assert any(c.axis == "y" and c.source_kind == "wall_fill" and c.bounds == (0.0, 8.0) for c in candidates)

    env = extract_authoritative_envelope(
        _GPT54,
        footprint={"x": (0.12, 14.88), "y": (0.12, 7.88)},
        footprint_tolerance_m=0.30,
    )
    assert env.axis("x").status == "accepted"
    assert env.axis("x").bounds == (0.0, 15.0)
    assert env.axis("y").status == "accepted"
    assert env.axis("y").bounds == (0.0, 8.0)


def test_cross_facade_authoritative_disagreement_conflicts_not_max():
    candidates = [
        EnvelopeCandidate("x", (0.0, 15.0), 15.0, "dimension", "South", "D1", role="overall", confidence=0.95),
        EnvelopeCandidate("x", (0.0, 15.2), 15.2, "dimension", "North", "D1", role="overall", confidence=0.95),
    ]
    env = resolve_authoritative_envelope(
        candidates,
        footprint={"x": (0.12, 14.88)},
        footprint_tolerance_m=0.30,
    )
    assert env.axis("x").status == "conflict"


def test_single_facade_without_authority_or_stroke_agreement_skips():
    candidates = [
        EnvelopeCandidate("x", (0.0, 15.0), 15.0, "dimension", "South", "D2", confidence=0.70),
    ]
    env = resolve_authoritative_envelope(
        candidates,
        footprint={"x": (0.12, 14.88)},
        footprint_tolerance_m=0.30,
    )
    assert env.axis("x").status == "skipped"
    assert "insufficient evidence" in env.axis("x").reason


def test_single_facade_overall_authority_can_accept_with_footprint_gate():
    candidates = [
        EnvelopeCandidate(
            "x",
            (0.0, 15.0),
            15.0,
            "dimension",
            "South",
            "D1",
            note="top overall total width",
            confidence=0.95,
        ),
    ]
    env = resolve_authoritative_envelope(
        candidates,
        footprint={"x": (0.12, 14.88)},
        footprint_tolerance_m=0.30,
    )
    assert env.axis("x").status == "accepted"
    assert env.axis("x").bounds == (0.0, 15.0)
