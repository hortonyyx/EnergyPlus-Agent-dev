"""Optional original-image counterexample; current synthetic contracts live separately."""
from PIL import Image
from tests.archive_paths import archive_path
from tests.test_plan_drawing_differences import (plan, drawing_differences, OPENING_OFFSET_CHECK, CONTINUOUS_SPACE_CHECK)


def test_sm25_gap_across_full_channel_adds_continuous_space_hint():
    sm25 = plan(
        x_anchors=[[283, 0], [1437, 25]],
        y_anchors=[[1235, 0], [310, 20]],
        footprint_pixels=[[283, 310], [976, 310], [976, 965.1], [1426, 965.1],
                          [1426, 1235], [513.8, 1235], [513.8, 594], [283, 594]],
        partitions=[
            {"id": "PA_rooms_south", "points": [[283, 487.3], [799.3, 487.3]]},
            {"id": "PD_div23", "points": [[736.4, 310], [736.4, 487.3]]},
            {"id": "PE_col_west", "points": [[799.3, 310], [799.3, 970.7]]},
        ],
        openings=[{"id": "D_r3", "kind": "door", "p1": [757.1, 487.3], "p2": [793.8, 487.3]}],
    )
    image_path = (archive_path('AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/review_bundle/rasters/1f_view.png'))
    with Image.open(image_path) as image:
        report = drawing_differences(image, sm25)
    item = next(row for row in report["items"]
                if row["type"] == "opening_offset_from_gap" and row["opening"] == "D_r3")
    assert item["gap"]["x_px"] == [745, 799]
    assert item["end_offsets_m"] == [0.26, -0.11]
    assert item["check"] == f"{OPENING_OFFSET_CHECK} {CONTINUOUS_SPACE_CHECK}"
