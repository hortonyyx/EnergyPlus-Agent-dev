"""B4 -- opening synthesis: cross-view identity pairing (dispatch 2026-09-03ag).

WHAT THIS FILE LOCKS
--------------------
The seven acceptance rules of the dispatch sheet, §四, as RULES ⛔ not as
transcripts of one run's readings:

1. the span gate is an EQUALITY, ⛔ not a threshold -- the module compares
   no float literal anywhere (AST lock), a 0.1 mm chain error is already
   a loud named failure, and on the four REAL sm25 facades the gate passes
   bit-exact while the DERIVED skin span reconciles against the facts
   layer's exterior ring (the dispatch's closure table, reproduced
   independently here, ⛔ not trusted from the orchestrator's probe);
2. the skin span takes EACH END's own wall thickness -- a fixture with
   four different edge thicknesses (0.37 / 0.30 / 0.24 / 0.20, ⛔ never
   all-240) closes, and the value a global-offset implementation would
   compute is proven WRONG by the same fixture;
3. pairing is by interval equality on the declared 0.1 mm grid: an
   interval one grid unit off is refused (never nearest-matched),
   same-interval stacks are refused as named groups (never ordered), and
   duplicate ids / off-grid values are loud;
4. the debt wiring is STRUCTURAL: deleting every "B4" word from a debt's
   description changes nothing (the cross-review's
   ``OWNER_TEXT_REMOVED=GREEN`` finding, reversed), and a description
   full of "B4" with an unregistered debt_id prefix wires NOTHING;
5. a debt is retired exactly when the gate passed for that product --
   proven end-to-end on B3's REAL bundle bytes;
6. the premise has a name and fails loudly: a one-bay elevation is
   rejected naming ``ELEVATION_CHAIN_SPANS_WHOLE_BUILDING`` and both
   readings;
7. (full-suite green + per-item closure -- the execution report's job.)

The real-data readings that are NOT locked: how many real openings pair
(the elevation's pixel-quantised intervals sit a few grid units off the
plan side today -- that is the reading side's precision, and locking it
red would pin the defect's existence, not a rule).  What IS locked on the
real corpus is the closure table, the sign/anchor readings, and the
completeness invariant (paired + refused == every opening, both sides).
"""
from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

import src.agent.correction.opening_synthesis as osm
from src.agent.correction.evidence_adapters import (
    ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
    adapt_as_drawn_elevation,
)
from src.agent.correction.evidence_contract import (
    ArtifactPointerV1,
    EvidenceDebtV1,
)
from src.agent.correction.opening_synthesis import (
    DEBT_REDEMPTION_REGISTRY,
    OpeningSynthesisError,
    grid_units,
    redeemable_debt_ids,
    span_equality_gate,
    synthesize_openings,
)
from src.agent.correction.projection_bridge import CutLineV1
from src.agent.reading.vector_contract import (
    CONTRACT_AS_DRAWN_ELEVATION_V0,
    classify_vector_json,
)

_PRODUCTS = Path(
    "AI_agent/logs/experiments/2026-08-23_as_drawn_reading_prototype/out"
)
_FACTS = Path(
    "case_tests/test_baseline/gt_staging/sm25-L_anchor/facts/as_measured.json"
)
_FACADES = ("east", "west", "north", "south")


# ── fixtures ────────────────────────────────────────────────────────────────── #
def _real_elevation(facade: str) -> dict:
    p = _PRODUCTS / f"sm25_{facade}_as_drawn.json"
    # ⛔ never skip on a missing fixture -- that is a red, not a pass
    assert p.is_file(), f"tracked elevation product missing: {p}"
    return json.loads(p.read_bytes())


def _facts_lines() -> tuple[tuple[CutLineV1, ...], int]:
    """Every wall/opening cut line of BOTH storeys, from the facts layer."""
    from src.agent.correction.projection_bridge import (
        cut_lines_from_as_measured_view,
    )

    facts = json.loads(_FACTS.read_bytes())
    upm = facts["units_per_metre"]
    lines: list[CutLineV1] = []
    for view in facts["views"]:
        view_lines, _ = cut_lines_from_as_measured_view(
            view, units_per_metre=upm
        )
        lines.extend(view_lines)
    return tuple(lines), upm


def _facts_exterior_bbox_u() -> dict[str, tuple[int, int]]:
    """The facts layer's exterior ring bbox per axis, in grid units --
    the INDEPENDENT ruler the derived skin span must reconcile against
    (the dispatch's closure table, first column)."""
    facts = json.loads(_FACTS.read_bytes())
    upm = facts["units_per_metre"]
    out: dict[str, tuple[int, int]] = {}
    for axis in ("x", "y"):
        lo = hi = None
        for view in facts["views"]:
            rings = view["footprint"]["rings"]
            exterior = [r for r in rings if r["kind"] == "exterior"][0]
            coords = exterior["points"]
            index = 0 if axis == "x" else 1
            values = [pt[index] for pt in coords]
            v_lo, v_hi = min(values), max(values)
            lo = v_lo if lo is None else min(lo, v_lo)
            hi = v_hi if hi is None else max(hi, v_hi)
        out[axis] = (grid_units(lo / upm, what=f"ring {axis} lo"),
                     grid_units(hi / upm, what=f"ring {axis} hi"))
    return out


