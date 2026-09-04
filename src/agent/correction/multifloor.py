"""B2: multi-floor assembly — derive per-storey z from the frozen floor-level
ladder (B3 evidence) and stack single-floor projections into one
``CorrectedGeometryV3`` with ``floors[]`` of length N.

⭐ The whole point of this module (dispatch 2026-09-03ai / rework 2026-09-04a):
the storey elevations are DERIVED from frozen reading bytes, ⛔ never
hand-filled.

Two things make "a hand-filled z assembles successfully" impossible rather than
merely discouraged:

  * **No raw z anywhere in the carrier (B-2, type layer).** The derived carrier
    ``_DerivedFloorLevel`` has NO settable z field — ``z_floor_m`` /
    ``ceiling_height_m`` are read-only PROPERTIES computed from a bounding pair
    of ``FloorLevelClaimV1`` (each of which names the frozen byte it was read
    from via ``z_ref``).  The old ``DerivedFloorLevel(z_floor_m=12.34,
    ceiling_height_m=5.67)`` hand-fill no longer type-checks: those keywords do
    not exist.  To put a z into an assembled geometry you must supply a claim
    whose ``z_m`` names a byte.
  * **The production entry runs B3's value↔byte gate (B-1).**
    ``pipeline.run_multifloor_correction`` consumes the sealed
    ``CorrectionEvidenceBundleArtifactV1`` (bundle + frozen bytes) and runs
    ``validate_evidence_bundle`` on it BEFORE any storey is derived, so a claim
    whose ``z_m`` drifted from its frozen byte is a named
    ``FLOOR_LEVEL_VALUE_DRIFTED_FROM_SOURCE`` red — the SAME B3 gate
    (``evidence_contract.py`` §B3), reused, ⛔ not re-implemented here.

Layering: this module is PURE — it depends only on the evidence contract, the
correction schema, and the geometry validator.  It never imports ``pipeline``.
The model-driven orchestration that runs the evidence chain once per plan
product and feeds the derived z into ``evidence_chain_z_floor_m`` /
``evidence_chain_ceiling_height_m`` lives in
``pipeline.run_multifloor_correction`` (which imports THIS module, not the
other way round).

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

from pydantic import ValidationError

from src.agent.correction.evidence_contract import (
    MIN_FLOOR_LEVELS,
    ArtifactPointerV1,
    FloorLevelClaimV1,
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


@dataclass(frozen=True)
class _DerivedFloorLevel:
    """One storey's z, DERIVED from a bounding pair of frozen floor-level
    claims (B2/T1) — ⛔ never hand-filled.

    ⭐ Type-level no-hand-fill (B-2, dispatch §二): this carrier holds the two
    bounding ``FloorLevelClaimV1`` (``lower`` = the rung this storey sits on,
    ``upper`` = the next rung up) and NOTHING a caller can set to a bare z.
    Every z-shaped attribute is a READ-ONLY property computed from those two
    claims:

      * ``z_floor_m`` is the lower rung's ``z_m`` (which names a frozen byte);
      * ``ceiling_height_m`` is the rise ``upper.z_m - lower.z_m`` — a DERIVED
        difference that carries BOTH operands' byte refs.

    There is no ``z_floor_m=`` / ``ceiling_height_m=`` constructor keyword, so
    the reviewer's ``DerivedFloorLevel(z_floor_m=12.34, ceiling_height_m=5.67)``
    hand-fill is a ``TypeError`` now, not a silent success.  This class is
    PRIVATE (⛔ not in ``__all__``): the only sanctioned minter is
    :func:`derive_floor_ladder`, and the only production-reachable path to it,
    ``pipeline.run_multifloor_correction``, validates the frozen carrier first
    (B-1).
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


def _is_footprint_mismatch_error(exc: ValidationError) -> bool:
    """B-3 (dispatch §三): is this ValidationError the common-footprint
    invariant firing, decided by the error's STRUCTURE — ⛔ never by a substring
    of ``str(exc)``?

    The footprint check is a model-level after-validator
    (``schema.py:_v3_integrity``), which pydantic tags ``type == "value_error"``
    with an EMPTY ``loc``.  pydantic runs that after-validator ONLY once every
    field validated, so a field-level error (missing / wrong-type /
    extra-forbidden — even one whose text happens to contain the footprint
    sentence) always carries a NON-empty ``loc`` and returns ``False`` here.  At
    :func:`assemble_multifloor_geometry`'s construction site
    (``windows``/``facade_segments`` empty, floor ids pre-de-duplicated) the
    only empty-loc value_error reachable is the footprint mismatch, so this
    predicate never renames another schema error as footprint (acceptance #4).
    """
    errs = exc.errors()
    return bool(errs) and all(
        e.get("loc") == () and e.get("type") == "value_error" for e in errs
    )


