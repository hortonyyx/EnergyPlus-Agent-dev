"""Offline compaction sweep over frozen histories; no model transport is used.

All model replies and domain state are held fixed. Miss estimates assume perfect
reuse of the immediately preceding request's common logical-message prefix.
They describe prefix invalidation, not actual service-side cache hit rates.
"""

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from src.agent_runtime.anthropic import convert_messages
from src.agent_runtime.context import ContextManager
from src.agent_runtime.estimation import estimate_chat_request
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts import HashedBlobRef

HERE = Path(__file__).resolve().parent
SETTINGS = [(150_000, .6), (150_000, .45), (150_000, .75), (180_000, .6), (200_000, .6)]


class MemoryStore(EventStore):
    """Use production readers and context logic, with writes only in memory."""
    def __init__(self, directory):
        self.directory = directory
        self.cache = {}
        self._root = self
        self.task_id = "offline-sweep"
        self._all_events = []

    def get_bytes(self, ref):
        if ref.uri not in self.cache:
            raw = (self.directory / ref.uri).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == ref.sha256
            self.cache[ref.uri] = raw
        return self.cache[ref.uri]

    def put_bytes(self, data, media_type="application/octet-stream"):
        digest = hashlib.sha256(data).hexdigest()
        uri = "memory/" + digest
        self.cache[uri] = data
        return HashedBlobRef(uri=uri, sha256=digest, media_type=media_type)

    def append(self, payload, *, source_refs=()):
        event = SimpleNamespace(event_id=f"sweep:{len(self._all_events)}", task_id=self.task_id,
            sequence=len(self._all_events), payload=payload, source_refs=source_refs)
        self._all_events.append(event)
        return event


def wire_body(messages, sources, config, tools):
    if config["versions"]["remote_model"]["route_id"] == "glm-subscription-anthropic":
        system, _, native, _ = convert_messages(messages, sources)
        return {"model": config["model"], "system": system, "messages": native,
            "stream": False, **config["parameters"],
            "tools": [{"name": t["function"]["name"], "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"]} for t in tools]}
    return {"model": config["model"], "messages": messages, "stream": False, "n": 1,
        **config["parameters"], "tools": tools, "tool_choice": "auto"}


def history_category(record, events):
    message = record.message
    if record.kind == "tool_result" or message.get("role") == "tool":
        event = events.get(record.source.event_id)
        return "tool_result:" + (event.payload.tool_name if event else "unknown")
    if record.image_keys:
        return "image_message"
    if message.get("role") == "assistant":
        if message.get("reasoning_content") or any(b.get("type") == "thinking" for b in message.get("anthropic_content", [])):
            return "assistant_with_thinking"
        return "assistant_tool_call" if message.get("tool_calls") else "assistant_text"
    return record.kind + ":" + message.get("role", "unknown")


def prefix_length(left, right):
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


