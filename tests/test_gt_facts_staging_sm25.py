"""②-1b R1/R2/R5, end to end on REAL sm25 data: the committed
``case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/`` trio must
reproduce bit-for-bit from the signed inputs, and the reproducibility gate
must have real teeth on this exact artefact (⛔ not just on a synthetic one --
see ``tests/test_gt_revisions_and_as_signed.py`` for the schema-level tests).

This mirrors the pattern ``tests/test_gt_raw_layer.py`` already uses for
``conversion_report.json``: clone the committed trio into a tmp dir, mutate
one copy, and check the gate reacts -- never mutate the real files in place.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.judge.as_measured import build_as_measured, content_sha256
from src.agent.judge.gt_facts_staging import facts_staging_dir, read_facts_candidate
from src.agent.judge.gt_revisions import (AsSignedReproductionError, AsSignedV1,
                                          RevisionsLedgerV1,
                                          as_signed_content_sha256,
                                          detect_translate_candidates,
                                          derive_as_signed,
                                          verify_as_signed_reproduction)

REPO_ROOT = Path(__file__).resolve().parents[1]
ANCHOR = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
CASE = "sm25-L_anchor"
CHANGED_HANDLES = ("13AD", "13AC", "13AF", "160A", "13AE")


@pytest.fixture(scope="module", autouse=True)
def staging_present():
    out = facts_staging_dir(CASE)
    for name in ("as_measured.json", "revisions.json", "as_signed.json"):
        assert (out / name).is_file(), f"missing ②-1b staged fact: {out / name}"


# =========================================================================== #
# verification #1 -- the three files are real, and as_measured matches ②-1a
# =========================================================================== #
def test_1_as_measured_matches_the_as_received_build_bit_for_bit():
    staged_as_measured, _revisions, _as_signed = read_facts_candidate(CASE)
    fresh = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                              ANCHOR / "request_as_measured.json")
    assert content_sha256(staged_as_measured) == content_sha256(fresh)


def test_6_the_five_line_worklist_is_all_unsigned_with_two_well_formed_candidates():
    """Verification #6: the待签清单 is machine-produced (recomputed here from
    scratch, not merely re-read) and every verdict is unsigned."""
    before = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                               ANCHOR / "request_as_measured.json")
    after = build_as_measured(ANCHOR / "sm25-L_t3.dxf", ANCHOR / "request.json")
    recomputed = detect_translate_candidates(before, after, CHANGED_HANDLES)
    assert len(recomputed) == 5
    assert all(r.verdict == "unsigned" for r in recomputed)
    assert all(r.signed_by is None and r.signed_at is None for r in recomputed)
    well_formed = {r.target.handle for r in recomputed if r.candidate_action is not None}
    assert well_formed == {"13AC", "160A"}
    flagged = {r.target.handle for r in recomputed if r.candidate_action is None}
    assert flagged == {"13AD", "13AE", "13AF"}

    _staged_am, staged_revisions, _staged_as_signed = read_facts_candidate(CASE)
    assert {r.id for r in staged_revisions.revisions} == {r.id for r in recomputed}
    assert all(r.verdict == "unsigned" for r in staged_revisions.revisions)


# =========================================================================== #
# verification #3 -- the reproducibility gate, on the REAL committed trio
# =========================================================================== #
def test_3_the_staged_trio_reproduces_bit_for_bit():
    as_measured, revisions, as_signed = read_facts_candidate(CASE)
    verify_as_signed_reproduction(as_measured, revisions, as_signed)  # must not raise


def test_3_a_hand_tampered_integer_in_the_staged_as_signed_is_caught(tmp_path):
    as_measured, revisions, as_signed = read_facts_candidate(CASE)
    raw = as_signed.model_dump(mode="json")
    raw["views"][0]["face_lines"][0]["const"] += 1
    tampered = AsSignedV1.model_validate(raw)
    with pytest.raises(AsSignedReproductionError):
        verify_as_signed_reproduction(as_measured, revisions, tampered)


def test_3_hand_tampering_a_revisions_action_moves_as_signed_and_its_hash(tmp_path):
    """Since the staged ledger is all-unsigned (no ``action`` anywhere yet),
    this signs the 13AC candidate by hand (in memory only) to prove the
    mutation direction has real teeth on THIS document, not only on the
    synthetic fixture."""
    as_measured, revisions, as_signed = read_facts_candidate(CASE)
    raw = revisions.model_dump(mode="json")
    entry = next(r for r in raw["revisions"] if r["id"] == "rev-13ac")
    assert entry["candidate_action"] is not None
    entry["verdict"] = "drawing_error"
    entry["action"] = entry["candidate_action"]
    entry["signed_by"] = "test"
    entry["signed_at"] = "2026-08-29T00:00:00Z"
    signed_ledger = RevisionsLedgerV1.model_validate(raw)

    before_hash = content_sha256(as_measured)  # unaffected reference point
    new_as_signed = derive_as_signed(as_measured, signed_ledger)
    assert new_as_signed.model_dump(mode="json") != as_signed.model_dump(mode="json")
    assert as_signed_content_sha256(new_as_signed) != as_signed_content_sha256(as_signed)
    verify_as_signed_reproduction(as_measured, signed_ledger, new_as_signed)
    # the OLD (all-unsigned) as_signed must NOT reproduce from the NEW ledger:
    with pytest.raises(AsSignedReproductionError):
        verify_as_signed_reproduction(as_measured, signed_ledger, as_signed)
    assert content_sha256(as_measured) == before_hash  # as_measured itself untouched
