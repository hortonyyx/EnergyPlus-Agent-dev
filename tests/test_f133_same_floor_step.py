"""F-133 — a real same-floor step on one wall line, and what the core does to it.

⛔⛔ THIS FILE LOCKS THE **CURRENT (DEFECTIVE)** BEHAVIOUR, NOT THE EXPECTED ONE.

    Expected behaviour = a real 60 mm step comes out of the deterministic core
    as it went in, two axes. It does not, and the reason is that `correction`
    has no walls and no thickness to reason with (R-6 / ②-2): the model's own
    coordinate jitter is 5-10 mm and a real 200/180 wall-basis jog is 10 mm --
    the SAME NUMBER -- so any "how big is the gap" rule at this layer is a coin
    flip. See logs/experiments/2026-08-28_wall_basis_jog/.

    **When ②-2 lands, the expected values in this file must be changed to
    "the step survives". If they cannot be changed, ②-2 did not actually solve
    the problem.**

What this file therefore asserts is two different things, and they must not be
confused:

  1. the four `test_step_*` cases pin today's *coordinates* -- a defect
     snapshot, meant to be rewritten;
  2. `test_*_ledger*` pin that the merge is **observable** -- that when an axis
     is destroyed the product says so, with both original values, the value
     they landed on, the floor and the axis. That half is not a defect
     snapshot: it must keep holding after ②-2 for whatever merges remain.

The four sizes are chosen to cover BOTH kill sites, which live in different
places and are governed by different tolerances:

    120 mm  -> survives (gap >= min_edge_length_m)
     60 mm  -> `_reconcile_cross_floor`'s Phase C sliver guard (MIN_EDGE_LENGTH)
     30 mm  -> `_identity_clusters`, per-floor (AXIS_JITTER_TOL)
     10 mm  -> `_identity_clusters`, per-floor (AXIS_JITTER_TOL)

A fixture that only exercised 60 mm would leave the whole < 50 mm band -- the
band a real 200/180 wall jog lands in -- untested.

Values are read through the SHIPPED `src/configs/correction.yaml` on purpose:
these are claims about what the pipeline actually ships today, not about a
hand-built tolerance set.
"""

from __future__ import annotations

import pytest

from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.config import load_core_tolerances

_LEDGER_RULE = "deterministic_core.same_floor_axis_merge"


def _same_floor_step(step_m: float) -> CorrectedGeometry:
    """One floor, four rooms, one horizontal wall line broken by `step_m`.

    Rooms A/C meet at y = 6.0; rooms B/D meet at y = 6.0 + step. Both halves of
    the wall are real and the step between them is real -- it is what a change
    of wall basis (240 mm wall vs 120 mm wall, one face held flush) looks like
    in plan.
    """
    return CorrectedGeometry(
        footprint_x=[0.0, 10.0],
        footprint_y=[0.0, 10.0],
        floors=[
            {
                "id": "F1",
                "name": "1F",
                "z_floor": 0.0,
                "ceiling_height": 3.0,
                "cells": [
                    {"id": "A", "role": "office", "x": [0.0, 4.0], "y": [0.0, 6.0]},
                    {"id": "B", "role": "office", "x": [4.0, 10.0], "y": [0.0, 6.0 + step_m]},
                    {"id": "C", "role": "office", "x": [0.0, 4.0], "y": [6.0, 10.0]},
                    {"id": "D", "role": "office", "x": [4.0, 10.0], "y": [6.0 + step_m, 10.0]},
                ],
            }
        ],
    )


def _run(step_m: float):
    out = apply_deterministic_core(_same_floor_step(step_m))
    y_axes = sorted({v for cell in out.floors[0].cells for v in cell.y})
    ledger = [e for e in out.corrections if e.get("rule_id") == _LEDGER_RULE]
    return out, y_axes, ledger


def test_shipped_tolerances_are_the_ones_these_cases_assume():
    """Self-check: the coordinates below are only meaningful under these values.

    [[regression-case-must-prove-its-own-premise]] -- if correction.yaml is
    retuned, this fails FIRST and names the reason, instead of the four step
    cases failing with an opaque coordinate mismatch.
    """
    tol = load_core_tolerances()
    assert tol.axis_jitter_tol_m == pytest.approx(0.05)
    assert tol.min_edge_length_m == pytest.approx(0.10)
    assert tol.structural_snap_grid_m == pytest.approx(0.01)


