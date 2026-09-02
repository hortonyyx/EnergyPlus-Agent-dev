"""②-2 modules 5+6: decision packet / response / three-beat executor
(2026-09-01).

Dispatch: ``AI_agent/logs/reviews/request/
2026-09-01_o22m56_decision_packet_and_executor.md``; authority: the
approved evidence-contract design §6.1–§6.3 + §9.1 step 5 ("model output
schema carries no coordinates; first exercise the three-beat executor
with FIXED responses, then wire the model").  No model is called
anywhere in this file -- every response is a fixed fixture, per §9.1
step 5 and dispatch task 3.

Acceptance coverage (dispatch §四)
----------------------------------
1  coordinates are STRUCTURALLY absent from the response side: extra
   fields are rejected by the type layer (``extra="forbid"``, the error
   is a schema error, not a name scan), and a full recursive walk of
   the response type tree finds no numeric leaf at all;
2  a stale packet hash is one of the four loud exits, residual intact;
3  a well-formed candidate id that is not in the packet's candidate set
   is refused loudly (UNKNOWN_RESPONSE_CANDIDATE), as are unknown and
   duplicate item ids;
4  each of the four loud exits has its own fixture, each leaves a
   non-empty residual manifest and never hands the final provisional
   out as a success product;
5  the four-part success conjunction is falsified one term at a time
   (open item kept / a failing check / a findings verdict / an
   ambiguous debt surviving under exploratory);
6  all five ``requested_effect`` kinds round-trip, each rejects
   unlisted fields, a sixth kind is rejected by the discriminator, and
   finding citations must resolve inside the packet;
8  zero wiring locks in module 4's STRENGTHENED shape (difference of
   reachable pipeline∪judge sets against module 2's contract, plus an
   AST allowlist over the new modules' whole import face), each proven
   able to go red on the spot;
9  the same bundle and the same fixed responses replay byte-identically
   (both the packet build and the whole loop outcome).
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from src.agent.correction import decision_executor as dx
from src.agent.correction import wall_compiler as wc
from src.agent.correction.decision_schema import (
    CorrectionDecisionPacketV1,
    CorrectionDecisionResponseV1,
    FindingV1,
    ItemDecisionV1,
    RequestWallReperceptionEffectV1,
    ReviewAlignmentEffectV1,
    ReviewOpeningHostEffectV1,
    ReviewSegmentationEffectV1,
    ReviewTopologyRelationEffectV1,
    WholeBuildingReviewV1,
)
from src.agent.correction.evidence_adapters import adapt_as_drawn_plan
from src.agent.reading.as_drawn.schema import SCHEMA


# ── as-drawn fixtures (same shape as module 4's test helpers) ──────────────── #
def _face(fid: str, axis: str, world_axis: str, col: int,
          runs_px: list) -> dict:
    runs_m = [[lo / 10.0, hi / 10.0] for lo, hi in runs_px]
    return {
        "id": fid, "axis": axis, "constant_world_axis": world_axis,
        "pos_px": float(col), "pos_m": 0.01 * col,
        "support_cols_px": [col, col + 1], "edges_m": [0.0, 0.02],
        "support_width_m": 0.02, "runs_px": runs_px, "runs_m": runs_m,
        "gaps": [], "ink_coverage_per_run": [1.0] * len(runs_px),
        "covered_px": sum(hi - lo for lo, hi in runs_px),
        "support_px": sum(hi - lo for lo, hi in runs_px) + 1,
    }


def _pair(face_a: str, face_b: str, spacing_px: float) -> dict:
    return {
        "face_a": face_a, "face_b": face_b,
        "spacing_px": spacing_px, "spacing_m": spacing_px / 100.0,
        "matched_declared_mm": [int(spacing_px)],
        "overlap_px": 80, "source": "selected",
    }


def _doc(face_lines: list[dict], pairs: list[dict],
         ambiguous: dict | None = None,
         non_wall: dict | None = None) -> dict:
    doc = {
        "schema": SCHEMA,
        "observations": {"face_lines": face_lines},
        "declarations": {},
        "hypotheses": {
            "pairs": pairs,
            "pair_candidates": [
                {k: v for k, v in p.items() if k != "source"}
                for p in pairs
            ],
            "opening_candidates": [], "opening_types": None,
            "pairs_status": "SELECTED",
            "non_wall_face_lines": non_wall or {},
            "unpaired_wall_faces": {},
            "solid_band_walls": {},
            "ambiguous_face_lines": ambiguous or {},
        },
    }
    return doc


def _adapt(doc: dict, input_id: str) -> object:
    raw = json.dumps(doc, indent=1).encode("utf-8")
    return adapt_as_drawn_plan(raw, input_id=input_id, floor_ref="1f")


def _one_pair_artifact():
    """One paired wall ⇒ one thickness_resolution open item."""
    doc = _doc(
        [_face("F01", "col", "x", 100, [[10, 100]]),
         _face("F02", "col", "x", 112, [[10, 100]])],
        [_pair("F01", "F02", 12.0)],
    )
    return _adapt(doc, "one_pair")


def _two_pair_artifact():
    """Two perpendicular paired walls ⇒ two open items, the fixture the
    four-exit and conjunct tests slice different decisions from."""
    doc = _doc(
        [_face("F01", "col", "x", 100, [[10, 100]]),
         _face("F02", "col", "x", 112, [[10, 100]]),
         _face("F11", "row", "y", 200, [[10, 90]]),
         _face("F12", "row", "y", 212, [[10, 90]])],
        [_pair("F01", "F02", 12.0), _pair("F11", "F12", 12.0)],
    )
    return _adapt(doc, "two_pairs")


def _overlap_artifact():
    """Two pairs on the SAME support line (same columns) whose runs
    overlap along the wall -- the collinear_wall_overlap check's tooth."""
    doc = _doc(
        [_face("F01", "col", "x", 100, [[10, 100]]),
         _face("F02", "col", "x", 112, [[10, 100]]),
         _face("F03", "col", "x", 100, [[50, 150]]),
         _face("F04", "col", "x", 112, [[50, 150]])],
        [_pair("F01", "F02", 12.0), _pair("F03", "F04", 12.0)],
    )
    return _adapt(doc, "overlap_pairs")


def _ambiguous_artifact():
    """One paired wall plus an ambiguous face (honest abstention) -- the
    exploratory debt that blocks success conjunct 4."""
    doc = _doc(
        [_face("F01", "col", "x", 100, [[10, 100]]),
         _face("F02", "col", "x", 112, [[10, 100]]),
         _face("F09", "row", "y", 300, [[4, 8]])],
        [_pair("F01", "F02", 12.0)],
        ambiguous={"F09": "could be a wall or furniture"},
    )
    return _adapt(doc, "ambiguous_pair")


