"""0_reading vector-JSON data model + legacy migration (M1)."""

from __future__ import annotations

from src.agent.reading.legacy import (
    attach_raw_metadata,
    load_reading_view,
    migrate_view,
    parse_value_m,
    reading_raw_metadata,
)
from src.agent.reading.schema import (
    Dimension,
    DimensionRole,
    Facade,
    FacadeOrientation,
    OrientationEvidence,
    ReadingView,
    RoomRoleObservation,
    Stroke,
)

__all__ = [
    "load_reading_view",
    "migrate_view",
    "parse_value_m",
    "attach_raw_metadata",
    "reading_raw_metadata",
    "Dimension",
    "DimensionRole",
    "Facade",
    "FacadeOrientation",
    "OrientationEvidence",
    "ReadingView",
    "RoomRoleObservation",
    "Stroke",
]