# --------------------------------------------------------------------------- #
# 1. today's coordinates (DEFECT SNAPSHOT -- rewrite these when ②-2 lands)
# --------------------------------------------------------------------------- #
def test_step_120mm_survives():
    """120 mm > min_edge_length_m: the step is kept. This is the correct answer."""
    _, y_axes, _ = _run(0.120)
    assert y_axes == [0.0, 6.0, 6.12, 10.0]


def test_step_60mm_is_merged_defect_snapshot():
    """⛔ DEFECT: a real 60 mm step is collapsed; BOTH wall lines move to 6.03."""
    _, y_axes, _ = _run(0.060)
    assert y_axes == [0.0, 6.03, 10.0]


def test_step_30mm_is_merged_defect_snapshot():
    """⛔ DEFECT: a real 30 mm step is collapsed to 6.02 by identity clustering."""
    _, y_axes, _ = _run(0.030)
    assert y_axes == [0.0, 6.02, 10.0]


def test_step_10mm_is_merged_defect_snapshot():
    """⛔ DEFECT: a real 10 mm step (200/180 wall, one face flush) vanishes entirely.

    This is the size that matters most and the one that is least distinguishable
    from noise -- the model's own jitter is the same 5-10 mm.
    """
    _, y_axes, _ = _run(0.010)
    assert y_axes == [0.0, 6.0, 10.0]


# --------------------------------------------------------------------------- #
# 2. the merge must be OBSERVABLE (keep asserting this after ②-2)
# --------------------------------------------------------------------------- #
def test_surviving_step_produces_no_ledger_row():
    """The 120 mm case must produce ZERO rows.

    This is the pole that gives the three positive cases below their teeth: a
    ledger that fired unconditionally would satisfy them and mean nothing
    ([[gate-with-only-negative-assertions-is-unobservable]]).
    """
    _, _, ledger = _run(0.120)
    assert ledger == []


@pytest.mark.parametrize(
    "step_m, expected_step, expected_tol, expected_values, expected_resolved",
    [
        # 50-100 mm: survives clustering, dies in the Phase C sliver guard.
        (0.060, "sliver_merge", "MIN_EDGE_LENGTH", [6.0, 6.06], 6.03),
        # < 50 mm: dies earlier, in per-floor identity clustering. Covering only
        # the 60 mm case would leave this entire band unobserved.
        (0.030, "identity_cluster", "AXIS_JITTER_TOL", [6.0, 6.03], 6.02),
        (0.010, "identity_cluster", "AXIS_JITTER_TOL", [6.0, 6.01], 6.0),
    ],
)
def test_merged_step_is_locatable_in_the_ledger(
    step_m, expected_step, expected_tol, expected_values, expected_resolved
):
    """Every swallowed same-floor axis leaves one row that can be pointed at.

    ⛔ A bare count is not enough: the row must name the floor, the axis, both
    original values and where they landed, or the record cannot be told apart
    from any other merge ([[absence-conflates-causes-in-observables]]).
    """
    _, _, ledger = _run(step_m)
    assert len(ledger) == 1, ledger
    row = ledger[0]

    assert row["axis"] == "y"
    assert row["floor"] == "1F"
    assert row["step"] == expected_step
    assert row["tolerance_name"] == expected_tol
    assert row["original_value"] == pytest.approx(expected_values)
    assert row["resolved_value"] == pytest.approx(expected_resolved)
    assert row["per_value_delta"] == pytest.approx(
        [expected_resolved - v for v in expected_values], abs=1e-9
    )
    assert row["separation"] == pytest.approx(step_m)
    # locatable by string too -- the target must carry floor + both values
    assert "1F" in row["target"]
    for v in expected_values:
        assert f"{v:.4f}" in row["target"]


def test_10mm_step_is_recorded_even_though_each_side_moves_under_output_precision():
    """The 10 mm case shifts each axis by <= output_precision_m (5 mm and 0 mm).

    An output-precision filter -- the rule that governs the ordinary
    `corrections` rows -- would therefore drop it, and the single most
    important case would go back to being silent. This asserts the ledger
    deliberately does NOT apply that filter.
    """
    tol = load_core_tolerances()
    _, _, ledger = _run(0.010)
    assert len(ledger) == 1
    row = ledger[0]
    assert max(abs(d) for d in row["per_value_delta"]) <= tol.output_precision_m
    assert row["separation"] == pytest.approx(0.010)