def _pairs_absent_artifact():
    """Rework B-3's own shape: perception supplied no pairing
    (``pairs=None`` + ``pairs_status=ABSENT_NO_MODEL_SELECTION``), both
    faces honestly declared ``non_wall`` so the accounting closes -- the
    bundle carries ``pairs_selection_absent`` (and, there being no wall
    claim at all, ``missing_channel(walls)`` too)."""
    doc = _doc(
        [_face("F01", "col", "x", 100, [[10, 100]]),
         _face("F02", "col", "x", 112, [[10, 100]])],
        [],
        non_wall={"F01": "text", "F02": "text"},
    )
    doc["hypotheses"]["pairs"] = None
    doc["hypotheses"]["pairs_status"] = "ABSENT_NO_MODEL_SELECTION"
    return _adapt(doc, "pairs_absent")


def _walls_missing_artifact():
    """No face lines at all: zero wall claims ⇒ the subject channel is
    ``absent`` with an explicit ``missing_channel(walls)`` debt."""
    return _adapt(_doc([], []), "walls_missing")


def _opening_artifact():
    """One paired wall PLUS one real opening candidate: the bundle's
    ``opening_claims`` carry ``op01`` -- what the packet's entity table
    must index as an ``opening``-kind entity (rework B-4)."""
    gap = {
        "lo_px": 20, "hi_px": 30, "len_px": 10, "len_m": 1.0,
        "ink_by_family": {}, "span_m": [0.5, 2.5],
    }
    f1 = _face("F01", "col", "x", 100, [[10, 100]])
    f1["gaps"] = [dict(gap)]
    f2 = _face("F02", "col", "x", 112, [[10, 100]])
    f2["gaps"] = [dict(gap)]
    doc = _doc([f1, f2], [_pair("F01", "F02", 12.0)])
    doc["hypotheses"]["opening_candidates"] = [
        {
            "id": "op01", "face_line": "F01", "gap_index": 0,
            "span_m": [0.5, 2.5], "len_m": 2.0, "len_px": 20,
            "ink_by_family": {},
        }
    ]
    return _adapt(doc, "opening_pair")


def _packet_round0(artifact, profile="strict"):
    compilation = wc.compile_wall_ir(artifact, profile=profile)
    packet = dx.build_decision_packet(
        compilation, bundle=artifact, round_index=0
    )
    return compilation, packet


def _select(item_id: str, packet, reason="OBSERVED_MATCHES_DECLARATION"):
    item = next(i for i in packet.open_items if i.item_id == item_id)
    candidate = item.candidates[0].candidate_id
    return CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(ItemDecisionV1(
            item_id=item_id, action="select_candidate",
            candidate_id=candidate, reason_code=reason,
        ),),
        whole_building_review={"verdict": "accept"},
    )


def _reject(item_id: str, packet, reason="NO_TRUSTED_EVIDENCE"):
    return CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(ItemDecisionV1(
            item_id=item_id, action="reject_all", reason_code=reason,
        ),),
        whole_building_review={"verdict": "accept"},
    )


def _round1_packet(artifact, first_response, profile="strict"):
    """The packet round 1 will actually see: round 0's decisions applied
    (or not), round_index=1, one previous decision hash.  Fixed-response
    fixtures must bind the CURRENT round's hash, so this precomputes it
    exactly the way the loop does."""
    applied = tuple(
        wc.FixedDecisionV1(item_id=d.item_id, candidate_id=d.candidate_id)
        for d in first_response.item_decisions
        if d.action == "select_candidate"
    )
    compilation = wc.compile_wall_ir(
        artifact, profile=profile, decisions=applied
    )
    return dx.build_decision_packet(
        compilation,
        bundle=artifact,
        round_index=1,
        previous_decision_hashes=(dx.decision_hash(first_response),),
    )


def _expect_error(thunk, code: str, cls=dx.DecisionLoopError):
    with pytest.raises(cls) as exc:
        thunk()
    assert exc.value.code == code, (
        f"expected {code}, got {exc.value.code}: {getattr(exc.value, 'context', '')}"
    )
    return exc.value


# =========================================================================== #
# Acceptance 1 -- coordinates are structurally absent from the response
# =========================================================================== #
def test_model_decision_schema_rejects_coordinate_fields():
    """Design §9.2's own row, on the response side.  Each coordinate-ish
    field is injected at every nesting level and must be refused BY THE
    SCHEMA (``extra_forbid``), before any executor code sees it -- the
    refusal is not a name scan anywhere."""
    base = {
        "packet_hash": "a" * 64,
        "whole_building_review": {"verdict": "accept"},
    }
    for field in ("x", "y", "z", "p1", "p2", "span", "thickness_m"):
        for where, mutate in (
            ("top", lambda d: d.update({field: 1.0})),
            ("item", lambda d: d.update(item_decisions=[{
                "item_id": "i", "action": "reject_all",
                "reason_code": "R", field: 1.0}])),
            ("review", lambda d: d["whole_building_review"].update(
                {field: 1.0})),
        ):
            payload = json.loads(json.dumps(base))
            mutate(payload)
            # the JSON door (the one a model actually uses): parses the
            # arrays AND still refuses the unlisted field
            with pytest.raises(ValidationError) as exc:
                CorrectionDecisionResponseV1.model_validate_json(
                    json.dumps(payload)
                )
            kinds = {e["type"] for e in exc.value.errors()}
            assert "extra_forbidden" in kinds, (field, where, kinds)


def test_response_type_tree_has_no_numeric_field():
    """The structural half of acceptance 1: walk EVERY field of the
    response type tree (through unions, tuples, optionals, annotations
    and nested models) and fail on any numeric leaf.  This is what makes
    "no coordinates" a property of the TYPE, not of field naming -- a
    numeric field cannot be constructed whatever it is called."""
    bad = []

    def visit(annotation, path: str) -> None:
        origin = typing.get_origin(annotation)
        if origin is typing.Literal or annotation is type(None):
            return
        if origin is None:
            if isinstance(annotation, type):
                if annotation in (int, float) and annotation is not bool:
                    bad.append(path)
                elif issubclass(annotation, BaseModel):
                    for name, field_info in annotation.model_fields.items():
                        visit(field_info.annotation, f"{path}.{name}")
            return
        for arg in typing.get_args(annotation):
            visit(arg, path)

    for name, field_info in CorrectionDecisionResponseV1.model_fields.items():
        visit(field_info.annotation, name)
    assert not bad, f"numeric fields reachable from the response: {bad}"


