"""Synthetic checks for candidate-bound architectural inference evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.tool_scripts import bim_agent_inference as inference


def _rehash(source):
    value = {key: item for key, item in source.items() if key != "source_model_sha256"}
    source["source_model_sha256"] = hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode()).hexdigest()
    return source


def _source(version=1):
    spaces = [
        {"id": "A", "floor_id": "F1", "polygon": [[0, 0], [4, 0], [4, 3], [0, 3]],
         "z_floor": 0, "height": 3, "role": "office"},
        {"id": "B", "floor_id": "F1", "polygon": [[4, 0], [6, 0], [6, 3], [4, 3]],
         "z_floor": 0, "height": 3, "role": "corridor"},
        {"id": "U", "floor_id": "F2", "polygon": [[0, 0], [5, 0], [5, 2], [0, 2]],
         "z_floor": 3, "height": 4, "role": "office"},
    ]
    boundaries = [
        {"id": "bA", "space_id": "A", "geometry_type": "wall",
         "vertices": [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]},
        {"id": "bB", "space_id": "B", "geometry_type": "wall",
         "vertices": [[4, 0, 0], [6, 0, 0], [6, 0, 3], [4, 0, 3]]},
        {"id": "bU", "space_id": "U", "geometry_type": "wall",
         "vertices": [[0, 0, 3], [5, 0, 3], [5, 0, 7], [0, 0, 7]]},
    ]
    openings = [
        {"id": "d1", "kind": "door", "host_boundary_id": "bA", "space_ids": ["A", "B"],
         "exterior": False, "connectivity": "unknown",
         "vertices": [[1.5, 0, 0], [2.5, 0, 0], [2.5, 0, 2], [1.5, 0, 2]]},
        {"id": "w1", "kind": "window", "host_boundary_id": "bA", "space_ids": ["A"],
         "exterior": True, "connectivity": "unknown",
         "vertices": [[0.2, 0, 1], [0.8, 0, 1], [0.8, 0, 2], [0.2, 0, 2]]},
        {"id": "w2", "kind": "window", "host_boundary_id": "bA", "space_ids": ["A"],
         "exterior": True, "connectivity": "unknown",
         "vertices": [[2.5, 0, 1], [3, 0, 1], [3, 0, 2], [2.5, 0, 2]]},
        {"id": "wU", "kind": "window", "host_boundary_id": "bU", "space_ids": ["U"],
         "exterior": True, "connectivity": "unknown",
         "vertices": [[1, 0, 4.2], [2, 0, 4.2], [2, 0, 5.7], [1, 0, 5.7]]},
    ]
    if version == 2:
        spaces[0] = {**spaces[0], "role": "meeting"}
        spaces[1] = {"id": "C", "floor_id": "F1", "polygon": [[4, 0], [7, 0], [7, 3], [4, 3]],
                     "z_floor": 0, "height": 3, "role": "corridor"}
        boundaries[1] = {"id": "bC", "space_id": "C", "geometry_type": "wall",
                         "vertices": [[4, 0, 0], [7, 0, 0], [7, 0, 3], [4, 0, 3]]}
        openings[0] = {**openings[0], "space_ids": ["A", "C"],
                       "vertices": [[1, 0, 0], [2.2, 0, 0], [2.2, 0, 2], [1, 0, 2]]}
        openings[2] = {**openings[2], "vertices": [[2.4, 0, 1], [3, 0, 1], [3, 0, 2], [2.4, 0, 2]]}
        openings.append({"id": "w3", "kind": "window", "host_boundary_id": "bC", "space_ids": ["C"],
                         "exterior": True, "connectivity": "unknown",
                         "vertices": [[5, 0, 1], [6, 0, 1], [6, 0, 2], [5, 0, 2]]})
        openings.append({"id": "d2", "kind": "passage", "host_boundary_id": "bC",
                         "space_ids": ["C"], "exterior": True, "connectivity": "open",
                         "vertices": [[4.2, 0, 0], [4.8, 0, 0], [4.8, 0, 2], [4.2, 0, 2]]})
    connection_spaces = ["A", "B"] if version == 1 else ["A", "C"]
    return _rehash({
        "schema_version": "source_bim_v3", "spaces": spaces, "boundaries": boundaries,
        "openings": openings,
        "floors": [{"id": "F1", "spanning_space_ids": []},
                   {"id": "F2", "spanning_space_ids": ["U"]}],
        "connections": [{"opening_id": "d1", "kind": "door", "space_ids": connection_spaces,
                         "exterior": False, "state": "unknown"}],
    })


class _Toolkit:
    def __init__(self, run: Path, readonly=False):
        self.run = run
        self.readonly = readonly
        self.events = []

    def candidate_path(self, candidate):
        path = self.run / candidate
        if candidate not in {"candidate_01", "candidate_02"} or not path.is_dir():
            raise ValueError("unknown candidate")
        return path

    def log(self, action, data):
        self.events.append((action, data))


class _Server:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorate(function):
            self.tools[function.__name__] = function
            return function
        return decorate


def _run(tmp_path):
    run = tmp_path / "run"
    for name, source in (("candidate_01", _source(1)), ("candidate_02", _source(2))):
        folder = run / name
        folder.mkdir(parents=True)
        (folder / "source_model.json").write_text(json.dumps(source, indent=2) + "\n")
    return run


def test_record_inference_validates_evidence_objects_and_detects_candidate_mutation(tmp_path):
    run = _run(tmp_path)
    toolkit = _Toolkit(run)
    declaration = {"statement": "The two saved spaces form an office and corridor pair.",
                   "basis": "inferred", "reason": "The saved roles and connected doorway support it.",
                   "source_refs": ["mesh_observation_001"],
                   "object_refs": [{"kind": "space", "id": "A"},
                                   {"kind": "opening", "id": "d1"}]}
    record = inference.record_inference(toolkit, json.dumps(declaration), "candidate_01")
    assert record["candidate_binding"]["source_model_sha256"] == _source(1)["source_model_sha256"]
    saved = run / record["record_file"]
    immutable_bytes = saved.read_bytes()
    assert inference.inspect_inference(toolkit, record["inference_id"])["binding_status"]["status"] == "current"

    explicit_gap = {"statement": "Internal finish is represented generically.", "basis": "simplified",
                    "reason": "No finish schedule was supplied.", "source_refs": [],
                    "missing_information": ["finish schedule"]}
    inference.record_inference(toolkit, json.dumps(explicit_gap))
    assert saved.read_bytes() == immutable_bytes
    with pytest.raises(ValueError, match="observed declarations require"):
        inference.record_inference(toolkit, json.dumps({**explicit_gap, "basis": "observed"}))
    with pytest.raises(ValueError, match="explicit missing_information"):
        inference.record_inference(toolkit, json.dumps({**explicit_gap, "missing_information": []}))
    with pytest.raises(ValueError, match="unknown space"):
        inference.record_inference(toolkit, json.dumps({**declaration,
            "object_refs": [{"kind": "space", "id": "absent"}]}), "candidate_01")

    source_path = run / "candidate_01/source_model.json"
    mutated = json.loads(source_path.read_text())
    mutated["spaces"][0]["role"] = "silently changed"
    source_path.write_text(json.dumps(mutated))
    status = inference.inspect_inference(toolkit, record["inference_id"])["binding_status"]
    assert status["status"] == "unavailable_or_invalid"
    with pytest.raises(ValueError, match="changed without a matching source hash"):
        inference.audit_inference_candidate(toolkit, "candidate_01")


def test_audit_reports_saved_dimensions_membership_doors_and_exact_entity_diff(tmp_path):
    run = _run(tmp_path)
    toolkit = _Toolkit(run)
    summary = inference.audit_inference_candidate(toolkit, "candidate_01")
    assert summary["counts"] == {"spaces": 3, "boundaries": 3, "openings": 4,
                                 "windows": 3, "doors": 1, "other_openings": 0}
    assert summary["space_dimension_ranges"] == {
        "bbox_x_span_m": {"min": 2, "max": 5}, "bbox_y_span_m": {"min": 2, "max": 3},
        "height_m": {"min": 3, "max": 4}, "footprint_area_m2": {"min": 6, "max": 12}}
    assert summary["window_count_distribution"] == {0: 1, 1: 1, 2: 1}
    assert summary["window_dimension_ranges"] == {
        "width_m": {"min": 0.5, "max": 1.0}, "height_m": {"min": 1.0, "max": 1.5},
        "sill_above_source_space_base_m": {"min": 1.0, "max": pytest.approx(1.2)},
        "sill_reference": "each referenced source space z_floor; not an assumed storey datum"}
    assert summary["floor_membership_counts"] == [
        {"floor_id": "F1", "space_count": 2, "declared_spanning_space_count": 0},
        {"floor_id": "F2", "space_count": 1, "declared_spanning_space_count": 1}]
    assert summary["door_summary"]["width_m"] == {"min": 1.0, "max": 1.0}
    assert summary["door_summary"]["height_m"] == {"min": 2.0, "max": 2.0}
    assert summary["door_summary"]["host_end_clearance_m"] == {"min": 1.5, "max": 1.5}
    assert summary["door_summary"]["midpoint_measured_count"] == 1
    assert summary["door_summary"]["exactly_centered_count"] == 1
    assert summary["door_summary"]["exactly_centered_id_sample"] == ["d1"]
    assert summary["door_summary"]["exactly_centered_sample_truncated"] is False
    assert summary["door_summary"]["exactly_centered_numerical_tolerance_m"] == 1e-6
    assert "not an architectural acceptance threshold" in summary["door_summary"]["midpoint_interpretation"]
    audit = json.loads((run / summary["audit_file"]).read_text())
    assert audit["room_roles"]["office"]["space_ids"] == ["A", "U"]
    assert audit["window_counts"]["by_space"] == {"A": 2, "B": 0, "U": 1}
    upper_window = next(row for row in audit["windows"] if row["id"] == "wU")
    assert upper_window["width_m"] == 1
    assert upper_window["height_m"] == pytest.approx(1.5)
    assert upper_window["sills_by_source_space"] == [{
        "space_id": "U", "source_space_z_floor_m": 3,
        "reference": "source_space_base_not_assumed_storey",
        "sill_above_source_space_base_m": pytest.approx(1.2)}]
    assert audit["floor_membership"][1]["space_ids"] == ["U"]
    door = audit["doors"][0]
    assert door["width_m"] == 1
    assert door["host_end_clearance_m"] == [1.5, 1.5]
    assert door["midpoint_along_host_from_start_m"] == 2
    assert door["normalized_midpoint_position_from_host_start"] == .5
    assert door["midpoint_distance_from_host_midpoint_m"] == 0
    assert door["exactly_centered_numerically"] is True
    assert door["endpoint_perpendicular_offset_m"] == [0, 0]
    assert door["connection_records"][0]["space_ids"] == ["A", "B"]
    compared = inference.audit_inference_candidate(toolkit, "candidate_02", "candidate_01")
    assert compared["comparison_counts"]["spaces"] == {
        "preserved_count": 1, "changed_count": 1, "added_count": 1, "removed_count": 1}
    entities = json.loads((run / compared["audit_file"]).read_text())["comparison"]["entities"]
    assert entities["spaces"] == {"preserved_ids": ["U"], "changed_ids": ["A"],
                                   "added_ids": ["C"], "removed_ids": ["B"]}
    assert entities["boundaries"] == {"preserved_ids": ["bA", "bU"], "changed_ids": [],
                                       "added_ids": ["bC"], "removed_ids": ["bB"]}
    assert entities["windows"] == {"preserved_ids": ["w1", "wU"], "changed_ids": ["w2"],
                                    "added_ids": ["w3"], "removed_ids": []}
    assert entities["openings"] == {"preserved_ids": [], "changed_ids": ["d1"],
                                     "added_ids": ["d2"], "removed_ids": []}
    assert "code compliance" in audit["scope"] and "acceptance" in audit["scope"]


def test_door_midpoint_facts_are_descriptive_and_host_direction_independent():
    opening = {"id": "center", "host_boundary_id": "forward", "space_ids": ["A"],
               "exterior": True, "connectivity": "unknown",
               "vertices": [[1.5, 0, 0], [2.5, 0, 0], [2.5, 0, 2], [1.5, 0, 2]]}
    boundaries = {
        "forward": {"vertices": [[0, 0, 0], [4, 0, 0], [4, 0, 3], [0, 0, 3]]},
        "reverse": {"vertices": [[4, 0, 0], [0, 0, 0], [0, 0, 3], [4, 0, 3]]},
    }
    forward = inference._door_fact(opening, boundaries, {})
    reverse = inference._door_fact({**opening, "host_boundary_id": "reverse"}, boundaries, {})
    assert forward["exactly_centered_numerically"] is True
    assert reverse["exactly_centered_numerically"] is True
    assert forward["normalized_midpoint_position_from_host_start"] == .5
    assert reverse["normalized_midpoint_position_from_host_start"] == .5

    offset = inference._door_fact({**opening, "id": "offset", "host_boundary_id": "reverse",
        "vertices": [[.5, 0, 0], [1.5, 0, 0], [1.5, 0, 2], [.5, 0, 2]]}, boundaries, {})
    assert offset["normalized_midpoint_position_from_host_start"] == .75
    assert offset["midpoint_distance_from_host_midpoint_m"] == 1
    assert offset["exactly_centered_numerically"] is False


def test_registers_only_for_writable_runs(tmp_path):
    writable, readonly = _Server(), _Server()
    inference.register_inference_tools(writable, _Toolkit(_run(tmp_path)))
    inference.register_inference_tools(readonly, _Toolkit(tmp_path / "unused", readonly=True))
    assert set(writable.tools) == {"record_inference", "inspect_inference", "audit_inference_candidate"}
    assert readonly.tools == {}
