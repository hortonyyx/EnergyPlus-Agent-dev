#!/usr/bin/env python3
"""Prepare and invoke the bounded sm21 historical-reading pilot.

This experiment deliberately exposes no native Claude tools.  The model can
only use the sibling ``reading_mcp.py`` server.  Evaluation and GT remain
outside this workspace and outside this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any
from uuid import UUID


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
REV = "723b0f98ed37285b66cb3d1d30caa8e42eb01a74"
MODEL = "claude-haiku-4-5-20251001"
DEFAULT_PROMPT = HERE / "pilot_prompt.md"
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

PROJECTED_PATHS = (
    "skills/intake_pipeline/0_reading/session_kickoff.md",
    "skills/intake_pipeline/0_reading/guide.md",
    "skills/intake_pipeline/0_reading/reading_guide.md",
    "skills/intake_pipeline/0_reading/pen_library.md",
    "skills/intake_pipeline/0_reading/cv_toolbox.md",
    "scripts/tool_scripts/cv_probe.py",
    "scripts/tool_scripts/render_vector_to_png.py",
    "src/__init__.py",
    "src/agent/__init__.py",
    "src/agent/reading/__init__.py",
    "src/agent/reading/schema.py",
    "src/agent/reading/legacy.py",
    "src/agent/reading/cv_toolbox/__init__.py",
    "src/agent/reading/cv_toolbox/tools.py",
    "src/agent/reading/cv_toolbox/recipes.py",
    "src/agent/reading/cv_toolbox/sidecar.py",
    "case_tests/e2e_tests/sm21_anchor/case_data/1f_view.png",
    "case_tests/e2e_tests/sm21_anchor/case_data/testdata_prompt.json",
)
EMPTY_PACKAGE_MARKERS = frozenset({"src/__init__.py", "src/agent/__init__.py"})

IMPLEMENTATION_FILES = (
    "run_historical_pilot.py",
    "reading_mcp.py",
    "verify_offline.py",
    "pilot_prompt.md",
)

_SECRET_VALUE = re.compile(
    r"(?i)(\b(?:[A-Za-z0-9_]*?(?:api[_ -]?key|authorization|auth[_ -]?token|"
    r"access[_ -]?token|oauth[_ -]?token|password|secret|token)))"
    r"(\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"
)
_BEARER_VALUE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SK_VALUE = re.compile(r"\bsk-[A-Za-z0-9_-]+")


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def _git_blob(path: str) -> bytes:
    if path not in PROJECTED_PATHS:
        raise ValueError(f"path is not in the projection allowlist: {path}")
    return subprocess.check_output(
        ["git", "show", f"{REV}:{path}"], cwd=REPO
    )


def build_workspace(target: Path) -> dict[str, Any]:
    """Create a byte-exact 723 allowlist projection at a new path."""
    target = target.resolve()
    if target.exists():
        raise FileExistsError(f"refusing existing workspace: {target}")
    target.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    for name in PROJECTED_PATHS:
        if name in EMPTY_PACKAGE_MARKERS:
            # Import only the frozen reading package.  The historical
            # src.agent package initializer imports the whole application graph,
            # which is deliberately absent from this projection.  This matches
            # the compatibility markers used by the 09-16 reproduction.
            data = b""
            source = "experiment:empty_package_marker"
        else:
            data = _git_blob(name)
            source = f"git:{REV}:{name}"
        output_name = name
        if name.startswith("case_tests/e2e_tests/sm21_anchor/case_data/"):
            output_name = "case_data/" + Path(name).name
        destination = target / output_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        destination.chmod(0o444)
        records.append(
            {
                "projected_path": output_name,
                "source": source,
                "sha256": digest_bytes(data),
                "bytes": len(data),
            }
        )

    (target / "0_reading").mkdir()
    (target / "requests").mkdir()
    manifest = {
        "schema": "historical_sm21_pilot_projection_v1",
        "revision": REV,
        "case": "sm21_anchor",
        "scope": "1f_view.png only",
        "files": records,
        "excluded": [
            "same-layout smalloffice_20 worked example",
            "GT and scorer inputs",
            "all prior sm21 runs and answers",
            ".git and repository browsing",
            "home and credentials",
        ],
    }
    dump(target / "projection_manifest.json", manifest)
    return manifest


def implementation_manifest() -> dict[str, Any]:
    rows = []
    for name in IMPLEMENTATION_FILES:
        path = HERE / name
        if path.is_file():
            rows.append(
                {
                    "path": name,
                    "sha256": digest_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    return {"schema": "historical_sm21_pilot_implementation_v1", "files": rows}


def cli_cwd_for(out: Path) -> Path:
    key = hashlib.sha256(str(out.resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"energyplus-historical-sm21-cli-{key}"


def prepare(out: Path) -> None:
    out = out.resolve()
    if out.exists():
        raise FileExistsError(f"refusing existing run directory: {out}")
    out.mkdir(parents=True)
    manifest = build_workspace(out / "workspace")
    (out / "invocations").mkdir()
    # Claude associates persisted sessions with cwd. Keep one stable, input-free
    # cwd outside the repository for the first turn and every --resume turn.
    cli_cwd = cli_cwd_for(out)
    cli_cwd.mkdir(exist_ok=True)
    dump(out / "cli_cwd.json", {"path": str(cli_cwd), "contains_admitted_inputs": False})
    dump(out / "input_manifest.json", manifest)
    implementation = implementation_manifest()
    dump(out / "implementation_manifest.json", implementation)
    print(
        json.dumps(
            {
                "run": str(out),
                "workspace": str(out / "workspace"),
                "cli_cwd": str(cli_cwd),
                "input_files": len(manifest["files"]),
                "implementation_files": len(implementation["files"]),
            },
            ensure_ascii=False,
        )
    )


def _isolated_env() -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in ("PATH", "HOME", "LANG", "LC_ALL")
        if key in os.environ
    }
    env["ENABLE_TOOL_SEARCH"] = "false"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _redact(text: str) -> str:
    text = _SECRET_VALUE.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text
    )
    text = _BEARER_VALUE.sub("Bearer [REDACTED]", text)
    return _SK_VALUE.sub("sk-[REDACTED]", text)


def _terminate_group(process: subprocess.Popen[str]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def command_for(run_root: Path, *, resume: bool) -> list[str]:
    workspace = run_root / "workspace"
    session_file = run_root / "session_id.txt"
    if not workspace.is_dir():
        raise RuntimeError("run workspace is missing; run prepare first")
    server = [
        sys.executable,
        str((HERE / "reading_mcp.py").resolve()),
        "serve",
        "--workspace",
        str(workspace.resolve()),
    ]
    mcp_config = {
        "mcpServers": {
            "reading": {
                "command": server[0],
                "args": server[1:],
                "alwaysLoad": True,
            }
        }
    }
    system_prompt = (
        "Perform only the supplied historical reading pilot. Use only the reading MCP. "
        "The MCP is the complete admitted information surface; unavailable paths must "
        "not be reconstructed or requested. Inspect original pixels, keep uncertain "
        "claims explicit, and submit one 1F reading for external source-only review."
    )
    command = [
        "claude",
        "-p",
        "--model",
        MODEL,
        "--tools",
        "",
        "--allowedTools",
        "mcp__reading__*",
        "--permission-mode",
        "dontAsk",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--settings",
        '{"disableAllHooks":true}',
        "--disable-slash-commands",
        "--mcp-config",
        json.dumps(mcp_config, separators=(",", ":")),
        "--output-format",
        "stream-json",
        "--verbose",
        "--system-prompt",
        system_prompt,
    ]
    if resume:
        if not session_file.is_file():
            raise RuntimeError("resume requested but session_id.txt is missing")
        session_id = session_file.read_text(encoding="utf-8").strip()
        try:
            session_id = str(UUID(session_id))
        except ValueError as error:
            raise RuntimeError("session_id.txt does not contain a valid UUID") from error
        command.extend(["--resume", session_id])
    return command


def command_record(command: list[str]) -> list[str]:
    recorded = list(command)
    system_index = recorded.index("--system-prompt") + 1
    recorded[system_index] = "[system prompt stored separately]"
    return recorded


def _snapshot(workspace: Path, invocation_dir: Path) -> dict[str, Any]:
    snapshot = invocation_dir / "snapshot"
    snapshot.mkdir()
    for name in ("0_reading", "requests"):
        source = workspace / name
        if source.exists():
            shutil.copytree(source, snapshot / name)
    for name in ("artifact_registry.json", "mcp_tools.jsonl", "projection_manifest.json"):
        source = workspace / name
        if source.is_file():
            shutil.copy2(source, snapshot / name)
    files = []
    for path in sorted(snapshot.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": str(path.relative_to(snapshot)),
                    "sha256": digest_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    result = {"schema": "historical_sm21_pilot_snapshot_v1", "files": files}
    dump(invocation_dir / "snapshot_manifest.json", result)
    return result


def invoke(
    *, out: Path, prompt_path: Path, label: str, resume: bool, timeout: int
) -> None:
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if not LABEL_RE.fullmatch(label):
        raise ValueError("label must match [A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
    run_root = out.resolve()
    workspace = run_root / "workspace"
    invocations = run_root / "invocations"
    session_file = run_root / "session_id.txt"
    for required in (workspace, invocations):
        if not required.is_dir():
            raise RuntimeError(f"prepared run directory is missing {required.name}/")
    cli_cwd_record = json.loads((run_root / "cli_cwd.json").read_text(encoding="utf-8"))
    cli_cwd = Path(cli_cwd_record.get("path", "")).resolve()
    if cli_cwd != cli_cwd_for(run_root).resolve():
        raise RuntimeError("cli_cwd.json does not match this run's stable isolated cwd")
    cli_cwd.mkdir(exist_ok=True)
    prompt_path = prompt_path.resolve()
    if not prompt_path.is_file():
        raise FileNotFoundError(prompt_path)
    prompt = prompt_path.read_text(encoding="utf-8")
    invocation_dir = invocations / label
    invocation_dir.mkdir(parents=True, exist_ok=False)
    (invocation_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    command = command_for(run_root, resume=resume)
    system_prompt = command[command.index("--system-prompt") + 1]
    dump(
        invocation_dir / "request.json",
        {
            "model_requested": MODEL,
            "channel": "Claude subscription OAuth; no API provider or fallback",
            "resume": resume,
            "timeout_seconds": timeout,
            "command": command_record(command),
            "system_prompt": system_prompt,
            "prompt_sha256": digest_bytes(prompt.encode("utf-8")),
            "input_manifest_sha256": digest_file(run_root / "input_manifest.json"),
            "implementation_manifest_sha256": digest_file(
                run_root / "implementation_manifest.json"
            ),
        },
    )

    env = _isolated_env()
    version = subprocess.check_output(
        ["claude", "--version"], env=env, text=True
    ).strip()
    stdout_path = invocation_dir / "events.jsonl"
    stderr_path = invocation_dir / "stderr.txt"
    started = time.monotonic()
    timed_out = False
    with stdout_path.open("x", encoding="utf-8") as stdout, stderr_path.open(
        "x", encoding="utf-8"
    ) as stderr:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=stderr,
            cwd=cli_cwd,
            env=env,
            text=True,
            start_new_session=True,
        )
        try:
            process.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_group(process)

    stdout_path.write_text(_redact(stdout_path.read_text(encoding="utf-8")), encoding="utf-8")
    stderr_path.write_text(_redact(stderr_path.read_text(encoding="utf-8")), encoding="utf-8")
    events = []
    for line in stdout_path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    result = next((event for event in reversed(events) if event.get("type") == "result"), {})
    session_id = next(
        (event.get("session_id") for event in events if event.get("session_id")), None
    )
    if session_id:
        try:
            session_id = str(UUID(session_id))
        except ValueError as error:
            raise RuntimeError("Claude stream returned an invalid session ID") from error
        session_file.write_text(session_id + "\n", encoding="utf-8")
    receipt = {
        "model_requested": MODEL,
        "actual_models": sorted(
            {
                event.get("message", {}).get("model")
                for event in events
                if event.get("message", {}).get("model")
            }
        ),
        "cli_version": version,
        "channel": "Claude subscription OAuth; no API provider or fallback",
        "resume": resume,
        "session_id": session_id,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "returncode": process.returncode,
        "result": result,
    }
    dump(invocation_dir / "receipt.json", receipt)
    snapshot = _snapshot(workspace, invocation_dir)
    print(
        json.dumps(
            {**receipt, "snapshot_files": len(snapshot["files"])},
            ensure_ascii=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--out", type=Path, required=True)
    invoke_parser = subparsers.add_parser("invoke")
    invoke_parser.add_argument("--out", type=Path, required=True)
    invoke_parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    invoke_parser.add_argument("--label", required=True)
    invoke_parser.add_argument("--resume", action="store_true")
    invoke_parser.add_argument("--timeout", type=int, default=1200)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.out)
    else:
        invoke(
            out=args.out,
            prompt_path=args.prompt,
            label=args.label,
            resume=args.resume,
            timeout=args.timeout,
        )


if __name__ == "__main__":
    main()