def _walls(
    *,
    width_m: float = 25.0,
    height_m: float = 20.0,
    west_t: float = 0.24,
    east_t: float = 0.24,
    south_t: float = 0.24,
    north_t: float = 0.24,
) -> tuple[CutLineV1, ...]:
    """A four-wall box whose four edge thicknesses are independently
    settable -- the fixture for acceptance #2 (⛔ never all-240)."""
    return (
        CutLineV1(axis="x", pos_m=south_t / 2, along_lo_m=0.0,
                  along_hi_m=width_m, half_thickness_m=south_t / 2,
                  kind="wall", origin_id="wall_south"),
        CutLineV1(axis="x", pos_m=height_m - north_t / 2, along_lo_m=0.0,
                  along_hi_m=width_m, half_thickness_m=north_t / 2,
                  kind="wall", origin_id="wall_north"),
        CutLineV1(axis="y", pos_m=west_t / 2, along_lo_m=0.0,
                  along_hi_m=height_m, half_thickness_m=west_t / 2,
                  kind="wall", origin_id="wall_west"),
        CutLineV1(axis="y", pos_m=width_m - east_t / 2, along_lo_m=0.0,
                  along_hi_m=height_m, half_thickness_m=east_t / 2,
                  kind="wall", origin_id="wall_east"),
    )


def _plan_opening(oid: str, lo_m: float, hi_m: float) -> CutLineV1:
    return CutLineV1(axis="x", pos_m=0.12, along_lo_m=lo_m, along_hi_m=hi_m,
                     half_thickness_m=0.12, kind="opening", origin_id=oid)


def _elevation_doc(
    *, family: str, chain_total_mm: float, openings: tuple = ()
) -> dict:
    """A minimal ``as_drawn_elevation_v0`` product for any chain total.

    Everything the B4 code reads is derived from the arguments (chain
    total, opening x/z ranges); the rest is the minimum the registered
    detector demands (schema declaration + openings/structure_lines
    keys).  No sm25 reading appears anywhere in it.
    """
    nodes = [
        {
            "id": f"O{k:02d}",
            "x_range_m": [float(xr[0]), float(xr[1])],
            "z_range_m": [float(zr[0]), float(zr[1])],
            "width_m": float(xr[1]) - float(xr[0]),
            "height_m": float(zr[1]) - float(zr[0]),
        }
        for k, (xr, zr) in enumerate(openings)
    ]
    return {
        "schema": "as_drawn_elevation_v0",
        "facade_label": family,
        "image_label": f"{family} synthetic",
        "calibration": {
            "x": {
                "values_mm": [chain_total_mm],
                "cum_mm": [0.0, chain_total_mm],
                "overall_mm": chain_total_mm,
                "matched_px": [0.0, chain_total_mm / 10.0],
                "origin_px": 0.0,
                "mm_per_px": 10.0,
                "residual_px": [0.0, 0.0],
                "rmse_px": 0.0,
                "max_abs_residual_px": 0.0,
                "chain_closure_mm": 0.0,
            },
            "z": {
                "values_mm": [3000.0],
                "cum_mm": [0.0, 3000.0],
                "overall_mm": 3000.0,
                "matched_px": [0.0, 300.0],
                "origin_px": 0.0,
                "mm_per_px": 10.0,
                "residual_px": [0.0, 0.0],
                "rmse_px": 0.0,
                "max_abs_residual_px": 0.0,
                "chain_closure_mm": 0.0,
            },
        },
        "structure_lines": [
            {
                "id": "L00", "axis": "row", "constant_quantity": "z",
                "pos_px": 0.0, "pos_m": 0.0, "cols_px": [0, 1],
                "runs_px": [[0.0, 1.0]], "runs_m": [[0.0, 0.001]],
                "gaps": [], "covered_px": 1, "span_ratio": 1.0,
            },
            {
                "id": "L01", "axis": "row", "constant_quantity": "z",
                "pos_px": 300.0, "pos_m": 3.0, "cols_px": [300, 301],
                "runs_px": [[0.0, 1.0]], "runs_m": [[0.0, 0.001]],
                "gaps": [], "covered_px": 1, "span_ratio": 1.0,
            },
        ],
        "openings": nodes,
    }


def _source(input_id: str) -> osm.ElevationSourceIdentity:
    """A caller-declared elevation source identity (synthetic ids; the
    REAL-bytes tests below use identities extracted from B3's own
    bundles)."""
    return osm.ElevationSourceIdentity(
        input_id=input_id,
        source_contract_id=CONTRACT_AS_DRAWN_ELEVATION_V0,
        source_output_sha256="0" * 64,
    )


#: (dispatch 2026-09-04e T3) the registry key the span debt is wired by:
#: the debt's ``obligation`` value, ⛔ never its ``debt_id`` prefix.
SPAN_OBLIGATION = "elevation_chain_spans_whole_building"


def _south_executed() -> osm.ExecutedRedemption:
    """The redemption a healthy South run executes: the span registry row,
    against the South source instance."""
    return osm.ExecutedRedemption(
        obligation=SPAN_OBLIGATION,
        row=DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION],
        source=_source("input_south"),
    )


def _debt(
    debt_id: str,
    description: str,
    *,
    source: osm.ElevationSourceIdentity | None = None,
    obligation: str | None = SPAN_OBLIGATION,
) -> EvidenceDebtV1:
    """A span-shaped debt.  With ``source`` it carries B3's REAL shape:
    one ``affected_ref`` naming exactly that source instance (B3 points it
    at ``/calibration`` -- the very node the gate reads).  ⛔ A debt
    without refs is the shape rework 1 refuses to retire: it names no
    source, so no run may claim it.  ``obligation`` defaults to the span
    obligation; pass ``None`` for the converse shape (a debt with no
    downstream obligation at all)."""
    refs: tuple[ArtifactPointerV1, ...] = ()
    if source is not None:
        refs = (
            ArtifactPointerV1(
                input_id=source.input_id,
                source_contract_id=source.source_contract_id,
                source_output_sha256=source.source_output_sha256,
                json_pointer="/calibration",
            ),
        )
    return EvidenceDebtV1(
        debt_id=debt_id,
        kind="other_known_missing",
        affected_refs=refs,
        description=description,
        obligation=obligation,
    )


SPAN_DEBT_ID = "debt_elevation_chain_span_unchecked_input_south"


