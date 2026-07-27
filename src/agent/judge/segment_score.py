"""Judge-only planar segment extraction and deterministic matching (B4b-B).

The module intentionally works with actual polygon edges.  It has no rectangle
or ``W/D`` fallback: callers must give typed GT or typed correction geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import hypot
from typing import Iterable, Mapping, Sequence

from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.judge.gt_schema import GroundTruthV3
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError


Point = tuple[float, float]


# W1 coordinate identity (representation-layer, NOT a geometric tolerance).
# Coordinates are NOT snapped to a global grid: any total discretization has a
# boundary, and a 1-ulp pair straddling it silently splits -- exactly the false
# red this batch removes (the r2 quantum-boundary pair).  Instead, the values
# actually appearing on each (side, floor, axis) are single-link clustered with
# a guard band and a diameter guard, so a same-intent seam (8.059999999999999 vs
# 8.06; 0.1+0.2 vs 0.3; a 1-ulp straddling pair) collapses to ONE atomic
# representative, and an unresolvable gap or a chain bridge is a LOUD reject.
# Pooling scope is per (side, floor, axis): GT and product pools never mix, so
# the answer's atoms are a pure function of the answer bytes (C-1').  Cross-
# document comparison happens only at the judge tolerance layer (plan_*_tol_m),
# product -> answer one-way (never reverse).
#
# Thresholds were MEASURED then chosen, not chosen then justified (R-2):
#   - signed-off sm24 GT: ZERO intra-document drift (50 vertices, no near pair);
#   - largest measured drift: 1 ulp at 8 m = 1.776357e-15 (13.0-4.94 vs 8.06);
#   - binary64 single-ulp bound across 1..20 m: 3.552714e-15.
# So merge sits 281x above the single-ulp bound (absorbs any arithmetic drift),
# split sits 100x below the 1e-9 minimum red gap (a 1e-9 seam stays split), and
# the open (merge, split) band is an explicit reject zone a grid cannot have.
# See AI_agent/logs/reviews/execution/2026-07-27_judge_identity_metric_glm.md
# for the full measurement table and two-sided headroom proof.
_COORDINATE_MERGE_THRESHOLD = 1e-12     # gap below this: same intent -> merge.
_COORDINATE_SPLIT_THRESHOLD = 1e-11     # gap above this: distinct intent -> split.
_COORDINATE_DIAMETER_THRESHOLD = 1e-11  # cluster diameter cap (chain-bridge guard).


@dataclass(frozen=True)
class _AxisIdentity:
    """One axis of one (side, floor): raw float -> atomic cluster representative.

    The representative is the cluster minimum, which is deterministic once the
    value set is fixed (sorted-set order) and never depends on input ordering.
    """
    side: str
    floor_id: str
    axis: str
    rep: Mapping[float, float]


def _cluster_axis(raw_values: Iterable[float], *, side: str, floor_id: str, axis: str,
                  identity_code: str) -> _AxisIdentity:
    """Single-link cluster with guard band + diameter guard (C-1 / C-1' / C-1'').

    Returns a raw -> representative mapping.  Raises ScoreContractError on a
    non-finite value, a gap inside the guard band (unresolvable ambiguity), or a
    cluster whose diameter exceeds the cap (a chain bridge).  Context always
    carries the hex binary64 of every value involved so the decision is
    reproducible from the sidecar alone.
    """
    values: list[float] = []
    for raw in raw_values:
        value = float(raw)
        if value != value or value == float("inf") or value == float("-inf"):
            raise ScoreContractError(identity_code, "scoring.input_identity",
                context={"reason": "identity_non_finite_value", "side": side,
                         "floor_id": floor_id, "axis": axis, "hex": float(value).hex()})
        values.append(value)
    unique = sorted(set(values))
    rep: dict[float, float] = {}
    if not unique:
        return _AxisIdentity(side, floor_id, axis, rep)
    clusters: list[tuple[float, float]] = []   # (cluster_min, cluster_max)
    cur_min = cur_max = unique[0]
    rep[unique[0]] = unique[0]
    for index in range(1, len(unique)):
        prev, value = unique[index - 1], unique[index]
        gap = value - prev
        if gap < _COORDINATE_MERGE_THRESHOLD:
            rep[value] = cur_min
            cur_max = value
        elif gap > _COORDINATE_SPLIT_THRESHOLD:
            clusters.append((cur_min, cur_max))
            cur_min = cur_max = value
            rep[value] = cur_min
        else:
            raise ScoreContractError(identity_code, "scoring.input_identity",
                context={"reason": "identity_guard_band_ambiguity", "side": side,
                    "floor_id": floor_id, "axis": axis, "gap": gap,
                    "merge": _COORDINATE_MERGE_THRESHOLD, "split": _COORDINATE_SPLIT_THRESHOLD,
                    "gap_hex": gap.hex(), "lo_hex": prev.hex(), "hi_hex": value.hex()})
    clusters.append((cur_min, cur_max))
    for lo, hi in clusters:
        diameter = hi - lo
        if diameter > _COORDINATE_DIAMETER_THRESHOLD:
            raise ScoreContractError(identity_code, "scoring.input_identity",
                context={"reason": "identity_chain_bridge_over_diameter", "side": side,
                    "floor_id": floor_id, "axis": axis, "diameter": diameter,
                    "diameter_threshold": _COORDINATE_DIAMETER_THRESHOLD,
                    "diameter_hex": diameter.hex(), "lo_hex": lo.hex(), "hi_hex": hi.hex()})
    return _AxisIdentity(side, floor_id, axis, rep)


def _build_floor_identity(points: Iterable[Sequence[float]], *, side: str, floor_id: str,
                          identity_code: str) -> tuple[_AxisIdentity, _AxisIdentity]:
    """Build the (x, y) identity pair for one document side on one floor."""
    materialized = tuple(points)
    x_id = _cluster_axis((float(p[0]) for p in materialized), side=side, floor_id=floor_id,
                         axis="x", identity_code=identity_code)
    y_id = _cluster_axis((float(p[1]) for p in materialized), side=side, floor_id=floor_id,
                         axis="y", identity_code=identity_code)
    return x_id, y_id


def _identify_point(point: Sequence[float], x_id: _AxisIdentity, y_id: _AxisIdentity) -> Point:
    # +0.0 collapses -0.0 to 0.0 so it can never poison a dict key or tuple compare.
    return (x_id.rep[float(point[0])] + 0.0, y_id.rep[float(point[1])] + 0.0)


@dataclass(frozen=True)
class PlanSegment:
    """A judge observation/target; ``key`` is audit data, never a tie breaker."""
    key: str
    floor_id: str
    p1: Point
    p2: Point
    zone_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    exterior: bool = True

    @property
    def length(self) -> float:
        return hypot(self.p2[0] - self.p1[0], self.p2[1] - self.p1[1])


@dataclass(frozen=True)
class SegmentAssignment:
    matched: tuple[tuple[PlanSegment, PlanSegment], ...]
    unmatched_targets: tuple[PlanSegment, ...]
    unmatched_observations: tuple[PlanSegment, ...]


@dataclass(frozen=True)
class SegmentScore:
    target: PlanSegment | None
    observation: PlanSegment | None
    status: str  # complete | within_tolerance | miss | extra | duplicate
    axis_alignment_error_m: float | None
    position_error_m: float | None
    extent_symmetric_difference_m: float | None
    # W4: length (m) this row contributes to its criterion denominator.  For a
    # matched row, the overlap length on the target's support line; for a miss,
    # the uncovered target length; for an extra, the observation length that
    # covered no target; for a duplicate, the target length covered by >1 obs.
    # Replaces the prior per-segment count of 1 (which over-weighted walls
    # facing many rooms by up to 3.96x on real sm24).
    eligible_units: float = 0.0


def _points(vertices: Sequence[Sequence[float]], x_id: _AxisIdentity, y_id: _AxisIdentity,
            *, identity_code: str) -> tuple[Point, ...]:
    # W1: map raw vertices through the (side, floor) axis identities so the same
    # decimal seam shares one atomic representative before any exact comparison.
    out = tuple(_identify_point(point, x_id, y_id) for point in vertices)
    if len(out) > 1 and out[0] == out[-1]:
        out = out[:-1]
    if len(out) < 3:
        raise ScoreContractError(identity_code, "scoring.input_identity",
            context={"reason": "polygon_too_short", "side": x_id.side, "floor_id": x_id.floor_id})
    # C-1''(4): identity merge must not collapse adjacent vertices (zero-length edge).
    for first, second in zip(out, out[1:] + out[:1]):
        if first == second:
            raise ScoreContractError(identity_code, "scoring.input_identity",
                context={"reason": "identity_merge_edge_collapse", "side": x_id.side,
                    "floor_id": x_id.floor_id, "axis": "xy", "hex": float(first[0]).hex()})
    return out


def _edges(vertices: Sequence[Sequence[float]], x_id: _AxisIdentity, y_id: _AxisIdentity,
           *, identity_code: str) -> tuple[tuple[Point, Point], ...]:
    ring = _points(vertices, x_id, y_id, identity_code=identity_code)
    return tuple((ring[index], ring[(index + 1) % len(ring)]) for index in range(len(ring)))


def _edge_key(p1: Point, p2: Point) -> tuple[Point, Point]:
    return p1, p2


def _lies_on_exterior(edge: tuple[Point, Point], exterior: Iterable[tuple[Point, Point]]) -> bool:
    """Exact axis-aligned containment allows a tiled zone's split exterior edge."""
    (a, b) = edge
    for p1, p2 in exterior:
        if p1[0] == p2[0] == a[0] == b[0] and min(p1[1], p2[1]) <= min(a[1], b[1]) and max(a[1], b[1]) <= max(p1[1], p2[1]): return True
        if p1[1] == p2[1] == a[1] == b[1] and min(p1[0], p2[0]) <= min(a[0], b[0]) and max(a[0], b[0]) <= max(p1[0], p2[0]): return True
    return False


def _canonical_geometry(segment: PlanSegment) -> tuple:
    return (segment.floor_id, min(segment.p1, segment.p2), max(segment.p1, segment.p2), segment.exterior,
            tuple(sorted(segment.zone_ids)))


def _tile_orthogonal_edges(
    directed: dict[tuple[Point, Point], list[str]],
    exterior_edges: tuple[tuple[Point, Point], ...],
    floor_id: str,
    *,
    identity_code: str,
) -> list[tuple[Point, Point, tuple[str, ...]]]:
    """Tile axis-aligned shared edges into T-junction sub-intervals (exact coverage).

    Every directed edge on a shared supporting line is tiled at the union of all
    endpoints into elementary sub-intervals; each sub-interval is attributed to
    the single zone on each side and becomes one paired segment.  Coverage must
    be exact -- a gap, an overlap, or an endpoint that does not meet precisely
    is a real topology break, not a T-junction, and is rejected.  Collinearity
    and coverage both use exact equality with no snapping or tolerance, mirroring
    ``_lies_on_exterior``: snapping would turn a nearby wall into a fictional
    shared edge.  Coordinates are already canonicalized at the scorer entry (RW-1).
    """
    # Bucket directed edges by supporting orthogonal line and traversal side.
    # CCW polygons on opposite sides of a wall traverse it in opposite
    # directions, so the two sides land in forward/reverse separately.
    lines: dict[tuple[str, float], dict[str, list[tuple[float, float, str]]]] = {}
    for (p1, p2), owners in directed.items():
        if p1[0] == p2[0]:
            axis, const = "V", p1[0]
            lo, hi = (p1[1], p2[1]) if p1[1] <= p2[1] else (p2[1], p1[1])
            forward = p2[1] > p1[1]
        else:
            axis, const = "H", p1[1]
            lo, hi = (p1[0], p2[0]) if p1[0] <= p2[0] else (p2[0], p1[0])
            forward = p2[0] > p1[0]
        side = "fwd" if forward else "rev"
        for owner in owners:
            lines.setdefault((axis, const), {"fwd": [], "rev": []})[side].append((lo, hi, owner))

    pairs: list[tuple[Point, Point, tuple[str, ...]]] = []
    for (axis, const), group in lines.items():
        cuts = sorted({coord for span in (group["fwd"] + group["rev"]) for coord in span[:2]})
        for lo, hi in zip(cuts, cuts[1:]):
            if lo == hi:
                continue
            geometry = ((const, lo), (const, hi)) if axis == "V" else ((lo, const), (hi, const))
            forward_owners = [owner for left, right, owner in group["fwd"] if left <= lo and hi <= right]
            reverse_owners = [owner for left, right, owner in group["rev"] if left <= lo and hi <= right]
            on_exterior = _lies_on_exterior(geometry, exterior_edges)
            if forward_owners and reverse_owners:
                if on_exterior:
                    raise ScoreContractError(identity_code, "scoring.input_identity",
                        context={"reason": "exterior_interior_topology_conflict", "floor_id": floor_id})
                if len(forward_owners) != 1 or len(reverse_owners) != 1:
                    raise ScoreContractError(identity_code, "scoring.input_identity",
                        context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id})
                pairs.append((geometry[0], geometry[1], tuple(sorted((forward_owners[0], reverse_owners[0])))))
            elif forward_owners or reverse_owners:
                if on_exterior:
                    # RW-3: a conforming tiling has exactly one owner per exterior
                    # edge per side.  Two same-direction owners on one
                    # exterior-only sub-interval means a zone is duplicated over
                    # the footprint (the silent-green hole).  This catches that
                    # specific shape -- it is NOT a claim that the helper detects
                    # every overlap; area-level zone overlap is the upstream
                    # coverage validator's job and a different layer.
                    if len(forward_owners) > 1 or len(reverse_owners) > 1:
                        raise ScoreContractError(identity_code, "scoring.input_identity",
                            context={"reason": "exterior_duplicate_owner", "floor_id": floor_id})
                    # single-owner exterior span: a legitimate boundary edge, not a wall
                else:
                    raise ScoreContractError(identity_code, "scoring.input_identity",
                        context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id})
            # else: open span with no edge on either side (e.g. a corridor mouth)
    return pairs


