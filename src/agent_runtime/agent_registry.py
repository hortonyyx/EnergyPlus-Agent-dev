"""Version the model-facing Agent files and exact MCP tool catalogs.

The registry is deliberately independent of the runtime code version.  It lets
two runners use the same tools, guidance, and task helpers while their harness
implementations differ.  Registering a version is an explicit local operation;
normal runs only verify the selected record.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Mapping


REGISTRY_RELATIVE_PATH = Path("src/agent_runtime/agent_versions.json")
_VERSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CATALOG_MODES = ("coordinator", "readonly", "coordinator_mesh", "readonly_mesh")
_FILE_KINDS = frozenset({"tool", "guidance", "task_description"})


class AgentVersionMismatch(ValueError):
    """The checked-out Agent files or live tool catalog differ from a record."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _registry_path(root: Path, registry_path: Path | None) -> Path:
    root = Path(root).resolve()
    # Explicit scratch registries let independently owned packages verify their
    # complete working files without editing the shared release registry. The
    # same strict file/catalog hash checks apply; nothing is auto-registered.
    override = os.environ.get("BIM_AGENT_REGISTRY_PATH") if registry_path is None else None
    if override is not None and not Path(override).is_absolute():
        raise ValueError("BIM_AGENT_REGISTRY_PATH must be absolute")
    path = Path(registry_path) if registry_path is not None else Path(override) if override else root / REGISTRY_RELATIVE_PATH
    return path.resolve()


def load_agent_registry(root: Path, registry_path: Path | None = None) -> dict[str, Any]:
    path = _registry_path(root, registry_path)
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AgentVersionMismatch(f"Agent version registry does not exist: {path}") from error
    if registry.get("schema_version") != "agent-version-registry.v1":
        raise AgentVersionMismatch("unsupported Agent version registry schema")
    versions = registry.get("versions")
    current = registry.get("current_version")
    if not isinstance(versions, dict) or not isinstance(current, str) or current not in versions:
        raise AgentVersionMismatch("Agent version registry has no valid current version")
    return registry


def agent_version_record(
    root: Path,
    version_id: str | None = None,
    *,
    registry_path: Path | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    """Return one registry record, optionally checking every registered file."""

    root = Path(root).resolve()
    registry = load_agent_registry(root, registry_path)
    selected = version_id or registry["current_version"]
    record = registry["versions"].get(selected)
    if not isinstance(record, dict):
        raise AgentVersionMismatch(f"Agent version is not registered: {selected}")
    if verify:
        changed: dict[str, str] = {}
        files = record.get("files")
        if not isinstance(files, dict) or not files:
            raise AgentVersionMismatch(f"Agent version {selected} has no registered files")
        for relative, metadata in files.items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                raise AgentVersionMismatch(f"registered Agent file escapes repository root: {relative}")
            expected = metadata.get("sha256") if isinstance(metadata, dict) else None
            actual = _sha256(path) if path.is_file() else "missing"
            if actual != expected:
                changed[relative] = actual
        if changed:
            raise AgentVersionMismatch(
                f"Agent version {selected} file mismatch: {json.dumps(changed, sort_keys=True)}"
            )
    return {"version_id": selected, **record}


async def _probe_tool_catalogs(root: Path) -> dict[str, str]:
    """Start the local MCP server and hash all four admitted-input catalogs."""

    from src.agent_runtime.mcp_tools import McpToolClient

    server = root / "scripts/tool_scripts/run_bim_agent.py"
    result: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix=".agent-registry-", dir=root) as temporary:
        base = Path(temporary)
        for mode in _CATALOG_MODES:
            run = base / mode
            run.mkdir()
            manifest: dict[str, Any] = {"images": {}, "scope": "Agent catalog registration"}
            if mode.endswith("_mesh"):
                manifest["mesh_input"] = {
                    "sha256": "0" * 64,
                    "frozen_path": "assets/registration-placeholder.glb",
                }
            run.joinpath("inputs.json").write_text(
                json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
            )
            arguments = [str(server), "serve", str(run)]
            if mode.startswith("readonly"):
                arguments.append("--readonly")
            async with McpToolClient(
                command=sys.executable, args=arguments, cwd=root, run_directory=run
            ) as client:
                tools = await client.list_tools()
            result[mode] = hashlib.sha256(_canonical_json_bytes(tools)).hexdigest()
    return result


