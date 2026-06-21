"""Shared room-role vocabulary for reading observations and downstream guards."""

from __future__ import annotations

import re

CANONICAL_ROLES = frozenset(
    {
        "unknown",
        "office",
        "corridor",
        "meeting",
        "conference",
        "lobby",
        "restroom",
        "toilet",
        "stair",
        "storage",
        "service",
        "kitchen",
        "breakroom",
        "mechanical",
        "electrical",
    }
)

ALIASES = {
    "meeting room": "meeting",
    "conference room": "conference",
    "entrance lobby": "lobby",
    "entry lobby": "lobby",
    "rest room": "restroom",
    "bathroom": "restroom",
    "wc": "toilet",
    "stairs": "stair",
    "stairwell": "stair",
    "break room": "breakroom",
    "pantry": "kitchen",
    "mechanical room": "mechanical",
    "electrical room": "electrical",
}

_SPACE_RE = re.compile(r"\s+")


def normalize(label: str | None) -> str:
    """Return the canonical role for a known label/alias, or a normalized label."""
    if label is None:
        return ""
    text = str(label).strip().lower().replace("_", " ").replace("-", " ")
    text = _SPACE_RE.sub(" ", text)
    return ALIASES.get(text, text)
