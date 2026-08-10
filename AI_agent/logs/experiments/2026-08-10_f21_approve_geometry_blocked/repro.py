#!/usr/bin/env python3
"""Read-only F-21 probe; run from the repository root.

It validates each native validate_case layout below case_tests/e2e_tests with
write_reports=False.  --prove copies one observed combo to a TemporaryDirectory
and exercises approve_geometry there; it never writes below case_tests/.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from src.agent.execution.run_policy_freeze import effective_run_policy
from src.agent.execution.step_orchestrator import approve_geometry
from src.agent.execution.validation_run import validate_case


ROOT = Path("case_tests/e2e_tests")
STAGE_DIRS = {"0_reading", "1_correction", "2_modelling", "3_split_pairing", "4_mep", "5_intakeoutput"}


def candidates() -> list[Path]:
    """Only directories using validate_case's per-stage artifact layout."""
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_dir()
        and "test_baseline/gt" not in path.as_posix()
        and STAGE_DIRS.intersection(child.name for child in path.iterdir() if child.is_dir())
    )


def case_for(run_dir: Path) -> Path:
    for parent in (run_dir, *run_dir.parents):
        if parent == ROOT.parent:
            break
        if (parent / "case_data").is_dir():
            return parent
    return run_dir


def validate(run_dir: Path, *, case_dir: Path | None = None) -> dict:
    # The EnergyPlus dictionary can print advisory text. Keep stdout machine-readable.
    with redirect_stdout(io.StringIO()):
        result = validate_case(run_dir, case_dir=case_dir or case_for(run_dir),
                               policy=effective_run_policy(run_dir), write_reports=False)
    return {
        "run": str(run_dir),
        "case_dir": str(case_dir or case_for(run_dir)),
        "geometry_digest": result.geometry_digest,
        "geometry_approved": result.geometry_approved,
        "blocked": result.blocked,
        "blocking_check_ids": [
            f"{key}:{row.check_id}"
            for key, report in result.reports.items()
            for row in report.blocking()
        ],
        "blocking_summary": result.blocking_summary,
    }


def isolated_approval_proof(row: dict) -> dict:
    """Prove the approval call writes despite this row's blocked=True, in /tmp."""
    source = Path(row["run"])
    original_case = case_for(source)
    with tempfile.TemporaryDirectory(prefix="f21_approve_geometry_blocked.") as temp:
        copied = Path(temp) / "run"
        # Omit any existing approval, so the saved file below was made by this probe.
        shutil.copytree(source, copied, ignore=shutil.ignore_patterns("geometry_approval.json"))
        before = validate(copied, case_dir=original_case)
        approval = approve_geometry(
            copied, actor="f21-repro", timestamp="2026-08-10T00:00:00Z",
            policy="required", note="isolated F-21 probe", case_dir=original_case,
        )
        after = validate(copied, case_dir=original_case)
        return {
            "source": str(source),
            "before_digest": before["geometry_digest"],
            "before_blocked": before["blocked"],
            "approve_returned": approval is not None,
            "saved_digest": approval.digest if approval else None,
            "approval_file_created_in_temp": (copied / "_run" / "geometry_approval.json").exists(),
            "after_geometry_approved": after["geometry_approved"],
            "after_blocked": after["blocked"],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prove", action="store_true", help="also run the isolated temporary-copy proof")
    args = parser.parse_args()
    # F-20 may edit this module concurrently.  This investigation is explicitly
    # about HEAD 78194f8, so never silently substitute an in-progress implementation.
    state = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", "src/agent/execution/validation_run.py"],
        check=False,
    )
    if state.returncode:
        raise SystemExit(
            "refusing to probe: src/agent/execution/validation_run.py differs from HEAD; "
            "run only against the recorded HEAD snapshot"
        )
    rows = []
    for run_dir in candidates():
        try:
            rows.append(validate(run_dir))
        except Exception as exc:  # retain malformed legacy layouts rather than silently skipping them
            rows.append({"run": str(run_dir), "error": f"{type(exc).__name__}: {exc}"})
    combos = [row for row in rows if row.get("geometry_digest") is not None and row.get("blocked") is True]
    output = {
        "candidate_count": len(rows),
        "error_count": sum("error" in row for row in rows),
        "digest_nonnull_count": sum(row.get("geometry_digest") is not None for row in rows),
        "digest_and_blocked_count": len(combos),
        "combos": combos,
    }
    if args.prove and combos:
        output["isolated_approval_proof"] = isolated_approval_proof(combos[0])
    # validate_case can replace sys.stdout in a dependency; use the original stream.
    print(json.dumps(output, indent=2, sort_keys=True), file=sys.__stdout__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
