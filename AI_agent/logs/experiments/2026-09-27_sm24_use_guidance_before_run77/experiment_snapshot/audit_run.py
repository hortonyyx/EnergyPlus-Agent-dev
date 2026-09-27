"""Post-generation audit and actual intervention exposure; never input to generation."""
import argparse
import gzip
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import Toolkit, digest, dump
from src.agent.execution.bim_height_coverage import height_coverage
from src.agent.roles import room_use_review
from . import server

HERE = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text())


def exposure(run, variant):
    calls, records, parsed_review_calls = {}, [], set()
    for line in gzip.open(run / "agent_stream.jsonl.gz", "rt"):
        parts = json.loads(line).get("message", {}).get("content", [])
        for block in parts if isinstance(parts, list) else []:
            if block.get("type") == "tool_use":
                calls[block["id"]] = {"name": block["name"].removeprefix("mcp__bim__"), "ordinal": len(calls) + 1}
            if block.get("type") != "tool_result":
                continue
            content = block.get("content", [])
            for part in content if isinstance(content, list) else []:
                if part.get("type") != "text":
                    continue
                try:
                    data = json.loads(part["text"])
                except ValueError:
                    continue
                if not isinstance(data, dict) or not isinstance(data.get("room_use_review"), dict):
                    continue
                call = calls[block["tool_use_id"]]
                parsed_review_calls.add(block["tool_use_id"])
                review = data["room_use_review"]
                has_action = "next_action" in review
                automatic = bool(data.get("source_geometry_ready"))
                if automatic:
                    assert has_action == (variant == "before")
                elif call["name"] in {"inspect_candidate", "finish_bim"}:
                    assert has_action
                records.append({**call, "candidate": data.get("candidate"), "automatic_save": automatic,
                                "has_action": has_action, "summary": review.get("summary")})
    save_tools = {"build_bim", "build_parametric_bim", "build_plan_bim", "revise_plan_bim",
                  "assemble_plan_bim", "revise_bim", "inspect_candidate", "finish_bim"}
    return {"actual_replies": records, "automatic_save_feedback_count": sum(r["automatic_save"] for r in records),
            "calls_without_parseable_use_feedback": [r for key, r in calls.items()
                if r["name"] in save_tools and key not in parsed_review_calls],
            "coverage_count_is_lower_bound": True,
            "limit": "Counts cover parseable returned review JSON only. Missing/failed/truncated replies are not evidence that feedback was withheld. Returned guidance is not proof of correct interpretation or an effect on geometry."}


def audit(run):
    assert (run / "summary.json").is_file(), "Generation must end before evaluation"
    frozen = load(HERE / f"{run.name}_frozen.json")
    manifest, summary = load(run / "inputs.json"), load(run / "summary.json")
    active, request = load(run / "runtime_use_guidance.json"), load(run / "agent_request.json")
    variant = frozen["variant"]
    assert active["variant"] == variant
    assert server.sha(request["system_prompt"]) == active["guide_sha256"] == frozen["guide_sha256"][variant]
    assert active["review_method_sha256"] == frozen["review_method_sha256"][variant]
    assert active["references_sha256"] == frozen["references_sha256"]
    expected = load(HERE.parent / "2026-09-27_sm21_runtime_surface_setup/current_tools.json")
    assert {t["name"]: t for t in active["tools"]} == expected
    assert request["effort"] == frozen["effort"] and request["timeout_seconds"] == frozen["timeout_seconds"]
    assert manifest["scope"] == frozen["scope"] and manifest["provider"] == frozen["provider"]
    assert manifest["max_candidates"] == frozen["max_candidates"] and manifest["continuation_rounds"] == 0
    for key in ("saved_generated_proposal", "building_declaration", "ground_truth_or_evaluation"):
        assert not manifest["input_contents"][key]["included"]
    assert "seed" not in manifest and "plan_recovery" not in manifest
    for name, expected_hash in frozen["implementation_sha256"].items():
        assert digest(run / "runtime_snapshot" / name) == manifest["implementation_sha256"][name] == expected_hash
    for name, expected_hash in frozen["experiment_sha256"].items():
        assert digest(run / "experiment_snapshot" / name) == expected_hash
    for name, expected_hash in frozen["image_sha256"].items():
        assert digest(run / "images" / name) == manifest["images"][name]["sha256"] == expected_hash
    receipts = [load(p) for p in run.glob("*_receipt.json")]
    assert len(receipts) == summary["subscription_invocations"] == 1
    assert all(r["actual_model"].startswith("claude-sonnet-") and r["provider"] == "claude" for r in receipts)
    actions = [json.loads(line) for line in (run / "tools.jsonl").read_text().splitlines()]
    assert not any(r["action"] == "review_detail" for r in actions)
    archive = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_continuation_setup.audit_run")
    archive.archive_streams(run)
    seen = exposure(run, variant)
    dump(run / "guidance_exposure.json", seen)
    if not summary["agent_response_completed"] or not (run / "delivery.json").is_file():
        dump(run / "postrun_audit.json", {"status": "interrupted_or_no_delivery", "guidance_exposure": seen,
             "limits": ["Generation failure retained; no retry or assumed quality scores."]})
        return
    if frozen["case"] == "sm21":
        base = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm21_current_tools_setup.audit_run")
        base.HERE = HERE
        base.audit(run)
    else:
        original = importlib.import_module("AI_agent.logs.experiments.2026-09-23_sm24_cold_plan_setup.audit_run")
        original.audit(run)
        base_report = load(run / "postrun_audit.json")
        candidate = base_report["candidate"]
        source = load(run / candidate / "source_model.json")
        shared = importlib.import_module("AI_agent.logs.experiments.2026-09-26_sm25_multifloor_setup.audit_run")
        from src.agent.judge.gt import load_gt_document
        opening = shared._opening_diagnostic(source, load_gt_document("sm24_anchor"), load(run / "evaluation/partition.json"))
        dump(run / "evaluation/exterior_opening_diagnostic.json", opening)
        toolkit = Toolkit(run)
        delivery = load(run / "delivery.json")
        assert room_use_review(source) == delivery["room_use_review"]
        assert height_coverage(toolkit.claims(), candidate) == delivery["height_coverage"]
        base_report.update(room_use=delivery["room_use_review"], height_coverage=delivery["height_coverage"]["summary"],
            height_mismatches=[r for r in opening["matched"] if r.get("z_within_judge_tolerance") is False],
            source_model_sha256=source["source_model_sha256"])
        dump(run / "postrun_audit.json", base_report)
    report = load(run / "postrun_audit.json")
    report["room_use_guidance_comparison"] = {"variant": variant, **seen,
        "controlled_difference": frozen["controlled_difference"], "limits": frozen["limits"]}
    dump(run / "postrun_audit.json", report)
    importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_view_references_setup.audit_views").audit(run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    audit(parser.parse_args().run.resolve())
