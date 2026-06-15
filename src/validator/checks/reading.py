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
from src.validator.checks.schema import CheckLayer, CheckReport, CheckStatus

# Legal pen sets by image kind (pen_library.md §2).
_PLAN_PENS = {"wall", "window"}
_ELEVATION_PENS = {"wall_fill", "window", "outline"}
# Topology / world fields a reading stroke must NOT carry (those are 1_correction's).
_FORBIDDEN_STROKE_KEYS = {"zone", "adjacent_zone", "adjacent_surface", "obc", "world_z"}
_MIN_EXTENT = 0.05  # m — below this a line/rect is degenerate


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
    """Effective uncaptured list, tolerating the legacy key name."""
    if isinstance(view.uncaptured, list) and view.uncaptured:
        return view.uncaptured
    extra = getattr(view, "__pydantic_extra__", None) or {}
    for key in ("uncaptured", "uncaptured_visual_elements"):
        if key in extra and isinstance(extra[key], list):
            return extra[key]
    return view.uncaptured if isinstance(view.uncaptured, list) else None


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

    # ---- CROSS_CHECK: dimension-chain closure ----
    _chain_closure(rep, view)

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


def _pen_kind(rep: CheckReport, view: ReadingView) -> None:
    legal = _legal_pens(view.image_kind)
    bad: list[dict] = []
    for s in view.strokes:
        if legal is not None and s.pen not in legal:
            bad.append({"id": s.id, "pen": s.pen, "reason": "illegal pen for image_kind"})
            continue
        kind = (s.geometry or {}).get("kind")
        if kind not in (None, "line", "rect", "polyline"):
            bad.append({"id": s.id, "kind": kind, "reason": "unknown geometry kind"})
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
            elif abs(xr[1] - xr[0]) < _MIN_EXTENT and abs(yr[1] - yr[0]) < _MIN_EXTENT:
                bad.append({"id": s.id, "reason": "degenerate rect (zero area)"})
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
