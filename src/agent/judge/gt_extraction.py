"""Manifest-bound, read-only DXF plan extraction for the GT v3 tooling.

This is deliberately only the Phase B plan core.  It creates a strict internal
``PlanExtractionResult``; segment/opening/elevation materialisation remains a
later phase and this module never writes a GT asset.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

import ezdxf
from ezdxf import bbox
from ezdxf.entities import DXFTagStorage
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize_full, unary_union

from src.agent.correction.footprint import footprint_fingerprint

from .gt_manifest import (EntitySelectorV1, GtExtractionManifestV1,
                          PlanViewBindingV1, validate_manifest_view_clips)
from .gt_schema import (DxfHandle, GtEntityRefV3, GtImplementationHashesV1,
                        GtPolygonV3, GtResolvedToolingConfigV1,
                        GtSourceDocumentV3, GtSourceViewV3, GtRingV3,
                        Hex64, JsonValue, StableId, StrictNonNegativeInt)


class ExtractionError(ValueError):
    """Stable, concise failure code for a fail-closed extraction condition."""


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DxfInspectionIssueV1(_StrictModel):
    code: str
    severity: Literal["BLOCK", "UNBOUND", "INFO"]
    view_id: StableId | None
    entity_handles: list[DxfHandle] = Field(default_factory=list)
    context: dict[str, JsonValue] = Field(default_factory=dict)


class DxfViewInspectionV1(_StrictModel):
    view_id: StableId
    kind: Literal["plan", "elevation", "unbound_cluster"]
    entity_count_by_type: dict[str, StrictNonNegativeInt]
    entity_count_by_layer: dict[str, StrictNonNegativeInt]
    matched_handles: list[DxfHandle]
    polygon_count: StrictNonNegativeInt
    dangle_count: StrictNonNegativeInt
    cut_count: StrictNonNegativeInt
    invalid_ring_count: StrictNonNegativeInt


class DxfInspectionReportV1(_StrictModel):
    report_version: Literal[1]
    status: Literal["PASS", "UNBOUND", "BLOCKED"]
    source_dxf_sha256: Hex64
    native_units_observed: str
    manifest_sha256: Hex64 | None
    judge_config_sha256: Hex64
    vg_config_sha256: Hex64
    proxy_entity_count: StrictNonNegativeInt
    views: list[DxfViewInspectionV1]
    issues: list[DxfInspectionIssueV1]


@dataclass(frozen=True)
class InspectionInputs:
    dxf_path: Path
    manifest: GtExtractionManifestV1 | None
    tooling: GtResolvedToolingConfigV1
    implementation_hashes: GtImplementationHashesV1


@dataclass(frozen=True)
class ExtractionInputs:
    dxf_path: Path
    manifest: GtExtractionManifestV1
    tooling: GtResolvedToolingConfigV1
    implementation_hashes: GtImplementationHashesV1


@dataclass(frozen=True)
class PlanZoneExtraction:
    id: str
    name: str
    role: str
    polygon: GtPolygonV3
    source_refs: tuple[GtEntityRefV3, ...]


@dataclass(frozen=True)
class PlanFloorExtraction:
    id: str
    name: str
    z_floor_m: float
    ceiling_height_m: float
    footprint: GtPolygonV3
    footprint_fingerprint: str
    zones: tuple[PlanZoneExtraction, ...]
    boundary_edge_sources: Mapping[tuple[tuple[float, float], tuple[float, float]], tuple[GtEntityRefV3, ...]]


@dataclass(frozen=True)
class PlanExtractionResult:
    case: str
    source: GtSourceDocumentV3
    floors: tuple[PlanFloorExtraction, ...]


_UNITS = {0: "unitless", 1: "in", 2: "ft", 4: "mm", 5: "cm", 6: "m"}
_UNIT_SCALE = {"m": 1.0, "mm": 0.001, "cm": 0.01, "in": 0.0254, "ft": 0.3048}
_SEVERITY = {"BLOCK": 0, "UNBOUND": 1, "INFO": 2}


def _fail(code: str) -> None:
    raise ExtractionError(code)


def _handle(entity) -> str:
    return str(entity.dxf.handle).upper()


def _inside(point: tuple[float, float], view: PlanViewBindingV1) -> bool:
    box = view.clip_box_dxf
    return box.xmin < point[0] < box.xmax and box.ymin < point[1] < box.ymax


def _clip_membership(point: tuple[float, float], view: PlanViewBindingV1) -> Literal["inside", "edge", "outside"]:
    box = view.clip_box_dxf
    if point[0] in (box.xmin, box.xmax) or point[1] in (box.ymin, box.ymax):
        return "edge"
    return "inside" if _inside(point, view) else "outside"


def _entity_points(entity) -> list[tuple[float, float]]:
    kind = entity.dxftype()
    if kind == "LINE":
        return [(float(entity.dxf.start.x), float(entity.dxf.start.y)),
                (float(entity.dxf.end.x), float(entity.dxf.end.y))]
    if kind == "LWPOLYLINE":
        if entity.has_arc:
            _fail("dxf_bulge_unsupported")
        return [(float(x), float(y)) for x, y, *_ in entity.get_points("xy")]
    if kind == "POLYLINE":
        return [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
    _fail("dxf_entity_type_unsupported")


def _selector_entities(msp, selector: EntitySelectorV1, view: PlanViewBindingV1) -> list:
    selected = []
    wanted = set(selector.handles)
    for entity in msp:
        if entity.dxftype() not in selector.entity_types or entity.dxf.layer not in selector.layers:
            continue
        if selector.handle_mode == "only_listed" and _handle(entity) not in wanted:
            continue
        points = _entity_points(entity)
        if not points:
            _fail("dxf_empty_entity")
        membership = [_clip_membership(point, view) for point in points]
        if "edge" in membership:
            _fail("dxf_entity_clip_boundary")
        if "inside" in membership and "outside" in membership:
            _fail("dxf_entity_clip_ambiguous")
        if "inside" not in membership:
            continue
        selected.append(entity)
    if selector.handle_mode == "only_listed" and {_handle(e) for e in selected} != wanted:
        _fail("dxf_selector_handle_missing")
    if len(selected) < selector.min_count or (selector.max_count is not None and len(selected) > selector.max_count):
        _fail("dxf_selector_count_mismatch")
    return sorted(selected, key=_handle)


def _transform(point: tuple[float, float], view: PlanViewBindingV1, metres_per_unit: float) -> tuple[float, float]:
    x, y = point[0] * metres_per_unit, point[1] * metres_per_unit
    affine = view.world_from_source_m
    return (affine.m00 * x + affine.m01 * y + affine.m02,
            affine.m10 * x + affine.m11 * y + affine.m12)


def _segments(entities, view: PlanViewBindingV1, metres_per_unit: float, role: str):
    output: list[tuple[tuple[float, float], tuple[float, float], GtEntityRefV3]] = []
    for entity in entities:
        points = [_transform(p, view, metres_per_unit) for p in _entity_points(entity)]
        if len(points) < 2:
            _fail("dxf_empty_entity")
        if entity.dxftype() == "LWPOLYLINE" and entity.closed and points[0] != points[-1]:
            points.append(points[0])
        for index, (start, end) in enumerate(zip(points, points[1:])):
            output.append((start, end, GtEntityRefV3(source_id="pending", view_id=view.id,
                entity_handle=_handle(entity), subentity_index=index if len(points) > 2 else None, role=role)))
    return output


def _snap_segments(segments, node_join_tolerance: float, axis_alignment_tolerance: float):
    points = sorted({p for start, end, _ in segments for p in (start, end)})
    groups: list[list[tuple[float, float]]] = []
    for point in points:
        hits = [group for group in groups if any((point[0] - p[0]) ** 2 + (point[1] - p[1]) ** 2 <= node_join_tolerance ** 2 for p in group)]
        if len(hits) > 1:
            merged = [p for group in hits for p in group] + [point]
            for group in hits: groups.remove(group)
            groups.append(merged)
        elif hits: hits[0].append(point)
        else: groups.append([point])
    mapping = {}
    for group in groups:
        if max((a[0]-b[0])**2 + (a[1]-b[1])**2 for a in group for b in group) > node_join_tolerance ** 2:
            _fail("dxf_node_snap_component_too_wide")
        representative = min(group)
        mapping.update({point: representative for point in group})
    snapped = []
    for start, end, ref in segments:
        start, end = mapping[start], mapping[end]
        dx, dy = end[0] - start[0], end[1] - start[1]
        if abs(dx) <= axis_alignment_tolerance < abs(dy): end = (start[0], end[1])
        elif abs(dy) <= axis_alignment_tolerance < abs(dx): end = (end[0], start[1])
        elif abs(dx) <= axis_alignment_tolerance and abs(dy) <= axis_alignment_tolerance: _fail("dxf_short_edge")
        elif abs(dx) > axis_alignment_tolerance and abs(dy) > axis_alignment_tolerance: _fail("dxf_nonorthogonal_edge")
        snapped.append((start, end, ref))
    return snapped


def _polygonize(segments, tolerance: float, diagnostics: dict[str, int] | None = None) -> list[Polygon]:
    lines = [LineString([start, end]) for start, end, _ in segments]
    polygons, cuts, dangles, invalid = polygonize_full(unary_union(lines))
    if diagnostics is not None:
        diagnostics.update(dangle_count=len(dangles.geoms), cut_count=len(cuts.geoms), invalid_ring_count=len(invalid.geoms))
    if not dangles.is_empty or not cuts.is_empty or not invalid.is_empty:
        _fail("dxf_polygonize_residual")
    result = list(polygons.geoms)
    if any(poly.area <= tolerance for poly in result):
        _fail("dxf_polygonize_sliver")
    return result


def _canonical_polygon(poly: Polygon) -> GtPolygonV3:
    if poly.geom_type != "Polygon" or poly.interiors:
        _fail("dxf_polygon_profile_unsupported")
    coords = [(float(x), float(y)) for x, y in list(poly.exterior.coords)[:-1]]
    if not poly.exterior.is_ccw:
        coords.reverse()
    # Remove collinear vertices only; no tolerance rewrite happens here.
    changed = True
    while changed:
        changed = False
        for index, current in enumerate(coords):
            previous, following = coords[index - 1], coords[(index + 1) % len(coords)]
            if (previous[0] == current[0] == following[0]) or (previous[1] == current[1] == following[1]):
                coords.pop(index); changed = True; break
    coords = coords[coords.index(min(coords)):] + coords[:coords.index(min(coords))]
    return GtPolygonV3(exterior=GtRingV3(vertices=[[x, y] for x, y in coords]), interior_rings=[])


def _refs_for_ring(ring: GtPolygonV3, segments, source_id: str, role: str):
    answer = {}
    vertices = [tuple(p) for p in ring.exterior.vertices]
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        refs = []
        for a, b, ref in segments:
            horizontal = a[1] == b[1] == start[1] == end[1] and min(max(a[0], b[0]), max(start[0], end[0])) > max(min(a[0], b[0]), min(start[0], end[0]))
            vertical = a[0] == b[0] == start[0] == end[0] and min(max(a[1], b[1]), max(start[1], end[1])) > max(min(a[1], b[1]), min(start[1], end[1]))
            if horizontal or vertical:
                refs.append(ref.model_copy(update={"source_id": source_id, "role": role}))
        if not refs:
            _fail("dxf_boundary_ancestry_missing")
        answer[(start, end)] = tuple(sorted(refs, key=lambda r: (r.entity_handle, r.subentity_index or -1)))
    return answer


def _source(manifest: GtExtractionManifestV1) -> GtSourceDocumentV3:
    views = []
    for view in sorted(manifest.views, key=lambda value: value.id):
        if isinstance(view, PlanViewBindingV1):
            views.append(GtSourceViewV3(id=view.id, kind="plan", floor_ids=[view.floor_id], projection_surface_key=None,
                facade_family=None, view_kind=None, world_along_coverage=None, direction_semantics=None, azimuth_deg=None))
    return GtSourceDocumentV3(id=manifest.source_id, kind="dxf", label=manifest.source_dxf_label,
        content_sha256=manifest.source_dxf_sha256, native_units=manifest.native_units,
        metres_per_unit=manifest.metres_per_unit, views=views)


def _check_input(inputs: InspectionInputs):
    path = Path(inputs.dxf_path)
    raw = path.read_bytes()
    doc = ezdxf.readfile(path)
    unit = _UNITS.get(doc.header.get("$INSUNITS", 0), str(doc.header.get("$INSUNITS", 0)))
    if inputs.manifest:
        manifest = inputs.manifest
        if hashlib.sha256(raw).hexdigest() != manifest.source_dxf_sha256: _fail("dxf_source_hash_mismatch")
        if unit != manifest.native_units: _fail("dxf_unit_mismatch")
        if unit != "unitless" and _UNIT_SCALE.get(unit) != manifest.metres_per_unit: _fail("dxf_unit_scale_mismatch")
        try:
            validate_manifest_view_clips(manifest, topology_area_tolerance_m2=inputs.tooling.tolerances.dxf_topology_area_tolerance_m2)
        except ValueError as error:
            _fail(str(error))
        if any(view.boundary_reference != "outer_skin" for view in manifest.views if isinstance(view, PlanViewBindingV1)):
            _fail("dxf_centerline_unsupported_in_phase_b")
    return doc, unit


def inspect_extraction_inputs(inputs: InspectionInputs) -> DxfInspectionReportV1:
    issues: list[DxfInspectionIssueV1] = []
    try:
        doc, unit = _check_input(inputs)
    except ExtractionError as error:
        issues.append(DxfInspectionIssueV1(code=str(error), severity="BLOCK", view_id=None))
        doc, unit = ezdxf.readfile(inputs.dxf_path), _UNITS.get(ezdxf.readfile(inputs.dxf_path).header.get("$INSUNITS", 0), "unknown")
    proxy_entities = [entity for entity in doc.modelspace() if isinstance(entity, DXFTagStorage) or entity.dxftype() in {"ACAD_PROXY_ENTITY", "ACAD_PROXY_GRAPHIC"}]
    proxy_count = len(proxy_entities)
    if inputs.manifest is None:
        issues.append(DxfInspectionIssueV1(code="dxf_manifest_required", severity="UNBOUND", view_id=None))
        views = []
    else:
        views = []
        for view in sorted((v for v in inputs.manifest.views if isinstance(v, PlanViewBindingV1)), key=lambda v: v.id):
            diagnostics = {"dangle_count": 0, "cut_count": 0, "invalid_ring_count": 0}
            try:
                footprint = _selector_entities(doc.modelspace(), view.footprint_boundary, view)
                segments = _snap_segments(_segments(footprint, view, inputs.manifest.metres_per_unit, "footprint_boundary"), inputs.tooling.tolerances.dxf_node_join_tolerance_m, inputs.tooling.tolerances.dxf_axis_alignment_tolerance_m)
                polygons = _polygonize(segments, inputs.tooling.tolerances.dxf_topology_area_tolerance_m2, diagnostics)
                zone = _selector_entities(doc.modelspace(), view.zone_boundaries, view)
                _polygonize(_snap_segments(_segments(footprint + zone, view, inputs.manifest.metres_per_unit, "zone_boundary"), inputs.tooling.tolerances.dxf_node_join_tolerance_m, inputs.tooling.tolerances.dxf_axis_alignment_tolerance_m), inputs.tooling.tolerances.dxf_topology_area_tolerance_m2, diagnostics)
                counts = Counter(e.dxftype() for e in footprint); layers = Counter(e.dxf.layer for e in footprint)
                views.append(DxfViewInspectionV1(view_id=view.id, kind="plan", entity_count_by_type=dict(counts), entity_count_by_layer=dict(layers), matched_handles=[_handle(e) for e in footprint], polygon_count=len(polygons), **diagnostics))
            except ExtractionError as error:
                issues.append(DxfInspectionIssueV1(code=str(error), severity="BLOCK", view_id=view.id))
                views.append(DxfViewInspectionV1(view_id=view.id, kind="plan", entity_count_by_type={}, entity_count_by_layer={}, matched_handles=[], polygon_count=0, **diagnostics))
            outside_proxy_handles: set[str] = set()
            for entity in proxy_entities:
                try:
                    extent = bbox.extents([entity], fast=True)
                    if not extent.has_data:
                        raise ValueError("proxy extent unavailable")
                    clip = view.clip_box_dxf
                    inside = (extent.extmin.x < clip.xmax and extent.extmax.x > clip.xmin
                              and extent.extmin.y < clip.ymax and extent.extmax.y > clip.ymin)
                except Exception:
                    issues.append(DxfInspectionIssueV1(code="dxf_proxy_extent_unavailable", severity="BLOCK", view_id=view.id, entity_handles=[_handle(entity)]))
                    continue
                if inside:
                    issues.append(DxfInspectionIssueV1(code="dxf_requires_graphics_export", severity="BLOCK", view_id=view.id, entity_handles=[_handle(entity)]))
                else:
                    outside_proxy_handles.add(_handle(entity))
            for handle in sorted(outside_proxy_handles):
                issues.append(DxfInspectionIssueV1(code="dxf_proxy_outside_bound_views", severity="INFO", view_id=view.id, entity_handles=[handle]))
    if proxy_count and inputs.manifest is None:
        issues.append(DxfInspectionIssueV1(code="dxf_requires_graphics_export", severity="INFO", view_id=None))
    issues.sort(key=lambda i: (_SEVERITY[i.severity], i.view_id or "", i.code, i.entity_handles))
    status = "BLOCKED" if any(i.severity == "BLOCK" for i in issues) else ("UNBOUND" if inputs.manifest is None else "PASS")
    return DxfInspectionReportV1(report_version=1, status=status, source_dxf_sha256=hashlib.sha256(Path(inputs.dxf_path).read_bytes()).hexdigest(), native_units_observed=unit, manifest_sha256=inputs.manifest.manifest_sha256 if inputs.manifest else None, judge_config_sha256=inputs.tooling.judge_config_sha256, vg_config_sha256=inputs.tooling.vg_config_sha256, proxy_entity_count=proxy_count, views=views, issues=issues)


def extract_plan_geometry(inputs: ExtractionInputs) -> PlanExtractionResult:
    report = inspect_extraction_inputs(InspectionInputs(inputs.dxf_path, inputs.manifest, inputs.tooling, inputs.implementation_hashes))
    if report.status != "PASS": _fail(f"dxf_inspection_{report.status.lower()}")
    doc, _ = _check_input(inputs)
    floors = []
    reference_ring = None
    floor_info = {floor.id: floor for floor in inputs.manifest.floors}
    for view in sorted((v for v in inputs.manifest.views if isinstance(v, PlanViewBindingV1)), key=lambda v: v.floor_id):
        footprint_segments = _snap_segments(_segments(_selector_entities(doc.modelspace(), view.footprint_boundary, view), view, inputs.manifest.metres_per_unit, "footprint_boundary"), inputs.tooling.tolerances.dxf_node_join_tolerance_m, inputs.tooling.tolerances.dxf_axis_alignment_tolerance_m)
        footprint_faces = _polygonize(footprint_segments, inputs.tooling.tolerances.dxf_topology_area_tolerance_m2)
        containing = [face for face in footprint_faces if all(face.contains(Point(seed.point_world_m)) for seed in view.zone_seeds)]
        if len(containing) != 1: _fail("dxf_footprint_seed_ambiguous")
        footprint = _canonical_polygon(containing[0])
        ring = tuple(tuple(p) for p in footprint.exterior.vertices)
        if reference_ring is None: reference_ring = ring
        elif ring != reference_ring: _fail("dxf_profile_floor_footprint_mismatch")
        zone_entities = _selector_entities(doc.modelspace(), view.zone_boundaries, view)
        zone_segments = _snap_segments(_segments(_selector_entities(doc.modelspace(), view.footprint_boundary, view) + zone_entities, view, inputs.manifest.metres_per_unit, "zone_boundary"), inputs.tooling.tolerances.dxf_node_join_tolerance_m, inputs.tooling.tolerances.dxf_axis_alignment_tolerance_m)
        zone_faces = _polygonize(zone_segments, inputs.tooling.tolerances.dxf_topology_area_tolerance_m2)
        zones = []
        for face in zone_faces:
            owners = [seed for seed in view.zone_seeds if face.contains(Point(seed.point_world_m))]
            if len(owners) != 1: _fail("dxf_zone_seed_ambiguous")
            if face.boundary.distance(Point(owners[0].point_world_m)) <= inputs.tooling.tolerances.dxf_node_join_tolerance_m:
                _fail("dxf_zone_seed_near_boundary")
            if not containing[0].covers(face): _fail("dxf_zone_outside_footprint")
            seed = owners[0]; polygon = _canonical_polygon(face)
            refs = tuple(ref for refs in _refs_for_ring(polygon, zone_segments, inputs.manifest.source_id, "zone_boundary").values() for ref in refs)
            unique_refs = {(ref.source_id, ref.view_id, ref.entity_handle, ref.subentity_index, ref.role): ref for ref in refs}
            zones.append(PlanZoneExtraction(seed.zone_id, seed.name, seed.role, polygon, tuple(sorted(unique_refs.values(), key=lambda r: (r.entity_handle, r.subentity_index or -1)))))
        if {zone.id for zone in zones} != {seed.zone_id for seed in view.zone_seeds}: _fail("dxf_zone_seed_missing")
        union = unary_union([Polygon(zone.polygon.exterior.vertices) for zone in zones])
        if union.symmetric_difference(containing[0]).area > inputs.tooling.tolerances.dxf_topology_area_tolerance_m2: _fail("dxf_zone_tiling_mismatch")
        info = floor_info[view.floor_id]
        floors.append(PlanFloorExtraction(info.id, info.name, info.z_floor_m, info.ceiling_height_m, footprint,
            footprint_fingerprint(footprint.exterior.vertices), tuple(sorted(zones, key=lambda z: z.id)),
            _refs_for_ring(footprint, footprint_segments, inputs.manifest.source_id, "footprint_boundary")))
    return PlanExtractionResult(inputs.manifest.case, _source(inputs.manifest), tuple(floors))
