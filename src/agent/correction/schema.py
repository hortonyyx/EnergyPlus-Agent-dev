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

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
