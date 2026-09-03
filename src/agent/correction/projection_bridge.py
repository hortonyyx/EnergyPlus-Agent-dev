"""B1 projection bridge: wall IR → rooms (``CorrectedGeometryV3`` cells).

Design authority: the projection-bridge design doc v7 (see the proposals
folder — ⛔ no repo-rooted path here, F-152: a repo path inside a .py string
constant would fabricate a dependency edge) — §四 the four steps, §六之三
the zero-parameter extension rule, §9.1 the collinear-gap contract.  This
module is the geometric core only:

    ① cut lines  = every wall midline + every opening span (as a midline
                   continuation) + collinear gaps (contract §9.1 option ①)
    ② endpoint extension: extend an endpoint onto a perpendicular line's
                   midline when the extending wall's band intersects the
                   other line's solid rectangle (touching counts)
    ③ cells      = the arrangement's bounded faces (shapely polygonize)
    ④ footprint  = the union of all bounded faces

The judge-side "wall → cavity" derivation is deliberately NOT reused
(design §三 路 C): this bridge cuts on midlines, the judge cuts on faces,
so the judge keeps its discriminating power over this module's defects.

Orthogonality (design §9.2): this bridge handles orthogonal midlines only,
and that assumption is LOCAL — it lives in exactly two places, the
``CutLineV1.axis`` literal type and :data:`ORTHOGONAL_AXES`.  A non-x/y axis
is rejected loudly at :func:`_validated_axis` (upstream, the wall compiler
already raises on non-x/y axes, so one cannot reach here today).

⭐ Length/thickness constants are FORBIDDEN in this module (guide §十三 #1):
every size is read from the data being processed (the other wall's own
declared thickness, this wall's own half thickness, the input's own declared
coordinate resolution).  The single tolerance is the input's declared
coordinate resolution — see :func:`resolution_from_units_per_metre`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict
from shapely.geometry import LineString, Point
from shapely.ops import polygonize, unary_union

from src.agent.correction.evidence_contract import (
    SOURCE_CONTRACT_AS_DRAWN,
    as_drawn_face_index,
    resolve_json_pointer,
)
from src.agent.correction.schema import (
    CellV3,
    CorrectedGeometryV3,
    FloorV3,
    FootprintRing,
)
from src.agent.correction.window_sources import Hex64, canonical_sha256

# ── the orthogonality assumption, localised and named (guide §十三 #3) ────── #
ORTHOGONAL_AXES: tuple[str, str] = ("x", "y")
"""The ONLY world axes this bridge understands (design §9.2: a non-x/y axis
cannot reach here today — the wall compiler raises on it upstream).  This
constant is the one place the orthogonality assumption lives; lifting it
later means touching this tuple and :class:`CutLineV1.axis`, not the repo."""


class ProjectionBridgeError(RuntimeError):
    """A loud, named failure of the projection bridge.

    ``code`` is machine-checkable (acceptance #4 asserts on it); the whole
    layer fails loudly — there is no silent fallback that hands a partial
    product downstream.
    """

    def __init__(self, code: str, detail: dict | None = None):
        self.code = code
        self.detail = detail or {}
        super().__init__(f"{code}: {detail or ''}")


def _validated_axis(axis: str) -> Literal["x", "y"]:
    """The ONE place a non-orthogonal axis is rejected (design §9.2)."""
    if axis not in ORTHOGONAL_AXES:
        raise ProjectionBridgeError(
            "NON_ORTHOGONAL_AXIS",
            {"axis": axis, "allowed": list(ORTHOGONAL_AXES)},
        )
    return axis  # type: ignore[return-value]


# ── the tolerance: the input's own declared resolution, nothing else ──────── #
def resolution_from_units_per_metre(units_per_metre: float) -> float:
    """1 unit in metres — the input's OWN declared coordinate resolution.

    ⚠️⚠️ N-3 (design §六之三, dispatch §三): ``units_per_metre`` exists ONLY on
    the gt-side facts layer (``as_measured``); the production chain is
    floating-point metres and carries no such field.  This tolerance is
    therefore bound to the FIXTURE input's granularity.  When the production
    chain is wired in, the granularity source MUST be redeclared there —
    ⛔ the 1-unit number must NOT be carried over.  A production caller with
    no declared granularity passes ``resolution_m=0.0`` (exact comparison),
    which is what the floating-point production data is: not quantised.
    """
    if units_per_metre <= 0:
        raise ProjectionBridgeError(
            "UNITS_PER_METRE_NOT_POSITIVE", {"units_per_metre": units_per_metre}
        )
    return 1.0 / float(units_per_metre)


# ── the cut line: the bridge's own representation ─────────────────────────── #
@dataclass(frozen=True)
class CutLineV1:
    """One line the arrangement is cut by, at a wall MIDLINE.

    ``pos_m`` is the midline's constant coordinate; ``along_lo_m``/``along_hi_m``
    the midline's extent along the other axis; ``half_thickness_m`` the source
    wall's own declared half thickness (openings: the carrier wall's — the
    opening's cross extent IS the wall band, probe §measurement 4).
    """

    axis: Literal["x", "y"]
    pos_m: float
    along_lo_m: float
    along_hi_m: float
    half_thickness_m: float
    kind: Literal["wall", "opening", "collinear_gap"]
    origin_id: str

    def __post_init__(self) -> None:
        _validated_axis(self.axis)

    @property
    def endpoint_lo(self) -> float:
        return self.along_lo_m

    @property
    def endpoint_hi(self) -> float:
        return self.along_hi_m


@dataclass(frozen=True)
class ExtensionRecordV1:
    """One executed endpoint extension (audit: what reached onto what)."""

    origin_id: str
    endpoint: Literal["lo", "hi"]
    from_m: float
    onto_origin_id: str
    onto_pos_m: float


@dataclass(frozen=True)
class CollinearGapRecordV1:
    """One collinear gap closed as an opening continuation (contract §9.1 ①).

    The rule: a gap between two co-axial, co-linear cut segments is treated
    as an opening continuation and closed by a cut segment of its own, so
    the two rooms the separating wall divides can never silently merge into
    one face.  ``half_thickness_from_origin`` names the wall segment whose
    own declared half thickness the closing segment borrows (⛔ no constant:
    the size is read from the data).
    """

    axis: Literal["x", "y"]
    pos_m: float
    from_m: float
    to_m: float
    half_thickness_from_origin: str


@dataclass(frozen=True)
class DanglingEndV1:
    """A named debt: an endpoint that after extension reaches nothing.

    Per design §四: a dangling end NEVER fails the layer — it is registered
    as a named debt and forces ``completion="degraded"``.  (The observation
    behind that rule, design §六之四 W2: a wall that was never observed
    leaves no geometric signature at all — only the judge's gt
    reconciliation can catch a missing wall, and this record is the honest
    "here is what I still see open" audit.)
    """

    debt_id: str
    origin_id: str
    endpoint: Literal["lo", "hi"]
    point_m: tuple[float, float]


@dataclass(frozen=True)
class ExtensionOutcome:
    """Everything step ② produces, for audit and for the tests."""

    lines: tuple[CutLineV1, ...]
    extensions: tuple[ExtensionRecordV1, ...] = ()
    collinear_gaps: tuple[CollinearGapRecordV1, ...] = ()


# ── step ①b: collinear gaps close as opening continuations (§9.1 option ①) ── #
def close_collinear_gaps(
    lines: Sequence[CutLineV1], *, resolution_m: float
) -> tuple[tuple[CutLineV1, ...], tuple[CollinearGapRecordV1, ...]]:
    """Close every gap between co-linear segments OF THE SAME wall (§9.1 ①).

    The dispatch has ALREADY chosen option ① (⛔ non-negotiable): a
    collinear gap is an opening continuation and gets a cut segment of its
    own.  The gap's scope is the segments' OWN wall — ``origin_id`` groups
    them (in the production shape that is one ``ResolvedWallV1``'s
    ``resolved_along_intervals``, which §9.1 names as the very thing that is
    multi-segment).  ⚠️ Measured on real sm25 (dispatch acceptance #6 is
    ⛔ non-negotiable F1=14/F2=15): closing gaps BETWEEN DIFFERENT walls
    over-cuts one face (15≠14) — the 2.24 m opening between two independent
    wall ids is a real open connection the gt signs as connected, so
    bridging it fabricates a wall.  A gap inside ONE wall is a drawn break
    of that wall (the §9.1 probe's 100 mm separator-wall split), and that —
    only that — is closed.

    Closing segments borrow the START-side segment's own declared half
    thickness (read from the data, ⛔ never a constant); declared openings
    carry their own origin and never bridge two different walls.
    """
    by_origin: dict[str, list[CutLineV1]] = {}
    for line in lines:
        _validated_axis(line.axis)
        by_origin.setdefault(line.origin_id, []).append(line)

    closed: list[CutLineV1] = list(lines)
    records: list[CollinearGapRecordV1] = []
    for origin_id, bucket in by_origin.items():
        if len(bucket) < 2:
            continue
        ordered = sorted(bucket, key=lambda l: (l.along_lo_m, l.along_hi_m))
        for left, right in zip(ordered, ordered[1:]):
            gap_lo, gap_hi = left.along_hi_m, right.along_lo_m
            if gap_hi - gap_lo <= resolution_m:
                continue  # touching segments: no gap to close
            records.append(
                CollinearGapRecordV1(
                    axis=left.axis,
                    pos_m=left.pos_m,
                    from_m=gap_lo,
                    to_m=gap_hi,
                    half_thickness_from_origin=origin_id,
                )
            )
            closed.append(
                CutLineV1(
                    axis=left.axis,
                    pos_m=left.pos_m,
                    along_lo_m=gap_lo,
                    along_hi_m=gap_hi,
                    half_thickness_m=left.half_thickness_m,
                    kind="collinear_gap",
                    origin_id=f"collinear_gap:{origin_id}",
                )
            )
    return tuple(closed), tuple(records)


# ── step ②: the zero-parameter extension rule (design §六之三 #4) ─────────── #
def _in_band(value: float, center: float, half: float, resolution_m: float) -> bool:
    """``|value − center| ≤ half + resolution`` — the ONLY comparison shape.

    ``half`` is always somebody's OWN declared half thickness and
    ``resolution_m`` always the input's OWN declared coordinate resolution
    (design §六之三: the tolerance is data-declared, ⛔ never a number the
    implementer picked).
    """
    return abs(value - center) <= half + resolution_m


def extend_endpoints(
    lines: Sequence[CutLineV1], *, resolution_m: float
) -> ExtensionOutcome:
    """Extend each endpoint onto a perpendicular midline it reaches.

    The rule (design §六之三 measurement 4 + v5's explicit precondition,
    cross-review B-R1): when THIS line's wall band intersects the OTHER
    line's solid rectangle — touching counts — and THIS line's endpoint lies
    inside the OTHER line's band, extend that endpoint onto the other line's
    MIDLINE.  Both sizes are read from the data:

    * the cross-direction band test uses THIS line's own half thickness
      (the end-lap buffer: an outer wall's midline necessarily sits half of
      the INNER wall's thickness beyond the inner wall's extent — the buffer
      is that geometry, ⛔ not a tunable, B-R1);
    * the endpoint test uses the OTHER line's own declared half thickness
      (the ruler the measured object provides itself).

    Extension is outward-only (``other.pos`` beyond the current endpoint),
    so a line that already crosses the other midline is never shortened.
    """
    for line in lines:
        _validated_axis(line.axis)
    records: list[ExtensionRecordV1] = []
    extended: list[CutLineV1] = []
    for line in lines:
        lo, hi = line.along_lo_m, line.along_hi_m
        lo_from, hi_from = lo, hi
        for other in lines:
            if other.axis == line.axis:
                continue  # the rule handles perpendicular pairs only
            # cross-direction: this line's BAND (pos ± my half thickness)
            # against the other line's along extent — touching counts, and
            # the declared resolution absorbs quantisation remainders.
            crosses = (
                other.along_lo_m - line.half_thickness_m - resolution_m
                <= line.pos_m
                <= other.along_hi_m + line.half_thickness_m + resolution_m
            )
            if not crosses:
                continue
            if (
                _in_band(lo, other.pos_m, other.half_thickness_m, resolution_m)
                and other.pos_m < lo
            ):
                lo = other.pos_m
                records.append(
                    ExtensionRecordV1(
                        origin_id=line.origin_id,
                        endpoint="lo",
                        from_m=lo_from,
                        onto_origin_id=other.origin_id,
                        onto_pos_m=other.pos_m,
                    )
                )
            if (
                _in_band(hi, other.pos_m, other.half_thickness_m, resolution_m)
                and other.pos_m > hi
            ):
                hi = other.pos_m
                records.append(
                    ExtensionRecordV1(
                        origin_id=line.origin_id,
                        endpoint="hi",
                        from_m=hi_from,
                        onto_origin_id=other.origin_id,
                        onto_pos_m=other.pos_m,
                    )
                )
        extended.append(
            CutLineV1(
                axis=line.axis,
                pos_m=line.pos_m,
                along_lo_m=lo,
                along_hi_m=hi,
                half_thickness_m=line.half_thickness_m,
                kind=line.kind,
                origin_id=line.origin_id,
            )
        )
    return ExtensionOutcome(lines=tuple(extended), extensions=tuple(records))


# ── steps ③④: the arrangement's bounded faces and the derived footprint ──── #
@dataclass(frozen=True)
class PartitionOutcome:
    """Steps ③④ in one auditable object."""

    faces: tuple[tuple[tuple[float, float], ...], ...]  # CCW open rings
    footprint_ring: tuple[tuple[float, float], ...]
    dangling_ends: tuple[DanglingEndV1, ...] = field(default=())


def _line_string(line: CutLineV1) -> LineString:
    if line.axis == "x":
        return LineString(
            [(line.along_lo_m, line.pos_m), (line.along_hi_m, line.pos_m)]
        )
    return LineString(
        [(line.pos_m, line.along_lo_m), (line.pos_m, line.along_hi_m)]
    )


def partition_lines(
    lines: Sequence[CutLineV1],
    *,
    resolution_m: float,
    origin_label: str = "",
) -> PartitionOutcome:
    """polygonize the extended lines; collect faces, footprint, dangling ends.

    Failure contract (design §四, acceptance #4): ZERO bounded faces after
    extension is the one and only layer-loud failure — everything else
    (dangling ends among them) degrades.  The dangling-end detector is the
    probe's own criterion: an extended endpoint that no OTHER line reaches
    (distance > 0 to every other segment) — an endpoint on another line
    contributes to closure, an endpoint in free space does not.
    """
    if not lines:
        raise ProjectionBridgeError("NO_CUT_LINES", {"origin": origin_label})
    segments = [_line_string(line) for line in lines]
    merged = unary_union(segments)
    bounded = list(polygonize(merged))
    faces = []
    for polygon in bounded:
        ring = tuple((float(x), float(y)) for x, y in polygon.exterior.coords)
        # shapely's exterior ring is closed (first == last); the cell
        # contract wants an OPEN ring
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        # orientation: cell polygons must be CCW (cell_geometry contract)
        area2 = sum(
            ring[i][0] * ring[(i + 1) % len(ring)][1]
            - ring[(i + 1) % len(ring)][0] * ring[i][1]
            for i in range(len(ring))
        )
        if area2 < 0:
            ring = tuple(reversed(ring))
        faces.append(ring)
    if not faces:
        raise ProjectionBridgeError(
            "NO_BOUNDED_FACES_AFTER_EXTENSION",
            {"n_cut_lines": len(lines), "origin": origin_label},
        )
    footprint = unary_union(bounded)
    # the footprint is the union of all bounded faces (step ④); interiors
    # (courtyards) are a shape this single-floor bridge does not cover —
    # loud, not silently dropped.
    if footprint.geom_type != "Polygon":
        raise ProjectionBridgeError(
            "FOOTPRINT_NOT_A_SINGLE_POLYGON",
            {"geom_type": footprint.geom_type, "origin": origin_label},
        )
    if footprint.interiors:
        raise ProjectionBridgeError(
            "FOOTPRINT_HAS_INTERIORS",
            {"n_interiors": len(footprint.interiors), "origin": origin_label},
        )
    fp_ring = tuple((float(x), float(y)) for x, y in footprint.exterior.coords)
    if len(fp_ring) > 1 and fp_ring[0] == fp_ring[-1]:
        fp_ring = fp_ring[:-1]

    dangling: list[DanglingEndV1] = []
    for index, line in enumerate(lines):
        for endpoint_label, endpoint in (
            ("lo", (line.along_lo_m if line.axis == "x" else line.pos_m,
                    line.pos_m if line.axis == "x" else line.along_lo_m)),
            ("hi", (line.along_hi_m if line.axis == "x" else line.pos_m,
                    line.pos_m if line.axis == "x" else line.along_hi_m)),
        ):
            point = Point(endpoint)
            reached = any(
                index != j and point.distance(seg) <= resolution_m
                for j, seg in enumerate(segments)
            )
            if not reached:
                dangling.append(
                    DanglingEndV1(
                        debt_id=(
                            f"dangling_end:{origin_label or 'view'}:"
                            f"{line.origin_id}:{endpoint_label}"
                        ),
                        origin_id=line.origin_id,
                        endpoint=endpoint_label,  # type: ignore[arg-type]
                        point_m=(float(endpoint[0]), float(endpoint[1])),
                    )
                )
    return PartitionOutcome(
        faces=tuple(faces),
        footprint_ring=fp_ring,
        dangling_ends=tuple(dangling),
    )


# ── the envelope contract (design §四, ⛔ no new vocabulary) ───────────────── #
_CFG = ConfigDict(extra="forbid")


class DanglingEndRecordV1(BaseModel):
    """Envelope-serialisable dangling-end debt (design §四: named + degraded)."""

    model_config = _CFG
    debt_id: str
    origin_id: str
    endpoint: Literal["lo", "hi"]
    point_m: tuple[float, float]


class CollinearGapSegmentRecordV1(BaseModel):
    """Envelope-serialisable record of one §9.1-① collinear-gap closing."""

    model_config = _CFG
    axis: Literal["x", "y"]
    pos_m: float
    from_m: float
    to_m: float
    half_thickness_from_origin: str


class CorrectedGeometryProjectionEnvelopeV1(BaseModel):
    """The projection bridge's whole product (design §四).

    Hard rules carried from the design (unchanged here):
    * ``source_resolved_sha256`` binds the input: it IS the wall
      compilation's ``content_sha256``; a mismatch at the consumer is a
      projection failure, and the bare ``geometry`` never travels without
      this envelope (⛔ never hand the geometry on as a complete product).
    * ``strict`` profiles refuse ``degraded`` before the judge;
      ``exploratory`` may pass it through, visible in the report, and never
      shrinks the judge's denominator.
    * ``output_basis`` reuses the judge-side value vocabulary
      (``wall_axis`` / ``outer_skin``) — the VALUES, ⛔ never the
      implementation (design §三 路 C stays rejected).

    Contract clauses this B1 module pins explicitly:
    * ``footprint_provenance="derived_from_walls"`` — B3 (cells tile the
      footprint, no holes) is TRUE BY CONSTRUCTION on this chain (the
      footprint IS the union of the cells), which is exactly why the outer
      outline reconciliation is handed to the judge side (zero-parameter:
      gt outer area vs derived area, the difference being the outer-wall
      t/2 inset).  The field makes that fact readable IN the product.
    * ``collinear_gap_segments`` — contract §9.1 option ① (dispatch §一之二,
      chosen, non-negotiable): a gap inside ONE wall (its own
      multi-segment extent) is an opening continuation and is closed by a
      cut segment; a gap BETWEEN two different walls is NOT (measured on
      real sm25: closing cross-wall gaps over-cuts a face against the
      signed gt).
    * ``completion``: ``degraded`` ⇔ at least one dangling end (design §四:
      the one named trigger — reading-ledger emptiness is NOT a
      completeness proof either way).
    """

    model_config = _CFG
    schema_version: Literal["projection_envelope_v1"]
    source_resolved_sha256: Hex64
    view_id: str | None = None
    floor_ref: str | None = None
    output_basis: Literal["wall_axis", "outer_skin"]
    geometry: CorrectedGeometryV3
    completion: Literal["complete", "degraded"]
    residual_evidence_debt_ids: tuple[str, ...] = ()
    dangling_end_debts: tuple[DanglingEndRecordV1, ...] = ()
    collinear_gap_segments: tuple[CollinearGapSegmentRecordV1, ...] = ()
    extension_count: int = 0
    face_count: int = 0
    tolerance_resolution_m: float
    resolution_source: str
    footprint_provenance: Literal["derived_from_walls"]
    projection_sha256: Hex64 | None = None


# ── loaders: the fixture world and the production world ───────────────────── #
def cut_lines_from_as_measured_view(
    view: dict[str, Any], *, units_per_metre: float
) -> tuple[tuple[CutLineV1, ...], float]:
    """Load cut lines from one gt-facts-layer view (the FIXTURE world).

    The fixture world (dispatch §三): the tolerance is bound to THIS
    input's own declared granularity — ``units_per_metre`` exists only
    here.  Wall midlines come from each wall's own face pair; opening
    midlines sit on the carrier wall's midline with the carrier's half
    thickness (the opening's cross extent IS the wall band).
    """
    resolution_m = resolution_from_units_per_metre(units_per_metre)
    lines: list[CutLineV1] = []
    for wall in view["walls"]:
        lines.append(
            CutLineV1(
                axis=_validated_axis(wall["axis"]),
                pos_m=(wall["face_lo"] + wall["face_hi"]) / 2.0 / units_per_metre,
                along_lo_m=wall["along_min"] / units_per_metre,
                along_hi_m=wall["along_max"] / units_per_metre,
                half_thickness_m=wall["thickness"] / 2.0 / units_per_metre,
                kind="wall",
                origin_id=wall["id"],
            )
        )
    for opening in view["openings"]:
        lines.append(
            CutLineV1(
                axis=_validated_axis(opening["axis"]),
                pos_m=(opening["cross_lo"] + opening["cross_hi"]) / 2.0 / units_per_metre,
                along_lo_m=opening["along_min"] / units_per_metre,
                along_hi_m=opening["along_max"] / units_per_metre,
                half_thickness_m=(
                    opening["cross_hi"] - opening["cross_lo"]
                ) / 2.0 / units_per_metre,
                kind="opening",
                origin_id=opening["id"],
            )
        )
    return tuple(lines), resolution_m


@dataclass(frozen=True)
class OpeningSpanV1:
    """One production opening, dereferenced BY REFERENCE (measured choice).

    The bundle's ``opening_claims`` are reference-only; the wiring
    dereferences each into (the face line's observation id + the opening's
    along-wall span in world metres) — ⛔ NOT into geometry.  Host-wall
    resolution is likewise by REFERENCE: the host is the wall whose own
    ``source_refs`` claim that face observation id.

    Why reference, not geometry (measured on the real sm25 2f product
    before this choice was made): a geometric band test
    (``|midline − face| ≤ half-thickness``) resolves only 11 of 87
    openings — 76 fail structurally, in two classes: (a) the wall's own
    resolved coverage EXCLUDES the opening gap, so the span sits between
    two segments OF THE SAME wall and matches both; (b) the midline is a
    DERIVED ``(face_a + face_b) / 2`` float, so the touching boundary is
    off by up to ~1 ulp (measured ``+4.3e-16`` on L009) and exact
    comparison flips.  The reference graph resolves 23/23 faces to exactly
    one wall — zero tolerance, zero geometry, and no invented epsilon.
    """

    opening_id: str
    face_observation_id: str
    span_lo_m: float
    span_hi_m: float


def _run_axis(constant_world_axis: Literal["x", "y"]) -> Literal["x", "y"]:
    """Map the wall compiler's CONSTANT-axis vocabulary onto this module's.

    ⚠️ Two different axis vocabularies meet here, and they are OPPOSITE:
    the wall compiler (and the face lines it reads) names the CONSTANT
    axis (``constant_world_axis == "x"`` ⇒ x is fixed, the line varies in
    y), while ``CutLineV1.axis`` names the RUN axis (``"x"`` ⇒ the
    rendered segment varies in x, ``_line_string`` puts ``pos_m`` on y —
    the convention the gt facts layer also uses, and the one the fixture
    loader inherits).  Copying ``constant_world_axis`` straight into
    ``CutLineV1.axis`` transposes the whole floor by 90° (measured: bbox
    [0.12, 0.12, 24.88, 19.88] becomes [0.12, 0.12, 19.88, 24.88] against
    the signed gt footprint x∈[0,25] y∈[0,20]).
    """
    return "y" if constant_world_axis == "x" else "x"


def cut_lines_from_wall_compilation(
    walls: Sequence[Any],
    opening_spans: Sequence[OpeningSpanV1] = (),
) -> tuple[tuple[CutLineV1, ...], tuple[DanglingEndRecordV1, ...]]:
    """Load cut lines from the production wall IR (``ResolvedWallV1``s).

    A wall whose centerline / thickness is unresolved cannot be projected:
    ⛔ skipping it silently is exactly the W2 failure mode (a missing wall
    leaves no geometric signature), so it fails LOUDLY here — the decision
    loop's success exit guarantees none reach this point.

    Openings resolve to their carrier wall by REFERENCE (see
    :class:`OpeningSpanV1`): the host is the wall whose ``source_refs``
    claim the opening's face observation.  The opening's cut line borrows
    the HOST wall's own axis / midline / half thickness — every number
    read from the wall's own resolution, ⛔ none invented here.
    """
    lines: list[CutLineV1] = []
    resolved_walls = []
    for wall in walls:
        centerline = wall.resolved_centerline
        thickness = wall.resolved_thickness_m
        if centerline is None or centerline.constant_world_axis is None \
                or centerline.constant_pos_m is None or thickness is None:
            raise ProjectionBridgeError(
                "WALL_NOT_PROJECTABLE",
                {"wall_id": wall.wall_id,
                 "has_centerline": centerline is not None,
                 "has_thickness": thickness is not None},
            )
        axis = _run_axis(
            _validated_axis(centerline.constant_world_axis)
        )
        resolved_walls.append(wall)
        for lo, hi in wall.resolved_along_intervals:
            lines.append(
                CutLineV1(
                    axis=axis,
                    pos_m=float(centerline.constant_pos_m),
                    along_lo_m=float(lo),
                    along_hi_m=float(hi),
                    half_thickness_m=float(thickness) / 2.0,
                    kind="wall",
                    origin_id=wall.wall_id,
                )
            )
    owner: dict[str, list[Any]] = {}
    for wall in resolved_walls:
        for ref in wall.source_refs:
            owner.setdefault(ref.observation_id, []).append(wall)
    for span in opening_spans:
        owners = owner.get(span.face_observation_id, ())
        if len(owners) != 1:
            raise ProjectionBridgeError(
                "OPENING_HOST_UNRESOLVED",
                {"opening_id": span.opening_id,
                 "face_observation_id": span.face_observation_id,
                 "n_owner_walls": len(owners),
                 "owner_wall_ids": [w.wall_id for w in owners]},
            )
        host = owners[0]
        centerline = host.resolved_centerline
        lines.append(
            CutLineV1(
                axis=_run_axis(
                    _validated_axis(centerline.constant_world_axis)
                ),
                pos_m=float(centerline.constant_pos_m),
                along_lo_m=span.span_lo_m,
                along_hi_m=span.span_hi_m,
                half_thickness_m=float(host.resolved_thickness_m) / 2.0,
                kind="opening",
                origin_id=span.opening_id,
            )
        )
    return tuple(lines), ()


def opening_spans_from_artifact(artifact: Any) -> tuple[OpeningSpanV1, ...]:
    """Dereference the bundle's ``opening_claims`` into spans (production).

    Walks every frozen as-drawn source, resolves each opening claim's json
    pointer into that source's own ``hypotheses.opening_candidates`` node
    (identity-checked the same way the wall compiler checks face nodes),
    and reads the claim's ``face_line`` id plus ``span_m``.  Malformed
    nodes, dangling pointers and face ids missing from the observation
    index are LOUD — a dangling opening reference is never a guess.
    """
    spans: list[OpeningSpanV1] = []
    for source in artifact.frozen_sources:
        meta = source.artifact
        if meta.source_contract_id != SOURCE_CONTRACT_AS_DRAWN:
            continue
        doc = json.loads(source.raw_bytes.decode("utf-8"))
        face_index = as_drawn_face_index(doc)
        for claim in artifact.bundle.opening_claims:
            if claim.source_ref.input_id != meta.input_id:
                continue
            node = resolve_json_pointer(doc, claim.source_ref.json_pointer)
            if not isinstance(node, dict) \
                    or node.get("id") != claim.source_ref.observation_id:
                raise ProjectionBridgeError(
                    "OPENING_NODE_MISMATCH",
                    {"input_id": meta.input_id,
                     "pointer": claim.source_ref.json_pointer,
                     "ref_says": claim.source_ref.observation_id},
                )
            face_line = node.get("face_line")
            span = node.get("span_m")
            if face_line not in face_index \
                    or not isinstance(span, list) or len(span) != 2 \
                    or not all(
                        isinstance(v, (int, float)) and not isinstance(v, bool)
                        for v in span
                    ) \
                    or not float(span[0]) < float(span[1]):
                raise ProjectionBridgeError(
                    "OPENING_DEREF_MALFORMED",
                    {"opening_id": claim.opening_id,
                     "face_line": face_line,
                     "span_m": span},
                )
            spans.append(
                OpeningSpanV1(
                    opening_id=claim.opening_id,
                    face_observation_id=face_line,
                    span_lo_m=float(span[0]),
                    span_hi_m=float(span[1]),
                )
            )
    return tuple(spans)


# ── the main entry: cut lines → envelope ──────────────────────────────────── #
def _cells_from_faces(
    faces: Sequence[tuple[tuple[float, float], ...]], *, floor_id: str
) -> list[CellV3]:
    cells: list[CellV3] = []
    ordered = sorted(
        faces,
        key=lambda ring: (
            min(p[0] for p in ring),
            min(p[1] for p in ring),
            len(ring),
            ring,
        ),
    )
    for index, ring in enumerate(ordered):
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        cells.append(
            CellV3(
                id=f"{floor_id}-c{index:03d}",
                x=[float(min(xs)), float(max(xs))],
                y=[float(min(ys)), float(max(ys))],
                polygon=[[float(x), float(y)] for x, y in ring],
            )
        )
    return cells


def project_cut_lines(
    cut_lines: Sequence[CutLineV1],
    *,
    resolution_m: float,
    resolution_source: str,
    source_resolved_sha256: str,
    floor_id: str,
    floor_name: str,
    z_floor_m: float,
    ceiling_height_m: float,
    output_basis: Literal["wall_axis", "outer_skin"] = "wall_axis",
    residual_debt_ids: Sequence[str] = (),
    view_id: str | None = None,
    floor_ref: str | None = None,
    origin_label: str = "",
) -> CorrectedGeometryProjectionEnvelopeV1:
    """Drive steps ①–④ and wrap the result in the envelope contract.

    ``resolution_source`` is a REQUIRED human-readable declaration of where
    ``resolution_m`` came from (N-3: the fixture world's is the gt facts
    layer's own ``units_per_metre``; the production chain must redeclare its
    own — passing 0.0 with a source note saying "floating-point, not
    quantised" is the honest production value today).

    ``z_floor_m`` / ``ceiling_height_m`` are required with no defaults: B1
    has no z source (that is B2's wiring) and ⛔ this module never invents
    one — a caller without a sourced value cannot construct a product.
    """
    if output_basis != "wall_axis":
        # The algorithm is parameterised on the basis (the contract carries
        # it); implementing the outer_skin form is explicitly NOT this
        # dispatch (§四).  Loud, never a silent axis-form fallback.
        raise ProjectionBridgeError(
            "PROJECTION_BASIS_UNIMPLEMENTED",
            {"requested": output_basis, "implemented": ["wall_axis"]},
        )
    closed, gap_records = close_collinear_gaps(cut_lines, resolution_m=resolution_m)
    extension = extend_endpoints(closed, resolution_m=resolution_m)
    partition = partition_lines(
        extension.lines, resolution_m=resolution_m, origin_label=origin_label
    )
    cells = _cells_from_faces(partition.faces, floor_id=floor_id)
    fp = partition.footprint_ring
    xs = [p[0] for p in fp]
    ys = [p[1] for p in fp]
    floor = FloorV3(
        id=floor_id,
        name=floor_name,
        z_floor=float(z_floor_m),
        ceiling_height=float(ceiling_height_m),
        footprint=FootprintRing(
            vertices=[[float(x), float(y)] for x, y in fp]
        ),
        cells=cells,
    )
    geometry = CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[float(min(xs)), float(max(xs))],
        footprint_y=[float(min(ys)), float(max(ys))],
        floors=[floor],
        windows=[],
        facade_segments=[],
    )
    dangling = tuple(
        DanglingEndRecordV1(
            debt_id=d.debt_id,
            origin_id=d.origin_id,
            endpoint=d.endpoint,
            point_m=tuple(d.point_m),  # type: ignore[arg-type]
        )
        for d in partition.dangling_ends
    )
    completion: Literal["complete", "degraded"] = (
        "degraded" if dangling else "complete"
    )
    envelope = CorrectedGeometryProjectionEnvelopeV1(
        schema_version="projection_envelope_v1",
        source_resolved_sha256=source_resolved_sha256,
        view_id=view_id,
        floor_ref=floor_ref,
        output_basis=output_basis,
        geometry=geometry,
        completion=completion,
        residual_evidence_debt_ids=tuple(sorted(set(residual_debt_ids))),
        dangling_end_debts=dangling,
        collinear_gap_segments=tuple(
            CollinearGapSegmentRecordV1(
                axis=g.axis,
                pos_m=g.pos_m,
                from_m=g.from_m,
                to_m=g.to_m,
                half_thickness_from_origin=g.half_thickness_from_origin,
            )
            for g in gap_records
        ),
        extension_count=len(extension.extensions),
        face_count=len(partition.faces),
        tolerance_resolution_m=float(resolution_m),
        resolution_source=resolution_source,
        footprint_provenance="derived_from_walls",
    )
    content = json.loads(envelope.model_dump_json())
    content.pop("projection_sha256")
    return envelope.model_copy(
        update={"projection_sha256": canonical_sha256(content)}
    )


__all__ = [
    "ORTHOGONAL_AXES",
    "CollinearGapRecordV1",
    "CollinearGapSegmentRecordV1",
    "CutLineV1",
    "CorrectedGeometryProjectionEnvelopeV1",
    "DanglingEndRecordV1",
    "DanglingEndV1",
    "ExtensionOutcome",
    "ExtensionRecordV1",
    "OpeningSpanV1",
    "PartitionOutcome",
    "ProjectionBridgeError",
    "cut_lines_from_as_measured_view",
    "cut_lines_from_wall_compilation",
    "opening_spans_from_artifact",
    "close_collinear_gaps",
    "extend_endpoints",
    "partition_lines",
    "project_cut_lines",
    "resolution_from_units_per_metre",
]
