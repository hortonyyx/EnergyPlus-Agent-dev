from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.agent.geometry.pixel_region import render_pixel_region


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def _two_rooms(*, breached: bool = False) -> Image.Image:
    image = Image.new("RGB", (32, 20), BLACK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 2, 13, 17), fill=WHITE)
    draw.rectangle((15, 2, 29, 17), fill=WHITE)
    if breached:
        draw.point((14, 10), fill=WHITE)
    return image


def test_seed_selects_only_its_four_connected_room():
    image = _two_rooms()

    preview, result = render_pixel_region(
        image, seed_pixel=(4, 5), background_rgb=WHITE, tolerance=0
    )

    assert isinstance(preview, Image.Image)
    assert result["region_pixel_count"] == 12 * 16
    assert result["bbox_px"] == [2, 2, 14, 18]
    assert result["touches_image_border"] is False
    assert [14.5, 10.5] not in result["outer_polygon_pixels"]
    flattened = {
        coordinate
        for point in result["outer_polygon_pixels"]
        for coordinate in point
    }
    assert {1.5, 13.5}.issubset(flattened)


def test_single_pixel_breach_leaks_into_the_other_room():
    image = _two_rooms(breached=True)

    _preview, result = render_pixel_region(
        image, seed_pixel=(4, 5), background_rgb=WHITE, tolerance=0
    )

    assert result["region_pixel_count"] == 12 * 16 + 15 * 16 + 1
    assert result["bbox_px"] == [2, 2, 30, 18]


def test_enclosed_raster_hole_is_retained_but_not_given_building_semantics():
    image = Image.new("RGB", (24, 22), BLACK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((3, 2, 20, 19), fill=WHITE)
    draw.rectangle((9, 8, 13, 12), fill=BLACK)

    _preview, result = render_pixel_region(
        image,
        seed_pixel=(5, 5),
        background_rgb=WHITE,
        tolerance=0,
        simplify_pixels=5,
    )

    assert result["hole_count"] == 1
    assert "not asserted building holes" in result["holes_meaning"]
    assert any("not a semantic room boundary" in item for item in result["warnings"])


def test_nonzero_bbox_coordinate_map_preview_limit_and_input_unchanged():
    image = Image.new("RGBA", (1800, 700), (*BLACK, 255))
    ImageDraw.Draw(image).rectangle((100, 50, 1699, 649), fill=(*WHITE, 255))
    before = np.asarray(image).copy()

    preview, result = render_pixel_region(
        image, seed_pixel=(200, 100), background_rgb=WHITE, tolerance=0
    )

    assert result["bbox_px"] == [100, 50, 1700, 650]
    coordinate_map = result["coordinate_map"]
    assert coordinate_map["source_crop_bbox_px"] == [84, 34, 1716, 666]
    assert coordinate_map["region_bbox_px"] == result["bbox_px"]
    assert coordinate_map["bbox_convention"].endswith("max_exclusive]")
    assert coordinate_map["right_tinted_panel"]["offset_px"][0] > 0
    assert max(preview.size) <= 1600
    assert np.array_equal(np.asarray(image), before)


@pytest.mark.parametrize(
    ("seed, background, expected"),
    [
        ((-1, 0), WHITE, "outside image bounds"),
        ((32, 0), WHITE, "outside image bounds"),
        ((0, 0), WHITE, "does not match"),
        ((1.5, 2), WHITE, "must be integers"),
    ],
)
def test_invalid_or_nonmatching_seed_is_rejected(seed, background, expected):
    with pytest.raises(ValueError, match=expected):
        render_pixel_region(_two_rooms(), seed, background, tolerance=0)


@pytest.mark.parametrize("simplify", [-0.1, 5.1])
def test_simplification_is_bounded(simplify):
    with pytest.raises(ValueError, match="between 0 and 5"):
        render_pixel_region(_two_rooms(), (4, 5), WHITE, simplify_pixels=simplify)
