"""Reader evidence reaches the unchanged delivery check without fitting BIM."""

import asyncio
import copy
import json

import pytest

from src.agent.runtime_roles.elevation import validate_elevation_artifact
from src.agent.runtime_roles.height_evidence import height_locations
from tests.test_role_d1g import height_session


def observed_west(session):
    artifact = session.registry.read("West")
    artifact.pop("artifact_sha256")
    artifact["elevations"] = [
        {"id": "ground", "kind": "ground", "value_m": 0, "evidence_type": "pixels", "bbox": [0, 6.5, 12, 7.5]},
        {"id": "eave", "kind": "eave", "value_m": 3, "evidence_type": "annotation", "bbox": [0, .5, 12, 1.5]},
    ]
    artifact["openings"][0]["bbox"] = [8, 2.4, 10, 5.2]
    return validate_elevation_artifact(artifact)


def test_reader_coordinates_reach_delivery_and_stale_heights_lose_coverage(tmp_path):
    with height_session(tmp_path) as session, asyncio.Runner() as runner:
        artifact = observed_west(session)
        task = session._task({"task_id": "located_west", "role_id": "elevation_reader",
                              "image": "plan.png", "target": "West"})
        record = session.registry.save(task, status="completed", artifact=artifact)
        artifact_path = session.store.directory / record["artifact"]["path"]
        original = artifact_path.read_bytes()
        match = session.match("located_west", "candidate_01")
        result = runner.run(session.apply_heights(match["match_id"]))["structuredContent"]
        assert result["status"] == "completed"
        toolkit = session.frozen.toolkit
        delivery = toolkit.delivery("candidate_02", selection_origin="offline_test")
        rows = {row["opening_id"]: row for row in delivery["height_coverage"]["openings"]}
        assert rows["West"]["status"] == "located_applied"
        assert all(rows[side]["status"] == "missing" for side in ("North", "South", "East"))
        assert len(list(session.run_directory.glob("candidate_*/report.json"))) == 2
        reviews = list((session.run_directory / "elevation_reviews").glob("review_*.json"))
        assert len(reviews) == 1
        assert json.loads(reviews[0].read_bytes())["role_height_evidence"]["openings"]["observed-West"][
            "original_bbox"] == artifact["openings"][0]["bbox"]
        # A new match confirms equal values without a new candidate or calibration.
        current = session.match("located_west", "candidate_02")
        assert runner.run(session.apply_heights(current["match_id"]))["structuredContent"]["height_write"]["unchanged"]
        assert len(list(session.run_directory.glob("candidate_*/report.json"))) == 2
        assert len(list((session.run_directory / "elevation_reviews").glob("review_*.json"))) == 1
        assert artifact_path.read_bytes() == original
        revised = toolkit.revise("candidate_02", json.dumps([{"op": "update_window", "id": "West",
            "changes": {"z": [.9, 2.31]}, "reason": "Uncited bounded edit", "source_refs": ["offline_test"]}]))
        rows = {row["opening_id"]: row for row in toolkit.located_heights(revised["candidate"])["openings"]}
        assert rows["West"]["status"] == "missing"


@pytest.mark.parametrize("defect", ["dimension_chain", "assumed_levels", "wrong_opening_region"])
def test_missing_or_unrelated_reader_coordinates_are_not_manufactured(tmp_path, defect):
    with height_session(tmp_path) as session:
        artifact = observed_west(session)
        match = {"tolerances_m": {"position": .35, "width": .25}, "matches": [
            {"artifact_opening_id": "observed-West", "source_opening_id": "West"}]}
        if defect == "dimension_chain":
            for level in artifact["elevations"]:
                level["bbox"] = [0, 0, 1, 8]
        elif defect == "assumed_levels":
            for level in artifact["elevations"]:
                level["evidence_type"] = "assumption"
        else:
            artifact["openings"][0]["bbox"] = [0, 0, 2, 2]
        before = copy.deepcopy(artifact)
        report = height_locations(artifact, match, [12, 8])
        assert artifact == before
        assert not any("source_box" in row for row in report["openings"].values())
        assert report["status"] != "prepared" or report["openings"]["observed-West"]["status"] != "prepared"


def test_single_level_scale_needs_independent_image_corroboration(tmp_path):
    with height_session(tmp_path) as session:
        artifact = observed_west(session)
        artifact["elevations"] = artifact["elevations"][:1]
        match = {"tolerances_m": {"position": .35, "width": .25}, "matches": []}
        assert height_locations(artifact, match, [12, 8])["status"] == "uncorroborated_vertical_scale"
        other = {**artifact["openings"][0], "id": "second", "x_px": [2, 4], "bbox": [2, 2.4, 4, 5.2]}
        artifact["openings"].append(other)
        assert height_locations(artifact, match, [12, 8])["status"] == "prepared"
        other["head_m"] = 10
        assert height_locations(artifact, match, [12, 8])["status"] == "uncorroborated_vertical_scale"
