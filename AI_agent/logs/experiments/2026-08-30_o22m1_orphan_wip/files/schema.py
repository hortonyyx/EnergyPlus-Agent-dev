"""The as-drawn plan **producer's own type** (②-2 module 1, 2026-08-30).

Why this file exists
--------------------
Until today ``as_drawn_v2.assemble()`` returned a bare ``dict`` and the only
thing that ever looked at an as-drawn product was
``reading/vector_contract.py``'s detector, which asked two questions::

    _is_declared(raw, AS_DRAWN_PLAN_SCHEMA) and _has_keys(raw, "observations",
                                                          "declarations",
                                                          "hypotheses")

⇒ **a file whose ``schema`` string matched and whose three top-level keys were
present was "recognized" no matter what was inside them.**  A bucket holding
``{"L003": {"reason": ...}}`` instead of ``{"L003": "..."}``, a pair missing its
``face_b``, a run written as three numbers instead of two — all of it passed as
a well-formed product.  The ②-2 design draft (`§4.4 #7`) names that failure
``MALFORMED_DECLARED_CONTRACT`` and rules that a declared-but-invalid product
must be loud; it cannot be, while nothing owns the shape.  This module owns it.

Two properties are deliberate and load-bearing
----------------------------------------------
1. ⭐ **Validation never returns a value.**  ``validate_plan_document`` is typed
   ``-> None`` on purpose: there is no validated object for a caller to
   serialize, so "the product went through the type" can never quietly become
   "the product is now whatever the type dumped".  The producer keeps and
   returns *its own object*; the type is a gate, ⛔ not a normalizer.  (Same
   lesson as ②-1c's NF-1: make the wrong path *not exist in the type* rather
   than forbid it in prose.)
2. ⭐ **Everything this version does not validate is declared, not swallowed.**
   ⛔ No ``extra="allow"`` standing in for "we did not get to that channel yet".
   Each such field is ``Annotated[Any, Deferred("why")]`` and
   ``deferred_channels()`` lists every one of them with its reason, so the debt
   is enumerable instead of being an absence nobody can see
   ([[absence-conflates-causes-in-observables]]).

Scope of this version — how many "buckets", and why
---------------------------------------------------
The GLM cut for this module reads (verbatim): *"字段覆盖 = 墙 + 洞口两族
(``face_lines`` / ``pairs`` / ``pair_candidates`` / 五桶 / ``opening_candidates``
/ ``opening_types``); ``ledger``/``roles`` 等非墙通道登记 plan.md 缓做"*.

⭐ **The perception buckets carried in ``hypotheses`` number FOUR, not five.**
Counted, not estimated:

* the approved ②-2 design draft §3.1 enumerates exactly four by name —
  ``non_wall_face_lines`` / ``unpaired_wall_faces`` / ``solid_band_walls`` /
  ``ambiguous_face_lines``;
* §4.3 of the same draft rules out the most tempting fifth in as many words:
  "``pair_candidates`` 是代码枚举的候选关系图，**不是第五或第七种墙**";
* the batch guide's perception table does list **six** buckets, but two of them
  are already named separately inside the very sentence that says "五桶":
  ``wall_pairs`` arrives as ``pairs``, and ``family_roles`` is the ``roles``
  that same sentence defers.  6 − 2 = 4;
* all three real products (sm24 1F, sm25 1F, sm25 2F) carry exactly these four
  and no other face-id-keyed bucket in ``hypotheses``;
* ⭐ the likeliest origin of "五" is the producer's own completeness ledger:
  ``as_drawn_v2.select_pairs`` accounts for a face line through **five** sources
  — the four buckets *plus the faces named by ``pairs`` itself*.  Five ways to
  be accounted for; four buckets.

⛔ So this version types four, and says so, rather than inventing a fifth.

Known structural debt this type deliberately does NOT paper over (N-1)
----------------------------------------------------------------------
``unpaired_wall_faces`` is ``dict[face_id, reason_text]`` and stays that way —
the design draft §3.1 says "先忠实接住当前 ``dict[face_id, reason_text]``,
不要趁建模偷偷重写历史产物".  ⚠️ But note what that costs downstream: sm25 2F's
``L012`` is a wall face whose counterface's **ink is present in the image and
was dropped by the reader** (F-86), and the only place that fact exists is the
free-text reason.  Module 2's ``counterface_state`` therefore cannot be derived
from this product — its sixth state ``ink_present_unpromoted`` (cross-family
finding N-1) has no typed carrier here, and ⛔ the reason string must not be
parsed to invent one.  Fixing that is a change to the *product*, which is
module 2's business and a separate signature.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError

SCHEMA = "as_drawn_plan_v2"
"""⭐ The one place this string is defined.  ``as_drawn_v2`` re-exports it so
every historical import site (``vector_contract``, tests) keeps working."""

PRODUCER_TYPE_VERSION = "as_drawn_plan_v2_producer_types_v1"

__all__ = [
    "SCHEMA",
    "PRODUCER_TYPE_VERSION",
    "Deferred",
    "AsDrawnPlanContractError",
    "AsDrawnPlanV2",
    "ObservationsV2",
    "DeclarationsV2",
    "HypothesesV2",
    "FaceLineV2",
    "GapV2",
    "InkProfileV2",
    "PairCandidateV2",
    "SelectedPairV2",
    "OpeningCandidateV2",
    "PERCEPTION_BUCKET_FIELDS",
    "validate_plan_document",
    "explain_rejection",
    "deferred_channels",
]


@dataclass(frozen=True)
class Deferred:
    """Marker: this channel is carried through **without being validated**.

    ⛔ Not the same as ``extra="allow"``: the field still has to be *present*
    and it is listed by :func:`deferred_channels` together with the reason it
    was left out, so "we have not typed this yet" is a readable fact rather
    than a silence.
    """

    why: str


class AsDrawnPlanContractError(ValueError):
    """A document claiming to be an as-drawn plan v2 product is not one."""


# ⭐ ``strict=True``: in lax mode pydantic coerces ``"0.24"`` into ``0.24``, so a
# bucket element carrying strings where the producer writes numbers would still
# "validate" — which is the exact class of silence this module exists to end.
# ⚠️ Measured against all three real products before turning it on: every float
# field really is a JSON float and every int field really is a JSON int (the
# producer routes them through ``round(...)`` / ``int(...)``), so strictness
# costs nothing today.  (Strict mode still accepts an int for a ``float`` field;
# that is pydantic's documented behaviour and is fine — JSON ``2`` and ``2.0``
# mean the same measurement.)
class _Node(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


_Pair2I = Annotated[list[int], Field(min_length=2, max_length=2)]
_Pair2F = Annotated[list[float], Field(min_length=2, max_length=2)]


class InkProfileV2(_Node):
    """One ink family's distance profile across one blank stretch of a line."""

    on_line: int
    by_distance_px: dict[str, int]
    """⛔ Bin keys are deliberately NOT pinned to ``PROFILE_BINS_PX``: the bin set
    is a producer *parameter*, and a re-parameterised run is a different config,
    not a malformed product."""
    span_ratio: float
    nearest_px: int | None


