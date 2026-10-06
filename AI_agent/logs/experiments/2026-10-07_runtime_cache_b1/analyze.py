"""Offline, hash-verified request diagnosis and ContextManager policy replay.

No adapters, credentials or external tools are invoked. Original archives are
read-only; projection events/blobs live in memory. JSON output contains metrics
and hashes, never a second copy of the archived requests or images.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from functools import reduce
from pathlib import Path

from src.agent_runtime.anthropic import convert_messages
from src.agent_runtime.context import ContextManager, ContextPolicy, HistoryRecord, ImageRecord, StateEntry
from src.agent_runtime.estimation import approximate_text_tokens, estimate_chat_request, get_model_profile
from src.agent_runtime.store import EventStore, json_bytes
from src.harness_contracts import EventEnvelope, HashedBlobRef


class Archive(EventStore):
    """Use the production lossless readers without opening a writer/lock."""

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.rows = [EventEnvelope.model_validate_json(line)
                     for line in (self.directory / "events.jsonl").read_bytes().splitlines()]
        self.cache = {}

    def get_bytes(self, ref):
        if ref.sha256 not in self.cache:
            self.cache[ref.sha256] = super().get_bytes(ref)
        return self.cache[ref.sha256]


class ReplayStore(Archive):
    """An in-memory overlay; replay cannot modify the supplied archive."""

    def __init__(self, archive, task_id):
        self.directory, self.cache = archive.directory, archive.cache
        self.rows = [e for e in archive.rows if e.task_id == task_id]
        self.task_id = task_id
        self.added = []

    @property
    def events(self):
        return self.rows + self.added

    def put_bytes(self, data, media_type="application/octet-stream"):
        digest = hashlib.sha256(data).hexdigest()
        self.cache[digest] = data
        return HashedBlobRef(uri=f"blobs/{digest}", sha256=digest, media_type=media_type)

    def append(self, payload, *, source_refs=()):
        template = self.rows[-1]
        seq = template.sequence + 1 + len(self.added)
        event = template.model_copy(update={"event_id": f"replay-{self.task_id}-{seq}",
            "sequence": seq, "payload": payload, "source_refs": tuple(source_refs)})
        self.added.append(event)
        return event


def without_markers(value):
    if isinstance(value, dict):
        return {k: without_markers(v) for k, v in value.items() if k != "cache_control"}
    if isinstance(value, list):
        return [without_markers(v) for v in value]
    return value


def first_difference(before, after, pointer=""):
    if type(before) is not type(after):
        return pointer + ":type"
    if isinstance(before, dict):
        for key in sorted(before.keys() | after.keys()):
            if key not in before or key not in after:
                return pointer + "/" + key
            found = first_difference(before[key], after[key], pointer + "/" + key)
            if found:
                return found
    elif isinstance(before, list):
        for i, (left, right) in enumerate(zip(before, after)):
            found = first_difference(left, right, pointer + f"/{i}")
            if found:
                return found
        if len(before) != len(after):
            return pointer + f"/{min(len(before), len(after))}:length"
    elif before != after:
        if isinstance(before, str):
            i = next((i for i, (a, b) in enumerate(zip(before, after)) if a != b), min(len(before), len(after)))
            return pointer + f":char-{i}"
        return pointer
    return None


def input_tokens(body):
    return estimate_chat_request(body, strict=True).input_tokens_estimate


def shared_prefix(before, after):
    """Conservative complete-block prefix: tools, system, conversation.

    The vendor tokenizer/serialization is not observable. Use the existing
    native request estimator (including its image profile) on exact matching
    blocks; do not credit any part of the first changed block. Moving ephemeral
    markers are reported separately and excluded from semantic equality.
    """
    if before is None:
        return 0, "first_request"
    before, after = without_markers(before), without_markers(after)
    prefix = {"model": after["model"], "max_tokens": after["max_tokens"], "system": [], "messages": []}
    if before.get("tools") != after.get("tools"):
        return 0, first_difference(before.get("tools"), after.get("tools"), "/tools")
    if "tools" in after:
        prefix["tools"] = after["tools"]
    for i, block in enumerate(after["system"]):
        if i >= len(before["system"]) or block != before["system"][i]:
            return input_tokens(prefix), f"/system/{i}"
        prefix["system"].append(block)
    if len(before["system"]) != len(after["system"]):
        return input_tokens(prefix), "/system:length"
    for i, message in enumerate(after["messages"]):
        if i >= len(before["messages"]) or message["role"] != before["messages"][i]["role"]:
            return input_tokens(prefix), f"/messages/{i}/role_or_append"
        matched = {"role": message["role"], "content": []}
        prefix["messages"].append(matched)
        previous = before["messages"][i]["content"]
        for j, block in enumerate(message["content"]):
            if j >= len(previous) or block != previous[j]:
                if not matched["content"]:
                    prefix["messages"].pop()
                return input_tokens(prefix), (f"/messages/{i}/content/{j}:append" if j >= len(previous)
                    else first_difference(previous[j], block, f"/messages/{i}/content/{j}"))
            matched["content"].append(block)
        if len(previous) != len(message["content"]):
            return input_tokens(prefix), f"/messages/{i}/content:length"
    return input_tokens(prefix), "equal_or_shorter"


def native_body(actual, projection):
    system, _, messages, _ = convert_messages(projection.messages, projection.sources)
    return {**actual, "system": system, "messages": messages}


def logical_tools(actual):
    return [{"type": "function", "function": {"name": t["name"],
        "description": t.get("description", ""), "parameters": t["input_schema"]}}
        for t in actual.get("tools", [])]


def load_increment(manager, archive, snapshot):
    """Replay original history/state, preserving this policy's prior decisions."""
    for item in snapshot["images"]:
        if item["key"] not in manager._images:
            manager._images[item["key"]] = ImageRecord.model_validate_json(json.dumps(
                {**item, "active": True, "removal_event_id": None}))
    old = len(manager._history)
    assert old <= len(snapshot["history"])
    for item in snapshot["history"][old:]:
        message = json.loads(archive.get_bytes(HashedBlobRef.model_validate(item["message_blob"])))
        manager._history.append(HistoryRecord.model_validate_json(json.dumps({**item, "message": message})))
    manager._next_history = snapshot["next_history"]
    manager._state = {item["key"]: StateEntry.model_validate_json(json.dumps(item)) for item in snapshot["state"]}
    manager._retrieval_pins = set(snapshot["retrieval_pins"])


