"""Post-generation checks only; no GT or reference answers enter the MCP server."""
import argparse
import gzip
import hashlib
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent


def audit(run):
    load = lambda p: json.loads(p.read_text())
    frozen = load(HERE / f"{run.name}_frozen.json")
    request = load(run / "agent_request.json")
    active = load(run / "runtime_profile.json")
    assert active["variant"] == frozen["variant"]
    assert active["method_sha256"] == frozen["method_sha256"][frozen["variant"]]
    assert active["references_sha256"] == frozen["references_sha256"]
    assert hashlib.sha256(request["system_prompt"].encode()).hexdigest() == active["guide_sha256"] == frozen["guide_sha256"]
    assert request["timeout_seconds"] == frozen["timeout_seconds"] and request["effort"] == frozen["effort"]
    expected_tools = load(HERE.parent / "2026-09-27_sm21_runtime_surface_setup/current_tools.json")
    assert {t["name"]: t for t in active["tools"]} == expected_tools
    for name, sha in frozen["experiment_sha256"].items():
        assert digest(run / "experiment_snapshot" / name) == sha
    base = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run")
    base.HERE = HERE
    base.audit(run)
    report = load(run / "postrun_audit.json")
    assert report["invocations"] == 1
    calls, successful_feedback = {}, 0
    for line in gzip.open(run / "agent_stream.jsonl.gz", "rt"):
        parts = json.loads(line).get("message", {}).get("content", [])
        for block in parts if isinstance(parts, list) else []:
            if block.get("type") == "tool_use":
                calls[block["id"]] = block["name"]
            if block.get("type") == "tool_result" and calls[block["tool_use_id"]] == "mcp__bim__pixel_profile":
                for part in block.get("content", []) if isinstance(block.get("content"), list) else []:
                    if part.get("type") != "text":
                        continue
                    try:
                        value = json.loads(part["text"])
                    except ValueError:
                        continue
                    if isinstance(value, dict) and "runs" in value:
                        assert ("evidence_note" in value) == (frozen["variant"] == "current")
                        assert all(("support_peaks" in r) == (frozen["variant"] == "current") for r in value["runs"])
                        successful_feedback += 1
    report["profile_feedback_comparison"] = {
        "variant": frozen["variant"], "successful_feedback_replies": successful_feedback,
        "active_method_and_tool_catalog_verified": True,
        "controlled_difference": frozen["controlled_difference"], "limits": frozen["limits"]}
    report["limits"][0] = "One arm of a two-run feedback comparison; not proof of causal recovery or stability."
    dump(run / "postrun_audit.json", report)
    importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
