"""S0 — 0_reading deterministic structure linter (M2a, gate ①).

Per contracts §1 0_reading and the pen library, this is a *per-image* linter: it
asks only "is this one drawing structurally well-formed and self-consistent",
never topology / cross-image / world placement (those belong to 1_correction).

Layers (§0.2):
  - INVARIANT (block): unique stroke/dimension ids, legal pen × kind for the
    image_kind, finite numerics, non-degenerate line/rect, parseable dimensions,
    axis-endpoint consistency, image-local facade fields present on elevations,
    uncaptured present as a list (NOT required non-empty — clean drawing → []).
  - CROSS_CHECK (flag): single-image dimension-chain closure (Σ segments ==
    overall), low-confidence internal stroke↔dimension consistency, out-of-bounds.

Returns a :class:`CheckReport`; policy (block vs flag) is applied by the report.
"""

from __future__ import annotations

import math

from src.agent.reading.legacy import parse_value_m
from src.agent.reading.schema import ReadingView
from src.agent.roles import CANONICAL_ROLES, normalize
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus

# Legal pen sets by image kind (pen_library.md §2).
_PLAN_PENS = {"wall", "window"}
_ELEVATION_PENS = {"wall_fill", "window", "outline"}
_GEOMETRY_KINDS = {"line", "rect", "polyline"}
# Topology / world fields a reading stroke must NOT carry (those are 1_correction's).
_FORBIDDEN_STROKE_KEYS = {
    "zone",
    "adjacent_zone",
    "adjacent_surface",
    "obc",
    "world_z",
    "is_exterior",
    "parent_wall_id",
    "parent_window_ids",
    "rooms",
}
_ROOM_LABEL_BASES = {"label", "furniture", "ocr"}
_MIN_EXTENT = 0.05  # m — below this a line/rect is degenerate
_OUTPUT_PRECISION_M = 0.01  # A0 OUTPUT_PRECISION / DIMCHAIN_CLOSE_TOL scale
_PROVENANCE_PENS = {"wall", "window", "wall_fill", "outline"}


def _finite(*vals) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals)


def _legal_pens(image_kind: str) -> set[str] | None:
    k = (image_kind or "").lower()
    if k == "plan":
        return _PLAN_PENS
    if k == "elevation":
        return _ELEVATION_PENS
    return None  # section/supplementary/other: pen set not constrained here


def _uncaptured_list(view: ReadingView) -> list | None:
    """Effective uncaptured entries, pooled across the canonical top-level
    ``uncaptured`` and the tolerated legacy carriers (top-level
    ``uncaptured_visual_elements`` extra, and the old nested
    ``self_check.uncaptured_visual_elements``). Returns ``None`` only when no
    carrier is present as a list at all."""
    found = False
    pooled: list = []
    if isinstance(view.uncaptured, list):
        found = True
        pooled.extend(view.uncaptured)
    extra = getattr(view, "__pydantic_extra__", None) or {}
    legacy = extra.get("uncaptured_visual_elements")
    if isinstance(legacy, list):
        found = True
        pooled.extend(legacy)
    if isinstance(view.self_check, dict):
        nested = view.self_check.get("uncaptured_visual_elements")
        if isinstance(nested, list):
            found = True
            pooled.extend(nested)
    return pooled if found else None


