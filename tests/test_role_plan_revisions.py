"""D1c draft/edit boundaries, whole-plan feedback and preservation contracts."""

import asyncio
import copy
import json

import jsonschema
import pytest

from src.agent.geometry.plan_partition import compile_plan_partition
from src.agent.runtime_roles.guidance import PLAN_READER_GUIDANCE
from src.agent.runtime_roles.plan_format import PLAN_EXAMPLE, READER_PLAN_EXAMPLE, plan_format_errors
from src.agent.runtime_roles.plan_review import revise_operations, validate_wall_reference
from src.agent.runtime_roles.readers import ReaderTools
from src.agent.runtime_roles.submission import WALL_REFERENCE_EXAMPLE
from src.agent.runtime_roles.trial import PlanTrial
from tests.test_role_readers import Frozen, plan
from tests.test_role_submission import operation
from tests.test_role_trial import Tools


def test_reference_example_is_complete_compilable_and_present_in_reader_guidance():
    assert plan_format_errors(PLAN_EXAMPLE) == []
    proposal, _ = compile_plan_partition(PLAN_EXAMPLE, image_size=(12, 8), image_name="plan.png")
    assert proposal
    for stale in ("Even a failed trial is the next rework base", "base_plan_sha256", "finishing budget below"):
        assert stale not in PLAN_READER_GUIDANCE


def test_reader_example_is_the_reference_plan_at_image_scale():
    assert plan_format_errors(READER_PLAN_EXAMPLE) == []
    proposal, _ = compile_plan_partition(READER_PLAN_EXAMPLE, image_size=(600, 420), image_name="plan.png")
    assert proposal
    reference, _ = compile_plan_partition(PLAN_EXAMPLE, image_size=(12, 8), image_name="plan.png")
    assert proposal["geometry"] == reference["geometry"]
    assert json.dumps(READER_PLAN_EXAMPLE, ensure_ascii=False, separators=(",", ":")) in PLAN_READER_GUIDANCE
    assert all(value > 20 for row in READER_PLAN_EXAMPLE["footprint_pixels"] for value in row)


def test_world_metre_points_and_invented_room_uses_are_named_before_compiling():
    # 10-06 probe run2: anchors and footprint in pixels, dividers and openings in metres.
    value = plan()
    value["x_anchors"] = [[247, 0], [613, 10]]
    value["y_anchors"] = [[878, 0], [150, 20]]
    value["footprint_pixels"] = [[247, 150], [613, 150], [613, 878], [247, 878]]
    value["partitions"] = [{"id": "west", "points": [[4.18, 19.75], [4.18, 0.25]], "source_refs": ["plan.png: wall"]}]
    value["openings"] = [{"id": "D_main", "kind": "door", "p1": [0.54, 20], "p2": [2.14, 20],
                          "z": [0, 2.1], "source_refs": ["plan.png: door"]}]
    value["space_seeds"] = [{"id": "hall", "point": [400, 500], "role": "open_office_meeting"},
                            {"id": "office", "point": [300, 300], "role": "office"}]
    errors = {row["path"]: row["message"] for row in plan_format_errors(value)}
    assert "never world metres" in errors["plan.partitions[0]"]
    assert "never world metres" in errors["plan.openings[0]"]
    assert "not a room_types code" in errors["plan.space_seeds[0].role"]
    assert not any(path.startswith("plan.space_seeds[1]") for path in errors)
    pixels = copy.deepcopy(value)
    pixels["partitions"][0]["points"] = [[400, 150], [400, 878]]
    pixels["openings"][0].update(p1=[267, 150], p2=[327, 150])
    pixels["space_seeds"][0]["role"] = "Office"
    assert plan_format_errors(pixels) == []


