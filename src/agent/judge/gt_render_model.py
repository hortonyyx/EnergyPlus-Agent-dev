"""Typed, judge-side render model for ground-truth visualisations.

The renderers in this module deliberately know only these small immutable
primitives.  Wire/schema interpretation lives in :func:`gt_to_render_model`;
this keeps a renderer from becoming a second (and inevitably looser) loader.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageColor, ImageDraw, ImageFont

from .gt_schema import GtDocument, GroundTruthV3, LegacyGroundTruthV2

Point2 = tuple[float, float]


@dataclass(frozen=True)
class RenderPolygon:
    id: str
    label: str
    role: str
    exterior: tuple[Point2, ...]


@dataclass(frozen=True)
class RenderSegment:
    id: str
    floor_id: str
    facade_family: Literal["North", "South", "East", "West"]
    p1: Point2
    p2: Point2
    depth_m: float
    visible_intervals: tuple[tuple[float, float], ...]
    projection_surface_keys: tuple[str, ...]


@dataclass(frozen=True)
class RenderOpening:
    id: str
    floor_id: str
    kind: Literal["window", "door"]
    segment_id: str
    world_along_interval: tuple[float, float]
    z_interval: tuple[float, float] | None


@dataclass(frozen=True)
class PlanRenderFloor:
    floor_id: str
    z_floor_m: float
    ceiling_height_m: float
    footprint_exterior: tuple[Point2, ...]
    zone_polygons: tuple[RenderPolygon, ...]
    boundary_segments: tuple[RenderSegment, ...]
    openings: tuple[RenderOpening, ...]


@dataclass(frozen=True)
class ElevationRenderSurface:
    key: str
    source_view_id: str
    floor_ids: tuple[str, ...]
    facade_family: Literal["North", "South", "East", "West"]
    view_kind: Literal["full", "partial"]
    direction_semantics: Literal["building_axis", "true_azimuth"]
    azimuth_deg: float | None
    world_along_coverage: tuple[float, float] | None
    segments: tuple[RenderSegment, ...]
    openings: tuple[RenderOpening, ...]


@dataclass(frozen=True)
class GtRenderModel:
    case: str
    source_schema_version: Literal[2, 3]
    north_axis_deg: float | None
    floors: tuple[PlanRenderFloor, ...]
    elevation_surfaces: tuple[ElevationRenderSurface, ...]
    verification_status: Literal["candidate", "human_verified"] = "candidate"
    reviewer_id: str | None = None
    reviewed_on: str | None = None
    content_sha256: str | None = None


def _point(point: list[float]) -> Point2:
    return (float(point[0]), float(point[1]))


def gt_to_render_model(doc: GtDocument) -> GtRenderModel:
    """Adapt a validated typed document; v2 remains an explicit legacy adapter."""
    if isinstance(doc, GroundTruthV3):
        segment_by_id: dict[str, RenderSegment] = {}
        floors: list[PlanRenderFloor] = []
        openings_by_floor: dict[str, list[RenderOpening]] = {}
        for opening in doc.openings:
            item = RenderOpening(opening.id, opening.floor_id, opening.kind,
                                 opening.boundary_segment_id,
                                 (float(opening.world_along_interval.lo), float(opening.world_along_interval.hi)),
                                 None if opening.z_interval is None else
                                 (float(opening.z_interval.lo), float(opening.z_interval.hi)))
            openings_by_floor.setdefault(item.floor_id, []).append(item)
        for floor in doc.floors:
            segments = tuple(RenderSegment(
                item.id, item.floor_id, item.facade_family, _point(item.p1), _point(item.p2),
                float(item.depth), tuple((float(v.lo), float(v.hi)) for v in item.visible_intervals),
                tuple(item.projection_surface_keys)) for item in floor.boundary_segments)
            segment_by_id.update({item.id: item for item in segments})
            zones = tuple(RenderPolygon(zone.id, zone.name, zone.role,
                                        tuple(_point(point) for point in zone.polygon.exterior.vertices))
                          for zone in floor.zones)
            floors.append(PlanRenderFloor(floor.id, float(floor.z_floor_m), float(floor.ceiling_height_m),
                                          tuple(_point(point) for point in floor.footprint.exterior.vertices), zones,
                                          segments, tuple(sorted(openings_by_floor.get(floor.id, []), key=lambda x: x.id))))
        surfaces: list[ElevationRenderSurface] = []
        for source in doc.sources:
            for view in source.views:
                if view.kind != "elevation":
                    continue
                key = view.projection_surface_key
                assert key is not None  # schema validation has already established this.
                segments = tuple(sorted((segment for segment in segment_by_id.values() if key in segment.projection_surface_keys),
                                        key=lambda x: (x.floor_id, x.id)))
                ids = {segment.id for segment in segments}
                openings = tuple(sorted((opening for opening in doc.openings if opening.boundary_segment_id in ids),
                                        key=lambda x: x.id))
                surfaces.append(ElevationRenderSurface(
                    key, view.id, tuple(view.floor_ids), view.facade_family, view.view_kind,
                    view.direction_semantics, None if view.azimuth_deg is None else float(view.azimuth_deg),
                    None if view.world_along_coverage is None else (float(view.world_along_coverage.lo), float(view.world_along_coverage.hi)),
                    segments, tuple(RenderOpening(item.id, item.floor_id, item.kind, item.boundary_segment_id,
                                                   (float(item.world_along_interval.lo), float(item.world_along_interval.hi)),
                                                   None if item.z_interval is None else (float(item.z_interval.lo), float(item.z_interval.hi)))
                                    for item in openings)))
        return GtRenderModel(doc.case, 3, None if doc.north_axis_deg is None else float(doc.north_axis_deg),
                             tuple(floors), tuple(sorted(surfaces, key=lambda x: (x.key, x.source_view_id))),
                             doc.verification.status, doc.verification.reviewer_id, doc.verification.reviewed_on,
                             doc.content_sha256)
    return _legacy_render_model(doc)


def _legacy_render_model(doc: LegacyGroundTruthV2) -> GtRenderModel:
    """The old rectangular W/D/four-facade interpretation, isolated for v2."""
    width, depth = float(doc.footprint.W_m), float(doc.footprint.D_m)
    edge = {"South": ((0., 0.), (width, 0.)), "North": ((width, depth), (0., depth)),
            "East": ((width, 0.), (width, depth)), "West": ((0., depth), (0., 0.))}
    floors: list[PlanRenderFloor] = []
    surface_data: dict[str, list[RenderSegment]] = {name: [] for name in edge}
    for floor in doc.floors:
        segments: list[RenderSegment] = []
        for family, (p1, p2) in edge.items():
            span = width if family in {"North", "South"} else depth
            item = RenderSegment(f"{floor.name}:{family}", floor.name, family, p1, p2, 0., ((0., span),), (family,))
            segments.append(item); surface_data[family].append(item)
        openings: list[RenderOpening] = []
        for group in doc.windows:
            if group.floor == floor.name:
                openings.extend(RenderOpening(f"{floor.name}:{group.facade}:window:{n}", floor.name, "window",
                                              f"{floor.name}:{group.facade}", (float(item.x_m), float(item.x_m + item.width_m)),
                                              (float(item.sill_m), float(item.head_m))) for n, item in enumerate(group.openings))
        for n, item in enumerate(doc.doors):
            if item.floor == floor.name:
                openings.append(RenderOpening(f"{floor.name}:{item.facade}:door:{n}", floor.name, "door",
                                              f"{floor.name}:{item.facade}", (float(item.x_m), float(item.x_m + item.width_m)),
                                              (float(item.sill_m), float(item.head_m))))
        zones = tuple(RenderPolygon(z.id, z.id, z.role, ((float(z.rect_m[0]), float(z.rect_m[1])),
              (float(z.rect_m[2]), float(z.rect_m[1])), (float(z.rect_m[2]), float(z.rect_m[3])),
              (float(z.rect_m[0]), float(z.rect_m[3])))) for z in floor.zones)
        floors.append(PlanRenderFloor(floor.name, float(floor.z_floor), float(floor.ceiling_height),
                                      ((0., 0.), (width, 0.), (width, depth), (0., depth)), zones,
                                      tuple(segments), tuple(openings)))
    surfaces = tuple(ElevationRenderSurface(key, key, tuple(f.floor_id for f in floors), key, "full", "building_axis", None,
                  None, tuple(value), tuple(item for floor in floors for item in floor.openings
                                            if item.segment_id.endswith(f":{key}")))
                  for key, value in sorted(surface_data.items()))
    return GtRenderModel(doc.case, 2, None, tuple(floors), surfaces, "human_verified" if doc.verified else "candidate",
                         doc.verified_by, doc.verified_on, doc.cad_sha256)


_FONTS: dict[int, ImageFont.FreeTypeFont] = {}
def _font(size: int) -> ImageFont.FreeTypeFont:
    return _FONTS.setdefault(size, ImageFont.load_default(size=size))

def _header(draw: ImageDraw.ImageDraw, model: GtRenderModel, title: str) -> None:
    hash_text = (model.content_sha256 or "unhashed")[:12]
    line = f"GT v{model.source_schema_version}  {model.case}  hash {hash_text}  {model.verification_status}"
    draw.text((12, 8), f"{title} — {line}", fill="#202020", font=_font(18))
    if model.verification_status == "human_verified":
        draw.text((12, 32), f"reviewer {model.reviewer_id}  date {model.reviewed_on}", fill="#202020", font=_font(13))

def _watermark(draw: ImageDraw.ImageDraw, image: Image.Image, model: GtRenderModel) -> None:
    if model.verification_status == "candidate":
        draw.rectangle((0, image.height - 30, image.width, image.height), fill="#500000")
        draw.text((12, image.height - 25), "CANDIDATE — NOT BASELINE", fill="white", font=_font(17))

def _bounds(points: tuple[Point2, ...]) -> tuple[float, float, float, float]:
    xs, ys = zip(*points); return min(xs), min(ys), max(xs), max(ys)


def _world_point_at_along(segment: RenderSegment, along: float) -> Point2:
    """Map an absolute canonical world-along value to the segment's world point."""
    if segment.facade_family in {"North", "South"}:
        return (along, segment.p1[1])
    return (segment.p1[0], along)

