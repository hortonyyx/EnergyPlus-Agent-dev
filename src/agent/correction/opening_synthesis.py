"""B4 -- opening synthesis: cross-view identity pairing (dispatch 2026-09-03ag).

WHAT THIS MODULE OWNS
---------------------
The three steps of the measured zero-parameter plan (see the cross-view
probe, ``AI_agent/logs/experiments/2026-09-02b_b4_cross_view_identity``),
plus the named premise they stand on:

1. **The anchor (T1).**  The elevation's local ``x = 0`` is the LEFT END of
   that drawing's dimension chain -- not a world origin.  Which WORLD end
   of the along-wall axis that is, is NOT guessed here: it comes from the
   project's one signed sign convention (``facade_convention``: looking at
   the facade from outside, local x running left to right), so
   ``world = along_origin + sign * local_x`` with ``sign`` from
   :func:`facade_convention.resolve_sign`.  On the real four sm25 facades
   that convention resolves exactly as measured (South/East +1,
   North/West -1 -- the observer's-left rule; the probe's own pairing data
   confirms it, see the B4 test file).  ``along_origin`` is the outer-skin
   end of the along-wall axis that the chain starts from.

   The outer-skin span is DERIVED, ⛔ never a constant and ⛔ never a
   single global offset: it is the midline bbox plus the two end walls'
   OWN half thicknesses, EACH END TAKING THE THICKNESS OF THE WALL(S)
   THAT END THE BBOX AT THAT END (dispatch §三: sm25's uniform 240 is a
   reading, not a theorem).  A fixture with four different edge
   thicknesses must and does come out right.

2. **The equality gate (T2, handed over from B3 by dispatch 2026-09-03).**
   ``chain_total_length == outer_skin_span`` is an EQUALITY, ⛔ never a
   threshold: B3 could not close this (it had no typed plan-side span and
   would have needed a nobody-signed tolerance against 0.01-0.5 px ink
   jitter), B4 can, because the plan side is an input here.  Mismatch is
   a loud, named failure -- and it is simultaneously the detector of the
   named premise below, at zero extra cost.

3. **The pairing (T3).**  Both sides are converted to world along-wall
   intervals and paired by **interval equality** -- ⛔ no nearest-distance,
   no order-based pairing, no "within tolerance" matching.  An elevation
   opening whose interval has no plan counterpart is named unmatched;
   it is NEVER guessed onto a neighbour.

THE NAMED PREMISE (T5)
----------------------
``ELEVATION_CHAIN_SPANS_WHOLE_BUILDING`` (defined by B3 in
``evidence_adapters``; imported, ⛔ not re-typed here -- one source): "the
elevation's dimension chain spans the whole building".  A property of how
this family of drawings is drawn, ⛔ not a theorem.  It must hold for the
anchor to mean anything; the equality gate (step 2) is its detector, so a
partial/one-bay elevation fails loudly by name instead of being silently
treated as whole-building.

THE ARITHMETIC DOMAIN (why every comparison here is integer)
------------------------------------------------------------
All comparisons run on the project's DECLARED coordinate grid, 0.1 mm
integer units (``DECLARED_GRID_UNITS_PER_M``; the gt-revision-ledger's
signed "coordinates are 0.1 mm integers" ruling).  Both families of input
already live on that grid -- the plan side natively (as-measured units),
the elevation side because its dimension-chain totals are drawn mm
integers and its interval readings are emitted at 0.1 mm granularity.
:func:`grid_units` enforces that membership EXACTLY (a round-trip float
equality, ⛔ no epsilon): a value off the grid is a loud input fault, so
the equality gate and the pairing are exact integer comparisons with zero
constants anywhere near them.  The elevation's pixel-quantised readings
(mm_per_px ~ 13.6 mm on the real facades) mean real-data intervals are
typically a few grid units off the plan side; those land in ``unmatched``,
which is the honest reading, ⛔ not a defect of the pairing rule.  Making
them match is the reading side's business (chain-tick evidence), never a
tolerance here.

THE DEBT WIRING (T4-b / T4-c; ⛔ structural, never textual)
-----------------------------------------------------------
B3 ships the span gap as an ``EvidenceDebtV1`` whose ``debt_id`` carries
the type prefix ``debt_elevation_chain_span_unchecked_``.  The
cross-review's N-1 finding was that "owned by B4" lived only in the FREE
TEXT ``description`` -- locking a word, not a structure
(``OWNER_TEXT_REMOVED=GREEN``).  This module's
:data:`DEBT_REDEMPTION_REGISTRY` wires debt TYPE PREFIXES (the structural
identity a producer mints into ``debt_id``) to the named gate that
redeems them; ``description`` is never read.  A debt whose type this
stage redeemed is RETIRED (:T4-c): it travels into the product's
``retired_debt_ids`` once the equality gate has actually passed for that
product -- a debt that failed the gate is NOT retired (the obligation is
still open, exactly as before).

⛔ NOT THIS MODULE'S BUSINESS: the EvidenceDebtV1 schema upgrade (adding
a structured obligation/owner field) is dispatch sheet §五 A-② STOP-AND-
REPORT territory -- it touches every existing debt and potentially the
hash of already-persisted products; the adapter seat must not invent it
unilaterally (see the B4 execution report for the written-up proposal).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict

from src.agent.correction.evidence_adapters import (
    ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
)
from src.agent.correction.evidence_contract import EvidenceDebtV1
from src.agent.correction.facade_convention import resolve_sign, world_axis
from src.agent.correction.projection_bridge import CutLineV1
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_ELEVATION_V0,
    classify_vector_json,
)

#: The project's signed coordinate granularity: 0.1 mm integer units per
#: metre (gt revision ledger, "coordinates are 0.1 mm integers").  This is
#: the ONE unit convention this module's arithmetic runs on; it is a
#: declared GRID, ⛔ not a tolerance.
DECLARED_GRID_UNITS_PER_M = 10_000

#: millimetres per grid unit (10 u = 1 mm).
_GRID_UNITS_PER_MM = 10

SYNTHESIS_SCHEMA_VERSION = "opening_synthesis_v1"

_FAMILIES = ("North", "South", "East", "West")


class OpeningSynthesisError(ValueError):
    """A loud, named rejection with a stable ``code`` (same shape as
    ``EvidenceContractError`` / ``ProjectionBridgeError``).  Everything
    this module rejects is an input-integrity or premise fault: never a
    model's job to fix, never silently absorbed."""

    def __init__(self, code: str, context: dict | None = None):
        self.code = code
        self.context = dict(context or {})
        super().__init__(f"{code}: {self.context}")