class GapV2(_Node):
    """A blank stretch of a face line — measurements only, ⛔ never a class."""

    lo_px: int
    hi_px: int
    len_px: int
    ink_by_family: dict[str, InkProfileV2]
    span_m: _Pair2F
    len_m: float


class FaceLineV2(_Node):
    """One traced face line in ``observations`` — the only scorable layer."""

    id: str
    axis: Literal["col", "row"]
    constant_world_axis: Literal["x", "y"]
    pos_px: float
    pos_m: float
    support_cols_px: _Pair2I
    edges_m: _Pair2F
    support_width_m: float
    runs_px: list[_Pair2I]
    runs_m: list[_Pair2F]
    gaps: list[GapV2]
    ink_coverage_per_run: list[float]
    covered_px: int
    support_px: int


class PairCandidateV2(_Node):
    """One admissible same-axis partnering, enumerated by code with ⛔ no
    spacing threshold.  ``matched_declared_mm`` is a LABEL, never a gate."""

    face_a: str
    face_b: str
    spacing_px: float
    spacing_m: float
    matched_declared_mm: list[int]
    overlap_px: int


class SelectedPairV2(PairCandidateV2):
    """A candidate that perception chose.  ⭐ The selection is the model's."""

    source: str


class OpeningCandidateV2(_Node):
    """Every blank stretch offered to perception, ⛔ unclassified."""

    id: str
    face_line: str
    gap_index: int
    span_m: _Pair2F
    len_m: float
    len_px: int
    ink_by_family: dict[str, InkProfileV2]