# ── acceptance #1: the gate is an equality, ⛔ not a threshold ───────────────── #
def test_gate_passes_bit_exact_on_the_real_four_facades():
    """The dispatch's closure table, reproduced on THIS tree's bytes: the
    derived skin span reconciles against the facts layer's exterior ring
    (an independent ruler), and the chain total equals it bit-exact on
    all four facades."""
    lines, _ = _facts_lines()
    walls = [l for l in lines if l.kind == "wall"]
    ring_bbox = _facts_exterior_bbox_u()
    for facade in _FACADES:
        doc = _real_elevation(facade)
        axis = "y" if doc["facade_label"] in ("East", "West") else "x"
        openings = [l for l in lines if l.kind == "opening" and l.axis == axis]
        product = synthesize_openings(
            elevation_doc=doc, walls=walls, plan_openings=openings,
            mirrored=False, local_x_positive="image_left_to_right",
        )
        assert product.world_axis == axis
        # the signed convention's readings, locked: observer-left rule
        expect_sign = -1 if doc["facade_label"] in ("North", "West") else 1
        assert product.sign == expect_sign
        # the anchor: x=0 maps to the skin end the sign points away from
        lo, hi = ring_bbox[axis]
        assert (product.skin_lo_u, product.skin_hi_u) == (lo, hi)
        assert product.along_origin_u == (lo if product.sign > 0 else hi)
        # the equality itself, bit-exact, per facade
        assert product.chain_total_u == hi - lo == (
            product.skin_hi_u - product.skin_lo_u
        )
        # completeness: every input opening is either paired or refused
        assert len(product.pairings) + len(
            product.unmatched_elevation_opening_ids
        ) == len(doc["openings"])
        assert len(product.pairings) + len(
            product.unmatched_plan_opening_ids
        ) == len(openings)


def test_gate_is_zero_threshold_one_grid_unit_already_fails():
    walls = _walls()  # all-240 box: x span = 24.760 + 0.120 + 0.120 = 25.000
    chain_mm = 25_000.0
    product = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=chain_mm),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
    )
    assert product.chain_total_u == 250_000
    with pytest.raises(OpeningSynthesisError) as caught:
        span_equality_gate(
            chain_total_mm=chain_mm - 0.1,  # ⭐ 0.1 mm -- the grid itself
            skin_lo_u=product.skin_lo_u,
            skin_hi_u=product.skin_hi_u,
        )
    assert caught.value.code == "ELEVATION_CHAIN_SPAN_MISMATCH"
    # chain_minus_skin in grid units: the chain is one unit SHORT
    assert caught.value.context["difference_grid_units"] == -1


def test_module_compares_no_float_literals():
    """The equality gate has no tolerance because NO comparison in the
    module involves a float literal (an ``abs(a - b) < 0.001`` shape is
    exactly what this AST walk catches).  Integers, names and calls only."""
    tree = ast.parse(inspect.getsource(osm))
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for side in (node.left, *node.comparators):
                if isinstance(side, ast.Constant) and isinstance(
                    side.value, float
                ):
                    pytest.fail(
                        f"float literal in a comparison at line "
                        f"{node.lineno}: {ast.unparse(node)}"
                    )


# ── acceptance #2: each edge takes ITS OWN wall's thickness ─────────────────── #
def test_each_edge_takes_its_own_wall_thickness():
    """Four DIFFERENT edge thicknesses (0.37 / 0.30 / 0.24 / 0.20 -- ⛔
    never all-240): both facades' spans close with each end contributing
    its own t/2, and the value a global-offset implementation would
    compute is proven wrong by the same fixture."""
    walls = _walls(west_t=0.37, east_t=0.30, south_t=0.24, north_t=0.20)
    # x span: midline bbox 24.665 + west's own 0.185 + east's own 0.150
    # (integer-mm arithmetic on purpose -- the expectations are derived
    # from the fixture data independently of any float path)
    x_span_mm = float(25_000 - 185 - 150 + 185 + 150)
    # y span: midline bbox 19.660 + south's own 0.120 + north's own 0.100
    y_span_mm = float(20_000 - 120 - 100 + 120 + 100)
    assert (x_span_mm, y_span_mm) == (25_000.0, 20_000.0)

    south = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="South", chain_total_mm=x_span_mm
        ),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
    )
    assert (south.skin_lo_u, south.skin_hi_u) == (0, 250_000)
    assert south.chain_total_u == 250_000

    east = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="East", chain_total_mm=y_span_mm
        ),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
    )
    assert (east.skin_lo_u, east.skin_hi_u) == (0, 200_000)
    assert east.chain_total_u == 200_000

    # ⭐ the mutation: a GLOBAL-offset implementation would compute the
    # x span as midline_bbox + 2 * (ONE wall's half thickness); both the
    # west-half and the east-half variants are wrong on this fixture, so
    # the gate must fail loudly on them (integer mm, on the grid).
    for global_half_mm in (185, 150):
        wrong_chain = float(25_000 - 185 - 150 + 2 * global_half_mm)
        with pytest.raises(OpeningSynthesisError) as caught:
            synthesize_openings(
                elevation_doc=_elevation_doc(
                    family="South", chain_total_mm=wrong_chain
                ),
                walls=walls, plan_openings=(), mirrored=False,
                local_x_positive="image_left_to_right",
            )
        assert caught.value.code == "ELEVATION_CHAIN_SPAN_MISMATCH"