def test_packet_side_may_carry_numbers_but_response_may_not():
    """The asymmetry is deliberate and worth pinning: the packet (code →
    model) carries the provisional's own numbers -- module 4's previews
    and coordinates -- while the response (model → code) carries none.
    A day where these agree is a day the model started authoring
    geometry."""
    packet_fields = {
        name for name in CorrectionDecisionPacketV1.model_fields
    }
    response_fields = {
        name for name in CorrectionDecisionResponseV1.model_fields
    }
    assert packet_fields & response_fields == {"packet_hash"}


# =========================================================================== #
# Acceptances 2+3 -- stale packet / unknown candidate / unknown item
# =========================================================================== #
def test_stale_packet_hash_is_rejected_loudly():
    """Acceptance 2: reply with the PREVIOUS round's packet hash ⇒ the
    stale_packet exit, with the residual manifest and no success
    product."""
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet0.open_items)
    first = _select(items[0], packet0)
    second = _select(items[1], packet0)  # binds ROUND 0's hash: stale
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(first, second)
    )
    assert outcome.exit_reason == "stale_packet"
    assert outcome.success is False
    assert outcome.residual_open_item_ids  # residual manifest kept
    assert outcome.final_completion == "degraded"
    assert len(outcome.rounds) == 1  # round 1 never executed


def test_unknown_candidate_is_rejected_loudly():
    """Acceptance 3: a WELL-FORMED candidate id (right shape, right
    prefix family) that is simply not in the item's candidate set."""
    artifact = _one_pair_artifact()
    _, packet = _packet_round0(artifact)
    item = packet.open_items[0]
    forged = CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(ItemDecisionV1(
            item_id=item.item_id, action="select_candidate",
            candidate_id="cand_" + "b" * 40,  # legal shape, wrong world
            reason_code="LOOKS_PLAUSIBLE",
        ),),
        whole_building_review={"verdict": "accept"},
    )
    error = _expect_error(
        lambda: dx.run_decision_loop(
            artifact, profile="strict", responses=(forged,)
        ),
        "UNKNOWN_RESPONSE_CANDIDATE",
    )
    assert error.context["available"] == [
        c.candidate_id for c in item.candidates
    ]


def test_unknown_and_duplicate_items_are_rejected_loudly():
    artifact = _one_pair_artifact()
    _, packet = _packet_round0(artifact)
    item = packet.open_items[0]
    ghost = CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(ItemDecisionV1(
            item_id="item_" + "9" * 40, action="reject_all",
            reason_code="GHOST_ITEM",
        ),),
        whole_building_review={"verdict": "accept"},
    )
    _expect_error(
        lambda: dx.run_decision_loop(artifact, responses=(ghost,)),
        "UNKNOWN_RESPONSE_ITEM",
    )
    twice = CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=(
            ItemDecisionV1(item_id=item.item_id, action="reject_all",
                           reason_code="FIRST"),
            ItemDecisionV1(item_id=item.item_id, action="reject_all",
                           reason_code="SECOND"),
        ),
        whole_building_review={"verdict": "accept"},
    )
    _expect_error(
        lambda: dx.run_decision_loop(artifact, responses=(twice,)),
        "DUPLICATE_RESPONSE_ITEM",
    )


def test_candidate_id_rides_only_on_select_candidate():
    """The schema-level half: select without a candidate and reject with
    one are both malformed responses."""
    with pytest.raises(ValidationError):
        ItemDecisionV1(item_id="i", action="select_candidate",
                       reason_code="R")
    with pytest.raises(ValidationError):
        ItemDecisionV1(item_id="i", action="reject_all",
                       candidate_id="cand_x", reason_code="R")


# =========================================================================== #
# Acceptance 4 -- the four loud exits, one fixture each
# =========================================================================== #
def test_exit_no_progress_after_a_streak_of_empty_rounds():
    """No progress = enough consecutive rounds executing NOTHING (each
    round a fresh reject -- not a repeat, which would be the cycle exit).
    The residual stays and the final provisional is not a product."""
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet0.open_items)
    first = _reject(items[1], packet0, reason="FIRST")
    packet1 = _round1_packet(artifact, first)
    second = _reject(items[0], packet1, reason="SECOND")  # fresh decision
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(first, second)
    )
    assert outcome.exit_reason == "no_progress"
    assert outcome.success is False
    assert len(outcome.residual_open_item_ids) == 2  # nothing was closed
    assert outcome.final_completion == "degraded"
    assert len(outcome.rounds) == 2


def test_exit_decision_hash_cycle_on_repeated_decision_set():
    """The model repeating itself verbatim: the same decision set in a
    later round is caught at that round's head, before execution."""
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet0.open_items)
    first = _reject(items[1], packet0, reason="STUCK")
    packet1 = _round1_packet(artifact, first)
    second = _reject(items[1], packet1, reason="STUCK")  # verbatim repeat
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(first, second)
    )
    assert outcome.exit_reason == "decision_hash_cycle"
    assert outcome.success is False
    assert len(outcome.residual_open_item_ids) == 2
    assert len(outcome.rounds) == 1  # the repeating round never ran


def test_exit_round_budget_exhausted_with_work_left():
    """Decisions ran, work remains, budget is gone: loud exit with the
    remaining item named in the residual manifest."""
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet0.open_items)
    outcome = dx.run_decision_loop(
        artifact, profile="strict",
        responses=(_select(items[0], packet0),),
        round_budget=1,
    )
    assert outcome.exit_reason == "round_budget_exhausted"
    assert outcome.success is False
    assert outcome.residual_open_item_ids == (items[1],)
    assert outcome.rounds[0].selected_item_ids == (items[0],)
    assert outcome.final_completion == "degraded"


def test_exit_stale_packet_keeps_residual_manifest():
    """(Paired with the acceptance-2 test, asserting the §6.3 clause
    verbatim: the LAST provisional geometry is not a success product --
    it travels degraded, for audit only.)"""
    artifact = _two_pair_artifact()
    compilation0, packet0 = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet0.open_items)
    first = _select(items[0], packet0)
    second = _select(items[1], packet0)  # binds round 0's hash again
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(first, second)
    )
    assert outcome.exit_reason == "stale_packet"
    assert outcome.success is False
    # the final provisional still names what it never decided
    assert outcome.final_provisional_sha256 is not None
    assert outcome.residual_open_item_ids == (items[1],)