def _pair_general_edges(
    directed: dict[tuple[Point, Point], list[str]],
    exterior_edges: tuple[tuple[Point, Point], ...],
    floor_id: str,
    *,
    identity_code: str,
) -> list[tuple[Point, Point, tuple[str, ...]]]:
    """Pair non-axis-aligned edges by exact reverse (RW-2 general-segment seam).

    The scorer must not reinterpret a near-orthogonal edge the upstream validator
    accepted as a topology break: ``cell_geometry`` admits edges with dx<1e-9 as
    orthogonal, so a legal correction can carry a dx=5e-10 exact-reverse seam that
    the GT/exact axis check would otherwise reject.  Such an edge is paired only
    with its exact reverse; a one-sided general edge with no reverse, or a
    same-direction duplicate owner, is a real topology break.  Footprint/exterior
    rings are axis-aligned (validated upstream), so a general edge is never on
    the exterior here -- the exterior/interior conflict check is unreachable on
    this path and intentionally omitted.  C2 enables orthogonal T-junction tiling
    today; a future non-orthogonal profile extends here without rewriting the API
    or the orthogonal path (invariant #6).
    """
    pairs: list[tuple[Point, Point, tuple[str, ...]]] = []
    consumed: set[tuple[Point, Point]] = set()
    for edge, owners in directed.items():
        if edge in consumed:
            continue
        p1, p2 = edge
        reverse = (p2, p1)
        rev_owners = directed.get(reverse)
        if rev_owners is None:
            raise ScoreContractError(identity_code, "scoring.input_identity",
                context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id})
        if len(owners) != 1 or len(rev_owners) != 1:
            raise ScoreContractError(identity_code, "scoring.input_identity",
                context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id})
        pairs.append((p1, p2, tuple(sorted((owners[0], rev_owners[0])))))
        consumed.add(edge)
        consumed.add(reverse)
    return pairs


