"""②-1b R1/R2: the ``revisions`` ledger schema and the ``as_measured +
revisions => as_signed`` mechanical derivation + reproducibility gate.

Uses a small, hand-built synthetic ``AsMeasuredV1`` throughout (⛔ not the real
sm25 fixtures -- those are exercised end-to-end, against the real staged
artefacts, in ``tests/test_gt_facts_staging_sm25.py``).  A synthetic document
is deliberately used here because these are SCHEMA and DERIVATION tests: what
matters is that the shapes and the arithmetic are right, not that a real
drawing happens to exercise them.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agent.judge.as_measured import (AsMeasuredConverterReadoutsV1,
                                         AsMeasuredFaceLineV1,
                                         AsMeasuredFootprintV1, AsMeasuredV1,
                                         AsMeasuredViewV1, AsMeasuredWallV1,
                                         content_sha256)
from src.agent.judge.gt_revisions import (AsSignedReproductionError,
                                          AsSignedV1, RevisionFindingV1,
                                          RevisionsLedgerV1, RevisionTargetV1,
                                          RevisionV1, TranslateActionV1,
                                          as_signed_content_sha256,
                                          canonical_as_signed_bytes,
                                          derive_as_signed,
                                          detect_translate_candidates,
                                          verify_as_signed_reproduction)


def _face(handle: str, *, axis="y", const=1000, along_min=0, along_max=5000) -> AsMeasuredFaceLineV1:
    return AsMeasuredFaceLineV1(id=handle, layer="WALL", axis=axis, const=const,
                                along_min=along_min, along_max=along_max)


def _minimal_view(view_id="plan-F1") -> AsMeasuredViewV1:
    lo, hi = _face("1A1", const=1000), _face("1A2", const=1240)
    #: ⭐ ②-1b-R (F-137): a THIRD face line, deliberately NOT referenced by any
    #: wall.  The generic "does a translate move exactly the named field"
    #: tests below use THIS handle -- "1A1"/"1A2" are wall-referenced, and
    #: since F-137's own consistency gate now runs at the end of every
    #: ``derive_as_signed``, translating either of them by any amount beyond
    #: the ~0.5mm group-quantisation tolerance correctly desyncs their wall
    #: and raises.  Using an unreferenced handle for the generic mechanics
    #: tests keeps them testing what they say they test; the F-137-specific
    #: battery below deliberately targets "1A1"/"1A2" to exercise the gate.
    unreferenced = _face("1A3", const=2000)
    wall = AsMeasuredWallV1(id="w1", axis="y", face_lo=1000, face_hi=1240, thickness=240,
                            along_min=0, along_max=5000,
                            face_line_ids_lo=["1A1"], face_line_ids_hi=["1A2"])
    readouts = AsMeasuredConverterReadoutsV1(
        dangles=0, cuts=0, invalid=0, degenerate_line_count=0,
        wall_lines_total=3, degenerate_in_wall_lines=0,
        all_wall_handles=["1A1", "1A2", "1A3"],
        face_lines_excluded_as_jamb_caps=[], face_lines_not_paired_into_a_wall=["1A3"])
    footprint = AsMeasuredFootprintV1(geom_type="Polygon", is_empty=False, rings=[])
    return AsMeasuredViewV1(view_id=view_id, floor_id="F1", face_lines=[lo, hi, unreferenced],
                            walls=[wall], openings=[], footprint=footprint,
                            converter_readouts=readouts)


def _minimal_doc() -> AsMeasuredV1:
    return AsMeasuredV1(case="synthetic", source_dxf_label="x.dxf",
                        source_dxf_sha256="a" * 64, request_sha256="b" * 64,
                        converter_implementation_fingerprint="c" * 64,
                        views=[_minimal_view()])


def _signed_revision(handle="1A3", field="const", delta=10, rev_id="rev-1") -> RevisionV1:
    return RevisionV1(
        id=rev_id, target=RevisionTargetV1(view_id="plan-F1", handle=handle),
        finding=RevisionFindingV1(check="probe", detail="synthetic probe"),
        verdict="drawing_error",
        action=TranslateActionV1(field=field, delta_0p1mm=delta),
        reason="test", signed_by="tester", signed_at="2026-08-29T00:00:00Z")


# =========================================================================== #
# R1 -- schema shape + structural signing gate (verification #2, #4)
# =========================================================================== #
def test_r1_a_signed_drawing_error_revision_is_well_formed():
    rev = _signed_revision()
    assert rev.verdict == "drawing_error"
    assert rev.action is not None


def test_r1_unsigned_cannot_carry_an_authoritative_action():
    """⭐⭐ Verification #2's structural half: a JSON ``verdict: null``-shaped
    (here: the sentinel ``"unsigned"``) record that tries to smuggle an
    ``action`` is refused AT CONSTRUCTION -- it can never reach
    :func:`derive_as_signed` at all."""
    with pytest.raises(ValidationError):
        RevisionV1(id="rev-x", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                  finding=RevisionFindingV1(check="probe", detail="d"),
                  verdict="unsigned",
                  action=TranslateActionV1(field="const", delta_0p1mm=10))


def test_r1_verdict_null_is_rejected_by_the_type_itself():
    """The literal wording of verification #2 ("verdict=null"): passing JSON
    ``null`` (not the ``"unsigned"`` sentinel) must fail too."""
    with pytest.raises(ValidationError):
        RevisionV1.model_validate({
            "id": "rev-x", "target": {"kind": "dxf_entity", "view_id": "plan-F1", "handle": "1A1"},
            "finding": {"check": "probe", "detail": "d"},
            "verdict": None, "action": {"kind": "translate", "field": "const", "delta_0p1mm": 10},
        })


def test_r1_signed_verdict_requires_a_signature():
    with pytest.raises(ValidationError):
        RevisionV1(id="rev-x", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                  finding=RevisionFindingV1(check="probe", detail="d"),
                  verdict="drawing_error",
                  action=TranslateActionV1(field="const", delta_0p1mm=10))


def test_r1_drawing_error_requires_an_action():
    with pytest.raises(ValidationError):
        RevisionV1(id="rev-x", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                  finding=RevisionFindingV1(check="probe", detail="d"),
                  verdict="drawing_error", signed_by="t", signed_at="2026-08-29T00:00:00Z")


def test_r1_as_designed_and_producer_defect_never_carry_an_action():
    for verdict in ("as_designed", "producer_defect"):
        with pytest.raises(ValidationError):
            RevisionV1(id="rev-x", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                      finding=RevisionFindingV1(check="probe", detail="d"),
                      verdict=verdict, signed_by="t", signed_at="2026-08-29T00:00:00Z",
                      action=TranslateActionV1(field="const", delta_0p1mm=10))
        # ⭐ but signed WITHOUT an action -- "记账后照报" -- is valid.
        RevisionV1(id="rev-x", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                  finding=RevisionFindingV1(check="probe", detail="d"),
                  verdict=verdict, signed_by="t", signed_at="2026-08-29T00:00:00Z",
                  reason="confirmed as designed")


def test_r1_candidate_action_is_visible_while_unsigned():
    """⭐ Dispatch: "机器算出的 target + finding + 候选 action" -- an unsigned
    record MAY show a proposal, just never an authoritative one."""
    rev = RevisionV1(id="rev-x", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                     finding=RevisionFindingV1(check="probe", detail="d"),
                     verdict="unsigned",
                     candidate_action=TranslateActionV1(field="const", delta_0p1mm=10))
    assert rev.candidate_action is not None
    assert rev.action is None


def test_r1_unsupported_action_kind_is_rejected_and_named():
    """⭐ Verification #4: an action kind other than ``translate`` must be
    refused LOUDLY and by name -- ⛔ not swallowed by an ``else: pass``."""
    with pytest.raises(ValidationError) as excinfo:
        RevisionV1.model_validate({
            "id": "rev-x", "target": {"kind": "dxf_entity", "view_id": "plan-F1", "handle": "1A1"},
            "finding": {"check": "probe", "detail": "d"}, "verdict": "drawing_error",
            "signed_by": "t", "signed_at": "2026-08-29T00:00:00Z",
            "action": {"kind": "merge", "field": "const", "delta_0p1mm": 10},
        })
    assert "kind" in str(excinfo.value)


def test_r1_translate_delta_zero_is_rejected():
    """A zero-delta translate is not a correction -- catch it at the source
    rather than let it silently no-op through the derivation."""
    with pytest.raises(ValidationError):
        TranslateActionV1(field="const", delta_0p1mm=0)


def test_r1_ledger_ids_must_be_unique():
    doc = _minimal_doc()
    with pytest.raises(ValidationError):
        RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                         revisions=[_signed_revision(rev_id="dup"), _signed_revision(rev_id="dup")])


# =========================================================================== #
# R2 -- mechanical derivation
# =========================================================================== #
def test_r2_translate_moves_exactly_the_named_field():
    """⭐ Uses the wall-UNREFERENCED handle "1A3" -- this test is about the
    mechanics of ``_apply_translate``, not F-137's wall-consistency gate
    (covered separately, on purpose, by the ``test_f137_*`` battery above)."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="1A3", field="const", delta=10)])
    signed = derive_as_signed(doc, ledger)
    view = next(v for v in signed.views if v.view_id == "plan-F1")
    h3 = next(f for f in view.face_lines if f.id == "1A3")
    h2 = next(f for f in view.face_lines if f.id == "1A2")
    assert h3.const == 2010          # 2000 + 10
    assert h2.const == 1240          # untouched


