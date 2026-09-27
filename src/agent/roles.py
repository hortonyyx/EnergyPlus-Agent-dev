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
                         "prefer a plausible inferred use over unknown. Do not suffix types with '_inferred'.")
    return role


def room_types_reference() -> str:
    return ("Choose role from this pinned OpenStudio level-1 catalog (code | 中文 | fixed color). "
            "Prefer a reasonable listed use based on building context, layout and furniture, "
            "even when uncertain; use a broader plausible type with explicit inference. "
            "Precise use identification is low priority for this lightweight BIM and users can revise it later. "
            "Reserve unknown for cases with no defensible listed choice; ambiguity alone is not enough. "
            "No invented roles; keep uncertainty and original "
            "drawing labels in source_refs/assumptions. This does not assign physical properties.\n"
            + CATALOG["source"]["url"] + "\n"
            + "\n".join(f"{r['code']} | {r['label_zh']} | {r['color']}"
                        + (f" | {r['annotation']}" if r["annotation"] else "")
                        for r in CATALOG["types"]))


def room_use_review(source: dict, *, include_next_action: bool = True) -> dict:
    """Report saved use-basis coverage, never certify function interpretation."""
    counts = {basis: 0 for basis in ("observed", "inferred", "unknown")}
    unrecorded = []
    unknown = []
    for space in source.get("spaces", []):
        if space.get("role", "unknown") == "unknown":
            unknown.append(space["id"])
        evidence = space.get("role_evidence")
        if evidence is None:
            unrecorded.append(space["id"])
        else:
            counts[evidence["basis"]] += 1
    result = {
        "source_model_sha256": source.get("source_model_sha256"),
        "summary": {"total_count": len(source.get("spaces", [])),
                    "recorded_count": sum(counts.values()), "unrecorded_count": len(unrecorded),
                    **{basis + "_count": count for basis, count in counts.items()}},
        "unrecorded_space_ids": unrecorded[:20],
        "unrecorded_ids_truncated": len(unrecorded) > 20,
        "unknown_space_ids": unknown[:20],
        "unknown_ids_truncated": len(unknown) > 20,
        "next_action": ("Read room_types and edits, inspect original room interiors, then use "
                        "revise_bim/set_space_role to choose a plausible use, including a reasonable "
                        "inference from building context. Prefer a broad listed type over unknown; "
                        "avoid spending excessive effort distinguishing similar plausible uses. "
                        "Read remaining cells with read_candidate_items; preserve physical partitions."
                        if unrecorded or unknown else "Use-basis records saved; unresolved inferences remain explicit."),
        "interpretation": "Counts cover structured role_evidence only, not semantic correctness. "
                          "Legacy source_refs may contain other evidence. Unknown remains a fallback when "
                          "no defensible listed use fits; it is not a preferred response to ambiguity.",
        "drawing_fidelity": "not_evaluated", "delivery_blocked": False,
    }
    if not include_next_action:
        # Every save reports the same factual coverage. Action guidance belongs
        # to explicit inspection/delivery, without inferring a fixed work phase.
        result.pop("next_action")
    return result