def _pair_interior_edges(
    directed: dict[tuple[Point, Point], list[str]],
    exterior_edges: tuple[tuple[Point, Point], ...],
    floor_id: str,
    *,
    identity_code: str,
) -> list[tuple[Point, Point, tuple[str, ...]]]:
    """Pair interior edges by exact coverage, T-junction aware (RW-1/2/3).

    Axis-aligned edges are tiled at the union of all endpoints into elementary
    sub-intervals (``_tile_orthogonal_edges``); non-axis-aligned edges pair only
    with their exact reverse (``_pair_general_edges``).  All coordinates are
    canonicalized at the scorer entry (RW-1), so every comparison below is exact
    (``==`` / ``<=``); a gap, an overlap, or an imprecise endpoint is a real
    topology break, not a T-junction, and is rejected.
    """
    ortho: dict[tuple[Point, Point], list[str]] = {}
    general: dict[tuple[Point, Point], list[str]] = {}
    for edge, owners in directed.items():
        p1, p2 = edge
        (ortho if p1[0] == p2[0] or p1[1] == p2[1] else general)[edge] = owners
    pairs = _tile_orthogonal_edges(ortho, exterior_edges, floor_id, identity_code=identity_code)
    pairs.extend(_pair_general_edges(general, exterior_edges, floor_id, identity_code=identity_code))
    return pairs


