"""Judge-only planar segment extraction and deterministic matching (B4b-B).

The module intentionally works with actual polygon edges.  It has no rectangle
or ``W/D`` fallback: callers must give typed GT or typed correction geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import hypot
from typing import Iterable, Sequence

from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.judge.gt_schema import GroundTruthV3
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError


Point = tuple[float, float]


# RW-1 (representation-layer canonicalization, NOT a geometric tolerance).
# The scorer pairs edges by exact identity (==, <=).  Binary float spellings of
# the same decimal seam differ by a few ulp (8.059999999999999 vs 8.06 on the GT
# side; 0.1+0.2 vs 0.3 on the correction side), and that microscopic difference
# used to be read as a topology break while the upstream validator stayed GREEN.
# Canonicalization snaps every coordinate to the nearest multiple of this quantum
# once, at the scorer entry, on BOTH the GT and correction sides with the same
# function and parameter, so identical seams share one identity and every
# comparison afterwards stays exact -- no fuzzy match, no tolerance in pairing.
#
# Separation (probe-verified, AI_agent/logs/reviews/execution/2026-07-27_plan_segment_tjunction.md):
#   ulp at the 20 m survey range ~= 3.55e-15  ->  quantum / ulp ~= 281,
#   so a few-ulp spelling is absorbed;
#   a 1e-9 endpoint gap is 1000 quanta, so it stays a red topology break (L-c).
# This mirrors FACADE_VISIBILITY_DEPTH_EPSILON (A0_contract.md): it absorbs only
# IEEE-754 arithmetic noise, never a physical resolution.  Do not widen it.
_COORDINATE_QUANTUM = 1e-12


def _canonical_coord(value: float) -> float:
    # +0.0 collapses -0.0 to 0.0 so it can never poison a dict key or tuple compare.
    return round(value / _COORDINATE_QUANTUM) * _COORDINATE_QUANTUM + 0.0


def _canonical_point(point: Sequence[float]) -> Point:
    return (_canonical_coord(float(point[0])), _canonical_coord(float(point[1])))


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
    status: str  # complete | within_tolerance | miss | extra
    axis_alignment_error_m: float | None
    position_error_m: float | None
    extent_symmetric_difference_m: float | None


def _points(vertices: Sequence[Sequence[float]]) -> tuple[Point, ...]:
    # RW-1: canonicalize on entry so the same decimal seam (8.059999999999999 /
    # 8.06, 0.1+0.2 / 0.3) shares one identity before any exact comparison.
    out = tuple(_canonical_point(point) for point in vertices)
    if len(out) > 1 and out[0] == out[-1]:
        out = out[:-1]
    if len(out) < 3:
        raise ScoreContractError("score_gt_identity_invalid", "scoring.input_identity", context={"reason": "polygon_too_short"})
    return out


def _edges(vertices: Sequence[Sequence[float]]) -> tuple[tuple[Point, Point], ...]:
    ring = _points(vertices)
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

    Interior edges pair by exact collinear coverage so a T-junction (one long
    wall faced by several collinear short walls) tiles into one segment per
    facing zone instead of rejecting the document.  See ``_pair_interior_edges``
    for the exactness contract.
    """
    output: list[PlanSegment] = []
    for floor in gt.floors:
        output.extend(PlanSegment(segment.id, floor.id, _canonical_point(segment.p1), _canonical_point(segment.p2), (),
                                  tuple(ref.view_id for ref in segment.source_refs), True)
                      for segment in floor.boundary_segments)
        directed: dict[tuple[Point, Point], list[str]] = {}
        for zone in floor.zones:
            for p1, p2 in _edges(zone.polygon.exterior.vertices):
                directed.setdefault(_edge_key(p1, p2), []).append(zone.id)
        exterior_edges = _edges(floor.footprint.exterior.vertices)
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

    Interior cell edges pair through the same exact-coverage helper as the GT
    side (``_pair_interior_edges``), so a T-junction corridor wall enters the
    observation set instead of being silently dropped.  A genuine topology break
    (gap/overlap/imprecise endpoint) fails loudly with the product identity
    error rather than discarding observations.
    """
    output: list[PlanSegment] = []
    for floor in geometry.floors:
        exterior_edges = _edges(floor.footprint.vertices)
        for number, (p1, p2) in enumerate(exterior_edges):
            output.append(PlanSegment("%s:footprint:%d" % (floor.id, number), floor.id, p1, p2,
                                      (), ("correction:%s" % floor.id,), True))
        directed: dict[tuple[Point, Point], list[str]] = {}
        for cell in floor.cells:
            for p1, p2 in _edges(_cell_polygon(cell)):
                directed.setdefault((p1, p2), []).append(cell.id)
        for p1, p2, zones in _pair_interior_edges(directed, exterior_edges, floor.id,
                                                   identity_code="score_product_identity_invalid"):
            output.append(PlanSegment("%s:interior:%s:%s" % (floor.id, min(p1, p2), max(p1, p2)), floor.id,
                                      p1, p2, zones, ("correction:%s" % floor.id,), False))
    return tuple(sorted(output, key=_canonical_geometry))


def coerce_plan_observations(observations: Iterable[PlanSegment | dict]) -> tuple[PlanSegment, ...]:
    """Typed dispatch adapter for reading observations; no v3 branch in legacy code."""
    rows: list[PlanSegment] = []
    for raw in observations:
        if isinstance(raw, PlanSegment):
            # RW-1: re-canonicalize so an observation built upstream shares the
            # same coordinate identity as the GT/correction extraction path.
            rows.append(PlanSegment(raw.key, raw.floor_id, _canonical_point(raw.p1), _canonical_point(raw.p2),
                                    raw.zone_ids, raw.source_ids, raw.exterior)); continue
        try:
            rows.append(PlanSegment(key=str(raw["id"]), floor_id=str(raw["floor_id"]),
                p1=_canonical_point(raw["p1"]), p2=_canonical_point(raw["p2"]),
                zone_ids=tuple(str(x) for x in raw.get("zone_ids", ())),
                source_ids=tuple(str(x) for x in raw.get("source_ids", ())), exterior=bool(raw.get("exterior", True))))
        except (KeyError, TypeError, ValueError) as exc:
            raise ScoreContractError("score_product_identity_invalid", "scoring.input_identity", context={"reason": "invalid_plan_observation"}) from exc
    return tuple(rows)


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


def assign_plan_segments(*, targets: Iterable[PlanSegment], observations: Iterable[PlanSegment],
                         config: JudgeScoreConfigV1) -> SegmentAssignment:
    """Solve the specified global objective and reject any equal optimum.

    The search is deliberately exhaustive: C2 plan fixtures are small, and this
    makes the tie rule auditable rather than relying on a library's ordering.
    """
    ts = tuple(sorted(targets, key=_canonical_geometry)); os = tuple(sorted(observations, key=_canonical_geometry))
    choices: list[list[tuple[int, tuple[float, float, float]] | None]] = []
    for target in ts:
        choices.append([None] + [(index, metric) for index, observed in enumerate(os)
                                 if (metric := _candidate(target, observed, config)) is not None])
    solutions: list[tuple[tuple[int | None, ...], tuple[float, float, float, float]]] = []
    def visit(index: int, used: frozenset[int], selected: list[int | None], metrics: tuple[float, float, float, float]) -> None:
        if index == len(ts):
            solutions.append((tuple(selected), metrics)); return
        for choice in choices[index]:
            if choice is None:
                visit(index + 1, used, selected + [None], metrics); continue
            observed_index, (overlap, position, extent) = choice
            if observed_index not in used:
                visit(index + 1, used | {observed_index}, selected + [observed_index],
                      (metrics[0] + 1, metrics[1] + overlap, metrics[2] + position, metrics[3] + extent))
    visit(0, frozenset(), [], (0, 0.0, 0.0, 0.0))
    def equal(a, b):
        eps = config.opening_assignment_tie_epsilon
        return a[0] == b[0] and all(abs(a[i] - b[i]) <= eps for i in range(1, 4))
    def better(a, b):
        eps = config.opening_assignment_tie_epsilon
        if a[0] != b[0]: return a[0] > b[0]
        if abs(a[1] - b[1]) > eps: return a[1] > b[1]
        if abs(a[2] - b[2]) > eps: return a[2] < b[2]
        return a[3] < b[3] - eps
    best_metric = solutions[0][1]
    for _, metric in solutions[1:]:
        if better(metric, best_metric): best_metric = metric
    winners = [selection for selection, metric in solutions if equal(metric, best_metric)]
    if len(winners) != 1:
        raise ScoreContractError("score_match_ambiguous", "scoring.matching", context={"kind": "segment", "candidate_assignments": len(winners)})
    selected = winners[0]
    used = {index for index in selected if index is not None}
    return SegmentAssignment(tuple((target, os[index]) for target, index in zip(ts, selected) if index is not None),
                             tuple(target for target, index in zip(ts, selected) if index is None),
                             tuple(observed for index, observed in enumerate(os) if index not in used))


def score_plan_segments(*, targets: Iterable[PlanSegment], observations: Iterable[PlanSegment],
                        config: JudgeScoreConfigV1) -> tuple[SegmentScore, ...]:
    """Materialize §8.3 complete/within/miss/extra states after assignment."""
    assignment = assign_plan_segments(targets=targets, observations=observations, config=config)
    rows: list[SegmentScore] = []
    for target, observed in assignment.matched:
        metric = _candidate(target, observed, config)
        assert metric is not None
        axis, position, extent = metric[0] * 0.0, metric[1], metric[2]
        # axis was a candidate gate; recompute its metre value for audit.
        dx, dy = target.p2[0] - target.p1[0], target.p2[1] - target.p1[1]
        n = target.length; nx, ny = -dy / n, dx / n
        axis = abs((observed.p2[0] - observed.p1[0]) * nx + (observed.p2[1] - observed.p1[1]) * ny)
        complete = position <= config.claim_complete_epsilon_m and extent <= config.claim_complete_epsilon_m and axis <= config.claim_complete_epsilon_m
        within = position <= config.plan_position_tol_m and extent <= config.plan_extent_tol_m and axis <= config.plan_axis_alignment_tol_m
        rows.append(SegmentScore(target, observed, "complete" if complete else ("within_tolerance" if within else "miss"), axis, position, extent))
    rows.extend(SegmentScore(target, None, "miss", None, None, None) for target in assignment.unmatched_targets)
    rows.extend(SegmentScore(None, observation, "extra", None, None, None) for observation in assignment.unmatched_observations)
    return tuple(rows)
