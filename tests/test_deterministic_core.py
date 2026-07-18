"""Deterministic-core guarantees: cluster -> snap-to-grid -> sliver guard, and
the window tier (fine grid + clamp into parent). Constants come from
src/configs/correction.yaml via the config loader."""

from __future__ import annotations

import pytest

from src.agent.correction import CorrectedGeometry, apply_deterministic_core
from src.agent.correction.config import CoreTolerances, load_core_tolerances
from src.agent.correction.envelope import (
    AuthoritativeEnvelope,
    EnvelopeAxisResolution,
    EnvelopeCandidate,
)
from src.agent.correction.geometry_validator import validate_corrected_geometry


def _tol(**over) -> CoreTolerances:
    base = dict(
        axis_jitter_tol_m=0.05,
        cross_floor_align_tol_m=0.11,
        structural_snap_grid_m=0.05,
        min_edge_length_m=0.10,
        output_precision_m=0.01,
        window_snap_grid_m=0.01,
        window_clamp_to_parent=True,
        envelope_reconcile_tol_m=0.30,
        coverage_area_tol_m2=0.05,
        envelope_axis_attach_tol_m=0.01,
        envelope_endpoint_match_tol_m=0.05,
        envelope_candidate_agreement_tol_m=0.05,
        gap_close_threshold_m=0.30,
        gap_arbitration_band_m=1.00,
        # Vg rework CR5 (§10.1): these two carry no dataclass default any
        # more — every helper must pass them explicitly; override via `over`
        # when a test needs a different value.
        facade_visibility_depth_epsilon_m=1e-9,
        facade_visibility_endpoint_epsilon_m=1e-9,
        window_segment_endpoint_clamp_tol_m=0.01,
        window_host_span_epsilon_m=1e-9,
        window_host_plane_epsilon_m=1e-9,
    )
    base.update(over)
    t = CoreTolerances(**base)
    t.validate()
    return t


def _two_floor(x_f1: float, x_f2: float, windows: list | None = None) -> CorrectedGeometry:
    """Two stacked floors whose mid partition is at x_f1 (F1) vs x_f2 (F2)."""
    return CorrectedGeometry(
        footprint_x=[0.0, 10.0],
        footprint_y=[0.0, 8.0],
        windows=windows or [],
        floors=[
            {
                "name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                "cells": [
                    {"id": "F1_A", "x": [0.0, x_f1], "y": [0.0, 8.0]},
                    {"id": "F1_B", "x": [x_f1, 10.0], "y": [0.0, 8.0]},
                ],
            },
            {
                "name": "F2", "z_floor": 3.6, "ceiling_height": 3.6,
                "cells": [
                    {"id": "F2_A", "x": [0.0, x_f2], "y": [0.0, 8.0]},
                    {"id": "F2_B", "x": [x_f2, 10.0], "y": [0.0, 8.0]},
                ],
            },
        ],
    )


def _multi_floor_partitions(partitions: list[list[float]]) -> CorrectedGeometry:
    floors = []
    for idx, axes in enumerate(partitions, start=1):
        bounds = [0.0, *axes, 10.0]
        floors.append(
            {
                "name": f"F{idx}",
                "z_floor": 3.6 * (idx - 1),
                "ceiling_height": 3.6,
                "cells": [
                    {
                        "id": f"F{idx}_{cell_idx}",
                        "x": [bounds[cell_idx], bounds[cell_idx + 1]],
                        "y": [0.0, 8.0],
                    }
                    for cell_idx in range(len(bounds) - 1)
                ],
            }
        )
    return CorrectedGeometry(footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0], floors=floors)


def _envelope_axis(axis: str, bounds: tuple[float, float], *, view: str = "South") -> EnvelopeAxisResolution:
    c = EnvelopeCandidate(
        axis=axis,
        bounds=bounds,
        span=bounds[1] - bounds[0],
        source_kind="dimension",
        view=view,
        source_id="D1",
        role="overall",
        note="overall total",
        confidence=0.95,
    )
    return EnvelopeAxisResolution(
        axis=axis,
        status="accepted",
        bounds=bounds,
        span=bounds[1] - bounds[0],
        source=c,
        candidates=(c,),
        reason="accepted",
    )


