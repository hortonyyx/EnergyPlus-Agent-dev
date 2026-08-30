"""AnswerCompiler -- ONE facts layer, SEVERAL exits (dispatch ②-1c R1).

    as_signed.json ──→ AnswerCompiler(profile) ──┬─→ form-A zone polygons
                                                 ├─→ form-B zone polygons
                                                 ├─→ reading exam (denominator
                                                 │    derived from facts, R4)
                                                 └─→ clear-span area table (R6)

⭐ ONE facts document + ONE deriver with several exits, ⛔ never two parallel
answers (guide §十: parallel answers drift apart -- that is F-130's shape).
``profile`` is an EXPLICIT parameter; nothing about evidence or thresholds
chooses a form.  The deriver is PURE (no human channel) and its version is
part of the answer key (``COMPILER_VERSION``).

## Basis determination (§1.4 / sol B5) -- recomputed, never copied

The compiler NEVER reads any stored ``basis``-shaped field.  For every cavity
edge it recomputes the S7 judgement from facts-layer geometry alone:

    exterior  ⟺  the point obtained by walking from the cavity edge THROUGH
                  the whole wall band (one unit past the far face) lies
                  OUTSIDE both the footprint and the wall region
                  -- "穿过墙后是否落 footprint exterior" (dispatch §1.4),
    interior  otherwise,
    offset    = t (exterior, form B) or t/2 (interior; every form-A edge).

MEASURED on real sm25 (probe, 2026-08-30): two cheaper-looking tests are
WRONG on the as-received drawing and were rejected --
  * "face lies on the footprint ring": FALSE POSITIVE -- the footprint ring
    dips along INTERIOR wall faces wherever polygonize could not close a
    region (z6's south wall 57600/60000 was called exterior and emitted its
    face 60000 instead of the midline 58800);
  * "face lies on the wall-region exterior ring": FALSE POSITIVE -- the wall
    region falls apart into components on the as-received drawing, and
    interior walls became component boundaries (14 zones went DIFF at once).
The exit-point test reproduces all 25 projectable zones BIT-FOR-BIT in 0.1 mm
units (F1 11 + F2 14), including the same physical wall line projecting to
BOTH 60000 (its exterior run, z0's north edge) and 58800 (its interior run,
z6's south edge) -- which is exactly how the signed gt's partition lines run,
and why the basis unit is ONE CAVITY-EDGE SPAN (⭐ 6b), never one wall and
never one vertex: one span, one basis, no step inside a span.

The raw face coordinate used for a support line is the MEAN of the drawn face
lines' own ``const`` values (⭐ probe-measured: the D3 group coordinate is
1mm-quantised -- 160600 vs the drawn 160596 -- and gt's partition line sits at
159996, the mean, not at 160000, the group coordinate).

## The three supplementary rules (dispatch §1.3, R2)

6a  form A collapses a step to zero -> two coincident vertices -> the vertex
    list is DEDUPED (consecutive-equal and wrap-around);
6b  the basis unit is one cavity-edge span (see above); a span never changes
    basis mid-span;
6c  junctions propagate LINES, not endpoints: zone vertices are the
    intersections of adjacent support lines, ⛔ never the wall lines' own
    endpoints (which stop at the struck wall's near face, so the corner block
    belongs to neither wall).

## Unprojectable and the dependency closure (R3 / sol B6)

The whole zone ring is one transaction: if ANY of its edges is
unprojectable, the ring carries NO coordinates (⛔ never half a ring, ledger
§1.5) and the reason chain names every component the failure propagated
through.  The six B6 rules are implemented in :func:`_compile_view` and
itemised in ``tests/test_answer_compiler_closure.py``.  The zone COUNT and
the reading exam are never shrunk by a failure (⛔ no denominator benefit).

## Version

``COMPILER_VERSION`` enters the answer key.  Bump it on any behavioural
change to the derivation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from .as_measured import (UNITS_PER_METRE, AsMeasuredOpeningV1,
                          AsMeasuredV1, AsMeasuredViewV1, AsMeasuredWallV1)
from .gt_revisions import (AsSignedV1, RevisionsLedgerV1,
                           revisions_content_sha256)
from .gt_schema import StableId
from .tarch_converter_schema import (TarchConversionRequestV1, _StrictModel)

__all__ = [
    "COMPILER_VERSION", "OutputProfile", "AnswerCompiler",
    "CompiledZoneEdgeV1", "CompiledZoneV1", "CompiledViewV1",
    "CompiledAnswerV1", "NaRecordV1", "read_facts_for_compilation",
    "AnswerCompilerInputError",
]

#: ⭐ Part of the answer key (R1): bump on any behavioural derivation change.
COMPILER_VERSION = 1


class AnswerCompilerInputError(ValueError):
    """Raised loudly when the compiler's inputs do not belong together."""


