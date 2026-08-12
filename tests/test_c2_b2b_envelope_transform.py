from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.deterministic import apply_deterministic_core
from src.agent.correction.envelope import (
    AuthoritativeEnvelope, EnvelopeAxisResolution, EnvelopeCandidate,
    dimension_chain_is_closed_for_endpoint, extract_wing_boundary_evidence_from_view,
)
from src.agent.correction.envelope import EnvelopeEndpointResolution, WingBoundaryEvidence
from src.agent.correction.envelope_transform import (
    EnvelopeAnnotationObservation, EnvelopeGateFinding, EnvelopeTransformRejected,
    apply_v3_envelope_transaction, observe_envelope_annotation_basis, resolve_envelope_move_intents,
)
from src.agent.correction.footprint import floor_footprint_fingerprint
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.correction.schema import CorrectedGeometry, CorrectedGeometryV3
from src.agent.correction.window_sources import (
    build_verified_window_resolver_inputs,
    source_locator,
)
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import OpeningEvidence, RequiredViewEntry, ViewManifest
from src.agent.reading import parse_reading_view
from src.agent.reading.constants import DIMCHAIN_CLOSE_TOL_M


def _geom():
    return ensure_corrected_geometry({
        "schema_version": "3", "footprint_x": [0, 10], "footprint_y": [0, 8],
        "floors": [{"id": "f1", "name": "F1", "z_floor": 0, "ceiling_height": 3,
                    "footprint": {"vertices": [[0, 0], [10, 0], [10, 3], [4, 3], [4, 8], [0, 8]]},
                    "cells": [{"id": "bottom", "x": [0, 10], "y": [0, 3]},
                              {"id": "top", "x": [0, 4], "y": [3, 8]}]}],
    })


def _envelope():
    candidate = EnvelopeCandidate("x", (0, 10.2), 10.2, "dimension", "South", "overall-x", role="overall", confidence=.95)
    return AuthoritativeEnvelope({"x": EnvelopeAxisResolution("x", "accepted", (0, 10.2), 10.2, candidate, candidates=(candidate,))})


def _u_geom(*, floors: int = 1, windows=None):
    rows = []
    for number in range(floors):
        rows.append({"id": f"f{number + 1}", "name": f"F{number + 1}", "z_floor": number * 3,
                     "ceiling_height": 3,
                     "footprint": {"vertices": [[0, 0], [10, 0], [10, 8], [7, 8], [7, 3], [3, 3], [3, 8], [0, 8]]},
                     "cells": [{"id": f"left-{number}", "x": [0, 3], "y": [0, 8]},
                               {"id": f"right-{number}", "x": [7, 10], "y": [0, 8]},
                               {"id": f"bottom-{number}", "x": [3, 7], "y": [0, 3]}]})
    return ensure_corrected_geometry({"schema_version": "3", "footprint_x": [0, 10], "footprint_y": [0, 8],
                                     "floors": rows, "windows": windows or []})


def _with_plan_marker(geom):
    """Build a real plan-source marker for the single-window B2b fixture."""
    window = geom.windows[0]
    reading = json.dumps({
        "image_kind": "plan",
        "strokes": [{
            "id": "P-W", "pen": "window",
            "geometry": {
                "x_range_m":list(window.span), "y_range_m":[0.0, 0.1],
            },
        }],
        "uncaptured": [],
    }, separators=(",", ":")).encode("utf-8")
    locator = source_locator(
        input_id="plan", observation_id="P-W",
        output_sha256=hashlib.sha256(reading).hexdigest(),
    )
    payload = geom.model_dump(mode="json")
    payload["windows"][0]["provenance"] = {
        "existence": {"provenance": "observed", "source_ids": [locator]},
    }
    with_provenance = ensure_corrected_geometry(payload)
    entry = RequiredViewEntry(
        input_id="plan", source_image="case_data/plan.png", image_sha256="a" * 64,
        view_type="plan", floor_ref=1,
        direction_source="standard_assumption", direction_semantics="building_axis",
        semantics_source="case_metadata", dimensioned=True,
        expected_output_id="plan",
        opening_evidence=OpeningEvidence(
            potentially_observable_claims=["existence", "host", "along", "width"],
        ),
    )
    manifest_payload = {
        "view_manifest_schema_version": "1", "claims_vocab_version": "1",
        "generator_version": "1", "completeness_ruleset_version": "1",
        "case_id": "b2b", "case_metadata_sha256": "a" * 64,
        "entries": [entry.model_dump(mode="json")],
    }
    manifest = ViewManifest(
        **manifest_payload, content_sha256=hash_obj(manifest_payload),
    )
    marker = build_verified_window_resolver_inputs(
        producer_draw=with_provenance,
        raw_view_manifest_bytes=manifest.model_dump_json().encode("utf-8"),
        raw_reading_artifacts={"plan": reading}, elevation_direction_facts=(),
    )
    return with_provenance, marker


