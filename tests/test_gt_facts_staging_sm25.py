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
                                          RevisionFindingV1, RevisionTargetV1,
                                          RevisionV1, RevisionsLedgerV1,
                                          as_signed_content_sha256,
                                          detect_translate_candidates,
                                          derive_as_signed,
                                          verify_as_signed_reproduction)

REPO_ROOT = Path(__file__).resolve().parents[1]
ANCHOR = REPO_ROOT / "case_tests/test_baseline/gt_sources/sm25-L_anchor"
CASE = "sm25-L_anchor"
CHANGED_HANDLES = ("13AD", "13AC", "13AF", "160A", "13AE")

#: ⭐⭐⭐ G-c (2026-09-07): the committed ledger is EMPTY, and that is the
#: unit's result -- every one of the three records it used to carry was
#: manufactured by the ingest treatment (a midpoint snap that pulled a correct
#: endpoint off its joint, and a stroke that fell between two rulers), ⛔ not by
#: the drawing.  The ladder produces the signed geometry directly, so the
#: detector finds nothing to ask a human about.
#:
#: ⛔ THAT EMPTINESS DELETES THE STOCK several locks in this file ran on: they
#: pinned ``derive_as_signed``'s behaviour by SIGNING a record that used to be
#: there.  ⛔ Deleting those locks would drop the very refusals they were
#: written to hold (F-137's wall/face-line consistency gate, the ledger's
#: hash coupling, and the schema's pre-verify rejection), so the stock is
#: BUILT here instead -- from a REAL face line of the REAL document, so the
#: signed action is still one the deriver would actually be handed.
def _synthetic_unsigned_record(as_measured, *, view_id: str = "plan-F1",
                               handle: str = "13AD",
                               field: str = "const", delta: int = -30) -> RevisionV1:
    """One well-formed, UNSIGNED candidate aimed at a face line that exists.

    ⛔ Unsigned on purpose: an unsigned record never touches geometry, so a
    ledger carrying it still reproduces the committed ``as_signed`` and can be
    round-tripped through the real write/read API.  Each test below signs its
    own copy, in memory, for the direction it is measuring.
    """
    view = next(v for v in as_measured.views if v.view_id == view_id)
    assert any(f.id == handle for f in view.face_lines), (
        f"premise: {handle} really is a face line of {view_id}")
    return RevisionV1(
        id=f"rev-{handle.lower()}",
        target=RevisionTargetV1(view_id=view_id, handle=handle),
        finding=RevisionFindingV1(
            check="synthetic_stock_for_a_lock",
            magnitude_0p1mm=delta,
            detail=("built by the test suite: the real ledger is empty after "
                    "G-c, so the behaviour under test has no shipped stock")),
        candidate_action={"kind": "translate", "field": field,
                          "delta_0p1mm": delta},
        verdict="unsigned")


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


def test_6_the_worklist_is_empty_because_the_detector_finds_nothing():
    """Verification #6, re-derived: the待签清单 is machine-produced (recomputed
    here from scratch, ⛔ not merely re-read) and it is now EMPTY.

    ⚠️ A-11 (2026-09-05) moved this shape once: with the 1 mm ingest snap in
    place, 13AC/160A's ~0.2 mm "difference" was pure representation residue and
    was absorbed, while 13AD/13AE surfaced a real ``const -30`` (3.0 mm) and
    13AF stayed inexpressible.  ⇒ 3 records.

    ⚠️⚠️ G-c (2026-09-07) moved it again, to ZERO -- and ⭐ the reason is the
    whole unit: those 3.0 mm were never the drawing's error.  The converter's
    own snap chose the MIDPOINT of a crooked stroke, which dragged the endpoint
    that was already correct 2.9 mm off the neighbour it shares a joint with;
    13AF meanwhile fell between the snap branch's entrance and the face-line
    classifier and vanished.  With the ladder anchoring on the joint instead,
    the as-received build reproduces the signed geometry and there is nothing
    left for a human to sign.

    ⛔⛔ AN EMPTY RESULT IS NOT SELF-PROVING, so this test does not stop there:
    the second half feeds the detector a document it MUST find something in, so
    "zero" cannot come from a detector that has quietly stopped working.
    """
    before = build_as_measured(ANCHOR / "sm25-L_t3_as_received.dxf",
                               ANCHOR / "request_as_measured.json")
    after = build_as_measured(ANCHOR / "sm25-L_t3.dxf", ANCHOR / "request.json")
    recomputed = detect_translate_candidates(before, after, CHANGED_HANDLES)
    assert recomputed == [], [r.id for r in recomputed]

    # ⭐ the same five handles, on a document whose face lines really do differ:
    # move one face line by hand and the detector must produce exactly one
    # well-formed candidate.  ⇒ the zero above is a MEASUREMENT, ⛔ not a
    # detector that no longer looks.
    raw = after.model_dump(mode="json")
    view = next(v for v in raw["views"] if v["view_id"] == "plan-F1")
    face = next(f for f in view["face_lines"] if f["id"] == "13AD")
    face["const"] += 30
    for wall in view["walls"]:
        for side in ("face_line_ids_lo", "face_line_ids_hi"):
            if "13AD" in wall[side]:
                wall["face_lo" if side.endswith("lo") else "face_hi"] += 30
                wall["thickness"] = abs(wall["face_hi"] - wall["face_lo"])
    moved = type(after).model_validate(raw)
    found = detect_translate_candidates(before, moved, CHANGED_HANDLES)
    assert [r.target.handle for r in found] == ["13AD"]
    assert found[0].candidate_action.field == "const"
    assert found[0].candidate_action.delta_0p1mm == 30
    assert found[0].verdict == "unsigned"

    _staged_am, staged_revisions, _staged_as_signed = read_facts_candidate(CASE)
    assert staged_revisions.revisions == []
    assert staged_revisions.as_measured_content_sha256 == content_sha256(before)


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