class OutputProfile(str, Enum):
    """The two -- and only two -- output forms (user 2026-08-29).

    ⛔ CLEAR SPAN IS DELIBERATELY ABSENT: it is a derived quantity
    (:func:`CompiledAnswerV1.clear_span_table`), never an output profile
    (two clear-span rooms leave a 240 mm gap between them -- InterZone red,
    or adiabatic walls if forced -- runs fine, physics wrong).
    """
    FORM_A_AXIS = "form_a_axis"                       # every wall -> midline
    FORM_B_EXTERIOR_SKIN = "form_b_exterior_skin"     # exterior -> outer skin


# --------------------------------------------------------------------------- #
# compiled output model
# --------------------------------------------------------------------------- #
class NaRecordV1(_StrictModel):
    """One propagation step of the dependency closure, ⛔ coordinates-free.

    A NA record carries component identities and reasons ONLY -- never a
    coordinate (verification #8: zero coordinate leakage out of an NA'd
    product)."""
    component_kind: str        # face_line | wall | opening | view | zone_binding
    component_id: str
    reason: str
    propagated_from: str | None = None


class CompiledZoneEdgeV1(_StrictModel):
    """One projected zone edge = one cavity-edge span, with its evidence.

    ``basis_evidence`` is the §1.4 留痕: which raw face the span sits on, the
    outward direction (into the wall band, away from the cavity), the exit
    point through the band, and whether that exit landed outside (exterior)
    or inside (interior)."""
    axis: str                  # wall-run axis ("x"/"y", as_measured convention)
    span_lo: int               # 0.1 mm, along the run
    span_hi: int
    out_const: int             # 0.1 mm, the projected support line
    basis: str                 # "exterior" | "interior"
    wall_ids: list[str]
    face_line_handles: list[str]
    basis_evidence: dict[str, Any]
    unprojectable: list[NaRecordV1] = field(default_factory=list)


class CompiledZoneV1(_StrictModel):
    zone_id: str | None        # None when the view-level binding is NA
    name: str | None
    floor_id: str
    profile: str
    #: ⭐ None ⟺ unprojectable.  A zone NEVER carries half a ring (§1.5).
    vertices: list[list[int]] | None
    edges: list[CompiledZoneEdgeV1]
    na: list[NaRecordV1]
    cavity_area_units2: int    # the CLEAR-SPAN numerator, always present


class CompiledViewV1(_StrictModel):
    view_id: str
    floor_id: str
    profile: str
    zones: list[CompiledZoneV1]
    zone_binding_na: list[NaRecordV1]
    counts: dict[str, int]     # expected / projected / na zones -- never shrunk


class CompiledAnswerV1(_StrictModel):
    case: str
    profile: str
    compiler_version: int
    derivation: dict[str, str]
    views: list[CompiledViewV1]


