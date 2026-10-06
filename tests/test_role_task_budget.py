"""Reader allowances come from the role, not from the coordinator's guess."""

import jsonschema
import pytest

from src.agent.runtime_roles.session import EXTRA_TOOLS, ROLE_TASK_BUDGET, TASK_SCHEMA


def test_coordinator_cannot_set_reader_budgets_but_internal_tasks_still_can():
    # 10-06 sm24 debug: the coordinator gave readers 100-120k tokens; they stopped
    # after two or three requests.
    schema = next(tool for tool in EXTRA_TOOLS if tool["name"] == "delegate_readers")["inputSchema"]
    task = {"task_id": "plan_f1", "role_id": "plan_reader", "image": "1f_view.png",
            "target": "F1", "instructions": "Read this floor."}
    jsonschema.validate({"tasks": [task]}, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"tasks": [{**task, "budget": {"tokens": 120000}}]}, schema)
    jsonschema.validate({**task, "budget": {"model_calls": 30}}, TASK_SCHEMA)


def test_role_defaults_cover_measured_reader_use_and_leave_tokens_to_the_run():
    # Measured on GLM-5.3-Flash: plan reader 19-30 requests, elevation reader up to 8.
    assert ROLE_TASK_BUDGET["plan_reader"]["model_calls"] >= 30
    assert ROLE_TASK_BUDGET["elevation_reader"]["model_calls"] >= 8
    assert all("tokens" not in budget for budget in ROLE_TASK_BUDGET.values())
