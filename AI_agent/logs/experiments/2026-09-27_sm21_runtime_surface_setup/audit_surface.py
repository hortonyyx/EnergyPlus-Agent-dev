"""Offline audit of exposed tools, references and actual historical MCP replies.

No subscription client is imported or run. Historical server registration uses
current imported helpers, so their unchanged source hashes are checked first.
Original runs are read only; only this setup directory receives reports.
"""
import asyncio
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP
from scripts.tool_scripts import run_bim_agent as current

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = "468d83f7"


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def old_text(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def capture_tools(module):
    # Registration only: do not start stdio, invoke a tool, or touch an old run.
    with tempfile.TemporaryDirectory(prefix="bim_surface_") as folder:
        run = Path(folder)
        (run / "inputs.json").write_text('{"images": {}}')
        servers = []
        with patch.object(FastMCP, "run", lambda self, *a, **kw: servers.append(self)):
            module.serve(run)
        assert len(servers) == 1
        return {t.name: t.model_dump(mode="json")
                for t in asyncio.run(servers[0].list_tools())}


def contracts():
    mesh = "scripts/tool_scripts/bim_agent_mesh.py"
    assert old_text(mesh) == (ROOT / mesh).read_text(), "Shared tool registration changed"
    historical = types.ModuleType("surface_historical_runtime")
    historical.__file__ = current.__file__
    sys.modules[historical.__name__] = historical
    exec(compile(old_text("scripts/tool_scripts/run_bim_agent.py"),
                 current.__file__, "exec"), historical.__dict__)
    old, new = capture_tools(historical), capture_tools(current)
    save("historical_tools.json", old)
    save("current_tools.json", new)
    changed = {name: [key for key in sorted(old[name].keys() | new[name].keys())
                      if old[name].get(key) != new[name].get(key)]
               for name in sorted(old.keys() & new.keys()) if old[name] != new[name]}
    namespace = {}
    exec(old_text("scripts/tool_scripts/bim_agent_guidance.py"), namespace)
    before, after = namespace["REFERENCES"], current.REFERENCES
    references = [{"topic": topic, "change": "added" if topic not in before else
                   "removed" if topic not in after else
                   "same" if before[topic] == after[topic] else "changed",
                   "old_chars": len(before.get(topic, "")),
                   "current_chars": len(after.get(topic, "")),
                   "old_sha256": sha(before[topic]) if topic in before else None,
                   "current_sha256": sha(after[topic]) if topic in after else None}
                  for topic in sorted(before.keys() | after.keys())]
    return {"historical_commit": BASE,
            "current_runner_sha256": sha(Path(current.__file__).read_text()),
            "method": "Capture real FastMCP registration without starting a server; shared mesh registration unchanged.",
            "tool_count": {"old": len(old), "current": len(new)},
            "serialized_tool_chars": {label: len(json.dumps(value, ensure_ascii=False))
                                       for label, value in [("old", old), ("current", new)]},
            "added_tools": sorted(new.keys() - old.keys()),
            "removed_tools": sorted(old.keys() - new.keys()),
            "changed_common_tool_fields": changed,
            "common_input_schemas_equal": all(old[n]["inputSchema"] == new[n]["inputSchema"]
                                               for n in old.keys() & new.keys()),
            "references": references}


def audit_stream(run):
    calls, replies, seen = {}, {}, set()
    archive = run / "agent_stream.jsonl.gz"
    for line in gzip.open(archive, "rt"):
        event = json.loads(line)
        content = event.get("message", {}).get("content", [])
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use" and block["id"] not in calls:
                calls[block["id"]] = {"ordinal": len(calls) + 1,
                    "tool": block["name"].removeprefix("mcp__bim__"), "input": block["input"]}
            elif block.get("type") == "tool_result":
                key = block["tool_use_id"]
                assert key in calls and key not in seen, key
                seen.add(key)
                parts = block.get("content", [])
                texts = ([p["text"] for p in parts if p.get("type") == "text"]
                         if isinstance(parts, list) else [str(parts)])
                images = sum(p.get("type") == "image" for p in parts) if isinstance(parts, list) else 0
                values = []
                for text in texts:
                    try:
                        value = json.loads(text)
                    except ValueError:
                        continue
                    if isinstance(value, dict):
                        values.append(value)
                replies[key] = {"values": values, "text_chars": sum(map(len, texts)),
                                "image_count": images,
                                "truncation_marker": any("[OUTPUT TRUNCATED" in text for text in texts),
                                "is_error": bool(block.get("is_error"))}
    first_ready = next((calls[key]["ordinal"] for key in calls
                        if any(v.get("source_geometry_ready") for v in replies.get(key, {}).get("values", []))), None)
    refs, candidates, truncations = [], [], []
    for key, call in calls.items():
        reply = replies.get(key, {})
        if reply.get("truncation_marker"):
            truncations.append({"ordinal": call["ordinal"], "tool": call["tool"],
                                "text_chars": reply["text_chars"], "image_count": reply["image_count"]})
        for value in reply.get("values", []):
            if call["tool"] == "get_bim_reference" and "reference" in value:
                refs.append({"ordinal": call["ordinal"], "topic": call["input"]["topic"],
                             "before_first_ready": first_ready is not None and call["ordinal"] < first_ready,
                             "reference_sha256": sha(value["reference"]), "chars": len(value["reference"])})
            if value.get("source_geometry_ready"):
                expected = len(value.get("source_image_projections", [])) + len(value.get("source_plan_views", []))
                sizes = sorted([(k, len(json.dumps(v, ensure_ascii=False))) for k, v in value.items()],
                               key=lambda row: -row[1])
                candidates.append({"ordinal": call["ordinal"], "tool": call["tool"],
                    "candidate": value.get("candidate"), "text_chars": reply["text_chars"],
                    "truncation_marker": reply["truncation_marker"],
                    "complete_json_parsed": True,
                    "image_count": reply["image_count"], "expected_image_count": expected,
                    "expected_images_present_by_count": reply["image_count"] == expected,
                    "room_use_review_chars": len(json.dumps(value["room_use_review"], ensure_ascii=False))
                                             if "room_use_review" in value else 0,
                    "largest_fields": sizes[:6], "top_level_fields": sorted(value)})
    first_plan_call = next((c for c in calls.values() if c["tool"] == "build_plan_bim"), None)
    first_plan = json.loads(first_plan_call["input"]["plan_json"]) if first_plan_call else {}
    return {"run": run.name, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "scope": "primary invocation stream only; no inference about provider hidden context",
            "tool_calls": len(calls), "tool_replies": len(replies),
            "first_ready_ordinal": first_ready,
            "first_plan_input": ({"ordinal": first_plan_call["ordinal"],
                                  "image": first_plan_call["input"]["image"],
                                  **{k: first_plan[k] for k in
                                     ("floor_id", "x_anchors", "y_anchors", "basis") if k in first_plan}}
                                 if first_plan_call else None),
            "first_assembly_ordinal": next((c["ordinal"] for c in calls.values()
                                              if c["tool"] == "assemble_plan_bim"), None),
            "first_claim_attempt_ordinal": next((c["ordinal"] for c in calls.values()
                                                   if c["tool"] == "record_claim"), None),
            "added_tool_calls": [c for c in calls.values() if c["tool"] in
                                 {"replace_claim_sources", "view_claim_evidence", "record_work_review"}],
            "reference_reads": refs, "candidate_replies": candidates,
            "truncation_markers": truncations,
            "call_counts": dict(Counter(c["tool"] for c in calls.values()))}


def main():
    surface = contracts()
    traces = [audit_stream(next(HERE.parent.glob(f"*run{number}"))) for number in (58, 69, 71, 72)]
    save("surface_comparison.json", surface)
    save("actual_reply_audit.json", traces)
    assert surface["common_input_schemas_equal"]
    assert all(c["expected_images_present_by_count"] for r in traces for c in r["candidate_replies"])
    print(json.dumps({"tool_counts": surface["tool_count"], "changed": surface["changed_common_tool_fields"],
          "references": {r["topic"]: r["change"] for r in surface["references"] if r["change"] != "same"},
          "runs": [{"run": r["run"], "candidates": len(r["candidate_replies"]),
                    "truncation_markers": len(r["truncation_markers"])} for r in traces]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
