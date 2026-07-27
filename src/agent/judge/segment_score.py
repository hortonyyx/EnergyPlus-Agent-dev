"""Judge-only planar segment extraction and deterministic matching (B4b-B).

The module intentionally works with actual polygon edges.  It has no rectangle
or ``W/D`` fallback: callers must give typed GT or typed correction geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import logging
from math import hypot
from typing import Iterable, Mapping, Sequence

from src.agent.correction.orthogonality import classify_edge_orthogonality
from src.agent.correction.schema import CorrectedGeometryV3
from src.agent.judge.gt_schema import GroundTruthV3
from src.agent.judge.score_schema import JudgeScoreConfigV1, ScoreContractError


Point = tuple[float, float]

_logger = logging.getLogger(__name__)


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
# §2.1 (controller ruling): the diameter cap MUST be <= the merge threshold.  A
# cap larger than merge (the prior 1e-11) lets a single-link chain of sub-merge
# gaps grow a cluster's diameter past the "same intent allowed spread" itself --
# three adjacent gaps each < merge can total 1.8e-12 > merge and still weld into
# one atom silently (contract ① violated, GREEN).  At diam = merge = 1e-12 a
# cluster may never span more than the very spread that defines "same intent".
_COORDINATE_DIAMETER_THRESHOLD = 1e-12  # cluster diameter cap (chain-bridge guard).

# R2-M1: per-target sub-interval sum tolerance.  The cut tiling partitions each
# target's [t0, t1] into matched/miss/duplicate sub-intervals whose lengths sum
# to target.length exactly in real arithmetic; the per-target conservation gate
# in match_plan_segments raises if they do not.  This absorbs ONLY floating-
# point accumulation in the three separate running sums (bounded by
# n_cuts * eps * length, well under 1e-12 for any realistic floor), so a dropped
# or inflated sub-interval -- a real cut-logic bug -- still lands as a loud
# reject.  This is NOT the observation over-charge window R2-M1 removed: that
# gate (_assert_obs_conservation) is strict (covered > obs_length, no window),
# because cover > length is geometrically impossible -- a sum of disjoint pieces
# of the observation's own projection can never exceed the projection, which is
# itself <= the obs length -- so any excess, however small, is the double-charge
# signature.  The prior 1e-9 slack there swallowed a real 5e-10 over-charge
# (sol live probe: covered=4.0000000005 on a 4.0 m wall) and turned a visible
# false red into a silent false green.  See R2-M1 in the r3 rework dispatch.
_SUBINTERVAL_SUM_TOL = 1e-9


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


def _cluster_axis(raw_values: Iterable[float], *, side: str, floor_id: str, axis: str) -> _AxisIdentity:
    """Single-link cluster with guard band + diameter guard (C-1 / C-1' / C-1'').

    Returns a raw -> representative mapping.  Raises ScoreContractError (an R-5
    neutral cause code) on a non-finite value, a gap inside the guard band
    (unresolvable ambiguity), or a cluster whose diameter exceeds the cap (a
    chain bridge).  Context always carries side/floor_id/axis and the hex
    binary64 of every value involved so the decision is reproducible from the
    sidecar alone.  The cause code is neutral (``score_identity_*``); the side
    (gt/product) lives in context["side"], NOT in the code -- a pairing failure
    (real topology break) still raises the side code score_*_identity_invalid.
    """
    values: list[float] = []
    for raw in raw_values:
        value = float(raw)
        if value != value or value == float("inf") or value == float("-inf"):
            raise ScoreContractError("score_identity_non_finite", "scoring.input_identity",
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
            raise ScoreContractError("score_identity_guard_band_ambiguity", "scoring.input_identity",
                context={"reason": "identity_guard_band_ambiguity", "side": side,
                    "floor_id": floor_id, "axis": axis, "gap": gap,
                    "merge": _COORDINATE_MERGE_THRESHOLD, "split": _COORDINATE_SPLIT_THRESHOLD,
                    "gap_hex": gap.hex(), "lo_hex": prev.hex(), "hi_hex": value.hex()})
    clusters.append((cur_min, cur_max))
    for lo, hi in clusters:
        diameter = hi - lo
        if diameter > _COORDINATE_DIAMETER_THRESHOLD:
            raise ScoreContractError("score_identity_chain_bridge", "scoring.input_identity",
                context={"reason": "identity_chain_bridge_over_diameter", "side": side,
                    "floor_id": floor_id, "axis": axis, "diameter": diameter,
                    "diameter_threshold": _COORDINATE_DIAMETER_THRESHOLD,
                    "diameter_hex": diameter.hex(), "lo_hex": lo.hex(), "hi_hex": hi.hex()})
    return _AxisIdentity(side, floor_id, axis, rep)


def _build_floor_identity(points: Iterable[Sequence[float]], *, side: str, floor_id: str,
                          ) -> tuple[_AxisIdentity, _AxisIdentity]:
    """Build the (x, y) identity pair for one document side on one floor."""
    materialized = tuple(points)
    x_id = _cluster_axis((float(p[0]) for p in materialized), side=side, floor_id=floor_id, axis="x")
    y_id = _cluster_axis((float(p[1]) for p in materialized), side=side, floor_id=floor_id, axis="y")
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
    raw = tuple((float(p[0]), float(p[1])) for p in vertices)
    out = tuple(_identify_point(point, x_id, y_id) for point in vertices)
    # Drop an EXPLICIT closing duplicate (first raw == last raw).  Keying this on
    # the raw points (not the identified reps) keeps it a pure ring-shape fix; a
    # genuine same-rep pair from two distinct vertices is the merge-collapse
    # reject below, handled separately so its context can name the real pair.
    if len(out) > 1 and raw[0] == raw[-1]:
        out, raw = out[:-1], raw[:-1]
    if len(out) < 3:
        raise ScoreContractError(identity_code, "scoring.input_identity",
            context={"reason": "polygon_too_short", "side": x_id.side, "floor_id": x_id.floor_id})
    # C-1''(4): identity merge must not collapse two distinct ring vertices into
    # one representative (zero-length edge).  R-5: record the ORIGINAL binary64
    # pair (both coords of both vertices) and the exact diameter, not just one
    # representative hex, so the merge decision is reproducible from the sidecar.
    ring_n = len(out)
    for idx in range(ring_n):
        first, second = out[idx], out[(idx + 1) % ring_n]
        if first == second:
            v1, v2 = raw[idx], raw[(idx + 1) % ring_n]
            diameter = hypot(v1[0] - v2[0], v1[1] - v2[1])
            raise ScoreContractError("score_identity_merge_collapse", "scoring.input_identity",
                context={"reason": "identity_merge_edge_collapse", "side": x_id.side,
                    "floor_id": x_id.floor_id, "axis": "xy",
                    "v1_hex": (v1[0].hex(), v1[1].hex()), "v2_hex": (v2[0].hex(), v2[1].hex()),
                    "diameter": diameter, "diameter_hex": diameter.hex()})
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
    diagnostics: list[_PairDiagnostic],
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
                    diagnostics.append(_PairDiagnostic(
                        category="identity", code=identity_code, gate_id="scoring.input_identity",
                        context={"reason": "exterior_interior_topology_conflict", "floor_id": floor_id}))
                    continue
                if len(forward_owners) != 1 or len(reverse_owners) != 1:
                    diagnostics.append(_PairDiagnostic(
                        category="identity", code=identity_code, gate_id="scoring.input_identity",
                        context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id}))
                    continue
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
                        diagnostics.append(_PairDiagnostic(
                            category="identity", code=identity_code, gate_id="scoring.input_identity",
                            context={"reason": "exterior_duplicate_owner", "floor_id": floor_id}))
                        continue
                    # single-owner exterior span: a legitimate boundary edge, not a wall
                else:
                    diagnostics.append(_PairDiagnostic(
                        category="identity", code=identity_code, gate_id="scoring.input_identity",
                        context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id}))
                    continue
            # else: open span with no edge on either side (e.g. a corridor mouth)
    return pairs


def _pair_general_edges(
    directed: dict[tuple[Point, Point], list[str]],
    exterior_edges: tuple[tuple[Point, Point], ...],
    floor_id: str,
    *,
    identity_code: str,
    diagnostics: list[_PairDiagnostic],
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
            diagnostics.append(_PairDiagnostic(
                category="identity", code=identity_code, gate_id="scoring.input_identity",
                context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id}))
            continue
        if len(owners) != 1 or len(rev_owners) != 1:
            diagnostics.append(_PairDiagnostic(
                category="identity", code=identity_code, gate_id="scoring.input_identity",
                context={"reason": "invalid_interior_edge_pair", "floor_id": floor_id}))
            consumed.add(edge)
            consumed.add(reverse)
            continue
        pairs.append((p1, p2, tuple(sorted((owners[0], rev_owners[0])))))
        consumed.add(edge)
        consumed.add(reverse)
    return pairs


def _log_advisory_hit(floor_id: str, p1: Point, p2: Point, *, unpaired: bool = False) -> None:
    """Record a near-orthogonal advisory edge in the runtime artifact (R-4 / §1.3).

    This is the runtime artifact for R-4's two-stage gating: a real run must be
    able to answer "did any near-orthogonal edge fire, and how many" before the
    advisory is allowed to flip to blocking.  A PAIRED advisory edge (exact
    reverse) is recorded as ``near_orthogonal_advisory_hit`` -- this batch only
    ADVISES (the edge is paired and scored normally).  An UNPAIRED advisory edge
    -- the exact shape that resolves as capability NA and that the later flip-to-
    blocking most needs to count -- is recorded as
    ``near_orthogonal_advisory_unpaired``.  Before r3 only the paired hits were
    logged, so the count was blind to precisely the edges that trigger NA.  The
    structured log carries the floor and the binary64 hex of both endpoints for
    reproducibility.
    """
    event = "near_orthogonal_advisory_unpaired" if unpaired else "near_orthogonal_advisory_hit"
    _logger.info(
        event,
        extra={"event": event, "floor_id": floor_id, "unpaired": unpaired,
               "p1_hex": (float(p1[0]).hex(), float(p1[1]).hex()),
               "p2_hex": (float(p2[0]).hex(), float(p2[1]).hex())},
    )


@dataclass(frozen=True)
class _PairDiagnostic:
    """One problem found while pairing interior edges, collected not raised.

    R2-B1: pairing problems are collected into a list and arbitrated AFTER all
    three buckets (advisory / orthogonal tile / general) have run, so a real
    topology break can never be masked by a capability NA (the r2 false-green:
    advisory ran first and its NA hid a true seam on the same floor).  The
    ``category`` is "identity" (a real topology break or a zone duplication) or
    "capability" (a shape the judge cannot measure).  ``code`` / ``gate_id`` /
    ``context`` reconstruct the exact ScoreContractError the prior raise would
    have thrown, so the arbitrator's chosen diagnostic is byte-identical to the
    pre-r2 behaviour for whichever diagnostic wins arbitration.
    """
    category: str
    code: str
    gate_id: str
    context: dict


def _pair_advisory_edges(
    advisory: dict[tuple[Point, Point], list[str]],
    floor_id: str,
    *,
    diagnostics: list[_PairDiagnostic],
) -> list[tuple[Point, Point, tuple[str, ...]]]:
    """Pair near-orthogonal advisory edges by exact reverse (W5 / R-4).

    Production admitted these edges (dx or dy in (0, 1e-9]) as axis-aligned, so
    the judge may NEVER brand them as a topology break -- that was the structural
    root of the false-red rounds (the judge convicting legal upstream geometry
    with its own exactness ceiling).  Each advisory edge pairs only with its
    EXACT reverse; a one-sided advisory edge, or one whose reverse carries a
    different near-axis spelling (5e-10 vs 4e-10), is a shape the judge's exact
    path cannot measure, so it resolves as capability NA
    (``score_unsupported_combination``), never ``score_*_identity_invalid``.  A
    successfully paired advisory edge is recorded (``_log_advisory_hit``) so
    R-4's later flip-to-blocking has a real-run signal to count.  Footprint and
    exterior rings are axis-aligned (validated upstream), so an advisory edge is
    never on the exterior here and no exterior/interior conflict check is needed.
    """
    pairs: list[tuple[Point, Point, tuple[str, ...]]] = []
    consumed: set[tuple[Point, Point]] = set()
    for edge, owners in advisory.items():
        if edge in consumed:
            continue
        p1, p2 = edge
        reverse = (p2, p1)
        rev_owners = advisory.get(reverse)
        if rev_owners is None or len(owners) != 1 or len(rev_owners) != 1:
            # R2-B1: collect, do not raise.  An unpaired advisory edge resolves
            # as capability NA, but that NA must be arbitrated AFTER the
            # orthogonal/general buckets so it can never mask a real seam on the
            # same floor.  §1.3: an unpaired advisory is ALSO recorded in the
            # runtime artifact -- the paired-hit-only log of r2 was blind to
            # exactly the edges that trigger NA, which are the ones R-4's later
            # flip-to-blocking most needs to count.
            _log_advisory_hit(floor_id, p1, p2, unpaired=True)
            diagnostics.append(_PairDiagnostic(
                category="capability", code="score_unsupported_combination",
                gate_id="scoring.capability",
                context={"reason": "near_orthogonal_advisory_unpaired", "floor_id": floor_id,
                         "edge_hex": (float(p1[0]).hex(), float(p1[1]).hex(),
                                      float(p2[0]).hex(), float(p2[1]).hex())}))
            continue
        _log_advisory_hit(floor_id, p1, p2)
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

    Edges are classified on the SHARED orthogonality yardstick (W5 / R-4) so the
    judge and the production validator can never disagree about a near-axis edge:
      * axis_aligned (exact 0) -- tiled at the union of all endpoints into
        elementary sub-intervals (``_tile_orthogonal_edges``).
      * near_orthogonal_advisory (0 < min(dx,dy) <= 1e-9) -- production admitted
        it, so the judge pairs it by exact reverse only; an unpaired one is a
        shape the judge cannot measure and resolves as capability NA, NEVER as a
        topology break (``_pair_advisory_edges``).  Each hit is recorded so a
        real run can answer "did this fire" (R-4 two-stage gating; advisory-only
        now, not yet flipped to blocking).
      * non_orthogonal (both > 1e-9) -- production rejects it, so a general-seam
        failure here IS a real topology break (``_pair_general_edges``).
    All coordinates are canonicalized at the scorer entry (RW-1), so every
    comparison below is exact (``==`` / ``<=``); a gap, an overlap, or an
    imprecise endpoint is a real topology break, not a T-junction, and is rejected.
    """
    ortho: dict[tuple[Point, Point], list[str]] = {}
    general: dict[tuple[Point, Point], list[str]] = {}
    advisory: dict[tuple[Point, Point], list[str]] = {}
    for edge, owners in directed.items():
        p1, p2 = edge
        cls = classify_edge_orthogonality(p2[0] - p1[0], p2[1] - p1[1])
        if cls == "axis_aligned":
            ortho[edge] = owners
        elif cls == "near_orthogonal_advisory":
            advisory[edge] = owners
        else:  # non_orthogonal
            general[edge] = owners
    # R2-B1: COLLECT, then ARBITRATE (controller dead-frame, not a re-ordering).
    # The three buckets run to completion appending diagnostics into one list;
    # the arbitrator decides which diagnostic wins.  This is the only structure
    # that closes both faces of the disease:
    #   * advisory-first (r2) raised capability NA at the first unpaired
    #     advisory edge, MASKING any real seam on the same floor -> false green.
    #   * tile-first (the "obvious" swap) re-raises a DERIVATIVE
    #     exterior_duplicate_owner the advisory lean perturbed onto a neighbour
    #     span ("second face"); same disease, different code.
    # Collect-then-arbitrate lets a real topology break outrank the NA without
    # letting the derivative convict the wrong span.  See
    # ``_arbitrate_pairing_diagnostics`` for the priority rule.
    diagnostics: list[_PairDiagnostic] = []
    pairs = list(_pair_advisory_edges(advisory, floor_id, diagnostics=diagnostics))
    pairs.extend(_tile_orthogonal_edges(ortho, exterior_edges, floor_id,
                                        identity_code=identity_code, diagnostics=diagnostics))
    pairs.extend(_pair_general_edges(general, exterior_edges, floor_id,
                                     identity_code=identity_code, diagnostics=diagnostics))
    _arbitrate_pairing_diagnostics(diagnostics, identity_code=identity_code)
    return pairs


# Reasons that are ALWAYS a real topology break, independent of any advisory
# edge: an interior edge with no facing pair, or an exterior/interior conflict
# on one span.  These outrank capability NA unconditionally (R2-B1 / §1.2).
#
# Order = within-class precision (§1.2 step 3 "closest to root cause"): an
# ``exterior_interior_topology_conflict`` is a STRUCTURAL, located violation --
# a zone crossing the footprint boundary, so two zones claim an interior edge
# that lies ON the exterior.  An ``invalid_interior_edge_pair`` is the generic
# "this interior edge has no facing pair / wrong owner count", which is very
# often a DOWNSTREAM SYMPTOM of that same misplaced zone (its other edges then
# dangle).  When a zone is pushed outside the footprint BOTH fire -- the
# boundary-crossing span raises the conflict, and the zone's dangling edges
# raise invalid_interior_edge_pair -- so the located, structural reason must win
# to report the root cause, not the derivative.  This is consistent with §1.2's
# example (a real seam's invalid_interior_edge_pair outranks an advisory-
# perturbed exterior_duplicate_owner): in both cases the independent root cause
# beats the derivative symptom.  (exterior_duplicate_owner is NOT in this set --
# it is advisory-derivative and routes to NA / step 3.)
_REAL_BREAK_REASONS = ("exterior_interior_topology_conflict", "invalid_interior_edge_pair")


def _arbitrate_pairing_diagnostics(diagnostics: list[_PairDiagnostic], *, identity_code: str) -> None:
    """R2-B1 priority rule over collected pairing diagnostics (§1.2 dead-frame).

    Hard rule: a real topology/identity break may NEVER be masked by a capability
    NA -- "the judge cannot measure this" loses to "the geometry is genuinely
    broken" every time.  Concretely:

      1. ANY real-break identity diagnostic (``exterior_interior_topology_
         conflict`` / ``invalid_interior_edge_pair``) wins -> the round ends red
         on the side identity code.  Within this class the located, structural
         reason is preferred over the generic one (``exterior_interior_topology_
         conflict`` -- a zone crossing the footprint boundary -- beats
         ``invalid_interior_edge_pair`` -- a dangling edge that is usually a
         downstream symptom of that same misplaced zone) -- §1.2 step 3.
      2. Else, if a capability NA exists, the round ends NA.  This is the ONLY
         path a capability NA may take: zero real breaks.
      3. Else an ``exterior_duplicate_owner`` with NO advisory present is a real
         zone duplication over the footprint (RW-3 silent-green hole) and stays
         red.

    ``exterior_duplicate_owner`` is deliberately NOT a real-break reason: a near-
    orthogonal advisory edge's lean (sub-1e-9) perturbs the endpoint of a
    neighbour exterior span, and two cells whose shared advisory wall carries
    different lean spellings (5e-10 vs 4e-10) then overlap on that exterior span
    by ~1e-10 -- a derivative of the unpaired advisory, not an independent zone
    duplication.  Routing that derivative to NA (step 2) is what keeps the R-4
    live counter-example (production five-way GREEN, shared advisory wall)
    resolving as capability NA while a TRUE seam plus the same advisory still
    ends red (the real break in step 1 wins).  A genuine zone duplication has no
    unpaired advisory on the floor, so it falls through to step 3.
    """
    real_breaks = [d for d in diagnostics if d.category == "identity"
                   and d.context.get("reason") in _REAL_BREAK_REASONS]
    if real_breaks:
        for preferred in _REAL_BREAK_REASONS:
            for diag in real_breaks:
                if diag.context.get("reason") == preferred:
                    raise ScoreContractError(identity_code, "scoring.input_identity", context=dict(diag.context))
    capability = [d for d in diagnostics if d.category == "capability"]
    if capability:
        diag = capability[0]
        raise ScoreContractError(diag.code, diag.gate_id, context=dict(diag.context))
    ambiguous = [d for d in diagnostics if d.category == "identity"]
    if ambiguous:
        diag = ambiguous[0]
        raise ScoreContractError(identity_code, "scoring.input_identity", context=dict(diag.context))


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
        x_id, y_id = _build_floor_identity(raw_points, side="gt", floor_id=floor.id)
        boundary_seen: set[tuple] = set()
        for segment in floor.boundary_segments:
            q1 = _identify_point(segment.p1, x_id, y_id)
            q2 = _identify_point(segment.p2, x_id, y_id)
            # C-1''(4): a boundary segment whose endpoints weld together is a
            # zero-length exterior edge; two boundary segments that weld to the
            # SAME geometry are a duplicate exterior owner.  Both are loud rejects.
            if q1 == q2:
                raise ScoreContractError("score_identity_merge_collapse", "scoring.input_identity",
                    context={"reason": "identity_boundary_segment_collapse", "side": "gt",
                        "floor_id": floor.id, "segment": segment.id,
                        "v1_hex": (float(segment.p1[0]).hex(), float(segment.p1[1]).hex()),
                        "v2_hex": (float(segment.p2[0]).hex(), float(segment.p2[1]).hex())})
            geom = (floor.id, min(q1, q2), max(q1, q2))
            if geom in boundary_seen:
                raise ScoreContractError("score_identity_merge_collapse", "scoring.input_identity",
                    context={"reason": "identity_boundary_duplicate_after_merge", "side": "gt",
                        "floor_id": floor.id, "segment": segment.id})
            boundary_seen.add(geom)
            output.append(PlanSegment(segment.id, floor.id, q1, q2, (),
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
        x_id, y_id = _build_floor_identity(raw_points, side="product", floor_id=floor.id)
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
        x_id, y_id = _build_floor_identity(points, side="product", floor_id=floor_id)
        for row in group:
            q1 = _identify_point(row.p1, x_id, y_id)
            q2 = _identify_point(row.p2, x_id, y_id)
            # C-1''(4): identity merge must not collapse a reading observation
            # to a zero-length segment ((0,0)->(5e-13,0) welds to a point).  This
            # is a loud reject, never a silent drop.
            if q1 == q2:
                raise ScoreContractError("score_identity_merge_collapse", "scoring.input_identity",
                    context={"reason": "identity_reading_segment_collapse", "side": "product",
                        "floor_id": floor_id, "observation": row.key,
                        "v1_hex": (float(row.p1[0]).hex(), float(row.p1[1]).hex()),
                        "v2_hex": (float(row.p2[0]).hex(), float(row.p2[1]).hex())})
            output.append(PlanSegment(row.key, row.floor_id, q1, q2, row.zone_ids, row.source_ids, row.exterior))
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


def _support_line_key(segment: PlanSegment) -> tuple[str, str, float]:
    """The geometric supporting line of a segment: (floor_id, axis, const).

    axis is "V" (vertical, x = const) when the segment runs more vertically,
    "H" (horizontal, y = const) otherwise.  Coordinates are already clustered to
    atomic representatives, so two targets on the same wall share an exactly
    equal const.  A near-orthogonal edge never reaches this axis-aligned path:
    it is resolved as unsupported (R-4 / W5) before pairing.
    """
    if abs(segment.p2[0] - segment.p1[0]) <= abs(segment.p2[1] - segment.p1[1]):
        return (segment.floor_id, "V", segment.p1[0])
    return (segment.floor_id, "H", segment.p1[1])


def _assert_target_conservation(target_key: str, length: float, matched_cover: float,
                                miss_length: float, duplicate_length: float) -> None:
    """B-1 / R2-M1 #2 per-target conservation hard gate.

    The cut tiling partitions each target's [t0, t1] into matched / miss /
    duplicate sub-intervals, so matched_cover + miss_length + duplicate_length
    must equal the target length exactly in real arithmetic.  A dropped or
    inflated sub-interval -- a cut-logic bug that silently mis-accounts the
    target's length (understating failing, or inventing passing/duplicate) --
    lands here as a loud reject: the denominator may never be quietly reshaped.
    The micro-tolerance absorbs ONLY FP accumulation in the three running sums;
    it is not an over-charge slack (the obs-level gate is strict, no window).
    """
    accounted = matched_cover + miss_length + duplicate_length
    if abs(accounted - length) > _SUBINTERVAL_SUM_TOL:
        raise ScoreContractError("score_denominator_nonconserving", "scoring.denominator_totality",
            context={"reason": "target_subintervals_do_not_tile", "target": target_key,
                     "target_length": length, "accounted_length": accounted, "deficit": length - accounted})


def _assert_obs_conservation(obs_key: str, obs_length: float, covered: float) -> None:
    """B-1 / R2-M1 conservation hard gate: an observation's charged cover may
    never exceed its own length -- STRICT, no tolerance window.

    ``covered`` is a sum of disjoint sub-intervals of the observation's own
    projection onto its registered support line, so in exact arithmetic it can
    never exceed that projection, which is itself <= the obs length.  ``covered
    > obs_length`` is therefore geometrically impossible -- it is the exact
    signature of a product wall charging length on two OVERLAPPING answer spans
    on the same support line (the 4 m wall that earned 6 m / 8 m).  R2-M1 removed
    the prior ``+ tol`` window: that window (1e-9) swallowed a real 5e-10
    over-charge (sol live probe: covered=4.0000000005 on a 4.0 m wall) and the
    negative extra was then silently dropped by ``extra > epsilon``, turning a
    visible false red into a silent false green.  The gate is now strict: any
    excess, however small, raises.  ``covered == obs_length`` (a single obs
    exactly spanning its registered targets) is the geometric equality and does
    not fire.
    """
    if covered > obs_length:
        raise ScoreContractError("score_denominator_nonconserving", "scoring.denominator_totality",
            context={"reason": "observation_cover_exceeds_length", "observation": obs_key,
                     "obs_length": obs_length, "covered": covered, "excess": covered - obs_length})


def match_plan_segments(*, targets: Iterable[PlanSegment], observations: Iterable[PlanSegment],
                        config: JudgeScoreConfigV1) -> tuple[tuple[SegmentScore, ...], dict[str, tuple[str, ...]]]:
    """Joint-cutpoint atomization with one-way support-line registration (W3/B-1).

    Coverage is a set operation with no tie, so ``score_match_ambiguous`` is
    structurally unreachable on this plan-wall path.  Three ordered steps
    (controller dead-frame, not advisory):

    1. ONE-WAY REGISTRATION (product -> answer, never reverse): each observation
       resolves the UNIQUE answer support line it belongs to.  Candidates are
       answer support lines for which ``_candidate`` succeeds (judge tolerance +
       positive projection overlap).  Exactly 1 -> registered.  0 -> the
       observation covers nothing (extra).  >= 2 -> the judge's own position
       tolerance cannot separate two parallel answer walls, so it LOUD-rejects
       (score_identity_support_ambiguous) -- never "take nearest", never "count
       both", never "first sorted": the ruler is being deformed by what it
       measures, and R-4 says say unsupported, not decide for the user.
    2. JOINT CUTPOINT per target (the existing set operation), but only the
       observations registered to that target's support line may participate --
       so one observation can never charge length on two parallel lines.
    3. CONSERVATION hard gates (R2-M1, both strict):
       (a) PER-TARGET: matched + miss + duplicate == target.length (the cut
           tiling partitions the target exactly) -- else raise.
       (b) PER-OBSERVATION: charged cover <= obs length, STRICT with NO
           tolerance window (cover > length is geometrically impossible -- the
           double-charge signature); a negative extra can therefore never again
           be swallowed by ``extra > epsilon`` (the r0 false-green shape).

    Returns (rows, observation_key -> sorted target keys it covers).
    """
    target_list = tuple(sorted(targets, key=_canonical_geometry))
    obs_list = tuple(sorted(observations, key=_canonical_geometry))
    # B-1 step 1: register each observation to its UNIQUE answer support line.
    obs_support: dict[str, tuple[str, str, float]] = {}
    for obs in obs_list:
        if obs.length == 0:
            continue
        eligible_lines: set[tuple[str, str, float]] = set()
        for target in target_list:
            if target.length == 0 or target.floor_id != obs.floor_id:
                continue
            if _candidate(target, obs, config) is None:
                continue
            eligible_lines.add(_support_line_key(target))
        if not eligible_lines:
            continue  # 0 candidate lines: observation covers no target -> extra
        if len(eligible_lines) >= 2:
            raise ScoreContractError("score_identity_support_ambiguous", "scoring.input_identity",
                context={"reason": "observation_eligible_for_multiple_support_lines",
                         "observation": obs.key, "side": "product",
                         "support_lines": sorted(line for line in eligible_lines)})
        obs_support[obs.key] = next(iter(eligible_lines))
    # B-1 step 2: per-target joint cutpoint; only observations registered to this
    # target's support line may participate.
    rows: list[SegmentScore] = []
    obs_covered: dict[str, float] = {obs.key: 0.0 for obs in obs_list}
    obs_to_targets: dict[str, set[str]] = {obs.key: set() for obs in obs_list}
    for target in target_list:
        length = target.length
        if length == 0:
            continue
        target_line = _support_line_key(target)
        dx, dy = target.p2[0] - target.p1[0], target.p2[1] - target.p1[1]
        tx, ty = dx / length, dy / length
        nx, ny = -ty, tx
        t0, t1 = sorted((target.p1[0] * tx + target.p1[1] * ty, target.p2[0] * tx + target.p2[1] * ty))
        candidates: list[tuple[PlanSegment, float, float, float, float]] = []
        cuts = {t0, t1}
        for obs in obs_list:
            if obs.length == 0 or obs_support.get(obs.key) != target_line:
                continue
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
        sorted_cuts = sorted(cuts)
        for a, b in zip(sorted_cuts, sorted_cuts[1:]):
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
        # R2-M1 #2: per-target sub-interval conservation hard gate.  The cut
        # tiling partitions this target's [t0, t1] into matched (exactly_one) /
        # miss / duplicate sub-intervals, so matched + miss + duplicate must equal
        # target.length exactly in real arithmetic.  A dropped or inflated sub-
        # interval (a cut-logic bug that silently mis-accounts the target's
        # length, understating failing or inventing passing) lands here as a loud
        # reject -- the denominator may never be quietly reshaped.
        _assert_target_conservation(target.key, length, sum(exactly_one.values()), miss_length, duplicate_length)
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
    # B-1 step 3 / R2-M1: conservation hard gate (strict, no window) + extra rows.
    # covered <= obs.length is guaranteed by the gate, so extra >= 0 here and a
    # negative extra can never again be swallowed by ``extra > epsilon`` (the r0
    # false-green shape: extra = 4 - 8 = -4 silently dropped).
    for obs in obs_list:
        if obs.length == 0:
            continue
        covered = obs_covered[obs.key]
        _assert_obs_conservation(obs.key, obs.length, covered)
        extra = obs.length - covered
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
