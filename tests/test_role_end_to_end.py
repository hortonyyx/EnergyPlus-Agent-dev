"""Real frozen-MCP D1 role pipeline and process-death recovery checks."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import Counter

import jsonschema
import pytest
from PIL import Image

from src.agent.geometry.plan_drawing_differences import drawing_differences
from src.agent.runtime_roles.entry import execute
from src.agent.runtime_roles.plan_review import opening_hosts, topology_issues
from src.agent.runtime_roles.submission import ELEVATION_SCHEMA, PLAN_SCHEMA
from src.agent.runtime_roles.trial import canonical_plan_sha256

from role_d1_fixtures import (
    CASES,
    assembly_review,
    elevation_submission,
    event_counts,
    make_fixture,
    plan_submission,
    reader_record,
)


class SimulatedProcessDeath(BaseException):
    pass


class CrashOnce:
    def __init__(self, boundary, predicate):
        self.boundary = boundary
        self.predicate = predicate
        self.triggered = False

    def __call__(self, boundary, engine):
        if not self.triggered and boundary == self.boundary and self.predicate(engine):
            self.triggered = True
            raise SimulatedProcessDeath(boundary)


def _events(output):
    rows = []
    for path in output.rglob("events.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            rows.append((path.relative_to(output).as_posix(), json.loads(line)["payload"]))
    return rows


def _reader_record_hashes(fixture):
    result = {}
    for path in (fixture.output / "tasks").glob("*/reader_record.json"):
        row = json.loads(path.read_bytes())
        result[row["task_id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _reader_events(fixture, task_id):
    # Child EventStores share the root append-only journal; task_id is carried
    # by the event envelope rather than a per-task events file.
    return [
        row["payload"]
        for line in (fixture.output / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if (row := json.loads(line))["task_id"] == task_id
    ]


def _reader_request_count(fixture):
    return sum(
        row.get("event_type") == "adapter_request"
        for task in fixture.tasks
        for row in _reader_events(fixture, task["task_id"])
    )


def _tool_count(output, name):
    return sum(
        row.get("event_type") == "tool_invocation" and row.get("tool_name") == name
        for _, row in _events(output)
    )


def _resume(fixture, *, fault_hook=None, reader_fault_hook=None):
    fixture.args.resume = True
    return asyncio.run(
        execute(
            fixture.args,
            adapter_factory=fixture.adapter_factory,
            fault_hook=fault_hook,
            reader_fault_hook=reader_fault_hook,
        )
    )


def _records(fixture):
    return [reader_record(fixture.output, task["task_id"]) for task in fixture.tasks]


def _assert_complete_pipeline(fixture, result, *, two_floors):
    assert result["status"] == "completed"
    assert result["finalization"]["status"] == "delivered"
    assert (fixture.output / "bim/delivery.json").is_file()
    assert (fixture.output / "bim/delivery.html").is_file()
    selection = json.loads(
        (fixture.output / "bim/delivery_selection.json").read_bytes()
    )
    source = json.loads(
        (
            fixture.output
            / "bim"
            / selection["candidate"]
            / "source_model.json"
        ).read_bytes()
    )
    assert source["source_model_sha256"] == selection["source_model_sha256"]
    assert len({space["floor_id"] for space in source["spaces"]}) == (2 if two_floors else 1)

    records = _records(fixture)
    assert all(record["status"] == "completed" for record in records)
    plan_records = [record for record in records if record["role_id"] == "plan_reader"]
    assert all(record["validation"]["validation_passed"] for record in plan_records)
    assert all(record["artifact"]["sha256"] for record in records)

    counts = event_counts(fixture.output)
    tools = Counter(counts.tools)
    assert tools["inputs"] == 1
    assert tools["delegate_readers"] == 1
    assert tools["trial_plan_bim"] == len(plan_records)
    assert tools["submit_plan_reading"] == len(plan_records)
    assert tools["submit_elevation_reading"] == 4
    assert tools["read_role_artifact"] == len(records)
    assert tools["build_from_artifact"] == len(plan_records)
    assert tools["match_elevation"] == 4
    assert tools["apply_elevation_heights"] == 4
    assert tools["check_openings"] == 1
    assert tools["inspect_candidate"] == 1
    assert tools["finish_bim"] == 1
    assert tools["assemble_plan_bim"] == (1 if two_floors else 0)
    assert tools["inspect_plan_draft"] == (2 if two_floors else 0)

    matches = [
        json.loads(path.read_bytes())
        for path in (fixture.output / "role_matches").glob("*.json")
    ]
    assert len(matches) == 4
    assert all(row["result"]["matches"] for row in matches)
    assert all(not row["result"]["conflicts"] for row in matches)
    assert all(not row["result"]["source_only"] for row in matches)
    assert all(not row["result"]["elevation_only"] for row in matches)
    accounting = result["role_accounting"]
    assert accounting["requests"] > 0
    assert accounting["by_role"]["coordinator"]["requests"] > 0
    assert accounting["by_role"]["plan_reader"]["requests"] == len(plan_records) * 3
    assert accounting["by_role"]["elevation_reader"]["requests"] == 8
    review = assembly_review(fixture.output)
    assert review and review["status"] in {"unchanged", "reviewed"}
    if review["status"] == "reviewed":
        assert {row["change_id"] for row in review["changes"]} == {
            row["change_id"] for row in review["decisions"]
        }


@pytest.mark.parametrize(("case_name", "two_floors"), [("sm21", True), ("sm24", False), ("sm25", True)])
def test_scripted_role_pipeline_runs_real_frozen_mcp(tmp_path, case_name, two_floors):
    fixture = make_fixture(case_name, tmp_path)
    result = asyncio.run(
        execute(fixture.args, adapter_factory=fixture.adapter_factory)
    )
    _assert_complete_pipeline(fixture, result, two_floors=two_floors)


@pytest.mark.parametrize("case_name", ["sm21", "sm24", "sm25"])
def test_fixture_submissions_match_explicit_tool_contracts(tmp_path, case_name):
    fixture = make_fixture(case_name, tmp_path)
    assert fixture.args.max_candidates == 24
    for artifact in fixture.plan_artifacts.values():
        arguments = plan_submission(artifact)
        jsonschema.validate(arguments, PLAN_SCHEMA)
        assert len(opening_hosts(artifact["plan"])) == len(artifact["plan"].get("openings", []))
        image_name = "1f_view.png" if artifact["plan"]["floor_id"] == "F1" else "2f_view.png"
        with Image.open(CASES[case_name] / "images" / image_name) as image:
            differences = drawing_differences(image, artifact["plan"])
        assert topology_issues([{
            "plan_sha256": canonical_plan_sha256(artifact["plan"]),
            "drawing_differences": differences,
        }]) == []
        assert arguments["topology_decisions"] == []
    for artifact in fixture.elevation_artifacts.values():
        arguments = elevation_submission(artifact)
        jsonschema.validate(arguments, ELEVATION_SCHEMA)
        assert set(arguments) == set(ELEVATION_SCHEMA["required"])


def test_resume_reader_after_trial_checkpoint_does_not_repeat_trial(tmp_path):
    fixture = make_fixture("sm24", tmp_path)
    crash = CrashOnce(
        "after_checkpoint",
        lambda engine: engine.role.role_id == "plan_reader"
        and engine.counts["tool_calls"] == 1,
    )
    with pytest.raises(SimulatedProcessDeath):
        asyncio.run(
            execute(
                fixture.args,
                adapter_factory=fixture.adapter_factory,
                reader_fault_hook=crash,
            )
        )
    assert crash.triggered
    assert _tool_count(fixture.output, "trial_plan_bim") == 1

    result = _resume(fixture)
    _assert_complete_pipeline(fixture, result, two_floors=False)
    assert _tool_count(fixture.output, "trial_plan_bim") == 1
    plan_task = next(task for task in fixture.tasks if task["role_id"] == "plan_reader")
    plan_events = [
        row
        for row in _reader_events(fixture, plan_task["task_id"])
        if row.get("event_type") == "adapter_request"
    ]
    assert len(plan_events) == 3


def test_resume_after_all_readers_preserves_reader_records(tmp_path):
    fixture = make_fixture("sm24", tmp_path)

    def all_readers_before_build(engine):
        return (
            len(_reader_record_hashes(fixture)) == len(fixture.tasks)
            and _tool_count(fixture.output, "build_from_artifact") == 0
        )

    crash = CrashOnce("after_checkpoint", all_readers_before_build)
    with pytest.raises(SimulatedProcessDeath):
        asyncio.run(
            execute(
                fixture.args,
                adapter_factory=fixture.adapter_factory,
                fault_hook=crash,
            )
        )
    hashes_at_crash = _reader_record_hashes(fixture)
    reader_requests_at_crash = _reader_request_count(fixture)
    assert reader_requests_at_crash > 0

    result = _resume(fixture)
    _assert_complete_pipeline(fixture, result, two_floors=False)
    assert _reader_record_hashes(fixture) == hashes_at_crash
    assert _reader_request_count(fixture) == reader_requests_at_crash


def test_resume_after_build_execution_does_not_repeat_build(tmp_path):
    fixture = make_fixture("sm24", tmp_path)

    def built_once(engine):
        executions = [
            event.payload
            for event in engine.store.events
            if event.payload.event_type == "tool_execution"
        ]
        return bool(executions and executions[-1].tool_name == "build_from_artifact")

    crash = CrashOnce("after_execution", built_once)
    with pytest.raises(SimulatedProcessDeath):
        asyncio.run(
            execute(
                fixture.args,
                adapter_factory=fixture.adapter_factory,
                fault_hook=crash,
            )
        )
    assert _tool_count(fixture.output, "build_from_artifact") == 1
    candidates_at_crash = len(list((fixture.output / "bim").glob("candidate_*")))

    result = _resume(fixture)
    _assert_complete_pipeline(fixture, result, two_floors=False)
    assert _tool_count(fixture.output, "build_from_artifact") == 1
    # Later height applications create candidates; the original plan build did
    # not create a second base candidate during recovery.
    assert candidates_at_crash == 1