def render_plan_model(model: GtRenderModel) -> Image.Image:
    panels: list[tuple[PlanRenderFloor, tuple[float, float, float, float], float]] = []
    for floor in model.floors:
        x0, y0, x1, y1 = _bounds(floor.footprint_exterior)
        ppm = min(90., max(36., 560. / max(x1 - x0, y1 - y0, .1)))
        panels.append((floor, (x0, y0, x1, y1), ppm))
    widths = [int((box[2] - box[0]) * ppm + 100) for _, box, ppm in panels]
    height = max([200] + [int((box[3] - box[1]) * ppm + 145) for _, box, ppm in panels])
    image = Image.new("RGB", (max(500, sum(widths) + 20 * max(0, len(widths) - 1)), height + 65), (252, 252, 251))
    draw = ImageDraw.Draw(image); _header(draw, model, "GT plan")
    cursor = 0; primitives: list[dict[str, object]] = []; north_vectors: list[tuple[float, float] | None] = []; opening_primitives: list[dict[str, object]] = []
    for (floor, box, ppm), panel_width in zip(panels, widths):
        x0, y0, x1, y1 = box; ox, oy = cursor + 48, 94
        def pix(point: Point2) -> tuple[float, float]: return (ox + (point[0] - x0) * ppm, oy + (y1 - point[1]) * ppm)
        draw.text((cursor + 20, 66), f"{floor.floor_id} z={floor.z_floor_m:g} h={floor.ceiling_height_m:g}", fill="#202020", font=_font(14))
        for zone in floor.zone_polygons:
            poly = [pix(point) for point in zone.exterior]
            draw.polygon(poly, fill=ImageColor.getrgb({"office":"#cfe3f2", "meeting":"#d7ecd2", "corridor":"#fdf0c8"}.get(zone.role.lower(), "#e9e9e9")), outline="#3a3a3a", width=2)
            draw.text(poly[0], f"{zone.id} {zone.label}", fill="#202020", font=_font(12)); primitives.append({"type":"zone", "id":zone.id,"points":zone.exterior})
        footprint = [pix(point) for point in floor.footprint_exterior]
        draw.line(footprint + [footprint[0]], fill="#111111", width=3); primitives.append({"type":"footprint", "points":floor.footprint_exterior})
        by_id = {item.id: item for item in floor.boundary_segments}
        for seg in floor.boundary_segments:
            a, b = pix(seg.p1), pix(seg.p2)
            # First show the complete boundary as a restrained hidden/dashed line,
            # then paint the Vg-derived visible subintervals solid on top.
            for step in range(0, 13, 2):
                t0, t1 = step / 12, min(1., (step + 1) / 12)
                draw.line(((a[0] + (b[0]-a[0])*t0, a[1] + (b[1]-a[1])*t0),
                           (a[0] + (b[0]-a[0])*t1, a[1] + (b[1]-a[1])*t1)), fill="#a00000", width=1)
            for lo, hi in seg.visible_intervals:
                p, q = pix(_world_point_at_along(seg, lo)), pix(_world_point_at_along(seg, hi))
                draw.line((p, q), fill="#404040", width=3)
            draw.text(((a[0]+b[0])/2, (a[1]+b[1])/2), f"{seg.id[-8:]} {seg.facade_family} d={seg.depth_m:g}", fill="#555555", font=_font(10))
        for opening in floor.openings:
            seg = by_id[opening.segment_id]
            a, b = opening.world_along_interval
            points = (_world_point_at_along(seg, a), _world_point_at_along(seg, b))
            draw.line(tuple(pix(point) for point in points), fill="#1f77b4" if opening.kind == "window" else "#b5651d", width=6)
            opening_primitives.append({"id": opening.id, "points": points})
        if model.north_axis_deg is None:
            draw.text((cursor + 18, height + 28), "+x / +y axes; true north unset", fill="#555555", font=_font(12))
            north_vectors.append(None)
        else:
            theta = math.radians(model.north_axis_deg); north = (-math.sin(theta), math.cos(theta))
            base = (cursor + 30, height + 28)
            draw.line((base, (base[0], base[1]-24)), fill="#202020", width=2)
            draw.line((base, (base[0] + north[0]*24, base[1] - north[1]*24)), fill="#0070b0", width=2)
            draw.text((cursor + 18, height + 28), f"building +Y ↑; true/project N ({north[0]:.6f}, {north[1]:.6f})", fill="#555555", font=_font(12))
            north_vectors.append(north)
        cursor += panel_width + 20
    image.info["render_primitives"] = primitives
    image.info["opening_primitives"] = opening_primitives
    image.info["north_vectors"] = north_vectors
    _watermark(draw, image, model); return image

