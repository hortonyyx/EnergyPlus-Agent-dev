"""Frozen independent repeat of run57, using only its original input images."""
import importlib
import json
from pathlib import Path

from scripts.tool_scripts.run_bim_agent import digest, dump

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN = HERE.parent / "2026-09-27_sm21_whole_building_repeat_claude_run58"
BASE = HERE.parent / "2026-09-26_sm21_whole_building_claude_run57"


def main():
    assert not RUN.exists(), "Independent runs must not overwrite earlier evidence"
    previous = json.loads((BASE / "inputs.json").read_text())
    runner = importlib.import_module(
        "AI_agent.logs.experiments.2026-09-26_sm21_whole_building_setup.run_cold")
    assert runner.SCOPE == previous["scope"]
    for name, sha in previous["implementation_sha256"].items():
        assert digest(ROOT / name) == sha, f"Frozen implementation changed: {name}"
    for name, metadata in previous["images"].items():
        assert digest(ROOT / "case_tests/e2e_tests/sm21_anchor/case_data" / name) == metadata["sha256"]
    dump(HERE / "repeat_preflight.json", {
        "baseline_run": str(BASE.relative_to(ROOT)),
        "baseline_manifest_sha256": digest(BASE / "inputs.json"),
        "same_scope": True,
        "implementation_sha256": previous["implementation_sha256"],
        "generation_inputs": "Six original PNG images and identical generic task only",
        "baseline_artifacts_exposed_to_model": False,
        "developer_participation": "Astra only; no live intervention or product delegation",
    })
    runner.HERE = HERE
    runner.RUN = RUN
    runner.main()


if __name__ == "__main__":
    main()