def _wing(value: float):
    evidence = WingBoundaryEvidence("South", "x", value, "South", "wing-dim", "wing-chain", 1,
                                    "south-wing", "from", "0" * 64)
    return AuthoritativeEnvelope(endpoint_resolutions=(EnvelopeEndpointResolution("accepted", evidence),))


def test_l_shape_overall_transform_is_atomic_and_preserves_coverage():
    before = _geom()
    result = apply_v3_envelope_transaction(before, load_core_tolerances(), _envelope())
    assert result.committed
    assert before.footprint_x == [0.0, 10.0]  # input never mutated
    assert result.geom.footprint_x == [0.0, 10.2]
    row = result.geom.corrections[-1]
    assert row["rule_id"] == "deterministic_core.envelope_atomic_transform"
    assert all(gate["ok"] for gate in row["hard_gates"])


def test_transaction_rejects_divergent_footprints_after_schema_is_bypassed(monkeypatch):
    """Depth lock: the divergent object reaches B2b's own scope gate."""
    before = _u_geom(floors=2)
    vertices = list(before.floors[1].footprint.vertices)
    vertices[1] = (9.0, vertices[1][1])
    object.__setattr__(before.floors[1].footprint, "vertices", vertices)
    calls = {"count": 0}

    def bypass_schema(cls, value):
        calls["count"] += 1
        assert isinstance(value, dict)
        return before

    monkeypatch.setattr(CorrectedGeometryV3, "model_validate", classmethod(bypass_schema))

    result = apply_v3_envelope_transaction(
        before, load_core_tolerances(), _envelope()
    )

    assert calls["count"] == 1
    assert not result.committed
    assert result.failed_gate_id == "correction.envelope_schema_scope"
    assert "per-floor footprints are not identical" in str(result.geom.conflicts[-1])


def test_u_wing_break_cross_floor_moves_internal_axis_without_notch_depth_drift():
    before = _u_geom(floors=2)
    result = apply_v3_envelope_transaction(before, load_core_tolerances(), _wing(3.1))
    assert result.committed
    assert all(3.1 in [point[0] for point in floor.footprint.vertices] for floor in result.geom.floors)
    assert all([point[1] for point in floor.footprint.vertices] == [point[1] for point in before.floors[index].footprint.vertices]
               for index, floor in enumerate(result.geom.floors))
    # The bottom-cell T junction shares the x=3 component even beyond the
    # footprint's vertical notch edge; it must move successfully, not conflict.
    assert all(floor.cells[2].x[0] == 3.1 for floor in result.geom.floors)


def test_t_junction_cell_edge_is_in_component_successfully():
    before = _u_geom()
    result = apply_v3_envelope_transaction(before, load_core_tolerances(), _wing(3.1))
    assert result.committed
    assert result.geom.floors[0].cells[0].x[1] == 3.1
    assert result.geom.floors[0].cells[2].x[0] == 3.1


def test_post_transform_window_min_width_and_wing_crossing_reject():
    narrow = _u_geom(windows=[{"id": "narrow", "floor": "F1", "floor_id": "f1", "facade": "South",
                               "span": [2.85, 3.0], "z": [1, 2], "room": "left-0"}])
    narrow, narrow_marker = _with_plan_marker(narrow)
    result = apply_v3_envelope_transaction(
        narrow, load_core_tolerances(), _wing(2.9),
        verified_window_inputs=narrow_marker,
    )
    assert not result.committed and result.failed_gate_id == "correction.window_host_unique"
    assert "falls below min_edge_length_m" in result.geom.conflicts[-1]["reason_unresolved"]
    crossing = _u_geom(windows=[{"id": "crossing", "floor": "F1", "floor_id": "f1", "facade": "South",
                                 "span": [3.05, 3.2], "z": [1, 2], "room": "bottom-0"}])
    crossing, crossing_marker = _with_plan_marker(crossing)
    result = apply_v3_envelope_transaction(
        crossing, load_core_tolerances(), _wing(3.1),
        verified_window_inputs=crossing_marker,
    )
    assert not result.committed and result.failed_gate_id == "correction.window_host_unique"
    assert "window span crosses wing break" in result.geom.conflicts[-1]["reason_unresolved"]