def test_end_wall_thickness_disagreement_is_loud():
    """Two walls sharing the midline extreme but disagreeing on thickness
    is a contradiction in the data, ⛔ never a silently chosen one."""
    walls = _walls(west_t=0.30, east_t=0.24) + (
        CutLineV1(axis="y", pos_m=0.15, along_lo_m=0.0, along_hi_m=20.0,
                  half_thickness_m=0.24 / 2, kind="wall",
                  origin_id="wall_west_b_thinner"),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=walls, plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "SKIN_END_WALL_THICKNESS_AMBIGUOUS"
    assert caught.value.context["end"] == "lo"


def test_wall_poking_past_the_end_wall_is_loud():
    """A wall whose own skin reaches past the midline-bbox end wall's
    breaks 'skin = midline bbox + each end's own t/2' for this input --
    the premise of the ARITHMETIC itself, checked, ⛔ not assumed.
    (The poker's MIDLINE sits inside the bbox -- pos 0.13 > the end
    wall's 0.12 -- so it is not the end wall; only its fat skin reaches
    past: pos 0.13 - half 0.20 = -0.07 < the end wall's skin 0.0.)"""
    walls = _walls() + (
        CutLineV1(axis="y", pos_m=0.13, along_lo_m=0.0, along_hi_m=20.0,
                  half_thickness_m=0.20, kind="wall",
                  origin_id="wall_poking_west"),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=walls, plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "SKIN_NOT_FROM_END_WALLS"


# ── acceptance #3: pairing by interval equality, ⛔ no heuristic ──────────────── #
def test_paired_by_exact_interval_equality_with_z_from_elevation():
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="South", chain_total_mm=25_000.0,
            openings=(((10.0, 11.8), (0.9, 2.6)),),
        ),
        walls=walls,
        plan_openings=(_plan_opening("win_a", 10.0, 11.8),),
        mirrored=False, local_x_positive="image_left_to_right",
    )
    assert len(product.pairings) == 1
    pair = product.pairings[0]
    assert pair.plan_opening_id == "win_a"
    assert pair.elevation_opening_id == "O00"
    assert (pair.span_lo_u, pair.span_hi_u) == (100_000, 118_000)
    # the z travels from the elevation side -- the whole point of B4
    assert (pair.z_low_u, pair.z_high_u) == (9_000, 26_000)


def test_mirrored_facade_anchors_from_the_far_end():
    """West: sign -1 under the signed convention, so the chain's x=0 is
    the y-MAX skin end -- the real West facade's measured behaviour, on
    the synthetic fixture."""
    walls = _walls()  # y span [0, 20]
    # local [4.66, 5.46] under sign -1 from origin 20 -> world [14.54, 15.34]
    product = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="West", chain_total_mm=20_000.0,
            openings=(((4.66, 5.46), (0.9, 2.6)),),
        ),
        walls=walls,
        plan_openings=(
            CutLineV1(axis="y", pos_m=0.12, along_lo_m=14.54,
                      along_hi_m=15.34, half_thickness_m=0.12,
                      kind="opening", origin_id="door_west"),
        ),
        mirrored=False, local_x_positive="image_left_to_right",
    )
    assert product.sign == -1
    assert product.along_origin_u == 200_000
    assert len(product.pairings) == 1
    assert (product.pairings[0].span_lo_u, product.pairings[0].span_hi_u) == (
        145_400, 153_400,
    )


def test_one_grid_unit_off_is_refused_not_nearest_matched():
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="South", chain_total_mm=25_000.0,
            openings=(((10.0001, 11.8), (0.9, 2.6)),),  # 1 grid unit off
        ),
        walls=walls,
        plan_openings=(_plan_opening("win_a", 10.0, 11.8),),
        mirrored=False, local_x_positive="image_left_to_right",
    )
    assert product.pairings == ()
    assert product.unmatched_elevation_opening_ids == ("O00",)
    assert product.unmatched_plan_opening_ids == ("win_a",)


def test_same_interval_stack_is_refused_as_a_named_group():
    """Two elevation openings with the SAME world interval (stacked
    storeys) and one plan opening: interval equality cannot decide 1:1,
    so the whole interval is refused and named -- ⛔ never ordered, never
    nearest, never first-wins."""
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="South", chain_total_mm=25_000.0,
            openings=(((10.0, 11.8), (0.9, 2.6)),
                      ((10.0, 11.8), (4.5, 6.2))),
        ),
        walls=walls,
        plan_openings=(_plan_opening("win_a", 10.0, 11.8),),
        mirrored=False, local_x_positive="image_left_to_right",
    )
    assert product.pairings == ()
    assert product.unmatched_elevation_opening_ids == ("O00", "O01")
    assert product.unmatched_plan_opening_ids == ("win_a",)
    assert product.same_interval_groups == (("O00", "O01", "win_a"),)


def test_two_plan_openings_near_one_elevation_opening_pair_only_the_equal():
    """One elevation interval, one EQUAL plan interval and one 1-unit-off
    plan interval: only the equal one pairs -- the near one is refused,
    ⛔ never adopted by proximity."""
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(
            family="South", chain_total_mm=25_000.0,
            openings=(((10.0, 11.8), (0.9, 2.6)),),
        ),
        walls=walls,
        plan_openings=(_plan_opening("win_off", 10.0, 11.8001),
                       _plan_opening("win_equal", 10.0, 11.8)),
        mirrored=False, local_x_positive="image_left_to_right",
    )
    assert [p.plan_opening_id for p in product.pairings] == ["win_equal"]
    assert product.unmatched_plan_opening_ids == ("win_off",)


