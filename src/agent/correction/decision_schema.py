"""②-2 module 5: the decision packet and the decision-response schemas.

Dispatch: the 2026-09-01 module 5+6 dispatch; authority: the 2026-08-30
evidence-contract design §6.1 / §6.2 (cross-family approved).  Module 4's
own docstring reserves exactly this slice: "cost vectors, packets and
response schemas (module 5)".

Shapes
------
``CorrectionDecisionPacketV1`` (code → model) and
``CorrectionDecisionResponseV1`` (model → code) carry the field lists of
design §6.1 / §6.2 verbatim; the open-item / auto-action / wall-summary
shapes are module 4's own types, re-used by import, never re-declared.
The module-4 seam ``FixedDecisionV1`` documents ("the response SCHEMA is
module 5's; this type is deliberately the minimal binding") is exactly
the ``select_candidate`` action below.

Two sub-structures §6.1 names without giving fields (``entity_to_source_
refs[]``, ``consistency_results[]``) get the smallest shapes that carry
the named meaning; the choice is recorded in the execution report, not
silently frozen here.

``provisional_geometry`` is the provisional compilation's content hash
(module 4's ``WallCompilationV1.content_sha256``), ⛔ not an embedded copy:
an embedded compilation would duplicate ``open_items`` / ``auto_actions``
that §6.1 also lists at the top level, and two copies can disagree.  One
hash anchor plus the flat lists leaves exactly one copy of everything.

Coordinates are structurally absent from the RESPONSE side
---------------------------------------------------------
The response type tree contains NO numeric field of any kind: item
decisions are (id, enum, id, reason) tuples, findings reference packet
entities by identifier and carry a discriminated ``requested_effect``
whose five kinds are a CLOSED value domain (design §6.2's table verbatim),
each with its own strict schema.  This is not a naming discipline: a
field holding a number cannot be constructed on this side, so "the model
outputs coordinates" fails at the type layer, whatever the field is
called.  ``extra="forbid"`` everywhere closes the last gap -- an ``x``
the schema never listed is rejected before any executor code runs, not
by a lexical scan for suspicious names.

The entity/reference closure ("all entities and refs must already be in
the packet", §6.2) is cross-object, so it cannot live in a schema: the
executor owns it.  Acceptance 3's fabricated-candidate fixture proves it
on the item path; the entity-index check proves it on the finding path.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agent.correction.evidence_contract import ArtifactPointerV1
from src.agent.correction.wall_compiler import (
    AutoActionV1,
    OpenItemV1,
    ResolvedWallV1,
)
from src.agent.correction.window_sources import Hex64

_CFG = ConfigDict(extra="forbid", strict=True)


# ── packet sub-structures §6.1 names without fields ------------------------- #
class EntitySourceRefsV1(BaseModel):
    """One packet entity, its kind and the frozen references that ground it.

    Minimal carrier of the §6.1 ``entity_to_source_refs[]`` slot: the
    model looks an entity up here to cite evidence, the executor checks
    finding citations against exactly this index.

    ``entity_kind`` is a CLOSED domain (rework B-4): the packet's entity
    table does not just list ids, it says WHAT each id is.  A ``review_
    opening_host`` finding must cite an entity whose kind really is
    ``opening``, and every candidate wall id one whose kind really is
    ``wall`` -- membership alone let a real wall id impersonate an
    opening, which is exactly the bypass the cross-review caught.
    """

    model_config = _CFG

    entity_id: str
    entity_kind: Literal[
        "wall", "opening", "open_item", "auto_action_scope"
    ]
    source_refs: tuple[ArtifactPointerV1, ...] = ()


class ConsistencyResultV1(BaseModel):
    """One deterministic check over the provisional compilation (§6.3
    step 4), as it travels on the NEXT packet.  ``check`` is a closed
    enum: growing the check face means growing this Literal, which is a
    visible diff -- an unnamed free-text check name cannot appear."""

    model_config = _CFG

    check: Literal["collinear_wall_overlap", "unshared_tail_coverage"]
    passed: bool
    detail: str


# ── §6.1 first beat: the packet (code → model) ------------------------------- #
class CorrectionDecisionPacketV1(BaseModel):
    """Everything the model may see for one adjudication round.  Hashed
    canonically: ``packet_hash`` is ``canonical_sha256`` over the packet
    with the hash field removed, so a response binding this hash binds
    every field of this packet (module 2's discipline, applied here)."""

    model_config = _CFG

    packet_hash: Hex64
    input_bundle_hash: Hex64
    solver_revision: str
    round_index: int
    previous_decision_hashes: tuple[Hex64, ...] = ()
    provisional_geometry: Hex64
    provisional_wall_summaries: tuple[ResolvedWallV1, ...] = ()
    entity_to_source_refs: tuple[EntitySourceRefsV1, ...] = ()
    auto_actions: tuple[AutoActionV1, ...] = ()
    consistency_results: tuple[ConsistencyResultV1, ...] = ()
    open_items: tuple[OpenItemV1, ...] = ()

    @model_validator(mode="after")
    def _round_agrees_with_history(self) -> "CorrectionDecisionPacketV1":
        if self.round_index < 0:
            raise ValueError("round_index counts from 0")
        if len(self.previous_decision_hashes) != self.round_index:
            raise ValueError(
                f"round_index={self.round_index} but "
                f"{len(self.previous_decision_hashes)} previous decision "
                "hash(es): exactly one decision hash per elapsed round"
            )
        return self


# ── §6.2 second beat: the response (model → code) ---------------------------- #
class ItemDecisionV1(BaseModel):
    """One decision on one packet item.  ``candidate_id`` rides along
    ONLY on ``select_candidate`` -- the other two actions decide WITHOUT
    a candidate (reject every listed one / hand the item back to reading),
    and a candidate id arriving with them is a malformed response."""

    model_config = _CFG

    item_id: str
    action: Literal["select_candidate", "reject_all", "request_reperception"]
    candidate_id: str | None = None
    reason_code: str

    @model_validator(mode="after")
    def _candidate_only_with_select(self) -> "ItemDecisionV1":
        if self.action == "select_candidate":
            if self.candidate_id is None:
                raise ValueError(
                    "select_candidate must name the chosen candidate"
                )
        elif self.candidate_id is not None:
            raise ValueError(
                f"{self.action} carries candidate_id={self.candidate_id!r}: "
                "only select_candidate may name a candidate"
            )
        return self


# ── the five requested_effect kinds (design §6.2's table, verbatim) ---------- #
class ReviewAlignmentEffectV1(BaseModel):
    """``review_alignment``: subject/reference entity ids from the packet;
    relation restricted to collinear/parallel/perpendicular.  The model
    names WHO to align and WHICH relation -- never a target line."""

    model_config = _CFG

    kind: Literal["review_alignment"]
    subject_entity_ids: tuple[str, ...]
    reference_entity_ids: tuple[str, ...]
    relation: Literal["collinear", "parallel", "perpendicular"]


class ReviewSegmentationEffectV1(BaseModel):
    """``review_segmentation``: packet subject ids; relation restricted to
    split_required/merge_review_required.  Candidates are enumerated by
    the compiler from source intervals, not described here."""

    model_config = _CFG

    kind: Literal["review_segmentation"]
    subject_entity_ids: tuple[str, ...]
    relation: Literal["split_required", "merge_review_required"]


class ReviewTopologyRelationEffectV1(BaseModel):
    """``review_topology_relation``: packet subject/reference ids; relation
    restricted to connect/separate."""

    model_config = _CFG

    kind: Literal["review_topology_relation"]
    subject_entity_ids: tuple[str, ...]
    reference_entity_ids: tuple[str, ...]
    relation: Literal["connect", "separate"]


class ReviewOpeningHostEffectV1(BaseModel):
    """``review_opening_host``: one packet opening id plus the candidate
    wall ids to rehost among.  The finding itself changes no host."""

    model_config = _CFG

    kind: Literal["review_opening_host"]
    opening_entity_id: str
    candidate_wall_entity_ids: tuple[str, ...]


class RequestWallReperceptionEffectV1(BaseModel):
    """``request_wall_reperception``: packet wall/item ids, the source
    refs being re-read and a reason code (design §7.3's wall-level
    directed request).  Generates no geometry."""

    model_config = _CFG

    kind: Literal["request_wall_reperception"]
    wall_item_entity_ids: tuple[str, ...]
    source_refs: tuple[ArtifactPointerV1, ...] = ()
    reason_code: str


RequestedEffectV1 = Annotated[
    Union[
        ReviewAlignmentEffectV1,
        ReviewSegmentationEffectV1,
        ReviewTopologyRelationEffectV1,
        ReviewOpeningHostEffectV1,
        RequestWallReperceptionEffectV1,
    ],
    Field(discriminator="kind"),
]


class FindingV1(BaseModel):
    """One whole-building finding.  It is a REQUEST for the next round's
    candidate generation, ⛔ not an executable instruction: the executor
    verifies it against the packet's entity/ref index and carries it to
    the next round; the bounded candidates it asks for are generated by
    code (compiler / opening resolver), never described here (§6.2)."""

    model_config = _CFG

    finding_id: str
    kind: str
    affected_entity_ids: tuple[str, ...] = ()
    source_refs: tuple[ArtifactPointerV1, ...] = ()
    requested_effect: RequestedEffectV1
    rationale: str


class WholeBuildingReviewV1(BaseModel):
    """The model's overall verdict on the SAME provisional geometry the
    packet hashed (§6.3's success condition 3 binds through packet_hash).
    ``findings`` may name problems the code never listed -- that channel
    exists precisely so the model never has to smuggle them into item
    decisions."""

    model_config = _CFG

    verdict: Literal["accept", "findings"]
    findings: tuple[FindingV1, ...] = ()

    @model_validator(mode="after")
    def _verdict_agrees_with_findings(self) -> "WholeBuildingReviewV1":
        if self.verdict == "accept" and self.findings:
            raise ValueError(
                "verdict=accept carries findings: acceptance is unconditioned"
            )
        return self


class CorrectionDecisionResponseV1(BaseModel):
    """The model's whole answer for one packet.  ⭐ There is no coordinate
    anywhere on this type or anything reachable from it -- see the module
    docstring; the structural proof is a test that walks this type's
    field tree and fails on ANY numeric field."""

    model_config = _CFG

    packet_hash: Hex64
    item_decisions: tuple[ItemDecisionV1, ...] = ()
    whole_building_review: WholeBuildingReviewV1


__all__ = [
    "ConsistencyResultV1",
    "CorrectionDecisionPacketV1",
    "CorrectionDecisionResponseV1",
    "EntitySourceRefsV1",
    "FindingV1",
    "ItemDecisionV1",
    "RequestedEffectV1",
    "RequestWallReperceptionEffectV1",
    "ReviewAlignmentEffectV1",
    "ReviewOpeningHostEffectV1",
    "ReviewSegmentationEffectV1",
    "ReviewTopologyRelationEffectV1",
    "WholeBuildingReviewV1",
]