def _three_bay_inset() -> CorrectedGeometry:
    return CorrectedGeometry(
        footprint_x=[0.12, 14.88],
        footprint_y=[0.12, 7.88],
        windows=[
            {"id": "W1", "floor": "F1", "facade": "South", "span": [1.0, 2.0], "z": [1.0, 2.0], "room": "A"},
            {"id": "W2", "floor": "F1", "facade": "East", "span": [3.0, 4.0], "z": [1.0, 2.0], "room": "C"},
        ],
        floors=[
            {
                "name": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.6,
                "cells": [
                    {"id": "A", "x": [0.12, 5.0], "y": [0.12, 7.88]},
                    {"id": "B", "x": [5.0, 10.0], "y": [0.12, 7.88]},
                    {"id": "C", "x": [10.0, 14.88], "y": [0.12, 7.88]},
                ],
            }
        ],
    )


def test_cross_floor_jitter_unified():
    """The same wall read as 4.90 (F1) and 4.95 (F2) becomes one canonical axis."""
    g = apply_deterministic_core(_two_floor(4.90, 4.95), _tol())
    right = {c.x[1] for fl in g.floors for c in fl.cells if c.id.endswith("_A")}
    assert len(right) == 1, f"cross-floor axis not unified: {right}"


def test_cross_floor_corridor_jitter_uses_align_tol():
    """Two floors read at 3.10 / 3.20 reconcile to one canonical axis."""
    g = apply_deterministic_core(_two_floor(3.10, 3.20), _tol())
    right = {c.x[1] for fl in g.floors for c in fl.cells if c.id.endswith("_A")}
    assert len(right) == 1
    assert any(e.get("rule_id") == "deterministic_core.cross_floor_align" for e in g.corrections)


def test_cross_floor_reconcile_preserves_same_floor_axes():
    """A nearby cross-floor read must not collapse two valid same-floor axes."""
    g = apply_deterministic_core(_multi_floor_partitions([[3.10, 3.21], [3.19]]), _tol())
    f1_bounds = sorted({x for c in g.floors[0].cells for x in c.x})
    assert 3.10 in f1_bounds
    assert any(abs(x - 3.20) < 1e-9 for x in f1_bounds)
    assert len([x for x in f1_bounds if 3.0 < x < 3.3]) == 2
    assert not g.unsupported
    assert (
        any(e.get("rule_id") == "deterministic_core.cross_floor_ambiguous" for e in g.corrections)
        or {c.x[1] for c in g.floors[1].cells if c.id == "F2_0"} <= set(f1_bounds)
    )


def test_cross_floor_three_floor_chain_does_not_collapse():
    """Adjacent links inside tol must not become one transitive cross-floor axis."""
    g = apply_deterministic_core(_multi_floor_partitions([[3.10], [3.18], [3.26]]), _tol())
    right = {c.x[1] for fl in g.floors for c in fl.cells if c.id.endswith("_0")}
    assert len(right) > 1
    assert any(e.get("rule_id") == "deterministic_core.cross_floor_ambiguous" for e in g.corrections)
    assert not g.unsupported


def test_cross_floor_competing_candidates_flagged_not_silently_stolen():
    """One-to-many cross-floor candidates stay split and emit an ambiguity audit."""
    g = apply_deterministic_core(
        _multi_floor_partitions([[3.10], [3.17, 3.29]]),
        _tol(cross_floor_align_tol_m=0.20),
    )
    f2_bounds = sorted({x for c in g.floors[1].cells for x in c.x})
    assert len([x for x in f2_bounds if 3.0 < x < 3.4]) == 2
    assert any(e.get("rule_id") == "deterministic_core.cross_floor_ambiguous" for e in g.corrections)
    assert not any(e.get("rule_id") == "deterministic_core.cross_floor_align" for e in g.corrections)
    assert not g.unsupported


def test_snapped_to_grid_no_mm_level_mean():
    """Cluster mean 4.925 must not leak out; result lands on the 50mm grid."""
    g = apply_deterministic_core(_two_floor(4.90, 4.95), _tol())
    val = next(c.x[1] for fl in g.floors for c in fl.cells if c.id == "F1_A")
    assert abs((val / 0.05) - round(val / 0.05)) < 1e-9, f"{val} not on 50mm grid"
    assert val != pytest.approx(4.925), "raw cluster mean leaked"