def test_duplicate_and_off_grid_inputs_are_loud():
    walls = _walls()
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=walls,
            plan_openings=(_plan_opening("win_a", 10.0, 11.8),
                           _plan_opening("win_a", 12.0, 13.0)),
            mirrored=False, local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "PLAN_OPENING_ID_DUPLICATE"

    doc = _elevation_doc(
        family="South", chain_total_mm=25_000.0,
        openings=(((10.0, 11.8), (0.9, 2.6)),
                  ((12.0, 13.0), (0.9, 2.6))),
    )
    # the factory auto-numbers ids; forge the duplicate by hand
    doc["openings"][1]["id"] = doc["openings"][0]["id"]
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=doc, walls=walls, plan_openings=(),
            mirrored=False, local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "ELEVATION_OPENING_ID_DUPLICATE"

    doc_off = _elevation_doc(
        family="South", chain_total_mm=25_000.0,
        openings=(((10.000_05, 11.8), (0.9, 2.6)),),  # half a grid unit
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=doc_off, walls=walls, plan_openings=(),
            mirrored=False, local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "VALUE_OFF_DECLARED_GRID"


def test_input_contracts_are_checked_not_assumed():
    walls = _walls()
    not_elevation = {"schema": "as_drawn_plan_v2", "openings": [],
                     "structure_lines": []}
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=not_elevation, walls=walls, plan_openings=(),
            mirrored=False, local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "ELEVATION_CONTRACT_MISMATCH"

    synthetic_family = _elevation_doc(family="Synthetic", chain_total_mm=25_000.0)
    assert (
        classify_vector_json(synthetic_family).contract_id
        == CONTRACT_AS_DRAWN_ELEVATION_V0
    )  # it IS a real elevation product by bytes ...
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(  # ... but not one of the four families
            elevation_doc=synthetic_family, walls=walls, plan_openings=(),
            mirrored=False, local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "FACADE_FAMILY_UNKNOWN"

    with pytest.raises(TypeError):
        # the direction inputs are fail-closed upstream: an unresolved
        # mirror flag must never be guessed to False here
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=walls, plan_openings=(),
            mirrored="unknown",  # type: ignore[arg-type]
            local_x_positive="image_left_to_right",
        )


# ── acceptance #6: the premise has a name and fails loudly ───────────────────── #
def test_one_bay_elevation_fails_naming_the_premise():
    """A one-bay (partial) elevation: the chain spans half the building,
    the premise 'the chain spans the whole building' is FALSE, and the
    gate says so by name with both readings -- ⛔ never silently treated
    as whole-building."""
    walls = _walls()
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(
                family="South", chain_total_mm=12_500.0  # one bay only
            ),
            walls=walls, plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "ELEVATION_CHAIN_SPAN_MISMATCH"
    assert (
        caught.value.context["premise"] == ELEVATION_CHAIN_SPANS_WHOLE_BUILDING
    )
    assert caught.value.context["chain_total_mm"] == 12_500.0
    assert caught.value.context["skin_span_mm"] == 25_000.0


def test_healthy_product_carries_the_premise_by_name():
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
    )
    assert product.premise == ELEVATION_CHAIN_SPANS_WHOLE_BUILDING


# ── acceptance #4/#5: the debt wiring is structural; retirement is real ─────── #
def test_debt_wiring_survives_removal_of_every_b4_word():
    """The cross-review measured ``OWNER_TEXT_REMOVED=GREEN`` as a
    DEFECT of B3's shape (the wiring locked a word).  Here the reverse
    is locked: a debt whose description never says "B4" at all is still
    wired, redeemed and retired -- because the wiring key is the debt's
    ``obligation`` field (dispatch 2026-09-04e T3) plus its
    ``affected_refs`` naming this run's source, ⛔ never the free text
    and ⛔ never the ``debt_id`` prefix."""
    debt = _debt(
        SPAN_DEBT_ID,
        description="span equality unverified until the plan side sees it",
        source=_source("input_south"),
    )
    assert "B4" not in debt.description
    assert redeemable_debt_ids(
        [debt], executed=_south_executed()
    ) == (SPAN_DEBT_ID,)

    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
        evidence_debts=[debt],
        elevation_source=_source("input_south"),
    )
    assert product.retired_debt_ids == (SPAN_DEBT_ID,)


def test_description_full_of_b4_wires_nothing():
    """The converse tooth: free text naming "B4" repeatedly must not
    wire a debt that carries no obligation -- otherwise the wiring would
    be textual again, just inverted.  (Dispatch 2026-09-04e T3: the
    debt_id prefix likewise wires NOTHING -- this impostor keeps the
    historical span-shaped ``debt_id`` and drops only the ``obligation``.)"""
    impostor = _debt(
        "debt_some_other_kind_input_1",
        description="Owner: B4. B4 must handle this. Trust B4.",
        source=_source("input_south"),
        obligation=None,
    )
    assert redeemable_debt_ids(
        [impostor], executed=_south_executed()
    ) == ()
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
        evidence_debts=[impostor],
        elevation_source=_source("input_south"),
    )
    assert product.retired_debt_ids == ()


