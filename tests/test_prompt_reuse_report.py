"""Offline diagnostics distinguish actual caching from merely stable input."""
import pytest

from scripts.dev.prompt_reuse_report import analyze


def request(identity, task, items, tools="same", model="test-model"):
    return {"event_id": identity, "task_id": task, "payload": {
        "event_type": "adapter_request", "adapter": "openai-responses-http-v1",
        "versions": {"remote_model": {"remote_alias": model}},
        "injected_content": [{"request_location": f"/input/{index}",
            "content": {"kind": "inline", "value": value}} for index, value in enumerate(items)] + [
                {"request_location": "/tools", "content": {"kind": "inline", "value": tools}}]}}


def response(identity, task, inputs, cached):
    return {"event_id": identity + "-response", "task_id": task, "payload": {
        "event_type": "model_response", "request_event_id": identity, "usage": {
            "kind": "reported", "raw_usage": {"input_tokens": inputs,
                "input_tokens_details": {"cached_tokens": cached}}}}}


def test_history_change_and_actual_cache_usage_are_separate():
    result = analyze([request("a", "p1", ["rules", "image", "state-1"]), response("a", "p1", 100, 0),
        request("b", "p1", ["rules", "image", "state-2"]), response("b", "p1", 120, 80),
        request("c", "p1", ["rules", "image", "state-2", "new"]), response("c", "p1", 150, 0)])
    assert [row["identical_leading_input_items"] for row in result["requests"]] == [None, 2, 3]
    assert result["tasks"]["p1"]["input_tokens"] == 370
    assert result["tasks"]["p1"]["cached_input_tokens"] == 80
    assert result["tasks"]["p1"]["uncached_input_tokens"] == 290


def test_parallel_roles_do_not_compare_unrelated_histories_or_hide_missing_usage():
    result = analyze([request("a", "p1", ["a"]), request("b", "p2", ["b"]),
        response("a", "p1", 100, 0), request("c", "p1", ["a", "c"], tools="changed")])
    assert result["requests"][1]["previous_request_event"] is None
    assert result["requests"][2]["previous_request_event"] == "a"
    assert result["requests"][2]["same_tool_definitions"] is False
    assert result["tasks"]["p1"]["cache_fraction"] is None
    assert not result["tasks"]["p2"]["usage_complete"]


def test_compaction_is_observed_without_claiming_it_caused_a_cache_miss():
    result = analyze([request("a", "p1", ["rules", "old"]), response("a", "p1", 100, 0),
        {"event_id": "compact", "task_id": "p1", "payload": {"event_type": "context", "action": "compact"}},
        request("b", "p1", ["rules", "checkpoint"]), response("b", "p1", 50, 10)])
    assert result["tasks"]["p1"]["compactions"] == 1
    assert result["requests"][-1]["identical_leading_input_items"] == 1
    assert result["tasks"]["p1"]["cache_fraction"] == 10 / 150


def test_other_provider_usage_is_not_interpreted_as_responses():
    event = request("a", "p1", ["rules"])
    event["payload"]["adapter"] = "anthropic-messages-http-v1"
    with pytest.raises(ValueError, match="only native Responses"):
        analyze([event])
