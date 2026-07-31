#!/usr/bin/env python3
"""Validated cv_probe request wrapper for isolated reading workspaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALLOWED_TOOLS = {
    "crop_zoom",
    "wall_line_profiler",
    "storey_line_profiler",
    "px_m_calibrator",
    "window_cc_detector",
    "overlay_logger",
    "prescan-plan",
    "prescan-elevation",
}
PATH_KEYS = {"image", "out_dir", "anchors_json", "candidates_json"}
# R2-2: parameters this wrapper turns into an OUTPUT LANDING POINT. `out_dir` is
# the only one across all of ALLOWED_TOOLS (sidecar/crop/overlay/prescan paths
# are all derived from it; `sidecar_name` and `label` are regex-pinned name
# components that cannot traverse). It must resolve into the writable root —
# "inside staging" is not enough, or a request can make this wrapper write into
# the read-only parts of the tree such as `tools/**`.
# This mirrors guard.py's REQUEST_OUTPUT_ROLE_KEYS / OUTPUT_ROOT_DIR on purpose:
# the hook and the wrapper must never disagree about where output may land.
OUTPUT_ROLE_KEYS = {"out_dir"}
OUTPUT_ROOT_DIR = "out"


def _staging_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (FileNotFoundError, ValueError):
        return False


def _resolve(value: str, root: Path) -> Path:
    if value.startswith("~") or ".." in value:
        raise ValueError(f"path token forbidden: {value}")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve(strict=False)
    if not _under(resolved, root):
        raise ValueError(f"path escapes staging: {value}")
    if path.exists() and not _under(path.resolve(strict=True), root):
        raise ValueError(f"symlink target escapes staging: {value}")
    return resolved


def _writable_root(root: Path, name: str) -> Path:
    return (root / name).resolve(strict=False)


def _resolve_output(value: str, root: Path) -> Path:
    resolved = _resolve(value, root)
    try:
        resolved.relative_to(_writable_root(root, OUTPUT_ROOT_DIR))
    except ValueError:
        raise ValueError(
            f"output path must land under {OUTPUT_ROOT_DIR}/, not {value!r}"
        ) from None
    return resolved


def _request_to_argv(request: dict, root: Path) -> list[str]:
    tool = request.get("tool")
    args = request.get("args")
    if tool not in ALLOWED_TOOLS:
        raise ValueError(f"unsupported cv_probe tool: {tool!r}")
    if not isinstance(args, dict):
        raise ValueError("request args must be an object")
    argv = [tool]
    for key, value in args.items():
        opt = f"--{key.replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                argv.append(opt)
            continue
        if key in OUTPUT_ROLE_KEYS:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a path string")
            value = str(_resolve_output(value, root))
        elif key in PATH_KEYS:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a path string")
            value = str(_resolve(value, root))
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        elif value is None:
            continue
        argv.extend([opt, str(value)])
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    ns = parser.parse_args(argv)
    root = _staging_root()
    request_path = _resolve(str(ns.request), root)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    cv_argv = _request_to_argv(request, root)
    sys.path.insert(0, str(root / "tools"))
    from cv_probe import main as cv_main  # noqa: WPS433

    return int(cv_main(cv_argv) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