def test_registry_rows_are_wiring_not_decoration(monkeypatch):
    """⭐ rework 1 (cross-review B-1): the registry's gate column is
    LOAD-BEARING.  The cross-review pointed the span obligation at
    ``grid_units`` -- a real, existing, callable of this module, signature
    and semantics both foreign -- and the old teeth waved it through while
    the debt was still retired (``WRONG_HANDLER_ACCEPTED= grid_units``).
    The teeth below refuse exactly that shape, at import time AND at the
    real call site, and a wrong handler means NO product, so no
    retirement.

    ⭐ dispatch 2026-09-04e T3/#6: the registry keys are now the
    ``obligation`` values, and ALL of rework 1's import-time teeth
    (HANDLER_MISSING / PREFIX_AMBIGUOUS) plus the retirement-side
    TYPE_AMBIGUOUS are re-triggered in the re-keyed world below -- each
    mutation is a shape the CURRENT wiring could actually take, ⛔ not a
    transcript of the old prefix world."""
    # the healthy shape: every row carries this module's named gate object
    # and a premise, and the span row's premise IS the product's premise
    for key, row in DEBT_REDEMPTION_REGISTRY.items():
        assert isinstance(row, osm.DebtRedemption), key
        assert callable(row.gate), f"{key}: gate missing"
        assert getattr(osm, row.gate.__name__, None) is row.gate, (
            f"{key}: gate is not a named function of this module"
        )
    assert DEBT_REDEMPTION_REGISTRY.keys() == {SPAN_OBLIGATION}
    assert (
        DEBT_REDEMPTION_REGISTRY[SPAN_OBLIGATION].premise
        == ELEVATION_CHAIN_SPANS_WHOLE_BUILDING
    )

    # (1) import-time teeth: the cross-review's exact mutation -- a
    # real-but-wrong existing callable -- is loud, ⛔ not accepted
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        SPAN_OBLIGATION,
        osm.DebtRedemption(
            premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING, gate=osm.grid_units
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_GATE_SIGNATURE_MISMATCH"
    assert caught.value.context["gate"] == "grid_units"
    monkeypatch.undo()

    # (1b) a lambda carries no module name: not module wiring
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        SPAN_OBLIGATION,
        osm.DebtRedemption(
            premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
            gate=lambda **kw: 0,
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_GATE_NOT_MODULE_FUNCTION"
    monkeypatch.undo()

    # (1c) ⭐ acceptance #6, tooth 1/3 re-keyed: a non-callable gate is
    # still the old loud refusal (the tooth is about the ROW's gate
    # column -- the key rename never touched it, and the re-trigger below
    # proves it bites under the obligation keys)
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        SPAN_OBLIGATION,
        osm.DebtRedemption(
            premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING, gate=None
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_HANDLER_MISSING"
    monkeypatch.undo()

    # (1d) two rows for one premise: the premise is the execution-side
    # lookup key, so two gates for it is ambiguous wiring (the twin key
    # deliberately shares NO prefix with the span key)
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        "elevation_chain_height_spans_building",
        osm.DebtRedemption(
            premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
            gate=span_equality_gate,
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_PREMISE_AMBIGUOUS"
    monkeypatch.undo()

    # (2) the RUNTIME shape of the same mutation (import teeth already
    # ran): the synthesis itself must fail loudly and retire NOTHING --
    # the cross-review's RETIRED= line, reversed
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        SPAN_OBLIGATION,
        osm.DebtRedemption(
            premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING, gate=osm.grid_units
        ),
    )
    debt = _debt(SPAN_DEBT_ID, description="wired by obligation, wrongly")
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=_walls(), plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
            evidence_debts=[debt],
        )
    assert caught.value.code == "DEBT_GATE_CALL_FAILED"
    assert caught.value.context["gate"] == "grid_units"
    monkeypatch.undo()

    # the control: healthy registry, same inputs -- a product exists and
    # the retirement works (the refusal above was the wiring's, ⛔ not the
    # input's)
    product = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
        walls=_walls(), plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
        evidence_debts=[_debt(SPAN_DEBT_ID, "wired", source=_source("input_south"))],
        elevation_source=_source("input_south"),
    )
    assert product.retired_debt_ids == (SPAN_DEBT_ID,)

    # (3) delete the row entirely: the premise the product promises is
    # unwired -- loud, ⛔ never a silent skip of the gate
    monkeypatch.delitem(DEBT_REDEMPTION_REGISTRY, SPAN_OBLIGATION)
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=_walls(), plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
        )
    assert caught.value.code == "PREMISE_GATE_UNWIRED"
    monkeypatch.undo()

    # (4) ⭐ acceptance #6, tooth 2/3 re-keyed: two obligation keys where
    # one is a PREFIX of the other is still ambiguous wiring -- the tooth
    # is a structural property of the KEY SPACE (it guards the next
    # enum value someone mints from reading as two rows), ⛔ not a
    # leftover of the debt_id world
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        "elevation_chain_spans",
        osm.DebtRedemption(
            premise="some other premise", gate=span_equality_gate
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_PREFIX_AMBIGUOUS"
    assert caught.value.context == {"key_a": SPAN_OBLIGATION, "key_b": "elevation_chain_spans"}
    monkeypatch.undo()

    # ⭐ acceptance #6, tooth 3/3 re-keyed: TYPE_AMBIGUOUS seen from the
    # debt side.  The old trigger (one debt_id matching two prefixes) is
    # STRUCTURALLY DEAD under exact-key matching -- a dict cannot hold a
    # key twice -- which is exactly what T3 bought.  The ambiguity that
    # CAN still happen: two rows (different keys) CLAIMING the same
    # premise, so which gate redeems the debt is undecided.  The runtime
    # tooth refuses it loudly; the import-time PREMISE_AMBIGUOUS tooth
    # (1d) refuses the same table earlier.
    both = _debt(
        "debt_elevation_chain_span_unchecked_a", description="",
        source=_source("input_south"),
    )
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        "elevation_chain_height_spans_building",
        osm.DebtRedemption(
            premise=ELEVATION_CHAIN_SPANS_WHOLE_BUILDING,
            gate=span_equality_gate,
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        redeemable_debt_ids([both], executed=_south_executed())
    assert caught.value.code == "DEBT_TYPE_AMBIGUOUS"
    assert caught.value.context["claimant_keys"] == [
        "elevation_chain_height_spans_building", SPAN_OBLIGATION,
    ]
    monkeypatch.undo()

    # (5) ⭐ dispatch T4 import tooth, direction A: a registry key OUTSIDE
    # the DebtObligationV1 domain is dead wiring -- no real debt can ever
    # carry it (the schema refuses the value), loud at import
    monkeypatch.setitem(
        DEBT_REDEMPTION_REGISTRY,
        "obligation_nobody_can_mint",
        osm.DebtRedemption(
            premise="some other premise", gate=span_equality_gate
        ),
    )
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_KEY_NOT_OBLIGATION"
    monkeypatch.undo()

    # (6) ⭐ dispatch T4 import tooth, direction B: a DebtObligationV1
    # value with NO registry row is a mintable promise nobody redeems --
    # loud at import (the structural form of "⛔ no slots for values
    # nobody redeems").  The empty-key check must pass first (no key
    # outside the domain), so this trigger deletes the span row and adds
    # NOTHING -- the uncovered domain value is the only defect left.
    monkeypatch.delitem(DEBT_REDEMPTION_REGISTRY, SPAN_OBLIGATION)
    with pytest.raises(OpeningSynthesisError) as caught:
        osm._assert_registry_well_formed()
    assert caught.value.code == "DEBT_REGISTRY_OBLIGATION_UNCOVERED"
    assert caught.value.context["obligation"] == SPAN_OBLIGATION
    monkeypatch.undo()


def test_b3s_real_span_debt_is_redeemed_on_real_bytes():
    """End-to-end on B3's real output: adapt the REAL East facade bytes
    (which mint the span debt with "Owner: B4." in its description),
    REWRITE that description to remove every "B4" word, and the debt is
    still recognised, redeemed and retired -- the structural wiring,
    exercised on the real product.  Rework 1: the retirement also needs
    the caller to declare WHICH source instance ran, taken here from the
    bundle's own artifact metadata (⭐ the identity is not re-typed by
    hand -- it is what B3 froze)."""
    raw = (_PRODUCTS / "sm25_east_as_drawn.json").read_bytes()
    artifact = adapt_as_drawn_elevation(
        raw, input_id="input_east", facade_ref="east"
    )
    span_debts = [
        d for d in artifact.bundle.evidence_debts
        if d.obligation == SPAN_OBLIGATION
    ]
    assert len(span_debts) == 1
    original = span_debts[0]
    assert "B4" in original.description  # the B3 shape, for contrast
    assert original.affected_refs  # B3's real debt names its source

    scrubbed = original.model_copy(
        update={"description": "span equality now checked by the plan side"}
    )
    assert "B4" not in scrubbed.description

    lines, _ = _facts_lines()
    walls = [l for l in lines if l.kind == "wall"]
    meta = artifact.bundle.source_artifacts[0]
    product = synthesize_openings(
        elevation_doc=json.loads(raw), walls=walls,
        plan_openings=[l for l in lines
                       if l.kind == "opening" and l.axis == "y"],
        mirrored=False, local_x_positive="image_left_to_right",
        evidence_debts=[scrubbed],
        elevation_source=osm.ElevationSourceIdentity(
            input_id=meta.input_id,
            source_contract_id=meta.source_contract_id,
            source_output_sha256=meta.source_output_sha256,
        ),
    )
    assert product.retired_debt_ids == (original.debt_id,)


def test_retirement_requires_the_gate_to_have_passed():
    """A debt that failed the gate is NOT retired: with the chain off by
    one bay the synthesis raises, so no product exists to carry the
    retirement -- the obligation stays exactly as open as before."""
    debt = _debt(SPAN_DEBT_ID, description="unchanged",
                 source=_source("input_south"))
    walls = _walls()
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(
                family="South", chain_total_mm=12_500.0
            ),
            walls=walls, plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
            evidence_debts=[debt],
            elevation_source=_source("input_south"),
        )
    assert caught.value.code == "ELEVATION_CHAIN_SPAN_MISMATCH"
    # and the debt itself is untouched by the refusal: a later healthy
    # run of the same gate, against the source it names, still redeems it
    assert redeemable_debt_ids(
        [debt], executed=_south_executed()
    ) == (SPAN_DEBT_ID,)


def test_retirement_binds_to_the_source_instance_real_bytes():
    """⭐ rework 1's second lock (cross-review B-2), built verbatim on the
    cross-review's counterexample shape -- B3's REAL bytes, ⛔ not a
    synthetic same-prefix-different-id pair:

    the cross-review adapted real East/West bytes into two LEGITIMATE
    debts, ran only South's gate, and measured

        CURRENT_FACADE= South
        RETIRED= ('debt_..._input_east', 'debt_..._input_west')

    South passing proves nothing about East/West.  Here the same three
    real debts (one per facade, each minted by B3 from that facade's own
    frozen bytes) go into one South run, and only South's own debt may
    retire."""
    lines, _ = _facts_lines()
    walls = [l for l in lines if l.kind == "wall"]

    debts: dict[str, EvidenceDebtV1] = {}
    identities: dict[str, osm.ElevationSourceIdentity] = {}
    for facade in ("east", "west", "south"):
        raw = (_PRODUCTS / f"sm25_{facade}_as_drawn.json").read_bytes()
        artifact = adapt_as_drawn_elevation(
            raw, input_id=f"input_{facade}", facade_ref=facade
        )
        span_debts = [
            d for d in artifact.bundle.evidence_debts
            if d.obligation == SPAN_OBLIGATION
        ]
        assert len(span_debts) == 1, facade
        debts[facade] = span_debts[0]
        meta = artifact.bundle.source_artifacts[0]
        identities[facade] = osm.ElevationSourceIdentity(
            input_id=meta.input_id,
            source_contract_id=meta.source_contract_id,
            source_output_sha256=meta.source_output_sha256,
        )
        # B3's real mint: the debt names exactly ITS OWN source
        assert debts[facade].affected_refs[0].input_id == f"input_{facade}"

    south_debt_id = debts["south"].debt_id
    east_debt_id = debts["east"].debt_id
    west_debt_id = debts["west"].debt_id
    assert len({south_debt_id, east_debt_id, west_debt_id}) == 3

    # the South run: all three REAL debts travel in, the source identity
    # declared is South's own -- and ONLY South's debt retires
    south_raw = (_PRODUCTS / "sm25_south_as_drawn.json").read_bytes()
    product = synthesize_openings(
        elevation_doc=json.loads(south_raw), walls=walls,
        plan_openings=[l for l in lines
                       if l.kind == "opening" and l.axis == "x"],
        mirrored=False, local_x_positive="image_left_to_right",
        evidence_debts=[debts["east"], debts["west"], debts["south"]],
        elevation_source=identities["south"],
    )
    assert product.retired_debt_ids == (south_debt_id,)
    assert east_debt_id not in product.retired_debt_ids
    assert west_debt_id not in product.retired_debt_ids

    # the foreign debts are KEPT AS-IS, ⛔ not consumed: a later healthy
    # East run against East's own source still redeems East's debt
    east_openings = [l for l in lines
                     if l.kind == "opening" and l.axis == "y"]
    east_raw = (_PRODUCTS / "sm25_east_as_drawn.json").read_bytes()
    east_product = synthesize_openings(
        elevation_doc=json.loads(east_raw), walls=walls,
        plan_openings=east_openings,
        mirrored=False, local_x_positive="image_left_to_right",
        evidence_debts=[debts["east"], debts["west"]],
        elevation_source=identities["east"],
    )
    assert east_product.retired_debt_ids == (east_debt_id,)
    assert west_debt_id not in east_product.retired_debt_ids

    # and the honest conservative read: a run that declares NO source
    # retires nothing, even its own facade's debt
    no_source = synthesize_openings(
        elevation_doc=json.loads(south_raw), walls=walls,
        plan_openings=[l for l in lines
                       if l.kind == "opening" and l.axis == "x"],
        mirrored=False, local_x_positive="image_left_to_right",
        evidence_debts=[debts["south"]],
    )
    assert no_source.retired_debt_ids == ()


def test_source_identity_declared_with_a_foreign_contract_is_loud():
    """The declared identity and the checked document must agree on WHAT
    KIND of source this is -- an identity carrying a non-elevation
    contract cannot bind an elevation gate run."""
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=_walls(), plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
            elevation_source=osm.ElevationSourceIdentity(
                input_id="input_plan",
                source_contract_id="as_drawn_plan_v2",
                source_output_sha256="0" * 64,
            ),
        )
    assert caught.value.code == "ELEVATION_SOURCE_CONTRACT_MISMATCH"