def test_sliver_guard_min_edge():
    """No two canonical axes end up closer than min_edge_length."""
    # partitions 0.07 apart on the two floors -> distinct clusters, but a 0.07
    # gap would be a sub-min-edge sliver; the guard must collapse them.
    g = apply_deterministic_core(_two_floor(4.90, 4.97), _tol())
    xs = sorted({c.x[0] for fl in g.floors for c in fl.cells} |
                {c.x[1] for fl in g.floors for c in fl.cells})
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert all(gp >= 0.10 - 1e-9 for gp in gaps), f"sliver survived: {xs}"


def test_window_uses_fine_grid_not_structural():
    """A window at 10mm offsets keeps them; it is not forced onto the 50mm grid."""
    g = _two_floor(5.0, 5.0, windows=[{"id": "W", "floor": "F1", "facade": "South",
                  "span": [1.013, 3.987], "z": [0.9, 2.1], "room": "F1_A"}])
    out = apply_deterministic_core(g, _tol())
    w = out.windows[0]
    assert w.span == [1.01, 3.99]  # rounded to 10mm, not snapped to 1.0/4.0
    assert w.z == [0.9, 2.1]


def test_window_clamped_into_parent():
    """An over-reaching window is clamped within its cell span and floor z-range."""
    g = _two_floor(5.0, 5.0, windows=[{"id": "W", "floor": "F1", "facade": "South",
                  "span": [1.0, 12.0], "z": [0.9, 9.0], "room": "F1_A"}])
    out = apply_deterministic_core(g, _tol())
    w = out.windows[0]
    assert w.span[1] <= 5.0  # within F1_A x = [0, 5]
    assert w.z[1] <= 3.6  # within floor z = [0, 3.6]


def test_window_clamp_can_be_disabled():
    g = _two_floor(5.0, 5.0, windows=[{"id": "W", "floor": "F1", "facade": "South",
                  "span": [1.0, 12.0], "z": [0.9, 2.1], "room": "F1_A"}])
    out = apply_deterministic_core(g, _tol(window_clamp_to_parent=False))
    assert out.windows[0].span[1] == 12.0  # snapped only, not clamped


def test_gap_close_internal_wall_reaches_exterior():
    """A cell edge 240mm short of the left exterior wall is pulled onto it."""
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                 "cells": [{"id": "A", "x": [0.24, 5.0], "y": [0.0, 8.0]},
                           {"id": "B", "x": [5.0, 10.0], "y": [0.0, 8.0]}]}],
    )
    out = apply_deterministic_core(g, _tol())
    a = next(c for c in out.floors[0].cells if c.id == "A")
    assert a.x[0] == 0.0, f"gap to exterior not closed: {a.x}"
    assert any(e.get("rule_id") == "deterministic_core.gap_close" for e in out.corrections)


def test_gap_close_leaves_interior_partition_untouched():
    """An interior partition far from any footprint boundary is not pulled."""
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                 "cells": [{"id": "A", "x": [0.0, 5.0], "y": [0.0, 8.0]},
                           {"id": "B", "x": [5.0, 10.0], "y": [0.0, 8.0]}]}],
    )
    out = apply_deterministic_core(g, _tol())
    shared = {c.x[1] for c in out.floors[0].cells if c.id == "A"}
    assert shared == {5.0}, "mid partition at 5.0 must not move to a boundary"


def test_gap_beyond_threshold_not_closed():
    """A 400mm gap (> 300mm) is left for A3, not auto-closed."""
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0], footprint_y=[0.0, 8.0],
        floors=[{"name": "F1", "z_floor": 0.0, "ceiling_height": 3.6,
                 "cells": [{"id": "A", "x": [0.40, 5.0], "y": [0.0, 8.0]}]}],
    )
    out = apply_deterministic_core(g, _tol())
    assert out.floors[0].cells[0].x[0] == 0.40