# =========================================================================== #
# Acceptance 5 -- the success conjunction falsified one term at a time
# =========================================================================== #
def test_success_conjunct_open_item_falsified():
    """Term 1: an open item remains (model rejected it) while everything
    else would allow success -- must NOT succeed, and the item stays in
    the residual manifest.  (One empty round is a legal rhythm, so the
    loop ends by budget here -- the point is success is refused.)"""
    artifact = _one_pair_artifact()
    _, packet = _packet_round0(artifact)
    item = packet.open_items[0].item_id
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(_reject(item, packet),)
    )
    assert outcome.success is False
    assert outcome.residual_open_item_ids == (item,)
    assert outcome.final_completion == "degraded"


def test_success_conjunct_checks_falsified():
    """Term 2: every decision made, model accepts, but the deterministic
    overlap check fails on the rebuilt provisional -- must NOT succeed."""
    artifact = _overlap_artifact()
    _, packet = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet.open_items)
    accept_all = CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=tuple(
            _select(i, packet).item_decisions[0] for i in items
        ),
        whole_building_review={"verdict": "accept"},
    )
    outcome = dx.run_decision_loop(artifact, responses=(accept_all,))
    assert outcome.exit_reason == "round_budget_exhausted"
    assert outcome.success is False
    assert outcome.rounds[0].failed_checks == ("collinear_wall_overlap",)


def test_success_conjunct_accept_falsified():
    """Term 3: everything decided, checks pass, but the model's overall
    verdict is `findings`, not `accept` -- must NOT succeed, and the
    finding must be carried (step ⑤'s receiving half)."""
    artifact = _one_pair_artifact()
    _, packet = _packet_round0(artifact)
    item = packet.open_items[0]
    decided = _select(item.item_id, packet)
    findings = CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        item_decisions=decided.item_decisions,
        whole_building_review=WholeBuildingReviewV1(
            verdict="findings",
            findings=(FindingV1(
                finding_id="FIND_ONE",
                kind="WHOLE_BUILDING_SHAPE",
                affected_entity_ids=(item.scope_entity_ids[0],),
                requested_effect=ReviewAlignmentEffectV1(
                    kind="review_alignment",
                    subject_entity_ids=(item.scope_entity_ids[0],),
                    reference_entity_ids=(item.scope_entity_ids[0],),
                    relation="collinear",
                ),
                rationale="WALL_MISALIGNED_WITH_NEIGHBOUR",
            ),),
        ),
    )
    outcome = dx.run_decision_loop(artifact, responses=(findings,))
    assert outcome.success is False
    assert [f.finding_id for f in outcome.pending_findings] == ["FIND_ONE"]


def test_success_conjunct_debt_falsified_under_exploratory():
    """Term 4: an ambiguous face survived on the record (exploratory
    continues past it) -- even with every item decided, checks green and
    an overall accept, this must NOT be declared a success (§9.4: the
    exploratory end state is degraded, not successful)."""
    artifact = _ambiguous_artifact()
    _, packet = _packet_round0(artifact, profile="exploratory")
    item = packet.open_items[0]
    outcome = dx.run_decision_loop(
        artifact, profile="exploratory",
        responses=(_select(item.item_id, packet),),
    )
    assert outcome.success is False
    ambiguous = [
        debt for debt in artifact.bundle.evidence_debts
        if debt.kind == "ambiguous_face"
    ]
    assert ambiguous  # premise: the debt this conjunct is about exists
    assert outcome.final_completion == "degraded"


def test_select_round_cannot_succeed_on_its_own_accept():
    """Rework B-1, the OVERTURNED lock.  This test USED to assert
    "one round select+accept ⇒ success" -- locking in exactly the wrong
    §6.3 semantics the cross-review caught: the accept was given to the
    PRE-execution provisional (the packet's hash), then the decisions
    moved the geometry, and the moved geometry was released as a success
    product on the strength of that stale accept.  §6.3 term 3 requires
    the accept to bind the SAME provisional hash it releases: a round
    that changed the geometry cannot succeed on its own accept."""
    artifact = _one_pair_artifact()
    _, packet = _packet_round0(artifact)
    outcome = dx.run_decision_loop(
        artifact, profile="strict",
        responses=(_select(packet.open_items[0].item_id, packet),),
    )
    assert outcome.exit_reason == "round_budget_exhausted"
    assert outcome.success is False
    # the decisions DID land (no item left open) -- what is refused is
    # calling this round's accept a release of the NEW geometry
    assert outcome.residual_open_item_ids == ()
    assert (
        packet.provisional_geometry
        != outcome.final_provisional_sha256
    )


def test_success_requires_next_round_accept_of_new_hash():
    """The positive control B-1 asks for: select round (geometry moves,
    not a success), THEN a fresh packet is built on the new provisional
    and a pure accept against THAT packet's hash succeeds.  The success
    round's provisional is the one the accept actually bound."""
    artifact = _one_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    select = _select(packet0.open_items[0].item_id, packet0)
    packet1 = _round1_packet(artifact, select)
    accept = CorrectionDecisionResponseV1(
        packet_hash=packet1.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(select, accept),
    )
    assert outcome.exit_reason == "success"
    assert outcome.success is True
    assert outcome.residual_open_item_ids == ()
    # §6.3 term 3, mechanically: the accepting round's packet carried
    # exactly the provisional that was released
    assert packet1.provisional_geometry == outcome.final_provisional_sha256
    assert outcome.rounds[-1].selected_item_ids == ()
    # the honest-bundle note from the old control still holds: support-
    # channel missing_channel debts travel on the SUCCESS record without
    # blocking it (policy rows: missing_channel on support channels)
    assert any(
        kind == "missing_channel" and channel != "walls"
        for kind, channel in (
            (d.kind, d.channel) for d in artifact.bundle.evidence_debts
        )
    )