def extract_gt_plan_segments(gt: GroundTruthV3) -> tuple[PlanSegment, ...]:
    """Return exterior GT segments and exact-coverage interior zone edges.

    Coordinates are mapped through a per-(side, floor, axis) identity (W1) so a
    same-intent seam shares one atomic representative before any exact
    comparison.  Interior edges pair by exact collinear coverage so a T-junction
    tiles into one segment per facing zone.  See ``_pair_interior_edges``.
    """
    output: list[PlanSegment] = []
    for floor in gt.floors:
        raw_points: list[Sequence[float]] = []
        raw_points.extend(floor.footprint.exterior.vertices)
        for zone in floor.zones:
            raw_points.extend(zone.polygon.exterior.vertices)
        for segment in floor.boundary_segments:
            raw_points.append(segment.p1)
            raw_points.append(segment.p2)
        x_id, y_id = _build_floor_identity(raw_points, side="gt", floor_id=floor.id,
                                           identity_code="score_gt_identity_invalid")
        for segment in floor.boundary_segments:
            output.append(PlanSegment(segment.id, floor.id, _identify_point(segment.p1, x_id, y_id),
                _identify_point(segment.p2, x_id, y_id), (),
                tuple(ref.view_id for ref in segment.source_refs), True))
        directed: dict[tuple[Point, Point], list[str]] = {}
        for zone in floor.zones:
            for p1, p2 in _edges(zone.polygon.exterior.vertices, x_id, y_id,
                                 identity_code="score_gt_identity_invalid"):
                directed.setdefault(_edge_key(p1, p2), []).append(zone.id)
        exterior_edges = _edges(floor.footprint.exterior.vertices, x_id, y_id,
                                identity_code="score_gt_identity_invalid")
        for p1, p2, zones in _pair_interior_edges(directed, exterior_edges, floor.id,
                                                   identity_code="score_gt_identity_invalid"):
            key = "interior:%s:%s:%s" % (floor.id, min(p1, p2), max(p1, p2))
            output.append(PlanSegment(key, floor.id, p1, p2, zones, (), False))
    return tuple(sorted(output, key=_canonical_geometry))


