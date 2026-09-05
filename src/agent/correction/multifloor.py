"""B2: multi-floor assembly — derive per-storey z from the frozen floor-level
ladder (B3 evidence) and stack single-floor projections into one
``CorrectedGeometryV3`` with ``floors[]`` of length N.

⭐ The whole point of this module (dispatch 2026-09-03ai / rework 2026-09-04a /
rework-2 2026-09-04g): the storey elevations are DERIVED from frozen reading
bytes, ⛔ never hand-filled.

Rework-3 (2026-09-04w) — round 3 fell to a forged CARRIER, not a forged claim
-----------------------------------------------------------------------------
Rounds 1-2 fixed the surface (z dropped from the entry signature, then the
claim paths gated), so the round-3 reviewer stopped forging claims and forged
the CARRIER instead: ``ValidatedFloorLadder((SimpleNamespace(z_floor_m=12.34,
...),))`` — a public dataclass constructor whose ``_levels`` element annotation
Python never enforces at runtime — after which ``assemble_multifloor_geometry``
read ``level.z_floor_m`` straight off whatever it found inside.  The docstring
said "The SEALED assembly carrier" while no seal existed ([[design-doc-
described-what-code-never-implemented]], [[gate-measures-right-but-carrier-
gets-swapped]]).  Two type-level facts are enforced now:

  * **The constructor is sealed** (dispatch §一(a)): ``__init__`` compares a
    token that exists ONLY inside the ``_seal_validated_ladder`` closure — not
    a module attribute, never returned, never stored on an instance.  Every
    construction attempt from outside (a direct call, ``dataclasses.replace``,
    a subclass constructor) is a named ``LADDER_MINT_SEAL_REQUIRED`` /
    ``LADDER_SEALED_NO_SUBCLASS`` red.  ⭐ Closure-held is strictly stronger
    than a module-global ``_SEAL``: an underscore global is still reachable as
    an attribute of the module, a closure cell of a factory that has returned
    is reachable only by introspection.

  * **The carrier stores NO z-bearing state** (dispatch §一(c) moved to the
    consumption boundary — the exit check, ⛔ not a narrower entrance): its only
    field is the sealed ``CorrectionEvidenceBundleArtifactV1``.  The per-storey
    levels are RE-DERIVED on every read — ``validate_evidence_bundle`` first,
    then ``_byte_z`` resolution — so there is no stored element to swap, and a
    shell forged with ``object.__new__`` (which no ``__init__`` can stop)
    still cannot move a z: whatever artifact it ends up carrying is GATED AT
    THE READ.  Assembly's z is therefore never a value read off instance
    state; it is always re-derived from frozen bytes that re-passed the gate
    in that very call.

Why "a hand-filled z assembles" is now un-CONSTRUCTIBLE, not merely refused:
the only z that reaches assembly is computed inside ``_levels_of`` from an
artifact that must re-pass ``validate_evidence_bundle`` at the moment of the
read.  Changing the assembled number requires supplying different frozen bytes
that still pass the gate — i.e. authoring a different frozen reading product,
which is the reading trust boundary the 2026-09-04p verdict adjudicated as out
of B2's scope.  (What no Python type layer can stop: runtime introspection that
reads this module's own closure cells or rebinds its globals — that is
equivalent to editing the code, and even then the z stays gated, because the
gate runs at consumption, ⛔ not at mint time only.)

Layering: this module depends only on the evidence contract, the correction
schema, and the geometry validator.  It never imports ``pipeline``.  The
model-driven orchestration that runs the evidence chain once per plan product
lives in ``pipeline.run_multifloor_correction`` (which imports THIS module, not
the other way round).

⛔ NOT this module's job (dispatch §四): opening synthesis (B4), touching the
projection bridge's geometry algorithm, relaxing the z-stack continuity check,
or reading gt.  It also does not specialise to sm25 — a specific storey count
or storey height is a reading, not a theorem: the storey count is COUNTED from
the data and each storey height is COMPUTED from it (⛔ no sm25 elevation
constant is written into this module — the acceptance greps for exactly that).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from src.agent.correction.evidence_contract import (
    ArtifactPointerV1,
    CorrectionEvidenceBundleArtifactV1,
    FloorLevelClaimV1,
    MIN_FLOOR_LEVELS,
    resolve_json_pointer,
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


def _byte_z(frozen_docs: dict[str, dict], ref: ArtifactPointerV1) -> float:
    """Resolve ONE z from the FROZEN BYTES via its ``z_ref`` json pointer.

    ⭐ This is the load-bearing "z is byte-derived" mechanism (B-2, dispatch
    §〇③(a)): the assembled z is always the byte the ref names, ⛔ never a value a
    caller set on a claim (``claim.z_m``) or baked onto a level.  A ``model_copy``
    on ``z_m`` — or a hand-forged level — therefore cannot move the z; only
    supplying different frozen bytes can, which is the reading trust boundary."""
    doc = frozen_docs.get(ref.input_id)
    if doc is None:
        raise MultiFloorAssemblyError(
            "FLOOR_LEVEL_SOURCE_UNKNOWN",
            {"input_id": ref.input_id, "pointer": ref.json_pointer},
        )
    try:
        value = resolve_json_pointer(doc, ref.json_pointer)
    except KeyError as exc:
        raise MultiFloorAssemblyError(
            "FLOOR_LEVEL_SOURCE_UNRESOLVED",
            {"input_id": ref.input_id, "pointer": ref.json_pointer,
             "because": str(exc)},
        ) from exc
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MultiFloorAssemblyError(
            "FLOOR_LEVEL_SOURCE_NOT_NUMERIC",
            {"input_id": ref.input_id, "pointer": ref.json_pointer,
             "got": type(value).__name__},
        )
    return float(value)


@dataclass(frozen=True, eq=False)
class _DerivedFloorLevel:
    """One storey's z, BYTE-RESOLVED from a bounding pair of gate-validated
    floor-level claims (B2/T1) — ⛔ never hand-filled.

    ⭐ Type-level no-hand-fill (B-2, dispatch §二 / §〇③): this carrier holds the
    two bounding ``FloorLevelClaimV1`` (``lower`` = the rung this storey sits on,
    ``upper`` = the next rung up) and the ``frozen_docs`` map its refs resolve
    into.  Every z-shaped attribute is a READ-ONLY property that DEREFERENCES the
    claim's ``z_ref`` INTO ``frozen_docs`` — it never reads ``claim.z_m`` and
    there is no settable z field:

      * ``z_floor_m`` is the byte named by ``lower.z_ref``;
      * ``ceiling_height_m`` is the rise ``upper-byte - lower-byte`` — a DERIVED
        difference whose BOTH operands are frozen bytes.

    There is no ``z_floor_m=`` / ``ceiling_height_m=`` constructor keyword, so the
    reviewer's ``DerivedFloorLevel(z_floor_m=12.34, ceiling_height_m=5.67)`` is a
    ``TypeError``.  And because z is byte-resolved, even a ``model_copy`` on a
    claim's ``z_m`` (the reviewer's round-2 bypass) has NO effect on the derived
    z — the byte the ref names is unchanged.  This class is PRIVATE; the only
    sanctioned minter is :func:`derive_floor_ladder`, which runs the frozen-byte
    gate first, and the sealed :class:`ValidatedFloorLadder` it returns is the
    only thing :func:`assemble_multifloor_geometry` accepts."""

    floor_index: int
    lower: FloorLevelClaimV1
    upper: FloorLevelClaimV1
    frozen_docs: dict

    @property
    def z_floor_m(self) -> float:
        return _byte_z(self.frozen_docs, self.lower.z_ref)

    @property
    def ceiling_height_m(self) -> float:
        return _byte_z(self.frozen_docs, self.upper.z_ref) - self.z_floor_m

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


# ── the seal (dispatch §一(a)) ──────────────────────────────────────────────── #
# ``_LADDER_SEAL`` exists ONLY inside this factory's closure: it is not a module
# attribute (⭐ unlike a ``_SEAL`` global, which stays reachable as ``m._SEAL``),
# it is never returned, and it is never stored on an instance.  The factory runs
# once at import and hands back the class plus a private minter that can present
# the token; module-external code has NO name that binds it.
def _seal_validated_ladder():
    _LADDER_SEAL = object()

    @dataclass(frozen=True, eq=False, init=False, repr=False)
    class ValidatedFloorLadder:
        """The SEALED assembly carrier (dispatch §一(a)+(c), rework-3).

        ⭐ CLAIM LEDGER — every claim below names the code that enforces it
        (rework-3 dispatch §二#3); a claim with no enforcing line gets deleted,
        ⛔ not narrated:

        1. "It cannot be populated from outside this module" — ``__init__``
           compares ``_seal`` against the closure-held ``_LADDER_SEAL``; any
           external construction attempt (direct call, ``dataclasses.replace``,
           a subclass's inherited constructor) raises the named
           ``LADDER_MINT_SEAL_REQUIRED``.  ``object.__new__`` can still yield an
           attribute-less shell — no ``__init__`` can stop that — which is why
           claim 3 exists.
        2. "It cannot be subclassed" — ``__init_subclass__`` raises the named
           ``LADDER_SEALED_NO_SUBCLASS`` at class-creation time, so an
           ``isinstance``-passing subclass with an overridden constructor
           cannot exist.
        3. "It stores NO z-bearing state, so there is nothing to swap" — its
           only field is ``_artifact``; ``__len__`` / ``__iter__`` /
           ``__getitem__`` all go through ``_levels_of_carrier``, which
           RE-DERIVES the levels (``validate_evidence_bundle`` first, then
           ``_byte_z`` resolution) on every read.  An ``object.__new__`` shell
           — or an honest carrier whose ``_artifact`` was swapped post-hoc —
           either assembles its artifact's GATED bytes or fails by name
           (``LADDER_CARRIER_CORRUPT`` / ``EvidenceContractError``); it can
           never assemble a value that was merely SET on an instance.
        4. "The only sanctioned minter gates first" — the closure-held
           ``_mint_sealed`` is module-private, and its only module-level caller
           is :func:`derive_floor_ladder`, whose first act is ``_levels_of``
           (the gate + derivation), so a bad artifact is a named red at the
           minter's door, ⛔ never inside assembly.
        """

        _artifact: CorrectionEvidenceBundleArtifactV1

        def __init__(self, _artifact=None, *, _seal=None):
            # ⭐ the parameter NAME matches the field name on purpose:
            # ``dataclasses.replace`` rebuilds init kwargs from FIELD names
            # (init=False on the decorator only suppresses GENERATING
            # ``__init__`` — the field's init flag stays True), so every
            # replace shape re-enters THIS seal check, ⛔ never a keyword
            # TypeError by accident.
            if _seal is not _LADDER_SEAL:
                raise MultiFloorAssemblyError(
                    "LADDER_MINT_SEAL_REQUIRED",
                    {
                        "got": type(self).__name__,
                        "reason": (
                            "ValidatedFloorLadder cannot be constructed "
                            "outside multifloor: it is minted only by "
                            "derive_floor_ladder, which runs the frozen-byte "
                            "gate first (dispatch §一(a))"
                        ),
                    },
                )
            if not isinstance(_artifact, CorrectionEvidenceBundleArtifactV1):
                raise MultiFloorAssemblyError(
                    "LADDER_MINT_REQUIRES_SEALED_ARTIFACT",
                    {
                        "got": (
                            type(_artifact).__name__
                            if _artifact is not None
                            else "None"
                        )
                    },
                )
            object.__setattr__(self, "_artifact", _artifact)

        def __init_subclass__(cls, **kwargs):
            raise MultiFloorAssemblyError(
                "LADDER_SEALED_NO_SUBCLASS",
                {
                    "subclass": cls.__name__,
                    "reason": (
                        "ValidatedFloorLadder is sealed; an isinstance-passing "
                        "subclass with an overridden constructor must not "
                        "exist (dispatch §一(a))"
                    ),
                },
            )

        def _levels_of_carrier(self) -> tuple[_DerivedFloorLevel, ...]:
            """The exit check (§一(c)): re-derive levels from the artifact AT
            THE READ — gate first, bytes only, ⛔ never instance-carried z."""
            artifact = getattr(self, "_artifact", None)
            if not isinstance(artifact, CorrectionEvidenceBundleArtifactV1):
                raise MultiFloorAssemblyError(
                    "LADDER_CARRIER_CORRUPT",
                    {
                        "got": (
                            type(artifact).__name__
                            if artifact is not None
                            else "None"
                        ),
                        "reason": (
                            "the carrier carries no sealed artifact — an "
                            "object.__new__ shell or a stripped instance "
                            "has no z to assemble (dispatch §一(c))"
                        ),
                    },
                )
            return _levels_of(artifact)

        def __len__(self) -> int:
            return len(self._levels_of_carrier())

        def __iter__(self):
            return iter(self._levels_of_carrier())

        def __getitem__(self, index):
            return self._levels_of_carrier()[index]

    def _mint_sealed(artifact: CorrectionEvidenceBundleArtifactV1):
        return ValidatedFloorLadder(artifact, _seal=_LADDER_SEAL)

    return ValidatedFloorLadder, _mint_sealed


ValidatedFloorLadder, _mint_sealed_ladder = _seal_validated_ladder()


def _mint_ladder(
    claims: Sequence[FloorLevelClaimV1],
    frozen_docs: dict[str, dict],
) -> tuple[_DerivedFloorLevel, ...]:
    """Build the DERIVED levels from ALREADY-GATE-VALIDATED claims + frozen docs.

    ⚠️ PRIVATE and byte-derived: the z used to order and to size each storey is
    resolved from ``frozen_docs`` (see :func:`_byte_z`), ⛔ never from
    ``claim.z_m``.  The rule (the consumer-side mirror of B3's
    ``FLOOR_LEVEL_SELECTION_RULE``): sort the rungs ascending by their frozen
    byte; N distinct rungs give N-1 storeys; storey ``i`` sits on rung ``i`` and
    rises to rung ``i+1``.  It returns the raw levels tuple — sealing them
    into a :class:`ValidatedFloorLadder` is :func:`derive_floor_ladder`'s job
    (the seal lives in the closure, ⛔ not here).

    Loud, never silent (T4):
      * fewer than ``MIN_FLOOR_LEVELS`` rungs -> ``FLOOR_LADDER_DEGENERATE``;
      * two rungs at the same byte z (the ladder does not strictly ascend,
        "标高不单调"), also exactly the degenerate zero-height case ->
        ``FLOOR_LADDER_NOT_ASCENDING``.

    ⛔ Sorting is NOT silent repair: after the sort, any adjacent pair whose
    rise is <= 0 can only be a duplicate rung, reported by name, not swallowed.
    """
    ordered = sorted(claims, key=lambda c: _byte_z(frozen_docs, c.z_ref))
    if len(ordered) < MIN_FLOOR_LEVELS:
        raise MultiFloorAssemblyError(
            "FLOOR_LADDER_DEGENERATE",
            {"n_levels": len(ordered), "min_levels": MIN_FLOOR_LEVELS},
        )
    levels: list[_DerivedFloorLevel] = []
    for index in range(len(ordered) - 1):
        lower, upper = ordered[index], ordered[index + 1]
        rise = _byte_z(frozen_docs, upper.z_ref) - _byte_z(frozen_docs, lower.z_ref)
        if rise <= 0.0:
            raise MultiFloorAssemblyError(
                "FLOOR_LADDER_NOT_ASCENDING",
                {
                    "lower_id": lower.structure_line_id,
                    "upper_id": upper.structure_line_id,
                    "z_lower_m": _byte_z(frozen_docs, lower.z_ref),
                    "z_upper_m": _byte_z(frozen_docs, upper.z_ref),
                    "rise_m": rise,
                },
            )
        levels.append(
            _DerivedFloorLevel(
                floor_index=index, lower=lower, upper=upper, frozen_docs=frozen_docs
            )
        )
    return tuple(levels)


def _levels_of(
    elevation_evidence: CorrectionEvidenceBundleArtifactV1,
) -> tuple[_DerivedFloorLevel, ...]:
    """THE single derivation core — gate FIRST, then byte-resolve the levels.

    ⭐ Rework-3 (dispatch §一(c) at the boundary): EVERY consumer of storey z —
    :func:`derive_floor_ladder`, the carrier's own ``__len__`` / ``__iter__`` /
    ``__getitem__``, and :func:`assemble_multifloor_geometry` — gets its levels
    from THIS function, which re-runs B3's ``validate_evidence_bundle`` and
    resolves each z from the frozen bytes via :func:`_byte_z`.  There is no
    second copy of the gate and no stored z anywhere: whatever a caller did to
    an instance in between cannot survive this re-derivation.  A claim whose
    ``z_m`` drifted from the byte its ``z_ref`` names is a named
    ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` red HERE."""
    validate_evidence_bundle(elevation_evidence)
    frozen_docs = {
        source.artifact.input_id: json.loads(source.raw_bytes)
        for source in elevation_evidence.frozen_sources
    }
    return _mint_ladder(elevation_evidence.bundle.floor_level_claims, frozen_docs)


def derive_floor_ladder(
    elevation_evidence: CorrectionEvidenceBundleArtifactV1,
) -> ValidatedFloorLadder:
    """B2/T1: turn B3's frozen floor-level ladder into a SEALED per-storey ladder.

    ⭐ B-1/B-2 (rework-2 2026-09-04g) + the rework-3 seal: the SOLE input is the
    SEALED carrier ``elevation_evidence`` (``CorrectionEvidenceBundleArtifactV1``
    = bundle plus its frozen bytes), ⛔ NOT a detached
    ``Sequence[FloorLevelClaimV1]``.  The FIRST act is B3's existing value↔byte
    gate via :func:`_levels_of`: a claim whose ``z_m`` drifted from the byte its
    ``z_ref`` names is a named ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` red
    HERE, before any carrier is minted (the derivation result is deliberately
    consumed only for its errors — the carrier re-derives on every read, so it
    stores no z-bearing state).  The returned :class:`ValidatedFloorLadder` is
    the only thing :func:`assemble_multifloor_geometry` accepts, so "passed the
    frozen-byte gate" is carried by the TYPE, ⛔ not by the history of some call.
    """
    _levels_of(elevation_evidence)
    return _mint_sealed_ladder(elevation_evidence)


def _footprint_fingerprint(floor: FloorV3):
    """A rotation/reflection-invariant fingerprint of one floor's footprint.

    ⭐ B-3 (dispatch §二 / §三): a VERBATIM copy of ``schema.py:_v3_integrity``'s
    per-floor identity fingerprint, so the explicit common-footprint pre-check
    below decides "footprints differ" EXACTLY as the schema would — never a
    looser or stricter mirror that would relabel a non-footprint error or miss a
    real one."""
    pts = [(float(x), float(y)) for x, y in floor.footprint.vertices]
    if pts and pts[0] == pts[-1]:
        pts.pop()
    forward = min(tuple(pts[i:] + pts[:i]) for i in range(len(pts)))
    rev = list(reversed(pts))
    backward = min(tuple(rev[i:] + rev[:i]) for i in range(len(rev)))
    return min(forward, backward)


def assemble_multifloor_geometry(
    ladder: ValidatedFloorLadder,
    single_floor_geometries: Sequence[CorrectedGeometryV3],
) -> CorrectedGeometryV3:
    """B2/T2+T3: stack N single-floor projections into one ``floors[]``.

    ⭐ B-2 (dispatch §〇③ + rework-3 §一(c)): the SOLE z-bearing input is
    ``ladder``, a SEALED :class:`ValidatedFloorLadder` minted only by
    :func:`derive_floor_ladder` (which runs the frozen-byte gate first).  A bare
    ``Sequence[_DerivedFloorLevel]`` — or anything else — is type-refused as
    ``UNSEALED_FLOOR_LADDER``, so no low-level-helper combination re-acquires
    production assembly capability.  ⭐ And this boundary does not TRUST the
    carrier's history either: the levels it consumes are RE-DERIVED through the
    carrier's read path (``tuple(ladder)`` -> gate + ``_byte_z`` resolution),
    ⛔ never read off stored instance state — so even an ``object.__new__``
    shell or a post-hoc-swapped artifact assembles only bytes that re-pass the
    gate in THIS call.  Each output floor's ``z_floor`` / ``ceiling_height``
    are re-stamped from that derived rung's BYTE-RESOLVED z, ⛔ never from
    whatever the incoming single-floor geometry carried.
    ``single_floor_geometries`` supplies only the XY (id/name/footprint/cells),
    one per storey, ground-up (``ladder[i]`` pairs with
    ``single_floor_geometries[i]``).

    Loud, never silent (T4):
      * ``ladder`` is not a ``ValidatedFloorLadder`` -> ``UNSEALED_FLOOR_LADDER``;
      * the carrier carries no sealed artifact (an ``object.__new__`` shell or
        a stripped instance) -> ``LADDER_CARRIER_CORRUPT`` (from the read path);
      * the carrier's artifact fails the re-run gate (e.g. a drifted ``z_m``)
        -> ``EvidenceContractError`` from ``_levels_of``, RAW, ⛔ never swallowed;
      * ``len(ladder) != len(single_floor_geometries)``
        -> ``FLOOR_PLAN_COUNT_MISMATCH`` (⛔ never a truncation);
      * a derived level with ``ceiling_height_m <= 0`` ->
        ``NONPOSITIVE_CEILING_HEIGHT`` (defense-in-depth: unreachable through
        the sealed surface, because ``_mint_ladder`` refuses non-ascending
        rungs — kept for a future assembler that stamps z from elsewhere);
      * a single-floor geometry not carrying exactly one floor
        -> ``EXPECTED_SINGLE_FLOOR_GEOMETRY``;
      * two storeys sharing a floor id -> ``DUPLICATE_FLOOR_ID`` (downstream
        cell ids are ``{floor_id}-cNNN``; a duplicate would collide cells).

    ⭐ B-3 (dispatch §二 / §三 / verdict B-3): the common-footprint invariant is
    checked by an EXPLICIT pre-construction comparison of every floor's footprint
    fingerprint (:func:`_footprint_fingerprint`, the schema's own algorithm).  A
    mismatch is raised by name as ``PER_FLOOR_FOOTPRINT_MISMATCH`` HERE, before
    the schema construction runs.  ⛔ The construction's ``ValidationError`` is
    NO LONGER inspected by ``loc``/``type`` or by any substring of ``str(exc)``:
    ``PER_FLOOR_FOOTPRINT_MISMATCH`` comes ONLY from this pre-check, so ANY schema
    error at construction (empty floor id, a future windows/segments rule, …)
    propagates RAW and can never be mislabeled as a footprint mismatch
    (acceptance #4, as a RULE — ⛔ not a list of exceptions).

    Then the stacked floors MUST pass the existing z-stack continuity check
    (``geometry_validator.check_zstack``, the same rule as
    ``pipeline.correction_draw_issues`` at pipeline.py:661): a break is
    ``Z_STACK_DISCONTINUITY``.  ⛔ The check is neither bypassed nor relaxed
    (T3) — it is called, and its "not ok" is raised.  (⚠️ By construction the
    stacked ladder is continuous; this guard therefore has teeth only against a
    future assembler that stamps z from some other source.  Its passing is a
    guardrail, ⛔ not an acceptance signal — see dispatch §三①.)

    ⭐ Localised assumption (invariant #6): assembly is COMMON-FOOTPRINT only —
    the current "共底面盒子 / 每层满铺楼板" simplification.  Per-floor DIFFERENT
    footprints (setback / 退台) are explicitly NOT this module's job (dispatch
    §四); the assumption is not 烤死-silent — a violation is the named
    ``PER_FLOOR_FOOTPRINT_MISMATCH`` above.
    """
    if not isinstance(ladder, ValidatedFloorLadder):
        raise MultiFloorAssemblyError(
            "UNSEALED_FLOOR_LADDER",
            {
                "got": type(ladder).__name__,
                "reason": (
                    "assembly accepts ONLY a ValidatedFloorLadder minted by "
                    "derive_floor_ladder (which runs the frozen-byte gate); a "
                    "detached level sequence has not passed the gate"
                ),
            },
        )
    # ⭐ rework-3: the levels are RE-DERIVED here (gate + byte resolution) via
    # the carrier's read path — an instance-carried z never reaches this loop.
    levels = tuple(ladder)
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
        # ⭐ z is re-stamped from the DERIVED level (byte-resolved) — evidence is
        # the single source of truth for storey elevation; the incoming
        # geometry's own z_floor/ceiling_height are not trusted here.
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

    # ⭐ B-3: EXPLICIT common-footprint pre-check (the schema's own fingerprint).
    # PER_FLOOR_FOOTPRINT_MISMATCH is raised ONLY here — so no schema
    # ValidationError at construction below can ever be mislabeled as footprint.
    if len({_footprint_fingerprint(floor) for floor in floors}) != 1:
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

    # ⛔ No try/except around the construction: any ValidationError (empty floor
    # id, etc.) propagates RAW — it is NEVER relabeled as footprint (B-3).
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
    "ValidatedFloorLadder",
    "assemble_multifloor_geometry",
    "derive_floor_ladder",
]
