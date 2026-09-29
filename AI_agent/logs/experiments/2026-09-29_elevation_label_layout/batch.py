"""Prepare one elevation-display comparison; a model run requires this batch's approval."""
import argparse
import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch


# Reuse the prior single-call launch/receipt guard without changing its files.
previous = importlib.import_module("AI_agent.logs.experiments.2026-09-29_calibrated_elevation_review.batch")
HELPER_FILE = Path(previous.__file__).resolve()
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-29_sm21_elevation_label_recovery_run90"
OLD = json.loads((HELPER_FILE.parent / "frozen.json").read_text())
previous.HERE, previous.RUN, previous.__file__ = HERE, RUN, __file__
runner, load, save, sha = previous.runner, previous.load, previous.save, previous.sha


def prepare():
    offline = HERE / "offline_preflight_colour"
    assert not (HERE / "frozen.json").exists() and not RUN.exists()

    class ModelBoundary(Exception):
        pass

    def stop(command, **kwargs):
        assert command[0] == "claude" and command[command.index("--model") + 1] == "claude-sonnet-5"
        raise ModelBoundary()

    with patch.object(subprocess, "Popen", stop):
        try:
            runner.run_experiment(previous.arguments(offline))
        except ModelBoundary:
            pass
        else:
            raise AssertionError("Model launch boundary was not intercepted")
    manifest, request = load(offline / "inputs.json"), load(offline / "agent_request.json")
    assert request == OLD["request"]
    assert manifest["images"] == OLD["images"]
    assert sha(offline / "seed/proposal.json") == OLD["seed_proposal_sha256"]
    execution = {name: sha(ROOT / name) for name in OLD["execution_sha256"]}
    changed = [name for name, value in execution.items() if value != OLD["execution_sha256"][name]]
    assert changed == ["src/agent/geometry/source_elevation_overlay.py"], changed
    assert manifest["implementation_sha256"] == {name: execution[name] for name in OLD["implementation_sha256"]}
    cli = subprocess.check_output(["claude", "--version"], text=True).strip()
    assert cli == OLD["cli_version"]
    assert hashlib.sha256(runner.GUIDE.encode()).hexdigest() == OLD["guide_sha256"]
    asyncio.run(previous.replay(offline))
    execution[str(HELPER_FILE.relative_to(ROOT))] = sha(HELPER_FILE)
    frozen = {**OLD, "mode": "saved_proposal_elevation_display_comparison",
              "baseline_commit": "42c45ada", "run": RUN.name,
              "implementation_sha256": manifest["implementation_sha256"],
              "execution_sha256": execution, "batch_script_sha256": sha(Path(__file__)),
              "production_changes_from_run89": changed,
              "limits": ["Same six originals, run88 proposal, scope, guide, model, effort and limits as run89.",
                         "Only production change: elevation annotation placement, grayscale reference background, purple doors and display metadata.",
                         "No prior claims, developer anchors, error locations, target dimensions, audits or GT supplied.",
                         "One saved-model comparison, not a cold start or proof of causality/stability.",
                         "No retry, continuation, local model, paid API or fallback."]}
    save(HERE / "frozen.json", frozen)
    save(HERE / "preflight.json", dict(model_calls=0, model_process_intercepted=True,
        real_stdio=True, full_colour_originals_and_grayscale_overlays_exact=True,
        same_request_images_seed_guide_and_cli_as_run89=True, production_changes=changed,
        frozen_sha256=sha(HERE / "frozen.json"), implementation_files=len(manifest["implementation_sha256"]),
        execution_files=len(execution), no_run90_created=not RUN.exists()))
    print(json.dumps(dict(prepared=True, model_calls=0, frozen_sha256=sha(HERE / "frozen.json"))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    prepare() if parser.parse_args().action == "prepare" else previous.run()