def _cell_polygon(cell) -> Sequence[Sequence[float]]:
    if cell.polygon is not None:
        return cell.polygon
    # This is a legacy field representation of an actual cell, not a floor bbox.
    return ((cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]), (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1]))


def extract_correction_plan_segments(geometry: CorrectedGeometryV3) -> tuple[PlanSegment, ...]:
    """Extract correction footprint and cell topology without a bbox reduction.

    Coordinates are mapped through a per-(side, floor, axis) identity (W1), the
    same contract as the GT side, so a same-intent seam shares one atomic
    representative.  Interior cell edges pair through the same exact-coverage
    helper (``_pair_interior_edges``); a genuine topology break fails loudly with
    the product identity error rather than discarding observations.
    """
    output: list[PlanSegment] = []
    for floor in geometry.floors:
        raw_points: list[Sequence[float]] = []
        raw_points.extend(floor.footprint.vertices)
        for cell in floor.cells:
            raw_points.extend(_cell_polygon(cell))
        x_id, y_id = _build_floor_identity(raw_points, side="product", floor_id=floor.id,
                                           identity_code="score_product_identity_invalid")
        exterior_edges = _edges(floor.footprint.vertices, x_id, y_id,
                                identity_code="score_product_identity_invalid")
        for number, (p1, p2) in enumerate(exterior_edges):
            output.append(PlanSegment("%s:footprint:%d" % (floor.id, number), floor.id, p1, p2,
                                      (), ("correction:%s" % floor.id,), True))
        directed: dict[tuple[Point, Point], list[str]] = {}
        for cell in floor.cells:
            for p1, p2 in _edges(_cell_polygon(cell), x_id, y_id,
                                 identity_code="score_product_identity_invalid"):
                directed.setdefault((p1, p2), []).append(cell.id)
        for p1, p2, zones in _pair_interior_edges(directed, exterior_edges, floor.id,
                                                   identity_code="score_product_identity_invalid"):
            output.append(PlanSegment("%s:interior:%s:%s" % (floor.id, min(p1, p2), max(p1, p2)), floor.id,
                                      p1, p2, zones, ("correction:%s" % floor.id,), False))
    return tuple(sorted(output, key=_canonical_geometry))