def test_post_vg_segment_binding_is_fail_closed_and_rolls_back():
    geom = _geom()
    digest = floor_footprint_fingerprint(geom, geom.floors[0])
    geom = ensure_corrected_geometry({**geom.model_dump(), "facade_segments": [{
        "id": "south-1", "floor_id": "f1", "facade_family": "South",
        "p1": [0, 0], "p2": [10, 0], "outward_normal": [0, -1],
        "world_along_interval": {"lo": 0, "hi": 10}, "depth": 0,
        "source_footprint_fingerprint": digest,
    }]})
    result = apply_v3_envelope_transaction(geom, load_core_tolerances(), _envelope())
    assert not result.committed
    assert result.failed_gate_id == "correction.facade_segment_binding"
    assert result.geom.conflicts[-1]["fallback_action"] == "rollback_keep_original_geometry"


def test_endpoint_closure_requires_explicit_tolerance_and_marker_is_extra_only():
    assert inspect.signature(dimension_chain_is_closed_for_endpoint).parameters["close_tol_m"].default is inspect.Parameter.empty
    view = parse_reading_view({
        "image_kind": "elevation", "image_label": "South", "facade": {"view_facade": "South", "mirrored": "false"}, "dimensions": [
            {"id": "overall", "value_m": 4, "from": [0, 0], "to": [4, 0], "axis": "x", "chain_id": "c", "role": "overall", "order": 0},
            {"id": "segment", "value_m": 4, "from": [0, 0], "to": [4, 0], "axis": "x", "chain_id": "c", "role": "segment", "order": 1,
             "boundary_kind": "wing_break", "boundary_endpoint": "from", "boundary_ref": "south-wing-a"},
        ],
    })
    assert dimension_chain_is_closed_for_endpoint(view, chain_id="c", axis="x", close_tol_m=DIMCHAIN_CLOSE_TOL_M)
    evidence = extract_wing_boundary_evidence_from_view(view, view_name="south", footprint=_geom())
    assert len(evidence) == 1
    assert evidence[0].boundary_ref == "south-wing-a"
    assert len(evidence[0].frame_transform_hash) == 64


@pytest.mark.parametrize("gate", [
    "correction.envelope_ring_valid", "correction.coverage", "correction.shared_boundary_consistency",
    "correction.window_host_unique", "correction.facade_segment_binding", "correction.envelope_identity_snapshot",
    "correction.envelope_bbox_projection", "correction.envelope_topology_preserved",
])
def test_each_hard_gate_rolls_back(monkeypatch, gate):
    import src.agent.correction.envelope_transform as transform
    before = _geom()
    monkeypatch.setattr(transform, "run_envelope_hard_gates", lambda *a, **k: (EnvelopeGateFinding(gate, False, "injected"),))
    result = apply_v3_envelope_transaction(before, load_core_tolerances(), _envelope())
    assert not result.committed and result.failed_gate_id == gate
    assert result.geom.corrections == before.corrections
    assert result.geom.unsupported == before.unsupported