class ObservationsV2(_Node):
    """What a ruler measured on pixels."""

    calibration: Annotated[
        Any,
        Deferred(
            "chain-fit calibration; not part of the wall/opening families this "
            "version was cut to cover (GLM §五 row 1)"
        ),
    ]
    ink_palette: Annotated[
        Any,
        Deferred(
            "discovered ink families; the role ASSIGNMENT is the deferred "
            "`roles` channel, so its evidence block is deferred with it"
        ),
    ]
    face_lines: list[FaceLineV2]
    components_by_family: Annotated[
        Any,
        Deferred(
            "connected components per discovered family; opening EVIDENCE is "
            "covered through opening_candidates, the raw component dump is not"
        ),
    ]
    dimension_witnesses: Annotated[
        Any,
        Deferred("dimension-chain tick map; the dimensions channel is module 2+"),
    ]


class DeclarationsV2(_Node):
    """What the drawing or its config ASSERTS, transcribed verbatim.

    ⛔ Wholly deferred in this version — GLM's cut is the wall + opening
    families, and every field here is a transcription channel, not a bucket.
    The five keys are still enumerated so a missing or invented channel is
    loud even while their interiors are not typed.
    """

    thickness_callouts_mm: Annotated[
        Any, Deferred("declaration channel; compared by text, out of this cut")
    ]
    thickness_callout_note: Annotated[Any, Deferred("prose note beside the above")]
    world_zero_px_declared: Annotated[
        Any, Deferred("declared origin; calibration channel, out of this cut")
    ]
    chains: Annotated[
        Any, Deferred("declared dimension chains; the dimensions channel is module 2+")
    ]
    drawing_box_px: Annotated[
        Any, Deferred("declared drawing frame; calibration channel, out of this cut")
    ]


#: ⭐ The four perception buckets, named once so nothing has to re-count them.
#: See this module's docstring for why it is four and not five.
PERCEPTION_BUCKET_FIELDS: tuple[str, ...] = (
    "non_wall_face_lines",
    "unpaired_wall_faces",
    "solid_band_walls",
    "ambiguous_face_lines",
)


class HypothesesV2(_Node):
    """Everything derived from the first two layers.  ⛔ Not scored."""

    family_roles: Annotated[
        Any,
        Deferred(
            "the `roles` channel GLM's cut defers explicitly "
            "('ledger/roles 等非墙通道登记 plan.md 缓做')"
        ),
    ]

    # -- opening family ---------------------------------------------------- #
    opening_candidates: list[OpeningCandidateV2]
    opening_candidates_basis: str
    opening_types: dict[str, str] | None
    """⛔ Values stay free ``str``: the opening vocabulary comes from OUTSIDE
    (perception), and hard-coding a closed set in code is how F-69 happened.
    ``None`` is the honest 'perception named nothing'."""
    opening_types_source: str | None

    # -- wall family ------------------------------------------------------- #
    pair_candidates: list[PairCandidateV2]
    pair_candidates_basis: str
    pairs: list[SelectedPairV2] | None
    """``None`` when perception supplied no selection — a LOUD downgrade the
    producer records rather than substituting a code rule."""

    non_wall_face_lines: dict[str, str]
    unpaired_wall_faces: dict[str, str]
    solid_band_walls: dict[str, str]
    ambiguous_face_lines: dict[str, str]

    perception_source: str | None
    pairs_status: Literal[
        "SELECTED", "SELECTED_INCOMPLETE", "ABSENT_NO_MODEL_SELECTION"
    ]
    """⭐ Closed on purpose, unlike ``opening_types``: this vocabulary is the
    producer's OWN (all three values are written by ``select_pairs`` twenty
    lines above the call site), so a fourth value is a producer change that
    must come with a type change."""
    pairs_note: str
    note: str


