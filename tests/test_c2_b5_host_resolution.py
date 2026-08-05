"""B5 Phase-B gates: resolver, B2b timing, evidence and negative proof."""
from __future__ import annotations

import hashlib
import inspect
import json
import copy
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.agent.correction.config import load_core_tolerances
from src.agent.correction.envelope import (
    AuthoritativeEnvelope,
    EnvelopeAxisResolution,
    EnvelopeCandidate,
    EnvelopeEndpointResolution,
    WingBoundaryEvidence,
)
from src.agent.correction.envelope_transform import (
    _dry_resolve_current_ring,
    apply_v3_envelope_transaction,
    run_envelope_hard_gates,
)
from src.agent.correction.facade_applicability import FacadeApplicabilityInvariantError
from src.agent.correction.facade_visibility import VisibilityTolerances, materialize_all_facade_segments
from src.agent.correction.finalize import PreparedCandidateIdentity, finalize_correction_draw
from src.agent.correction.parse import CorrectionTarget, correction_target
from src.agent.correction.schema import CorrectedGeometry, CorrectedGeometryV3, FieldProvenance, FootprintRing
from src.agent.correction.window_host import (
    NegativeEvidenceDecisionV1,
    WindowEvidenceDecisionV1,
    WindowEvidenceLedgerV1,
    WindowHostClaimsV1,
    WindowHostConflictV1,
    WindowHostResolutionError,
    WindowHostResolutionV1,
    apply_window_host_resolutions,
    derive_window_evidence_ledger,
    map_va_applicability_error,
    resolve_window_hosts,
)
from src.agent.correction.window_sources import (
    ElevationDirectionFactV1,
    build_verified_window_resolver_inputs,
    source_locator,
)
from src.agent.execution.manifest import hash_obj
from src.agent.execution.view_manifest import (
    CaseMetadataSourceRef,
    CompletenessAssertion,
    Coverage,
    OpeningEvidence,
    RequiredViewEntry,
    ViewManifest,
)

H = "a" * 64
RECT = [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]
U_RING = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [7.0, 8.0],
          [7.0, 3.0], [3.0, 3.0], [3.0, 8.0], [0.0, 8.0]]
L_RING = [[0.0, 0.0], [10.0, 0.0], [10.0, 3.0], [4.0, 3.0], [4.0, 8.0], [0.0, 8.0]]
PARTIAL_EAST_RING = [[0.0, 0.0], [10.0, 0.0], [10.0, 5.0], [7.0, 5.0],
                     [7.0, 3.0], [3.0, 3.0], [3.0, 8.0], [0.0, 8.0]]


def _opening_evidence(channel: str, *, complete: bool) -> OpeningEvidence:
    claims = (["existence", "host", "along", "width"] if channel == "plan"
              else ["existence", "along", "width", "sill", "head", "appearance"])
    if not complete:
        return OpeningEvidence(potentially_observable_claims=claims)
    assertion_id = f"complete-{channel}"
    frame, region = (("plan_floor_region", "full_floor") if channel == "plan"
                     else ("elevation_local_along", "full_facade"))
    return OpeningEvidence(
        potentially_observable_claims=claims,
        negative_evidence_capable_claims=["existence"],
        coverage=Coverage(
            frame=frame, region=region, completeness_assertion_id=assertion_id,
        ),
        completeness_assertion=CompletenessAssertion(
            assertion_id=assertion_id,
            source_ref=CaseMetadataSourceRef(
                source="case_metadata", json_pointer=f"/views/{channel}/completeness",
                case_metadata_sha256=H,
            ),
        ),
    )


def _entry(input_id: str, channel: str, *, family: str = "South", complete: bool = False):
    return RequiredViewEntry(
        input_id=input_id, source_image=f"case_data/{input_id}.png", image_sha256=H,
        view_type=channel, floor_ref=1 if channel == "plan" else None,
        declared_direction_token=family if channel == "elevation" else None,
        direction_source="standard_assumption", direction_semantics="building_axis",
        semantics_source="case_metadata", building_view_direction=family if channel == "elevation" else None,
        dimensioned=True, expected_output_id=input_id,
        opening_evidence=_opening_evidence(channel, complete=complete),
    )


def _manifest(*entries):
    payload = {
        "view_manifest_schema_version": "1", "claims_vocab_version": "1",
        "generator_version": "1", "completeness_ruleset_version": "1",
        "case_id": "case", "case_metadata_sha256": H,
        "entries": [entry.model_dump(mode="json") for entry in sorted(entries, key=lambda item: item.input_id)],
    }
    manifest = ViewManifest(**payload, content_sha256=hash_obj(payload))
    return manifest, manifest.model_dump_json().encode("utf-8")