def test_r2_as_designed_and_producer_defect_never_touch_geometry():
    doc = _minimal_doc()
    for verdict in ("as_designed", "producer_defect"):
        rev = RevisionV1(id=f"rev-{verdict}", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                         finding=RevisionFindingV1(check="probe", detail="d"),
                         verdict=verdict, signed_by="t", signed_at="2026-08-29T00:00:00Z")
        ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                                  revisions=[rev])
        signed = derive_as_signed(doc, ledger)
        view = next(v for v in signed.views if v.view_id == "plan-F1")
        assert [f.model_dump() for f in view.face_lines] == [
            f.model_dump() for f in doc.views[0].face_lines]


def test_r2_an_unsigned_record_cannot_influence_as_signed():
    """⭐⭐ Verification #2, end to end: even though the schema already refuses
    to let an unsigned record carry an ``action`` (tested above), prove the
    DERIVATION path too -- an all-unsigned ledger produces as_signed
    IDENTICAL (same content_sha256) to as_measured plus only the derivation
    key, regardless of what ``candidate_action`` / ``finding`` say."""
    doc = _minimal_doc()
    rev = RevisionV1(id="rev-1", target=RevisionTargetV1(view_id="plan-F1", handle="1A1"),
                     finding=RevisionFindingV1(check="probe", detail="d"), verdict="unsigned",
                     candidate_action=TranslateActionV1(field="const", delta_0p1mm=999))
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[rev])
    signed = derive_as_signed(doc, ledger)
    view = next(v for v in signed.views if v.view_id == "plan-F1")
    assert [f.model_dump() for f in view.face_lines] == [
        f.model_dump() for f in doc.views[0].face_lines]


