import copy

import numpy as np
from PIL import Image, ImageDraw
import pytest

from src.agent.geometry.space_ink_support import measure_space_ink, render_space_ink


def space(points=None):
    return {"space_id": "arbitrary-room", "pixel_polygon": points or [[20, 20], [220, 20], [220, 180], [20, 180]]}


@pytest.mark.parametrize("background,ink", [("black", "white"), ("white", "black")])
def test_interior_double_line_is_observation_not_wall_or_mutation(background, ink):
    image = Image.new("RGB", (250, 210), background)
    draw = ImageDraw.Draw(image)
    for x in (117, 123):
        draw.line([(x, 20), (x, 180)], fill=ink)
    spaces = [space()]
    old_pixels, old_spaces = np.asarray(image).copy(), copy.deepcopy(spaces)
    report = measure_space_ink(image, spaces)
    assert [s["cross_pixels"] for s in report["strokes"]] == [[117, 117], [123, 123]]
    assert {s["space_id"] for s in report["strokes"]} == {"arbitrary-room"}
    assert report["drawing_fidelity"] == "not_evaluated"
    assert "furniture" in report["interpretation"]
    assert np.array_equal(np.asarray(image), old_pixels) and spaces == old_spaces


def test_concave_room_does_not_search_empty_bounding_box_or_bridge_intervals():
    image = Image.new("RGB", (260, 240), "black")
    draw = ImageDraw.Draw(image)
    # U-shaped room. Long horizontal stroke exists ONLY in the absent notch.
    room = space([[20, 20], [70, 20], [70, 170], [180, 170], [180, 20], [230, 20], [230, 220], [20, 220]])
    draw.line([(85, 90), (165, 90)], fill="white")
    assert measure_space_ink(image, [room])["strokes"] == []
    # Separate supports in the two arms stay separate, not one line across notch.
    draw.line([(20, 110), (70, 110)], fill="white")
    draw.line([(180, 110), (230, 110)], fill="white")
    result = measure_space_ink(image, [room], inset_fraction=0.05)
    spans = [s["support_span_pixels"] for s in result["strokes"] if s["axis"] == "y"]
    assert len(spans) == 2 and spans[0][1] < spans[1][0]


def test_unobserved_low_contrast_and_small_regions_do_not_become_passes():
    image = Image.new("RGB", (250, 210), "black")
    ImageDraw.Draw(image).line([(120, 20), (120, 180)], fill=(40, 40, 40))
    result = measure_space_ink(image, [space(), {"space_id": "tiny", "pixel_polygon": [[1, 1], [9, 1], [9, 9], [1, 9]]}])
    assert result["strokes"] == []
    assert result["spaces"][1]["status"] == "below_sampling_span"
    assert "not proof" in result["interpretation"]
    assert result["drawing_fidelity"] == "not_evaluated"


def test_full_length_furniture_remains_a_reported_ambiguity():
    image = Image.new("RGB", (250, 210), "black")
    ImageDraw.Draw(image).rectangle([85, 25, 150, 170], outline="white")
    report = measure_space_ink(image, [space()])
    assert report["strokes"]
    assert "not detected walls" in report["interpretation"]
    assert all("wall" not in s for s in report["strokes"])


def test_render_retains_clean_full_room_and_maps_original_coordinates():
    image = Image.new("RGB", (250, 210), "black")
    ImageDraw.Draw(image).line([(120, 20), (120, 180)], fill="white")
    report = measure_space_ink(image, [space()])
    picture, metadata = render_space_ink(image, report, "arbitrary-room")
    x0, y0, x1, y1 = metadata["crop_original_pixels"]
    assert x0 < 20 and y0 < 20 and x1 > 220 and y1 > 180
    panel = metadata["clean_panel_native_pixels"]
    assert metadata["native_pixels_per_returned_pixel"] == [1, 1]
    assert np.array_equal(np.asarray(picture.crop(panel)), np.asarray(image.crop((x0, y0, x1, y1))))
    assert picture.getpixel((120-x0, panel[1]+100-y0)) == (255, 255, 255)


def test_invalid_space_and_parameters_are_not_silently_accepted():
    image = Image.new("RGB", (250, 210), "black")
    with pytest.raises(ValueError, match="unique"):
        measure_space_ink(image, [space(), space()])
    with pytest.raises(ValueError, match="outside"):
        measure_space_ink(image, [space([[0, 0], [260, 0], [0, 200]])])
    with pytest.raises(ValueError, match="finite"):
        measure_space_ink(image, [space()], inset_fraction=float("nan"))
