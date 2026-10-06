import copy
import json

import pytest

from src.agent.execution.bim_claims import Claim
from src.agent.runtime_roles.elevation import (
    height_application,
    match_elevation,
    validate_elevation_artifact,
)


SOURCE_HASH = "a" * 64


def _opening(opening_id, kind, p1, p2, z, host):
    return {
        "id": opening_id,
        "kind": kind,
        "exterior": True,
        "host_boundary_id": host,
        "space_ids": ["room"],
        "vertices": [
            [*p1, z[0]],
            [*p2, z[0]],
            [*p2, z[1]],
            [*p1, z[1]],
        ],
    }


@pytest.fixture
def source_bim():
    return {
        "source_model_sha256": SOURCE_HASH,
        "spaces": [{"id": "room", "floor_id": "F1"}],
        "boundaries": [
            {
                "id": "north",
                "vertices": [
                    [10, 10, 0],
                    [0, 10, 0],
                    [0, 10, 3],
                    [10, 10, 3],
                ],
            }
        ],
        "openings": [
            _opening("W1", "window", (1.0, 10), (2.0, 10), (1.0, 2.2), "north"),
            _opening("W2", "window", (2.08, 10), (3.08, 10), (1.0, 2.2), "north"),
            _opening("D1", "door", (6.0, 10), (7.0, 10), (0.0, 2.1), "north"),
        ],
    }


@pytest.fixture
def artifact():
    # North facade seen from outside: facing South, so image left-to-right is -X.
    return {
        "orientation": "North",
        "view_direction": "South",
        "x_calibration": {
            "pixel_start": 100,
            "pixel_end": 1100,
            "world_start_m": 10,
            "world_end_m": 0,
        },
        "elevations": [
            {
                "id": "ground",
                "kind": "ground",
                "value_m": 0,
                "evidence_type": "annotation",
                "bbox": [10, 500, 80, 550],
            },
            {
                "id": "floor-F1",
                "floor_id": "F1",
                "kind": "floor",
                "value_m": 0,
                "evidence_type": "annotation",
                "bbox": [10, 480, 80, 530],
            },
            {
                "id": "eave",
                "kind": "eave",
                "value_m": 3,
                "evidence_type": "pixels",
                "bbox": [10, 40, 80, 90],
            },
        ],
        "openings": [
            {
                "id": "read-D1",
                "floor_id": "F1",
                "kind": "door",
                "x_px": [400, 500],
                "width_m": 1.0,
                "sill_m": 0.0,
                "head_m": 2.1,
                "evidence_type": "annotation_and_pixels",
                "bbox": [390, 160, 510, 510],
            },
            {
                "id": "read-W2",
                "floor_id": "F1",
                "kind": "window",
                "x_px": [792, 892],
                "width_m": 1.0,
                "sill_m": 1.0,
                "head_m": 2.2,
                "evidence_type": "pixels",
                "bbox": [784, 180, 900, 400],
            },
            {
                "id": "read-W1",
                "floor_id": "F1",
                "kind": "window",
                "x_px": [900, 1000],
                "width_m": 1.0,
                "sill_m": 1.0,
                "head_m": 2.2,
                "evidence_type": "annotation",
                "bbox": [890, 180, 1010, 400],
            },
        ],
        "counts": [{"floor_id": "F1", "window_count": 2, "door_count": 1}],
        "unresolved": [],
    }


def test_validate_defaults_runtime_fields_and_absolute_z(artifact):
    result = validate_elevation_artifact(artifact, image_name="North_view.png")
    assert result["schema_version"] == "elevation_reader_v1"
    assert result["artifact_id"] == "elevation:North:North_view"
    assert result["image"] == "North_view.png"
    assert result["x_calibration"]["world_axis"] == "x"
    assert len(result["artifact_sha256"]) == 64
    assert result["openings"][2]["sill_m"] == 1.0
    assert validate_elevation_artifact(result) == result


def test_validate_rejects_stale_artifact_hash(artifact):
    result = validate_elevation_artifact(artifact, image_name="North_view.png")
    result["artifact_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="artifact_sha256"):
        validate_elevation_artifact(result)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item["counts"][0].update(window_count=1), "openings contains 2"),
        (lambda item: item["openings"][1].update(x_px=[150, 190]), "left-to-right"),
        (lambda item: item["openings"][2].update(head_m=0.9), "absolute building Z"),
        (lambda item: item["openings"][2].update(bbox=[1, 2, 1, 3]), "positive width"),
        (
            lambda item: item["x_calibration"].update(world_start_m=0, world_end_m=10),
            "contradicts view_direction",
        ),
    ],
)
def test_validate_rejects_specific_bad_fields(artifact, mutation, message):
    mutation(artifact)
    with pytest.raises(ValueError, match=message):
        validate_elevation_artifact(artifact, image_name="North_view.png")


def test_validate_requires_assigned_image(artifact):
    with pytest.raises(ValueError, match="image"):
        validate_elevation_artifact(artifact)


@pytest.mark.parametrize(
    ("orientation", "view_direction", "world_start", "world_end", "axis"),
    [
        ("North", "South", 10, 0, "x"),
        ("South", "North", 0, 10, "x"),
        ("East", "West", 0, 10, "y"),
        ("West", "East", 10, 0, "y"),
    ],
)
def test_validate_cardinal_outside_view_world_signs(
    artifact, orientation, view_direction, world_start, world_end, axis
):
    artifact.update(orientation=orientation, view_direction=view_direction)
    artifact["x_calibration"].update(
        world_start_m=world_start, world_end_m=world_end
    )
    result = validate_elevation_artifact(artifact, image_name=f"{orientation}_view.png")
    assert result["x_calibration"]["world_axis"] == axis
    artifact["x_calibration"].update(
        world_start_m=world_end, world_end_m=world_start
    )
    with pytest.raises(ValueError, match="contradicts view_direction"):
        validate_elevation_artifact(artifact, image_name=f"{orientation}_view.png")