# ── the declared-grid arithmetic (exact, ⛔ no epsilon) ─────────────────────── #
def grid_units(value_m: float, *, what: str) -> int:
    """Metres -> 0.1 mm grid units, EXACTLY on the declared grid.

    The membership test is a round-trip float equality: ``u / 10_000 ==
    value_m``.  A value that is a grid point's nearest double round-trips
    bit-identically (measured on every real reading this module consumes:
    wall midlines, half thicknesses, chain totals, elevation interval
    readings); a value BETWEEN grid points does not, and that is exactly
    the fault this raises.  ⛔ No epsilon anywhere: this is the grid the
    project signed, enforced as a premise, not approximated.
    """
    scaled = value_m * DECLARED_GRID_UNITS_PER_M
    unit = round(scaled)
    if unit / DECLARED_GRID_UNITS_PER_M != value_m:
        raise OpeningSynthesisError(
            "VALUE_OFF_DECLARED_GRID",
            {"what": what, "value_m": value_m},
        )
    return unit


def grid_units_from_mm(value_mm: float, *, what: str) -> int:
    """Millimetres -> 0.1 mm grid units, same exact-membership discipline
    as :func:`grid_units` (chain totals are drawn mm integers; a chain
    value off the 0.1 mm grid is a malformed chain, loudly so)."""
    scaled = value_mm * _GRID_UNITS_PER_MM
    unit = round(scaled)
    if unit / _GRID_UNITS_PER_MM != value_mm:
        raise OpeningSynthesisError(
            "VALUE_OFF_DECLARED_GRID",
            {"what": what, "value_mm": value_mm},
        )
    return unit


def _mm_display(unit: int) -> float:
    """Grid units -> mm for error contexts and product readings only;
    ⛔ never an input to a comparison."""
    return unit / _GRID_UNITS_PER_MM


