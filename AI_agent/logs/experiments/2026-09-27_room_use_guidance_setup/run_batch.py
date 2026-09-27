"""Prepare or execute the explicit four-run batch; execution needs user approval."""
import argparse
import importlib
import inspect
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as runner
from . import server

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPES = {case: importlib.import_module(
    f"AI_agent.logs.experiments.2026-09-26_{case}_whole_building_setup.run_cold").SCOPE
    for case in ("sm21", "sm24")}
ARMS = [{"case": case, "variant": variant,
         "run": f"2026-09-27_{case}_use_guidance_{variant}_run{number}"}
        for case, variant, number in [("sm21", "before", 75), ("sm21", "after", 76),
                                     ("sm24", "before", 77), ("sm24", "after", 78)]]


def conditions():
    paths = json.loads((HERE.parent / "2026-09-27_sm21_profile_current_run74/inputs.json").read_text())["implementation_sha256"]
    return {"cases": {case: {"scope": scope, "image_sha256": {
                p.name: runner.digest(p) for p in sorted((ROOT / f"case_tests/e2e_tests/{case}_anchor/case_data").glob("*.png"))}}
                for case, scope in SCOPES.items()},
            "provider": "claude", "role": "sonnet", "effort": "medium", "timeout_seconds": 3000,
            "max_candidates": 24, "continuation_rounds": 0, "primary_invocations_per_arm": 1,
            "guide_sha256": {"before": server.sha(server.BEFORE_GUIDE), "after": server.sha(server.CURRENT_GUIDE)},
            "review_method_sha256": {"before": server.sha(inspect.getsource(server.baseline_feedback)),
                                      "after": server.sha(inspect.getsource(server.CURRENT_REVIEW))},
            "references_sha256": server.sha(json.dumps(runner.REFERENCES, sort_keys=True)),
            "implementation_sha256": {p: runner.digest(ROOT / p) for p in paths},
            "experiment_sha256": {p.name: runner.digest(p) for p in sorted(HERE.iterdir())
                                  if p.suffix == ".py" or p.name == "baseline_guide.json"},
            "controlled_difference": "Room-use guidance placement only: shorter standing use guidance and no next_action on automatic candidate-save coverage. Explicit inspection/delivery, factual coverage, catalogs, edits, geometry and other tools retained.",
            "limits": ["Two surfaces form one work-organization change; this does not isolate their individual effects.",
                       "One invocation per case/arm cannot establish stability or the historical regression cause.",
                       "No saved BIM, GT, prior measurements, correct answers, live hints, nested calls, continuations or automatic retries."]}


def run_arm(case, variant):
    arm = next(a for a in ARMS if a["case"] == case and a["variant"] == variant)
    prepared = json.loads((HERE / "proposed_batch.json").read_text())
    current = conditions()
    assert current == prepared["conditions"], "Prepared batch changed; review its conditions again"
    run = HERE.parent / arm["run"]
    frozen_path = HERE / f"{arm['run']}_frozen.json"
    assert not run.exists() and not frozen_path.exists(), "Never replace a run"
    frozen = {**current, **arm, **current["cases"][case],
              "mode": "original_only_room_use_guidance_comparison",
              "producer_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    runner.dump(frozen_path, frozen)
    original_subscription = runner.subscription
    calls = 0

    def invoke(run, *args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and kwargs["model"] == "sonnet" and not kwargs.get("readonly")
        runner.dump(run / "experiment_condition.json", frozen)
        manifest = json.loads((run / "inputs.json").read_text())
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        for path, expected in frozen["implementation_sha256"].items():
            assert runner.digest(ROOT / path) == expected
            target = run / "runtime_snapshot" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / path).read_bytes())
        for path, expected in frozen["experiment_sha256"].items():
            assert runner.digest(HERE / path) == expected
            target = run / "experiment_snapshot" / path
            target.parent.mkdir(exist_ok=True)
            target.write_bytes((HERE / path).read_bytes())
        with patch.object(runner, "__file__", str(HERE / "server.py")):
            return original_subscription(run, *args, **kwargs)

    with server.condition(variant), patch.object(runner, "subscription", invoke):
        runner.run_experiment(SimpleNamespace(command="run", out=run,
            images=ROOT / f"case_tests/e2e_tests/{case}_anchor/case_data", mesh=None, building_input=None,
            scope=SCOPES[case], timeout=3000, max_candidates=24, continuation_rounds=0,
            provider="claude", exploratory_opus=False, effort="medium",
            resume_candidate=None, resume_plan=None, plan_image=None))
    assert calls == 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run"))
    parser.add_argument("--case", choices=("sm21", "sm24"))
    parser.add_argument("--variant", choices=("before", "after"))
    args = parser.parse_args()
    if args.command == "prepare":
        runner.dump(HERE / "proposed_batch.json", {"status": "prepared_not_approved_not_run",
            "arms": ARMS, "total_primary_invocations": 4, "conditions": conditions(),
            "evaluation": "After generation: original partitions/openings/hosts/connections/heights, source/view consistency, actual guidance exposure, plausible use evidence, and viewer. Preserve each run; no automatic acceptance or extra samples."})
    else:
        assert args.case and args.variant
        run_arm(args.case, args.variant)


if __name__ == "__main__":
    main()