def test_r2_ledger_bound_to_a_different_as_measured_is_refused():
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256="0" * 64,
                              revisions=[])
    with pytest.raises(AsSignedReproductionError):
        derive_as_signed(doc, ledger)


def test_r2_translate_target_not_found_is_refused_loudly():
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="FFF")])
    with pytest.raises(AsSignedReproductionError):
        derive_as_signed(doc, ledger)


def test_r2_a_translate_that_breaks_along_min_max_fails_loudly():
    """The re-validation in :func:`_apply_translate` is not decorative:
    a translate that pushes along_min past along_max must raise, not silently
    produce a broken face line."""
    doc = _minimal_doc()
    # 1A1 has along_min=0, along_max=5000; push along_min past along_max.
    rev = _signed_revision(handle="1A1", field="along_min", delta=6000)
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[rev])
    with pytest.raises(ValidationError):
        derive_as_signed(doc, ledger)


# =========================================================================== #
# Reproducibility gate -- verification #3, BOTH mutation directions
# =========================================================================== #
def test_gate_reproduces_on_an_unmutated_trio():
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision()])
    signed = derive_as_signed(doc, ledger)
    verify_as_signed_reproduction(doc, ledger, signed)  # must not raise


def test_gate_a_hand_tampered_integer_in_as_signed_is_caught():
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision()])
    signed = derive_as_signed(doc, ledger)
    raw = signed.model_dump(mode="json")
    raw["views"][0]["face_lines"][0]["const"] += 1
    tampered = AsSignedV1.model_validate(raw)
    with pytest.raises(AsSignedReproductionError):
        verify_as_signed_reproduction(doc, ledger, tampered)


def test_gate_editing_a_revisions_action_moves_as_signed_and_its_hash():
    """⭐ Verification #3's second half, literally: "手改 revisions 一条
    action ⇒ as_signed 跟着变且新旧哈希不同"."""
    doc = _minimal_doc()
    ledger_a = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                                revisions=[_signed_revision(delta=10)])
    ledger_b = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                                revisions=[_signed_revision(delta=20)])
    signed_a = derive_as_signed(doc, ledger_a)
    signed_b = derive_as_signed(doc, ledger_b)
    assert as_signed_content_sha256(signed_a) != as_signed_content_sha256(signed_b)
    verify_as_signed_reproduction(doc, ledger_a, signed_a)
    verify_as_signed_reproduction(doc, ledger_b, signed_b)
    # and the OLD as_signed no longer reproduces from the NEW ledger:
    with pytest.raises(AsSignedReproductionError):
        verify_as_signed_reproduction(doc, ledger_b, signed_a)


