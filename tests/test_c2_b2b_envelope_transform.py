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
    EnvelopeGateFinding, EnvelopeTransformRejected, apply_v3_envelope_transaction,
)
from src.agent.correction.footprint import floor_footprint_fingerprint
from src.agent.correction.parse import ensure_corrected_geometry
from src.agent.correction.schema import CorrectedGeometry
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
                "x_range": list(window.span), "y_range": [0.0, 0.1],
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
