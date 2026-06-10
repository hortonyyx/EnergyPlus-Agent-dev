"""Materialized intermediate geometry for the staged correction pipeline.

correction stage (LLM correction) emits `CorrectedGeometry`; the deterministic core snaps
it; the modeling/MEP stages (LLM modeling) consumes it to produce `IntakeOutput`. Holding this
artifact explicit decouples the stages (swap a model per stage) and makes the
correction checkpoint verifiable and diffable for evaluation.

Geometry is rectangular cells for the current regime (one cell = one room/zone
footprint, world meters). Polygon cells are a future extension; `extra="allow"`
keeps the schema forward-compatible without breaking older artifacts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Cell(BaseModel):
    """One enclosed room footprint on a floor (world meters)."""

    model_config = ConfigDict(extra="allow")
    id: str
    role: str = "office"
    x: list[float]  # [min, max]
    y: list[float]  # [min, max]


class Window(BaseModel):
    """One window, positioned on a facade in world coordinates."""

    model_config = ConfigDict(extra="allow")
    id: str
    floor: str
    facade: str  # North | South | East | West
    span: list[float]  # along-facade world range [min, max] (x for N/S, y for E/W)
    z: list[float]  # [sill, head] world
    room: str | None = None  # cell id this window belongs to


class Floor(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    z_floor: float
    ceiling_height: float
    cells: list[Cell]


class CorrectedGeometry(BaseModel):
    """Corrected, world-frame, centerline geometry primitives — the correction-stage output."""

    model_config = ConfigDict(extra="allow")
    footprint_x: list[float]  # [min, max]
    footprint_y: list[float]  # [min, max]
    floors: list[Floor]
    windows: list[Window] = Field(default_factory=list)
    # Audit (A0 schema, kept as flexible dicts so a stage need not over-specify).
    corrections: list[dict] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    unsupported: list[dict] = Field(default_factory=list)
    notes: str | None = None