# --------------------------------------------------------------------------- #
# internal geometry model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _WallGroup:
    """One physical wall = one face pair: its runs plus the openings that
    bridge them (an opening's carrier names the two runs it splits)."""
    axis: str
    face_lo: int               # D3 group coordinate -- IDENTITY only
    face_hi: int
    runs: tuple[AsMeasuredWallV1, ...]
    openings: tuple[AsMeasuredOpeningV1, ...]
    handles: frozenset[str]

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.axis, self.face_lo, self.face_hi)

    @property
    def run_ids(self) -> list[str]:
        return [w.id for w in self.runs]

    def raw_face(self, side: str, face_by_id: dict) -> int:
        """The drawn face coordinate: mean of the face lines' own ``const``
        values, ⭐ not the 1mm-quantised D3 group coordinate (probe: the
        drawn faces sit at 159396/160596 while the group says 159400/160600,
        and gt's partition line sits at the mean 159996, not at 160000)."""
        vals = [h for w in self.runs
                for h in (w.face_line_ids_lo if side == "lo"
                          else w.face_line_ids_hi)]
        return round(sum(face_by_id[h].const for h in vals) / len(vals))

    def coverage(self) -> list[tuple[int, int]]:
        out = [(w.along_min, w.along_max) for w in self.runs]
        out += [(o.along_min, o.along_max) for o in self.openings]
        return out


@dataclass
class _Span:
    """One cavity-edge span: the basis unit (6b)."""
    axis: str
    const: int                 # the D3 group face coordinate it touches
    lo: int
    hi: int
    group: _WallGroup | None   # None -> unowned (a gap in the facts)
    side: int                  # -1 cavity at smaller const, +1 at larger
    edge: CompiledZoneEdgeV1 | None = None
    na: list[NaRecordV1] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# the compiler
