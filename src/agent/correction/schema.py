"""Materialized intermediate geometry for the staged correction pipeline.

correction stage (LLM correction) emits `CorrectedGeometry`; the deterministic core snaps
it; the modeling/MEP stages (LLM modeling) consumes it to produce `IntakeOutput`. Holding this
artifact explicit decouples the stages (swap a model per stage) and makes the
correction checkpoint verifiable and diffable for evaluation.

Geometry is rectangular cells in schema v1 (one cell = one room/zone footprint,
world meters). Schema v2 may use orthogonal polygon cells; `x`/`y` remain
required and are the polygon bbox projection.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal, get_args, get_origin

from pydantic import AllowInfNan, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from src.agent.correction.claims import WINDOW_CLAIMS

# F-15 (2026-08-07): marker for fields that are the deterministic core's OWN
# audit trail — computed downstream from a correction draw, never legal input
# TO one. A field carrying this marker in its ``json_schema_extra`` is
# mechanically stripped from the JSON Schema shown to the correction LLM
# prompt (``vocab.producer_facing_json_schema``); validation against the full
# ``CorrectedGeometryV3`` (this module) is completely unaffected — the
# stripping only touches what the model is TOLD it may write, not what the
# core accepts/rejects. ``_producer_preflight``
# (correction/window_sources.py) remains the authoritative, unweakened door:
# a draw that fills a marked field anyway is still hard-rejected.
#
# A field marked this way NEVER gets a value from anywhere but a later,
# non-draw stage (e.g. Vg materializes `facade_segments` at finalize; the
# separate e4_orientation phase resolves `north_axis`) — it stays legitimately
# absent/None all through a draw and its preflight. Contrast with
# CORRECTION_DRAW_DERIVED below, whose fields the SCHEMA ITSELF fills in
# unconditionally the moment validation succeeds.
CORRECTION_DRAW_FORBIDDEN = "correction_draw_forbidden"

# F-16 follow-up (2026-08-08, orchestrator interface sweep §6 摊一 Step 2):
# marker for fields that are ALSO illegal input to a draw, but — unlike
# CORRECTION_DRAW_FORBIDDEN fields — the schema's own validator derives and
# fills them in from other fields of the SAME draw as soon as construction
# succeeds (WindowV3.floor <- by_id[floor_id].name), so by the time any code
# holds a validated instance the field is ALWAYS populated. That makes
# "is it populated?" meaningless as a post-construction preflight check (it
# would fire on every valid instance, derived or not) — the only point where
# "did the MODEL supply a value" is still observable is the raw draw payload,
# before ``model_validate`` ever runs. Kept as a distinct marker (rather than
# reusing CORRECTION_DRAW_FORBIDDEN for both) so that distinction is encoded
# in the schema itself and each consumer can tell, mechanically, which kind
# of field it is holding — not something a caller has to remember per field
# name. Still gets the SAME prompt-schema stripping treatment as
# CORRECTION_DRAW_FORBIDDEN (see ``vocab.producer_facing_json_schema``): the
# model must not see either kind as a fillable field.
CORRECTION_DRAW_DERIVED = "correction_draw_derived"


def _marked_field_names(model_cls: type[BaseModel], marker: str) -> tuple[str, ...]:
    names = []
    for name, field in model_cls.model_fields.items():
        extra = field.json_schema_extra
        if isinstance(extra, dict) and extra.get(marker) is True:
            names.append(name)
    return tuple(sorted(names))


def draw_forbidden_field_names(model_cls: type[BaseModel]) -> tuple[str, ...]:
    """Names of ``model_cls``'s OWN top-level fields marked
    ``CORRECTION_DRAW_FORBIDDEN`` (F-15 follow-up, 2026-08-07 orchestrator
    A3/B1).

    This is the SINGLE source both consumers must agree with — previously
    they each hardcoded their own name list and drifted: the prompt-schema
    stripper (``vocab.producer_facing_json_schema``) already read the marker
    correctly, but ``parse.parse_correction_draw``'s b2-phase draw-contract
    gate independently hardcoded ``facade_segments`` + ``north_axis`` by
    name — so when ``north_axis`` was later found to need the SAME
    protection as ``facade_segments`` (a real run filled it and was
    rejected), only one of the two lists needed updating, and it would have
    been easy to update the wrong one, or only the gate, and quietly
    re-widen the gap. Deriving both from this single function makes that
    class of drift structurally impossible: mark a field once, both
    consumers see it.

    Only inspects ``model_cls.model_fields`` directly (top-level fields of
    the model actually passed in — e.g. ``CorrectedGeometryV3``), NOT nested
    models reached through them (e.g. ``WindowV3.facade_segment_id``, a
    per-window field). Nested list-of-submodel fields (``windows``) are
    covered by the sibling function :func:`nested_draw_forbidden_fields`
    below — kept separate rather than folded into a single recursive walk
    because the two call shapes differ (a container's own fields vs. each
    item of a list field), and unifying them into one generic recursive
    function would either need to guess how deep to descend or risk
    picking up marked fields on unrelated nested models reached through
    other paths (e.g. a future marked field on ``FacadeSegment``, itself
    already gated at the container level via ``facade_segments``).

    Deliberately does NOT also match ``CORRECTION_DRAW_DERIVED`` — the two
    markers' consumers have opposite post-construction semantics (see that
    marker's docstring), and this function's only caller
    (``_producer_preflight``'s top-level check, plus the b2 gate) needs the
    "stays legitimately absent" set specifically.
    """
    return _marked_field_names(model_cls, CORRECTION_DRAW_FORBIDDEN)


def _nested_marked_fields(container_cls: type[BaseModel], marker: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for name, field in container_cls.model_fields.items():
        if get_origin(field.annotation) is not list:
            continue
        args = get_args(field.annotation)
        if len(args) != 1:
            continue
        item_type = args[0]
        if not (isinstance(item_type, type) and issubclass(item_type, BaseModel)):
            continue
        marked = _marked_field_names(item_type, marker)
        if marked:
            result[name] = marked
    return result


def nested_draw_forbidden_fields(container_cls: type[BaseModel]) -> dict[str, tuple[str, ...]]:
    """Map ``container_cls``'s own ``list[<submodel>]`` fields to the
    ``CORRECTION_DRAW_FORBIDDEN``-marked field names declared on each
    submodel (F-16 follow-up, 2026-08-08 orchestrator interface sweep §6).

    Companion to :func:`draw_forbidden_field_names`, one level down: where
    that function answers "which of THIS model's own fields are forbidden",
    this one answers "for each of this model's list-of-submodel fields,
    which of THAT submodel's fields are forbidden". Both read the SAME
    marker (``CORRECTION_DRAW_FORBIDDEN`` in ``json_schema_extra``), so a
    field marked once is picked up by whichever function matches its
    nesting depth — no second, hand-maintained name list at either level.

    This closes a drift that F-15's original fix (marker + top-level
    stripping/gate only) left open: ``WindowV3.facade_segment_id`` carries
    the marker (so the prompt-schema stripper already excludes it, since
    that stripper recurses through ``$defs`` and finds it regardless of
    nesting depth — see ``vocab.producer_facing_json_schema``), but the
    runtime draw-contract gates (``parse.py``'s b2 check,
    ``window_sources.py._producer_preflight``) each independently
    hardcoded the literal field name ``"facade_segment_id"`` instead of
    reading the marker — precisely the two-list drift pattern F-15 was
    meant to eliminate, just one level deeper than F-15 first looked.

    Only descends exactly one level (``list[BaseModel]`` fields whose item
    type itself declares at least one marked field); a submodel with no
    marked fields is simply absent from the returned mapping. Deliberately
    does not recurse further (e.g. into a list field's own nested list
    fields) — no current schema needs that depth, and guessing at it would
    risk snagging on unrelated future nesting.

    Intentionally excludes ``CORRECTION_DRAW_DERIVED``-marked fields (e.g.
    ``WindowV3.floor``) — see :func:`nested_draw_derived_fields` and that
    marker's docstring for why a post-construction "is it populated?" check
    (which is how ``_producer_preflight`` uses this function's result) would
    be meaningless, not merely redundant, for a field the schema itself
    always fills in.
    """
    return _nested_marked_fields(container_cls, CORRECTION_DRAW_FORBIDDEN)


def nested_draw_derived_fields(container_cls: type[BaseModel]) -> dict[str, tuple[str, ...]]:
    """Map ``container_cls``'s own ``list[<submodel>]`` fields to the
    ``CORRECTION_DRAW_DERIVED``-marked field names declared on each submodel
    (F-16, 2026-08-08 orchestrator interface sweep §6 摊一 Step 2).

    Same shape as :func:`nested_draw_forbidden_fields`, different marker.
    The split matters at the call site: this set is only safe to check
    against the RAW draw payload dict, before ``model_validate`` runs (see
    ``parse.parse_correction_draw``'s b2 gate) — a validated instance's
    fields of this kind are unconditionally populated by the model's own
    ``model_validator``, so "is it None?" can never distinguish a model-drawn
    value from a derived one after the fact.
    """
    return _nested_marked_fields(container_cls, CORRECTION_DRAW_DERIVED)


from src.agent.correction.constants import SCHEMA_VERSION_V1

# Case-insensitive aliases the facade validator accepts; anything else (e.g.
# "Northeast", a typo) is rejected so the geometry stages never silently treat
# an unknown facade as North/South.
_FACADE_ALIASES = {
    "north": "North", "n": "North",
    "south": "South", "s": "South",
    "east": "East", "e": "East",
    "west": "West", "w": "West",
}


class Cell(BaseModel):
    """One enclosed room footprint on a floor (world meters)."""

    model_config = ConfigDict(extra="allow")
    id: str
    role: str = "office"
    x: list[float]  # [min, max]
    y: list[float]  # [min, max]
    polygon: list[list[float]] | None = None  # exterior ring, CCW, not closed


class Window(BaseModel):
    """One window, positioned on a facade in world coordinates."""

    model_config = ConfigDict(extra="allow")
    id: str
    floor: str
    facade: Literal["North", "South", "East", "West"]
    span: list[float]  # along-facade world range [min, max] (x for N/S, y for E/W)
    z: list[float]  # [sill, head] world
    room: str | None = None  # cell id this window belongs to

    @field_validator("facade", mode="before")
    @classmethod
    def _normalize_facade(cls, v):
        if isinstance(v, str):
            return _FACADE_ALIASES.get(v.strip().lower(), v)
        return v


class Floor(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    z_floor: float
    ceiling_height: float
    cells: list[Cell]


class CorrectedGeometry(BaseModel):
    """Corrected, world-frame, centerline geometry primitives — the correction-stage output."""

    model_config = ConfigDict(extra="allow")
    schema_version: str = SCHEMA_VERSION_V1
    footprint_x: list[float]  # [min, max]
    footprint_y: list[float]  # [min, max]
    floors: list[Floor]
    windows: list[Window] = Field(default_factory=list)
    # Audit (A0 schema, kept as flexible dicts so a stage need not over-specify).
    corrections: list[dict] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    unsupported: list[dict] = Field(default_factory=list)
    notes: str | None = None


# V3 is deliberately a strict subclass family.  The legacy classes above must
# remain wire-identical: historical V1/V2 artifacts retain their permissive
# extra fields and their existing serializer bytes.
FiniteFloat = Annotated[float, AllowInfNan(False)]
Hex64 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Point2 = tuple[FiniteFloat, FiniteFloat]


class FootprintRing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vertices: list[Point2] = Field(min_length=4)


class WorldInterval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lo: FiniteFloat
    hi: FiniteFloat

    @model_validator(mode="after")
    def _ordered(self):
        if self.lo >= self.hi:
            raise ValueError("world interval requires lo < hi")
        return self


class KnowledgeRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str
    dataset_version: str
    entry_id: str
    candidate_id: str
    content_sha256: Hex64


class FieldProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provenance: Literal["observed", "derived", "assumed"]
    source_ids: list[str] = Field(default_factory=list)
    method: str | None = None
    knowledge_ref: KnowledgeRef | None = None


class FacadeSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    floor_id: str
    facade_family: Literal["North", "South", "East", "West"]
    p1: Point2
    p2: Point2
    outward_normal: tuple[Literal[-1, 0, 1], Literal[-1, 0, 1]]
    world_along_interval: WorldInterval
    depth: Annotated[FiniteFloat, Field(ge=0)]
    visible_intervals: list[WorldInterval] = Field(default_factory=list)
    source_footprint_fingerprint: Hex64

    @model_validator(mode="after")
    def _valid_segment(self):
        (x1, y1), (x2, y2) = self.p1, self.p2
        nx, ny = self.outward_normal
        if (x1, y1) == (x2, y2) or (x1 != x2 and y1 != y2):
            raise ValueError("facade segment must be non-zero and axis-aligned")
        if abs(nx) + abs(ny) != 1 or (x1 != x2 and nx != 0) or (y1 != y2 and ny != 0):
            raise ValueError("facade segment normal must be unit and perpendicular")
        expected = {"North": (0, 1), "South": (0, -1), "East": (1, 0), "West": (-1, 0)}
        if (nx, ny) != expected[self.facade_family]:
            raise ValueError("facade segment normal disagrees with facade_family")
        span = sorted((x1, x2) if y1 == y2 else (y1, y2))
        if (self.world_along_interval.lo, self.world_along_interval.hi) != tuple(span):
            raise ValueError("world_along_interval must equal segment projection")
        prev = None
        for interval in self.visible_intervals:
            if interval.lo < self.world_along_interval.lo or interval.hi > self.world_along_interval.hi:
                raise ValueError("visible interval lies outside segment")
            if prev is not None and interval.lo < prev:
                raise ValueError("visible intervals must be sorted and disjoint")
            prev = interval.hi
        return self


class NorthAxisEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value_deg: FiniteFloat
    provenance: Literal["observed", "derived", "assumed"]
    source_ids: list[str] = Field(default_factory=list)
    uncertainty_deg: Annotated[FiniteFloat, Field(ge=0)] | None = None
    method: str | None = None
    frame_transform_hash: Hex64 | None = None

    @model_validator(mode="after")
    def _axis(self):
        object.__setattr__(self, "value_deg", self.value_deg % 360)
        if self.provenance == "observed" and not self.source_ids:
            raise ValueError("observed north axis requires source_ids")
        return self


class CellV3(Cell):
    model_config = ConfigDict(extra="forbid")


class FloorV3(Floor):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(frozen=True)
    footprint: FootprintRing
    cells: list[CellV3] = Field(min_length=1)


class WindowV3(Window):
    model_config = ConfigDict(extra="forbid")
    floor_id: str
    # F-16 (2026-08-08, orchestrator interface sweep §6 摊一 Step 2): base
    # `Window.floor` (str, required) is a v1/v2 leftover — v1 has no
    # `floor_id` at all, so `floor` (a name string) is its ONLY floor
    # reference and must stay exactly as-is there (untouched: this override
    # lives on WindowV3 only, base `Window`/`CorrectedGeometry` are
    # unaffected). On v3, `floor_id` is the authoritative reference and
    # `floor` becomes a pure, optional, DERIVED display echo of
    # `by_id[floor_id].name` (see `CorrectedGeometryV3._v3_integrity` below)
    # — the model no longer supplies it at all, closing off the "two
    # independent declarations of the same fact" shape that produced F-16
    # (`floors[0].id="F1"` / `name="Level 1"`, window's `floor="F1"` written
    # against the id instead of the name the old required-field contract
    # wanted). Marked CORRECTION_DRAW_DERIVED, not CORRECTION_DRAW_FORBIDDEN
    # — see that marker's docstring for why the two need to stay distinct.
    floor: str | None = Field(
        default=None, json_schema_extra={CORRECTION_DRAW_DERIVED: True}
    )
    facade_segment_id: str | None = Field(
        default=None, json_schema_extra={CORRECTION_DRAW_FORBIDDEN: True}
    )
    provenance: dict[str, FieldProvenance] | None = None

    @field_validator("provenance")
    @classmethod
    def _claims_vocab(cls, value):
        if value is not None and not set(value).issubset(WINDOW_CLAIMS):
            raise ValueError("window provenance keys must be opening-claim vocabulary")
        return value


class DebtResolutionAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["debt_resolution"]
    resolves_debt_id: Hex64
    rationale: str
    source: Literal["llm_correction", "a3"]


class CorrectedGeometryV3(CorrectedGeometry):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["3"]
    floors: list[FloorV3] = Field(min_length=1)
    windows: list[WindowV3] = Field(default_factory=list)
    facade_segments: list[FacadeSegment] = Field(
        default_factory=list, json_schema_extra={CORRECTION_DRAW_FORBIDDEN: True}
    )
    # F-15 follow-up (2026-08-07, orchestrator A3): `north_axis` is exactly
    # the same shape of core-only field as `facade_segments` — under the b2
    # (draw) phase_contract it must ALWAYS stay unpopulated (see
    # feature_state.derive_feature_state_claims: a b2-phase v3 draw is
    # unconditionally `typed_north_axis="declared_unpopulated"`; only the
    # SEPARATE, non-LLM `e4_orientation` enrichment phase — a different call
    # site entirely, orientation.py, never a draw prompt — is allowed to
    # populate it). It was NOT marked in the original F-15 fix (facade_segments
    # / facade_segment_id only), so the b2 draw contract gate in parse.py kept
    # a second, independently-hardcoded name list — exactly the drift this
    # marker is meant to prevent. Now marked, so both the prompt-stripper
    # (vocab.producer_facing_json_schema) AND the runtime gate
    # (parse.parse_correction_draw's b2 check, via
    # schema.draw_forbidden_field_names) read the SAME single source.
    north_axis: NorthAxisEvidence | None = Field(
        default=None, json_schema_extra={CORRECTION_DRAW_FORBIDDEN: True}
    )

    @model_validator(mode="after")
    def _v3_integrity(self):
        ids = [fl.id for fl in self.floors]
        if any(not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("v3 floor ids must be non-empty and globally unique")
        by_id = {fl.id: fl for fl in self.floors}
        for win in self.windows:
            floor = by_id.get(win.floor_id)
            if floor is None:
                raise ValueError(f"window {win.id}: unknown floor_id {win.floor_id}")
            # F-16 (2026-08-08, §6 摊一 Step 2): `floor` is derived from
            # `floor_id`, not model input (see WindowV3.floor above) — the
            # PRIMARY door rejecting a draw that supplied it is
            # parse.parse_correction_draw's raw-payload b2 gate (typed
            # WindowResolverInputError, category=model_draw_error, so a
            # rejection carries retry guidance — see that gate's comment for
            # why this pydantic-level check must NOT be the primary one: by
            # the time a WindowV3 instance exists, any exception raised here
            # is a plain ValueError wrapped into pydantic's ValidationError,
            # which is exactly the F-15-shaped mistake this project already
            # paid for once — bare ValidationError never reaches the
            # model_draw_error retry-guidance channel). This branch is the
            # schema's OWN, unconditional invariant enforcement — it runs
            # regardless of which door (if any) a caller went through, so a
            # value that already agrees with the derivation (e.g. a v1->v3
            # round-trip that copied it forward correctly) is accepted
            # as-is; only a genuine mismatch is rejected here, as a
            # defense-in-depth backstop for callers that construct
            # `CorrectedGeometryV3` directly instead of going through
            # `parse_correction_draw`.
            if win.floor is None:
                win.floor = floor.name
            elif win.floor != floor.name:
                raise ValueError(f"window {win.id}: floor must match referenced floor name")
        segment_ids = {seg.id for seg in self.facade_segments}
        if len(segment_ids) != len(self.facade_segments):
            raise ValueError("facade segment ids must be globally unique")
        for seg in self.facade_segments:
            floor = by_id.get(seg.floor_id)
            if floor is None:
                raise ValueError(f"facade segment {seg.id}: unknown floor_id")
            from src.agent.correction.footprint import floor_footprint_fingerprint
            if seg.source_footprint_fingerprint != floor_footprint_fingerprint(self, floor):
                raise ValueError(
                    f"facade segment {seg.id}: source_footprint_fingerprint does not match floor footprint"
                )
        for win in self.windows:
            if win.facade_segment_id is not None and win.facade_segment_id not in segment_ids:
                raise ValueError(f"window {win.id}: unknown facade_segment_id")
        # B2 permits different encodings during draw (core canonicalizes them),
        # but every floor must describe the same geometric footprint domain.
        def fingerprint(floor):
            pts = [(float(x), float(y)) for x, y in floor.footprint.vertices]
            if pts[0] == pts[-1]:
                pts.pop()
            forward = min(tuple(pts[i:] + pts[:i]) for i in range(len(pts)))
            rev = list(reversed(pts))
            backward = min(tuple(rev[i:] + rev[:i]) for i in range(len(rev)))
            return min(forward, backward)
        if len({fingerprint(floor) for floor in self.floors}) != 1:
            raise ValueError("v3 per-floor footprints must have identical geometry")
        for row in [*self.corrections, *self.conflicts, *self.unsupported]:
            if isinstance(row, dict) and row.get("kind") == "debt_resolution":
                DebtResolutionAuditEntry.model_validate(row)
            if isinstance(row, dict) and row.get("kind") == "window_host_resolution":
                # Local import avoids a schema -> source-wire import cycle while
                # registering the B5 strict accepted-audit shape for v3 only.
                from src.agent.correction.window_host import WindowHostResolutionAuditV1
                WindowHostResolutionAuditV1.model_validate_json(
                    json.dumps(row, separators=(",", ":"), ensure_ascii=False),
                )
        return self
