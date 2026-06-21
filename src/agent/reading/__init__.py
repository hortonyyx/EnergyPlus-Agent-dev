"""0_reading vector-JSON data model + legacy migration (M1)."""

from __future__ import annotations

from src.agent.reading.legacy import (
    load_reading_view,
    migrate_view,
    parse_value_m,
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
    "Dimension",
    "DimensionRole",
    "Facade",
    "FacadeOrientation",
    "OrientationEvidence",
    "ReadingView",
    "RoomRoleObservation",
    "Stroke",
]
