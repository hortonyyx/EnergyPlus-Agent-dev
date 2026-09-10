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
