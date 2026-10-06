"""C4 public dispatch, compact feedback and coordinator boundary behavior."""

import asyncio
import copy
import json

import pytest

from src.agent.runtime_roles.coordinates import READER_COORDINATES, task_coordinates
from src.agent.runtime_roles.feedback import assembly_reply
from src.agent.runtime_roles.session import COORDINATOR_ORDINARY_TOOLS, EXTRA_TOOLS
from test_role_session import dispatch, environment  # noqa: F401


@pytest.mark.parametrize("instructions", [None, ""])
def test_public_dispatch_needs_origin_caps_instructions_and_accepts_structured_strings(environment, instructions):
    store, make = environment
    session = make()
    missing = asyncio.run(session.call_tool("delegate_readers", {"tasks": [dispatch()]}))
    long = asyncio.run(session.call_tool("delegate_readers", {"tasks": [dispatch(
        origin="Southwest corner", instructions="x" * 401)]}))
    assert missing["isError"] and long["isError"]
    assert not session.registry.records

    task = dispatch(origin="Southwest corner")
    if instructions is None:
        del task["instructions"]
    else:
        task["instructions"] = instructions
    raw = asyncio.run(session.call_tool("delegate_readers", {"tasks": json.dumps([task])}))
    assert not raw["isError"], raw
    row = raw["structuredContent"]["results"][0]
    assert row["status"] == "completed" and row["first_submission_passed"] is True
    assert "validation" not in row and "unresolved" not in row
    full = asyncio.run(session.call_tool("read_role_artifact", {"task_id": row["task_id"],
        "sha256": row["artifact"]["sha256"]}))["structuredContent"]
    assert full["record"]["validation"]["validation_passed"]
    assert full["artifact"]["unresolved"]
    admitted = session.registry.task(row["task_id"])
    assert admitted["coordinate_contract"]["units"] == READER_COORDINATES["elevation_reader"]
    assert "geometric values in metres" not in json.dumps(admitted)


def test_failed_dispatch_record_remains_readable(environment):
    _, make = environment
    session = make()
    task = session._task(dispatch())
    session.registry.save(task, status="failed", reason="Saved source failure")
    value = asyncio.run(session.call_tool("read_role_artifact", {"task_id": task["task_id"]}))
    assert not value["isError"]
    assert value["structuredContent"]["record"]["reason"] == "Saved source failure"
    assert value["structuredContent"]["artifact"] is None


def test_coordinator_catalog_and_ordinary_string_parameters(environment):
    _, make = environment
    session = make()
    async def catalog():
        return [{"name": name, "inputSchema": {"type": "object", "properties": {
            "enabled": {"type": "boolean"}, "items": {"type": "array"}},
            "additionalProperties": False}} for name in
            [*COORDINATOR_ORDINARY_TOOLS, "build_plan_bim", "claim_transaction"]]
    session.frozen.list_tools = catalog
    names = {t["name"] for t in asyncio.run(session.list_tools())}
    assert names == COORDINATOR_ORDINARY_TOOLS | {t["name"] for t in EXTRA_TOOLS}
    rejected = asyncio.run(session.call_tool("claim_transaction", {}))
    assert rejected["isError"] and not session.frozen.calls
    raw = asyncio.run(session.call_tool("inputs", {"enabled": "true", "items": "[1,2]"}))
    assert not raw["isError"]
    assert session.frozen.calls[-1] == ("inputs", {"enabled": True, "items": [1, 2]})
    raw = asyncio.run(session.call_tool("inputs", {"enabled": "yes"}))
    assert raw["isError"] and len(session.frozen.calls) == 1


def test_assembly_projection_keeps_decisions_recoverable_and_notes_in_receipt(tmp_path):
    value = {"status": "needs_decisions", "reader_notes": [{"task_id": "p1", "note": "keep fully"}],
        "decisions": [{"decision_id": str(i), "reason": "same reason", "action": "same action",
            "detail": {"bbox": [i, 1, 2, 3], "source_opening_id": f"W{i}"}} for i in range(2)]}
    original = copy.deepcopy(value)
    path = tmp_path / "assembly.json"
    path.write_text(json.dumps({"response": value}), encoding="utf-8")
    reply = assembly_reply(value, path)
    assert value == original
    assert reply["reader_notes"]["count"] == 1
    assert "keep fully" not in json.dumps(reply)
    for row, expected in zip(reply["decisions"], value["decisions"]):
        restored = {key: item for key, item in row.items() if key != "guidance"}
        restored.update(reply["decision_guidance"][row["guidance"]])
        assert restored == expected
    assert json.loads(path.read_bytes())["response"] == original


def test_coordinate_contract_has_role_specific_units():
    for role, target in (("plan_reader", "F1"), ("elevation_reader", "South/F1")):
        contract = task_coordinates({"role_id": role, "target": target, "origin": "corner"})
        assert contract["units"] == READER_COORDINATES[role]
    assert "opening points" in READER_COORDINATES["plan_reader"]
    assert "second anchor item" in READER_COORDINATES["plan_reader"]
    assert "x_px" in READER_COORDINATES["elevation_reader"]
    assert "absolute elevations" in READER_COORDINATES["elevation_reader"]