def state_metrics(body):
    for message in reversed(body["messages"]):
        for block in reversed(message["content"]):
            text = block.get("text", "")
            if text.startswith("Current runtime state"):
                values = json.loads(text.split(": ", 1)[1])
                return {"characters": len(text), "text_tokens_estimate": approximate_text_tokens(text),
                    "items": {item["key"]: {"characters": len(json_bytes(item["value"]).decode()),
                        "text_tokens_estimate": approximate_text_tokens(json_bytes(item["value"]).decode())}
                        for item in values}}
    return {"characters": 0, "text_tokens_estimate": 0, "items": {}}


def cache_markers(body):
    found = []
    def walk(value, pointer=""):
        if isinstance(value, dict):
            if "cache_control" in value:
                found.append({"location": pointer, "value": value["cache_control"]})
            for key, child in value.items():
                walk(child, pointer + "/" + key)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                walk(child, pointer + f"/{i}")
    walk(body)
    return found


def summarize(rows):
    usable = [r for r in rows if not r["first_request"] and not r["long_wait"]]
    without_wait = [r for r in rows if not r["long_wait"]]
    return {
        "requests": len(rows),
        "mean_input_tokens_estimate": round(statistics.mean(r["input_tokens_estimate"] for r in rows), 2),
        "max_input_tokens_estimate": max(r["input_tokens_estimate"] for r in rows),
        "sum_input_tokens_estimate": sum(r["input_tokens_estimate"] for r in rows),
        "compactions": sum(r["compactions"] for r in rows),
        "shared_prefix_ratio_excluding_long_wait": round(
            sum(r["shared_prefix_tokens_estimate"] for r in without_wait)
            / max(1, sum(r["input_tokens_estimate"] for r in without_wait)), 6),
        "shared_prefix_ratio_excluding_first_and_long_wait": round(
            sum(r["shared_prefix_tokens_estimate"] for r in usable) / max(1, sum(r["input_tokens_estimate"] for r in usable)), 6),
        "shared_prefix_ratio_all_requests": round(sum(r["shared_prefix_tokens_estimate"] for r in rows)
            / sum(r["input_tokens_estimate"] for r in rows), 6),
        "long_wait_request_numbers": [r["request_number"] for r in rows if r["long_wait"]],
    }


