#!/usr/bin/env python3
"""Build, spawn, review, and merge isolated 0_reading workspaces."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.execution.isolation import (  # noqa: E402
    build_isolation_workspace,
    merge_isolated_output,
    spawn_command,
    write_feedback,
)


def _cmd_build(args: argparse.Namespace) -> int:
    manifest = build_isolation_workspace(
        args.case_dir,
        run_dir=args.run_dir,
        staging_root=args.staging_root,
    )
    print(manifest.staging_root)
    return 0


def _cmd_spawn(args: argparse.Namespace) -> int:
    cmd = spawn_command(args.staging_root, model=args.model, execute=args.execute)
    if not args.execute:
        print(shlex.join(cmd))
    return 0


def _cmd_feedback(args: argparse.Namespace) -> int:
    text = args.text
    if args.file:
        text = args.file.read_text(encoding="utf-8")
    path = write_feedback(args.staging_root, text, name=args.name)
    print(path)
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    attempt_dir = merge_isolated_output(
        args.staging_root,
        args.run_dir,
        output_path=args.output,
        accept=not args.no_accept,
    )
    print(json.dumps({"attempt_dir": str(attempt_dir)}, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build")
    p.add_argument("--case-dir", required=True, type=Path)
    p.add_argument("--run-dir", type=Path)
    p.add_argument("--staging-root", type=Path)
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("spawn")
    p.add_argument("--staging-root", required=True, type=Path)
    p.add_argument("--model")
    p.add_argument("--execute", action="store_true")
    p.set_defaults(func=_cmd_spawn)

    p = sub.add_parser("feedback")
    p.add_argument("--staging-root", required=True, type=Path)
    p.add_argument("--text", default="")
    p.add_argument("--file", type=Path)
    p.add_argument("--name", default="feedback.md")
    p.set_defaults(func=_cmd_feedback)

    p = sub.add_parser("merge")
    p.add_argument("--staging-root", required=True, type=Path)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--no-accept", action="store_true")
    p.set_defaults(func=_cmd_merge)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
