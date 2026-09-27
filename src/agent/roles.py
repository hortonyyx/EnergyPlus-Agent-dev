"""Pinned OpenStudio classification and project presentation data; no physics."""
from __future__ import annotations

import json
import re
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name("data") / "room_types.json"
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
ROOM_TYPES = {row["code"]: row for row in CATALOG["types"]}
CANONICAL_ROLES = frozenset(ROOM_TYPES)
ALIASES = CATALOG["aliases"]


def _key(label: str) -> str:
    return re.sub(r"[\s_/-]+", " ", label.strip().lower())


_LOOKUP = {_key(code): code for code in ROOM_TYPES}
_LOOKUP.update({_key(alias): code for alias, code in ALIASES.items()})
_LOOKUP.update({_key(row["label_zh"]): code for code, row in ROOM_TYPES.items()})


def normalize(label: str | None) -> str:
    """Resolve catalog names/known historical aliases; retain unknown text."""
    text = _key(str(label or ""))
    return _LOOKUP.get(text, text)


def require_role(label: str | None) -> str:
    """Reject invented types; an absent declaration is explicitly unknown."""
    role = normalize(label) or "unknown"
    if role not in ROOM_TYPES:
        raise ValueError(f"room role {label!r} is not in the room_types catalog; "
                         "read get_bim_reference('room_types') and choose a listed code, "
                         "or 'unknown' with evidence/assumptions. Do not suffix types with '_inferred'.")
    return role


def room_types_reference() -> str:
    return ("Choose role from this pinned OpenStudio level-1 catalog (code | 中文 | fixed color). "
            "unknown is a project sentinel. No invented roles; keep uncertainty and original "
            "drawing labels in source_refs/assumptions. This does not assign physical properties.\n"
            + CATALOG["source"]["url"] + "\n"
            + "\n".join(f"{r['code']} | {r['label_zh']} | {r['color']}"
                        + (f" | {r['annotation']}" if r["annotation"] else "")
                        for r in CATALOG["types"]))
