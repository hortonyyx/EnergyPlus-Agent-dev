"""Checks attached to a reader's immutable trial, never to the single-model path."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping


CONTINUOUS_HINT = "one continuous space rather than a wall with an opening"
COLLECTIONS = ("partitions", "space_seeds", "openings")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def box(value, image_size=None):
    if (not isinstance(value, list) or len(value) != 4
            or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in value)
            or value[0] < 0 or value[1] < 0 or value[2] <= value[0] or value[3] <= value[1]):
        raise ValueError("bbox needs original-image [left,top,right,bottom]. Minimum correct example: [0,0,10,10]")
    if image_size and (value[2] > image_size[0] or value[3] > image_size[1]):
        raise ValueError(f"bbox exceeds original image {image_size}. Minimum correct example: [0,0,10,10]")
    return value


def plan_changes(before, after):
    """Compare by stable object ID; no fuzzy matching that can hide lost objects."""
    result = []
    for key in sorted((set(before) | set(after)) - set(COLLECTIONS)):
        if before.get(key) != after.get(key):
            result.append({"item": "plan." + key, "before": before.get(key), "after": after.get(key)})
    for key in COLLECTIONS:
        old_rows, new_rows = before.get(key, []), after.get(key, [])
        if not isinstance(old_rows, list) or not isinstance(new_rows, list):
            if old_rows != new_rows:
                result.append({"item": "plan." + key, "before": old_rows, "after": new_rows})
            continue
        def stable(rows):
            return (all(isinstance(row, Mapping) and isinstance(row.get("id"), str) and row["id"] for row in rows)
                    and len({row["id"] for row in rows}) == len(rows))
        if not stable(old_rows) or not stable(new_rows):
            # A failed malformed draft has no stable IDs yet. Keep its exact
            # index-addressable differences so fixing that format cannot hide
            # unrelated changes or strand the reader behind a KeyError.
            for index in range(max(len(old_rows), len(new_rows))):
                old = old_rows[index] if index < len(old_rows) else None
                new = new_rows[index] if index < len(new_rows) else None
                if old != new:
                    result.append({"item": f"plan.{key}[{index}]", "before": old, "after": new})
            continue
        old = {row["id"]: row for row in old_rows}
        new = {row["id"]: row for row in new_rows}
        for identity in sorted(set(old) | set(new)):
            if old.get(identity) != new.get(identity):
                result.append({"item": f"plan.{key}:{identity}", "before": old.get(identity), "after": new.get(identity)})
    return result


def review_changes(before, after, declarations, *, image_size=None, allowed_targets=None):
    changes = plan_changes(before, after)
    declared = {}
    if not isinstance(declarations, list):
        raise ValueError("changes must be a list of {item, reason, bbox}")
    for row in declarations:
        if not isinstance(row, Mapping) or set(row) != {"item", "reason", "bbox"}:
            raise ValueError("each change needs item, reason and bbox. Minimum correct example: "
                             '{"item":"plan.openings:D1","reason":"correct flagged endpoint","bbox":[0,0,10,10]}')
        if not isinstance(row["reason"], str) or not row["reason"].strip():
            raise ValueError("each change needs a specific drawing/check issue in reason")
        box(row["bbox"], image_size)
        if row["item"] in declared:
            raise ValueError("duplicate change item: " + row["item"])
        declared[row["item"]] = row
    actual = {row["item"] for row in changes}
    if actual != set(declared):
        raise ValueError("Rework must list exactly the changed items before trial; unrelated objects stay fixed. "
                         + json.dumps({"undeclared_changes": sorted(actual - set(declared)),
                                       "listed_but_unchanged": sorted(set(declared) - actual)}, ensure_ascii=False))
    if allowed_targets is not None and not actual <= set(allowed_targets):
        raise ValueError("Rework changed items outside the coordinator's pointed issues: "
                         + ", ".join(sorted(actual - set(allowed_targets))))
    return [{**row, "reason": declared[row["item"]]["reason"], "bbox": declared[row["item"]]["bbox"]}
            for row in changes]


def topology_issues(receipts):
    """Include earlier warnings: deleting a bad wall cannot erase its review duty."""
    found = {}
    for receipt in receipts:
        report = receipt.get("drawing_differences", {})
        for row in report.get("items", []) if isinstance(report, Mapping) else []:
            kind = row.get("type", row.get("kind"))
            if kind != "unsupported_open_separator" and not (
                    kind == "opening_offset_from_gap" and CONTINUOUS_HINT in row.get("check", "")):
                continue
            identity = {key: row[key] for key in ("type", "kind", "divider", "opening", "gap",
                        "x_px", "y_px") if key in row}
            issue_id = "topology-" + _digest(identity)[:16]
            found.setdefault(issue_id, {"issue_id": issue_id, "plan_sha256": receipt["plan_sha256"], **row,
                "divider_points": receipt.get("topology_dividers", {}).get(row.get("divider"))})
    return list(found.values())


def _segments(plan):
    ring = plan["footprint_pixels"]
    for index, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        yield f"footprint:{index}", a, b
    for row in plan.get("partitions", []):
        for a, b in zip(row["points"], row["points"][1:]):
            yield row["id"], a, b


def opening_hosts(plan):
    """Verify both input endpoints share a declared wall; never move them to pass."""
    result = []
    segments = list(_segments(plan))
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    groups = {}
    for identity, a, b in segments:
        groups.setdefault(identity, []).append(LineString([a, b]))
    footprint = unary_union([line for identity, lines in groups.items() if identity.startswith("footprint:") for line in lines])
    for row in plan.get("openings", []):
        opening = LineString([row["p1"], row["p2"]])
        hosts = sorted(identity for identity, lines in groups.items()
                       if opening.length > 1e-6 and opening.difference(unary_union(lines)).length <= 1e-6)
        if not any(identity.startswith("footprint:") for identity in hosts) and opening.length > 1e-6:
            if opening.difference(footprint).length <= 1e-6:
                hosts.append("footprint")
        if len(hosts) != 1:
            raise ValueError(f"plan.openings:{row['id']}: both endpoints must lie on one declared wall line; "
                             f"found {hosts}. Correct the pointed endpoints/wall and trial again; no automatic snapping.")
        result.append({"id": row["id"], "wall": hosts[0], "p1": row["p1"], "p2": row["p2"]})
    return result


def validate_wall_reference(value, *, image_size=None):
    allowed = {"centerline", "inner_face", "outer_face", "explicit_face"}
    if not isinstance(value, Mapping) or set(value) != {"convention", "dimension_basis", "basis", "bbox"}:
        raise ValueError('wall_reference needs convention, dimension_basis, basis and bbox. Minimum correct example: '
                         '{"convention":"centerline","dimension_basis":"centerline",'
                         '"basis":"dimensions converted to the same representative wall line","bbox":[0,0,10,10]}')
    if value["convention"] not in allowed or value["dimension_basis"] != value["convention"]:
        raise ValueError("All floor walls and dimension anchors must use the same declared wall-reference convention")
    if not isinstance(value["basis"], str) or not value["basis"].strip():
        raise ValueError("wall_reference.basis must explain the drawn dimension chain and any face-to-line conversion")
    box(value["bbox"], image_size)
    return dict(value)


def validate_topology(issues, decisions, plan, *, image_size=None):
    if not isinstance(decisions, list):
        raise ValueError("topology_decisions must be a list")
    by_id = {row["issue_id"]: row for row in issues}
    supplied = {}
    openings = {row["id"]: row for row in plan.get("openings", [])}
    for row in decisions:
        if not isinstance(row, Mapping) or set(row) != {"issue_id", "decision", "basis", "bbox"}:
            raise ValueError('topology_decisions item needs issue_id, decision, basis, bbox. Minimum correct example: '
                             '{"issue_id":"topology-...","decision":"retain_opening","basis":"same physical wall on both sides","bbox":[0,0,10,10]}')
        identity = row["issue_id"]
        if identity not in by_id or identity in supplied:
            raise ValueError("unknown or duplicate topology issue_id: " + str(identity))
        if not isinstance(row["basis"], str) or not row["basis"].strip():
            raise ValueError("topology decision needs a drawing-based explanation of whether both sides are the same wall")
        box(row["bbox"], image_size)
        issue = by_id[identity]
        look = issue.get("look_box")
        if look and (row["bbox"][2] <= look[0] or row["bbox"][0] >= look[2]
                     or row["bbox"][3] <= look[1] or row["bbox"][1] >= look[3]):
            raise ValueError("topology evidence bbox must overlap the flagged local image region")
        if row["decision"] == "retain_opening":
            if issue.get("opening") not in openings:
                raise ValueError("retain_opening requires the flagged opening in the submitted trial")
            opening = openings[issue["opening"]]
            from shapely.geometry import LineString, box as region_box
            from shapely.ops import unary_union
            line = LineString([opening["p1"], opening["p2"]])
            hosts = [LineString([a, b]) for identity, a, b in _segments(plan) if identity == issue.get("divider")]
            if (not hosts or line.difference(unary_union(hosts)).length > 1e-6
                    or (look and not line.intersects(region_box(*look)))):
                raise ValueError("retain_opening must retain the flagged opening on its flagged divider in the local gap region")
        elif row["decision"] == "continuous_space":
            if issue.get("opening") in openings:
                raise ValueError("continuous_space requires removing the flagged opening as well as the artificial wall")
            region = issue.get("gap", issue)
            xp, yp = region.get("x_px"), region.get("y_px")
            if isinstance(xp, list) and isinstance(yp, (float, int)):
                start, end = [xp[0], yp], [xp[1], yp]
            elif isinstance(yp, list) and isinstance(xp, (float, int)):
                start, end = [xp, yp[0]], [xp, yp[1]]
            else:
                raise ValueError("topology issue has no checkable gap coordinates")
            from shapely.geometry import LineString
            gap = LineString([start, end])
            # Difference reports round pixels. Reuse the exact declared wall
            # coordinate when available so a fractional pixel cannot evade the check.
            original = issue.get("divider_points")
            if original:
                for a, b in zip(original, original[1:]):
                    if start[0] == end[0] and a[0] == b[0] and abs(a[0] - start[0]) <= .51:
                        gap = LineString([[a[0], start[1]], [a[0], end[1]]])
                    elif start[1] == end[1] and a[1] == b[1] and abs(a[1] - start[1]) <= .51:
                        gap = LineString([[start[0], a[1]], [end[0], a[1]]])
            for segment_id, a, b in _segments(plan):
                line = LineString([a, b])
                # Renaming and shifting a separator within this local corridor
                # does not implement a continuous-space decision either.
                if look:
                    if start[0] == end[0] and a[0] == b[0] and look[0] <= a[0] <= look[2]:
                        overlap = max(0, min(max(a[1], b[1]), max(start[1], end[1]))
                                      - max(min(a[1], b[1]), min(start[1], end[1])))
                    elif start[1] == end[1] and a[1] == b[1] and look[1] <= a[1] <= look[3]:
                        overlap = max(0, min(max(a[0], b[0]), max(start[0], end[0]))
                                      - max(min(a[0], b[0]), min(start[0], end[0])))
                    else:
                        overlap = 0
                    if overlap >= .85 * gap.length:
                        raise ValueError("continuous_space still has a declared wall spanning the flagged local gap")
                if segment_id == issue.get("divider"):
                    if original:
                        moved = line.difference(LineString(original)).length > 1e-6
                    else:
                        # Legacy warnings have only the flagged straight line.
                        moved = (abs(a[0] - start[0]) > 1e-6 or abs(b[0] - start[0]) > 1e-6
                                 if start[0] == end[0] else
                                 abs(a[1] - start[1]) > 1e-6 or abs(b[1] - start[1]) > 1e-6)
                    if moved:
                        raise ValueError("continuous_space requires removing the flagged wall segment, not moving its divider")
                if gap.intersection(line).length > 1e-6:
                    raise ValueError("continuous_space still has a declared wall crossing the inkless gap")
        else:
            raise ValueError("decision must be retain_opening or continuous_space")
        supplied[identity] = dict(row)
    if set(by_id) != set(supplied):
        raise ValueError("Every topology warning needs a located retain_opening/continuous_space decision; missing: "
                         + ", ".join(sorted(set(by_id) - set(supplied))))
    return list(supplied.values())