def check_reading_view(
    view: ReadingView, *, capability_profile: str = "rectangular"
) -> CheckReport:
    rep = CheckReport(stage="0_reading", capability_profile=capability_profile)

    # ---- INVARIANT: unique ids ----
    _unique_ids(rep, "stroke", [s.id for s in view.strokes])
    _unique_ids(rep, "dimension", [d.id for d in view.dimensions])

    # ---- INVARIANT: legal pen × kind ----
    _pen_kind(rep, view)

    # ---- INVARIANT: no topology/world fields on strokes ----
    _no_topology_fields(rep, view)

    # ---- INVARIANT: finite + non-degenerate geometry ----
    _geometry_wellformed(rep, view)

    # ---- INVARIANT: dimensions parseable + axis-endpoint consistent ----
    _dimensions_wellformed(rep, view)

    # ---- INVARIANT: elevation facade image-local fields present ----
    _facade_fields(rep, view)

    # ---- INVARIANT: uncaptured present as a list (not required non-empty) ----
    unc = _uncaptured_list(view)
    if unc is None:
        rep.add_fail(
            "reading.uncaptured_present", CheckLayer.INVARIANT,
            "uncaptured field missing or not a list",
        )
    else:
        rep.add_pass("reading.uncaptured_present", CheckLayer.INVARIANT,
                     evidence={"count": len(unc)})

    # ---- INVARIANT: topology-light room-role observations, only if present ----
    _room_labels_wellformed(rep, view)

    # ---- CROSS_CHECK: dimension-chain closure ----
    _chain_closure(rep, view)

    # ---- CROSS_CHECK: stroke provenance + internal stroke↔dimension consistency ----
    _stroke_dimension_consistency(rep, view)

    # ---- CROSS_CHECK: healed door openings leave a trace in uncaptured ----
    _door_heal_traced(rep, view)

    return rep


def _unique_ids(rep: CheckReport, kind: str, ids: list[str]) -> None:
    seen, dupes = set(), []
    for i in ids:
        if i in seen:
            dupes.append(i)
        seen.add(i)
    if dupes:
        rep.add_fail(
            f"reading.{kind}_ids_unique", CheckLayer.INVARIANT,
            f"duplicate {kind} id(s): {sorted(set(dupes))}",
            evidence={"duplicates": sorted(set(dupes))},
        )
    else:
        rep.add_pass(f"reading.{kind}_ids_unique", CheckLayer.INVARIANT)


def _room_labels_wellformed(rep: CheckReport, view: ReadingView) -> None:
    labels = view.room_labels
    if not labels:
        return

    _unique_ids(rep, "room_label", [label.id for label in labels])

    bad_roles = []
    for label in labels:
        role = normalize(label.role)
        if role not in CANONICAL_ROLES:
            bad_roles.append({"id": label.id, "role": label.role, "normalized": role})
    if bad_roles:
        rep.add_fail(
            "reading.room_label_roles_valid", CheckLayer.INVARIANT,
            f"{len(bad_roles)} room label role(s) outside canonical vocabulary",
            evidence={
                "offenders": bad_roles,
                "canonical_roles": sorted(CANONICAL_ROLES),
            },
        )
    else:
        rep.add_pass("reading.room_label_roles_valid", CheckLayer.INVARIANT)

    bad_basis = [
        {"id": label.id, "basis": label.basis}
        for label in labels
        if label.basis not in _ROOM_LABEL_BASES
    ]
    if bad_basis:
        rep.add_fail(
            "reading.room_label_basis_valid", CheckLayer.INVARIANT,
            f"{len(bad_basis)} room label(s) with illegal basis",
            evidence={"offenders": bad_basis, "allowed": sorted(_ROOM_LABEL_BASES)},
        )
    else:
        rep.add_pass("reading.room_label_basis_valid", CheckLayer.INVARIANT)

    bounds = _image_bounds(view)
    bad_anchors = []
    if bounds is None:
        bad_anchors = [{"id": label.id, "anchor": label.anchor, "reason": "no image bounds"} for label in labels]
    else:
        xmin, xmax, ymin, ymax = bounds
        for label in labels:
            anchor = label.anchor
            if len(anchor) != 2 or not _finite(*anchor):
                bad_anchors.append(
                    {"id": label.id, "anchor": anchor, "reason": "not two finite numbers"}
                )
                continue
            x, y = anchor
            if not (xmin <= x <= xmax and ymin <= y <= ymax):
                bad_anchors.append(
                    {
                        "id": label.id,
                        "anchor": anchor,
                        "reason": "outside image bounds",
                    }
                )
    if bad_anchors:
        rep.add_fail(
            "reading.room_label_anchors_in_bounds", CheckLayer.CROSS_CHECK,
            f"{len(bad_anchors)} room label anchor(s) invalid or out of bounds",
            evidence={"offenders": bad_anchors, "bounds": bounds},
        )
    else:
        rep.add_pass(
            "reading.room_label_anchors_in_bounds", CheckLayer.CROSS_CHECK,
            evidence={"bounds": bounds},
        )


