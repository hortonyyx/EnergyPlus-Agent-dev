"""``AsMeasuredV1`` -- the first of the facts layer's three cuts.

    as_measured  +  revisions  =>  as_signed        (architecture/gt_revision_ledger.md §一)
    ^^^^^^^^^^^ THIS FILE.  ⛔ ``revisions`` / ``as_signed`` are ②-1b, not here.

⭐ WHAT IT IS: what the machine measured off the **un-retouched** drawing.
⛔ WHAT IT IS NOT: an answer.  Nothing here is projected, expanded, or given a
modelling ``basis``; ⛔ this file does not know what an outer skin is.

## Three things it deliberately does NOT store (dispatch ②-1a R2)

1. ``basis`` -- axis vs outer-skin is a CHOICE MADE WHEN COMPILING AN ANSWER
   (guide §十.6b), not something a drawing can be measured for.  ⇒ ②-1c.
2. **expanded endpoints** -- F-122 measured that the S7 zone-edge report's
   per-edge endpoints are the answer edges AFTER S7 pushed them out by t or t/2
   (``offset_m == (t if outer_skin else t/2)``, 136/136; all 272 endpoints
   already 0.060-0.339 m outside their claimed cavity).  Copying them in would
   be a semantic reverse-migration, and any compiler then validated against
   them would only replay the producer's own choice.
3. ``boundary_condition`` (interior/exterior identity) -- ⇒ ②-1d.

⭐ Consequently the source of every field here is **P1 (S0-S4)**, i.e.
``run_p1_plan_view``, and ⛔ never S5-S7.  ``test_as_measured_facts_layer.py``
greps this module for the S7 names and fails if one appears.

## Junctions: the layer stores LINES, ⛔ not corner points

Guide §十.6c, measured on sm25: all 54 orthogonal junctions agree -- a wall line
stops at the NEAR FACE of the wall it runs into, so the corner square is claimed
by neither.  A facts layer that stored per-edge corner points would freeze one
particular junction resolution into the record and turn F-134 from "solved in
the S7 expansion step" into "unsolved".  So a wall is stored as
``(two face lines, thickness, along-wall interval)`` and the along-wall interval
is for the denominator and for locating openings -- ⛔ NOT for deciding corners.

## 0.1 mm integers, and why that is a REPRESENTATION change, ⛔ not a snap

User 2026-08-29: coordinates are stored as integers in units of 0.1 mm.  ⛔ This
is not a tolerance and ⛔ not an extra snapping pass -- the converter has already
quantised; this is the *storage type*.  Floats cannot be compared bit-for-bit
after a round trip, and F-98's family of "the two rulers disagree in the 12th
decimal" problems is a property of the representation, not of the geometry.
Every geometric number below is ``int``; ⛔ there is no float in the document
outside ``converter_readouts``, where the converter's own records ride out
VERBATIM (see below).  ``test_as_measured_facts_layer.py`` asserts exactly that.

## ⛔ Nothing is re-derived from the drawing

Everything is either copied from ``P1PlanViewGeometry`` or is a unit conversion
of something copied from it.  The 2026-08-29 lesson (the converter had already
computed the readouts and the consumer dropped them on the floor) is why
``dangles`` / ``cuts`` / ``invalid`` / ``diagnostics`` / ``gates`` are carried
through untouched, ⛔ never recomputed.

⭐ And nothing is dropped silently either ([[absence-conflates-causes-in-observables]]).
``wall_lines`` can legitimately contain a stroke that is neither horizontal nor
vertical (measured: 1 in as-received ``plan-F1`` -- F-129).  It cannot be a
"face line at a constant coordinate", so it is itemised in
``converter_readouts.non_orthogonal_lines`` and a model validator enforces the
ledger identity

    wall_lines_total == len(face_lines) + non_orthogonal + degenerate

so a stroke can never leave the record by simply not being appended to a list.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from .gt_manifest import Affine2D, load_gt_tooling_config
from .gt_schema import (REPO_ROOT, DxfHandle, Hex64, HumanLabel, StableId,
                        StrictNonNegativeInt)
from .tarch_converter_schema import (JsonDict, TarchConversionRequestV1,
                                     _StrictModel, compute_request_sha256)
from .tarch_normalize import P1PlanViewGeometry, run_p1_plan_view

GT_CFG = REPO_ROOT / "src/configs/judge_gt.yaml"
VG_CFG = REPO_ROOT / "src/configs/correction.yaml"

#: Storage unit.  1 world metre == 10000 units.  ⛔ Declared, never inferred.
UNITS_PER_METRE = 10_000
UNIT_LABEL = "0.1mm"


class AsMeasuredUnavailable(RuntimeError):
    """⛔ Raised instead of returning a facts document that is quietly partial.

    Same shape as ``DenominatorUnavailable`` (F-126): there is no object to keep
    using, and the reason is named.  ⛔ An empty/blocked conversion must never be
    indistinguishable from "this drawing genuinely has nothing on it".
    """

    def __init__(self, reason: str, *, view_id: str, detail: str,
                 blocking_codes: list[str] | None = None) -> None:
        self.reason = reason
        self.view_id = view_id
        self.detail = detail
        self.blocking_codes = list(blocking_codes or [])
        super().__init__(f"as_measured_unavailable[{reason}] view={view_id}: {detail}"
                         + (f" (BLOCK: {', '.join(self.blocking_codes)})"
                            if self.blocking_codes else ""))


# --------------------------------------------------------------------------- #
# unit conversion -- the ONLY place metres become storage integers
# --------------------------------------------------------------------------- #
def to_units(metres: float) -> int:
    """World metres -> 0.1 mm integer.  ⛔ One implementation, used everywhere.

    ``round`` is banker's rounding: deterministic, and the half-way case is
    0.05 mm -- three orders of magnitude below anything the converter's own
    quantisation leaves behind.
    """
    return int(round(float(metres) * UNITS_PER_METRE))


def _axis_aligned(affine: Affine2D, view_id: str) -> tuple[float, float, float, float]:
    """Return (sx, tx, sy, ty) for an axis-preserving source->world affine.

    ⛔ Loud, not assumed: a constant-coordinate face line only *exists* if the
    transform maps the x axis to the x axis.  Measured on sm25-L, both plan
    views are pure scale+translate (``m01 == m10 == 0.0``, ``m00 == m11 ==
    0.001``) -- but a request is free to declare a rotation, and this layer
    would silently mislabel every axis if it did.
    """
    if affine.m01 != 0.0 or affine.m10 != 0.0:
        raise AsMeasuredUnavailable(
            "non_axis_aligned_affine", view_id=view_id,
            detail=(f"world_from_source_m has m01={affine.m01} m10={affine.m10}; "
                    "a constant-coordinate face line is not well defined under "
                    "a rotating/shearing transform"))
    return affine.m00, affine.m02, affine.m11, affine.m12


# --------------------------------------------------------------------------- #
# schema
# --------------------------------------------------------------------------- #
class AsMeasuredFaceLineV1(_StrictModel):
    """One drawn wall FACE line, exactly as the converter collected it.

    ``axis`` is the direction the line RUNS ALONG; the constant coordinate is on
    the other axis.  ⛔ There is no "wall side" here -- which of a wall's two
    faces this is, is stated by the wall that references it, not by the line.
    """
    id: DxfHandle                       # the DXF handle; unique within a view
    layer: HumanLabel
    axis: Literal["x", "y"]
    const: int                          # 0.1 mm, on the axis normal to ``axis``
    along_min: int                      # 0.1 mm
    along_max: int                      # 0.1 mm

    @model_validator(mode="after")
    def _ordered(self):
        if self.along_min >= self.along_max:
            raise ValueError("as_measured_face_line_degenerate")
        return self


class AsMeasuredWallV1(_StrictModel):
    """One thickness-homogeneous wall band = its two face lines + its extent.

    ⭐ ``thickness`` is DERIVED (``face_hi - face_lo``) and stored anyway, so a
    consumer never has to re-derive it -- but it is stored as the INTEGER
    DIFFERENCE OF THE TWO STORED FACES, so "recompute it from the two faces and
    compare bit-for-bit" is a real check and not a re-run of a float formula.
    """
    id: StableId
    axis: Literal["x", "y"]             # along-wall (running) axis
    face_lo: int                        # 0.1 mm, normal axis
    face_hi: int                        # 0.1 mm, normal axis
    thickness: int                      # 0.1 mm == face_hi - face_lo
    along_min: int
    along_max: int
    #: handles of the face lines lying on ``face_lo`` / ``face_hi``.  A face can
    #: be drawn as several collinear fragments, hence lists.  ⛔ Empty is legal
    #: and MEANINGFUL (the band was evidenced by jamb caps whose face line was
    #: not collected) -- it is never papered over.
    face_line_ids_lo: list[DxfHandle] = Field(default_factory=list)
    face_line_ids_hi: list[DxfHandle] = Field(default_factory=list)
    cap_handles: list[DxfHandle] = Field(default_factory=list)

    @model_validator(mode="after")
    def _thickness_is_the_difference(self):
        if self.thickness != self.face_hi - self.face_lo:
            raise ValueError("as_measured_thickness_not_face_difference")
        if self.thickness <= 0:
            raise ValueError("as_measured_thickness_not_positive")
        return self


class AsMeasuredOpeningV1(_StrictModel):
    """One opening, with the wall it sits in named by reference."""
    id: DxfHandle
    block_name: HumanLabel
    kind: Literal["window", "door"]
    axis: Literal["x", "y"]             # along-wall axis
    along_min: int
    along_max: int
    cross_lo: int                       # normal-axis interval, 0.1 mm
    cross_hi: int
    #: ⛔ ``None`` is a stated fact, not an omission: the matching wall band was
    #: absent or ambiguous, and ``converter_readouts.unresolved_opening_carriers``
    #: says which.
    carrier_wall_id: StableId | None = None
    jamb_handles: list[DxfHandle] = Field(default_factory=list)
    classification: Literal["exterior", "interior_excluded"] = "exterior"

    @model_validator(mode="after")
    def _ordered(self):
        if self.along_min > self.along_max or self.cross_lo > self.cross_hi:
            raise ValueError("as_measured_opening_interval_unordered")
        return self


class AsMeasuredRingV1(_StrictModel):
    """One ring of the measured footprint, in 0.1 mm integers."""
    polygon_index: StrictNonNegativeInt
    kind: Literal["exterior", "interior"]
    points: list[list[int]] = Field(min_length=4)

    @model_validator(mode="after")
    def _pairs(self):
        if any(len(p) != 2 for p in self.points):
            raise ValueError("as_measured_ring_point_not_a_pair")
        return self


class AsMeasuredFootprintV1(_StrictModel):
    geom_type: HumanLabel
    is_empty: bool
    rings: list[AsMeasuredRingV1] = Field(default_factory=list)


class AsMeasuredNonOrthogonalLineV1(_StrictModel):
    """A collected stroke that is neither horizontal nor vertical.

    ⭐ It exists (measured: 1 in as-received ``plan-F1``; F-129) and it cannot be
    a constant-coordinate face line.  ⛔ So it is NAMED here rather than dropped:
    "the record has no such wall" and "the record silently refused this wall"
    must not look the same ([[absence-conflates-causes-in-observables]]).
    """
    id: DxfHandle
    layer: HumanLabel
    p0: list[int] = Field(min_length=2, max_length=2)   # 0.1 mm world
    p1: list[int] = Field(min_length=2, max_length=2)


class AsMeasuredConverterReadoutsV1(_StrictModel):
    """The converter's OWN verdicts, carried VERBATIM.

    ⛔ Not one geometric value in here is recomputed.  2026-08-29's lesson was
    that the converter had already produced these and the consumer threw them
    away; the fix is transport, ⛔ not a second opinion.
    """
    dangles: StrictNonNegativeInt
    cuts: StrictNonNegativeInt
    invalid: StrictNonNegativeInt
    degenerate_line_count: StrictNonNegativeInt
    #: identity partners for the face-line ledger (see the document validator)
    wall_lines_total: StrictNonNegativeInt
    degenerate_in_wall_lines: StrictNonNegativeInt
    all_wall_handles: list[DxfHandle] = Field(default_factory=list)
    consumed_wall_handles: list[DxfHandle] = Field(default_factory=list)
    non_orthogonal_lines: list[AsMeasuredNonOrthogonalLineV1] = Field(default_factory=list)
    unresolved_opening_carriers: list[JsonDict] = Field(default_factory=list)
    walls_missing_a_face_line: list[StableId] = Field(default_factory=list)
    #: ⭐ the ONLY subtree in the whole document allowed to contain floats: these
    #: are the converter's own records in the converter's own frames.
    diagnostics: list[JsonDict] = Field(default_factory=list)
    gates: list[JsonDict] = Field(default_factory=list)


class AsMeasuredViewV1(_StrictModel):
    view_id: StableId
    floor_id: StableId
    face_lines: list[AsMeasuredFaceLineV1] = Field(default_factory=list)
    walls: list[AsMeasuredWallV1] = Field(default_factory=list)
    openings: list[AsMeasuredOpeningV1] = Field(default_factory=list)
    footprint: AsMeasuredFootprintV1
    converter_readouts: AsMeasuredConverterReadoutsV1

    @model_validator(mode="after")
    def _ledger_identity(self):
        """⛔ Every collected stroke is accounted for in exactly one bucket.

        This is the "consumption ledger" shape, not a range check: an
        unforeseen stroke stops being a silent omission and becomes a named
        red ([[declare-the-dialect-plus-consumption-ledger]]).
        """
        r = self.converter_readouts
        total = (len(self.face_lines) + len(r.non_orthogonal_lines)
                 + r.degenerate_in_wall_lines)
        if total != r.wall_lines_total:
            raise ValueError(
                f"as_measured_wall_line_ledger_broken: "
                f"{r.wall_lines_total} collected != {len(self.face_lines)} face_lines "
                f"+ {len(r.non_orthogonal_lines)} non_orthogonal "
                f"+ {r.degenerate_in_wall_lines} degenerate")
        ids = [f.id for f in self.face_lines]
        if len(ids) != len(set(ids)):
            raise ValueError("as_measured_face_line_id_not_unique")
        known = set(ids)
        for wall in self.walls:
            for ref in (*wall.face_line_ids_lo, *wall.face_line_ids_hi):
                if ref not in known:
                    raise ValueError(f"as_measured_dangling_face_line_ref:{ref}")
        wall_ids = {w.id for w in self.walls}
        for opening in self.openings:
            if opening.carrier_wall_id is not None and opening.carrier_wall_id not in wall_ids:
                raise ValueError(
                    f"as_measured_dangling_carrier_ref:{opening.carrier_wall_id}")
        return self


class AsMeasuredV1(_StrictModel):
    """The facts-layer document for one drawing.  ⛔ Never edited after writing.

    Trust root (ledger §七): the source DXF hash + the request hash.  ⛔ The
    converter IMPLEMENTATION fingerprint is sol's B1 and is NOT solved here --
    stating that plainly is the point; a field holding a value nobody signed
    would read as an attestation.
    """
    schema_version: Literal[1] = 1
    case: StableId
    #: ⭐ names the drawing this was measured off -- for sm25 that is the
    #: AS-RECEIVED file, not the signed one (ledger §十 / guide §十.3).
    source_dxf_label: HumanLabel
    source_dxf_sha256: Hex64
    request_sha256: Hex64
    coordinate_unit: Literal["0.1mm"] = "0.1mm"
    units_per_metre: Literal[10000] = 10000
    #: ⛔ Stated absence, not a missing field: B1 is ②-1b.
    converter_implementation_fingerprint: None = None
    views: list[AsMeasuredViewV1] = Field(min_length=1)

    @model_validator(mode="after")
    def _views_unique_and_sorted(self):
        ids = [v.view_id for v in self.views]
        if ids != sorted(ids):
            raise ValueError("as_measured_views_not_sorted")
        if len(ids) != len(set(ids)):
            raise ValueError("as_measured_view_id_not_unique")
        return self


# --------------------------------------------------------------------------- #
# canonical bytes -- the object the reproducibility gate hashes
# --------------------------------------------------------------------------- #
def canonical_bytes(document: AsMeasuredV1) -> bytes:
    """⭐ ONE canonical serialisation, mirroring ``compute_request_sha256``.

    ``sort_keys`` removes any dependence on field insertion order; the lists
    below were already put in a total order by the builder, because a *sorted
    dump of an unsorted list* is still unsorted.
    """
    payload = document.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"


def content_sha256(document: AsMeasuredV1) -> str:
    return hashlib.sha256(canonical_bytes(document)).hexdigest()


# --------------------------------------------------------------------------- #
# R1 -- the as-received request is a PURE SOURCE SWAP of the signed one
# --------------------------------------------------------------------------- #
#: The only keys allowed to differ between ``request.json`` (signed, points at
#: the retouched drawing) and ``request_as_measured.json`` (points at the
#: as-received drawing).  ⭐ Each one differs *because the source file differs*:
#:   source_dxf_label / source_dxf_sha256  -- which file
#:   normalized_source_id                  -- the id of what normalising THAT file yields
#:   request_sha256                        -- the signature over the above
REQUEST_AS_MEASURED_ALLOWED_DELTA = ("source_dxf_label", "source_dxf_sha256",
                                     "normalized_source_id", "request_sha256")


#: Suffix appended to ``normalized_source_id``.  Normalising a DIFFERENT source
#: file yields a DIFFERENT normalised artefact, so it needs a different id;
#: ⛔ sharing the signed id would make two distinct artefacts collide.
AS_RECEIVED_ID_SUFFIX = ".as-received"


def request_file_bytes(raw: dict) -> bytes:
    """The repo's own request-file formatting, recovered rather than invented.

    ⭐ VERIFIED, not assumed: ``json.loads`` of the shipped signed
    ``request.json`` re-dumped through this function is byte-identical to the
    file on disk (25909 == 25909).  That is what lets the derived request be
    checked with ``==`` on bytes instead of "looks equivalent", and it is why
    key order is PRESERVED rather than sorted -- the derived file then diffs
    against the signed one in exactly the four places it is allowed to differ.
    """
    return (json.dumps(raw, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def derive_as_measured_request(signed_request: Path, as_received_dxf: Path) -> bytes:
    """⭐ The as-received request is DERIVED, ⛔ never authored.

    R1 asked for a request that lets the converter run on the as-received
    drawing ⛔ without changing a single byte of the signed one.  Two roads were
    open; this is road 甲 (a second file), with road 甲's own risk -- two request
    files drifting apart, which is F-130's shape -- closed structurally instead
    of by discipline:

      the second file is not maintained, it is COMPUTED from the first, and
      ``test_as_measured_facts_layer.py`` recomputes it and compares BYTES.

    ⛔ Road 乙 (one request declaring two sources) was rejected for a concrete
    reason, not a preference: every extra key lands in ``model_dump`` and
    therefore in ``compute_request_sha256``, so it would either break all three
    signed hashes or need yet another entry in the
    ``REQUEST_VERSIONS_WITHOUT_SPACE_BINDING``-style strip list -- i.e. a second
    field that the signatures deliberately do not cover, in the trust root, to
    solve a problem a separate file solves with no signature surface at all.
    """
    raw = json.loads(Path(signed_request).read_text(encoding="utf-8"))
    as_received_dxf = Path(as_received_dxf)
    raw["source_dxf_label"] = as_received_dxf.name
    raw["source_dxf_sha256"] = hashlib.sha256(as_received_dxf.read_bytes()).hexdigest()
    raw["normalized_source_id"] = raw["normalized_source_id"] + AS_RECEIVED_ID_SUFFIX
    raw["request_sha256"] = "0" * 64
    raw["request_sha256"] = compute_request_sha256(
        TarchConversionRequestV1.model_validate(raw))
    return request_file_bytes(raw)


def assert_request_is_pure_source_swap(signed_request: Path,
                                       as_measured_request: Path) -> dict[str, tuple[Any, Any]]:
    """⛔ Two request files must not be able to drift apart (F-130's shape).

    Adding a second request is the cheap way to run the converter on the
    as-received drawing WITHOUT touching a signed file's bytes.  Its cost is
    that the two can then be edited independently and quietly disagree about
    clip boxes, selectors, dialect rules or the affine -- at which point
    "measured off the original drawing" and "the answer" stop being comparable
    and nothing says so.

    ⭐ So the second file is not a second opinion: it is the first file with a
    NAMED, ENUMERATED delta, and this function is the gate that keeps it that
    way.  Returns ``{key: (signed_value, as_measured_value)}`` for the delta.
    """
    signed = json.loads(Path(signed_request).read_text(encoding="utf-8"))
    other = json.loads(Path(as_measured_request).read_text(encoding="utf-8"))
    if set(signed) != set(other):
        raise ValueError(
            "as_measured_request_key_set_differs: "
            f"only_signed={sorted(set(signed) - set(other))} "
            f"only_as_measured={sorted(set(other) - set(signed))}")
    delta: dict[str, tuple[Any, Any]] = {}
    disagreements = []
    for key in sorted(signed):
        if signed[key] == other[key]:
            continue
        if key in REQUEST_AS_MEASURED_ALLOWED_DELTA:
            delta[key] = (signed[key], other[key])
        else:
            disagreements.append(key)
    if disagreements:
        raise ValueError(f"as_measured_request_drifted_on:{sorted(disagreements)}")
    missing = [k for k in REQUEST_AS_MEASURED_ALLOWED_DELTA if k not in delta]
    if missing:
        raise ValueError(
            "as_measured_request_is_not_a_source_swap: these keys were expected "
            f"to differ and do not: {missing}")
    return delta


# --------------------------------------------------------------------------- #
# builder
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# ordering seams -- ⭐ the ONLY thing standing between this layer and the
# string-hash seed, so each one is a named, patchable object rather than an
# inline ``.sort(key=lambda ...)``.
#
# ⛔ Not a stylistic choice: a lock that says "reversing the input changed
# nothing" cannot tell a builder that SORTS from a builder that IGNORES its
# input.  Neutering a named key to a constant makes the sort a no-op (Python's
# sort is stable) and the same lock then goes red -- which is what proves the
# sort, and not luck, is holding the reproducibility gate up
# ([[gate-with-only-negative-assertions-is-unobservable]]).
# --------------------------------------------------------------------------- #
def _face_line_sort_key(face: "AsMeasuredFaceLineV1"):
    return (face.axis, face.const, face.along_min, face.along_max, face.id)


def _wall_sort_key(wall: "AsMeasuredWallV1"):
    return (wall.axis, wall.face_lo, wall.face_hi, wall.along_min, wall.along_max, wall.id)


def _opening_sort_key(opening: "AsMeasuredOpeningV1"):
    return (opening.axis, opening.cross_lo, opening.cross_hi,
            opening.along_min, opening.along_max, opening.id)


def _sorted_handles(values) -> list[str]:
    """Total order for every handle collection.

    ⭐ This is the one that the seed actually attacks: ``all_wall_handles`` and
    ``consumed_wall_handles`` are ``set[str]``, and ``str`` is the type whose
    hash Python randomises per process.  ⛔ Iterating them directly would make
    the document's bytes a function of ``PYTHONHASHSEED``.
    """
    return sorted(values)


def _face_line_records(geo: P1PlanViewGeometry, sx: float, tx: float,
                       sy: float, ty: float) -> tuple[list[AsMeasuredFaceLineV1],
                                                      list[AsMeasuredNonOrthogonalLineV1],
                                                      int]:
    faces: list[AsMeasuredFaceLineV1] = []
    skew: list[AsMeasuredNonOrthogonalLineV1] = []
    degenerate = 0
    for handle, x0, y0, x1, y1 in geo.wall_lines:
        layer = geo.wall_line_layers.get(handle, "")
        wx0, wx1 = to_units(sx * x0 + tx), to_units(sx * x1 + tx)
        wy0, wy1 = to_units(sy * y0 + ty), to_units(sy * y1 + ty)
        if x0 != x1 and y0 != y1:
            skew.append(AsMeasuredNonOrthogonalLineV1(
                id=handle, layer=layer, p0=[wx0, wy0], p1=[wx1, wy1]))
            continue
        if x0 == x1 and y0 == y1:
            degenerate += 1
            continue
        if x0 == x1:                       # runs along y, constant x
            faces.append(AsMeasuredFaceLineV1(
                id=handle, layer=layer, axis="y", const=wx0,
                along_min=min(wy0, wy1), along_max=max(wy0, wy1)))
        else:                              # runs along x, constant y
            faces.append(AsMeasuredFaceLineV1(
                id=handle, layer=layer, axis="x", const=wy0,
                along_min=min(wx0, wx1), along_max=max(wx0, wx1)))
    faces.sort(key=_face_line_sort_key)
    skew.sort(key=lambda s: (s.p0, s.p1, s.id))
    return faces, skew, degenerate


def _wall_records(geo: P1PlanViewGeometry, faces: list[AsMeasuredFaceLineV1],
                  sx: float, tx: float, sy: float,
                  ty: float) -> tuple[list[AsMeasuredWallV1], list[str]]:
    """Bands -> walls, with each band's two faces named by handle.

    ⭐ The reference is resolved by matching the band's own face coordinate
    against the face lines' constant coordinate IN THE STORED UNIT -- i.e. the
    two are compared after both have gone through ``to_units``.  ⛔ Comparing
    floats here would make the reference depend on the 12th decimal place.
    """
    by_const: dict[tuple[str, int], list[str]] = {}
    for face in faces:
        by_const.setdefault((face.axis, face.const), []).append(face.id)
    walls: list[AsMeasuredWallV1] = []
    unresolved: list[str] = []
    for band in geo.wall_bands:
        if band.axis == "x":               # runs along x, faces are y coords
            lo, hi = to_units(sy * band.face_lo_mm + ty), to_units(sy * band.face_hi_mm + ty)
            amin = to_units(sx * band.along_min_mm + tx)
            amax = to_units(sx * band.along_max_mm + tx)
            face_axis = "x"                # the FACE LINES run along x
        else:                              # runs along y, faces are x coords
            lo, hi = to_units(sx * band.face_lo_mm + tx), to_units(sx * band.face_hi_mm + tx)
            amin = to_units(sy * band.along_min_mm + ty)
            amax = to_units(sy * band.along_max_mm + ty)
            face_axis = "y"
        lo, hi = (lo, hi) if lo <= hi else (hi, lo)
        amin, amax = (amin, amax) if amin <= amax else (amax, amin)
        wall_id = f"w_{band.axis}_{lo}_{hi}"
        ids_lo = sorted(by_const.get((face_axis, lo), []))
        ids_hi = sorted(by_const.get((face_axis, hi), []))
        if not ids_lo or not ids_hi:
            unresolved.append(wall_id)
        walls.append(AsMeasuredWallV1(
            id=wall_id, axis=band.axis, face_lo=lo, face_hi=hi, thickness=hi - lo,
            along_min=amin, along_max=amax,
            face_line_ids_lo=ids_lo, face_line_ids_hi=ids_hi,
            cap_handles=_sorted_handles(set(band.cap_handles))))
    walls.sort(key=_wall_sort_key)
    return walls, _sorted_handles(set(unresolved))


def _opening_records(geo: P1PlanViewGeometry, walls: list[AsMeasuredWallV1],
                     sx: float, tx: float, sy: float,
                     ty: float) -> tuple[list[AsMeasuredOpeningV1], list[dict]]:
    by_face: dict[tuple[str, int, int], list[AsMeasuredWallV1]] = {}
    for wall in walls:
        by_face.setdefault((wall.axis, wall.face_lo, wall.face_hi), []).append(wall)
    records: list[AsMeasuredOpeningV1] = []
    unresolved: list[dict] = []
    for op in geo.openings:
        x0, y0, x1, y1 = op.rect_dxf_mm
        wx = sorted((to_units(sx * x0 + tx), to_units(sx * x1 + tx)))
        wy = sorted((to_units(sy * y0 + ty), to_units(sy * y1 + ty)))
        c0, c1 = op.cross_section_mm
        if op.axis == "x":
            along_min, along_max = wx
            cross = sorted((to_units(sy * c0 + ty), to_units(sy * c1 + ty)))
        else:
            along_min, along_max = wy
            cross = sorted((to_units(sx * c0 + tx), to_units(sx * c1 + tx)))
        candidates = [w for w in by_face.get((op.axis, cross[0], cross[1]), [])
                      if not (along_max < w.along_min or along_min > w.along_max)]
        carrier: str | None = None
        if len(candidates) == 1:
            carrier = candidates[0].id
        else:
            unresolved.append({"opening_id": op.handle, "axis": op.axis,
                               "cross_lo": cross[0], "cross_hi": cross[1],
                               "candidate_wall_ids": _sorted_handles(w.id for w in candidates),
                               "reason": "no_band" if not candidates else "ambiguous"})
        records.append(AsMeasuredOpeningV1(
            id=op.handle, block_name=op.block_name, kind=op.kind, axis=op.axis,
            along_min=along_min, along_max=along_max,
            cross_lo=cross[0], cross_hi=cross[1], carrier_wall_id=carrier,
            jamb_handles=_sorted_handles(set(op.jamb_handles)),
            classification=op.classification))
    records.sort(key=_opening_sort_key)
    unresolved.sort(key=lambda u: u["opening_id"])
    return records, unresolved


def _footprint_record(geo: P1PlanViewGeometry, sx: float, tx: float,
                      sy: float, ty: float) -> AsMeasuredFootprintV1:
    poly = geo.footprint_polygon
    rings: list[AsMeasuredRingV1] = []
    if poly is not None and not poly.is_empty:
        parts = list(getattr(poly, "geoms", [poly]))
        for index, part in enumerate(parts):
            exterior = getattr(part, "exterior", None)
            if exterior is None:
                continue
            rings.append(AsMeasuredRingV1(
                polygon_index=index, kind="exterior",
                points=[[to_units(sx * x + tx), to_units(sy * y + ty)]
                        for x, y in exterior.coords]))
            for hole in part.interiors:
                rings.append(AsMeasuredRingV1(
                    polygon_index=index, kind="interior",
                    points=[[to_units(sx * x + tx), to_units(sy * y + ty)]
                            for x, y in hole.coords]))
    return AsMeasuredFootprintV1(
        geom_type=str(poly.geom_type) if poly is not None else "None",
        is_empty=bool(poly is None or poly.is_empty), rings=rings)


def _readout_records(geo: P1PlanViewGeometry) -> tuple[list[dict], list[dict]]:
    """Diagnostics + gates, VERBATIM.  ⛔ Nothing here is recomputed or filtered.

    ⭐ Not filtered by severity either: F-B (2026-08-29) measured that dropping
    BLOCK codes on a *successful* path passed the entire suite, because the only
    fixture with that combination was never inspected.
    """
    diagnostics = [{
        "code": str(getattr(d.code, "value", d.code)),
        "severity": str(getattr(d.severity, "value", d.severity)),
        "stage": str(getattr(d.stage, "value", d.stage)),
        "action_code": d.action_code,
        "handles": [str(h) for h in d.source_entity_handles],
        "points_dxf_mm": [[float(p[0]), float(p[1])] for p in d.source_points_dxf_mm],
        "context": d.context,
    } for d in geo.diagnostics]
    gates = [{"id": g.id, "name": g.name, "passed": bool(g.passed)} for g in geo.gates]
    return diagnostics, gates


#: ⭐ The identity gate, ⛔ NOT a new policy: this is GLM's "C-身份" criterion from
#: the F-126b cross-review, reused verbatim -- *no BLOCK whose stage is S0_input*.
#: S0 is the stage that asks "is the thing being measured the thing that was
#: declared"; a BLOCK there means the ruler never got to the drawing at all.
S0_INPUT_STAGE = "S0_input"


def _refuse_if_the_ruler_never_measured(geo: P1PlanViewGeometry) -> None:
    """⛔ Refuse loudly when the conversion never happened -- and ONLY then.

    ⚠️ The tempting rule ("refuse on any BLOCK") is wrong here and would defeat
    the whole layer.  MEASURED on the as-received sm25 drawing: it raises
    ``tarch_wall_nonorthogonal`` (BLOCK, S1) and ``tarch_wall_free_end`` (BLOCK,
    S4) precisely BECAUSE it is the un-retouched drawing -- those BLOCKs are the
    drawing's warts, which is the thing this layer exists to record.  Refusing
    on them would mean the facts layer can only ever measure drawings that have
    already been cleaned up, i.e. exactly the "bake the retouching into history"
    outcome the ledger §十 rejects.

    ⭐ So the split is the one the F-126b review already argued and accepted:
    a ``S0_input`` BLOCK (or no geometry at all) means *the measurement did not
    happen*; a content BLOCK means *the measurement happened and found
    something*.  The latter rides out in ``converter_readouts`` -- ⛔ not
    filtered, not summarised away (F-B).
    """
    s0_blocks = sorted({str(getattr(d.code, "value", d.code)) for d in geo.diagnostics
                        if str(getattr(d.severity, "value", d.severity)) == "BLOCK"
                        and str(getattr(d.stage, "value", d.stage)) == S0_INPUT_STAGE})
    if s0_blocks:
        raise AsMeasuredUnavailable(
            "upstream_identity_block", view_id=geo.view_id, blocking_codes=s0_blocks,
            detail="an S0_input BLOCK means the converter never measured this "
                   "drawing; recording that as a facts layer would store an "
                   "absence as a measurement")
    if not geo.wall_lines:
        raise AsMeasuredUnavailable(
            "no_geometry", view_id=geo.view_id,
            detail="the conversion ran without an S0 block and still collected "
                   "zero wall lines; that is a different failure from a refused "
                   "input and must not share its exit")


def build_view(geo: P1PlanViewGeometry, affine: Affine2D) -> AsMeasuredViewV1:
    """⭐ Pure: P1 geometry in, facts document out.  ⛔ Reads no file."""
    _refuse_if_the_ruler_never_measured(geo)
    sx, tx, sy, ty = _axis_aligned(affine, geo.view_id)
    faces, skew, degenerate = _face_line_records(geo, sx, tx, sy, ty)
    walls, faceless = _wall_records(geo, faces, sx, tx, sy, ty)
    openings, unresolved = _opening_records(geo, walls, sx, tx, sy, ty)
    diagnostics, gates = _readout_records(geo)
    return AsMeasuredViewV1(
        view_id=geo.view_id, floor_id=geo.floor_id,
        face_lines=faces, walls=walls, openings=openings,
        footprint=_footprint_record(geo, sx, tx, sy, ty),
        converter_readouts=AsMeasuredConverterReadoutsV1(
            dangles=geo.dangles, cuts=geo.cuts, invalid=geo.invalid,
            degenerate_line_count=geo.degenerate_line_count,
            wall_lines_total=len(geo.wall_lines),
            degenerate_in_wall_lines=degenerate,
            all_wall_handles=_sorted_handles(geo.all_wall_handles),
            consumed_wall_handles=_sorted_handles(geo.consumed_wall_handles),
            non_orthogonal_lines=skew,
            unresolved_opening_carriers=unresolved,
            walls_missing_a_face_line=faceless,
            diagnostics=diagnostics, gates=gates))


def build_as_measured(dxf: Path, request_path: Path, *,
                      view_ids: list[str] | None = None) -> AsMeasuredV1:
    """Measure ``dxf`` under ``request_path`` and return the facts document.

    ⛔ The DXF is staged into a temp dir before the converter sees it: answer
    roots are read-only inputs and ``run_p1_plan_view`` enforces that
    structurally.  ⛔ Nothing is written to disk by this function.
    """
    dxf = Path(dxf)
    request = TarchConversionRequestV1.model_validate_json(
        Path(request_path).read_text(encoding="utf-8"))
    wanted = sorted(view_ids) if view_ids else sorted(v.id for v in request.plan_views)
    tooling = load_gt_tooling_config(GT_CFG, VG_CFG)
    views: list[AsMeasuredViewV1] = []
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / dxf.name
        shutil.copy2(dxf, staged)
        for view_id in wanted:
            view = next(v for v in request.plan_views if v.id == view_id)
            geo = run_p1_plan_view(staged, request, view, tooling)
            views.append(build_view(geo, view.world_from_source_m))
    return AsMeasuredV1(
        case=request.case,
        source_dxf_label=dxf.name,
        source_dxf_sha256=hashlib.sha256(dxf.read_bytes()).hexdigest(),
        request_sha256=compute_request_sha256(request),
        views=views)


__all__ = [
    "UNITS_PER_METRE", "UNIT_LABEL", "REQUEST_AS_MEASURED_ALLOWED_DELTA",
    "AsMeasuredUnavailable", "AsMeasuredV1", "AsMeasuredViewV1",
    "AsMeasuredFaceLineV1", "AsMeasuredWallV1", "AsMeasuredOpeningV1",
    "AsMeasuredRingV1", "AsMeasuredFootprintV1",
    "AsMeasuredNonOrthogonalLineV1", "AsMeasuredConverterReadoutsV1",
    "assert_request_is_pure_source_swap", "derive_as_measured_request",
    "request_file_bytes", "AS_RECEIVED_ID_SUFFIX",
    "build_as_measured", "build_view",
    "S0_INPUT_STAGE",
    "canonical_bytes", "content_sha256", "to_units",
]
