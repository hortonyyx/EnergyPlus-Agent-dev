#!/usr/bin/env python3
"""Run the 723b0f9 schema loader and reading gate without importing current code."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
REVISION = "723b0f9"
sys.path.insert(0, str(HERE))

from src.agent.reading import load_reading_view  # noqa: E402
from src.validator.checks.reading import check_reading_view  # noqa: E402


def _result(path: Path, *, dimensioned: bool, run_profile: str, capability_profile: str) -> dict:
    raw_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        view = load_reading_view(path)
        report = check_reading_view(
            view,
            capability_profile=capability_profile,
            run_profile=run_profile,
            view_metadata={"dimensioned": dimensioned},
        )
    except Exception as exc:  # The CLI must return a JSON failure, not a traceback-only result.
        return {
            "path": str(path.resolve()),
            "sha256": raw_sha256,
            "schema_valid": False,
            "passed": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }

    status_counts = Counter(item.status.value for item in report.results)
    blocking = [item.model_dump(mode="json") for item in report.blocking()]
    flagged = [item.model_dump(mode="json") for item in report.flagged()]
    return {
        "path": str(path.resolve()),
        "sha256": raw_sha256,
        "schema_valid": True,
        "passed": report.passed,
        "status_counts": dict(sorted(status_counts.items())),
        "blocking": blocking,
        "flagged": flagged,
        "report": report.model_dump(mode="json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check one or more reading JSON files with the frozen 723b0f9 gate."
    )
    parser.add_argument("reading_json", nargs="+", type=Path)
    parser.add_argument(
        "--dimensioned",
        choices=("true", "false"),
        default="false",
        help=(
            "Historical run_stage metadata flag. The 07-07 sm24 recorded attempt used false "
            "even though dimensions were present."
        ),
    )
    parser.add_argument(
        "--run-profile",
        choices=("exploratory", "dev", "golden", "regression"),
        default="exploratory",
    )
    parser.add_argument("--capability-profile", default="orthogonal_polygon")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    checked = [
        _result(
            path,
            dimensioned=args.dimensioned == "true",
            run_profile=args.run_profile,
            capability_profile=args.capability_profile,
        )
        for path in args.reading_json
    ]
    module_files = {
        "loader": str(Path(inspect.getsourcefile(load_reading_view) or "").resolve()),
        "gate": str(Path(inspect.getsourcefile(check_reading_view) or "").resolve()),
    }
    current_gate_imported = any(
        HERE not in Path(path).parents for path in module_files.values()
    )
    payload = {
        "checker_revision": REVISION,
        "checker_root": str(HERE),
        "module_files": module_files,
        "current_project_gate_imported": current_gate_imported,
        "settings": {
            "dimensioned": args.dimensioned == "true",
            "run_profile": args.run_profile,
            "capability_profile": args.capability_profile,
        },
        "results": checked,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    if any(not item["schema_valid"] for item in checked):
        return 2
    return 0 if all(item["passed"] for item in checked) else 1


if __name__ == "__main__":
    raise SystemExit(main())