# =========================================================================== #
# Rework B-2 -- decisions accumulate monotonically across rounds
# =========================================================================== #
def _two_round_responses(artifact):
    """Two items, one selected per round, then a pure accept of the new
    provisional -- the canonical multi-round convergence path."""
    _, packet0 = _packet_round0(artifact)
    ids = sorted(i.item_id for i in packet0.open_items)
    first = _select(ids[0], packet0)
    packet1 = _round1_packet(artifact, first)
    second = _select(ids[1], packet1)
    packet2 = dx.build_decision_packet(
        wc.compile_wall_ir(artifact, decisions=(
            wc.FixedDecisionV1(
                item_id=first.item_decisions[0].item_id,
                candidate_id=first.item_decisions[0].candidate_id,
            ),
            wc.FixedDecisionV1(
                item_id=second.item_decisions[0].item_id,
                candidate_id=second.item_decisions[0].candidate_id,
            ),
        )),
        bundle=artifact,
        round_index=2,
        previous_decision_hashes=(
            dx.decision_hash(first), dx.decision_hash(second),
        ),
    )
    accept = CorrectionDecisionResponseV1(
        packet_hash=packet2.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    return (first, second, accept), ids


def test_two_items_decided_across_two_rounds_both_survive():
    """B-2's own fixture: round 0 closes item A, round 1 closes item B --
    BOTH closures must survive into the success state.  Before the
    rework the second round's compile dropped the first round's decision
    (residual re-opened the item round 0 had closed) and this exact
    sequence died in ``round_budget_exhausted``."""
    artifact = _two_pair_artifact()
    responses, ids = _two_round_responses(artifact)
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=responses,
    )
    assert outcome.exit_reason == "success"
    assert outcome.success is True
    # BOTH items closed and STAYING closed is the point: the residual is
    # empty, and each round's record shows its own item selected
    assert outcome.residual_open_item_ids == ()
    assert [r.selected_item_ids for r in outcome.rounds] == [
        (ids[0],), (ids[1],), (),
    ]


def test_accumulation_removed_reopens_the_closed_item(monkeypatch):
    """Turns-red proof for the accumulation fix: with the history dropped
    from the compile (the pre-rework behaviour, simulated by keeping only
    the LAST round's decisions), the same fixture sequence must NOT
    succeed -- the first round's item re-opens and the loop cannot
    converge.  The monkeypatch target is the executor module's own name
    (the loop calls ``compile_wall_ir`` through its module globals)."""
    real_compile = dx.compile_wall_ir

    def drop_history(artifact, *, profile="strict", decisions=()):
        return real_compile(
            artifact, profile=profile, decisions=tuple(decisions[-1:])
        )

    monkeypatch.setattr(dx, "compile_wall_ir", drop_history)
    artifact = _two_pair_artifact()
    responses, ids = _two_round_responses(artifact)
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=responses,
    )
    assert outcome.exit_reason != "success"
    assert outcome.success is False
    assert ids[0] in outcome.residual_open_item_ids  # the re-opened one


def test_accept_mixed_into_every_select_round_never_succeeds():
    """Acceptance 6, the same-shape input for B-1 (a DIFFERENT carrier of
    the same disease family): instead of one select+accept round, EVERY
    round selects the remaining item AND accepts in the same breath.  No
    round's accept ever binds the geometry it executed onto -- so no
    round may succeed, and the sequence must end loud, not washed into a
    success by the last round's optimistic verdict."""
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    ids = sorted(i.item_id for i in packet0.open_items)
    first = _select(ids[0], packet0)
    packet1 = _round1_packet(artifact, first)
    second = _select(ids[1], packet1)  # verdict=accept rides along too
    outcome = dx.run_decision_loop(
        artifact, profile="strict", responses=(first, second),
    )
    assert outcome.exit_reason != "success"
    assert outcome.success is False
    # both items WERE decided; the loop simply never got an accept that
    # bound the final provisional
    assert outcome.residual_open_item_ids == ()


# =========================================================================== #
# Rework B-3 -- the explicit profile × debt-kind/channel policy
# =========================================================================== #
#: The expectation grid, written out INDEPENDENTLY of the implementation
#: table (a plain reading of §6.1/§6.3/§9.4): key = (kind, is-the-subject
#: channel).  Every cell is exercised below -- so flipping any single
#: ruling is a visible red, not a silent semantics change.
_DEBT_POLICY_EXPECTATION = {
    profile: {
        ("ambiguous_face", True): True,
        ("ambiguous_face", False): True,
        ("pairs_selection_absent", True): True,
        ("pairs_selection_absent", False): True,
        ("missing_channel", True): True,
        ("missing_channel", False): False,
        ("zero_payload_channel", True): True,
        ("zero_payload_channel", False): False,
        ("other_known_missing", True): False,
        ("other_known_missing", False): False,
    }
    for profile in ("strict", "exploratory")
}


@pytest.mark.parametrize("walls_subject", [True, False, None])
@pytest.mark.parametrize(
    "kind",
    ["ambiguous_face", "pairs_selection_absent", "missing_channel",
     "zero_payload_channel", "other_known_missing"],
)
@pytest.mark.parametrize("profile", ["strict", "exploratory"])
def test_debt_policy_cell_by_cell(profile, kind, walls_subject):
    """All 30 cells of the policy grid: subject-channel (``walls``) on
    the boolean axis, support channels and ``channel=None`` on the other
    side of it."""
    if walls_subject is None:
        channel = None
    else:
        channel = "walls" if walls_subject else "dimensions"
    expected = _DEBT_POLICY_EXPECTATION[profile][(kind, bool(walls_subject))]
    assert dx._debt_blocks_success(kind, channel, profile) is expected


def test_debt_policy_unregistered_cell_raises():
    """A (kind, channel) pair the table never registered is a policy GAP
    -- it raises, never silently passes (nor silently blocks)."""
    with pytest.raises(dx.DecisionLoopError) as exc:
        dx._debt_blocks_success("some_future_kind", "walls", "strict")
    assert exc.value.code == "DEBT_POLICY_CELL_UNREGISTERED"


def test_pairs_absent_blocks_success_in_both_profiles():
    """B-3's own end-to-end shape: honest ``non_wall`` faces (zero open
    items), an overall accept -- and a ``pairs_selection_absent`` debt on
    the record.  §6.1 says reading-pairs-missing is ``reperception_
    required``; correction may not substitute in ANY profile, so neither
    profile may call this a success."""
    for profile in ("strict", "exploratory"):
        artifact = _pairs_absent_artifact()
        _, packet = _packet_round0(artifact, profile=profile)
        assert packet.open_items == ()  # premise: nothing left to decide
        outcome = dx.run_decision_loop(
            artifact, profile=profile,
            responses=(CorrectionDecisionResponseV1(
                packet_hash=packet.packet_hash,
                whole_building_review={"verdict": "accept"},
            ),),
        )
        assert outcome.exit_reason != "success", profile
        assert outcome.success is False
        assert outcome.residual_debt_ids  # the manifest says why


