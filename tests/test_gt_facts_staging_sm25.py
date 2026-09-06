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

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import src.agent.judge.gt_facts_staging as gt_facts_staging
from src.agent.judge.as_measured import build_as_measured, content_sha256
from src.agent.judge.gt_facts_staging import (_facts_staging_dir,
                                              read_facts_candidate,
                                              write_facts_candidate)
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
    out = _facts_staging_dir(CASE)
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


def test_6_the_worklist_is_all_unsigned_and_matches_the_a11_shape():
    """Verification #6: the待签清单 is machine-produced (recomputed here from
    scratch, not merely re-read) and every verdict is unsigned.

    ⚠️ A-11 (2026-09-05) moved this shape, MEASURED: with the 1 mm ingest
    snap in place, 13AC/160A's ~0.2 mm "difference" was pure representation
    residue and is absorbed (their records are GONE -- the user's ruling
    that residue belongs to the measurement representation, ⛔ never to a
    signed ``drawing_error``), while 13AD/13AE -- admitted as face lines by
    the ②-1b-S snap gates -- now surface their REAL correction as a
    well-formed single-field translate (const -30, i.e. 3.0 mm).  13AF
    remains inexpressible as a translate (still absent from the
    as-received face_lines).  See gt_revisions.py's module docstring."""
    before = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                               ANCHOR / "request_as_measured.json")
    after = build_as_measured(ANCHOR / "sm25-L_t3.dxf", ANCHOR / "request.json")
    recomputed = detect_translate_candidates(before, after, CHANGED_HANDLES)
    assert len(recomputed) == 3
    assert all(r.verdict == "unsigned" for r in recomputed)
    assert all(r.signed_by is None and r.signed_at is None for r in recomputed)
    well_formed = {r.target.handle: r.candidate_action for r in recomputed
                   if r.candidate_action is not None}
    assert set(well_formed) == {"13AD", "13AE"}
    for action in well_formed.values():
        assert action.field == "const" and action.delta_0p1mm == -30
    flagged = {r.target.handle for r in recomputed if r.candidate_action is None}
    assert flagged == {"13AF"}

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


def test_3_signing_the_real_const_candidate_is_refused_by_the_wall_face_gate(tmp_path):
    """⚠️ A-11 finding, locked: the ledger's real const-direction candidate
    (rev-13ad, ``const -30``) CANNOT be signed as a single-field translate --
    ``derive_as_signed``'s wall/face-line consistency gate refuses it loudly,
    because moving one face off its wall's ``face_hi`` would leave a
    ``walls`` block quietly disagreeing with the face lines it names.  A
    3.0 mm wall move needs the compiler-layer re-pairing (②-1c), ⛔ not a
    silent single-field apply.  (Pre-A-11 the signable record was
    rev-13ac's ~0.2 mm ALONG-axis trim, which never touched a wall face --
    and which the 1 mm snap has since absorbed.)"""
    as_measured, revisions, as_signed = read_facts_candidate(CASE)
    raw = revisions.model_dump(mode="json")
    entry = next(r for r in raw["revisions"] if r["id"] == "rev-13ad")
    assert entry["candidate_action"] is not None
    entry["verdict"] = "drawing_error"
    entry["action"] = entry["candidate_action"]
    entry["signed_by"] = "test"
    entry["signed_at"] = "2026-08-29T00:00:00Z"
    signed_ledger = RevisionsLedgerV1.model_validate(raw)
    with pytest.raises(AsSignedReproductionError,
                       match="as_signed_wall_face_hi_disagrees_with_its_face_lines"):
        derive_as_signed(as_measured, signed_ledger)


def test_3_hand_tampering_a_revisions_action_moves_as_signed_and_its_hash(tmp_path):
    """The staged ledger is all-unsigned (no ``action`` anywhere yet); this
    signs a WELL-FORMED along-axis translate by hand (in memory only) to
    prove the mutation direction has real teeth on THIS document, not only
    on the synthetic fixture.  The along axis is chosen deliberately: it
    trims a face line's end without moving it off its wall's face, so it is
    the one kind of action the current deriver can apply without the
    consistency gate correctly refusing (see the sibling test above for
    the const-direction refusal)."""
    as_measured, revisions, as_signed = read_facts_candidate(CASE)
    raw = revisions.model_dump(mode="json")
    entry = next(r for r in raw["revisions"] if r["id"] == "rev-13ad")
    entry["verdict"] = "drawing_error"
    entry["action"] = {"kind": "translate", "field": "along_min",
                       "delta_0p1mm": -10}
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


