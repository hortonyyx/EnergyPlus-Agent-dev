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
    out = tuple((float(point[0]), float(point[1])) for point in vertices)
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


def extract_gt_plan_segments(gt: GroundTruthV3) -> tuple[PlanSegment, ...]:
    """Return exterior GT segments and exact-reverse-paired interior zone edges."""
    output: list[PlanSegment] = []
    for floor in gt.floors:
        output.extend(PlanSegment(segment.id, floor.id, tuple(segment.p1), tuple(segment.p2), (),
                                  tuple(ref.view_id for ref in segment.source_refs), True)
                      for segment in floor.boundary_segments)
        # C2 validation already proved tiling.  Deliberately use exact tuples:
        # snapping here would turn nearby walls into a fictional shared edge.
        directed: dict[tuple[Point, Point], list[str]] = {}
        exterior_edges = _edges(floor.footprint.exterior.vertices)
        for zone in floor.zones:
            for p1, p2 in _edges(zone.polygon.exterior.vertices):
                directed.setdefault(_edge_key(p1, p2), []).append(zone.id)
        consumed: set[tuple[Point, Point]] = set()
        for (p1, p2), owners in directed.items():
            if (p1, p2) in consumed:
                continue
            reverse = directed.get((p2, p1), [])
            if not reverse and _lies_on_exterior((p1, p2), exterior_edges):
                continue
            if reverse and _lies_on_exterior((p1, p2), exterior_edges):
                raise ScoreContractError("score_gt_identity_invalid", "scoring.input_identity",
                    context={"reason": "exterior_interior_topology_conflict", "floor_id": floor.id})
            if len(owners) != 1 or len(reverse) != 1:
                raise ScoreContractError("score_gt_identity_invalid", "scoring.input_identity",
                    context={"reason": "invalid_interior_edge_pair", "floor_id": floor.id})
            consumed.add((p1, p2)); consumed.add((p2, p1))
            zones = tuple(sorted((owners[0], reverse[0])))
            key = "interior:%s:%s:%s" % (floor.id, min(p1, p2), max(p1, p2))
            output.append(PlanSegment(key, floor.id, p1, p2, zones, (), False))
    return tuple(sorted(output, key=_canonical_geometry))


def _cell_polygon(cell) -> Sequence[Sequence[float]]:
    if cell.polygon is not None:
        return cell.polygon
    # This is a legacy field representation of an actual cell, not a floor bbox.
    return ((cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]), (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1]))


def extract_correction_plan_segments(geometry: CorrectedGeometryV3) -> tuple[PlanSegment, ...]:
    """Extract correction footprint and cell topology without a bbox reduction."""
    output: list[PlanSegment] = []
    for floor in geometry.floors:
        for number, (p1, p2) in enumerate(_edges(floor.footprint.vertices)):
            output.append(PlanSegment("%s:footprint:%d" % (floor.id, number), floor.id, p1, p2,
                                      (), ("correction:%s" % floor.id,), True))
        directed: dict[tuple[Point, Point], list[str]] = {}
        for cell in floor.cells:
            for p1, p2 in _edges(_cell_polygon(cell)):
                directed.setdefault((p1, p2), []).append(cell.id)
        consumed: set[tuple[Point, Point]] = set()
        for edge, owners in directed.items():
            reverse = directed.get((edge[1], edge[0]), [])
            if edge in consumed or len(owners) != 1 or len(reverse) != 1:
                continue
            consumed.add(edge); consumed.add((edge[1], edge[0]))
            output.append(PlanSegment("%s:interior:%s:%s" % (floor.id, min(edge), max(edge)), floor.id,
                                      edge[0], edge[1], tuple(sorted((owners[0], reverse[0]))),
                                      ("correction:%s" % floor.id,), False))
    return tuple(sorted(output, key=_canonical_geometry))


def coerce_plan_observations(observations: Iterable[PlanSegment | dict]) -> tuple[PlanSegment, ...]:
    """Typed dispatch adapter for reading observations; no v3 branch in legacy code."""
    rows: list[PlanSegment] = []
    for raw in observations:
        if isinstance(raw, PlanSegment):
            rows.append(raw); continue
        try:
            rows.append(PlanSegment(key=str(raw["id"]), floor_id=str(raw["floor_id"]),
                p1=(float(raw["p1"][0]), float(raw["p1"][1])), p2=(float(raw["p2"][0]), float(raw["p2"][1])),
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
