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
from typing import Annotated, Literal

from pydantic import AllowInfNan, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from src.agent.correction.claims import WINDOW_CLAIMS
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
    facade_segment_id: str | None = None
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
    facade_segments: list[FacadeSegment] = Field(default_factory=list)
    north_axis: NorthAxisEvidence | None = None

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
            if win.floor != floor.name:
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
