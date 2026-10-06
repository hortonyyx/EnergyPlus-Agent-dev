"""Measure real saved role feedback and catalogs; no models and no source-run writes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from trial_replay import DEFAULT_SOURCE, REPO, _resolve_capture

sys.path.insert(0, str(REPO))
from src.agent.runtime_roles.feedback import assembly_reply, reader_batch_reply
from src.agent.runtime_roles.guidance import get_role_guide
from src.agent.runtime_roles.session import COORDINATOR_ORDINARY_TOOLS, EXTRA_TOOLS, envelope
from src.agent.runtime_roles.submission import SUBMISSION_TOOLS
from src.agent_runtime.adapter import convert_tool_result
from src.agent_runtime.loop import RunLimits
from src.agent_runtime.store import EventStore


def events(run):
    return [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]


def text_chars(raw):
    return sum(len(row["text"]) for row in raw.get("content", []) if row.get("type") == "text")


def visible(store, raw, call_id):
    message, _, _, _ = convert_tool_result(call_id, raw, store)
    return len(message["content"])


def guide_counts(guide, tools):
    return {"guide_chars": len(guide), "tools": len(tools),
        "description_chars": sum(len(tool.get("description", "")) for tool in tools),
        "schema_chars": sum(len(json.dumps(tool["input_schema"], ensure_ascii=False)) for tool in tools)}


def main():
    output = {"scope": "offline projections of hash-verified saved run3/run6 envelopes",
              "model_service_requests": 0, "feedback": [], "roles": {}}
    scratch = REPO / "AI_agent/archive/local_backup/c4/feedback_replay"
    limits = RunLimits(model_calls=1, tool_calls=1, tokens=1000, seconds=60)
    with EventStore(scratch, run_id="c4-feedback", task_id="coordinator",
                    budget_limit=limits.ledger_limit()) as store:
        for name in ("sm24_run3", "sm24_run6"):
            run = DEFAULT_SOURCE / name
            rows = events(run)
            first = {}
            for row in rows:
                payload = row["payload"]
                if payload["event_type"] == "tool_execution" and payload["tool_name"] in {
                        "submit_plan_reading", "submit_elevation_reading"}:
                    first.setdefault(row["task_id"], payload["outcome"] == "succeeded")
            measured = set()
            for row in rows:
                payload = row["payload"]
                tool = payload.get("tool_name")
                if payload["event_type"] != "tool_execution" or tool not in {
                        "delegate_readers", "assemble_from_readers"} or tool in measured:
                    continue
                raw = _resolve_capture(run, payload["raw_result"])
                value = raw.get("structuredContent")
                if not value or value.get("status") == "rejected":
                    continue
                measured.add(tool)
                if tool == "delegate_readers":
                    after = reader_batch_reply(value, first)
                    preserved = all(a["artifact"] is None or a["artifact"]["sha256"] == b["artifact"]["sha256"]
                        for a, b in zip(after["results"], value["results"]))
                    for result in value["results"]:
                        if result.get("artifact"):
                            artifact = run / result["artifact"]["path"]
                            assert hashlib.sha256(artifact.read_bytes()).hexdigest() == result["artifact"]["sha256"]
                else:
                    receipt_file = "role_assemblies/" + value["assembly_id"] + ".json"
                    path = run / receipt_file
                    saved = json.loads(path.read_bytes())["response"]
                    assert saved == value
                    after = assembly_reply(value, path, receipt_file=receipt_file)
                    restored = []
                    for decision in after["decisions"]:
                        item = {k: v for k, v in decision.items() if k != "guidance"}
                        item.update(after.get("decision_guidance", {}).get(decision.get("guidance"), {}))
                        restored.append(item)
                    preserved = restored == value["decisions"]
                    assert after["reader_notes"]["count"] == len(value["reader_notes"])
                assert preserved
                new_raw = envelope(after)
                output["feedback"].append({"run": name, "event_id": row["event_id"], "tool": tool,
                    "before_tool_text_chars": text_chars(raw), "after_tool_text_chars": text_chars(new_raw),
                    "before_adapter_visible_chars": visible(store, raw, f"old-{name}-{tool}"),
                    "after_adapter_visible_chars": visible(store, new_raw, f"new-{name}-{tool}"),
                    "artifact_hashes_or_located_decisions_preserved": preserved})

            if name != "sm24_run6":
                continue
            for row in rows:
                payload = row["payload"]
                if payload["event_type"] != "adapter_request":
                    continue
                if row["task_id"] == "coordinator":
                    role = "coordinator"
                else:
                    task_paths = list((run / "tasks").glob("*/reader_task.json"))
                    task = next(json.loads(p.read_bytes()) for p in task_paths
                                if json.loads(p.read_bytes())["task_id"] == row["task_id"])
                    role = task["role_id"]
                if role in output["roles"]:
                    continue
                wire = _resolve_capture(run, payload["final_request_body"])
                guide = "\n".join(block["text"] for block in wire["system"] if block.get("type") == "text")
                tools = wire["tools"]
                if role == "coordinator":
                    current = [t for t in tools if t["name"] in COORDINATOR_ORDINARY_TOOLS]
                    current += [{"name": t["name"], "description": t["description"],
                        "input_schema": t["inputSchema"]} for t in EXTRA_TOOLS]
                else:
                    current = [dict(t) for t in tools]
                    submission = SUBMISSION_TOOLS[role]
                    for t in current:
                        if t["name"] == submission["name"]:
                            t["description"], t["input_schema"] = submission["description"], submission["inputSchema"]
                output["roles"][role] = {"before": guide_counts(guide, tools),
                    "after": guide_counts(get_role_guide(role), current),
                    "after_tool_names": [t["name"] for t in current],
                    "before_wire_sha256": payload["wire_sha256"],
                    "after_catalog_source": "unchanged frozen tools from verified wire + current role descriptions/schemas"}
                if len(output["roles"]) == 3:
                    break
    destination = Path(__file__).with_suffix(".json")
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
