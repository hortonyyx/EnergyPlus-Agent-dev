"""Offline end-to-end continuation, persistence and stopping-boundary checks."""
import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from scripts.tool_scripts import run_bim_agent as runner
from scripts.tool_scripts.bim_agent_continuation import (
    current_delivery, persisted_state, record_work_review, run_continuations,
)
from tests.test_bim_agent_tools import _json_result, _server_session
from tests.test_bim_claims import setup_run
from tests.test_bim_height_coverage import _confirm_window, _window_claim


def read(path):
    return json.loads(path.read_text())


def receipt():
    return {"elapsed_seconds": 2, "returncode": 0,
            "result": {"is_error": False, "result": "Saved, with unresolved items.", "total_cost_usd": .1}}


def test_same_run_preserves_height_confirmation_across_use_edit_then_accepts_explained_stop(tmp_path, monkeypatch):
    old, _ = setup_run(tmp_path)
    (old / "seed/report.json").write_text('{"evaluation":"DO_NOT_EXPOSE"}')
    calls = []

    def invoke(run, prompt, **kwargs):
        calls.append(kwargs)
        toolkit = runner.Toolkit(run)
        assert "DO_NOT_EXPOSE" not in prompt
        assert kwargs["timeout"] <= 300
        if kwargs["name"] != "agent":
            assert kwargs["receipt_context"]["role"] == "main_agent_continuation"
            assert "scope sentinel" in prompt and "Current saved delivery" in prompt
            assert 'Shared candidate export budget: {"limit": 24' in prompt
            assert read(run / "work_turn.json")["active"]
        if kwargs["name"] == "continuation_01":
            record_work_review(toolkit, "seed", "continue", "Height evidence is in scope", "Confirm window")
            row = _window_claim(toolkit)
            _confirm_window(toolkit, row["id"], {"z": {"claim": row["id"], "value": "height"}})
        elif kwargs["name"] == "continuation_02":
            assert current_delivery(toolkit)["height_coverage"]["summary"]["image_linked_count"] == 1
            record_work_review(toolkit, "seed", "continue", "Use remains unexamined", "Record explained unknown")
            identity = read(run / "seed/source_model.json")["spaces"][0]["id"]
            result = toolkit.revise("seed", json.dumps([dict(op="set_space_role", space_id=identity,
                role="unknown", basis="unknown", source_refs=["plan.png synthetic blank interior"],
                assumptions=["No room-use label or furniture evidence"], reason="Review ambiguous room")]))
            assert result["source_geometry_ready"]
            runner.dump(run / "delivery_selection.json", {"candidate": result["candidate"]})
        elif kwargs["name"] == "continuation_03":
            delivery = current_delivery(toolkit)
            assert delivery["height_coverage"]["summary"]["image_linked_count"] == 1
            assert delivery["room_use_review"]["summary"]["unknown_count"] == 1
            record_work_review(toolkit, delivery["candidate"], "stop", "Other rooms outside scope; internal height unavailable")
        row = receipt()
        runner.dump(run / f"{kwargs['name']}_receipt.json", row)
        return row

    monkeypatch.setattr(runner, "subscription", invoke)
    args = SimpleNamespace(images=old / "images", out=tmp_path / "continued", scope="scope sentinel",
                           timeout=300, resume_candidate=old / "seed", continuation_rounds=3)
    runner.run_experiment(args)
    summary, delivery = read(args.out / "summary.json"), read(args.out / "delivery.json")
    assert len(calls) == summary["subscription_invocations"] == 4
    assert summary["elapsed_seconds"] == 8
    assert summary["estimated_cost_usd"] == .4
    assert summary["continuation"]["stop_reason"] == "model_stop"
    assert summary["continuation"]["task_completion"] == "not_certified"
    assert [t["persisted_source_or_evidence_changed"] for t in summary["continuation"]["turns"]] == [True, True, False]
    assert delivery["generation_status"]["continuation"] == summary["continuation"]
    assert delivery["height_coverage"]["summary"]["unchecked_height_opening_ids"] == ["door"]
    assert not read(args.out / "work_turn.json")["active"]
    before, after = read(args.out / "seed/source_model.json"), read(args.out / delivery["source_model"])
    for field in ("floors", "boundaries", "openings", "connections", "opening_hosts", "boundary_relations"):
        assert before[field] == after[field]


