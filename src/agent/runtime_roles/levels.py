"""Apply explicitly cited elevation levels to a copy of a reader plan."""

from __future__ import annotations

import copy
import json
import math


def apply_levels(registry, plan, *, z_floor=None, z_floor_evidence=None,
                 ceiling_height=None, ceiling_height_evidence=None):
    updated, citations = copy.deepcopy(plan), {}
    for field, value, reference in (("z_floor", z_floor, z_floor_evidence),
                                     ("ceiling_height", ceiling_height, ceiling_height_evidence)):
        if value is None and reference is None:
            continue
        if (isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value)
                or not isinstance(reference, dict) or set(reference) != {"task_id", "elevation_id"}):
            raise ValueError(f"{field} needs finite metres and {field}_evidence with task_id + elevation_id")
        artifact = registry.read(reference["task_id"], role_id="elevation_reader")
        level = next((row for row in artifact["elevations"] if row["id"] == reference["elevation_id"]), None)
        if level is None:
            raise ValueError(f"{field}_evidence refers to an unknown elevation_id")
        if field == "z_floor" and level.get("floor_id") not in (None, plan["floor_id"]):
            raise ValueError(f"{field}_evidence belongs to a different floor")
        expected = level["value_m"] if field == "z_floor" else level["value_m"] - updated["z_floor"]
        if not math.isclose(value, expected, rel_tol=0, abs_tol=1e-8):
            raise ValueError(f"{field}={value} disagrees with cited absolute level; expected {expected} m "
                             "(ceiling_height = cited top Z minus floor Z)")
        if field == "ceiling_height" and value <= 0:
            raise ValueError("ceiling_height must be positive")
        citations[field] = {**reference, "value_m": value, "previous_value_m": plan[field],
            "artifact_sha256": registry.records[reference["task_id"]]["artifact"]["sha256"],
            "image": artifact["image"], "level": copy.deepcopy(level)}
        updated[field] = value
    if citations:
        # Basis survives in compilation metadata; the assumptions/evidence list
        # also travels into the source candidate, including later assemblies.
        # This resolution explicitly supersedes, not erases, the reader guess.
        resolved = "Role elevation levels override plan assumptions: " + json.dumps(
            citations, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        updated["basis"] = updated.get("basis", "") + "\n" + resolved
        updated.setdefault("assumptions", []).append(resolved)
    return updated, citations
