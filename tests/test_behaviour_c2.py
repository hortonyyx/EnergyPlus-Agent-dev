"""The same behaviour measures for both transports, including domain failures."""
import asyncio
import copy
import gzip
import json
from pathlib import Path

import pytest

from src.agent.runtime_behaviour import load_behaviour, tool_result_data, write_behaviour_report


def test_metadata_survives_time_tail_and_transport_wrappers():
    data = {"name": "North.png", "display_scale_actual": [2, 2], "original_size": [900, 600]}
    text = json.dumps(data) + '\n已用 40 分钟；剩余 60 分钟。'
    forms = [text, {"content": [{"type": "text", "text": text}]},
             {"structuredContent": data, "content": [{"type": "text", "text": text}]},
             {"tool_message": {"content": json.dumps({"content": [{"type": "text", "text": text}]})}}]
    assert all(tool_result_data(value) == data for value in forms)
    truncated = '{"candidate":"candidate_04","source_geometry_ready":true,"evidence":['
    assert tool_result_data(truncated) == {"candidate": "candidate_04", "source_geometry_ready": True,
                                          "_partial_json": True}


def test_saved_claims_domain_outcomes_and_unanswered_calls_are_not_conflated(tmp_path):
    run = tmp_path / "run"
    (run / "claims").mkdir(parents=True)
    claim = {"candidate": "candidate_01", "objects": [{"kind": "window", "id": "W1"}],
             "values": {"z": [1, 2]}, "reason": "own chain"}
    saved = {"id": "claim_0001", "claim": claim, "sources": [{"image": "West.png"}],
             "resolved_values": {"z": [1, 2]}}
    (run / "claims/claim_0001.json").write_text(json.dumps(saved))
    steps = []
    def add(tool, data, *, error=False, args=None):
        steps.append(dict(index=len(steps)+1, t_call=len(steps), tool=tool, arguments=args or {},
                          result_text=json.dumps(data)+'\n剩余 1 分钟。', is_error=error,
                          model_text_before="", thinking_tokens_before=0))
    add("view_image", {"name": "West.png", "display_scale_actual": [2, 2]}, args={"name": "West.png"})
    add("build_plan_bim", {"status": "error", "source_geometry_ready": False})
    add("revise_plan_bim", {"candidate": "candidate_01", "source_geometry_ready": True})
    add("record_claim", {"id": "claim_0001", "sources": [{"image": "wrong-return.png"}]},
        args={"claim_json": json.dumps(claim)})
    add("revise_bim", {"status": "error"}, error=True)
    add("build_bim", {"candidate": "candidate_02", "source_geometry_ready": False})
    (run / "candidate_02").mkdir()
    (run / "candidate_02/report.json").write_text('{"source_geometry_ready": false}')
    # Reading a failed candidate is a successful inspection, not another failed build.
    add("inspect_candidate", {"candidate": "candidate_02", "report": {"source_geometry_ready": False}})
    record = dict(run="fixture", receipt={}, invocations=[dict(invocation=1, stream="archive", steps=steps)])
    archive = tmp_path / "record.json.gz"
    with gzip.open(archive, "wt") as stream:
        json.dump(record, stream)
    loaded = load_behaviour(archive, source_root=run)
    summary = loaded["summary"]
    assert (summary["call_errors"], summary["domain_failures"], summary["usable_source_drafts"]) == (1, 2, 1)
    assert summary["first_build_attempt_s"] == 1 and summary["first_draft_s"] == 2
    assert summary["full_views_before_first_build_attempt"] == 1
    assert summary["height_provenance_claims"][0]["sources"] == ["West.png"]
    assert summary["height_provenance_claims"][0]["evidence_capture"] == "saved_claim_file"
    assert summary["claims_from_saved_files"] == 1
    assert '剩余 1 分钟' in loaded["invocations"][0]["steps"][0]["result_text"]
    out = tmp_path / "reports"
    write_behaviour_report(archive, out, source_root=run)
    assert "调用报错 | 领域未成功 | 可用源稿" in (out/"timeline.md").read_text()


@pytest.fixture
def responses_run(tmp_path):
    from test_agent_runtime import MESSAGES
    from test_runtime_responses_integration import engine_for, native

    engine = engine_for(tmp_path, [native(("v", "view", {}), ("e", "error", {})), native(text="Done")])
    with engine.store as store:
        assert asyncio.run(engine.run(MESSAGES))["status"] == "completed"
        yield store


def _responses_evidence(store):
    events = [event.model_dump(mode="json") for event in store.events]
    presentation = next(event for event in events if event["payload"]["event_type"] == "tool_presentation")
    by_id = {event["event_id"]: event for event in events}
    request = by_id[presentation["payload"]["request_event_id"]]
    from src.agent.runtime_behaviour import _captured

    visible = _captured(presentation["payload"]["shown_result"], store.directory)
    body = _captured(request["payload"]["final_request_body"], store.directory)
    return events, presentation, request, visible, body