def test_authoritative_envelope_accepts_bounds_and_moves_only_perimeter_edges():
    g = _three_bay_inset()
    env = AuthoritativeEnvelope(
        axes={
            "x": _envelope_axis("x", (0.0, 15.0)),
            "y": _envelope_axis("y", (0.0, 8.0), view="East"),
        }
    )
    out = apply_deterministic_core(g, _tol(), authoritative_envelope=env)

    assert out.footprint_x == [0.0, 15.0]
    assert out.footprint_y == [0.0, 8.0]
    cells = {c.id: c for c in out.floors[0].cells}
    assert cells["A"].x == [0.0, 5.0]
    assert cells["B"].x == [5.0, 10.0]
    assert cells["C"].x == [10.0, 15.0]
    assert {x for c in out.floors[0].cells for x in c.x if x in {5.0, 10.0}} == {5.0, 10.0}
    assert cells["A"].y == [0.0, 8.0]
    assert [w.span for w in out.windows] == [[1.0, 2.0], [3.0, 4.0]]
    assert not [f for f in validate_corrected_geometry(out) if not f.ok]
    assert any(e.get("rule_id") == "deterministic_core.envelope_reconcile" for e in out.corrections)


def test_authoritative_envelope_over_tolerance_rejected():
    g = _three_bay_inset()
    baseline = apply_deterministic_core(_three_bay_inset(), _tol())
    env = AuthoritativeEnvelope(axes={"x": _envelope_axis("x", (0.0, 16.0))})
    out = apply_deterministic_core(g, _tol(), authoritative_envelope=env)
    assert out.footprint_x == baseline.footprint_x
    assert any(
        e.get("rule_id") == "deterministic_core.envelope_reconcile"
        and "exceeds" in e.get("reason", "")
        for e in out.unsupported
    )


def test_authoritative_envelope_none_is_noop_for_envelope_path():
    baseline = apply_deterministic_core(_three_bay_inset(), _tol(gap_close_threshold_m=0.30))
    out = apply_deterministic_core(
        _three_bay_inset(),
        _tol(gap_close_threshold_m=0.30),
        authoritative_envelope=None,
    )
    assert out.model_dump() == baseline.model_dump()
    assert not any(e.get("rule_id") == "deterministic_core.envelope_reconcile" for e in out.corrections)


def test_authoritative_envelope_origin_ambiguity_skips():
    candidate = EnvelopeCandidate(
        axis="x",
        bounds=None,
        span=15.0,
        source_kind="dimension_text",
        view="South",
        source_id="D1",
        role="overall",
        note="overall total",
        confidence=0.5,
    )
    env = AuthoritativeEnvelope(
        axes={
            "x": EnvelopeAxisResolution(
                axis="x",
                status="accepted",
                bounds=None,
                span=15.0,
                source=candidate,
                candidates=(candidate,),
            )
        }
    )
    out = apply_deterministic_core(_three_bay_inset(), _tol(), authoritative_envelope=env)
    baseline = apply_deterministic_core(_three_bay_inset(), _tol())
    assert out.footprint_x == baseline.footprint_x
    assert any("origin ambiguity" in e.get("reason", "") for e in out.unsupported)


def test_authoritative_envelope_insufficient_evidence_skip_logged():
    c = EnvelopeCandidate(
        axis="x",
        bounds=(0.0, 15.0),
        span=15.0,
        source_kind="dimension",
        view="South",
        source_id="D2",
        confidence=0.6,
    )
    env = AuthoritativeEnvelope(
        axes={
            "x": EnvelopeAxisResolution(
                axis="x",
                status="skipped",
                candidates=(c,),
                reason="insufficient evidence",
            )
        }
    )
    out = apply_deterministic_core(_three_bay_inset(), _tol(), authoritative_envelope=env)
    baseline = apply_deterministic_core(_three_bay_inset(), _tol())
    assert out.footprint_x == baseline.footprint_x
    assert any("insufficient evidence" in e.get("reason", "") for e in out.unsupported)


def test_authoritative_envelope_pre_move_guard_rejects_cell_collapse():
    g = CorrectedGeometry(
        footprint_x=[0.0, 10.0],
        footprint_y=[0.0, 8.0],
        floors=[
            {
                "name": "F1",
                "z_floor": 0.0,
                "ceiling_height": 3.6,
                "cells": [
                    {"id": "thin", "x": [0.0, 0.20], "y": [0.0, 8.0]},
                    {"id": "rest", "x": [0.20, 10.0], "y": [0.0, 8.0]},
                ],
            }
        ],
    )
    env = AuthoritativeEnvelope(axes={"x": _envelope_axis("x", (0.15, 10.0))})
    out = apply_deterministic_core(g, _tol(), authoritative_envelope=env)
    assert out.footprint_x == [0.0, 10.0]
    assert any(
        e.get("rule_id") == "deterministic_core.envelope_reconcile"
        and e.get("offending_cells")
        for e in out.unsupported
    )


