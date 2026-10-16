import copy

import pytest
from PIL import Image, ImageDraw

from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.geometry.plan_wall_metadata_checks import append_wall_metadata_checks


def scene(*, background="white", mirror=False, side="outer_face", thickness=.24, opening=False):
    plan = {"reading_type": "plan", "floor_id": "F1", "basis": "Synthetic 100px/m fixture",
            "x_anchors": [[100, 0], [900, 8]], "y_anchors": [[100, 8], [900, 0]],
            "footprint_pixels": [[100, 100], [900, 100], [900, 900], [100, 900]],
            "partitions": [], "space_seeds": [], "openings": [], "assumptions": [], "unresolved": [],
            "wall_metadata": [{"target": "footprint:0", "thickness_m": thickness,
                               "reference_side": side, "evidence_status": "observed" if thickness else "unknown",
                               "basis": "Synthetic paired strokes", "source_refs": ["fixture"]}]}
    if mirror:
        plan["x_anchors"] = [[900, 0], [100, 8]]
        plan["y_anchors"] = [[900, 8], [100, 0]]
    image = Image.new("RGB", (1000, 1000), background)
    draw = ImageDraw.Draw(image)
    color = "black" if background == "white" else "white"
    for y in (100, 124):
        draw.line([(100, y), (900, y)], fill=color, width=1)
    if opening:
        plan["openings"] = [{"id": "W1", "kind": "window", "p1": [180, 100], "p2": [820, 100]}]
        draw.rectangle([180, 95, 820, 130], fill=background)
    _, metadata = compile_plan_partition(plan, image_size=image.size, image_name="plan.png")
    report = {"status": "reported", "items": [], "total": 0, "counts": {}, "scope": "Existing scope", "coverage": {}}
    return plan, image, metadata, report


@pytest.mark.parametrize("background,mirror,opening", [("white", False, False), ("black", True, False), ("black", False, True)])
def test_matching_faces_and_openings_do_not_create_hints_or_change_inputs(background, mirror, opening):
    plan, image, metadata, report = scene(background=background, mirror=mirror, opening=opening)
    before = copy.deepcopy((plan, metadata, report)); pixels = image.tobytes()
    result = append_wall_metadata_checks(report, image, plan, metadata)
    assert result["items"] == []
    assert result["coverage"]["wall_metadata"]["compared_segments"] == 1
    assert (plan, metadata, report) == before and image.tobytes() == pixels


@pytest.mark.parametrize("side,thickness", [("inner_face", .24), ("outer_face", .72)])
def test_wrong_declared_side_or_thickness_yields_located_ink_hint(side, thickness):
    plan, image, metadata, report = scene(side=side, thickness=thickness)
    result = append_wall_metadata_checks(report, image, plan, metadata)
    assert result["total"] == 1
    issue = result["items"][0]
    assert issue["wall_target"] == "footprint:0"
    assert issue["nearby_parallel_ink_px"] == [100, 124]
    assert issue["ink_spacing_m"] == .24
    assert issue["look_box"][1] <= 100 < 124 <= issue["look_box"][3]
    assert result["status"] == "reported"


@pytest.mark.parametrize("unknown", ["side", "thickness", "blank", "third_line", "clipped"])
def test_unknown_absent_ambiguous_or_clipped_ink_is_not_negative_evidence(unknown):
    plan, image, metadata, report = scene(side="inner_face", thickness=.24)
    if unknown == "side":
        plan["wall_metadata"][0]["reference_side"] = "unknown"
    elif unknown == "thickness":
        plan["wall_metadata"][0].update(thickness_m=None, evidence_status="unknown")
    elif unknown == "blank":
        image.paste("white", (0, 0, *image.size))
    elif unknown == "third_line":
        ImageDraw.Draw(image).line([(100, 144), (900, 144)], fill="black")
    else:
        image = image.crop((0, 80, 1000, 1000))
        for point in plan["footprint_pixels"]:
            point[1] -= 80
        for anchor in plan["y_anchors"]:
            anchor[0] -= 80
        _, metadata = compile_plan_partition(plan, image_size=image.size, image_name="plan.png")
    result = append_wall_metadata_checks(report, image, plan, metadata)
    assert result["total"] == 0
    assert result["coverage"]["wall_metadata"]["compared_segments"] == 0
