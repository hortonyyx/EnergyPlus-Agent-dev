#!/usr/bin/env python3
"""S-6 evidence-retention probe.

F-35: do CV sidecars (out/cv/cv_evidence/**) reach the attempt after a REAL merge?
F-50: exact merge failure when only one per-image view exists (no aggregate).
      plus: aggregate-with-one-view shape — is it archivable at all?
F-44: access_log on ALLOW carries tool_input_excerpt + executed_code sha256.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))

from src.agent.execution.isolation import (  # noqa: E402
    build_isolation_workspace,
    merge_isolated_output,
)
from src.agent.execution.view_manifest import provision_view_manifest  # noqa: E402

CASE_SRC = REPO / "case_tests" / "e2e_tests" / "sm21_anchor"
REAL_VIEWS = json.loads(
    (CASE_SRC / "run_2026-06-20_gpt54_reading" / "0_reading" / "attempts" / "002" / "output.json").read_text("utf-8")
)
OUT = Path(__file__).resolve().parent / "s6_evidence_report.json"
IMG = "case_data/1f_view.png"


def _env(staging: Path) -> dict:
    return {"PATH": os.environ.get("PATH", ""), "HOME": "/tmp", "PYTHONPATH": str(staging)}


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="s6_", dir="/tmp/ep_isolation"))
    report: dict = {}

    # ============ F-35: CV evidence after a real merge =====================
    case_dir = tmp / "case"
    shutil.copytree(CASE_SRC, case_dir)
    run_dir = tmp / "run_f35"
    run_dir.mkdir()
    (run_dir / "run_config.yaml").write_text("", encoding="utf-8")
    provision_view_manifest(case_dir, run_dir)
    staging = build_isolation_workspace(
        case_dir, run_dir=run_dir, staging_root=tmp / "staging_f35"
    ).staging_root

    # run one REAL probe through the wrapper so out/cv really has a sidecar
    proc = subprocess.run(
        [sys.executable, "tools/run_cv_probe.py", "--tool", "storey_line_profiler",
         "--image", IMG, "--out-dir", "out/cv"],
        capture_output=True, text=True, cwd=staging, env=_env(staging), check=False)
    sidecars_before = sorted(
        str(p.relative_to(staging)) for p in (staging / "out" / "cv").rglob("*.json")
    ) if (staging / "out" / "cv").exists() else []
    (staging / "out" / "output.json").write_text(json.dumps({"views": REAL_VIEWS}), encoding="utf-8")
    (staging / "out" / "reading_summary.md").write_text("summary", encoding="utf-8")

    attempt_dir = merge_isolated_output(staging, run_dir)
    attempt_tree = sorted(str(p.relative_to(attempt_dir)) for p in attempt_dir.rglob("*"))
    stage_tree = sorted(
        str(p.relative_to(run_dir / "0_reading")) for p in (run_dir / "0_reading").rglob("*")
    )
    report["f35"] = {
        "probe_rc": proc.returncode,
        "sidecars_in_staging_before_merge": sidecars_before,
        "attempt_dir": str(attempt_dir),
        "attempt_tree": attempt_tree,
        "stage_tree": stage_tree,
        "cv_evidence_in_attempt": any("cv" in p for p in attempt_tree),
    }

    # ============ F-50: single per-image view, no aggregate ==================
    run_dir2 = tmp / "run_f50a"
    run_dir2.mkdir()
    (run_dir2 / "run_config.yaml").write_text("", encoding="utf-8")
    provision_view_manifest(case_dir, run_dir2)
    staging2 = build_isolation_workspace(
        case_dir, run_dir=run_dir2, staging_root=tmp / "staging_f50a"
    ).staging_root
    (staging2 / "out" / "1f_view.json").write_text(
        json.dumps(REAL_VIEWS["1f_view"]), encoding="utf-8"
    )
    try:
        merge_isolated_output(staging2, run_dir2)
        report["f50_per_image_single"] = {"outcome": "MERGED (unexpected)"}
    except ValueError as exc:
        report["f50_per_image_single"] = {"outcome": "ValueError", "message": str(exc)}
    report["f50_per_image_single"]["attempts_created"] = sorted(
        p.name for p in (run_dir2 / "0_reading" / "attempts").iterdir()
    ) if (run_dir2 / "0_reading" / "attempts").exists() else []

    # ============ F-50b: aggregate output.json with ONE view =================
    run_dir3 = tmp / "run_f50b"
    run_dir3.mkdir()
    (run_dir3 / "run_config.yaml").write_text("", encoding="utf-8")
    provision_view_manifest(case_dir, run_dir3)
    staging3 = build_isolation_workspace(
        case_dir, run_dir=run_dir3, staging_root=tmp / "staging_f50b"
    ).staging_root
    (staging3 / "out" / "output.json").write_text(
        json.dumps({"views": {"1f_view": REAL_VIEWS["1f_view"]}}), encoding="utf-8"
    )
    try:
        attempt3 = merge_isolated_output(staging3, run_dir3)
        checks = json.loads((attempt3 / "checks.json").read_text("utf-8"))
        cov = [r for r in checks["results"] if r["check_id"] == "reading.view_manifest_coverage"]
        from src.agent.execution.manifest import load_run_manifest
        report["f50_aggregate_single"] = {
            "outcome": "merged as attempt (filed)",
            "attempt": attempt3.name,
            "coverage_status": cov[0]["status"] if cov else None,
            "coverage_evidence": cov[0].get("evidence") if cov else None,
            "accepted": load_run_manifest(run_dir3).accepted("0_reading") is not None,
        }
    except ValueError as exc:
        report["f50_aggregate_single"] = {"outcome": "ValueError", "message": str(exc)}

    # ============ F-44: access_log on allow ================================
    run_dir4 = tmp / "run_f44"
    run_dir4.mkdir()
    (run_dir4 / "run_config.yaml").write_text("", encoding="utf-8")
    provision_view_manifest(case_dir, run_dir4)
    staging4 = build_isolation_workspace(
        case_dir, run_dir=run_dir4, staging_root=tmp / "staging_f44"
    ).staging_root
    log = staging4 / "access_log.jsonl"
    hooks = [
        {"tool_name": "Bash", "tool_input": {
            "command": f"python tools/run_cv_probe.py --tool storey_line_profiler --image {IMG} --out-dir out/f44"}},
        {"tool_name": "Bash", "tool_input": {
            "command": "python -c 'print(1+1)'"}},
        {"tool_name": "Write", "tool_input": {"file_path": "out/note.md", "content": "hello"}},
        {"tool_name": "Bash", "tool_input": {"command": "cat case_tests/x"}},
    ]
    for payload in hooks:
        subprocess.run([sys.executable, str(staging4 / "guard.py")],
                       input=json.dumps(payload), text=True, cwd=staging4,
                       capture_output=True, check=False)
    entries = [json.loads(line) for line in log.read_text("utf-8").splitlines() if line.strip()]
    report["f44"] = {
        "entries": [
            {
                "decision": e["decision"],
                "reason": e["reason"][:80],
                "has_excerpt": bool(e.get("tool_input_excerpt")),
                "excerpt_len": len(e.get("tool_input_excerpt", "")),
                "excerpt_sample": e.get("tool_input_excerpt", "")[:150],
                "executed_code": e.get("executed_code"),
            }
            for e in entries
        ]
    }

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
