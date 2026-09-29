"""Reuse post-generation checks on the approved display-package run only."""
import argparse
import importlib

from .batch import HERE, ROOT, RUN, load, save, sha

shared = importlib.import_module("AI_agent.logs.experiments.2026-09-29_calibrated_elevation_review.audit_run")
shared.HERE, shared.ROOT, shared.RUN = HERE, ROOT, RUN


def completed():
    assert sha(HERE / "batch.py") == load(HERE / "frozen.json")["batch_script_sha256"]
    return shared.completed()


def main(action):
    completed()  # No evaluation/GT access until the real model receipt completes.
    if action == "behavior":
        shared.behavior()
    else:
        shared.evaluate()
        report = load(RUN / "postrun_audit.json")
        report["input_mode"] = load(HERE / "frozen.json")["mode"]
        save(RUN / "postrun_audit.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["behavior", "evaluate"])
    main(parser.parse_args().action)
