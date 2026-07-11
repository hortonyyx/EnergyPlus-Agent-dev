"""C2 B-M/B2 §2.8: the shared claims vocabulary (single source, consumed by
view-manifest opening_evidence, WindowV3.provenance keys, Va, B4b)."""

from __future__ import annotations

from src.agent.correction import claims


def test_window_claims_is_exactly_the_seven_e2_words():
    assert claims.WINDOW_CLAIMS == frozenset(
        {"existence", "host", "along", "width", "sill", "head", "appearance"}
    )


def test_named_constants_match_vocab_strings():
    assert claims.CLAIM_EXISTENCE == "existence"
    assert claims.CLAIM_HOST == "host"
    assert claims.CLAIM_ALONG == "along"
    assert claims.CLAIM_WIDTH == "width"
    assert claims.CLAIM_SILL == "sill"
    assert claims.CLAIM_HEAD == "head"
    assert claims.CLAIM_APPEARANCE == "appearance"
    all_named = {
        claims.CLAIM_EXISTENCE, claims.CLAIM_HOST, claims.CLAIM_ALONG, claims.CLAIM_WIDTH,
        claims.CLAIM_SILL, claims.CLAIM_HEAD, claims.CLAIM_APPEARANCE,
    }
    assert all_named == claims.WINDOW_CLAIMS


def test_plan_and_elevation_potentially_observable_subsets():
    assert claims.PLAN_POTENTIALLY_OBSERVABLE_CLAIMS == frozenset(
        {"existence", "host", "along", "width"}
    )
    assert claims.ELEVATION_POTENTIALLY_OBSERVABLE_CLAIMS == frozenset(
        {"existence", "along", "width", "sill", "head", "appearance"}
    )
    assert claims.PLAN_POTENTIALLY_OBSERVABLE_CLAIMS <= claims.WINDOW_CLAIMS
    assert claims.ELEVATION_POTENTIALLY_OBSERVABLE_CLAIMS <= claims.WINDOW_CLAIMS


def test_claims_vocab_version_is_a_string_constant():
    assert claims.CLAIMS_VOCAB_VERSION == "1"
