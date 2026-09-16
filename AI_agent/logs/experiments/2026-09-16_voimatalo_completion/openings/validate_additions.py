#!/usr/bin/env python3
"""Validate opening additions through the existing Voimatalo source assembler."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT / "AI_agent/logs/experiments/2026-09-15_voimatalo_developer_walkthrough"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    base_path = OLD / "assembly_observations.json"
    additions_path = HERE / "assembly_windows.json"
    base = json.loads(base_path.read_text())
    additions = json.loads(additions_path.read_text())
    expected_ids = {row["id"] for row in additions["openings"]}
    merged = {
        **base,
        "openings": base["openings"] + additions["openings"],
        "completion_additions": {
            "source": "assembly_windows.json",
            "count": len(expected_ids),
        },
    }
    with tempfile.TemporaryDirectory(prefix="voimatalo-opening-check-") as temporary:
        temporary_path = Path(temporary)
        aperture_path = temporary_path / "merged_apertures.json"
        aperture_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        adjusted_plan_path = temporary_path / "case_plan_adjusted_levels.json"
        adjusted_plan = json.loads((OLD / "case_plan.json").read_text())
        adjusted_plan["storey_levels_m"] = [
            0, 5.6, 9.32, 12.48, 15.63, 18.78, 21.93, 25.10, 27.8
        ]
        adjusted_plan_path.write_text(
            json.dumps(adjusted_plan, ensure_ascii=False, indent=2) + "\n"
        )

        def run(label: str, plan_path: Path) -> tuple[dict, Path]:
            candidate_path = temporary_path / f"candidate_{label}"
            command = [
                sys.executable,
                str(OLD / "assemble_model.py"),
                "--plan",
                str(plan_path),
                "--apertures",
                str(aperture_path),
                "--out",
                str(candidate_path),
            ]
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            return {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }, candidate_path

        frozen_run, _ = run("frozen_levels", OLD / "case_plan.json")
        adjusted_run, candidate_path = run("adjusted_levels", adjusted_plan_path)
        result = {
            "schema": "voimatalo_opening_addition_validation_v1",
            "frozen_level_run_expected_host_failure": frozen_run,
            "adjusted_storey_levels_m": adjusted_plan["storey_levels_m"],
            "adjusted_level_run": adjusted_run,
            "base_apertures_sha256": digest(base_path),
            "additions_sha256": digest(additions_path),
            "base_opening_count": len(base["openings"]),
            "addition_count": len(expected_ids),
            "duplicate_ids_across_base_and_additions": sorted(
                {row["id"] for row in base["openings"]} & expected_ids
            ),
        }
        if adjusted_run["returncode"] == 0:
            source = json.loads((candidate_path / "source_model.json").read_text())
            built = {row["id"]: row for row in source["openings"] if row["id"] in expected_ids}
            result.update(
                {
                    "source_status": json.loads(
                        (candidate_path / "report.json").read_text()
                    ).get("status"),
                    "built_addition_count": len(built),
                    "missing_addition_ids": sorted(expected_ids - set(built)),
                    "unbuilt_openings": source["unbuilt_openings"],
                    "conflict_count": len(source["conflicts"]),
                    "built_hosts": {
                        opening_id: row["host_boundary_id"]
                        for opening_id, row in sorted(built.items())
                    },
                    "passed": (
                        len(built) == len(expected_ids)
                        and not source["unbuilt_openings"]
                        and not source["conflicts"]
                    ),
                }
            )
        else:
            result["passed"] = False
    (HERE / "validation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
