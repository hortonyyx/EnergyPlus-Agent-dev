"""②-1b-T R1/R2/R3: the staging root's write- and read-side reproducibility
gates, and the structural (⛔ not lexical) closure of the promotion seam.

Uses the same synthetic ``AsMeasuredV1`` builder as
``tests/test_gt_revisions_and_as_signed.py`` (schema/derivation concerns);
the REAL sm25 trio's own write/read round trip is exercised separately below
so this file also proves the new gates do not regress the one real case that
matters (dispatch acceptance #3).
"""
from __future__ import annotations

import json

import pytest

import src.agent.judge.gt_facts_staging as gt_facts_staging
from src.agent.judge.as_measured import AsMeasuredV1, content_sha256
from src.agent.judge.gt_facts_staging import (read_facts_candidate,
                                              write_facts_candidate)
from src.agent.judge.gt_revisions import (AsSignedReproductionError, AsSignedV1,
                                          RevisionsLedgerV1,
                                          as_signed_content_sha256,
                                          canonical_as_signed_bytes,
                                          derive_as_signed)
from tests.test_gt_revisions_and_as_signed import _minimal_doc

CASE = "synthetic-staging-gate"


def _empty_ledger(as_measured: AsMeasuredV1) -> RevisionsLedgerV1:
    return RevisionsLedgerV1(case=as_measured.case,
                             as_measured_content_sha256=content_sha256(as_measured),
                             revisions=[])


def _tamper(as_signed: AsSignedV1) -> AsSignedV1:
    raw = as_signed.model_dump(mode="json")
    raw["views"][0]["face_lines"][0]["const"] += 1
    return AsSignedV1.model_validate(raw)


# =========================================================================== #
# R1 -- write side (dispatch acceptance #1, #5)
# =========================================================================== #
def test_r1_write_side_rejects_an_inconsistent_trio_and_leaves_no_residue(tmp_path, monkeypatch):
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    as_measured = _minimal_doc()
    ledger = _empty_ledger(as_measured)
    genuine = derive_as_signed(as_measured, ledger)
    tampered = _tamper(genuine)
    assert canonical_as_signed_bytes(tampered) != canonical_as_signed_bytes(genuine)

    out_dir = gt_facts_staging._facts_staging_dir(CASE)
    assert not out_dir.exists()

    # ⭐ Prove this is THE NEW gate blocking it, not an incidental I/O
    # failure: the exact same tampered bytes are perfectly writable when the
    # gate is bypassed -- this is exactly what ``write_facts_candidate``
    # itself did before R1 (write first, verify never). If this write did
    # NOT succeed, the assertion below (the gated call leaves no residue)
    # would be proving nothing.
    gt_facts_staging._write_atomic(out_dir / "as_signed.json",
                                   canonical_as_signed_bytes(tampered))
    assert (out_dir / "as_signed.json").is_file()
    (out_dir / "as_signed.json").unlink()
    out_dir.rmdir()
    assert not out_dir.exists()

    # The gated call: must fail loudly, and touch the filesystem not at all.
    with pytest.raises(AsSignedReproductionError):
        write_facts_candidate(CASE, as_measured, ledger, tampered)
    assert not out_dir.exists(), "a rejected write must leave zero residual files/dirs"


def test_r1_a_consistent_trio_still_writes_in(tmp_path, monkeypatch):
    """The negative fixture above only proves the door has teeth if the SAME
    door lets a genuine trio through (dispatch acceptance #3's write half)."""
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    as_measured = _minimal_doc()
    ledger = _empty_ledger(as_measured)
    genuine = derive_as_signed(as_measured, ledger)
    out_dir = write_facts_candidate(CASE, as_measured, ledger, genuine)
    assert (out_dir / "as_measured.json").is_file()
    assert (out_dir / "revisions.json").is_file()
    assert (out_dir / "as_signed.json").is_file()


# =========================================================================== #
# R2 -- read side (dispatch acceptance #2, #5)
# =========================================================================== #
def test_r2_read_side_rejects_a_hand_tampered_as_signed(tmp_path, monkeypatch):
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    as_measured = _minimal_doc()
    ledger = _empty_ledger(as_measured)
    genuine = derive_as_signed(as_measured, ledger)
    write_facts_candidate(CASE, as_measured, ledger, genuine)

    out_dir = gt_facts_staging._facts_staging_dir(CASE)
    raw_bytes = (out_dir / "as_signed.json").read_bytes()

    # ⭐ Prove parsing ALONE (what ``read_facts_candidate`` did before R2 --
    # three independent ``model_validate_json`` calls, no cross-check) does
    # NOT notice the tamper about to be introduced: it is schema-valid, just
    # no longer the document that reproduces from (as_measured, ledger).
    AsSignedV1.model_validate_json(raw_bytes)

    # Hand-tamper the file on disk directly -- NOT through this module. This
    # is exactly the attack R2 exists for (dispatch §二 R2's "文件可以被任何
    # 人用任何方式放进那个目录"): something else edited a file already sitting
    # in the staging directory.
    tampered_raw = json.loads(raw_bytes)
    tampered_raw["views"][0]["face_lines"][0]["const"] += 1
    (out_dir / "as_signed.json").write_text(
        json.dumps(tampered_raw, ensure_ascii=False), encoding="utf-8")

    # Each file, read on its own, is still schema-valid JSON -- confirming
    # the failure below can only come from the NEW cross-document check.
    AsSignedV1.model_validate_json((out_dir / "as_signed.json").read_bytes())

    with pytest.raises(AsSignedReproductionError):
        read_facts_candidate(CASE)


