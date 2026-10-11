"""Explicit external locations for optional historical checks.

Nothing falls back to a repository archive or silently restores historical data.
The check command supplies these roots only for an explicitly selected archive run.
"""

import os
from pathlib import Path


def archive_path(relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("archive path must be relative and remain within its root")
    if path.parts and path.parts[0] == "case_tests":
        key, suffix = "SIM_BIM_TEST_CASES_ROOT", Path(*path.parts[1:])
    else:
        key, suffix = "SIM_BIM_TEST_ARCHIVE_ROOT", path
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"historical check requires an explicit {key}")
    root = Path(value)
    if not root.is_absolute():
        raise ValueError(f"{key} must be an absolute external path")
    target = (root / suffix).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("archive path escapes its explicit root")
    return target
