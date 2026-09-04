"""B2: multi-floor assembly — derive per-storey z from the frozen floor-level
ladder (B3 evidence) and stack single-floor projections into one
``CorrectedGeometryV3`` with ``floors[]`` of length N.

⭐ The whole point of this module (dispatch 2026-09-03ai / reworks 2026-09-04a
/ 2026-09-04g): the storey elevations are DERIVED from frozen reading bytes,
⛔ never hand-filled.

Rework 2 (2026-09-04g) — "a hand-filled z assembles" must be IMPOSSIBLE AT THE
TYPE LAYER, not merely discouraged
--------------------------------------------------------------------------
The two earlier reworks changed only the SURFACE (drop the z keyword; then make
the carrier private + z a read-only property).  Both times the reviewer walked
around it with PUBLIC API: keep two honest claims' ``z_ref``, ``model_copy`` the
``z_m`` to 12.34, and call the two public helpers ``derive_floor_ladder`` +
``assemble_multifloor_geometry`` — which validated nothing — to mint a private
level for them.  The defect was never "the class was public"; it was that a
public helper re-obtained assembly capability from DETACHED, forgeable claims.

The fix is dispatch §〇③ exit (a): the assembly boundary consumes ONLY a
carrier whose type PROVES it passed the frozen-byte gate, and that carrier
cannot be minted except by passing through the gate:

  * :class:`_ValidatedFloorLadder` is the sole input to
    :func:`assemble_multifloor_geometry`.  Its only minter is
    :func:`derive_floor_ladder`, whose FIRST act is to run B3's
    ``validate_evidence_bundle`` on the SEALED carrier
    (``CorrectionEvidenceBundleArtifactV1`` = bundle + frozen bytes).  A claim
    whose ``z_m`` drifted from the frozen byte its ``z_ref`` names is a named
    ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` red BEFORE any level exists.
  * ``derive_floor_ladder`` NO LONGER accepts a bare
    ``Sequence[FloorLevelClaimV1]`` — the exact thing the reviewer
    ``model_copy``-mutated.  Detached claims cannot reach the derivation at
    all; the only door is the sealed, byte-gated bundle.
  * both ``_ValidatedFloorLadder`` and the single-view carrier
    :class:`_ProjectionStorey` require the module-private :data:`_LADDER_SEAL`
    at construction.  The seal is never exported, never returned, never stored
    on an instance — so no PUBLIC-API composition can forge either carrier.
    "Passed the frozen-byte gate" is thus a property of the TYPE, ⛔ not of some
    call's history.

⭐ Why is "hand-fill z then assemble" now UN-CONSTRUCTIBLE?  Because the only
value the assembly boundary accepts (a ``_ValidatedFloorLadder``) can only be
obtained from :func:`derive_floor_ladder`, which runs the byte gate; and the
only way to get z=12.34 past that gate is a frozen source that GENUINELY carries
12.34 at the byte the ``z_ref`` names — i.e. real evidence, not a hand-fill.
There is no public-API path that yields the carrier without the gate.

The production entry ``pipeline.run_multifloor_correction`` inherits all of
this: it hands its sealed elevation carrier to ``derive_floor_ladder`` and its
per-storey ``_ProjectionStorey`` tokens to ``run_correction`` — which itself no
longer takes a bare z (it consumes only a sealed ``_ProjectionStorey``), so the
OLD hand-fill production face is gone too.

Layering: this module is PURE — it depends only on the evidence contract, the
correction schema, and the geometry validator.  It never imports ``pipeline``.

⛔ NOT this module's job (dispatch §四): opening synthesis (B4), touching the
projection bridge's geometry algorithm, relaxing the z-stack continuity check,
or reading gt.  It also does not specialise to sm25 — a specific storey count
or storey height is a reading, not a theorem: the storey count is COUNTED from
the data and each storey height is COMPUTED from it (⛔ no sm25 elevation
constant is written into this module — the acceptance greps for exactly that).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.agent.correction.evidence_contract import (
    MIN_FLOOR_LEVELS,
    ArtifactPointerV1,
    CorrectionEvidenceBundleArtifactV1,
    FloorLevelClaimV1,
    validate_evidence_bundle,
)
from src.agent.correction.geometry_validator import check_zstack
from src.agent.correction.schema import CorrectedGeometryV3, FloorV3


class MultiFloorAssemblyError(RuntimeError):
    """A named, LOUD refusal from the multi-floor assembly (dispatch T4).

    Mirrors the projection bridge's ``ProjectionBridgeError`` shape: a code
    token plus a machine-readable detail dict, so a bad input is a counted,
    diagnosable red — ⛔ never a silent shrug or a fabricated floor."""

    def __init__(self, code: str, detail: dict | None = None):
        self.code = code
        self.detail = detail or {}
        super().__init__(f"{code}: {self.detail}" if self.detail else code)


# ── the seal: the ONLY authority that lets a validated carrier exist ───────── #
class _LadderSeal:
    """A module-private capability token (rework 2026-09-04g, dispatch §〇③(a)).

    It is never in ``__all__``, never returned by any function, and never
    stored as an instance attribute — so no PUBLIC-API composition can obtain
    it.  It is the single thing that authorises a :class:`_ValidatedFloorLadder`
    or a :class:`_ProjectionStorey` to be constructed, which is what makes
    "passed the frozen-byte gate" a property of the TYPE rather than of some
    call's history.  (⚠️ It is not a claim of true unreachability — Python has
    no private state; it is a claim that the reviewer's discipline of composing
    only PUBLIC API cannot reach it, which is exactly the bypass the two prior
    reworks fell to.)
    """

    __slots__ = ()


_LADDER_SEAL = _LadderSeal()


@dataclass(frozen=True)
class _DerivedFloorLevel:
    """One storey's z, DERIVED from a bounding pair of frozen floor-level
    claims (B2/T1) — ⛔ never hand-filled.

    ⭐ Type-level no-hand-fill (dispatch §二): this carrier holds the two
    bounding ``FloorLevelClaimV1`` (``lower`` = the rung this storey sits on,
    ``upper`` = the next rung up) and NOTHING a caller can set to a bare z.
    Every z-shaped attribute is a READ-ONLY property computed from those two
    claims.  There is no ``z_floor_m=`` / ``ceiling_height_m=`` constructor
    keyword.

    ⚠️ This level, on its OWN, is NOT the assembly-capable carrier: a caller
    can still ``model_copy`` a claim's ``z_m`` and forge one of these (the
    boundary test does exactly that).  What forging it buys is nothing — the
    assembly boundary (:func:`assemble_multifloor_geometry`) accepts only a
    SEALED :class:`_ValidatedFloorLadder`, and the single-view chain accepts
    only a SEALED :class:`_ProjectionStorey`; neither can be minted from a
    forged level.
    """

    floor_index: int
    lower: FloorLevelClaimV1
    upper: FloorLevelClaimV1

    @property
    def z_floor_m(self) -> float:
        return self.lower.z_m

    @property
    def ceiling_height_m(self) -> float:
        return self.upper.z_m - self.lower.z_m

    @property
    def z_floor_claim_id(self) -> str:
        return self.lower.structure_line_id

    @property
    def z_floor_ref(self) -> ArtifactPointerV1:
        return self.lower.z_ref

    @property
    def z_top_claim_id(self) -> str:
        return self.upper.structure_line_id

    @property
    def z_top_ref(self) -> ArtifactPointerV1:
        return self.upper.z_ref


class _ProjectionStorey:
    """One storey's byte-gated z for the SINGLE-VIEW evidence chain
    (``pipeline.run_correction(evidence_chain=True)``).

    ⭐ This is the migrated shape of the OLD ``evidence_chain_z_floor_m`` /
    ``evidence_chain_ceiling_height_m`` bare-float production face (dispatch
    §一#2).  It carries the same two numbers, but it is SEALED: constructing it
    requires the module-private :data:`_LADDER_SEAL`, and the only code that
    holds the seal is :meth:`_ValidatedFloorLadder.storeys`.  A caller of
    ``run_correction`` therefore cannot hand-fill a z — it can only pass a
    storey minted from a byte-gated :class:`_ValidatedFloorLadder`.

    ⛔ Not a dataclass: a frozen dataclass storing the seal would be
    re-mintable via ``dataclasses.replace(storey, z_floor_m=12.34)`` (which
    copies the seal forward).  A plain slotted class with a guarded ``__init__``
    and no stored seal closes that.
    """

    __slots__ = ("_z_floor_m", "_ceiling_height_m")

    def __init__(self, *, z_floor_m: float, ceiling_height_m: float, seal: _LadderSeal):
        if seal is not _LADDER_SEAL:
            raise MultiFloorAssemblyError(
                "UNSEALED_PROJECTION_STOREY",
                {
                    "reason": (
                        "a _ProjectionStorey may only be minted from a "
                        "byte-gated _ValidatedFloorLadder; there is no "
                        "hand-fill path (dispatch §一#2 / §〇③)"
                    )
                },
            )
        object.__setattr__(self, "_z_floor_m", float(z_floor_m))
        object.__setattr__(self, "_ceiling_height_m", float(ceiling_height_m))

    @property
    def z_floor_m(self) -> float:
        return self._z_floor_m

    @property
    def ceiling_height_m(self) -> float:
        return self._ceiling_height_m


class _ValidatedFloorLadder:
    """A storey ladder whose z's have PASSED the frozen-byte gate.

    ⭐ Type-level proof (dispatch §〇③(a)): the assembly boundary
    (:func:`assemble_multifloor_geometry`) accepts ONLY this type, and the ONLY
    minter is :func:`derive_floor_ladder`, which runs ``validate_evidence_
    bundle`` on the sealed carrier BEFORE constructing it.  Constructing one
    requires the module-private :data:`_LADDER_SEAL`, so a caller cannot forge a
    ladder with a hand-filled z: no public-API path yields a
    ``_ValidatedFloorLadder``, and detached / hand-mutated claims never reach
    the minter because its byte gate rejects them first.

    ⛔ Not a dataclass (same reason as :class:`_ProjectionStorey`): ``replace``
    would copy the seal forward and let injected levels ride in.
    """

    __slots__ = ("_levels",)

    def __init__(self, levels: Sequence[_DerivedFloorLevel], *, seal: _LadderSeal):
        if seal is not _LADDER_SEAL:
            raise MultiFloorAssemblyError(
                "UNSEALED_LADDER",
                {
                    "reason": (
                        "a _ValidatedFloorLadder may only be minted by "
                        "derive_floor_ladder AFTER validate_evidence_bundle; "
                        "the assembly boundary accepts nothing else "
                        "(dispatch §〇③(a))"
                    )
                },
            )
        object.__setattr__(self, "_levels", tuple(levels))

    @property
    def levels(self) -> tuple[_DerivedFloorLevel, ...]:
        return self._levels

    @property
    def storeys(self) -> tuple[_ProjectionStorey, ...]:
        """The per-storey SEALED z tokens for the single-view chain.  These
        are the ONLY legitimate ``run_correction`` z carriers, and they exist
        only because THIS ladder passed the byte gate."""
        return tuple(
            _ProjectionStorey(
                z_floor_m=level.z_floor_m,
                ceiling_height_m=level.ceiling_height_m,
                seal=_LADDER_SEAL,
            )
            for level in self._levels
        )


def _footprint_fingerprint(floor: FloorV3):
    """Byte-for-byte the schema's OWN common-footprint fingerprint
    (``schema.py:_v3_integrity``'s local ``fingerprint`` closure): the
    canonical vertex tuple, independent of start vertex and winding direction.

    ⭐ B-3 (dispatch §三, exit (a)): mirrored here so :func:`assemble_multifloor_
    geometry` can compare footprints EXPLICITLY *before* construction and raise
    its OWN named ``PER_FLOOR_FOOTPRINT_MISMATCH``.  Because that comparison is
    the authority for the footprint label, every OTHER model-level integrity
    fault at the construction site (an empty floor id, …) is left to surface as
    a RAW ``ValidationError`` — ⛔ never relabeled by a shared ``loc/type``
    structure (which prior rework used and the reviewer defeated with an empty
    floor id that has the identical ``loc == () / type == 'value_error'``
    shape).  Mirroring the producer's exact definition is deliberate
    ([[recompute-gate-must-mirror-producer-definition]])."""
    pts = [(float(x), float(y)) for x, y in floor.footprint.vertices]
    if pts[0] == pts[-1]:
        pts.pop()
    forward = min(tuple(pts[i:] + pts[:i]) for i in range(len(pts)))
    rev = list(reversed(pts))
    backward = min(tuple(rev[i:] + rev[:i]) for i in range(len(rev)))
    return min(forward, backward)


def _derive_levels(
    floor_level_claims: Sequence[FloorLevelClaimV1],
) -> tuple[_DerivedFloorLevel, ...]:
    """The PURE geometry of the ladder, on ALREADY-VALIDATED claims.

    ⚠️ ⛔ NOT a public minter and NOT the byte gate: it returns BARE levels,
    and the assembly boundary requires the SEALED ladder that only
    :func:`derive_floor_ladder` mints (after ``validate_evidence_bundle``).  It
    is factored out only so the degenerate / non-ascending geometry checks can
    be exercised directly; composing it never re-obtains assembly capability.

    The rule (the consumer-side mirror of B3's ``FLOOR_LEVEL_SELECTION_RULE``):
    sort the claimed rungs ascending; N distinct rungs give N-1 storeys; storey
    ``i`` sits on rung ``i`` and rises to rung ``i+1``.  Each z is a byte read
    from the frozen source, ⛔ never invented — the returned level's
    ``z_floor_ref`` / ``z_top_ref`` are the very ``z_ref`` pointers the two
    bounding claims carry.

    Loud, never silent (T4):
      * fewer than ``MIN_FLOOR_LEVELS`` rungs -> ``FLOOR_LADDER_DEGENERATE``;
      * two rungs at the same z (the ladder does not strictly ascend) -> which
        is also exactly the degenerate zero-height case -> ``FLOOR_LADDER_NOT_
        ASCENDING``.

    ⛔ Sorting is NOT silent repair of a genuinely non-monotone ladder: after
    the sort, any adjacent pair whose rise is <= 0 can only be a duplicate rung,
    reported by name rather than swallowed.
    """
    claims = sorted(floor_level_claims, key=lambda c: c.z_m)
    if len(claims) < MIN_FLOOR_LEVELS:
        raise MultiFloorAssemblyError(
            "FLOOR_LADDER_DEGENERATE",
            {"n_levels": len(claims), "min_levels": MIN_FLOOR_LEVELS},
        )
    levels: list[_DerivedFloorLevel] = []
    for index in range(len(claims) - 1):
        lower, upper = claims[index], claims[index + 1]
        rise = upper.z_m - lower.z_m
        if rise <= 0.0:
            raise MultiFloorAssemblyError(
                "FLOOR_LADDER_NOT_ASCENDING",
                {
                    "lower_id": lower.structure_line_id,
                    "upper_id": upper.structure_line_id,
                    "z_lower_m": lower.z_m,
                    "z_upper_m": upper.z_m,
                    "rise_m": rise,
                },
            )
        levels.append(
            _DerivedFloorLevel(floor_index=index, lower=lower, upper=upper)
        )
    return tuple(levels)


def derive_floor_ladder(
    elevation_evidence: CorrectionEvidenceBundleArtifactV1,
) -> _ValidatedFloorLadder:
    """B2/T1: turn B3's frozen floor-level ladder into a SEALED, byte-gated
    storey ladder — the sole assembly-capable carrier.

    ⭐ B-1 / B-2 (dispatch §〇③): the ONLY input is the SEALED carrier
    ``CorrectionEvidenceBundleArtifactV1`` (bundle + frozen bytes), ⛔ never a
    detached ``Sequence[FloorLevelClaimV1]`` (the exact thing the reviewer
    ``model_copy``-mutated in the last two reworks).  The FIRST thing this does
    is run B3's existing value↔byte gate ``validate_evidence_bundle`` on it, so
    a claim whose ``z_m`` drifted from the frozen byte its ``z_ref`` names is a
    named ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` red BEFORE any level exists.
    Only then are the levels derived and SEALED into a
    :class:`_ValidatedFloorLadder`.

    ⇒ There is no public-API path that hands the assembly boundary a ladder
    with a hand-filled z: the byte gate is the sole mint condition, and the only
    way past it is a frozen source that genuinely carries the z at the byte its
    ``z_ref`` names.
    """
    validate_evidence_bundle(elevation_evidence)
    levels = _derive_levels(elevation_evidence.bundle.floor_level_claims)
    return _ValidatedFloorLadder(levels, seal=_LADDER_SEAL)


def assemble_multifloor_geometry(
    ladder: _ValidatedFloorLadder,
    single_floor_geometries: Sequence[CorrectedGeometryV3],
) -> CorrectedGeometryV3:
    """B2/T2+T3: stack N single-floor projections into one ``floors[]``.

    ⭐ B-2 (dispatch §〇③(a)): the SOLE z carrier is ``ladder``, a SEALED
    :class:`_ValidatedFloorLadder` that only :func:`derive_floor_ladder` can
    mint (after the byte gate).  There is no z parameter, and no way to pass a
    hand-filled z: an object that is not a byte-gated ladder is refused by type
    here (``UNVALIDATED_LADDER``), before any floor is stacked.  The output
    floor's ``z_floor`` / ``ceiling_height`` are re-stamped from the derived
    rung, ⛔ never taken from whatever the incoming single-floor geometry
    happened to carry.  ``single_floor_geometries`` supplies only the XY, one
    per storey, ground-up (``ladder.levels[i]`` pairs with
    ``single_floor_geometries[i]``).

    Loud, never silent (T4):
      * a non-ladder ``ladder`` -> ``UNVALIDATED_LADDER``;
      * ``len(levels) != len(single_floor_geometries)``
        -> ``FLOOR_PLAN_COUNT_MISMATCH``;
      * a derived level with ``ceiling_height_m <= 0``
        -> ``NONPOSITIVE_CEILING_HEIGHT`` (a defensive boundary check: even a
        forged ``_DerivedFloorLevel`` sealed into a ladder is stopped here);
      * a single-floor geometry that does not carry exactly one floor
        -> ``EXPECTED_SINGLE_FLOOR_GEOMETRY``;
      * two storeys sharing a floor id -> ``DUPLICATE_FLOOR_ID``;
      * per-floor footprints that are not the same domain (setback / 退台)
        -> ``PER_FLOOR_FOOTPRINT_MISMATCH`` (invariant #6: assembly is
        common-footprint only — this simplification is the current 共底面盒子
        assumption, ⛔ not烤死-silent, and NOT B2's job to relax; see §四).

    ⭐ B-3 (dispatch §三, exit (a)): the footprint mismatch is decided by an
    EXPLICIT common-footprint pre-comparison (:func:`_footprint_fingerprint`,
    the schema's own definition) raised BEFORE the final ``CorrectedGeometryV3``
    construction.  Consequently the construction's ``ValidationError`` is
    surfaced RAW for every OTHER integrity fault — an empty floor id, etc. — and
    is ⛔ NEVER relabeled by a shared ``loc/type`` structure (which the reviewer
    defeated by making an empty floor id wear footprint's ``loc == () /
    type == 'value_error'`` shape).  The schema's own footprint check remains
    the authority and runs unchanged; this pre-comparison only lets B2 name the
    same verdict without stealing the identity of unrelated errors.

    Then the stacked floors MUST pass the EXISTING z-stack continuity check
    (``geometry_validator.check_zstack``, the same rule as
    ``pipeline.correction_draw_issues`` at pipeline.py:661): a break is
    ``Z_STACK_DISCONTINUITY``.  ⛔ The check is neither bypassed nor relaxed
    (T3) — it is called, and its "not ok" is raised.  (⚠️ By construction the
    stacked ladder is continuous; this guard therefore has teeth only against a
    future assembler that stamps z from some other source.  Its passing is a
    guardrail, ⛔ not an acceptance signal — see dispatch §三①.)
    """
    if not isinstance(ladder, _ValidatedFloorLadder):
        # ⭐ Type-layer refusal (B-2): the assembly boundary accepts ONLY the
        # sealed, byte-gated ladder.  A raw list of levels — forged or not — is
        # not a ladder and cannot enter here.
        raise MultiFloorAssemblyError(
            "UNVALIDATED_LADDER",
            {
                "got": type(ladder).__name__,
                "reason": (
                    "assembly consumes only a byte-gated _ValidatedFloorLadder "
                    "minted by derive_floor_ladder (dispatch §〇③(a))"
                ),
            },
        )
    levels = ladder.levels
    if len(levels) != len(single_floor_geometries):
        raise MultiFloorAssemblyError(
            "FLOOR_PLAN_COUNT_MISMATCH",
            {
                "n_storeys_from_ladder": len(levels),
                "n_plan_products": len(single_floor_geometries),
            },
        )

    floors: list[FloorV3] = []
    seen_ids: dict[str, int] = {}
    xs_lo: list[float] = []
    xs_hi: list[float] = []
    ys_lo: list[float] = []
    ys_hi: list[float] = []
    for level, geom in zip(levels, single_floor_geometries):
        if level.ceiling_height_m <= 0.0:
            raise MultiFloorAssemblyError(
                "NONPOSITIVE_CEILING_HEIGHT",
                {
                    "floor_index": level.floor_index,
                    "ceiling_height_m": level.ceiling_height_m,
                },
            )
        if len(geom.floors) != 1:
            raise MultiFloorAssemblyError(
                "EXPECTED_SINGLE_FLOOR_GEOMETRY",
                {"floor_index": level.floor_index, "n_floors": len(geom.floors)},
            )
        src = geom.floors[0]
        if src.id in seen_ids:
            raise MultiFloorAssemblyError(
                "DUPLICATE_FLOOR_ID",
                {
                    "floor_id": src.id,
                    "first_index": seen_ids[src.id],
                    "second_index": level.floor_index,
                },
            )
        seen_ids[src.id] = level.floor_index
        # ⭐ z is re-stamped from the DERIVED level — evidence is the single
        # source of truth for storey elevation; the incoming geometry's own
        # z_floor/ceiling_height are not trusted here.
        floors.append(
            src.model_copy(
                update={
                    "z_floor": float(level.z_floor_m),
                    "ceiling_height": float(level.ceiling_height_m),
                }
            )
        )
        xs_lo.append(float(geom.footprint_x[0]))
        xs_hi.append(float(geom.footprint_x[1]))
        ys_lo.append(float(geom.footprint_y[0]))
        ys_hi.append(float(geom.footprint_y[1]))

    # ⭐ B-3 exit (a): EXPLICIT common-footprint pre-comparison, BEFORE the
    # schema construction.  A genuine mismatch is named here; any OTHER
    # construction-time ValidationError is then left to surface RAW below.
    if len({_footprint_fingerprint(f) for f in floors}) > 1:
        raise MultiFloorAssemblyError(
            "PER_FLOOR_FOOTPRINT_MISMATCH",
            {
                "floor_ids": [f.id for f in floors],
                "reason": (
                    "assembly is common-footprint only (invariant #6); "
                    "per-floor different footprints (setback) are not B2's "
                    "job — see dispatch §四"
                ),
            },
        )

    # ⛔ No try/except relabel: the schema's ValidationError surfaces RAW for
    # every integrity fault (the footprint case is already named above).
    assembled = CorrectedGeometryV3(
        schema_version="3",
        footprint_x=[min(xs_lo), max(xs_hi)],
        footprint_y=[min(ys_lo), max(ys_hi)],
        floors=floors,
        windows=[],
        facade_segments=[],
    )

    zstack = check_zstack(assembled)
    if not zstack.ok:
        raise MultiFloorAssemblyError(
            "Z_STACK_DISCONTINUITY", dict(zstack.evidence or {})
        )
    return assembled


__all__ = [
    "MultiFloorAssemblyError",
    "assemble_multifloor_geometry",
    "derive_floor_ladder",
]