def test_all_rows_and_nested_formats_reported_in_one_response_without_compiler_call():
    async def scenario():
        value = plan()
        del value["ceiling_height"]
        value["units"] = "mm"
        value["partitions"] = [{"id": "P1", "p1": [1, 1], "p2": [2, 2]},
                               {"id": "P2", "points": [[1], [False, 3]], "source_refs": []}]
        value["space_seeds"] = [{"id": "S1", "seed": [1, 2]}, {"id": "S1", "point": [1, "x"]}]
        value["openings"] *= 2
        value["openings"][0]["room"] = "left"
        tools = Tools()
        trial = PlanTrial(tools, image_name="plan.png")
        reader = ReaderTools(Frozen(), role_id="plan_reader", image_name="plan.png", trial=trial)
        envelope = await reader.call_tool("trial_plan_bim", {"plan": value})
        receipt = envelope["structuredContent"]
        assert receipt["error_type"] == "plan_format" and tools.calls == []
        assert receipt["repair_hint"]["example"] == READER_PLAN_EXAMPLE
        errors = receipt["format_errors"]
        assert any(row["path"] == "plan" and "ceiling_height" in row["message"] for row in errors)
        for collection in ("partitions", "space_seeds", "openings"):
            for index in (0, 1):
                assert any(row["path"].startswith(f"plan.{collection}[{index}]") for row in errors)
        assert all(row["message"] in envelope["content"][-1]["text"] for row in errors)
        assert trial.baseline() == (None, None)
        assert (await reader.call_tool("trial_plan_bim", {"plan": plan()}))["structuredContent"]["status"] == "passed"
    asyncio.run(scenario())


def test_all_alias_conflicts_and_bad_quantities_are_listed_together():
    value = plan()
    value["partitions"][0]["pixels"] = value["partitions"][0]["points"]
    value["space_seeds"][0]["pixels"] = value["space_seeds"][0]["point"]
    value["z_floor"] = {"value": "0", "unit": "feet"}
    value["openings"][0]["z"] = [float("nan"), True]
    errors = plan_format_errors(value)
    assert sum("both pixels" in row["message"] for row in errors) == 2
    assert {row["path"] for row in errors} >= {"plan.z_floor", "plan.openings[0].z[0]", "plan.openings[0].z[1]"}


def test_compile_failures_allow_full_redrafting_then_failed_revision_preserves_last_success():
    async def scenario():
        tools = Tools(ready=False)
        trial = PlanTrial(tools, image_name="plan.png")
        first = await trial.run(plan())
        assert first["source_geometry_ready"] is False and trial.baseline() == (None, None)
        second_plan = plan()
        second_plan["basis"] += " revised calibration"
        second = await trial.run(second_plan)
        assert second["base_plan_sha256"] is None
        tools.ready = True
        third_plan = plan()
        third_plan["basis"] += " final calibration"
        good = await trial.run(third_plan)
        tools.ready = False
        bad = await trial.run(operations=[operation(p2=[10, 42])])
        assert bad["status"] == "failed" and bad["phase"] == "operations"
        assert trial.baseline() == (third_plan, good["plan_sha256"])
        tools.ready = True
        repaired = await trial.run(operations=[operation(p2=[10, 41])])
        assert repaired["base_plan_sha256"] == good["plan_sha256"]
        assert repaired["changes"][0]["before"]["p2"] == [10, 40]
        assert repaired["plan_revision"]["unchanged_ids"]["partitions"] == ["P1"]
        with pytest.raises(ValueError, match="operations"):
            await trial.run(trial.load_plan(repaired))
    asyncio.run(scenario())


def test_all_shared_operation_kinds_and_failed_batch_leave_input_unchanged():
    value = plan()
    original = copy.deepcopy(value)
    common = {"reason": "located correction", "source_refs": ["plan.png: original"], "bbox": [0, 0, 100, 100]}
    operations = [
        {**common, "op": "update", "collection": "openings", "id": "W1", "changes": {"p2": [10, 41]}},
        {**common, "op": "add", "collection": "space_seeds", "value": {"id": "right", "point": [80, 40]}},
        {**common, "op": "remove", "collection": "partitions", "id": "P1"},
        {**common, "op": "set", "field": "basis", "value": "revised observation"},
    ]
    changed, audit = revise_operations(value, operations)
    assert len(audit["actual_changes"]) == 4 and value == original
    assert changed["partitions"] == [] and changed["space_seeds"][0] == value["space_seeds"][0]
    with pytest.raises(ValueError, match="does not exist"):
        revise_operations(value, [operations[0], {**operations[2], "id": "missing"}])
    assert value == original