def _write_responses_evidence(store, events, presentation, request, visible, body):
    from src.agent_runtime.store import json_bytes
    import hashlib

    presentation["payload"]["shown_result"] = store.capture(visible, force_blob=True).model_dump(mode="json")
    request["payload"]["final_request_body"] = store.capture(body, force_blob=True).model_dump(mode="json")
    request["payload"]["wire_sha256"] = hashlib.sha256(json_bytes(body)).hexdigest()
    path = store.path
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    return path


def test_responses_report_accepts_native_metadata_and_reopens_exact_images(responses_run, tmp_path):
    store = responses_run
    record = load_behaviour(store.path)
    steps = record["invocations"][0]["steps"]
    assert len(steps) == 2 and all(step["delivered_to_model"] for step in steps)
    assert [step["outcome"] for step in steps] == ["succeeded", "failed"]
    for step in steps:
        visible, prepared = step["model_visible_result"], step["prepared_result"]
        assert visible["tool_message"] == prepared["tool_message"]
        assert visible["image_blocks"] == prepared["image_blocks"]
        assert "wire_tool_result" in visible and visible != prepared
    assert sum(block["type"] == "input_image"
               for block in steps[0]["model_visible_result"]["wire_image_blocks"]) == 1
    out = tmp_path / "report"
    write_behaviour_report(store.path, out)
    assert load_behaviour(out)["invocations"] == record["invocations"]
    assert (out / "timeline.md").is_file()


@pytest.mark.parametrize("damage,match", [
    ("wire_text", "absent from the actual request"),
    ("logical_text", "differs from native content"),
    ("wire_image", "images differ from native content"),
    ("missing_image", "images are absent from the actual request"),
    ("wrong_call", "absent from the actual request"),
    ("wrong_request", "lacks its native request"),
    ("changed_text", "lacks its prior context decision"),
    ("forged_context", "lacks its prior context decision"),
    ("changed_image", "lacks its prior context decision"),
])
def test_responses_report_rejects_content_and_image_tampering(responses_run, damage, match):
    store = responses_run
    events, presentation, request, visible, body = _responses_evidence(store)
    result = visible["wire_tool_result"]
    if damage == "wire_text":
        result["output"][0]["text"] = "forged observation"
    elif damage == "logical_text":
        visible["tool_message"]["content"] = "forged observation"
    elif damage == "wire_image":
        next(block for block in visible["wire_image_blocks"] if block["type"] == "input_image")[
            "image_url"] = "data:image/png;base64,Zm9yZ2Vk"
    elif damage == "missing_image":
        for item in body["input"]:
            if isinstance(item.get("content"), list):
                item["content"] = [block for block in item["content"] if block.get("type") != "input_image"]
    elif damage == "wrong_call":
        visible["tool_message"]["tool_call_id"] = "different-call"
    elif damage == "wrong_request":
        presentation["payload"]["request_event_id"] = "absent-request"
    elif damage in {"changed_text", "forged_context"}:
        visible["tool_message"]["content"] = "forged observation"
        result["output"][0]["text"] = "forged observation"
        for item in body["input"]:
            if item.get("type") == "function_call_output" and item.get("call_id") == "v":
                item["output"] = copy.deepcopy(result["output"])
        if damage == "forged_context":
            presentation["payload"]["context_event_id"] = presentation["payload"]["tool_execution_event_id"]
    else:
        import base64
        import io
        from PIL import Image

        png = io.BytesIO()
        Image.new("RGB", (4, 4), (0, 0, 255)).save(png, format="PNG")
        url = "data:image/png;base64," + base64.b64encode(png.getvalue()).decode("ascii")
        next(block for block in visible["image_blocks"] if block["type"] == "image_url")[
            "image_url"]["url"] = url
        next(block for block in visible["wire_image_blocks"] if block["type"] == "input_image")[
            "image_url"] = url
        for item in body["input"]:
            for block in item.get("content", []):
                if block.get("type") == "input_image":
                    block["image_url"] = url
    path = _write_responses_evidence(store, events, presentation, request, visible, body)
    with pytest.raises(ValueError, match=match):
        load_behaviour(path)