def _image_bounds(view: ReadingView) -> tuple[float, float, float, float] | None:
    explicit = _explicit_image_bounds(view)
    if explicit is not None:
        return explicit

    xs: list[float] = []
    ys: list[float] = []

    def add_pt(pt) -> None:
        if isinstance(pt, list) and len(pt) >= 2 and _finite(pt[0], pt[1]):
            xs.append(float(pt[0]))
            ys.append(float(pt[1]))

    for stroke in view.strokes:
        g = stroke.geometry or {}
        kind = g.get("kind")
        if kind == "line":
            add_pt(g.get("p1"))
            add_pt(g.get("p2"))
        elif kind == "rect":
            xr, yr = g.get("x_range_m"), g.get("y_range_m")
            if isinstance(xr, list) and isinstance(yr, list) and len(xr) >= 2 and len(yr) >= 2:
                add_pt([xr[0], yr[0]])
                add_pt([xr[1], yr[1]])
        elif kind == "polyline":
            for pt in g.get("points", []):
                add_pt(pt)
    for dim in view.dimensions:
        add_pt(dim.from_pt)
        add_pt(dim.to)

    if not xs or not ys:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def _explicit_image_bounds(view: ReadingView) -> tuple[float, float, float, float] | None:
    extra = getattr(view, "__pydantic_extra__", None) or {}
    bounds = extra.get("image_bounds")
    if isinstance(bounds, dict):
        xr, yr = bounds.get("x"), bounds.get("y")
        if (
            isinstance(xr, list)
            and isinstance(yr, list)
            and len(xr) >= 2
            and len(yr) >= 2
            and _finite(xr[0], xr[1], yr[0], yr[1])
        ):
            return float(xr[0]), float(xr[1]), float(yr[0]), float(yr[1])
    if (
        isinstance(bounds, list)
        and len(bounds) == 2
        and all(isinstance(pt, list) and len(pt) >= 2 for pt in bounds)
        and _finite(bounds[0][0], bounds[0][1], bounds[1][0], bounds[1][1])
    ):
        xs = [float(bounds[0][0]), float(bounds[1][0])]
        ys = [float(bounds[0][1]), float(bounds[1][1])]
        return min(xs), max(xs), min(ys), max(ys)

    size = extra.get("image_size") or extra.get("image_dimensions")
    if isinstance(size, list) and len(size) >= 2 and _finite(size[0], size[1]):
        return 0.0, float(size[0]), 0.0, float(size[1])
    width, height = extra.get("image_width"), extra.get("image_height")
    if _finite(width, height):
        return 0.0, float(width), 0.0, float(height)
    return None


def _pen_kind(rep: CheckReport, view: ReadingView) -> None:
    legal = _legal_pens(view.image_kind)
    bad: list[dict] = []
    for s in view.strokes:
        if legal is not None and s.pen not in legal:
            bad.append({"id": s.id, "pen": s.pen, "reason": "illegal pen for image_kind"})
            continue
        kind = (s.geometry or {}).get("kind")
        if kind not in _GEOMETRY_KINDS:
            reason = "missing geometry kind" if kind is None else "unknown geometry kind"
            bad.append({"id": s.id, "kind": kind, "reason": reason})
    if bad:
        rep.add_fail(
            "reading.pen_kind_valid", CheckLayer.INVARIANT,
            f"{len(bad)} stroke(s) with illegal pen/kind for image_kind="
            f"'{view.image_kind}'",
            evidence={"offenders": bad, "legal_pens": sorted(legal) if legal else None},
        )
    else:
        rep.add_pass("reading.pen_kind_valid", CheckLayer.INVARIANT)


def _no_topology_fields(rep: CheckReport, view: ReadingView) -> None:
    bad = []
    for s in view.strokes:
        extra = getattr(s, "__pydantic_extra__", None) or {}
        hit = _FORBIDDEN_STROKE_KEYS & set(extra)
        hit |= _FORBIDDEN_STROKE_KEYS & set(s.geometry or {})
        if hit:
            bad.append({"id": s.id, "fields": sorted(hit)})
    if bad:
        rep.add_fail(
            "reading.no_topology_fields", CheckLayer.INVARIANT,
            "stroke(s) carry topology/world fields (belong to 1_correction)",
            evidence={"offenders": bad},
        )
    else:
        rep.add_pass("reading.no_topology_fields", CheckLayer.INVARIANT)