def test_gate_canonical_bytes_is_a_pure_function_of_the_document():
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision()])
    signed = derive_as_signed(doc, ledger)
    assert canonical_as_signed_bytes(signed) == canonical_as_signed_bytes(
        AsSignedV1.model_validate(signed.model_dump(mode="json")))


# =========================================================================== #
# F-137 (②-1b-R B-1, ⛔ BLOCKING) -- a wall must still match its named face
# lines after a translate.  ``_minimal_doc``'s wall is deliberately TIED
# (both "1A1" and "1A2" share along=[0,5000]), so translating EITHER handle
# by ANY nonzero amount on ANY field immediately makes it the binding side --
# no accidental "this delta happened not to be the binding constraint" noise
# (a real pitfall MEASURED against actual sm25 data while building this
# battery: a small along_min delta on a non-binding handle produces no
# observable change and must NOT be mistaken for a gate that lacks teeth).
# =========================================================================== #
def test_f137_a_const_translate_desyncs_face_lo_is_caught():
    """The original defect shape: translate the LO-side handle's ``const``;
    the wall's self-reported ``face_lo`` goes stale."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="1A1", field="const", delta=500)])
    with pytest.raises(AsSignedReproductionError, match="as_signed_wall_face_lo_disagrees"):
        derive_as_signed(doc, ledger)


def test_f137_b_same_shape_different_face_line_is_also_caught():
    """⭐ Verification #2: a DIFFERENT face line (the HI side instead of LO)
    must ALSO be caught -- ①只证明「这个例子修好了」，②才证明「这类缺陷修好了」."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="1A2", field="const", delta=500)])
    with pytest.raises(AsSignedReproductionError, match="as_signed_wall_face_hi_disagrees"):
        derive_as_signed(doc, ledger)


def test_f137_c_same_shape_different_field_along_min_is_caught():
    """⭐ Verification #2: field=along_min must ALSO be caught."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="1A1", field="along_min", delta=500)])
    with pytest.raises(AsSignedReproductionError, match="as_signed_wall_along_extent_disagrees"):
        derive_as_signed(doc, ledger)


def test_f137_d_same_shape_different_field_along_max_is_caught():
    """⭐ Verification #2: field=along_max must ALSO be caught."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="1A2", field="along_max", delta=-500)])
    with pytest.raises(AsSignedReproductionError, match="as_signed_wall_along_extent_disagrees"):
        derive_as_signed(doc, ledger)