@pytest.mark.parametrize("context_location", ["before", "after", "other_task", "before_execution", "unrelated_image"])
def test_responses_report_accepts_image_removal_only_with_prior_context(responses_run, context_location):
    store = responses_run
    events, presentation, request, visible, body = _responses_evidence(store)
    image = request["payload"]["images"][0]["sent"]
    visible["image_blocks"] = []
    visible["wire_image_blocks"] = []
    for item in body["input"]:
        if isinstance(item.get("content"), list):
            item["content"] = [block for block in item["content"] if block.get("type") != "input_image"]
    context = {**copy.deepcopy(request), "event_id": "context-remove-image", "payload": {
        "event_type": "context", "action": "remove_image", "reason": "fixture image eviction", "image": image}}
    insertion = events.index(request) + (context_location == "after")
    if context_location == "before_execution":
        insertion = next(index for index, event in enumerate(events)
                         if event["event_id"] == presentation["payload"]["tool_execution_event_id"])
    if context_location == "unrelated_image":
        context["payload"]["image"] = store.put_bytes(b"different image", "image/png").model_dump(mode="json")
    events.insert(insertion, context)
    if context_location == "other_task":
        context["task_id"] = "another-reader"
    for index, event in enumerate(events):
        event["sequence"] = index
    presentation["payload"]["context_event_id"] = context["event_id"]
    path = _write_responses_evidence(store, events, presentation, request, visible, body)
    if context_location == "before":
        step = load_behaviour(path)["invocations"][0]["steps"][0]
        assert step["delivered_to_model"] and step["model_visible_result"]["image_blocks"] == []
        assert step["prepared_result"]["image_blocks"]
    else:
        match = ("not explained by their context decisions" if context_location == "unrelated_image"
                 else "lacks its prior context decision")
        with pytest.raises(ValueError, match=match):
            load_behaviour(path)


@pytest.mark.parametrize("context_location", ["before_execution", "after_execution"])
def test_responses_report_rejects_text_rewrite_with_unrelated_valid_context(responses_run, context_location):
    store = responses_run
    events, presentation, request, visible, body = _responses_evidence(store)
    visible["tool_message"]["content"] = "forged observation"
    visible["wire_tool_result"]["output"] = [{"type": "input_text", "text": "forged observation"}]
    for item in body["input"]:
        if item.get("type") == "function_call_output" and item.get("call_id") == "v":
            item["output"] = copy.deepcopy(visible["wire_tool_result"]["output"])
    context = {**copy.deepcopy(request), "event_id": "unrelated-context", "payload": {
        "event_type": "context", "action": "retain_image", "reason": "unrelated retention",
        "image": request["payload"]["images"][0]["sent"]}}
    execution_index = next(index for index, event in enumerate(events)
                           if event["event_id"] == presentation["payload"]["tool_execution_event_id"])
    events.insert(execution_index if context_location == "before_execution" else events.index(request), context)
    for index, event in enumerate(events):
        event["sequence"] = index
    presentation["payload"]["context_event_id"] = context["event_id"]
    path = _write_responses_evidence(store, events, presentation, request, visible, body)
    with pytest.raises(ValueError, match="context decision"):
        load_behaviour(path)


@pytest.mark.parametrize("damage", [None, "wrong_original_hash", "unrelated_execution"])
def test_responses_report_binds_text_reference_to_original_result(responses_run, damage):
    from src.agent.runtime_behaviour import _captured
    from src.agent_runtime.context import _message_content_sha

    store = responses_run
    events, presentation, request, visible, body = _responses_evidence(store)
    execution_id = presentation["payload"]["tool_execution_event_id"]
    execution = next(event for event in events if event["event_id"] == execution_id)
    original = _captured(execution["payload"]["shown_result"], store.directory)["tool_message"]
    content_sha = _message_content_sha(original) if damage != "wrong_original_hash" else "0" * 64
    reference = {"content_sha256": content_sha, "full_result_history_id": "history-full-result",
                 "reason": "exact repeated large tool result"}
    text = json.dumps({"context_reference": reference}, sort_keys=True, separators=(",", ":"))
    visible["tool_message"]["content"] = text
    visible["wire_tool_result"]["output"] = [{"type": "input_text", "text": text}]
    for item in body["input"]:
        if item.get("type") == "function_call_output" and item.get("call_id") == "v":
            item["output"] = copy.deepcopy(visible["wire_tool_result"]["output"])
    source_id = execution_id if damage != "unrelated_execution" else "other-execution"
    summary = store.put_json({"kind": "large_result_references", "replacements": [{
        "event_id": source_id, "content_sha256": content_sha,
        "full_result_history_id": reference["full_result_history_id"]}]})
    context = {**copy.deepcopy(request), "event_id": "reference-context", "payload": {
        "event_type": "context", "action": "compact", "reason": "exact repeated large tool result",
        "summary": summary.model_dump(mode="json"), "replaced_event_ids": [source_id]}}
    events.insert(events.index(request), context)
    for index, event in enumerate(events):
        event["sequence"] = index
    presentation["payload"]["context_event_id"] = context["event_id"]
    path = _write_responses_evidence(store, events, presentation, request, visible, body)
    if damage:
        with pytest.raises(ValueError, match="not explained by its context decisions"):
            load_behaviour(path)
    else:
        assert load_behaviour(path)["invocations"][0]["steps"][0]["delivered_to_model"]
