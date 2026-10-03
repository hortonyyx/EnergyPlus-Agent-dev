"""Score the new-runtime migration run with the 10-02 GLM baseline criteria (no model calls).

The runtime keeps the frozen tool server's run directory under ``bim/``; the 10-02 audits read the
Claude Code runner's files (summary, receipt, stream). This adapter copies ``bim/`` into a temporary
view, adds only the fields those audits read (marked as written by the adapter), and runs the
unchanged 09-23 original-image plan audit, the typed-GT exterior opening diagnostic and the 09-30
cross-case scorer. Runtime facts come from the runtime's own receipt and events. The run directory
is never modified; results are written next to this script.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
PREFIX = "AI_agent.logs.experiments."
RUNS = {"attempt_01": HERE.parent / "2026-10-03_runtime_r1/runs/migration_sm24_glm_paratera",
        "attempt_02": HERE / "runs/attempt_02_output_32000",
        "attempt_03": HERE / "runs/attempt_03_6000s",
        # Same subscription as the 10-02 baseline, only the runtime changes.
        **{f"subscription_{i:02d}": HERE / f"runs/subscription_{i:02d}" for i in (1, 2, 3)}}
SUBSCRIPTION = {name for name in RUNS if name.startswith("subscription_")}
BASELINE = HERE.parent / "2026-10-02_sm24_glm_baseline"
TASK_SHA256 = "a05ae6d543fdd14076a46859c8b4e2fa781f560a0ddfcce6d1948597632fa795"
GUIDE_SHA256 = "9ca4fdcda8b446a58fd97466f4849628a54e6a2966b4db480407bb7131516b34"
BUDGET_SECONDS = {"attempt_01": 3000, "attempt_02": 3000, "attempt_03": 6000,
                  **{name: 3000 for name in SUBSCRIPTION}}
# Yuan per million tokens, derived from the 10-03 Paratera bill (AI_agent/workflow/models.md).
PRICE = {"GLM-5.3-Flash": {"input": 0.8, "output": 2.8}}


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def when(event):
    stamp = event["occurred_at"]
    return datetime.fromisoformat(stamp["value"].replace("Z", "+00:00")) if stamp.get("kind") == "known" else None


def runtime_facts(run, subscription=False):
    receipt = load(run / "receipt.json")
    events = [json.loads(line) for line in (run / "events.jsonl").read_text().splitlines()]
    payloads = [e["payload"] for e in events]
    usage, models, tools, outcomes, failures = Counter(), Counter(), Counter(), Counter(), []
    for item in payloads:
        kind = item.get("event_type")
        if kind == "model_response":
            raw = (item.get("usage") or {}).get("raw_usage") or {}
            usage["prompt"] += raw.get("prompt_tokens", 0)
            usage["completion"] += raw.get("completion_tokens", 0)
            usage["total"] += raw.get("total_tokens", 0)
            usage["cached"] += (raw.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
            usage["reasoning"] += (raw.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            usage["responses_without_usage"] += not raw
            blob = (item.get("raw_response") or {}).get("blob") or {}
            path = run / blob["uri"] if blob.get("uri") else None
            models[load(path).get("model") if path and path.is_file() else "not_captured"] += 1
        elif kind == "tool_execution":
            tools[item["tool_name"]] += 1
            outcomes[item.get("outcome")] += 1
            if item.get("outcome") != "succeeded":
                failures.append(dict(tool=item["tool_name"], outcome=item.get("outcome")))
    times = [t for t in map(when, events) if t]
    price = PRICE["GLM-5.3-Flash"]
    return dict(
        status=receipt.get("status"), answer_present=bool(receipt.get("answer")),
        receipt_elapsed_seconds=receipt.get("elapsed_seconds"),
        event_span_seconds=round((times[-1] - times[0]).total_seconds(), 1) if times else None,
        model_calls=receipt.get("model_calls"), retries=receipt.get("retries"), fallback=receipt.get("fallback"),
        reported_models=dict(models), usage=dict(usage),
        request_image_attachments=sum(len(p.get("images") or []) for p in payloads
                                      if p.get("event_type") == "adapter_request"),
        estimated_yuan_text_only=None if subscription else
            round((usage["prompt"] * price["input"] + usage["completion"] * price["output"]) / 1e6, 3),
        yuan_note="Subscription: no usage-based price." if subscription else
            "Reported tokens only; the Paratera bill also charges image tokens the usage omits.",
        per_round=dict(
            output_tokens=round(usage["completion"] / receipt["model_calls"]) if receipt.get("model_calls") else None,
            seconds=round(receipt["elapsed_seconds"] / receipt["model_calls"], 1)
            if receipt.get("model_calls") and receipt.get("elapsed_seconds") else None),
        tool_calls=dict(tools), tool_outcomes=dict(outcomes), tool_failures=failures,
        lifecycle=[{k: p.get(k) for k in ("action", "reason", "failure_stage")}
                   for p in payloads if p.get("event_type") == "run_lifecycle"],
        budget_actions=dict(Counter(p.get("action") for p in payloads if p.get("event_type") == "budget")),
        event_types=dict(Counter(p.get("event_type") for p in payloads)))


def expected_task(seconds):
    """The 10-02 baseline task text; attempt 03 changes only its budget sentence."""
    prompt = load(HERE.parent / "2026-10-02_glm_baseline/preflight_glm_sm24.json")["prompt"]
    assert hashlib.sha256(prompt.encode()).hexdigest() == TASK_SHA256
    return prompt.replace("Budget: 3000 seconds.", f"Budget: {seconds} seconds.")


def compat_view(run, target, facts, seconds):
    """Copy bim/ and add only the runner fields the unchanged audits read, marked as adapter-written."""
    from scripts.tool_scripts.run_bim_agent import Toolkit
    assert (run / "task.txt").read_text() == expected_task(seconds)
    assert digest(run / "guide.txt") == GUIDE_SHA256
    baseline = load(BASELINE / "inputs.json")
    implementation = baseline["implementation_sha256"]
    changed = [name for name, sha in implementation.items() if digest(ROOT / name) != sha]
    assert not changed, f"frozen tool files differ from the 10-02 baseline: {changed}"
    view = target / run.name
    shutil.copytree(run / "bim", view, ignore=shutil.ignore_patterns(".harness_tmp"))
    manifest = load(view / "inputs.json")
    images = {k: v["sha256"] for k, v in manifest["images"].items()}
    assert images == {k: v["sha256"] for k, v in baseline["images"].items()}
    manifest.update(implementation_sha256=implementation,
                    input_contents={"ground_truth_or_evaluation": {"included": False},
                                    "building_declaration": {"included": False}},
                    evaluation_adapter_note="implementation_sha256 and input_contents added by the "
                                            "migration evaluation adapter; the runtime's inputs.json is unchanged")
    dump(view / "inputs.json", manifest)
    selection = view / "delivery_selection.json"
    if selection.exists():
        chosen, origin = load(selection)["candidate"], "agent_selected"
    else:
        saved = sorted(view.glob("candidate_*/source_model.json"))
        if not saved:
            return view, None, "no_saved_candidate"
        chosen, origin = saved[-1].parent.name, "latest_saved_fallback_not_agent_selected"
    completed = facts["status"] == "completed" and facts["answer_present"]
    Toolkit(view).delivery(chosen, selection_origin=origin, generation_status=dict(
        state="completed" if completed else "interrupted", agent_response_completed=completed,
        elapsed_seconds=facts["receipt_elapsed_seconds"], runtime_status=facts["status"]))
    dump(view / "summary.json", dict(written_by="migration evaluation adapter, not the runtime",
                                     agent_response_completed=completed,
                                     delivery=dict(candidate=chosen, selection_origin=origin)))
    return view, chosen, origin


def evaluate(name):
    run = RUNS[name]
    facts = runtime_facts(run, subscription=name in SUBSCRIPTION)
    with tempfile.TemporaryDirectory(prefix="migration-eval-") as tmp:
        view, chosen, origin = compat_view(run, Path(tmp), facts, BUDGET_SECONDS[name])
        quality = None
        if chosen:
            importlib.import_module(PREFIX + "2026-09-23_sm24_cold_plan_setup.audit_run").audit(view)
            shared = importlib.import_module(PREFIX + "2026-09-26_sm25_multifloor_setup.audit_run")
            source, _, _ = shared.replay_final(view, chosen)
            from src.agent.judge.gt import load_gt_document
            opening = shared._opening_diagnostic(source, load_gt_document("sm24_anchor"),
                                                 load(view / "evaluation/partition.json"))
            dump(view / "evaluation/exterior_opening_diagnostic.json", opening)
            cross = importlib.import_module(PREFIX + "2026-09-30_instruction_fix.evaluate_cross_case")
            quality = cross.assess_saved(view, "sm24")
            evidence = HERE / "evaluation" / name
            evidence.mkdir(parents=True, exist_ok=True)
            for path in [view / "postrun_audit.json", *sorted((view / "evaluation").glob("*.json"))]:
                shutil.copyfile(path, evidence / path.name)
    baseline = load(BASELINE / "cross_case_evaluation.json")
    pick = lambda r: None if r is None else dict(
        rooms_one_to_one=r["spaces_one_to_one"]["pass_"], counts=r["counts"],
        positions=r["original_openings"]["positions"], hosts=r["original_openings"]["hosts"],
        door_connections=r["original_openings"]["door_connections"],
        reference_openings=r["original_openings"]["reference_count"],
        heights_within=r["strict_heights"]["within"], heights_expected=r["strict_heights"]["expected"],
        height_mismatches=[m["opening_id"] for m in r["strict_heights"]["mismatches"]])
    result = dict(attempt=name, run=str(run.relative_to(ROOT)), delivered_candidate=chosen, selection_origin=origin,
                  runtime=facts, migration=pick(quality), baseline_10_02=pick(baseline),
                  baseline_seconds=load(BASELINE / "agent_receipt.json").get("elapsed_seconds"),
                  full_quality=quality)
    dump(HERE / f"evaluation_{name}.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "full_quality"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt", choices=tuple(RUNS))
    evaluate(parser.parse_args().attempt)