@pytest.mark.parametrize("mode, expected, count", [
    ("disabled", "disabled", 0), ("deadline", "deadline_reserve", 0),
    ("initial_error", "invocation_interrupted", 0), ("no_candidate", "no_saved_candidate", 0),
    ("no_change", "no_persisted_change", 1), ("missing_decision", "missing_work_decision", 1),
    ("turn_error", "invocation_interrupted", 1), ("limit", "round_limit", 1),
])
def test_stops_without_prose_or_view_logs_counting_as_progress(tmp_path, mode, expected, count):
    run, toolkit = setup_run(tmp_path)
    toolkit.manifest["deadline_epoch"] = time.time() + (10 if mode == "deadline" else 300)
    start = receipt()
    if mode == "initial_error":
        start["result"]["is_error"] = True
    if mode == "no_candidate":
        (run / "seed/source_model.json").unlink()
    calls = []

    def invoke(prompt, **kwargs):
        calls.append(kwargs)
        toolkit.log("view_image", {"prose": "I reviewed everything"})
        if mode != "missing_decision":
            record_work_review(toolkit, "seed", "continue", "Review useful evidence", "Confirm window")
        if mode == "limit":
            row = _window_claim(toolkit)
            _confirm_window(toolkit, row["id"], {"z": {"claim": row["id"], "value": "height"}})
        returned = receipt()
        if mode == "turn_error":
            returned["timed_out"] = True
        return returned

    records, result = run_continuations(toolkit, start,
        max_rounds=0 if mode == "disabled" else 1 if mode == "limit" else 4,
        invoke=invoke, compact=runner.delivery_tool_reply)
    assert result["stop_reason"] == expected
    assert len(calls) == count and len(records) == count + 1


def test_decision_mcp_validates_active_turn_and_is_unavailable_to_readonly_worker(tmp_path):
    async def scenario():
        run, _ = setup_run(tmp_path)
        args = dict(candidate="seed", decision="continue", reason="Read original", next_action="Review use")
        async with _server_session(run, readonly=False) as session:
            assert (await session.call_tool("record_work_review", args)).isError
            runner.dump(run / "work_turn.json", {"name": "continuation_01", "active": True})
            assert (await session.call_tool("record_work_review", {**args, "next_action": " "})).isError
            assert (await session.call_tool("record_work_review", {**args, "decision": "passed"})).isError
            result = _json_result(await session.call_tool("record_work_review", args))
            assert result["source_model_sha256"] == read(run / "seed/source_model.json")["source_model_sha256"]
            assert result["task_completion"] == "model_judgment_only"
        async with _server_session(run, readonly=True) as session:
            assert "record_work_review" not in {t.name for t in (await session.list_tools()).tools}
    asyncio.run(scenario())


def test_persisted_state_ignores_unrelated_evaluation_and_decision_files(tmp_path):
    run, toolkit = setup_run(tmp_path)
    delivery = current_delivery(toolkit)
    before = persisted_state(run, delivery)
    (run / "evaluation").mkdir()
    (run / "evaluation/answers.json").write_text("not even valid JSON")
    runner.dump(run / "work_turn.json", {"name": "continuation_01", "active": True})
    record_work_review(toolkit, "seed", "continue", "Pick action", "Read image")
    assert persisted_state(run, delivery) == before


@pytest.mark.parametrize("value", [-1, 5, True])
def test_invalid_bound_cannot_create_run_or_call_model(tmp_path, value):
    with pytest.raises(ValueError, match="continuation_rounds"):
        runner.run_experiment(SimpleNamespace(continuation_rounds=value, out=tmp_path / "no_run"))
    assert not (tmp_path / "no_run").exists()
