from pathlib import Path

from PIL import Image, ImageDraw

from src.agent.geometry.plan_drawing_differences import (
    CONTINUOUS_SPACE_CHECK,
    OPENING_OFFSET_CHECK,
    compact_differences,
    drawing_differences,
)

# 0.01 m per pixel; a 5 x 3 m building with a filled exterior band.
PLAN = {"floor_id": "F1", "x_anchors": [[50, 0], [550, 5]], "y_anchors": [[350, 0], [50, 3]],
        "footprint_pixels": [[50, 50], [550, 50], [550, 350], [50, 350]], "partitions": [], "openings": []}


def drawing(*, divider_gap=None, arcs=False, furniture=False, extra_dividers=(), dividers=(296, 304), tables=()):
    image = Image.new("RGB", (600, 400), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 550, 350], fill=(128, 128, 128))
    draw.rectangle([70, 70, 530, 330], fill="black")
    for x0, y0, x1, y1 in tables:  # free-standing double-outlined furniture
        draw.rectangle([x0, y0, x1, y1], outline="white")
        draw.rectangle([x0 + 6, y0 + 6, x1 - 6, y1 - 6], outline="white")
    for x in (*dividers, *extra_dividers):
        if divider_gap:
            draw.line([(x, 70), (x, divider_gap[0])], fill="white")
            draw.line([(x, divider_gap[1]), (x, 330)], fill="white")
        else:
            draw.line([(x, 70), (x, 330)], fill="white")
    if arcs:  # double-door arcs touching the wall line at the middle of the doorway
        middle = (divider_gap[0] + divider_gap[1]) // 2
        draw.line([(296, middle - 1), (304, middle + 1)], fill=(0, 255, 255))
    if furniture:  # a free-standing double-outlined table
        draw.rectangle([120, 150, 260, 230], outline="white")
        draw.rectangle([126, 156, 254, 224], outline="white")
    return image


def plan(**changes):
    return {**PLAN, **changes}


def divider(x=300):
    return [{"id": "wall", "points": [[x, 50], [x, 350]]}]


def door(y0, y1, x=300, kind="door"):
    return [{"id": "D1", "kind": kind, "p1": [x, y0], "p2": [x, y1]}]


def kinds(report):
    return [row["type"] for row in report["items"]]


def test_drawn_divider_missing_from_declaration_is_reported_with_its_place():
    report = drawing_differences(drawing(), plan())
    assert kinds(report) == ["undeclared_wall_line"]
    item = report["items"][0]
    assert item["axis"] == "vertical" and abs(item["x_m"] - 2.5) < 0.05 and item["length_m"] >= 2.5
    assert report["status"] == "reported" and report["scope"]


def test_declared_divider_and_free_standing_furniture_give_no_items():
    assert kinds(drawing_differences(drawing(furniture=True), plan(partitions=divider()))) == []


def test_door_on_continuous_wall_and_the_undeclared_gap_are_reported():
    report = drawing_differences(drawing(divider_gap=(150, 240)),
                                 plan(partitions=divider(), openings=door(260, 320)))
    assert set(kinds(report)) == {"opening_on_continuous_ink", "wall_gap_without_opening"}
    gap = next(row for row in report["items"] if row["type"] == "wall_gap_without_opening")
    assert abs(gap["gap_m"] - 0.89) < 0.05


def test_matching_door_is_quiet_and_an_offset_end_is_reported():
    quiet = drawing_differences(drawing(divider_gap=(150, 240)), plan(partitions=divider(), openings=door(150, 240)))
    assert kinds(quiet) == []
    offset = drawing_differences(drawing(divider_gap=(150, 240)), plan(partitions=divider(), openings=door(150, 270)))
    assert kinds(offset) == ["opening_offset_from_gap"]
    start, end = offset["items"][0]["end_offsets_m"]
    assert abs(start) <= 0.02 and abs(end - 0.3) <= 0.02
    assert offset["items"][0]["check"] == OPENING_OFFSET_CHECK


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
    image_path = (Path(__file__).parents[1] /
                  "AI_agent/logs/experiments/2026-08-20_sm25_conversion_request/"
                  "review_bundle/rasters/1f_view.png")
    with Image.open(image_path) as image:
        report = drawing_differences(image, sm25)
    item = next(row for row in report["items"]
                if row["type"] == "opening_offset_from_gap" and row["opening"] == "D_r3")
    assert item["gap"]["x_px"] == [745, 799]
    assert item["end_offsets_m"] == [0.26, -0.11]
    assert item["check"] == f"{OPENING_OFFSET_CHECK} {CONTINUOUS_SPACE_CHECK}"