class AsDrawnPlanV2(BaseModel):
    """The whole three-layer as-drawn plan product.

    ⚠️ ``extra="ignore"`` at the top level is a decision, ⛔ not an oversight.
    ``vector_contract`` discipline #4 requires that a file which is
    *simultaneously* a valid as-drawn product and a valid legacy reading view be
    reported as AMBIGUOUS rather than resolved by declaration order.  A
    top-level ``extra="forbid"`` would make that double match structurally
    impossible and silently demote it to a single verdict — moving an invariant
    this dispatch was not asked to move ([[moving-a-gate-to-a-new-measurement-point]]).
    Every nested node forbids extras, which is where "the bucket's elements do
    not have the right shape" actually lives.
    """

    model_config = ConfigDict(extra="ignore", strict=True, populate_by_name=True)

    schema_value: Literal[SCHEMA] = Field(alias="schema")
    image: str
    image_label: str | None
    observations: ObservationsV2
    declarations: DeclarationsV2
    hypotheses: HypothesesV2
    ledger: Annotated[
        Any,
        Deferred(
            "counts-only self-report; GLM's cut defers it explicitly "
            "('ledger/roles 等非墙通道登记 plan.md 缓做')"
        ),
    ]


# --------------------------------------------------------------------------- #
# API — a gate, ⛔ never a normalizer
# --------------------------------------------------------------------------- #
def _one_line(exc: ValidationError, limit: int = 4) -> str:
    errs = exc.errors()
    shown = "; ".join(
        f"{'/'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in errs[:limit]
    )
    if len(errs) > limit:
        shown += f"; (+{len(errs) - limit} more)"
    return f"{len(errs)} structural error(s): {shown}"


def validate_plan_document(doc: Any) -> None:
    """Raise :class:`AsDrawnPlanContractError` unless ``doc`` IS the product.

    ⭐ Returns ``None`` by design.  A caller that wanted "the validated
    document" would have to reach for ``AsDrawnPlanV2.model_validate`` itself
    and could then serialize the model instead of the product — which is how a
    validator quietly becomes a rewriter.  There is nothing here to serialize.
    """
    try:
        AsDrawnPlanV2.model_validate(doc)
    except ValidationError as exc:
        raise AsDrawnPlanContractError(_one_line(exc)) from exc


def explain_rejection(doc: Any) -> str | None:
    """``None`` when ``doc`` is a valid product, else a one-line reason.

    ⛔ Never raises: its caller is ``vector_contract``, whose discipline #6
    forbids an exception escaping the classifier (the ledger it would destroy
    is the record that names the offender).
    """
    try:
        AsDrawnPlanV2.model_validate(doc)
    except ValidationError as exc:
        return _one_line(exc)
    except Exception as exc:  # noqa: BLE001 - boundary, see docstring
        return f"could not be validated: {type(exc).__name__}: {exc}"
    return None


def _nested_models(annotation: Any) -> list[type[BaseModel]]:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]
    found: list[type[BaseModel]] = []
    for arg in get_args(annotation):
        found.extend(_nested_models(arg))
    return found


def deferred_channels() -> tuple[tuple[str, str], ...]:
    """Every ``(json_pointer, why)`` this version carries WITHOUT validating.

    ⭐ Derived from the models themselves, ⛔ not a hand-maintained list that can
    drift away from the code it claims to describe.
    """
    out: list[tuple[str, str]] = []

    def walk(model: type[BaseModel], prefix: str) -> None:
        for name, field in model.model_fields.items():
            key = field.alias or name
            pointer = f"{prefix}/{key}"
            marks = [m for m in field.metadata if isinstance(m, Deferred)]
            if marks:
                out.append((pointer, marks[0].why))
                continue
            for sub in _nested_models(field.annotation):
                walk(sub, pointer)

    walk(AsDrawnPlanV2, "")
    return tuple(out)