def derive_floor_ladder(
    floor_level_claims: Sequence[FloorLevelClaimV1],
) -> tuple[_DerivedFloorLevel, ...]:
    """B2/T1: turn B3's frozen floor-level ladder into per-storey z meta.

    ⚠️ This is a LOW-LEVEL helper on already-validated claims, ⛔ NOT a
    production capability entry: the production path
    (``pipeline.run_multifloor_correction``) runs the B3 value↔byte gate on the
    sealed carrier BEFORE calling this, so a hand-crafted claim whose ``z_m``
    drifted from its byte never reaches here on a real run (B-1).

    The rule (the consumer-side mirror of B3's ``FLOOR_LEVEL_SELECTION_RULE``):
    sort the claimed rungs ascending; N distinct rungs give N-1 storeys;
    storey ``i`` sits on rung ``i`` and rises to rung ``i+1``.  Each z is a
    byte read from the frozen source, ⛔ never invented — the returned level's
    ``z_floor_ref`` / ``z_top_ref`` are the very ``z_ref`` pointers the two
    bounding claims carry, so acceptance #1 can dereference any derived value
    straight back to the frozen bytes.

    Loud, never silent (T4):
      * fewer than ``MIN_FLOOR_LEVELS`` rungs -> ``FLOOR_LADDER_DEGENERATE``;
      * two rungs at the same z (the ladder does not strictly ascend, i.e.
        "标高不单调"), which is also exactly the degenerate case that would
        compute a zero storey height -> ``FLOOR_LADDER_NOT_ASCENDING``.

    ⛔ Sorting is NOT silent repair of a genuinely non-monotone ladder: after
    the sort, any adjacent pair whose rise is <= 0 can only be a duplicate
    rung, and that is reported by name rather than swallowed.
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


def assemble_multifloor_geometry(
    levels: Sequence[_DerivedFloorLevel],
    single_floor_geometries: Sequence[CorrectedGeometryV3],
) -> CorrectedGeometryV3:
    """B2/T2+T3: stack N single-floor projections into one ``floors[]``.

    ``levels`` (from :func:`derive_floor_ladder`) is the SOLE source of every
    assembled floor's z: the output floor's ``z_floor`` / ``ceiling_height``
    are re-stamped from the derived rung, ⛔ never taken from whatever the
    incoming single-floor geometry happened to carry.  ``single_floor_
    geometries`` supplies only the XY — the ``FloorV3`` id/name/footprint/cells
    — one per storey, ground-up (``levels[i]`` pairs with
    ``single_floor_geometries[i]``).  There is no z parameter, and ``levels``
    carries no raw z either (its z is a property of frozen-byte-bound claims):
    the hand-fill path does not exist at this boundary (T5 / B-2).

    Loud, never silent (T4):
      * ``len(levels) != len(single_floor_geometries)``
        -> ``FLOOR_PLAN_COUNT_MISMATCH`` (the storey count comes from the
        elevation ladder; a plan-product count that disagrees is a real,
        unresolvable mismatch, ⛔ never a truncation);
      * a derived level with ``ceiling_height_m <= 0``
        -> ``NONPOSITIVE_CEILING_HEIGHT`` (a defensive boundary check: even a
        forged ``_DerivedFloorLevel`` whose bounding claims do not ascend is
        stopped here, before it can stamp a non-physical storey height);
      * a single-floor geometry that does not carry exactly one floor
        -> ``EXPECTED_SINGLE_FLOOR_GEOMETRY``;
      * two storeys sharing a floor id -> ``DUPLICATE_FLOOR_ID`` (downstream
        geometry dicts key on cell id, and cell ids are ``{floor_id}-cNNN``,
        so a duplicate floor id silently collides cells last-wins).

    Then the stacked floors MUST pass the existing z-stack continuity check
    (``geometry_validator.check_zstack``, the same rule as
    ``pipeline.correction_draw_issues`` at pipeline.py:661): a break is
    ``Z_STACK_DISCONTINUITY``.  ⛔ The check is neither bypassed nor relaxed
    (T3) — it is called, and its "not ok" is raised.  (⚠️ By construction the
    stacked ladder is continuous, since ``z_floor[i] + ceiling[i] ==
    rung[i+1] == z_floor[i+1]``; this guard therefore has teeth only against a
    future assembler that stamps z from some other source.  Its passing is a
    guardrail, ⛔ not an acceptance signal — see dispatch §三①.)

    ⭐ Localised assumption (invariant #6): assembly is COMMON-FOOTPRINT only.
    Every storey must describe the same footprint domain — the current
    "共底面盒子 / 每层满铺楼板" simplification, which the ``CorrectedGeometryV3``
    schema already enforces (``per-floor footprints must have identical
    geometry``).  Per-floor DIFFERENT footprints (setback / 退台) are explicitly
    NOT this module's job (dispatch §四); the assumption is not烤死-silent — a
    violation is re-raised here as a named ``PER_FLOOR_FOOTPRINT_MISMATCH``.
    ⛔ The label is decided by the ERROR'S STRUCTURE (loc/type), ⛔ never by a
    substring of ``str(exc)`` (B-3): see the ``except`` below.
    """
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

    try:
        assembled = CorrectedGeometryV3(
            schema_version="3",
            footprint_x=[min(xs_lo), max(xs_hi)],
            footprint_y=[min(ys_lo), max(ys_hi)],
            floors=floors,
            windows=[],
            facade_segments=[],
        )
    except ValidationError as exc:
        # B-3 (dispatch §三 / verdict B-3): the label is decided by the error's
        # STRUCTURE (see :func:`_is_footprint_mismatch_error`), ⛔ NEVER by a
        # substring of ``str(exc)``.  A field-level schema error — even one
        # whose text happens to contain the footprint sentence — surfaces RAW,
        # never relabeled (acceptance #4).  ⛔ The schema's own check stays the
        # authority; this branch only renames its verdict.
        if _is_footprint_mismatch_error(exc):
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
            ) from exc
        raise

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