def test_f137_e_same_shape_negative_delta_is_also_caught():
    """⭐ Verification #2: the SIGN of the delta must not matter."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[_signed_revision(handle="1A1", field="const", delta=-500)])
    with pytest.raises(AsSignedReproductionError, match="as_signed_wall_face_lo_disagrees"):
        derive_as_signed(doc, ledger)


def test_f137_f_zero_revisions_does_not_misfire():
    """⭐ Verification #3 (⛔ not misfiring is as real a requirement as
    catching the defect): an untouched document must reproduce cleanly --
    the gate compares against the SAME (group-quantised) coordinate the wall
    was originally built from, not a stricter one nothing could ever satisfy."""
    doc = _minimal_doc()
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[])
    derive_as_signed(doc, ledger)   # must not raise


def test_f137_g_split_const_group_is_not_a_false_positive():
    """⭐⭐ Regression for the false positive this gate ACTUALLY produced while
    being built: a wall's ``face_lo``/``face_hi`` is the 1 mm GROUP coordinate
    (``AsMeasuredWallV1``'s own docstring), which can legitimately differ from
    an untouched member face line's own exact ``const`` by up to ~0.5 mm --
    MEASURED on real sm25-L_anchor data (handle ``140E``, const=159396, its
    wall's face_lo=159400, zero revisions applied) BEFORE this test existed,
    when the gate compared raw ``const`` instead of the group-rounded value.
    Reproduced here with a synthetic 0.4 mm split so it runs fast and never
    depends on the real DXF fixture staying exactly as it is today.
    """
    view = _minimal_view()
    faces = list(view.face_lines)
    faces[0] = AsMeasuredFaceLineV1.model_validate(
        {**faces[0].model_dump(mode="json"), "const": 996})   # 0.4mm off face_lo=1000
    view = AsMeasuredViewV1.model_validate(
        {**view.model_dump(mode="json"),
         "face_lines": [f.model_dump(mode="json") for f in faces]})
    doc = AsMeasuredV1.model_validate({
        **_minimal_doc().model_dump(mode="json"),
        "views": [view.model_dump(mode="json")]})
    ledger = RevisionsLedgerV1(case="synthetic", as_measured_content_sha256=content_sha256(doc),
                              revisions=[])
    derive_as_signed(doc, ledger)   # must NOT raise -- 0.4mm is within the 1mm group tolerance


# =========================================================================== #
# detect_translate_candidates -- R1's "机器算出" detector
# =========================================================================== #
def test_detect_a_single_field_translate():
    before = _minimal_doc()
    after_view = _minimal_view()
    after_view = AsMeasuredViewV1.model_validate({
        **after_view.model_dump(mode="json"),
        "face_lines": [
            {**after_view.face_lines[0].model_dump(mode="json"), "const": 1010},
            after_view.face_lines[1].model_dump(mode="json"),
            after_view.face_lines[2].model_dump(mode="json"),
        ]})
    after = AsMeasuredV1.model_validate({**before.model_dump(mode="json"),
                                        "views": [after_view.model_dump(mode="json")]})
    candidates = detect_translate_candidates(before, after, ["1A1"])
    assert len(candidates) == 1
    assert candidates[0].verdict == "unsigned"
    assert candidates[0].candidate_action == TranslateActionV1(field="const", delta_0p1mm=10)


def test_detect_a_handle_absent_on_one_side_gets_no_candidate_action():
    before = _minimal_doc()
    candidates = detect_translate_candidates(before, before, ["DOES-NOT-EXIST-ANYWHERE"])
    assert candidates == []          # absent on BOTH sides -> nothing to report


def test_detect_multi_field_change_is_flagged_not_guessed():
    before = _minimal_doc()
    after_view = _minimal_view()
    after_view = AsMeasuredViewV1.model_validate({
        **after_view.model_dump(mode="json"),
        "face_lines": [
            {**after_view.face_lines[0].model_dump(mode="json"), "const": 1010, "along_min": 100},
            after_view.face_lines[1].model_dump(mode="json"),
            after_view.face_lines[2].model_dump(mode="json"),
        ]})
    after = AsMeasuredV1.model_validate({**before.model_dump(mode="json"),
                                        "views": [after_view.model_dump(mode="json")]})
    candidates = detect_translate_candidates(before, after, ["1A1"])
    assert len(candidates) == 1
    assert candidates[0].candidate_action is None
    assert candidates[0].finding.check == "face_line_multiple_fields_changed"


def test_detect_axis_swap_with_numeric_coincidence_is_not_reported_as_translate():
    """⭐⭐ F-139 (②-1b-R, GLM ⭐ new-break finding N-6): reproduces the exact
    probe GLM used -- before is a y-running line, after is the SAME handle
    now x-running, with a ``const`` that happens to differ by a plausible
    "translate" amount.  Before the fix this was reported as a well-formed
    translate candidate with no mention of axis at all; it must now be
    refused, named, like the 3 real "needs a straighten" sm25 candidates.
    """
    before = _minimal_doc()
    after_view = _minimal_view()
    swapped = AsMeasuredFaceLineV1.model_validate({
        **after_view.face_lines[0].model_dump(mode="json"),
        "axis": "x", "const": 990})   # was axis="y", const=1000 -- numeric coincidence, wrong axis
    after_view = AsMeasuredViewV1.model_validate({
        **after_view.model_dump(mode="json"),
        "face_lines": [swapped.model_dump(mode="json"),
                      after_view.face_lines[1].model_dump(mode="json"),
                      after_view.face_lines[2].model_dump(mode="json")]})
    after = AsMeasuredV1.model_validate({**before.model_dump(mode="json"),
                                        "views": [after_view.model_dump(mode="json")]})
    candidates = detect_translate_candidates(before, after, ["1A1"])
    assert len(candidates) == 1
    assert candidates[0].candidate_action is None, (
        "an axis-swapped numeric coincidence must NOT be reported as a translate")
    assert candidates[0].finding.check == "face_line_axis_changed"
    assert "axis" in candidates[0].finding.detail.lower()
    assert candidates[0].verdict == "unsigned"