def _reading(channel: str, strokes, *, family: str = "South") -> bytes:
    payload = {"image_kind": channel, "strokes": list(strokes), "uncaptured": []}
    if channel == "elevation":
        payload["facade"] = {
            "view_facade": family, "mirrored": False,
            "local_x_positive": "image_left_to_right",
        }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _context(
    *,
    ring=RECT,
    cells=None,
    facade="South",
    span=(1.0, 2.0),
    z=(1.0, 2.0),
    room="r1",
    plan_geometry=None,
    elevation_geometry=None,
    existence_channels=("plan",),
    plan_complete=False,
    elevation_complete=False,
    source_facade=None,
    existence_method=None,
):
    source_facade = source_facade or facade
    cells = cells or [{"id": "r1", "x": [min(x for x, _ in ring), max(x for x, _ in ring)],
                       "y": [min(y for _, y in ring), max(y for _, y in ring)], "polygon": ring}]
    manifest, raw_manifest = _manifest(
        _entry("plan", "plan", family=source_facade, complete=plan_complete),
        _entry("elevation", "elevation", family=source_facade, complete=elevation_complete),
    )
    plan_strokes = (() if plan_geometry is None else (
        {"id": "P-W", "pen": "window", "geometry": plan_geometry},
    ))
    elevation_strokes = (() if elevation_geometry is None else (
        {"id": "E-W", "pen": "window", "geometry": elevation_geometry},
    ))
    artifacts = {
        "plan": _reading("plan", plan_strokes, family=source_facade),
        "elevation": _reading("elevation", elevation_strokes, family=source_facade),
    }
    locators = {}
    if plan_geometry is not None:
        locators["plan"] = source_locator(
            input_id="plan", observation_id="P-W",
            output_sha256=hashlib.sha256(artifacts["plan"]).hexdigest(),
        )
    if elevation_geometry is not None:
        locators["elevation"] = source_locator(
            input_id="elevation", observation_id="E-W",
            output_sha256=hashlib.sha256(artifacts["elevation"]).hexdigest(),
        )
    windows = []
    if existence_channels:
        windows.append({
            "id": "w1", "floor": "F1", "floor_id": "f1", "facade": facade,
            "span": list(span), "z": list(z), "room": room,
            "provenance": {"existence": {
                "provenance": "observed",
                "source_ids": [locators[channel] for channel in existence_channels],
                "method": existence_method,
            }},
        })
    geom = CorrectedGeometryV3.model_validate({
        "schema_version": "3",
        "footprint_x": [min(x for x, _ in ring), max(x for x, _ in ring)],
        "footprint_y": [min(y for _, y in ring), max(y for _, y in ring)],
        "floors": [{
            "id": "f1", "name": "F1", "z_floor": 0.0, "ceiling_height": 3.0,
            "footprint": {"vertices": ring}, "cells": cells,
        }],
        "windows": windows, "facade_segments": [],
    })
    fact = ElevationDirectionFactV1(
        input_id="elevation", resolved_building_direction=source_facade,
        resolution_source="manifest_building_axis", mirrored=False,
        local_x_positive="image_left_to_right", orientation_output_hash=None,
        adapter_version=None, view_manifest_sha256=manifest.content_sha256,
    )
    verified = build_verified_window_resolver_inputs(
        producer_draw=geom, raw_view_manifest_bytes=raw_manifest,
        raw_reading_artifacts=artifacts, elevation_direction_facts=(fact,),
    )
    return geom, verified


def _materialized(geom):
    return geom.model_copy(update={"facade_segments": list(materialize_all_facade_segments(
        geom, tolerances=VisibilityTolerances(1e-9, 1e-9),
    ))})


def _resolve(geom, verified):
    return resolve_window_hosts(
        _materialized(geom), verified_inputs=verified,
        tolerances=load_core_tolerances(), commit=False,
    )


def _reason(exc) -> str:
    assert isinstance(exc.value, WindowHostResolutionError)
    assert len(exc.value.conflicts) == 1
    return exc.value.conflicts[0].reason_code


def _overall_x_envelope(value: float) -> AuthoritativeEnvelope:
    candidate = EnvelopeCandidate(
        "x", (0.0, value), value, "dimension", "South", "overall-x",
        role="overall", confidence=.99,
    )
    return AuthoritativeEnvelope({
        "x": EnvelopeAxisResolution(
            "x", "accepted", (0.0, value), value, candidate,
            candidates=(candidate,),
        ),
    })


def _wing_envelope(value: float) -> AuthoritativeEnvelope:
    evidence = WingBoundaryEvidence(
        "South", "x", value, "South", "wing-dim", "wing-chain", 1,
        "south-wing", "from", "0" * 64,
    )
    return AuthoritativeEnvelope(
        endpoint_resolutions=(EnvelopeEndpointResolution("accepted", evidence),),
    )


def test_b5_b1_plan_hidden_segment_is_a_real_vg_hidden_edge():
    geom, verified = _context(
        ring=U_RING, facade="East", span=(4.0, 5.0), room="r1",
        plan_geometry={"x_range_m":[2.9, 3.1], "y_range_m":[4.0, 5.0]},
    )
    materialized = _materialized(geom)
    hidden = next(segment for segment in materialized.facade_segments
                  if segment.facade_family == "East" and segment.p1[0] == 3.0)
    assert hidden.visible_intervals == []
    row = resolve_window_hosts(
        materialized, verified_inputs=verified, tolerances=load_core_tolerances(), commit=False,
    ).resolutions[0]
    assert (row.branch, row.facade_segment_id, row.visible_overlap_intervals) == ("plan", hidden.id, ())


