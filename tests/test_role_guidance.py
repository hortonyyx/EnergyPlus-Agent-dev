from scripts.tool_scripts.bim_agent_guidance import build_guide
from src.agent.runtime_roles.elevation import validate_elevation_artifact
from src.agent.runtime_roles.guidance import (
    ELEVATION_EXAMPLE,
    guidance_catalog,
    get_role_guide,
    get_role_tool_names,
)


def test_reader_guides_are_single_image_and_keep_corresponding_existing_method():
    plan = get_role_guide("plan_reader")
    elevation = get_role_guide("elevation_reader")
    assert "exactly one original image" in plan
    assert "CALIBRATE ONCE PER PLAN" in plan and "RESOLVE THE DIFFERENCES" in plan
    assert "trial_plan_bim" in plan and "build_from_artifact" not in plan
    for unavailable in (
        "build_plan_bim", "inspect_plan_draft", "revise_plan_bim",
        "claim_transaction", "assemble_plan_bim",
    ):
        assert unavailable not in plan
    assert "HEIGHTS FROM ELEVATIONS" in elevation and "trial_plan_bim" not in elevation
    assert "apply_elevation_heights" not in elevation


def test_elevation_guide_exposes_a_complete_valid_minimum_example():
    normalized = validate_elevation_artifact(ELEVATION_EXAMPLE, image_name="North.png")
    assert normalized["image"] == "North.png"
    assert normalized["x_calibration"]["world_start_m"] == 10.0
    assert normalized["x_calibration"]["world_end_m"] == 0.0
    assert normalized["counts"] == [{"floor_id": "F1", "window_count": 1, "door_count": 0}]

    guide = get_role_guide("elevation_reader")
    for required in (
        "world_start_m", "world_end_m", '"kind":"ground"',
        '"kind":"window"', "annotation_and_pixels",
    ):
        assert required in guide


def test_coordinator_guide_names_role_workflow_and_does_not_tell_it_to_draft():
    guide = get_role_guide("coordinator")
    for name in get_role_tool_names("coordinator"):
        assert name in guide
    assert "does not independently draft plan walls" in guide


def test_catalog_reports_exact_character_counts_and_unchanged_single_model():
    before = build_guide(images="drawings", mesh=False)
    catalog = guidance_catalog()
    after = build_guide(images="drawings", mesh=False)
    assert before == after
    assert catalog["single_model"]["character_count"] == len(before)
    for role_id, row in catalog["roles"].items():
        assert row["character_count"] == len(get_role_guide(role_id))
        assert row["character_count"] > 0