def test_role_tool_catalog_removes_manual_bookkeeping_and_accepts_only_one_mode():
    async def scenario():
        reader = ReaderTools(Frozen(), role_id="plan_reader", image_name="plan.png", trial=PlanTrial(Tools(), image_name="plan.png"))
        schema = next(tool["inputSchema"] for tool in await reader.list_tools() if tool["name"] == "trial_plan_bim")
        assert set(schema["properties"]) == {"plan", "operations"}
        jsonschema.validate({"operations": [operation(p2=[10, 41])]}, schema)
        for arguments in ({"plan": plan(), "base_plan_sha256": "a" * 64},
                          {"plan": plan(), "changes": []}, {"plan": plan(), "operations": []}):
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(arguments, schema)
            assert (await reader.call_tool("trial_plan_bim", arguments))["isError"]
        assert (await reader.call_tool("trial_plan_bim", {"operations": [operation(p2=[10, 41])]}))["isError"]
    asyncio.run(scenario())


def test_cross_task_operations_only_touch_named_targets_and_continue_from_new_baseline():
    async def scenario():
        prior = PlanTrial(Tools(), image_name="plan.png")
        good = await prior.run(plan())
        current = PlanTrial(Tools(), image_name="plan.png")
        current.inherit_reference(prior, good["plan_sha256"], ["plan.openings:W1"])
        with pytest.raises(ValueError, match="operations"):
            await current.run(plan())
        with pytest.raises(ValueError, match="outside the coordinator"):
            await current.run(operations=[{**operation(), "collection": "partitions", "id": "P1",
                                          "changes": {"points": [[61, 10], [61, 110]]}}])
        one = await current.run(operations=[operation(p2=[10, 41])])
        two = await current.run(operations=[operation(p2=[10, 42])])
        assert one["base_plan_sha256"] == good["plan_sha256"]
        assert two["base_plan_sha256"] == one["plan_sha256"]
        assert current.load_plan(two)["partitions"] == plan()["partitions"]
        assert current.load_plan(two)["space_seeds"] == plan()["space_seeds"]
        with pytest.raises(ValueError, match="rework_targets"):
            current.inherit_reference(prior, good["plan_sha256"], ["plan.openings"])
        failed = PlanTrial(Tools(False), image_name="plan.png")
        failed_receipt = await failed.run(plan())
        with pytest.raises(ValueError, match="successful isolated trial"):
            current.inherit_reference(failed, failed_receipt["plan_sha256"], ["plan.openings:W1"])
    asyncio.run(scenario())


def test_failed_noop_revision_does_not_invalidate_prior_success_with_same_hash():
    async def scenario():
        tools = Tools()
        trial = PlanTrial(tools, image_name="plan.png")
        good = await trial.run(plan())
        tools.ready = False
        failed = await trial.run(operations=[operation(p2=[10, 40])])
        assert failed["plan_sha256"] == good["plan_sha256"] and failed["changes"] == []
        assert trial.verified_plan(good["plan_sha256"])[1]["validation_passed"]
        assert trial.require_success(plan()) == good
    asyncio.run(scenario())


def test_invalid_operation_type_is_a_correctable_prewrite_rejection():
    async def scenario():
        tools = Tools()
        trial = PlanTrial(tools, image_name="plan.png")
        good = await trial.run(plan())
        reader = ReaderTools(Frozen(), role_id="plan_reader", image_name="plan.png", trial=trial)
        bad = await reader.call_tool("trial_plan_bim", {"operations": [{**operation(p2=[10, 41]), "op": []}]})
        assert bad["isError"] and bad["structuredContent"]["status"] == "rejected"
        assert len(tools.calls) == 1 and trial.baseline()[1] == good["plan_sha256"]
    asyncio.run(scenario())


def test_wall_reference_allows_distinct_lines_but_rejects_contradiction_per_category():
    assert validate_wall_reference(WALL_REFERENCE_EXAMPLE) == WALL_REFERENCE_EXAMPLE
    invalid = copy.deepcopy(WALL_REFERENCE_EXAMPLE)
    invalid["partitions"]["dimension_basis"] = "outer_face"
    with pytest.raises(ValueError, match="partitions.*same declared"):
        validate_wall_reference(invalid)
    with pytest.raises(ValueError, match="separate perimeter"):
        validate_wall_reference(WALL_REFERENCE_EXAMPLE["perimeter"])
