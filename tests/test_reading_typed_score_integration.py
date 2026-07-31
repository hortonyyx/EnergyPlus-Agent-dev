"""Slice 4 RED locks for reading certificates and source-specific scoring."""

from __future__ import annotations

import copy

from tests.test_reading_typed_scoring_slice0 import (
    _denominator_wire,
    _grade_payload,
    _real_payload,
)


def _component(sidecar: dict, source: str, component: str) -> dict:
    return next(
        item
        for item in sidecar["certificates"]["reading_normalization"][
            "component_applicability"
        ]
        if item["source_input_id"] == source
        and item["component"] == component
    )


def test_real_reading_sidecar_publishes_both_certificates_and_channel_scores(
    tmp_path,
):
    sidecar, _ = _grade_payload(tmp_path, _real_payload(), name="real_scored")

    assert sidecar["payload"]["kind"] == "c2_scored"
    normalization = sidecar["certificates"]["reading_normalization"]
    applicability = sidecar["certificates"]["source_applicability"]
    assert normalization is not None
    assert applicability is not None
    assert sidecar["identity"]["reading_normalization_sha256"] == (
        normalization["content_sha256"]
    )
    assert sidecar["identity"]["source_applicability_sha256"] == (
        applicability["content_sha256"]
    )
    assert sidecar["identity"]["denominator_basis_sha256"] == (
        applicability["denominator_basis_sha256"]
    )
    assert sidecar["identity"]["denominator_sha256"] == (
        applicability["denominator_sha256"]
    )
    assert applicability["denominator_atoms"]
    assert sidecar["payload"]["segment_rows"]
    assert sidecar["payload"]["opening_source_rows"]
    channels = {
        item["channel"]: item for item in sidecar["payload"]["channel_applicability"]
    }
    assert channels["plan"]["status"] == "applicable"
    assert channels["elevation"]["status"] == "partially_applicable"
    assert (
        sidecar["payload"]["visibility_counts"][
            "project_convention_vertical_datums"
        ]
        == 4
    )
    assert (
        sidecar["payload"]["visibility_counts"][
            "elevation_local_x_sense_disagreements"
        ]
        == 2
    )


def test_supported_empty_and_invalid_plan_both_retain_targets_as_misses(tmp_path):
    normal = _real_payload()
    empty = copy.deepcopy(normal)
    empty["views"]["1f_view"]["strokes"] = []
    invalid_frame = copy.deepcopy(normal)
    del invalid_frame["views"]["1f_view"]["scale_origin"]["world_x_m"]

    normal_sidecar, _ = _grade_payload(tmp_path, normal, name="plan_normal")
    empty_sidecar, _ = _grade_payload(tmp_path, empty, name="plan_empty")
    invalid_sidecar, _ = _grade_payload(
        tmp_path,
        invalid_frame,
        name="plan_invalid_frame",
    )
    assert _denominator_wire(normal_sidecar) == _denominator_wire(empty_sidecar)
    assert _denominator_wire(normal_sidecar) == _denominator_wire(
        invalid_sidecar
    )
    assert _component(
        empty_sidecar, "1f_view", "plan_segments"
    )["status"] == "applicable"
    invalid_component = _component(
        invalid_sidecar, "1f_view", "plan_segments"
    )
    assert invalid_component["status"] == "not_applicable"
    assert invalid_component["denominator_disposition"] == "retain_as_miss"

    empty_targets = [
        row
        for row in empty_sidecar["payload"]["segment_rows"]
        if row["target_id"] is not None
    ]
    invalid_targets = [
        row
        for row in invalid_sidecar["payload"]["segment_rows"]
        if row["target_id"] is not None
    ]
    assert empty_targets
    assert invalid_targets
    assert all(row["status"] == "miss" for row in empty_targets)
    assert all(row["status"] == "miss" for row in invalid_targets)
    assert sum(row["eligible_units"] for row in empty_targets) == sum(
        row["eligible_units"] for row in invalid_targets
    )


def test_plan_input_id_maps_through_binding_gt_view_set_and_host_stays_na(
    tmp_path,
):
    payload = _real_payload()
    payload["views"]["1f_view"]["strokes"].append(
        {
            "id": "independent-plan-window",
            "pen": "window",
            "geometry": {
                "kind": "line",
                "p1": [4.66, 20.0],
                "p2": [9.46, 20.0],
            },
        }
    )
    sidecar, _ = _grade_payload(tmp_path, payload, name="plan_window")
    source_rows = [
        row
        for row in sidecar["payload"]["opening_source_rows"]
        if row["source_input_id"] == "1f_view"
    ]
    assert source_rows
    assert any(
        row["claim"] == "existence"
        and row["matched_observation_ids"]
        and row["result"] in {"complete", "within_tolerance"}
        for row in source_rows
    )
    host_rows = [
        row
        for row in sidecar["payload"]["claim_rows"]
        if row["claim"] == "host"
    ]
    assert host_rows
    assert all(
        row["result"] == "not_applicable"
        and row["na_reason"] == "reading_topology_unavailable"
        for row in host_rows
        if row["target_kind"] == "window"
    )


def test_reading_policy_uses_channel_specific_source_rows(tmp_path):
    sidecar, _ = _grade_payload(
        tmp_path,
        _real_payload(),
        name="channel_policy",
    )
    criteria = {
        item["criterion_id"]: item
        for item in sidecar["payload"]["score_criteria"]
    }
    elevation_rows = [
        row
        for row in sidecar["payload"]["opening_source_rows"]
        if row["channel"] == "elevation"
        and row["claim"] in {"along", "width", "sill", "head"}
    ]
    assert elevation_rows
    assert criteria["window_elevation_geometry"]["denominator_units"] == sum(
        row["eligible_units"] for row in elevation_rows
    )
    assert criteria["window_elevation_geometry"]["denominator_units"] > 0