def analyze_run(directory, *, ratio=None, threshold=None, policy_factory=None):
    started = time.monotonic()
    archive = Archive(directory)
    checkpoints, responses, pending_context = {}, {}, defaultdict(list)
    for e in archive.rows:
        p = e.payload
        if p.event_type == "model_response":
            responses[p.request_event_id] = e
    managers, prior = {}, {}
    raw_rows, projected_rows = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for e in archive.rows:
        p, task = e.payload, e.task_id
        if p.event_type == "checkpoint":
            checkpoints[task] = p.state
        elif p.event_type == "context":
            pending_context[task].append(e)
        elif p.event_type == "adapter_request":
            actual = archive.resolve(p.final_request_body)
            assert hashlib.sha256(json_bytes(actual)).hexdigest() == p.wire_sha256
            snapshot = archive.get_json_tree(checkpoints[task])
            context = snapshot["context"]
            current_profile = json.loads(json.dumps(asdict(get_model_profile(actual["model"], strict=True))))
            if snapshot["config"]["model_profile"] != current_profile:
                raise ValueError("model estimation profile changed; replay with the archived profile/code")
            role = snapshot["config"]["role"]["role_id"]
            previous = prior.get(task)
            delta = ((e.occurred_at.value - previous["response_time"]).total_seconds()
                     if previous and previous["response_time"] is not None else None)
            request_delta = (e.occurred_at.value - previous["request_time"]).total_seconds() if previous else None
            response = responses.get(e.event_id)
            usage = (response.payload.usage.raw_usage
                     if response is not None and response.payload.usage.kind == "reported" else {})
            common, difference = shared_prefix(previous["body"] if previous else None, actual)
            events = pending_context.pop(task, [])
            counts = Counter(c.payload.action for c in events)
            # A compaction may remove images too: report the joint causal event,
            # not a separate competing explanation for each removed picture.
            cause = ("first_request" if previous is None else "compression" if counts["compact"]
                     else "append_or_mutable_state_tail")
            reported_input = (sum(usage.get(k, 0) for k in (
                "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) if usage else None)
            row = {"request_number": len(raw_rows[task]) + 1, "event_id": e.event_id,
                "at": e.occurred_at.value.isoformat(), "role": role, "first_request": previous is None,
                "gap_after_previous_response_seconds": delta, "long_wait": delta is not None and delta > 300,
                "gap_after_previous_request_seconds": request_delta,
                "wire_sha256": p.wire_sha256, "input_tokens_estimate": input_tokens(actual),
                "response_event_id": response.event_id if response else None,
                "usage_status": response.payload.usage.kind if response else "missing_response",
                "model_profile_sha256": hashlib.sha256(json_bytes(current_profile)).hexdigest(),
                "provider_usage": usage, "reported_total_input_tokens": reported_input,
                "reported_total_tokens": reported_input + usage.get("output_tokens", 0) if usage else None,
                "shared_prefix_tokens_estimate": common,
                "semantic_first_difference": difference,
                "wire_first_difference": first_difference(previous["body"], actual) if previous else "first_request",
                "cause": cause, "context_actions": dict(counts), "compactions": counts["compact"],
                "image_decisions": [{"event_id": c.event_id, "action": c.payload.action,
                    "reason": c.payload.reason, "view_id": c.payload.view_id} for c in events
                    if c.payload.action != "compact"],
                "state_tail": state_metrics(actual), "cache_markers": cache_markers(actual)}
            raw_rows[task].append(row)
            old_policy = ContextPolicy.model_validate_json(json.dumps(context["policy"]))
            for name in ("before", "after"):
                key = (task, name)
                if key not in managers:
                    chosen = old_policy
                    if name == "after":
                        if policy_factory:
                            chosen = policy_factory(role, old_policy)
                        else:
                            chosen = old_policy.model_copy(update={
                                **({"compact_to_ratio": ratio} if ratio is not None else {}),
                                **({"compact_at_tokens": threshold} if threshold is not None else {})})
                    managers[key] = ContextManager(ReplayStore(archive, task), policy=chosen)
                manager = managers[key]
                load_increment(manager, archive, context)
                start = len(manager.store.added)
                projection = manager.project(token_estimator=lambda messages: input_tokens({
                    "model": actual["model"], "max_tokens": actual["max_tokens"],
                    "messages": messages, "tools": logical_tools(actual)}))
                body = native_body(actual, projection)
                full_state = [item.model_dump(mode="json") for item in manager.state]
                assert full_state == context["state"], "projection changed lossless state"
                replay_hash = hashlib.sha256(json_bytes(body)).hexdigest()
                if name == "before" and replay_hash != p.wire_sha256:
                    raise AssertionError(f"baseline replay drift at {task}/{e.event_id}: "
                        + str(first_difference(body, actual)))
                rows = projected_rows[task][name]
                prefix, diff = shared_prefix(prior.get(key), body)
                compact = sum(v.payload.action == "compact" for v in manager.store.added[start:])
                rows.append({k: row[k] for k in ("request_number", "event_id", "first_request", "long_wait")} | {
                    "input_tokens_estimate": input_tokens(body), "shared_prefix_tokens_estimate": prefix,
                    "semantic_first_difference": diff, "compactions": compact, "wire_sha256": replay_hash,
                    "included_history_messages": len(projection.included_history_ids),
                    "archived_history_messages": len(projection.omitted_history_ids),
                    "state_tail": state_metrics(body),
                    "state_sha256": hashlib.sha256(json_bytes(full_state)).hexdigest()})
                prior[key] = body
            prior[task] = {"body": actual, "response_time": response.occurred_at.value if response else None,
                           "request_time": e.occurred_at.value}
            if row["request_number"] == 1 or row["request_number"] % 10 == 0:
                print(f"{Path(directory).name} {task} #{row['request_number']} replayed", flush=True)
    result = {"run": Path(directory).name, "events_sha256": hashlib.sha256((Path(directory)/"events.jsonl").read_bytes()).hexdigest(),
              "offline_seconds": round(time.monotonic() - started, 3), "baseline_wire_matches": sum(map(len, raw_rows.values())), "tasks": {}}
    for task, rows in raw_rows.items():
        cache = [r["provider_usage"].get("cache_read_input_tokens", 0) for r in rows]
        # Anthropic usage keeps uncached input, cache reads and cache writes separate.
        reported_input = sum(r["provider_usage"].get("input_tokens", 0) + r["provider_usage"].get("cache_read_input_tokens", 0)
            + r["provider_usage"].get("cache_creation_input_tokens", 0) for r in rows)
        reported_output = sum(r["provider_usage"].get("output_tokens", 0) for r in rows)
        result["tasks"][task] = {"role": rows[0]["role"], "actual": {**summarize(rows),
            "cache_read_tokens": sum(cache), "reported_total_input_tokens": reported_input,
            "reported_output_tokens": reported_output, "reported_total_tokens": reported_input + reported_output,
            "cache_read_ratio": sum(cache) / reported_input if reported_input else None,
            "requests_missing_usage": sum(r["usage_status"] != "reported" for r in rows),
            "nonzero_cache_values": sorted(set(cache) - {0}),
            "nonzero_cache_gcd": reduce(math.gcd, cache)},
            "policies": {name: managers[(task, name)].policy.model_dump(mode="json") for name in ("before", "after")},
            "replay": {name: summarize(values) for name, values in projected_rows[task].items()},
            "actual_requests": rows, "replayed_requests": dict(projected_rows[task])}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ratio", type=float)
    parser.add_argument("--threshold", type=int)
    parser.add_argument("--role-policy", action="store_true")
    args = parser.parse_args()
    factory = None
    if args.role_policy:
        from src.agent.runtime_roles.context_policy import role_context_policy
        factory = lambda role, old: role_context_policy(role, base=old)
    result = {"schema_version": 1, "method": "hash-verified native requests; conservative complete-block prefix, cache_control ignored only for semantic comparison; original per-request checkpoint histories/state replayed sequentially; >300s response-to-next-request gap excluded separately; no service calls",
        "runs": [analyze_run(path, ratio=args.ratio, threshold=args.threshold, policy_factory=factory) for path in args.runs]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for run in result["runs"]:
        print(run["run"], json.dumps({t: d["replay"] for t, d in run["tasks"].items()}))


if __name__ == "__main__":
    main()
