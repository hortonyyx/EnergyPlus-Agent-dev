import copy

import pytest
from PIL import Image, ImageChops

from src.agent.geometry.source_elevation_overlay import render_elevation_overlay
from tests.test_source_elevation_view import _source


def _render(source, image, **changes):
    settings = dict(facade="North", horizontal_anchors=[[50, 4], [450, 0]],
                    z_anchors=[[650, 0], [50, 6]], basis="Synthetic outer width and absolute floor datum")
    return render_elevation_overlay(source, image, **{**settings, **changes})


def test_overlay_preserves_source_original_and_absolute_floor_frame():
    source = _source()
    before = copy.deepcopy(source)
    original = Image.new("RGB", (500, 700), "black")
    untouched = original.copy()
    image, meta = _render(source, original)
    assert source == before and ImageChops.difference(original, untouched).getbbox() is None
    assert image.size == original.size
    openings = {row["id"]: row for row in meta["projected_openings"]}
    assert set(openings) == {"north-f1", "north-f2", "north-door"}
    assert {p[0] for p in openings["north-f1"]["pixel_vertices"]} == {320, 420}
    assert {p[1] for p in openings["north-f1"]["pixel_vertices"]} == {450, 550}
    assert min(p[1] for p in openings["north-f2"]["pixel_vertices"]) == 150
    assert image.getpixel((400, 450)) == (255, 145, 0)
    assert meta["direction"] == "-x"  # Explicit negative anchors are not reversed again.
    assert meta["calibration_unverified"] and meta["drawing_fidelity"] == "not_evaluated"
    assert not any(row["out_of_image"] for row in openings.values())


@pytest.mark.parametrize("changes,match", [
    ({"basis": " "}, "basis"),
    ({"horizontal_anchors": [[50, 0], [50, 4]]}, "distinct"),
    ({"z_anchors": [[700, 0], [50, 6]]}, "bounds"),
    ({"z_anchors": [[650, 0], [50, float('nan')]]}, "finite"),
])
def test_overlay_rejects_invalid_observed_frames(changes, match):
    with pytest.raises(ValueError, match=match):
        _render(_source(), Image.new("RGB", (500, 700)), **changes)


def test_overlay_exposes_clipped_geometry_and_different_scales():
    _, meta = _render(_source(), Image.new("RGB", (500, 700)),
                     horizontal_anchors=[[100, 0], [200, 0.5]])
    assert meta["calibration_warnings"]
    assert any(row["out_of_image"] for row in meta["projected_exterior_walls"])
    assert meta["drawing_fidelity"] == "not_evaluated"