# --------------------------------------------------------------------------- #
class AnswerCompiler:
    """``AnswerCompiler(profile).compile(as_signed, revisions, request)``.

    Pure derivation: no filesystem, no human channel, no stored ``basis``
    field is ever read (verification #2 deletes every basis-shaped key and
    expects a bit-identical output).
    """

    def __init__(self, profile: OutputProfile):
        self.profile = profile

    # -- the other three exits (R4 / R6) -----------------------------------
    def reading_exam(self, as_signed: AsSignedV1,
                     request: TarchConversionRequestV1, *,
                     merge_m: float | None = None) -> dict:
        """The READING EXAM (which face lines must be drawn), derived from
        the facts layer (R4) -- ⛔ the converter is NOT re-run here, which is
        exactly what closes F-130: both rulers now derive from one frozen
        document.  Same D1-D5 core as the DXF path
        (:func:`src.agent.judge.as_drawn.denominator.denominator_from_facts`)."""
        from .as_drawn.denominator import MERGE_M, denominator_from_facts
        kwargs = {"merge_m": merge_m} if merge_m is not None else {}
        return {v.view_id: denominator_from_facts(v, request, **kwargs)
                for v in as_signed.views}

    @staticmethod
    def clear_span_table(answer: CompiledAnswerV1) -> dict:
        """The CLEAR-SPAN table (R6): per-zone usable area, the cavity area
        in 0.1 mm² units -- a DERIVED QUANTITY, ⛔ never an output profile
        (form-C was rejected: two clear-span rooms leave a 240 mm gap, the
        InterZone pair breaks and heat transfer silently dies).

        Present for EVERY zone, NA ones included (the cavity is measured
        geometry even when the projection is not) -- the table never shrinks
        because a zone failed to project."""
        table = {}
        for view in answer.views:
            table[view.view_id] = {
                (z.zone_id or f"cavity_{i:02d}"): {
                    "clear_span_area_units2": z.cavity_area_units2,
                    "clear_span_area_m2": round(
                        z.cavity_area_units2 / (UNITS_PER_METRE * UNITS_PER_METRE), 6),
                    "projected": z.vertices is not None,
                }
                for i, z in enumerate(view.zones)}
        return table

    # -- metamorphic re-projection (R5) ------------------------------------
    def reproject(self, answer: CompiledAnswerV1,
                  to_profile: "OutputProfile") -> CompiledAnswerV1:
        """Form A <-> B re-projection THROUGH the facts layer (R5's round
        trip): every edge carries its evidence (raw face, outward direction,
        thickness, exit verdict), so the other form's const is
        ``raw_face ± offset(other profile)`` -- recomputed from evidence,
        ⛔ not a stored "delta t/2" (which would replay this compiler's own
        earlier answer back at it)."""
        other = AnswerCompiler(to_profile)
        if to_profile is answer_profile(answer):
            return answer
        for view in answer.views:
            for zone in view.zones:
                if zone.vertices is None:
                    continue
                for edge in zone.edges:
                    ev = edge.basis_evidence
                    raw, t = ev["raw_face_const"], ev["thickness_units"]
                    outward = ev["outward"]
                    if to_profile is OutputProfile.FORM_A_AXIS:
                        offset = t // 2
                    else:
                        offset = (t if ev["exit_outside_footprint_and_wall_region"]
                                  else t // 2)
                    edge.out_const = raw + outward * offset
                zone.vertices = [[v[0], v[1]]
                                 for v in _support_vertices_from_edges(zone.edges)]
        answer.profile = to_profile.value
        for view in answer.views:
            view.profile = to_profile.value
            for zone in view.zones:
                zone.profile = to_profile.value
        return answer

    # -- public entry ------------------------------------------------------
    def compile(self, as_signed: AsSignedV1, revisions: RevisionsLedgerV1,
                request: TarchConversionRequestV1) -> CompiledAnswerV1:
        self._assert_inputs_belong_together(as_signed, revisions, request)
        views = [self._compile_view(v, revisions, request)
                 for v in as_signed.views]
        return CompiledAnswerV1(
            case=as_signed.case,
            profile=self.profile.value,
            compiler_version=COMPILER_VERSION,
            derivation={
                "as_signed_source_dxf_sha256": as_signed.source_dxf_sha256,
                "revisions_content_sha256": revisions_content_sha256(revisions),
                "compiler_version": str(COMPILER_VERSION),
                "profile": self.profile.value,
            },
            views=views)

    @staticmethod
    def _assert_inputs_belong_together(as_signed: AsSignedV1,
                                       revisions: RevisionsLedgerV1,
                                       request: TarchConversionRequestV1
                                       ) -> None:
        if revisions.as_measured_content_sha256 != _as_measured_hash(as_signed):
            raise AnswerCompilerInputError(
                "answer_compiler_revisions_do_not_target_this_as_signed: "
                f"ledger names {revisions.as_measured_content_sha256}")
        if request.request_sha256 != as_signed.request_sha256:
            raise AnswerCompilerInputError(
                "answer_compiler_request_does_not_match_as_signed: request "
                f"{request.request_sha256} != as_signed {as_signed.request_sha256}")

    # -- per-view compilation ----------------------------------------------
    def _compile_view(self, view: AsMeasuredViewV1,
                      revisions: RevisionsLedgerV1,
                      request: TarchConversionRequestV1) -> CompiledViewV1:
        plan_view = next((pv for pv in request.plan_views
                          if pv.id == view.view_id), None)
        if plan_view is None:
            raise AnswerCompilerInputError(
                f"answer_compiler_view_not_in_request:{view.view_id}")

        unsigned_handles = {r.target.handle for r in revisions.revisions
                            if r.verdict == "unsigned"}

        face_by_id = {f.id: f for f in view.face_lines}
        groups = _build_groups(view, face_by_id)
        wall_region = _wall_region(view)
        footprint = _footprint_polygon(view)

        cavities = _cavity_faces(footprint, wall_region, request)
        expected = plan_view.zone_intent.expected_count

        zones: list[CompiledZoneV1] = []
        # canonical order (S6's own): (minx, miny) of the cavity bounds
        ordered = sorted(cavities, key=lambda g: (round(g.bounds[0], 6),
                                                  round(g.bounds[1], 6)))
        binding_na: list[NaRecordV1] = []
        entries = plan_view.zone_intent.entries
        bindable = len(ordered) == expected
        if not bindable:
            binding_na.append(NaRecordV1(
                component_kind="zone_binding", component_id=view.view_id,
                reason=(f"cavity_count_mismatch:{len(ordered)}!={expected} "
                        "-- identity binding needs S6's own count gate; the "
                        "RING GEOMETRY below is still compiled and "
                        "reconcilable, only the id/name binding is NA")))

        for idx, cavity in enumerate(ordered):
            zone_id = entries[idx].zone_id if (bindable and idx < len(entries)) else None
            name = entries[idx].name if (bindable and idx < len(entries)) else None
            zones.append(self._compile_zone(
                view, cavity, zone_id, name, groups, face_by_id,
                wall_region, footprint, unsigned_handles))

        return CompiledViewV1(
            view_id=view.view_id, floor_id=view.floor_id,
            profile=self.profile.value, zones=zones,
            zone_binding_na=binding_na,
            counts={
                "expected_zones": expected,
                "cavity_faces": len(ordered),
                "projected_zones": sum(1 for z in zones if z.vertices is not None),
                "na_zones": sum(1 for z in zones if z.vertices is None),
            })

    # -- per-zone compilation ----------------------------------------------
    def _compile_zone(self, view: AsMeasuredViewV1, cavity: Polygon,
                      zone_id: str | None, name: str | None,
                      groups: dict[tuple[str, int, int], _WallGroup],
                      face_by_id: dict, wall_region: Polygon,
                      footprint: Polygon,
                      unsigned_handles: set[str]) -> CompiledZoneV1:
        rep = cavity.representative_point()
        ring = list(cavity.exterior.coords)
        spans: list[_Span] = []
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a[0] == b[0]:    # vertical edge runs along y (as_measured axis)
                axis, const = "y", int(a[0])
                lo, hi = int(min(a[1], b[1])), int(max(a[1], b[1]))
                side = -1 if rep.x < const else 1
            else:
                axis, const = "x", int(a[1])
                lo, hi = int(min(a[0], b[0])), int(max(a[0], b[0]))
                side = -1 if rep.y < const else 1
            spans.append(_Span(axis=axis, const=const, lo=lo, hi=hi,
                               group=_owning_group(groups, axis, const, lo, hi),
                               side=side))

        # -- per-span basis + NA (R3 rules 1/2/4/5) ------------------------
        for s in spans:
            if s.group is None:
                s.na.append(NaRecordV1(
                    component_kind="wall", component_id=f"{s.axis}@{s.const}",
                    reason=(f"unowned_edge:[{s.lo},{s.hi}] -- no wall face pair "
                            "owns this cavity edge (a gap in the facts layer; "
                            "e.g. a face line the converter never collected)"),
                    propagated_from=view.view_id))
                continue
            hit = s.group.handles & unsigned_handles
            if hit:
                s.na.append(NaRecordV1(
                    component_kind="face_line", component_id=",".join(sorted(hit)),
                    reason="unsigned_revision_target: the ledger names this "
                           "line but no verdict is signed -- ⛔ silently using "
                           "as_measured's value would pass off 'unsigned' as "
                           "'already correct'",
                    propagated_from=",".join(sorted(s.group.run_ids)))
            raw = s.group.raw_face("lo" if s.side < 0 else "hi", face_by_id)
            thickness = (s.group.raw_face("hi", face_by_id)
                         - s.group.raw_face("lo", face_by_id))
            if thickness <= 0:
                s.na.append(NaRecordV1(
                    component_kind="wall", component_id=",".join(s.group.run_ids),
                    reason=f"nonpositive_thickness:{thickness}"))
                continue
            s.edge = self._project_span(s, raw, thickness, wall_region,
                                        footprint, view.view_id)

        na = [n for s in spans for n in s.na]
        na += [n for s in spans if s.edge is not None for n in s.edge.unprojectable]

        if any(s.edge is None for s in spans):
            # ⛔ the ring is one transaction: no coordinates at all (§1.5)
            return CompiledZoneV1(
                zone_id=zone_id, name=name, floor_id=view.floor_id,
                profile=self.profile.value, vertices=None,
                edges=[s.edge for s in spans if s.edge is not None],
                na=na, cavity_area_units2=int(round(cavity.area)))

        # -- 6c: merge same-group collinear spans, intersect support lines --
        merged = _merge_collinear(spans)
        vertices = _support_vertices(merged)
        return CompiledZoneV1(
            zone_id=zone_id, name=name, floor_id=view.floor_id,
            profile=self.profile.value,
            vertices=[[v[0], v[1]] for v in vertices],
            edges=[s.edge for s in merged], na=na,
            cavity_area_units2=int(round(cavity.area)))

    # -- the projection of ONE span (6b: one span, one basis) --------------
    def _project_span(self, span: _Span, raw_face: int, thickness: int,
                      wall_region: Polygon, footprint: Polygon,
                      view_id: str) -> CompiledZoneEdgeV1:
        outward = -span.side                     # into the band, away from cavity
        mid_along = (span.lo + span.hi) // 2
        exit_const = raw_face + outward * (thickness + 1)
        exit_pt = (Point(exit_const, mid_along) if span.axis == "y"
                   else Point(mid_along, exit_const))
        outside = (not footprint.contains(exit_pt)
                   and not wall_region.contains(exit_pt))
        if self.profile is OutputProfile.FORM_A_AXIS:
            basis = "interior"                   # A: every wall -> midline
            offset = thickness // 2
        else:
            basis = "exterior" if outside else "interior"
            offset = thickness if outside else thickness // 2
        na: list[NaRecordV1] = []
        if (thickness % 2
                and offset == thickness // 2):   # midline off the 0.1mm grid
            na.append(NaRecordV1(
                component_kind="wall",
                component_id=",".join(span.group.run_ids),
                reason=f"half_unit_midline:{raw_face}±{thickness}/2"))
        return CompiledZoneEdgeV1(
            axis=span.axis, span_lo=span.lo, span_hi=span.hi,
            out_const=raw_face + outward * offset, basis=basis,
            wall_ids=list(span.group.run_ids),
            face_line_handles=sorted(span.group.handles),
            basis_evidence={
                "raw_face_const": raw_face,
                "thickness_units": thickness,
                "outward": outward,
                "exit_point": [int(exit_pt.x), int(exit_pt.y)],
                "exit_outside_footprint_and_wall_region": bool(outside),
                "exit_in_footprint": bool(footprint.contains(exit_pt)),
                "exit_in_wall_region": bool(wall_region.contains(exit_pt)),
            },
            unprojectable=na)


# --------------------------------------------------------------------------- #
# pure helpers
# --------------------------------------------------------------------------- #
def _as_measured_hash(as_signed: AsSignedV1) -> str:
    """The revisions ledger binds to the AS_MEASURED content hash; as_signed
    carries it in its derivation key (and equals as_measured + signed
    revisions, so the binding is checkable without re-deriving)."""
    return as_signed.derivation.as_measured_content_sha256


def _build_groups(view: AsMeasuredViewV1,
                  face_by_id: dict) -> dict[tuple[str, int, int], _WallGroup]:
    by_id = {w.id: w for w in view.walls}
    runs: dict[tuple[str, int, int], list[AsMeasuredWallV1]] = {}
    for w in view.walls:
        runs.setdefault((w.axis, w.face_lo, w.face_hi), []).append(w)
    openings: dict[tuple[str, int, int], list[AsMeasuredOpeningV1]] = {}
    for o in view.openings:
        for wid in o.carrier_wall_ids:
            w = by_id.get(wid)
            if w is None:
                continue
            openings.setdefault((w.axis, w.face_lo, w.face_hi), []).append(o)
    groups: dict[tuple[str, int, int], _WallGroup] = {}
    for key, ws in runs.items():
        groups[key] = _WallGroup(
            axis=key[0], face_lo=key[1], face_hi=key[2],
            runs=tuple(sorted(ws, key=lambda w: (w.along_min, w.along_max,
                                                 w.id))),
            openings=tuple(sorted(openings.get(key, []),
                                  key=lambda o: (o.along_min, o.along_max, o.id))),
            handles=frozenset(h for w in ws
                              for h in list(w.face_line_ids_lo)
                              + list(w.face_line_ids_hi)))
    return groups


def _wall_region(view: AsMeasuredViewV1) -> Polygon:
    """The solid wall mass: wall band rectangles UNION opening fill
    rectangles (S4 polygonises over walls + opening fills; the difference
    without fills leaks rooms into each other through doorways)."""
    rects = []
    for w in view.walls:
        rects.append(_band_rect(w.axis, w.face_lo, w.face_hi,
                                w.along_min, w.along_max))
    for o in view.openings:
        rects.append(_band_rect(o.axis, o.cross_lo, o.cross_hi,
                                o.along_min, o.along_max))
    return unary_union(rects)


def _band_rect(axis: str, lo: int, hi: int, along_lo: int,
               along_hi: int) -> Polygon:
    if axis == "x":          # runs along x, faces are y coordinates
        return Polygon([(along_lo, lo), (along_hi, lo),
                        (along_hi, hi), (along_lo, hi)])
    return Polygon([(lo, along_lo), (lo, along_hi), (hi, along_hi), (hi, along_lo)])


def _footprint_polygon(view: AsMeasuredViewV1) -> Polygon:
    ext = next((r for r in view.footprint.rings if r.kind == "exterior"), None)
    if ext is None:
        raise AnswerCompilerInputError(
            f"answer_compiler_view_has_no_exterior_ring:{view.view_id}")
    return Polygon([(p[0], p[1]) for p in ext.points])


def _cavity_faces(footprint: Polygon, wall_region: Polygon,
                  request: TarchConversionRequestV1) -> list[Polygon]:
    """footprint − wall mass, S5's own area bisection (A_room from the
    request -- the criterion is identical to S5's, ⛔ no second opinion)."""
    threshold = request.min_room_area_m2 * UNITS_PER_METRE * UNITS_PER_METRE
    diff = footprint.difference(wall_region)
    faces = list(diff.geoms) if diff.geom_type == "MultiPolygon" else [diff]
    return [f for f in faces if f.area > threshold]


def _owning_group(groups: dict[tuple[str, int, int], _WallGroup],
                  axis: str, const: int, lo: int, hi: int) -> _WallGroup | None:
    """The wall group whose face (or bridging opening's cross face) this
    cavity span touches.  Face match first; opening-cross is the fallback --
    a span across a window lives on the fill rectangle's cross edge, which
    sits exactly on the wall faces."""
    for g in groups.values():
        if g.axis != axis or const not in (g.face_lo, g.face_hi):
            continue
        if any(min(c1, hi) - max(c0, lo) > 0 for c0, c1 in g.coverage()):
            return g
    for g in groups.values():
        if g.axis != axis:
            continue
        if any(const in (o.cross_lo, o.cross_hi)
               and min(o.along_max, hi) - max(o.along_min, lo) > 0
               for o in g.openings):
            return g
    return None


def _merge_collinear(spans: list[_Span]) -> list[_Span]:
    """6a/6c prep: consecutive spans of the SAME group, side and projected
    const are ONE support segment -- rotate the ring first so the start sits
    at a group change (the ring may start mid-wall)."""
    if not spans:
        return []
    start = 0
    for i in range(len(spans)):
        prev = spans[i - 1]
        if (prev.axis != spans[i].axis or prev.group != spans[i].group
                or prev.side != spans[i].side):
            start = i
            break
    rot = spans[start:] + spans[:start]
    merged: list[_Span] = []
    for s in rot:
        last = merged[-1] if merged else None
        if (last is not None and last.axis == s.axis
                and last.group == s.group and last.side == s.side
                and last.edge is not None and s.edge is not None
                and last.edge.out_const == s.edge.out_const):
            # absorb: same support line -> one span, one edge (6c's "one
            # line per wall", and the corner belongs to the INTERSECTION)
            last.hi = s.hi
            last.edge = last.edge.model_copy(
                update={"span_hi": s.hi})
            continue
        merged.append(s)
    return merged


def _support_vertices(merged: list[_Span]) -> list[tuple[int, int]]:
    """6c: vertices are INTERSECTIONS of adjacent support lines (one x-const
    with one y-const), ⛔ never wall-line endpoints; 6a: dedupe coincident
    vertices (a form-A step collapsing to zero)."""
    verts: list[tuple[int, int]] = []
    for i in range(len(merged)):
        a, b = merged[i - 1], merged[i]
        if a.axis == "y":                       # a's const is an x coordinate
            verts.append((a.edge.out_const, b.edge.out_const))
        else:
            verts.append((b.edge.out_const, a.edge.out_const))
    ded: list[tuple[int, int]] = []
    for v in verts:
        if not ded or v != ded[-1]:             # 6a: consecutive duplicates
            ded.append(v)
    if len(ded) > 1 and ded[0] == ded[-1]:      # 6a: wrap-around duplicate
        ded.pop()
    return ded


# --------------------------------------------------------------------------- #
# F-146 structural fix: the EXIT-side gate on the answer root's facts
# --------------------------------------------------------------------------- #
def read_facts_for_compilation(case: str) -> tuple[AsMeasuredV1, Any, AsSignedV1]:
    """The ONE read path the compiler's callers use for a case's facts trio.

    ⭐ F-146's structural fix (exit check, not entry narrowing): if the
    ANSWER ROOT already carries a facts trio (the promotion path will copy
    one there, ledger §八), it is read through the SAME reproducibility
    verification the staging read path runs --
    :func:`src.agent.judge.gt_revisions.verify_as_signed_reproduction` --
    so a trio that arrived under ``gt/<case>/facts/`` by ANY means (copied
    directory, hand-typed path, a future writer that bypassed the staging
    gate, TOCTOU during the copy) is re-verified on EVERY read.  The gate
    does not care how the bytes got there; it only asks whether what is
    there NOW reproduces.

    Until promotion copies facts, the staging root -- whose read path
    already runs the same gate -- serves the case.
    """
    trio = _read_answer_root_facts(case)
    if trio is not None:
        return trio
    from .gt_facts_staging import read_facts_candidate  # local: no cycles
    return read_facts_candidate(case)


def _read_answer_root_facts(case: str) -> tuple[AsMeasuredV1, Any, AsSignedV1] | None:
    """Answer-root branch of the exit gate: None while ``gt/<case>/facts/``
    does not exist; otherwise the parsed trio, freshly verified."""
    from .gt_revisions import (RevisionsLedgerV1,
                               verify_as_signed_reproduction)
    from .gt_schema import REPO_ROOT
    root = REPO_ROOT / "case_tests/test_baseline/gt" / case / "facts"
    if not root.is_dir():
        return None
    as_measured = AsMeasuredV1.model_validate_json(
        (root / "as_measured.json").read_bytes())
    revisions = RevisionsLedgerV1.model_validate_json(
        (root / "revisions.json").read_bytes())
    as_signed = AsSignedV1.model_validate_json(
        (root / "as_signed.json").read_bytes())
    verify_as_signed_reproduction(as_measured, revisions, as_signed)
    return as_measured, revisions, as_signed