def coerce_plan_observations(observations: Iterable[PlanSegment | dict]) -> tuple[PlanSegment, ...]:
    """Typed dispatch adapter for reading observations; no v3 branch in legacy code.

    Observations are parsed with their raw coordinates, then mapped through a
    per-(side, floor, axis) identity (W1) -- the same contract as the GT/
    correction extraction paths -- so a same-intent seam shares one identity.
    """
    raw_rows: list[PlanSegment] = []
    for raw in observations:
        if isinstance(raw, PlanSegment):
            raw_rows.append(PlanSegment(raw.key, raw.floor_id, raw.p1, raw.p2,
                                        raw.zone_ids, raw.source_ids, raw.exterior)); continue
        try:
            raw_rows.append(PlanSegment(key=str(raw["id"]), floor_id=str(raw["floor_id"]),
                p1=(float(raw["p1"][0]), float(raw["p1"][1])), p2=(float(raw["p2"][0]), float(raw["p2"][1])),
                zone_ids=tuple(str(x) for x in raw.get("zone_ids", ())),
                source_ids=tuple(str(x) for x in raw.get("source_ids", ())), exterior=bool(raw.get("exterior", True))))
        except (KeyError, TypeError, ValueError) as exc:
            raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity", context={"reason": "invalid_plan_observation"}) from exc
    # W1: build per-floor identities and map every observation through them.
    by_floor: dict[str, list[PlanSegment]] = {}
    for row in raw_rows:
        by_floor.setdefault(row.floor_id, []).append(row)
    output: list[PlanSegment] = []
    for floor_id, group in by_floor.items():
        points = [point for row in group for point in (row.p1, row.p2)]
        x_id, y_id = _build_floor_identity(points, side="product", floor_id=floor_id,
                                           identity_code="score_product_identity_invalid")
        for row in group:
            output.append(PlanSegment(row.key, row.floor_id, _identify_point(row.p1, x_id, y_id),
                _identify_point(row.p2, x_id, y_id), row.zone_ids, row.source_ids, row.exterior))
    return tuple(output)