# ── step 2 (T2): the span equality gate, named for the registry ────────────── #
def span_equality_gate(
    *, chain_total_mm: float, skin_lo_u: int, skin_hi_u: int
) -> int:
    """``chain_total == outer_skin_span`` -- an EQUALITY on the declared
    grid, ⛔ not a threshold.

    Returns the span in grid units on success.  On mismatch this raises
    ``ELEVATION_CHAIN_SPAN_MISMATCH`` naming the premise whose failure it
    is (a partial/one-bay elevation is the loud case, T5) and BOTH
    readings -- a mismatch report without both numbers is an invitation
    for someone downstream to "fix" it with a tolerance, which is the one
    thing this gate exists to prevent.
    """
    chain_u = grid_units_from_mm(chain_total_mm, what="chain_total_mm")
    span_u = skin_hi_u - skin_lo_u
    if chain_u != span_u:
        raise OpeningSynthesisError(
            "ELEVATION_CHAIN_SPAN_MISMATCH",
            {
                "premise": ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
                "chain_total_mm": chain_total_mm,
                "skin_span_mm": _mm_display(span_u),
                "skin_lo_mm": _mm_display(skin_lo_u),
                "skin_hi_mm": _mm_display(skin_hi_u),
                "difference_grid_units": chain_u - span_u,
            },
        )
    return span_u


# ── T4-b: the debt redemption registry (structural, ⛔ never textual) ───────── #
#: debt TYPE PREFIX (the structural identity minted into ``debt_id`` by the
#: producer) -> the name of THIS module's gate that redeems it.  The value
#: must be a real callable of this module (checked at import), so the
#: registry entry is wiring, ⛔ not a string ornament.  ⛔⛔ ``description``
#: is never consulted: the cross-review measured that "Owner: B4" living
#: in free text locks a WORD, not a structure (``OWNER_TEXT_REMOVED=GREEN``).
DEBT_REDEMPTION_REGISTRY: dict[str, str] = {
    "debt_elevation_chain_span_unchecked_": "span_equality_gate",
}


def _assert_registry_well_formed() -> None:
    """Import-time teeth for the registry itself:

    * every value names a callable of THIS module (a registry row whose
      handler does not exist is decoration, and a future rename must be
      loud here, not silent dead wiring);
    * no key is a proper prefix of another key (a ``debt_id`` matching two
      type prefixes would be ambiguous wiring -- exactly the
      ``case``-path-through flavour of smuggling this project keeps
      finding).
    """
    seen: dict[str, str] = {}
    for prefix, handler in DEBT_REDEMPTION_REGISTRY.items():
        target = globals().get(handler)
        if not callable(target):
            raise OpeningSynthesisError(
                "DEBT_REGISTRY_HANDLER_MISSING",
                {"prefix": prefix, "handler": handler},
            )
        for other in seen:
            if other.startswith(prefix) or prefix.startswith(other):
                raise OpeningSynthesisError(
                    "DEBT_REGISTRY_PREFIX_AMBIGUOUS",
                    {"prefix_a": other, "prefix_b": prefix},
                )
        seen[prefix] = handler


_assert_registry_well_formed()


def redeemable_debt_ids(debts: Sequence[EvidenceDebtV1]) -> tuple[str, ...]:
    """Which of these debts THIS stage redeems, by debt TYPE PREFIX only.

    A ``debt_id`` matching ZERO registry prefixes is simply not ours (the
    caller keeps it); matching MORE than one is ambiguous wiring and is
    loud.  ⛔ The free-text ``description`` is never read.
    """
    redeemed: list[str] = []
    for debt in debts:
        matches = [
            prefix
            for prefix in DEBT_REDEMPTION_REGISTRY
            if debt.debt_id.startswith(prefix)
        ]
        if len(matches) > 1:
            raise OpeningSynthesisError(
                "DEBT_TYPE_AMBIGUOUS",
                {"debt_id": debt.debt_id, "matched_prefixes": sorted(matches)},
            )
        if matches:
            redeemed.append(debt.debt_id)
    return tuple(sorted(redeemed))