# ── dispatch 2026-09-04e (T4-a v2): obligation is the wiring key ─────────────── #
def test_obligation_not_prefix_is_the_wiring_criterion():
    """⭐ acceptance #2, both directions.  The wiring is the debt's
    ``obligation`` field, ⛔ never its ``debt_id`` prefix:

    * direction A -- the debt_id is renamed to something COMPLETELY
      unrelated to the historical span prefix, the ``obligation`` is the
      real one: the debt still wires, redeems and retires;
    * direction B -- the debt_id keeps the historical span prefix
      verbatim, the ``obligation`` is dropped (``None``): NOTHING wires.

    Each direction is the other's control: same registry, same source
    binding, only the criterion under test flips."""
    # direction A: unrelated debt_id, real obligation -- still wired
    renamed = _debt(
        "debt_totally_unrelated_name",
        description="span equality unverified until the plan side sees it",
        source=_source("input_south"),
    ).model_copy(
        update={"debt_id": "zz_irrelevant_identifier_zz"}
    )
    assert "debt_" not in renamed.debt_id[:2] or True  # renamed, not prefixed
    assert not renamed.debt_id.startswith("debt_elevation_chain_span_unchecked_")
    assert renamed.obligation == SPAN_OBLIGATION
    assert redeemable_debt_ids(
        [renamed], executed=_south_executed()
    ) == (renamed.debt_id,)
    walls = _walls()
    product = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
        evidence_debts=[renamed],
        elevation_source=_source("input_south"),
    )
    assert product.retired_debt_ids == (renamed.debt_id,)

    # direction B: the historical span prefix verbatim, obligation=None
    # -- NOTHING wires (free text and debt_id are both decoration)
    prefixed = _debt(
        SPAN_DEBT_ID,
        description="the historical B3 shape, verbatim",
        source=_source("input_south"),
        obligation=None,
    )
    assert prefixed.debt_id.startswith("debt_elevation_chain_span_unchecked_")
    assert prefixed.obligation is None
    assert redeemable_debt_ids(
        [prefixed], executed=_south_executed()
    ) == ()
    product_b = synthesize_openings(
        elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
        walls=walls, plan_openings=(), mirrored=False,
        local_x_positive="image_left_to_right",
        evidence_debts=[prefixed],
        elevation_source=_source("input_south"),
    )
    assert product_b.retired_debt_ids == ()