def test_3_signing_a_const_candidate_is_refused_by_the_wall_face_gate(tmp_path):
    """⚠️ A-11 finding, kept: a ``const``-direction translate CANNOT be signed
    as a single-field action -- ``derive_as_signed``'s wall/face-line
    consistency gate (F-137) refuses it loudly, because moving one face off its
    wall's ``face_hi`` would leave a ``walls`` block quietly disagreeing with
    the face lines it names.  A 3.0 mm wall move needs the compiler-layer
    re-pairing (②-1c), ⛔ not a silent single-field apply.

    ⚠️⚠️ G-c UPDATE (2026-09-07): this used to sign ``rev-13ad`` out of the
    committed ledger.  That record is gone -- the ladder made it unnecessary --
    so the record is BUILT here, aimed at the SAME real face line with the SAME
    ``const -30``.  ⛔ The refusal being pinned is unchanged; only where the
    record comes from moved, and it has to move because the alternative is
    dropping a lock on a gate nothing else covers.
    """
    as_measured, revisions, _as_signed = read_facts_candidate(CASE)
    assert revisions.revisions == [], "premise: the shipped ledger is empty"
    record = _synthetic_unsigned_record(as_measured)
    raw = revisions.model_dump(mode="json")
    entry = record.model_dump(mode="json")
    entry["verdict"] = "drawing_error"
    entry["action"] = entry["candidate_action"]
    entry["signed_by"] = "test"
    entry["signed_at"] = "2026-09-07T00:00:00Z"
    raw["revisions"] = [entry]
    signed_ledger = RevisionsLedgerV1.model_validate(raw)
    with pytest.raises(AsSignedReproductionError,
                       match="as_signed_wall_face_.._disagrees_with_its_face_lines"):
        derive_as_signed(as_measured, signed_ledger)


def test_3_hand_tampering_a_revisions_action_moves_as_signed_and_its_hash(tmp_path):
    """Signs a WELL-FORMED along-axis translate by hand (in memory only) to
    prove the mutation direction has real teeth on THIS document, not only on
    the synthetic 1-view fixture.  The along axis is chosen deliberately: it
    trims a face line's end without moving it off its wall's face, so it is the
    one kind of action the current deriver can apply without the consistency
    gate correctly refusing (see the sibling test above for the const-direction
    refusal).

    ⚠️ G-c UPDATE (2026-09-07): the record is built rather than read, for the
    reason given on that sibling -- the committed ledger is empty now.
    """
    as_measured, revisions, as_signed = read_facts_candidate(CASE)
    raw = revisions.model_dump(mode="json")
    entry = _synthetic_unsigned_record(
        as_measured, field="along_min", delta=-10).model_dump(mode="json")
    entry["verdict"] = "drawing_error"
    entry["action"] = {"kind": "translate", "field": "along_min",
                       "delta_0p1mm": -10}
    entry["signed_by"] = "test"
    entry["signed_at"] = "2026-09-07T00:00:00Z"
    raw["revisions"] = [entry]
    signed_ledger = RevisionsLedgerV1.model_validate(raw)

    before_hash = content_sha256(as_measured)  # unaffected reference point
    new_as_signed = derive_as_signed(as_measured, signed_ledger)
    assert new_as_signed.model_dump(mode="json") != as_signed.model_dump(mode="json")
    assert as_signed_content_sha256(new_as_signed) != as_signed_content_sha256(as_signed)
    verify_as_signed_reproduction(as_measured, signed_ledger, new_as_signed)
    # the OLD (empty-ledger) as_signed must NOT reproduce from the NEW ledger:
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
    if not raw["revisions"]:
        # ⚠️ G-c UPDATE (2026-09-07): the shipped ledger is empty, so the file
        # has no handle left to break.  ⛔ The mechanism under test -- pydantic
        # refusing the FILE before our own gate ever runs -- is unrelated to
        # why the ledger is empty, so the stock is built rather than the lock
        # dropped.  An UNSIGNED record changes no geometry, so the trio still
        # reproduces and the read path reaches the schema exactly as before.
        as_measured, _rev, _sig = read_facts_candidate(CASE)
        raw["revisions"] = [_synthetic_unsigned_record(as_measured)
                            .model_dump(mode="json")]
    entry = raw["revisions"][0]
    original_handle = entry["target"]["handle"]
    entry["target"]["handle"] = original_handle.lower()
    assert entry["target"]["handle"] != original_handle
    p.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValidationError):
        read_facts_candidate(CASE)