# ── the product ────────────────────────────────────────────────────────────── #
class OpeningPairingV1(BaseModel):
    """One cross-view identity: a plan opening and an elevation opening
    whose WORLD along-wall intervals are EQUAL on the declared grid.  The
    z travels from the elevation side -- that is the whole point of the
    synthesis (the plan side has no z)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    plan_opening_id: str
    elevation_opening_id: str
    span_lo_u: int
    span_hi_u: int
    z_low_u: int
    z_high_u: int


class OpeningSynthesisV1(BaseModel):
    """The B4 product.  Everything geometric is in 0.1 mm grid units --
    the module never emits a bare float metre that a consumer would have
    to compare with a tolerance.  ``unmatched_*`` name every opening the
    equality rule did NOT pair: an honest refusal list, ⛔ not an error
    and ⛔ never silently dropped."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["opening_synthesis_v1"]
    facade_family: str
    world_axis: Literal["x", "y"]
    sign: Literal[-1, 1]
    #: the anchor (T1): the world grid coordinate the elevation chain's
    #: ``x = 0`` maps to -- the outer-skin end the chain starts from.
    along_origin_u: int
    chain_total_u: int
    skin_lo_u: int
    skin_hi_u: int
    premise: str
    pairings: tuple[OpeningPairingV1, ...] = ()
    unmatched_plan_opening_ids: tuple[str, ...] = ()
    unmatched_elevation_opening_ids: tuple[str, ...] = ()
    #: openings that share one world along-wall interval with at least one
    #: OTHER opening (either side): interval equality cannot decide 1:1
    #: identity there (the real shape: stacked-storey windows directly
    #: above each other read as identical intervals), so EVERY member of
    #: such a group is refused, never guessed.  Storey identity is B2's
    #: dimension; this field is the honest "not decidable here" ledger.
    same_interval_groups: tuple[tuple[str, ...], ...] = ()
    #: T4-c: debts whose obligation THIS product actually discharged (the
    #: equality gate passed for this facade).  ⛔ Not a claim to have
    #: closed the debt type in general -- per product, per facade.
    retired_debt_ids: tuple[str, ...] = ()


# ── input views ─────────────────────────────────────────────────────────────── #
@dataclass(frozen=True)
class _SkinEnvelope:
    """The along-wall outer-skin span, per-end sourced (T1's arithmetic)."""

    lo_u: int
    hi_u: int
    #: each end's OWN half thickness, read from the walls that end the
    #: bbox AT THAT END (audit: which walls, which thickness -- so a
    #: reader can see the span was never one global offset).
    lo_end_half_u: int
    hi_end_half_u: int
    lo_end_wall_ids: tuple[str, ...]
    hi_end_wall_ids: tuple[str, ...]


def _skin_envelope(
    walls: Sequence[CutLineV1], *, across_axis: str, family: str
) -> _SkinEnvelope:
    """Midline bbox + each end's own ``t/2`` (T1), per-end sourced.

    ⚠️ AXIS VOCABULARY (the transposition trap this file's neighbours have
    already bitten on -- see ``projection_bridge._run_axis``): the along
    axis of a facade is ``world_axis(family)``; the walls that DECIDE a
    span along that axis are the ones whose MIDLINE is constant there,
    i.e. the walls RUNNING ON THE OTHER AXIS (``CutLineV1.axis`` names the
    run axis).  East/West span y ⇒ decided by x-running walls' ``pos_m``;
    North/South span x ⇒ decided by y-running walls' ``pos_m``.

    Per end: the walls whose midline ENDS the bbox there must agree on
    ONE half thickness (a disagreement is a contradiction in the data,
    loud), and the skin the end wall computes must be the skin of the
    WHOLE wall set on that side -- otherwise "outer skin = midline bbox +
    each end's own t/2" is false for this input (some other wall already
    pokes past the end wall), and that too is loud, ⛔ never silently
    absorbed into a wider envelope.
    """
    deciders = [w for w in walls if w.axis != across_axis]
    if not deciders:
        raise OpeningSynthesisError(
            "NO_WALLS_ALONG_FACADE_AXIS",
            {"family": family, "across_axis": across_axis},
        )
    pos_u = {
        w.origin_id: grid_units(w.pos_m, what=f"wall {w.origin_id} pos_m")
        for w in deciders
    }
    half_u = {
        w.origin_id: grid_units(
            w.half_thickness_m, what=f"wall {w.origin_id} half_thickness_m"
        )
        for w in deciders
    }
    mid_lo = min(pos_u.values())
    mid_hi = max(pos_u.values())

    def _end(end: Literal["lo", "hi"]) -> tuple[int, tuple[str, ...]]:
        edge = mid_lo if end == "lo" else mid_hi
        ids = tuple(
            sorted(w.origin_id for w in deciders if pos_u[w.origin_id] == edge)
        )
        halves = {half_u[i] for i in ids}
        if len(halves) != 1:
            raise OpeningSynthesisError(
                "SKIN_END_WALL_THICKNESS_AMBIGUOUS",
                {
                    "family": family,
                    "end": end,
                    "wall_ids": ids,
                    "half_thicknesses_u": sorted(halves),
                },
            )
        return halves.pop(), ids

    lo_half, lo_ids = _end("lo")
    hi_half, hi_ids = _end("hi")
    skin_lo = mid_lo - lo_half
    skin_hi = mid_hi + hi_half

    envelope_lo = min(pos_u[i] - half_u[i] for i in pos_u)
    envelope_hi = max(pos_u[i] + half_u[i] for i in pos_u)
    if envelope_lo != skin_lo or envelope_hi != skin_hi:
        raise OpeningSynthesisError(
            "SKIN_NOT_FROM_END_WALLS",
            {
                "family": family,
                "end_wall_skin": [_mm_display(skin_lo), _mm_display(skin_hi)],
                "wall_set_envelope": [
                    _mm_display(envelope_lo),
                    _mm_display(envelope_hi),
                ],
                "note": (
                    "some wall pokes past the midline-bbox end wall: the "
                    "premise 'outer skin = midline bbox + each end's own "
                    "t/2' is false for this input"
                ),
            },
        )
    return _SkinEnvelope(
        lo_u=skin_lo,
        hi_u=skin_hi,
        lo_end_half_u=lo_half,
        hi_end_half_u=hi_half,
        lo_end_wall_ids=lo_ids,
        hi_end_wall_ids=hi_ids,
    )