def test_invariant_gap_close_ordering():
    """gap_close must sit between jitter tol and the arbitration band."""
    with pytest.raises(ValueError):
        _tol(gap_close_threshold_m=0.04)  # below axis_jitter_tol 0.05
    with pytest.raises(ValueError):
        _tol(gap_close_threshold_m=1.5)  # above arbitration band 1.0


def test_invariant_grid_not_above_min_edge():
    """The config guard rejects a structural grid coarser than the sliver floor."""
    with pytest.raises(ValueError):
        _tol(structural_snap_grid_m=0.20, min_edge_length_m=0.10)


def test_default_config_loads():
    """The shipped correction.yaml parses and satisfies its own invariants."""
    tol = load_core_tolerances()
    tol.validate()
    assert tol.structural_snap_grid_m <= tol.min_edge_length_m


def test_default_config_loads_facade_visibility_epsilons():
    """C2 Vg (§10.1): the shipped two epsilons load exactly and validate."""
    tol = load_core_tolerances()
    assert tol.facade_visibility_depth_epsilon_m == 1e-9
    assert tol.facade_visibility_endpoint_epsilon_m == 1e-9
    tol.validate()


@pytest.mark.parametrize("bad_depth_eps", [0.0, -1e-9, float("nan"), float("inf"), 1.0])
def test_invariant_facade_visibility_depth_epsilon_bounds(bad_depth_eps):
    """Must be strictly inside (0, structural_snap_grid_m) — a degeneracy
    guard, never a measurement tolerance (§10.1)."""
    with pytest.raises(ValueError):
        _tol(facade_visibility_depth_epsilon_m=bad_depth_eps)


@pytest.mark.parametrize("bad_endpoint_eps", [0.0, -1e-9, float("nan"), 1.0])
def test_invariant_facade_visibility_endpoint_epsilon_bounds(bad_endpoint_eps):
    """Must be strictly inside (0, min_edge_length_m)."""
    with pytest.raises(ValueError):
        _tol(facade_visibility_endpoint_epsilon_m=bad_endpoint_eps)


def test_facade_visibility_epsilons_have_no_dataclass_default():
    """C2 Vg rework CR5 (§10.1): the two Vg epsilons must NOT carry a
    dataclass default — omitting either one at the Python construction
    boundary raises `TypeError` immediately, never a silent 1e-9 fallback.
    This replaces the pre-rework test that asserted the opposite (that the
    `_tol()` helper could omit them and still get a valid instance); every
    direct `CoreTolerances(...)` call site, including test helpers, must now
    pass both explicitly (see the updated `_tol()` helper above and its
    siblings in test_c2_b1_cell_polygon.py / test_kernel_guards.py)."""
    base = dict(
        axis_jitter_tol_m=0.05, cross_floor_align_tol_m=0.11, structural_snap_grid_m=0.05,
        min_edge_length_m=0.10, output_precision_m=0.01, window_snap_grid_m=0.01,
        window_clamp_to_parent=True, envelope_reconcile_tol_m=0.30, coverage_area_tol_m2=0.05,
        envelope_axis_attach_tol_m=0.01, envelope_endpoint_match_tol_m=0.05,
        envelope_candidate_agreement_tol_m=0.05,
        gap_close_threshold_m=0.30, gap_arbitration_band_m=1.00,
    )
    with pytest.raises(TypeError):
        CoreTolerances(**base)  # both epsilons omitted
    with pytest.raises(TypeError):
        CoreTolerances(**base, facade_visibility_depth_epsilon_m=1e-9)  # endpoint epsilon omitted
    with pytest.raises(TypeError):
        CoreTolerances(**base, facade_visibility_endpoint_epsilon_m=1e-9)  # depth epsilon omitted
    # both supplied: constructs and validates fine (sanity check the
    # rewritten field order in config.py did not break normal construction).
    tol = CoreTolerances(**base, facade_visibility_depth_epsilon_m=1e-9,
                         facade_visibility_endpoint_epsilon_m=1e-9,
                         window_segment_endpoint_clamp_tol_m=0.01,
                         window_host_span_epsilon_m=1e-9,
                         window_host_plane_epsilon_m=1e-9)
    tol.validate()
