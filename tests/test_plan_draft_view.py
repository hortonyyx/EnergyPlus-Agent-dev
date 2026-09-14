"""Literal draft views expose declarations without turning them into source BIM."""
from PIL import Image

from src.agent.geometry.plan_draft_view import render_plan_draft


def test_plan_draft_view_keeps_declared_endpoints_and_categories():
    original = Image.new("RGB", (100, 80), "white")
    plan = {
        "footprint_pixels": [[10, 10], [90, 10], [90, 70], [10, 70]],
        # A diagonal is intentionally previewable even though the compiler rejects it.
        "partitions": [{"id": "hanging", "points": [[20, 20], [70, 50]]}],
        # This is intentionally off any host; the draft view must not move or trim it.
        "openings": [{"id": "D-away", "kind": "door", "p1": [40, 40], "p2": [60, 40]}],
    }

    preview, metadata = render_plan_draft(
        original, plan, image_name="plan.png", image_sha256="a" * 64,
        plan_file="plan_drafts/draft_001/plan.json", plan_sha256="b" * 64,
    )

    assert preview.size == (440, original.height + 24)
    assert preview.getpixel((50, 40)) == (255, 145, 0)
    assert metadata["declaration"] == plan
    assert metadata["rendered"]["footprint"][0]["declared_pixel_points"] == plan["footprint_pixels"]
    assert metadata["rendered"]["partitions"][0]["declared_pixel_points"] == [[20, 20], [70, 50]]
    assert metadata["rendered"]["openings"][0]["declared_p1"] == [40, 40]
    assert metadata["rendered"]["openings"][0]["declared_p2"] == [60, 40]
    assert metadata["unrenderable"] == []
    assert metadata["draft_only"] and not metadata["source_bim"]
    assert metadata["drawing_fidelity"] == "not_evaluated"
    assert metadata["room_status"] == "not_inferred_or_claimed"
    assert metadata["method"] == {
        "coordinate_frame": "identity_original_image_pixels",
        "original_image_box_in_preview": [0, 0, 100, 80],
        "preview_output_size": [440, 104],
        "endpoints_modified": False,
        "endpoint_markers_centered_at_declared_points": True,
        "partitions_extended_or_snapped": False,
        "openings_clipped_or_hosted": False,
        "spaces_or_rooms_derived": False,
    }


def test_plan_draft_view_lists_points_it_cannot_draw_without_joining_across_them():
    plan = {
        "footprint_pixels": [[1, 1], [19, 1], [19, 19], [1, 19]],
        "partitions": [{"id": "P1", "points": [[2, 2], ["bad", 4], [18, 18]]}],
        "openings": [{"id": "D1", "kind": "door", "p1": [-1, 5], "p2": [4, 5]}],
    }
    _, metadata = render_plan_draft(
        Image.new("RGB", (20, 20), "white"), plan,
        image_name="plan.png", image_sha256="a" * 64,
        plan_file="draft/plan.json", plan_sha256="b" * 64,
    )

    assert metadata["rendered"]["partitions"][0]["drawn_segment_count"] == 0
    assert not metadata["rendered"]["openings"][0]["drawn"]
    assert [row["path"] for row in metadata["unrenderable"]] == [
        "plan.partitions[0].points[1]", "plan.openings[0].p1",
    ]
    assert metadata["declaration"] == plan