def _require_elevation_contract(doc: dict) -> None:
    """The elevation input must BE an ``as_drawn_elevation_v0`` product --
    classified by its bytes (the registered detector), ⛔ never by file
    name or by a field's say-so."""
    decision = classify_vector_json(doc)
    if decision.contract_id != CONTRACT_AS_DRAWN_ELEVATION_V0:
        raise OpeningSynthesisError(
            "ELEVATION_CONTRACT_MISMATCH",
            {
                "detected": decision.contract_id,
                "required": CONTRACT_AS_DRAWN_ELEVATION_V0,
                "reason": decision.reason,
            },
        )


def _elevation_chain_total_mm(doc: dict, family: str) -> float:
    chain = (doc.get("calibration") or {}).get("x")
    if not isinstance(chain, dict) or not isinstance(
        chain.get("cum_mm"), list
    ) or not chain["cum_mm"]:
        raise OpeningSynthesisError(
            "ELEVATION_CHAIN_MISSING",
            {"family": family},
        )
    total = chain["cum_mm"][-1]
    if isinstance(total, bool) or not isinstance(total, (int, float)):
        raise OpeningSynthesisError(
            "ELEVATION_CHAIN_TOTAL_NOT_NUMERIC",
            {"family": family, "cum_mm_last": total},
        )
    return total


def _elevation_openings(doc: dict) -> tuple[tuple[str, float, float, float, float], ...]:
    """(id, x_lo_m, x_hi_m, z_lo_m, z_hi_m) for every opening, validated
    loudly -- the pairing never touches an unvalidated node."""
    nodes = doc.get("openings")
    if not isinstance(nodes, list):
        raise OpeningSynthesisError(
            "ELEVATION_OPENINGS_MISSING", {"got": type(nodes).__name__}
        )
    out: list[tuple[str, float, float, float, float]] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise OpeningSynthesisError(
                "ELEVATION_OPENING_NODE_MALFORMED", {"index": index}
            )
        oid = node.get("id")
        if not isinstance(oid, str) or not oid:
            raise OpeningSynthesisError(
                "ELEVATION_OPENING_WITHOUT_ID", {"index": index}
            )
        parsed = []
        for field in ("x_range_m", "z_range_m"):
            span = node.get(field)
            if (
                not isinstance(span, list)
                or len(span) != 2
                or any(
                    isinstance(v, bool) or not isinstance(v, (int, float))
                    for v in span
                )
                or not float(span[0]) < float(span[1])
            ):
                raise OpeningSynthesisError(
                    "ELEVATION_OPENING_RANGE_MALFORMED",
                    {"opening_id": oid, "field": field, "value": span},
                )
            parsed.extend(float(v) for v in span)
        out.append((oid, parsed[0], parsed[1], parsed[2], parsed[3]))
    return tuple(out)


