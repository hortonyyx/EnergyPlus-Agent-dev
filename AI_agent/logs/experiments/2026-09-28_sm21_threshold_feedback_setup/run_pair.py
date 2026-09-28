"""Prepared two-arm batch. Run only after the user approves this concrete batch."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from scripts.tool_scripts import run_bim_agent as runner
from . import server

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = importlib.import_module(
    "AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold").SCOPE


def conditions():
    images = ROOT / "case_tests/e2e_tests/sm21_anchor/case_data"
    producer_paths = json.loads((HERE.parent /
        "2026-09-27_sm21_guidance_control_run71/inputs.json").read_text())["implementation_sha256"]
    return dict(scope=SCOPE, mode="original_only_view_profile_threshold_comparison",
        image_sha256={p.name: runner.digest(p) for p in sorted(images.glob("*.png"))},
        guide_sha256=hashlib.sha256(runner.GUIDE.encode()).hexdigest(),
        references_sha256=hashlib.sha256(json.dumps(runner.REFERENCES, sort_keys=True).encode()).hexdigest(),
        provider="claude", role="sonnet", effort="medium", timeout_seconds=3000,
        max_candidates=24, continuation_rounds=0, primary_invocations_per_arm=1,
        implementation_sha256={name: runner.digest(ROOT / name) for name in producer_paths},
        experiment_sha256={p.name: runner.digest(p) for p in sorted(HERE.glob("*.py"))},
        method_sha256={"legacy": server.method_hash(server.LEGACY.view_profile),
                       "current": server.method_hash(runner.Toolkit.view_profile)},
        controlled_difference="Only Toolkit.view_profile response: unchanged thresholded candidates plus explicit positive support excluded by that same threshold on both axes. Same 39 tool schemas/descriptions, GUIDE, references, geometry, images and budgets.",
        withheld=["saved BIM/plans", "old observations/calibrations", "GT/evaluation",
                  "building declaration", "correct counts/coordinates/heights", "developer live answers"],
        limits=["One pair is diagnostic, not evidence of stability or a unique historical cause.",
                "This does not itself fix mm/m errors, dimension transcription or facade-height interpretation.",
                "No continuations or nested model calls; no automatic retries or further cases."])


def require_completed_run(run_path):
    summary = json.loads((run_path / "summary.json").read_text())
    receipt = json.loads((run_path / "agent_receipt.json").read_text())
    result = receipt.get("result") or {}
    if (not summary.get("agent_response_completed") or receipt.get("returncode") != 0
            or result.get("is_error")):
        raise RuntimeError("Model invocation failed or interrupted; preserved run is not a completed result. Stop and inspect its receipt before any next invocation.")


def run(variant, name):
    assert name and Path(name).name == name and name not in {".", ".."}
    run_path = HERE.parent / name
    frozen_path = HERE / f"{name}_frozen.json"
    assert not run_path.exists() and not frozen_path.exists(), "Never overwrite a run"
    frozen = {**conditions(), "variant": variant,
              "producer_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}
    proposed = json.loads((HERE / "proposed_batch.json").read_text())
    assert proposed["conditions"] == conditions(), "Prepared conditions changed; review the batch again"
    runner.dump(frozen_path, frozen)
    original_subscription = runner.subscription
    calls = 0

    def subscription(run, *args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls == 1 and not kwargs.get("readonly") and kwargs["model"] == "sonnet"
        runner.dump(run / "experiment_condition.json", frozen)
        manifest = json.loads((run / "inputs.json").read_text())
        assert manifest["implementation_sha256"] == frozen["implementation_sha256"]
        for name, expected in frozen["implementation_sha256"].items():
            source = ROOT / name
            assert runner.digest(source) == expected
            target = run / "runtime_snapshot" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        for name, expected in frozen["experiment_sha256"].items():
            assert runner.digest(HERE / name) == expected
            target = run / "experiment_snapshot" / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes((HERE / name).read_bytes())
        # The manifest was already hashed against the real producer. Change only
        # the MCP process entry for this call; restore __file__ on every exit.
        with patch.object(runner, "__file__", str(HERE / "server.py")):
            return original_subscription(run, *args, **kwargs)

    with patch.object(runner, "subscription", subscription):
        runner.run_experiment(SimpleNamespace(command="run",
            images=ROOT / "case_tests/e2e_tests/sm21_anchor/case_data", mesh=None,
            building_input=None, out=run_path, scope=SCOPE, timeout=3000,
            continuation_rounds=0, max_candidates=24, provider="claude", exploratory_opus=False,
            effort="medium", resume_candidate=None, resume_plan=None, plan_image=None))
    assert calls == 1
    require_completed_run(run_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "run"])
    parser.add_argument("--variant", choices=["legacy", "current"])
    parser.add_argument("--run")
    args = parser.parse_args()
    if args.command == "prepare":
        runner.dump(HERE / "proposed_batch.json", {"status": "proposed_not_authorized_or_run",
            "arms": ["legacy", "current"], "total_primary_invocations": 2, "conditions": conditions(),
            "evaluation": "Post-generation only: original/GT partitions with distinct room identity, openings/hosts/connections/height families, source/display/transport and viewer. Audit actual view_pixel_profile exposure and affected observation/decision; preserve interruptions and all failures. One pair cannot prove stability or a unique cause."})
    else:
        assert args.variant and args.run, "--variant and --run required"
        run(args.variant, args.run)


if __name__ == "__main__":
    main()
