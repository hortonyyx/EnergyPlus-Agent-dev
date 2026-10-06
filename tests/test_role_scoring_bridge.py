from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_d1b/scoring_bridge.py"
REFERENCE = ROOT / "AI_agent/logs/experiments/2026-10-06_role_division_analysis/references/sm24_anchor.json"
SPEC = importlib.util.spec_from_file_location("role_scoring_bridge_tested", BRIDGE_PATH)
assert SPEC is not None and SPEC.loader is not None
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


def _plan_artifact():
    plan = {
        "floor_id": "F1",
        "z_floor": 0.0,
        "ceiling_height": 3.0,
        "x_anchors": [[10, 0.0], [90, 8.0]],
        "y_anchors": [[90, 0.0], [10, 8.0]],
        "basis": "two explicit axes and one observed exterior opening",
        "footprint_pixels": [[10, 90], [90, 90], [90, 10], [10, 10]],
        "partitions": [],
        "space_seeds": [{"id": "room", "point": [50, 50], "role": "office"}],
        "openings": [{
            "id": "W1", "kind": "window", "p1": [40, 10], "p2": [60, 10],
            "z": [1.0, 2.4], "source_refs": ["plan.png:north window"],
        }],
        "assumptions": ["one room"],
        "unresolved": [],
    }
    targets = [
        "plan.x_anchors", "plan.y_anchors", "plan.footprint_pixels",
        "plan.space_seeds:room", "plan.openings:W1",
    ]
    return {
        "plan": plan,
        "evidence": [
            {"item": item, "source": "plan.png", "bbox": [1, 1, 99, 99]}
            for item in targets
        ],
        "unresolved": [],
    }


def test_direct_plan_artifact_converts_without_reference_data():
    conversion = BRIDGE.convert_role_artifacts(
        case="unit",
        plan_artifact=_plan_artifact(),
        plan_image_size=(100, 100),
        plan_image_name="plan.png",
        assigned_plan_floors=["F1"],
    )
    row = conversion["answer"]["plan_questions"][0]
    assert row["floor_id"] == "F1"
    assert row["exterior_m"] == [[0.0, 0.0], [8.0, 0.0], [8.0, 8.0], [0.0, 8.0]]
    assert len(row["rooms"]) == 1
    assert row["openings"][0]["span_m"] == [3.0, 5.0]
    assert conversion["inputs"][0]["evidence_count"] == 5


def test_submit_delivery_unresolved_extends_trial_plan_without_mutating_it():
    artifact = _plan_artifact()
    artifact["plan"]["unresolved"] = ["trial question"]
    artifact["unresolved"] = ["trial question", "delivery-only question"]
    original = copy.deepcopy(artifact)
    conversion = BRIDGE.convert_role_artifacts(
        case="unit",
        plan_artifact=artifact,
        plan_image_size=(100, 100),
        plan_image_name="plan.png",
        assigned_plan_floors=["F1"],
    )
    assert artifact == original
    assert conversion["inputs"][0]["unresolved"] == [
        "trial question", "delivery-only question",
    ]


def test_trial_source_metadata_accepts_submit_delivery_unresolved_extension():
    artifact = _plan_artifact()
    artifact["plan"]["unresolved"] = ["trial question"]
    artifact["unresolved"] = ["trial question", "delivery-only question"]
    source = {"floors": [], "spaces": [], "openings": [], "boundaries": []}
    receipt = {
        "status": "passed", "source_geometry_ready": True,
        "candidate_source_sha256": BRIDGE._sha256(source),
    }
    conversion = BRIDGE.convert_role_artifacts(
        case="unit",
        plan_artifact=artifact,
        plan_trial_source=source,
        plan_trial_receipt=receipt,
        plan_image_name="plan.png",
    )
    metadata = next(row for row in conversion["inputs"] if row["kind"] == "plan_artifact_metadata")
    assert metadata["unresolved"] == ["trial question", "delivery-only question"]


def test_elevation_calibration_maps_reversed_world_axis():
    artifact = {
        "schema_version": "elevation_reader_v1",
        "image": "North_view.png",
        "orientation": "North",
        "view_direction": "South",
        "x_calibration": {
            "pixel_start": 100.0, "pixel_end": 900.0,
            "world_axis": "x", "world_start_m": 10.0, "world_end_m": 0.0,
        },
        "elevations": [
            {"id": "ground", "kind": "ground", "floor_id": None, "value_m": 0.0,
             "bbox": [100, 900, 900, 902], "evidence_type": "pixels"},
            {"id": "eave", "kind": "eave", "floor_id": None, "value_m": 4.5,
             "bbox": [100, 100, 900, 102], "evidence_type": "pixels"},
        ],
        "openings": [{
            "id": "W1", "kind": "window", "floor_id": "F1", "x_px": [180.0, 580.0],
            "width_m": 5.0, "sill_m": 1.0, "head_m": 3.4,
            "bbox": [180, 300, 580, 700], "evidence_type": "pixels",
        }],
        "counts": [{"floor_id": "F1", "door_count": 0, "window_count": 1}],
        "unresolved": [],
    }
    row, audit = BRIDGE.neutral_elevation_from_artifact(artifact)
    assert row["facade"] == "North"
    assert row["openings"][0]["span_m"] == pytest.approx([4.0, 9.0])
    assert audit["world_axis"] == "x"


def test_assigned_scope_does_not_penalize_unassigned_facades():
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    answer = copy.deepcopy(reference)
    answer["elevation_questions"] = [
        row for row in answer["elevation_questions"] if row["facade"] in {"North", "East"}
    ]
    conversion = {
        "answer": answer,
        "scope": {
            "assigned": {"plan_floors": ["F1"], "elevation_facades": ["East", "North"]},
            "submitted": {"plan_floors": ["F1"], "elevation_facades": ["East", "North"]},
            "missing_assigned": {"plan_floors": [], "elevation_facades": []},
        },
    }
    result = BRIDGE.score_scoped_answer(reference, conversion)
    assert result["assigned_role_score"]["status"] == "pass"
    assert result["assigned_role_score"]["questions_passed"] == 3
    assert result["complete_reference_score"]["status"] == "severe"
    assert result["coverage"]["unassigned_reference"] == {
        "plan_floors": [], "elevation_facades": ["South", "West"],
    }


def test_trial_source_must_be_bound_to_passed_receipt():
    source = {"floors": [], "spaces": [], "openings": [], "boundaries": []}
    receipt = {
        "status": "failed", "source_geometry_ready": False,
        "candidate_source_sha256": BRIDGE._sha256(source),
    }
    with pytest.raises(ValueError, match="not a passed"):
        BRIDGE.neutral_plan_from_trial_source(source, receipt, case="unit")