def test_fault_injection_propagates_unexpected_and_preserves_input(monkeypatch):
    import src.agent.correction.envelope_transform as transform
    before = _geom()
    snapshot = before.model_dump()
    monkeypatch.setattr(transform, "_apply_components", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected")))
    with pytest.raises(RuntimeError, match="injected"):
        apply_v3_envelope_transaction(before, load_core_tolerances(), _envelope())
    assert before.model_dump() == snapshot


def test_evidence_conflict_is_audited_and_identity_failures_are_classified():
    conflict = AuthoritativeEnvelope({"x": EnvelopeAxisResolution("x", "conflict", reason="views disagree")})
    result = apply_v3_envelope_transaction(_geom(), load_core_tolerances(), conflict)
    assert result.geom.conflicts[-1]["reason"] == "views disagree"
    bad = _u_geom(windows=[{"id": "bad", "floor": "F1", "floor_id": "f1", "facade": "South", "span": [0, 1], "z": [1, 2], "room": None}])
    result = apply_v3_envelope_transaction(bad, load_core_tolerances(), _wing(3.1))
    assert result.geom.conflicts[-1]["conflict_type"] == "reference_or_identity_ambiguity"


def test_source_facade_requires_a_real_facade_token_not_substring_guess():
    candidate = EnvelopeCandidate("x", (0, 10.2), 10.2, "dimension", "Southeast", "bad", role="overall", confidence=.95)
    env = AuthoritativeEnvelope({"x": EnvelopeAxisResolution("x", "accepted", (0, 10.2), 10.2, candidate)})
    result = apply_v3_envelope_transaction(_geom(), load_core_tolerances(), env)
    assert result.failed_gate_id == "correction.envelope_evidence_scope"


@pytest.mark.parametrize("schema_version", ["1", "2"])
@pytest.mark.parametrize("state", ["none", "accepted", "skipped", "conflict", "over_tol"])
def test_v1_v2_legacy_envelope_matrix_semantic_snapshots(schema_version, state):
    geom = CorrectedGeometry.model_validate({"schema_version": schema_version, "footprint_x": [0, 10], "footprint_y": [0, 8],
                                             "floors": [{"name": "F1", "z_floor": 0, "ceiling_height": 3,
                                                         "cells": [{"id": "room", "x": [0, 10], "y": [0, 8]}]}]})
    if state == "none":
        env = None
    else:
        status = {"accepted": "accepted", "skipped": "skipped", "conflict": "conflict", "over_tol": "accepted"}[state]
        bounds = (0.0, 10.2 if state == "accepted" else 11.0)
        source = EnvelopeCandidate("x", bounds, bounds[1], "dimension", "South", "legacy", role="overall", confidence=.95)
        env = AuthoritativeEnvelope({"x": EnvelopeAxisResolution("x", status, bounds if status == "accepted" else None,
                                                                    source=source, reason=f"{state} fixture")})
    result = apply_deterministic_core(geom, load_core_tolerances(), authoritative_envelope=env,
                                      capability_profile="orthogonal_polygon" if schema_version == "2" else "rectangular")
    if state == "accepted":
        assert result.footprint_x == [0.0, 10.2]
        assert result.corrections[-1]["rule_id"] == "deterministic_core.envelope_reconcile"
    elif state == "conflict":
        assert result.conflicts[-1]["reason"] == "conflict fixture"
    elif state in {"skipped", "over_tol"}:
        assert result.unsupported
    else:
        assert result.model_dump()["corrections"] == []


# ---------------------------------------------------------------------------
# 摊 C (2026-08-12): EnvelopeAnnotationObservation / observe_envelope_
# annotation_basis locks. See AI_agent/logs/reviews/request/
# 2026-08-12_c_annotation_observable_and_f23_dispatch_claude.md §C.
#
# `_geom()`'s footprint bbox is exactly [0,10] x [0,8] (its L-shaped ring
# still spans that full rectangle -- observe_envelope_annotation_basis only
# ever looks at footprint_bbox(), never the ring's interior shape), so it is
# reused here rather than adding a second geometry fixture.
# ---------------------------------------------------------------------------


def _annotation_envelope(dx: float | None, dy: float | None) -> AuthoritativeEnvelope:
    """Authoritative envelope for `_geom()`'s [0,10] x [0,8] bbox, whose
    accepted bounds are displaced by `dx`/`dy` outward on BOTH the lo and hi
    side of the x/y axis respectively (so every one of the 4 observations
    -- x.lo, x.hi, y.lo, y.hi -- lands in the same basis, keeping each
    lock's assertions uniform). `None` on an axis means that axis has no
    entry in `AuthoritativeEnvelope.axes` at all -- `envelope.axis(axis)`
    then returns `None`, the `no_authoritative_evidence` case.
    """
    axes: dict[str, EnvelopeAxisResolution] = {}
    for axis, base_lo, base_hi, delta, source in (
        ("x", 0.0, 10.0, dx, "South"), ("y", 0.0, 8.0, dy, "West"),
    ):
        if delta is None:
            continue
        bounds = (base_lo - delta, base_hi + delta)
        candidate = EnvelopeCandidate(
            axis, bounds, bounds[1] - bounds[0], "dimension", source, f"src-{axis}",
            role="overall", confidence=.95,
        )
        axes[axis] = EnvelopeAxisResolution(
            axis, "accepted", bounds, bounds[1] - bounds[0], candidate, candidates=(candidate,),
        )
    return AuthoritativeEnvelope(axes)


def test_annotation_basis_names_axis_line_annotation_when_displacement_is_negligible():
    """C.4 lock 1/4: displacement <= output_precision_m (0.01 m) =>
    "axis_line_annotation" -- plan.md's original rule's most-wanted-to-see
    row, and the one `resolve_envelope_move_intents` structurally can never
    produce a signal for (its first `continue`, envelope_transform.py:
    296-297: displacement <= output_precision_m never becomes an intent).

    Self-proving premise: on this exact (geom, envelope, tol), the
    pre-existing "observable channel" (`corrections[].intents`, i.e.
    `resolve_envelope_move_intents`) really does produce nothing at all --
    proving this state was genuinely invisible before this batch, not just
    named differently.
    """
    tol = load_core_tolerances()
    geom, envelope = _geom(), _annotation_envelope(0.0, 0.0)

    intents = resolve_envelope_move_intents(geom, envelope, tol)
    assert intents == ()  # self-proving premise: old channel is silent here

    observations = observe_envelope_annotation_basis(geom, envelope, tol)
    assert len(observations) == 4
    assert all(o.basis == "axis_line_annotation" for o in observations)
    assert all(o.displacement_m == 0.0 for o in observations)
    assert {(o.axis, o.side) for o in observations} == {
        ("x", "lo"), ("x", "hi"), ("y", "lo"), ("y", "hi"),
    }

    # Real entry point, not just the bare function: apply_v3_envelope_
    # transaction wires observe_envelope_annotation_basis in unconditionally
    # (envelope_transform.py:748), on every exit path -- including this
    # "zero intents" no-op commit.
    result = apply_v3_envelope_transaction(geom, tol, envelope)
    assert not result.committed and result.intent_ids == ()
    assert result.annotation_basis == observations


def test_annotation_basis_names_outer_skin_annotation_at_half_wall_thickness_scale():
    """C.4 lock 2/4: output_precision_m < displacement <=
    envelope_reconcile_tol_m (0.12 m, this project's half-wall-thickness
    reference magnitude, per plan.md/the dispatch doc) =>
    "outer_skin_annotation". This is the ONE basis plan.md's original rule
    could already see a raw number for.

    Self-proving premise: on this fixture, `resolve_envelope_move_intents`
    DOES fire (contrast with the other three locks in this group) -- so the
    new observation is not inventing a signal, it is naming one that was
    already a bare, unlabeled numeric delta (plan.md's own third table row:
    "其他值 | 需人工判读"). `EnvelopeMoveIntent` carries no basis
    classification field at all; only the new observation does.
    """
    tol = load_core_tolerances()
    geom, envelope = _geom(), _annotation_envelope(0.12, 0.12)

    intents = resolve_envelope_move_intents(geom, envelope, tol)
    assert len(intents) == 4  # self-proving premise: old channel DOES fire here...
    assert not {"basis", "basis_label"} & set(intents[0].__dict__)  # ...but never names *why*

    observations = observe_envelope_annotation_basis(geom, envelope, tol)
    assert len(observations) == 4
    assert all(o.basis == "outer_skin_annotation" for o in observations)
    assert all(o.displacement_m == pytest.approx(0.12) for o in observations)

    result = apply_v3_envelope_transaction(geom, tol, envelope)
    assert result.committed  # unlike the other three locks: this state really moves geometry
    assert result.geom.footprint_x == [-0.12, 10.12]
    assert result.geom.footprint_y == [-0.12, 8.12]
    assert result.annotation_basis == observations


def test_annotation_basis_names_exceeds_tolerance_beyond_reconcile_tol():
    """C.4 lock 3/4: displacement > envelope_reconcile_tol_m (0.30 m) =>
    "exceeds_tolerance" -- the dispatch doc's "正是最该报警的那一档": with
    the old rule, this reads identically to "no evidence at all".

    Self-proving premise: `resolve_envelope_move_intents` is silent here
    too (its SECOND `continue`, envelope_transform.py:298-299).
    """
    tol = load_core_tolerances()
    geom, envelope = _geom(), _annotation_envelope(0.5, 0.5)

    intents = resolve_envelope_move_intents(geom, envelope, tol)
    assert intents == ()  # self-proving premise: old channel is silent here too

    observations = observe_envelope_annotation_basis(geom, envelope, tol)
    assert len(observations) == 4
    assert all(o.basis == "exceeds_tolerance" for o in observations)
    assert all(o.displacement_m == pytest.approx(0.5) for o in observations)

    result = apply_v3_envelope_transaction(geom, tol, envelope)
    assert not result.committed and result.intent_ids == ()
    assert result.annotation_basis == observations


def test_annotation_basis_names_no_authoritative_evidence_when_axis_unresolved():
    """C.4 lock 4/4: the axis has no accepted envelope resolution at all
    (never appears in `AuthoritativeEnvelope.axes`) => "no_authoritative_
    evidence" -- structurally indistinguishable, through the old channel,
    from "displacement is zero" or "displacement exceeds tolerance": all
    three read as the same silence.

    Self-proving premise: `resolve_envelope_move_intents` is silent here
    too (its `resolution is None -> continue` guard, envelope_transform.py:
    288-289).
    """
    tol = load_core_tolerances()
    geom, envelope = _geom(), _annotation_envelope(None, None)
    assert envelope.axis("x") is None and envelope.axis("y") is None  # fixture sanity

    intents = resolve_envelope_move_intents(geom, envelope, tol)
    assert intents == ()  # self-proving premise: old channel is silent here too

    observations = observe_envelope_annotation_basis(geom, envelope, tol)
    assert len(observations) == 4
    assert all(o.basis == "no_authoritative_evidence" for o in observations)
    assert all(o.displacement_m is None and o.new_value_m is None for o in observations)
    assert all(o.old_value_m is not None for o in observations)  # footprint side is still reported

    result = apply_v3_envelope_transaction(geom, tol, envelope)
    assert not result.committed and result.intent_ids == ()
    assert result.annotation_basis == observations


@pytest.mark.parametrize("dx,dy,expected_basis,committed", [
    # committed exit path (real intents -> _apply_components runs and
    # recomputes footprint_x/y fresh from the ring on its way out).
    (0.12, 0.12, "outer_skin_annotation", True),
    # no-intents early-return path (envelope_transform.py:762-763 returns
    # `before` completely as-is -- nothing downstream re-derives anything).
    # A neuter run during this batch's own verification (2026-08-12,
    # reverted, see execution log) found that a contamination bug written
    # as `geom.footprint_x = [...]` inside observe_envelope_annotation_basis
    # is SILENTLY SELF-HEALED by _apply_components on the committed path
    # (which recomputes footprint_x/y from the ring unconditionally) but
    # DOES surface on the no-intents path -- so both paths are exercised
    # here, not just one.
    (0.0, 0.0, "axis_line_annotation", False),
])
def test_annotation_basis_observation_never_perturbs_existing_transaction_outputs(
    monkeypatch, dx, dy, expected_basis, committed,
):
    """C.4 invariance lock: C.3 §4 requires that adding this observation
    leave every existing judgement byte-for-byte unchanged ("纯观测...加了
    它,所有现有测试的结果必须一字不变"). Proven here by swapping the real
    `observe_envelope_annotation_basis` for a stub that returns a visibly
    different value, and showing every OTHER field
    `apply_v3_envelope_transaction` already promised --
    committed/geom/transaction_id/intent_ids/failed_gate_id -- comes out
    byte-for-byte identical regardless. This is stronger than "existing
    tests still pass" alone: it proves the observation call at
    envelope_transform.py:748 is a pure, non-participating side channel,
    not a hidden dependency the rest of the transaction could ever read
    back -- on BOTH the committed and the no-intents exit path (see the
    parametrize comment above for why one alone is not enough).
    """
    import src.agent.correction.envelope_transform as transform

    tol = load_core_tolerances()
    envelope = _annotation_envelope(dx, dy)
    baseline = apply_v3_envelope_transaction(_geom(), tol, envelope)
    # self-proving premise: this fixture really produces a non-trivial
    # observation -- swapping it for a stub below would be a vacuous no-op
    # test if the real function already returned nothing interesting.
    assert baseline.annotation_basis
    assert all(o.basis == expected_basis for o in baseline.annotation_basis)
    assert baseline.committed is committed

    def stub(*_args, **_kwargs):
        return (EnvelopeAnnotationObservation(
            axis="x", side="lo", basis="exceeds_tolerance", basis_label="stub",
            old_value_m=None, new_value_m=None, displacement_m=None, interpretation="stub",
        ),)

    monkeypatch.setattr(transform, "observe_envelope_annotation_basis", stub)
    swapped = apply_v3_envelope_transaction(_geom(), tol, envelope)

    # the stub really took effect (this is not comparing a cached result)...
    assert swapped.annotation_basis != baseline.annotation_basis
    assert swapped.annotation_basis[0].basis == "exceeds_tolerance"
    # ...yet every other field is untouched.
    for field_name in ("committed", "geom", "transaction_id", "intent_ids", "failed_gate_id"):
        assert getattr(swapped, field_name) == getattr(baseline, field_name), field_name
    # the observation must never leak into the geometry artifact itself --
    # it lives only on EnvelopeTransactionResult, never on `.geom`.
    assert "annotation_basis" not in swapped.geom.model_dump()
