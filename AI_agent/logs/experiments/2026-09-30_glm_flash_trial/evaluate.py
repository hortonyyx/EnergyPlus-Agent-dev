"""Offline trial assessment and a factual comparison with Sonnet run98."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
trial = importlib.import_module("AI_agent.logs.experiments.2026-09-30_glm_flash_trial.trial")
checks = importlib.import_module("AI_agent.logs.experiments.2026-09-30_instruction_fix.evaluate")
audit_module = importlib.import_module("AI_agent.logs.experiments.2026-09-30_glm_flash_trial.audit_sm21")
load, dump = trial.load, trial.runner.dump


def brief(result):
    original, heights = result.get("original_openings", {}), result.get("strict_heights", {})
    return dict(run=result["run"], completed=result["completed"], model=result["actual_model"],
                elapsed_seconds=result["elapsed_seconds"], counts=result.get("counts"),
                spaces_one_to_one=result.get("spaces_one_to_one", {}).get("pass_"),
                opening_positions=original.get("positions"), opening_hosts=original.get("hosts"),
                opening_reference_count=original.get("reference_count"),
                door_connections=original.get("door_connections"),
                strict_heights_within=heights.get("within"), strict_heights_matched=heights.get("matched"),
                strict_partition_status=result.get("strict_partition_status"),
                behaviour=result.get("behaviour"))


def main():
    run = trial.RUN
    summary, receipt, manifest = (load(run / name) for name in
                                ("summary.json", "agent_receipt.json", "inputs.json"))
    condition = load(run / "experiment_condition.json")
    assert condition == dict(run_id="glm_trial01", **load(HERE / "preflight.json")["conditions"])
    assert hashlib.sha256(manifest["scope"].encode()).hexdigest() == condition["scope_sha256"]
    for name, sha in condition["transport_sha256"].items():
        assert trial.runner.digest(run / "runtime_snapshot" / name) == sha
    completed = (summary.get("agent_response_completed") is True and receipt.get("returncode") == 0
                 and receipt.get("actual_model") == trial.MODEL and not receipt.get("timed_out")
                 and not receipt.get("routing_error") and not (receipt.get("result") or {}).get("is_error"))
    tools = run / "tools.jsonl"
    result = dict(run=run.name, completed=completed, elapsed_seconds=receipt.get("elapsed_seconds"),
                  actual_model=receipt.get("actual_model"),
                  behaviour=checks.behaviour(run) if tools.exists() and tools.stat().st_size else {},
                  drawing_differences=checks.difference_trace(run))
    if completed and (run / "delivery.json").exists():
        frozen = dict(scope=manifest["scope"], provider="glm",
                      image_sha256={k: v["sha256"] for k, v in manifest["images"].items()},
                      mode="instruction_fix_glm_trial_original_only_cold", continuation_rounds=0,
                      max_candidates=24)
        target = HERE / f"{run.name}_frozen.json"
        if target.exists():
            assert load(target) == frozen
        else:
            dump(target, frozen)
        audit = audit_module.audit(run)
        source = load(run / audit["candidate"] / "source_model.json")
        result.update(counts=audit["counts"], strict_partition_status=audit["strict_partition_status"],
                      space_identity_findings=audit["space_identity_findings"],
                      spaces_one_to_one=checks.spaces_one_to_one(audit["original_openings"], source),
                      original_openings=audit["original_openings"],
                      exterior_matched=audit["matched_exterior"],
                      exterior_parameters_match_old_tolerance=audit["exterior_parameters_match"],
                      strict_heights=checks.strict_heights(run), unresolved=audit["unresolved"],
                      source_assumptions=audit["source_assumptions"])
    else:
        result["quality"] = "No complete delivered result; retain evidence, no retry or repair."
    dump(run / "trial_evaluation.json", result)
    comparison = dict(baseline=brief(load(trial.BASELINE / "fix_evaluation.json")), current=brief(result),
                      same_prompt_system_images_and_runtime=True,
                      changed="Provider and requested model only; separate subscription service/session.",
                      limits=["One trial is not stability evidence or a causal estimate of model quality.",
                              "No production model/default change; main Sonnet recovery remains separate."])
    dump(HERE / "comparison.json", comparison)
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