def test_exact_match_handles_tight_windows_and_exterior_door(source_bim, artifact):
    artifact["image"] = "North_view.png"
    result = match_elevation(source_bim, artifact, candidate="candidate_01")
    assert [(row["artifact_opening_id"], row["source_opening_id"]) for row in result["matches"]] == [
        ("read-D1", "D1"),
        ("read-W2", "W2"),
        ("read-W1", "W1"),
    ]
    assert result["elevation_only"] == []
    assert result["source_only"] == []
    assert result["conflicts"] == []
    assert result["counts"][0]["matches"] is True
    assert result["source_model_sha256"] == SOURCE_HASH
    assert result["can_apply"] is True


def test_missing_one_opening_preserves_neighbors(source_bim, artifact):
    artifact["image"] = "North_view.png"
    artifact["openings"].pop(1)
    artifact["counts"][0]["window_count"] = 1
    result = match_elevation(source_bim, artifact)
    assert {row["source_opening_id"] for row in result["matches"]} == {"W1", "D1"}
    assert [row["source_id"] for row in result["source_only"]] == ["W2"]


def test_extra_one_opening_is_not_forced_onto_source(source_bim, artifact):
    artifact["image"] = "North_view.png"
    extra = copy.deepcopy(artifact["openings"][1])
    extra.update(id="read-W-extra", x_px=[700, 750], width_m=0.5, bbox=[690, 180, 760, 400])
    artifact["openings"].insert(1, extra)
    artifact["counts"][0]["window_count"] = 3
    result = match_elevation(source_bim, artifact)
    assert {row["source_opening_id"] for row in result["matches"]} == {"W1", "W2", "D1"}
    assert [row["artifact_opening_id"] for row in result["elevation_only"]] == [
        "read-W-extra"
    ]


def test_overall_shift_returns_conflicts_instead_of_false_matches(source_bim, artifact):
    artifact["image"] = "North_view.png"
    for opening in artifact["openings"]:
        opening["x_px"] = [value + 100 for value in opening["x_px"]]
        opening["bbox"] = [
            opening["bbox"][0] + 100,
            opening["bbox"][1],
            opening["bbox"][2] + 100,
            opening["bbox"][3],
        ]
    result = match_elevation(source_bim, artifact)
    assert result["matches"] == []
    assert len([row for row in result["conflicts"] if row.get("type") == "position_or_width_conflict"]) == 3
    assert result["can_apply"] is False


def test_width_difference_is_a_conflict(source_bim, artifact):
    artifact["image"] = "North_view.png"
    artifact["openings"][2]["width_m"] = 1.5
    result = match_elevation(source_bim, artifact)
    assert {row["source_opening_id"] for row in result["matches"]} == {"W2", "D1"}
    conflict = next(row for row in result["conflicts"] if row.get("source_opening_id") == "W1")
    assert conflict["width_difference_m"] == pytest.approx(0.5)


def test_height_application_emits_existing_claim_transaction_shape(source_bim, artifact):
    artifact["image"] = "North_view.png"
    match = match_elevation(source_bim, artifact, candidate="candidate_01")
    result = height_application(
        artifact,
        match,
        source_bim,
        provenance={"candidate": "candidate_01", "task_id": "elevation-1"},
    )
    assert result["candidate"] == "candidate_01"
    assert len(result["entries"]) == 3
    assert json.loads(result["entries_json"]) == result["entries"]
    assert all(Claim.model_validate(row["claim"]) for row in result["entries"])
    window = next(
        row for row in result["entries"] if row["claim"]["objects"][0]["id"] == "W1"
    )
    assert window["action"] == "apply"
    assert window["claim"]["sources"] == [
        {"image": "North_view.png", "box": [890.0, 180.0, 1010.0, 400.0]}
    ]
    assert window["claim"]["values"]["height"] == {
        "type": "literal",
        "value": [1.0, 2.2],
        "unit": "m",
    }
    assert window["operations"][0]["op"] == "update_window"
    assert window["operations"][0]["changes"]["z"] == {
        "claim": "$claim",
        "value": "height",
    }
    door = next(
        row for row in result["entries"] if row["claim"]["objects"][0]["id"] == "D1"
    )
    assert door["claim"]["objects"][0]["kind"] == "opening"
    assert door["operations"][0]["op"] == "update_opening"


def test_height_application_rejects_stale_source(source_bim, artifact):
    artifact["image"] = "North_view.png"
    match = match_elevation(source_bim, artifact, candidate="candidate_01")
    changed = {**source_bim, "source_model_sha256": "b" * 64}
    with pytest.raises(ValueError, match="stale"):
        height_application(
            artifact,
            match,
            changed,
            provenance={"candidate": "candidate_01"},
        )


def test_height_application_keeps_unmatched_items_unprocessed(source_bim, artifact):
    artifact["image"] = "North_view.png"
    artifact["openings"].pop(1)
    artifact["counts"][0]["window_count"] = 1
    match = match_elevation(source_bim, artifact, candidate="candidate_01")
    result = height_application(
        artifact, match, source_bim, provenance={"candidate": "candidate_01"}
    )
    assert len(result["entries"]) == 2
    assert [row["source_id"] for row in result["unprocessed"]["source_only"]] == ["W2"]


def test_image_name_cannot_be_silently_rebound(artifact):
    artifact["image"] = "other.png"
    with pytest.raises(ValueError, match="assigned image_name"):
        validate_elevation_artifact(artifact, image_name="North_view.png")