def _candidate(target: PlanSegment, observed: PlanSegment, config: JudgeScoreConfigV1) -> tuple[float, float, float] | None:
    if target.floor_id != observed.floor_id or target.length == 0 or observed.length == 0:
        return None
    dx, dy = target.p2[0] - target.p1[0], target.p2[1] - target.p1[1]
    length = target.length; tx, ty = dx / length, dy / length
    nx, ny = -ty, tx
    qdx, qdy = observed.p2[0] - observed.p1[0], observed.p2[1] - observed.p1[1]
    # This is a perpendicular endpoint displacement in metres, not a
    # dimensionless angle: a long diagonal must not evade the axis tolerance.
    axis_error = abs(qdx * nx + qdy * ny)
    if axis_error > config.plan_axis_alignment_tol_m:
        return None
    tmid = ((target.p1[0] + target.p2[0]) / 2, (target.p1[1] + target.p2[1]) / 2)
    qmid = ((observed.p1[0] + observed.p2[0]) / 2, (observed.p1[1] + observed.p2[1]) / 2)
    position = abs((qmid[0] - tmid[0]) * nx + (qmid[1] - tmid[1]) * ny)
    if position > config.plan_position_tol_m:
        return None
    t0, t1 = sorted((target.p1[0] * tx + target.p1[1] * ty, target.p2[0] * tx + target.p2[1] * ty))
    q0, q1 = sorted((observed.p1[0] * tx + observed.p1[1] * ty, observed.p2[0] * tx + observed.p2[1] * ty))
    overlap = max(0.0, min(t1, q1) - max(t0, q0))
    if overlap <= 0:
        return None
    symmetric_difference = abs(t0 - q0) + abs(t1 - q1)
    return overlap, position, symmetric_difference


def match_plan_segments(*, targets: Iterable[PlanSegment], observations: Iterable[PlanSegment],
                        config: JudgeScoreConfigV1) -> tuple[tuple[SegmentScore, ...], dict[str, tuple[str, ...]]]:
    """Joint-cutpoint atomization (W3); coverage is a set operation with no tie.

    For each target, candidate observations (``_candidate`` success at the judge
    tolerance layer) are projected onto the target's support line; the union of
    all endpoints cuts the target span into atomic intervals, each attributed to
    the SET of observations covering it.  An interval covered by exactly one
    observation becomes matched length on that (target, observation) pair; an
    interval covered by none is a miss; an interval covered by more than one is
    a duplicate (counted once toward the target, reported separately so policy
    can route it to no_duplicate_wall_strokes without double-counting a wall).
    Observation length covering no target is extra.  Cross-document registration
    is product -> answer one-way via the judge tolerance (never reverse), and GT
    and product identity pools stay separate (C-1').  Because every interval is
    decided by set membership -- there is no assignment optimization and no tie
    to break -- ``score_match_ambiguous`` is structurally unreachable on this
    plan-wall path.  Returns (rows, observation_key -> sorted target keys it
    covers) so the score service can rebuild a multi-cover product_to_gt.
    """
    target_list = tuple(sorted(targets, key=_canonical_geometry))
    obs_list = tuple(sorted(observations, key=_canonical_geometry))
    rows: list[SegmentScore] = []
    obs_covered: dict[str, float] = {obs.key: 0.0 for obs in obs_list}
    obs_to_targets: dict[str, set[str]] = {obs.key: set() for obs in obs_list}
    for target in target_list:
        length = target.length
        if length == 0:
            continue
        dx, dy = target.p2[0] - target.p1[0], target.p2[1] - target.p1[1]
        tx, ty = dx / length, dy / length
        nx, ny = -ty, tx
        t0, t1 = sorted((target.p1[0] * tx + target.p1[1] * ty, target.p2[0] * tx + target.p2[1] * ty))
        candidates: list[tuple[PlanSegment, float, float, float, float]] = []
        cuts = {t0, t1}
        for obs in obs_list:
            metric = _candidate(target, obs, config)
            if metric is None:
                continue
            _overlap, position, _extent = metric
            qdx, qdy = obs.p2[0] - obs.p1[0], obs.p2[1] - obs.p1[1]
            axis_error = abs(qdx * nx + qdy * ny)
            o_lo, o_hi = sorted((obs.p1[0] * tx + obs.p1[1] * ty, obs.p2[0] * tx + obs.p2[1] * ty))
            lo, hi = max(o_lo, t0), min(o_hi, t1)
            if hi <= lo:
                continue
            candidates.append((obs, lo, hi, axis_error, position))
            cuts.add(lo)
            cuts.add(hi)
        exactly_one: dict[str, float] = {}
        miss_length = 0.0
        duplicate_length = 0.0
        for a, b in zip(sorted(cuts), sorted(cuts)[1:]):
            if b <= a:
                continue
            covering = [item for item in candidates if item[1] <= a and b <= item[2]]
            if not covering:
                miss_length += b - a
                continue
            for obs, _lo, _hi, _axis, _pos in covering:
                obs_covered[obs.key] += b - a
                obs_to_targets[obs.key].add(target.key)
            if len(covering) == 1:
                exactly_one[covering[0][0].key] = exactly_one.get(covering[0][0].key, 0.0) + (b - a)
            else:
                duplicate_length += b - a
        for obs, lo, hi, axis_error, position in candidates:
            cover = exactly_one.get(obs.key, 0.0)
            if cover <= 0.0:
                continue
            complete = axis_error <= config.claim_complete_epsilon_m and position <= config.claim_complete_epsilon_m
            within = axis_error <= config.plan_axis_alignment_tol_m and position <= config.plan_position_tol_m
            status = "complete" if complete else ("within_tolerance" if within else "miss")
            rows.append(SegmentScore(target, obs, status, axis_error, position, target.length - cover,
                                     eligible_units=cover))
        if miss_length > 0.0:
            rows.append(SegmentScore(target, None, "miss", None, None, None, eligible_units=miss_length))
        if duplicate_length > 0.0:
            rows.append(SegmentScore(target, None, "duplicate", None, None, None, eligible_units=duplicate_length))
    for obs in obs_list:
        extra = obs.length - obs_covered[obs.key]
        if extra > config.claim_complete_epsilon_m:
            rows.append(SegmentScore(None, obs, "extra", None, None, None, eligible_units=extra))
    observation_map = {key: tuple(sorted(values)) for key, values in obs_to_targets.items() if values}
    return tuple(rows), observation_map


