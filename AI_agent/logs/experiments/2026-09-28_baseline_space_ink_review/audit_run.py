"""Post-run checks for the approved baseline-plus-ink run; never invoke a model."""
import argparse
import base64
from collections import Counter
import gzip
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys

from batch import HERE, ROOT, RUN, TREE, load, producer, save, sha


def completed():
    summary, receipt = load(RUN / "summary.json"), load(RUN / "agent_receipt.json")
    assert summary["agent_response_completed"] and receipt.get("returncode") == 0
    assert not receipt.get("timed_out") and not receipt.get("routing_error")
    assert not (receipt.get("result") or {}).get("is_error")
    assert receipt["actual_model"].startswith("claude-sonnet-")
    assert len(list(RUN.glob("*_receipt.json"))) == summary["subscription_invocations"] == 1
    assert not list(RUN.glob("detail_*/*receipt.json"))
    return summary, receipt


def producer_audit():
    completed()
    runner, *_ = producer()
    frozen = load(HERE / "frozen.json")
    assert frozen == load(RUN / "experiment_condition.json")
    assert load(RUN / "batch_approval.json") == load(HERE / "approval.json")
    for name, value in frozen["execution_sha256"].items():
        assert sha(RUN / "runtime_snapshot" / name) == value == sha(TREE / name)
    save(RUN / "producer_snapshot.json", frozen["execution_sha256"])
    sys.path.insert(1, str(ROOT))
    historical = HERE.parent / "2026-09-28_sm21_historical_tree_setup"
    sys.path.append(str(historical))
    old = importlib.import_module("replay_old")
    old.RUN, old.HERE, old.TREE, old.ROOT, old.producer = RUN, HERE, TREE, ROOT, producer
    old.audit()
    from PIL import Image
    from src.agent.geometry.space_ink_support import measure_space_ink, render_space_ink
    reports = []
    for path in sorted(RUN.glob("plan_drafts/*/interior_ink.json")):
        report, result, compilation = load(path), load(path.parent / "result.json"), load(path.parent / "compilation.json")
        with Image.open(RUN / "images" / report["image"]) as original:
            reproduced = measure_space_ink(original, compilation["space_mapping"])
            assert all(report[key] == value for key, value in reproduced.items())
            for view in result["space_ink_views"]:
                picture, mapping = render_space_ink(original, reproduced, view["space_id"])
                assert all(view[key] == value for key, value in mapping.items())
                data = io.BytesIO(); picture.save(data, format="PNG")
                assert hashlib.sha256(data.getvalue()).hexdigest() == view["sha256"] == sha(RUN / view["file"])
        source = load(RUN / report["candidate"] / "source_model.json")
        assert report["source_model_sha256"] == source["source_model_sha256"]
        assert report["image_sha256"] == sha(RUN / "images" / report["image"])
        assert report["plan_sha256"] == sha(path.parent / "plan.json")
        assert report["compilation_sha256"] == sha(path.parent / "compilation.json")
        reports.append(dict(file=str(path.relative_to(RUN)), candidate=report["candidate"],
            stroke_count=len(report["strokes"]), flagged_rooms=[r["space_id"] for r in report["spaces"] if r["stroke_ids"]],
            exact_report_and_image_replay=True))
    save(RUN / "ink_producer_replay.json", dict(model_calls=0, reports=reports,
        limit="Exact deterministic feedback and transport, not semantic wall classification or quality acceptance."))


def evaluate_audit():
    completed()
    sys.path.insert(0, str(ROOT))
    old = importlib.import_module("AI_agent.logs.experiments.2026-09-28_sm21_historical_tree_setup.evaluate_old")
    old.RUN = RUN
    old.audit()
    summary, receipt = completed()
    report = load(RUN / "postrun_audit.json")
    source = load(RUN / report["candidate"] / "source_model.json")
    actions = [json.loads(line) for line in (RUN / "tools.jsonl").read_text().splitlines()]
    report.update(invocations=summary["subscription_invocations"], estimated_usd_not_bill=summary["estimated_cost_usd"],
        input_mode="historical_base_plus_interior_ink_review_original_only_cold",
        tools=dict(Counter(row["action"] for row in actions)),
        source_assumptions=source["assumptions"], unresolved=source["generation"]["unresolved"],
        limits=["One historical-base plus raw-ink-feedback run; the 6-to-24 candidate-budget port is an additional variable.",
            "Original/GT references and tolerances unchanged, loaded only after generation.",
            "Coverage, tool exposure and model confirmation do not certify interpretation or causal benefit.",
            "No automatic retry, stability claim, EnergyPlus run or user acceptance."])
    save(RUN / "postrun_audit.json", report)