def test_walls_channel_missing_blocks_success_in_both_profiles():
    """The subject channel's ``missing_channel``: zero wall claims at all
    -- an empty accept over an empty provisional must not wash into a
    success (the provisional would BE nothing)."""
    for profile in ("strict", "exploratory"):
        artifact = _walls_missing_artifact()
        _, packet = _packet_round0(artifact, profile=profile)
        outcome = dx.run_decision_loop(
            artifact, profile=profile,
            responses=(CorrectionDecisionResponseV1(
                packet_hash=packet.packet_hash,
                whole_building_review={"verdict": "accept"},
            ),),
        )
        assert outcome.exit_reason != "success", profile
        assert outcome.success is False
        kinds = {
            (d.kind, d.channel) for d in artifact.bundle.evidence_debts
        }
        assert ("missing_channel", "walls") in kinds  # premise holds


# =========================================================================== #
# Rework B-4 -- openings in the packet, typed entity closure
# =========================================================================== #
def _opening_packet():
    artifact = _opening_artifact()
    compilation, packet = _packet_round0(artifact)
    return artifact, packet


def _packet_wall_ids(packet):
    return [
        e.entity_id for e in packet.entity_to_source_refs
        if e.entity_kind == "wall"
    ]


def test_packet_indexes_real_openings_with_kind():
    """The rework's own headline reading: the packet's entity table
    carries the bundle's real opening claims, TYPED as ``opening`` --
    before the rework the entity table held no opening at all (the real
    products indexed 0 of 85/87/87)."""
    _, packet = _opening_packet()
    opening_entities = {
        e.entity_id: e.entity_kind
        for e in packet.entity_to_source_refs
        if e.entity_id == "op01"
    }
    assert opening_entities == {"op01": "opening"}
    assert _packet_wall_ids(packet)  # walls are typed too


def _opening_host_response(packet, *, opening_id, candidate_ids):
    return CorrectionDecisionResponseV1(
        packet_hash=packet.packet_hash,
        whole_building_review=WholeBuildingReviewV1(
            verdict="findings",
            findings=(FindingV1(
                finding_id="F_OPENING_PROBE", kind="OPENING_HOST",
                affected_entity_ids=(opening_id,),
                requested_effect=ReviewOpeningHostEffectV1(
                    kind="review_opening_host",
                    opening_entity_id=opening_id,
                    candidate_wall_entity_ids=tuple(candidate_ids),
                ),
                rationale="PROBE",
            ),),
        ),
    )


def test_fabricated_candidate_wall_id_is_refused():
    """B-4 example 1: a wall id invented OUTSIDE the packet in the
    candidate list -- membership alone was enough to carry it into
    pending_findings before; now the entity table refuses it."""
    artifact, packet = _opening_packet()
    response = _opening_host_response(
        packet, opening_id="op01",
        candidate_ids=_packet_wall_ids(packet)
        + ["wall_invented_outside_packet"],
    )
    _expect_error(
        lambda: dx.run_decision_loop(artifact, responses=(response,)),
        "FINDING_ENTITY_NOT_IN_PACKET",
    )


def test_wall_id_cannot_impersonate_an_opening():
    """B-4 example 2: a REAL packet wall id in the ``opening_entity_id``
    slot.  It is in the packet, so membership passes -- the KIND check is
    what catches the impersonation."""
    artifact, packet = _opening_packet()
    wall_id = _packet_wall_ids(packet)[0]
    response = _opening_host_response(
        packet, opening_id=wall_id, candidate_ids=_packet_wall_ids(packet),
    )
    _expect_error(
        lambda: dx.run_decision_loop(artifact, responses=(response,)),
        "FINDING_ENTITY_WRONG_KIND",
    )


def test_candidate_list_entry_must_be_wall_kind():
    """Same-shape input for B-4 (a different carrier of the same family):
    the candidate slot cites a REAL packet entity of the WRONG kind (an
    open item id, not a wall id) -- presence passes, kind refuses."""
    artifact, packet = _opening_packet()
    item_id = packet.open_items[0].item_id
    response = _opening_host_response(
        packet, opening_id="op01", candidate_ids=(item_id,),
    )
    _expect_error(
        lambda: dx.run_decision_loop(artifact, responses=(response,)),
        "FINDING_ENTITY_WRONG_KIND",
    )


def test_legal_opening_host_finding_rides_the_outcome():
    """The positive control: a real opening id in the opening slot and
    real wall ids in the candidate list -- typed membership PASSES and
    the finding rides the outcome (the closure must be able to say yes,
    or "cannot legally use review_opening_host" would still be true)."""
    artifact, packet = _opening_packet()
    response = _opening_host_response(
        packet, opening_id="op01", candidate_ids=_packet_wall_ids(packet),
    )
    outcome = dx.run_decision_loop(artifact, responses=(response,))
    assert [
        f.finding_id for f in outcome.pending_findings
    ] == ["F_OPENING_PROBE"]
    effect = outcome.pending_findings[0].requested_effect
    assert effect.opening_entity_id == "op01"