def assign_plan_segments(*, targets: Iterable[PlanSegment], observations: Iterable[PlanSegment],
                         config: JudgeScoreConfigV1) -> SegmentAssignment:
    """Compatibility view of the joint-cutpoint match (W3).

    Returns matched pairs plus fully-unmatched targets/observations.  A target
    partially covered appears in ``matched`` (its covered pair), not in
    ``unmatched_targets``; only a target with no covering observation is
    unmatched.  ``score_match_ambiguous`` is structurally unreachable here.
    """
    target_list = tuple(sorted(targets, key=_canonical_geometry))
    obs_list = tuple(sorted(observations, key=_canonical_geometry))
    rows, _ = match_plan_segments(targets=target_list, observations=obs_list, config=config)
    matched = tuple(sorted(((row.target, row.observation) for row in rows
                            if row.target is not None and row.observation is not None),
                           key=lambda pair: _canonical_geometry(pair[0])))
    matched_target_keys = {row.target.key for row in rows if row.target is not None and row.observation is not None}
    matched_obs_keys = {row.observation.key for row in rows if row.target is not None and row.observation is not None}
    unmatched_targets = tuple(sorted((target for target in target_list if target.key not in matched_target_keys),
                                     key=_canonical_geometry))
    unmatched_observations = tuple(sorted((obs for obs in obs_list if obs.key not in matched_obs_keys),
                                          key=_canonical_geometry))
    return SegmentAssignment(matched, unmatched_targets, unmatched_observations)


def score_plan_segments(*, targets: Iterable[PlanSegment], observations: Iterable[PlanSegment],
                        config: JudgeScoreConfigV1) -> tuple[SegmentScore, ...]:
    """Materialize complete/within/miss/extra/duplicate rows via joint cutpoints (W3)."""
    rows, _ = match_plan_segments(targets=targets, observations=observations, config=config)
    return rows