def _geometry_wellformed(rep: CheckReport, view: ReadingView) -> None:
    bad = []
    for s in view.strokes:
        g = s.geometry or {}
        kind = g.get("kind")
        if kind == "line":
            p1, p2 = g.get("p1"), g.get("p2")
            if not (p1 and p2 and _finite(*p1, *p2)):
                bad.append({"id": s.id, "reason": "non-finite line endpoints"})
            elif math.dist(p1[:2], p2[:2]) < _MIN_EXTENT:
                bad.append({"id": s.id, "reason": "degenerate line (zero length)"})
        elif kind == "rect":
            xr, yr = g.get("x_range_m"), g.get("y_range_m")
            if not (xr and yr and _finite(*xr, *yr)):
                bad.append({"id": s.id, "reason": "non-finite rect range"})
            elif abs(xr[1] - xr[0]) < _MIN_EXTENT or abs(yr[1] - yr[0]) < _MIN_EXTENT:
                # EITHER collapsed axis makes a rectangle degenerate (zero area).
                bad.append({"id": s.id, "reason": "degenerate rect (collapsed axis)"})
        elif kind == "polyline":
            pts = g.get("points")
            if not (
                isinstance(pts, list)
                and len(pts) >= 2
                and all(isinstance(pt, list) and len(pt) >= 2 and _finite(*pt[:2]) for pt in pts)
            ):
                bad.append({"id": s.id, "reason": "malformed polyline points"})
            elif sum(math.dist(pts[i - 1][:2], pts[i][:2]) for i in range(1, len(pts))) < _MIN_EXTENT:
                bad.append({"id": s.id, "reason": "degenerate polyline (zero length)"})
    if bad:
        rep.add_fail(
            "reading.nondegenerate_geometry", CheckLayer.INVARIANT,
            f"{len(bad)} stroke(s) with non-finite or degenerate geometry",
            evidence={"offenders": bad},
        )
    else:
        rep.add_pass("reading.nondegenerate_geometry", CheckLayer.INVARIANT)


def _dimensions_wellformed(rep: CheckReport, view: ReadingView) -> None:
    unparseable, axis_bad = [], []
    for d in view.dimensions:
        val = d.value_m if d.value_m is not None else parse_value_m(d.text_verbatim or d.text)
        if val is None:
            unparseable.append(d.id)
        # axis-endpoint consistency: a dimension's axis must match the axis along
        # which its endpoints actually differ.
        if d.axis and d.from_pt and d.to and _finite(*d.from_pt[:2], *d.to[:2]):
            dx = abs(d.to[0] - d.from_pt[0])
            dy = abs(d.to[1] - d.from_pt[1])
            if d.axis == "x" and dx < dy:
                axis_bad.append({"id": d.id, "axis": "x", "dx": dx, "dy": dy})
            elif d.axis == "y" and dy < dx:
                axis_bad.append({"id": d.id, "axis": "y", "dx": dx, "dy": dy})
    if unparseable:
        rep.add_fail(
            "reading.dimension_parseable", CheckLayer.INVARIANT,
            f"{len(unparseable)} dimension(s) with no parseable value",
            evidence={"ids": unparseable},
        )
    else:
        rep.add_pass("reading.dimension_parseable", CheckLayer.INVARIANT)
    if axis_bad:
        rep.add_fail(
            "reading.axis_endpoint_consistent", CheckLayer.INVARIANT,
            f"{len(axis_bad)} dimension(s) whose axis disagrees with endpoints",
            evidence={"offenders": axis_bad},
        )
    else:
        rep.add_pass("reading.axis_endpoint_consistent", CheckLayer.INVARIANT)