def replay(directory, settings=SETTINGS):
    reader = MemoryStore(directory)
    events = EventStore.read_events(directory / "events.jsonl")
    by_id = {e.event_id: e for e in events}
    snapshots, original_bodies, original_responses = [], [], []
    checkpoint = None
    response_map = {e.payload.request_event_id: e.payload for e in events if e.payload.event_type == "model_response"}
    for event in events:
        if event.payload.event_type == "checkpoint":
            checkpoint = event.payload.state
        elif event.payload.event_type == "adapter_request":
            wire = reader.capture_bytes(event.payload.final_request_body)
            assert hashlib.sha256(wire).hexdigest() == event.payload.wire_sha256
            assert json_bytes(json.loads(wire)) == wire  # Comparison below is exact wire bytes.
            assert checkpoint is not None
            snapshots.append(checkpoint)
            original_bodies.append(json.loads(wire))
            original_responses.append(response_map[event.event_id].usage.raw_usage)
    native = "system" in original_bodies[0]
    tools = ([{"type": "function", "function": {"name": t["name"], "description": t["description"],
              "parameters": t["input_schema"]}} for t in original_bodies[0]["tools"]]
             if native else original_bodies[0]["tools"])
    results = []
    for threshold, ratio in settings:
        # A new in-memory context sequence per candidate; original history blobs
        # can be shared because get_bytes verifies them and no write goes to disk.
        store = MemoryStore(directory)
        store.cache = reader.cache
        archived, last, image_states = [], None, {}
        previous_messages, previous_ids = [], set()
        rows, categories = [], Counter()
        for number, (ref, body) in enumerate(zip(snapshots, original_bodies), 1):
            snapshot = reader.get_json_tree(ref)
            config = snapshot["config"]
            payload = copy.deepcopy(snapshot["context"])
            payload["policy"].update(compact_at_tokens=threshold, compact_to_ratio=ratio)
            payload["archived_history_ids"], payload["last_compaction"] = archived, last
            for image in payload["images"]:
                image["active"], image["removal_event_id"] = image_states.get(image["key"], (True, None))
            manager = ContextManager.load(store, payload)
            state_before = json_bytes([entry.model_dump(mode="json") for entry in manager.state])
            projected_state = manager.model_state()
            protected = {r.history_id for r in manager.history[:manager.policy.preserve_initial_messages]}
            required = set(config.get("required_context_tags", [])) | set(manager.policy.pinned_tags)
            views = set(config.get("required_view_ids", []))
            images = {image.key: image for image in manager.images}
            pins = set(payload.get("retrieval_pins", []))
            protected.update(r.history_id for r in manager.history if required & set(r.tags) or any(
                key in pins or images[key].view_id in views or required & set(images[key].tags)
                for key in r.image_keys))
            estimator = lambda messages: estimate_chat_request({"model": config["model"],
                "messages": messages, "tools": tools, **config["parameters"]}).input_tokens_estimate
            before = set(archived)
            projection = manager.project(token_estimator=estimator, consume_retrievals=False,
                required_tags=tuple(config.get("required_context_tags", [])),
                required_view_ids=tuple(config.get("required_view_ids", [])))
            messages = list(projection.messages)
            projected_body = wire_body(messages, list(projection.sources), config, tools)
            if (threshold, ratio) == SETTINGS[0]:
                assert json_bytes(projected_body) == json_bytes(body), (directory.name, number, "baseline request differs")
            state_after = json_bytes([entry.model_dump(mode="json") for entry in manager.state])
            assert state_before == state_after
            assert projection.checklist == manager.checklist()
            assert projected_state == manager.model_state()
            if projected_state:
                prefix = "Current runtime state (machine generated; epistemic status is authoritative): "
                sent_states = [json.loads(m["content"][len(prefix):]) for m in messages
                    if isinstance(m.get("content"), str) and m["content"].startswith(prefix)]
                assert sent_states == [projected_state]
            # Initial instructions/input and any pins remain present, while the
            # complete machine state is unchanged, including all epistemic labels.
            initial = {r.history_id for r in manager.history[:manager.policy.preserve_initial_messages]}
            assert initial <= set(projection.included_history_ids)
            assert protected <= set(projection.included_history_ids)
            new_archived = set(projection.omitted_history_ids) - before
            removed = [r for r in manager.history if r.history_id in new_archived]
            step_categories = Counter(history_category(r, by_id) for r in removed)
            categories.update(step_categories)
            encoded = [json_bytes(m) for m in messages]
            common = prefix_length(previous_messages, encoded)
            total = estimator(messages)
            # Tools remain static across every request. On the first request no
            # prefix is counted as cached; afterwards even an empty common
            # message prefix can reuse the static tools in this idealized model.
            cached = min(total, estimator(messages[:common])) if number > 1 else 0
            missed = total - cached
            retained_old = [r.message for r in manager.history
                            if r.history_id in previous_ids and r.history_id in projection.included_history_ids]
            old_cost = max(0, estimator(retained_old) - estimator([])) if retained_old else 0
            reset_refill = max(0, old_cost - max(0, cached - estimator([]))) if new_archived else 0
            wire_estimate = estimate_chat_request(projected_body)
            limits = [v for v in (wire_estimate.context_window_tokens, config["limits"].get("context_tokens")) if v]
            row = {"step": number, "compacted": bool(new_archived), "input_estimate": total,
                "estimated_uncached_input": missed, "compaction_refill_estimate": reset_refill,
                "removed_messages": len(removed), "removed_images": sum(len(r.image_keys) for r in removed),
                "removed_categories": dict(step_categories), "key_state_preserved": state_before == state_after,
                "protected_messages_preserved": len(protected), "projected_state_preserved": True,
                "state_sha256": hashlib.sha256(state_after).hexdigest(),
                "state_categories": dict(Counter(e.category for e in manager.state if e.active)),
                "context_limit_exceeded": bool(limits and wire_estimate.reservation_tokens > min(limits)),
                "wire_reservation_tokens": wire_estimate.reservation_tokens}
            rows.append(row)
            previous_messages = encoded
            previous_ids = {r.history_id for r in manager.history}
            archived = list(projection.omitted_history_ids)
            last = manager.dump()["last_compaction"]
            image_states = {image.key: (image.active, image.removal_event_id) for image in manager.images}
        record = {"threshold": threshold, "ratio": ratio, "requests": len(rows),
            "compactions": sum(row["compacted"] for row in rows),
            "estimated_uncached_input": sum(row["estimated_uncached_input"] for row in rows),
            "compaction_refill_estimate": sum(row["compaction_refill_estimate"] for row in rows),
            "input_estimate_total": sum(row["input_estimate"] for row in rows),
            "context_limit_exceeded_requests": sum(row["context_limit_exceeded"] for row in rows),
            "max_wire_reservation_tokens": max(row["wire_reservation_tokens"] for row in rows),
            "removed_messages": sum(row["removed_messages"] for row in rows),
            "removed_images": sum(row["removed_images"] for row in rows),
            "removed_categories": dict(categories), "key_state_preserved": all(row["key_state_preserved"] for row in rows),
            "baseline_wire_identical": True if (threshold, ratio) == SETTINGS[0] else None,
            "steps": rows}
        results.append(record)
        print(json.dumps({"run": directory.name, **{k: record[k] for k in (
            "threshold", "ratio", "compactions", "estimated_uncached_input", "context_limit_exceeded_requests")}}), flush=True)
    usage = Counter()
    for raw in original_responses:
        if "prompt_tokens" in raw:
            cached = raw.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            usage["input_tokens"] += raw["prompt_tokens"]
            usage["cache_read_tokens"] += cached
            usage["uncached_input_tokens"] += raw["prompt_tokens"] - cached
        else:
            cached = raw.get("cache_read_input_tokens", 0)
            uncached = raw["input_tokens"] + raw.get("cache_creation_input_tokens", 0)
            usage["input_tokens"] += uncached + cached
            usage["cache_read_tokens"] += cached
            usage["uncached_input_tokens"] += uncached
    return {"run": directory.name, "requests": len(snapshots), "recorded_usage": dict(usage), "variants": results}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append")
    args = parser.parse_args()
    verification = json.loads((HERE / "archive_verification.json").read_bytes())
    names = args.run or [row["run"] for row in verification["runs"]]
    output = HERE / "replay"
    output.mkdir(exist_ok=True)
    for name in names:
        assert name in {row["run"] for row in verification["runs"]}
        result = replay(HERE / ".tmp/history" / name)
        result.update(model_requests=0, defaults_changed=False,
            method="Production ContextManager projects recorded full histories and exact machine state. Perfect immediate logical-message-prefix reuse is an analytical estimate, not a service cache prediction; responses stay fixed.")
        (output / (name + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