def test_cross_floor_merge_is_not_recorded_as_a_same_floor_merge():
    """Collapsing one wall read differently on two FLOORS is the parameter's job.

    It is already audited as `cross_floor_align`; recording it here as well
    would bury the same-floor rows in exactly the noise this ledger exists to
    surface.
    """
    geom = CorrectedGeometry(
        footprint_x=[0.0, 10.0],
        footprint_y=[0.0, 8.0],
        floors=[
            {
                "id": "F1", "name": "1F", "z_floor": 0.0, "ceiling_height": 3.0,
                "cells": [
                    {"id": "F1_A", "role": "office", "x": [0.0, 4.90], "y": [0.0, 8.0]},
                    {"id": "F1_B", "role": "office", "x": [4.90, 10.0], "y": [0.0, 8.0]},
                ],
            },
            {
                "id": "F2", "name": "2F", "z_floor": 3.0, "ceiling_height": 3.0,
                "cells": [
                    {"id": "F2_A", "role": "office", "x": [0.0, 4.95], "y": [0.0, 8.0]},
                    {"id": "F2_B", "role": "office", "x": [4.95, 10.0], "y": [0.0, 8.0]},
                ],
            },
        ],
    )
    out = apply_deterministic_core(geom)
    mids = {c.x[1] for fl in out.floors for c in fl.cells if c.id.endswith("_A")}
    assert len(mids) == 1, f"cross-floor axis not unified: {mids}"
    assert not [e for e in out.corrections if e.get("rule_id") == _LEDGER_RULE]


# --------------------------------------------------------------------------- #
# 3. R2 — the geometry kernel's sliver floor is not a second, independent number
# --------------------------------------------------------------------------- #
def test_modelling_edge_floor_follows_the_active_correction_config(tmp_path, monkeypatch):
    """`modelling`'s sliver floor and `min_edge_length_m` must be ONE number.

    Both are handed to the same validator (`cell_geometry.cell_polygon`) on two
    different call paths. Before F-133 R2 the geometry path used its own literal
    `_MIN_EDGE = 0.10`, so with the config raised to 0.200 m a 0.15 m cell edge
    was REJECTED by the correction path and ACCEPTED by the geometry path --
    one validator, two answers.

    ⛔ The point of the override is that a same-valued duplicate is
    indistinguishable from a shared source until the two are made to disagree
    ([[neuter-proves-wiring-not-discriminating-power]]). Asserting only that
    both read 0.10 under the shipped config would pass on the old code too.
    """
    from src.agent.correction.cell_geometry import validate_cell_polygon
    from src.agent.correction.config import CORRECTION_CONFIG_ENV, resolve_correction_config_path
    from src.agent.correction.schema import Cell
    from src.agent.geometry import modelling

    shipped = resolve_correction_config_path().read_text(encoding="utf-8")
    assert "min_edge_length_m: 0.100" in shipped
    override = tmp_path / "correction_min_edge_200mm.yaml"
    override.write_text(
        shipped.replace("min_edge_length_m: 0.100", "min_edge_length_m: 0.200"),
        encoding="utf-8",
    )
    monkeypatch.setenv(CORRECTION_CONFIG_ENV, str(override))

    tol = load_core_tolerances()
    assert tol.min_edge_length_m == pytest.approx(0.200), "override config did not take"
    assert modelling._min_edge() == pytest.approx(0.200), (
        "modelling still holds an independent sliver floor"
    )

    thin = Cell(
        id="thin", role="office", x=[0.0, 3.0], y=[0.0, 0.15],
        polygon=[[0.0, 0.0], [3.0, 0.0], [3.0, 0.15], [0.0, 0.15]],
    )
    with pytest.raises(ValueError):
        validate_cell_polygon(thin, min_edge_length_m=tol.min_edge_length_m)
    with pytest.raises(ValueError):
        modelling._cell_polygon(thin)


def test_modelling_edge_floor_value_is_unchanged_under_the_shipped_config():
    """R2 changed the SOURCE of the number, not the number. 0.100 m, as before."""
    from src.agent.geometry import modelling

    assert modelling._min_edge() == pytest.approx(0.100)
    assert load_core_tolerances().min_edge_length_m == pytest.approx(0.100)