def _door_heal_traced(rep: CheckReport, view: ReadingView) -> None:
    """Flag a healed door opening (a wall stroke whose note says it healed a door)
    that leaves no matching trace in ``uncaptured`` — the old "acknowledged skip
    vs silent loss" discipline (guide §2.1 guardrail 4). Advisory: a missing audit
    note does not corrupt geometry, so this surfaces to gate② rather than blocks.
    Only fires when a heal happened, so a clean drawing with ``uncaptured=[]`` is
    untouched."""
    # Match the guide §2.1 convention phrase "healed door opening at <position>"
    # (precise — avoids false-flagging a note like "door not healed").
    healed = [
        s for s in view.strokes
        if isinstance(getattr(s, "note", None), str) and "healed door" in s.note.lower()
    ]
    if not healed:
        rep.add("reading.door_heal_traced", CheckStatus.NOT_APPLICABLE,
                CheckLayer.CROSS_CHECK, message="no healed door openings")
        return
    pooled = _uncaptured_list(view) or []
    heal_traces = [e for e in pooled if "heal" in str(e).lower()]
    if not heal_traces:
        rep.add_fail(
            "reading.door_heal_traced", CheckLayer.CROSS_CHECK,
            f"{len(healed)} wall stroke(s) healed a door opening but `uncaptured` "
            "records no heal trace (silent-loss risk; see guide §2.1)",
            evidence={
                "healed_stroke_ids": [s.id for s in healed],
                "uncaptured_entries": len(pooled),
            },
        )
    else:
        rep.add_pass(
            "reading.door_heal_traced", CheckLayer.CROSS_CHECK,
            evidence={
                "healed_stroke_ids": [s.id for s in healed],
                "heal_traces": len(heal_traces),
            },
        )


def _facade_fields(rep: CheckReport, view: ReadingView) -> None:
    if (view.image_kind or "").lower() != "elevation":
        rep.add("reading.facade_fields", CheckStatus.NOT_APPLICABLE, CheckLayer.INVARIANT,
                message="not an elevation")
        return
    f = view.facade
    if f is None or f.view_facade is None:
        rep.add_fail(
            "reading.facade_fields", CheckLayer.INVARIANT,
            "elevation missing image-local facade orientation (view_facade)",
        )
    else:
        rep.add_pass("reading.facade_fields", CheckLayer.INVARIANT,
                     evidence={"view_facade": f.view_facade, "mirrored": str(f.mirrored)})


def _chain_closure(rep: CheckReport, view: ReadingView) -> None:
    """Σ segment values == overall value, per chain_id (cross_check flag)."""
    chains: dict[str, dict] = {}
    for d in view.dimensions:
        if not d.chain_id:
            continue
        c = chains.setdefault(d.chain_id, {"overall": None, "segments": []})
        val = d.value_m if d.value_m is not None else parse_value_m(d.text_verbatim or d.text)
        if val is None:
            continue
        if d.role and d.role.value in ("overall", "baseline"):
            c["overall"] = val
        elif d.role and d.role.value == "segment":
            c["segments"].append(val)
    if not chains:
        rep.add("reading.dimension_chain_closure", CheckStatus.NOT_APPLICABLE,
                CheckLayer.CROSS_CHECK, message="no chain_id-tagged dimensions")
        return
    mismatches = []
    for cid, c in chains.items():
        if c["overall"] is None or not c["segments"]:
            continue
        seg_sum = sum(c["segments"])
        if abs(seg_sum - c["overall"]) > 0.05:
            mismatches.append(
                {"chain": cid, "overall": c["overall"], "segment_sum": seg_sum}
            )
    if mismatches:
        rep.add_fail(
            "reading.dimension_chain_closure", CheckLayer.CROSS_CHECK,
            f"{len(mismatches)} dimension chain(s) do not close",
            evidence={"mismatches": mismatches},
        )
    else:
        rep.add_pass("reading.dimension_chain_closure", CheckLayer.CROSS_CHECK,
                     evidence={"chains_checked": len(chains)})


