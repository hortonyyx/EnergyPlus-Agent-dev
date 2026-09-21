#!/usr/bin/env python3
"""Controller-only legacy evaluation after both reader invocations are frozen."""
from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
REV = "723b0f98ed37285b66cb3d1d30caa8e42eb01a74"
RUN = ROOT / "AI_agent/logs/experiments/2026-09-21_historical_sm21_pilot_run01"
GATE = ROOT / "AI_agent/logs/experiments/2026-09-16_reading_method_reproduction/controller_legacy_gate"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def old(path):
    return subprocess.check_output(["git", "show", f"{REV}:{path}"], cwd=ROOT)


def main():
    out = RUN / "controller_evaluation"
    out.mkdir(exist_ok=False)
    inputs = {}
    for label, number in [("pilot_01", "001"), ("pilot_02", "002")]:
        invocation = RUN / "invocations" / label
        receipt = json.loads((invocation / "receipt.json").read_text())
        assert receipt["returncode"] == 0 and not receipt["timed_out"]
        review = json.loads((invocation / "source_review.json").read_text())
        reading = invocation / "snapshot/0_reading/submissions" / number / "1f_view.json"
        assert sha(reading.read_bytes()) == review["files"]["1f_view.json"]
        inputs[label] = reading
    # Reader sessions are complete; no model is resumed by this script.
    manifest = {"revision": REV, "scope": "controller_only_after_final_source_review",
                "GT_fed_to_reader": False, "sources": {}, "inputs": {
                    label: {"path": str(p.relative_to(ROOT)), "sha256": sha(p.read_bytes())}
                    for label, p in inputs.items()}}
    for path in GATE.rglob("*.py"):
        relative = path.relative_to(GATE).as_posix()
        data = path.read_bytes()
        compatibility_markers = {"src/__init__.py", "src/agent/__init__.py",
                                 "src/validator/__init__.py", "src/validator/checks/__init__.py"}
        if relative.startswith("src/") and relative not in compatibility_markers:
            assert data == old(relative), relative
        manifest["sources"][str(path.relative_to(ROOT))] = sha(data)
    command = [sys.executable, str(GATE / "check_legacy.py"),
               *[str(p) for p in inputs.values()], "--dimensioned", "true", "--pretty"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    (out / "legacy_gate.json").write_text(result.stdout)
    (out / "legacy_gate_stderr.txt").write_text(result.stderr)
    assert result.returncode in (0, 1), result.stderr
    manifest["gate_command"] = command
    manifest["gate_compatibility_markers"] = sorted(compatibility_markers)
    manifest["gate_returncode"] = result.returncode
    with tempfile.TemporaryDirectory(prefix="historical-controller-score-") as tmp:
        package = Path(tmp) / "legacy_score"
        package.mkdir()
        (package / "__init__.py").write_text("")
        for name in ("gt.py", "reading_score.py"):
            source = "src/agent/judge/" + name
            data = old(source)
            manifest["sources"][f"git:{REV}:{source}"] = sha(data)
            (package / name).write_bytes(data)
        gt_source = "case_tests/test_baseline/gt/sm21_anchor/gt.json"
        gt_bytes = old(gt_source)
        manifest["sources"][f"git:{REV}:{gt_source}"] = sha(gt_bytes)
        gt = json.loads(gt_bytes)
        sys.path.insert(0, tmp)
        scorer = importlib.import_module("legacy_score.reading_score")
        scores = {}
        for label, path in inputs.items():
            score = scorer.score_floor(json.loads(path.read_text()), gt, "Floor 1")
            scores[label] = {"wall_hits": score.wall_hits(), "window_hits": score.window_hits(),
                             "boundary_hits": score.boundary_hits(),
                             "max_wall_offset_m": score.max_wall_offset(),
                             "detail": dataclasses.asdict(score)}
        (out / "legacy_scores.json").write_text(json.dumps(scores, indent=2) + "\n")
    manifest["limits"] = "One-floor old wall/window scorer only; no whole-case 100-point score, doors, source overlay registration or BIM verdict."
    manifest["result_sha256"] = {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({label: {k: v for k, v in row.items() if k != "detail"}
                      for label, row in scores.items()}))


if __name__ == "__main__":
    main()
