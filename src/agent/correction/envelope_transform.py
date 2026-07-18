"""Pure, fail-closed v3 envelope transform transaction (C2 B2b)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Literal

from shapely.geometry import Polygon

from src.agent.correction.cell_geometry import cell_has_polygon, cell_polygon, cell_polygon_vertices, set_cell_polygon_vertices, validate_cell_polygon
from src.agent.correction.config import CoreTolerances
from src.agent.correction.envelope import AuthoritativeEnvelope, _FACADE_RE
from src.agent.correction.footprint import floor_footprint, floor_footprint_fingerprint, footprint_bbox
from src.agent.correction.geometry_validator import validate_corrected_geometry
from src.agent.correction.parse import ensure_corrected_geometry, validate_final_corrected_geometry
from src.agent.correction.schema import CorrectedGeometryV3, FootprintRing
from src.agent.correction.facade_visibility import (
    VisibilityTolerances,
    materialize_all_facade_segments,
)
from src.agent.correction.window_host import (
    WindowHostClaimsV1,
    WindowHostResolutionError,
    map_direction_binding_error,
    resolve_window_hosts,
)
from src.agent.correction.window_sources import (
    VerifiedWindowResolverInputs,
    WindowDirectionBindingError,
)

EnvelopeClaimKind = Literal["overall_bound", "wing_break_endpoint"]
EnvelopeAxis = Literal["x", "y"]
EnvelopeSide = Literal["lo", "hi", "internal"]
ResolutionStatus = Literal["accepted", "skipped", "conflict"]


@dataclass(frozen=True)
class EnvelopeMoveIntent:
    intent_id: str
    claim_kind: EnvelopeClaimKind
    axis: EnvelopeAxis
    side: EnvelopeSide
    old_value: float
    new_value: float
    source_facade: Literal["North", "South", "East", "West"]
    source_ids: tuple[str, ...]
    boundary_ref: str | None = None


@dataclass(frozen=True)
class AxisInterval:
    lo: float
    hi: float


@dataclass(frozen=True)
class VertexRef:
    owner_kind: Literal["footprint", "cell"]
    floor_id: str
    owner_id: str
    vertex_index: int


@dataclass(frozen=True)
class SharedAxisComponent:
    axis: EnvelopeAxis
    old_value: float
    new_value: float
    intervals: tuple[AxisInterval, ...]
    vertices: tuple[VertexRef, ...]


@dataclass(frozen=True)
class EnvelopeGateFinding:
    check_id: str
    ok: bool
    message: str = ""
    evidence: dict | None = None


@dataclass(frozen=True)
class EnvelopeTransactionResult:
    geom: CorrectedGeometryV3
    committed: bool
    transaction_id: str | None
    intent_ids: tuple[str, ...]
    failed_gate_id: str | None = None


class EnvelopeTransformRejected(ValueError):
    def __init__(self, gate_id: str, message: str, evidence: dict | None = None):
        super().__init__(message)
        self.gate_id = gate_id
        self.evidence = {} if evidence is None else dict(evidence)


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _intent_id(**data) -> str:
    return sha256(_canonical(data).encode()).hexdigest()


def _facade_for_axis(axis: str) -> set[str]:
    return {"North", "South"} if axis == "x" else {"East", "West"}


def resolve_envelope_move_intents(
    geom: CorrectedGeometryV3, envelope: AuthoritativeEnvelope, tol: CoreTolerances,
) -> tuple[EnvelopeMoveIntent, ...]:
    bbox = footprint_bbox(geom)
    intents: list[EnvelopeMoveIntent] = []
    for axis, bounds in (("x", bbox[0]), ("y", bbox[1])):
        resolution = envelope.axis(axis)
        if resolution is None or resolution.status != "accepted" or resolution.bounds is None:
            continue
        source = resolution.source
        match = _FACADE_RE.search(source.view) if source else None
        facade = match.group(1).capitalize() if match else ""
        if facade not in _facade_for_axis(axis):
            raise EnvelopeTransformRejected("correction.envelope_evidence_scope", "overall evidence facade does not own its world axis")
        for side, old, new in (("lo", bounds[0], resolution.bounds[0]), ("hi", bounds[1], resolution.bounds[1])):
            if abs(float(new) - float(old)) <= tol.output_precision_m:
                continue
            if abs(float(new) - float(old)) > tol.envelope_reconcile_tol_m:
                continue
            data = {"claim_kind": "overall_bound", "axis": axis, "side": side,
                    "old_value": float(old), "new_value": float(new), "source_facade": facade,
                    "source_ids": tuple(sorted({source.source_id} if source else set()))}
            intents.append(EnvelopeMoveIntent(intent_id=_intent_id(**data), boundary_ref=None, **data))
    axes = {"x": sorted({float(p[0]) for f in geom.floors for p in f.footprint.vertices}),
            "y": sorted({float(p[1]) for f in geom.floors for p in f.footprint.vertices})}
    for resolution in envelope.endpoint_resolutions:
        if resolution.status != "accepted" or resolution.evidence is None:
            continue
        evidence = resolution.evidence
        # The reading supplies the resolved endpoint; it may legitimately be
        # one facade reconciliation delta away from the current canonical axis
        # (the U fixture is 3.00 -> 3.10).  Uniqueness is still mandatory and
        # the actual correction stays bounded by ENVELOPE_RECONCILE_TOL below.
        candidates = [v for v in axes[evidence.world_axis] if abs(v - evidence.world_value) <= tol.envelope_reconcile_tol_m]
        if len(candidates) != 1:
            raise EnvelopeTransformRejected("correction.envelope_axis_attachment", "wing endpoint does not identify one shared axis", {"boundary_ref": evidence.boundary_ref, "matches": candidates})
        old = candidates[0]
        if abs(evidence.world_value - old) > tol.envelope_reconcile_tol_m:
            continue
        data = {"claim_kind": "wing_break_endpoint", "axis": evidence.world_axis, "side": "internal",
                "old_value": old, "new_value": evidence.world_value, "source_facade": evidence.facade,
                "source_ids": tuple(sorted({evidence.source_id, *resolution.corroborating_sources}))}
        intents.append(EnvelopeMoveIntent(intent_id=_intent_id(**data), boundary_ref=evidence.boundary_ref, **data))
    intents.sort(key=lambda i: (i.axis, i.old_value, i.new_value, i.intent_id))
    seen: dict[tuple[str, float], float] = {}
    targets: set[tuple[str, float]] = set()
    for intent in intents:
        key = (intent.axis, intent.old_value)
        if key in seen and seen[key] != intent.new_value:
            raise EnvelopeTransformRejected("correction.envelope_intent_consistency", "one shared axis has multiple target values")
        if (intent.axis, intent.new_value) in targets and intent.new_value != intent.old_value:
            raise EnvelopeTransformRejected("correction.envelope_intent_consistency", "two axes would collapse")
        seen[key] = intent.new_value
        targets.add((intent.axis, intent.new_value))
    return tuple(intents)


def _edges(points):
    return list(zip(points, points[1:] + points[:1]))


def _owner_points(owner) -> list[tuple[float, float]]:
    if isinstance(owner, FootprintRing):
        return [tuple(p) for p in owner.vertices]
    return cell_polygon_vertices(owner) or [
        (owner.x[0], owner.y[0]), (owner.x[1], owner.y[0]),
        (owner.x[1], owner.y[1]), (owner.x[0], owner.y[1]),
    ]


def _intervals_overlap(a: tuple[float, float], b: tuple[float, float], tol: CoreTolerances) -> bool:
    return max(a[0], b[0]) <= min(a[1], b[1]) + tol.envelope_axis_attach_tol_m


def _floor_axis_edges(floor, intent: EnvelopeMoveIntent, tol: CoreTolerances):
    """Planar graph input: footprint *and every cell* collinear edge.

    Each edge is deliberately retained with its owner.  The closure below is
    one-dimensional only (parallel edges on the constant axis), so a crossing
    horizontal/vertical edge cannot accidentally translate the whole floor.
    """
    idx, other = (0, 1) if intent.axis == "x" else (1, 0)
    owners = [("footprint", floor.id, floor.footprint), *[("cell", cell.id, cell) for cell in floor.cells]]
    out = []
    for kind, owner_id, owner in owners:
        for edge_index, (a, b) in enumerate(_edges(_owner_points(owner))):
            if (abs(a[idx] - intent.old_value) <= tol.envelope_axis_attach_tol_m
                    and abs(b[idx] - intent.old_value) <= tol.envelope_axis_attach_tol_m
                    and abs(a[other] - b[other]) > tol.envelope_axis_attach_tol_m):
                out.append((kind, owner_id, edge_index, tuple(sorted((float(a[other]), float(b[other]))))))
    return out


def _floor_component_intervals(floor, intent: EnvelopeMoveIntent, tol: CoreTolerances) -> list[AxisInterval]:
    edges = _floor_axis_edges(floor, intent, tol)
    idx = 0 if intent.axis == "x" else 1
    footprint = [edge for edge in edges if edge[0] == "footprint"]
    if intent.side in {"lo", "hi"}:
        values = [p[idx] for p in floor.footprint.vertices]
        boundary = min(values) if intent.side == "lo" else max(values)
        active = [edge[3] for edge in footprint if abs(boundary - intent.old_value) <= tol.envelope_axis_attach_tol_m]
    else:
        active = [edge[3] for edge in footprint]
    if not active:
        return []
    # T-junctions and overlap endpoints become graph nodes: repeatedly absorb
    # any owner edge touching the current interval closure.  This carries an
    # interior shared wall beyond a footprint-edge interval while keeping a
    # disconnected same-coordinate wall out of the component.
    changed = True
    while changed:
        changed = False
        for _kind, _owner, _edge, interval in edges:
            if any(_intervals_overlap(interval, current, tol) for current in active) and interval not in active:
                active.append(interval)
                changed = True
    active.sort()
    merged: list[list[float]] = []
    for lo, hi in active:
        if not merged or lo > merged[-1][1] + tol.envelope_axis_attach_tol_m:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    return [AxisInterval(lo, hi) for lo, hi in merged]


def _intervals_for_component(geom: CorrectedGeometryV3, intent: EnvelopeMoveIntent, tol: CoreTolerances) -> list[AxisInterval]:
    per_floor = [_floor_component_intervals(floor, intent, tol) for floor in geom.floors]
    if not per_floor or any(not intervals for intervals in per_floor):
        return []
    # Identical rings are required; a different per-floor graph closure means
    # the endpoint cannot be proven topologically identical across the stack.
    first = [(i.lo, i.hi) for i in per_floor[0]]
    if any([(i.lo, i.hi) for i in intervals] != first for intervals in per_floor[1:]):
        return []
    return [AxisInterval(lo, hi) for lo, hi in first]


def _on_component(point, axis: str, old: float, intervals: tuple[AxisInterval, ...], tol: CoreTolerances) -> bool:
    idx, other = (0, 1) if axis == "x" else (1, 0)
    return abs(float(point[idx]) - old) <= tol.envelope_axis_attach_tol_m and any(
        i.lo - tol.envelope_axis_attach_tol_m <= float(point[other]) <= i.hi + tol.envelope_axis_attach_tol_m for i in intervals
    )


def build_shared_axis_component(geom: CorrectedGeometryV3, intent: EnvelopeMoveIntent, tol: CoreTolerances) -> SharedAxisComponent:
    intervals = tuple(_intervals_for_component(geom, intent, tol))
    refs: list[VertexRef] = []
    for floor in geom.floors:
        for index, point in enumerate(floor.footprint.vertices):
            if _on_component(point, intent.axis, intent.old_value, intervals, tol):
                refs.append(VertexRef("footprint", floor.id, floor.id, index))
        for cell in floor.cells:
            points = cell_polygon_vertices(cell)
            if points is None:
                points = [(cell.x[0], cell.y[0]), (cell.x[1], cell.y[0]), (cell.x[1], cell.y[1]), (cell.x[0], cell.y[1])]
            for index, point in enumerate(points):
                if _on_component(point, intent.axis, intent.old_value, intervals, tol):
                    refs.append(VertexRef("cell", floor.id, cell.id, index))
    if not intervals or not any(r.owner_kind == "footprint" for r in refs) or not any(r.owner_kind == "cell" for r in refs):
        raise EnvelopeTransformRejected("correction.envelope_axis_attachment", "shared axis is not attached to both footprint and cells")
    return SharedAxisComponent(intent.axis, intent.old_value, intent.new_value, intervals, tuple(refs))


def cell_adjacency_signature(geom: CorrectedGeometryV3, tol: CoreTolerances) -> tuple[tuple[str, str, str], ...]:
    pairs = []
    for floor in geom.floors:
        cells = list(floor.cells)
        for idx, left in enumerate(cells):
            for right in cells[idx + 1:]:
                if cell_polygon(left).boundary.intersection(cell_polygon(right).boundary).length > tol.envelope_axis_attach_tol_m:
                    pairs.append((floor.id, *sorted((left.id, right.id))))
    return tuple(sorted(pairs))


def topology_signature(geom: CorrectedGeometryV3, tol: CoreTolerances) -> tuple:
    rings = []
    for floor in geom.floors:
        points = [tuple(p) for p in floor.footprint.vertices]
        turns = tuple((int((b[0]-a[0]) * (c[1]-b[1]) - (b[1]-a[1]) * (c[0]-b[0]) > 0) - int((b[0]-a[0]) * (c[1]-b[1]) - (b[1]-a[1]) * (c[0]-b[0]) < 0)) for a,b,c in zip(points[-1:]+points[:-1], points, points[1:]+points[:1]))
        rings.append((floor.id, len(points), turns, len(floor.cells), len(Polygon(points).interiors)))
    return tuple(rings), cell_adjacency_signature(geom, tol)


def check_shared_boundary_consistency(before: CorrectedGeometryV3, candidate: CorrectedGeometryV3, tol: CoreTolerances) -> EnvelopeGateFinding:
    ok = cell_adjacency_signature(before, tol) == cell_adjacency_signature(candidate, tol)
    return EnvelopeGateFinding("correction.shared_boundary_consistency", ok, "cell adjacency changed" if not ok else "")


def run_envelope_hard_gates(before: CorrectedGeometryV3, candidate: CorrectedGeometryV3, *,
                            intents: tuple[EnvelopeMoveIntent, ...], tol: CoreTolerances,
                            window_host_ok: bool,
                            window_host_message: str = "") -> tuple[EnvelopeGateFinding, ...]:
    findings: list[EnvelopeGateFinding] = []
    try:
        validate_final_corrected_geometry(candidate)
        findings.append(EnvelopeGateFinding("correction.envelope_ring_valid", True))
    except ValueError as exc:
        return (EnvelopeGateFinding("correction.envelope_ring_valid", False, str(exc)),)
    coverage = [f for f in validate_corrected_geometry(candidate) if f.check_id == "correction.coverage" and not f.ok]
    findings.append(EnvelopeGateFinding("correction.coverage", not coverage, "; ".join(f.message for f in coverage)))
    if coverage:
        return tuple(findings)
    shared = check_shared_boundary_consistency(before, candidate, tol)
    findings.append(shared)
    if not shared.ok:
        return tuple(findings)
    findings.append(EnvelopeGateFinding(
        "correction.window_host_unique", window_host_ok,
        window_host_message if not window_host_ok else "",
    ))
    if not findings[-1].ok:
        return tuple(findings)
    binding_ok = not candidate.facade_segments and all(w.facade_segment_id is None for w in candidate.windows)
    findings.append(EnvelopeGateFinding("correction.facade_segment_binding", binding_ok))
    if not binding_ok:
        return tuple(findings)
    identity_ok = (tuple(f.id for f in before.floors) == tuple(f.id for f in candidate.floors)
                   and tuple((w.id, w.floor_id, w.facade_segment_id) for w in before.windows) == tuple((w.id, w.floor_id, w.facade_segment_id) for w in candidate.windows)
                   and {c.id for f in before.floors for c in f.cells} == {c.id for f in candidate.floors for c in f.cells})
    findings.append(EnvelopeGateFinding("correction.envelope_identity_snapshot", identity_ok))
    if not identity_ok:
        return tuple(findings)
    bbox = footprint_bbox(candidate)
    bbox_ok = candidate.footprint_x == list(bbox[0]) and candidate.footprint_y == list(bbox[1]) and len({floor_footprint_fingerprint(candidate, f) for f in candidate.floors}) == 1
    findings.append(EnvelopeGateFinding("correction.envelope_bbox_projection", bbox_ok))
    if not bbox_ok:
        return tuple(findings)
    topology_ok = topology_signature(before, tol) == topology_signature(candidate, tol)
    findings.append(EnvelopeGateFinding("correction.envelope_topology_preserved", topology_ok))
    return tuple(findings)


def _materialize_axis_splits(points, component: SharedAxisComponent, tol: CoreTolerances):
    """Split collinear owner edges at planar-graph/T-junction endpoints."""
    idx, other = (0, 1) if component.axis == "x" else (1, 0)
    out = []
    for a, b in _edges(list(points)):
        out.append(tuple(a))
        if (abs(a[idx] - component.old_value) > tol.envelope_axis_attach_tol_m
                or abs(b[idx] - component.old_value) > tol.envelope_axis_attach_tol_m):
            continue
        lo, hi = sorted((a[other], b[other]))
        cuts = sorted({bound for interval in component.intervals for bound in (interval.lo, interval.hi)
                       if lo + tol.envelope_axis_attach_tol_m < bound < hi - tol.envelope_axis_attach_tol_m})
        for cut in cuts:
            values = list(a)
            values[idx] = component.old_value
            values[other] = cut
            out.append(tuple(values))
    return out


def _canonical_open_ccw(points, tol: CoreTolerances):
    """Drop only redundant vertices; keep deliberate transform kinks."""
    clean = []
    for point in points:
        if not clean or point != clean[-1]:
            clean.append(tuple(float(v) for v in point))
    if len(clean) > 1 and clean[0] == clean[-1]:
        clean.pop()
    changed = True
    while changed and len(clean) > 4:
        changed = False
        kept = []
        for index, point in enumerate(clean):
            prev, nxt = clean[index - 1], clean[(index + 1) % len(clean)]
            # A degree-2 point is redundant only when all three vertices remain
            # on one exact orthogonal line.  A materialized kink changes axis
            # and therefore survives this pass.
            if ((prev[0] == point[0] == nxt[0]) or (prev[1] == point[1] == nxt[1])):
                changed = True
                continue
            kept.append(point)
        clean = kept
    twice_area = sum(a[0] * b[1] - a[1] * b[0] for a, b in _edges(clean))
    if twice_area < 0:
        clean = [clean[0], *reversed(clean[1:])]
    return clean


def _apply_components(candidate: CorrectedGeometryV3, components: dict[str, SharedAxisComponent], tol: CoreTolerances) -> dict[str, list[str]]:
    moved = {"floor_vertex_refs": [], "cell_vertex_refs": [], "window_span_refs": [], "promoted_rect_cells_to_polygon": []}
    for component in components.values():
        idx = 0 if component.axis == "x" else 1
        for floor in candidate.floors:
            ring = []
            for n, point in enumerate(_materialize_axis_splits(floor.footprint.vertices, component, tol)):
                values = list(point)
                if _on_component(values, component.axis, component.old_value, component.intervals, tol):
                    values[idx] = component.new_value; moved["floor_vertex_refs"].append(f"{floor.id}:{n}")
                ring.append(tuple(values))
            floor.footprint = FootprintRing(vertices=_canonical_open_ccw(ring, tol))
            for cell in floor.cells:
                original_polygon = cell_has_polygon(cell)
                points = _materialize_axis_splits(_owner_points(cell), component, tol)
                changed = False; updated = []
                for n, point in enumerate(points):
                    values = list(point)
                    if _on_component(values, component.axis, component.old_value, component.intervals, tol):
                        values[idx] = component.new_value; changed = True; moved["cell_vertex_refs"].append(f"{floor.id}:{cell.id}:{n}")
                    updated.append(tuple(values))
                if changed:
                    updated = _canonical_open_ccw(updated, tol)
                    xs, ys = {p[0] for p in updated}, {p[1] for p in updated}
                    is_rect = len(updated) == 4 and len(xs) == 2 and len(ys) == 2
                    if original_polygon or not is_rect:
                        if not original_polygon: moved["promoted_rect_cells_to_polygon"].append(cell.id)
                        set_cell_polygon_vertices(cell, updated)
                    else:
                        cell.x, cell.y = [min(xs), max(xs)], [min(ys), max(ys)]
    for floor in candidate.floors:
        for cell in floor.cells:
            if cell_has_polygon(cell): validate_cell_polygon(cell, min_edge_length_m=tol.min_edge_length_m)
    bbox = footprint_bbox(candidate)
    candidate.footprint_x, candidate.footprint_y = list(bbox[0]), list(bbox[1])
    return moved


def _append_evidence_audit(geom: CorrectedGeometryV3, envelope: AuthoritativeEnvelope, tol: CoreTolerances) -> None:
    """Keep v3 skipped/conflict evidence as visible as the legacy branch."""
    bbox = footprint_bbox(geom)
    for axis, bounds in (("x", bbox[0]), ("y", bbox[1])):
        resolution = envelope.axis(axis)
        if resolution is None or resolution.status == "accepted":
            if resolution and resolution.bounds:
                delta = max(abs(resolution.bounds[0] - bounds[0]), abs(resolution.bounds[1] - bounds[1]))
                if delta > tol.envelope_reconcile_tol_m:
                    geom.unsupported.append({"target": f"{axis}.footprint", "axis": axis,
                                             "reason": f"authoritative envelope delta {delta:.3f} m exceeds ENVELOPE_RECONCILE_TOL {tol.envelope_reconcile_tol_m:.3f} m"})
            continue
        row = {"target": f"{axis}.footprint", "axis": axis, "reason": resolution.reason or f"facade envelope {resolution.status}"}
        (geom.conflicts if resolution.status == "conflict" else geom.unsupported).append(row)
    for resolution in envelope.endpoint_resolutions:
        if resolution.status == "conflict":
            geom.conflicts.append({"target": "building.per_floor_footprints", "reason": resolution.reason or "wing boundary evidence conflict",
                                   "boundary_ref": resolution.candidates[0].boundary_ref if resolution.candidates else None})
        elif resolution.status == "skipped":
            geom.unsupported.append({"target": "building.per_floor_footprints", "reason": resolution.reason or "wing boundary evidence skipped"})


def _conflict_shape(gate_id: str) -> tuple[str, str]:
    if gate_id in {"correction.window_host_unique", "correction.window_host_resolution", "correction.envelope_identity_snapshot", "correction.envelope_axis_attachment", "correction.envelope_schema_scope", "correction.envelope_evidence_scope"}:
        return "reference_or_identity_ambiguity", "numeric"
    if gate_id in {"correction.envelope_topology_preserved", "correction.envelope_ring_valid", "correction.shared_boundary_consistency", "correction.envelope_min_edge", "correction.envelope_notch_depth_authority"}:
        return "unsupported_geometry", "topology_identity"
    return "facade_plan_mismatch", "numeric"


def _dry_resolve_current_ring(
    geom: CorrectedGeometryV3,
    *,
    verified_window_inputs: VerifiedWindowResolverInputs,
    tol: CoreTolerances,
    phase: Literal["dry_pre_transform", "dry_post_transform"],
) -> WindowHostClaimsV1:
    visibility_tolerances = VisibilityTolerances(
        depth_epsilon_m=tol.facade_visibility_depth_epsilon_m,
        endpoint_epsilon_m=tol.facade_visibility_endpoint_epsilon_m,
    )
    transient_segments = materialize_all_facade_segments(
        geom, tolerances=visibility_tolerances,
    )
    dry_geom = geom.model_copy(
        deep=True, update={"facade_segments": list(transient_segments)},
    )
    try:
        return resolve_window_hosts(
            dry_geom, verified_inputs=verified_window_inputs,
            tolerances=tol, commit=False,
        )
    except WindowDirectionBindingError as exc:
        raise WindowHostResolutionError(
            map_direction_binding_error(
                exc, geom=dry_geom, verified_inputs=verified_window_inputs, phase=phase,
            ),
            phase=phase,
            context=exc.context,
        ) from exc


def _host_parity(before: WindowHostClaimsV1, after: WindowHostClaimsV1) -> bool:
    before_rows = {
        row.window_id: (row.floor_id, row.room_id, row.branch, row.facade_family)
        for row in before.resolutions
    }
    after_rows = {
        row.window_id: (row.floor_id, row.room_id, row.branch, row.facade_family)
        for row in after.resolutions
    }
    return before_rows == after_rows


def apply_v3_envelope_transaction(
    geom: CorrectedGeometryV3,
    tol: CoreTolerances,
    authoritative_envelope: AuthoritativeEnvelope,
    *,
    verified_window_inputs: VerifiedWindowResolverInputs | None = None,
) -> EnvelopeTransactionResult:
    before = CorrectedGeometryV3.model_validate(geom.model_dump())
    intent_ids: tuple[str, ...] = ()
    transaction_id: str | None = None
    try:
        # Phase A #1: strict v3/open rings/same per-floor contract.
        assert before.schema_version == "3"
        if any(f.footprint.vertices[0] == f.footprint.vertices[-1] for f in before.floors):
            raise EnvelopeTransformRejected("correction.envelope_schema_scope", "v3 floor footprint must be open")
        if len({floor_footprint_fingerprint(before, f) for f in before.floors}) != 1:
            raise EnvelopeTransformRejected("correction.envelope_schema_scope", "per-floor footprints are not identical")
        _append_evidence_audit(before, authoritative_envelope, tol)
        # Phase A #2/#3: evidence scope then deterministic intent consistency.
        intents = resolve_envelope_move_intents(before, authoritative_envelope, tol)
        intent_ids = tuple(i.intent_id for i in intents)
        if not intents:
            return EnvelopeTransactionResult(before, False, None, (), None)
        transaction_id = sha256(_canonical({"schema_version": "3", "before_fingerprints": sorted(floor_footprint_fingerprint(before, f) for f in before.floors), "intents": [asdict(i) for i in intents]}).encode()).hexdigest()
        # Phase A #4: reject post-Vg bindings before any candidate write.
        if before.facade_segments or any(w.facade_segment_id is not None for w in before.windows):
            raise EnvelopeTransformRejected("correction.facade_segment_binding", "post-Vg facade bindings cannot enter B2b transaction", {"segments": [s.id for s in before.facade_segments], "windows": [w.id for w in before.windows if w.facade_segment_id is not None]})
        if before.windows and verified_window_inputs is None:
            raise EnvelopeTransformRejected(
                "correction.window_host_resolution",
                "v3 windows require verified source-aware resolver inputs",
            )
        pre_hosts = (_dry_resolve_current_ring(
            before, verified_window_inputs=verified_window_inputs, tol=tol,
            phase="dry_pre_transform",
        ) if verified_window_inputs is not None else None)
        pre_host_by_window = {
            row.window_id: row for row in pre_hosts.resolutions
        } if pre_hosts is not None else {}
        # Phase A #5 then #6.
        components = {i.intent_id: build_shared_axis_component(before, i, tol) for i in intents}
        candidate = before.model_copy(deep=True)
        moved = _apply_components(candidate, components, tol)
        for window in candidate.windows:
            host = pre_host_by_window[window.id]
            for component in components.values():
                if component.axis == ("x" if window.facade in {"North", "South"} else "y"):
                    for n, endpoint in enumerate(window.span):
                        if (abs(endpoint - component.old_value) <= tol.envelope_axis_attach_tol_m
                                and host.room_boundary_interval.lo - tol.envelope_axis_attach_tol_m <= endpoint <= host.room_boundary_interval.hi + tol.envelope_axis_attach_tol_m
                                and any(i.lo - tol.envelope_axis_attach_tol_m <= endpoint <= i.hi + tol.envelope_axis_attach_tol_m for i in component.intervals)):
                            window.span[n] = component.new_value; moved["window_span_refs"].append(f"{window.id}:span[{n}]")
        for window in candidate.windows:
            if (window.span[1] - window.span[0] < tol.min_edge_length_m
                    or window.z[1] - window.z[0] < tol.min_edge_length_m):
                raise EnvelopeTransformRejected(
                    "correction.window_host_unique",
                    "window width or height falls below min_edge_length_m",
                    {"window": window.id, "span": list(window.span), "z": list(window.z)},
                )
            along_axis = "x" if window.facade in {"North", "South"} else "y"
            for intent in intents:
                if intent.claim_kind == "wing_break_endpoint" and intent.axis == along_axis:
                    if window.span[0] < intent.new_value < window.span[1]:
                        raise EnvelopeTransformRejected(
                            "correction.window_host_unique", "window span crosses wing break",
                            {"window": window.id, "boundary_ref": intent.boundary_ref},
                        )
        # Phase B deliberately happens after coordinate simulation and before audit.
        if topology_signature(before, tol) != topology_signature(candidate, tol):
            raise EnvelopeTransformRejected("correction.envelope_topology_preserved", "candidate topology changed")
        post_hosts = None
        if verified_window_inputs is not None:
            try:
                post_hosts = _dry_resolve_current_ring(
                    candidate, verified_window_inputs=verified_window_inputs,
                    tol=tol, phase="dry_post_transform",
                )
            except WindowHostResolutionError as exc:
                if any(
                    row.fallback_action == "invariant_no_geometry_commit" for row in exc.conflicts
                ):
                    raise
                raise EnvelopeTransformRejected(
                    "correction.window_host_resolution",
                    "post-transform source-aware host resolution failed",
                    {"conflicts": [row.model_dump(mode="json") for row in exc.conflicts]},
                ) from exc
        host_ok = pre_hosts is None or (post_hosts is not None and _host_parity(pre_hosts, post_hosts))
        findings = run_envelope_hard_gates(
            before, candidate, intents=intents, tol=tol,
            window_host_ok=host_ok,
            window_host_message="window source/room/facade host changed",
        )
        failed = next((f for f in findings if not f.ok), None)
        if failed:
            raise EnvelopeTransformRejected(failed.check_id, failed.message, failed.evidence)
        candidate.corrections.append({
            "rule_id": "deterministic_core.envelope_atomic_transform", "stage": "core", "target": "building.per_floor_footprints", "claim_type": "numeric", "transaction_id": transaction_id,
            "source_ids": sorted({s for i in intents for s in i.source_ids}),
            "original_value": {"footprint_fingerprints": {f.id: floor_footprint_fingerprint(before, f) for f in before.floors}, "bbox": {"x": list(footprint_bbox(before)[0]), "y": list(footprint_bbox(before)[1])}},
            "resolved_value": {"footprint_fingerprints": {f.id: floor_footprint_fingerprint(candidate, f) for f in candidate.floors}, "bbox": {"x": list(footprint_bbox(candidate)[0]), "y": list(footprint_bbox(candidate)[1])}},
            "value_type": "polygon", "intents": [{k: v for k, v in asdict(i).items() if k != "source_ids"} for i in intents],
            "moved": {k: sorted(v) for k, v in moved.items()}, "hard_gates": [{"check_id": f.check_id, "ok": f.ok} for f in findings],
            "tolerance_name": "ENVELOPE_RECONCILE_TOL", "tolerance_value": tol.envelope_reconcile_tol_m,
            "attachment_tolerance_name": "ENVELOPE_AXIS_ATTACH_TOL", "attachment_tolerance_value": tol.envelope_axis_attach_tol_m,
            "endpoint_match_tolerance_name": "ENVELOPE_ENDPOINT_MATCH_TOL", "endpoint_match_tolerance_value": tol.envelope_endpoint_match_tol_m, "changes_topology": False,
        })
        return EnvelopeTransactionResult(CorrectedGeometryV3.model_validate(candidate.model_dump()), True, transaction_id, intent_ids)
    except EnvelopeTransformRejected as exc:
        returned = before.model_copy(deep=True)
        conflict_type, claim_type = _conflict_shape(exc.gate_id)
        returned.conflicts.append({"rule_id": "deterministic_core.envelope_atomic_transform", "stage": "core", "target": "building.per_floor_footprints", "conflict_type": conflict_type, "claim_type": claim_type, "transaction_id": transaction_id, "intent_ids": list(intent_ids), "source_ids": [], "failed_gate_id": exc.gate_id, "reason_unresolved": str(exc), "evidence": exc.evidence, "fallback_action": "rollback_keep_original_geometry"})
        return EnvelopeTransactionResult(returned, False, transaction_id, intent_ids, exc.gate_id)