def test_pure_accept_after_failed_accept_exits_cycle():
    """The path-overlap fixture from the rework report (R五): a pure
    accept that FAILS on another conjunct (an item still open), followed
    by ANOTHER pure accept.  The second one repeats the (empty) decision
    set, so the loud exit is ``decision_hash_cycle`` -- not a silent
    third round, and not the stall streak expiring first."""
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    ids = sorted(i.item_id for i in packet0.open_items)
    first = _select(ids[0], packet0)
    packet1 = _round1_packet(artifact, first)
    accept1 = CorrectionDecisionResponseV1(
        packet_hash=packet1.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    # round 1's accept failed on conjunct 1 (ids[1] still open); the
    # compilation it leaves behind is exactly packet1's own
    decided = wc.compile_wall_ir(artifact, decisions=(
        wc.FixedDecisionV1(
            item_id=first.item_decisions[0].item_id,
            candidate_id=first.item_decisions[0].candidate_id,
        ),
    ))
    packet2 = dx.build_decision_packet(
        decided, bundle=artifact, round_index=2,
        previous_decision_hashes=(
            dx.decision_hash(first), dx.decision_hash(accept1),
        ),
    )
    accept2 = CorrectionDecisionResponseV1(
        packet_hash=packet2.packet_hash,
        whole_building_review={"verdict": "accept"},
    )
    outcome = dx.run_decision_loop(
        artifact, responses=(first, accept1, accept2),
    )
    assert outcome.exit_reason == "decision_hash_cycle"
    assert outcome.success is False
    assert ids[1] in outcome.residual_open_item_ids


# =========================================================================== #
# Acceptance 6 -- the five requested_effect kinds, closed at the type layer
# =========================================================================== #
_EFFECT_KINDS = {
    "review_alignment": lambda: ReviewAlignmentEffectV1(
        kind="review_alignment", subject_entity_ids=("w1",),
        reference_entity_ids=("w2",), relation="collinear"),
    "review_segmentation": lambda: ReviewSegmentationEffectV1(
        kind="review_segmentation", subject_entity_ids=("w1",),
        relation="split_required"),
    "review_topology_relation": lambda: ReviewTopologyRelationEffectV1(
        kind="review_topology_relation", subject_entity_ids=("w1",),
        reference_entity_ids=("w2",), relation="connect"),
    "review_opening_host": lambda: ReviewOpeningHostEffectV1(
        kind="review_opening_host", opening_entity_id="op1",
        candidate_wall_entity_ids=("w1", "w2")),
    "request_wall_reperception": lambda: RequestWallReperceptionEffectV1(
        kind="request_wall_reperception",
        wall_item_entity_ids=("w1",), reason_code="CANNOT_READ_BAND"),
}


def test_every_effect_kind_roundtrips_and_rejects_unlisted_fields():
    for kind, factory in _EFFECT_KINDS.items():
        effect = factory()
        assert effect.kind == kind
        # each kind rejects an unlisted field OF ITS OWN (strict schema
        # per kind, not one loose union member)
        payload = effect.model_dump()
        payload["target_pos_m"] = 3.5  # the smuggling attempt
        with pytest.raises(ValidationError) as exc:
            type(effect).model_validate(payload)
        kinds = {e["type"] for e in exc.value.errors()}
        assert "extra_forbidden" in kinds, (kind, kinds)


def test_sixth_effect_kind_is_rejected_by_the_discriminator():
    payload = {
        "kind": "review_magic",  # not in the closed §6.2 table
        "subject_entity_ids": ("w1",), "relation": "collinear",
    }
    with pytest.raises(ValidationError) as exc:
        FindingV1(finding_id="F", kind="K", rationale="R",
                  requested_effect=payload)
    messages = " ".join(e["msg"] for e in exc.value.errors())
    assert "review_magic" in messages  # the union refused to match


def test_relation_value_domains_are_closed():
    """Each kind's relation enum is closed too: 'diagonal' is not an
    alignment relation, whatever the model might think."""
    with pytest.raises(ValidationError):
        ReviewAlignmentEffectV1(
            kind="review_alignment", subject_entity_ids=("w1",),
            reference_entity_ids=("w2",), relation="diagonal")


def test_finding_citations_must_resolve_inside_the_packet():
    """A finding citing an entity the packet never indexed is refused
    loudly; the same finding with a packet entity rides the outcome."""
    artifact = _one_pair_artifact()
    _, packet = _packet_round0(artifact)
    item = packet.open_items[0]
    wall_id = item.scope_entity_ids[0]

    def response_for(effect_subject):
        return CorrectionDecisionResponseV1(
            packet_hash=packet.packet_hash,
            item_decisions=_select(item.item_id, packet).item_decisions,
            whole_building_review=WholeBuildingReviewV1(
                verdict="findings",
                findings=(FindingV1(
                    finding_id="FIND_ONE", kind="SHAPE",
                    affected_entity_ids=(effect_subject,),
                    requested_effect=RequestWallReperceptionEffectV1(
                        kind="request_wall_reperception",
                        wall_item_entity_ids=(effect_subject,),
                        reason_code="CANNOT_READ"),
                    rationale="BAND_UNREADABLE",
                ),),
            ),
        )

    _expect_error(
        lambda: dx.run_decision_loop(
            artifact, responses=(response_for("wall_invented_9"),)
        ),
        "FINDING_ENTITY_NOT_IN_PACKET",
    )
    outcome = dx.run_decision_loop(
        artifact, responses=(response_for(wall_id),)
    )
    assert [f.finding_id for f in outcome.pending_findings] == ["FIND_ONE"]


# =========================================================================== #
# The deterministic check face has teeth (it is not a rubber stamp)
# =========================================================================== #
def test_overlap_check_catches_two_walls_sharing_along_span():
    artifact = _overlap_artifact()
    compilation = wc.compile_wall_ir(artifact)
    results = {c.check: c for c in dx.run_consistency_checks(compilation)}
    overlap = results["collinear_wall_overlap"]
    assert overlap.passed is False
    wall_ids = sorted(w.wall_id for w in compilation.walls)
    assert wall_ids[0] in overlap.detail and wall_ids[1] in overlap.detail


def test_tail_coverage_check_catches_a_drifted_fragment():
    """The information-preservation check proves its discriminating
    power the only honest way: take a REAL compilation (unequal faces,
    so a tail fragment exists), drift one fragment outside its wall,
    and the check must go red -- a gate that only ever sees honest
    products has no teeth (the carrier can be swapped)."""
    doc = _doc(
        [_face("F01", "col", "x", 100, [[10, 100]]),
         _face("F02", "col", "x", 112, [[10, 40]])],
        [_pair("F01", "F02", 12.0)],
    )
    artifact = _adapt(doc, "tail_fixture")
    compilation = wc.compile_wall_ir(artifact)
    assert all(c.passed for c in dx.run_consistency_checks(compilation))
    wall = compilation.walls[0]
    assert wall.unshared_tail_fragments, "premise broke: no fragment"
    fragment = wall.unshared_tail_fragments[0]
    _, hi = fragment.along_interval_m
    drifted = fragment.model_copy(
        update={"along_interval_m": (hi + 5.0, hi + 9.0)}
    )
    tampered = wall.model_copy(update={"unshared_tail_fragments": (drifted,)})
    compilation = compilation.model_copy(
        update={"walls": [tampered] + list(compilation.walls[1:])}
    )
    results = {c.check: c for c in dx.run_consistency_checks(compilation)}
    assert results["unshared_tail_coverage"].passed is False


# =========================================================================== #
# Acceptance 8 -- zero wiring, module 4's STRENGTHENED lock shape
# =========================================================================== #
#: The two new modules' ENTIRE non-stdlib import face: module 2/4's
#: corrections modules (types, hash discipline, the compiler itself),
#: module 5's schema (module 6 imports it), and pydantic.  Anything
#: outside this set is a new wiring edge and fails the AST lock on
#: purpose at the diff.
_DECISION_IMPORT_ALLOWLIST = frozenset({
    "src.agent.correction.evidence_contract",
    "src.agent.correction.wall_compiler",
    "src.agent.correction.window_sources",
    "src.agent.correction.decision_schema",
    "pydantic",
})


def _probe_modules(target: str, extra_path: str | None = None) -> set[str]:
    probe = (
        "import sys; " + (
            f"sys.path.insert(0, {extra_path!r}); " if extra_path else ""
        ) +
        "import " + target + "; "
        "print(sorted(m for m in sys.modules if "
        "m == 'src.agent.pipeline' or m.startswith('src.agent.judge')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    assert result.returncode == 0, result.stderr
    return set(ast.literal_eval(result.stdout.strip()))


def _external_imports(source: str) -> set[str]:
    """The AST lock's core, factored so the turns-red test can aim it at
    a deliberately foreign source."""
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module)
    return {
        name for name in imported
        if not name.startswith("_")
        and name.split(".")[0] not in sys.stdlib_module_names
    }


def test_decision_modules_add_no_pipeline_or_judge_edge_beyond_module_2():
    """Lock 1 (difference): the pipeline∪judge modules reachable after
    importing EACH new module equal module 2's own reachable set -- the
    same strengthened premise module 4 shipped: bare absence of judge in
    sys.modules is structurally unreachable inside this package (the
    package init chain carries it), so the measured quantity is the
    DIFFERENCE, and the difference must be empty."""
    baseline = _probe_modules("src.agent.correction.evidence_contract")
    assert baseline, "premise broke: module 2 no longer reaches judge"
    for target in ("src.agent.correction.decision_schema",
                   "src.agent.correction.decision_executor"):
        mine = _probe_modules(target)
        assert mine == baseline, (
            f"{target} changed the reachable pipeline/judge set: "
            f"added={sorted(mine - baseline)} "
            f"removed={sorted(baseline - mine)}"
        )


def test_decision_modules_import_face_is_the_allowlist():
    """Lock 2 (face): every non-stdlib import in the new modules' own
    source, AST-walked, sits on the explicit allowlist -- a third import
    fails here, at the diff."""
    import src.agent.correction.decision_schema as ds
    for module in (ds, dx):
        source = Path(module.__file__).read_text(encoding="utf-8")
        external = _external_imports(source)
        assert external <= _DECISION_IMPORT_ALLOWLIST, (
            f"{module.__name__}: {sorted(external - _DECISION_IMPORT_ALLOWLIST)}"
        )


def test_ast_lock_turns_red_on_a_foreign_import():
    """The AST lock's on-the-spot red proof: aim it at a source carrying
    one import outside the allowlist and it must flag exactly that (the
    allowlisted ``pydantic`` in the same source stays quiet)."""
    foreign = _external_imports(
        "import json\nimport requests\nfrom pydantic import BaseModel\n"
    )
    assert foreign - _DECISION_IMPORT_ALLOWLIST == {"requests"}
    assert _DECISION_IMPORT_ALLOWLIST & foreign == {"pydantic"}


def test_difference_lock_turns_red_on_a_real_new_edge():
    """The difference lock's on-the-spot red proof: a module in a temp
    directory that really imports the pipeline reaches it (probe runs in
    a subprocess, nothing is written into this package).  The reachable
    set gains exactly the pipeline -- which is what the lock refuses."""
    import tempfile as _tf
    with _tf.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad_wiring_probe.py"
        bad.write_text("import src.agent.pipeline\n", encoding="utf-8")
        baseline = _probe_modules("src.agent.correction.evidence_contract")
        reached = _probe_modules("bad_wiring_probe", extra_path=tmp)
        added = reached - baseline
        assert added, "premise broke: the probe found no new edge"
        assert "src.agent.pipeline" in added


# =========================================================================== #
# Acceptance 9 -- determinism (module 2/4's hash discipline, executor half)
# =========================================================================== #
def test_same_bundle_and_decisions_produce_byte_identical_artifacts():
    artifact = _two_pair_artifact()
    _, packet0 = _packet_round0(artifact)
    items = sorted(i.item_id for i in packet0.open_items)
    responses = (
        _select(items[0], packet0),
        _select(items[1], _round1_packet(artifact, _select(items[0], packet0))),
    )
    first = dx.run_decision_loop(artifact, responses=responses)
    second = dx.run_decision_loop(artifact, responses=responses)
    assert first.content_sha256 == second.content_sha256
    assert first.model_dump_json() == second.model_dump_json()
    # the packet build is deterministic on its own, byte for byte
    compilation = wc.compile_wall_ir(artifact)
    p1 = dx.build_decision_packet(compilation, bundle=artifact, round_index=0)
    p2 = dx.build_decision_packet(compilation, bundle=artifact, round_index=0)
    assert p1.model_dump_json() == p2.model_dump_json()


def test_packet_hash_binds_the_whole_world():
    """The binding is total: round index, the provisional hash, or any
    open item changing MUST move the packet hash -- a response binding
    the hash binds all of it."""
    artifact = _two_pair_artifact()
    compilation, packet = _packet_round0(artifact)
    assert packet.previous_decision_hashes == ()
    later = dx.build_decision_packet(
        compilation, bundle=artifact, round_index=1,
        previous_decision_hashes=("c" * 64,),
    )
    assert later.packet_hash != packet.packet_hash
    assert later.provisional_geometry == packet.provisional_geometry
    # a different provisional (one decision applied) moves the hash too
    item = packet.open_items[0]
    decided = wc.compile_wall_ir(
        artifact, decisions=(wc.FixedDecisionV1(
            item_id=item.item_id,
            candidate_id=item.candidates[0].candidate_id),)
    )
    moved = dx.build_decision_packet(decided, bundle=artifact, round_index=0)
    assert moved.provisional_geometry != packet.provisional_geometry


def test_packet_rejects_history_that_disagrees_with_round_index():
    """round_index=2 with ZERO previous decision hashes: the packet's own
    validator refuses the disagreement (one decision hash per elapsed
    round)."""
    one_pair = _one_pair_artifact()
    compilation = wc.compile_wall_ir(one_pair)
    packet = dx.build_decision_packet(
        compilation, bundle=one_pair, round_index=0
    )
    payload = json.loads(packet.model_dump_json())
    payload["round_index"] = 2
    with pytest.raises(ValidationError):
        CorrectionDecisionPacketV1.model_validate(payload)


def test_model_response_json_entry_accepts_arrays():
    """The door module 7 will actually use: a model's JSON (arrays, not
    python tuples) parses through ``model_validate_json`` even under the
    strict config -- pinned here so the wiring step cannot discover it
    as a surprise."""
    payload = json.dumps({
        "packet_hash": "a" * 64,
        "item_decisions": [
            {"item_id": "i1", "action": "reject_all", "reason_code": "R"}],
        "whole_building_review": {"verdict": "accept"},
    })
    parsed = CorrectionDecisionResponseV1.model_validate_json(payload)
    assert parsed.item_decisions[0].action == "reject_all"
