import copy
import hashlib

import pytest

from src.agent.runtime_roles.reader_context import previous_artifact_context
from src.agent.runtime_roles.artifacts import ArtifactRegistry
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts.budget import BudgetAmounts
from tests.test_role_readers import artifact


def fixture():
    value = artifact()
    value["notes"] = [{"item": "W1", "basis": "observed opening; verify height"}]
    audit = {"status": "pass", "grid_step_m": .1,
             "items": [{"path": "wall.x", "original_m": 3.94, "adopted_m": 3.9,
                        "repeated_evidence": "x" * 1000} for _ in range(30)],
             "summary": {"moved_coordinates": 30}}
    value["plan"]["regularization"] = {"status": "pass", "lite_bim": copy.deepcopy(audit)}
    value["plan"]["regularization_inputs"] = {
        "line_references": [{"partition_id": "P1", "basis": "dimension", "source_refs": ["drawing"]}],
        "reading_alignment": {"lite_bim": audit},
    }
    return value


def test_plan_projection_preserves_editable_geometry_evidence_and_source():
    original = fixture()
    snapshot = copy.deepcopy(original)
    result = previous_artifact_context(original, role_id="plan_reader")
    for field in ("footprint_pixels", "partitions", "openings", "space_seeds", "z_floor", "ceiling_height",
                  "x_anchors", "y_anchors", "basis", "assumptions", "unresolved"):
        assert result["plan"][field] == original["plan"][field]
    assert result["evidence"] == original["evidence"] and result["notes"] == original["notes"]
    assert "regularization" not in result["plan"]
    assert "reading_alignment" not in result["plan"]["regularization_inputs"]
    assert result["plan"]["regularization_inputs"]["line_references"] == original["plan"]["regularization_inputs"]["line_references"]
    assert len(json_bytes(result)) < len(json_bytes(original)) / 10
    for ref in result["context_audit"]["omitted_audits"]:
        value = original
        for key in ref["json_pointer"].strip("/").split("/"):
            value = value[key]
        assert ref["canonical_sha256"] == hashlib.sha256(json_bytes(value)).hexdigest()
    result["plan"]["openings"][0]["z"][0] = 999
    assert original == snapshot


def test_prompt_removal_cannot_remove_original_immutable_registry_audit(tmp_path):
    value = fixture()
    with EventStore(tmp_path / "store", run_id="projection", task_id="coordinator",
                    budget_limit=BudgetAmounts(calls=1)) as store:
        registry = ArtifactRegistry(store)
        task = {"task_id": "plan_f1", "role_id": "plan_reader", "image": "plan.png",
                "target": "F1", "input_sha256": "a" * 64}
        record = registry.save(task, status="completed", artifact=value, validation={"validation_passed": True})
        original_file = store.directory / record["artifact"]["path"]
        before = original_file.read_bytes()
        projected = previous_artifact_context(registry.read("plan_f1"), role_id="plan_reader",
                                             artifact_reference=record["artifact"])
        assert projected["context_audit"]["registry_reference"] == record["artifact"]
        assert projected["context_audit"]["canonical_artifact_sha256"] == record["artifact"]["sha256"]
        projected.pop("context_audit")
        projected["plan"].pop("regularization_inputs")
        assert registry.read("plan_f1") == value and original_file.read_bytes() == before
        with pytest.raises(ValueError, match="cannot be overwritten"):
            registry.save(task, status="completed", artifact=projected, validation={"validation_passed": True})


def test_elevation_readings_remain_reusable_with_bounded_adoption_examples():
    opening = {"id": "W", "floor_id": "F1", "kind": "window", "x_px": [50, 100],
               "width_m": 1.4, "sill_m": .9, "head_m": 2.1, "evidence_type": "annotation",
               "bbox": [50, 40, 100, 80]}
    value = {"orientation": "North", "view_direction": "South", "openings": [opening],
             "elevations": [{"id": "F1", "value_m": 0}], "counts": [{"window_count": 1}],
             "z_calibration": {"pixel_start": 0, "world_start_m": 10}, "unresolved": [],
             "artifact_sha256": "historical-normalized-hash",
             "ink_alignment": {"status": "pass", "openings": [{"payload": "x" * 10000}]},
             "regularization": {"grid_step_m": .1, "changes": [
                 {"item_kind": "opening", "item_id": "W", "field": "width_m", "original_m": 1.44,
                  "adopted_m": 1.4} for _ in range(30)]}}
    result = previous_artifact_context(value, role_id="elevation_reader")
    assert result["openings"] == value["openings"]
    assert result["z_calibration"] == value["z_calibration"]
    assert not {"ink_alignment", "regularization", "artifact_sha256"} & result.keys()
    audit = result["context_audit"]
    assert len(audit["adoption_examples"]) == 12 and audit["adoption_examples_remaining"] == 18
    assert audit["adoption_examples"][0]["original_m"] == 1.44


def test_absent_previous_delivery_stays_absent():
    assert previous_artifact_context(None, role_id="plan_reader") is None