def _require_lines(
    lines: Sequence[CutLineV1], *, kind: Literal["wall", "opening"], what: str
) -> None:
    for line in lines:
        if line.kind != kind:
            raise OpeningSynthesisError(
                "CUT_LINE_KIND_MISMATCH",
                {"what": what, "origin_id": line.origin_id,
                 "expected_kind": kind, "got_kind": line.kind},
            )


# ── the synthesis itself ────────────────────────────────────────────────────── #
def synthesize_openings(
    *,
    elevation_doc: dict,
    walls: Sequence[CutLineV1],
    plan_openings: Sequence[CutLineV1],
    mirrored: bool,
    local_x_positive: str,
    evidence_debts: Sequence[EvidenceDebtV1] = (),
) -> OpeningSynthesisV1:
    """Steps 1-3 + the premise gate + the debt retirement, one facade.

    ``walls`` / ``plan_openings`` are the plan side's wall and opening cut
    lines (the projection bridge's representation -- either loader
    produces them; here they are pure data).  The CALLER decides which
    openings are candidates for THIS facade (the visibility question --
    which wall bands this facade sees across a stepped volume -- is
    ``facade_visibility``'s business, ⛔ not smuggled in here as a
    bbox-extreme shortcut).

    ``mirrored`` / ``local_x_positive`` are the caller's DECLARED drawing
    orientation, resolved fail-closed through the signed convention
    (``facade_convention``); this function ⛔ never guesses a direction,
    and an unresolved mirror flag is a loud input fault upstream.
    """
    _require_elevation_contract(elevation_doc)
    _require_lines(walls, kind="wall", what="walls")
    _require_lines(plan_openings, kind="opening", what="plan_openings")

    family = elevation_doc.get("facade_label")
    if family not in _FAMILIES:
        raise OpeningSynthesisError(
            "FACADE_FAMILY_UNKNOWN", {"facade_label": family}
        )
    axis = world_axis(family)
    sign = resolve_sign(
        family, mirrored=mirrored, local_x_positive=local_x_positive
    )

    # -- step 1 (T1): the anchor ------------------------------------------------
    skin = _skin_envelope(walls, across_axis=axis, family=family)
    # the chain's x=0 is the outer-skin end the SIGN points away from:
    # sign +1 => x=0 is the lo end, sign -1 => the hi end (the signed
    # convention's observer-left rule; measured on all four real facades).
    along_origin_u = skin.lo_u if sign > 0 else skin.hi_u

    # -- step 2 (T2 == T5's detector): the equality gate ------------------------
    chain_total_mm = _elevation_chain_total_mm(elevation_doc, family)
    # the gate IS the premise's detector: mismatch raises by name, so
    # reaching here means chain_total_u == the outer-skin span, exactly.
    span_u = span_equality_gate(
        chain_total_mm=chain_total_mm,
        skin_lo_u=skin.lo_u,
        skin_hi_u=skin.hi_u,
    )
    chain_total_u = span_u

    # -- step 3 (T3): pair by interval EQUALITY on the declared grid ------------
    # Both sides are bucketed by world interval FIRST, then reconciled:
    # an interval with exactly one opening on EACH side is one pairing;
    # anything else (one side empty = no counterpart, either side with
    # more than one = identity not decidable by this criterion) is
    # refused by name.  ⛔ No ordering, no proximity, no tie-breaking.
    plan_by_interval: dict[tuple[int, int], list[str]] = {}
    plan_ids_seen: set[str] = set()
    for opening in plan_openings:
        if opening.origin_id in plan_ids_seen:
            # uniqueness over the WHOLE input, ⛔ not per interval bucket:
            # the same id at two intervals is the same corruption
            raise OpeningSynthesisError(
                "PLAN_OPENING_ID_DUPLICATE",
                {"opening_id": opening.origin_id},
            )
        plan_ids_seen.add(opening.origin_id)
        lo_u = grid_units(
            opening.along_lo_m, what=f"plan opening {opening.origin_id} lo"
        )
        hi_u = grid_units(
            opening.along_hi_m, what=f"plan opening {opening.origin_id} hi"
        )
        if not lo_u < hi_u:
            raise OpeningSynthesisError(
                "PLAN_OPENING_SPAN_DEGENERATE",
                {"opening_id": opening.origin_id, "span_u": [lo_u, hi_u]},
            )
        plan_by_interval.setdefault((lo_u, hi_u), []).append(
            opening.origin_id
        )

    elevation_by_interval: dict[
        tuple[int, int], list[tuple[str, int, int]]
    ] = {}
    elevation_ids_seen: set[str] = set()
    for oid, x_lo, x_hi, z_lo, z_hi in _elevation_openings(elevation_doc):
        if oid in elevation_ids_seen:
            # whole-input uniqueness, same discipline as the plan side
            raise OpeningSynthesisError(
                "ELEVATION_OPENING_ID_DUPLICATE", {"opening_id": oid}
            )
        elevation_ids_seen.add(oid)
        lo_u = grid_units(x_lo, what=f"elevation opening {oid} x_lo")
        hi_u = grid_units(x_hi, what=f"elevation opening {oid} x_hi")
        # world = along_origin + sign * local  (facade_convention §6.3's one
        # formula, evaluated in the integer grid domain so no float ever
        # touches a comparison)
        world_lo = along_origin_u + sign * lo_u
        world_hi = along_origin_u + sign * hi_u
        interval = (min(world_lo, world_hi), max(world_lo, world_hi))
        elevation_by_interval.setdefault(interval, []).append(
            (
                oid,
                grid_units(z_lo, what=f"elevation opening {oid} z_lo"),
                grid_units(z_hi, what=f"elevation opening {oid} z_hi"),
            )
        )

    pairings: list[OpeningPairingV1] = []
    unmatched_plan: list[str] = []
    unmatched_elevation: list[str] = []
    same_interval_groups: list[tuple[str, ...]] = []
    for interval in sorted(set(plan_by_interval) | set(elevation_by_interval)):
        plans_here = plan_by_interval.get(interval, [])
        elevations_here = elevation_by_interval.get(interval, [])
        if len(plans_here) == 1 and len(elevations_here) == 1:
            oid, z_low_u, z_high_u = elevations_here[0]
            pairings.append(
                OpeningPairingV1(
                    plan_opening_id=plans_here[0],
                    elevation_opening_id=oid,
                    span_lo_u=interval[0],
                    span_hi_u=interval[1],
                    z_low_u=z_low_u,
                    z_high_u=z_high_u,
                )
            )
            continue
        # refuse the whole interval: some member has no counterpart, or
        # identity is not decidable (stacked same-interval openings) --
        # either way ⛔ never guessed onto a neighbour
        unmatched_plan.extend(plans_here)
        unmatched_elevation.extend(o for o, _, _ in elevations_here)
        if len(plans_here) + len(elevations_here) > 1:
            # only genuine ambiguity gets a group; a lone opening with no
            # counterpart is simply unmatched, not "ambiguous"
            same_interval_groups.append(
                tuple(sorted(plans_here + [o for o, _, _ in elevations_here]))
            )

    # -- T4-c: retire what this product actually redeemed (gate passed) ---------
    retired = redeemable_debt_ids(evidence_debts)

    return OpeningSynthesisV1(
        schema_version=SYNTHESIS_SCHEMA_VERSION,
        facade_family=family,
        world_axis=axis,
        sign=sign,
        along_origin_u=along_origin_u,
        chain_total_u=chain_total_u,
        skin_lo_u=skin.lo_u,
        skin_hi_u=skin.hi_u,
        premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
        pairings=tuple(
            sorted(pairings, key=lambda p: (p.span_lo_u, p.elevation_opening_id))
        ),
        unmatched_plan_opening_ids=tuple(sorted(unmatched_plan)),
        unmatched_elevation_opening_ids=tuple(sorted(unmatched_elevation)),
        same_interval_groups=tuple(same_interval_groups),
        retired_debt_ids=retired,
    )


__all__ = [
    "DECLARED_GRID_UNITS_PER_M",
    "DEBT_REDEMPTION_REGISTRY",
    "OpeningPairingV1",
    "OpeningSynthesisError",
    "OpeningSynthesisV1",
    "grid_units",
    "grid_units_from_mm",
    "redeemable_debt_ids",
    "span_equality_gate",
    "synthesize_openings",
]