def test_r2_a_genuinely_unmodified_trio_still_reads_out(tmp_path, monkeypatch):
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    as_measured = _minimal_doc()
    ledger = _empty_ledger(as_measured)
    genuine = derive_as_signed(as_measured, ledger)
    write_facts_candidate(CASE, as_measured, ledger, genuine)

    read_am, read_ledger, read_signed = read_facts_candidate(CASE)
    assert content_sha256(read_am) == content_sha256(as_measured)
    assert as_signed_content_sha256(read_signed) == as_signed_content_sha256(genuine)


# =========================================================================== #
# R3 -- structural closure of the promotion seam (dispatch acceptance #4, #5)
# =========================================================================== #
def test_r3_no_public_path_or_directory_accessor_is_exported():
    """⭐⭐ This is the fixture that WOULD have failed against the
    pre-②-1b-T module: ``__all__`` used to be
    ``["FACTS_STAGING_ROOT", "facts_staging_dir", "write_facts_candidate",
    "read_facts_candidate"]`` -- a future ``promote_gt_v3`` could import
    ``facts_staging_dir(case)`` and ``shutil.copytree`` it straight into
    ``gt/<case>/facts/`` without ever going through a verified read.

    ⭐ ②-1b-T-R (rework, R1/GLM F-1): ``__all__`` grew a THIRD name,
    ``FactsStagingCaseError`` -- deliberately public, because a caller
    building ``case`` from something outside its control needs a stable
    exception type to catch. This does NOT reopen the R3 gap: an exception
    CLASS is not a path or a directory handle, it cannot be handed to
    ``shutil.copytree``, and asserting the exact 2-name set (as the
    pre-rework version of this test did) would now fail on every future
    legitimate addition to ``__all__`` that has nothing to do with paths --
    the test would be measuring "did the set change at all", not "is a
    path/directory accessor exported", which is the actual thing R3 cares
    about. Hence: assert the *specific* names this dispatch closed off
    stay closed, not that ``__all__`` is frozen at exactly two entries.
    """
    assert set(gt_facts_staging.__all__) == {
        "write_facts_candidate", "read_facts_candidate", "FactsStagingCaseError"}
    assert not hasattr(gt_facts_staging, "facts_staging_dir")
    assert not hasattr(gt_facts_staging, "FACTS_STAGING_ROOT")
    # FactsStagingCaseError being public does not reopen R3's gap: it is an
    # exception CLASS, not a callable that could ever return a Path a caller
    # hands to shutil.copytree (that property is checked on the actual
    # return values of the other two exports by
    # test_r3_read_facts_candidate_returns_typed_documents_never_a_path,
    # below).
    assert isinstance(gt_facts_staging.FactsStagingCaseError, type)
    assert issubclass(gt_facts_staging.FactsStagingCaseError, ValueError)
    # The capability has not vanished (staging still has to know where its
    # own files live) -- it is merely no longer part of the public surface a
    # future promotion implementer would discover and reach for:
    assert hasattr(gt_facts_staging, "_facts_staging_dir")
    assert "_facts_staging_dir" not in gt_facts_staging.__all__


def test_r3_read_facts_candidate_returns_typed_documents_never_a_path(tmp_path, monkeypatch):
    """The one sanctioned exit for CONSUMING staged facts returns the same
    three Pydantic types ``write_facts_candidate`` accepts -- never a
    filesystem handle a caller could hand to ``shutil.copytree``. Checked on
    the ACTUAL returned objects (not just the annotation, which
    ``from __future__ import annotations`` leaves as an unevaluated string)."""
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    as_measured = _minimal_doc()
    ledger = _empty_ledger(as_measured)
    genuine = derive_as_signed(as_measured, ledger)
    write_facts_candidate(CASE, as_measured, ledger, genuine)

    result = read_facts_candidate(CASE)
    assert isinstance(result, tuple) and len(result) == 3
    got_am, got_ledger, got_signed = result
    assert isinstance(got_am, AsMeasuredV1)
    assert isinstance(got_ledger, RevisionsLedgerV1)
    assert isinstance(got_signed, AsSignedV1)
    assert not any(hasattr(x, "__fspath__") for x in result)  # ⛔ no Path-like object anywhere


# =========================================================================== #
# Not-misfired-on-the-real-thing (dispatch acceptance #3)
# =========================================================================== #
def test_real_sm25_trio_still_writes_in_and_reads_out_through_both_new_gates(tmp_path, monkeypatch):
    """The REAL, already-committed ``sm25-L_anchor`` staging trio (proven to
    reproduce bit-for-bit in ``tests/test_gt_facts_staging_sm25.py``) must
    not be caught by either new gate: round-trip it through a SECOND,
    isolated staging root via the now-gated ``write_facts_candidate`` /
    ``read_facts_candidate`` and confirm the content survives byte-for-byte.
    """
    real_as_measured, real_ledger, real_as_signed = read_facts_candidate("sm25-L_anchor")

    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    write_facts_candidate("sm25-L_anchor", real_as_measured, real_ledger, real_as_signed)
    round_tripped_am, round_tripped_ledger, round_tripped_signed = read_facts_candidate(
        "sm25-L_anchor")

    assert content_sha256(round_tripped_am) == content_sha256(real_as_measured)
    assert as_signed_content_sha256(round_tripped_signed) == as_signed_content_sha256(
        real_as_signed)
    assert round_tripped_ledger.model_dump(mode="json") == real_ledger.model_dump(mode="json")
