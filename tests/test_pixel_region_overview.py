from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from src.agent.geometry.pixel_region_overview import render_pixel_region_overview


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def test_overview_keeps_diagonal_components_separate_and_seeds_each_region():
    image = Image.new("RGB", (12, 12), BLACK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 2, 4, 4), fill=WHITE)
    draw.rectangle((5, 5, 7, 7), fill=WHITE)  # Diagonal contact only.

    _preview, result = render_pixel_region_overview(
        image, WHITE, tolerance=0, min_pixels=1
    )

    assert [candidate["pixel_count"] for candidate in result["candidates"]] == [9, 9]
    assert [candidate["bbox_px"] for candidate in result["candidates"]] == [
        [2, 2, 5, 5],
        [5, 5, 8, 8],
    ]
    for candidate in result["candidates"]:
        x, y = candidate["seed_pixel"]
        assert image.getpixel((x, y)) == WHITE
        assert candidate["id"] in {"R01", "R02"}


def test_overview_applies_colour_tolerance_and_reports_area_border_and_truncation():
    image = Image.new("RGB", (30, 20), BLACK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 29, 1), fill=(250, 250, 250))  # Border component.
    draw.rectangle((3, 3, 6, 6), fill=WHITE)
    draw.rectangle((10, 3, 14, 6), fill=WHITE)
    draw.point((20, 4), fill=WHITE)

    _preview, result = render_pixel_region_overview(
        image, WHITE, tolerance=8.7, min_pixels=4, max_regions=1
    )

    assert [candidate["pixel_count"] for candidate in result["candidates"]] == [20]
    exclusions = result["region_exclusions"]
    assert exclusions["touching_image_border"]["count"] == 1
    assert exclusions["below_min_pixels"]["count"] == 1
    assert exclusions["truncated_by_max_regions"]["count"] == 1
    assert "not asserted to be exterior space" in exclusions["touching_image_border"]["reason"]


def test_overview_clean_panel_and_coordinate_map_preserve_original_coordinates():
    image = Image.new("RGB", (1800, 700), BLACK)
    ImageDraw.Draw(image).rectangle((100, 50, 1699, 649), fill=WHITE)
    before = np.asarray(image).copy()

    preview, result = render_pixel_region_overview(
        image, WHITE, tolerance=0, min_pixels=10, include_border=True
    )

    assert result["candidates"][0]["bbox_px"] == [100, 50, 1700, 650]
    seed_x, seed_y = result["candidates"][0]["seed_pixel"]
    assert 100 <= seed_x < 1700 and 50 <= seed_y < 650
    assert result["coordinate_map"]["source_size_px"] == [1800, 700]
    assert result["coordinate_map"]["right_numbered_panel"]["offset_px"][0] > 0
    assert max(preview.size) <= 1600
    # The clean left panel starts with the original black source corner.
    assert preview.getpixel((0, 0)) == BLACK
    assert np.array_equal(np.asarray(image), before)