def register_agent_version(
    root: Path,
    version_id: str,
    *,
    registry_path: Path | None = None,
    catalog_hashes: Mapping[str, str] | None = None,
    additional_files: Mapping[str, str] | None = None,
    make_current: bool = True,
) -> dict[str, Any]:
    """Hash the current registered file set and append a new immutable version."""

    if not _VERSION_ID.fullmatch(version_id):
        raise ValueError("version ID must use 1-128 letters, digits, dots, underscores, or hyphens")
    root = Path(root).resolve()
    path = _registry_path(root, registry_path)
    registry = load_agent_registry(root, path)
    if version_id in registry["versions"]:
        raise ValueError(f"Agent version already exists: {version_id}")
    base = registry["versions"][registry["current_version"]]
    files: dict[str, dict[str, str]] = {}
    for relative, metadata in base["files"].items():
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError(f"cannot register missing or out-of-root Agent file: {relative}")
        files[relative] = {"kind": metadata["kind"], "sha256": _sha256(target)}
    for relative, kind in (additional_files or {}).items():
        if kind not in _FILE_KINDS:
            raise ValueError(f"unsupported Agent file kind for {relative}: {kind}")
        target = (root / relative).resolve()
        if (not target.is_relative_to(root) or not target.is_file()
                or Path(relative).is_absolute()):
            raise ValueError(f"cannot register missing or out-of-root Agent file: {relative}")
        normalized = target.relative_to(root).as_posix()
        files[normalized] = {"kind": kind, "sha256": _sha256(target)}
    if catalog_hashes is None:
        catalog_hashes = asyncio.run(_probe_tool_catalogs(root))
    catalogs = dict(catalog_hashes)
    if set(catalogs) != set(_CATALOG_MODES):
        raise ValueError(f"tool catalog hashes must cover exactly: {', '.join(_CATALOG_MODES)}")
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in catalogs.values()):
        raise ValueError("tool catalog hashes must be lowercase SHA-256 values")
    try:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        source_commit = "unknown"
    record = {
        "source_commit": source_commit,
        "files": files,
        "tool_catalog_sha256": {mode: catalogs[mode] for mode in _CATALOG_MODES},
    }
    registry["versions"][version_id] = record
    if make_current:
        registry["current_version"] = version_id
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return {"version_id": version_id, **record}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register and verify model-facing Agent versions")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser("verify", help="verify a registered version")
    verify_parser.add_argument("--version")
    register_parser = subparsers.add_parser("register", help="register current Agent bytes as a new version")
    register_parser.add_argument("--version", required=True)
    register_parser.add_argument(
        "--add-file", action="append", default=[], metavar="KIND:PATH",
        help="also register a new tool, guidance, or task_description file",
    )
    for command_parser in (verify_parser, register_parser):
        command_parser.add_argument("--root", type=Path, default=Path.cwd())
        command_parser.add_argument("--registry", type=Path)
    args = parser.parse_args(argv)
    if args.command == "verify":
        record = agent_version_record(
            args.root, args.version, registry_path=args.registry, verify=True
        )
    else:
        additions: dict[str, str] = {}
        for item in args.add_file:
            try:
                kind, relative = item.split(":", 1)
            except ValueError as error:
                raise ValueError("--add-file must be KIND:PATH") from error
            if not relative or relative in additions:
                raise ValueError("--add-file paths must be non-empty and unique")
            additions[relative] = kind
        record = register_agent_version(
            args.root, args.version, registry_path=args.registry,
            additional_files=additions,
        )
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