def _stroke_dimension_consistency(rep: CheckReport, view: ReadingView) -> None:
    """Report provenance coverage and flag plan-wall coordinates that sit exactly
    on dimension-chain cumulative positions. This is advisory only: a real wall can
    be dimensioned, so J0 must verify the rendered/source image evidence."""
    structural = [s for s in view.strokes if s.pen in _PROVENANCE_PENS]
    with_provenance = [
        s for s in structural if getattr(s, "provenance", None) is not None
    ]
    if not structural or not with_provenance:
        mode = "legacy"
    elif len(with_provenance) == len(structural):
        mode = "full"
    else:
        mode = "partial"
    rep.add_pass(
        "reading.stroke_provenance_coverage",
        CheckLayer.CROSS_CHECK,
        evidence={
            "provenance_mode": mode,
            "structural_strokes": len(structural),
            "with_provenance": len(with_provenance),
        },
    )

    if (view.image_kind or "").lower() != "plan":
        rep.add(
            "reading.stroke_dimension_consistency",
            CheckStatus.NOT_APPLICABLE,
            CheckLayer.CROSS_CHECK,
            message="not a plan",
        )
        return

    dim_positions = _dimension_chain_positions(view)
    if not dim_positions.get("x") and not dim_positions.get("y"):
        rep.add(
            "reading.stroke_dimension_consistency",
            CheckStatus.NOT_APPLICABLE,
            CheckLayer.CROSS_CHECK,
            message="no chain_id-tagged x/y dimension cumulative positions",
        )
        return

    bounds = _wall_bounds(view)
    offenders = []
    for stroke in view.strokes:
        if stroke.pen != "wall":
            continue
        if getattr(stroke, "provenance", None) == "dimension_derived":
            continue
        axis_line = _wall_axis_line(stroke)
        if axis_line is None:
            continue
        axis, coord, p1, p2 = axis_line
        if _is_perimeter_axis(axis, coord, bounds):
            continue
        matches = [
            pos for pos in dim_positions.get(axis, [])
            if abs(pos["coord"] - coord) <= _OUTPUT_PRECISION_M
        ]
        if not matches:
            continue
        joined = _wall_join_evidence(view, stroke, p1, p2)
        offenders.append({
            "stroke_id": stroke.id,
            "axis": axis,
            "coord_m": coord,
            "matching_dimension_ids": sorted({
                dim_id for pos in matches for dim_id in pos["dimension_ids"]
            }),
            "matching_positions": matches,
            "joins_walls": joined,
            "bounds_rooms_inferable": joined["both_endpoints_join"],
        })

    if offenders:
        rep.add_fail(
            "reading.stroke_dimension_consistency",
            CheckLayer.CROSS_CHECK,
            f"{len(offenders)} plan wall stroke coordinate(s) coincide with "
            "dimension-chain cumulative positions; verify each is a real "
            "room-bounding wall",
            evidence={"tolerance_m": _OUTPUT_PRECISION_M, "offenders": offenders},
        )
    else:
        rep.add_pass(
            "reading.stroke_dimension_consistency",
            CheckLayer.CROSS_CHECK,
            evidence={
                "tolerance_m": _OUTPUT_PRECISION_M,
                "axes_with_chains": sorted(k for k, v in dim_positions.items() if v),
            },
        )


def _dimension_chain_positions(view: ReadingView) -> dict[str, list[dict]]:
    chains: dict[tuple[str, str], list] = {}
    for d in view.dimensions:
        if d.chain_id and d.axis in ("x", "y"):
            chains.setdefault((d.chain_id, d.axis), []).append(d)

    positions: dict[str, list[dict]] = {"x": [], "y": []}
    seen: set[tuple[str, float, tuple[str, ...]]] = set()
    for (chain_id, axis), dims in chains.items():
        ordered = sorted(dims, key=lambda d: (d.order is None, d.order or 0, d.id))
        running = 0.0
        running_ids: list[str] = []
        for d in ordered:
            # Prefer explicit endpoints: they are already cumulative coordinates in
            # the reading frame and avoid guessing a datum.
            endpoint_coords = []
            if d.from_pt and len(d.from_pt) >= 2 and _finite(*d.from_pt[:2]):
                endpoint_coords.append(float(d.from_pt[0 if axis == "x" else 1]))
            if d.to and len(d.to) >= 2 and _finite(*d.to[:2]):
                endpoint_coords.append(float(d.to[0 if axis == "x" else 1]))
            for coord in endpoint_coords:
                _add_dim_position(positions, seen, axis, coord, [d.id], chain_id)

            val = d.value_m if d.value_m is not None else parse_value_m(d.text_verbatim or d.text)
            if val is None:
                continue
            role = d.role.value if d.role is not None else None
            if role == "segment":
                running += float(val)
                running_ids.append(d.id)
                _add_dim_position(positions, seen, axis, running, running_ids, chain_id)
    return positions


