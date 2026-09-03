"""B2: multi-floor assembly — derive per-storey z from the frozen floor-level
ladder (B3 evidence) and stack single-floor projections into one
``CorrectedGeometryV3`` with ``floors[]`` of length N.

⭐ The whole point of this module (dispatch 2026-09-03ai): the storey
elevations are DERIVED from frozen reading bytes, ⛔ never hand-filled.  There
is no z parameter anywhere in this module — a caller cannot inject one — and
every derived value traces back to the exact byte it came from, the same rule
B3 holds for its ``floor_level_claims`` (each carries a ``z_ref``).

Layering: this module is PURE — it depends only on the evidence contract, the
correction schema, and the geometry validator.  It never imports
``pipeline``.  The model-driven orchestration that runs the evidence chain
once per plan product and feeds the derived z into
``evidence_chain_z_floor_m`` / ``evidence_chain_ceiling_height_m`` lives in
``pipeline.run_multifloor_correction`` (which imports THIS module, not the
other way round).

⛔ NOT this module's job (dispatch §四): opening synthesis (B4), touching the
projection bridge's geometry algorithm, relaxing the z-stack continuity check,
or reading gt.  It also does not specialise to sm25 — "two floors" / "3.6 m"
are readings, not theorems: the storey count is COUNTED from the data and each
storey height is COMPUTED from the data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

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
class DerivedFloorLevel:
    """One storey's z, DERIVED from the frozen floor-level ladder (B2/T1).

    ⛔ Never hand-filled: every field traces to a byte in the frozen reading
    product.  ``z_floor_m`` is the ladder rung this storey sits on;
    ``ceiling_height_m`` is the rise to the next rung — a DERIVED difference,
    so it carries BOTH operands' byte refs (``z_floor_ref`` for the lower
    rung, ``z_top_ref`` for the upper), ⛔ never a bare number with no source.
    """

    floor_index: int
    z_floor_m: float
    ceiling_height_m: float
    z_floor_claim_id: str
    z_floor_ref: ArtifactPointerV1
    z_top_claim_id: str
    z_top_ref: ArtifactPointerV1


def derive_floor_ladder(
    floor_level_claims: Sequence[FloorLevelClaimV1],
) -> tuple[DerivedFloorLevel, ...]:
    """B2/T1: turn B3's frozen floor-level ladder into per-storey z meta.

    The rule (the consumer-side mirror of B3's ``FLOOR_LEVEL_SELECTION_RULE``):
    sort the claimed rungs ascending; N distinct rungs give N-1 storeys;
    storey ``i`` sits on rung ``i`` and rises to rung ``i+1``.  Each z is a
    byte read from the frozen source, ⛔ never invented — the returned
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
    levels: list[DerivedFloorLevel] = []
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
            DerivedFloorLevel(
                floor_index=index,
                z_floor_m=lower.z_m,
                ceiling_height_m=rise,
                z_floor_claim_id=lower.structure_line_id,
                z_floor_ref=lower.z_ref,
                z_top_claim_id=upper.structure_line_id,
                z_top_ref=upper.z_ref,
            )
        )
    return tuple(levels)


def assemble_multifloor_geometry(
    levels: Sequence[DerivedFloorLevel],
    single_floor_geometries: Sequence[CorrectedGeometryV3],
) -> CorrectedGeometryV3:
    """B2/T2+T3: stack N single-floor projections into one ``floors[]``.

    ``levels`` (from :func:`derive_floor_ladder`) is the SOLE source of every
    assembled floor's z: the output floor's ``z_floor`` / ``ceiling_height``
    are re-stamped from the derived rung, ⛔ never taken from whatever the
    incoming single-floor geometry happened to carry.  ``single_floor_
    geometries`` supplies only the XY — the ``FloorV3`` id/name/footprint/cells
    — one per storey, ground-up (``levels[i]`` pairs with
    ``single_floor_geometries[i]``).  There is no z parameter: the hand-fill
    path does not exist at this boundary (T5).

    Loud, never silent (T4):
      * ``len(levels) != len(single_floor_geometries)``
        -> ``FLOOR_PLAN_COUNT_MISMATCH`` (the storey count comes from the
        elevation ladder; a plan-product count that disagrees is a real,
        unresolvable mismatch, ⛔ never a truncation);
      * a derived level with ``ceiling_height_m <= 0``
        -> ``NONPOSITIVE_CEILING_HEIGHT`` (a defensive boundary check: even if
        a caller hand-built a ``DerivedFloorLevel`` bypassing
        :func:`derive_floor_ladder`, a non-physical storey height stops here);
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
    "DerivedFloorLevel",
    "MultiFloorAssemblyError",
    "assemble_multifloor_geometry",
    "derive_floor_ladder",
]