def test_b5_b2_elevation_visible_segment_fills_unique_room_and_keeps_ids_distinct(tmp_path: Path):
    geom, verified = _context(
        room=None, plan_geometry=None,
        elevation_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    window = result.geom.windows[0]
    assert window.room == "r1"
    assert window.facade_segment_id and window.facade_segment_id != window.room
    assert result.window_host_claims.resolutions[0].branch == "elevation"
    assert result.window_host_claims.resolutions[0].visible_overlap_intervals


def test_final_commit_writes_one_strict_audit_and_preserves_observed_provenance(tmp_path: Path):
    geom, verified = _context(
        span=(-0.006, 1.0),
        plan_geometry={"x_range_m":[-0.006, 1.0], "y_range_m":[0.0, 0.1]},
    )
    original_source_ids = tuple(geom.windows[0].provenance["existence"].source_ids)
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    rows = [row for row in result.geom.corrections if row.get("kind") == "window_host_resolution"]
    assert len(rows) == 1
    row = rows[0]
    assert row["original_facade_segment_id"] is None
    assert row["original_span"] == {"lo": -0.01, "hi": 1.0}
    assert row["resolved_span"] == {"lo": 0.0, "hi": 1.0}
    assert tuple(row["source_ids"]) == original_source_ids
    assert tuple(result.geom.windows[0].provenance["existence"].source_ids) == original_source_ids


def test_commit_rejects_self_consistently_resigned_resolver_output_tamper():
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    materialized = _materialized(geom)
    claims = resolve_window_hosts(
        materialized, verified_inputs=verified,
        tolerances=load_core_tolerances(), commit=False,
    )

    def independent_sha256(value) -> str:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    row_payload = claims.resolutions[0].model_dump(mode="json")
    row_payload["clamped_span"]["hi"] = 2.1
    unhashed_row = dict(row_payload)
    unhashed_row.pop("resolution_sha256")
    row_payload["resolution_sha256"] = independent_sha256(unhashed_row)
    tampered_row = WindowHostResolutionV1.model_validate_json(json.dumps(row_payload))
    claims_payload = claims.model_dump(mode="json")
    claims_payload["resolutions"] = [tampered_row.model_dump(mode="json")]
    claims_payload["aggregate_sha256"] = independent_sha256(
        [tampered_row.resolution_sha256],
    )
    tampered_claims = WindowHostClaimsV1.model_validate_json(json.dumps(claims_payload))

    with pytest.raises(WindowHostResolutionError) as exc:
        apply_window_host_resolutions(
            materialized, claims=tampered_claims, verified_inputs=verified,
            tolerances=load_core_tolerances(),
        )
    assert _reason(exc) == "resolver_output_tampered"
    assert materialized.windows[0].facade_segment_id is None


def test_b5_b3_cross_segment_rejects_instead_of_using_window_center():
    geom, verified = _context(
        ring=L_RING, facade="North", span=(3.9, 4.1), room=None,
        plan_geometry=None,
        elevation_geometry={"x_range_m":[5.9, 6.1], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "cross_segment_boundary"
    assert len(exc.value.conflicts[0].crossed_segment_ids) == 2


@pytest.mark.parametrize("channel", ["plan", "elevation"])
def test_geo_cross_room_boundary_is_typed_for_each_source_branch(channel):
    cells = [
        {"id": "left", "x": [0.0, 2.0], "y": [0.0, 3.0]},
        {"id": "right", "x": [2.0, 4.0], "y": [0.0, 3.0]},
    ]
    geom, verified = _context(
        cells=cells, span=(1.8, 2.2), room="left" if channel == "plan" else None,
        plan_geometry={"x_range_m":[1.8, 2.2], "y_range_m":[0.0, 0.1]} if channel == "plan" else None,
        elevation_geometry={"x_range_m":[1.8, 2.2], "y_range_m":[1.0, 2.0]} if channel == "elevation" else None,
        existence_channels=(channel,),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "cross_room_boundary"


def test_geo_cell_bbox_cannot_replace_actual_room_boundary():
    cells = [
        {"id": "declared", "x": [0.0, 4.0], "y": [0.0, 3.0],
         "polygon": [[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [4.0, 1.0], [4.0, 3.0], [0.0, 3.0]]},
        {"id": "actual", "x": [2.0, 4.0], "y": [0.0, 1.0]},
    ]
    geom, verified = _context(
        cells=cells, span=(2.5, 3.5), room="declared",
        plan_geometry={"x_range_m":[2.5, 3.5], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "room_mismatch"


def test_source_locator_for_another_window_cannot_attach_by_hash_presence():
    geom, verified = _context(
        span=(1.0, 2.0),
        plan_geometry={"x_range_m":[2.5, 3.5], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "source_geometry_mismatch"


def test_geo_zero_segment_candidate_is_typed():
    geom, verified = _context(
        span=(8.0, 9.0),
        plan_geometry={"x_range_m":[8.0, 9.0], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "zero_segment_candidates"


def test_geo_multiple_overlapping_segment_candidates_reject_without_id_tiebreak():
    geom, verified = _context(
        ring=U_RING, facade="East", span=(4.0, 5.0), room="r1",
        plan_geometry={"x_range_m":[0.0, 10.0], "y_range_m":[4.0, 5.0]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "multiple_segment_candidates"
    assert len(exc.value.conflicts[0].candidate_segment_ids) == 2


def test_plan_plane_filter_keeps_coplanar_segments_for_cross_segment_rejection(monkeypatch):
    geom, verified = _context(
        span=(1.8, 2.2),
        plan_geometry={"x_range_m":[1.8, 2.2], "y_range_m":[0.0, 0.1]},
    )
    materialized = _materialized(geom)
    south = next(row for row in materialized.facade_segments if row.facade_family == "South")
    left = south.model_copy(update={
        "id": f"{south.id}:left", "p2": (2.0, 0.0),
        "world_along_interval": south.world_along_interval.model_copy(update={"hi": 2.0}),
        "visible_intervals": [
            south.world_along_interval.model_copy(update={"hi": 2.0}),
        ],
    })
    right = south.model_copy(update={
        "id": f"{south.id}:right", "p1": (2.0, 0.0),
        "world_along_interval": south.world_along_interval.model_copy(update={"lo": 2.0}),
        "visible_intervals": [
            south.world_along_interval.model_copy(update={"lo": 2.0}),
        ],
    })
    split = materialized.model_copy(update={
        "facade_segments": [
            row for row in materialized.facade_segments if row.id != south.id
        ] + [left, right],
    })
    import src.agent.correction.window_host as host_module
    monkeypatch.setattr(
        host_module, "materialize_current_ring_va_elevation_bindings", lambda **kwargs: (),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        resolve_window_hosts(
            split, verified_inputs=verified, tolerances=load_core_tolerances(), commit=False,
        )
    assert _reason(exc) == "cross_segment_boundary"
    assert set(exc.value.conflicts[0].crossed_segment_ids) == {left.id, right.id}


def test_elevation_segment_not_visible_is_a_typed_safety_rejection(monkeypatch):
    geom, verified = _context(
        room=None, plan_geometry=None,
        elevation_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    materialized = _materialized(geom)
    import src.agent.correction.window_host as host_module
    real = host_module.materialize_current_ring_va_elevation_bindings
    bindings = real(
        geom=materialized,
        manifest=verified.inputs.view_manifest,
        direction_facts=verified.inputs.elevation_direction_facts,
        visibility_tolerances=VisibilityTolerances(1e-9, 1e-9),
    )
    hidden = materialized.model_copy(update={
        "facade_segments": [
            row.model_copy(update={"visible_intervals": []})
            if row.facade_family == "South" else row
            for row in materialized.facade_segments
        ],
    })
    monkeypatch.setattr(
        host_module, "materialize_current_ring_va_elevation_bindings",
        lambda **kwargs: bindings,
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        resolve_window_hosts(
            hidden, verified_inputs=verified, tolerances=load_core_tolerances(), commit=False,
        )
    assert _reason(exc) == "elevation_segment_not_visible"


def test_elevation_binding_facade_mismatch_is_rejected_by_resolver():
    geom, verified = _context(
        facade="South", source_facade="North", room=None, plan_geometry=None,
        elevation_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "facade_mismatch"


def test_resolver_source_channel_missing_is_typed_even_for_defensive_marker_tamper():
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    tampered = copy.copy(verified)
    object.__setattr__(
        tampered, "inputs", verified.inputs.model_copy(update={"claim_links": ()}),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, tampered)
    assert _reason(exc) == "source_channel_missing"


def test_invalid_host_line_is_typed_after_candidate_selection(monkeypatch):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    materialized = _materialized(geom)
    south = next(row for row in materialized.facade_segments if row.facade_family == "South")
    degenerate = south.model_copy(update={"p2": south.p1})
    invalid = materialized.model_copy(update={
        "facade_segments": [
            degenerate if row.id == south.id else row for row in materialized.facade_segments
        ],
    })
    import src.agent.correction.window_host as host_module
    monkeypatch.setattr(
        host_module, "materialize_current_ring_va_elevation_bindings", lambda **kwargs: (),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        resolve_window_hosts(
            invalid, verified_inputs=verified, tolerances=load_core_tolerances(), commit=False,
        )
    assert _reason(exc) == "invalid_host_line"


@pytest.mark.parametrize(
    ("span", "expected"),
    [((-0.005, 1.0), (0.0, 1.0)), ((-0.011, 1.0), "segment_endpoint_overrun")],
)
def test_geo_segment_endpoint_clamp_and_overrun_have_separate_locks(span, expected):
    geom, verified = _context(
        span=span, plan_geometry={"x_range_m":list(span), "y_range_m":[0.0, 0.1]},
    )
    if isinstance(expected, tuple):
        row = _resolve(geom, verified).resolutions[0]
        assert (row.clamped_span.lo, row.clamped_span.hi) == expected
    else:
        with pytest.raises(WindowHostResolutionError) as exc:
            _resolve(geom, verified)
        assert _reason(exc) == expected


def test_geo_overlapping_room_intervals_reject_multiple():
    cells = [
        {"id": "a", "x": [0.0, 4.0], "y": [0.0, 3.0]},
        {"id": "b", "x": [0.0, 4.0], "y": [0.0, 3.0]},
    ]
    geom, verified = _context(
        cells=cells, room="a", plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "multiple_room_interval_candidates"


def test_geo_zero_room_interval_candidate_is_typed():
    cells = [{"id": "r1", "x": [0.0, 1.0], "y": [0.0, 3.0]}]
    geom, verified = _context(
        cells=cells, span=(2.0, 3.0), room="r1",
        plan_geometry={"x_range_m":[2.0, 3.0], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "zero_room_interval_candidates"


def test_elevation_segment_spanning_rooms_fills_only_the_unique_complete_interval():
    cells = [
        {"id": "left", "x": [0.0, 2.0], "y": [0.0, 3.0]},
        {"id": "right", "x": [2.0, 4.0], "y": [0.0, 3.0]},
    ]
    geom, verified = _context(
        cells=cells, span=(2.5, 3.5), room=None, plan_geometry=None,
        elevation_geometry={"x_range_m":[2.5, 3.5], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    row = _resolve(geom, verified).resolutions[0]
    assert row.room_id == "right" and row.facade_segment_id != row.room_id


def test_elevation_prefilled_wrong_room_is_rejected_not_overwritten():
    cells = [
        {"id": "left", "x": [0.0, 2.0], "y": [0.0, 3.0]},
        {"id": "right", "x": [2.0, 4.0], "y": [0.0, 3.0]},
    ]
    geom, verified = _context(
        cells=cells, span=(2.5, 3.5), room="left", plan_geometry=None,
        elevation_geometry={"x_range_m":[2.5, 3.5], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "room_mismatch"


def test_geo_plan_declared_room_mismatch_is_typed():
    cells = [
        {"id": "left", "x": [0.0, 2.0], "y": [0.0, 3.0]},
        {"id": "right", "x": [2.0, 4.0], "y": [0.0, 3.0]},
    ]
    geom, verified = _context(
        cells=cells, span=(2.5, 3.5), room="left",
        plan_geometry={"x_range_m":[2.5, 3.5], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "room_mismatch"


def test_geo_invalid_window_width_is_never_dropped_before_resolver(tmp_path: Path):
    geom, verified = _context(
        span=(1.0, 1.05), plan_geometry={"x_range_m":[1.0, 1.05], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        finalize_correction_draw(
            geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
            verified_window_inputs=verified,
        )
    assert _reason(exc) == "invalid_window_span"


def test_geo_full_parent_face_window_is_a_locked_safety_rejection():
    geom, verified = _context(
        span=(0.0, 4.0), z=(0.0, 3.0),
        plan_geometry={"x_range_m":[0.0, 4.0], "y_range_m":[0.0, 0.1]},
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        _resolve(geom, verified)
    assert _reason(exc) == "invalid_window_span"


def test_b2b_post_resolver_needs_input_rolls_back_without_state_leakage():
    # The 4.0 -> 3.85 envelope makes this full-height opening consume the
    # complete post-transform host face.  Only the post-ring resolver can see
    # that relation, and it must reject atomically as invalid_window_span.
    geom, verified = _context(
        span=(0.0, 3.85), z=(0.0, 3.0),
        plan_geometry={"x_range_m":[0.0, 3.85], "y_range_m":[0.0, 0.1]},
    )
    before = geom.model_dump(mode="json")
    result = apply_v3_envelope_transaction(
        geom, load_core_tolerances(), _overall_x_envelope(3.85),
        verified_window_inputs=verified,
    )
    assert not result.committed
    assert result.failed_gate_id == "correction.window_host_resolution"
    assert result.geom.windows[0].span == [0.0, 3.85]
    assert result.geom.windows[0].facade_segment_id is None
    assert result.geom.facade_segments == []
    assert not any(row.get("kind") == "window_host_resolution"
                   for row in result.geom.corrections)
    assert result.geom.conflicts[-1]["evidence"]["conflicts"][0]["reason_code"] == (
        "invalid_window_span"
    )
    assert geom.model_dump(mode="json") == before


def test_b2b_dry_post_ring_fingerprint_invariant_pierces_transaction(monkeypatch):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    before = geom.model_dump(mode="json")
    import src.agent.correction.envelope_transform as transform
    real = transform.materialize_all_facade_segments
    calls = 0

    def tamper_second_ring(*args, **kwargs):
        nonlocal calls
        calls += 1
        rows = list(real(*args, **kwargs))
        if calls == 2:
            rows[0] = rows[0].model_copy(update={
                "source_footprint_fingerprint": "b" * 64,
            })
        return tuple(rows)

    monkeypatch.setattr(transform, "materialize_all_facade_segments", tamper_second_ring)
    with pytest.raises(WindowHostResolutionError) as exc:
        apply_v3_envelope_transaction(
            geom, load_core_tolerances(), _overall_x_envelope(4.2),
            verified_window_inputs=verified,
        )
    assert calls == 2
    assert {row.upstream_error_code for row in exc.value.conflicts} == {
        "direction_binding_ring_invalid",
    }
    assert all(row.fallback_action == "invariant_no_geometry_commit"
               for row in exc.value.conflicts)
    assert exc.value.phase == "dry_post_transform"
    assert exc.value.context
    assert geom.model_dump(mode="json") == before


def test_b2b_geometry_room_ownership_change_fails_host_parity_and_rolls_back():
    cells = [
        {"id": "left", "x": [0.0, 3.0], "y": [0.0, 8.0]},
        {"id": "right", "x": [7.0, 10.0], "y": [0.0, 8.0]},
        {"id": "bottom", "x": [3.0, 7.0], "y": [0.0, 3.0]},
    ]
    geom, verified = _context(
        ring=U_RING, cells=cells, facade="South", span=(3.05, 3.15),
        room=None, plan_geometry=None,
        elevation_geometry={"x_range_m":[3.05, 3.15], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    result = apply_v3_envelope_transaction(
        geom, load_core_tolerances(), _wing_envelope(3.2),
        verified_window_inputs=verified,
    )
    assert not result.committed
    assert result.failed_gate_id == "correction.window_host_unique"
    assert result.geom.windows[0].room is None
    assert result.geom.windows[0].facade_segment_id is None
    assert result.geom.floors[0].footprint.vertices == geom.floors[0].footprint.vertices
    assert result.geom.conflicts[-1]["reason_unresolved"] == (
        "window source/room/facade host changed"
    )


def test_run_envelope_hard_gates_requires_explicit_window_host_result():
    assert inspect.signature(run_envelope_hard_gates).parameters[
        "window_host_ok"
    ].default is inspect.Parameter.empty


def test_b2b_mixed_post_conflicts_pierce_when_any_row_is_invariant(monkeypatch):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    pre = _resolve(geom, verified)
    common = dict(
        kind="window_host_conflict", conflict_schema_version="1",
        window_id="w1", floor_id="f1", branch="plan", raw_span=None,
        source_input_ids=(), candidate_segment_ids=(), candidate_room_ids=(),
        crossed_segment_ids=(), trusted_negative=(),
        failed_gate_id="correction.window_host_resolution", blocking=True,
    )
    needs_input = WindowHostConflictV1(
        **common, reason_code="zero_segment_candidates", upstream_error_code=None,
        fallback_action="needs_input_no_geometry_commit",
    )
    invariant = WindowHostConflictV1(
        **common, reason_code="direction_binding_invalid",
        upstream_error_code="direction_binding_ring_invalid",
        fallback_action="invariant_no_geometry_commit",
    )
    import src.agent.correction.envelope_transform as transform
    calls = 0

    def mixed_on_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return pre
        raise WindowHostResolutionError(
            (needs_input, invariant), phase="dry_post_transform",
            context={"probe": "mixed"},
        )

    monkeypatch.setattr(transform, "_dry_resolve_current_ring", mixed_on_post)
    with pytest.raises(WindowHostResolutionError) as exc:
        apply_v3_envelope_transaction(
            geom, load_core_tolerances(), _overall_x_envelope(4.2),
            verified_window_inputs=verified,
        )
    assert calls == 2
    assert {row.fallback_action for row in exc.value.conflicts} == {
        "needs_input_no_geometry_commit", "invariant_no_geometry_commit",
    }


def test_room_interval_merge_receives_span_epsilon_not_plane_epsilon(monkeypatch):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    tolerances = replace(
        load_core_tolerances(),
        window_host_plane_epsilon_m=1e-10,
        window_host_span_epsilon_m=1e-9,
    )
    import src.agent.correction.window_host as host_module
    real = host_module._room_intervals
    seen = []

    def spy(*args, **kwargs):
        seen.append((kwargs["plane_eps"], kwargs["span_eps"]))
        return real(*args, **kwargs)

    monkeypatch.setattr(host_module, "_room_intervals", spy)
    resolve_window_hosts(
        _materialized(geom), verified_inputs=verified,
        tolerances=tolerances, commit=False,
    )
    assert seen == [(1e-10, 1e-9)]


def test_b5_b4_b2b_rederives_pre_and_post_ring_bindings(monkeypatch):
    geom, verified = _context(
        span=(1.0, 2.0), plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    candidate = EnvelopeCandidate(
        "x", (0.0, 4.2), 4.2, "dimension", "South", "overall-x",
        role="overall", confidence=.99,
    )
    envelope = AuthoritativeEnvelope({
        "x": EnvelopeAxisResolution(
            "x", "accepted", (0.0, 4.2), 4.2, candidate, candidates=(candidate,),
        ),
    })
    import src.agent.correction.window_host as host_module
    real = host_module.materialize_current_ring_va_elevation_bindings
    seen = []

    def spy(**kwargs):
        rows = real(**kwargs)
        seen.append((rows[0].source_footprint_fingerprint, rows[0].frame_transform_sha256))
        return rows

    monkeypatch.setattr(host_module, "materialize_current_ring_va_elevation_bindings", spy)
    result = apply_v3_envelope_transaction(
        geom, load_core_tolerances(), envelope, verified_window_inputs=verified,
    )
    assert result.committed
    assert len(seen) == 2 and seen[0] != seen[1]
    assert result.geom.facade_segments == []
    assert result.geom.windows[0].facade_segment_id is None


def test_finalize_calls_binding_on_dry_pre_dry_post_and_final_current_ring(monkeypatch, tmp_path: Path):
    geom, verified = _context(
        span=(1.0, 2.0), plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    candidate = EnvelopeCandidate(
        "x", (0.0, 4.2), 4.2, "dimension", "South", "overall-x",
        role="overall", confidence=.99,
    )
    envelope = AuthoritativeEnvelope({
        "x": EnvelopeAxisResolution(
            "x", "accepted", (0.0, 4.2), 4.2, candidate, candidates=(candidate,),
        ),
    })
    import src.agent.correction.finalize as finalize_module
    import src.agent.correction.window_host as host_module
    monkeypatch.setattr(finalize_module, "extract_authoritative_envelope", lambda *args, **kwargs: envelope)
    real = host_module.materialize_current_ring_va_elevation_bindings
    seen = []

    def spy(**kwargs):
        rows = real(**kwargs)
        seen.append((rows[0].source_footprint_fingerprint, rows[0].frame_transform_sha256))
        return rows

    monkeypatch.setattr(host_module, "materialize_current_ring_va_elevation_bindings", spy)
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    # dry-pre is the original ring; dry-post plus every final recomputation use
    # the transformed ring.  No 13-field binding crosses that boundary.
    assert len(seen) >= 5
    assert seen[0] != seen[1]
    assert all(item == seen[1] for item in seen[1:])
    assert result.geom.footprint_x == [0.0, 4.2]
    assert result.window_evidence_ledger.output_sha256 == result.prepared_candidate_identity.output_sha256


def test_bind_5_dry_ring_fingerprint_tamper_maps_to_typed_invariant(monkeypatch):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    import src.agent.correction.envelope_transform as transform
    real = transform.materialize_all_facade_segments

    def tampered(*args, **kwargs):
        rows = list(real(*args, **kwargs))
        rows[0] = rows[0].model_copy(update={"source_footprint_fingerprint": "b" * 64})
        return tuple(rows)

    monkeypatch.setattr(transform, "materialize_all_facade_segments", tampered)
    with pytest.raises(WindowHostResolutionError) as exc:
        _dry_resolve_current_ring(
            geom, verified_window_inputs=verified, tol=load_core_tolerances(),
            phase="dry_pre_transform",
        )
    row = exc.value.conflicts[0]
    assert (row.upstream_error_code, row.reason_code, row.fallback_action) == (
        "direction_binding_ring_invalid", "direction_binding_invalid", "invariant_no_geometry_commit",
    )
    assert exc.value.phase == "dry_pre_transform"
    assert exc.value.context.get("upstream_error")


def test_bind_6_dry_multifloor_ring_incompatibility_maps_to_typed_invariant():
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    first = geom.floors[0]
    second = first.model_copy(deep=True, update={
        "id": "f2", "name": "F2", "z_floor": 3.0,
        "footprint": FootprintRing(vertices=[(0.0, 0.0), (5.0, 0.0), (5.0, 3.0), (0.0, 3.0)]),
        "cells": [first.cells[0].model_copy(update={"id": "r2", "x": [0.0, 5.0]})],
    })
    incompatible = geom.model_copy(deep=True, update={"floors": [first, second]})
    with pytest.raises(WindowHostResolutionError) as exc:
        _dry_resolve_current_ring(
            incompatible, verified_window_inputs=verified, tol=load_core_tolerances(),
            phase="dry_post_transform",
        )
    assert {row.upstream_error_code for row in exc.value.conflicts} == {
        "direction_binding_ring_incompatible",
    }
    assert all(row.fallback_action == "invariant_no_geometry_commit" for row in exc.value.conflicts)
    assert exc.value.phase == "dry_post_transform"
    assert exc.value.context


def test_finalize_marker_backed_core_floor_reference_tamper_hits_identity_invariant(
    monkeypatch, tmp_path: Path,
):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    import src.agent.correction.finalize as finalize_module

    def tamper_core(
        candidate, tol=None, *, authoritative_envelope=None,
        capability_profile="rectangular", verified_window_inputs=None,
    ):
        candidate.windows[0].floor_id = "tampered-floor"
        return candidate

    monkeypatch.setattr(finalize_module, "apply_deterministic_core", tamper_core)
    with pytest.raises(ValueError, match="finalize invariant"):
        finalize_correction_draw(
            geom, vector_dir=tmp_path,
            target=correction_target("orthogonal_polygon"),
            verified_window_inputs=verified,
        )


def test_legacy_v1_finalize_rejects_misrouted_verified_window_marker(tmp_path: Path):
    _, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    legacy = {
        "schema_version": "1", "footprint_x": [0, 4], "footprint_y": [0, 3],
        "floors": [{
            "name": "F1", "z_floor": 0, "ceiling_height": 3,
            "cells": [{"id": "r1", "x": [0, 4], "y": [0, 3]}],
        }],
    }
    with pytest.raises(ValueError, match="legacy v1/v2 finalize forbids"):
        finalize_correction_draw(
            legacy, vector_dir=tmp_path, target=correction_target("rectangular"),
            verified_window_inputs=verified,
        )


def test_legacy_v2_finalize_rejects_misrouted_verified_window_marker(tmp_path: Path):
    _, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    legacy = CorrectedGeometry.model_validate({
        "schema_version": "2", "footprint_x": [0, 4], "footprint_y": [0, 3],
        "floors": [{
            "name": "F1", "z_floor": 0, "ceiling_height": 3,
            "cells": [{"id": "r1", "x": [0, 4], "y": [0, 3]}],
        }],
    })
    target = CorrectionTarget("2", CorrectedGeometry, "rectangular")
    with pytest.raises(ValueError, match="legacy v1/v2 finalize forbids"):
        finalize_correction_draw(
            legacy, vector_dir=tmp_path, target=target,
            verified_window_inputs=verified,
        )


def test_b5_b5_complete_other_channel_negative_blocks(tmp_path: Path):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
        elevation_complete=True,
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        finalize_correction_draw(
            geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
            verified_window_inputs=verified,
        )
    assert _reason(exc) == "trusted_negative_conflict"
    assert exc.value.conflicts[0].trusted_negative[0].covers_complete_target
    assert geom.windows[0].facade_segment_id is None


def test_negative_without_manifest_completeness_is_uncorroborated(tmp_path: Path):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
        elevation_complete=False,
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    elevation = next(row for row in result.window_evidence_ledger.decisions[0].negative_evidence
                     if row.channel == "elevation")
    assert elevation.outcome == "uncorroborated"
    assert result.geom.windows[0].facade_segment_id is not None


def test_reference_positive_source_is_excluded_from_negative_inputs(tmp_path: Path):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
        elevation_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[1.0, 2.0]},
        existence_channels=("plan", "elevation"), elevation_complete=True,
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    elevation = next(row for row in result.window_evidence_ledger.decisions[0].negative_evidence
                     if row.channel == "elevation")
    assert elevation.positive_evidence_declared and elevation.outcome == "positive"
    assert result.window_evidence_ledger.decisions[0].corroboration_status == "supported"


def test_hidden_other_channel_negative_is_uncorroborated_and_does_not_delete_window(tmp_path: Path):
    geom, verified = _context(
        ring=U_RING, facade="East", span=(4.0, 5.0), room="r1",
        plan_geometry={"x_range_m":[2.9, 3.1], "y_range_m":[4.0, 5.0]},
        elevation_complete=True,
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    elevation = next(row for row in result.window_evidence_ledger.decisions[0].negative_evidence
                     if row.channel == "elevation")
    assert elevation.outcome == "uncorroborated"
    assert not elevation.covers_complete_target
    assert len(result.geom.windows) == 1 and result.geom.windows[0].facade_segment_id


def test_partial_visible_negative_coverage_is_not_promoted_to_complete(tmp_path: Path):
    geom, verified = _context(
        ring=PARTIAL_EAST_RING, facade="East", span=(4.0, 6.0), room="r1",
        plan_geometry={"x_range_m":[2.9, 3.1], "y_range_m":[4.0, 6.0]},
        elevation_complete=True,
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    elevation = next(row for row in result.window_evidence_ledger.decisions[0].negative_evidence
                     if row.channel == "elevation")
    assert elevation.negative_intervals
    assert not elevation.covers_complete_target
    assert elevation.outcome == "uncorroborated"


def test_trusted_negative_is_symmetric_elevation_positive_plan_complete(tmp_path: Path):
    geom, verified = _context(
        room=None, plan_geometry=None, plan_complete=True,
        elevation_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[1.0, 2.0]},
        existence_channels=("elevation",),
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        finalize_correction_draw(
            geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
            verified_window_inputs=verified,
        )
    assert _reason(exc) == "trusted_negative_conflict"
    assert exc.value.conflicts[0].trusted_negative[0].channel == "plan"


def test_attribute_zero_intersection_is_owned_by_va_mapper(tmp_path: Path):
    geom, first = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
        elevation_geometry={"x_range_m":[3.0, 4.0], "y_range_m":[1.0, 2.0]},
        existence_channels=("plan",),
    )
    elevation_source = next(source for source in first.inputs.source_windows if source.channel == "elevation")
    window = geom.windows[0].model_copy(deep=True)
    window.provenance["width"] = FieldProvenance(
        provenance="observed", source_ids=[elevation_source.source_locator],
    )
    geom = geom.model_copy(update={"windows": [window]})
    verified = build_verified_window_resolver_inputs(
        producer_draw=geom,
        raw_view_manifest_bytes=first.raw_view_manifest_bytes,
        raw_reading_artifacts=dict(first.raw_reading_artifacts),
        elevation_direction_facts=first.inputs.elevation_direction_facts,
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        finalize_correction_draw(
            geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
            verified_window_inputs=verified,
        )
    row = exc.value.conflicts[0]
    assert (row.reason_code, row.upstream_error_code) == (
        "claim_evidence_invalid", "va_claim_ledger_invalid",
    )


def test_va_existence_ledger_drift_is_mapped_in_derive_leg(
    monkeypatch, tmp_path: Path,
):
    result = _evidence_result(tmp_path)
    import src.agent.correction.window_host as host_module

    def reject_existence(**kwargs):
        raise FacadeApplicabilityInvariantError(
            "va_claim_ledger_invalid", {"opening_id": "w1", "claim": "existence"},
        )

    monkeypatch.setattr(
        host_module, "derive_opening_claim_applicability", reject_existence,
    )
    with pytest.raises(WindowHostResolutionError) as exc:
        derive_window_evidence_ledger(
            result.geom,
            host_claims=result.window_host_claims,
            verified_inputs=result.verified_window_resolver_inputs,
            candidate_identity=result.prepared_candidate_identity,
            tolerances=load_core_tolerances(),
        )
    row = exc.value.conflicts[0]
    assert (row.reason_code, row.upstream_error_code, row.fallback_action) == (
        "va_identity_invalid", "va_claim_ledger_invalid", "invariant_no_geometry_commit",
    )
    assert exc.value.phase == "final"
    assert exc.value.context == {"opening_id": "w1", "claim": "existence"}


def test_va_stale_candidate_identity_is_rejected_in_derive_leg(tmp_path: Path):
    result = _evidence_result(tmp_path)
    stale = copy.copy(result.prepared_candidate_identity)
    object.__setattr__(stale, "output_bytes", b"stale-output")
    with pytest.raises(WindowHostResolutionError) as exc:
        derive_window_evidence_ledger(
            result.geom,
            host_claims=result.window_host_claims,
            verified_inputs=result.verified_window_resolver_inputs,
            candidate_identity=stale,
            tolerances=load_core_tolerances(),
        )
    assert {row.reason_code for row in exc.value.conflicts} == {"va_identity_invalid"}
    assert {row.upstream_error_code for row in exc.value.conflicts} == {"va_identity_mismatch"}
    assert all(row.fallback_action == "invariant_no_geometry_commit"
               for row in exc.value.conflicts)


def test_product_self_reported_completeness_does_not_change_va_negative_decision(
    tmp_path: Path,
):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
        elevation_complete=False,
        existence_method="product_self_report: elevation complete; no opening seen",
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    elevation = next(
        row for row in result.window_evidence_ledger.decisions[0].negative_evidence
        if row.channel == "elevation"
    )
    assert elevation.outcome == "uncorroborated"
    assert not elevation.negative_evidence_capable
    assert elevation.completeness_assertion_id is None
    assert result.geom.windows[0].facade_segment_id is not None


def test_positive_and_trusted_negative_same_source_is_structurally_unrepresentable():
    with pytest.raises(ValidationError, match="trusted negative requires complete, non-positive"):
        NegativeEvidenceDecisionV1(
            source_input_id="elevation", channel="elevation", claim="existence",
            positive_evidence_declared=True,
            negative_evidence_capable=True,
            completeness_assertion_id="complete-elevation",
            coverage_frame="elevation_local_along",
            coverage_region="full_facade",
            negative_intervals=(),
            covers_complete_target=True,
            outcome="trusted_negative_conflict",
        )


def test_b5_b6_zero_window_totality_has_empty_host_and_evidence_hashes(tmp_path: Path):
    geom, verified = _context(
        plan_geometry=None, elevation_geometry=None, existence_channels=(),
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    empty_hash = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
    assert result.window_host_claims.resolutions == ()
    assert result.window_host_claims.aggregate_sha256 == empty_hash
    assert result.window_evidence_ledger.decisions == ()
    assert result.window_evidence_ledger.aggregate_sha256 == empty_hash


def test_b5_b6_nonempty_window_host_evidence_and_audit_sets_are_total(tmp_path: Path):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    geom_ids = {window.id for window in result.geom.windows}
    host_ids = {row.window_id for row in result.window_host_claims.resolutions}
    evidence_ids = {row.window_id for row in result.window_evidence_ledger.decisions}
    audit_ids = {row["window_id"] for row in result.geom.corrections
                 if row.get("kind") == "window_host_resolution"}
    assert geom_ids == host_ids == evidence_ids == audit_ids == {"w1"}
    assert result.window_host_claims.facade_segments_sha256 == result.window_evidence_ledger.facade_segments_sha256


def test_b5_b7_candidate_identity_uses_exact_writer_serializer_bytes(tmp_path: Path):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    result = finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )
    identity = result.prepared_candidate_identity
    assert identity.output_bytes == result.geom.model_dump_json(indent=2).encode("utf-8")
    assert identity.output_sha256 == hashlib.sha256(identity.output_bytes).hexdigest()
    assert result.verified_window_resolver_inputs is verified
    assert result.window_evidence_ledger.output_sha256 == identity.output_sha256
    assert result.window_evidence_ledger.feature_states_sha256 == identity.feature_states_sha256


def test_candidate_identity_rejects_placeholder_output_hash():
    with pytest.raises(ValueError, match="candidate_output_identity_drift"):
        PreparedCandidateIdentity(
            output_bytes=b"{}", output_sha256="0" * 64,
            feature_states_bytes=b"{}", feature_states_sha256="0" * 64,
        )


def test_candidate_identity_rejects_placeholder_feature_states_hash():
    with pytest.raises(ValueError, match="candidate_feature_states_identity_drift"):
        PreparedCandidateIdentity(
            output_bytes=b"{}", output_sha256=hashlib.sha256(b"{}").hexdigest(),
            feature_states_bytes=b"{}", feature_states_sha256="0" * 64,
        )


def _evidence_result(tmp_path):
    geom, verified = _context(
        plan_geometry={"x_range_m":[1.0, 2.0], "y_range_m":[0.0, 0.1]},
    )
    return finalize_correction_draw(
        geom, vector_dir=tmp_path, target=correction_target("orthogonal_polygon"),
        verified_window_inputs=verified,
    )


def test_evidence_decision_hash_tamper_rejected(tmp_path: Path):
    ledger = _evidence_result(tmp_path).window_evidence_ledger
    payload = ledger.decisions[0].model_dump()
    payload["evidence_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="evidence_sha256"):
        WindowEvidenceDecisionV1.model_validate(payload)


def test_evidence_aggregate_hash_tamper_rejected(tmp_path: Path):
    ledger = _evidence_result(tmp_path).window_evidence_ledger
    payload = ledger.model_dump()
    payload["aggregate_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="aggregate_sha256"):
        WindowEvidenceLedgerV1.model_validate(payload)


def test_evidence_content_hash_tamper_rejected(tmp_path: Path):
    ledger = _evidence_result(tmp_path).window_evidence_ledger
    payload = ledger.model_dump()
    payload["content_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="content_sha256"):
        WindowEvidenceLedgerV1.model_validate(payload)


def test_va_direction_error_mapper_has_independent_lock(tmp_path: Path):
    result = _evidence_result(tmp_path)
    rows = map_va_applicability_error(
        FacadeApplicabilityInvariantError("va_direction_unresolved", {"input_id": "elevation"}),
        host_claims=result.window_host_claims,
        verified_inputs=result.verified_window_resolver_inputs,
    )
    assert {row.reason_code for row in rows} == {"direction_binding_invalid"}


def test_va_identity_error_mapper_has_invariant_fallback_lock(tmp_path: Path):
    result = _evidence_result(tmp_path)
    rows = map_va_applicability_error(
        FacadeApplicabilityInvariantError("va_identity_mismatch", {}),
        host_claims=result.window_host_claims,
        verified_inputs=result.verified_window_resolver_inputs,
    )
    assert {row.reason_code for row in rows} == {"va_identity_invalid"}
    assert {row.fallback_action for row in rows} == {"invariant_no_geometry_commit"}


def test_va_unknown_error_code_never_fails_open(tmp_path: Path):
    result = _evidence_result(tmp_path)
    with pytest.raises(RuntimeError, match="unknown facade applicability error"):
        map_va_applicability_error(
            FacadeApplicabilityInvariantError("new_unmapped_code", {}),
            host_claims=result.window_host_claims,
            verified_inputs=result.verified_window_resolver_inputs,
        )


def test_va_mapper_cannot_emit_an_empty_typed_conflict_tuple():
    geom, verified = _context(
        plan_geometry=None, elevation_geometry=None, existence_channels=(),
    )
    empty_claims = _resolve(geom, verified)
    with pytest.raises(RuntimeError, match="no host resolution for a typed conflict"):
        map_va_applicability_error(
            FacadeApplicabilityInvariantError("va_identity_mismatch", {}),
            host_claims=empty_claims,
            verified_inputs=verified,
        )


def test_evidence_deriver_candidate_identity_has_a_concrete_type_annotation():
    annotation = inspect.signature(derive_window_evidence_ledger).parameters[
        "candidate_identity"
    ].annotation
    assert annotation not in {inspect.Parameter.empty, ""}
    assert "PreparedCandidateIdentity" in str(annotation)
