"""Post-generation exposure and existing sm21 quality audits; never a model input."""
import argparse
import gzip
import hashlib
import importlib
import json
from pathlib import Path
from unittest.mock import patch

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
load = lambda path: json.loads(path.read_text())


def exposure(run, variant):
    calls, parsed, records = {}, set(), []
    stream = run / "agent_stream.jsonl.gz"
    opener = gzip.open if stream.exists() else open
    if not stream.exists():
        stream = run / "agent_stream.jsonl"
    with opener(stream, "rt") as lines:
        for line in lines:
            parts = json.loads(line).get("message", {}).get("content", [])
            for block in parts if isinstance(parts, list) else []:
                if block.get("type") == "tool_use":
                    calls[block["id"]] = {"name": block["name"], "ordinal": len(calls) + 1}
                key = block.get("tool_use_id")
                if block.get("type") != "tool_result" or calls.get(key, {}).get("name") != "mcp__bim__view_pixel_profile":
                    continue
                content = block.get("content", [])
                for part in content if isinstance(content, list) else []:
                    if part.get("type") != "text":
                        continue
                    try:
                        data = json.loads(part["text"])
                    except ValueError:
                        continue
                    if not isinstance(data, dict) or "profile_id" not in data or "candidates" not in data:
                        continue
                    assert ("threshold_excluded_support" in data) == (variant == "current")
                    assert ("threshold_excluded_support" in data["cross_axis_profile"]) == (variant == "current")
                    parsed.add(key)
                    records.append({**calls[key], "profile_id": data["profile_id"],
                        "excluded_coordinates": data.get("threshold_excluded_support", {}).get("coordinate_count"),
                        "cross_axis_excluded_coordinates": data["cross_axis_profile"].get("threshold_excluded_support", {}).get("coordinate_count")})
    return {"parsed_replies": records, "unparsed_or_failed_calls": [
        value for key, value in calls.items() if value["name"] == "mcp__bim__view_pixel_profile" and key not in parsed],
        "limit": "Returned evidence is not verified understanding. Missing parseable replies are not proof of no exposure."}


def audit(run):
    frozen = load(HERE / f"{run.name}_frozen.json")
    summary, receipt = load(run / "summary.json"), load(run / "agent_receipt.json")
    request = load(run / "agent_request.json")
    assert request["effort"] == frozen["effort"] and request["timeout_seconds"] == frozen["timeout_seconds"]
    assert hashlib.sha256(request["system_prompt"].encode()).hexdigest() == frozen["guide_sha256"]
    for name, sha in frozen["implementation_sha256"].items():
        assert digest(run / "runtime_snapshot" / name) == sha
    for name, sha in frozen["experiment_sha256"].items():
        assert digest(run / "experiment_snapshot" / name) == sha
    completed = summary.get("agent_response_completed") and receipt.get("returncode") == 0 and not (receipt.get("result") or {}).get("is_error")
    if not completed:
        dump(run / "threshold_audit.json", {"completed": False, "quality": "unknown_as_completed_run",
            "returncode": receipt.get("returncode"), "saved_delivery": summary.get("delivery"),
            "instruction": "Preserve interruption; do not start another run without inspecting the actual receipt. Saved geometry can be diagnosed separately, not counted as a completed result."})
        return
    active = load(run / "runtime_threshold.json")
    assert active["variant"] == frozen["variant"]
    assert active["method_sha256"] == frozen["method_sha256"][frozen["variant"]]
    assert active["guide_sha256"] == frozen["guide_sha256"]
    assert active["references_sha256"] == frozen["references_sha256"]
    expected = load(HERE.parent / "2026-09-27_sm21_runtime_surface_setup/current_tools.json")
    assert {t["name"]: t for t in active["tools"]} == expected
    base = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run")
    with patch.object(base, "HERE", HERE):
        base.audit(run)
    report = load(run / "postrun_audit.json")
    assert report["invocations"] == 1
    report["limits"][0] = "One arm of a threshold-feedback comparison; not proof of causal recovery or stability."
    report["threshold_feedback"] = {"variant": frozen["variant"], **exposure(run, frozen["variant"])}
    report["limits"].append("Seed-based opening host/connection scores alone can accept merged rooms; inspect independent space identity and partition findings before interpreting those scores.")
    dump(run / "postrun_audit.json", report)
    importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
