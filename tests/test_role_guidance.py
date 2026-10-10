from scripts.tool_scripts.bim_agent_guidance import build_guide
import jsonschema

from src.agent.runtime_roles.elevation import elevation_submission_tool, expand_elevation_submission, validate_elevation_artifact
from src.agent.runtime_roles.guidance import (
    ELEVATION_EXAMPLE,
    COMPACT_ELEVATION_EXAMPLE,
    guidance_catalog,
    get_role_guide,
    get_role_tool_names,
)
from src.agent.runtime_roles.session import EXTRA_TOOLS


def test_reader_guides_are_single_image_and_keep_corresponding_existing_method():
    plan = get_role_guide("plan_reader")
    elevation = get_role_guide("elevation_reader")
    assert "exactly one original image" in plan
    assert "trial_plan_bim" in plan and "build_from_artifact" not in plan
    for unavailable in (
        "build_plan_bim", "inspect_plan_draft", "revise_plan_bim",
        "claim_transaction", "assemble_plan_bim",
    ):
        assert unavailable not in plan
    assert "trial_plan_bim" not in elevation
    assert "apply_elevation_heights" not in elevation


def test_elevation_guide_exposes_a_complete_valid_minimum_example():
    jsonschema.validate(COMPACT_ELEVATION_EXAMPLE, elevation_submission_tool()["inputSchema"])
    normalized = validate_elevation_artifact(expand_elevation_submission(COMPACT_ELEVATION_EXAMPLE, "North/F1"), image_name="North.png")
    assert normalized["image"] == "North.png"
    assert normalized["x_calibration"]["world_start_m"] == 10.0
    assert normalized["x_calibration"]["world_end_m"] == 0.0
    assert normalized["counts"] == [{"floor_id": "F1", "window_count": 1, "door_count": 0}]
    assert normalized["openings"][0]["width_m"] > 0
    assert normalized["openings"][0]["head_m"] > normalized["openings"][0]["sill_m"]
    assert normalized["regularization"]["grid_step_m"] == 0.1

def test_coordinator_guide_names_role_workflow_and_does_not_tell_it_to_draft():
    guide = get_role_guide("coordinator")
    for name in get_role_tool_names("coordinator"):
        assert name in guide
    assert "Do not draft walls or reread heights" in guide
    assert "Every >30cm difference must be explicitly\ndecided before finish_bim" in guide
    assert "Unchosen >30cm differences retain plan" not in guide
    tool_text = " ".join(tool["description"] for tool in EXTRA_TOOLS)
    assert ">30cm differences require an explicit decision before delivery" in tool_text
    assert "unchosen items retain plan" not in tool_text
    assert "runtime carries the prior task's located failure handoff automatically" in guide
    assert "explicit rework_targets" in tool_text
    assert "preserves every unpointed plan or elevation object and its original-reading audit" in tool_text


def test_catalog_reports_exact_character_counts_and_unchanged_single_model():
    before = build_guide(images="drawings", mesh=False)
    catalog = guidance_catalog()
    after = build_guide(images="drawings", mesh=False)
    assert before == after
    assert catalog["single_model"]["character_count"] == len(before)
    for role_id, row in catalog["roles"].items():
        assert row["character_count"] == len(get_role_guide(role_id))
        assert row["character_count"] > 0