# =========================================================================== #
# ②-1b-T-R R2 (GLM F-2): real-shape mutations locked in on disk, through the
# ACTUAL read_facts_candidate entry point -- not the synthetic 1-view fixture
# in tests/test_gt_revisions_and_as_signed.py, and not an in-memory-only
# verify_as_signed_reproduction() call the way test_3_a_hand_tampered_*
# above does it.
#
# Cross-review ran a 20-dimension real-shape tamper matrix (18 red, 2 green
# and known-harmless) and found this file had locked in NONE of it. Picking
# WHICH 2-3 to add: the judging criterion is "does it declare covering a
# quantity that nothing here actually measures yet" -- so the three below
# are chosen to be pairwise DIFFERENT along every axis that matters, not
# "three tampers that happen to work":
#   1. as_signed.json,  on-disk, via read_facts_candidate -- the file this
#      dispatch mutates elsewhere, but never through the real read path.
#   2. as_measured.json, on-disk -- ZERO existing coverage of this file at
#      all before this rework, any dimension.
#   3. revisions.json,  on-disk, engineered to fail PYDANTIC SCHEMA
#      validation (a DxfHandle pattern violation) rather than
#      verify_as_signed_reproduction -- GLM's F-2 headline: 4/18 of its red
#      dimensions were caught by this "second line of defense", which this
#      module's own docstrings never claimed and nothing here tests.
# Each is therefore a genuinely distinct quantity: a different FILE, and (for
# #3) a different FAILURE MECHANISM -- not three variations on one theme.
# =========================================================================== #
def _real_trio_cloned_into(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Round-trip the REAL committed sm25 trio into an isolated tmp staging
    root via the actual public write/read API (never mutate the committed
    files in place -- this file's own docstring's stated pattern)."""
    real_am, real_revisions, real_as_signed = read_facts_candidate(CASE)
    monkeypatch.setattr(gt_facts_staging, "_FACTS_STAGING_ROOT", tmp_path)
    write_facts_candidate(CASE, real_am, real_revisions, real_as_signed)
    return gt_facts_staging._facts_staging_dir(CASE)


def test_r2_on_disk_as_signed_tamper_is_caught_through_the_real_read_path(tmp_path, monkeypatch):
    """Distinct from test_3_a_hand_tampered_integer_in_the_staged_as_signed_is_caught
    above: that test builds an in-memory ``AsSignedV1`` and calls
    ``verify_as_signed_reproduction`` directly. This one hand-edits the
    actual on-disk byte and goes through ``read_facts_candidate`` -- the
    entry point ②-1c will actually call -- on the real 2-view/446-face-line
    sm25 shape."""
    out_dir = _real_trio_cloned_into(tmp_path, monkeypatch)
    p = out_dir / "as_signed.json"
    raw = json.loads(p.read_text())
    raw["views"][0]["face_lines"][0]["const"] += 1
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(AsSignedReproductionError):
        read_facts_candidate(CASE)


def test_r2_on_disk_as_measured_hash_break_is_caught(tmp_path, monkeypatch):
    """``as_measured.json`` had ZERO real-shape mutation coverage in this
    file before this rework. Flips one hex digit of ``source_dxf_sha256``
    (schema-valid: still a 64-char lowercase-hex ``Hex64``, so this is NOT
    the schema-layer mechanism #3 below exercises) -- the only thing that
    can catch it is ``derive_as_signed``'s own FIRST check, the
    ``as_measured_content_sha256`` cross-reference against the ledger."""
    out_dir = _real_trio_cloned_into(tmp_path, monkeypatch)
    p = out_dir / "as_measured.json"
    raw = json.loads(p.read_text())
    original = raw["source_dxf_sha256"]
    raw["source_dxf_sha256"] = ("0" if original[0] != "0" else "1") + original[1:]
    assert raw["source_dxf_sha256"] != original
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(AsSignedReproductionError,
                       match="as_signed_revisions_do_not_target_this_as_measured"):
        read_facts_candidate(CASE)


def test_r2_on_disk_revisions_schema_break_is_caught_before_verify_even_runs(tmp_path, monkeypatch):
    """⭐⭐ GLM's F-2 headline finding, locked in: lower-cases one DXF handle
    in the staged revisions ledger. ``DxfHandle`` is ``^[0-9A-F]+$``
    (uppercase only, ``gt_schema.py``), so this fails
    ``RevisionsLedgerV1.model_validate_json`` INSIDE ``read_facts_candidate``
    -- a ``pydantic.ValidationError``, raised before
    ``verify_as_signed_reproduction`` is ever reached. A completely
    different failure mechanism from the other two tests in this section,
    which both raise ``AsSignedReproductionError`` from our OWN gate."""
    out_dir = _real_trio_cloned_into(tmp_path, monkeypatch)
    p = out_dir / "revisions.json"
    raw = json.loads(p.read_text())
    entry = raw["revisions"][0]
    original_handle = entry["target"]["handle"]
    entry["target"]["handle"] = original_handle.lower()
    assert entry["target"]["handle"] != original_handle
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValidationError):
        read_facts_candidate(CASE)