def _add_dim_position(
    positions: dict[str, list[dict]],
    seen: set[tuple[str, float, tuple[str, ...]]],
    axis: str,
    coord: float,
    dimension_ids: list[str],
    chain_id: str,
) -> None:
    rounded = round(float(coord), 6)
    ids = tuple(sorted(dimension_ids))
    key = (axis, rounded, ids)
    if key in seen:
        return
    seen.add(key)
    positions[axis].append({
        "coord": rounded,
        "dimension_ids": list(ids),
        "chain_id": chain_id,
    })


def _wall_axis_line(stroke) -> tuple[str, float, list[float], list[float]] | None:
    g = stroke.geometry or {}
    if g.get("kind") != "line":
        return None
    p1, p2 = g.get("p1"), g.get("p2")
    if not (isinstance(p1, list) and isinstance(p2, list) and len(p1) >= 2 and len(p2) >= 2):
        return None
    if not _finite(*p1[:2], *p2[:2]):
        return None
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    if abs(x1 - x2) <= _OUTPUT_PRECISION_M:
        return "x", round((x1 + x2) / 2, 6), [x1, y1], [x2, y2]
    if abs(y1 - y2) <= _OUTPUT_PRECISION_M:
        return "y", round((y1 + y2) / 2, 6), [x1, y1], [x2, y2]
    return None


def _wall_bounds(view: ReadingView) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for stroke in view.strokes:
        if stroke.pen != "wall":
            continue
        g = stroke.geometry or {}
        if g.get("kind") != "line":
            continue
        p1, p2 = g.get("p1"), g.get("p2")
        if (
            isinstance(p1, list) and isinstance(p2, list)
            and len(p1) >= 2 and len(p2) >= 2
            and _finite(*p1[:2], *p2[:2])
        ):
            xs.extend([float(p1[0]), float(p2[0])])
            ys.extend([float(p1[1]), float(p2[1])])
    if not xs or not ys:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def _is_perimeter_axis(
    axis: str, coord: float, bounds: tuple[float, float, float, float] | None
) -> bool:
    if bounds is None:
        return False
    xmin, xmax, ymin, ymax = bounds
    extremes = (xmin, xmax) if axis == "x" else (ymin, ymax)
    return any(abs(coord - edge) <= _OUTPUT_PRECISION_M for edge in extremes)


def _wall_join_evidence(view: ReadingView, stroke, p1: list[float], p2: list[float]) -> dict:
    joins = [
        _point_joins_other_wall(view, stroke.id, p1),
        _point_joins_other_wall(view, stroke.id, p2),
    ]
    return {
        "p1": joins[0],
        "p2": joins[1],
        "both_endpoints_join": all(joins),
    }


def _point_joins_other_wall(view: ReadingView, own_id: str, pt: list[float]) -> bool:
    for other in view.strokes:
        if other.id == own_id or other.pen != "wall":
            continue
        g = other.geometry or {}
        if g.get("kind") != "line":
            continue
        p1, p2 = g.get("p1"), g.get("p2")
        if not (
            isinstance(p1, list) and isinstance(p2, list)
            and len(p1) >= 2 and len(p2) >= 2
            and _finite(*p1[:2], *p2[:2])
        ):
            continue
        if _point_on_segment(pt, [float(p1[0]), float(p1[1])], [float(p2[0]), float(p2[1])]):
            return True
    return False


def _point_on_segment(pt: list[float], a: list[float], b: list[float]) -> bool:
    px, py = pt
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    seg_len2 = dx * dx + dy * dy
    if seg_len2 <= 0:
        return False
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len2))
    closest = [ax + t * dx, ay + t * dy]
    return math.dist(pt, closest) <= _OUTPUT_PRECISION_M