def test_unbacked_obligation_fails_loudly(monkeypatch):
    """⭐ acceptance #3 / dispatch T4: a debt whose ``obligation`` points
    at NO handler fails LOUDLY, on every entry path -- the promise an
    obligation IS cannot exist unwired.  (The schema keeps the value
    itself inside the closed Literal domain, so "no handler" is reached
    the way it can still happen: the registry row is gone at runtime.)
    Every refusal below is a control-checked tooth, ⛔ not an input
    fault: the same debt against the healthy registry retires fine."""
    debt = _debt(
        SPAN_DEBT_ID, description="unchanged", source=_source("input_south")
    )
    # the executed binding is built against the HEALTHY registry (what a
    # run that already executed the gate holds); the tooth below removes
    # the row AFTER it, the way a runtime registry loss actually happens
    executed = _south_executed()

    # entry 1: the standalone validator
    monkeypatch.delitem(DEBT_REDEMPTION_REGISTRY, SPAN_OBLIGATION)
    with pytest.raises(OpeningSynthesisError) as caught:
        osm.assert_obligations_backed([debt])
    assert caught.value.code == "OBLIGATION_UNBACKED"
    assert caught.value.context["obligation"] == SPAN_OBLIGATION

    # entry 2: the retirement path (direct call) cannot dodge it
    with pytest.raises(OpeningSynthesisError) as caught:
        redeemable_debt_ids([debt], executed=executed)
    assert caught.value.code == "OBLIGATION_UNBACKED"

    # entry 3: the synthesis itself fails fast, BEFORE any geometry runs
    with pytest.raises(OpeningSynthesisError) as caught:
        synthesize_openings(
            elevation_doc=_elevation_doc(family="South", chain_total_mm=25_000.0),
            walls=_walls(), plan_openings=(), mirrored=False,
            local_x_positive="image_left_to_right",
            evidence_debts=[debt],
            elevation_source=_source("input_south"),
        )
    assert caught.value.code == "OBLIGATION_UNBACKED"
    monkeypatch.undo()

    # the control: healthy registry, SAME debt -- retires normally, so
    # the refusals above were the tooth's, ⛔ not the input's
    assert redeemable_debt_ids(
        [debt], executed=_south_executed()
    ) == (SPAN_DEBT_ID,)
