from __future__ import annotations

import copy

import pytest
from PIL import Image

from src.agent.geometry.source_image_overlay import render_source_overlay
from src.agent.geometry.source_model import _digest


def _source():
    source = {
        "floors": [{"id": "F1"}],
        "spaces": [{
            "id": "room", "floor_id": "F1",
            "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
        }],
        "openings": [
            {"id": "door", "kind": "door", "space_ids": ["room"],
             "vertices": [[10, 3, 0], [10, 5, 0], [10, 5, 2.1], [10, 3, 2.1]]},
            {"id": "window", "kind": "window", "space_ids": ["room"],
             "vertices": [[2, 0, 1], [4, 0, 1], [4, 0, 2], [2, 0, 2]]},
        ],
    }
    source["source_model_sha256"] = _digest(source)
    return source


def _wall_evidence_source():
    """Two same-x walls make a normal-axis-only check deliberately ambiguous."""
    source = {
        "floors": [{"id": "F1"}, {"id": "F2"}],
        "spaces": [{"id": "room", "floor_id": "F1", "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]}],
        "openings": [],
        "wall_references": [
            {"id": "north", "floor_id": "F1", "axis": "x", "boundary_ids": ["north-boundary"],
             "evidence_status": "observed", "representative_endpoints": [[2, 0], [2, 2]]},
            {"id": "south", "floor_id": "F1", "axis": "x", "boundary_ids": ["south-boundary"],
             "evidence_status": "observed", "representative_endpoints": [[2, 8], [2, 10]]},
            {"id": "other-floor", "floor_id": "F2", "axis": "x", "boundary_ids": ["f2-boundary"],
             "evidence_status": "observed", "representative_endpoints": [[2, 0], [2, 2]]},
        ],
        "wall_dimension_report": {"dimensions": [
            {"id": "wrong-host", "start": {"wall_id": "south", "image": "plan-a.png", "pixel": [26, 82]},
             "end": {"wall_id": "south", "image": "plan-b.png", "pixel": [26, 82]}},
            {"id": "other-image", "start": {"wall_id": "north", "image": "plan-b.png", "pixel": [26, 82]}},
            {"id": "other-floor", "start": {"wall_id": "other-floor", "image": "plan-a.png", "pixel": [26, 82]}},
        ]},
    }
    source["source_model_sha256"] = _digest(source)
    return source


def test_projects_source_geometry_on_original_pixels_without_mutating_inputs():
    source = _source()
    before_source = copy.deepcopy(source)
    image = Image.new("RGB", (100, 100), "white")
    before_pixels = image.tobytes()

    overlay, meta = render_source_overlay(
        source, image, floor_id="F1",
        x_anchors=[[10, 0], [90, 10]],
        y_anchors=[[90, 0], [50, 10]],
        basis="outer plan extents selected from visible dimension extensions",
    )

    assert source == before_source
    assert image.tobytes() == before_pixels
    assert overlay.getpixel((10, 70)) == (255, 0, 255)
    assert overlay.getpixel((90, 75)) == (255, 165, 0)
    assert overlay.getpixel((34, 90)) == (0, 255, 0)
    assert meta["drawing_fidelity"] == "not_evaluated"
    assert meta["calibration_unverified"] is True
    assert meta["scale"]["pixels_per_world_metre"] == {"x": 8.0, "y": -4.0}
    assert meta["scale"]["warnings"]
    assert meta["projected_openings"] == [
        {"id": "door", "kind": "door", "space_ids": ["room"],
         "pixel_endpoints": [[90.0, 78.0], [90.0, 70.0]], "out_of_image": False},
        {"id": "window", "kind": "window", "space_ids": ["room"],
         "pixel_endpoints": [[26.0, 90.0], [42.0, 90.0]], "out_of_image": False},
    ]


def test_rejects_a_tampered_source_hash_before_projecting():
    source = _source()
    source["spaces"][0]["polygon"][2][0] = 11
    with pytest.raises(ValueError, match="source_model_sha256"):
        render_source_overlay(
            source, Image.new("RGB", (100, 100), "white"), floor_id="F1",
            x_anchors=[[10, 0], [90, 10]], y_anchors=[[90, 0], [50, 10]], basis="synthetic",
        )


def test_wall_evidence_overlay_keeps_exact_image_points_and_reports_host_extent_conditionally():
    source = _wall_evidence_source()
    before = copy.deepcopy(source)
    image = Image.new("RGB", (100, 100), "white")
    image_before = image.tobytes()

    overlay, metadata = render_source_overlay(
        source, image, floor_id="F1", image_name="plan-a.png",
        x_anchors=[[10, 0], [90, 10]], y_anchors=[[90, 0], [10, 10]], basis="synthetic flipped y",
    )

    projection = metadata["wall_evidence_projection"]
    assert source == before and image.tobytes() == image_before
    assert metadata["drawing_fidelity"] == "not_evaluated"
    assert projection["scope"] == {
        "image_name": "plan-a.png", "floor_id": "F1",
        "endpoint_selection": "exact original image name and linked wall floor",
        "view_status": "not_visually_verified",
    }
    assert [row["wall_id"] for row in projection["walls"]] == ["north", "south"]
    assert len(projection["endpoints"]) == 1  # Other image and other floor are intentionally absent.
    endpoint = projection["endpoints"][0]
    assert endpoint["marker"] == "D1:S"
    assert endpoint["dimension_id"] == "wrong-host"
    assert endpoint["wall_id"] == "south" and endpoint["boundary_ids"] == ["south-boundary"]
    assert endpoint["pixel"] == [26, 82]  # The source evidence point is not moved to a wall endpoint.
    assert endpoint["mapped_world_point_m"] == [2.0, 1.0]
    assert endpoint["projected_host_endpoints"] == [[26.0, 26.0], [26.0, 10.0]]
    assert endpoint["tangential_range_m"] == [8.0, 10.0]
    assert endpoint["tangential_outside_distance_m"] == 7.0
    assert endpoint["normal_displacement_m"] == 0.0
    assert endpoint["status"] == "conditional_projection_not_visually_verified"
    assert overlay.getpixel((26, 82)) != (255, 255, 255)
    assert not any("pass" in str(value).lower() for value in projection.values())

    corrected = copy.deepcopy(source)
    corrected["wall_dimension_report"]["dimensions"][0]["start"]["wall_id"] = "north"
    corrected["source_model_sha256"] = _digest({key: value for key, value in corrected.items()
                                                  if key != "source_model_sha256"})
    _, corrected_metadata = render_source_overlay(
        corrected, image, floor_id="F1", image_name="plan-a.png",
        x_anchors=[[10, 0], [90, 10]], y_anchors=[[90, 0], [10, 10]], basis="synthetic flipped y",
    )
    assert corrected_metadata["wall_evidence_projection"]["endpoints"][0]["tangential_outside_distance_m"] == 0.0


def test_overlay_without_image_name_has_no_wall_evidence_projection():
    _, metadata = render_source_overlay(
        _wall_evidence_source(), Image.new("RGB", (100, 100), "white"), floor_id="F1",
        x_anchors=[[10, 0], [90, 10]], y_anchors=[[90, 0], [10, 10]], basis="synthetic",
    )
    assert "wall_evidence_projection" not in metadata