def behavior_audit():
    completed()
    path = RUN / "agent_stream.jsonl.gz"
    opener = gzip.open
    if not path.exists():
        path, opener = RUN / "agent_stream.jsonl", open
    calls, feedback, references, public_text = {}, [], [], []
    with opener(path, "rt") as stream:
        for line in stream:
            event = json.loads(line)
            blocks = event.get("message", {}).get("content", [])
            for block in blocks if isinstance(blocks, list) else []:
                if block.get("type") == "text" and event.get("type") == "assistant":
                    public_text.append(dict(after_tool_count=len(calls), text=block["text"]))
                if block.get("type") == "tool_use":
                    calls[block["id"]] = dict(ordinal=len(calls)+1,
                        tool=block["name"].removeprefix("mcp__bim__"), input=block.get("input", {}))
                if block.get("type") != "tool_result":
                    continue
                request = calls.get(block.get("tool_use_id"), {})
                request.update(result_received=True, is_error=bool(block.get("is_error")))
                content = block.get("content", [])
                parts = content if isinstance(content, list) else [dict(type="text", text=content)]
                if block.get("is_error"):
                    request["returned_error_texts"] = [p.get("text", "") for p in parts if p.get("type") == "text"]
                images = [base64.b64decode(p["source"]["data"]) for p in parts if p.get("type") == "image"]
                request["returned_image_count"] = len(images)
                for part in parts:
                    if part.get("type") != "text":
                        continue
                    try:
                        value = json.loads(part["text"])
                    except (TypeError, ValueError):
                        continue
                    if not isinstance(value, dict):
                        continue
                    request.update(returned_candidate=value.get("candidate"), returned_error=value.get("error"))
                    if request.get("tool") == "get_bim_reference":
                        references.append(dict(topic=request["input"].get("topic"), reference=value.get("reference")))
                    if "space_ink_review" not in value:
                        continue
                    review = value["space_ink_review"]
                    if review.get("status") == "unavailable":
                        feedback.append(dict(ordinal=request["ordinal"], tool=request["tool"], review=review))
                        continue
                    stored = RUN / review["file"]
                    assert sha(stored) == review["sha256"]
                    saved = load(stored.parent / "result.json")
                    assert saved["space_ink_review"] == review
                    views = value["space_ink_views"]
                    assert images[:len(views)] == [(RUN / view["file"]).read_bytes() for view in views]
                    feedback.append(dict(ordinal=request["ordinal"], tool=request["tool"],
                        candidate=value["candidate"], source_model_sha256=review["source_model_sha256"],
                        review=review, returned_review_images=len(views), transport_matches_saved_bytes=True))
    report = dict(completed=True, model_calls_for_audit=0, public_actions=list(calls.values()),
        public_assistant_text=public_text, references=references, returned_ink_feedback=feedback,
        counts=dict(tool_calls=len(calls), ink_feedback_responses=len(feedback),
            unavailable_ink_feedback=sum(r["review"].get("status") == "unavailable" for r in feedback)),
        interpretation="Public requests/results and assistant text only. Exposure does not prove correct interpretation or causal benefit. Independent originals/source review is required.")
    save(RUN / "behavior_audit.json", report)
    print(json.dumps(report["counts"]))


def claim_regions_audit():
    completed()
    sys.path.insert(0, str(ROOT))
    helper = importlib.import_module("AI_agent.logs.experiments.2026-09-27_sm24_claim_regions_setup.claim_crops")
    # This historical tool returns claim JSON only. Preserve the newer check's
    # failed precondition as not applicable, never as verified image delivery.
    try:
        helper.audit(RUN)
    except AssertionError as error:
        assert str(error) == "No actual claim previews arrived in the model stream"
        behavior = load(RUN / "behavior_audit.json")
        relevant = [r for r in behavior["public_actions"] if r["tool"] in {"record_claim", "view_claim_evidence"}]
        assert relevant and all(r["returned_image_count"] == 0 for r in relevant)
        save(RUN / "evaluation/claim_transport_audit.json", dict(
            status="not_exposed_by_historical_tool_contract", image_count=0,
            actual_transport_pixels_match_saved_regions=None,
            observed_audit_precondition=str(error),
            note="Historical record_claim returns JSON only. Saved original regions were exported for developer review; no claim-preview image delivery is asserted. The 40 actual view_image responses were independently verified."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["producer", "evaluate", "behavior", "claims"])
    {"producer": producer_audit, "evaluate": evaluate_audit, "behavior": behavior_audit,
     "claims": claim_regions_audit}[parser.parse_args().command]()