def test_arc_ink_inside_a_doorway_does_not_split_the_gap():
    report = drawing_differences(drawing(divider_gap=(150, 240), arcs=True),
                                 plan(partitions=divider(), openings=door(150, 240)))
    assert kinds(report) == []


def test_declared_divider_where_nothing_is_drawn():
    report = drawing_differences(drawing(), plan(partitions=divider() + [{"id": "ghost", "points": [[420, 50], [420, 350]]}]))
    assert kinds(report) == ["declared_divider_with_little_ink"]
    assert report["items"][0]["divider"] == "ghost"


def test_no_declared_dividers_with_several_drawn_walls_gives_one_alert():
    report = drawing_differences(drawing(extra_dividers=(150, 158, 420, 428)), plan())
    assert kinds(report)[0] == "no_dividers_declared" and report["items"][0]["ink_lines"] >= 3
    assert report["items"][0]["scope"] == "floor"


def test_open_room_with_free_standing_double_line_furniture_gives_no_items():
    tables = [(100, 120, 300, 200), (320, 120, 500, 200), (150, 230, 450, 300)]
    report = drawing_differences(drawing(dividers=(), tables=tables), plan())
    assert kinds(report) == []


def test_implausible_scale_is_not_checked_and_says_why():
    report = drawing_differences(drawing(), plan(x_anchors=[[50, 0], [550, 5000]], y_anchors=[[350, 0], [50, 3000]]))
    assert report["status"] == "not_checked" and "implausible" in report["reason"] and report["items"] == []


def test_compact_form_keeps_counts_and_marks_truncation():
    report = drawing_differences(drawing(extra_dividers=(150, 158, 420, 428)), plan())
    short = compact_differences(report, limit=1)
    assert short["total"] == report["total"] and len(short["items"]) == 1
    assert short["truncated"] is (report["total"] > 1) and short["meaning"] and "inspect_plan_draft" in short["full_list"]


def test_double_lines_interrupted_by_doors_still_find_missing_divider():
    image = drawing(divider_gap=(150,240))
    report = drawing_differences(image, plan())
    assert any(item['type']=='undeclared_wall_line' and abs(item['x_m']-2.5)<.05
               for item in report['items'])


def test_full_width_open_separator_does_not_hide_unsupported_partition():
    image = drawing(dividers=())
    report = drawing_differences(image, plan(partitions=divider(), openings=door(50,350,kind='open')))
    assert kinds(report) == ['unsupported_open_separator']
    assert report['items'][0]['opening'] == 'D1'
    # A normal door gap in a supported wall is not a fake partition diagnosis.
    report = drawing_differences(drawing(divider_gap=(150,240)),
                                plan(partitions=divider(), openings=door(150,240,kind='open')))
    assert 'unsupported_open_separator' not in kinds(report)


def test_zero_and_unchecked_results_state_the_actual_scope():
    report = drawing_differences(drawing(),plan(partitions=divider()))
    assert report['total'] == 0
    assert report['coverage']['declared_divider_count'] == 1
    assert report['coverage']['tested_divider_segments'] == 1
    assert report['coverage']['not_checked'] and report['coverage']['zero_means']
    assert compact_differences(report)['coverage'] == report['coverage']


def test_interrupted_face_does_not_pair_long_wall_with_short_furniture_edge():
    # Earlier A4 tuning paired a short desk edge with a long corridor face in
    # sm21. Both have ink, but they are not the two faces of the same wall.
    import numpy as np
    from src.agent.geometry.plan_drawing_differences import _interrupted_pairs
    ink = np.zeros((200,600), dtype=bool)
    ink[80,50:550] = True
    ink[80,250:315] = False
    ink[88,350:490] = True
    assert not _interrupted_pairs(ink, 'h', .01, .01)