def render_elevation_model(model: GtRenderModel) -> Image.Image:
    surfaces = tuple(sorted(model.elevation_surfaces, key=lambda value: (value.key, value.source_view_id)))
    if not surfaces:
        image = Image.new("RGB", (760, 170), (252, 252, 251)); draw = ImageDraw.Draw(image); _header(draw, model, "GT elevations")
        draw.text((25, 95), "NO ELEVATION SOURCE BINDING", fill="#900000", font=_font(20)); _watermark(draw, image, model); return image
    panel_width, panel_height = 430, 330
    image = Image.new("RGB", (len(surfaces) * panel_width + (len(surfaces)-1)*18, panel_height + 65), (252,252,251)); draw = ImageDraw.Draw(image); _header(draw, model, "GT elevations")
    floor_by_id = {floor.floor_id: floor for floor in model.floors}
    primitives: list[dict[str, object]] = []; segment_primitives: list[dict[str, object]] = []
    for index, surface in enumerate(surfaces):
        ox, oy = index * (panel_width + 18), 88
        segments = surface.segments
        # along has to follow the schema's facade-local interval, not a bbox coordinate.
        def extent(segment: RenderSegment) -> tuple[float, float]:
            axis = 0 if segment.facade_family in {"North", "South"} else 1
            return tuple(sorted((segment.p1[axis], segment.p2[axis])))
        lo = min((extent(segment)[0] for segment in segments), default=0.)
        hi = max((extent(segment)[1] for segment in segments), default=1.)
        if surface.world_along_coverage is not None: lo, hi = surface.world_along_coverage
        max_z = max((floor_by_id[item].z_floor_m + floor_by_id[item].ceiling_height_m for item in surface.floor_ids), default=3.)
        ppm = min(75., 300. / max(hi-lo, max_z, .1)); tx=lambda value: ox+55+(value-lo)*ppm; tz=lambda value: oy+225-value*ppm
        draw.text((ox+12, oy-18), f"{surface.key} / {surface.source_view_id}", fill="#202020", font=_font(13))
        draw.rectangle((tx(lo), tz(max_z), tx(hi), tz(0)), outline="#111111", width=2)
        for segment in segments:
            sl, sh = extent(segment)
            if surface.world_along_coverage is not None and (sh <= lo or sl >= hi): continue
            z_floor = floor_by_id[segment.floor_id].z_floor_m
            for step in range(0, 13, 2):
                a, b = sl + (sh-sl)*step/12, sl + (sh-sl)*min(1., (step+1)/12)
                draw.line((tx(max(lo,a)), tz(z_floor), tx(min(hi,b)), tz(z_floor)), fill="#a00000", width=1)
            for visible_lo, visible_hi in segment.visible_intervals:
                if visible_hi > lo and visible_lo < hi:
                    draw.line((tx(max(lo,visible_lo)), tz(z_floor), tx(min(hi,visible_hi)), tz(z_floor)), fill="#404040", width=3)
            segment_primitives.append({"id": segment.id, "z_floor_m": z_floor, "visible_intervals": segment.visible_intervals})
        for opening in surface.openings:
            if opening.z_interval is None:
                continue
            a,b = opening.world_along_interval
            if b <= lo or a >= hi: continue
            draw.rectangle((tx(max(a,lo)), tz(opening.z_interval[1]), tx(min(b,hi)), tz(opening.z_interval[0])), outline="#1f77b4" if opening.kind=="window" else "#b5651d", width=3)
        if surface.world_along_coverage is not None: draw.text((ox+12, oy+245), "PARTIAL — CLIPPED AT COVERAGE", fill="#900000", font=_font(11))
        if any(value.z_interval is None for value in surface.openings): draw.text((ox+12, oy+262), "PLAN-ONLY / Z UNSET", fill="#900000", font=_font(11))
        primitives.append({"type":"surface", "key":surface.key, "segments":len(segments)})
    image.info["render_primitives"] = primitives; image.info["segment_primitives"] = segment_primitives; _watermark(draw, image, model); return image
